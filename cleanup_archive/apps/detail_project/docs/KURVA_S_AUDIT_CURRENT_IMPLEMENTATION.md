# Kurva S - Current Implementation Audit

**Date**: 2025-11-26
**Phase**: Pre-2F (Baseline Assessment)
**Status**: ✅ Audit Complete

---

## 📋 Executive Summary

### Current Status
The Kurva S (S-Curve) feature is **ALREADY IMPLEMENTED** with a sophisticated, production-ready architecture. The current implementation includes:

- ✅ **Dual curve display** (Planned vs Actual)
- ✅ **Interactive charts** (ECharts library)
- ✅ **Intelligent curve calculation** (3 algorithms with auto-selection)
- ✅ **Volume-weighted progress** (accurate project tracking)
- ✅ **Responsive design** (dark mode, tooltips)
- ✅ **Tab integration** (lazy rendering on tab activation)

### Key Finding
**The Kurva S already displays both Planned and Actual curves simultaneously**, which was a major requirement for Phase 2E.2. However, it operates on **SINGLE MODE DATA** (not dual mode aware).

### Gap Analysis
The primary gap is **integration with Phase 2E.1 dual state architecture**:
- Current: Uses `state.modifiedCells` and `state.assignmentMap` (single source)
- Needed: Switch between `plannedState` and `actualState` based on `progressMode`

---

## 🏗️ Architecture Overview

### File Structure

```
detail_project/static/detail_project/js/jadwal_pekerjaan/kelola_tahapan/
├── kurva_s_module.js       (734 lines) - Core chart logic
└── kurva_s_tab.js          (79 lines)  - Tab activation handler

detail_project/templates/detail_project/
└── kelola_tahapan_grid_modern.html - Contains <div id="scurve-chart">
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Chart Library** | ECharts 5.x | Interactive S-curve rendering |
| **Data Source** | `state.modifiedCells`, `state.assignmentMap` | Cell values and assignments |
| **Volume Data** | `state.volumeMap` | Pekerjaan volumes for weighting |
| **Module System** | Custom registry | Lazy loading and lifecycle |
| **Theme Support** | CSS variables (`data-bs-theme`) | Dark/light mode |

### Dependencies

```javascript
// External
window.echarts - ECharts library

// Internal
window.KelolaTahapanPageApp - Application bootstrap
window.KelolaTahapanModuleManifest - Module registry
state.modifiedCells - Cell value map
state.assignmentMap - Assignment map
state.volumeMap - Volume lookup
state.timeColumns - Time period columns
state.flatPekerjaan - Pekerjaan list
```

---

## 🔍 Detailed Component Analysis

### 1. kurva_s_module.js (Core Logic)

#### 1.1 Data Calculation Architecture

The module implements a **sophisticated 3-tier calculation strategy**:

```
┌─────────────────────────────────────────────────┐
│         PLANNED CURVE CALCULATION               │
├─────────────────────────────────────────────────┤
│                                                 │
│  Strategy 1: Volume-Based (Preferred)          │
│  ├─ Uses: Assignment data + Volume weights     │
│  ├─ Algorithm: Accumulate assigned volumes     │
│  └─ Best for: Projects with assignments        │
│                                                 │
│  Strategy 2: Ideal S-Curve (Fallback)          │
│  ├─ Uses: Sigmoid (logistic) function          │
│  ├─ Formula: 100 / (1 + e^(-k*(t - t₀)))      │
│  └─ Best for: New projects without data        │
│                                                 │
│  Strategy 3: Linear (Last Resort)              │
│  ├─ Uses: Equal distribution across periods    │
│  ├─ Formula: P(t) = (100/n) * (t+1)           │
│  └─ Best for: Backwards compatibility          │
│                                                 │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│         ACTUAL CURVE CALCULATION                │
├─────────────────────────────────────────────────┤
│                                                 │
│  Volume-Weighted Progress (Always)              │
│  ├─ Uses: Cell values + Volume weights         │
│  ├─ Algorithm: Sum (volume × progress%)        │
│  └─ Cumulative: Running total across periods   │
│                                                 │
└─────────────────────────────────────────────────┘
```

#### 1.2 Key Functions

##### `calculateVolumeBasedPlannedCurve()` (lines 205-254)
**Purpose**: Calculate planned curve from assignment data

**Algorithm**:
```javascript
// Pseudocode
for each column:
  identify pekerjaan assigned to this column
  add their TOTAL volumes (not progress %)
  accumulate to get cumulative planned volume
  convert to percentage of total project volume
```

**Example**:
```
Project: 3 pekerjaan (100m², 200m², 100m² = 400m² total)
- Pekerjaan A (100m²) assigned to Week 1
- Pekerjaan B (200m²) assigned to Week 2
- Pekerjaan C (100m²) assigned to Week 3

Result:
- Week 1: 25%  (100/400)
- Week 2: 75%  (300/400)
- Week 3: 100% (400/400)
```

**Critical Code**:
```javascript
// Lines 228-243
let cumulativePlannedVolume = 0;
const assignedPekerjaan = new Set(); // Prevent double-counting

columns.forEach((col, index) => {
  const assignedInThisColumn = columnAssignments.get(index) || new Set();

  assignedInThisColumn.forEach((pekerjaanId) => {
    if (!assignedPekerjaan.has(pekerjaanId)) {
      const volume = getVolumeForPekerjaan(volumeLookup, pekerjaanId, 1);
      cumulativePlannedVolume += volume;
      assignedPekerjaan.add(pekerjaanId);
    }
  });

  const plannedPercent = totalVolume > 0
    ? Math.min(100, Math.max(0, (cumulativePlannedVolume / totalVolume) * 100))
    : 0;

  plannedSeries.push(Number(plannedPercent.toFixed(2)));
});
```

##### `calculateIdealSCurve()` (lines 288-305)
**Purpose**: Generate sigmoid-based S-curve for new projects

**Mathematical Formula**:
```
P(t) = 100 / (1 + e^(-k*(t - t₀)))

Where:
- t = time period index (0 to n-1)
- t₀ = midpoint (n/2)
- k = steepness factor (default: 0.8)
- P(t) = cumulative percentage at time t
```

**Curve Properties**:
- Starts near 0% (slow ramp-up)
- Accelerates in middle (peak productivity)
- Slows near 100% (completion/tapering)

**Steepness Options**:
```
k = 0.5  →  Gentle S-curve (gradual)
k = 0.8  →  Moderate S-curve (default, balanced)
k = 1.2  →  Steep S-curve (aggressive)
```

**Code**:
```javascript
// Lines 296-302
columns.forEach((col, index) => {
  const t = index;
  const exponent = -steepnessFactor * (t - midpoint);
  const sigmoid = 100 / (1 + Math.exp(exponent));
  plannedSeries.push(Number(sigmoid.toFixed(2)));
});
```

##### `calculatePlannedCurve()` (lines 378-414)
**Purpose**: Hybrid strategy selector

**Decision Flow**:
```javascript
// Lines 384-410
const hasAssignments = cellValues && cellValues.size > 0;

if (hasAssignments) {
  // Strategy 1: Volume-based (most accurate)
  const volumeBased = calculateVolumeBasedPlannedCurve(...);
  if (volumeBased.length > 0 && volumeBased[volumeBased.length - 1] > 0) {
    return volumeBased;
  }
}

if (useIdealCurve) {
  // Strategy 2: Ideal S-curve (realistic fallback)
  return calculateIdealSCurve(columns, steepnessFactor);
}

if (fallbackToLinear) {
  // Strategy 3: Linear (last resort)
  return calculateLinearPlannedCurve(columns);
}

return []; // Ultimate fallback
```

##### `buildDataset()` (lines 416-505)
**Purpose**: Build complete dataset for chart

**Process**:
```javascript
// 1. Get time columns (sorted by date)
const columns = getColumns(state);

// 2. Build lookup maps
const volumeLookup = buildVolumeLookup(state);      // pekerjaanId → volume
const cellValues = buildCellValueMap(state);        // cellKey → percentage
const pekerjaanIds = collectPekerjaanIds(state);    // Set of all IDs

// 3. Calculate total project volume
let totalVolume = 0;
pekerjaanIds.forEach((id) => {
  totalVolume += getVolumeForPekerjaan(volumeLookup, id, 1);
});

// 4. Calculate PLANNED curve (hybrid strategy)
const plannedSeries = calculatePlannedCurve(
  columns, volumeLookup, cellValues, totalVolume, getVolumeForPekerjaan
);

// 5. Calculate ACTUAL curve (volume-weighted)
const actualSeries = [];
let cumulativeActualVolume = 0;

columns.forEach((col, index) => {
  cumulativeActualVolume += columnTotals[index] || 0;
  const actualPercent = totalVolume > 0
    ? Math.min(100, (cumulativeActualVolume / totalVolume) * 100)
    : 0;
  actualSeries.push(Number(actualPercent.toFixed(2)));
});

// 6. Build detailed data for tooltips
const details = columns.map((col, index) => ({
  label: labels[index],
  planned: plannedSeries[index] || 0,
  actual: actualSeries[index] || 0,
  variance: (actualSeries[index] || 0) - (plannedSeries[index] || 0),
  start: col.startDate,
  end: col.endDate,
  tooltip: col.tooltip || labels[index],
}));

return { labels, planned: plannedSeries, actual: actualSeries, details };
```

**Output Format**:
```javascript
{
  labels: ['Week 1', 'Week 2', ...],           // X-axis labels
  planned: [25, 50, 75, 100],                  // Planned curve data
  actual: [20, 45, 70, 90],                    // Actual curve data
  details: [                                    // Tooltip data
    {
      label: 'Week 1',
      planned: 25,
      actual: 20,
      variance: -5,
      start: Date(2025-01-01),
      end: Date(2025-01-07),
      tooltip: 'Week 1 (Jan 1-7)'
    },
    ...
  ],
  totalVolume: 1000,                           // Total project volume
  columnTotals: [200, 250, 250, 300],          // Per-column volumes
}
```

#### 1.3 Chart Configuration

##### `createChartOption()` (lines 529-647)
**Purpose**: Build ECharts configuration object

**Key Features**:

1. **Dual Series Configuration**:
```javascript
series: [
  {
    name: 'Planned',
    type: 'line',
    smooth: true,
    data: data.planned,
    lineStyle: {
      color: colors.plannedLine,  // Blue
      width: 2,
      type: 'dashed',             // Dashed line
    },
    areaStyle: {
      color: colors.plannedArea,  // Semi-transparent fill
    },
    symbolSize: 6,
  },
  {
    name: 'Actual',
    type: 'line',
    smooth: true,
    data: data.actual,
    lineStyle: {
      color: colors.actualLine,   // Green
      width: 3,                   // Thicker line
    },
    areaStyle: {
      color: colors.actualArea,
    },
    symbolSize: 7,
  },
]
```

2. **Rich Tooltip Formatter** (lines 538-572):
```javascript
tooltip: {
  trigger: 'axis',
  formatter: (params) => {
    const detail = data.details[index];
    const variance = detail.variance;

    // Color-coded variance
    let varianceColor;
    if (variance > 5) {
      varianceColor = '#22c55e'; // Green (ahead)
    } else if (variance < -5) {
      varianceColor = '#ef4444'; // Red (behind)
    } else {
      varianceColor = '#3b82f6'; // Blue (on track)
    }

    return `
      <strong>${label}</strong>
      <div>Periode: ${start} - ${end}</div>
      <div>Rencana: <strong>${planned}%</strong></div>
      <div>Aktual: <strong>${actual}%</strong></div>
      <div style="color:${varianceColor}">
        Variance: <strong>${varianceText}</strong>
      </div>
    `;
  },
}
```

3. **Theme Support** (lines 53-75):
```javascript
function getThemeColors() {
  const theme = document.documentElement.getAttribute('data-bs-theme');

  if (theme === 'dark') {
    return {
      text: '#f8fafc',
      axis: '#cbd5f5',
      plannedLine: '#60a5fa',     // Light blue
      actualLine: '#34d399',      // Light green
      gridLine: '#334155',
    };
  }

  return {
    text: '#1f2937',
    axis: '#374151',
    plannedLine: '#0d6efd',       // Dark blue
    actualLine: '#198754',        // Dark green
    gridLine: '#e5e7eb',
  };
}
```

4. **Responsive Grid**:
```javascript
grid: {
  left: '4%',
  right: '4%',
  top: '12%',
  bottom: '6%',
  containLabel: true,  // Auto-adjust for labels
}
```

#### 1.4 Module Lifecycle

##### `init()` (line 685)
```javascript
function init(context = {}) {
  return refresh(context);
}
```

##### `refresh()` (lines 664-683)
```javascript
function refresh(context = {}) {
  // 1. Resolve state
  const state = resolveState(context.state);
  if (!state) return 'legacy';

  // 2. Ensure chart instance exists
  const chart = ensureChartInstance(state);
  if (chart === 'legacy') return 'legacy';

  // 3. Build dataset from state
  const dataset = buildDataset(state, context) || buildFallbackDataset();

  // 4. Create chart options
  const option = createChartOption(dataset);

  // 5. Update chart
  chart.setOption(option, true); // true = replace all options

  // 6. Store for debugging
  moduleStore.dataset = dataset;
  moduleStore.option = option;

  return chart;
}
```

##### `resize()` (lines 689-700)
```javascript
function resize(context = {}) {
  const state = resolveState(context.state);
  if (!state || !state.scurveChart) return 'legacy';

  try {
    state.scurveChart.resize();  // ECharts resize API
  } catch (error) {
    bootstrap.log.warn('Resize failed', error);
  }

  return state.scurveChart;
}
```

---

### 2. kurva_s_tab.js (Tab Integration)

#### Purpose
Handles lazy rendering and resize on tab activation.

#### Key Logic

```javascript
// Lines 34-54
function bindTabActivation(kurva) {
  const tab = document.getElementById('scurve-tab');
  if (!tab) return;

  tab.addEventListener('shown.bs.tab', () => {
    // Option 1: Refresh view (if method exists)
    const result = kurva.refreshView
      ? kurva.refreshView({ reason: 'tab-shown', rebuild: false })
      : null;

    // Option 2: Init or resize (fallback)
    if (result === 'legacy' || result === null) {
      if (!kurva.getChart || !kurva.getChart()) {
        kurva.init && kurva.init({ reason: 'tab-shown' });
      } else if (kurva.resize) {
        kurva.resize();
      }
    }
  });

  moduleStore.bound = true;
}
```

**Why Tab Activation?**
- ECharts requires visible DOM element for initialization
- Tab content is hidden on page load (`display: none`)
- Chart must be initialized/resized when tab becomes visible
- Prevents rendering issues and dimension calculations

---

## 🔧 Current Data Flow

### End-to-End Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERACTION                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  User edits cells in grid → modifiedCells Map updated      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  User clicks "Kurva S" tab                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  kurva_s_tab.js: 'shown.bs.tab' event fires                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  kurva_s_module.js: refresh() called                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  buildDataset(state):                                       │
│  ├─ volumeLookup = buildVolumeLookup(state.volumeMap)      │
│  ├─ cellValues = buildCellValueMap(state)                  │
│  │   ├─ Merge state.assignmentMap                          │
│  │   └─ Merge state.modifiedCells                          │
│  ├─ Calculate totalVolume                                   │
│  ├─ Calculate PLANNED curve (hybrid strategy)              │
│  └─ Calculate ACTUAL curve (volume-weighted)               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  createChartOption(dataset):                                │
│  ├─ Get theme colors                                        │
│  ├─ Configure dual series (Planned + Actual)               │
│  ├─ Setup tooltip formatter                                 │
│  └─ Setup legend, axes, grid                                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  chart.setOption(option, true):                             │
│  └─ ECharts renders dual curve S-chart                     │
└─────────────────────────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              USER SEES KURVA S CHART                        │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Progress %                                         │    │
│  │ 100┤                              ╱───── Actual    │    │
│  │    │                           ╱─╱                 │    │
│  │ 75┤                        ╱─╱                     │    │
│  │    │                    ╱─╱                        │    │
│  │ 50┤             ...──╱╱        ╱─── Planned       │    │
│  │    │         ...──  ╱      ...─                    │    │
│  │ 25┤    ...──      ╱  ...──                        │    │
│  │    │...──        ╱...──                            │    │
│  │  0┼──┴──┴──┴──┴──┴──┴──┴──┴──┴──→ Time           │    │
│  │   W1 W2 W3 W4 W5 W6 W7 W8 W9 W10                 │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### State Dependencies

```javascript
// Current implementation reads from:
state.modifiedCells      // Map<cellKey, value> - user edits
state.assignmentMap      // Map<cellKey, value> - saved assignments
state.volumeMap          // Map<pekerjaanId, volume> - volumes
state.timeColumns        // Array<Column> - time periods
state.flatPekerjaan      // Array<Node> - pekerjaan list

// Does NOT currently use:
state.progressMode       // ❌ Not used (always shows single mode)
state.plannedState       // ❌ Not used (Phase 2E.1 architecture)
state.actualState        // ❌ Not used (Phase 2E.1 architecture)
```

---

## 🎯 Gap Analysis for Phase 2F

### What Works ✅

1. **Dual Curve Display**: Already shows Planned vs Actual simultaneously
2. **Interactive Features**: Tooltips, hover effects, legend toggle
3. **Theme Support**: Dark/light mode color schemes
4. **Responsive**: Grid layout adapts to container
5. **Performance**: Lazy rendering on tab activation
6. **Sophisticated Algorithms**: 3-tier calculation strategy
7. **Volume Weighting**: Accurate project progress calculation
8. **Tab Integration**: Proper lifecycle management

### What's Missing ❌

#### 1. **Dual Mode Awareness** (Critical)
**Problem**: Uses single data source (`state.modifiedCells`)
**Impact**: Shows only one mode's data, not dual tracking

**Current Code** (lines 128-149):
```javascript
function buildCellValueMap(state) {
  const map = new Map();

  // ❌ Uses shared state (single mode only)
  if (state.assignmentMap instanceof Map) {
    state.assignmentMap.forEach((value, key) => assignValue(key, value));
  }

  if (state.modifiedCells instanceof Map) {
    state.modifiedCells.forEach((value, key) => assignValue(key, value));
  }

  return map;
}
```

**Needed**:
```javascript
function buildCellValueMap(state, progressMode) {
  const map = new Map();

  // ✅ Mode-aware state selection
  const modeState = progressMode === 'actual'
    ? state.actualState
    : state.plannedState;

  if (modeState.assignmentMap instanceof Map) {
    modeState.assignmentMap.forEach((value, key) => assignValue(key, value));
  }

  if (modeState.modifiedCells instanceof Map) {
    modeState.modifiedCells.forEach((value, key) => assignValue(key, value));
  }

  return map;
}
```

#### 2. **Mode Switching UI** (Medium Priority)
**Problem**: No way to toggle between Perencanaan/Realisasi curves
**Impact**: Can't compare modes visually

**Needed**: Add mode selector in Kurva S tab
```html
<!-- In Kurva S tab content -->
<div class="kurva-s-mode-selector mb-3">
  <label class="form-label">Tampilkan Data:</label>
  <div class="btn-group" role="group">
    <input type="radio" class="btn-check" name="kurvaSMode" id="kurva-planned" value="planned" checked>
    <label class="btn btn-outline-info btn-sm" for="kurva-planned">
      Perencanaan
    </label>

    <input type="radio" class="btn-check" name="kurvaSMode" id="kurva-actual" value="actual">
    <label class="btn btn-outline-success btn-sm" for="kurva-actual">
      Realisasi
    </label>

    <input type="radio" class="btn-check" name="kurvaSMode" id="kurva-both" value="both">
    <label class="btn btn-outline-primary btn-sm" for="kurva-both">
      Kedua Kurva
    </label>
  </div>
</div>
```

#### 3. **Dual Dataset Configuration** (Medium Priority)
**Problem**: Current implementation shows "Planned" vs "Actual" but both come from same mode data
**Impact**: Misleading labels when in Realisasi mode

**Needed**: When `progressMode === 'both'`, build two separate datasets:
```javascript
// Planned curve from plannedState
const plannedDataset = buildDataset(state, 'planned');

// Actual curve from actualState
const actualDataset = buildDataset(state, 'actual');

// Merge for chart
const combinedDataset = {
  labels: plannedDataset.labels,
  planned: plannedDataset.actual, // Use actual from planned mode
  actual: actualDataset.actual,   // Use actual from actual mode
  details: mergDetails(plannedDataset.details, actualDataset.details),
};
```

#### 4. **Backend API Mode Support** (Low Priority - Already Done?)
**Check**: Does the data fetch API support `?mode=planned|actual`?

**Current**: Kurva S reads from client-side state only (no fetch on tab open)
**Conclusion**: No backend changes needed (data already in state from grid)

---

## 📊 Feature Matrix Comparison

| Feature | Current Implementation | Phase 2E.2 Requirements | Gap |
|---------|----------------------|-------------------------|-----|
| **Dual Curve Display** | ✅ Yes (Planned + Actual) | ✅ Required | None |
| **Interactive Tooltips** | ✅ Yes (variance shown) | ✅ Required | None |
| **Variance Calculation** | ✅ Yes (per period) | ✅ Required | None |
| **Color-Coded Variance** | ✅ Yes (red/green/blue) | ✅ Required | None |
| **Theme Support** | ✅ Yes (dark/light) | ⚪ Nice-to-have | None |
| **Volume Weighting** | ✅ Yes (sophisticated) | ⚪ Nice-to-have | None |
| **Smooth Curves** | ✅ Yes (bezier interpolation) | ⚪ Nice-to-have | None |
| **Area Fill** | ✅ Yes (semi-transparent) | ⚪ Nice-to-have | None |
| **Legend Toggle** | ✅ Yes (ECharts built-in) | ⚪ Nice-to-have | None |
| **Export Support** | ❌ No (ECharts has it but not wired) | ⚪ Nice-to-have | Medium |
| **Mode Switching** | ❌ No (single mode only) | ✅ Required | **Critical** |
| **Dual State Integration** | ❌ No (uses shared state) | ✅ Required | **Critical** |
| **Mode Label Accuracy** | ⚠️ Misleading (always says "Planned" vs "Actual") | ✅ Required | **High** |

---

## 🚀 Phase 2F Implementation Strategy

### Scope Decision

Given that **Kurva S dual curve already exists**, Phase 2F should focus on:

1. **Integration with Phase 2E.1 Dual State** (Critical)
2. **Mode Switching UI** (High)
3. **Accurate Curve Labeling** (High)
4. **Export Enhancement** (Medium)

### Effort Estimate Revision

| Original Phase 2E.2 Plan | Actual Effort Needed |
|--------------------------|----------------------|
| Backend variance calculation | ✅ Already done (in chart) |
| Dual curve Kurva S | ✅ Already implemented |
| Frontend variance columns | ❌ Out of scope (grid feature) |
| Kurva S dual mode integration | ⏳ **2-3 hours** (new task) |
| Mode switching UI | ⏳ **1-2 hours** (new task) |
| Export enhancements | ⏳ **1 hour** (optional) |
| Testing | ⏳ **1 hour** |

**New Phase 2F Estimate**: **5-7 hours** (instead of 10+ hours)

### Proposed Phase 2F Roadmap

#### Phase 2F.1: Dual Mode Integration (3 hours)
1. Modify `buildCellValueMap()` to accept `progressMode` parameter
2. Update `buildDataset()` to use mode-specific state
3. Add mode detection logic in `refresh()`
4. Test with both modes

#### Phase 2F.2: Mode Switching UI (2 hours)
1. Add mode selector radio buttons in Kurva S tab
2. Wire up event listeners
3. Update chart labels based on mode
4. Add "Both Modes" option (overlay curves from both states)

#### Phase 2F.3: Polish & Export (2 hours)
1. Fix curve labels (e.g., "Perencanaan" vs "Realisasi" instead of "Planned" vs "Actual")
2. Add export button (PNG, SVG via ECharts API)
3. Add loading indicator
4. Testing and documentation

---

## 🎨 Visualization Examples

### Current Output (Single Mode)

```
Progress %
100% ┤                                  ╱─────── Actual (solid green)
     │                               ╱─╱
 75% ┤                            ╱─╱
     │                         ╱─╱
 50% ┤                  ...──╱╱          ╱──── Planned (dashed blue)
     │              ...──  ╱         ...─
 25% ┤        ...──      ╱     ...──
     │  ...──         ╱  ...──
  0% ┼──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──→ Time
     W1 W2 W3 W4 W5 W6 W7 W8 W9 W10 W11 W12

Legend:
──── Planned (blue dashed)  ← Volume-based or sigmoid
──── Actual (green solid)   ← From modifiedCells/assignmentMap
████ Semi-transparent fill
```

**Note**: "Planned" curve is calculated, "Actual" is from cell data. Both use SAME MODE data currently.

### Needed Output (Dual Mode - Phase 2F)

```
Progress %
100% ┤                                  ╱─────── Realisasi (solid green)
     │                               ╱─╱
 75% ┤                            ╱─╱
     │                         ╱─╱       ╱──── Perencanaan (dashed blue)
 50% ┤                  ...──╱╱    ...──
     │              ...──  ╱   ...──
 25% ┤        ...──      ╱...──
     │  ...──         ╱..──
  0% ┼──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──→ Time
     W1 W2 W3 W4 W5 W6 W7 W8 W9 W10 W11 W12

Legend:
──── Perencanaan (blue dashed)  ← From plannedState
──── Realisasi (green solid)    ← From actualState
████ Variance area (red if behind, green if ahead)
```

---

## 🔍 Code Quality Assessment

### Strengths ✅

1. **Well-Documented**: Extensive JSDoc comments explaining algorithms
2. **Modular Design**: Clear separation of concerns (calculation vs rendering)
3. **Defensive Coding**: Type checks, fallbacks, error handling
4. **Performance**: Lazy rendering, efficient Map usage
5. **Maintainable**: Readable variable names, logical flow
6. **Testable**: Pure functions with clear inputs/outputs

### Areas for Improvement 🔧

1. **Magic Numbers**: Steepness factor (0.8), variance thresholds (±5%) hardcoded
2. **No Unit Tests**: Complex calculation logic should have tests
3. **Limited Configuration**: No way to customize curve calculation method
4. **Tight Coupling**: Direct DOM access (`document.getElementById`)
5. **Error Reporting**: Silent failures (`return 'legacy'`)

### Technical Debt

| Issue | Severity | Effort to Fix |
|-------|----------|---------------|
| No unit tests for calculation functions | Medium | 3 hours |
| Hardcoded thresholds | Low | 30 min |
| 'legacy' return values unclear | Low | 1 hour |
| No loading state | Low | 30 min |

---

## 📋 Integration Points

### With Phase 2E.1 Architecture

```javascript
// Current state structure (Phase 2E.1)
state = {
  progressMode: 'planned' | 'actual',

  plannedState: {
    modifiedCells: Map<string, number>,
    assignmentMap: Map<string, number>,
    // ...
  },

  actualState: {
    modifiedCells: Map<string, number>,
    assignmentMap: Map<string, number>,
    // ...
  },

  // Shared (mode-independent)
  timeColumns: Array<Column>,
  volumeMap: Map<string, number>,
  flatPekerjaan: Array<Node>,
};
```

**Kurva S Integration**:
```javascript
// Modified buildCellValueMap() - Phase 2F
function buildCellValueMap(state, progressMode = null) {
  const mode = progressMode || state.progressMode || 'planned';
  const modeState = mode === 'actual' ? state.actualState : state.plannedState;

  const map = new Map();

  // Use mode-specific state
  if (modeState.assignmentMap instanceof Map) {
    modeState.assignmentMap.forEach((value, key) => assignValue(key, value));
  }

  if (modeState.modifiedCells instanceof Map) {
    modeState.modifiedCells.forEach((value, key) => assignValue(key, value));
  }

  return map;
}
```

---

## 🎯 Recommendations

### Immediate Actions (Phase 2F.1)

1. ✅ **Modify `buildCellValueMap()`** to accept `progressMode` parameter
2. ✅ **Update `buildDataset()`** to pass mode to helper functions
3. ✅ **Test dual mode integration** with existing data
4. ✅ **Add mode selector UI** to Kurva S tab

### Short-Term (Phase 2F.2)

1. ⏳ **Add "Both Modes" view** (overlay curves from both states)
2. ⏳ **Implement export feature** (PNG, CSV, Excel)
3. ⏳ **Add loading indicator**
4. ⏳ **Write unit tests** for calculation functions

### Long-Term (Phase 2F.3+)

1. 💡 **Configurable curve calculation** (let users choose algorithm)
2. 💡 **Historical variance tracking** (show how variance changed)
3. 💡 **Forecast feature** (predict completion based on trend)
4. 💡 **Gantt chart integration** (dual timeline bars)

---

## 📊 API Surface Documentation

### Public Methods

```javascript
// Module: kurvaS (registered in bootstrap)

// Initialize chart
init(context?: { state?: State, scurveOptions?: Options })
  → Returns: echarts.ECharts instance or 'legacy'

// Refresh chart with new data
refresh(context?: { state?: State, scurveOptions?: Options })
  → Returns: echarts.ECharts instance or 'legacy'

// Resize chart (e.g., on window resize)
resize(context?: { state?: State })
  → Returns: echarts.ECharts instance or 'legacy'

// Get current chart instance
getChart(context?: { state?: State })
  → Returns: echarts.ECharts instance or null
```

### Configuration Options

```javascript
context.scurveOptions = {
  useIdealCurve: boolean,       // Use sigmoid if no assignments (default: true)
  steepnessFactor: number,      // Sigmoid steepness 0.5-1.5 (default: 0.8)
  fallbackToLinear: boolean,    // Use linear as last resort (default: true)
};
```

### State Requirements

```javascript
state = {
  // Required
  timeColumns: Array<{
    id: string | number,
    label?: string,
    rangeLabel?: string,
    startDate?: Date | string,
    endDate?: Date | string,
    index?: number,
  }>,

  // Required for volume-based calculation
  modifiedCells: Map<string, number>,   // cellKey → percentage
  assignmentMap: Map<string, number>,   // cellKey → percentage
  volumeMap: Map<string, number>,       // pekerjaanId → volume

  // Optional
  flatPekerjaan: Array<{
    id: string | number,
    type?: string,
  }>,

  // Phase 2F additions
  progressMode?: 'planned' | 'actual',
  plannedState?: { modifiedCells, assignmentMap },
  actualState?: { modifiedCells, assignmentMap },
};
```

---

## 🔗 Dependencies

### External Libraries

```javascript
window.echarts  // ECharts 5.x (Apache-2.0 license)
```

**CDN Links** (check template):
```html
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
```

### Internal Dependencies

```javascript
window.KelolaTahapanPageApp          // Application bootstrap
window.KelolaTahapanModuleManifest   // Module registry
window.kelolaTahapanPageState        // Global state (fallback)
```

---

## 📁 File Locations Summary

```
D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\

├── static\detail_project\js\jadwal_pekerjaan\kelola_tahapan\
│   ├── kurva_s_module.js           ← Core calculation + rendering (734 lines)
│   └── kurva_s_tab.js              ← Tab activation handler (79 lines)
│
├── templates\detail_project\
│   └── kelola_tahapan_grid_modern.html  ← Contains <div id="scurve-chart">
│
└── docs\
    ├── PHASE_2E1_COMPLETE.md       ← Phase 2E.1 completion report
    ├── PHASE_2E_ROADMAP_NEXT.md    ← Future roadmap
    └── KURVA_S_AUDIT_CURRENT_IMPLEMENTATION.md  ← This document
```

---

## ✅ Audit Completion Checklist

- [x] Read kurva_s_module.js (734 lines)
- [x] Read kurva_s_tab.js (79 lines)
- [x] Analyzed data flow
- [x] Documented algorithms
- [x] Identified integration points
- [x] Gap analysis vs Phase 2E.2 requirements
- [x] Effort estimate revision
- [x] Recommendations documented

---

## 📞 Next Steps

1. **Present audit findings** to user
2. **Get approval** for revised Phase 2F scope
3. **Create Phase 2F implementation plan** (detailed task breakdown)
4. **Begin Phase 2F.1** (Dual mode integration)

---

**Audit Completed By**: Claude Code
**Date**: 2025-11-26
**Next Review**: After Phase 2F.1 completion

---

**End of Audit Report**
