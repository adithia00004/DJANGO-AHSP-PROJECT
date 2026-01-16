# Chart Modules Analysis - ES6 Migration Assessment

**Project:** Django AHSP - Detail Project
**Analysis Date:** 2025-11-20
**Analyzed By:** Claude Code (Automated Analysis)
**Total Modules Analyzed:** 3

---

## Executive Summary

This document provides a comprehensive analysis of legacy chart modules in the Kelola Tahapan feature, preparing for migration to ES6 module system. The analysis covers S-Curve (Kurva S) visualization using ECharts and Gantt chart visualization using Frappe Gantt library.

### Key Findings

- **Total Lines of Code:** 1,554 lines across 3 modules
- **Primary Dependencies:** ECharts (S-Curve), Frappe Gantt (Gantt Chart)
- **Architecture Pattern:** IIFE (Immediately Invoked Function Expression) with global namespace
- **Code Quality:** Well-documented with extensive inline comments
- **Migration Complexity:** Medium overall
- **Estimated Migration Effort:** 16-24 developer hours

### Modules Overview

| Module | Lines | Complexity | Priority | Dependencies |
|--------|-------|------------|----------|--------------|
| kurva_s_module.js | 733 | Medium | High | ECharts |
| gantt_module.js | 705 | Medium | High | Frappe Gantt |
| gantt_tab.js | 116 | Easy | Medium | gantt_module.js |

---

## Module 1: Kurva S (S-Curve Chart) Module

### Basic Information

- **File Path:** `d:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\jadwal_pekerjaan\kelola_tahapan\kurva_s_module.js`
- **File Size:** 733 lines
- **Module ID:** `kurva_s_module`
- **Namespace:** `KelolaTahapanPageModules.kurvaS`

### Main Responsibilities

The Kurva S module is responsible for rendering and managing S-Curve (progress curve) visualizations that compare planned vs. actual project progress over time.

**Core Functionality:**
1. **Data Processing:** Aggregates pekerjaan (work item) assignments into time-series data
2. **Curve Calculation:** Implements three algorithms for calculating planned curves:
   - Volume-based planned curve (primary, data-driven)
   - Ideal sigmoid S-curve (mathematical model for new projects)
   - Linear fallback curve (basic distribution)
3. **Chart Rendering:** Uses ECharts to display interactive dual-line area charts
4. **Theme Support:** Dynamic color schemes for light/dark modes
5. **Progress Tracking:** Calculates cumulative progress percentages with variance analysis

### Key Functions

#### Public API Functions (8 total)

| Function | Purpose | Complexity |
|----------|---------|------------|
| `init(context)` | Initialize chart with initial render | Low |
| `refresh(context)` | Update chart with new data | Medium |
| `resize(context)` | Handle window resize events | Low |
| `getChart(context)` | Return ECharts instance | Low |
| `resolveState(stateOverride)` | Access application state | Low |
| `resolveDom(state)` | Get DOM references | Low |
| `buildDataset(state, context)` | Build chart data from state | High |

#### Internal Functions (14 total)

| Function | Purpose | Lines | Complexity |
|----------|---------|-------|------------|
| `getThemeColors()` | Get theme-specific colors | 22 | Low |
| `getColumns(state)` | Get sorted time columns | 8 | Low |
| `buildVolumeLookup(state)` | Map pekerjaan to volumes | 14 | Medium |
| `getVolumeForPekerjaan()` | Get volume for specific pekerjaan | 12 | Low |
| `buildCellValueMap(state)` | Map assignments to percentages | 21 | Medium |
| `collectPekerjaanIds()` | Collect all pekerjaan IDs | 17 | Low |
| `calculateVolumeBasedPlannedCurve()` | Volume-weighted planned curve | 50 | **High** |
| `calculateIdealSCurve()` | Sigmoid mathematical curve | 18 | Medium |
| `calculateLinearPlannedCurve()` | Simple linear distribution | 10 | Low |
| `calculatePlannedCurve()` | Hybrid strategy selector | 37 | **High** |
| `buildFallbackDataset()` | Default demo data | 8 | Low |
| `formatDateLabel(date)` | Format dates for display | 9 | Low |
| `createChartOption(dataset)` | Build ECharts configuration | 118 | **High** |
| `ensureChartInstance(state)` | Initialize ECharts instance | 13 | Low |

### Algorithm Highlights

#### 1. Volume-Based Planned Curve (Lines 205-254)

**Algorithm:**
```
For each time period (column):
  1. Identify pekerjaan assigned to this period
  2. Sum their TOTAL volumes (not progress, full volume)
  3. Accumulate to get cumulative planned volume
  4. Convert to percentage of total project volume
```

**Example:**
- Project with 3 pekerjaan: 100m², 200m², 100m² (total: 400m²)
- Pekerjaan A (100m²) assigned to Column 0 → 25% (100/400)
- Pekerjaan B (200m²) assigned to Column 1 → 75% (300/400)
- Pekerjaan C (100m²) assigned to Column 2 → 100% (400/400)

**Complexity:** O(n*m) where n = pekerjaan count, m = time columns

#### 2. Ideal Sigmoid S-Curve (Lines 288-305)

**Mathematical Formula:**
```
P(t) = 100 / (1 + e^(-k*(t - t₀)))
```

Where:
- `t` = time period index (0 to n-1)
- `t₀` = midpoint of timeline (n/2)
- `k` = steepness factor (default: 0.8)
- `P(t)` = cumulative percentage at time t

**Curve Properties:**
- Starts near 0% (slow ramp-up)
- Accelerates in middle (peak productivity)
- Slows down near 100% (completion/tapering)

**Steepness Options:**
- `k = 0.5`: Gentle curve (gradual progress)
- `k = 0.8`: Moderate curve (default, balanced)
- `k = 1.2`: Steep curve (aggressive schedule)

#### 3. Hybrid Strategy (Lines 378-414)

**Decision Flow:**
```
Has assignments? → Yes → Volume-based planned curve
       ↓
       No
       ↓
Use ideal curve? → Yes → Sigmoid S-curve
       ↓
       No
       ↓
Linear fallback
```

This ensures the best possible curve based on available data.

### Dependencies

#### External Libraries
- **ECharts** (v5.x assumed)
  - Required for: Chart rendering, interaction, theming
  - Usage: `window.echarts.init()`, `chart.setOption()`
  - Type: Critical dependency

#### Internal Dependencies
- **Bootstrap App:** `window.KelolaTahapanPageApp`
- **Module Manifest:** `window.KelolaTahapanModuleManifest`
- **Page State:** `window.kelolaTahapanPageState`

### Data Inputs

#### Required State Properties

| Property | Type | Purpose |
|----------|------|---------|
| `timeColumns` | Array | Time period definitions with startDate/endDate |
| `volumeMap` | Map/Object | Pekerjaan ID → volume mapping |
| `assignmentMap` | Map/Object | Cell key → percentage assignments |
| `modifiedCells` | Map/Object | User-modified cell values |
| `flatPekerjaan` | Array | Flattened pekerjaan list |
| `scurveChart` | Object | ECharts instance reference |
| `domRefs.scurveChart` | Element | DOM element for chart container |

#### Optional Context Properties

| Property | Type | Purpose | Default |
|----------|------|---------|---------|
| `scurveOptions.useIdealCurve` | Boolean | Enable sigmoid curve | `true` |
| `scurveOptions.steepnessFactor` | Number | Sigmoid steepness | `0.8` |
| `scurveOptions.fallbackToLinear` | Boolean | Use linear fallback | `true` |

### Chart Configuration

#### Color Schemes

**Light Mode:**
```javascript
{
  text: '#1f2937',           // Dark gray for text
  axis: '#374151',           // Medium gray for axis
  plannedLine: '#0d6efd',    // Bootstrap blue
  plannedArea: 'rgba(13, 110, 253, 0.12)', // Light blue area
  actualLine: '#198754',     // Bootstrap green
  actualArea: 'rgba(25, 135, 84, 0.12)',   // Light green area
  gridLine: '#e5e7eb',       // Light gray grid
}
```

**Dark Mode:**
```javascript
{
  text: '#f8fafc',           // Light gray for text
  axis: '#cbd5f5',           // Light blue-gray for axis
  plannedLine: '#60a5fa',    // Bright blue
  plannedArea: 'rgba(96, 165, 250, 0.15)', // Bright blue area
  actualLine: '#34d399',     // Bright green
  actualArea: 'rgba(52, 211, 153, 0.18)',  // Bright green area
  gridLine: '#334155',       // Dark gray grid
}
```

#### Chart Options

**Series Configuration:**
- **Planned Series:**
  - Type: Line with area fill
  - Style: Dashed line (width: 2px)
  - Smooth: Enabled
  - Symbol size: 6px

- **Actual Series:**
  - Type: Line with area fill
  - Style: Solid line (width: 3px)
  - Smooth: Enabled
  - Symbol size: 7px

**Grid Layout:**
- Left: 4%, Right: 4%
- Top: 12%, Bottom: 6%
- Contains label: true

**Axes:**
- X-Axis: Category type, labels from time columns
- Y-Axis: Value type (0-100%), percentage formatter

### Event Handlers

#### Tooltip Formatter (Lines 537-572)

**Features:**
- Shows period label and date range
- Displays planned vs. actual percentages
- Calculates variance with status indicators:
  - **Green:** +5% or more (Ahead of schedule)
  - **Red:** -5% or less (Behind schedule)
  - **Blue:** ±5% (On track)

**Data Displayed:**
```
[Period Label]
Periode: [Start Date] - [End Date]

Rencana: [Planned %]
Aktual: [Actual %]
Variance: [±X%] (Status)
```

### Migration Complexity Assessment

**Overall Complexity: MEDIUM**

#### Easy Aspects
- Well-structured pure functions
- Clear separation of concerns
- Minimal side effects
- Good documentation

#### Medium Aspects
- State management through global namespace
- Dynamic theme switching logic
- Complex data transformation pipelines
- ECharts instance lifecycle management

#### Challenges
1. **State Resolution:** Currently uses multiple fallback sources (window globals)
2. **Side Effects:** Modifies state.scurveChart directly
3. **Global Dependencies:** Relies on window.echarts, bootstrap, manifest
4. **Module Registration:** Custom registration pattern needs adapter
5. **Bridge Pattern:** Legacy facade support needs migration strategy

#### Migration Checklist

- [ ] Convert IIFE to ES6 module with export
- [ ] Replace global state access with props/injection
- [ ] Create Chart configuration class
- [ ] Implement proper TypeScript interfaces for state
- [ ] Add unit tests for curve calculation algorithms
- [ ] Migrate ECharts instance to reactive wrapper
- [ ] Remove global namespace pollution
- [ ] Add error boundaries and fallbacks

---

## Module 2: Gantt Chart Module

### Basic Information

- **File Path:** `d:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\jadwal_pekerjaan\kelola_tahapan\gantt_module.js`
- **File Size:** 705 lines
- **Module ID:** `gantt_module`
- **Namespace:** `KelolaTahapanPageModules.gantt`

### Main Responsibilities

The Gantt module renders interactive Gantt charts using Frappe Gantt library, displaying project schedules, task hierarchies, and progress visualization.

**Core Functionality:**
1. **Task Building:** Converts hierarchical pekerjaan tree into Gantt-compatible tasks
2. **Progress Calculation:** Aggregates volume-weighted progress by tahapan (phase)
3. **Timeline Management:** Handles project date ranges and time periods
4. **View Mode Control:** Supports Day, Week, Month view modes
5. **Interactive Tooltips:** Shows task details, segments, and progress
6. **Hierarchy Display:** Visualizes task nesting with indentation

### Key Functions

#### Public API Functions (9 total)

| Function | Purpose | Complexity |
|----------|---------|------------|
| `init(context)` | Initialize Gantt chart | Medium |
| `refresh(context)` | Update chart with new data | High |
| `destroy()` | Clean up instance and listeners | Low |
| `setViewMode(mode, context)` | Change view mode (Day/Week/Month) | Medium |
| `getViewMode()` | Get current view mode | Low |
| `buildTasks(context)` | Generate task list from state | High |
| `calculateProgress(context)` | Calculate tahapan progress | High |
| `resolveState(stateOverride)` | Access application state | Low |
| `resolveDom(state)` | Get DOM references | Low |

#### Internal Functions (12 total)

| Function | Purpose | Lines | Complexity |
|----------|---------|-------|------------|
| `prepareUtils(contextUtils)` | Initialize utility functions | 14 | Low |
| `normalizeViewMode(mode)` | Normalize view mode string | 7 | Low |
| `buildPekerjaanPathMaps()` | Build node and path maps | 25 | Medium |
| `buildPekerjaanHierarchy()` | Extract pekerjaan with levels | 23 | Medium |
| `buildPekerjaanTasks()` | Convert to Gantt tasks | 127 | **Very High** |
| `computeProjectRange(state)` | Calculate project date range | 11 | Low |
| `defaultEscapeHtml(text)` | HTML escape for security | 5 | Low |
| `defaultNormalizeToISODate()` | Date normalization | 26 | Medium |
| `defaultGetProjectStartDate()` | Get project start date | 14 | Low |
| `buildPopupHtml(task, utils)` | Generate tooltip HTML | 35 | Medium |
| `buildGanttOptions()` | Create Frappe Gantt options | 20 | Medium |
| `ensureGantt()` | Initialize/refresh Gantt instance | 30 | **High** |
| `emitSelectionEvent()` | Emit task selection event | 17 | Low |
| `bindResizeHandler()` | Bind window resize listener | 12 | Low |

### Algorithm Highlights

#### 1. Volume-Weighted Progress Calculation (Lines 193-296)

**Algorithm:**
```
For each assignment (pekerjaanId-columnId → percentage):
  1. Look up column's tahapanId
  2. Get pekerjaan volume from volumeMap
  3. Calculate weighted progress = volume × percentage
  4. Accumulate by tahapanId

For each tahapan:
  Progress = (sum of weighted progress) / (sum of volumes)
  OR if no volumes:
  Progress = (sum of percentages) / count
```

**Example:**
```
Tahapan A has 3 pekerjaan:
  - Pekerjaan 1: 100m², 50% done → 50m²
  - Pekerjaan 2: 200m², 75% done → 150m²
  - Pekerjaan 3: 100m², 25% done → 25m²

Total: 400m², 225m² done
Progress: 225/400 = 56.25%
```

**Complexity:** O(n) where n = assignment count

#### 2. Task Hierarchy Building (Lines 312-335)

**Algorithm:**
```
Walk pekerjaan tree recursively:
  For each node:
    - Build path from ancestors (e.g., ["Struktur", "Balok", "B1"])
    - Record level (depth in tree)
    - Store only nodes with type='pekerjaan'
    - Pass path to children for continuation
```

**Result:**
```javascript
[
  { id: "1", level: 2, pathParts: ["Struktur", "Balok", "B1"] },
  { id: "2", level: 2, pathParts: ["Struktur", "Balok", "B2"] },
  { id: "3", level: 2, pathParts: ["Struktur", "Kolom", "K1"] },
]
```

#### 3. Task Segment Aggregation (Lines 337-463)

**Algorithm:**
```
For each pekerjaan:
  Create bucket to collect all time segments

  For each assignment (pekerjaanId-columnId → percent):
    Add to bucket:
      - Accumulate total percentage
      - Track earliest start date
      - Track latest end date
      - Store segment details

  Build final task:
    - Start: earliest column start
    - End: latest column end
    - Progress: sum of percentages
    - Metadata: segments for tooltip
```

**Complexity:** O(n*m) where n = pekerjaan count, m = assignments per pekerjaan

### Dependencies

#### External Libraries
- **Frappe Gantt** (assumed latest version)
  - Required for: Gantt chart rendering
  - Usage: `new Gantt(element, tasks, options)`
  - Type: Critical dependency
  - Methods used: `refresh()`, `change_view_mode()`, `destroy()`

#### Internal Dependencies
- **Bootstrap App:** `window.KelolaTahapanPageApp`
- **Module Manifest:** `window.KelolaTahapanModuleManifest`
- **Page State:** `window.kelolaTahapanPageState`
- **Event Bus:** `window.KelolaTahapanPage.events`

### Data Inputs

#### Required State Properties

| Property | Type | Purpose |
|----------|------|---------|
| `pekerjaanTree` | Array | Hierarchical tree of work items |
| `flatPekerjaan` | Array | Flattened pekerjaan list (optional) |
| `timeColumns` | Array | Time periods with dates |
| `volumeMap` | Map | Pekerjaan ID → volume (m², m³, etc.) |
| `assignmentMap` | Map | "pekerjaanId-columnId" → percentage |
| `modifiedCells` | Map | User-modified assignments |
| `tahapanList` | Array | List of project phases |
| `tahapanProgressMap` | Map | Calculated progress by tahapan |
| `projectStart` | Date/String | Project start date |
| `projectEnd` | Date/String | Project end date |
| `ganttInstance` | Object | Frappe Gantt instance reference |
| `ganttTasks` | Array | Generated task array |
| `domRefs.ganttChart` | Element | DOM container element |

#### Utility Functions

| Function | Purpose | Default Implementation |
|----------|---------|------------------------|
| `escapeHtml(text)` | Sanitize HTML for XSS prevention | `div.textContent` method |
| `normalizeToISODate(value)` | Convert to ISO date string | Date parsing with validation |
| `getProjectStartDate(state)` | Determine project start | tahapanList[0] or state.projectStart |

### Chart Configuration

#### View Modes

| Mode | Description | Bar Width | Use Case |
|------|-------------|-----------|----------|
| `Day` | Daily granularity | Narrow | Short projects (<2 months) |
| `Week` | Weekly granularity | Medium | Standard projects (2-12 months) |
| `Month` | Monthly granularity | Wide | Long projects (>1 year) |

**Default:** Week

#### Task Display

**Name Formatting:**
```javascript
// Indentation based on hierarchy level
const indentPrefix = '\u00A0\u00A0'.repeat(Math.max(0, level - 2));
const name = indentPrefix + leafNodeName;

// Example:
// Level 0: "Struktur"
// Level 1: "  Balok"        (2 spaces)
// Level 2: "    B1"         (4 spaces)
```

**Custom Classes:**
- `gantt-task-complete`: Applied when progress >= 100%

#### Tooltip (Popup) Structure

**HTML Template:**
```html
<div class="gantt-popup">
  <h5>[Task Name]</h5>

  <div class="gantt-popup-section">
    <strong>Periode:</strong> [Start] s/d [End]
  </div>

  <div class="gantt-popup-section">
    <strong>Progress:</strong> [XX.X%]
  </div>

  <div class="gantt-popup-section">
    <strong>Distribusi:</strong>
    <ul class="gantt-popup-segments">
      <li>
        <span class="gantt-popup-segment-label">[Period Label]</span>
        <span class="gantt-popup-segment-percent">[XX%]</span>
      </li>
      <!-- More segments... -->
    </ul>
  </div>
</div>
```

**Empty State:**
When no assignments exist:
```html
<p class="mb-0 text-muted">
  <em>Belum ada distribusi progres</em>
</p>
```

### Event Handlers

#### 1. Task Click Event

**Triggered:** When user clicks on a Gantt bar

**Action:**
```javascript
on_click(task) {
  // Extract pekerjaanId from task.id ("pekerjaan-123")
  const pekerjaanId = task.id.match(/^pekerjaan-(.+)$/)[1];

  // Emit event to application
  window.KelolaTahapanPage.events.emit('gantt:select', {
    pekerjaanId,
    task,
    state,
  });
}
```

**Event Payload:**
- `pekerjaanId`: String ID of the work item
- `task`: Full Frappe Gantt task object
- `state`: Current application state

#### 2. View Mode Change

**Triggered:** When user switches between Day/Week/Month

**Action:**
```javascript
on_view_change(mode) {
  const normalized = normalizeViewMode(mode); // 'Day', 'Week', or 'Month'
  moduleStore.viewMode = normalized;
  state.cache.ganttViewMode = normalized;
  moduleStore.emitViewChange?.(normalized);
}
```

#### 3. Window Resize

**Bound:** On module initialization
**Unbind:** On module destroy

**Action:**
```javascript
window.addEventListener('resize', () => {
  ganttInstance.refresh(state.ganttTasks);
  ganttInstance.change_view_mode(currentViewMode);
});
```

### Migration Complexity Assessment

**Overall Complexity: MEDIUM-HIGH**

#### Easy Aspects
- Pure utility functions (escapeHtml, normalizeToISODate)
- Simple state lookups
- View mode normalization

#### Medium Aspects
- Progress calculation algorithm
- Hierarchy traversal
- Task metadata building

#### Challenging Aspects
- Complex task aggregation logic (360+ line function)
- Frappe Gantt instance lifecycle
- Date range calculations with edge cases
- Nested data transformations

#### Critical Challenges
1. **Frappe Gantt Integration:** Third-party library needs wrapper/adapter
2. **Complex Task Building:** `buildPekerjaanTasks()` is 127 lines with nested logic
3. **State Mutation:** Directly modifies state.ganttInstance, state.ganttTasks
4. **Event System:** Custom event emitter integration
5. **Window Event Handlers:** Manual binding/unbinding required
6. **Date Normalization:** Complex date handling with fallbacks

#### Migration Checklist

- [ ] Convert IIFE to ES6 module
- [ ] Create GanttChartService class
- [ ] Implement ProgressCalculator utility class
- [ ] Create TaskBuilder with unit tests
- [ ] Wrap Frappe Gantt in reactive component
- [ ] Add TypeScript interfaces for Task, Progress, etc.
- [ ] Implement proper cleanup/unmount
- [ ] Refactor buildPekerjaanTasks (split into smaller functions)
- [ ] Add error handling for invalid dates
- [ ] Create DateUtils module for normalization

---

## Module 3: Gantt Tab UI Module

### Basic Information

- **File Path:** `d:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\jadwal_pekerjaan\kelola_tahapan\gantt_tab.js`
- **File Size:** 116 lines
- **Module ID:** `gantt_tab_module`
- **Namespace:** `KelolaTahapanPageModules.ganttTab`

### Main Responsibilities

This is a lightweight UI controller module that binds toolbar controls and tab activation events to the Gantt chart module.

**Core Functionality:**
1. **Toolbar Binding:** Connects view mode buttons (Day/Week/Month) to Gantt module
2. **Tab Activation:** Refreshes Gantt when tab is shown (Bootstrap tabs integration)
3. **Button State Sync:** Updates active button states based on current view mode

### Key Functions

#### Public API Functions (2 total)

| Function | Purpose | Complexity |
|----------|---------|------------|
| `init()` | Initialize toolbar and tab listeners | Low |
| `refresh()` | Re-sync button states | Low |

#### Internal Functions (4 total)

| Function | Purpose | Lines | Complexity |
|----------|---------|-------|------------|
| `getFacade()` | Get global facade object | 3 | Low |
| `getGanttFacade()` | Get Gantt module facade | 5 | Low |
| `syncButtons(buttons, mode)` | Update button active states | 10 | Low |
| `bindToolbar(gantt)` | Attach click listeners to buttons | 24 | Low |
| `bindTabActivation(gantt)` | Attach tab shown listener | 13 | Low |

### Dependencies

#### External Libraries
- **Bootstrap 5** (for tabs)
  - Used for: `shown.bs.tab` event
  - Type: UI framework dependency

#### Internal Dependencies
- **Gantt Module:** `facade.gantt`
- **Module Manifest:** `window.KelolaTahapanModuleManifest`
- **Bootstrap App:** `window.KelolaTahapanPageApp`

### Data Inputs

**Minimal - this is a UI-only module:**

#### DOM Elements Required

| Selector | Purpose | Required |
|----------|---------|----------|
| `.gantt-toolbar` | Container for view mode buttons | Yes |
| `[data-gantt-view]` | View mode toggle buttons | Yes |
| `#gantt-tab` | Bootstrap tab element | Yes |

#### Button Configuration

**HTML Structure:**
```html
<div class="gantt-toolbar">
  <button data-gantt-view="Day">Day</button>
  <button data-gantt-view="Week">Week</button>
  <button data-gantt-view="Month">Month</button>
</div>
```

**Attribute:**
- `data-gantt-view`: Specifies view mode value (Day/Week/Month)

### Event Handlers

#### 1. View Mode Button Click

**Selector:** `[data-gantt-view]`

**Handler:**
```javascript
button.addEventListener('click', (event) => {
  event.preventDefault();
  const mode = button.getAttribute('data-gantt-view') || 'Week';
  const normalized = gantt.setViewMode(mode, {
    refresh: true,
    rebuildTasks: false
  });
  syncButtons(buttons, normalized);
});
```

**Flow:**
1. Prevent default button behavior
2. Get mode from data attribute
3. Call Gantt module's `setViewMode()`
4. Sync button active states

#### 2. Tab Activation (Bootstrap Tabs)

**Event:** `shown.bs.tab`
**Element:** `#gantt-tab`

**Handler:**
```javascript
ganttTab.addEventListener('shown.bs.tab', () => {
  const result = gantt.refreshView
    ? gantt.refreshView({ reason: 'tab-shown', rebuildTasks: false })
    : null;

  if (result === 'legacy' || result === null) {
    gantt.init && gantt.init();
  }
});
```

**Purpose:** Ensures Gantt renders correctly when tab becomes visible

### Migration Complexity Assessment

**Overall Complexity: EASY**

#### Easy Aspects
- Minimal logic (only event binding)
- No complex data transformations
- Clear separation from business logic
- Small codebase (116 lines)

#### Challenges
1. **Bootstrap Integration:** Needs migration to modern framework tabs
2. **Facade Pattern:** Depends on global facade access
3. **DOM Queries:** Direct DOM manipulation needs reactive approach

#### Migration Checklist

- [ ] Convert to ES6 module
- [ ] Replace facade with props/dependency injection
- [ ] Use framework-specific tab events (Vue/React)
- [ ] Replace querySelector with refs/templates
- [ ] Add TypeScript types
- [ ] Create unit tests for button sync logic

**Estimated Effort:** 2-3 hours (trivial migration)

---

## Consolidated Migration Recommendations

### Priority Order

1. **High Priority:** kurva_s_module.js, gantt_module.js (core functionality)
2. **Medium Priority:** gantt_tab.js (UI binding)
3. **Low Priority:** Legacy facade bridges

### Migration Strategy

#### Phase 1: Foundation (Week 1)

**Tasks:**
1. Create ES6 module structure
2. Define TypeScript interfaces for state objects
3. Set up build configuration (Webpack/Vite)
4. Create utility modules (DateUtils, ColorTheme, etc.)

**Deliverables:**
- `src/modules/charts/` directory structure
- `types/state.d.ts` type definitions
- Build configuration

#### Phase 2: Chart Services (Week 2-3)

**Tasks:**
1. Migrate S-Curve module to `ScurveChartService` class
2. Migrate Gantt module to `GanttChartService` class
3. Create wrapper components for ECharts and Frappe Gantt
4. Implement reactive state management

**Deliverables:**
- `ScurveChartService.js` (ES6 class)
- `GanttChartService.js` (ES6 class)
- `EChartsWrapper.vue/jsx` (framework component)
- `FrappeGanttWrapper.vue/jsx` (framework component)

#### Phase 3: Integration & Testing (Week 4)

**Tasks:**
1. Migrate gantt_tab.js to UI components
2. Integrate with existing page architecture
3. Write unit tests (Jest/Vitest)
4. Write integration tests
5. Update documentation

**Deliverables:**
- Complete ES6 module suite
- Test coverage >80%
- Migration guide documentation

### Proposed ES6 Class Structure

#### 1. ScurveChartService Class

```javascript
// src/modules/charts/ScurveChartService.js

import * as echarts from 'echarts';
import { ThemeManager } from '../utils/ThemeManager';
import { CurveCalculator } from './CurveCalculator';

/**
 * S-Curve Chart Service
 * Manages S-Curve chart rendering and data processing
 */
export class ScurveChartService {
  constructor(containerElement, options = {}) {
    this.container = containerElement;
    this.options = {
      useIdealCurve: true,
      steepnessFactor: 0.8,
      fallbackToLinear: true,
      ...options,
    };

    this.chartInstance = null;
    this.themeManager = new ThemeManager();
    this.curveCalculator = new CurveCalculator();
  }

  /**
   * Initialize chart instance
   */
  init() {
    if (!this.container) {
      throw new Error('ScurveChartService: Container element required');
    }

    this.chartInstance = echarts.init(this.container);
    this.bindThemeListener();
    return this;
  }

  /**
   * Build dataset from state
   * @param {Object} state - Application state
   * @returns {Object} Chart dataset
   */
  buildDataset(state) {
    const columns = this.getColumns(state);
    if (!columns.length) return null;

    const volumeLookup = this.buildVolumeLookup(state);
    const cellValues = this.buildCellValueMap(state);
    const pekerjaanIds = this.collectPekerjaanIds(state, cellValues);

    const totalVolume = this.calculateTotalVolume(pekerjaanIds, volumeLookup);

    // Calculate curves
    const planned = this.curveCalculator.calculatePlannedCurve(
      columns,
      volumeLookup,
      cellValues,
      totalVolume,
      this.options
    );

    const actual = this.calculateActualCurve(
      columns,
      volumeLookup,
      cellValues,
      totalVolume
    );

    return {
      labels: this.buildLabels(columns),
      planned,
      actual,
      details: this.buildDetails(columns, planned, actual),
      totalVolume,
    };
  }

  /**
   * Render or update chart
   * @param {Object} dataset - Chart dataset
   */
  render(dataset) {
    if (!this.chartInstance) {
      throw new Error('ScurveChartService: Chart not initialized');
    }

    const colors = this.themeManager.getColors();
    const option = this.createChartOption(dataset, colors);

    this.chartInstance.setOption(option, true);
    return this;
  }

  /**
   * Resize chart
   */
  resize() {
    this.chartInstance?.resize();
    return this;
  }

  /**
   * Destroy chart and cleanup
   */
  destroy() {
    this.unbindThemeListener();
    this.chartInstance?.dispose();
    this.chartInstance = null;
  }

  // ... (private methods)
}
```

#### 2. GanttChartService Class

```javascript
// src/modules/charts/GanttChartService.js

import Gantt from 'frappe-gantt';
import { ProgressCalculator } from './ProgressCalculator';
import { TaskBuilder } from './TaskBuilder';
import { DateUtils } from '../utils/DateUtils';

/**
 * Gantt Chart Service
 * Manages Frappe Gantt chart rendering and task building
 */
export class GanttChartService {
  constructor(containerElement, options = {}) {
    this.container = containerElement;
    this.options = {
      viewMode: 'Week',
      ...options,
    };

    this.ganttInstance = null;
    this.progressCalculator = new ProgressCalculator();
    this.taskBuilder = new TaskBuilder();
    this.resizeHandler = null;
  }

  /**
   * Initialize Gantt chart
   * @param {Array} tasks - Task array
   */
  init(tasks = []) {
    if (!this.container) {
      throw new Error('GanttChartService: Container element required');
    }

    if (typeof Gantt !== 'function') {
      throw new Error('GanttChartService: Frappe Gantt library not loaded');
    }

    this.ganttInstance = new Gantt(this.container, tasks, {
      view_mode: this.options.viewMode,
      date_format: 'YYYY-MM-DD',
      custom_popup_html: this.buildPopupHtml.bind(this),
      on_click: this.handleTaskClick.bind(this),
      on_view_change: this.handleViewChange.bind(this),
    });

    this.bindResizeHandler();
    return this;
  }

  /**
   * Build tasks from state
   * @param {Object} state - Application state
   * @returns {Array} Gantt tasks
   */
  buildTasks(state) {
    // Calculate progress first
    const progressMap = this.progressCalculator.calculate(state);

    // Build task hierarchy
    const tasks = this.taskBuilder.build(state, progressMap);

    return tasks;
  }

  /**
   * Refresh chart with new tasks
   * @param {Array} tasks - Updated task array
   */
  refresh(tasks) {
    if (!this.ganttInstance) {
      return this.init(tasks);
    }

    this.ganttInstance.refresh(tasks);
    this.ganttInstance.change_view_mode(this.options.viewMode);
    return this;
  }

  /**
   * Set view mode
   * @param {String} mode - 'Day', 'Week', or 'Month'
   */
  setViewMode(mode) {
    const normalized = this.normalizeViewMode(mode);
    this.options.viewMode = normalized;
    this.ganttInstance?.change_view_mode(normalized);
    return this;
  }

  /**
   * Get current view mode
   * @returns {String}
   */
  getViewMode() {
    return this.options.viewMode;
  }

  /**
   * Destroy Gantt and cleanup
   */
  destroy() {
    this.unbindResizeHandler();
    this.ganttInstance = null;
  }

  // ... (private methods)
}
```

#### 3. Supporting Utility Classes

**CurveCalculator.js:**
```javascript
export class CurveCalculator {
  calculateVolumeBasedCurve(columns, volumeLookup, cellValues, totalVolume) {
    // Implementation from lines 205-254
  }

  calculateIdealSCurve(columns, steepness = 0.8) {
    // Implementation from lines 288-305
  }

  calculateLinearCurve(columns) {
    // Implementation from lines 329-339
  }

  calculatePlannedCurve(columns, volumeLookup, cellValues, totalVolume, options) {
    // Hybrid strategy from lines 378-414
  }
}
```

**ProgressCalculator.js:**
```javascript
export class ProgressCalculator {
  calculate(state) {
    // Implementation from lines 193-296
    return progressMap;
  }

  calculateVolumeWeighted(assignments, volumeMap) {
    // Helper method
  }

  calculateAveragePercent(assignments) {
    // Helper method
  }
}
```

**TaskBuilder.js:**
```javascript
export class TaskBuilder {
  build(state, progressMap) {
    const hierarchy = this.buildHierarchy(state);
    const tasks = this.buildPekerjaanTasks(state, hierarchy);
    return tasks;
  }

  buildHierarchy(state) {
    // Implementation from lines 312-335
  }

  buildPekerjaanTasks(state, pekerjaanList) {
    // Implementation from lines 337-463 (refactored)
  }

  aggregateSegments(assignments, columnLookup) {
    // Extracted helper
  }
}
```

**ThemeManager.js:**
```javascript
export class ThemeManager {
  constructor() {
    this.observers = [];
  }

  getCurrentTheme() {
    return document.documentElement.getAttribute('data-bs-theme') || 'light';
  }

  getColors(theme = null) {
    const currentTheme = theme || this.getCurrentTheme();
    return currentTheme === 'dark' ? this.darkColors : this.lightColors;
  }

  observe(callback) {
    this.observers.push(callback);
  }

  // MutationObserver for theme changes
}
```

**DateUtils.js:**
```javascript
export class DateUtils {
  static normalizeToISODate(value, fallback = null) {
    // Implementation from lines 76-101
  }

  static formatDateLabel(date, locale = 'id-ID') {
    // Implementation from lines 518-527
  }

  static computeRange(startDate, endDate, defaultDuration = 30) {
    // Helper for date range calculations
  }
}
```

### State Management Migration

#### Current Architecture

**Global State Access:**
```javascript
const state = window.kelolaTahapanPageState || bootstrap.state;
```

**Problems:**
- Tight coupling to global namespace
- Hard to test
- No type safety
- Side effects everywhere

#### Proposed Architecture

**Option A: Props/Dependency Injection (Recommended)**

```javascript
// Usage in framework component (Vue example)
<template>
  <div ref="chartContainer"></div>
</template>

<script>
import { ScurveChartService } from '@/modules/charts/ScurveChartService';

export default {
  props: {
    timeColumns: Array,
    volumeMap: Map,
    assignmentMap: Map,
    // ... other state props
  },

  data() {
    return {
      chartService: null,
    };
  },

  mounted() {
    this.chartService = new ScurveChartService(this.$refs.chartContainer);
    this.chartService.init();
    this.updateChart();
  },

  methods: {
    updateChart() {
      const dataset = this.chartService.buildDataset({
        timeColumns: this.timeColumns,
        volumeMap: this.volumeMap,
        assignmentMap: this.assignmentMap,
      });
      this.chartService.render(dataset);
    },
  },

  watch: {
    assignmentMap: {
      handler() {
        this.updateChart();
      },
      deep: true,
    },
  },

  beforeUnmount() {
    this.chartService.destroy();
  },
};
</script>
```

**Option B: Vuex/Pinia Store (if using Vue)**

```javascript
// store/modules/kelolaTahapan.js
export const kelolaTahapanModule = {
  state: () => ({
    timeColumns: [],
    volumeMap: new Map(),
    assignmentMap: new Map(),
    modifiedCells: new Map(),
    // ...
  }),

  getters: {
    scurveDataset(state) {
      const service = new ScurveChartService();
      return service.buildDataset(state);
    },

    ganttTasks(state) {
      const service = new GanttChartService();
      return service.buildTasks(state);
    },
  },

  mutations: {
    SET_ASSIGNMENT(state, { key, value }) {
      state.assignmentMap.set(key, value);
    },
    // ...
  },
};
```

### Testing Strategy

#### Unit Tests

**ScurveChartService.test.js:**
```javascript
import { describe, test, expect, beforeEach } from 'vitest';
import { ScurveChartService } from './ScurveChartService';

describe('ScurveChartService', () => {
  let service;
  let container;

  beforeEach(() => {
    container = document.createElement('div');
    service = new ScurveChartService(container);
  });

  describe('CurveCalculator', () => {
    test('calculates volume-based planned curve correctly', () => {
      const columns = [
        { id: 'col1', startDate: new Date('2025-01-01') },
        { id: 'col2', startDate: new Date('2025-01-08') },
      ];
      const volumeLookup = new Map([
        ['pek1', 100],
        ['pek2', 200],
      ]);
      const cellValues = new Map([
        ['pek1-col1', 100],
        ['pek2-col2', 100],
      ]);

      const dataset = service.buildDataset({
        timeColumns: columns,
        volumeMap: volumeLookup,
        assignmentMap: cellValues,
      });

      expect(dataset.planned).toEqual([33.33, 100]);
    });

    test('calculates ideal sigmoid curve when no assignments', () => {
      const columns = [
        { id: 'col1', startDate: new Date('2025-01-01') },
        { id: 'col2', startDate: new Date('2025-01-08') },
        { id: 'col3', startDate: new Date('2025-01-15') },
        { id: 'col4', startDate: new Date('2025-01-22') },
      ];

      const dataset = service.buildDataset({
        timeColumns: columns,
        volumeMap: new Map(),
        assignmentMap: new Map(),
      });

      // Sigmoid should produce S-shape (low, medium, medium, high)
      expect(dataset.planned[0]).toBeLessThan(20);
      expect(dataset.planned[3]).toBeGreaterThan(80);
    });
  });

  describe('Theme support', () => {
    test('returns correct colors for light theme', () => {
      document.documentElement.setAttribute('data-bs-theme', 'light');
      const colors = service.themeManager.getColors();

      expect(colors.plannedLine).toBe('#0d6efd');
      expect(colors.actualLine).toBe('#198754');
    });

    test('returns correct colors for dark theme', () => {
      document.documentElement.setAttribute('data-bs-theme', 'dark');
      const colors = service.themeManager.getColors();

      expect(colors.plannedLine).toBe('#60a5fa');
      expect(colors.actualLine).toBe('#34d399');
    });
  });
});
```

**GanttChartService.test.js:**
```javascript
import { describe, test, expect } from 'vitest';
import { GanttChartService } from './GanttChartService';

describe('GanttChartService', () => {
  describe('ProgressCalculator', () => {
    test('calculates volume-weighted progress correctly', () => {
      const state = {
        volumeMap: new Map([
          [1, 100],
          [2, 200],
        ]),
        assignmentMap: new Map([
          ['1-col1', 50],
          ['2-col1', 75],
        ]),
        timeColumns: [
          { id: 'col1', tahapanId: 'tahap1' },
        ],
        tahapanList: [
          { id: 'tahap1' },
        ],
      };

      const service = new GanttChartService(document.createElement('div'));
      const progressMap = service.progressCalculator.calculate(state);

      // (100*50 + 200*75) / (100 + 200) = 20000 / 300 = 66.67%
      expect(progressMap.get('tahap1').progress).toBeCloseTo(66.67, 2);
    });
  });

  describe('TaskBuilder', () => {
    test('builds hierarchy with correct indentation', () => {
      const state = {
        pekerjaanTree: [
          {
            id: 1,
            type: 'kategori',
            nama: 'Struktur',
            children: [
              { id: 2, type: 'pekerjaan', nama: 'Balok' },
              { id: 3, type: 'pekerjaan', nama: 'Kolom' },
            ],
          },
        ],
        // ... minimal state
      };

      const service = new GanttChartService(document.createElement('div'));
      const tasks = service.buildTasks(state);

      expect(tasks[0].metadata.pathParts).toEqual(['Struktur', 'Balok']);
      expect(tasks[1].metadata.pathParts).toEqual(['Struktur', 'Kolom']);
    });
  });
});
```

#### Integration Tests

**Test Scenarios:**
1. Full render cycle (state → dataset → chart)
2. Theme switching updates chart colors
3. Window resize triggers chart resize
4. View mode changes update Gantt layout
5. Assignment updates trigger chart refresh

### Error Handling

**Current State:** Minimal error handling, relies on console.warn

**Proposed Improvements:**

```javascript
export class ChartError extends Error {
  constructor(message, code, details = {}) {
    super(message);
    this.name = 'ChartError';
    this.code = code;
    this.details = details;
  }
}

export class ScurveChartService {
  buildDataset(state) {
    try {
      if (!state) {
        throw new ChartError(
          'State is required',
          'INVALID_STATE',
          { state }
        );
      }

      if (!Array.isArray(state.timeColumns) || state.timeColumns.length === 0) {
        throw new ChartError(
          'No time columns provided',
          'MISSING_COLUMNS',
          { timeColumns: state.timeColumns }
        );
      }

      // ... build dataset

    } catch (error) {
      if (error instanceof ChartError) {
        this.handleChartError(error);
      } else {
        this.handleUnexpectedError(error);
      }

      // Return fallback dataset
      return this.buildFallbackDataset();
    }
  }

  handleChartError(error) {
    console.error(`[ScurveChartService] ${error.message}`, error.details);

    // Emit event for application to handle
    this.emit('error', error);
  }
}
```

### Performance Optimizations

**Current Issues:**
1. No memoization of expensive calculations
2. Rebuilds entire dataset on every refresh
3. No debouncing on resize events

**Proposed Optimizations:**

```javascript
import { memoize } from 'lodash-es';

export class ScurveChartService {
  constructor(container, options) {
    // ...

    // Memoize expensive calculations
    this.buildDataset = memoize(
      this.buildDataset.bind(this),
      (state) => {
        // Cache key: hash of relevant state properties
        return JSON.stringify({
          columns: state.timeColumns,
          assignments: Array.from(state.assignmentMap),
          volumes: Array.from(state.volumeMap),
        });
      }
    );

    // Debounce resize
    this.resize = debounce(this.resize.bind(this), 150);
  }
}
```

---

## Migration Effort Estimation

### Time Breakdown

| Task | Hours | Complexity |
|------|-------|------------|
| **Phase 1: Foundation** | | |
| Set up ES6 module structure | 4 | Easy |
| Create TypeScript interfaces | 3 | Easy |
| Configure build tools (Webpack/Vite) | 2 | Easy |
| Create utility modules (DateUtils, ThemeManager) | 3 | Easy |
| **Subtotal** | **12** | |
| | | |
| **Phase 2: S-Curve Migration** | | |
| Migrate to ScurveChartService class | 6 | Medium |
| Create CurveCalculator utility | 4 | Medium |
| Wrap ECharts in reactive component | 3 | Medium |
| Write unit tests | 4 | Medium |
| **Subtotal** | **17** | |
| | | |
| **Phase 3: Gantt Migration** | | |
| Migrate to GanttChartService class | 8 | Medium-High |
| Create ProgressCalculator utility | 3 | Medium |
| Create TaskBuilder utility | 5 | Medium |
| Wrap Frappe Gantt in reactive component | 4 | Medium |
| Write unit tests | 5 | Medium |
| **Subtotal** | **25** | |
| | | |
| **Phase 4: UI Integration** | | |
| Migrate gantt_tab.js to components | 2 | Easy |
| Integrate with framework (Vue/React) | 4 | Medium |
| Update page architecture | 3 | Medium |
| **Subtotal** | **9** | |
| | | |
| **Phase 5: Testing & Documentation** | | |
| Write integration tests | 6 | Medium |
| End-to-end testing | 4 | Medium |
| Update documentation | 3 | Easy |
| Code review and refinement | 4 | Medium |
| **Subtotal** | **17** | |
| | | |
| **TOTAL** | **80 hours** | **(10 days)** |

### Risk Factors

**High Risk:**
- Frappe Gantt library compatibility (may need version upgrade)
- Complex state dependencies (breaking changes possible)
- Date handling edge cases (timezone, DST issues)

**Medium Risk:**
- ECharts API changes
- Performance regression in large datasets
- Theme switching integration

**Low Risk:**
- Utility function migration
- UI component binding
- Test coverage

### Recommended Staffing

**Ideal Team:**
- 1 Senior Developer (lead migration, complex algorithms)
- 1 Mid-level Developer (utilities, testing)

**Timeline:** 2 weeks sprint

**Milestone Checkpoints:**
- Day 3: Foundation complete, build working
- Day 7: S-Curve migrated and tested
- Day 10: Gantt migrated and tested
- Day 12: Integration complete
- Day 14: Testing complete, ready for deployment

---

## Conclusion

### Summary of Findings

The legacy chart modules are well-structured but tightly coupled to global namespace and IIFE pattern. Migration to ES6 modules is **feasible** with **medium complexity**.

**Strengths:**
- Excellent inline documentation
- Pure functions with clear responsibilities
- Sophisticated algorithms (sigmoid, volume-weighted)
- Good separation between data processing and rendering

**Weaknesses:**
- Global state dependencies
- No type safety
- Limited error handling
- Manual memory management (event listeners)

### Migration Viability

**Verdict: RECOMMENDED**

**Reasons:**
1. Code is clean and well-documented (easy to understand)
2. Most functions are pure (easy to test)
3. Clear business logic separation
4. Modern ES6 will improve maintainability significantly

**Confidence Level: High (85%)**

### Next Steps

1. **Immediate:**
   - Get stakeholder approval for 2-week sprint
   - Set up development branch
   - Configure build tools

2. **Short-term (Week 1):**
   - Create ES6 module structure
   - Write TypeScript interfaces
   - Begin S-Curve migration

3. **Medium-term (Week 2):**
   - Complete Gantt migration
   - Integration and testing
   - Code review

4. **Long-term (Post-migration):**
   - Monitor performance in production
   - Gather user feedback
   - Plan for additional chart types

---

## Appendix

### A. Glossary

| Term | Definition |
|------|------------|
| **AHSP** | Analisis Harga Satuan Pekerjaan (Unit Price Analysis) |
| **Pekerjaan** | Work item / task in project schedule |
| **Tahapan** | Project phase / milestone |
| **Kurva S** | S-Curve (cumulative progress chart) |
| **Volume** | Quantity of work (m², m³, unit, etc.) |
| **IIFE** | Immediately Invoked Function Expression |
| **Sigmoid** | S-shaped mathematical curve |

### B. External Library Versions

| Library | Current | Recommended |
|---------|---------|-------------|
| ECharts | Unknown | 5.5.0+ |
| Frappe Gantt | Unknown | Latest (2.x) |
| Bootstrap | 5.x | 5.3+ |

### C. Related Files

**Supporting Modules (not analyzed in detail):**
- `shared_module.js` - Shared utilities
- `time_column_generator_module.js` - Time column generation
- `validation_module.js` - Input validation
- `data_loader_module.js` - Data fetching
- `grid_module.js` - Grid component
- `save_handler_module.js` - Save operations
- `module_manifest.js` - Module registry

**Recommendation:** Analyze these modules in follow-up assessment.

### D. Browser Compatibility

**Target Browsers:**
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

**ES6 Features Used (Post-Migration):**
- Classes
- Arrow functions
- Template literals
- Destructuring
- Modules (import/export)
- Map/Set
- Promises

**Polyfills Required:** None (modern browsers only)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-20
**Maintained By:** Development Team
