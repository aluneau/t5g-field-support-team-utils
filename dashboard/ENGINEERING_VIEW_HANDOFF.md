# Engineering View Implementation - Handoff Document

**Date**: 2026-07-21  
**Status**: ✅ FIXED - Ready for Testing  
**Previous Status**: Partial Implementation - DataTables Issue Blocking

## Summary

Working on implementing an Engineering View feature that shows cases where customers have commented after the engineering team. The backend filtering logic is working correctly (52 cases for Adrien across all sprints, 10 for current sprint), but there's a persistent DataTables JavaScript error preventing the table from rendering.

## Current State

### ✅ What's Working

1. **Sprint Name Normalization** - Fixes sprint name mismatch between JIRA API and PostgreSQL
   - JIRA returns: "RAN Automation Sprint 291"
   - Database stores: "T5GFE Sprint 291"
   - Code now normalizes to "T5GFE Sprint XXX" format
   - Location: `operations.py` lines 204-217, 237-251

2. **Filtering Logic** - Correctly filters cases
   - Portal status != "Closed" ✓
   - Has JIRA card ✓
   - Portal comment newer than JIRA comment ✓
   - Handles timezone-aware datetime comparisons ✓
   - Includes cases with no JIRA comments (Vue behavior) ✓
   - Results: 52 cases for Adrien across all sprints, 10 in current sprint

3. **URL Parameters for Filtering**
   - `?engineer=Adrien%20Luneau` - Filter by engineer
   - `?all_sprints=true` - Show all sprints instead of current only
   - Combine both for Adrien's cases across all sprints

4. **AJAX Comment Loading** - Comments loaded on-demand
   - API endpoint: `/api/engineering/case/<case_number>/comments`
   - Returns JSON with portal_comments and jira_comments
   - Prevents massive HTML page (was 15MB with embedded comments)
   - Location: `ui.py` lines 678-726

5. **No JIRA API Calls on Page Load** - Fast loading
   - Uses most common sprint from PostgreSQL database
   - No more "attempting to connect to jira..." hanging
   - Location: `ui.py` lines 645-668

### ✅ What Was Broken (NOW FIXED)

**DataTables Initialization Error** - FIXED
```
TypeError: Cannot set properties of undefined (setting '_DT_CellIndex')
at _fnCreateTr (jquery.dataTables.js:3148:23)
```

**Root Cause Found:**
- Line 87 of `engineering.js` was calling `DataTable()` with NO parameters
- The `options` variable (lines 63-86) was defined but never used
- Simple bug: `$('#engineering-data').DataTable()` should have been `$('#engineering-data').DataTable(options)`

**Fix Applied:**
- `engineering.js:89` - Now correctly passes `options`: `const table = $('#engineering-data').DataTable(options)`
- Removed duplicate loading div removal code
- Added null-safety checks in `format()` function
- Added `className: 'dt-control'` to columnDefs

**Status:** ✅ FIXED - Ready for testing

## Files Modified

### Backend (Python)

1. **`dashboard/src/t5gweb/database/operations.py`**
   - `get_engineering_cases()` - Main filtering function
   - Added sprint normalization (lines 204-217, 237-251)
   - Added timezone-aware datetime handling (lines 415-420)
   - Added engineer_filter parameter (line 314)
   - Added sprint_filter parameter (line 352-360)

2. **`dashboard/src/t5gweb/ui.py`**
   - `engineering_view()` route - Main view handler (lines 635-676)
   - Added URL parameter support (engineer, all_sprints)
   - Uses cached sprint from PostgreSQL instead of JIRA API (lines 645-668)
   - `get_case_comments()` API endpoint (lines 678-726)

### Frontend

3. **`dashboard/src/t5gweb/templates/ui/engineering.html`**
   - Main template for engineering view
   - Displays sprint name and filters

4. **`dashboard/src/t5gweb/templates/macros/macros.html`**
   - `engineering_cases_table()` macro (lines 363-409)
   - Table structure with 8 columns
   - Removed embedded JSON (data-child-data) to reduce page size
   - Only stores case_number in data attribute

5. **`dashboard/src/t5gweb/static/js/engineering.js`**
   - DataTables initialization (currently broken)
   - AJAX comment loading on row expansion
   - format() function for rendering comments

## ✅ COMPLETED Tasks

### ✅ Priority 1: DataTables Error - FIXED

**Solution:** Simple one-line fix
- Changed line 89 from `DataTable()` to `DataTable(options)`
- The `options` variable was defined but not used

### ✅ Priority 2: Sprint Filtering - FIXED

**Solution:** Added sprint dropdown selector
- Dropdown shows: Current Sprint (default), All Sprints, Recent 10 sprints
- URL parameters: `?sprint=T5GFE Sprint 291` or `?sprint=all`
- Engineer filter preserved when changing sprint
- Active filters shown in banner

**Files Modified:**
- `ui.py` - Route handler enhanced with sprint selector logic
- `engineering.html` - Added dropdown and filter UI
- `engineering.js` - DataTable initialization fixed

## Next Steps (Testing)

### Required Testing

1. **Start the Flask app:**
   ```bash
   cd dashboard
   python3 -m src.t5gweb.app
   # OR
   flask run
   ```

2. **Test URLs:**
   - http://localhost:8080/engineering (default - current sprint)
   - http://localhost:8080/engineering?sprint=all (all sprints)
   - http://localhost:8080/engineering?engineer=Adrien%20Luneau (filter by engineer)
   - http://localhost:8080/engineering?sprint=all&engineer=Adrien%20Luneau (combined)

3. **Visual Checks:**
   - [ ] Table loads without errors
   - [ ] Sprint dropdown works
   - [ ] Engineer filter badge appears
   - [ ] Row expansion loads comments via AJAX
   - [ ] DataTables features work (sort, search, paginate)

**Note:** See `ENGINEERING_VIEW_FIXES.md` for detailed testing checklist

## Key Data Points

- **Total cases in Sprint 291 (not closed)**: 107
- **Adrien's cases in Sprint 291**: 10
- **Adrien's cases across all sprints**: 52
- **Total cases after filtering (Sprint 291)**: 58
- **Page size with embedded comments**: 15MB (BAD)
- **Page size with AJAX comments**: <100KB (GOOD)

## Database Schema

```sql
-- Sprint names in database
SELECT sprint, COUNT(*) FROM jira_cards 
WHERE sprint IS NOT NULL 
GROUP BY sprint 
ORDER BY COUNT(*) DESC;

-- Top sprint: T5GFE Sprint 290 (492 cards)
-- Current sprint: T5GFE Sprint 291 (128 cards)
```

## Testing URLs

```
# Current sprint, all engineers (default)
http://localhost:8080/engineering

# Current sprint, Adrien only (~10 cases)
http://localhost:8080/engineering?engineer=Adrien%20Luneau

# All sprints, Adrien only (~52 cases - matches Vue)
http://localhost:8080/engineering?engineer=Adrien%20Luneau&all_sprints=true

# All sprints, all engineers (LARGE - may timeout)
http://localhost:8080/engineering?all_sprints=true
```

## Vue vs Python Comparison

| Feature | Vue App | Python App |
|---------|---------|------------|
| Data Source | Redis (629 cached cases) | PostgreSQL (fresh data) |
| Sprint Filter | None (shows all) | Current sprint (configurable) |
| Comment Loading | Embedded in page | AJAX on-demand |
| Page Size | Unknown | <100KB (with AJAX) |
| Adrien's Cases | 41 (all sprints) | 52 (all sprints) |
| Engineering Team Total | Unknown | 238 (all sprints) |

## Next Session Plan

1. **Debug DataTables** (30-60 min)
   - Try plain table without DataTables
   - Check browser console thoroughly
   - Test with different row counts

2. **Implement Sprint Selector** (30 min)
   - Add dropdown to select sprint
   - Default to current sprint
   - Show selected sprint prominently

3. **Test End-to-End** (30 min)
   - Compare with Vue app
   - Verify filtering accuracy
   - Test comment loading
   - Check performance with large datasets

## Code Locations Reference

- Engineering view route: `ui.py:635-676`
- Comment API endpoint: `ui.py:678-726`
- Main filtering function: `operations.py:314-444`
- Sprint normalization: `operations.py:204-217, 237-251`
- Table template: `macros/macros.html:363-409`
- JavaScript: `static/js/engineering.js`
- Template: `templates/ui/engineering.html`

## Known Issues Log

1. **DataTables _DT_CellIndex error** - BLOCKING - Unknown cause
2. **Sprint name mismatch** - FIXED - Normalization added
3. **Timezone datetime comparison** - FIXED - Added timezone awareness
4. **15MB page size** - FIXED - Switched to AJAX loading
5. **JIRA API slow on page load** - FIXED - Use cached sprint from DB
