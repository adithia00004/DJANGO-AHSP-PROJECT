/**
 * GridRenderer - Modern ES6 Grid Rendering Engine
 * Handles dual-panel grid rendering (left tree structure + right time cells)
 *
 * Migrated from: jadwal_pekerjaan/kelola_tahapan/grid_module.js
 * Date: 2025-11-19
 *
 * ARCHITECTURE:
 * - ES6 class with clean method organization
 * - No global dependencies
 * - Returns HTML strings (DOM insertion handled externally)
 * - Event delegation ready (no individual listeners)
 * - Comprehensive logging with [GridRenderer] prefix
 *
 * RESPONSIBILITIES:
 * - Render left panel (tree structure with volume info)
 * - Render right panel (time cells with progress)
 * - Render time column headers
 * - Render progress chips and validation indicators
 * - Calculate row progress totals
 * - Provide tree expand/collapse logic
 * - Sync row heights between panels
 *
 * DOES NOT HANDLE (Phase 2C):
 * - Event listeners (grid-event-handlers.js)
 * - Cell editing (grid-cell-editor.js)
 * - Save operations (grid-save-handler.js)
 */

// =========================================================================
// UTILITY FUNCTIONS
// =========================================================================

/**
 * Escape HTML special characters to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped HTML
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

/**
 * Format number with Indonesian locale
 * @param {number} num - Number to format
 * @param {number} decimals - Decimal places
 * @returns {string} Formatted number
 */
function formatNumber(num, decimals = 2) {
  if (num === null || num === undefined || num === '') return '-';
  const n = parseFloat(num);
  if (Number.isNaN(n)) return '-';
  return n.toLocaleString('id-ID', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

// =========================================================================
// GRID RENDERER CLASS
// =========================================================================

/**
 * GridRenderer - Main rendering engine for dual-panel grid
 *
 * @example
 * const renderer = new GridRenderer(state, {
 *   escapeHtml: customEscape,
 *   formatNumber: customFormat
 * });
 *
 * const { leftHTML, rightHTML } = renderer.renderTables();
 */
export class GridRenderer {
  /**
   * Create a new GridRenderer instance
   * @param {Object} state - Application state
   * @param {Array} state.pekerjaanTree - Hierarchical tree of pekerjaan
   * @param {Array} state.timeColumns - Time column definitions
   * @param {Map} state.volumeMap - Volume per pekerjaan (nodeId -> volume)
   * @param {Map} state.assignmentMap - Saved progress values (cellKey -> percentage)
   * @param {Map} state.modifiedCells - Modified but unsaved values (cellKey -> percentage)
   * @param {Set} state.expandedNodes - IDs of expanded tree nodes
   * @param {Set} state.volumeResetJobs - IDs of pekerjaan needing volume update
   * @param {string} state.displayMode - Display mode ('percentage' | 'volume')
   * @param {Array} state.flatPekerjaan - Flattened pekerjaan list
   * @param {Object} options - Configuration options
   * @param {Function} options.escapeHtml - Custom HTML escape function
   * @param {Function} options.formatNumber - Custom number formatter
   */
  constructor(state, options = {}) {
    if (!state) {
      throw new Error('[GridRenderer] State is required');
    }

    this.state = state;
    this.options = options;

    // Utilities with fallback defaults
    this.escapeHtml = options.escapeHtml || escapeHtml;
    this.formatNumber = options.formatNumber || formatNumber;

    console.log('[GridRenderer] Initialized');
  }

  // =======================================================================
  // MAIN RENDERING
  // =======================================================================

  /**
   * Render both left and right tables
   * Main entry point for grid rendering.
   *
   * @returns {Object|null} { leftHTML: string, rightHTML: string } or null if invalid state
   */
  renderTables() {
    if (!this.state || !Array.isArray(this.state.pekerjaanTree)) {
      console.warn('[GridRenderer] Invalid state or missing pekerjaanTree');
      return null;
    }

    console.log(`[GridRenderer] Rendering tables for ${this.state.pekerjaanTree.length} root nodes`);

    const leftRows = [];
    const rightRows = [];

    // Recursively render each root node
    this.state.pekerjaanTree.forEach((node) => {
      this._renderLeftRow(node, leftRows, true, null);
      this._renderRightRow(node, rightRows, true, null);
    });

    const leftHTML = leftRows.join('');
    const rightHTML = rightRows.join('');

    console.log(`[GridRenderer] ✅ Rendered ${leftRows.length} rows`);

    return { leftHTML, rightHTML };
  }

  // =======================================================================
  // LEFT PANEL RENDERING (Tree Structure)
  // =======================================================================

  /**
   * Render a single row in the left panel (tree structure)
   * Recursively renders children if node is expanded.
   *
   * @param {Object} node - Tree node
   * @param {Array} leftRows - Accumulator for HTML rows
   * @param {boolean} parentVisible - Whether parent is visible
   * @private
   */
  _renderLeftRow(node, leftRows, parentVisible = true, parentId = null) {
    const isExpanded = this._isNodeExpanded(node.id);
    const isVisible = parentVisible;
    const needsVolumeReset = (
      node.type === 'pekerjaan' &&
      this.state.volumeResetJobs instanceof Set &&
      this.state.volumeResetJobs.has(node.id)
    );

    // Build row classes
    const rowClasses = [`row-${node.type}`];
    if (!isVisible) rowClasses.push('row-hidden');
    if (needsVolumeReset) rowClasses.push('volume-warning');
    const rowClass = rowClasses.join(' ').trim();

    // Build level class for indentation
    const levelClass = `level-${node.level}`;

    // Tree toggle icon (only for parent nodes)
    let toggleIcon = '';
    if (node.children && node.children.length > 0) {
      const toggleClass = isExpanded ? '' : 'collapsed';
      toggleIcon = `<span class="tree-toggle ${toggleClass}" data-node-id="${node.id}">
        <i class="bi bi-caret-down-fill"></i>
      </span>`;
    }

    // Volume display (only for pekerjaan nodes)
    const volumeValue = (this.state.volumeMap && this.state.volumeMap.has(node.id))
      ? this.state.volumeMap.get(node.id)
      : 0;
    const volume = node.type === 'pekerjaan'
      ? this.formatNumber(volumeValue)
      : '';

    // Satuan display
    const satuan = node.type === 'pekerjaan'
      ? this.escapeHtml(node.satuan)
      : '';

    // Progress chip (only for pekerjaan nodes)
    const progressChip = node.type === 'pekerjaan'
      ? this._renderProgressChip(node.id)
      : '';

    // Render row
    leftRows.push(`
      <tr class="${rowClass}" data-node-id="${node.id}" data-parent-id="${parentId ?? ''}" data-row-index="${leftRows.length}">
        <td class="col-uraian ${levelClass}">
          <div class="tree-node">
            <div class="tree-node-body">
              ${needsVolumeReset ? '<div class="tree-node-meta"><span class="kt-volume-pill">Perlu update volume</span></div>' : ''}
              <div class="tree-node-title">
                <span class="tree-node-label">${this.escapeHtml(node.nama)}</span>
                ${progressChip}
              </div>
            </div>
          </div>
        </td>
        <td class="col-volume text-right">${volume}</td>
        <td class="col-satuan">${satuan}</td>
      </tr>
    `);

    // Recursively render children
    if (node.children && node.children.length > 0) {
      node.children.forEach((child) => {
        this._renderLeftRow(child, leftRows, isExpanded && isVisible, node.id);
      });
    }
  }

  // =======================================================================
  // RIGHT PANEL RENDERING (Time Cells)
  // =======================================================================

  /**
   * Render a single row in the right panel (time columns)
   * Recursively renders children if node is expanded.
   *
   * @param {Object} node - Tree node
   * @param {Array} rightRows - Accumulator for HTML rows
   * @param {boolean} parentVisible - Whether parent is visible
   * @private
   */
  _renderRightRow(node, rightRows, parentVisible = true, parentId = null) {
    const isExpanded = this._isNodeExpanded(node.id);
    const isVisible = parentVisible;
    const needsVolumeReset = (
      node.type === 'pekerjaan' &&
      this.state.volumeResetJobs instanceof Set &&
      this.state.volumeResetJobs.has(node.id)
    );

    // Build row classes
    const rowClasses = [`row-${node.type}`];
    if (!isVisible) rowClasses.push('row-hidden');
    if (needsVolumeReset) rowClasses.push('volume-warning');
    const rowClass = rowClasses.join(' ').trim();

    // Render time cells for each column
    const timeCells = (this.state.timeColumns || [])
      .map((col) => this._renderTimeCell(node, col))
      .join('');

    // Render row
    rightRows.push(`
      <tr class="${rowClass}" data-node-id="${node.id}" data-parent-id="${parentId ?? ''}" data-row-index="${rightRows.length}">
        ${timeCells}
      </tr>
    `);

    // Recursively render children
    if (node.children && node.children.length > 0) {
      node.children.forEach((child) => {
        this._renderRightRow(child, rightRows, isExpanded && isVisible, node.id);
      });
    }
  }

  /**
   * Render a single time cell
   * Shows percentage or volume based on display mode.
   * Only pekerjaan nodes are editable.
   *
   * @param {Object} node - Tree node
   * @param {Object} column - Time column definition
   * @returns {string} HTML for cell
   * @private
   */
  _renderTimeCell(node, column) {
    // Non-pekerjaan nodes get readonly cells
    if (node.type !== 'pekerjaan') {
      return `<td class="time-cell readonly" data-node-id="${node.id}" data-col-id="${column.id}"></td>`;
    }

    const cellKey = `${node.id}-${column.id}`;
    const savedValue = this._getAssignmentValue(cellKey);
    const { value: currentValue, modifiedValue } = this.getEffectiveCellValue(node.id, column.id, savedValue);

    // Build cell classes
    let cellClasses = 'time-cell editable';
    if (savedValue > 0) {
      cellClasses += ' saved';
    }
    if (modifiedValue !== undefined && modifiedValue !== savedValue) {
      cellClasses += ' modified';
    }

    // Build display value
    let displayValue = '';
    if (currentValue > 0 || (currentValue === 0 && savedValue > 0)) {
      if (this.state.displayMode === 'volume') {
        // Volume mode: show calculated volume
        const volume = this.state.volumeMap && this.state.volumeMap.has(node.id)
          ? this.state.volumeMap.get(node.id)
          : 0;
        const volValue = (volume * currentValue / 100).toFixed(2);
        displayValue = `<span class="cell-value volume">${volValue}</span>`;
      } else {
        // Percentage mode: show percentage
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

  /**
   * Render badge that indicates node type (Klasifikasi/Sub-Klasifikasi/Pekerjaan)
   * @param {Object} node - Tree node
   * @returns {string} HTML badge
   * @private
   */
  /**
   * Render time column headers
   * Creates <th> elements with proper formatting and tooltips.
   * Uses DocumentFragment for performance.
   *
   * @param {HTMLElement} headerRow - Header row element to populate
   * @returns {HTMLElement|string} Populated header row or 'legacy' if invalid
   */
  renderTimeHeader(headerRow) {
    if (!headerRow || !Array.isArray(this.state.timeColumns)) {
      console.warn('[GridRenderer] Invalid header row or time columns');
      return 'legacy';
    }

    console.log(`[GridRenderer] Rendering ${this.state.timeColumns.length} time headers`);

    headerRow.innerHTML = '';
    const fragment = document.createDocumentFragment();

    this.state.timeColumns.forEach((col) => {
      const th = document.createElement('th');
      th.dataset.colId = col.id;

      const line1 = col.label || '';
      const line2 = col.rangeLabel || col.subLabel || '';
      const columnMode = (col.generationMode || col.type || '').toLowerCase();
      const isMonthly = columnMode === 'monthly';

      // Escape and format labels
      let safeLine1 = this.escapeHtml(line1);
      const safeLine2 = this.escapeHtml(line2);

      // Monthly mode: remove colon suffix
      if (isMonthly && typeof safeLine1 === 'string') {
        const colonIndex = safeLine1.indexOf(':');
        if (colonIndex !== -1) {
          safeLine1 = safeLine1.slice(0, colonIndex).trim();
        }
      }

      // Build header content
      const headerParts = [`<span class="time-header__label">${safeLine1}</span>`];
      if (line2 && !isMonthly) {
        headerParts.push(`<span class="time-header__range">${safeLine2}</span>`);
      }
      th.innerHTML = `<div class="time-header">${headerParts.join('')}</div>`;

      // Set tooltip
      th.title = col.tooltip || (line2 ? `${line1} ${line2}`.trim() : line1);

      fragment.appendChild(th);
    });

    headerRow.appendChild(fragment);
    console.log('[GridRenderer] ✅ Time headers rendered');

    return headerRow;
  }

  // =======================================================================
  // PROGRESS CALCULATION & VALIDATION
  // =======================================================================

  /**
   * Render progress chip for a pekerjaan row
   * Shows total progress percentage with validation status.
   *
   * @param {string|number} nodeId - Node ID
   * @returns {string} HTML for progress chip
   * @private
   */
  _renderProgressChip(nodeId) {
    const total = this.calculateRowProgress(nodeId);
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

  /**
   * Calculate total progress for a row (sum of all time columns)
   * Used for progress validation (should total 100%).
   *
   * @param {string|number} nodeId - Node ID
   * @returns {number|null} Total percentage or null if invalid
   */
  calculateRowProgress(nodeId) {
    if (!this.state || !Array.isArray(this.state.timeColumns) || this.state.timeColumns.length === 0) {
      return null;
    }

    let total = 0;
    this.state.timeColumns.forEach((column) => {
      const { value } = this.getEffectiveCellValue(nodeId, column.id);
      const numeric = Number.isFinite(value) ? value : parseFloat(value) || 0;
      total += numeric;
    });

    if (!Number.isFinite(total)) {
      return null;
    }

    return parseFloat(total.toFixed(1));
  }

  // =======================================================================
  // CELL VALUE RESOLUTION
  // =======================================================================

  /**
   * Get effective cell value (modified or saved)
   * Checks modifiedCells Map first, falls back to assignmentMap.
   *
   * @param {string|number} nodeId - Node ID
   * @param {string} columnId - Column ID
   * @param {number} fallbackSaved - Fallback saved value
   * @returns {Object} { value: number, modifiedValue: number|undefined }
   */
  getEffectiveCellValue(nodeId, columnId, fallbackSaved = 0) {
    const cellKey = `${nodeId}-${columnId}`;
    const savedNumeric = typeof fallbackSaved === 'number'
      ? fallbackSaved
      : parseFloat(fallbackSaved) || 0;

    let modifiedValue;
    if (this.state.modifiedCells instanceof Map && this.state.modifiedCells.has(cellKey)) {
      const candidate = parseFloat(this.state.modifiedCells.get(cellKey));
      if (Number.isFinite(candidate)) {
        modifiedValue = candidate;
      }
    }

    const value = modifiedValue !== undefined ? modifiedValue : savedNumeric;
    return { value, modifiedValue };
  }

  /**
   * Get saved assignment value from assignmentMap
   * @param {string} cellKey - Cell key (nodeId-columnId)
   * @returns {number} Saved value or 0
   * @private
   */
  _getAssignmentValue(cellKey) {
    if (!this.state || !this.state.assignmentMap) return 0;

    if (this.state.assignmentMap instanceof Map) {
      return this.state.assignmentMap.get(cellKey) || 0;
    }

    if (typeof this.state.assignmentMap.get === 'function') {
      return this.state.assignmentMap.get(cellKey) || 0;
    }

    if (Object.prototype.hasOwnProperty.call(this.state.assignmentMap, cellKey)) {
      return this.state.assignmentMap[cellKey];
    }

    return 0;
  }

  // =======================================================================
  // TREE STATE MANAGEMENT
  // =======================================================================

  /**
   * Check if a node is expanded
   * @param {string|number} nodeId - Node ID
   * @returns {boolean} True if expanded
   * @private
   */
  _isNodeExpanded(nodeId) {
    if (!this.state || !this.state.expandedNodes) {
      return true; // Default to expanded
    }
    return this.state.expandedNodes.has(nodeId) !== false;
  }

  /**
   * Toggle node expansion state
   * Updates expandedNodes Set and returns new state.
   *
   * @param {string|number} nodeId - Node ID
   * @returns {boolean} New expanded state
   */
  toggleNode(nodeId) {
    if (!this.state.expandedNodes) {
      this.state.expandedNodes = new Set();
    }

    const isCurrentlyExpanded = this.state.expandedNodes.has(nodeId);

    if (isCurrentlyExpanded) {
      this.state.expandedNodes.delete(nodeId);
      console.log(`[GridRenderer] Collapsed node: ${nodeId}`);
      return false;
    } else {
      this.state.expandedNodes.add(nodeId);
      console.log(`[GridRenderer] Expanded node: ${nodeId}`);
      return true;
    }
  }

  /**
   * Expand a node
   * @param {string|number} nodeId - Node ID
   */
  expandNode(nodeId) {
    if (!this.state.expandedNodes) {
      this.state.expandedNodes = new Set();
    }
    this.state.expandedNodes.add(nodeId);
    console.log(`[GridRenderer] Expanded node: ${nodeId}`);
  }

  /**
   * Collapse a node
   * @param {string|number} nodeId - Node ID
   */
  collapseNode(nodeId) {
    if (!this.state.expandedNodes) {
      return;
    }
    this.state.expandedNodes.delete(nodeId);
    console.log(`[GridRenderer] Collapsed node: ${nodeId}`);
  }

  /**
   * Expand all nodes in tree
   */
  expandAll() {
    if (!this.state.expandedNodes) {
      this.state.expandedNodes = new Set();
    }

    const collectIds = (nodes) => {
      nodes.forEach((node) => {
        if (!node || !node.id) return;
        if (node.children && node.children.length > 0) {
          this.state.expandedNodes.add(node.id);
          collectIds(node.children);
        }
      });
    };

    if (Array.isArray(this.state.pekerjaanTree)) {
      collectIds(this.state.pekerjaanTree);
      console.log(`[GridRenderer] Expanded all nodes (${this.state.expandedNodes.size} nodes)`);
    }
  }

  /**
   * Collapse all nodes in tree
   */
  collapseAll() {
    if (this.state.expandedNodes) {
      this.state.expandedNodes.clear();
      console.log('[GridRenderer] Collapsed all nodes');
    }
  }

  // =======================================================================
  // UI SYNCHRONIZATION
  // =======================================================================

  /**
   * Synchronize row heights between left and right panels
   * Ensures rows align properly across dual panels.
   *
   * @param {Object} domRefs - DOM references
   * @param {HTMLElement} domRefs.leftTbody - Left table body
   * @param {HTMLElement} domRefs.rightTbody - Right table body
   */
  syncRowHeights(domRefs) {
    if (this.state?.useAgGrid) {
      return;
    }

    const leftTbody = domRefs.leftTbody || document.getElementById('left-tbody');
    const rightTbody = domRefs.rightTbody || document.getElementById('right-tbody');

    if (!leftTbody || !rightTbody) {
      return;
    }

    const leftRows = leftTbody.querySelectorAll('tr');
    const rightRows = rightTbody.querySelectorAll('tr');

    console.log(`[GridRenderer] Syncing heights for ${leftRows.length} rows`);

    // Batch read phase (avoid layout thrashing)
    const heights = [];
    leftRows.forEach((leftRow, index) => {
      const rightRow = rightRows[index];
      if (!rightRow) return;

      // Reset heights first
      leftRow.style.height = '';
      rightRow.style.height = '';

      // Read heights
      const leftHeight = leftRow.offsetHeight;
      const rightHeight = rightRow.offsetHeight;
      const maxHeight = Math.max(leftHeight, rightHeight);

      heights.push(maxHeight);
    });

    // Batch write phase
    leftRows.forEach((leftRow, index) => {
      const rightRow = rightRows[index];
      if (!rightRow || !heights[index]) return;

      const maxHeight = heights[index];
      leftRow.style.height = `${maxHeight}px`;
      rightRow.style.height = `${maxHeight}px`;
    });

    console.log('[GridRenderer] ✅ Row heights synchronized');
  }

  /**
   * Synchronize header heights between left and right panels
   * @param {Object} domRefs - DOM references
   * @param {HTMLElement} domRefs.leftThead - Left table header
   * @param {HTMLElement} domRefs.rightThead - Right table header
   */
  syncHeaderHeights(domRefs) {
    const leftThead = domRefs.leftThead || document.getElementById('left-thead');
    const rightThead = domRefs.rightThead || document.getElementById('right-thead');

    if (!leftThead || !rightThead) {
      console.warn('[GridRenderer] Cannot sync header heights: missing thead elements');
      return;
    }

    const leftHeaderRow = leftThead.querySelector('tr');
    const rightHeaderRow = rightThead.querySelector('tr');

    if (!leftHeaderRow || !rightHeaderRow) {
      console.warn('[GridRenderer] Cannot sync header heights: missing tr elements');
      return;
    }

    // Reset heights
    leftHeaderRow.style.height = '';
    rightHeaderRow.style.height = '';

    // Calculate max height
    const maxHeight = Math.max(leftHeaderRow.offsetHeight, rightHeaderRow.offsetHeight);

    // Apply max height
    leftHeaderRow.style.height = `${maxHeight}px`;
    rightHeaderRow.style.height = `${maxHeight}px`;

    console.log(`[GridRenderer] Header heights synchronized: ${maxHeight}px`);
  }

  /**
   * Setup scroll synchronization between left and right panels
   * @param {Object} domRefs - DOM references
   * @param {HTMLElement} domRefs.leftPanelScroll - Left scroll container
   * @param {HTMLElement} domRefs.rightPanelScroll - Right scroll container
   * @returns {Object|null} Cleanup handlers or null if already setup
   */
  setupScrollSync(domRefs) {
    const leftPanel = domRefs.leftPanelScroll || document.querySelector('.left-panel-scroll');
    const rightPanel = domRefs.rightPanelScroll || document.querySelector('.right-panel-scroll');

    if (!leftPanel || !rightPanel) {
      console.warn('[GridRenderer] Cannot setup scroll sync: missing scroll containers');
      return null;
    }

    // Check if already setup
    if (this.state.cache && this.state.cache.gridScrollSyncBound) {
      console.log('[GridRenderer] Scroll sync already setup');
      return this.state.cache.gridScrollSyncBound;
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

    const handlers = { syncFromRight, syncFromLeft };

    // Cache handlers for cleanup
    if (!this.state.cache) {
      this.state.cache = {};
    }
    this.state.cache.gridScrollSyncBound = handlers;

    console.log('[GridRenderer] ✅ Scroll sync setup complete');
    return handlers;
  }

  // =======================================================================
  // UTILITY METHODS
  // =======================================================================

  /**
   * Get statistics about rendered grid
   * @returns {Object} Grid statistics
   */
  getStats() {
    const totalRows = this.state.flatPekerjaan ? this.state.flatPekerjaan.length : 0;
    const pekerjaanRows = this.state.flatPekerjaan
      ? this.state.flatPekerjaan.filter(n => n.type === 'pekerjaan').length
      : 0;
    const timeColumns = this.state.timeColumns ? this.state.timeColumns.length : 0;
    const totalCells = pekerjaanRows * timeColumns;
    const modifiedCells = this.state.modifiedCells ? this.state.modifiedCells.size : 0;
    const expandedNodes = this.state.expandedNodes ? this.state.expandedNodes.size : 0;

    return {
      totalRows,
      pekerjaanRows,
      timeColumns,
      totalCells,
      modifiedCells,
      expandedNodes
    };
  }

  /**
   * Validate grid state
   * @returns {Object} Validation result
   */
  validateState() {
    const errors = [];
    const warnings = [];

    if (!Array.isArray(this.state.pekerjaanTree)) {
      errors.push('Missing pekerjaanTree');
    }

    if (!Array.isArray(this.state.timeColumns)) {
      errors.push('Missing timeColumns');
    }

    if (!(this.state.volumeMap instanceof Map)) {
      warnings.push('volumeMap is not a Map');
    }

    if (!(this.state.assignmentMap instanceof Map)) {
      warnings.push('assignmentMap is not a Map');
    }

    if (!(this.state.modifiedCells instanceof Map)) {
      warnings.push('modifiedCells is not a Map');
    }

    if (!(this.state.expandedNodes instanceof Set)) {
      warnings.push('expandedNodes is not a Set');
    }

    const isValid = errors.length === 0;

    if (!isValid) {
      console.error('[GridRenderer] Validation errors:', errors);
    }

    if (warnings.length > 0) {
      console.warn('[GridRenderer] Validation warnings:', warnings);
    }

    return {
      isValid,
      errors,
      warnings
    };
  }
}

// Export utilities for external use
export {
  escapeHtml,
  formatNumber
};
