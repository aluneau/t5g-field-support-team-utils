# Engineering View Implementation Plan

## Overview
Create a new "Engineering View" page in the Python Flask dashboard that mirrors the functionality of the Vue.js `CasesList.vue` component from `~/Projets/new-dashboard-front`, but using server-side rendering with Jinja2 templates and querying data directly from PostgreSQL.

## Requirements

### Core Functionality
- Display cases that need engineering attention
- Show cases where customer has commented after engineering team
- Read-only view (no comment posting - that's for later)
- Display both portal and JIRA comments in expandable rows

### Filtering Logic
Cases must meet ALL of these criteria:
1. **Portal Status**: NOT "Closed" (`Case.status != 'Closed'`)
2. **Has JIRA Card**: Must have an associated `JiraCard` record
3. **Current Sprint**: `JiraCard.sprint` matches the currently active sprint from JIRA
4. **Needs Attention**: Most recent portal comment is newer than the most recent JIRA comment

The filtering algorithm (from Vue reference):
```javascript
// Skip if no jira comments exist
if (c.jiraComments[0] == undefined) return null;

let jiraCommentLastUpdateDate = new Date(c.jiraComments[0].updated)
let portalCommentLastUpdateDate = new Date(c.portalComments?.[0]?.publishedDate || "1970-01-01")

// Show case only if portal comment is newer than jira comment
if (jiraCommentLastUpdateDate >= portalCommentLastUpdateDate) {
    return null;  // Filter out
}
return c;  // Include
```

### Columns to Display
Match the Vue dashboard columns exactly:
1. **Case Number** - Link to Red Hat portal (`Case.case_number`)
2. **Severity** - Display as badge (`Case.severity`)
3. **Summary** - Case title (`Case.summary`)
4. **Field Engineer Assigned** - JIRA assignee (`JiraCard.assignee`, show "None" if null)
5. **Most Recent Comment** - Show most recent JIRA comment with date and preview
6. **Portal Status** - Case status (`Case.status`)
7. **Jira Status** - Card status (`JiraCard.status`)

### Expandable Row Details
When row is expanded, show two-column layout:
- **Left column (60%)**: Portal comments
  - Scrollable list
  - Each comment shows: author, date, comment body (rendered as markdown)
  - Styled by comment type (customer/associate/bug)
- **Right column (40%)**: JIRA comments  
  - Scrollable list
  - Each comment shows: author, date, comment body (rendered as markdown)
  - Sorted by date (newest first)

### Sprint Detection
- Query JIRA API using `get_latest_sprint(conn, board_id, sprintname)` to get active sprint
- Filter `JiraCard` records where `sprint` field matches the active sprint name/ID
- This ensures view always shows current sprint without manual config updates

### Technical Decisions

#### NOT Implemented (Deferred)
- ❌ `critSit` field (not in schema, skip for now)
- ❌ `noUpdateDate` field (skip for now, add later when implementing "Not changed" button)
- ❌ Comment posting functionality (textarea, Submit button, "Not changed" button)
- ❌ AI-generated comment suggestions

#### Data Source
- Query PostgreSQL directly (NOT Redis cache)
- Join `Case`, `Comment`, `JiraCard`, `JiraComment` tables

#### Presentation
- Server-side rendered Jinja2 template (NOT REST API)
- Use DataTables library (like existing views)
- Expandable rows pattern (like existing `cases_table` macro)

#### Route
- URL: `/engineering`
- Add to navigation menu in `skeleton.html`

## Implementation Steps

### 1. Database Query Function
Create a new function in `t5gweb/t5gweb.py` or `t5gweb/database/operations.py`:

```python
def get_engineering_cases(active_sprint_name):
    """
    Query cases that need engineering attention for the current sprint.
    
    Returns dict structure matching Vue dashboard format:
    {
        case_number: {
            'case_number': str,
            'severity': int,
            'summary': str,
            'field_engineer': str,
            'portal_status': str,
            'jira_status': str,
            'portal_comments': [...],
            'jira_comments': [...],
            'most_recent_jira_comment': {...}
        }
    }
    """
    # 1. Join Case + JiraCard + Comments
    # 2. Filter: status != 'Closed', sprint == active_sprint_name, has jira card
    # 3. Load portal comments (ordered by date desc)
    # 4. Load jira comments (ordered by date desc)  
    # 5. Apply filtering: portal comment newer than jira comment
    # 6. Return structured dict
```

### 2. Route Handler
Add to `t5gweb/ui.py`:

```python
@BP.route("/engineering")
@login_required
def engineering_view():
    """Display engineering cases needing attention for current sprint"""
    cfg = set_cfg()
    
    # Get JIRA connection
    jira_conn = get_jira_connection(cfg)
    
    # Get active sprint
    board_id = get_board_id(jira_conn, cfg["board"])
    active_sprint = get_latest_sprint(jira_conn, board_id.id, cfg["sprintname"])
    
    # Query cases
    engineering_cases = get_engineering_cases(active_sprint.name)
    
    return render_template(
        "ui/engineering.html",
        cases=engineering_cases,
        active_sprint=active_sprint.name,
        jira_server=cfg["server"],
        page_title="Engineering View"
    )
```

### 3. Jinja2 Template
Create `src/t5gweb/templates/ui/engineering.html`:

```html
{% extends "skeleton.html" %}
{% import 'macros/macros.html' as macros %}
{% block title %}{{ page_title }}{% endblock %}
{% block content %}
    <div class="container-fluid copy mt-5">
        <h2>Engineering View - {{ active_sprint }}</h2>
        {{ macros.engineering_cases_table(cases, jira_server) }}
    </div>
    {{ macros.include_datatables_js_css() }}
    {{ macros.include_datatables_plugins_js_css() }}
    <script src="{{ url_for('static', filename='js/engineering.js') }}"></script>
{% endblock %}
```

### 4. Macro for Table
Add to `src/t5gweb/templates/macros/macros.html`:

```jinja2
{% macro engineering_cases_table(cases, jira_server) -%}
    <table class="table table-bordered table-hover" id="engineering-data">
        <thead>
            <tr>
                <th></th>  <!-- Expander -->
                <th>Case#</th>
                <th>Severity</th>
                <th>Summary</th>
                <th>Field Engineer</th>
                <th>Most Recent Comment</th>
                <th>Portal Status</th>
                <th>Jira Status</th>
            </tr>
        </thead>
        <tbody>
            {% for case_number, case_data in cases.items() %}
            <tr data-child-data="{{ case_data | tojson | forceescape }}">
                <td class="dt-control"></td>
                <td>
                    <a href="https://access.redhat.com/support/cases/#/case/{{ case_number }}" target="_blank">
                        {{ case_number }}
                    </a>
                </td>
                <td><span class="badge severity">{{ case_data.severity }}</span></td>
                <td>{{ case_data.summary }}</td>
                <td>{{ case_data.field_engineer or "None" }}</td>
                <td>
                    {% if case_data.most_recent_jira_comment %}
                        <strong>{{ case_data.most_recent_jira_comment.updated }}</strong>
                        {{ case_data.most_recent_jira_comment.body[:100] }}...
                    {% else %}
                        No comments
                    {% endif %}
                </td>
                <td>{{ case_data.portal_status }}</td>
                <td>{{ case_data.jira_status }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
{%- endmacro %}
```

### 5. Child Row Template (Expandable)
The child row content should render:
- Portal comments on left (styled with borders for customer/associate/bug)
- JIRA comments on right
- Use grid layout (similar to Vue: `grid-cols-5`, left gets `col-span-3`, right gets `col-span-2`)

### 6. JavaScript for DataTables
Create `src/t5gweb/static/js/engineering.js`:
- Initialize DataTable on `#engineering-data`
- Handle row expansion/collapse
- Render child rows with two-column comment layout
- Enable search, sorting, pagination

### 7. Navigation Link
Update `src/t5gweb/templates/skeleton.html`:
- Add "Engineering View" link to navigation menu
- Link to `/engineering` route

## Data Structure Reference

### Database Schema Relationships
```
Case (1) --> (N) Comment [portal comments]
Case (1) --> (N) JiraCard
JiraCard (1) --> (N) JiraComment
```

### Join Query Pattern
```sql
SELECT 
    c.case_number,
    c.severity,
    c.summary,
    c.status as portal_status,
    jc.assignee as field_engineer,
    jc.status as jira_status,
    jc.sprint
FROM cases c
INNER JOIN jira_cards jc 
    ON c.case_number = jc.case_number 
    AND c.created_date = jc.created_date
WHERE c.status != 'Closed'
    AND jc.sprint = :active_sprint_name
```

Then separately load:
- Portal comments: `SELECT * FROM comments WHERE case_number = ? ORDER BY commented_at DESC`
- JIRA comments: `SELECT * FROM jira_comments WHERE jira_card_id = ? ORDER BY last_update_date DESC`

## Testing Checklist
- [ ] Cases filtered correctly (only current sprint, not closed, needs attention)
- [ ] Table displays all required columns
- [ ] Row expansion shows portal and JIRA comments
- [ ] Portal comments styled correctly (customer/associate/bug borders)
- [ ] JIRA comments sorted by date (newest first)
- [ ] Markdown rendering works for comment bodies
- [ ] Search/sort/pagination works
- [ ] Navigation link works
- [ ] Links to portal cases open correctly
- [ ] Handles edge cases (no comments, no assignee, etc.)

## Future Enhancements (Not in This Version)
- Add `no_update_date` field to `Case` model
- Implement "Submit comment" functionality
- Implement "Not changed" button
- Add `crit_sit` field/logic
- AI-generated comment suggestions
- Real-time updates
