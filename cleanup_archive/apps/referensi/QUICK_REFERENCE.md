# ⚡ Quick Reference Card - AHSP Database Management

## 🎯 For Developers

### File Locations
```
Templates:  referensi/templates/referensi/ahsp_database.html
JavaScript: referensi/static/referensi/js/ahsp_database_v2.js
CSS:        referensi/static/referensi/css/ahsp_database.css
Python API: referensi/views/api/bulk_ops.py
Service:    referensi/services/admin_service.py
```

### Key IDs & Selectors
```javascript
// Tables
'#tableJobs'                    // Jobs table
'#tableItems'                   // Items table

// Row Limit
'#rowLimitJobs'                 // Jobs row limit dropdown
'#rowLimitItems'                // Items row limit dropdown

// Column Toggle
'#btnColumnToggleJobs'          // Jobs column button
'#btnColumnToggleItems'         // Items column button
'#modalColumnToggle'            // Column toggle modal
'#columnToggleList'             // Column checkbox list
'#btnResetColumns'              // Reset columns button

// Search & Autocomplete
'#quickSearchJobs'              // Jobs search input
'#quickSearchItems'             // Items search input
'#autocompleteJobsDropdown'     // Jobs autocomplete
'#autocompleteItemsDropdown'    // Items autocomplete
'#btnSearchJobs'                // Jobs search button
'#btnSearchItems'               // Items search button

// Bulk Delete
'#btnBulkDelete'                // Open bulk delete modal
'#modalBulkDelete'              // Bulk delete modal
'#btnPreviewDelete'             // Preview delete
'#btnConfirmDelete'             // Execute delete

// CSS Classes
'.ahsp-database-table'          // Table styling
'.column-resizer'               // Resize handle
'.column-hidden'                // Hidden column
'.row-highlighted'              // Highlighted row
'.is-modified'                  // Modified field
'.autocomplete-dropdown'        // Autocomplete UI
'.autocomplete-item'            // Autocomplete suggestion
```

### JavaScript Modules
```javascript
// In ahsp_database_v2.js
autocompleteModule              // Lines 55-359
bulkDeleteModule                // Lines 365-551
tableSortModule                 // Lines 557-638
changeTrackingModule            // Lines 644-735
rowLimitModule                  // Lines 741-783
columnVisibilityModule          // Lines 789-953
resizableColumnsModule          // Lines 959-1084

// Initialization (line 1090)
document.addEventListener('DOMContentLoaded', function() {
    autocompleteModule.init();
    bulkDeleteModule.init();
    tableSortModule.init();
    changeTrackingModule.init();
    rowLimitModule.init();
    columnVisibilityModule.init();
    resizableColumnsModule.init();
});
```

### LocalStorage Keys
```javascript
// Format: {tableId}_{feature}
'tableJobs_rowLimit'            // "20"|"50"|"100"|"200"
'tableJobs_hiddenColumns'       // JSON: [2, 5, 7]
'tableJobs_columnWidths'        // JSON: ["120px", "250px", ...]

'tableItems_rowLimit'
'tableItems_hiddenColumns'
'tableItems_columnWidths'
```

### API Endpoints
```python
# In referensi/urls.py
path('api/delete/preview', api_delete_preview, name='api_delete_preview')
path('api/delete/execute', api_bulk_delete, name='api_bulk_delete')
path('api/search', api_search_ahsp, name='api_search_ahsp')

# Usage in JavaScript
config.deletePreviewUrl         // From window.AHSP_DB_CONFIG
config.deleteExecuteUrl
config.searchUrl
```

---

## 🎯 For Users

### Keyboard Shortcuts
```
Search Autocomplete:
  ↓ / ↑       Navigate suggestions
  Enter       Select suggestion or search
  Esc         Close dropdown

Table:
  Click       Sort by column
  Drag        Resize column width
  Scroll      Navigate table
```

### Quick Actions
```
Change rows displayed:    Top-left dropdown (20/50/100/200)
Hide/show columns:        "Kolom" button → check/uncheck
Resize column:            Drag column border
Search data:              Type in search box, click Search
Jump to row:              Click autocomplete suggestion
Delete bulk:              "Hapus Data" button → preview → confirm
Save changes:             "Simpan" button → confirm
```

### Visual Indicators
```
Yellow border          = Field modified
Yellow button          = Unsaved changes
Blue arrow ↑/↓        = Sorted column
Blue line on border    = Resizable column
Yellow row highlight   = Jump-to target
Toast notification     = Action result
```

---

## 🎯 For Admins

### Permissions Required
```python
# View database
'referensi.view_ahspreferensi'

# Edit records
'referensi.change_ahspreferensi'

# Bulk delete
'referensi.delete_ahspreferensi'
```

### Common Tasks

#### Task 1: Bulk Delete Old Data
```
1. Click "Hapus Data" (red button)
2. Select "Sumber" or enter "File Sumber"
3. Click "Preview"
4. Review counts and affected data
5. Click "Hapus Data"
6. Confirm in browser dialog
7. Wait for success message
8. Page reloads automatically
```

#### Task 2: Customize Table View
```
1. Click "Kolom" button
2. Uncheck unnecessary columns
3. Click "Terapkan" or outside modal
4. Drag column borders to resize
5. Change row limit dropdown
6. Settings saved automatically
```

#### Task 3: Find and Edit Specific Data
```
1. Type search term (min 2 chars)
2. Wait for autocomplete suggestions
3. Click matching suggestion
4. Table jumps to that row (highlighted)
5. Edit the field
6. Save button turns yellow
7. Click "Simpan"
8. Confirm changes
9. Data saved to database
```

---

## 🐛 Debug Checklist

### Issue: JavaScript not working
```bash
# Check file loaded
View → Developer Tools → Network tab → Check ahsp_database_v2.js (200 OK)

# Check console errors
View → Developer Tools → Console tab → Look for red errors

# Check DOM ready
Console: document.readyState  # Should be "complete"

# Force reload
Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
```

### Issue: Settings not saving
```javascript
// Check localStorage available
console.log(localStorage);  // Should not be null

// Check quota
console.log(JSON.stringify(localStorage).length + " chars used");

// Check incognito mode
// localStorage may be disabled in private browsing

// Clear old data
localStorage.clear();  // Caution: removes all settings
```

### Issue: Table performance slow
```javascript
// Check row count
console.log(document.querySelectorAll('#tableJobs tbody tr').length);

// Reduce row limit
// Use dropdown to select 20 or 50 instead of 200

// Hide unused columns
// Use "Kolom" button to hide columns you don't need
```

---

## 📊 Performance Tips

### For Large Datasets (5000+ rows)
```
✅ Use row limit 50 or 100 (not 200)
✅ Hide columns you don't need
✅ Use search to filter data
✅ Sort by relevant columns
✅ Close autocomplete when not needed
```

### For Slow Connections
```
✅ Minimize reloads (use save sparingly)
✅ Let autocomplete debounce (wait 300ms)
✅ Use quick search instead of full reload
✅ Resize columns once, then save
```

### For Browser Memory
```
✅ Close other tabs
✅ Clear browser cache periodically
✅ Don't keep page open for hours
✅ Reload page if feels slow
```

---

## 🔧 Common Customizations

### Change Row Limit Options
```javascript
// In ahsp_database.html, find:
<select id="rowLimitJobs">
  <option value="20">20</option>
  <option value="50" selected>50</option>
  <option value="100">100</option>
  <option value="200">200</option>
  <!-- Add more: -->
  <option value="500">500</option>
  <option value="1000">1000</option>
</select>
```

### Change Autocomplete Limit
```javascript
// In ahsp_database_v2.js line ~201:
buildSuggestions(query, tableId) {
    // ...
    return suggestions.slice(0, 10);  // Change 10 to your limit
}
```

### Change Debounce Delay
```javascript
// In ahsp_database_v2.js line ~84:
input.addEventListener('input', debounce((e) => {
    this.handleInput(e.target, dropdown, tableId);
}, 300));  // Change 300ms to your preference
```

### Change Minimum Column Width
```javascript
// In ahsp_database_v2.js line ~1031:
if (newWidth >= 60) {  // Change 60px to your preference
    this.currentColumn.style.width = newWidth + 'px';
}
```

---

## 🎨 CSS Customization

### Change Row Spacing
```css
/* In ahsp_database.css */
.ahsp-database-table td,
.ahsp-database-table th {
    padding: 0.375rem 0.5rem !important;  /* Adjust these values */
}
```

### Change Highlight Color
```css
/* Row highlight on jump */
.row-highlighted {
    background-color: #fff3cd !important;  /* Change color */
    animation: highlightPulse 0.6s ease-in-out;
}
```

### Change Resizer Color
```css
.column-resizer:hover,
.column-resizer.resizing {
    background-color: #0d6efd;  /* Change blue to your color */
}
```

---

## 📚 Related Documentation

```
AHSP_DATABASE_FEATURES.md      - Phase 1-3 features
AUTOCOMPLETE_FEATURE.md        - Detailed autocomplete docs
TABLE_ENHANCEMENTS.md          - Phase 4 features (NEW)
IMPLEMENTATION_SUMMARY_V2.md   - Complete overview
VISUAL_GUIDE.md                - UI components guide
REFACTORING_SUMMARY.md         - UI changes history
BUGFIX_CHANGELOG.md            - Bug fix log
```

---

## 🚨 Emergency Rollback

### If something breaks:
```bash
# 1. Check git status
git status

# 2. See recent changes
git log --oneline -5

# 3. Revert to previous commit
git revert HEAD

# 4. Or hard reset (CAUTION: loses changes)
git reset --hard HEAD~1

# 5. Collect static files
python manage.py collectstatic --noinput

# 6. Restart server
# (Varies by hosting platform)

# 7. Clear browser cache
# Ctrl+Shift+Delete → Clear cache
```

---

## 💡 Tips & Tricks

### For Developers
```
✅ Use browser DevTools to inspect localStorage
✅ Console.log() is your friend for debugging
✅ Test with different row counts (10, 100, 5000)
✅ Test on different browsers (Chrome, Firefox, Safari, Edge)
✅ Use git branches for experimental features
```

### For Users
```
✅ Double-click column border to auto-fit (coming soon)
✅ Bookmark your view settings (saved automatically)
✅ Use Ctrl+F for browser search within visible rows
✅ Export data before bulk delete (coming soon)
✅ Report bugs with browser console screenshot
```

---

## 📞 Support Resources

### Self-Help
```
1. Check this Quick Reference
2. Read TABLE_ENHANCEMENTS.md for feature details
3. Check browser console for error messages
4. Clear browser cache and try again
5. Try in incognito/private mode
```

### Getting Help
```
1. Screenshot the issue
2. Open browser console (F12)
3. Copy any error messages
4. Note steps to reproduce
5. Check Django logs for backend errors
```

### Common Error Messages
```
"Failed to fetch"
  → Check network connection, verify API endpoints

"localStorage is not defined"
  → Browser privacy settings blocking storage

"Cannot read property of undefined"
  → Table element not found, check HTML IDs

"CSRF verification failed"
  → Refresh page, check cookies enabled
```

---

## ✅ Pre-Deployment Checklist

```
[ ] All JavaScript modules initialized
[ ] All IDs present in HTML
[ ] CSS file loaded and applied
[ ] API endpoints responding (200 OK)
[ ] Permissions configured correctly
[ ] localStorage works (not disabled)
[ ] Tested on Chrome, Firefox, Edge
[ ] Tested with 50, 100, 5000 rows
[ ] Bulk delete tested with preview
[ ] Change tracking shows modifications
[ ] Column resize saves to storage
[ ] Column visibility persists
[ ] Row limit persists
[ ] Mobile responsive (basic)
[ ] No console errors
[ ] Django logs show no errors
```

---

## 🎯 Success Metrics

### After Implementation
```
User can:
✅ Control rows displayed (20-200)
✅ Hide/show any column
✅ Resize columns to preference
✅ Find data in < 2 seconds
✅ Edit data with clear feedback
✅ Delete bulk data safely
✅ Save settings across sessions
```

### Performance Targets
```
⚡ Autocomplete: < 50ms response
⚡ Row limit change: < 10ms
⚡ Column resize: Real-time (< 5ms)
⚡ Table sort: < 100ms for 5000 rows
⚡ Page load: < 2 seconds
```

---

**Quick Reference v2.0** ⚡

Last Updated: 2025-11-03
Status: Production Ready ✅
