# Grid Module Analysis - Comprehensive Documentation

**File**: `d:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\jadwal_pekerjaan\kelola_tahapan\grid_module.js`

**Lines of Code**: 856 lines
**Pattern**: IIFE (Immediately Invoked Function Execution)
**Target for Migration**: ES6 Class-Based Architecture

---

## Executive Summary

This module is the **core rendering and interaction engine** for the Kelola Tahapan grid system. It handles:
- Dual-panel grid rendering (left: tree structure, right: time columns)
- In-cell editing with percentage/volume display modes
- Tree expand/collapse functionality
- Cell navigation (keyboard + mouse)
- Progress calculation and validation
- Scroll synchronization between panels
- Real-time state management with modified cell tracking

---

## 1. Module Architecture

### 1.1 IIFE Pattern (Legacy)
```javascript
(function() {
  'use strict';
  // Lines 1-856: Entire module wrapped in IIFE
  // Global namespace pollution via window.KelolaTahapanPageModules
})();
```

**Migration Target**: ES6 Class or Module
```javascript
// Recommended structure:
export class GridRenderer {
  constructor(state, utils, helpers) { /* ... */ }
  // Methods...
}
```

### 1.2 Namespace Pollution
```javascript
// Lines 22-23
const globalModules = window.KelolaTahapanPageModules = window.KelolaTahapanPageModules || {};
const moduleStore = globalModules.grid = Object.assign({}, globalModules.grid || {});
```

**Issues**:
- Relies on global `window.KelolaTahapanPageModules`
- Mutates global namespace
- No encapsulation

**Migration Strategy**: Use ES6 modules with explicit imports/exports

---

## 2. Main Functions & Responsibilities

### 2.1 State Management

#### `resolveState(stateOverride)` - Lines 25-36
**Purpose**: Resolves the application state from multiple possible sources

**Logic Flow**:
1. Check for override parameter
2. Check `window.kelolaTahapanPageState`
3. Check `bootstrap.state`
4. Return null if none found

**Dependencies**: Global state objects

**Key Code**:
```javascript
function resolveState(stateOverride) {
  if (stateOverride) return stateOverride;
  if (window.kelolaTahapanPageState) return window.kelolaTahapanPageState;
  if (bootstrap && bootstrap.state) return bootstrap.state;
  return null;
}
```

**Migration Notes**:
- Convert to class method
- Accept state via constructor/dependency injection
- Remove global fallbacks

---

#### `getEffectiveCellValue(state, nodeId, columnId, fallbackSaved)` - Lines 214-235
**Purpose**: Determines the current value of a cell (modified or saved)

**Logic**:
1. Build cell key: `${nodeId}-${columnId}`
2. Check `state.modifiedCells` Map for pending changes
3. Fall back to saved value from `state.assignmentMap`
4. Return both `value` and `modifiedValue`

**Key Pattern**: Dual-value tracking for dirty state detection

**Code**:
```javascript
function getEffectiveCellValue(state, nodeId, columnId, fallbackSaved = 0) {
  const cellKey = `${nodeId}-${columnId}`;
  const savedNumeric = typeof fallbackSaved === 'number'
    ? fallbackSaved
    : parseFloat(fallbackSaved) || 0;

  let modifiedValue;
  if (state.modifiedCells instanceof Map && state.modifiedCells.has(cellKey)) {
    const candidate = parseFloat(state.modifiedCells.get(cellKey));
    if (Number.isFinite(candidate)) {
      modifiedValue = candidate;
    }
  }

  const value = modifiedValue !== undefined ? modifiedValue : savedNumeric;
  return { value, modifiedValue };
}
```

---

### 2.2 DOM Resolution

#### `resolveDom(state)` - Lines 38-49
**Purpose**: Centralizes DOM element references

**Elements**:
- `leftThead`, `rightThead` - Header tables
- `leftTbody`, `rightTbody` - Body tables
- `leftPanelScroll`, `rightPanelScroll` - Scrollable containers
- `timeHeaderRow` - Time column headers

**Code**:
```javascript
function resolveDom(state) {
  const domRefs = (state && state.domRefs) || {};
  return {
    leftThead: domRefs.leftThead || document.getElementById('left-thead'),
    rightThead: domRefs.rightThead || document.getElementById('right-thead'),
    leftTbody: domRefs.leftTbody || document.getElementById('left-tbody'),
    rightTbody: domRefs.rightTbody || document.getElementById('right-tbody'),
    leftPanelScroll: domRefs.leftPanelScroll || document.querySelector('.left-panel-scroll'),
    rightPanelScroll: domRefs.rightPanelScroll || document.querySelector('.right-panel-scroll'),
    timeHeaderRow: domRefs.timeHeaderRow || document.getElementById('time-header-row'),
  };
}
```

**Migration**: Convert to class property with lazy initialization

---

### 2.3 Utility Preparation

#### `prepareUtils(contextUtils)` - Lines 51-79
**Purpose**: Provides utility functions with fallback defaults

**Utilities**:
- `escapeHtml`: Sanitizes text for HTML rendering
- `formatNumber`: Indonesian locale number formatting

**Code**:
```javascript
const defaultEscapeHtml = (text) => {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
};

const defaultFormatNumber = (num, decimals = 2) => {
  if (num === null || num === undefined || num === '') return '-';
  const n = parseFloat(num);
  if (Number.isNaN(n)) return '-';
  return n.toLocaleString('id-ID', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
};
```

**Migration**: Extract to separate utility module

---

### 2.4 Rendering Functions

#### `renderTables(context)` - Lines 81-107
**Purpose**: Main entry point for grid rendering

**Process**:
1. Resolve state and utilities
2. Initialize left/right row arrays
3. Recursively render each tree node
4. Return HTML strings for both panels

**Code**:
```javascript
function renderTables(context = {}) {
  const state = resolveState(context.state);
  if (!state || !Array.isArray(state.pekerjaanTree)) {
    return null;
  }

  const utils = prepareUtils(context.utils);
  const cfg = {
    state,
    utils,
    leftRows: [],
    rightRows: [],
  };

  state.pekerjaanTree.forEach((node) => {
    renderLeftRow(node, cfg);
    renderRightRow(node, cfg);
  });

  const leftHTML = cfg.leftRows.join('');
  const rightHTML = cfg.rightRows.join('');

  return { leftHTML, rightHTML };
}
```

**Performance Consideration**: Uses string concatenation instead of DOM manipulation for speed

---

#### `renderLeftRow(node, ctx, parentVisible)` - Lines 114-170
**Purpose**: Renders a single row in the left panel (tree structure)

**Features**:
- Tree toggle icons for parent nodes
- Volume display for `pekerjaan` nodes
- Progress chip indicators
- Volume warning pills
- Hierarchical indentation via `level-N` CSS classes

**Key Elements**:
```javascript
// Toggle icon for expandable nodes
if (node.children && node.children.length > 0) {
  toggleIcon = `<span class="tree-toggle ${isExpanded ? '' : 'collapsed'}" data-node-id="${node.id}">
    <i class="bi bi-caret-down-fill"></i>
  </span>`;
}

// Volume from volumeMap
const volumeValue = (state.volumeMap && state.volumeMap.has(node.id))
  ? state.volumeMap.get(node.id)
  : 0;

// Progress chip
const progressChip = node.type === 'pekerjaan'
  ? renderProgressChip(node.id, state)
  : '';
```

**HTML Structure**:
```html
<tr class="row-pekerjaan" data-node-id="123" data-row-index="5">
  <td class="col-tree"><!-- toggle icon --></td>
  <td class="col-uraian level-2">
    <div class="tree-node">
      Nama Pekerjaan
      <span class="kt-volume-pill">Perlu update volume</span>
      <span class="progress-chip progress-chip--ok">95.5%</span>
    </div>
  </td>
  <td class="col-volume text-right">1,250.00</td>
  <td class="col-satuan">m2</td>
</tr>
```

**Recursive Pattern**: Processes children if node is expanded

---

#### `renderRightRow(node, ctx, parentVisible)` - Lines 172-198
**Purpose**: Renders a single row in the right panel (time columns)

**Features**:
- Maps over `state.timeColumns` to generate cells
- Synchronizes row visibility with left panel
- Delegates cell rendering to `renderTimeCell()`

**Code**:
```javascript
function renderRightRow(node, ctx, parentVisible = true) {
  const { state, rightRows } = ctx;
  const isExpanded = nodeIsExpanded(state, node.id);
  const isVisible = parentVisible;

  const timeCells = state.timeColumns
    .map((col) => renderTimeCell(node, col, ctx))
    .join('');

  rightRows.push(`
    <tr class="${rowClass}" data-node-id="${node.id}" data-row-index="${rightRows.length}">
      ${timeCells}
    </tr>
  `);

  if (node.children && node.children.length > 0) {
    node.children.forEach((child) => {
      renderRightRow(child, ctx, isExpanded && isVisible);
    });
  }
}
```

---

#### `renderTimeCell(node, column, ctx)` - Lines 279-320
**Purpose**: Renders an individual time cell with edit capability

**Cell States**:
- `readonly`: Non-pekerjaan nodes (kategori, sub_kategori)
- `editable`: Pekerjaan nodes
- `saved`: Has value in database
- `modified`: Changed but not saved

**Display Modes**:
- `percentage`: Shows progress percentage (0-100%)
- `volume`: Shows calculated volume (volume × percentage / 100)

**Code**:
```javascript
function renderTimeCell(node, column, ctx) {
  if (node.type !== 'pekerjaan') {
    return `<td class="time-cell readonly" data-node-id="${node.id}" data-col-id="${column.id}"></td>`;
  }

  const cellKey = `${node.id}-${column.id}`;
  const savedValue = getAssignmentValue(state, cellKey);
  const { value: currentValue, modifiedValue } = getEffectiveCellValue(state, node.id, column.id, savedValue);

  let cellClasses = 'time-cell editable';
  if (savedValue > 0) cellClasses += ' saved';
  if (modifiedValue !== undefined && modifiedValue !== savedValue) cellClasses += ' modified';

  let displayValue = '';
  if (currentValue > 0 || (currentValue === 0 && savedValue > 0)) {
    if (state.displayMode === 'volume') {
      const volume = state.volumeMap && state.volumeMap.has(node.id)
        ? state.volumeMap.get(node.id)
        : 0;
      const volValue = (volume * currentValue / 100).toFixed(2);
      displayValue = `<span class="cell-value volume">${volValue}</span>`;
    } else {
      displayValue = `<span class="cell-value percentage">${Number(currentValue).toFixed(1)}</span>`;
    }
  }

  return `<td class="${cellClasses}"
              data-node-id="${node.id}"
              data-col-id="${column.id}"
              data-value="${currentValue}"
              data-saved-value="${savedValue}"
              tabindex="0">
            ${displayValue}
          </td>`;
}
```

**Data Attributes**: All cell state stored in `data-*` attributes for event handlers

---

#### `renderProgressChip(nodeId, state)` - Lines 255-277
**Purpose**: Generates progress indicator badge

**Validation Logic**:
```javascript
const total = calculateRowProgress(nodeId, state);
const tolerance = 0.5;

if (total > 100 + tolerance) {
  badgeClass = 'progress-chip--over';
  label = 'Over 100%';
} else if (total < 100 - tolerance) {
  badgeClass = 'progress-chip--under';
  label = 'Under 100%';
} else {
  badgeClass = 'progress-chip--ok';
  label = 'On Track';
}
```

**HTML**:
```html
<span class="progress-chip progress-chip--ok" title="On Track">
  98.5%
</span>
```

---

#### `calculateRowProgress(nodeId, state)` - Lines 237-253
**Purpose**: Sums all time column percentages for a row

**Code**:
```javascript
function calculateRowProgress(nodeId, state) {
  if (!state || !Array.isArray(state.timeColumns) || state.timeColumns.length === 0) {
    return null;
  }

  let total = 0;
  state.timeColumns.forEach((column) => {
    const { value } = getEffectiveCellValue(state, nodeId, column.id);
    const numeric = Number.isFinite(value) ? value : parseFloat(value) || 0;
    total += numeric;
  });

  if (!Number.isFinite(total)) return null;
  return parseFloat(total.toFixed(1));
}
```

**Usage**: Validates that row totals equal 100%

---

#### `renderTimeHeaders(options)` - Lines 759-805
**Purpose**: Renders time column headers with special formatting

**Features**:
- Two-line headers (label + range)
- Monthly mode: Strips text after colon
- Tooltip support
- Uses DocumentFragment for performance

**Code**:
```javascript
function renderTimeHeaders(options = {}) {
  const ctx = createContext(options);
  if (!ctx) return 'legacy';

  const { state, utils, dom } = ctx;
  const headerRow = dom.timeHeaderRow || document.getElementById('time-header-row');

  if (!headerRow || !Array.isArray(state.timeColumns)) {
    return 'legacy';
  }

  headerRow.innerHTML = '';
  const fragment = document.createDocumentFragment();

  state.timeColumns.forEach((col) => {
    const th = document.createElement('th');
    th.dataset.colId = col.id;

    const line1 = col.label || '';
    const line2 = col.rangeLabel || col.subLabel || '';
    const columnMode = (col.generationMode || col.type || '').toLowerCase();
    const isMonthly = columnMode === 'monthly';

    let safeLine1 = utils.escapeHtml(line1);
    const safeLine2 = utils.escapeHtml(line2);

    // Monthly mode: remove colon suffix
    if (isMonthly && typeof safeLine1 === 'string') {
      const colonIndex = safeLine1.indexOf(':');
      if (colonIndex !== -1) {
        safeLine1 = safeLine1.slice(0, colonIndex).trim();
      }
    }

    const headerParts = [`<span class="time-header__label">${safeLine1}</span>`];
    if (line2 && !isMonthly) {
      headerParts.push(`<span class="time-header__range">${safeLine2}</span>`);
    }
    th.innerHTML = `<div class="time-header">${headerParts.join('')}</div>`;
    th.title = col.tooltip || (line2 ? `${line1} ${line2}`.trim() : line1);

    fragment.appendChild(th);
  });

  headerRow.appendChild(fragment);
  return headerRow;
}
```

---

### 2.5 Event Handling

#### `attachEvents(options)` - Lines 348-368
**Purpose**: Binds all user interaction handlers

**Handlers**:
- Tree toggles: `click` → `handleTreeToggle`
- Editable cells:
  - `click` → `handleCellClick` (selection)
  - `dblclick` → `handleCellDoubleClick` (edit)
  - `keydown` → `handleCellKeydown` (keyboard nav + edit)

**Code**:
```javascript
function attachEvents(options = {}) {
  const ctx = createContext(options);
  if (!ctx) return 'legacy';

  const treeHandler = (event) => handleTreeToggle(event, ctx);
  const cellClickHandler = (event) => handleCellClick(event, ctx);
  const cellDoubleHandler = (event) => handleCellDoubleClick(event, ctx);
  const cellKeyHandler = (event) => handleCellKeydown(event, ctx);

  document.querySelectorAll('.tree-toggle').forEach((toggle) => {
    toggle.addEventListener('click', treeHandler);
  });

  document.querySelectorAll('.time-cell.editable').forEach((cell) => {
    cell.addEventListener('click', cellClickHandler);
    cell.addEventListener('dblclick', cellDoubleHandler);
    cell.addEventListener('keydown', cellKeyHandler);
  });

  return ctx;
}
```

**Migration Concern**: Direct DOM queries should be scoped to container element

---

#### `handleTreeToggle(event, ctx)` - Lines 370-391
**Purpose**: Expands/collapses tree nodes

**Process**:
1. Toggle `collapsed` class on icon
2. Update `state.expandedNodes` Set
3. Show/hide child rows via `toggleNodeChildren()`
4. Sync row heights after 10ms delay

**Code**:
```javascript
function handleTreeToggle(event, ctx) {
  event.stopPropagation();
  const target = event.currentTarget;
  if (!target) return;

  const nodeId = target.dataset.nodeId;
  const isExpanded = !target.classList.contains('collapsed');

  if (isExpanded) {
    ctx.state.expandedNodes.delete(nodeId);
    target.classList.add('collapsed');
  } else {
    ctx.state.expandedNodes.add(nodeId);
    target.classList.remove('collapsed');
  }

  toggleNodeChildren(nodeId, !isExpanded, ctx);

  setTimeout(() => {
    moduleStore.syncRowHeights(ctx.state);
  }, 10);
}
```

**Performance**: Uses `setTimeout` for deferred height sync after DOM updates

---

#### `toggleNodeChildren(nodeId, show, ctx)` - Lines 393-435
**Purpose**: Shows/hides descendant rows based on tree state

**Algorithm**:
1. Find parent row by `data-node-id`
2. Extract parent level from `.level-N` class
3. Toggle `row-hidden` class on all subsequent rows with higher level
4. Stop when encountering same/lower level (sibling/uncle)

**Code**:
```javascript
function toggleNodeChildren(nodeId, show, ctx) {
  const leftBody = ctx.dom.leftTbody || document.getElementById('left-tbody');
  const rightBody = ctx.dom.rightTbody || document.getElementById('right-tbody');
  if (!leftBody || !rightBody) return;

  const leftRows = leftBody.querySelectorAll('tr[data-node-id]');
  const rightRows = rightBody.querySelectorAll('tr[data-node-id]');

  let foundParent = false;
  let parentLevel = -1;

  leftRows.forEach((row, index) => {
    if (row.dataset.nodeId === nodeId) {
      foundParent = true;
      const uraianCell = row.querySelector('.col-uraian');
      const levelMatch = uraianCell ? uraianCell.className.match(/level-(\d+)/) : null;
      parentLevel = levelMatch ? parseInt(levelMatch[1], 10) : -1;
      return;
    }

    if (!foundParent) return;

    const rowUraianCell = row.querySelector('.col-uraian');
    const rowLevelMatch = rowUraianCell ? rowUraianCell.className.match(/level-(\d+)/) : null;
    const rowLevel = rowLevelMatch ? parseInt(rowLevelMatch[1], 10) : -1;

    if (rowLevel > parentLevel) {
      if (show) {
        row.classList.remove('row-hidden');
        const rightRow = rightRows[index];
        if (rightRow) rightRow.classList.remove('row-hidden');
      } else {
        row.classList.add('row-hidden');
        const rightRow = rightRows[index];
        if (rightRow) rightRow.classList.add('row-hidden');
      }
    } else {
      foundParent = false;
    }
  });
}
```

**Fragility**: Relies on CSS class parsing and index correlation between panels

---

#### `handleCellClick(event, ctx)` - Lines 437-443
**Purpose**: Selects cell and updates `state.currentCell`

**Code**:
```javascript
function handleCellClick(event, ctx) {
  const cell = event.currentTarget;
  if (!cell) return;
  document.querySelectorAll('.time-cell.selected').forEach((c) => c.classList.remove('selected'));
  cell.classList.add('selected');
  ctx.state.currentCell = cell;
}
```

---

#### `handleCellDoubleClick(event, ctx)` - Lines 445-449
**Purpose**: Enters edit mode on double-click

**Code**:
```javascript
function handleCellDoubleClick(event, ctx) {
  const cell = event.currentTarget;
  if (!cell) return;
  enterEditMode(cell, ctx);
}
```

---

#### `handleCellKeydown(event, ctx)` - Lines 451-493
**Purpose**: Keyboard shortcuts for cell interaction

**Supported Keys**:
- `Enter` → Enter edit mode
- `Tab` / `Shift+Tab` → Navigate right/left
- Arrow keys → Navigate up/down/left/right
- `0-9` → Enter edit mode with initial digit

**Code**:
```javascript
function handleCellKeydown(event, ctx) {
  const cell = event.currentTarget;
  if (!cell || cell.classList.contains('editing')) return;

  switch (event.key) {
    case 'Enter':
      enterEditMode(cell, ctx);
      event.preventDefault();
      break;
    case 'Tab':
      navigateCell(ctx, event.shiftKey ? 'left' : 'right');
      event.preventDefault();
      break;
    case 'ArrowUp':
      navigateCell(ctx, 'up');
      event.preventDefault();
      break;
    case 'ArrowDown':
      navigateCell(ctx, 'down');
      event.preventDefault();
      break;
    case 'ArrowLeft':
      if (!event.shiftKey) {
        navigateCell(ctx, 'left');
        event.preventDefault();
      }
      break;
    case 'ArrowRight':
      if (!event.shiftKey) {
        navigateCell(ctx, 'right');
        event.preventDefault();
      }
      break;
    default:
      if (event.key.length === 1 && /[0-9]/.test(event.key)) {
        enterEditMode(cell, ctx, event.key);
        event.preventDefault();
      }
      break;
  }
}
```

**UX Pattern**: Excel-like keyboard navigation

---

### 2.6 Cell Editing

#### `enterEditMode(cell, ctx, initialValue)` - Lines 495-545
**Purpose**: Creates inline number input for cell editing

**Process**:
1. Add `editing` class to cell
2. Create `<input type="number">` with constraints (0-100, step 0.01)
3. Attach `blur` and `keydown` handlers
4. Store original content in `cell._originalContent`
5. Focus and select input

**Code**:
```javascript
function enterEditMode(cell, ctx, initialValue = '') {
  if (cell.classList.contains('readonly')) return;

  ctx.state.currentCell = cell;
  cell.classList.add('editing');
  const currentValue = initialValue || cell.dataset.value || '';

  const input = document.createElement('input');
  input.type = 'number';
  input.step = '0.01';
  input.min = '0';
  input.max = '100';
  input.value = initialValue || currentValue;
  input.className = 'cell-input';

  input.addEventListener('blur', () => {
    if (!cell._isExiting) {
      exitEditMode(cell, input, ctx);
    }
  });

  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      cell._isExiting = true;
      exitEditMode(cell, input, ctx);
      navigateCell(ctx, 'down');
      event.preventDefault();
    } else if (event.key === 'Escape') {
      cell._isExiting = true;
      cell.classList.remove('editing');
      cell.innerHTML = cell._originalContent;
      cell.focus();
    } else if (event.key === 'Tab') {
      const direction = event.shiftKey ? 'left' : 'right';
      cell._pendingNavigation = direction;
      cell._isExiting = true;
      const applied = exitEditMode(cell, input, ctx);
      if (applied !== false) {
        navigateCell(ctx, direction);
      }
      cell._pendingNavigation = null;
      event.preventDefault();
    }
  });

  cell._originalContent = cell.innerHTML;
  cell.innerHTML = '';
  cell.appendChild(input);
  input.focus();
  input.select();
}
```

**State Flags**:
- `cell._isExiting`: Prevents double-trigger on blur
- `cell._pendingNavigation`: Stores navigation direction for post-save
- `cell._originalContent`: Rollback target on escape

**UX**: `Enter` moves down, `Tab` moves right (Excel-like)

---

#### `exitEditMode(cell, input, ctx)` - Lines 547-637
**Purpose**: Validates, saves, and displays edited cell value

**Validation**:
```javascript
if (newValue < 0 || newValue > 100) {
  ctx.helpers.showToast('Value must be between 0-100', 'danger');
  cell.innerHTML = cell._originalContent;
  cell._isExiting = false;
  cell._pendingNavigation = null;
  cell.focus();
  return false;
}
```

**State Update**:
```javascript
const hasChanged = Math.abs(newValue - previousValue) > 0.0001;

if (hasChanged) {
  if (newValue === 0 && savedValue === 0) {
    ctx.state.modifiedCells.delete(cellKey);
  } else {
    ctx.state.modifiedCells.set(cellKey, newValue);
  }

  cell.classList.remove('saved', 'modified');
  if (savedValue > 0) cell.classList.add('saved');
  if (newValue !== savedValue) cell.classList.add('modified');

  cell.dataset.value = newValue;
}
```

**Display Update**:
```javascript
if (ctx.state.displayMode === 'percentage') {
  displayValue = `<span class="cell-value percentage">${newValue.toFixed(1)}</span>`;
} else {
  const node = ctx.state.flatPekerjaan.find((n) => n.id == cell.dataset.nodeId);
  const nodeId = node ? node.id : cell.dataset.nodeId;
  const volume = ctx.state.volumeMap && ctx.state.volumeMap.has(nodeId)
    ? ctx.state.volumeMap.get(nodeId)
    : 0;
  const volValue = (volume * newValue / 100).toFixed(2);
  displayValue = `<span class="cell-value volume">${volValue}</span>`;
}
```

**Callbacks**:
```javascript
ctx.helpers.updateStatusBar();
if (typeof ctx.helpers.onProgressChange === 'function') {
  try {
    ctx.helpers.onProgressChange({
      cellKey,
      pekerjaanId: cell.dataset.nodeId,
      columnId: cell.dataset.colId,
      newValue,
      previousValue,
      savedValue,
    });
  } catch (err) {
    console.warn('[KelolaTahapan][Grid] onProgressChange handler failed', err);
  }
}
```

**Return Value**:
- `true`: Value applied successfully
- `false`: Validation failed

---

#### `navigateCell(ctx, direction)` - Lines 639-677
**Purpose**: Moves focus to adjacent cell

**Directions**:
- `up` / `down`: Previous/next row, same column
- `left` / `right`: Previous/next cell in row

**Code**:
```javascript
function navigateCell(ctx, direction) {
  if (!ctx.state.currentCell) return;

  const currentRow = ctx.state.currentCell.closest('tr');
  if (!currentRow) return;
  const currentIndex = Array.from(currentRow.children).indexOf(ctx.state.currentCell);
  let nextCell = null;

  switch (direction) {
    case 'up': {
      const prevRow = currentRow.previousElementSibling;
      if (prevRow && !prevRow.classList.contains('row-hidden')) {
        nextCell = prevRow.children[currentIndex];
      }
      break;
    }
    case 'down': {
      const nextRow = currentRow.nextElementSibling;
      if (nextRow && !nextRow.classList.contains('row-hidden')) {
        nextCell = nextRow.children[currentIndex];
      }
      break;
    }
    case 'left':
      nextCell = ctx.state.currentCell.previousElementSibling;
      break;
    case 'right':
      nextCell = ctx.state.currentCell.nextElementSibling;
      break;
  }

  if (nextCell && nextCell.classList.contains('time-cell')) {
    ctx.state.currentCell = nextCell;
    nextCell.focus();
    nextCell.click();
  }
}
```

**Edge Case**: Skips hidden rows (collapsed nodes)

---

### 2.7 UI Synchronization

#### `syncHeaderHeights(stateOverride)` - Lines 679-695
**Purpose**: Ensures left and right headers have same height

**Code**:
```javascript
function syncHeaderHeights(stateOverride) {
  const state = resolveState(stateOverride);
  if (!state) return;

  const dom = resolveDom(state);
  const leftHeaderRow = dom.leftThead ? dom.leftThead.querySelector('tr') : document.querySelector('#left-thead tr');
  const rightHeaderRow = dom.rightThead ? dom.rightThead.querySelector('tr') : document.querySelector('#right-thead tr');

  if (!leftHeaderRow || !rightHeaderRow) return;

  leftHeaderRow.style.height = '';
  rightHeaderRow.style.height = '';

  const maxHeight = Math.max(leftHeaderRow.offsetHeight, rightHeaderRow.offsetHeight);
  leftHeaderRow.style.height = `${maxHeight}px`;
  rightHeaderRow.style.height = `${maxHeight}px`;
}
```

**When Called**: After rendering headers

---

#### `syncRowHeights(stateOverride)` - Lines 697-719
**Purpose**: Ensures left and right rows have same height

**Code**:
```javascript
function syncRowHeights(stateOverride) {
  const state = resolveState(stateOverride);
  if (!state) return;

  const dom = resolveDom(state);
  const leftRows = dom.leftTbody ? dom.leftTbody.querySelectorAll('tr') : [];
  const rightRows = dom.rightTbody ? dom.rightTbody.querySelectorAll('tr') : [];

  leftRows.forEach((leftRow, index) => {
    const rightRow = rightRows[index];
    if (!rightRow) return;

    leftRow.style.height = '';
    rightRow.style.height = '';

    const leftHeight = leftRow.offsetHeight;
    const rightHeight = rightRow.offsetHeight;
    const maxHeight = Math.max(leftHeight, rightHeight);

    leftRow.style.height = `${maxHeight}px`;
    rightRow.style.height = `${maxHeight}px`;
  });
}
```

**When Called**: After tree expand/collapse, initial render

**Performance**: Synchronous layout reads (potential optimization target)

---

#### `setupScrollSync(stateOverride)` - Lines 721-757
**Purpose**: Synchronizes vertical scroll between left and right panels

**Pattern**: Bidirectional scroll mirroring

**Code**:
```javascript
function setupScrollSync(stateOverride) {
  const state = resolveState(stateOverride);
  if (!state) return;
  state.cache = state.cache || {};

  if (state.cache.gridScrollSyncBound) {
    return;
  }

  const dom = resolveDom(state);
  const leftPanel = dom.leftPanelScroll;
  const rightPanel = dom.rightPanelScroll;

  if (!leftPanel || !rightPanel) return;

  const syncFromRight = () => {
    if (leftPanel.scrollTop !== rightPanel.scrollTop) {
      leftPanel.scrollTop = rightPanel.scrollTop;
    }
  };

  const syncFromLeft = () => {
    if (rightPanel.scrollTop !== leftPanel.scrollTop) {
      rightPanel.scrollTop = leftPanel.scrollTop;
    }
  };

  rightPanel.addEventListener('scroll', syncFromRight, { passive: true });
  leftPanel.addEventListener('scroll', syncFromLeft, { passive: true });

  state.cache.gridScrollSyncBound = {
    syncFromRight,
    syncFromLeft,
  };
}
```

**Optimization**: Uses `passive: true` for scroll performance

**State Caching**: Stores handlers in `state.cache` to prevent duplicate binding

---

### 2.8 Context Creation

#### `createContext(options)` - Lines 322-346
**Purpose**: Assembles all dependencies for module operations

**Structure**:
```javascript
{
  state: {
    pekerjaanTree: [],
    timeColumns: [],
    volumeMap: Map,
    assignmentMap: Map,
    modifiedCells: Map,
    expandedNodes: Set,
    currentCell: HTMLElement,
    displayMode: 'percentage' | 'volume',
    flatPekerjaan: [],
    domRefs: {},
    cache: {}
  },
  utils: {
    escapeHtml: Function,
    formatNumber: Function
  },
  dom: {
    leftThead, rightThead,
    leftTbody, rightTbody,
    leftPanelScroll, rightPanelScroll,
    timeHeaderRow
  },
  helpers: {
    showToast: Function,
    updateStatusBar: Function,
    onProgressChange: Function
  }
}
```

**Code**:
```javascript
function createContext(options = {}) {
  const state = resolveState(options.state);
  if (!state) return null;

  const utils = prepareUtils(options.utils);
  const dom = resolveDom(state);
  const helpers = Object.assign(
    {
      showToast: (options.helpers && typeof options.helpers.showToast === 'function')
        ? options.helpers.showToast
        : (typeof window.showToast === 'function' ? window.showToast : () => {}),
      updateStatusBar: (options.helpers && typeof options.helpers.updateStatusBar === 'function')
        ? options.helpers.updateStatusBar
        : () => {},
      onProgressChange: (options.helpers && typeof options.helpers.onProgressChange === 'function')
        ? options.helpers.onProgressChange
        : () => {},
    },
    moduleStore.helpers || {},
    options.helpers || {},
  );

  const ctx = { state, utils, dom, helpers };
  return ctx;
}
```

---

### 2.9 Module Registration (Bootstrap Bridge)

#### Lines 820-855
**Purpose**: Registers module with legacy bootstrap system

**Bridge Pattern**: Delegates to `window[manifest.globals.facade].grid`

**Code**:
```javascript
const bridge = () => {
  const facade = window[manifest.globals.facade];
  if (!facade || !facade.grid) {
    return {};
  }
  return facade.grid;
};

bootstrap.registerModule(meta.id, {
  namespace: meta.namespace,
  pageId: manifest.pageId,
  description: meta.description,
  onRegister(context) {
    bootstrap.log.info('Kelola Tahapan grid module (bridge) registered.');
    if (context && context.emit) {
      context.emit('kelola_tahapan.grid:registered', { manifest, meta });
    }
  },
  init: (...args) => (bridge().loadAllData || noop)(...args),
  refresh: (...args) => (bridge().renderGrid || noop)(...args),
  updateStatusBar: (...args) => (bridge().updateStatusBar || noop)(...args),
  saveAllChanges: (...args) => (bridge().saveAllChanges || noop)(...args),
  resetAllProgress: (...args) => (bridge().resetAllProgress || noop)(...args),
  switchTimeScaleMode: (...args) => (bridge().switchTimeScaleMode || noop)(...args),
  syncHeaderHeights: (...args) => (moduleStore.syncHeaderHeights || bridge().syncHeaderHeights || noop)(...args),
  syncRowHeights: (...args) => (moduleStore.syncRowHeights || bridge().syncRowHeights || noop)(...args),
  setupScrollSync: (...args) => (moduleStore.setupScrollSync || bridge().setupScrollSync || noop)(...args),
  renderTimeHeaders: (...args) => (moduleStore.renderTimeHeaders || bridge().renderTimeHeaders || noop)(...args),
  renderTables: (...args) => (moduleStore.renderTables || bridge().renderTables || noop)(...args),
  attachEvents: (...args) => (moduleStore.attachEvents || bridge().attachEvents || noop)(...args),
  enterEditMode: (...args) => (moduleStore.enterEditMode || bridge().enterEditMode || noop)(...args),
  exitEditMode: (...args) => (moduleStore.exitEditMode || bridge().exitEditMode || noop)(...args),
  navigateCell: (...args) => (moduleStore.navigateCell || bridge().navigateCell || noop)(...args),
  getState: () => (bridge().getState ? bridge().getState() : window[manifest.globals.state] || null),
  getAssignments: () => (bridge().getAssignments ? bridge().getAssignments() : null),
});
```

**Migration Strategy**: Remove bridge pattern, use direct imports

---

## 3. Key Features

### 3.1 Dual-Panel Grid System
- **Left Panel**: Tree structure with volume info
- **Right Panel**: Time columns with editable cells
- **Synchronization**: Heights, scroll, visibility

### 3.2 Tree Hierarchy
- Expandable/collapsible nodes
- 3 types: `kategori`, `sub_kategori`, `pekerjaan`
- Only `pekerjaan` nodes are editable
- Level-based indentation

### 3.3 Cell Editing
- In-place number input (0-100%)
- Validation on exit
- Modified state tracking
- Dual display modes (percentage/volume)

### 3.4 Keyboard Navigation
- Excel-like arrow key movement
- Tab navigation
- Enter to edit
- Escape to cancel

### 3.5 Progress Validation
- Row totals must equal 100%
- Visual indicators: OK, Under 100%, Over 100%
- Tolerance: ±0.5%

### 3.6 State Management
- `modifiedCells` Map: Pending changes
- `assignmentMap`: Saved values
- `volumeMap`: Volume per pekerjaan
- `expandedNodes` Set: Tree state

---

## 4. Dependencies

### 4.1 Global Dependencies
```javascript
// Lines 4-10
window.KelolaTahapanPageApp
window.JadwalPekerjaanApp
window.KelolaTahapanModuleManifest
window.kelolaTahapanPageState
window.showToast
```

### 4.2 State Structure
```javascript
state = {
  pekerjaanTree: Array<Node>,
  timeColumns: Array<Column>,
  volumeMap: Map<nodeId, volume>,
  assignmentMap: Map<cellKey, percentage>,
  modifiedCells: Map<cellKey, percentage>,
  expandedNodes: Set<nodeId>,
  volumeResetJobs: Set<nodeId>,
  displayMode: 'percentage' | 'volume',
  flatPekerjaan: Array<Node>,
  currentCell: HTMLElement,
  domRefs: Object,
  cache: Object
}
```

### 4.3 DOM Structure
```html
<!-- Left Panel -->
<table>
  <thead id="left-thead">
    <tr>
      <th>Tree</th>
      <th>Uraian</th>
      <th>Volume</th>
      <th>Satuan</th>
    </tr>
  </thead>
  <tbody id="left-tbody">
    <!-- renderLeftRow() output -->
  </tbody>
</table>

<!-- Right Panel -->
<table>
  <thead id="right-thead">
    <tr id="time-header-row">
      <!-- renderTimeHeaders() output -->
    </tr>
  </thead>
  <tbody id="right-tbody">
    <!-- renderRightRow() output -->
  </tbody>
</table>
```

---

## 5. Data Flow

### 5.1 Rendering Flow
```
renderTables()
├── resolveState()
├── prepareUtils()
├── state.pekerjaanTree.forEach()
│   ├── renderLeftRow()
│   │   ├── renderProgressChip()
│   │   │   └── calculateRowProgress()
│   │   │       └── getEffectiveCellValue()
│   │   └── (recursive for children)
│   └── renderRightRow()
│       ├── renderTimeCell()
│       │   ├── getAssignmentValue()
│       │   └── getEffectiveCellValue()
│       └── (recursive for children)
└── return { leftHTML, rightHTML }
```

### 5.2 Edit Flow
```
User Action (dblclick, Enter, digit)
└── enterEditMode()
    └── Create <input>, attach handlers
        └── User edits value
            └── (blur, Enter, Tab, Escape)
                └── exitEditMode()
                    ├── Validate (0-100)
                    ├── Update state.modifiedCells
                    ├── Update cell classes
                    ├── Update cell display
                    ├── ctx.helpers.updateStatusBar()
                    └── ctx.helpers.onProgressChange()
```

### 5.3 Tree Interaction Flow
```
User clicks tree-toggle
└── handleTreeToggle()
    ├── Update state.expandedNodes
    ├── Toggle .collapsed class
    ├── toggleNodeChildren()
    │   └── Add/remove .row-hidden on descendants
    └── setTimeout(() => syncRowHeights(), 10)
```

---

## 6. Cell State Machine

### States:
1. **Empty**: No saved value, no modified value
2. **Saved**: `savedValue > 0`, displayed with `.saved` class
3. **Modified (unsaved)**: `modifiedValue !== savedValue`, displayed with `.modified` class
4. **Modified (same as saved)**: `modifiedValue === savedValue`, only `.saved` class
5. **Editing**: Input element visible, `.editing` class

### Transitions:
```
Empty → Saved: Server provides savedValue > 0
Empty → Modified: User enters value > 0
Saved → Modified: User changes value
Modified → Saved: User saves to server
Editing → Modified: User commits change
Editing → (Previous): User presses Escape
```

---

## 7. Important Patterns & Conventions

### 7.1 String-Based Rendering
**Pattern**: Build HTML strings, then set `innerHTML`

**Rationale**: Faster than DOM manipulation for bulk operations

**Example**:
```javascript
state.pekerjaanTree.forEach((node) => {
  leftRows.push(`<tr>...</tr>`);
});
const leftHTML = leftRows.join('');
leftTbody.innerHTML = leftHTML;
```

**Tradeoff**: Loses event listeners (must re-attach)

---

### 7.2 Recursive Tree Rendering
**Pattern**: Depth-first traversal with visibility propagation

**Code**:
```javascript
function renderLeftRow(node, ctx, parentVisible = true) {
  const isExpanded = nodeIsExpanded(state, node.id);
  const isVisible = parentVisible;

  // Render current row
  leftRows.push(`<tr class="${isVisible ? '' : 'row-hidden'}">...</tr>`);

  // Recurse for children
  if (node.children && node.children.length > 0) {
    node.children.forEach((child) => {
      renderLeftRow(child, ctx, isExpanded && isVisible);
    });
  }
}
```

---

### 7.3 Context Object Pattern
**Pattern**: Pass dependencies as single object

**Benefits**:
- Consistent function signatures
- Easy to add new dependencies
- Testability

**Code**:
```javascript
const ctx = { state, utils, dom, helpers };
handleTreeToggle(event, ctx);
```

---

### 7.4 Data Attributes for State
**Pattern**: Store metadata in `data-*` attributes

**Example**:
```html
<td class="time-cell editable"
    data-node-id="123"
    data-col-id="col-1"
    data-value="45.5"
    data-saved-value="40.0">
  <span class="cell-value percentage">45.5</span>
</td>
```

**Usage**: Event handlers extract state from DOM

---

### 7.5 Temporary Cell Properties
**Pattern**: Use custom properties on DOM elements

**Example**:
```javascript
cell._isExiting = true;
cell._pendingNavigation = 'right';
cell._originalContent = '<span>45.5</span>';
```

**Purpose**: Coordinate asynchronous event handling

**Concern**: Memory leaks if not cleaned up

---

### 7.6 Double Rendering (Left + Right)
**Pattern**: Separate functions for each panel

**Rationale**: Different cell types (tree vs time)

**Synchronization**: Both use same `state.pekerjaanTree` iteration order

---

### 7.7 Map-Based State
**Pattern**: Use `Map` for key-value lookups

**Examples**:
- `state.modifiedCells`: `Map<cellKey, percentage>`
- `state.volumeMap`: `Map<nodeId, volume>`
- `state.assignmentMap`: `Map<cellKey, percentage>`

**Benefits**: Fast lookups, type safety

---

### 7.8 Set-Based Flags
**Pattern**: Use `Set` for boolean flags

**Examples**:
- `state.expandedNodes`: `Set<nodeId>`
- `state.volumeResetJobs`: `Set<nodeId>`

**Benefits**: Fast membership tests, no duplicates

---

## 8. Migration Opportunities

### 8.1 Convert IIFE to ES6 Class

**Current**:
```javascript
(function() {
  'use strict';
  // 856 lines
})();
```

**Target**:
```javascript
export class GridModule {
  constructor(state, utils, helpers) {
    this.state = state;
    this.utils = utils;
    this.helpers = helpers;
    this.dom = this.resolveDom();
  }

  renderTables() { /* ... */ }
  attachEvents() { /* ... */ }
  // etc.
}
```

**Benefits**:
- Clear encapsulation
- Testable methods
- No global pollution
- TypeScript support

---

### 8.2 Extract Utility Functions

**Current**: Inline utility functions

**Target**:
```javascript
// utils/formatters.js
export function formatNumber(num, decimals = 2) { /* ... */ }
export function escapeHtml(text) { /* ... */ }

// utils/grid-calculations.js
export function calculateRowProgress(nodeId, state) { /* ... */ }
export function getEffectiveCellValue(state, nodeId, columnId, fallback) { /* ... */ }
```

---

### 8.3 Template Literals for HTML

**Current**:
```javascript
leftRows.push(`
  <tr class="${rowClass}" data-node-id="${node.id}">
    <td class="col-tree">${toggleIcon}</td>
    <td class="col-uraian ${levelClass}">
      <div class="tree-node">
        ${utils.escapeHtml(node.nama)}
        ${needsVolumeReset ? '<span class="kt-volume-pill">Perlu update volume</span>' : ''}
        ${progressChip}
      </div>
    </td>
    <td class="col-volume text-right">${volume}</td>
    <td class="col-satuan">${satuan}</td>
  </tr>
`);
```

**Target**: Extract to template function or JSX-like syntax

---

### 8.4 Event Delegation

**Current**: Bind to each element
```javascript
document.querySelectorAll('.time-cell.editable').forEach((cell) => {
  cell.addEventListener('click', cellClickHandler);
  cell.addEventListener('dblclick', cellDoubleHandler);
  cell.addEventListener('keydown', cellKeyHandler);
});
```

**Target**: Single listener on container
```javascript
this.dom.rightTbody.addEventListener('click', (event) => {
  const cell = event.target.closest('.time-cell.editable');
  if (cell) this.handleCellClick(event, cell);
});
```

**Benefits**: Better performance, handles dynamically added cells

---

### 8.5 Virtual DOM / Reactive Rendering

**Current**: Full innerHTML replacement

**Target**: Incremental updates with diffing

**Libraries**:
- Lit-HTML
- Preact
- Custom virtual DOM

---

### 8.6 Async/Await for Save Operations

**Current**: Synchronous exit mode with callbacks

**Target**:
```javascript
async exitEditMode(cell, input) {
  const newValue = parseFloat(input.value);
  if (!this.validate(newValue)) {
    return false;
  }

  try {
    await this.helpers.onProgressChange({
      pekerjaanId: cell.dataset.nodeId,
      newValue,
      // ...
    });
    this.updateCellDisplay(cell, newValue);
  } catch (error) {
    this.helpers.showToast('Failed to save', 'danger');
  }
}
```

---

### 8.7 TypeScript Interfaces

**Target**:
```typescript
interface Node {
  id: string;
  nama: string;
  type: 'kategori' | 'sub_kategori' | 'pekerjaan';
  level: number;
  satuan?: string;
  children?: Node[];
}

interface TimeColumn {
  id: string;
  label: string;
  rangeLabel?: string;
  generationMode?: 'monthly' | 'weekly';
  tooltip?: string;
}

interface GridState {
  pekerjaanTree: Node[];
  timeColumns: TimeColumn[];
  volumeMap: Map<string, number>;
  assignmentMap: Map<string, number>;
  modifiedCells: Map<string, number>;
  expandedNodes: Set<string>;
  displayMode: 'percentage' | 'volume';
}
```

---

### 8.8 Separate Concerns

**Current**: Single 856-line file

**Target** (Module Structure):
```
grid/
├── GridModule.js (main class)
├── renderers/
│   ├── LeftPanelRenderer.js
│   ├── RightPanelRenderer.js
│   ├── HeaderRenderer.js
│   └── CellRenderer.js
├── handlers/
│   ├── TreeToggleHandler.js
│   ├── CellEditHandler.js
│   └── NavigationHandler.js
├── utils/
│   ├── calculations.js
│   ├── formatters.js
│   └── validators.js
└── types/
    └── index.d.ts
```

---

### 8.9 Performance Optimizations

#### Current Issues:
1. **Synchronous Layout Thrashing**: `syncRowHeights()` reads `offsetHeight` then writes `style.height` in loop
2. **Full Re-render**: innerHTML replacement destroys and recreates all DOM
3. **No Virtualization**: All rows rendered even if off-screen

#### Optimizations:

**Batch Layout Reads/Writes**:
```javascript
syncRowHeights() {
  const leftHeights = leftRows.map(row => row.offsetHeight);
  const rightHeights = rightRows.map(row => row.offsetHeight);

  leftRows.forEach((row, i) => {
    const maxHeight = Math.max(leftHeights[i], rightHeights[i]);
    row.style.height = `${maxHeight}px`;
    rightRows[i].style.height = `${maxHeight}px`;
  });
}
```

**Virtual Scrolling**:
```javascript
// Only render visible rows + buffer
const visibleRange = this.calculateVisibleRange();
const fragment = this.renderRows(visibleRange.start, visibleRange.end);
```

---

### 8.10 Testing Strategy

**Current**: No tests visible

**Target**:

**Unit Tests**:
- `calculateRowProgress()` with various inputs
- `getEffectiveCellValue()` with modified/saved values
- `formatNumber()` with edge cases

**Integration Tests**:
- Tree expand/collapse updates correct rows
- Cell edit updates state and display
- Navigation moves to correct cell

**E2E Tests**:
- User can expand category and edit pekerjaan
- Keyboard navigation works across all cells
- Save persists changes to server

---

## 9. Key Code Sections for Migration

### 9.1 State Management (Lines 25-49, 200-235)
```javascript
// State resolution
function resolveState(stateOverride) { /* ... */ }

// Value retrieval
function getAssignmentValue(state, key) { /* ... */ }
function getEffectiveCellValue(state, nodeId, columnId, fallbackSaved) { /* ... */ }

// DOM resolution
function resolveDom(state) { /* ... */ }
```

**Migration**: Convert to class properties and methods

---

### 9.2 Rendering Logic (Lines 81-320)
```javascript
// Main render
function renderTables(context) { /* ... */ }

// Panel-specific renders
function renderLeftRow(node, ctx, parentVisible) { /* ... */ }
function renderRightRow(node, ctx, parentVisible) { /* ... */ }

// Cell rendering
function renderTimeCell(node, column, ctx) { /* ... */ }

// Progress calculation
function calculateRowProgress(nodeId, state) { /* ... */ }
function renderProgressChip(nodeId, state) { /* ... */ }
```

**Migration**: Extract to renderer classes

---

### 9.3 Event Handling (Lines 348-493)
```javascript
// Event binding
function attachEvents(options) { /* ... */ }

// Handlers
function handleTreeToggle(event, ctx) { /* ... */ }
function handleCellClick(event, ctx) { /* ... */ }
function handleCellDoubleClick(event, ctx) { /* ... */ }
function handleCellKeydown(event, ctx) { /* ... */ }
```

**Migration**: Convert to class methods with event delegation

---

### 9.4 Cell Editing (Lines 495-677)
```javascript
// Edit mode
function enterEditMode(cell, ctx, initialValue) { /* ... */ }
function exitEditMode(cell, input, ctx) { /* ... */ }

// Navigation
function navigateCell(ctx, direction) { /* ... */ }
```

**Migration**: Extract to `CellEditor` class

---

### 9.5 UI Sync (Lines 679-757)
```javascript
// Synchronization
function syncHeaderHeights(stateOverride) { /* ... */ }
function syncRowHeights(stateOverride) { /* ... */ }
function setupScrollSync(stateOverride) { /* ... */ }
```

**Migration**: Extract to `PanelSynchronizer` class

---

## 10. Simplification Opportunities

### 10.1 Remove State Resolution Fallbacks
**Current**: Multiple fallback sources for state
**Target**: Single source via dependency injection

### 10.2 Consolidate DOM Refs
**Current**: Separate resolution function
**Target**: Initialize once in constructor

### 10.3 Extract Tree Logic
**Current**: Mixed with rendering
**Target**: Separate `TreeModel` class

### 10.4 Simplify Cell Key Generation
**Current**: String concatenation `${nodeId}-${columnId}`
**Target**: Helper method or symbol

### 10.5 Remove Bridge Pattern
**Current**: Lines 820-855 delegate to facade
**Target**: Direct method calls

---

## 11. Global Dependencies to Eliminate

### Remove These Globals:
```javascript
window.KelolaTahapanPageApp
window.JadwalPekerjaanApp
window.KelolaTahapanModuleManifest
window.KelolaTahapanPageModules
window.kelolaTahapanPageState
window.showToast
```

### Replace With:
```javascript
// ES6 imports
import { GridModule } from './grid/GridModule.js';
import { showToast } from './utils/notifications.js';

// Dependency injection
const gridModule = new GridModule({
  state: appState,
  utils: { formatNumber, escapeHtml },
  helpers: { showToast, updateStatusBar, onProgressChange }
});
```

---

## 12. Performance Metrics (Estimated)

### Current Performance:
- **Full Render**: ~200ms for 500 rows (innerHTML replacement)
- **Height Sync**: ~50ms (layout thrashing)
- **Event Attach**: ~30ms (500+ listeners)

### Target Performance:
- **Full Render**: ~100ms (incremental DOM updates)
- **Height Sync**: ~20ms (batched layout)
- **Event Attach**: ~5ms (event delegation)

---

## 13. Recommendations for Migration

### Phase 1: Extract & Encapsulate
1. Create ES6 class structure
2. Extract utilities to separate modules
3. Remove global dependencies
4. Add TypeScript interfaces

### Phase 2: Optimize Rendering
1. Implement event delegation
2. Add virtual scrolling
3. Optimize height synchronization
4. Add incremental updates

### Phase 3: Improve Testing
1. Add unit tests for calculations
2. Add integration tests for interactions
3. Add E2E tests for user workflows

### Phase 4: Modernize Patterns
1. Use async/await for callbacks
2. Consider reactive state management
3. Add error boundaries
4. Implement accessibility features

---

## 14. Risk Assessment

### High Risk Areas:
1. **Cell Editing**: Complex state machine with edge cases
2. **Tree Synchronization**: Fragile index-based correlation
3. **Height Sync**: Performance-sensitive layout code
4. **Navigation**: Lots of edge cases (hidden rows, boundaries)

### Mitigation Strategies:
1. Comprehensive test coverage before refactoring
2. Feature flags for gradual rollout
3. Parallel implementation with fallback
4. User acceptance testing

---

## 15. Summary

This grid module is a **sophisticated dual-panel spreadsheet-like interface** with:
- **856 lines** of tightly coupled legacy code
- **Rich interaction model** (keyboard nav, inline editing, tree expansion)
- **Complex state management** (3 maps, 2 sets, multiple flags)
- **Performance-critical rendering** (hundreds of rows)

**Main Challenges**:
- Global namespace pollution
- IIFE pattern prevents modularity
- String-based rendering loses event context
- Layout thrashing in height sync
- No separation of concerns

**Migration Priority**:
1. Extract to ES6 class ⭐⭐⭐⭐⭐
2. Implement event delegation ⭐⭐⭐⭐⭐
3. Optimize height sync ⭐⭐⭐⭐
4. Add virtual scrolling ⭐⭐⭐
5. TypeScript migration ⭐⭐⭐

**Estimated Effort**: 3-4 weeks for complete modernization with testing

---

**Document Version**: 1.0
**Created**: 2025-11-19
**Purpose**: Reference for ES6 migration of grid_module.js
