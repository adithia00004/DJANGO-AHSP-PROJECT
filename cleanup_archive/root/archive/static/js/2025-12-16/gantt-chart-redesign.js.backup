/**
 * Gantt Chart Redesign - Main Component
 * Orchestrates tree panel, timeline panel, and data synchronization
 * @module gantt-chart-redesign
 */

import { GanttDataModel } from './gantt-data-model.js';
import { GanttTreePanel } from './gantt-tree-panel.js';
import { GanttTimelinePanel } from './gantt-timeline-panel.js';
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
      enableSync: options.enableSync !== false,
      ...options
    };

    // Data model
    this.dataModel = new GanttDataModel();

    // Components
    this.treePanel = null;
    this.timelinePanel = null;

    // State
    this.state = {
      loading: false,
      initialized: false,
      selectedNodeId: null,
      mode: this.options.mode
    };

    // Event callbacks
    this.onDataChange = options.onDataChange || (() => {});
    this.onNodeSelect = options.onNodeSelect || (() => {});
    this.onMilestoneChange = options.onMilestoneChange || (() => {});

    // Milestone popup
    this.milestonePopup = null;
  }

  /**
   * Initialize Gantt Chart
   */
  async initialize(rawData) {
    console.log('🚀 Initializing Gantt Chart Redesign...');
    this.state.loading = true;

    try {
      // Build DOM structure (tree + timeline containers)
      this._buildDOM();

      // Note: Loading spinner already shown in HTML template
      // No need to call _showLoading() which would overwrite the DOM!

      // Initialize data model
      this.dataModel.initialize(rawData);

      // Create components
      await this._createComponents();

      // Setup synchronization
      this._setupSync();

      // Mark as initialized BEFORE rendering
      this.state.loading = false;
      this.state.initialized = true;

      // Initial render (must be after state.initialized = true)
      this.render();

      console.log('✅ Gantt Chart Redesign initialized successfully');
      Toast.success('Gantt Chart loaded successfully');

    } catch (error) {
      console.error('❌ Failed to initialize Gantt Chart:', error);
      this._showError('Failed to initialize Gantt Chart: ' + error.message);
      this.state.loading = false;
      throw error;
    }
  }

  /**
   * Build DOM structure
   */
  _buildDOM() {
    this.container.innerHTML = '';
    this.container.className = 'gantt-container';

    // Create panels
    const treeContainer = document.createElement('div');
    treeContainer.className = 'gantt-tree-panel-container';
    this.container.appendChild(treeContainer);

    const timelineContainer = document.createElement('div');
    timelineContainer.className = 'gantt-timeline-panel-container';
    this.container.appendChild(timelineContainer);

    // Store references
    this.elements = {
      treeContainer,
      timelineContainer
    };
  }

  /**
   * Create components
   */
  async _createComponents() {
    // Create tree panel
    this.treePanel = new GanttTreePanel(
      this.elements.treeContainer,
      this.dataModel,
      {
        mode: this.state.mode,
        onNodeClick: (nodeId) => this._handleNodeClick(nodeId),
        onNodeExpand: (nodeId, expanded) => this._handleNodeExpand(nodeId, expanded),
        onSearchChange: (searchText) => this._handleSearchChange(searchText)
      }
    );

    // Create timeline panel
    this.timelinePanel = new GanttTimelinePanel(
      this.elements.timelineContainer,
      this.dataModel,
      {
        mode: this.state.mode,
        rowHeight: this.options.rowHeight,
        showMilestones: this.options.enableMilestones,
        onBarClick: (node, type, event) => this._handleBarClick(node, type, event),
        onMilestoneClick: (milestone, event) => this._handleMilestoneClick(milestone, event),
        onScroll: (scrollState) => this._handleTimelineScroll(scrollState)
      }
    );

    // Create milestone popup
    this._createMilestonePopup();
  }

  /**
   * Setup synchronization between panels
   */
  _setupSync() {
    if (!this.options.enableSync) return;

    // Sync scroll between tree and timeline
    let treeScrolling = false;
    let timelineScrolling = false;

    // Tree scroll -> Timeline scroll
    this.treePanel.elements.treeContent.addEventListener('scroll', () => {
      if (timelineScrolling) return;
      treeScrolling = true;

      const scrollTop = this.treePanel.getScrollTop();
      this.timelinePanel.syncScrollY(scrollTop);

      setTimeout(() => { treeScrolling = false; }, 50);
    });

    // Timeline scroll -> Tree scroll
    this.timelinePanel.elements.content.addEventListener('scroll', () => {
      if (treeScrolling) return;
      timelineScrolling = true;

      const scrollTop = this.timelinePanel.elements.content.scrollTop;
      this.treePanel.setScrollTop(scrollTop);

      setTimeout(() => { timelineScrolling = false; }, 50);
    });
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

    // Highlight in timeline (future enhancement)
  }

  /**
   * Handle node expand/collapse
   */
  _handleNodeExpand(nodeId, expanded) {
    console.log(`${expanded ? '📂' : '📁'} Node ${expanded ? 'expanded' : 'collapsed'}:`, nodeId);

    // Re-render both panels
    this.render();
  }

  /**
   * Handle search change
   */
  _handleSearchChange(searchText) {
    console.log('🔍 Search:', searchText);

    // Future: Highlight matching nodes in timeline
  }

  /**
   * Handle bar click
   */
  _handleBarClick(node, type, event) {
    console.log(`📊 Bar clicked: ${node.name} (${type})`);

    // Select the node
    this._handleNodeClick(node.id);

    // Show bar details (future enhancement)
    Toast.info(`${node.name}: ${type === 'planned' ? 'Planned' : 'Actual'} - ${type === 'planned' ? node.planned.progress : node.actual.progress}%`);
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
   * Handle timeline scroll
   */
  _handleTimelineScroll(scrollState) {
    // Future: Update visible date range indicator
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

    // Render both panels
    this.treePanel.render();
    this.timelinePanel.render();
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

    if (this.treePanel) {
      this.treePanel.setMode(mode);
    }

    if (this.timelinePanel) {
      this.timelinePanel.setMode(mode);
    }

    console.log(`🔄 Mode changed to: ${mode}`);
  }

  /**
   * Expand all nodes
   */
  expandAll() {
    if (this.treePanel) {
      this.treePanel.expandAll();
      this.render();
    }
  }

  /**
   * Collapse all nodes
   */
  collapseAll() {
    if (this.treePanel) {
      this.treePanel.collapseAll();
      this.render();
    }
  }

  /**
   * Scroll to node
   */
  scrollToNode(nodeId) {
    if (this.treePanel) {
      this.treePanel.scrollToNode(nodeId);
    }
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

    if (this.treePanel) {
      this.treePanel.destroy();
    }

    if (this.timelinePanel) {
      this.timelinePanel.destroy();
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
