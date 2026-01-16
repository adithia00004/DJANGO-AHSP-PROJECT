# Kurva S - Gap Analysis & Corrective Action Plan

**Date:** 2025-12-12
**Audited By:** User
**Status:** 🔴 **CRITICAL GAPS IDENTIFIED**
**Priority:** ⚠️ **IMMEDIATE ACTION REQUIRED**

---

## 📋 Executive Summary

Audit menunjukkan **gap kritis** antara **roadmap documentation** vs **actual implementation**. Roadmap menyatakan "100% aligned, siap implementasi", tetapi **kode aktual belum mengimplementasikan Phase 1-3 fixes**. Diperlukan corrective action segera untuk align implementasi dengan roadmap.

**Critical Findings:**
- ❌ **Canvas overlay** masih versi lama (full scrollWidth, no transform compensation)
- ❌ **Koordinat X** masih absolut (no pinnedWidth/scrollLeft adjustment)
- ❌ **Y-axis overlay** tidak fixed ke viewport kanan
- ❌ **Data pipeline** menggunakan simple average (no volume/harga weighting, no dataset-builder.js)
- ❌ **Cost mode integration** tidak ter-implement (masih pakai uPlot lama)
- ❌ **Documentation misleading** (claim 100% ready tapi kode belum match)

---

## 🔍 Gap Analysis: Roadmap vs Reality

### Gap #1: Canvas Overlay Architecture 🔴 CRITICAL

**Roadmap Claim:**
> "Phase 1 complete: Transform compensation applied, viewport-sized canvas, no overlap with frozen column"

**Reality (KurvaSCanvasOverlay.js:103-110):**
```javascript
// ❌ CURRENT IMPLEMENTATION (BROKEN)
syncWithTable() {
  // Canvas covers FULL scrollable area
  this.canvas.width = scrollArea.scrollWidth;  // ❌ Can exceed 32,767px!
  this.canvas.height = scrollArea.scrollHeight;

  // Keep canvases positioned at 0,0
  this.canvas.style.left = '0px';  // ❌ NO pinnedWidth offset!
  this.canvas.style.top = '0px';
  // ❌ NO transform compensation!
  // ❌ NO scrollLeft tracking!
}
```

**Problems:**
1. ❌ Canvas width = `scrollWidth` (risks >32k px blank canvas)
2. ❌ Canvas left = `0px` (overlaps frozen column)
3. ❌ No `transform: translateX(scrollLeft)` (will scroll with parent)
4. ❌ No scroll position tracking (`this.scrollLeft = 0`)

**Expected (Per Roadmap Phase 1):**
```javascript
// ✅ SHOULD BE (Phase 1 Pattern)
syncWithTable() {
  const scrollArea = this.tableManager?.bodyScroll;
  if (!scrollArea) return;

  // Track scroll position
  this.scrollLeft = scrollArea.scrollLeft || 0;
  this.pinnedWidth = this._getPinnedWidth();

  // Viewport-sized canvas (not full scrollWidth)
  const viewportWidth = scrollArea.clientWidth - this.pinnedWidth;
  const MAX_CANVAS_WIDTH = 32000;

  this.canvas.width = Math.min(viewportWidth, MAX_CANVAS_WIDTH);
  this.canvas.height = Math.min(scrollArea.clientHeight, 16000);

  // Transform compensation
  this.canvas.style.left = `${this.pinnedWidth}px`;  // ✅ Start after frozen
  this.canvas.style.transform = `translateX(${this.scrollLeft}px)`;  // ✅ Compensate scroll
}
```

**Impact:** 🔴 **CRITICAL**
- Curve overlaps frozen column ✗
- Canvas can go blank on large projects (>32k px) ✗
- No scroll compensation → visual jumping ✗

**Status:** ❌ **NOT IMPLEMENTED** (Gap: 100%)

---

### Gap #2: Coordinate System 🔴 CRITICAL

**Roadmap Claim:**
> "Phase 2 complete: X=0 at frozen boundary, nodes on grid lines (column right edge), canvas-relative coordinates"

**Reality (KurvaSCanvasOverlay.js:282):**
```javascript
// ❌ CURRENT IMPLEMENTATION (WRONG)
_getWeekColumnCenters(cellRects) {
  cellRects.forEach((rect) => {
    // Calculate center X position of this column (absolute coordinates)
    const centerX = rect.x + rect.width / 2;  // ❌ Absolute, not canvas-relative!
    columnCenters.set(columnId, centerX);    // ❌ No pinnedWidth/scrollLeft adjustment!
  });
  return columnCenters;
}
```

**Problems:**
1. ❌ X coordinates are **absolute** (from scrollArea edge), not **canvas-relative**
2. ❌ Nodes at **column center**, not **grid lines** (column right edge)
3. ❌ No `pinnedWidth` subtraction
4. ❌ No `scrollLeft` subtraction
5. ❌ X=0 is scrollArea left edge, NOT frozen boundary

**Expected (Per Roadmap Phase 2):**
```javascript
// ✅ SHOULD BE (Phase 2 Pattern)
_getWeekGridLines(cellRects) {
  const gridLines = new Map();

  // Special case: X=0 at frozen boundary
  gridLines.set('0', 0);  // ✅ Origin at frozen/scrollable boundary

  cellRects.forEach((rect) => {
    const columnId = String(rect.columnId);
    if (!gridLines.has(columnId)) {
      // ✅ Grid line = right edge of column (not center!)
      const absoluteGridLineX = rect.x + rect.width;

      // ✅ Canvas-relative coordinates
      const canvasGridLineX = absoluteGridLineX - this.pinnedWidth - this.scrollLeft;

      gridLines.set(columnId, canvasGridLineX);
    }
  });

  return gridLines;
}
```

**Impact:** 🔴 **CRITICAL**
- Nodes NOT on grid lines (user requirement violated) ✗
- X=0 not at frozen boundary (user requirement violated) ✗
- Coordinates break on scroll (no compensation) ✗

**Status:** ❌ **NOT IMPLEMENTED** (Gap: 100%)

---

### Gap #3: Y-Axis Overlay Positioning 🟡 HIGH

**Roadmap Claim:**
> "Y-axis overlay fixed to right viewport edge, stays visible during scroll"

**Reality (KurvaSCanvasOverlay.js:36-38):**
```javascript
// ❌ CURRENT IMPLEMENTATION (PROBLEMATIC)
this.yAxisCanvas.style.cssText = `
  position: absolute;
  top: 0;
  right: 0;  // ❌ Right 0 of scrollArea (scrolls with content!)
  // ...
`;
```

**Problems:**
1. ❌ `position: absolute` with `right: 0` means right edge of **scrollArea**
2. ❌ When scrollArea scrolls horizontally, Y-axis scrolls with it
3. ❌ Y-axis not "pinned" to viewport right edge
4. ❌ Height = scrollHeight (can be very tall, unnecessary)

**Expected (Per Roadmap):**
```javascript
// ✅ SHOULD BE (Fixed to Viewport)
this.yAxisCanvas.style.cssText = `
  position: fixed;  // ✅ Fixed to viewport
  top: ${scrollAreaTop}px;  // ✅ Align with scroll area top
  right: 20px;  // ✅ Fixed distance from viewport right
  width: 60px;
  height: ${scrollAreaHeight}px;  // ✅ Match visible height only
  pointer-events: none;
  z-index: 11;
`;

// OR use sticky positioning within grid
this.yAxisCanvas.style.cssText = `
  position: sticky;  // ✅ Sticky within scroll area
  right: 0;
  top: 0;
  // ...
`;
```

**Impact:** 🟡 **HIGH**
- Y-axis moves with horizontal scroll (bad UX) ✗
- Not "pinned" as claimed in roadmap ✗

**Status:** ❌ **NOT IMPLEMENTED** (Gap: 100%)

---

### Gap #4: Data Pipeline & Weighting 🔴 CRITICAL

**Roadmap Claim:**
> "Uses dataset-builder.js with volume/harga weighting and API integration for cost mode"

**Reality (UnifiedTableManager.js:353-395):**
```javascript
// ❌ CURRENT IMPLEMENTATION (SIMPLE AVERAGE, NO WEIGHTING)
_calculateCumulativeProgress(timeColumns, cellData) {
  let cumulativeProgress = 0;

  sortedColumns.forEach((col) => {
    // Sum all progress values for this week
    let weekProgress = 0;
    let weekCount = 0;

    cellData.forEach((value, cellKey) => {
      const [, colId] = String(cellKey).split('-');
      if (String(colId).trim() === String(columnId).trim()) {
        const numValue = Number(value);
        if (Number.isFinite(numValue)) {
          weekProgress += numValue;  // ❌ Just sum values
          weekCount += 1;
        }
      }
    });

    // Average progress for this week
    const avgProgress = weekCount > 0 ? weekProgress / weekCount : 0;  // ❌ Simple average!
    cumulativeProgress += avgProgress;  // ❌ No volume/harga weighting!

    curvePoints.push({
      columnId: String(columnId),
      cumulativeProgress: Math.min(100, cumulativeProgress),
    });
  });

  return curvePoints;
}
```

**Problems:**
1. ❌ Uses **simple average** (sum / count), not **weighted by volume or harga**
2. ❌ Does NOT use `dataset-builder.js` functions
3. ❌ Does NOT call `buildProgressDataset()` or `buildCostDataset()`
4. ❌ Ignores `volumeLookup` and `hargaLookup`
5. ❌ Cumulative calculation is **additive average** (wrong formula!)

**Expected (Per Roadmap & Consistency Report):**
```javascript
// ✅ SHOULD BE (Use dataset-builder.js)
import { buildProgressDataset, buildCostDataset } from '../kurva-s/dataset-builder.js';

_buildCurveData(payload = {}) {
  const stateManager = this.state?.stateManager;

  // For progress mode: Use dataset-builder.js with weighting
  const dataset = buildProgressDataset({
    timeColumns: this.state.timeColumns,
    stateManager: stateManager,
    volumeLookup: this._buildVolumeLookup(),
    hargaLookup: this._buildHargaLookup(),
    totalBiayaProject: this.state.totalBiayaProject,
  });

  if (!dataset) {
    return { planned: [], actual: [] };
  }

  return {
    planned: dataset.details || [],  // ✅ Weighted cumulative
    actual: dataset.details || [],
  };
}
```

**Impact:** 🔴 **CRITICAL**
- **Incorrect curve calculation** (simple average vs weighted)
- Small tasks weighted same as large tasks ✗
- Does not match backend API calculation ✗
- Violates consistency report claims ✗

**Status:** ❌ **NOT IMPLEMENTED** (Gap: 100%)

---

### Gap #5: Cost Mode Integration 🔴 CRITICAL

**Roadmap Claim:**
> "Cost mode uses api_kurva_s_harga_data with EVM metrics, integrated with overlay"

**Reality:**
```javascript
// ❌ CURRENT STATE: No cost mode in overlay
// KurvaSCanvasOverlay.js has NO cost mode support
// UnifiedTableManager._buildCurveData() only handles progress mode

// ❌ jadwal_kegiatan_app.js still uses OLD uPlot chart for cost mode
```

**Investigation Needed:**
```javascript
// detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js
// Search for: kurvaSChart, toggleProgressCost, btn-harga, btn-progress
```

**Problems:**
1. ❌ `KurvaSCanvasOverlay` has NO cost mode implementation
2. ❌ No `buildCostDataset()` integration
3. ❌ No API `/kurva-s-harga/` fetch
4. ❌ Old `uPlot` chart still active for cost toggle
5. ❌ **Two separate systems** (overlay for progress, uPlot for cost) → conflict risk

**Expected (Per Roadmap):**
```javascript
// ✅ SHOULD BE (Unified Cost/Progress Toggle)
class KurvaSCanvasOverlay {
  setMode(mode) {
    this.mode = mode;  // 'progress' or 'cost'

    if (mode === 'cost') {
      // Fetch cost data from API
      this._fetchCostData().then(costData => {
        const dataset = buildCostDataset(costData);
        this.renderCurve(dataset);
      });
    } else {
      // Use grid data (progress mode)
      const dataset = buildProgressDataset(this.state);
      this.renderCurve(dataset);
    }
  }

  async _fetchCostData() {
    const response = await fetch(`/detail-project/api/v2/project/${this.projectId}/kurva-s-harga/`);
    return await response.json();
  }
}
```

**Impact:** 🔴 **CRITICAL**
- Cost mode NOT integrated with new overlay ✗
- Two chart systems active (confusion, conflicts) ✗
- API integration missing ✗
- User requirement not met ✗

**Status:** ❌ **NOT IMPLEMENTED** (Gap: 100%)

---

### Gap #6: Scroll Event Handling 🟡 HIGH

**Roadmap Claim:**
> "Phase 1: Immediate _updateTransform() with RAF throttling for smooth 60fps scroll"

**Reality (KurvaSCanvasOverlay.js:54-58):**
```javascript
// ❌ CURRENT IMPLEMENTATION (NO THROTTLING)
scrollTarget.addEventListener('scroll', () => {
  if (this.visible) {
    this.syncWithTable();  // ❌ Heavy operation on EVERY scroll event!
  }
}, { passive: true });
```

**Problems:**
1. ❌ Calls `syncWithTable()` on EVERY scroll event (10-50ms operation!)
2. ❌ No `requestAnimationFrame` throttling
3. ❌ No `_updateTransform()` lightweight method
4. ❌ Frame drops during fast scroll

**Expected (Per Roadmap Phase 1):**
```javascript
// ✅ SHOULD BE (RAF Throttling)
this._syncScheduled = false;

scrollTarget.addEventListener('scroll', () => {
  if (this.visible) {
    // Immediate transform update (<1ms)
    this._updateTransform();

    // Throttle heavy re-render (60fps max)
    if (!this._syncScheduled) {
      this._syncScheduled = true;
      requestAnimationFrame(() => {
        this._syncScheduled = false;
        this.syncWithTable();  // Full re-render (throttled)
      });
    }
  }
}, { passive: true });

_updateTransform() {
  const scrollArea = this.tableManager?.bodyScroll;
  if (!scrollArea) return;

  this.scrollLeft = scrollArea.scrollLeft || 0;
  this.canvas.style.transform = `translateX(${this.scrollLeft}px)`;
  // <1ms - GPU accelerated
}
```

**Impact:** 🟡 **HIGH**
- Poor scroll performance (frame drops) ✗
- Not GPU-accelerated ✗
- Heavy operation on every scroll ✗

**Status:** ❌ **NOT IMPLEMENTED** (Gap: 100%)

---

## 📊 Gap Summary Matrix

| Gap | Roadmap Claim | Reality | Impact | Status | Gap % |
|-----|---------------|---------|--------|--------|-------|
| **#1: Canvas Architecture** | Viewport-sized, transform compensation | Full scrollWidth, left: 0, no transform | 🔴 CRITICAL | ❌ Not Implemented | 100% |
| **#2: Coordinate System** | Canvas-relative, grid lines, X=0 at boundary | Absolute, column centers, X=0 at edge | 🔴 CRITICAL | ❌ Not Implemented | 100% |
| **#3: Y-Axis Positioning** | Fixed to viewport right | Absolute in scrollArea (scrolls) | 🟡 HIGH | ❌ Not Implemented | 100% |
| **#4: Data Pipeline** | dataset-builder.js with volume/harga weighting | Simple average in UnifiedTableManager | 🔴 CRITICAL | ❌ Not Implemented | 100% |
| **#5: Cost Mode** | API integration, EVM metrics, overlay unified | No cost mode, separate uPlot chart | 🔴 CRITICAL | ❌ Not Implemented | 100% |
| **#6: Scroll Handling** | RAF throttling, _updateTransform | syncWithTable on every scroll | 🟡 HIGH | ❌ Not Implemented | 100% |

**Overall Gap:** ❌ **100% of roadmap Phase 1-3 fixes NOT implemented**

---

## 🔴 Root Cause Analysis

### Why Did This Happen?

**1. Documentation Created Before Implementation** ✗
- Roadmap written as "plan" but marked as "complete"
- Consistency report claimed "100% ready" without code verification
- Gap between "design" and "reality"

**2. Overlay Created Before Roadmap** ✗
- `KurvaSCanvasOverlay.js` created earlier (legacy approach)
- Roadmap written later (improved approach)
- Code NOT updated to match roadmap

**3. Multiple Data Pipelines** ✗
- UnifiedTableManager has its own `_buildCurveData()`
- dataset-builder.js exists but not used
- Confusion about which pipeline to use

**4. Incomplete Migration** ✗
- Old uPlot chart still active for cost mode
- New overlay only partial (progress mode only)
- Two systems coexisting

---

## ✅ Corrective Action Plan

### Strategy Options

**Option A: Implement Roadmap (Full Fix)** ← **RECOMMENDED**
- ✅ Implement Phase 1-3 fixes in `KurvaSCanvasOverlay.js`
- ✅ Integrate `dataset-builder.js` for data pipeline
- ✅ Add cost mode support with API integration
- ✅ Deprecate old uPlot chart
- **Effort:** 3-4 hours (Phase 1: 30min, Phase 2: 45min, Phase 3: 30min, Cost Mode: 1.5h, Testing: 30min)
- **Risk:** Low (proven patterns from Gantt)
- **Benefit:** Fully working, consistent, maintainable

**Option B: Update Roadmap to Match Reality** ← **NOT RECOMMENDED**
- ✗ Update roadmap to reflect current simple implementation
- ✗ Keep simple average calculation
- ✗ Accept current limitations
- **Effort:** 1 hour (documentation only)
- **Risk:** Medium (technical debt remains)
- **Benefit:** Low (doesn't solve fundamental issues)

**Option C: Hybrid Approach** ← **COMPROMISE**
- ✅ Fix critical issues only (#1 Canvas, #2 Coordinates, #4 Data)
- ⚠️ Defer cost mode to later phase
- ⚠️ Keep current Y-axis positioning (document as known limitation)
- **Effort:** 2 hours
- **Risk:** Medium (partial fix)
- **Benefit:** Medium (core issues fixed, some deferred)

**RECOMMENDATION:** ✅ **Option A (Full Fix)**

**Reasoning:**
1. Proven patterns already exist (Gantt fixes)
2. Total effort reasonable (3-4 hours)
3. Eliminates all technical debt
4. Meets all user requirements
5. Avoids future confusion

---

## 📋 Action Plan: Option A (Full Implementation)

### Phase 1: Canvas Architecture Fix (30 min) 🔴 CRITICAL

**File:** `KurvaSCanvasOverlay.js`

**Tasks:**
1. Add scroll tracking to constructor
2. Add `_updatePinnedWidth()` method
3. Update `syncWithTable()` with viewport sizing & transform
4. Add `_updateTransform()` method
5. Update scroll handler with RAF throttling

**Code Changes:**

```javascript
// Constructor - Add tracking
constructor(tableManager) {
  // ... existing ...
  this.scrollLeft = 0;
  this._syncScheduled = false;
  this.pinnedWidth = 0;
}

// New method: Get pinned width
_getPinnedWidth() {
  const pinnedCols = this.tableManager?.getPinnedColumnsWidth?.();
  return Math.max(0, pinnedCols || 0);
}

// Updated: syncWithTable
syncWithTable() {
  const scrollArea = this.tableManager?.bodyScroll;
  if (!scrollArea) return;

  // Update pinned width and scroll position
  this.pinnedWidth = this._getPinnedWidth();
  this.scrollLeft = scrollArea.scrollLeft || 0;

  // Viewport-sized canvas
  const viewportWidth = scrollArea.clientWidth - this.pinnedWidth;
  const MAX_CANVAS_WIDTH = 32000;

  this.canvas.width = Math.min(viewportWidth, MAX_CANVAS_WIDTH);
  this.canvas.height = Math.min(scrollArea.scrollHeight, 16000);
  this.yAxisCanvas.height = this.canvas.height;

  // Transform compensation
  this.canvas.style.position = 'absolute';
  this.canvas.style.left = `${this.pinnedWidth}px`;
  this.canvas.style.top = '0px';
  this.canvas.style.transform = `translateX(${this.scrollLeft}px)`;

  // ... rest of method (clear, draw) ...
}

// New method: Immediate transform update
_updateTransform() {
  const scrollArea = this.tableManager?.bodyScroll;
  if (!scrollArea) return;

  this.scrollLeft = scrollArea.scrollLeft || 0;
  this.canvas.style.transform = `translateX(${this.scrollLeft}px)`;
}

// Updated: Scroll handler (in constructor)
scrollTarget.addEventListener('scroll', () => {
  if (this.visible) {
    // Immediate transform
    this._updateTransform();

    // Throttled full sync
    if (!this._syncScheduled) {
      this._syncScheduled = true;
      requestAnimationFrame(() => {
        this._syncScheduled = false;
        this.syncWithTable();
      });
    }
  }
}, { passive: true });
```

**Success Criteria:**
- ✅ Canvas width < 32,000px
- ✅ Canvas starts at `pinnedWidth`
- ✅ Transform applied: `translateX(scrollLeft)`
- ✅ No overlap with frozen column
- ✅ Smooth scroll (60fps)

---

### Phase 2: Coordinate System Fix (45 min) 🔴 CRITICAL

**File:** `KurvaSCanvasOverlay.js`

**Tasks:**
1. Rename `_getWeekColumnCenters()` → `_getWeekGridLines()`
2. Update to use column **right edge** (not center)
3. Subtract `pinnedWidth` and `scrollLeft` for canvas-relative coords
4. Add X=0 at frozen boundary

**Code Changes:**

```javascript
// Renamed & Updated method
_getWeekGridLines(cellRects) {
  const gridLines = new Map();

  // Special: X=0 at frozen boundary
  gridLines.set('0', 0);

  cellRects.forEach((rect) => {
    const columnId = String(rect.columnId);
    if (!gridLines.has(columnId)) {
      // Grid line = right edge of column
      const absoluteGridLineX = rect.x + rect.width;

      // Canvas-relative coordinates
      const canvasGridLineX = absoluteGridLineX - this.pinnedWidth - this.scrollLeft;

      gridLines.set(columnId, canvasGridLineX);
    }
  });

  console.log('[KurvaSOverlay] Grid lines (canvas-relative):', Array.from(gridLines.entries()).slice(0, 3));
  return gridLines;
}

// Updated: _mapDataToCanvasPoints
_mapDataToCanvasPoints(cellRects, dataPoints) {
  const points = [];
  const tableHeight = this.canvas.height;
  const y0percent = tableHeight - 40;
  const y100percent = 40;

  // Get grid lines (NOT column centers)
  const gridLines = this._getWeekGridLines(cellRects);

  dataPoints.forEach((dataPoint) => {
    const columnId = dataPoint.columnId || dataPoint.weekId || dataPoint.week;
    const progress = Number.isFinite(dataPoint.cumulativeProgress)
      ? dataPoint.cumulativeProgress
      : dataPoint.progress || 0;

    // Find X position on grid line
    const gridLineX = gridLines.get(String(columnId));
    if (!Number.isFinite(gridLineX)) {
      return;
    }

    const y = this._interpolateY(progress, y0percent, y100percent);

    points.push({
      x: gridLineX,  // ✅ Canvas-relative, on grid line
      y: y,
      columnId: columnId,
      progress: progress,
      weekNumber: dataPoint.weekNumber,
      weekProgress: dataPoint.weekProgress,
    });
  });

  return points;
}
```

**Success Criteria:**
- ✅ X=0 at frozen boundary
- ✅ Nodes on grid lines (column right edge)
- ✅ Coordinates canvas-relative
- ✅ Scroll compensation included

---

### Phase 3: Data Pipeline Integration (1 hour) 🔴 CRITICAL

**File:** `UnifiedTableManager.js`

**Tasks:**
1. Import `dataset-builder.js` functions
2. Replace `_calculateCumulativeProgress()` with `buildProgressDataset()`
3. Add volume/harga lookup building
4. Update `_buildCurveData()` to use new pipeline

**Code Changes:**

```javascript
// At top of file
import { buildProgressDataset, buildCostDataset } from '../kurva-s/dataset-builder.js';

// Replace entire _buildCurveData method
_buildCurveData(payload = {}) {
  const stateManager = this.state?.stateManager || this.options?.stateManager;

  // Build dataset using dataset-builder.js
  const dataset = buildProgressDataset({
    timeColumns: this.state?.timeColumns || [],
    stateManager: stateManager,
    volumeLookup: this._buildVolumeLookup(),
    hargaLookup: this._buildHargaLookup(),
    totalBiayaProject: this.state?.totalBiayaProject,
    plannedState: this.state,
    actualState: this.state,
  });

  if (!dataset || !dataset.details) {
    this._log('buildCurveData:noDataset');
    return { planned: [], actual: [] };
  }

  // Map dataset.details to curve format
  const planned = dataset.details.map(detail => ({
    columnId: detail.metadata?.id || detail.metadata?.fieldId,
    weekNumber: detail.metadata?.weekNumber,
    cumulativeProgress: detail.planned,
    weekProgress: detail.metadata?.plannedWeekProgress || 0,
  }));

  const actual = dataset.details.map(detail => ({
    columnId: detail.metadata?.id || detail.metadata?.fieldId,
    weekNumber: detail.metadata?.weekNumber,
    cumulativeProgress: detail.actual,
    weekProgress: detail.metadata?.actualWeekProgress || 0,
  }));

  this._log('buildCurveData:success', {
    planned: planned.length,
    actual: actual.length,
    useHarga: dataset.useHargaCalculation,
  });

  return { planned, actual };
}

// New method: Build volume lookup
_buildVolumeLookup() {
  const lookup = new Map();
  const rows = this.state?.tree || [];

  const traverse = (nodes) => {
    nodes.forEach(node => {
      const volume = node.raw?.volume || node.volume || 1;
      lookup.set(String(node.id), parseFloat(volume) || 1);

      if (node.subRows) traverse(node.subRows);
    });
  };

  traverse(rows);
  return lookup;
}

// New method: Build harga lookup
_buildHargaLookup() {
  const lookup = new Map();
  const hargaMap = this.state?.hargaMap || new Map();

  hargaMap.forEach((harga, pekerjaanId) => {
    lookup.set(String(pekerjaanId), parseFloat(harga) || 0);
  });

  return lookup;
}

// DELETE old method
// _calculateCumulativeProgress() { ... }  ← DELETE THIS
```

**Success Criteria:**
- ✅ Uses `buildProgressDataset()` from dataset-builder.js
- ✅ Volume/harga weighting applied
- ✅ Matches backend calculation logic
- ✅ No simple average calculation

---

### Phase 4: Cost Mode Integration (1.5 hours) 🔴 CRITICAL

**Files:** `KurvaSCanvasOverlay.js`, `UnifiedTableManager.js`, `jadwal_kegiatan_app.js`

**Tasks:**
1. Add cost mode support to `KurvaSCanvasOverlay`
2. Add API fetch method
3. Update `UnifiedTableManager` to handle cost mode
4. Deprecate old uPlot chart
5. Wire up cost/progress toggle

**Code Changes (KurvaSCanvasOverlay.js):**

```javascript
// Add to constructor
constructor(tableManager, options = {}) {
  // ... existing ...
  this.mode = 'progress';  // 'progress' or 'cost'
  this.projectId = options.projectId || null;
}

// New method: Set mode
async setMode(mode) {
  if (this.mode === mode) return;
  this.mode = mode;

  console.log('[KurvaSOverlay] Switching to mode:', mode);

  if (mode === 'cost') {
    await this._loadCostMode();
  } else {
    this._loadProgressMode();
  }
}

// New method: Load cost mode
async _loadCostMode() {
  if (!this.projectId) {
    console.error('[KurvaSOverlay] No projectId for cost mode');
    return;
  }

  try {
    const response = await fetch(
      `/detail-project/api/v2/project/${this.projectId}/kurva-s-harga/`,
      { credentials: 'include' }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const costData = await response.json();
    const dataset = buildCostDataset(costData);

    if (!dataset || !dataset.details) {
      console.error('[KurvaSOverlay] Invalid cost dataset');
      return;
    }

    // Map to curve format
    const planned = dataset.details.weeklySummary.map(week => ({
      columnId: week.weekNumber,
      weekNumber: week.weekNumber,
      cumulativeProgress: week.plannedPercent,
      weekProgress: week.plannedPercent,
    }));

    const actual = dataset.details.weeklySummary.map(week => ({
      columnId: week.weekNumber,
      weekNumber: week.weekNumber,
      cumulativeProgress: week.actualPercent,
      weekProgress: week.actualPercent,
    }));

    this.renderCurve({ planned, actual });

    console.log('[KurvaSOverlay] Cost mode loaded:', {
      plannedPoints: planned.length,
      actualPoints: actual.length,
      totalCost: dataset.totalBiaya,
    });

  } catch (error) {
    console.error('[KurvaSOverlay] Failed to load cost mode:', error);
  }
}

// New method: Load progress mode
_loadProgressMode() {
  // Trigger refresh from UnifiedTableManager
  if (typeof this.tableManager?._refreshKurvaSOverlay === 'function') {
    this.tableManager._refreshKurvaSOverlay();
  }
}
```

**Code Changes (UnifiedTableManager.js):**

```javascript
// Update _refreshKurvaSOverlay to check mode
_refreshKurvaSOverlay(payload = {}) {
  if (!this.overlays.kurva || !this.tanstackGrid) return;

  // Only build progress data if in progress mode
  if (this.overlays.kurva.mode === 'progress') {
    const curveData = this._buildCurveData(payload);
    this.overlays.kurva.renderCurve(curveData);
  }
  // For cost mode, overlay fetches its own data
}
```

**Code Changes (jadwal_kegiatan_app.js):**

```javascript
// Find cost/progress toggle handler and update
const toggleCostProgress = document.getElementById('toggle-cost-progress');
if (toggleCostProgress) {
  toggleCostProgress.addEventListener('click', async (e) => {
    const mode = e.target.dataset.mode;  // 'progress' or 'cost'

    // Update overlay mode (NEW)
    if (unifiedManager?.overlays?.kurva) {
      await unifiedManager.overlays.kurva.setMode(mode);
    }

    // Deprecate old uPlot chart
    // if (kurvaSChart) {
    //   kurvaSChart.hide();  // Hide old chart
    // }

    // Update button states
    document.querySelectorAll('[data-mode]').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.mode === mode);
    });
  });
}
```

**Success Criteria:**
- ✅ Cost mode fetches from `/kurva-s-harga/` API
- ✅ Uses `buildCostDataset()` from dataset-builder.js
- ✅ Toggle switches between progress/cost in overlay
- ✅ Old uPlot chart deprecated
- ✅ Single unified system

---

### Phase 5: Testing & Validation (30 min)

**Manual Tests:**

**Test 1: Canvas Architecture**
- [ ] Canvas width < 32,000px (check in DevTools)
- [ ] Canvas left = pinnedWidth (e.g., 300px)
- [ ] Transform visible: `translateX(scrollLeft)`
- [ ] No overlap with frozen column
- [ ] Smooth scroll (no lag)

**Test 2: Coordinate System**
- [ ] First node at frozen boundary grid line
- [ ] Subsequent nodes on vertical grid lines (column right edges)
- [ ] Nodes stay aligned during scroll
- [ ] X coordinates adjust with scroll

**Test 3: Data Pipeline**
- [ ] Curve weighted by volume/harga (not simple average)
- [ ] Large tasks contribute more than small tasks
- [ ] Cumulative progress reaches 100% at end

**Test 4: Cost Mode**
- [ ] Click "Cost" toggle
- [ ] Curve switches to cost data from API
- [ ] EVM metrics available (PV, EV, AC)
- [ ] Click "Progress" toggle → switches back
- [ ] No errors in console

**Test 5: Performance**
- [ ] Fast horizontal scroll → no visual lag
- [ ] No console errors
- [ ] Frame rate stays ~60fps (check DevTools Performance)

---

## 📅 Implementation Timeline

| Phase | Duration | Priority | Status |
|-------|----------|----------|--------|
| **Phase 1:** Canvas Architecture Fix | 30 min | 🔴 CRITICAL | 📋 Pending |
| **Phase 2:** Coordinate System Fix | 45 min | 🔴 CRITICAL | 📋 Pending |
| **Phase 3:** Data Pipeline Integration | 1 hour | 🔴 CRITICAL | 📋 Pending |
| **Phase 4:** Cost Mode Integration | 1.5 hours | 🔴 CRITICAL | 📋 Pending |
| **Phase 5:** Testing & Validation | 30 min | 🟡 HIGH | 📋 Pending |
| **Total** | **~4 hours** | - | **0% Complete** |

---

## 📝 Documentation Updates Required

After implementation complete, update:

1. **KURVA_S_ROADMAP_CONSISTENCY_REPORT.md**
   - Change status from "100% ready" to "Implementation Complete"
   - Add actual implementation dates
   - Update "Reality" sections with new code

2. **KURVA_S_IMPLEMENTATION_ROADMAP.md**
   - Mark Phase 1-3 as ✅ Complete
   - Add Phase 4 (Cost Mode) completion
   - Add actual duration vs estimated

3. **Create KURVA_S_IMPLEMENTATION_COMPLETE.md**
   - Summarize all changes made
   - Before/after code comparisons
   - Test results
   - Performance metrics

---

## ✅ Success Criteria

### Functional
- [ ] Curve does NOT overlap frozen column at any scroll position
- [ ] Nodes positioned on grid lines (column right edges)
- [ ] X=0 at frozen/scrollable boundary
- [ ] Curve weighted by volume/harga (not simple average)
- [ ] Cost mode integrated (API + dataset-builder.js)
- [ ] Smooth scroll performance (60fps)

### Technical
- [ ] Canvas width < 32,000px (viewport-sized)
- [ ] Transform compensation applied
- [ ] Canvas-relative coordinates
- [ ] RAF throttling for scroll
- [ ] dataset-builder.js used for data pipeline
- [ ] Old uPlot chart deprecated

### User Experience
- [ ] Curve appears immediately on mode switch
- [ ] No visual lag during scroll
- [ ] Cost/Progress toggle works seamlessly
- [ ] No console errors
- [ ] Matches user requirements (grid lines, X=0 at boundary)

---

## 🚨 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Integration breaks existing code** | 🟡 Medium | 🔴 High | Test thoroughly, keep old uPlot as fallback initially |
| **Cost API returns unexpected format** | 🟢 Low | 🟡 Medium | Add error handling, fallback to progress mode |
| **Performance regression** | 🟢 Low | 🟡 Medium | Use proven patterns from Gantt, benchmark before/after |
| **Coordinate calculation errors** | 🟡 Medium | 🔴 High | Extensive manual testing, compare with Gantt reference |
| **Dataset-builder.js incompatibility** | 🟢 Low | 🟡 Medium | Already used in other modules, well-tested |

**Overall Risk:** 🟡 **MEDIUM** (mitigated by proven patterns and incremental approach)

---

## 📞 Approval & Next Steps

**Status:** ⏸️ **AWAITING USER APPROVAL**

**Questions for User:**

1. **Approve Option A (Full Fix)?**
   - ✅ Yes → Proceed with 4-hour implementation
   - ❌ No → Choose Option B or C

2. **Priority for Cost Mode?**
   - 🔴 High → Include in current sprint (Phase 4)
   - 🟡 Medium → Defer to next sprint
   - 🟢 Low → Keep old uPlot for now

3. **Testing Support?**
   - Can user test during implementation (incremental)?
   - Or test after all phases complete?

**Next Action:**
- User reviews this gap analysis
- User approves action plan (Option A/B/C)
- Implementation begins immediately after approval

---

**Report Prepared By:** Claude Code
**Date:** 2025-12-12
**Audit Source:** User feedback
**Status:** 🔴 **GAPS IDENTIFIED - ACTION PLAN READY**
