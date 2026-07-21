import sys
sys.path.insert(0, 'src')

from t5gweb.database.session import db_config
from t5gweb.database.models import JiraCard
from sqlalchemy import func

session = db_config.SessionLocal()

# Check if any cards have multiple sprints stored (they shouldn't)
print("=== Sprint Distribution in Database ===")
sprints = session.query(JiraCard.sprint, func.count(JiraCard.jira_card_id))\
    .filter(JiraCard.sprint.isnot(None))\
    .group_by(JiraCard.sprint)\
    .order_by(func.count(JiraCard.jira_card_id).desc())\
    .limit(10)\
    .all()

for sprint, count in sprints:
    print(f"{sprint}: {count} cards")

# Check a specific case that might have moved between sprints
print("\n=== Example: Cards that might have moved sprints ===")
sample_cards = session.query(JiraCard.jira_card_id, JiraCard.case_number, JiraCard.sprint)\
    .filter(JiraCard.sprint.isnot(None))\
    .limit(5)\
    .all()

for card_id, case_num, sprint in sample_cards:
    print(f"{card_id} (Case {case_num}): Sprint = '{sprint}'")

session.close()
