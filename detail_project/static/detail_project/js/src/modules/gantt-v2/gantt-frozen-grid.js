/**
 * Gantt Frozen Grid - V2 Architecture
 * Proof of Concept: Single grid with frozen columns (CSS sticky)
 * @module gantt-frozen-grid
 */

import { Toast } from '@modules/shared/ux-enhancements.js';

/**
 * GanttFrozenGrid - Main component for frozen column Gantt
 */
export class GanttFrozenGrid {
  constructor(container, options = {}) {
    this.container = typeof container === 'string'
      ? document.querySelector(container)
      : container;

    if (!this.container) {
      throw new Error('Gantt container not found');
    }

    // Options
    this.options = {
      rowHeight: options.rowHeight || 40,
      frozenColumnWidth: 280,
      volumeColumnWidth: 70,
      satuanColumnWidth: 70,
      timelineColumnWidth: 100,
      timeScale: options.timeScale || 'week',
      ...options
    };

    // State
    this.state = {
      rows: [],
      timelineColumns: [],
      scrollTop: 0,
      scrollLeft: 0,
      initialized: false,
      expandedNodes: new Map() // Track expand/collapse state by node ID
    };

    // Elements
    this.elements = {
      gridContainer: null
    };

    // Theme observer
    this.themeObserver = null;

    // Store pekerjaan and timeColumns for re-render after expand/collapse
    this.pekerjaan = [];
    this.timeColumns = [];
  }

  /**
   * Initialize Gantt with app context
   * @param {JadwalKegiatanApp} app - App instance with StateManager, tahapan, etc.
   */
  async initialize(app) {
    console.log('🚀 Initializing Gantt Frozen Grid V2 (Phase 2: Real Data)...');

    try {
      // Store app reference for data access
      this.app = app;
      this.stateManager = app.stateManager;
      this.timeColumnGenerator = app.timeColumnGenerator;

      // Debug: Check what we have
      console.log('[GanttV2] App references:', {
        hasStateManager: !!this.stateManager,
        hasTimeColumnGenerator: !!this.timeColumnGenerator,
        hasFlatPekerjaan: !!app.state?.flatPekerjaan
      });

      // Get real data
      const pekerjaan = app.state.flatPekerjaan || [];

      // IMPORTANT: TimeColumnGenerator stores columns in state.timeColumns, not this.columns!
      const timeColumns = this.timeColumnGenerator?.state?.timeColumns || app.state?.timeColumns || [];

      console.log('[GanttV2] Data loaded:', {
        pekerjaanCount: pekerjaan.length,
        timeColumnsCount: timeColumns.length,
        timeScale: app.state?.timeScale || 'unknown'
      });

      // Debug: Show first few columns and pekerjaan
      if (timeColumns.length > 0) {
        console.log('[GanttV2] First 3 columns:', timeColumns.slice(0, 3));
        console.log('[GanttV2] First 3 column IDs:', timeColumns.slice(0, 3).map(c => c.id));
        console.log('[GanttV2] Last 3 columns:', timeColumns.slice(-3));
        console.log('[GanttV2] Last 3 column IDs:', timeColumns.slice(-3).map(c => c.id));

        // CRITICAL: Check if column ID is tahapanId
        const firstCol = timeColumns[0];
        console.log('[GanttV2] First column structure:', {
          id: firstCol.id,
          tahapanId: firstCol.tahapanId,
          label: firstCol.label
        });
      } else {
        console.warn('[GanttV2] ⚠️ NO TIME COLUMNS! TimeColumnGenerator might not be initialized.');
        console.log('[GanttV2] TimeColumnGenerator object:', this.timeColumnGenerator);

        // Fallback to demo mode
        console.warn('[GanttV2] Falling back to DEMO mode with hardcoded 20 weeks...');
        const demoColumns = this._generateDemoTimeColumns(20);

        this._buildDOM(demoColumns.length);
        this._renderRealData(pekerjaan, demoColumns);

        this.state.initialized = true;
        console.log('✅ Gantt Frozen Grid V2 initialized (DEMO MODE - no TimeColumnGenerator)');
        Toast.success('📊 Gantt Chart loaded (Demo Mode)', 2000);
        return;
      }

      // Debug: Show first few pekerjaan
      if (pekerjaan.length > 0) {
        console.log('[GanttV2] First pekerjaan:', pekerjaan[0]);
        console.log('[GanttV2] Pekerjaan types:', pekerjaan.slice(0, 5).map(p => ({
          id: p.id,
          type: p.type,
          level: p.level,
          nama: p.nama?.substring(0, 30)
        })));
      }

      // Store data for re-render (expand/collapse)
      this.pekerjaan = pekerjaan;
      this.timeColumns = timeColumns;

      // Initialize all non-leaf nodes as expanded by default
      this._initializeExpandState(pekerjaan);

      // Build DOM structure with dynamic columns
      this._buildDOM(timeColumns.length);

      // Render real data
      this._renderRealData(pekerjaan, timeColumns);

      // Setup theme observer to re-render on theme change
      this._setupThemeObserver(pekerjaan, timeColumns);

      this.state.initialized = true;

      console.log('✅ Gantt Frozen Grid V2 initialized successfully');
      Toast.success('📊 Gantt Chart loaded', 2000);

    } catch (error) {
      console.error('❌ Failed to initialize Gantt Frozen Grid:', error);
      throw error;
    }
  }

  /**
   * Build DOM structure with CSS Grid
   * @private
   */
  _buildDOM(timeColumnCount) {
    this.container.innerHTML = '';
    this.container.className = 'gantt-frozen-container';

    // Detect dark mode - ONLY check data-bs-theme attribute (Bootstrap 5.3+)
    // Don't use prefers-color-scheme as fallback to avoid conflicts
    const theme = document.documentElement.getAttribute('data-bs-theme');
    const isDarkMode = theme === 'dark';

    console.log('[GanttV2] Theme detection:', {
      'data-bs-theme': theme,
      isDarkMode,
      hasTimeColumns: timeColumnCount
    });

    const bgColor = isDarkMode ? '#1e1e1e' : '#ffffff';
    const borderColor = isDarkMode ? '#404040' : '#dee2e6';

    // Create grid container with dynamic columns
    const gridContainer = document.createElement('div');
    gridContainer.className = 'gantt-grid';
    gridContainer.style.cssText = `
      display: grid;
      grid-template-columns: 280px 70px 70px repeat(${timeColumnCount}, 100px);
      overflow: auto;
      height: 600px;
      background: ${bgColor};
      border: 1px solid ${borderColor};
    `;

    this.container.appendChild(gridContainer);
    this.elements.gridContainer = gridContainer;

    // Store for later use
    this.isDarkMode = isDarkMode;
    this.borderColor = borderColor;
  }

  /**
   * Render real data (Phase 2)
   * @private
   */
  _renderRealData(pekerjaan, timeColumns) {
    this._renderHeaders(timeColumns);
    this._renderDataRows(pekerjaan, timeColumns);
  }

  /**
   * Render header row with real timeline
   * @private
   */
  _renderHeaders(timeColumns) {
    const headerBg = this.isDarkMode ? '#2d2d2d' : 'var(--bs-light, #f8f9fa)';
    const headerColor = this.isDarkMode ? '#e0e0e0' : '#212529';

    // Frozen headers
    const frozenHeaders = [
      { label: 'Pekerjaan', width: '280px' },
      { label: 'Volume', width: '70px' },
      { label: 'Satuan', width: '70px' }
    ];

    frozenHeaders.forEach((header, i) => {
      const headerCell = document.createElement('div');
      headerCell.className = 'gantt-header-cell frozen';
      headerCell.style.cssText = `
        position: sticky;
        left: ${this._calculateStickyLeft(i)}px;
        top: 0;
        z-index: 20;
        background: ${headerBg};
        color: ${headerColor};
        font-weight: 600;
        padding: 0.5rem;
        border-bottom: 2px solid ${this.borderColor};
        border-right: ${i === 2 ? '2px' : '1px'} solid ${this.borderColor};
        ${i === 0 ? `border-left: 1px solid ${this.borderColor};` : ''}
        display: flex;
        align-items: center;
        height: ${this.options.rowHeight}px;
        box-sizing: border-box;
      `;
      headerCell.textContent = header.label;
      this.elements.gridContainer.appendChild(headerCell);
    });

    // Timeline headers from TimeColumnGenerator
    timeColumns.forEach((col, i) => {
      const headerCell = document.createElement('div');
      headerCell.className = 'gantt-header-cell timeline';
      headerCell.style.cssText = `
        position: sticky;
        top: 0;
        z-index: 10;
        background: ${headerBg};
        color: ${headerColor};
        font-weight: 600;
        padding: 0.25rem;
        border-bottom: 2px solid ${this.borderColor};
        border-right: 1px solid ${this.isDarkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)'};
        ${i === 0 ? `border-left: 1px solid ${this.borderColor};` : ''}
        text-align: center;
        font-size: 0.75rem;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        gap: 0.1rem;
        line-height: 1.1;
        height: ${this.options.rowHeight}px;
        box-sizing: border-box;
      `;

      // Main label (e.g., "Week 1" or "Jan 2025")
      const labelSpan = document.createElement('div');
      labelSpan.style.cssText = 'font-weight: 600; font-size: 0.7rem;';
      labelSpan.textContent = col.label || col.id;
      headerCell.appendChild(labelSpan);

      // Date range (e.g., "01-07 Jan")
      if (col.rangeLabel || col.subLabel) {
        const rangeSpan = document.createElement('div');
        rangeSpan.style.cssText = `
          font-weight: 400;
          font-size: 0.6rem;
          color: ${this.isDarkMode ? '#9ca3af' : '#6c757d'};
          opacity: 0.85;
        `;
        rangeSpan.textContent = col.rangeLabel || col.subLabel;
        headerCell.appendChild(rangeSpan);
      }

      this.elements.gridContainer.appendChild(headerCell);
    });

    console.log(`[GanttV2] Rendered ${timeColumns.length} timeline headers`);
  }

  /**
   * Render data rows with real pekerjaan
   * @private
   */
  _renderDataRows(pekerjaan, timeColumns) {
    if (!pekerjaan || pekerjaan.length === 0) {
      console.warn('[GanttV2] No pekerjaan data to render');
      return;
    }

    // Get only visible rows (respecting expand/collapse state)
    const visibleRows = this._getVisibleRows(pekerjaan);

    console.log(`[GanttV2] Rendering ${visibleRows.length}/${pekerjaan.length} visible rows`);

    visibleRows.forEach(node => {
      // Determine level for indentation
      const level = node.level || 0;
      const hasChildren = node.children && node.children.length > 0;

      // Frozen cells (pass node for expand/collapse toggle)
      this._createFrozenCell(node.nama || node.name || 'Unknown', 0, level, 'left', node, hasChildren);
      this._createFrozenCell(node.volume || 0, 1, 0, 'right');
      this._createFrozenCell(node.satuan || '-', 2, 0, 'center');

      // Timeline cells with assignments
      // Only render bars for actual pekerjaan (leaf nodes)
      this._renderTimelineCells(node, timeColumns);
    });

    console.log(`✅ Rendered ${visibleRows.length} rows`);
  }

  /**
   * Create frozen cell with text wrap support and expand/collapse toggle
   * @private
   */
  _createFrozenCell(content, columnIndex, level = 0, align = 'left', node = null, hasChildren = false) {
    const cell = document.createElement('div');
    cell.className = 'gantt-cell frozen';
    if (columnIndex === 0) {
      cell.classList.add('tree-column');
    }
    if (columnIndex === 2) {
      cell.classList.add('frozen-last');
    }

    const stickyLeft = this._calculateStickyLeft(columnIndex);
    const paddingLeft = columnIndex === 0 ? `${0.5 + level * 1.5}rem` : '0.5rem'; // Indentation based on level

    const bgColor = this.isDarkMode ? '#1e1e1e' : 'white';
    const textColor = this.isDarkMode ? '#e0e0e0' : '#212529';

    // Determine font weight based on hierarchy level
    // Level 0 = Klasifikasi (bold 700), Level 1 = Sub-klasifikasi (semibold 600), Level 2+ = Pekerjaan (normal 400)
    const fontWeight = level === 0 ? '700' : level === 1 ? '600' : '400';

    // Fix #1: Add border-left to prevent gap on left side
    // Fix #2: Use font-size 0.7rem and ensure text is vertically centered with align-items: center
    cell.style.cssText = `
      position: sticky;
      left: ${stickyLeft}px;
      z-index: 5;
      background: ${bgColor};
      color: ${textColor};
      padding: 0.5rem;
      padding-left: ${paddingLeft};
      display: flex;
      align-items: center;
      justify-content: ${align === 'right' ? 'flex-end' : align === 'center' ? 'center' : 'flex-start'};
      font-size: ${columnIndex === 0 ? '0.7rem' : '0.875rem'};
      font-weight: ${columnIndex === 0 ? fontWeight : '400'};
      height: ${this.options.rowHeight}px;
      line-height: 1.2;
      box-sizing: border-box;
      overflow: hidden;
    `;

    // Text content wrapper for first column (name)
    if (columnIndex === 0) {
      const textSpan = document.createElement('span');
      textSpan.textContent = content;
      textSpan.style.cssText = `
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        flex: 1;
      `;
      cell.appendChild(textSpan);
    } else {
      // For other columns (volume, satuan), just add text directly
      cell.textContent = content;
    }

    this.elements.gridContainer.appendChild(cell);

    return cell;
  }

  /**
   * Render timeline cells for a pekerjaan row with continuous bars
   * @private
   */
  _renderTimelineCells(node, timeColumns) {
    // Get all cell values for planned and actual modes
    const plannedCells = this.stateManager.getAllCellsForMode('planned');
    const actualCells = this.stateManager.getAllCellsForMode('actual');

    // Extract assignments for this pekerjaan
    const plannedAssignments = this._extractAssignmentsForPekerjaan(node.id, plannedCells, timeColumns);
    const actualAssignments = this._extractAssignmentsForPekerjaan(node.id, actualCells, timeColumns);

    // Debug assignments for ALL pekerjaan (type === 'pekerjaan')
    if (node.type === 'pekerjaan') {
      console.log(`[GanttV2] Row ${node.id} (${node.nama?.substring(0, 30)}) assignments:`, {
        planned: plannedAssignments.length,
        actual: actualAssignments.length,
        plannedSample: plannedAssignments.slice(0, 3),
        actualSample: actualAssignments.slice(0, 3),
        plannedCellsTotal: plannedCells.size,
        actualCellsTotal: actualCells.size
      });

      // Debug: Show sample cell keys
      if (plannedCells.size > 0) {
        const sampleKeys = Array.from(plannedCells.keys()).slice(0, 5);
        console.log(`[GanttV2] Sample planned cell keys:`, sampleKeys);
      }
    }

    // Find date range for bars
    const plannedRange = this._getBarRange(plannedAssignments, timeColumns);
    const actualRange = this._getBarRange(actualAssignments, timeColumns);

    // Render each timeline cell
    timeColumns.forEach((col, colIndex) => {
      const cell = this._createTimelineCell(colIndex);

      // Check if this cell is part of planned bar range
      if (plannedRange && colIndex >= plannedRange.startIndex && colIndex <= plannedRange.endIndex) {
        this._addContinuousBarSegment(cell, 'planned', colIndex, plannedRange, plannedAssignments, timeColumns);
      }

      // Check if this cell is part of actual bar range
      if (actualRange && colIndex >= actualRange.startIndex && colIndex <= actualRange.endIndex) {
        this._addContinuousBarSegment(cell, 'actual', colIndex, actualRange, actualAssignments, timeColumns);
      }

      this.elements.gridContainer.appendChild(cell);
    });
  }

  /**
   * Extract assignments for a specific pekerjaan from cell map
   * @private
   * @param {number|string} pekerjaanId - Pekerjaan ID
   * @param {Map} cellMap - Cell value map from StateManager (key format: "pekerjaanId-columnId")
   * @param {Array} timeColumns - Timeline columns
   * @returns {Array} Array of assignments {tahapan_id, volume}
   */
  _extractAssignmentsForPekerjaan(pekerjaanId, cellMap, timeColumns) {
    const assignments = [];
    const pekerjaanIdStr = String(pekerjaanId);

    // Debug: Log first matching cell
    let firstMatch = false;

    // Iterate through all cells and find ones belonging to this pekerjaan
    cellMap.forEach((value, cellKey) => {
      const [cellPekerjaanId, columnId] = cellKey.split('-');

      if (cellPekerjaanId === pekerjaanIdStr && value > 0) {
        // Find the tahapan_id (column ID) from columnId
        const tahapanId = parseInt(columnId.replace('col_', ''));

        // Debug first match
        if (!firstMatch) {
          console.log(`[GanttV2] First match for pekerjaan ${pekerjaanId}:`, {
            cellKey,
            columnId,
            tahapanId,
            value,
            timeColumnsHasId: timeColumns.some(col => col.tahapanId === tahapanId)
          });
          firstMatch = true;
        }

        assignments.push({
          tahapan_id: tahapanId,
          volume: value
        });
      }
    });

    return assignments;
  }

  /**
   * Get bar range (start and end column index) for assignments
   * @private
   */
  _getBarRange(assignments, timeColumns) {
    if (!assignments || assignments.length === 0) return null;

    let startIndex = Infinity;
    let endIndex = -1;

    assignments.forEach(assignment => {
      // FIXED: Use col.tahapanId (numeric) instead of col.id (string "tahap-XXXX")
      const colIndex = timeColumns.findIndex(col => col.tahapanId === assignment.tahapan_id);
      if (colIndex !== -1) {
        startIndex = Math.min(startIndex, colIndex);
        endIndex = Math.max(endIndex, colIndex);
      }
    });

    if (startIndex === Infinity) return null;

    return { startIndex, endIndex };
  }

  /**
   * Add continuous bar segment to cell
   * @private
   */
  _addContinuousBarSegment(cell, type, colIndex, range, assignments, timeColumns) {
    const isFirst = colIndex === range.startIndex;
    const isLast = colIndex === range.endIndex;
    const isSingle = isFirst && isLast;

    // Calculate progress for this cell
    const col = timeColumns[colIndex];
    // FIXED: Use col.tahapanId (numeric) instead of col.id (string "tahap-XXXX")
    const assignment = assignments.find(a => col && a.tahapan_id === col.tahapanId);
    const progress = assignment?.volume || 0;

    // Dark mode colors
    const colors = type === 'planned'
      ? {
          bg: this.isDarkMode ? 'rgba(66, 153, 225, 0.5)' : 'rgba(13, 110, 253, 0.5)',
          border: this.isDarkMode ? '#4299e1' : '#0d6efd',
          progress: this.isDarkMode ? '#2c5282' : '#084298'
        }
      : {
          bg: this.isDarkMode ? 'rgba(237, 137, 54, 0.9)' : 'rgba(253, 126, 20, 0.9)',
          border: this.isDarkMode ? '#ed8936' : '#dc6d08',
          progress: this.isDarkMode ? '#9c4221' : '#b34d00'
        };

    const bar = document.createElement('div');
    bar.className = `gantt-bar-continuous ${type}`;
    bar.style.cssText = `
      position: absolute;
      top: ${type === 'planned' ? '25%' : '50%'};
      left: 0;
      width: 100%;
      height: 18px;
      transform: translateY(-50%);
      background: ${colors.bg};
      border-top: 1px solid ${colors.border};
      border-bottom: 2px solid ${colors.border};
      ${isFirst || isSingle ? `border-left: 2px solid ${colors.border}; border-top-left-radius: 4px; border-bottom-left-radius: 4px;` : ''}
      ${isLast || isSingle ? `border-right: 2px solid ${colors.border}; border-top-right-radius: 4px; border-bottom-right-radius: 4px;` : ''}
      z-index: ${type === 'actual' ? '3' : '2'};
      overflow: hidden;
    `;

    // Progress fill
    if (progress > 0) {
      const progressFill = document.createElement('div');
      progressFill.className = 'gantt-bar-progress';
      progressFill.style.cssText = `
        position: absolute;
        left: 0;
        top: 0;
        height: 100%;
        width: ${Math.min(progress, 100)}%;
        background: ${colors.progress};
        opacity: 0.6;
      `;
      bar.appendChild(progressFill);
    }

    cell.appendChild(bar);
  }

  /**
   * Create timeline cell
   * @private
   */
  _createTimelineCell(colIndex) {
    const cell = document.createElement('div');
    cell.className = 'gantt-cell timeline';
    if (colIndex === 0) {
      cell.classList.add('timeline-first');
    }
    cell.dataset.colIndex = colIndex;

    const bgColor = this.isDarkMode ? '#1e1e1e' : 'white';

    // CRITICAL: Use height, not min-height, to match frozen cells
    cell.style.cssText = `
      position: relative;
      background: ${bgColor};
      height: ${this.options.rowHeight}px;
      box-sizing: border-box;
    `;

    return cell;
  }

  /**
   * Calculate sticky left position for frozen columns
   * @private
   */
  _calculateStickyLeft(columnIndex) {
    const widths = [0, 280, 350]; // Cumulative widths
    return widths[columnIndex] || 0;
  }

  /**
   * Generate demo time columns (fallback when TimeColumnGenerator not available)
   * @private
   * @param {number} count - Number of weeks to generate
   * @returns {Array} Array of column objects
   */
  _generateDemoTimeColumns(count) {
    const columns = [];
    for (let i = 0; i < count; i++) {
      columns.push({
        id: 1000 + i, // Use high IDs to avoid conflicts
        label: `W${i + 1}`,
        startDate: new Date(2025, 0, 1 + i * 7), // Weekly intervals
        endDate: new Date(2025, 0, 8 + i * 7)
      });
    }
    return columns;
  }

  /**
   * Initialize expand state for all non-leaf nodes (Phase 3.1)
   * @private
   */
  _initializeExpandState(pekerjaan) {
    pekerjaan.forEach(node => {
      if (node.children && node.children.length > 0) {
        // Default: all nodes expanded
        this.state.expandedNodes.set(node.id, true);
      }
    });
    console.log(`[GanttV2] Initialized expand state for ${this.state.expandedNodes.size} parent nodes`);
  }

  /**
   * Get visible rows based on expand/collapse state (Phase 3.1)
   * IMPORTANT: flatPekerjaan is already a flat array, not nested!
   * @private
   */
  _getVisibleRows(pekerjaan) {
    const visible = [];
    const collapsedParents = new Set();

    // flatPekerjaan is already flat, so just filter based on parent collapse state
    pekerjaan.forEach(node => {
      // Check if any of this node's parents are collapsed
      const parentId = node.parent_id || node.parentId;

      // If this node has a parent that's collapsed, skip it
      if (parentId && collapsedParents.has(parentId)) {
        // Also mark this node as having a collapsed parent
        collapsedParents.add(node.id);
        return;
      }

      // Add this node to visible list
      visible.push(node);

      // If this node is collapsed, mark it so its children will be hidden
      const isCollapsed = this.state.expandedNodes.get(node.id) === false;
      if (isCollapsed) {
        collapsedParents.add(node.id);
      }
    });

    return visible;
  }

  /**
   * Toggle expand/collapse state for a node (Phase 3.1)
   * @private
   */
  _toggleNodeExpand(nodeId) {
    const currentState = this.state.expandedNodes.get(nodeId);
    const newState = !currentState;

    this.state.expandedNodes.set(nodeId, newState);

    console.log(`[GanttV2] Node ${nodeId} ${newState ? 'expanded' : 'collapsed'}`);

    // Re-render chart with new expand state
    this._buildDOM(this.timeColumns.length);
    this._renderRealData(this.pekerjaan, this.timeColumns);
  }

  /**
   * Setup theme observer to re-render on dark/light mode switch
   * @private
   */
  _setupThemeObserver(pekerjaan, timeColumns) {
    // Disconnect previous observer if exists
    if (this.themeObserver) {
      this.themeObserver.disconnect();
    }

    // Watch for data-bs-theme attribute changes on <html>
    this.themeObserver = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'attributes' && mutation.attributeName === 'data-bs-theme') {
          const newTheme = document.documentElement.getAttribute('data-bs-theme');
          console.log('[GanttV2] Theme changed to:', newTheme);

          // Re-render entire chart with new theme colors
          this._buildDOM(timeColumns.length);
          this._renderRealData(pekerjaan, timeColumns);

          Toast.info(`🎨 Gantt theme updated: ${newTheme}`, 1500);
        }
      });
    });

    this.themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-bs-theme']
    });

    console.log('[GanttV2] Theme observer setup complete');
  }

  /**
   * Update Gantt chart with latest data
   * Called after data changes (e.g., after save)
   */
  update() {
    if (!this.state.initialized) {
      console.warn('[GanttV2] Cannot update - not initialized');
      return;
    }

    if (!this.app) {
      console.warn('[GanttV2] Cannot update - no app reference');
      return;
    }

    console.log('[GanttV2] Updating chart with latest data...');

    // Get fresh data from app
    const pekerjaan = this.app.state.flatPekerjaan || [];
    const timeColumns = this.timeColumnGenerator?.state?.timeColumns || this.app.state?.timeColumns || [];

    // Clear existing grid content (but keep container structure)
    if (this.elements.gridContainer) {
      this.elements.gridContainer.innerHTML = '';
    }

    // Re-render with updated data
    this._renderRealData(pekerjaan, timeColumns);

    // Store for expand/collapse
    this.pekerjaan = pekerjaan;
    this.timeColumns = timeColumns;

    console.log('[GanttV2] ✅ Chart updated successfully');
  }

  /**
   * Destroy and cleanup
   */
  destroy() {
    // Disconnect theme observer
    if (this.themeObserver) {
      this.themeObserver.disconnect();
      this.themeObserver = null;
    }

    if (this.container) {
      this.container.innerHTML = '';
    }
    this.state.initialized = false;
    console.log('Gantt Frozen Grid destroyed');
  }
}
