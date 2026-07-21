#!/usr/bin/env python3
"""Test script to debug engineering view filtering"""

import sys
sys.path.insert(0, '/home/aluneau/Projets/t5g-field-support-team-utils/dashboard/src')

from datetime import datetime, timezone
from t5gweb.database.session import db_config
from t5gweb.database.models import Case, JiraCard, JiraComment, Comment
from sqlalchemy import func

session = db_config.SessionLocal()

# Get sprint name - hardcode for now
active_sprint_name = "RAN Automation Sprint 291"

# Query cases with JIRA cards in active sprint
cases_query = (
    session.query(Case, JiraCard)
    .join(JiraCard,
          (Case.case_number == JiraCard.case_number) &
          (Case.created_date == JiraCard.created_date))
    .filter(Case.status != 'Closed')
    .filter(JiraCard.sprint == active_sprint_name)
)

all_cases = cases_query.all()
print(f"Total cases in sprint '{active_sprint_name}' (not closed): {len(all_cases)}")

# Check specific case
test_case_number = "04450735"
test_case = session.query(Case, JiraCard).join(
    JiraCard,
    (Case.case_number == JiraCard.case_number) &
    (Case.created_date == JiraCard.created_date)
).filter(Case.case_number == test_case_number).first()

if test_case:
    case, jira_card = test_case
    print(f"\nCase {test_case_number} found:")
    print(f"  Status: {case.status}")
    print(f"  Sprint: {jira_card.sprint}")
    print(f"  Assignee: {jira_card.assignee}")

    # Check comments
    portal_comments = session.query(Comment).filter(
        Comment.case_number == test_case_number
    ).order_by(Comment.commented_at.desc()).all()

    jira_comments = session.query(JiraComment).filter(
        JiraComment.jira_card_id == jira_card.jira_card_id
    ).order_by(JiraComment.last_update_date.desc()).all()

    print(f"  Portal comments: {len(portal_comments)}")
    if portal_comments:
        print(f"    Most recent: {portal_comments[0].commented_at}")

    print(f"  JIRA comments: {len(jira_comments)}")
    if jira_comments:
        print(f"    Most recent: {jira_comments[0].last_update_date}")

    # Apply filtering logic
    if not jira_comments:
        print("  DECISION: INCLUDE (no JIRA comments)")
    else:
        jira_last = jira_comments[0].last_update_date
        portal_last = portal_comments[0].commented_at if portal_comments else datetime(1970, 1, 1, tzinfo=timezone.utc)

        if jira_last >= portal_last:
            print(f"  DECISION: EXCLUDE (JIRA {jira_last} >= portal {portal_last})")
        else:
            print(f"  DECISION: INCLUDE (portal {portal_last} > JIRA {jira_last})")
else:
    print(f"\nCase {test_case_number} NOT FOUND in database")

session.close()
