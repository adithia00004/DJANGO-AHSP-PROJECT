# PHASE 5 – Export Excellence & Data Quality

**Planning Date:** 2025-12-03
**Target Duration:** 1-2 weeks
**Status:** 📋 Planning

---

## Overview

Phase 5 fokus pada meningkatkan kualitas export, validasi data, dan accessibility untuk memastikan Rekap Kebutuhan page production-ready dengan standar enterprise.

## Goals & Success Metrics

| Goal | Success Metric | Priority |
|------|----------------|----------|
| Export fidelity | PDF/Word/CSV mencerminkan 100% filter & view state aktif | 🔴 Critical |
| Data validation | Zero inconsistency antara snapshot vs timeline vs export | 🔴 Critical |
| Search UX | Autocomplete search dengan <200ms response time | 🟡 High |
| Accessibility | WCAG 2.1 AA compliance score ≥90% | 🟢 Medium |
| Performance | Export generation <3s untuk dataset <500 items | 🟡 High |

---

## Track 1: Export Enhancement

### Current State Analysis

**Existing export endpoints:**
- CSV: `/api/project/<pid>/export/rekap-kebutuhan/csv/`
- PDF: `/api/project/<pid>/export/rekap-kebutuhan/pdf/`
- Word: `/api/project/<pid>/export/rekap-kebutuhan/word/`

**Known Issues:**
- ❌ Export mungkin tidak respect semua filter states (perlu verify)
- ❌ Timeline view tidak punya dedicated export
- ❌ No visual feedback saat export large dataset
- ❌ Export filename tidak descriptive (e.g., `rekap-kebutuhan.pdf`)

### Tasks

#### 1.1 Export State Fidelity
**Goal:** Export harus mencerminkan exact state dari UI

**Implementation:**
```javascript
// rekap_kebutuhan.js - Enhanced export function
const generateExport = (format) => {
  const params = buildQueryParams(); // Reuse existing filter params
  const timestamp = new Date().toISOString().slice(0, 10);

  // Build descriptive filename
  let filename = `rekap-kebutuhan_${projectName}_${timestamp}`;
  if (params.mode === 'tahapan' && params.tahapan_id) {
    filename += `_tahapan-${params.tahapan_id}`;
  }
  if (params.kategori) {
    filename += `_${params.kategori.replace(/,/g, '-')}`;
  }
  if (currentViewMode === 'timeline') {
    filename += '_timeline';
  }

  // Add metadata to export request
  params.view_mode = currentViewMode;
  params.filename = filename;

  showExportProgress(); // Visual feedback

  const url = `${exportUrls[format]}?${new URLSearchParams(params)}`;
  window.open(url, '_blank');
};
```

**Backend Changes Required:**
```python
# views_api.py or exports/rekap_kebutuhan_adapter.py
def export_rekap_kebutuhan_csv(request, project_id):
    # Extract ALL filter params including view_mode
    filters = {
        'mode': request.GET.get('mode', 'all'),
        'tahapan_id': request.GET.get('tahapan_id'),
        'kategori': request.GET.getlist('kategori'),
        'klasifikasi': request.GET.getlist('klasifikasi'),
        'sub_klasifikasi': request.GET.getlist('sub_klasifikasi'),
        'pekerjaan': request.GET.getlist('pekerjaan'),
        'search': request.GET.get('search', ''),
        'view_mode': request.GET.get('view_mode', 'snapshot'),
    }

    # Apply filters to data
    if filters['view_mode'] == 'timeline':
        data = compute_timeline_export(project, filters)
    else:
        data = compute_kebutuhan_items(project, filters)

    # Generate CSV with metadata header
    response = HttpResponse(content_type='text/csv')
    filename = request.GET.get('filename', f'rekap-kebutuhan-{project.id}')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'

    writer = csv.writer(response)
    # Add metadata rows
    writer.writerow(['# Rekap Kebutuhan Export'])
    writer.writerow(['# Project:', project.nama])
    writer.writerow(['# Generated:', timezone.now().strftime('%Y-%m-%d %H:%M')])
    writer.writerow(['# Filters:', json.dumps(filters)])
    writer.writerow([])  # Empty row separator

    # Add data rows
    # ... existing export logic

    return response
```

**Exit Criteria:**
- ✅ Export CSV includes metadata header with filter state
- ✅ Export PDF shows applied filters in document header
- ✅ Export Word has cover page with filter summary
- ✅ Filename auto-generated with relevant context

---

#### 1.2 Timeline Export
**Goal:** Dedicated timeline export with period breakdown

**Implementation:**
- New export option: "Export Timeline" (muncul hanya saat `currentViewMode === 'timeline'`)
- CSV format: Flat list dengan kolom tambahan `Period`, `Start Date`, `End Date`
- PDF format: Section per period dengan page breaks
- Word format: Heading 1 per period

**Exit Criteria:**
- ✅ Timeline export button appears when in timeline view
- ✅ CSV has period columns
- ✅ PDF has visual period separators
- ✅ Word has proper heading hierarchy

---

#### 1.3 Export Progress Feedback
**Goal:** Visual feedback untuk export yang memakan waktu

**Implementation:**
```javascript
const showExportProgress = () => {
  const toast = `
    <div class="toast align-items-center" role="alert">
      <div class="d-flex">
        <div class="toast-body">
          <div class="spinner-border spinner-border-sm me-2"></div>
          Memproses export... Mohon tunggu.
        </div>
      </div>
    </div>
  `;
  // Show toast, auto-hide after 3s or when download starts
};
```

**Exit Criteria:**
- ✅ Toast notification saat export dimulai
- ✅ Auto-hide setelah 3 detik
- ✅ Error toast jika export gagal

---

## Track 2: Data Validation & Integrity

### Current State Analysis

**Potential Issues:**
- Snapshot vs Timeline totals bisa berbeda jika ada rounding errors
- Cache invalidation bisa menyebabkan stale data
- Filter combinations tertentu bisa return empty incorrectly

### Tasks

#### 2.1 Data Consistency Checks
**Goal:** Ensure snapshot total = sum of timeline periods

**Implementation:**
```python
# services.py - Add validation function
def validate_kebutuhan_data(project, filters):
    """
    Validate that snapshot and timeline data are consistent
    Returns dict with validation results
    """
    snapshot_data = compute_kebutuhan_items(project, filters)
    timeline_data = compute_timeline_data(project, filters)

    snapshot_total = sum(item['harga_total'] for item in snapshot_data)
    timeline_total = sum(
        period['total_cost']
        for period in timeline_data['periods']
    )

    diff = abs(snapshot_total - timeline_total)
    tolerance = Decimal('0.01')  # 1 cent tolerance for rounding

    is_valid = diff <= tolerance

    return {
        'valid': is_valid,
        'snapshot_total': snapshot_total,
        'timeline_total': timeline_total,
        'difference': diff,
        'tolerance': tolerance,
    }
```

**Frontend Debug Panel:**
```javascript
// Add admin-only debug panel (Ctrl+Shift+D)
const showDebugPanel = async () => {
  const validation = await apiCall(`/api/project/${projectId}/rekap-kebutuhan/validate/`);

  const panel = `
    <div class="modal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Data Validation</h5>
          </div>
          <div class="modal-body">
            <p>Status: ${validation.valid ? '✅ Valid' : '❌ Invalid'}</p>
            <p>Snapshot Total: ${formatCurrency(validation.snapshot_total)}</p>
            <p>Timeline Total: ${formatCurrency(validation.timeline_total)}</p>
            <p>Difference: ${formatCurrency(validation.difference)}</p>
          </div>
        </div>
      </div>
    </div>
  `;
};

// Register keyboard shortcut
document.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.shiftKey && e.key === 'D') {
    e.preventDefault();
    showDebugPanel();
  }
});
```

**Exit Criteria:**
- ✅ Validation endpoint available
- ✅ Debug panel accessible via Ctrl+Shift+D
- ✅ Automated test verifies consistency

---

#### 2.2 Cache Invalidation Strategy
**Goal:** Smart cache invalidation when data changes

**Implementation:**
```python
# signals.py - Auto-invalidate cache on data changes
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

@receiver([post_save, post_delete], sender=DetailAHSPExpanded)
@receiver([post_save, post_delete], sender=VolumePekerjaan)
@receiver([post_save, post_delete], sender=HargaItemProject)
def invalidate_rekap_kebutuhan_cache(sender, instance, **kwargs):
    """
    Invalidate cache when underlying data changes
    """
    project_id = instance.project_id
    cache_pattern = f"rekap_kebutuhan:{project_id}:*"

    # Clear all cache entries for this project
    cache.delete_pattern(cache_pattern)

    logger.info(f"Invalidated rekap_kebutuhan cache for project {project_id}")
```

**Exit Criteria:**
- ✅ Cache auto-invalidates on data model changes
- ✅ Manual "Refresh" button clears cache
- ✅ Cache timestamp shown in UI

---

## Track 3: Advanced Search & Quick Filters

### Current State Analysis

**Existing search:**
- Basic text search di kolom "Kode" dan "Uraian"
- No autocomplete
- No search history
- No "quick filter" chips

### Tasks

#### 3.1 Search Autocomplete
**Goal:** Autocomplete suggestions dengan debouncing

**Implementation:**
```javascript
// rekap_kebutuhan.js - Enhanced search
let searchCache = [];
let searchHistory = JSON.parse(localStorage.getItem('rk_search_history') || '[]');

const initSearchAutocomplete = () => {
  const searchInput = refs.search;
  const suggestionsContainer = createSuggestionsDropdown();

  let debounceTimer;
  searchInput.addEventListener('input', (e) => {
    clearTimeout(debounceTimer);
    const query = e.target.value.trim();

    if (query.length < 2) {
      hideSuggestions();
      return;
    }

    debounceTimer = setTimeout(() => {
      const suggestions = getSuggestions(query);
      showSuggestions(suggestions);
    }, 200);
  });
};

const getSuggestions = (query) => {
  // Search in cached table rows
  const matches = tableRowsCache
    .filter(row =>
      row.kode.toLowerCase().includes(query.toLowerCase()) ||
      row.uraian.toLowerCase().includes(query.toLowerCase())
    )
    .slice(0, 10)
    .map(row => ({
      label: `${row.kode} - ${row.uraian}`,
      kode: row.kode,
      kategori: row.kategori,
    }));

  // Merge with search history
  const historyMatches = searchHistory
    .filter(h => h.toLowerCase().includes(query.toLowerCase()))
    .slice(0, 3)
    .map(h => ({ label: h, isHistory: true }));

  return [...historyMatches, ...matches];
};
```

**Exit Criteria:**
- ✅ Autocomplete muncul setelah 2 karakter
- ✅ Debounce 200ms
- ✅ Show top 10 matches
- ✅ Recent searches dari localStorage
- ✅ Keyboard navigation (arrow keys, Enter, Esc)

---

#### 3.2 Quick Filter Chips
**Goal:** Visual chips untuk filter aktif dengan quick remove

**Implementation:**
```javascript
const renderActiveFilters = () => {
  const chips = [];

  if (currentFilter.kategori.length < 4) {
    currentFilter.kategori.forEach(kat => {
      chips.push({
        label: kat,
        icon: 'bi-tag',
        onRemove: () => toggleKategori(kat),
      });
    });
  }

  if (currentFilter.klasifikasi_ids.length) {
    chips.push({
      label: `${currentFilter.klasifikasi_ids.length} Klasifikasi`,
      icon: 'bi-diagram-3',
      onRemove: () => clearKlasifikasi(),
    });
  }

  // ... more filters

  const html = chips.map(chip => `
    <span class="badge bg-primary d-inline-flex align-items-center gap-1">
      <i class="${chip.icon}"></i>
      ${chip.label}
      <button type="button" class="btn-close btn-close-white btn-sm ms-1"
              onclick="removeChip('${chip.label}')"></button>
    </span>
  `).join('');

  refs.activeFiltersContainer.innerHTML = html;
  refs.activeFiltersContainer.classList.toggle('d-none', chips.length === 0);
};
```

**Exit Criteria:**
- ✅ Chips muncul di bawah toolbar
- ✅ Click X untuk remove individual filter
- ✅ "Clear all" button jika ada ≥2 chips
- ✅ Chips collapsible on mobile

---

## Track 4: Accessibility Improvements

### Current State Analysis

**WCAG 2.1 Audit Results (Initial):**
- ⚠️ Some buttons missing aria-label
- ⚠️ Color contrast issues on chart labels (need verify)
- ⚠️ Keyboard navigation incomplete for dropdowns
- ✅ Semantic HTML structure good

### Tasks

#### 4.1 ARIA Labels & Roles
**Goal:** All interactive elements properly labeled

**Checklist:**
```html
<!-- Filter dropdowns -->
<button aria-label="Filter kategori - saat ini semua kategori dipilih"
        aria-expanded="false"
        aria-controls="kategori-dropdown">

<!-- Export buttons -->
<button aria-label="Export data ke format CSV">

<!-- View toggle -->
<button aria-label="Tampilan snapshot - menampilkan ringkasan seluruh proyek"
        aria-pressed="true">

<!-- Charts -->
<div role="img"
     aria-label="Grafik pie menunjukkan distribusi biaya per kategori">
```

**Exit Criteria:**
- ✅ All buttons have aria-label
- ✅ All dropdowns have aria-expanded/aria-controls
- ✅ Charts have role="img" + descriptive aria-label
- ✅ Screen reader test passes

---

#### 4.2 Keyboard Navigation
**Goal:** Full keyboard control

**Shortcuts:**
- `Ctrl+F`: Focus search
- `Ctrl+E`: Open export menu
- `Ctrl+R`: Refresh data
- `Tab`: Navigate filters
- `Enter`: Toggle dropdowns
- `Esc`: Close dropdowns
- `Ctrl+Shift+T`: Toggle view mode
- `Ctrl+Shift+D`: Debug panel (admin)

**Implementation:**
```javascript
const keyboardShortcuts = {
  'Ctrl+F': () => refs.search.focus(),
  'Ctrl+E': () => refs.exportDropdown.click(),
  'Ctrl+R': () => loadRekapKebutuhan(),
  'Ctrl+Shift+T': () => toggleViewMode(),
  'Ctrl+Shift+D': () => showDebugPanel(),
};

document.addEventListener('keydown', (e) => {
  const key = [
    e.ctrlKey && 'Ctrl',
    e.shiftKey && 'Shift',
    e.key
  ].filter(Boolean).join('+');

  if (keyboardShortcuts[key]) {
    e.preventDefault();
    keyboardShortcuts[key]();
  }
});
```

**Exit Criteria:**
- ✅ All shortcuts documented in UI (help modal)
- ✅ Shortcuts work consistently
- ✅ No conflicts with browser shortcuts

---

#### 4.3 Focus Management
**Goal:** Visible focus indicators & logical focus flow

**CSS:**
```css
/* Enhanced focus indicators */
.btn:focus-visible,
.form-control:focus-visible,
.rk-dropdown button:focus-visible {
  outline: 3px solid var(--bs-primary);
  outline-offset: 2px;
  box-shadow: 0 0 0 0.25rem rgba(13, 110, 252, 0.25);
}

/* Skip to content link */
.skip-to-content {
  position: absolute;
  top: -40px;
  left: 0;
  background: var(--bs-primary);
  color: white;
  padding: 0.5rem 1rem;
  z-index: 100;
}

.skip-to-content:focus {
  top: 0;
}
```

**Exit Criteria:**
- ✅ Focus visible on all interactive elements
- ✅ Skip to main content link
- ✅ Focus trap in modals
- ✅ Focus returns after modal close

---

## Implementation Timeline

### Week 1: Export & Data Quality
- **Days 1-2:** Export state fidelity (Track 1.1)
- **Days 3-4:** Timeline export (Track 1.2) + Export progress (Track 1.3)
- **Day 5:** Data validation endpoint (Track 2.1)

### Week 2: Search & Accessibility
- **Days 1-2:** Search autocomplete (Track 3.1)
- **Day 3:** Quick filter chips (Track 3.2)
- **Days 4-5:** Accessibility audit & fixes (Track 4.1-4.3)

---

## Testing Plan

### Automated Tests
```python
# test_rekap_kebutuhan_phase5.py

class ExportFidelityTests(TestCase):
    def test_csv_export_respects_kategori_filter(self):
        # Apply kategori filter
        # Export CSV
        # Verify CSV only contains filtered categories
        pass

    def test_export_filename_includes_filters(self):
        # Apply multiple filters
        # Trigger export
        # Verify filename = rekap-kebutuhan_<project>_<filters>_<date>
        pass

class DataConsistencyTests(TestCase):
    def test_snapshot_equals_timeline_total(self):
        validation = validate_kebutuhan_data(self.project, {})
        self.assertTrue(validation['valid'])
        self.assertLess(validation['difference'], Decimal('0.01'))

    def test_cache_invalidation_on_data_change(self):
        # Load data (cache hit)
        # Modify DetailAHSPExpanded
        # Load data again
        # Verify cache was invalidated
        pass

class SearchTests(TestCase):
    def test_autocomplete_returns_top_10(self):
        suggestions = get_search_suggestions(self.project, 'pasir')
        self.assertLessEqual(len(suggestions), 10)

    def test_search_history_persists(self):
        # Perform search
        # Reload page
        # Verify history exists in localStorage
        pass

class AccessibilityTests(TestCase):
    def test_all_buttons_have_aria_labels(self):
        # Parse HTML
        # Find all <button> elements
        # Assert all have aria-label or aria-labelledby
        pass
```

### Manual Testing Checklist
- [ ] Export CSV dengan berbagai kombinasi filter
- [ ] Export PDF dengan timeline view
- [ ] Verify export filename descriptive
- [ ] Test autocomplete dengan query cepat
- [ ] Test keyboard shortcuts (semua)
- [ ] Screen reader test (NVDA/JAWS)
- [ ] Tab navigation complete flow
- [ ] Debug panel (Ctrl+Shift+D)
- [ ] Cache refresh button
- [ ] Filter chips clear individual & all

---

## Success Criteria (Phase 5 Exit)

1. **Export Quality**
   - ✅ Export mencerminkan 100% UI state
   - ✅ Filename auto-generated dengan context
   - ✅ Timeline export dengan period breakdown
   - ✅ Visual progress feedback

2. **Data Integrity**
   - ✅ Snapshot total = Timeline total (within tolerance)
   - ✅ Cache auto-invalidates on data changes
   - ✅ Debug panel untuk validation

3. **Search UX**
   - ✅ Autocomplete <200ms response
   - ✅ Search history persists
   - ✅ Quick filter chips

4. **Accessibility**
   - ✅ WCAG 2.1 AA score ≥90%
   - ✅ Full keyboard navigation
   - ✅ Screen reader compatible

5. **Performance**
   - ✅ Export generation <3s for <500 items
   - ✅ Autocomplete debounce 200ms
   - ✅ No UI blocking during export

---

## Dependencies & Risks

| Dependency | Risk Level | Mitigation |
|------------|-----------|------------|
| Backend export refactor | 🟡 Medium | Start with CSV, iterate to PDF/Word |
| Large dataset export timeout | 🔴 High | Implement background job for >1000 items |
| localStorage quota | 🟢 Low | Limit search history to 50 items |
| Browser compatibility (autocomplete) | 🟢 Low | Use standard HTML5 datalist fallback |

---

## Next Phase Preview: Phase 6 (Future)

Potential topics for Phase 6:
- **Collaborative Features:** Comments, annotations on items
- **Budget Tracking:** Compare planned vs actual costs
- **Supplier Integration:** Link items to suppliers
- **Mobile App:** PWA for on-site access
- **AI Insights:** Cost prediction, anomaly detection

**Decision point:** Phase 6 planning will begin after Phase 5 retrospective.

---

**Last Updated:** 2025-12-03
**Document Owner:** Development Team
**Review Cycle:** End of each week during Phase 5 implementation
