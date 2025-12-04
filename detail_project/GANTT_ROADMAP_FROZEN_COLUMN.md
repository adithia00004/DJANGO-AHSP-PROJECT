# Gantt Chart Roadmap - Frozen Column Architecture

**Date:** 2025-12-03
**Approach:** Frozen Column (position: sticky)
**Total Duration:** 7 days
**Objective:** Build production-ready Gantt with perfect alignment and Grid View consistency

---

## Executive Summary

### Why Frozen Column?

1. ✅ **Perfect Alignment** - Single DOM tree eliminates coordinate system drift
2. ✅ **Native Scrolling** - Browser handles scroll, zero JS sync overhead
3. ✅ **Grid View Consistency** - Reuse TimeColumnGenerator and StateManager
4. ✅ **Future-Proof** - Built on web standards (CSS sticky), not custom sync logic

### Success Criteria

- ✅ Zero pixel misalignment between frozen columns and timeline
- ✅ Same time segmentation as Grid View (week/month from tahapan)
- ✅ Same progress data source (StateManager)
- ✅ Smooth 60fps scrolling with 1000+ tasks
- ✅ Feature parity: tree, search, zoom, milestones

---

## Architecture Overview

### Visual Structure

```
┌──────────────────────────────────────────────────────────────────┐
│ Gantt Container (single scroll container)                        │
├──────────────────────────────────────────────────────────────────┤
│ ┌─────────────────┬───────────────────────────────────────────┐ │
│ │ FROZEN COLUMNS  │ TIMELINE COLUMNS (scrollable)             │ │
│ │ (sticky left)   │                                           │ │
│ ├─────────────────┼───────────────────────────────────────────┤ │
│ │ Header Row      │                                           │ │
│ ├─────┬─────┬─────┼──────┬──────┬──────┬──────┬──────┬──────┤ │
│ │ Pkg │ Vol │ Sat │ W1   │ W2   │ W3   │ W4   │ W5   │ W6   │ │
│ ├─────┼─────┼─────┼──────┼──────┼──────┼──────┼──────┼──────┤ │
│ │ 📁A │ 100 │ m3  │██████│██    │      │      │      │      │ │
│ │ 📁B │  50 │ m2  │      │██████│██    │      │      │      │ │
│ │ 📄T1│  20 │ ls  │      │      │██████│      │      │      │ │
│ └─────┴─────┴─────┴──────┴──────┴──────┴──────┴──────┴──────┘ │
│                                                                  │
│ ← Frozen stays   → Timeline scrolls horizontally →              │
└──────────────────────────────────────────────────────────────────┘
```

### Technical Stack

**Core Technology:**
- CSS Grid Layout (display: grid)
- CSS Sticky Positioning (position: sticky)
- Vanilla JavaScript (ES6 modules)
- HTML Canvas for bars (optional, can use CSS)

**Reused Modules:**
- `TimeColumnGenerator` - Grid View's time segmentation logic
- `StateManager` - Grid View's progress data
- `DataLoader` - Grid View's data loading
- `GanttDataModel` - Keep existing (with modifications)

**New Modules:**
- `GanttFrozenGrid` - Main grid component
- `GanttRowRenderer` - Render individual rows
- `GanttBarRenderer` - Render timeline bars
- `GanttVirtualScroller` - Virtual scrolling for performance

---

## Detailed Roadmap

### PHASE 0: Architectural Planning & Design

**Duration:** 0.5 days (4 hours)
**Status:** IN PROGRESS

#### Objectives

1. Finalize frozen column specifications
2. Define data structures and interfaces
3. Create mockups and CSS architecture
4. Plan file organization

#### Tasks

**Task 0.1: Design Specifications**

```javascript
// Frozen Columns Configuration
const FROZEN_COLUMNS = [
  {
    field: 'hierarchy',
    headerName: 'Pekerjaan',
    width: 280,
    minWidth: 200,
    maxWidth: 400,
    resizable: true,
    type: 'tree' // Supports hierarchy with expand/collapse
  },
  {
    field: 'volume',
    headerName: 'Volume',
    width: 70,
    resizable: false,
    align: 'right'
  },
  {
    field: 'satuan',
    headerName: 'Satuan',
    width: 70,
    resizable: false,
    align: 'center'
  }
];

// Timeline Columns (generated from TimeColumnGenerator)
const TIMELINE_COLUMNS = [
  // Generated dynamically based on:
  // - Project date range
  // - Time scale (week/month)
  // - Tahapan from Grid View
  {
    field: 'week_1',
    headerName: 'Minggu 1',
    dateRange: { start: '2025-12-01', end: '2025-12-07' },
    width: 100,
    type: 'timeline'
  },
  // ... more weeks/months
];
```

**Task 0.2: Data Structure Interface**

```typescript
// Define interfaces for type safety
interface GanttRow {
  id: string;
  type: 'klasifikasi' | 'sub-klasifikasi' | 'pekerjaan';
  level: number;
  expanded: boolean;

  // Frozen column data
  name: string;
  kode: string;
  volume: number;
  satuan: string;

  // Timeline data
  bars: {
    planned: {
      startDate: Date;
      endDate: Date;
      progress: number; // 0-100
    };
    actual: {
      startDate: Date;
      endDate: Date;
      progress: number; // 0-100
    };
  };

  // Progress per tahapan (from StateManager)
  tahapanProgress: Map<string, { planned: number; actual: number }>;
}

interface GanttConfig {
  frozenColumns: FrozenColumn[];
  timelineColumns: TimelineColumn[];
  rowHeight: number;
  timeScale: 'week' | 'month';
  virtualScrolling: boolean;
  showMilestones: boolean;
}
```

**Task 0.3: CSS Architecture**

```css
/* Base Grid Layout */
.gantt-frozen-grid {
  display: grid;
  grid-template-columns:
    [frozen-start] 280px 70px 70px [frozen-end timeline-start]
    repeat(auto-fill, 100px) [timeline-end];
  overflow: auto;
  height: 600px;
}

/* Sticky Frozen Columns */
.gantt-cell.frozen {
  position: sticky;
  left: 0; /* First column */
  z-index: 10;
  background: white;
  border-right: 2px solid var(--bs-border-color);
}

.gantt-cell.frozen:nth-child(2) {
  left: 280px; /* Volume column */
}

.gantt-cell.frozen:nth-child(3) {
  left: 350px; /* Satuan column */
}

/* Timeline Cells */
.gantt-cell.timeline {
  position: relative;
  min-height: 40px;
  border-right: 1px solid var(--bs-border-color-subtle);
}

/* Bars inside timeline cells */
.gantt-bar {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  height: 24px;
  border-radius: 4px;
}

.gantt-bar.planned {
  background: rgba(13, 110, 253, 0.4);
  border: 2px solid #0d6efd;
  z-index: 1;
}

.gantt-bar.actual {
  background: rgba(253, 126, 20, 1.0);
  border: 2px solid #dc6d08;
  z-index: 2;
}
```

**Task 0.4: File Organization**

```
src/modules/gantt-v2/
├── gantt-frozen-grid.js          # Main component
├── gantt-data-adapter.js         # Adapt Grid data to Gantt format
├── gantt-row-renderer.js         # Render individual rows
├── gantt-bar-renderer.js         # Render timeline bars
├── gantt-timeline-generator.js   # Wrap TimeColumnGenerator
├── gantt-virtual-scroller.js     # Virtual scrolling
├── gantt-interaction-handler.js  # Mouse/keyboard events
├── gantt-milestone-manager.js    # Milestone creation/editing
└── utils/
    ├── date-utils.js             # Date calculations
    ├── bar-position-calculator.js # Calculate bar X position
    └── tree-utils.js             # Hierarchy expand/collapse
```

#### Deliverables

- ✅ Finalized specifications document
- ✅ Data structure interfaces
- ✅ CSS architecture
- ✅ File structure created

---

### PHASE 1: Proof of Concept - Frozen Column Layout

**Duration:** 1.5 days
**Dependencies:** Phase 0 complete

#### Objectives

1. Validate frozen column approach works
2. Prove perfect alignment at all scroll positions
3. Test with 1000+ rows for performance
4. Get user approval before full implementation

#### Tasks

**Task 1.1: Basic Grid Structure (4 hours)**

Create minimal HTML/CSS structure:

```javascript
// gantt-frozen-grid.js
export class GanttFrozenGrid {
  constructor(container, options = {}) {
    this.container = container;
    this.options = {
      rowHeight: 40,
      frozenColumnWidth: 280,
      timelineColumnWidth: 100,
      ...options
    };

    this.state = {
      rows: [],
      columns: [],
      scrollTop: 0,
      scrollLeft: 0
    };
  }

  initialize(data) {
    this._buildDOM();
    this._renderHeaders();
    this._renderRows(data);
  }

  _buildDOM() {
    this.container.innerHTML = '';
    this.container.className = 'gantt-frozen-grid';

    // Single grid container with CSS Grid layout
    const grid = document.createElement('div');
    grid.className = 'gantt-grid-container';
    grid.style.cssText = `
      display: grid;
      grid-template-columns: 280px 70px 70px repeat(20, 100px);
      overflow: auto;
      height: 600px;
    `;

    this.container.appendChild(grid);
    this.gridContainer = grid;
  }

  _renderHeaders() {
    // Frozen headers
    const frozenHeaders = [
      { label: 'Pekerjaan', width: '280px', frozen: true },
      { label: 'Volume', width: '70px', frozen: true },
      { label: 'Satuan', width: '70px', frozen: true }
    ];

    frozenHeaders.forEach((header, i) => {
      const headerCell = document.createElement('div');
      headerCell.className = 'gantt-header-cell frozen';
      headerCell.style.cssText = `
        position: sticky;
        left: ${this._calculateStickyLeft(i)}px;
        z-index: 20;
        background: var(--bs-light);
        font-weight: 600;
        padding: 0.75rem 1rem;
        border-bottom: 2px solid var(--bs-border-color);
      `;
      headerCell.textContent = header.label;
      this.gridContainer.appendChild(headerCell);
    });

    // Timeline headers (hardcoded for POC)
    for (let i = 1; i <= 20; i++) {
      const headerCell = document.createElement('div');
      headerCell.className = 'gantt-header-cell timeline';
      headerCell.style.cssText = `
        background: var(--bs-light);
        font-weight: 600;
        padding: 0.75rem 0.5rem;
        border-bottom: 2px solid var(--bs-border-color);
        text-align: center;
      `;
      headerCell.textContent = `W${i}`;
      this.gridContainer.appendChild(headerCell);
    }
  }

  _renderRows(data) {
    // Render 10 hardcoded rows for POC
    const demoRows = [
      { id: 1, name: '📁 Pekerjaan Tanah', volume: 100, satuan: 'm3', level: 0 },
      { id: 2, name: '  📁 Galian Tanah', volume: 60, satuan: 'm3', level: 1 },
      { id: 3, name: '    📄 Galian Tanah Biasa', volume: 40, satuan: 'm3', level: 2 },
      { id: 4, name: '    📄 Galian Tanah Keras', volume: 20, satuan: 'm3', level: 2 },
      { id: 5, name: '  📁 Urugan Tanah', volume: 40, satuan: 'm3', level: 1 },
      { id: 6, name: '    📄 Urugan Tanah Pilihan', volume: 40, satuan: 'm3', level: 2 },
      { id: 7, name: '📁 Pekerjaan Struktur', volume: 200, satuan: 'm3', level: 0 },
      { id: 8, name: '  📁 Beton', volume: 150, satuan: 'm3', level: 1 },
      { id: 9, name: '    📄 Beton K225', volume: 100, satuan: 'm3', level: 2 },
      { id: 10, name: '    📄 Beton K300', volume: 50, satuan: 'm3', level: 2 }
    ];

    demoRows.forEach(row => {
      // Frozen cells
      const nameCell = this._createCell(row.name, 0, true, row.level);
      const volumeCell = this._createCell(row.volume, 1, true);
      const satuanCell = this._createCell(row.satuan, 2, true);

      this.gridContainer.appendChild(nameCell);
      this.gridContainer.appendChild(volumeCell);
      this.gridContainer.appendChild(satuanCell);

      // Timeline cells (20 weeks)
      for (let i = 0; i < 20; i++) {
        const timelineCell = this._createCell('', i, false);

        // Add demo bar (only on some cells)
        if (row.level === 2 && i >= 2 && i <= 6) {
          const bar = this._createDemoBar(i - 2, 5);
          timelineCell.appendChild(bar);
        }

        this.gridContainer.appendChild(timelineCell);
      }
    });
  }

  _createCell(content, columnIndex, frozen, level = 0) {
    const cell = document.createElement('div');
    cell.className = `gantt-cell ${frozen ? 'frozen' : 'timeline'}`;

    if (frozen) {
      const stickyLeft = this._calculateStickyLeft(columnIndex);
      cell.style.cssText = `
        position: sticky;
        left: ${stickyLeft}px;
        z-index: 10;
        background: white;
        padding: 0.5rem ${columnIndex === 0 ? `${level * 20}px` : '0.5rem'};
        border-bottom: 1px solid var(--bs-border-color);
        border-right: ${columnIndex === 2 ? '2' : '1'}px solid var(--bs-border-color);
      `;
    } else {
      cell.style.cssText = `
        position: relative;
        border-bottom: 1px solid var(--bs-border-color);
        border-right: 1px solid var(--bs-border-color-subtle);
        background: white;
      `;
    }

    cell.textContent = content;
    return cell;
  }

  _calculateStickyLeft(columnIndex) {
    const widths = [0, 280, 350]; // Cumulative widths
    return widths[columnIndex] || 0;
  }

  _createDemoBar(startWeek, duration) {
    const bar = document.createElement('div');
    bar.className = 'gantt-bar planned';
    bar.style.cssText = `
      position: absolute;
      top: 50%;
      left: ${(startWeek / duration) * 100}%;
      width: ${(duration / 5) * 100}%;
      height: 24px;
      transform: translateY(-50%);
      background: rgba(13, 110, 253, 0.4);
      border: 2px solid #0d6efd;
      border-radius: 4px;
    `;
    return bar;
  }
}
```

**Task 1.2: Integration Test (2 hours)**

```javascript
// In jadwal_kegiatan_app.js
_initializeFrozenGantt() {
  const container = document.getElementById('gantt-redesign-container');

  // Create POC instance
  this.ganttFrozenGrid = new GanttFrozenGrid(container, {
    rowHeight: 40,
    frozenColumnWidth: 280,
    timelineColumnWidth: 100
  });

  // Initialize with demo data
  this.ganttFrozenGrid.initialize();

  console.log('✅ Frozen Column Gantt POC initialized');
}
```

**Task 1.3: Alignment Verification (2 hours)**

Create test script to verify alignment:

```javascript
// test-alignment.js
function verifyAlignment() {
  const rows = document.querySelectorAll('.gantt-cell');
  const results = [];

  // Group cells by row
  let currentRow = [];
  rows.forEach((cell, i) => {
    currentRow.push(cell);
    if (currentRow.length === 23) { // 3 frozen + 20 timeline
      results.push(verifyRowAlignment(currentRow));
      currentRow = [];
    }
  });

  console.log('Alignment Test Results:', results);
  return results.every(r => r.aligned);
}

function verifyRowAlignment(rowCells) {
  const tops = rowCells.map(cell => cell.getBoundingClientRect().top);
  const heights = rowCells.map(cell => cell.offsetHeight);

  // All cells in same row should have same top position
  const maxTopDiff = Math.max(...tops) - Math.min(...tops);

  return {
    aligned: maxTopDiff < 1, // Allow <1px difference (sub-pixel)
    maxDiff: maxTopDiff,
    tops,
    heights
  };
}

// Run test
window.testGanttAlignment = verifyAlignment;
```

**Task 1.4: Performance Test (3 hours)**

Test with 1000 rows:

```javascript
_renderLargeDataset() {
  const rows = [];

  // Generate 1000 rows
  for (let i = 0; i < 1000; i++) {
    rows.push({
      id: i,
      name: `Task ${i}`,
      volume: Math.floor(Math.random() * 100),
      satuan: 'm3',
      level: i % 3 // Vary levels
    });
  }

  const startTime = performance.now();
  this._renderRows(rows);
  const endTime = performance.now();

  console.log(`Rendered 1000 rows in ${endTime - startTime}ms`);

  // Test scroll performance
  this._testScrollPerformance();
}

_testScrollPerformance() {
  const container = this.gridContainer;
  let frameCount = 0;
  let lastTime = performance.now();

  const measureFPS = () => {
    frameCount++;
    const now = performance.now();
    const elapsed = now - lastTime;

    if (elapsed >= 1000) {
      console.log(`Scroll FPS: ${frameCount}`);
      frameCount = 0;
      lastTime = now;
    }

    if (container.scrollTop < container.scrollHeight - container.clientHeight) {
      requestAnimationFrame(measureFPS);
    }
  };

  // Auto-scroll to test
  container.addEventListener('scroll', measureFPS, { once: true });
  container.scrollTop += 10;
}
```

#### Deliverables

- ✅ Working POC with 10 rows
- ✅ Perfect alignment verified (< 1px diff)
- ✅ Performance test results (1000 rows, 60fps scroll)
- ✅ User approval to proceed

#### Success Metrics

- Zero pixel misalignment at any scroll position
- Render 1000 rows in < 500ms
- Maintain 60fps during scroll
- User confirms visual correctness

---

### PHASE 2: Data Integration - TimeColumnGenerator & StateManager

**Duration:** 1 day
**Dependencies:** Phase 1 approved

#### Objectives

1. Replace hardcoded timeline columns with TimeColumnGenerator
2. Use StateManager for progress data
3. Match Grid View's time segmentation exactly
4. Verify data consistency between Grid and Gantt

#### Tasks

**Task 2.1: TimeColumnGenerator Integration (3 hours)**

```javascript
// gantt-timeline-generator.js
import { TimeColumnGenerator } from '@modules/grid/time-column-generator.js';

export class GanttTimelineGenerator {
  constructor(tahapanList, timeScale) {
    this.tahapanList = tahapanList;
    this.timeScale = timeScale; // 'week' or 'month'
    this.columnGenerator = new TimeColumnGenerator(tahapanList);
  }

  /**
   * Generate timeline columns matching Grid View
   */
  generateColumns() {
    // Use Grid's TimeColumnGenerator
    const gridColumns = this.columnGenerator.generate();

    // Transform to Gantt format
    return gridColumns.map((col, index) => ({
      field: col.column_id,
      headerName: col.label,
      dateRange: {
        start: col.start_date,
        end: col.end_date
      },
      width: this.timeScale === 'week' ? 100 : 150,
      index: index,
      type: 'timeline'
    }));
  }

  /**
   * Get column for specific date
   */
  getColumnForDate(date) {
    const columns = this.generateColumns();
    return columns.find(col => {
      const start = new Date(col.dateRange.start);
      const end = new Date(col.dateRange.end);
      return date >= start && date <= end;
    });
  }

  /**
   * Calculate bar position within columns
   */
  calculateBarPosition(startDate, endDate, columns) {
    const startCol = this.getColumnForDate(startDate);
    const endCol = this.getColumnForDate(endDate);

    if (!startCol || !endCol) return null;

    return {
      startColumnIndex: startCol.index,
      endColumnIndex: endCol.index,
      startOffset: this._calculateOffsetInColumn(startDate, startCol),
      endOffset: this._calculateOffsetInColumn(endDate, endCol)
    };
  }

  _calculateOffsetInColumn(date, column) {
    const colStart = new Date(column.dateRange.start);
    const colEnd = new Date(column.dateRange.end);
    const colDuration = colEnd - colStart;
    const dateOffset = date - colStart;

    return (dateOffset / colDuration) * 100; // % within column
  }
}
```

**Task 2.2: StateManager Integration (3 hours)**

```javascript
// gantt-data-adapter.js
export class GanttDataAdapter {
  constructor(stateManager, tahapanList, flatPekerjaan) {
    this.stateManager = stateManager;
    this.tahapanList = tahapanList;
    this.flatPekerjaan = flatPekerjaan;
  }

  /**
   * Adapt Grid data to Gantt row format
   */
  prepareGanttRows() {
    const rows = [];

    // Only use pekerjaan nodes (leaf nodes)
    const pekerjaanNodes = this.flatPekerjaan.filter(n => n.type === 'pekerjaan');

    pekerjaanNodes.forEach(node => {
      rows.push({
        id: node.id,
        type: node.type,
        level: node.level,
        expanded: node.expanded || true,

        // Frozen column data
        name: node.nama || 'Unknown',
        kode: node.kode || '',
        volume: node.volume || 0,
        satuan: node.satuan || '-',

        // Parent info for hierarchy
        klasifikasi_id: node.klasifikasi_id,
        klasifikasi_name: node.klasifikasi_name,
        sub_klasifikasi_id: node.sub_klasifikasi_id,
        sub_klasifikasi_name: node.sub_klasifikasi_name,

        // Timeline data from StateManager
        tahapanProgress: this._getTahapanProgress(node.id),

        // Aggregated bars (calculated from tahapan)
        bars: this._calculateAggregatedBars(node)
      });
    });

    return rows;
  }

  _getTahapanProgress(pekerjaanId) {
    const progressMap = new Map();

    this.tahapanList.forEach(tahapan => {
      const planned = this.stateManager.getCellValue(
        pekerjaanId,
        tahapan.column_id,
        'planned'
      );
      const actual = this.stateManager.getCellValue(
        pekerjaanId,
        tahapan.column_id,
        'actual'
      );

      progressMap.set(tahapan.column_id, {
        planned: planned || 0,
        actual: actual || 0
      });
    });

    return progressMap;
  }

  _calculateAggregatedBars(node) {
    // Calculate overall start/end dates from tahapan with progress
    let earliestStart = null;
    let latestEnd = null;
    let totalPlanned = 0;
    let totalActual = 0;

    this.tahapanList.forEach(tahapan => {
      const progress = this.stateManager.getCellValue(
        node.id,
        tahapan.column_id,
        'planned'
      );

      if (progress && progress > 0) {
        const start = new Date(tahapan.start_date);
        const end = new Date(tahapan.end_date);

        if (!earliestStart || start < earliestStart) {
          earliestStart = start;
        }
        if (!latestEnd || end > latestEnd) {
          latestEnd = end;
        }

        totalPlanned += progress;
        totalActual += this.stateManager.getCellValue(
          node.id,
          tahapan.column_id,
          'actual'
        ) || 0;
      }
    });

    const avgPlanned = totalPlanned / this.tahapanList.length;
    const avgActual = totalActual / this.tahapanList.length;

    return {
      planned: {
        startDate: earliestStart || new Date(node.tgl_mulai_rencana),
        endDate: latestEnd || new Date(node.tgl_selesai_rencana),
        progress: Math.round(avgPlanned)
      },
      actual: {
        startDate: earliestStart || new Date(node.tgl_mulai_realisasi),
        endDate: latestEnd || new Date(node.tgl_selesai_realisasi),
        progress: Math.round(avgActual)
      }
    };
  }
}
```

**Task 2.3: Update GanttFrozenGrid (2 hours)**

```javascript
// gantt-frozen-grid.js
initialize(jadwalKegiatanApp) {
  // Get data from app
  const tahapanList = jadwalKegiatanApp.state.tahapanList;
  const flatPekerjaan = jadwalKegiatanApp.state.flatPekerjaan;
  const stateManager = jadwalKegiatanApp.stateManager;

  // Setup timeline generator
  this.timelineGen = new GanttTimelineGenerator(tahapanList, 'week');
  this.timelineColumns = this.timelineGen.generateColumns();

  // Setup data adapter
  this.dataAdapter = new GanttDataAdapter(stateManager, tahapanList, flatPekerjaan);
  this.rows = this.dataAdapter.prepareGanttRows();

  // Build DOM
  this._buildDOM();
  this._renderHeaders();
  this._renderRows();

  console.log(`✅ Gantt initialized with ${this.rows.length} rows, ${this.timelineColumns.length} columns`);
}
```

#### Deliverables

- ✅ Timeline columns match Grid View exactly
- ✅ Progress data from StateManager
- ✅ Bars positioned based on tahapan dates
- ✅ Console log confirms data consistency

---

### PHASE 3: Core Features - Tree, Bars, Interaction

**Duration:** 2 days
**Dependencies:** Phase 2 complete

#### Objectives

1. Hierarchical tree with expand/collapse
2. Dual bars (planned + actual) with progress fill
3. Mouse interactions (hover, click, drag)
4. Tooltip with task details

#### Tasks

**Task 3.1: Hierarchical Tree (4 hours)**

**Task 3.2: Bar Rendering (4 hours)**

**Task 3.3: Interaction Handlers (4 hours)**

**Task 3.4: Tooltips (2 hours)**

---

### PHASE 4: Advanced Features - Zoom, Search, Milestones

**Duration:** 1.5 days
**Dependencies:** Phase 3 complete

#### Tasks

**Task 4.1: Zoom (Week/Month toggle) (3 hours)**

**Task 4.2: Search & Highlight (2 hours)**

**Task 4.3: Fit to Screen (2 hours)**

**Task 4.4: Today Marker (2 hours)**

**Task 4.5: Milestone Creation (3 hours)**

---

### PHASE 5: Performance & Polish

**Duration:** 1 day
**Dependencies:** Phase 4 complete

#### Tasks

**Task 5.1: Virtual Scrolling (4 hours)**

**Task 5.2: Responsive Design (2 hours)**

**Task 5.3: Dark Mode (1 hour)**

**Task 5.4: Cross-browser Testing (1 hour)**

---

## Timeline Summary

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 0 | 0.5 days | Architecture & Design |
| Phase 1 | 1.5 days | POC with Perfect Alignment |
| Phase 2 | 1 day | Data Integration |
| Phase 3 | 2 days | Core Features |
| Phase 4 | 1.5 days | Advanced Features |
| Phase 5 | 1 day | Performance & Polish |
| **TOTAL** | **7.5 days** | **Production-Ready Gantt** |

---

## Risk Mitigation

### Risk 1: Sticky positioning browser compatibility

**Mitigation:** Fallback to JavaScript-based positioning for IE11

### Risk 2: Performance with 1000+ rows

**Mitigation:** Virtual scrolling (Phase 5), only render visible rows

### Risk 3: Bar positioning accuracy

**Mitigation:** Use exact date calculations from TimeColumnGenerator

### Risk 4: StateManager data changes

**Mitigation:** Subscribe to StateManager events for real-time updates

---

## Success Metrics

- ✅ Zero pixel misalignment (verified in Phase 1)
- ✅ Same time segmentation as Grid (verified in Phase 2)
- ✅ Same progress data as Grid (verified in Phase 2)
- ✅ 60fps scrolling with 1000+ tasks (verified in Phase 5)
- ✅ Feature parity with requirements (verified in Phase 4)

---

## Next Step: User Approval

**Question for User:**

Apakah roadmap ini sudah sesuai? Saya siap mulai **Phase 0 & 1** (2 hari) untuk membuat **Proof of Concept** yang menunjukkan:

1. ✅ Perfect alignment (zero pixel drift)
2. ✅ Timeline columns match Grid View
3. ✅ Smooth 60fps scrolling
4. ✅ Performance with 1000 rows

Setelah POC berhasil, kita bisa lanjut ke Phase 2-5 untuk implementasi lengkap.

**Approve to start?**
