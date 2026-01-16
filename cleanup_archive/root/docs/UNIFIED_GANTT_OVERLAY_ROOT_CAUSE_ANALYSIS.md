# 🔴 ROOT CAUSE ANALYSIS: Unified Gantt Overlay Bar Chart Tidak Muncul

**Date:** 2025-12-07
**System:** Unified Table Manager + Gantt Canvas Overlay
**Status:** CRITICAL BUG IDENTIFIED

---

## 🎯 EXECUTIVE SUMMARY

Bar chart tidak muncul pada **Unified Gantt Overlay** mode karena **DATA FLOW BREAKDOWN** di 3 titik kritis:

1. **UnifiedTableManager._buildBarData()** filtering bars yang valid
2. **GanttCanvasOverlay.syncWithTable()** tidak menemukan cell rectangles yang match
3. **TanStackGridManager.getCellBoundingRects()** return data dengan format yang tidak sesuai

---

## 🔍 DETAILED ROOT CAUSE

### **ISSUE #1: Bar Data Filter Terlalu Ketat** ⚠️
**File:** `UnifiedTableManager.js` line 132-134

```javascript
if ((!Number.isFinite(plannedValue) || plannedValue <= 0) &&
    (!Number.isFinite(actualValue) || actualValue <= 0)) {
  return;  // ❌ Skip cell - NO BAR CREATED
}
```

**Problem:**
- Kondisi `<=` 0 mengeliminasi bars dengan nilai 0
- Tapi dalam konteks gantt, nilai 0 bisa berarti "not started yet" dan tetap harus ditampilkan sebagai empty bar
- Jika **semua** data bernilai 0 atau invalid → `barData.length === 0` → **NO BARS RENDERED**

**Expected Behavior:**
- Bars dengan `planned > 0` ATAU `actual > 0` harus di-render
- Bars dengan nilai 0/0 bisa di-skip (ini OK)

**Diagnosis:**
```javascript
// Check di browser console:
console.log('[DEBUG] Planned cells:', mergedPlanned.size);
console.log('[DEBUG] Actual cells:', mergedActual.size);
console.log('[DEBUG] Bar data count:', barData.length);

// Jika mergedPlanned.size > 0 TAPI barData.length === 0
// → Berarti semua cell di-filter out karena plannedValue <= 0
```

---

### **ISSUE #2: Cell Rectangle Matching Failure** 🎯
**File:** `GanttCanvasOverlay.js` line 105-108

```javascript
this.barData.forEach((bar) => {
  const rect = cellRects.find(
    (c) => c.pekerjaanId === bar.pekerjaanId && c.columnId === bar.columnId,
  );
  if (!rect) return;  // ❌ BAR SKIPPED - NO MATCHING RECT
```

**Problem:**
- `bar.pekerjaanId` dan `bar.columnId` harus **EXACT MATCH** dengan `rect.pekerjaanId` dan `rect.columnId`
- Jika ada type mismatch (string vs number) → NO MATCH → NO BAR DRAWN

**Contoh Kasus:**
```javascript
// Bar data:
{
  pekerjaanId: 123,        // Number
  columnId: "col_456",     // String
  value: 25
}

// Cell rect:
{
  pekerjaanId: "123",      // String (dari dataset.pekerjaanId)
  columnId: "col_456",     // String
  x: 100, y: 50, ...
}

// Comparison:
123 === "123"  // ❌ FALSE → NO MATCH!
```

**Fix Required:**
```javascript
const rect = cellRects.find(
  (c) => String(c.pekerjaanId) === String(bar.pekerjaanId) &&
         c.columnId === bar.columnId
);
```

---

### **ISSUE #3: getCellBoundingRects Return Empty** 📦
**File:** `TanStackGridManager.js` line 437-460

```javascript
getCellBoundingRects() {
  const cells = this.bodyInner.querySelectorAll('.tanstack-grid-cell[data-column-id]');
  // ⚠️ Jika selector tidak match → cells.length === 0 → return []
}
```

**Potential Causes:**
1. **DOM not rendered yet** - Virtual scrolling belum render cells
2. **Class name mismatch** - Cells tidak memiliki class `tanstack-grid-cell`
3. **Missing data-column-id** - Attribute tidak di-set pada time cells
4. **Overlay called too early** - Before table rendering complete

**Diagnosis:**
```javascript
// Add to GanttCanvasOverlay.syncWithTable():
console.log('[DEBUG] Cell rects count:', cellRects.length);
console.log('[DEBUG] First 3 rects:', cellRects.slice(0, 3));

// Check DOM:
const cells = document.querySelectorAll('.tanstack-grid-cell[data-column-id]');
console.log('[DEBUG] DOM cells found:', cells.length);
```

---

### **ISSUE #4: Skeleton Grid Lines Instead of Bars** 🎨
**File:** `GanttCanvasOverlay.js` line 74-78

```javascript
// Skeleton visual aid: outline cells for alignment verification
this.ctx.strokeStyle = '#e2e8f0';
cellRects.forEach((rect) => {
  this.ctx.strokeRect(rect.x, rect.y, rect.width, rect.height);
});
```

**Problem:**
- Ini hanya menggambar **GRID OUTLINE**, bukan bar chart
- Jika `barData.length === 0`, hanya grid lines yang terlihat
- User mengira bar chart tidak muncul, padahal sebenarnya **NO DATA TO RENDER**

**Visual:**
```
Expected:  ████████░░░░░░  (Blue bar 50%)
Actual:    │         │      (Only grid lines)
```

---

## 🛠️ COMPREHENSIVE FIX STRATEGY

### **Fix #1: Improve Bar Data Building**
**File:** `UnifiedTableManager.js`

```javascript
_buildBarData(payload = {}) {
  // ... existing code ...

  tree.forEach((row) => {
    const pekerjaanId = row.pekerjaanId || row.id || row.raw?.pekerjaan_id;
    const label = row.name || row.raw?.nama || pekerjaanId;
    if (!pekerjaanId) return;

    columns.forEach((col) => {
      const meta = col.meta?.columnMeta;
      if (!col.meta?.timeColumn || !meta) return;

      const columnId = col.fieldId || col.id;
      const cellKey = `${pekerjaanId}-${columnId}`;

      // 🔧 FIX: Get values with proper fallback
      const fallback = this.tanstackGrid?.getTimeCellValue?.(pekerjaanId, columnId, meta) || 0;
      const plannedValue = this._resolveValue(mergedPlanned, cellKey, fallback);
      const actualValue = this._resolveValue(mergedActual, cellKey, 0);

      // 🔧 FIX: Changed condition - allow bars with AT LEAST one value > 0
      if ((Number.isFinite(plannedValue) && plannedValue > 0) ||
          (Number.isFinite(actualValue) && actualValue > 0)) {

        barData.push({
          pekerjaanId: String(pekerjaanId),  // 🔧 FIX: Convert to string for matching
          columnId: String(columnId),        // 🔧 FIX: Ensure string
          value: Number(actualValue) || 0,
          planned: Number(plannedValue) || 0,
          actual: Number(actualValue) || 0,
          variance: (Number(actualValue) || 0) - (Number(plannedValue) || 0),
          label,
          color: '#4dabf7',
        });
      }
    });
  });

  // 🔧 FIX: Add warning if no bars
  if (barData.length === 0) {
    console.warn('[UnifiedTable] ⚠️ NO BAR DATA! Check:',{
      'mergedPlanned.size': mergedPlanned?.size || 0,
      'mergedActual.size': mergedActual?.size || 0,
      'tree.length': tree.length,
      'columns.length': columns.length,
      'timeColumnsWithMeta': columns.filter(c => c.meta?.timeColumn).length
    });
  }

  this._log('buildBarData:done', { bars: barData.length });
  return barData;
}
```

---

### **Fix #2: Type-Safe Cell Matching**
**File:** `GanttCanvasOverlay.js`

```javascript
_drawBars(cellRects) {
  if (!Array.isArray(cellRects) || cellRects.length === 0 || this.barData.length === 0) {
    console.warn('[GanttOverlay] Cannot draw bars:', {
      cellRects: cellRects?.length || 0,
      barData: this.barData.length
    });
    return;
  }

  let barsDrawn = 0;
  let barsSkipped = 0;

  this.barData.forEach((bar) => {
    // 🔧 FIX: Type-safe matching with string conversion
    const rect = cellRects.find((c) =>
      String(c.pekerjaanId) === String(bar.pekerjaanId) &&
      String(c.columnId) === String(bar.columnId)
    );

    if (!rect) {
      barsSkipped++;
      if (barsSkipped <= 3) {
        console.warn('[GanttOverlay] No rect for bar:', {
          pekerjaanId: bar.pekerjaanId,
          columnId: bar.columnId,
          availableRects: cellRects.slice(0, 3).map(r => ({
            pId: r.pekerjaanId,
            cId: r.columnId
          }))
        });
      }
      return;
    }

    // ... existing bar drawing code ...
    barsDrawn++;
  });

  console.log(`[GanttOverlay] Bars drawn: ${barsDrawn}/${this.barData.length} (skipped: ${barsSkipped})`);
}
```

---

### **Fix #3: Ensure Cells Have Required Attributes**
**File:** `TanStackGridManager.js`

```javascript
_renderTimeCell(cellEl, row, pekerjaanId, columnId, columnMeta, columnDef) {
  // ... existing code ...

  // 🔧 FIX: Ensure data attributes for overlay matching
  cellEl.dataset.cellId = this._getCellKey(pekerjaanId, columnId);
  cellEl.dataset.pekerjaanId = String(pekerjaanId);  // 🔧 FIX: Convert to string
  cellEl.dataset.columnId = String(columnId);        // 🔧 FIX: Convert to string

  // 🔧 FIX: Add class for selector
  cellEl.classList.add('tanstack-grid-cell', 'time-cell');

  // ... rest of rendering ...
}
```

---

### **Fix #4: Add Comprehensive Debugging**
**File:** `GanttCanvasOverlay.js`

```javascript
syncWithTable() {
  const scrollArea = this.tableManager?.bodyScroll;
  if (!scrollArea) {
    console.error('[GanttOverlay] No scroll area!');
    return;
  }

  this.canvas.width = scrollArea.scrollWidth;
  this.canvas.height = scrollArea.scrollHeight;

  const cellRects = typeof this.tableManager.getCellBoundingRects === 'function'
    ? this.tableManager.getCellBoundingRects()
    : [];

  this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  this.barRects = [];

  // 🔧 FIX: Enhanced logging
  this._log('sync', {
    cells: cellRects.length,
    bars: this.barData.length,
    deps: this.dependencies.length,
    size: { w: this.canvas.width, h: this.canvas.height },
  });

  // 🔧 FIX: Add detailed diagnostic
  if (this.barData.length > 0 && cellRects.length === 0) {
    console.error('[GanttOverlay] ❌ CRITICAL: Have bar data but NO cell rects!');
    console.error('[GanttOverlay] Possible causes:');
    console.error('  1. Virtual scrolling not rendered cells yet');
    console.error('  2. DOM selector .tanstack-grid-cell[data-column-id] not matching');
    console.error('  3. Overlay initialized before table render complete');

    // Try to find cells with different selector
    const allCells = scrollArea.querySelectorAll('.tanstack-grid-cell');
    console.warn('[GanttOverlay] Found cells without data-column-id:', allCells.length);
  }

  // Skeleton visual aid - draw grid outline
  this.ctx.strokeStyle = '#e2e8f0';
  cellRects.forEach((rect) => {
    this.ctx.strokeRect(rect.x, rect.y, rect.width, rect.height);
  });

  this._drawBars(cellRects);
  this._drawDependencies(cellRects);
}
```

---

## 🧪 TESTING PROCEDURE

### **Test 1: Verify Data Loading**
```javascript
// Browser Console:
window.DEBUG_GANTT = true;

// Then switch to Gantt tab and check:
// 1. [UnifiedTable] buildBarData:start - shows mergedPlanned.size, mergedActual.size
// 2. [UnifiedTable] buildBarData:done - shows bars count
// 3. [GanttOverlay] sync - shows cells, bars count
// 4. [GanttOverlay] Bars drawn: X/Y
```

### **Test 2: Inspect Cell Rectangles**
```javascript
// After Gantt mode activated:
const overlay = document.querySelector('.gantt-canvas-overlay');
const manager = window.appInstance?.unifiedManager;

if (manager?.tanstackGrid) {
  const rects = manager.tanstackGrid.getCellBoundingRects();
  console.log('Cell rects:', rects.length);
  console.log('Sample rect:', rects[0]);
}
```

### **Test 3: Verify Bar Data Structure**
```javascript
const unifiedManager = window.appInstance?.unifiedManager;
if (unifiedManager) {
  const barData = unifiedManager._buildBarData({
    tree: appInstance.state.pekerjaanTree,
    timeColumns: appInstance._getDisplayTimeColumns()
  });
  console.log('Bar data:', barData.length);
  console.log('First bar:', barData[0]);
}
```

---

## 📋 IMPLEMENTATION CHECKLIST

- [ ] Fix #1: Update `UnifiedTableManager._buildBarData()` filter logic
- [ ] Fix #2: Add type-safe matching in `GanttCanvasOverlay._drawBars()`
- [ ] Fix #3: Ensure data attributes in `TanStackGridManager._renderTimeCell()`
- [ ] Fix #4: Add comprehensive debugging logs
- [ ] Test: Verify bars render with sample data
- [ ] Test: Verify bars update on scroll
- [ ] Test: Verify bars update on data change
- [ ] Documentation: Update unified overlay architecture docs

---

## 🎯 EXPECTED OUTCOME

After applying all fixes:

1. **Bars dengan data planned > 0** akan muncul sebagai blue bars
2. **Bars dengan data actual > 0** akan muncul sebagai orange bars (overlay)
3. **Console logs** akan menunjukkan diagnostic information yang jelas
4. **No silent failures** - semua error akan di-log dengan konteks yang jelas

