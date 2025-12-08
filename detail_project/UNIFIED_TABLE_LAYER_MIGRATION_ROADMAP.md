# Unified Table Layer Migration Roadmap
## Jadwal Pekerjaan Page - Grid/Gantt/Kurva-S Architecture Consolidation

**Document Version:** 1.0
**Created:** 2025-12-05
**Project Scope:** Migrate 3 separate mode implementations to unified table layer
**Timeline:** 10 days
**Status:** Planning Phase (Baseline refreshed 2025-12-05)

### Baseline Update (per 2025-12-05)
- Legacy AG-Grid/ECharts/Frappe dependencies sudah dibersihkan dari template & bundle; hanya TanStack Grid + Gantt V2 (canvas) + uPlot yang aktif.
- TanStack Grid sudah mendukung frozen columns, keyboard navigation, validation border, auto-edit on digit, null/0 → “-”, klasifikasi/sub-klasifikasi read-only, dan over-limit warning dengan border merah.
- Gantt V2 (frozen column) tetap berjalan mandiri; Kurva-S memakai uPlot cost/progress toggle dengan variance.
- StateManager sinkronisasi antar-mode sudah stabil; tab switching saat ini merender ulang per mode (target pengurangan di roadmap ini).
- Safety guard: Unified layer akan dilakukan inkremental (renderer swap + overlay), tanpa menghapus Gantt V2 sampai parity tercapai dan checklist lulus.

### Progress Update (2025-12-05)
- ✅ Satu instance `UnifiedTableManager` dipakai lintas tab (Grid/Gantt/Kurva); `unifiedGanttManager` dihapus untuk menghindari double-mount dan duplikasi state.
- ✅ Host TanStack grid kini dipindahkan antar-tab saat masuk/keluar Gantt, lalu dikembalikan ke parent asal agar scroll/expand/focus tetap konsisten.
- ✅ `_renderGrid()` kini memicu `_syncGridViews()` juga pada unified mode sehingga refresh pasca-save/time-scale change turut memperbarui overlay.
- ✅ Gantt overlay membaca nilai dari `StateManager.getAllCellsForMode()` (termasuk `modifiedCells` planned/actual) sehingga bar/variance akurat sebelum commit.
- 🔄 QA checklist belum dijalankan pasca perubahan ini; perlu smoke test tab switch + overlay alignment.

---

## Executive Summary

### Vision
Consolidate Grid, Gantt V2, and Kurva-S modes into a **single unified TanStack table layer** with mode-specific overlays. This architecture eliminates redundant rendering, reduces memory overhead, and provides seamless tab switching while preserving 100% feature parity.

### Feature Preservation Guarantee

**CRITICAL REQUIREMENT:** All existing features MUST remain functional throughout migration.

✅ **Zero Feature Regression Policy**
- Every feature from current Grid, Gantt V2, and Kurva-S implementations will be preserved
- Incremental migration with validation checkpoints after each phase
- Rollback procedures in place for each phase
- Feature parity matrix verification (see Section 4)

### Key Benefits

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Tab Switch Time | 330ms | <50ms | **85% faster** |
| Memory Usage | ~100 MB | ~60 MB | **-40%** |
| Bundle Size | 272 KB | 260 KB | **-12 KB** |
| Code Complexity | 3 implementations | 1 unified layer | **40% reduction** |
| Maintenance | High duplication | Single source of truth | **3x easier** |

---

## Part 1: Current vs Proposed Architecture

### Current Architecture (3 Separate Implementations)

```
┌─────────────────────────────────────────────────────────┐
│                  Jadwal Kegiatan App                    │
└────────┬─────────────────┬──────────────────┬───────────┘
         │                 │                  │
    ┌────▼─────┐     ┌─────▼──────┐    ┌─────▼──────┐
    │  Grid    │     │  Gantt V2  │    │  Kurva-S   │
    │  Mode    │     │   Mode     │    │   Mode     │
    └────┬─────┘     └─────┬──────┘    └─────┬──────┘
         │                 │                  │
    ┌────▼─────┐     ┌─────▼──────┐    ┌─────▼──────┐
    │ TanStack │     │ Canvas +   │    │  TanStack  │
    │  Grid    │     │ Frozen Grid│    │ + uPlot    │
    │ (813 LOC)│     │ (14 KB)    │    │ (516 LOC)  │
    └──────────┘     └────────────┘    └────────────┘

PROBLEM: Tree structure, columns, and data are IDENTICAL
         → 3x rendering overhead on tab switch
         → State sync complexity (scroll, tree expansion)
         → Memory duplication
```

**Issues:**
1. **Redundant Rendering**: Switching tabs destroys and re-creates entire table (330ms)
2. **Memory Overhead**: 3 instances of tree structure + column definitions (~100 MB)
3. **State Sync Complexity**: Manually sync scroll position, tree expansion, cell focus
4. **Code Duplication**: Similar logic in 3 files (grid manager, gantt frozen grid, kurva grid)

### Proposed Architecture (Unified Table Layer)

```
┌─────────────────────────────────────────────────────────┐
│              Unified Table Manager                      │
│  (Single TanStack Grid Instance - Persistent)           │
└────────┬────────────────────────────────────────────────┘
         │
    ┌────▼──────────────────────────────────────┐
    │   Mode-Specific Cell Renderer Factory     │
    │   ┌─────────┬──────────┬──────────┐      │
    │   │  Input  │  Gantt   │ Readonly │      │
    │   │  Mode   │  Cell    │  Mode    │      │
    │   └─────────┴──────────┴──────────┘      │
    └───────────────────────────────────────────┘
         │              │              │
    ┌────▼────┐    ┌────▼────┐   ┌────▼────┐
    │  Grid   │    │ Canvas  │   │ Kurva-S │
    │  View   │    │ Overlay │   │  Panel  │
    │         │    │ (Gantt) │   │ (uPlot) │
    └─────────┘    └─────────┘   └─────────┘

SOLUTION: One table, three presentation layers
          → Zero re-render on tab switch (<50ms)
          → Single source of truth for state
          → -40% memory, -12 KB bundle
```

**Advantages:**
1. **Zero Re-render**: Table persists, only overlay visibility changes
2. **Unified State**: Tree expansion, scroll, focus automatically preserved
3. **Memory Efficiency**: Single DOM tree structure (~60 MB)
4. **Simplified Maintenance**: One table implementation to maintain

---

## Part 2: Feature Parity Matrix

### Grid Mode Features (100% Preservation)

| Feature | Current Implementation | Unified Layer Implementation | Status |
|---------|------------------------|------------------------------|--------|
| Virtual Scrolling | TanStack Virtual (overscan:8) | ✅ Same implementation | Preserved |
| Tree Expand/Collapse | `_renderTreeCell()` | ✅ Same implementation | Preserved |
| Inline Editing | Input cells with validation | ✅ `InputCellRenderer` | Preserved |
| Tab/Enter Navigation | Keyboard handler | ✅ Same handler | Preserved |
| Auto-edit on Digit | Keypress detection | ✅ Same logic | Preserved |
| Validation Border | Red border on over-limit | ✅ Same CSS class | Preserved |
| Null/0 Display | Show as "-" | ✅ Same formatter | Preserved |
| Read-only Cells | Klasifikasi/sub-klasifikasi | ✅ Same logic | Preserved |
| Column Pinning | Left-frozen columns | ✅ Same implementation | Preserved |
| Scroll Sync | Header-body sync | ✅ Same sync logic | Preserved |

**Verification Method**: Visual regression testing + E2E tests for each feature.

### Gantt V2 Mode Features (100% Preservation)

| Feature | Current Implementation | Unified Layer Implementation | Status |
|---------|------------------------|------------------------------|--------|
| Progress Bars | Canvas bar rendering | ✅ `GanttCanvasOverlay.drawBar()` | Preserved |
| Dependency Lines | Canvas arrows | ✅ `GanttCanvasOverlay.drawDependencies()` | Preserved |
| Drag-to-Resize | Mouse event on bars | ✅ Canvas interaction layer | Preserved |
| Color by Status | Status-based fill color | ✅ Same color logic | Preserved |
| Hover Tooltip | Bar metadata popup | ✅ Canvas mouse events | Preserved |
| Tree Hierarchy | Nested pekerjaan | ✅ Same tree structure | Preserved |
| Week Column Alignment | Cell-bar sync | ✅ `getCellBoundingRects()` sync | Enhanced |

**Verification Method**: Gantt feature parity checklist (Day 7) + visual comparison.

### Kurva-S Mode Features (100% Preservation)

| Feature | Current Implementation | Unified Layer Implementation | Status |
|---------|------------------------|------------------------------|--------|
| uPlot Chart | Standalone chart component | ✅ Same component, side panel | Preserved |
| Cost/Progress Toggle | `toggleView()` method | ✅ Same method | Preserved |
| Variance Color | Red/green deviation | ✅ Same color logic | Preserved |
| Zoom/Pan | Wheel interaction | ✅ Same interaction | Preserved |
| Rupiah Tooltip | Currency formatter | ✅ Same formatter | Preserved |
| Weekly Summary | Data aggregation | ✅ Same aggregation | Preserved |
| Date Formatting | dd/mm-dd/mm range | ✅ Same formatter | Preserved |

**Verification Method**: Chart rendering comparison + data accuracy validation.

### Cross-Mode Features (100% Preservation)

| Feature | Current Implementation | Unified Layer Implementation | Status |
|---------|------------------------|------------------------------|--------|
| State Sync | StateManager event bus | ✅ Same event bus | Preserved |
| Export Excel | Grid data serialization | ✅ Same serialization | Preserved |
| Undo/Redo | StateManager stack | ✅ Same stack | Preserved |
| Bulk Edit | Multi-cell update | ✅ Same logic | Preserved |
| Search/Filter | Row filtering | ✅ Same filtering | Preserved |

---

## Part 3: Detailed 10-Day Implementation Plan

### Phase 1: Proof of Concept (Days 1-3)

#### **Day 1: Cell Renderer Abstraction**

**Goal**: Extract cell rendering logic into pluggable renderers without breaking existing Grid mode.

**Status (done):** Factory + renderer skeletons sudah ditambahkan. `tanstack-grid-manager.js` kini memiliki `setCellRenderer(mode)` dan `_renderTimeCell` mendelegasikan ke renderer, dengan `_renderTimeCellLegacy` menjaga perilaku lama. Renderer yang tersedia: `InputCellRenderer`, `GanttCellRenderer`, `ReadonlyCellRenderer` (masih reuse legacy render untuk menjaga no-regression).

**Tasks:**
1. Create `CellRendererFactory.js` with base renderer interface
2. Extract input cell logic to `InputCellRenderer.js`
3. Create `GanttCellRenderer.js` (simplified, no interaction yet)
4. Create `ReadonlyCellRenderer.js` for Kurva-S mode
5. Add `setCellRenderer()` method to `TanStackGridManager`

**Files to Create:**
- `detail_project/static/detail_project/js/src/modules/grid/renderers/CellRendererFactory.js`
- `detail_project/static/detail_project/js/src/modules/grid/renderers/InputCellRenderer.js`
- `detail_project/static/detail_project/js/src/modules/grid/renderers/GanttCellRenderer.js`
- `detail_project/static/detail_project/js/src/modules/grid/renderers/ReadonlyCellRenderer.js`

**Files to Modify:**
- `detail_project/static/detail_project/js/src/modules/grid/tanstack-grid-manager.js`:
  - Import `CellRendererFactory`
  - Replace `_renderTimeCell()` logic with `this.cellRenderer.render(cell, data)`
  - Add `setCellRenderer(mode)` method

**Code Example:**
```javascript
// CellRendererFactory.js
export class CellRendererFactory {
  static create(mode) {
    switch (mode) {
      case 'input': return new InputCellRenderer();
      case 'gantt-cell': return new GanttCellRenderer();
      case 'readonly': return new ReadonlyCellRenderer();
      default: throw new Error(`Unknown renderer mode: ${mode}`);
    }
  }
}

// tanstack-grid-manager.js - NEW METHOD
setCellRenderer(mode) {
  this.cellRenderer = CellRendererFactory.create(mode);
  this._renderRowsOnly(); // Re-render cells without tree rebuild
}
```

**Validation Checkpoint:**
- [ ] Grid mode still works with `InputCellRenderer`
- [ ] No visual/functional regressions in editing
- [ ] Tab/Enter navigation still works
- [ ] Validation borders still appear
- [x] Renderer delegasi aktif dan memakai legacy render (no regression)

**Rollback**: Revert `tanstack-grid-manager.js` changes if checkpoint fails.

---

#### **Day 2: Canvas Overlay Skeleton**

**Goal**: Create canvas overlay infrastructure that positions over table cells.

**Status (done):** `GanttCanvasOverlay.js` dibuat dengan show/hide/sync, menempel ke `bodyScroll` dan menggambar outline sel untuk verifikasi alignment. `tanstack-grid-manager.js` kini menyediakan `getCellBoundingRects()` untuk sinkronisasi posisi. Overlay hanya aktif saat dipanggil dan tidak mengubah perilaku existing grid (pointer-events:none).

**Tasks:**
1. Create `GanttCanvasOverlay.js` with show/hide methods
2. Implement `getCellBoundingRects()` in `TanStackGridManager`
3. Add `syncWithTable()` method for canvas resizing
4. Test canvas positioning accuracy (no bars yet, just grid overlay)

**Files to Create:**
- `detail_project/static/detail_project/js/src/modules/gantt/GanttCanvasOverlay.js`

**Files to Modify:**
- `detail_project/static/detail_project/js/src/modules/grid/tanstack-grid-manager.js`:
  - Add `getCellBoundingRects()` method
  - Add scroll event listener to trigger canvas sync

**Code Example:**
```javascript
// tanstack-grid-manager.js - NEW METHOD
getCellBoundingRects() {
  const rects = [];
  const containerRect = this.bodyScroll.getBoundingClientRect();
  const cells = this.bodyInner.querySelectorAll('.tanstack-grid-cell[data-column-id]');

  cells.forEach(cell => {
    const rect = cell.getBoundingClientRect();
    rects.push({
      pekerjaanId: cell.dataset.pekerjaanId,
      columnId: cell.dataset.columnId,
      x: rect.x - containerRect.x,
      y: rect.y - containerRect.y,
      width: rect.width,
      height: rect.height,
      scrollTop: this.bodyScroll.scrollTop,
      scrollLeft: this.bodyScroll.scrollLeft
    });
  });

  return rects;
}

// GanttCanvasOverlay.js
export class GanttCanvasOverlay {
  constructor(tableManager) {
    this.tableManager = tableManager;
    this.canvas = document.createElement('canvas');
    this.canvas.className = 'gantt-canvas-overlay';
    this.canvas.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      pointer-events: auto;
      z-index: 10;
    `;
    this.ctx = this.canvas.getContext('2d');
    this.visible = false;

    // Sync canvas on scroll
    this.tableManager.bodyScroll.addEventListener('scroll', () => {
      if (this.visible) this.syncWithTable();
    });
  }

  show() {
    if (!this.visible) {
      this.tableManager.bodyScroll.style.position = 'relative';
      this.tableManager.bodyScroll.appendChild(this.canvas);
      this.visible = true;
      this.syncWithTable();
    }
  }

  hide() {
    if (this.visible && this.canvas.parentNode) {
      this.canvas.parentNode.removeChild(this.canvas);
      this.visible = false;
    }
  }

  syncWithTable() {
    const scrollArea = this.tableManager.bodyScroll;
    this.canvas.width = scrollArea.scrollWidth;
    this.canvas.height = scrollArea.scrollHeight;

    // Get cell positions
    const cellRects = this.tableManager.getCellBoundingRects();

    // Clear canvas
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // Draw test grid (for Day 2 validation)
    cellRects.forEach(rect => {
      this.ctx.strokeStyle = '#e2e8f0';
      this.ctx.strokeRect(rect.x, rect.y, rect.width, rect.height);
    });
  }
}
```

**Validation Checkpoint:**
- [ ] Canvas overlays table cells precisely
- [ ] Canvas scrolls with table body
- [ ] No performance degradation during scroll
- [ ] Canvas hides when not in Gantt mode
- [x] Skeleton overlay draws outline grid for alignment check

**Rollback**: Remove canvas overlay files if positioning fails.

---

#### **Day 3: Mode Switching Infrastructure**

**Goal**: Create `UnifiedTableManager` to orchestrate mode switching.

**Status (done - skeleton, not yet wired in app):** `UnifiedTableManager.js` ditambahkan. Ia mem-mount satu instance `TanStackGridManager`, menyediakan `switchMode(mode)` yang mengganti renderer (grid/gantt/readonly) dan menampilkan `GanttCanvasOverlay` tanpa mengubah jadwal_kegiatan_app.js. Kurva overlay disiapkan sebagai placeholder (belum di-wire) untuk menjaga zero-regression.

**Tasks:**
1. Create `UnifiedTableManager.js` with `switchMode()` method
2. Integrate with existing `jadwal_kegiatan_app.js`
3. Test mode switching without breaking tabs
4. Verify tree expansion state persists across modes

**Files to Create:**
- `detail_project/static/detail_project/js/src/modules/unified/UnifiedTableManager.js`

**Files to Modify:**
- `detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js`:
  - Replace separate grid/gantt/kurva instances with `UnifiedTableManager`
  - Update tab click handlers to call `unifiedManager.switchMode(mode)`

**Code Example:**
```javascript
// UnifiedTableManager.js
import { TanStackGridManager } from '../grid/tanstack-grid-manager.js';
import { GanttCanvasOverlay } from '../gantt/GanttCanvasOverlay.js';
import { KurvaSUPlotChart } from '../kurva-s/uplot-chart.js';

export class UnifiedTableManager {
  constructor(state, options) {
    this.state = state;
    this.options = options;
    this.currentMode = 'grid';
    this.tanstackGrid = null;
    this.overlays = {
      gantt: null,
      kurva: null
    };
  }

  mount(container, domTargets) {
    // Mount TanStack grid once
    this.tanstackGrid = new TanStackGridManager(this.state, this.options);
    this.tanstackGrid.mount(container, domTargets);

    // Initialize in grid mode
    this.tanstackGrid.setCellRenderer('input');
  }

  switchMode(newMode) {
    if (newMode === this.currentMode) return;

    const oldMode = this.currentMode;
    this.currentMode = newMode;

    console.log(`[UnifiedTable] Switching: ${oldMode} → ${newMode}`);

    // Hide old overlays
    if (oldMode === 'gantt' && this.overlays.gantt) {
      this.overlays.gantt.hide();
    }
    if (oldMode === 'kurva' && this.overlays.kurva) {
      this.overlays.kurva.hide();
    }

    // Switch cell renderer (NO table re-render)
    const rendererMap = {
      'grid': 'input',
      'gantt': 'gantt-cell',
      'kurva': 'readonly'
    };
    this.tanstackGrid.setCellRenderer(rendererMap[newMode]);

    // Show new overlay
    if (newMode === 'gantt') {
      if (!this.overlays.gantt) {
        this.overlays.gantt = new GanttCanvasOverlay(this.tanstackGrid);
      }
      this.overlays.gantt.show();
    }

    if (newMode === 'kurva') {
      if (!this.overlays.kurva) {
        this.overlays.kurva = this._initKurvaChart();
      }
      this.overlays.kurva.show();
    }
  }

  _initKurvaChart() {
    // Keep existing uPlot chart as side panel
    const chartContainer = document.getElementById('kurva-s-chart-container');
    return new KurvaSUPlotChart(this.state, { container: chartContainer });
  }
}

// jadwal_kegiatan_app.js - UPDATED
import { UnifiedTableManager } from './modules/unified/UnifiedTableManager.js';

// Replace old initialization
const unifiedManager = new UnifiedTableManager(state, options);
unifiedManager.mount(gridContainer, domTargets);

// Update tab handlers
document.querySelectorAll('.mode-tab').forEach(tab => {
  tab.addEventListener('click', (e) => {
    const mode = e.target.dataset.mode; // 'grid' | 'gantt' | 'kurva'
    unifiedManager.switchMode(mode);
  });
});
```

**Validation Checkpoint:**
- [ ] Tab switching works without errors
- [ ] Tree expansion state persists across modes
- [ ] Scroll position preserved on mode switch
- [ ] No memory leaks (check DevTools Memory tab)
- [ ] Mode switch time < 100ms (Day 3 baseline)

**Rollback**: Keep old separate implementations if mode switching breaks.

---

### Phase 2: Gantt Canvas Implementation (Days 4-7)

#### **Day 4: Basic Bar Rendering**

**Goal**: Draw Gantt progress bars aligned with table cells.

**Status (done - skeleton):** Overlay sudah menggambar bar sederhana (warna default) memakai data dari `UnifiedTableManager._buildBarData` yang mengambil nilai progress via `TanStackGridManager.getTimeCellValue()` dan posisi sel dari `getCellBoundingRects()`. Overlay auto-refresh saat `updateData` dan ketika switch ke mode gantt. Pointer-events tetap dimatikan; interaksi/background bar akan diteruskan di fase berikut.

**Tasks:**
1. Implement `_drawBar()` method in `GanttCanvasOverlay`
2. Get progress data from StateManager
3. Render bars with correct width based on progress percentage
4. Add background bar + progress fill

**Files to Modify:**
- `detail_project/static/detail_project/js/src/modules/gantt/GanttCanvasOverlay.js`:
  - Replace test grid with actual bar rendering
  - Add `_getProgressData(pekerjaanId, columnId)` helper
  - Implement `_drawBar(rect, progressData)`

**Code Example:**
```javascript
// GanttCanvasOverlay.js - ENHANCED
syncWithTable() {
  const cellRects = this.tableManager.getCellBoundingRects();

  // Resize canvas
  this.canvas.width = this.tableManager.bodyScroll.scrollWidth;
  this.canvas.height = this.tableManager.bodyScroll.scrollHeight;

  // Clear canvas
  this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

  // Draw bars
  cellRects.forEach(rect => {
    const progressData = this._getProgressData(rect.pekerjaanId, rect.columnId);
    if (progressData && progressData.progress > 0) {
      this._drawBar(rect, progressData);
    }
  });
}

_getProgressData(pekerjaanId, columnId) {
  const stateManager = this.tableManager.stateManager;
  const cellKey = `${pekerjaanId}-${columnId}`;
  const actualValue = stateManager.getCellValue(cellKey, 'actual') || 0;
  const plannedValue = stateManager.getCellValue(cellKey, 'planned') || 0;

  return {
    progress: actualValue,
    planned: plannedValue,
    variance: actualValue - plannedValue,
    pekerjaanId,
    columnId
  };
}

_drawBar(rect, progressData) {
  const barHeight = rect.height * 0.6; // 60% of cell height
  const barY = rect.y + (rect.height - barHeight) / 2;
  const fillWidth = rect.width * (progressData.progress / 100);

  // Background bar (planned)
  this.ctx.fillStyle = '#e2e8f0';
  this.ctx.fillRect(rect.x + 2, barY, rect.width - 4, barHeight);

  // Progress fill (actual)
  const fillColor = this._getBarColor(progressData);
  this.ctx.fillStyle = fillColor;
  this.ctx.fillRect(rect.x + 2, barY, fillWidth - 4, barHeight);

  // Border
  this.ctx.strokeStyle = '#cbd5e1';
  this.ctx.lineWidth = 1;
  this.ctx.strokeRect(rect.x + 2, barY, rect.width - 4, barHeight);
}

_getBarColor(progressData) {
  const variance = progressData.variance;
  if (variance < -5) return '#ef4444'; // Red: behind schedule
  if (variance > 5) return '#10b981';  // Green: ahead of schedule
  return '#3b82f6'; // Blue: on schedule
}
```

**Validation Checkpoint:**
- [ ] Bars render aligned with cells
- [ ] Bar width matches progress percentage
- [ ] Color coding matches variance (red/green/blue)
- [ ] No visual glitches on scroll
- [x] Skeleton bar rendering refreshed on data update/switch mode

**Rollback**: Revert to test grid if bars misalign.

---

#### **Day 5: Dependency Lines**

**Goal**: Draw arrows connecting dependent tasks.

**Status (done - skeleton):** `GanttCanvasOverlay` sekarang memiliki `renderDependencies()` dan `_drawDependencies()` yang menggambar garis + arrow head antar sel (berdasar pekerjaan/kolom). `UnifiedTableManager.updateData` meneruskan `payload.dependencies` ke overlay. Jika data tidak tersedia, diabaikan (zero-regression).

**Checkpoint update:** skeleton dependency lines tampil ketika data diberikan; aman diabaikan jika data kosong.

**Tasks:**
1. Extract dependency data from StateManager
2. Implement `_drawDependencyLine()` method
3. Calculate start/end points based on cell positions
4. Add arrow heads for visual clarity

**Files to Modify:**
- `detail_project/static/detail_project/js/src/modules/gantt/GanttCanvasOverlay.js`:
  - Add `_getDependencies()` helper
  - Add `_drawDependencyLine(fromRect, toRect, type)` method
  - Call dependency drawing after bar rendering

**Code Example:**
```javascript
// GanttCanvasOverlay.js - ENHANCED
syncWithTable() {
  // ... existing bar rendering ...

  // Draw dependency lines
  const dependencies = this._getDependencies();
  dependencies.forEach(dep => {
    const fromRect = cellRects.find(r =>
      r.pekerjaanId === dep.from.pekerjaanId && r.columnId === dep.from.columnId
    );
    const toRect = cellRects.find(r =>
      r.pekerjaanId === dep.to.pekerjaanId && r.columnId === dep.to.columnId
    );

    if (fromRect && toRect) {
      this._drawDependencyLine(fromRect, toRect, dep.type);
    }
  });
}

_getDependencies() {
  const dependencies = [];
  const state = this.tableManager.state;

  // Extract from state.dependencies array
  (state.dependencies || []).forEach(dep => {
    dependencies.push({
      from: { pekerjaanId: dep.fromId, columnId: dep.fromColumn },
      to: { pekerjaanId: dep.toId, columnId: dep.toColumn },
      type: dep.type || 'finish-to-start'
    });
  });

  return dependencies;
}

_drawDependencyLine(fromRect, toRect, type) {
  this.ctx.strokeStyle = '#64748b';
  this.ctx.lineWidth = 2;
  this.ctx.setLineDash([5, 3]);

  const fromX = fromRect.x + fromRect.width;
  const fromY = fromRect.y + fromRect.height / 2;
  const toX = toRect.x;
  const toY = toRect.y + toRect.height / 2;

  // Draw line
  this.ctx.beginPath();
  this.ctx.moveTo(fromX, fromY);
  this.ctx.lineTo(toX, toY);
  this.ctx.stroke();

  // Draw arrow head
  this._drawArrowHead(toX, toY, Math.atan2(toY - fromY, toX - fromX));

  this.ctx.setLineDash([]); // Reset dash
}

_drawArrowHead(x, y, angle) {
  const headLength = 8;
  this.ctx.fillStyle = '#64748b';
  this.ctx.beginPath();
  this.ctx.moveTo(x, y);
  this.ctx.lineTo(
    x - headLength * Math.cos(angle - Math.PI / 6),
    y - headLength * Math.sin(angle - Math.PI / 6)
  );
  this.ctx.lineTo(
    x - headLength * Math.cos(angle + Math.PI / 6),
    y - headLength * Math.sin(angle + Math.PI / 6)
  );
  this.ctx.closePath();
  this.ctx.fill();
}
```

**Validation Checkpoint:**
- [ ] Dependency lines connect correct cells
- [ ] Arrow heads point in correct direction
- [ ] Lines don't overlap bars unreadably
- [ ] Performance acceptable with 100+ dependencies

**Rollback**: Comment out dependency drawing if performance degrades.

---

#### **Day 6: Interactive Features (Hover, Tooltip)**

**Goal**: Add mouse interaction for bar hover and tooltips.

**Status (done - skeleton):** Canvas sudah aktif pointer-events; `GanttCanvasOverlay` menyimpan `barRects`, melakukan hit-test pada mousemove, dan menampilkan tooltip sederhana (pekerjaan, kolom, progress). Tooltip otomatis hilang saat mouse keluar. Hover highlight/variance detail akan disusul pada tahap berikut.

**Tasks:**
1. Implement mouse event handlers on canvas
2. Detect which bar is under cursor
3. Show tooltip with pekerjaan name, progress, variance
4. Add hover highlight effect

**Files to Modify:**
- `detail_project/static/detail_project/js/src/modules/gantt/GanttCanvasOverlay.js`:
  - Add `_setupMouseEvents()` in constructor
  - Implement `_handleMouseMove(e)` for hover detection
  - Create tooltip DOM element
  - Implement `_showTooltip(progressData, mouseX, mouseY)`

**Code Example:**
```javascript
// GanttCanvasOverlay.js - ENHANCED
constructor(tableManager) {
  // ... existing code ...

  this.tooltip = this._createTooltip();
  this.hoveredBar = null;
  this._setupMouseEvents();
}

_createTooltip() {
  const tooltip = document.createElement('div');
  tooltip.className = 'gantt-tooltip';
  tooltip.style.cssText = `
    position: absolute;
    background: rgba(0, 0, 0, 0.9);
    color: white;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 12px;
    pointer-events: none;
    z-index: 1000;
    display: none;
  `;
  document.body.appendChild(tooltip);
  return tooltip;
}

_setupMouseEvents() {
  this.canvas.addEventListener('mousemove', (e) => this._handleMouseMove(e));
  this.canvas.addEventListener('mouseleave', () => this._hideTooltip());
}

_handleMouseMove(e) {
  const rect = this.canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left + this.tableManager.bodyScroll.scrollLeft;
  const mouseY = e.clientY - rect.top + this.tableManager.bodyScroll.scrollTop;

  const cellRects = this.tableManager.getCellBoundingRects();
  let hoveredBar = null;

  for (const cellRect of cellRects) {
    const progressData = this._getProgressData(cellRect.pekerjaanId, cellRect.columnId);
    if (!progressData || progressData.progress === 0) continue;

    const barHeight = cellRect.height * 0.6;
    const barY = cellRect.y + (cellRect.height - barHeight) / 2;
    const barWidth = cellRect.width * (progressData.progress / 100);

    if (mouseX >= cellRect.x && mouseX <= cellRect.x + barWidth &&
        mouseY >= barY && mouseY <= barY + barHeight) {
      hoveredBar = { rect: cellRect, data: progressData };
      break;
    }
  }

  if (hoveredBar) {
    this._showTooltip(hoveredBar.data, e.clientX, e.clientY);
    this.canvas.style.cursor = 'pointer';
  } else {
    this._hideTooltip();
    this.canvas.style.cursor = 'default';
  }
}

_showTooltip(progressData, mouseX, mouseY) {
  const pekerjaanName = this._getPekerjaanName(progressData.pekerjaanId);
  const varianceColor = progressData.variance >= 0 ? '#10b981' : '#ef4444';

  this.tooltip.innerHTML = `
    <div><strong>${pekerjaanName}</strong></div>
    <div>Actual: ${progressData.progress}%</div>
    <div>Planned: ${progressData.planned}%</div>
    <div style="color: ${varianceColor}">
      Variance: ${progressData.variance > 0 ? '+' : ''}${progressData.variance}%
    </div>
  `;

  this.tooltip.style.left = `${mouseX + 10}px`;
  this.tooltip.style.top = `${mouseY + 10}px`;
  this.tooltip.style.display = 'block';
}

_hideTooltip() {
  this.tooltip.style.display = 'none';
}

_getPekerjaanName(pekerjaanId) {
  const state = this.tableManager.state;
  const pekerjaan = state.flattenedData?.find(p => String(p.id) === String(pekerjaanId));
  return pekerjaan?.name || pekerjaan?.nama_pekerjaan || 'Unknown';
}
```

**Validation Checkpoint:**
- [ ] Tooltip shows on bar hover
- [ ] Tooltip displays correct data (name, progress, variance)
- [ ] Cursor changes to pointer on hover
- [ ] No tooltip flickering
- [x] Tooltip dasar tampil pada hover, hilang saat mouse leave

**Rollback**: Remove mouse events if tooltip positioning breaks.

---

#### **Day 7: Gantt Feature Parity Testing**

**Goal**: Verify all Gantt V2 features work in canvas overlay.

**Status:** Siap uji (unified default aktif, legacy Gantt dimatikan kecuali `enableLegacyGantt`). Overlay kini di-mount via `_initializeUnifiedGanttOverlay` ketika tab Gantt dibuka; tab switch memanggil `switchMode('gantt')`. Bar/dep/tooltip sudah dirender dari StateManager assignments; parity perlu verifikasi visual.

**Tasks:**
1. Create feature parity checklist
2. Test each feature side-by-side with old Gantt V2
3. Fix any missing features
4. Performance benchmark (render time, scroll FPS)

**Feature Parity Checklist:**
```
Gantt V2 Feature Parity Checklist (Day 7)

Visual Features:
[ ] Progress bars render with correct width
[ ] Color coding (red/green/blue) based on variance
[ ] Background bar shows planned progress
[ ] Dependency lines connect correct tasks
[ ] Arrow heads point in correct direction
[ ] Tree hierarchy visible (expand/collapse)

Interactive Features:
[ ] Hover tooltip shows pekerjaan name
[ ] Tooltip shows actual/planned/variance percentages
[ ] Cursor changes to pointer on bar hover
[ ] Tooltip follows mouse movement
[ ] Scroll performance smooth (>55 FPS)

Data Accuracy:
[ ] Bar width matches actual progress from StateManager
[ ] Variance calculation correct (actual - planned)
[ ] Dependencies match state.dependencies array
[ ] All pekerjaan rows render bars

Performance:
[ ] Initial render < 200ms
[ ] Scroll performance > 55 FPS
[ ] Tab switch to Gantt < 100ms
[ ] Memory usage < 70 MB
```

**Validation Checkpoint:**
- [ ] All checklist items pass
- [ ] Visual comparison with old Gantt V2 shows parity
- [ ] No regressions from old implementation

**Rollback**: Keep old Gantt V2 active if any critical feature missing.

---

### Phase 3: Integration & Testing (Days 8-9)

#### **Day 8: Cross-Mode Testing**

**Goal**: Test all 3 modes work seamlessly together.

**Tasks:**
1. Test Grid → Gantt → Kurva-S mode switching
2. Verify tree expansion persists across modes
3. Test StateManager edit sync across modes
4. Test export Excel from each mode
5. Performance profiling (memory, CPU)

**Test Scenarios:**

**Scenario 1: Mode Switching**
```
1. Open Grid mode
2. Expand 3 tree nodes
3. Scroll to week 10
4. Edit cell value (pekerjaan X, week 5: 50%)
5. Switch to Gantt mode
   ✓ Tree nodes still expanded
   ✓ Scrolled to week 10
   ✓ Bar for pekerjaan X shows 50% in week 5
6. Switch to Kurva-S mode
   ✓ Tree nodes still expanded
   ✓ Chart shows updated data point
7. Switch back to Grid mode
   ✓ Cell still shows 50%
   ✓ Tree expansion preserved
```

**Scenario 2: State Sync**
```
1. Grid mode: Edit pekerjaan A, week 3: 75%
2. Switch to Gantt mode
   ✓ Bar width shows 75%
3. Grid mode: Commit changes
4. Switch to Kurva-S mode
   ✓ Chart updates with new cumulative progress
5. Undo in Grid mode
6. Switch to Gantt mode
   ✓ Bar reverts to previous value
```

**Scenario 3: Export**
```
1. Grid mode: Export Excel
   ✓ All data exported correctly
2. Gantt mode: Export Excel
   ✓ Same data exported (no difference)
3. Kurva-S mode: Export Excel
   ✓ Same data exported
```

**Performance Profiling:**
```javascript
// Add to jadwal_kegiatan_app.js for Day 8 testing
function profileModeSwitch(fromMode, toMode) {
  const startTime = performance.now();
  const startMemory = performance.memory?.usedJSHeapSize || 0;

  unifiedManager.switchMode(toMode);

  const endTime = performance.now();
  const endMemory = performance.memory?.usedJSHeapSize || 0;

  console.log(`[Profile] ${fromMode} → ${toMode}:`, {
    time: `${(endTime - startTime).toFixed(2)}ms`,
    memoryDelta: `${((endMemory - startMemory) / 1024 / 1024).toFixed(2)} MB`
  });
}

// Test all mode transitions
profileModeSwitch('grid', 'gantt');
profileModeSwitch('gantt', 'kurva');
profileModeSwitch('kurva', 'grid');
```

**Validation Checkpoint:**
- [ ] All 3 test scenarios pass
- [ ] Mode switch time < 50ms
- [ ] Memory usage < 60 MB
- [ ] No console errors

**Rollback**: Fix critical bugs before proceeding to Day 9.

---

#### **Day 9: Performance Optimization**

**Goal**: Optimize rendering and memory usage.

**Tasks:**
1. Implement canvas dirty region tracking (only redraw changed bars)
2. Debounce scroll events for canvas sync
3. Optimize cell rect calculation (cache results)
4. Add requestAnimationFrame for smooth redraws
5. Profile bundle size (verify -12 KB target)

**Optimization 1: Dirty Region Tracking**
```javascript
// GanttCanvasOverlay.js - OPTIMIZED
constructor(tableManager) {
  // ... existing code ...
  this.dirtyRegions = new Set(); // Track which cells changed
}

markDirty(pekerjaanId, columnId) {
  this.dirtyRegions.add(`${pekerjaanId}-${columnId}`);
  this._scheduleRedraw();
}

_scheduleRedraw() {
  if (this.redrawScheduled) return;
  this.redrawScheduled = true;

  requestAnimationFrame(() => {
    this._redrawDirtyRegions();
    this.redrawScheduled = false;
  });
}

_redrawDirtyRegions() {
  if (this.dirtyRegions.size === 0) return;

  const cellRects = this.tableManager.getCellBoundingRects();

  this.dirtyRegions.forEach(cellKey => {
    const [pekerjaanId, columnId] = cellKey.split('-');
    const rect = cellRects.find(r =>
      r.pekerjaanId === pekerjaanId && r.columnId === columnId
    );

    if (rect) {
      // Clear only this cell's region
      this.ctx.clearRect(rect.x - 2, rect.y - 2, rect.width + 4, rect.height + 4);

      // Redraw bar
      const progressData = this._getProgressData(pekerjaanId, columnId);
      if (progressData && progressData.progress > 0) {
        this._drawBar(rect, progressData);
      }
    }
  });

  this.dirtyRegions.clear();
}
```

**Optimization 2: Scroll Debouncing**
```javascript
// GanttCanvasOverlay.js - OPTIMIZED
constructor(tableManager) {
  // ... existing code ...

  let scrollTimeout;
  this.tableManager.bodyScroll.addEventListener('scroll', () => {
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(() => {
      if (this.visible) this.syncWithTable();
    }, 16); // ~60 FPS
  });
}
```

**Optimization 3: Cell Rect Caching**
```javascript
// tanstack-grid-manager.js - OPTIMIZED
getCellBoundingRects(forceRefresh = false) {
  if (!forceRefresh && this._cachedCellRects &&
      this._lastScrollTop === this.bodyScroll.scrollTop &&
      this._lastScrollLeft === this.bodyScroll.scrollLeft) {
    return this._cachedCellRects;
  }

  // ... existing calculation ...

  this._cachedCellRects = rects;
  this._lastScrollTop = this.bodyScroll.scrollTop;
  this._lastScrollLeft = this.bodyScroll.scrollLeft;

  return rects;
}
```

**Bundle Size Verification:**
```bash
# Run build and check sizes
npm run build

# Expected output after Gantt V2 removal:
# vendor-tanstack.js: ~86 KB
# vendor-uplot.js: ~78 KB
# core.js: ~27 KB
# gantt-v2.js: REMOVED (-14 KB)
# jadwal-kegiatan.js: ~67 KB
# Total: ~260 KB (down from 272 KB)
```

**Validation Checkpoint:**
- [ ] Scroll performance > 60 FPS
- [ ] Canvas redraw time < 16ms (60 FPS)
- [ ] Memory usage stable (no leaks)
- [ ] Bundle size reduced to ~260 KB

**Rollback**: Remove optimizations if they introduce bugs.

---

### Phase 4: Legacy Code Cleanup (Day 10)

#### **Day 10: Gantt V2 Removal & Documentation**

**Goal**: Remove all legacy Gantt V2 code and update documentation.

**CRITICAL**: Only proceed with cleanup after ALL Day 8-9 validations pass.

**Tasks:**

**1. Remove Gantt V2 Files**

Files to DELETE:
```
detail_project/static/detail_project/js/src/modules/gantt/gantt-frozen-grid.js (14 KB)
detail_project/static/detail_project/js/src/modules/gantt/gantt-v2-legacy.js (if exists)
```

**Validation Before Deletion:**
```bash
# Search for any imports of gantt-frozen-grid.js
grep -r "gantt-frozen-grid" detail_project/static/detail_project/js/

# Expected: Only found in jadwal_kegiatan_app.js (will be removed next)
```

**2. Update Main App File**

File to MODIFY: `detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js`

**BEFORE (Old Implementation):**
```javascript
import { GanttFrozenGrid } from './modules/gantt/gantt-frozen-grid.js';
import { TanStackGridManager } from './modules/grid/tanstack-grid-manager.js';
import { KurvaSUPlotChart } from './modules/kurva-s/uplot-chart.js';

// Separate instances
let gridInstance = null;
let ganttInstance = null;
let kurvaSInstance = null;

function initializeGrid() {
  gridInstance = new TanStackGridManager(state, options);
  gridInstance.mount(gridContainer, gridDomTargets);
}

function initializeGantt() {
  ganttInstance = new GanttFrozenGrid(state, options);
  ganttInstance.mount(ganttContainer, ganttDomTargets);
}

function initializeKurvaS() {
  kurvaSInstance = new KurvaSUPlotChart(state, chartOptions);
  kurvaSInstance.mount(chartContainer);
}

// Tab switching destroys and recreates instances
tabGrid.addEventListener('click', () => {
  if (ganttInstance) ganttInstance.destroy();
  if (kurvaSInstance) kurvaSInstance.destroy();
  initializeGrid();
});
```

**AFTER (Unified Implementation):**
```javascript
import { UnifiedTableManager } from './modules/unified/UnifiedTableManager.js';

// Single instance
let unifiedManager = null;

function initializeUnifiedTable() {
  unifiedManager = new UnifiedTableManager(state, options);
  unifiedManager.mount(gridContainer, gridDomTargets);
}

// Tab switching only changes mode (NO destroy/recreate)
tabGrid.addEventListener('click', () => {
  unifiedManager.switchMode('grid');
  setActiveTab('grid');
});

tabGantt.addEventListener('click', () => {
  unifiedManager.switchMode('gantt');
  setActiveTab('gantt');
});

tabKurvaS.addEventListener('click', () => {
  unifiedManager.switchMode('kurva');
  setActiveTab('kurva');
});

function setActiveTab(mode) {
  document.querySelectorAll('.mode-tab').forEach(tab => {
    tab.classList.toggle('active', tab.dataset.mode === mode);
  });
}
```

**3. Remove Event Listeners**

Search for and remove Gantt V2-specific event listeners:
```javascript
// REMOVE these from jadwal_kegiatan_app.js
StateManager.getInstance().on('gantt-v2:bar-click', handleBarClick);
StateManager.getInstance().on('gantt-v2:dependency-update', handleDependencyUpdate);

// These are now handled by GanttCanvasOverlay internally
```

**4. Update Tests**

Files to MODIFY:
- `detail_project/static/detail_project/js/tests/gantt.test.js` (if exists)

**Update test imports:**
```javascript
// BEFORE
import { GanttFrozenGrid } from '../src/modules/gantt/gantt-frozen-grid.js';

// AFTER
import { UnifiedTableManager } from '../src/modules/unified/UnifiedTableManager.js';
import { GanttCanvasOverlay } from '../src/modules/gantt/GanttCanvasOverlay.js';

// Update test cases
describe('Gantt Mode', () => {
  let unifiedManager;

  beforeEach(() => {
    unifiedManager = new UnifiedTableManager(mockState, mockOptions);
    unifiedManager.mount(mockContainer, mockDomTargets);
    unifiedManager.switchMode('gantt');
  });

  it('should render bars aligned with cells', () => {
    const overlay = unifiedManager.overlays.gantt;
    expect(overlay.visible).toBe(true);
    // ... rest of test
  });
});
```

**5. Verify Bundle Build**

```bash
# Rebuild bundle
npm run build

# Check for removed files
ls -lh detail_project/static/detail_project/dist/assets/

# Expected: gantt-v2.*.js file REMOVED
# Verify bundle size reduction:
# Before: 272 KB
# After: 260 KB (-12 KB)
```

**6. Update Documentation**

File to UPDATE: `FINAL_MIGRATION_AUDIT_REPORT.md`

Add new section:
```markdown
## Phase 6: Unified Table Layer Migration (Days 11-20)

**Status:** COMPLETE ✅

### Changes:
- Consolidated Grid/Gantt/Kurva-S into single TanStack table instance
- Replaced `gantt-frozen-grid.js` (14 KB) with `GanttCanvasOverlay.js` (canvas overlay)
- Removed redundant rendering on tab switch (330ms → <50ms)
- Memory reduction: 100 MB → 60 MB (-40%)
- Bundle size: 272 KB → 260 KB (-12 KB)

### Files Removed:
- ❌ `gantt-frozen-grid.js`
- ❌ Gantt V2 event listeners in `jadwal_kegiatan_app.js`

### Files Added:
- ✅ `UnifiedTableManager.js` (orchestration)
- ✅ `GanttCanvasOverlay.js` (canvas-based Gantt rendering)
- ✅ `CellRendererFactory.js` (pluggable cell renderers)
- ✅ `InputCellRenderer.js`, `GanttCellRenderer.js`, `ReadonlyCellRenderer.js`

### Performance Results:
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Tab Switch | 330ms | 45ms | **86% faster** |
| Memory | 100 MB | 58 MB | **42% reduction** |
| Bundle | 272 KB | 260 KB | **-12 KB** |
| Scroll FPS | 55-60 | 60 | **Stable 60 FPS** |
```

**7. Final Verification Checklist**

```
Cleanup Verification Checklist (Day 10)

Code Cleanup:
[ ] gantt-frozen-grid.js deleted
[ ] No import references to gantt-frozen-grid.js
[ ] Gantt V2 event listeners removed
[ ] jadwal_kegiatan_app.js updated to UnifiedTableManager
[ ] Tests updated to use new architecture

Build Verification:
[ ] npm run build succeeds without errors
[ ] No gantt-v2.*.js in dist/assets/
[ ] Bundle size reduced to ~260 KB
[ ] No console warnings about missing modules

Functional Verification:
[ ] Grid mode works (input, validation, Tab/Enter)
[ ] Gantt mode works (bars, dependencies, tooltip)
[ ] Kurva-S mode works (chart, toggle, zoom)
[ ] Mode switching < 50ms
[ ] Tree expansion persists across modes
[ ] StateManager sync works across modes
[ ] Export Excel works from all modes

Performance Verification:
[ ] Memory usage < 60 MB (DevTools Memory tab)
[ ] Scroll performance > 60 FPS
[ ] No memory leaks after 20+ mode switches
[ ] First render < 200ms

Documentation:
[ ] FINAL_MIGRATION_AUDIT_REPORT.md updated
[ ] This roadmap marked as COMPLETE
[ ] Release notes prepared
```

**Validation Checkpoint:**
- [ ] ALL checklist items pass
- [ ] No regressions from unified architecture
- [ ] Bundle analysis confirms -12 KB reduction

**Rollback**: If ANY critical issue found, restore Gantt V2 files from git:
```bash
git checkout HEAD -- detail_project/static/detail_project/js/src/modules/gantt/gantt-frozen-grid.js
git checkout HEAD -- detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js
npm run build
```

---

## Part 4: Risk Mitigation & Rollback Procedures

### Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Canvas positioning misalignment | Medium | High | Day 2 validation checkpoint; adjust rect calculation |
| Performance degradation on scroll | Low | High | Day 9 optimization; debounce + dirty regions |
| Feature regression in Gantt | Medium | Critical | Day 7 parity testing; keep V2 until verified |
| Memory leaks from overlays | Low | Medium | Day 8 profiling; proper cleanup in hide() |
| Bundle size increase | Low | Medium | Day 10 verification; tree-shaking check |

### Rollback Procedures

**Phase 1 Rollback (Days 1-3)**
```bash
# If cell renderer abstraction breaks Grid mode
git checkout HEAD -- detail_project/static/detail_project/js/src/modules/grid/tanstack-grid-manager.js
rm -rf detail_project/static/detail_project/js/src/modules/grid/renderers/
npm run build
```

**Phase 2 Rollback (Days 4-7)**
```bash
# If canvas overlay doesn't achieve Gantt parity
# Keep old gantt-frozen-grid.js active
git checkout HEAD -- detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js

# Disable canvas overlay
# In UnifiedTableManager.js, comment out:
# this.overlays.gantt.show();
```

**Phase 3 Rollback (Days 8-9)**
```bash
# If performance optimizations introduce bugs
git diff HEAD -- detail_project/static/detail_project/js/src/modules/gantt/GanttCanvasOverlay.js
# Revert specific optimization commits
git checkout <commit-before-optimization> -- <file>
```

**Phase 4 Rollback (Day 10)**
```bash
# If cleanup breaks production
git checkout HEAD -- detail_project/static/detail_project/js/src/modules/gantt/gantt-frozen-grid.js
git checkout HEAD -- detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js
npm run build
```

**Emergency Full Rollback**
```bash
# Restore entire codebase to pre-migration state
git checkout <commit-before-migration> .
npm install
npm run build
```

---

## Part 5: Testing Strategy

### Unit Tests

**Test Files to Create:**

`detail_project/static/detail_project/js/tests/unified-table-manager.test.js`
```javascript
import { UnifiedTableManager } from '../src/modules/unified/UnifiedTableManager.js';

describe('UnifiedTableManager', () => {
  it('should mount TanStack grid once', () => {
    const manager = new UnifiedTableManager(mockState, mockOptions);
    manager.mount(mockContainer, mockDomTargets);
    expect(manager.tanstackGrid).toBeDefined();
  });

  it('should switch modes without re-rendering table', () => {
    const manager = new UnifiedTableManager(mockState, mockOptions);
    manager.mount(mockContainer, mockDomTargets);

    const tableInstance = manager.tanstackGrid;
    manager.switchMode('gantt');

    expect(manager.tanstackGrid).toBe(tableInstance); // Same instance
  });

  it('should preserve tree expansion across mode switches', () => {
    const manager = new UnifiedTableManager(mockState, mockOptions);
    manager.mount(mockContainer, mockDomTargets);

    // Expand row in Grid mode
    manager.tanstackGrid.toggleRow('pekerjaan-123');
    const expandedBefore = manager.tanstackGrid.getExpandedRows();

    // Switch to Gantt
    manager.switchMode('gantt');
    const expandedAfter = manager.tanstackGrid.getExpandedRows();

    expect(expandedAfter).toEqual(expandedBefore);
  });
});
```

`detail_project/static/detail_project/js/tests/gantt-canvas-overlay.test.js`
```javascript
import { GanttCanvasOverlay } from '../src/modules/gantt/GanttCanvasOverlay.js';

describe('GanttCanvasOverlay', () => {
  it('should create canvas element on show()', () => {
    const overlay = new GanttCanvasOverlay(mockTableManager);
    overlay.show();

    expect(overlay.canvas.parentNode).toBe(mockTableManager.bodyScroll);
    expect(overlay.visible).toBe(true);
  });

  it('should draw bars aligned with cell positions', () => {
    const overlay = new GanttCanvasOverlay(mockTableManager);
    overlay.show();

    const cellRects = [
      { pekerjaanId: '123', columnId: 'week-1', x: 0, y: 0, width: 100, height: 40 }
    ];
    mockTableManager.getCellBoundingRects = () => cellRects;

    overlay.syncWithTable();

    // Verify canvas size
    expect(overlay.canvas.width).toBe(mockTableManager.bodyScroll.scrollWidth);
  });

  it('should show tooltip on bar hover', () => {
    const overlay = new GanttCanvasOverlay(mockTableManager);
    overlay.show();

    // Simulate mouse over bar
    const mouseEvent = new MouseEvent('mousemove', { clientX: 50, clientY: 20 });
    overlay.canvas.dispatchEvent(mouseEvent);

    expect(overlay.tooltip.style.display).toBe('block');
  });
});
```

### Integration Tests

**Test Scenarios:**

`detail_project/static/detail_project/js/tests/integration/mode-switching.test.js`
```javascript
describe('Mode Switching Integration', () => {
  it('should sync data across all modes', async () => {
    const app = await initializeApp();

    // Grid mode: edit cell
    app.unifiedManager.switchMode('grid');
    app.unifiedManager.tanstackGrid.setCellValue('pekerjaan-123', 'week-1', 75);

    // Gantt mode: verify bar width
    app.unifiedManager.switchMode('gantt');
    const barData = app.unifiedManager.overlays.gantt._getProgressData('pekerjaan-123', 'week-1');
    expect(barData.progress).toBe(75);

    // Kurva-S mode: verify chart data
    app.unifiedManager.switchMode('kurva');
    const chartData = app.unifiedManager.overlays.kurva.getData();
    expect(chartData.actual[0]).toBeGreaterThan(0); // Cumulative includes new value
  });
});
```

### E2E Tests (Manual Checklist)

**Day 8 Manual Testing Checklist:**
```
Grid Mode:
[ ] Click expand icon → tree expands
[ ] Type digit in cell → auto-edit mode
[ ] Press Tab → moves to next cell
[ ] Press Enter → moves down
[ ] Edit value > 100 → red border + toast
[ ] Scroll to week 20 → smooth scroll
[ ] Export Excel → file downloads

Gantt Mode:
[ ] Switch from Grid → bars render instantly (<50ms)
[ ] Hover over bar → tooltip appears
[ ] Tooltip shows: name, actual%, planned%, variance%
[ ] Variance > 0 → green bar
[ ] Variance < 0 → red bar
[ ] Dependency line connects tasks
[ ] Scroll → canvas syncs with cells

Kurva-S Mode:
[ ] Switch from Gantt → chart renders
[ ] Click "Cost" toggle → switches to cost view
[ ] Hover over point → tooltip shows Rupiah
[ ] Scroll wheel → zoom in/out
[ ] Pan chart → date range updates
[ ] Click "Reset Zoom" → returns to full view

Cross-Mode:
[ ] Grid → Gantt → Grid: tree expansion persists
[ ] Grid → Kurva → Grid: scroll position persists
[ ] Edit in Grid → switch to Gantt → bar updates
[ ] Commit in Grid → switch to Kurva → chart updates
[ ] Undo in Grid → switch to Gantt → bar reverts
```

---

## Part 6: Performance Benchmarks

### Performance Targets

| Metric | Baseline (Current) | Target (Unified) | Measurement Method |
|--------|-------------------|------------------|---------------------|
| Tab Switch Time | 330ms | <50ms | `performance.now()` before/after |
| Memory Usage | ~100 MB | <60 MB | Chrome DevTools Memory Profiler |
| Bundle Size | 272 KB | ~260 KB | `ls -lh dist/assets/` |
| Initial Render | ~180ms | <200ms | `performance.mark()` in mount() |
| Scroll FPS | 55-60 | 60 | Chrome DevTools Performance tab |
| Canvas Redraw | N/A | <16ms | `performance.now()` in syncWithTable() |

### Performance Measurement Code

Add to `jadwal_kegiatan_app.js` for Day 9 profiling:

```javascript
class PerformanceMonitor {
  constructor() {
    this.metrics = [];
  }

  measureModeSwitch(fromMode, toMode, callback) {
    performance.mark('mode-switch-start');
    const memoryBefore = performance.memory?.usedJSHeapSize || 0;

    callback();

    performance.mark('mode-switch-end');
    performance.measure('mode-switch', 'mode-switch-start', 'mode-switch-end');

    const measure = performance.getEntriesByName('mode-switch')[0];
    const memoryAfter = performance.memory?.usedJSHeapSize || 0;

    this.metrics.push({
      transition: `${fromMode} → ${toMode}`,
      duration: measure.duration.toFixed(2),
      memoryDelta: ((memoryAfter - memoryBefore) / 1024 / 1024).toFixed(2)
    });

    performance.clearMarks();
    performance.clearMeasures();
  }

  getReport() {
    console.table(this.metrics);
    const avgDuration = this.metrics.reduce((sum, m) => sum + parseFloat(m.duration), 0) / this.metrics.length;
    console.log(`Average mode switch time: ${avgDuration.toFixed(2)}ms`);
  }
}

// Usage
const perfMonitor = new PerformanceMonitor();

tabGantt.addEventListener('click', () => {
  perfMonitor.measureModeSwitch('grid', 'gantt', () => {
    unifiedManager.switchMode('gantt');
  });
});

// After 20 mode switches
setTimeout(() => perfMonitor.getReport(), 60000);
```

### Expected Results (Day 9)

```
Performance Report (Unified Table Layer)

┌─────────────┬──────────┬─────────────┐
│ Transition  │ Duration │ Memory Δ    │
├─────────────┼──────────┼─────────────┤
│ grid→gantt  │ 42ms     │ +0.5 MB     │
│ gantt→kurva │ 38ms     │ +0.2 MB     │
│ kurva→grid  │ 35ms     │ -0.3 MB     │
│ grid→gantt  │ 45ms     │ +0.4 MB     │
│ gantt→grid  │ 40ms     │ -0.5 MB     │
└─────────────┴──────────┴─────────────┘

Average mode switch time: 40ms ✅ (Target: <50ms)
Peak memory usage: 58 MB ✅ (Target: <60 MB)
Bundle size: 260 KB ✅ (Target: ~260 KB)
```

---

## Part 7: Success Criteria

### Phase 1 Success Criteria (Days 1-3)
- [ ] `CellRendererFactory` implemented with 3 renderer types
- [ ] Grid mode works with `InputCellRenderer` (no regressions)
- [ ] Canvas overlay positions correctly over table cells
- [ ] `UnifiedTableManager` switches modes without errors
- [ ] Mode switch time < 100ms (Day 3 baseline)

### Phase 2 Success Criteria (Days 4-7)
- [ ] Gantt bars render aligned with cells
- [ ] Bar width accurately reflects progress percentage
- [ ] Color coding (red/green/blue) based on variance
- [ ] Dependency lines connect correct tasks with arrows
- [ ] Hover tooltip shows pekerjaan name + percentages
- [ ] **ALL Gantt V2 features verified in parity checklist**

### Phase 3 Success Criteria (Days 8-9)
- [ ] All 3 cross-mode test scenarios pass
- [ ] Tree expansion persists across all mode switches
- [ ] StateManager edits sync across all modes
- [ ] Export Excel works from all modes
- [ ] Mode switch time < 50ms ✅ **TARGET MET**
- [ ] Memory usage < 60 MB ✅ **TARGET MET**
- [ ] Scroll performance 60 FPS ✅ **TARGET MET**

### Phase 4 Success Criteria (Day 10)
- [ ] `gantt-frozen-grid.js` deleted successfully
- [ ] No import references to deleted files
- [ ] Bundle size reduced to ~260 KB ✅ **TARGET MET**
- [ ] All cleanup verification checklist items pass
- [ ] Documentation updated
- [ ] **ZERO regressions from old implementation**

### Overall Success Criteria
- [ ] 100% feature parity (Grid, Gantt, Kurva-S)
- [ ] 85% faster tab switching (330ms → <50ms)
- [ ] 40% memory reduction (100 MB → <60 MB)
- [ ] -12 KB bundle size reduction
- [ ] Production-ready (all tests pass)
- [ ] **READY FOR RELEASE** ✅

---

## Part 8: Timeline & Resource Allocation

### Daily Schedule

| Day | Phase | Focus | Estimated Hours | Deliverables |
|-----|-------|-------|-----------------|--------------|
| 1 | Phase 1 | Cell Renderer Abstraction | 6-8h | `CellRendererFactory`, 3 renderer classes |
| 2 | Phase 1 | Canvas Overlay Skeleton | 6-8h | `GanttCanvasOverlay`, positioning logic |
| 3 | Phase 1 | Mode Switching | 6-8h | `UnifiedTableManager`, tab integration |
| 4 | Phase 2 | Basic Bar Rendering | 6-8h | Bar drawing logic, color coding |
| 5 | Phase 2 | Dependency Lines | 6-8h | Arrow rendering, connection logic |
| 6 | Phase 2 | Interactive Features | 6-8h | Tooltip, hover detection |
| 7 | Phase 2 | Gantt Parity Testing | 4-6h | Feature parity checklist verified |
| 8 | Phase 3 | Cross-Mode Testing | 6-8h | Integration test scenarios |
| 9 | Phase 3 | Performance Optimization | 6-8h | Dirty regions, debouncing, caching |
| 10 | Phase 4 | Cleanup & Documentation | 4-6h | File removal, docs update |

**Total Estimated Effort:** 56-74 hours (7-9 working days)

### Parallel Work Opportunities

Days 1-3 (Phase 1) can be partially parallelized:
- **Developer A**: Cell renderer abstraction (Day 1)
- **Developer B**: Canvas overlay skeleton (Day 2)
- **Merge on Day 3**: Integrate both for mode switching

Days 4-6 (Phase 2) can be partially parallelized:
- **Developer A**: Bar rendering + color coding
- **Developer B**: Dependency lines
- **Day 6**: Both work on interactive features

---

## Part 9: Post-Migration Enhancements (Optional)

### Optional Enhancements (After Day 10)

**Enhancement 1: Drag-to-Resize Bars**
```javascript
// GanttCanvasOverlay.js - FUTURE ENHANCEMENT
_setupMouseEvents() {
  // ... existing hover logic ...

  this.canvas.addEventListener('mousedown', (e) => {
    const hoveredBar = this._getBarAtPosition(e.clientX, e.clientY);
    if (hoveredBar) {
      this._startBarResize(hoveredBar, e);
    }
  });
}

_startBarResize(bar, startEvent) {
  const onMouseMove = (e) => {
    const newWidth = e.clientX - bar.rect.x;
    const newProgress = Math.min(100, Math.max(0, (newWidth / bar.rect.width) * 100));
    this._updateBarProgress(bar, newProgress);
  };

  const onMouseUp = () => {
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
  };

  document.addEventListener('mousemove', onMouseMove);
  document.addEventListener('mouseup', onMouseUp);
}
```

**Enhancement 2: Cost Mode Toggle Button**
```javascript
// Add UI button in toolbar
<button id="toggle-cost-mode" class="btn btn-secondary">
  Switch to Cost View
</button>

// In UnifiedTableManager
toggleCostMode() {
  this.costModeEnabled = !this.costModeEnabled;

  if (this.currentMode === 'kurva') {
    this.overlays.kurva.toggleView(); // Existing uPlot toggle
  }

  // Update button text
  document.getElementById('toggle-cost-mode').textContent =
    this.costModeEnabled ? 'Switch to Progress View' : 'Switch to Cost View';
}
```

**Enhancement 3: Gantt Mini-Map**
```javascript
// Show miniature overview of entire Gantt timeline
class GanttMiniMap {
  constructor(overlay) {
    this.overlay = overlay;
    this.canvas = document.createElement('canvas');
    this.canvas.className = 'gantt-minimap';
    this.canvas.width = 200;
    this.canvas.height = 100;
  }

  render() {
    // Draw compressed view of all bars
    // Show viewport rectangle
    // Allow click-to-scroll
  }
}
```

---

## Appendix A: File Structure After Migration

```
detail_project/static/detail_project/js/src/
├── jadwal_kegiatan_app.js (UPDATED - uses UnifiedTableManager)
├── modules/
│   ├── unified/
│   │   └── UnifiedTableManager.js (NEW - orchestration layer)
│   ├── grid/
│   │   ├── tanstack-grid-manager.js (UPDATED - added setCellRenderer, getCellBoundingRects)
│   │   └── renderers/
│   │       ├── CellRendererFactory.js (NEW)
│   │       ├── InputCellRenderer.js (NEW - extracted from tanstack-grid-manager)
│   │       ├── GanttCellRenderer.js (NEW - simplified for overlay)
│   │       └── ReadonlyCellRenderer.js (NEW - for Kurva-S mode)
│   ├── gantt/
│   │   ├── GanttCanvasOverlay.js (NEW - replaces gantt-frozen-grid.js)
│   │   └── gantt-frozen-grid.js (DELETED in Phase 4)
│   ├── kurva-s/
│   │   ├── uplot-chart.js (NO CHANGES - continues as side panel)
│   │   └── dataset-builder.js (NO CHANGES)
│   └── shared/
│       └── chart-utils.js (NO CHANGES)
└── tests/
    ├── unified-table-manager.test.js (NEW)
    └── gantt-canvas-overlay.test.js (NEW)
```

---

## Appendix B: Architecture Diagrams

### Before: 3 Separate Implementations

```
┌─────────────────────────────────────────────────────────┐
│         User clicks "Grid" tab                          │
└────────────────┬────────────────────────────────────────┘
                 │
         ┌───────▼────────┐
         │ Destroy Gantt  │ ← 150ms (unmount, cleanup)
         │ Destroy Kurva  │
         └───────┬────────┘
                 │
         ┌───────▼────────┐
         │ Create Grid    │ ← 180ms (mount, render)
         │ Instance       │
         └────────────────┘

TOTAL: 330ms per tab switch
```

### After: Unified Table Layer

```
┌─────────────────────────────────────────────────────────┐
│         User clicks "Gantt" tab                         │
└────────────────┬────────────────────────────────────────┘
                 │
         ┌───────▼────────┐
         │ Switch Cell    │ ← 10ms (renderer swap)
         │ Renderer       │
         └───────┬────────┘
                 │
         ┌───────▼────────┐
         │ Show Canvas    │ ← 35ms (overlay visibility + sync)
         │ Overlay        │
         └────────────────┘

TOTAL: 45ms per tab switch ✅ (85% faster)
```

---

## Conclusion

This roadmap provides a comprehensive, step-by-step plan to migrate the Jadwal Pekerjaan page from 3 separate mode implementations to a unified table layer architecture. The migration is structured into 4 phases over 10 days, with validation checkpoints and rollback procedures at each phase to ensure **zero feature regression**.

### Key Guarantees

✅ **100% Feature Preservation**: All features from Grid, Gantt V2, and Kurva-S modes will be preserved
✅ **85% Performance Improvement**: Tab switching from 330ms to <50ms
✅ **40% Memory Reduction**: From 100 MB to <60 MB
✅ **Complete Cleanup**: Gantt V2 legacy code removed in Phase 4 (Day 10)
✅ **Production Ready**: Comprehensive testing and rollback procedures

### Next Steps

1. **User Approval**: Review and approve this roadmap
2. **Day 1 Start**: Begin Phase 1 (Cell Renderer Abstraction)
3. **Daily Standups**: Review progress against validation checkpoints
4. **Day 10 Completion**: Cleanup and release

**Status:** Ready to Begin ✅
**Estimated Completion:** 10 working days
**Risk Level:** Low (incremental migration with rollback procedures)

---

**Document End**
