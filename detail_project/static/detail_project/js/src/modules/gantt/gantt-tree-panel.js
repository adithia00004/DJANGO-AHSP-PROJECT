/**
 * Gantt Tree Panel Component
 * Displays hierarchical tree with expand/collapse functionality
 * @module gantt-tree-panel
 */

import { debounce } from '@modules/shared/ux-enhancements.js';

/**
 * Tree Panel Component
 */
export class GanttTreePanel {
  constructor(container, dataModel, options = {}) {
    this.container = container;
    this.dataModel = dataModel;

    // Options
    this.options = {
      width: options.width || '30%',
      minWidth: options.minWidth || 250,
      maxWidth: options.maxWidth || 500,
      showSearch: options.showSearch !== false,
      showStats: options.showStats !== false,
      mode: options.mode || 'planned', // 'planned' or 'actual'
      ...options
    };

    // State
    this.state = {
      searchText: '',
      selectedNodeId: null,
      hoveredNodeId: null,
      scrollTop: 0
    };

    // Event callbacks
    this.onNodeClick = options.onNodeClick || (() => {});
    this.onNodeExpand = options.onNodeExpand || (() => {});
    this.onSearchChange = options.onSearchChange || (() => {});

    // DOM elements
    this.elements = {};

    this.init();
  }

  /**
   * Initialize tree panel
   */
  init() {
    console.log('🌳 Initializing Tree Panel...');
    this._buildDOM();
    this._attachEventListeners();
    this.render();
    console.log('✅ Tree Panel initialized');
  }

  /**
   * Build DOM structure
   */
  _buildDOM() {
    this.container.innerHTML = '';
    this.container.className = 'gantt-tree-panel';

    // ALIGNMENT FIX: Add header spacer to match timeline header height
    // Timeline has toolbar (~48px) + scale (60px) = ~108px total
    const headerSpacer = document.createElement('div');
    headerSpacer.className = 'tree-header-spacer';
    headerSpacer.innerHTML = `
      <div class="tree-toolbar-spacer" style="height: 48px; padding: 0.75rem 1rem; display: flex; align-items: center; border-bottom: 1px solid var(--bs-border-color); background: var(--bs-light);">
        <input type="text" class="tree-search-input form-control form-control-sm" placeholder="Search tasks..." style="max-width: 200px;">
      </div>
      <div class="tree-scale-spacer" style="height: 60px; border-bottom: 1px solid var(--bs-border-color); background: var(--bs-light);"></div>
    `;
    this.container.appendChild(headerSpacer);
    this.elements.searchInput = headerSpacer.querySelector('.tree-search-input');

    // Tree content (scrollable)
    const treeContent = document.createElement('div');
    treeContent.className = 'tree-content';
    this.container.appendChild(treeContent);
    this.elements.treeContent = treeContent;

    // Resize handle
    const resizeHandle = document.createElement('div');
    resizeHandle.className = 'tree-resize-handle';
    resizeHandle.setAttribute('aria-label', 'Resize tree panel');
    this.container.appendChild(resizeHandle);
    this.elements.resizeHandle = resizeHandle;
  }

  /**
   * Attach event listeners
   */
  _attachEventListeners() {
    // Search
    if (this.elements.searchInput) {
      const debouncedSearch = debounce((value) => {
        this.state.searchText = value;
        this.onSearchChange(value);
        this.render();
      }, 300);

      this.elements.searchInput.addEventListener('input', (e) => {
        debouncedSearch(e.target.value);
      });
    }

    // Tree content events (delegated)
    this.elements.treeContent.addEventListener('click', (e) => {
      this._handleTreeClick(e);
    });

    this.elements.treeContent.addEventListener('mouseenter', (e) => {
      if (e.target.classList.contains('tree-node-row')) {
        const nodeId = e.target.dataset.nodeId;
        this.state.hoveredNodeId = nodeId;
        this._highlightRow(nodeId);
      }
    }, true);

    this.elements.treeContent.addEventListener('mouseleave', (e) => {
      if (e.target.classList.contains('tree-node-row')) {
        this.state.hoveredNodeId = null;
        this._unhighlightRow(e.target.dataset.nodeId);
      }
    }, true);

    // Resize handle
    this._setupResizeHandle();

    // Scroll sync
    this.elements.treeContent.addEventListener('scroll', () => {
      this.state.scrollTop = this.elements.treeContent.scrollTop;
    });
  }

  /**
   * Handle tree click events
   */
  _handleTreeClick(e) {
    const target = e.target;

    // Expand/collapse button (check both button and icon inside button)
    const expandBtn = target.classList.contains('tree-expand-btn')
      ? target
      : target.closest('.tree-expand-btn');

    if (expandBtn) {
      const nodeId = expandBtn.closest('.tree-node-row').dataset.nodeId;
      this._toggleNode(nodeId);
      e.stopPropagation(); // Prevent node selection
      return;
    }

    // Node row click
    if (target.classList.contains('tree-node-row') || target.closest('.tree-node-row')) {
      const row = target.classList.contains('tree-node-row')
        ? target
        : target.closest('.tree-node-row');

      const nodeId = row.dataset.nodeId;
      this._selectNode(nodeId);
      return;
    }
  }

  /**
   * Toggle node expand/collapse
   */
  _toggleNode(nodeId) {
    const expanded = this.dataModel.toggleNode(nodeId);
    this.onNodeExpand(nodeId, expanded);
    this.render();
  }

  /**
   * Select node
   */
  _selectNode(nodeId) {
    this.state.selectedNodeId = nodeId;
    this.onNodeClick(nodeId);
    this.render();
  }

  /**
   * Highlight row on hover
   */
  _highlightRow(nodeId) {
    const row = this.elements.treeContent.querySelector(`[data-node-id="${nodeId}"]`);
    if (row) {
      row.classList.add('hovered');
    }
  }

  /**
   * Unhighlight row
   */
  _unhighlightRow(nodeId) {
    const row = this.elements.treeContent.querySelector(`[data-node-id="${nodeId}"]`);
    if (row) {
      row.classList.remove('hovered');
    }
  }

  /**
   * Setup resize handle
   */
  _setupResizeHandle() {
    let isResizing = false;
    let startX = 0;
    let startWidth = 0;

    this.elements.resizeHandle.addEventListener('mousedown', (e) => {
      isResizing = true;
      startX = e.clientX;
      startWidth = this.container.offsetWidth;
      document.body.style.cursor = 'col-resize';
      e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
      if (!isResizing) return;

      const delta = e.clientX - startX;
      const newWidth = startWidth + delta;

      // Constrain width
      if (newWidth >= this.options.minWidth && newWidth <= this.options.maxWidth) {
        this.container.style.width = newWidth + 'px';
      }
    });

    document.addEventListener('mouseup', () => {
      if (isResizing) {
        isResizing = false;
        document.body.style.cursor = '';
      }
    });
  }

  /**
   * Render tree panel
   */
  render() {
    // Render stats
    if (this.elements.statsBar) {
      this._renderStats();
    }

    // Render tree
    this._renderTree();
  }

  /**
   * Render stats bar
   */
  _renderStats() {
    const total = this.dataModel.getTotalPekerjaanCount();
    const klasifikasiCount = this.dataModel.klasifikasi.length;

    // Calculate overall progress
    let totalProgress = 0;
    let count = 0;

    this.dataModel.klasifikasi.forEach(klas => {
      const progress = klas.getAggregatedProgress(this.options.mode);
      if (progress > 0) {
        totalProgress += progress;
        count++;
      }
    });

    const avgProgress = count > 0 ? Math.round(totalProgress / count) : 0;

    this.elements.statsBar.innerHTML = `
      <div class="tree-stat">
        <i class="bi bi-diagram-3"></i>
        <span>${klasifikasiCount} Categories</span>
      </div>
      <div class="tree-stat">
        <i class="bi bi-list-check"></i>
        <span>${total} Tasks</span>
      </div>
      <div class="tree-stat">
        <i class="bi bi-graph-up"></i>
        <span>${avgProgress}% Complete</span>
      </div>
    `;
  }

  /**
   * Render tree nodes - FIX 10: No elimination, only highlight
   */
  _renderTree() {
    const nodes = this.dataModel.getFlattenedTree();

    // Render ALL nodes (no filtering/elimination)
    // Search text will be highlighted via _highlightSearch()
    const html = nodes.map(node => this._renderNode(node)).join('');

    this.elements.treeContent.innerHTML = html;

    // Restore scroll position
    this.elements.treeContent.scrollTop = this.state.scrollTop;
  }

  /**
   * Filter nodes by search text
   */
  _filterNodesBySearch(nodes) {
    const searchLower = this.state.searchText.toLowerCase();
    return nodes.filter(node => {
      return node.name.toLowerCase().includes(searchLower) ||
             node.kode.toLowerCase().includes(searchLower);
    });
  }

  /**
   * Render single node
   */
  _renderNode(node) {
    const isSelected = this.state.selectedNodeId === node.id;
    const indent = (node.level - 1) * 20; // 20px per level

    let icon = '';
    let expandBtn = '';
    let progressBadge = '';

    // Icon based on type
    switch (node.type) {
      case 'klasifikasi':
        icon = '<i class="bi bi-folder2"></i>';
        break;
      case 'sub-klasifikasi':
        icon = '<i class="bi bi-folder"></i>';
        break;
      case 'pekerjaan':
        icon = this._getStatusIcon(node.status);
        break;
    }

    // Expand button - DISABLED for alignment priority
    // Toggle expand/collapse removed to maintain perfect alignment
    // All nodes shown flat
    expandBtn = '<span class="tree-expand-spacer"></span>';

    // Progress badge for parent nodes
    if (node.type !== 'pekerjaan') {
      const progress = node.getAggregatedProgress(this.options.mode);
      const progressClass = this._getProgressClass(progress);
      progressBadge = `
        <span class="tree-progress-badge ${progressClass}">
          ${progress}%
        </span>
      `;
    } else {
      // Status badge for pekerjaan
      const progress = this.options.mode === 'planned'
        ? node.planned.progress
        : node.actual.progress;
      const progressClass = this._getProgressClass(progress);
      progressBadge = `
        <span class="tree-progress-badge ${progressClass}">
          ${progress}%
        </span>
      `;
    }

    return `
      <div
        class="tree-node-row level-${node.level} ${isSelected ? 'selected' : ''} ${node.type}"
        data-node-id="${node.id}"
        data-node-type="${node.type}"
        style="padding-left: ${indent}px"
      >
        ${expandBtn}
        <span class="tree-node-icon">${icon}</span>
        <span class="tree-node-label">
          ${node.kode ? `<span class="tree-node-kode">${node.kode}</span>` : ''}
          <span class="tree-node-name">${this._highlightSearch(node.name)}</span>
        </span>
        ${progressBadge}
      </div>
    `;
  }

  /**
   * Get status icon for pekerjaan
   */
  _getStatusIcon(status) {
    const icons = {
      'not-started': '<i class="bi bi-circle text-muted"></i>',
      'in-progress': '<i class="bi bi-play-circle text-primary"></i>',
      'complete': '<i class="bi bi-check-circle text-success"></i>',
      'delayed': '<i class="bi bi-exclamation-circle text-danger"></i>'
    };
    return icons[status] || icons['not-started'];
  }

  /**
   * Get progress class based on percentage
   */
  _getProgressClass(progress) {
    if (progress === 0) return 'progress-none';
    if (progress < 25) return 'progress-low';
    if (progress < 50) return 'progress-medium';
    if (progress < 75) return 'progress-high';
    if (progress < 100) return 'progress-very-high';
    return 'progress-complete';
  }

  /**
   * Highlight search text in string
   */
  _highlightSearch(text) {
    if (!this.state.searchText) return text;

    const regex = new RegExp(`(${this.state.searchText})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
  }

  /**
   * Update mode (planned/actual)
   */
  setMode(mode) {
    this.options.mode = mode;
    this.render();
  }

  /**
   * Scroll to node
   */
  scrollToNode(nodeId) {
    const row = this.elements.treeContent.querySelector(`[data-node-id="${nodeId}"]`);
    if (row) {
      row.scrollIntoView({ behavior: 'smooth', block: 'center' });
      this._selectNode(nodeId);
    }
  }

  /**
   * Expand all nodes
   */
  expandAll() {
    this.dataModel.klasifikasi.forEach(klas => {
      klas.expanded = true;
      klas.getSubKlasifikasi().forEach(sub => {
        sub.expanded = true;
      });
    });
    this.render();
  }

  /**
   * Collapse all nodes
   */
  collapseAll() {
    this.dataModel.klasifikasi.forEach(klas => {
      klas.expanded = false;
    });
    this.render();
  }

  /**
   * Get selected node
   */
  getSelectedNode() {
    return this.dataModel.getNodeById(this.state.selectedNodeId);
  }

  /**
   * Get scroll top
   */
  getScrollTop() {
    return this.state.scrollTop;
  }

  /**
   * Set scroll top
   */
  setScrollTop(scrollTop) {
    this.state.scrollTop = scrollTop;
    this.elements.treeContent.scrollTop = scrollTop;
  }

  /**
   * Destroy tree panel
   */
  destroy() {
    this.container.innerHTML = '';
    console.log('🗑️ Tree Panel destroyed');
  }
}

export default GanttTreePanel;
