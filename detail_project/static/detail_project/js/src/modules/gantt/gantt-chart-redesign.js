/**
 * Gantt Chart Redesign - Main Component
 * Uses frozen column architecture with TanStackGridManager + GanttCanvasOverlay
 * @module gantt-chart-redesign
 */

import { GanttDataModel } from './gantt-data-model.js';
import { GanttCanvasOverlay } from './GanttCanvasOverlay.js';
import { TanStackGridManager } from '@modules/grid/tanstack-grid-manager.js';
import { StateManager } from '@modules/core/state-manager.js';
import { Toast } from '@modules/shared/ux-enhancements.js';

/**
 * Main Gantt Chart Component
 */
export class GanttChartRedesign {
  constructor(container, options = {}) {
    this.container = typeof container === 'string'
      ? document.querySelector(container)
      : container;

    if (!this.container) {
      throw new Error('Gantt container not found');
    }

    // Options
    this.options = {
      mode: options.mode || 'planned', // 'planned' or 'actual'
      rowHeight: options.rowHeight || 40,
      enableMilestones: options.enableMilestones !== false,
      ...options
    };

    // Data model
    this.dataModel = new GanttDataModel();

    // Components (Frozen Column Architecture)
    this.gridManager = null;      // TanStackGridManager for unified grid
    this.canvasOverlay = null;    // GanttCanvasOverlay for bars
    this.stateManager = null;     // StateManager for data sync

    // State
    this.state = {
      loading: false,
      initialized: false,
      selectedNodeId: null,
      mode: this.options.mode,
      tahapanList: [] // Timeline columns (populated from options)
    };

    // Event callbacks
    this.onDataChange = options.onDataChange || (() => {});
    this.onNodeSelect = options.onNodeSelect || (() => {});
    this.onMilestoneChange = options.onMilestoneChange || (() => {});

    // Milestone popup
    this.milestonePopup = null;

    // Timeline configuration (from options or defaults)
    this.state.tahapanList = options.tahapanList || [];
  }

  /**
   * Initialize Gantt Chart
   */
  async initialize(rawData) {
    console.log('🚀 Initializing Gantt Chart (Frozen Column)...');
    this.state.loading = true;

    try {
      // Build DOM structure (single grid)
      this._buildDOM();

      // Initialize data model
      this.dataModel.initialize(rawData);

      // Create components (grid + overlay)
      await this._createComponents();

      // Setup StateManager event listeners
      this._setupStateListeners();

      // Mark as initialized BEFORE rendering
      this.state.loading = false;
      this.state.initialized = true;

      // Initial render
      this.render();

      console.log('✅ Gantt Chart (Frozen Column) initialized successfully');
      Toast.success('Gantt Chart loaded successfully');

    } catch (error) {
      console.error('❌ Failed to initialize Gantt Chart:', error);
      this._showError('Failed to initialize Gantt Chart: ' + error.message);
      this.state.loading = false;
      throw error;
    }
  }

  /**
   * Build DOM structure (Frozen Column Architecture)
   * Creates single scrollable grid container
   */
  _buildDOM() {
    this.container.innerHTML = '';
    this.container.className = 'gantt-container';

    // Create grid wrapper (for TanStackGridManager + canvas overlay)
    const gridWrapper = document.createElement('div');
    gridWrapper.className = 'gantt-grid-wrapper';
    gridWrapper.style.position = 'relative';
    gridWrapper.style.width = '100%';
    gridWrapper.style.height = '100%';
    this.container.appendChild(gridWrapper);

    // Create table element for grid
    const table = document.createElement('table');
    table.className = 'gantt-grid';
    gridWrapper.appendChild(table);

    // Store references
    this.elements = {
      gridWrapper,
      table
    };
  }

  /**
   * Create components (Frozen Column Architecture)
   */
  async _createComponents() {
    // Initialize StateManager (single source of truth for cell data)
    const flatData = this.dataModel.getFlatData();
    this.stateManager = new StateManager(flatData);

    // Build column definitions for TanStackGridManager
    const columns = this._buildGanttColumns();

    // Create TanStackGridManager
    this.gridManager = new TanStackGridManager({
      container: this.elements.table,
      columns: columns,
      data: flatData,
      options: {
        enableVirtualization: true,
        rowHeight: this.options.rowHeight,
        enableHierarchy: true,
        getRowId: (row) => String(row.id),
        onCellClick: (row, column) => this._handleCellClick(row, column),
      }
    });

    // Wait for grid to render
    await new Promise(resolve => setTimeout(resolve, 100));

    // Create GanttCanvasOverlay for bars
    this.canvasOverlay = new GanttCanvasOverlay(
      this.elements.gridWrapper,
      this.gridManager,
      {
        mode: this.state.mode,
        onBarClick: (pekerjaanId, columnId) => this._handleBarClick(pekerjaanId, columnId)
      }
    );

    // Create milestone popup
    this._createMilestonePopup();
  }

  /**
   * Build column definitions for Gantt grid
   * Returns array of frozen columns (tree structure) + timeline columns
   */
  _buildGanttColumns() {
    const columns = [];

    // Frozen Column 1: Tree (Hierarchy + Name)
    columns.push({
      id: 'name',
      header: 'Work Breakdown Structure',
      accessorKey: 'name',
      size: 300,
      minSize: 200,
      maxSize: 500,
      meta: {
        pinned: true, // Frozen column
        columnIndex: 0
      },
      cell: (info) => {
        const row = info.row.original;
        const level = row.level || 0;
        const indent = level * 20;

        // Render tree structure with expand/collapse
        let html = `<div style="padding-left: ${indent}px; display: flex; align-items: center; gap: 0.5rem;">`;

        // Expand/collapse button
        if (!row.isLeaf() || row.children?.length > 0) {
          html += `
            <button class="tree-expand-btn" data-row-id="${row.id}">
              <i class="bi bi-chevron-${row.expanded ? 'down' : 'right'}"></i>
            </button>
          `;
        } else {
          html += `<span class="tree-expand-spacer"></span>`;
        }

        // Icon
        const icon = row.type === 'klasifikasi' ? 'folder' :
                     row.type === 'sub-klasifikasi' ? 'folder2' : 'file-earmark';
        html += `<i class="bi bi-${icon} tree-node-icon"></i>`;

        // Name + Code
        html += `
          <div class="tree-node-label">
            ${row.kode ? `<span class="tree-node-kode">${row.kode}</span>` : ''}
            <span class="tree-node-name">${row.name}</span>
          </div>
        `;

        html += `</div>`;
        return html;
      }
    });

    // Timeline columns (dynamic based on tahapanList)
    if (this.state.tahapanList && this.state.tahapanList.length > 0) {
      this.state.tahapanList.forEach((tahapan, index) => {
        columns.push({
          id: tahapan.column_id,
          header: tahapan.nama_tahapan,
          accessorKey: tahapan.column_id,
          size: 80,
          minSize: 60,
          maxSize: 120,
          meta: {
            pinned: false,
            columnIndex: index + 1,
            tahapanId: tahapan.id
          },
          cell: (info) => {
            // Timeline cells are empty - canvas overlay renders bars
            return '';
          }
        });
      });
    } else {
      // Fallback: If no tahapanList, create placeholder columns
      console.warn('⚠️ No tahapanList provided, using placeholder columns');
      for (let i = 0; i < 12; i++) {
        const monthName = new Date(2024, i, 1).toLocaleDateString('en', { month: 'short' });
        columns.push({
          id: `month_${i}`,
          header: monthName,
          accessorKey: `month_${i}`,
          size: 80,
          minSize: 60,
          maxSize: 120,
          meta: {
            pinned: false,
            columnIndex: i + 1
          },
          cell: () => ''
        });
      }
    }

    return columns;
  }

  /**
   * Setup StateManager event listeners
   */
  _setupStateListeners() {
    if (!this.stateManager) return;

    // Listen to individual cell updates
    this.stateManager.on('cell:updated', (event) => {
      const { pekerjaanId, columnId, field, value } = event;

      // Only re-render if planned/actual changed
      if (field === 'planned' || field === 'actual') {
        console.log(`[Gantt] Cell updated: ${pekerjaanId}/${columnId}/${field} = ${value}`);
        this._renderBars();
      }
    });

    // Listen to bulk updates (e.g., after data import)
    this.stateManager.on('bulk:updated', () => {
      console.log('[Gantt] Bulk update detected, re-rendering all bars');
      this._renderBars();
    });

    // Listen to mode changes (planned vs actual)
    this.stateManager.on('mode:changed', (mode) => {
      console.log(`[Gantt] Mode changed to: ${mode}`);
      this.state.mode = mode;
      this._renderBars();
    });
  }

  /**
   * Render Gantt bars (called by StateManager events)
   */
  _renderBars() {
    if (this.canvasOverlay && this.state.initialized) {
      this.canvasOverlay.syncWithTable();
    }
  }

  /**
   * Handle cell click (from TanStackGridManager)
   */
  _handleCellClick(row, column) {
    // Handle expand/collapse button click
    if (event.target.closest('.tree-expand-btn')) {
      this._handleNodeExpand(row.id, !row.expanded);
      return;
    }

    // Handle node selection
    this._handleNodeClick(row.id);
  }

  /**
   * Handle node click
   */
  _handleNodeClick(nodeId) {
    this.state.selectedNodeId = nodeId;
    const node = this.dataModel.getNodeById(nodeId);

    console.log('📌 Node selected:', node);

    // Notify external listeners
    this.onNodeSelect(node);
  }

  /**
   * Handle node expand/collapse
   */
  _handleNodeExpand(nodeId, expanded) {
    console.log(`${expanded ? '📂' : '📁'} Node ${expanded ? 'expanded' : 'collapsed'}:`, nodeId);

    // Toggle node in data model
    const node = this.dataModel.getNodeById(nodeId);
    if (node) {
      node.expanded = expanded;
    }

    // Re-render grid
    this.render();
  }

  /**
   * Handle bar click (from GanttCanvasOverlay)
   */
  _handleBarClick(pekerjaanId, columnId) {
    const node = this.dataModel.getNodeById(pekerjaanId);
    if (!node) return;

    console.log(`📊 Bar clicked: ${node.name} (${columnId})`);

    // Select the node
    this._handleNodeClick(pekerjaanId);

    // Get progress value from StateManager
    const field = this.state.mode === 'planned' ? 'planned' : 'actual';
    const value = this.stateManager.getCellValue(pekerjaanId, columnId, field);

    // Show bar details
    Toast.info(`${node.name}: ${field} = ${value || 0}%`);
  }

  /**
   * Handle milestone click
   */
  _handleMilestoneClick(milestone, event) {
    console.log('🎯 Milestone clicked:', milestone);

    // Show milestone popup
    this._showMilestonePopup(milestone, event);
  }

  /**
   * Create milestone popup
   */
  _createMilestonePopup() {
    if (!this.options.enableMilestones) return;

    const popup = document.createElement('div');
    popup.className = 'milestone-popup';
    popup.innerHTML = `
      <div class="milestone-popup-header">
        <h6 class="milestone-popup-title"></h6>
        <button class="milestone-popup-close" aria-label="Close">
          <i class="bi bi-x"></i>
        </button>
      </div>
      <div class="milestone-popup-body">
        <div class="milestone-popup-date">
          <i class="bi bi-calendar"></i>
          <span class="milestone-date-text"></span>
        </div>
        <div class="milestone-popup-description"></div>
        <div class="milestone-popup-comments"></div>
      </div>
    `;

    document.body.appendChild(popup);
    this.milestonePopup = popup;

    // Close button
    popup.querySelector('.milestone-popup-close').addEventListener('click', () => {
      this._hideMilestonePopup();
    });

    // Click outside to close
    document.addEventListener('click', (e) => {
      if (popup.classList.contains('visible') &&
          !popup.contains(e.target) &&
          !e.target.closest('.milestone-marker')) {
        this._hideMilestonePopup();
      }
    });
  }

  /**
   * Show milestone popup
   */
  _showMilestonePopup(milestone, event) {
    if (!this.milestonePopup) return;

    // Populate popup
    this.milestonePopup.querySelector('.milestone-popup-title').textContent = milestone.title;
    this.milestonePopup.querySelector('.milestone-date-text').textContent =
      milestone.date.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    this.milestonePopup.querySelector('.milestone-popup-description').textContent =
      milestone.description || 'No description';

    // Render comments
    const commentsContainer = this.milestonePopup.querySelector('.milestone-popup-comments');
    if (milestone.comments.length > 0) {
      commentsContainer.innerHTML = milestone.comments.map(comment => `
        <div class="milestone-comment">
          <div class="milestone-comment-author">${comment.author}</div>
          <div class="milestone-comment-text">${comment.text}</div>
          <div class="milestone-comment-time">${this._formatDate(comment.timestamp)}</div>
        </div>
      `).join('');
    } else {
      commentsContainer.innerHTML = '<p class="text-muted">No comments yet</p>';
    }

    // Position popup near click
    const x = event.clientX;
    const y = event.clientY;

    this.milestonePopup.style.left = x + 10 + 'px';
    this.milestonePopup.style.top = y + 10 + 'px';

    // Show popup
    this.milestonePopup.classList.add('visible');
  }

  /**
   * Hide milestone popup
   */
  _hideMilestonePopup() {
    if (this.milestonePopup) {
      this.milestonePopup.classList.remove('visible');
    }
  }

  /**
   * Format date for display
   */
  _formatDate(date) {
    const now = new Date();
    const diff = now - date;
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    return 'Just now';
  }

  /**
   * Show loading state
   */
  _showLoading() {
    this.container.innerHTML = `
      <div class="gantt-loading">
        <div class="gantt-loading-spinner"></div>
        <p>Loading Gantt Chart...</p>
      </div>
    `;
  }

  /**
   * Show error state
   */
  _showError(message) {
    this.container.innerHTML = `
      <div class="gantt-empty">
        <i class="bi bi-exclamation-triangle text-danger"></i>
        <h5>Error Loading Gantt Chart</h5>
        <p>${message}</p>
      </div>
    `;
  }

  /**
   * Show empty state
   */
  _showEmpty() {
    this.container.innerHTML = `
      <div class="gantt-empty">
        <i class="bi bi-calendar-x"></i>
        <h5>No Data Available</h5>
        <p>No tasks to display in Gantt Chart</p>
      </div>
    `;
  }

  /**
   * Render Gantt Chart
   */
  render() {
    if (!this.state.initialized) return;

    // Check if data is empty
    if (this.dataModel.getTotalPekerjaanCount() === 0) {
      this._showEmpty();
      return;
    }

    // Render grid
    if (this.gridManager) {
      const flatData = this.dataModel.getFlatData();
      this.gridManager.updateData(flatData);
    }

    // Render canvas overlay
    this._renderBars();
  }

  /**
   * Set mode (planned/actual)
   */
  setMode(mode) {
    if (!['planned', 'actual'].includes(mode)) {
      console.warn('Invalid mode:', mode);
      return;
    }

    this.state.mode = mode;

    // Update canvas overlay mode
    if (this.canvasOverlay) {
      this.canvasOverlay.setMode(mode);
    }

    // Notify StateManager
    if (this.stateManager) {
      this.stateManager.emit('mode:changed', mode);
    }

    console.log(`🔄 Mode changed to: ${mode}`);
  }

  /**
   * Expand all nodes
   */
  expandAll() {
    const allNodes = this.dataModel.getFlatData();
    allNodes.forEach(node => {
      if (!node.isLeaf()) {
        node.expanded = true;
      }
    });
    this.render();
  }

  /**
   * Collapse all nodes
   */
  collapseAll() {
    const allNodes = this.dataModel.getFlatData();
    allNodes.forEach(node => {
      if (!node.isLeaf()) {
        node.expanded = false;
      }
    });
    this.render();
  }

  /**
   * Scroll to node (not implemented in frozen column yet)
   */
  scrollToNode(nodeId) {
    console.warn('scrollToNode not yet implemented in frozen column architecture');
    // TODO: Implement grid row scrolling
  }

  /**
   * Add milestone
   */
  addMilestone(milestoneData) {
    const milestone = this.dataModel.addMilestone(milestoneData);
    this.onMilestoneChange('add', milestone);
    this.render();
    Toast.success('Milestone added');
    return milestone;
  }

  /**
   * Remove milestone
   */
  removeMilestone(milestoneId) {
    this.dataModel.removeMilestone(milestoneId);
    this.onMilestoneChange('remove', milestoneId);
    this.render();
    Toast.success('Milestone removed');
  }

  /**
   * Update data from external source (grid)
   */
  updateData(rawData) {
    console.log('🔄 Updating Gantt data...');

    try {
      this.dataModel.initialize(rawData);

      // Update StateManager
      if (this.stateManager) {
        this.stateManager.updateData(this.dataModel.getFlatData());
      }

      this.render();
      Toast.success('Gantt Chart updated');
    } catch (error) {
      console.error('❌ Failed to update data:', error);
      Toast.error('Failed to update Gantt Chart');
    }
  }

  /**
   * Export data
   */
  exportData() {
    return this.dataModel.toJSON();
  }

  /**
   * Get selected node
   */
  getSelectedNode() {
    return this.dataModel.getNodeById(this.state.selectedNodeId);
  }

  /**
   * Search nodes
   */
  search(searchText) {
    return this.dataModel.searchNodes(searchText);
  }

  /**
   * Destroy Gantt Chart
   */
  destroy() {
    console.log('🗑️ Destroying Gantt Chart...');

    if (this.gridManager) {
      this.gridManager.destroy();
    }

    if (this.canvasOverlay) {
      this.canvasOverlay.destroy();
    }

    if (this.milestonePopup) {
      this.milestonePopup.remove();
    }

    this.container.innerHTML = '';
    this.state.initialized = false;

    console.log('✅ Gantt Chart destroyed');
  }
}

export default GanttChartRedesign;
