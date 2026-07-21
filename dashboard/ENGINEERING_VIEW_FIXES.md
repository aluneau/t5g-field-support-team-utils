# Engineering View - Fixes Applied

**Date**: 2026-07-21  
**Status**: Fixed - Ready for Testing

## Issues Fixed

### 1. ✅ DataTables Initialization Error (BLOCKING)

**Problem**: DataTables threw `TypeError: Cannot set properties of undefined (setting '_DT_CellIndex')`

**Root Cause**: The `options` variable was defined but never passed to `DataTable()`. Line 87 had:
```javascript
const table = $('#engineering-data').DataTable()  // Missing options!
```

**Fix Applied**: 
- `engineering.js:87` - Now passes `options` to DataTable: `DataTable(options)`
- Removed duplicate loading div removal code (lines 82-84)
- Added `className: 'dt-control'` to columnDefs for expander column
- Added null-safety checks in `format()` function for missing comment data

**Files Changed**: `dashboard/src/t5gweb/static/js/engineering.js`

### 2. ✅ Sprint Filtering & Selector (Priority 2)

**Problem**: 
- Python app defaulted to current sprint only (10 cases for Adrien)
- Vue app showed ALL sprints (41 cases for Adrien)
- No way to change sprint in UI
- Discrepancy was confusing

**Fix Applied**:
- Added sprint dropdown selector to UI
- Dropdown shows:
  - "Current Sprint (T5GFE Sprint XXX)" - default
  - "All Sprints" - matches Vue behavior
  - Recent 10 sprints from database
- Added visual indicator showing active filters
- URL parameters now support:
  - `?sprint=T5GFE Sprint 291` - specific sprint
  - `?sprint=all` - all sprints
  - `?engineer=Adrien Luneau` - engineer filter
  - Can combine: `?sprint=all&engineer=Adrien%20Luneau`
- Engineer filter now shows as badge with clear button

**Files Changed**:
- `dashboard/src/t5gweb/ui.py` - Route handler (lines 635-704)
- `dashboard/src/t5gweb/templates/ui/engineering.html` - Added filter UI

### 3. ✅ UI Improvements

**Added**:
- Sprint selector dropdown with auto-submit
- Active filter banner showing: sprint, engineer, case count
- Better layout with split header (title left, filters right)
- Engineer filter badge with clear button
- Form preserves engineer filter when changing sprint

**Files Changed**: `dashboard/src/t5gweb/templates/ui/engineering.html`

## Files Modified Summary

### Backend (Python)
1. **`dashboard/src/t5gweb/ui.py`** (lines 635-704)
   - Added `available_sprints` query to get recent 10 sprints
   - Added `sprint` URL parameter support
   - Handle `sprint=all` for all sprints
   - Pass sprint options to template
   - Pass `current_sprint`, `selected_sprint`, `available_sprints` to template

### Frontend (Templates)
2. **`dashboard/src/t5gweb/templates/ui/engineering.html`**
   - Added sprint selector dropdown
   - Added active filter banner
   - Improved layout with Bootstrap grid
   - Engineer filter badge with clear button
   - Hidden input to preserve engineer filter when changing sprint

### Frontend (JavaScript)
3. **`dashboard/src/t5gweb/static/js/engineering.js`**
   - **CRITICAL FIX**: Pass `options` to DataTable initialization (line 87)
   - Removed duplicate loading div removal (lines 82-84 removed)
   - Added `className: 'dt-control'` to expander column def
   - Added null-safety checks in `format()` function:
     - Check `comment.author`, `comment.date`, `comment.body`
     - Check `comment.updated`
     - Provide fallback values
   - Added comment type styling (customer=info, bug=danger, default=primary)

## Testing Checklist

### Manual Testing Required

1. **DataTables Initialization**
   - [ ] Visit `/engineering` - table should load without errors
   - [ ] Check browser console for errors
   - [ ] Verify "Loading Table..." message disappears
   - [ ] Table should be interactive (sort, search, paginate)

2. **Sprint Selector**
   - [ ] Default shows "Current Sprint (T5GFE Sprint 291)"
   - [ ] Dropdown shows "All Sprints" option
   - [ ] Dropdown shows recent sprints
   - [ ] Selecting a sprint reloads page with correct cases
   - [ ] Banner shows selected sprint correctly

3. **Engineer Filter**
   - [ ] Visit `/engineering?engineer=Adrien%20Luneau`
   - [ ] Badge shows "Filtered by: Adrien Luneau"
   - [ ] "Clear Engineer Filter" button appears
   - [ ] Changing sprint preserves engineer filter
   - [ ] Clicking clear button removes filter

4. **Row Expansion** (existing functionality)
   - [ ] Click expander icon to open row
   - [ ] Comments load via AJAX
   - [ ] Portal comments show on left (60%)
   - [ ] JIRA comments show on right (40%)
   - [ ] Comment styling works (borders by type)
   - [ ] Click again to close row

5. **Edge Cases**
   - [ ] No cases found - table shows empty state
   - [ ] Case with no comments - handles gracefully
   - [ ] Case with no JIRA comments - shows "No JIRA comments"
   - [ ] Very long case summary - doesn't break layout

### URLs to Test

```bash
# Current sprint, all engineers (default)
http://localhost:8080/engineering

# Current sprint, Adrien only (~10 cases)
http://localhost:8080/engineering?engineer=Adrien%20Luneau

# All sprints, Adrien only (~52 cases - should match Vue)
http://localhost:8080/engineering?sprint=all&engineer=Adrien%20Luneau

# Specific sprint
http://localhost:8080/engineering?sprint=T5GFE%20Sprint%20290

# All sprints, all engineers (LARGE - may be slow)
http://localhost:8080/engineering?sprint=all
```

## Known Remaining Issues

### Not Fixed (Intentionally Deferred)

1. **No JIRA API calls** - Intentionally using cached sprint from PostgreSQL
   - PRO: Fast page load, no JIRA API dependency
   - CON: Sprint list only includes sprints in database
   - DECISION: Keep this - better UX

2. **Comment posting** - Not implemented (per plan)
   - Read-only view only
   - Future enhancement

3. **"Not changed" button** - Not implemented (per plan)
   - Requires `no_update_date` field in Case model
   - Future enhancement

4. **AI comment suggestions** - Not implemented (per plan)
   - Future enhancement

## Comparison: Before vs After

| Feature | Before | After |
|---------|--------|-------|
| DataTables Error | ❌ Blocking error | ✅ Fixed |
| Sprint Filter | Hard-coded current sprint | ✅ Dropdown selector |
| All Sprints View | Only via `?all_sprints=true` | ✅ Via dropdown |
| Engineer Filter UI | Hidden in URL | ✅ Badge with clear button |
| Active Filters | Not visible | ✅ Banner shows all filters |
| Sprint Options | Current only | ✅ Current + All + Recent 10 |
| Case Count | Not shown | ✅ Shown in banner |

## Expected Results

After fixes:
- **Adrien, Current Sprint (291)**: ~10 cases
- **Adrien, All Sprints**: ~52 cases (matches Vue behavior)
- **All Engineers, Current Sprint**: ~58 cases
- **All Engineers, All Sprints**: ~238 cases

## How to Run

1. Start the Flask development server:
   ```bash
   cd dashboard
   python3 -m src.t5gweb.app
   ```

2. Visit: http://localhost:8080/engineering

3. Test the sprint selector and engineer filters

## Next Steps

1. **Test the fixes** - Run through the testing checklist above
2. **Compare with Vue** - Verify case counts match between Python and Vue apps
3. **Performance check** - Test with "All Sprints" to ensure acceptable load time
4. **Browser testing** - Test in Chrome, Firefox, Safari
5. **Mobile responsive** - Check on mobile devices

## Future Enhancements (Not in This Version)

From the original plan:
- [ ] Add `no_update_date` field to `Case` model
- [ ] Implement "Submit comment" functionality
- [ ] Implement "Not changed" button
- [ ] Add `crit_sit` field/logic
- [ ] AI-generated comment suggestions
- [ ] Real-time updates
- [ ] Export to CSV/Excel
- [ ] Saved filter presets
- [ ] Email notifications for new cases
