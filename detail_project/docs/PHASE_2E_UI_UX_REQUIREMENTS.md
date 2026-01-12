# Phase 2E: UI/UX Requirements & Improvements

**Date**: 2025-11-23
**Status**: 📋 **REQUIREMENTS GATHERING**
**Purpose**: Detailed UI/UX requirements for grid improvements across all modes

---

## 🎯 OVERVIEW

Before implementing mode switching and time period configuration, we need to ensure the UI/UX is properly designed for all modes (Weekly & Monthly). This document captures detailed requirements for grid behavior, input validation, and visual consistency.

---

## 📋 REQUIREMENT #1: Grid Scrolling Behavior

### Current Issues
- ❌ Only right panel scrolls horizontally
- ❌ Vertical scroll not synchronized between left/right panels
- ❌ Row heights might not align during scroll

### Required Behavior

#### 1.1 Horizontal Scroll (Right Panel Only)
**Requirement**: Right panel (tahapan columns) should scroll horizontally while left panel (pekerjaan tree) stays fixed.

**Implementation**:
```html
<!-- Left Panel: Fixed (no horizontal scroll) -->
<div class="left-panel-wrapper" style="overflow-x: hidden; overflow-y: hidden;">
  <table class="left-table">
    <thead><!-- Uraian, Volume, Satuan --></thead>
    <tbody><!-- Pekerjaan rows --></tbody>
  </table>
</div>

<!-- Right Panel: Horizontal scroll -->
<div class="right-panel-wrapper" style="overflow-x: auto; overflow-y: hidden;">
  <table class="right-table">
    <thead><!-- Week 1, Week 2, ... --></thead>
    <tbody><!-- Percentage cells --></tbody>
  </table>
</div>
```

**User Experience**:
- ✅ User scrolls horizontally → Only right panel (week columns) scrolls
- ✅ Left panel (pekerjaan names) stays visible at all times
- ✅ Smooth scrolling (no jank)
- ✅ Scrollbar visible only on right panel

---

#### 1.2 Vertical Scroll (Synchronized Both Panels)
**Requirement**: When user scrolls vertically, BOTH left and right panels scroll together in perfect sync.

**Implementation**:
```javascript
// Sync vertical scroll between left and right panels
const leftPanel = document.querySelector('.left-panel-wrapper');
const rightPanel = document.querySelector('.right-panel-wrapper');

// Create a shared container for vertical scrolling
const scrollContainer = document.querySelector('.split-panel-wrapper');

scrollContainer.addEventListener('scroll', (e) => {
  const scrollTop = e.target.scrollTop;

  // Sync both panels to same vertical position
  leftPanel.scrollTop = scrollTop;
  rightPanel.scrollTop = scrollTop;
});

// Also sync when scrolling individual panels (fallback)
leftPanel.addEventListener('scroll', (e) => {
  rightPanel.scrollTop = e.target.scrollTop;
});

rightPanel.addEventListener('scroll', (e) => {
  leftPanel.scrollTop = e.target.scrollTop;
});
```

**User Experience**:
- ✅ User scrolls vertically → Both panels scroll together
- ✅ No misalignment between left and right rows
- ✅ Scrollbar appears on container (not individual panels)
- ✅ Works with mouse wheel, trackpad, and scrollbar

---

#### 1.3 Row Height Synchronization
**Requirement**: Rows in left and right panels must have identical heights at all times.

**Current Implementation** (already in place):
```javascript
// grid-renderer.js
_syncRowHeights() {
  const leftRows = this.domRefs.leftTbody.querySelectorAll('tr');
  const rightRows = this.domRefs.rightTbody.querySelectorAll('tr');

  leftRows.forEach((leftRow, index) => {
    const rightRow = rightRows[index];
    if (!rightRow) return;

    const leftHeight = leftRow.offsetHeight;
    const rightHeight = rightRow.offsetHeight;
    const maxHeight = Math.max(leftHeight, rightHeight);

    leftRow.style.height = `${maxHeight}px`;
    rightRow.style.height = `${maxHeight}px`;
  });
}
```

**Enhancement Needed**:
```javascript
// Call sync after any DOM change
_renderRow(node, index) {
  // ... render logic ...

  // Sync heights after render
  requestAnimationFrame(() => {
    this._syncRowHeights();
  });
}

// Re-sync on window resize
window.addEventListener('resize', debounce(() => {
  this._syncRowHeights();
}, 100));

// Re-sync after cell content changes
_onCellValueChange(cellId, newValue) {
  // ... update cell ...

  requestAnimationFrame(() => {
    this._syncRowHeights();
  });
}
```

---

### Testing Checklist: Scrolling
- [ ] Horizontal scroll works on right panel only
- [ ] Left panel stays fixed during horizontal scroll
- [ ] Vertical scroll syncs both panels perfectly
- [ ] No row misalignment during scroll
- [ ] Row heights stay synced after content changes
- [ ] Scrolling smooth (no lag or jank)
- [ ] Works on Chrome, Firefox, Edge
- [ ] Works with mouse wheel, trackpad, scrollbar

---

## 📋 REQUIREMENT #2: Input Validation & Error Handling

### Current Issues
- ❌ No input type validation (user can enter text)
- ❌ No range validation (can enter > 100% or negative)
- ❌ No cumulative validation (total > 100% per pekerjaan)
- ❌ No visual error indicators

### Required Behavior

#### 2.1 Input Type Validation
**Requirement**: Only allow numeric input (integers or decimals) with max 2 decimal places.

**Implementation**:
```javascript
// Input field configuration
function createPercentageInput(cellKey, currentValue) {
  const input = document.createElement('input');
  input.type = 'number';
  input.step = '0.01';  // Allow decimals up to 2 places
  input.min = '0.01';   // Minimum 0.01%
  input.max = '100.00'; // Maximum 100%
  input.value = currentValue || '';
  input.placeholder = '0.00';
  input.classList.add('cell-input', 'percentage-input');

  // Real-time validation
  input.addEventListener('input', (e) => {
    validatePercentageInput(e.target);
  });

  // Validation on blur
  input.addEventListener('blur', (e) => {
    validateAndFormatPercentage(e.target);
  });

  return input;
}

function validatePercentageInput(input) {
  const value = parseFloat(input.value);

  // Remove non-numeric characters
  input.value = input.value.replace(/[^0-9.]/g, '');

  // Only one decimal point
  const parts = input.value.split('.');
  if (parts.length > 2) {
    input.value = parts[0] + '.' + parts.slice(1).join('');
  }

  // Max 2 decimal places
  if (parts[1] && parts[1].length > 2) {
    input.value = parseFloat(input.value).toFixed(2);
  }

  // Visual feedback
  if (isNaN(value) || value < 0.01 || value > 100) {
    input.classList.add('invalid');
  } else {
    input.classList.remove('invalid');
  }
}

function validateAndFormatPercentage(input) {
  let value = parseFloat(input.value);

  // Handle invalid input
  if (isNaN(value) || value < 0.01) {
    input.value = '';
    return;
  }

  // Clamp to range
  value = Math.max(0.01, Math.min(100, value));

  // Format to 2 decimal places
  input.value = value.toFixed(2);
}
```

**Visual Feedback**:
```css
/* Invalid input styling */
.cell-input.invalid {
  border: 2px solid #dc3545 !important;
  background-color: #fff5f5;
}

.cell-input.invalid:focus {
  box-shadow: 0 0 0 0.2rem rgba(220, 53, 69, 0.25);
}
```

---

#### 2.2 Range Validation
**Requirement**: Percentage must be between 0.01% and 100.00%.

**Validation Rules**:
```javascript
const VALIDATION_RULES = {
  MIN_PERCENTAGE: 0.01,
  MAX_PERCENTAGE: 100.00,
  DECIMAL_PLACES: 2
};

function validateRange(value) {
  const num = parseFloat(value);

  if (isNaN(num)) {
    return {
      valid: false,
      error: 'Input harus berupa angka'
    };
  }

  if (num < VALIDATION_RULES.MIN_PERCENTAGE) {
    return {
      valid: false,
      error: `Minimum ${VALIDATION_RULES.MIN_PERCENTAGE}%`
    };
  }

  if (num > VALIDATION_RULES.MAX_PERCENTAGE) {
    return {
      valid: false,
      error: `Maksimum ${VALIDATION_RULES.MAX_PERCENTAGE}%`
    };
  }

  return { valid: true };
}
```

**Error Display**:
```javascript
function showInputError(input, errorMessage) {
  // Add invalid class
  input.classList.add('invalid');

  // Create tooltip
  const tooltip = document.createElement('div');
  tooltip.classList.add('input-error-tooltip');
  tooltip.textContent = errorMessage;

  // Position tooltip
  const rect = input.getBoundingClientRect();
  tooltip.style.top = `${rect.bottom + 5}px`;
  tooltip.style.left = `${rect.left}px`;

  // Append to body
  document.body.appendChild(tooltip);

  // Remove after 3 seconds
  setTimeout(() => {
    tooltip.remove();
  }, 3000);
}
```

```css
/* Error tooltip */
.input-error-tooltip {
  position: absolute;
  z-index: 1000;
  background: #dc3545;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  white-space: nowrap;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.input-error-tooltip::before {
  content: '';
  position: absolute;
  top: -4px;
  left: 10px;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-bottom: 4px solid #dc3545;
}
```

---

#### 2.3 Cumulative Validation (Total ≤ 100%)
**Requirement**: Total percentage across all tahapan for a single pekerjaan must not exceed 100%.

**Implementation**:
```javascript
function validateCumulativePercentage(pekerjaanId, newValue, currentTahapanId) {
  // Get all assignments for this pekerjaan
  const assignments = state.assignmentMap || new Map();

  let total = 0;

  // Sum all existing assignments
  state.timeColumns.forEach(column => {
    const cellKey = `${pekerjaanId}-${column.id}`;

    if (column.tahapanId === currentTahapanId) {
      // Use new value for current cell
      total += parseFloat(newValue) || 0;
    } else {
      // Use existing value for other cells
      total += parseFloat(assignments.get(cellKey)) || 0;
    }
  });

  // Check if total exceeds 100%
  if (total > 100) {
    return {
      valid: false,
      total: total,
      exceeded: total - 100,
      error: `Total progress (${total.toFixed(2)}%) melebihi 100%. Kelebihan: ${(total - 100).toFixed(2)}%`
    };
  }

  return {
    valid: true,
    total: total,
    remaining: 100 - total
  };
}
```

**Visual Feedback**:
```javascript
function updateProgressSummary(pekerjaanId) {
  const validation = validateCumulativePercentage(pekerjaanId, 0, null);

  // Find pekerjaan row
  const row = document.querySelector(`tr[data-pekerjaan-id="${pekerjaanId}"]`);
  if (!row) return;

  // Get or create progress indicator
  let indicator = row.querySelector('.progress-indicator');
  if (!indicator) {
    indicator = document.createElement('span');
    indicator.classList.add('progress-indicator');
    row.querySelector('.col-uraian').appendChild(indicator);
  }

  // Update indicator
  const total = validation.total;
  indicator.textContent = `${total.toFixed(2)}%`;

  // Color coding
  indicator.classList.remove('complete', 'partial', 'exceeded');

  if (total > 100) {
    indicator.classList.add('exceeded');
    indicator.title = `Kelebihan: ${(total - 100).toFixed(2)}%`;
  } else if (total === 100) {
    indicator.classList.add('complete');
    indicator.title = 'Lengkap (100%)';
  } else if (total > 0) {
    indicator.classList.add('partial');
    indicator.title = `Tersisa: ${(100 - total).toFixed(2)}%`;
  }
}
```

```css
/* Progress indicator */
.progress-indicator {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: bold;
}

.progress-indicator.partial {
  background-color: #ffc107;
  color: #000;
}

.progress-indicator.complete {
  background-color: #28a745;
  color: white;
}

.progress-indicator.exceeded {
  background-color: #dc3545;
  color: white;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
```

---

#### 2.4 Save Validation
**Requirement**: Prevent saving if any pekerjaan has total > 100%.

**Implementation**:
```javascript
// In SaveHandler
async save() {
  // Validate all pekerjaan before save
  const validation = this.validateAllPekerjaan();

  if (!validation.valid) {
    this.showValidationErrors(validation.errors);
    return;
  }

  // Proceed with save
  // ...
}

validateAllPekerjaan() {
  const errors = [];
  const pekerjaanNodes = this.state.flatPekerjaan.filter(n => n.type === 'pekerjaan');

  pekerjaanNodes.forEach(node => {
    const validation = validateCumulativePercentage(node.id, 0, null);

    if (!validation.valid) {
      errors.push({
        pekerjaanId: node.id,
        pekerjaanName: node.nama,
        total: validation.total,
        exceeded: validation.exceeded
      });
    }
  });

  return {
    valid: errors.length === 0,
    errors: errors
  };
}

showValidationErrors(errors) {
  const errorList = errors.map(e =>
    `- ${e.pekerjaanName}: ${e.total.toFixed(2)}% (kelebihan ${e.exceeded.toFixed(2)}%)`
  ).join('\n');

  const message = `
Tidak dapat menyimpan. Beberapa pekerjaan melebihi 100%:

${errorList}

Harap perbaiki terlebih dahulu.
  `;

  // Show modal or alert
  alert(message); // Replace with proper modal
}
```

---

### Testing Checklist: Input Validation
- [ ] Only numeric input accepted
- [ ] Max 2 decimal places enforced
- [ ] Range 0.01-100 enforced
- [ ] Invalid input shows red border
- [ ] Error tooltip shows correct message
- [ ] Cumulative validation calculates correctly
- [ ] Progress indicator shows current total
- [ ] Exceeded total shows red indicator
- [ ] Cannot save if total > 100%
- [ ] Validation error modal shows all issues

---

## 📋 REQUIREMENT #3: Column Width Standardization

### Current Issues
- ❌ Column widths vary between modes
- ❌ Weekly columns might be too narrow
- ❌ Monthly columns might be too wide
- ❌ No visual consistency

### Required Behavior

#### 3.1 Standard Column Widths

**Weekly Mode**:
```css
/* Weekly column widths */
.right-table th.time-column.weekly,
.right-table td.time-cell.weekly {
  min-width: 100px;
  max-width: 120px;
  width: 110px;
}

/* Header spans 2 rows for weekly */
.right-table th.time-column.weekly {
  text-align: center;
  vertical-align: middle;
}

.right-table th.time-column.weekly .week-label {
  display: block;
  font-weight: bold;
  font-size: 13px;
}

.right-table th.time-column.weekly .week-range {
  display: block;
  font-size: 11px;
  color: #6c757d;
  margin-top: 2px;
}
```

**Monthly Mode**:
```css
/* Monthly column widths */
.right-table th.time-column.monthly,
.right-table td.time-cell.monthly {
  min-width: 120px;
  max-width: 150px;
  width: 135px;
}

.right-table th.time-column.monthly {
  text-align: center;
  vertical-align: middle;
}

.right-table th.time-column.monthly .month-label {
  display: block;
  font-weight: bold;
  font-size: 14px;
}

.right-table th.time-column.monthly .month-range {
  display: block;
  font-size: 11px;
  color: #6c757d;
  margin-top: 2px;
}
```

**Left Panel (Fixed)**:
```css
/* Left panel columns - same for all modes */
.left-table th.col-tree,
.left-table td.col-tree {
  width: 40px;
  min-width: 40px;
  max-width: 40px;
}

.left-table th.col-uraian,
.left-table td.col-uraian {
  width: 400px;
  min-width: 300px;
  max-width: 500px;
}

.left-table th.col-volume,
.left-table td.col-volume {
  width: 100px;
  min-width: 80px;
  max-width: 120px;
}

.left-table th.col-satuan,
.left-table td.col-satuan {
  width: 80px;
  min-width: 60px;
  max-width: 100px;
}
```

---

#### 3.2 Responsive Column Widths

**For smaller screens** (optional future enhancement):
```css
@media (max-width: 1200px) {
  /* Reduce weekly column width */
  .right-table th.time-column.weekly,
  .right-table td.time-cell.weekly {
    min-width: 90px;
    width: 95px;
  }

  /* Reduce monthly column width */
  .right-table th.time-column.monthly,
  .right-table td.time-cell.monthly {
    min-width: 110px;
    width: 120px;
  }

  /* Reduce left panel widths */
  .left-table th.col-uraian,
  .left-table td.col-uraian {
    width: 300px;
  }
}
```

---

#### 3.3 Column Header Template

**Weekly Header**:
```html
<th class="time-column weekly" data-column-id="tahap-2240">
  <div class="column-header-content">
    <span class="week-label">Week 1</span>
    <span class="week-range">(09/01 - 15/01)</span>
    <span class="week-days" title="3 hari kerja">3d</span>
  </div>
</th>
```

**Monthly Header**:
```html
<th class="time-column monthly" data-column-id="tahap-3001">
  <div class="column-header-content">
    <span class="month-label">Jan 2026</span>
    <span class="month-range">(01/01 - 31/01)</span>
    <span class="month-weeks" title="4 minggu">4w</span>
  </div>
</th>
```

---

### Testing Checklist: Column Widths
- [ ] Weekly columns: 110px standard
- [ ] Monthly columns: 135px standard
- [ ] Left panel columns: consistent across modes
- [ ] Headers display correctly (label + range)
- [ ] Partial periods show day/week count
- [ ] Responsive widths work (optional)
- [ ] Visual consistency across modes

---

## 📋 REQUIREMENT #4: Additional UI/UX Improvements

### 4.1 Loading States

**During data load**:
```html
<div class="grid-loading-overlay">
  <div class="spinner-border text-primary" role="status">
    <span class="visually-hidden">Loading...</span>
  </div>
  <p class="mt-2">Memuat data...</p>
</div>
```

**During save**:
```html
<div class="save-progress-indicator">
  <div class="spinner-border spinner-border-sm" role="status"></div>
  <span class="ms-2">Menyimpan...</span>
</div>
```

---

### 4.2 Empty State Messages

**No time columns**:
```html
<div class="empty-state text-center py-5">
  <i class="bi bi-calendar-x" style="font-size: 3rem; color: #6c757d;"></i>
  <h5 class="mt-3">Belum ada periode waktu</h5>
  <p class="text-muted">Silakan generate periode waktu terlebih dahulu.</p>
  <button class="btn btn-primary" onclick="generateTimePeriods()">
    <i class="bi bi-plus-circle"></i> Generate Periode
  </button>
</div>
```

**No pekerjaan**:
```html
<div class="empty-state text-center py-5">
  <i class="bi bi-inbox" style="font-size: 3rem; color: #6c757d;"></i>
  <h5 class="mt-3">Belum ada pekerjaan</h5>
  <p class="text-muted">Tambahkan pekerjaan terlebih dahulu untuk melanjutkan.</p>
  <a href="/detail_project/110/add-pekerjaan/" class="btn btn-primary">
    <i class="bi bi-plus-circle"></i> Tambah Pekerjaan
  </a>
</div>
```

---

### 4.3 Keyboard Shortcuts

**Navigation**:
- `Tab` / `Shift+Tab`: Move between cells
- `Enter`: Save current cell and move down
- `Escape`: Cancel editing
- `Ctrl+S`: Save all changes

**Implementation**:
```javascript
document.addEventListener('keydown', (e) => {
  // Ctrl+S to save
  if (e.ctrlKey && e.key === 's') {
    e.preventDefault();
    saveHandler.save();
    return;
  }

  // Handle cell navigation
  const activeCell = document.activeElement;
  if (!activeCell.classList.contains('cell-input')) return;

  if (e.key === 'Enter') {
    e.preventDefault();
    moveToNextCell(activeCell, 'down');
  } else if (e.key === 'Escape') {
    activeCell.blur();
  }
});
```

---

### 4.4 Context Menu (Right-click)

**On cell right-click**:
```javascript
cell.addEventListener('contextmenu', (e) => {
  e.preventDefault();

  const menu = createContextMenu([
    { label: 'Clear Cell', icon: 'bi-x', action: () => clearCell(cellId) },
    { label: 'Copy Value', icon: 'bi-clipboard', action: () => copyValue(cellId) },
    { label: 'Paste Value', icon: 'bi-clipboard-check', action: () => pasteValue(cellId) },
    { separator: true },
    { label: 'Fill Down', icon: 'bi-arrow-down', action: () => fillDown(cellId) },
    { label: 'Fill Right', icon: 'bi-arrow-right', action: () => fillRight(cellId) }
  ]);

  showContextMenu(menu, e.clientX, e.clientY);
});
```

---

### 4.5 Progress Summary Panel

**Sticky footer showing totals**:
```html
<div class="progress-summary-panel">
  <div class="summary-item">
    <label>Total Pekerjaan:</label>
    <span class="value">25</span>
  </div>
  <div class="summary-item">
    <label>Lengkap (100%):</label>
    <span class="value text-success">12</span>
  </div>
  <div class="summary-item">
    <label>Parsial (< 100%):</label>
    <span class="value text-warning">8</span>
  </div>
  <div class="summary-item">
    <label>Kelebihan (> 100%):</label>
    <span class="value text-danger">5</span>
  </div>
  <div class="summary-item">
    <label>Belum diisi:</label>
    <span class="value text-muted">0</span>
  </div>
</div>
```

---

### 4.6 Chart Preview Thumbnails

**In grid tab, show mini chart previews**:
```html
<div class="chart-previews">
  <div class="chart-preview-item">
    <label>Kurva-S</label>
    <canvas id="kurva-s-mini" width="200" height="100"></canvas>
  </div>
  <div class="chart-preview-item">
    <label>Gantt</label>
    <canvas id="gantt-mini" width="200" height="100"></canvas>
  </div>
</div>
```

---

### Testing Checklist: Additional Features
- [ ] Loading overlay shows during data load
- [ ] Save indicator shows during save
- [ ] Empty states display correctly
- [ ] Keyboard shortcuts work
- [ ] Context menu appears on right-click
- [ ] Progress summary updates in real-time
- [ ] Chart previews render (optional)

---

## 🎯 PRIORITY MATRIX

### Must Have (P0) - Critical for Launch
1. ✅ **Synchronized Vertical Scroll** - Core functionality
2. ✅ **Input Type Validation** - Prevent bad data
3. ✅ **Cumulative Validation** - Prevent total > 100%
4. ✅ **Standard Column Widths** - Visual consistency
5. ✅ **Loading States** - User feedback
6. ✅ **Empty States** - Guide new users

### Should Have (P1) - Important for UX
7. ✅ **Range Validation Error Tooltips** - Better feedback
8. ✅ **Progress Indicator per Pekerjaan** - Visual progress tracking
9. ✅ **Save Validation** - Prevent invalid saves
10. ✅ **Keyboard Shortcuts (Tab, Enter)** - Faster data entry

### Nice to Have (P2) - Polish
11. ⏳ **Context Menu** - Power user features
12. ⏳ **Progress Summary Panel** - Overview statistics
13. ⏳ **Chart Previews** - Quick glance at charts
14. ⏳ **Responsive Column Widths** - Mobile support

---

## 📋 IMPLEMENTATION CHECKLIST

### Phase 2E.1: Grid Scrolling (Must Have)
- [ ] Implement synchronized vertical scroll
- [ ] Test horizontal scroll (right panel only)
- [ ] Enhance row height synchronization
- [ ] Add scroll event listeners
- [ ] Test across browsers

### Phase 2E.2: Input Validation (Must Have)
- [ ] Implement input type validation
- [ ] Add range validation (0.01-100)
- [ ] Create cumulative validation logic
- [ ] Add visual error indicators
- [ ] Implement save-time validation
- [ ] Create validation error modal

### Phase 2E.3: Column Standardization (Must Have)
- [ ] Define standard widths (weekly, monthly)
- [ ] Update CSS for column widths
- [ ] Create column header templates
- [ ] Test visual consistency

### Phase 2E.4: UI Polish (Should Have)
- [ ] Add loading overlays
- [ ] Create empty state components
- [ ] Implement keyboard shortcuts
- [ ] Add progress indicators
- [ ] Test user flows

### Phase 2E.5: Advanced Features (Nice to Have)
- [ ] Implement context menu
- [ ] Create progress summary panel
- [ ] Add chart preview thumbnails
- [ ] Responsive design enhancements

---

**Last Updated**: 2025-11-23
**Status**: Requirements Complete - Ready for Roadmap Integration
**Next**: Update PHASE_2E_ROADMAP.md to include UI/UX requirements
