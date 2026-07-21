#!/usr/bin/env python3
"""
Resync sprint field from JIRA to PostgreSQL for all cards.

This script fetches all JIRA cards and updates their sprint field in PostgreSQL
to match the current sprint value in JIRA.
"""

import sys
import os
import logging

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from t5gweb.utils import set_cfg
from t5gweb.api import get_jira_connection
from t5gweb.database.session import db_config
from t5gweb.database.models import JiraCard
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def resync_all_sprints():
    """Resync sprint field for all JIRA cards in database"""

    # Get JIRA connection
    cfg = set_cfg()
    jira_conn = get_jira_connection(cfg)

    session = db_config.SessionLocal()

    try:
        # Get all JIRA cards from database
        all_cards = session.query(JiraCard).all()
        logging.info(f"Found {len(all_cards)} cards in database to resync")

        updated_count = 0
        error_count = 0
        no_change_count = 0

        for i, card in enumerate(all_cards, 1):
            try:
                # Fetch current data from JIRA
                issue = jira_conn.issue(card.jira_card_id)

                # Extract sprint value - use the LAST sprint (most recent)
                sprint_value = None
                if hasattr(issue.fields, "customfield_10020") and issue.fields.customfield_10020:
                    sprint_obj = issue.fields.customfield_10020[-1]  # Get last sprint
                    raw_sprint_name = getattr(sprint_obj, 'name', str(sprint_obj))

                    # Normalize sprint name to "T5GFE Sprint XXX" format
                    match = re.search(r'Sprint\s+(\d+)', raw_sprint_name)
                    if match:
                        sprint_value = f"T5GFE Sprint {match.group(1)}"
                    else:
                        sprint_value = raw_sprint_name

                # Update if changed
                if card.sprint != sprint_value:
                    old_sprint = card.sprint
                    card.sprint = sprint_value
                    session.merge(card)
                    updated_count += 1
                    logging.info(f"[{i}/{len(all_cards)}] {card.jira_card_id}: '{old_sprint}' → '{sprint_value}'")
                else:
                    no_change_count += 1

                # Commit every 50 cards to avoid large transactions
                if i % 50 == 0:
                    session.commit()
                    logging.info(f"Progress: {i}/{len(all_cards)} cards processed")

            except Exception as e:
                logging.error(f"Error processing {card.jira_card_id}: {e}")
                error_count += 1
                session.rollback()
                continue

        # Final commit
        session.commit()

        logging.info("=" * 60)
        logging.info("Resync Summary:")
        logging.info(f"  Total cards: {len(all_cards)}")
        logging.info(f"  Updated: {updated_count}")
        logging.info(f"  No change: {no_change_count}")
        logging.info(f"  Errors: {error_count}")
        logging.info("=" * 60)

        # Show sprint distribution after update
        from sqlalchemy import func
        sprint_counts = session.query(JiraCard.sprint, func.count(JiraCard.jira_card_id))\
            .filter(JiraCard.sprint.isnot(None))\
            .group_by(JiraCard.sprint)\
            .order_by(func.count(JiraCard.jira_card_id).desc())\
            .limit(10)\
            .all()

        logging.info("\nSprint distribution after sync:")
        for sprint, count in sprint_counts:
            logging.info(f"  {sprint}: {count} cards")

    except Exception as e:
        logging.error(f"Failed to resync sprints: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    logging.info("Starting sprint resync...")
    resync_all_sprints()
    logging.info("Sprint resync completed!")
