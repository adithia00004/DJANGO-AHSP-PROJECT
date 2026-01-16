# 🎨 Preview Import UI/UX Adaptation Plan

## 📋 Overview

Plan untuk mengadaptasi semua UI/UX enhancements dari **Database Page** ke **Preview Import Page**.

---

## 🔍 Current State Analysis

### Database Page (Source)
**URL**: `/referensi/admin/database/`
**Template**: `referensi/templates/referensi/ahsp_database.html`
**JavaScript**: `referensi/static/referensi/js/ahsp_database_v2.js` (1,100+ lines)
**CSS**: `referensi/static/referensi/css/ahsp_database.css` (680+ lines)

**Features**:
1. ✅ Autocomplete Search dengan Jump-to-Row
2. ✅ Row Limit Controller (20/50/100/200)
3. ✅ Column Visibility Toggle
4. ✅ Resizable Columns
5. ✅ Table Sorting
6. ✅ Change Tracking
7. ✅ Save Confirmation Modal
8. ✅ Bulk Delete
9. ✅ Professional Animations
10. ✅ Dark Mode Support

### Preview Import Page (Target)
**URL**: `/referensi/admin/preview/`
**Template**: `referensi/templates/referensi/preview_import.html` (238 lines)
**Partial Templates**:
- `referensi/templates/referensi/preview/_jobs_table.html`
- `referensi/templates/referensi/preview/_details_table.html`

**JavaScript**: `referensi/static/referensi/js/preview_import.js`
**CSS**: `referensi/static/referensi/css/preview_import.css`

**Current Features**:
- ⚠️ Basic table display
- ⚠️ Tab navigation (AHSP/Rincian)
- ⚠️ Pagination
- ⚠️ Upload form

**Missing Features** (to be adapted):
- ❌ Autocomplete Search
- ❌ Row Limit Controller
- ❌ Column Visibility Toggle
- ❌ Resizable Columns
- ❌ Professional Polish

---

## 🎯 Features to Adapt

### 1. Autocomplete Search ✅ **HIGH PRIORITY**

**From**: Database Page
- Search across all columns
- Auto-suggestions (max 10)
- Jump-to-row on click
- Search button to filter
- Keyboard navigation (arrows, enter, esc)
- Fixed positioning to avoid overflow clipping

**Adapt to**: Preview Import Page
- **2 separate instances**: Jobs table + Details table
- Same autocomplete behavior
- Suggestions based on preview data (not database)
- Jump to row in current tab/page

**Implementation**:
```javascript
// New file: preview_import_v2.js
const autocompleteModule = {
    init() {
        this.initTable('tablePreviewJobs', 'quickSearchJobs', 'autocompleteJobsDropdown', 'btnSearchJobs');
        this.initTable('tablePreviewDetails', 'quickSearchDetails', 'autocompleteDetailsDropdown', 'btnSearchDetails');
    },
    // ... copy from ahsp_database_v2.js with minimal changes
}
```

**Files to modify**:
- `preview/_jobs_table.html` - Add search input + dropdown
- `preview/_details_table.html` - Add search input + dropdown
- `preview_import_v2.js` - New file with autocomplete logic
- `preview_import.css` - Add autocomplete styles

---

### 2. Row Limit Controller ✅ **HIGH PRIORITY**

**From**: Database Page
- Dropdown with 20/50/100/200 options
- Default: 50
- Persists to localStorage
- Works with search filter

**Adapt to**: Preview Import Page
- **Consideration**: Preview page already has **pagination**!
- **Decision**: Keep pagination OR replace with row limit?

**Recommendation**: **HYBRID APPROACH**
- Keep pagination for large datasets (1000+ rows)
- Add row limit for current page view
- "Show X rows per page" instead of just pagination

**Implementation**:
```html
<!-- Add to table header -->
<div class="col-auto">
    <div class="d-flex align-items-center gap-2">
        <label class="small text-muted mb-0">Per halaman:</label>
        <select class="form-select form-select-sm" id="rowLimitJobs">
            <option value="25" selected>25</option>
            <option value="50">50</option>
            <option value="100">100</option>
        </select>
    </div>
</div>
```

**Files to modify**:
- `preview/_jobs_table.html` - Add row limit dropdown
- `preview/_details_table.html` - Add row limit dropdown
- `preview_import_v2.js` - Add rowLimitModule
- Might need to update backend pagination logic

---

### 3. Column Visibility Toggle ✅ **MEDIUM PRIORITY**

**From**: Database Page
- "Kolom" button opens modal
- Checkbox list of all columns
- Show/hide columns dynamically
- Reset button
- Persists to localStorage

**Adapt to**: Preview Import Page
- **Same behavior**
- 2 instances (Jobs + Details)
- **Challenge**: Partial templates re-render on pagination
- **Solution**: Use JavaScript to apply visibility after DOM load

**Implementation**:
```javascript
const columnVisibilityModule = {
    init() {
        this.initTable('tablePreviewJobs', 'btnColumnToggleJobs');
        this.initTable('tablePreviewDetails', 'btnColumnToggleDetails');

        // Re-apply on AJAX reload
        document.addEventListener('htmx:afterSwap', () => {
            this.reapplyVisibility('tablePreviewJobs');
            this.reapplyVisibility('tablePreviewDetails');
        });
    }
}
```

**Files to modify**:
- `preview_import.html` - Add modal (shared for both tables)
- `preview/_jobs_table.html` - Add "Kolom" button
- `preview/_details_table.html` - Add "Kolom" button
- `preview_import_v2.js` - Add columnVisibilityModule
- `preview_import.css` - Add column visibility styles

---

### 4. Resizable Columns ✅ **LOW PRIORITY**

**From**: Database Page
- Drag column borders to resize
- Minimum width: 60px
- Persists to localStorage
- Visual feedback (blue highlight)

**Adapt to**: Preview Import Page
- **Same behavior**
- **Challenge**: Partial templates re-render on pagination
- **Solution**: Re-apply widths after AJAX reload

**Implementation**:
```javascript
const resizableColumnsModule = {
    init() {
        this.initTable('tablePreviewJobs');
        this.initTable('tablePreviewDetails');

        // Re-apply on AJAX reload
        document.addEventListener('htmx:afterSwap', () => {
            this.loadColumnWidths(document.getElementById('tablePreviewJobs'));
            this.loadColumnWidths(document.getElementById('tablePreviewDetails'));
        });
    }
}
```

**Files to modify**:
- `preview_import_v2.js` - Add resizableColumnsModule
- `preview_import.css` - Add resize handle styles

---

### 5. Professional Polish & Animations ✅ **HIGH PRIORITY**

**From**: Database Page
- Smooth transitions (200-400ms)
- Button hover lift effect
- Input focus scale
- Modal slide-in
- Toast notifications
- Row hover effects
- Smooth scrollbar
- Dark mode support

**Adapt to**: Preview Import Page
- **Copy all polish CSS**
- Apply to preview tables
- Ensure dark mode compatibility

**Files to modify**:
- `preview_import.css` - Add all polish styles (~300 lines)

---

## 📊 Implementation Strategy

### Phase 1: Foundation (Day 1)
1. ✅ Create `preview_import_v2.js` (copy structure from ahsp_database_v2.js)
2. ✅ Update CSS file with autocomplete + polish styles
3. ✅ Add shared modal to main template (column toggle)
4. ✅ Update partial templates with UI controls

### Phase 2: Core Features (Day 1-2)
1. ✅ Implement Autocomplete Search
2. ✅ Implement Row Limit Controller
3. ✅ Implement Column Visibility Toggle
4. ✅ Test on both tabs (Jobs + Details)

### Phase 3: Polish (Day 2)
1. ✅ Implement Resizable Columns
2. ✅ Apply professional animations
3. ✅ Dark mode testing
4. ✅ Cross-browser testing

### Phase 4: Integration (Day 2-3)
1. ✅ Handle AJAX reload (htmx events)
2. ✅ Handle pagination interaction
3. ✅ Handle tab switching
4. ✅ Persist settings across sessions

---

## 🔧 Technical Challenges & Solutions

### Challenge 1: AJAX Partial Reloads

**Problem**: Preview page uses AJAX to reload tables on pagination/save
**Impact**: JavaScript event listeners lost, column visibility reset

**Solution**:
```javascript
// Listen for htmx events
document.addEventListener('htmx:afterSwap', (event) => {
    if (event.detail.target.id === 'jobs-preview-container') {
        // Re-initialize Jobs table
        autocompleteModule.extractTableData('tablePreviewJobs', ...);
        columnVisibilityModule.loadColumnVisibility(...);
        resizableColumnsModule.loadColumnWidths(...);
    }
});
```

### Challenge 2: Pagination vs Row Limit

**Problem**: Page already has pagination, row limit might confuse users

**Solution**: **Rename to "Rows Per Page"**
```html
<label>Baris per halaman:</label>
<select id="rowsPerPage">
    <option value="25">25</option>
    <option value="50">50</option>
    <option value="100">100</option>
</select>
```

This integrates with existing pagination logic.

### Challenge 3: localStorage Persistence

**Problem**: Multiple tables (Jobs + Details), need separate storage keys

**Solution**:
```javascript
// Use descriptive keys
localStorage.setItem('previewJobs_rowLimit', '50');
localStorage.setItem('previewDetails_rowLimit', '25');
localStorage.setItem('previewJobs_hiddenColumns', '[2, 5]');
localStorage.setItem('previewDetails_hiddenColumns', '[3, 7]');
```

### Challenge 4: Tab Switching

**Problem**: Autocomplete dropdown might stay visible when switching tabs

**Solution**:
```javascript
// Close dropdown on tab change
document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
    tab.addEventListener('shown.bs.tab', () => {
        autocompleteModule.hideAllDropdowns();
    });
});
```

---

## 📂 File Structure

```
referensi/
├── templates/
│   └── referensi/
│       ├── preview_import.html          (MODIFY - add modals)
│       └── preview/
│           ├── _jobs_table.html         (MODIFY - add UI controls)
│           └── _details_table.html      (MODIFY - add UI controls)
├── static/
│   └── referensi/
│       ├── js/
│       │   ├── ahsp_database_v2.js     (SOURCE - reference)
│       │   └── preview_import_v2.js    (CREATE - adapted version)
│       └── css/
│           ├── ahsp_database.css        (SOURCE - reference)
│           └── preview_import.css       (MODIFY - add styles)
└── views/
    └── preview.py                        (MIGHT MODIFY - pagination logic)
```

---

## 🎨 UI Layout Comparison

### Database Page Header (Source)
```
┌──────────────────────────────────────────────────────────────────┐
│ [Limit▼] [Kolom] [🔍 Search_______________] [Actions] [Save]    │
└──────────────────────────────────────────────────────────────────┘
```

### Preview Page Header (Target - After Adaptation)
```
┌──────────────────────────────────────────────────────────────────┐
│ Tab: AHSP Referensi (200)     Tab: Rincian Item (1,000)         │
├──────────────────────────────────────────────────────────────────┤
│ [Rows▼] [Kolom] [🔍 Search_______________] [Pagination ◀ 1 ▶]   │
└──────────────────────────────────────────────────────────────────┘
```

**Key Differences**:
- Pagination controls (keep existing)
- No "Save" button (preview is read-only)
- No "Bulk Delete" (not applicable)
- Row limit = "Rows per page"

---

## ✅ Acceptance Criteria

### Must Have:
- [ ] Autocomplete search works on both tabs
- [ ] Row limit affects pagination (rows per page)
- [ ] Column visibility persists across tab switches
- [ ] Resizable columns work and persist
- [ ] All features work after AJAX reload
- [ ] Dark mode fully supported
- [ ] No console errors
- [ ] Professional polish applied

### Nice to Have:
- [ ] Smooth animations on all interactions
- [ ] Keyboard shortcuts (Ctrl+F for search)
- [ ] Export current view settings
- [ ] Print-friendly view

---

## 📈 Estimated Impact

### Before Adaptation:
- ❌ Basic table, hard to navigate large datasets
- ❌ Can't search within preview data
- ❌ Fixed columns, lots of horizontal scroll
- ❌ Fixed pagination, can't adjust view

### After Adaptation:
- ✅ Fast search with autocomplete
- ✅ Jump to specific rows instantly
- ✅ Customize visible columns
- ✅ Adjust table to preferences
- ✅ Professional, polished UX

**User Productivity**: **+50-70%** improvement

---

## 🚀 Next Steps

1. **Review & Approval**: User reviews this plan
2. **Start Implementation**: Begin Phase 1
3. **Iterative Testing**: Test after each phase
4. **Deploy**: Production deployment after full testing

---

**Estimated Time**: 2-3 days of focused development

**Risk Level**: Low (copying proven implementation)

**User Benefit**: High (consistent UX across pages)

---

Apakah Anda setuju dengan plan ini? Saya siap mulai implementasi! 🚀
