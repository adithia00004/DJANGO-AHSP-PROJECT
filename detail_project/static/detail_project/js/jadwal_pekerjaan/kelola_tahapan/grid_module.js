(function() {
  'use strict';

  const bootstrap = window.KelolaTahapanPageApp || window.JadwalPekerjaanApp;
  const manifest = window.KelolaTahapanModuleManifest;
  if (!bootstrap || !manifest || !manifest.modules || !manifest.modules.grid) {
    return;
  }

  const meta = manifest.modules.grid;
  const noop = () => undefined;
  const hasModule = typeof bootstrap.hasModule === 'function'
    ? (id) => bootstrap.hasModule(id)
    : (id) => bootstrap.modules && bootstrap.modules.has
      ? bootstrap.modules.has(id)
      : false;

  if (hasModule(meta.id)) {
    return;
  }

  const globalModules = window.KelolaTahapanPageModules = window.KelolaTahapanPageModules || {};
  const moduleStore = globalModules.grid = Object.assign({}, globalModules.grid || {});

  function resolveState(stateOverride) {
    if (stateOverride) {
      return stateOverride;
    }
    if (window.kelolaTahapanPageState) {
      return window.kelolaTahapanPageState;
    }
    if (bootstrap && bootstrap.state) {
      return bootstrap.state;
    }
    return null;
  }

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

  function prepareUtils(contextUtils) {
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

    const utils = Object.assign(
      {
        escapeHtml: defaultEscapeHtml,
        formatNumber: defaultFormatNumber,
      },
      moduleStore.utils || {},
      contextUtils || {},
    );

    moduleStore.utils = utils;
    return utils;
  }

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

    return {
      leftHTML,
      rightHTML,
    };
  }

  function nodeIsExpanded(state, nodeId) {
    if (!state || !state.expandedNodes) return true;
    return state.expandedNodes.has(nodeId) !== false;
  }

  function renderLeftRow(node, ctx, parentVisible = true) {
    const { state, utils, leftRows } = ctx;
    const isExpanded = nodeIsExpanded(state, node.id);
    const isVisible = parentVisible;
    const needsVolumeReset = (
      node.type === 'pekerjaan' &&
      state.volumeResetJobs instanceof Set &&
      state.volumeResetJobs.has(node.id)
    );
    const rowClasses = [`row-${node.type}`];
    if (!isVisible) rowClasses.push('row-hidden');
    if (needsVolumeReset) rowClasses.push('volume-warning');
    const rowClass = rowClasses.join(' ').trim();
    const levelClass = `level-${node.level}`;

    let toggleIcon = '';
    if (node.children && node.children.length > 0) {
      toggleIcon = `<span class="tree-toggle ${isExpanded ? '' : 'collapsed'}" data-node-id="${node.id}">
        <i class="bi bi-caret-down-fill"></i>
      </span>`;
    }

    const volumeValue = (state.volumeMap && state.volumeMap.has(node.id))
      ? state.volumeMap.get(node.id)
      : 0;
    const volume = node.type === 'pekerjaan'
      ? utils.formatNumber(volumeValue)
      : '';
    const satuan = node.type === 'pekerjaan' ? utils.escapeHtml(node.satuan) : '';

    const progressChip = node.type === 'pekerjaan'
      ? renderProgressChip(node.id, state)
      : '';

    leftRows.push(`
      <tr class="${rowClass}" data-node-id="${node.id}" data-row-index="${leftRows.length}">
        <td class="col-tree">
          ${toggleIcon}
        </td>
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

    if (node.children && node.children.length > 0) {
      node.children.forEach((child) => {
        renderLeftRow(child, ctx, isExpanded && isVisible);
      });
    }
  }

  function renderRightRow(node, ctx, parentVisible = true) {
    const { state, rightRows } = ctx;
    const isExpanded = nodeIsExpanded(state, node.id);
    const isVisible = parentVisible;
    const needsVolumeReset = (
      node.type === 'pekerjaan' &&
      state.volumeResetJobs instanceof Set &&
      state.volumeResetJobs.has(node.id)
    );
    const rowClass = `row-${node.type} ${isVisible ? '' : 'row-hidden'}${needsVolumeReset ? ' volume-warning' : ''}`.trim();

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

  function getAssignmentValue(state, key) {
    if (!state || !state.assignmentMap) return 0;
    if (state.assignmentMap instanceof Map) {
      return state.assignmentMap.get(key) || 0;
    }
    if (typeof state.assignmentMap.get === 'function') {
      return state.assignmentMap.get(key) || 0;
    }
    if (Object.prototype.hasOwnProperty.call(state.assignmentMap, key)) {
      return state.assignmentMap[key];
    }
    return 0;
  }

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
    } else if (state.modifiedCells && typeof state.modifiedCells.get === 'function') {
      const candidate = parseFloat(state.modifiedCells.get(cellKey));
      if (Number.isFinite(candidate)) {
        modifiedValue = candidate;
      }
    }

    const value = modifiedValue !== undefined ? modifiedValue : savedNumeric;
    return { value, modifiedValue };
  }

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

    if (!Number.isFinite(total)) {
      return null;
    }
    return parseFloat(total.toFixed(1));
  }

  function renderProgressChip(nodeId, state) {
    const total = calculateRowProgress(nodeId, state);
    if (total === null) {
      return '';
    }

    const tolerance = 0.5;
    let badgeClass = 'progress-chip--ok';
    let label = 'On Track';
    if (total > 100 + tolerance) {
      badgeClass = 'progress-chip--over';
      label = 'Over 100%';
    } else if (total < 100 - tolerance) {
      badgeClass = 'progress-chip--under';
      label = 'Under 100%';
    }

    return `
      <span class="progress-chip ${badgeClass}" title="${label}">
        ${total.toFixed(1)}%
      </span>
    `;
  }

  function renderTimeCell(node, column, ctx) {
    const { state, utils } = ctx;
    if (node.type !== 'pekerjaan') {
      return `<td class="time-cell readonly" data-node-id="${node.id}" data-col-id="${column.id}"></td>`;
    }

    const cellKey = `${node.id}-${column.id}`;
    const savedValue = getAssignmentValue(state, cellKey);
    const { value: currentValue, modifiedValue } = getEffectiveCellValue(state, node.id, column.id, savedValue);

    let cellClasses = 'time-cell editable';

    if (savedValue > 0) {
      cellClasses += ' saved';
    }

    if (modifiedValue !== undefined && modifiedValue !== savedValue) {
      cellClasses += ' modified';
    }

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

      if (!foundParent) {
        return;
      }

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

  function handleCellClick(event, ctx) {
    const cell = event.currentTarget;
    if (!cell) return;
    document.querySelectorAll('.time-cell.selected').forEach((c) => c.classList.remove('selected'));
    cell.classList.add('selected');
    ctx.state.currentCell = cell;
  }

  function handleCellDoubleClick(event, ctx) {
    const cell = event.currentTarget;
    if (!cell) return;
    enterEditMode(cell, ctx);
  }

  function handleCellKeydown(event, ctx) {
    const cell = event.currentTarget;
    if (!cell || cell.classList.contains('editing')) {
      return;
    }

    switch (event.key) {
      case 'Enter':
        enterEditMode(cell, ctx);
        event.preventDefault();
        break;
      case 'Tab': {
        const direction = event.shiftKey ? 'left' : 'right';
        console.log('[Grid] Tab pressed, direction:', direction, 'current cell:', cell.dataset.colId);

        // CRITICAL: Prevent default BEFORE navigation
        // This stops browser from jumping to next focusable element
        event.preventDefault();
        event.stopPropagation();

        navigateCell(ctx, direction);
        break;
      }
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

  function exitEditMode(cell, input, ctx) {
    const parsedInput = parseFloat(input.value);
    const newValue = Number.isFinite(parsedInput) ? parsedInput : 0;

    const savedValueRaw = parseFloat(cell.dataset.savedValue);
    const savedValue = Number.isFinite(savedValueRaw) ? savedValueRaw : 0;

    const cellKey = `${cell.dataset.nodeId}-${cell.dataset.colId}`;

    cell.classList.remove('editing');

    if (newValue < 0 || newValue > 100) {
      ctx.helpers.showToast('Value must be between 0-100', 'danger');
      cell.innerHTML = cell._originalContent;
      cell._isExiting = false;
      cell._pendingNavigation = null;
      cell.focus();
      return false;
    }

    const currentValueRaw = parseFloat(cell.dataset.value);
    const currentValue = Number.isFinite(currentValueRaw) ? currentValueRaw : savedValue;
    const modifiedValueRaw = ctx.state.modifiedCells.has(cellKey)
      ? parseFloat(ctx.state.modifiedCells.get(cellKey))
      : null;
    const previousValue = Number.isFinite(modifiedValueRaw) ? modifiedValueRaw : currentValue;

    const hasChanged = Math.abs(newValue - previousValue) > 0.0001;

    if (hasChanged) {
      if (newValue === 0 && savedValue === 0) {
        ctx.state.modifiedCells.delete(cellKey);
      } else {
        ctx.state.modifiedCells.set(cellKey, newValue);
      }

      cell.classList.remove('saved', 'modified');

      if (savedValue > 0) {
        cell.classList.add('saved');
      }

      if (newValue !== savedValue) {
        cell.classList.add('modified');
      }

      cell.dataset.value = newValue;

      let displayValue = '';
      if (newValue > 0 || (newValue === 0 && savedValue !== 0)) {
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
      }
      cell.innerHTML = displayValue;

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
    } else {
      cell.innerHTML = cell._originalContent;
    }

    const pendingNavigation = cell._pendingNavigation;
    cell._isExiting = false;
    if (!pendingNavigation) {
      cell.focus();
    }
    cell._pendingNavigation = null;
    return true;
  }

  function navigateCell(ctx, direction) {
    console.log('[Grid] navigateCell called, direction:', direction);

    if (!ctx.state.currentCell) {
      console.warn('[Grid] No current cell');
      return;
    }

    const currentRow = ctx.state.currentCell.closest('tr');
    if (!currentRow) {
      console.warn('[Grid] No current row');
      return;
    }

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
      case 'right':
        console.log('[Grid] Horizontal navigation detected');
        // For horizontal navigation, always check if we need to scroll first
        nextCell = findNextHorizontalCell(ctx, direction, currentRow, currentIndex);
        console.log('[Grid] findNextHorizontalCell returned:', nextCell);
        break;
      default:
        break;
    }

    // Handle different return values
    if (nextCell === 'scrolling') {
      // Scroll is happening asynchronously - do nothing here
      // scrollToRevealNextCell will handle the focus
      console.log('[Grid] Scrolling in progress - async focus will happen');
      return;
    }

    if (nextCell && typeof nextCell === 'object' && nextCell.classList && nextCell.classList.contains('time-cell')) {
      console.log('[Grid] Moving to next cell:', nextCell.dataset.colId);
      ctx.state.currentCell = nextCell;
      nextCell.focus();
      nextCell.click();
    } else {
      console.log('[Grid] No next cell found');
    }
  }

  /**
   * Find next cell in horizontal direction, scrolling if necessary
   * This prevents Tab from jumping to first column when reaching viewport edge
   *
   * STRATEGY:
   * 1. Check if next cell exists in DOM (already rendered)
   * 2. If yes -> return it immediately
   * 3. If no -> check if column exists in state.timeColumns
   * 4. If column exists -> trigger scroll and async focus
   * 5. If no more columns -> stay at current position
   */
  function findNextHorizontalCell(ctx, direction, currentRow, currentIndex) {
    const currentCell = ctx.state.currentCell;
    const currentColId = currentCell.dataset.colId;

    console.log('[Grid] findNextHorizontalCell - current col:', currentColId, 'direction:', direction);

    // Find current column index in state.timeColumns (the source of truth)
    if (!ctx.state.timeColumns || !Array.isArray(ctx.state.timeColumns)) {
      console.warn('[Grid] No timeColumns in state');
      return null;
    }

    console.log('[Grid] Total columns:', ctx.state.timeColumns.length);

    const currentColIndex = ctx.state.timeColumns.findIndex(col => String(col.id) === String(currentColId));
    console.log('[Grid] Current col index:', currentColIndex);

    if (currentColIndex === -1) {
      // Current column not found in state - fallback to DOM navigation
      console.warn('[Grid] Current column not found in timeColumns, using DOM fallback');
      return direction === 'right'
        ? currentCell.nextElementSibling
        : currentCell.previousElementSibling;
    }

    // Calculate target column index
    const targetColIndex = direction === 'right' ? currentColIndex + 1 : currentColIndex - 1;
    console.log('[Grid] Target col index:', targetColIndex);

    // Check if target column exists in state
    if (targetColIndex < 0 || targetColIndex >= ctx.state.timeColumns.length) {
      // We're at the actual edge - no more columns exist
      console.log('[Grid] At edge - no more columns');
      return null;
    }

    const targetColId = ctx.state.timeColumns[targetColIndex].id;
    console.log('[Grid] Target col ID:', targetColId);

    // CRITICAL: Check if current cell is at viewport edge
    // If yes, we MUST scroll first before checking DOM
    const isAtViewportEdge = isCellAtViewportEdge(ctx, currentCell, direction);
    console.log('[Grid] Is at viewport edge?', isAtViewportEdge);

    if (isAtViewportEdge) {
      // At viewport edge - MUST scroll first
      console.log('[Grid] At viewport edge - forcing scroll');
      scrollToRevealNextCell(ctx, direction, currentRow, currentIndex, targetColId);
      // Return special marker to prevent default Tab behavior
      return 'scrolling';
    }

    // Not at edge - try to find the target cell in DOM
    const targetCell = currentRow.querySelector(`[data-col-id="${targetColId}"]`);

    if (targetCell && targetCell.classList.contains('time-cell')) {
      // Cell already rendered - return it
      console.log('[Grid] Target cell found in DOM');
      return targetCell;
    }

    // Cell not rendered yet but not at edge - still scroll
    console.log('[Grid] Target cell NOT in DOM - triggering scroll');
    scrollToRevealNextCell(ctx, direction, currentRow, currentIndex, targetColId);

    // Return special marker to prevent default Tab behavior
    return 'scrolling';
  }

  /**
   * Check if current cell is at the edge of viewport
   * This determines if we need to scroll before Tab navigation
   */
  function isCellAtViewportEdge(ctx, cell, direction) {
    const dom = resolveDom(ctx.state);
    const scrollContainer = dom.rightPanelScroll;

    if (!scrollContainer) {
      return false;
    }

    const cellRect = cell.getBoundingClientRect();
    const containerRect = scrollContainer.getBoundingClientRect();

    if (direction === 'right') {
      // Check if cell is near right edge of viewport
      // Consider edge if cell's right is within 2x cell width of container's right
      const distanceToEdge = containerRect.right - cellRect.right;
      const threshold = cellRect.width * 2;
      console.log('[Grid] Distance to right edge:', distanceToEdge, 'threshold:', threshold);
      return distanceToEdge < threshold;
    } else if (direction === 'left') {
      // Check if cell is near left edge of viewport
      const distanceToEdge = cellRect.left - containerRect.left;
      const threshold = cellRect.width * 2;
      console.log('[Grid] Distance to left edge:', distanceToEdge, 'threshold:', threshold);
      return distanceToEdge < threshold;
    }

    return false;
  }

  /**
   * Scroll viewport to reveal next cell, then focus it
   * Handles virtual scrolling where cells are not rendered until visible
   *
   * IMPORTANT: This function prevents Tab from jumping to column 1
   * by ensuring horizontal scroll happens before focus moves
   *
   * @param {Object} ctx - Context object with state and DOM refs
   * @param {string} direction - 'left' or 'right'
   * @param {HTMLElement} currentRow - Current row element
   * @param {number} currentIndex - Current cell index in row (unused but kept for compatibility)
   * @param {string|number} targetColId - Target column ID to focus after scroll
   */
  function scrollToRevealNextCell(ctx, direction, currentRow, currentIndex, targetColId) {
    console.log('[Grid] scrollToRevealNextCell - target col:', targetColId, 'direction:', direction);

    const dom = resolveDom(ctx.state);
    const scrollContainer = dom.rightPanelScroll;

    if (!scrollContainer) {
      console.warn('[Grid] No scroll container found');
      return;
    }

    const currentCell = ctx.state.currentCell;
    const cellRect = currentCell.getBoundingClientRect();
    const scrollLeft = scrollContainer.scrollLeft;

    console.log('[Grid] Current scroll:', scrollLeft, 'Cell width:', cellRect.width);

    // Calculate how much to scroll
    // We want to reveal the next cell by scrolling exactly one cell width
    let scrollAmount = 0;

    if (direction === 'right') {
      // Scroll right: move by current cell width to reveal next column
      scrollAmount = cellRect.width;
    } else if (direction === 'left') {
      // Scroll left: move by current cell width to reveal previous column
      scrollAmount = -cellRect.width;
    }

    const targetScrollLeft = Math.max(0, scrollLeft + scrollAmount);
    console.log('[Grid] Target scroll:', targetScrollLeft);

    // Perform scroll
    scrollContainer.scrollLeft = targetScrollLeft;
    console.log('[Grid] Scroll set to:', scrollContainer.scrollLeft);

    // Use double RAF to ensure DOM has updated after scroll
    // First RAF: browser schedules repaint
    requestAnimationFrame(() => {
      console.log('[Grid] First RAF');
      // Second RAF: repaint has completed, cells should be rendered
      requestAnimationFrame(() => {
        console.log('[Grid] Second RAF - looking for target cell');
        // Try to find the target cell by column ID (most reliable)
        let nextCell = null;

        if (targetColId) {
          nextCell = currentRow.querySelector(`[data-col-id="${targetColId}"]`);
          console.log('[Grid] Query by targetColId result:', nextCell);
        }

        // Fallback: try sibling navigation
        if (!nextCell) {
          console.log('[Grid] Trying sibling fallback');
          if (direction === 'right') {
            nextCell = currentCell.nextElementSibling;
          } else if (direction === 'left') {
            nextCell = currentCell.previousElementSibling;
          }
          console.log('[Grid] Sibling navigation result:', nextCell);
        }

        if (nextCell && nextCell.classList.contains('time-cell')) {
          // Success! Cell is now rendered after scroll
          console.log('[Grid] SUCCESS - focusing on:', nextCell.dataset.colId);
          ctx.state.currentCell = nextCell;
          nextCell.focus();
          nextCell.click();
        } else {
          console.error('[Grid] FAILED - no cell found after scroll');
        }
      });
    });
  }

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

    if (!leftPanel || !rightPanel) {
      return;
    }

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

  function renderTimeHeaders(options = {}) {
    const ctx = createContext(options);
    if (!ctx) return 'legacy';

    const { state, utils, dom } = ctx;
    const headerRow = dom.timeHeaderRow
      || (dom.rightThead ? dom.rightThead.querySelector('#time-header-row') : null)
      || document.getElementById('time-header-row');

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
      let safeLine1 = utils.escapeHtml ? utils.escapeHtml(line1) : line1;
      const safeLine2 = utils.escapeHtml ? utils.escapeHtml(line2) : line2;

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

  Object.assign(moduleStore, {
    resolveState,
    syncHeaderHeights,
    syncRowHeights,
    setupScrollSync,
    renderTimeHeaders,
    renderTables,
    attachEvents,
    enterEditMode,
    exitEditMode,
    navigateCell,
  });

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
})();
