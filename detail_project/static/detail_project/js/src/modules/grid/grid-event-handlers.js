/**
 * Grid Event Handlers Module (Refactored with Event Delegation)
 * Fixes memory leaks by using event delegation pattern
 * License: MIT
 */

import { EventDelegationManager, cleanupEventListeners } from '@shared/event-delegation.js';
import { rafThrottle } from '@shared/performance-utils.js';
import { handleCellValidation } from '@shared/validation-utils.js';

/**
 * Grid Event Manager
 * Manages all grid events using efficient delegation pattern
 */
export class GridEventManager {
  constructor(state, helpers) {
    this.state = state;
    this.helpers = helpers;
    this.eventManagers = new Map();
    this.scrollHandlers = new Map();
  }

  /**
   * Attaches all grid event listeners using delegation
   */
  attachEvents() {
    const leftTbody = this.state.domRefs?.leftTbody || document.getElementById('left-tbody');
    const rightTbody = this.state.domRefs?.rightTbody || document.getElementById('right-tbody');
    const leftScroll = this.state.domRefs?.leftPanelScroll || document.querySelector('.left-panel-scroll');
    const rightScroll = this.state.domRefs?.rightPanelScroll || document.querySelector('.right-panel-scroll');

    if (!leftTbody || !rightTbody) {
      console.error('Grid containers not found');
      return false;
    }

    // Clean up any existing listeners
    this.cleanup();

    // Setup left panel events (tree toggles, expand/collapse)
    this._setupLeftPanelEvents(leftTbody);

    // Setup right panel events (cell editing)
    this._setupRightPanelEvents(rightTbody);

    // Setup scroll synchronization
    if (leftScroll && rightScroll) {
      this._setupScrollSync(leftScroll, rightScroll);
    }

    const topHorizontalScroll =
      this.state.domRefs?.horizontalScrollTop || document.getElementById('right-panel-scroll-top');
    if (topHorizontalScroll && rightScroll) {
      this._setupHorizontalScrollSync(topHorizontalScroll, rightScroll);
    }

    return true;
  }

  /**
   * Setup left panel event delegation
   */
  _setupLeftPanelEvents(container) {
    const leftManager = new EventDelegationManager(container);

    // Tree toggle clicks
    leftManager.on('click', '.tree-toggle', (event, target) => {
      this._handleTreeToggle(event, target);
    });

    // Row selection (optional feature)
    leftManager.on('click', '.name-cell', (event, target) => {
      this._handleRowSelection(event, target);
    });

    this.eventManagers.set('left-panel', leftManager);
  }

  /**
   * Setup right panel event delegation (cell editing)
   */
  _setupRightPanelEvents(container) {
    const rightManager = new EventDelegationManager(container);

    // Cell click (single click - select)
    rightManager.on('click', '.time-cell.editable', (event, target) => {
      this._handleCellClick(event, target);
    });

    // Cell double-click (enter edit mode)
    rightManager.on('dblclick', '.time-cell.editable', (event, target) => {
      this._handleCellDoubleClick(event, target);
    });

    // Input events on cell inputs (with validation)
    rightManager.on('input', '.time-cell input', (event, target) => {
      this._handleCellInput(event, target);
    });

    // Blur events (validate and save)
    rightManager.on('blur', '.time-cell input', (event, target) => {
      this._handleCellBlur(event, target);
    });

    // Keydown events (Enter, Escape, Tab navigation)
    rightManager.on('keydown', '.time-cell input', (event, target) => {
      this._handleCellKeydown(event, target);
    });

    this.eventManagers.set('right-panel', rightManager);
  }

  /**
   * Setup scroll synchronization with RAF throttle for performance
   */
  _setupScrollSync(leftScroll, rightScroll) {
    // Throttle scroll events to 60fps using requestAnimationFrame
    const syncLeftToRight = rafThrottle(() => {
      rightScroll.scrollTop = leftScroll.scrollTop;
    });

    const syncRightToLeft = rafThrottle(() => {
      leftScroll.scrollTop = rightScroll.scrollTop;
    });

    // Attach scroll listeners
    leftScroll.addEventListener('scroll', syncLeftToRight, { passive: true });
    rightScroll.addEventListener('scroll', syncRightToLeft, { passive: true });

    // Store handlers for cleanup
    this.scrollHandlers.set('left', { element: leftScroll, handler: syncLeftToRight });
    this.scrollHandlers.set('right', { element: rightScroll, handler: syncRightToLeft });
  }

  _setupHorizontalScrollSync(topScroll, bottomScroll) {
    const syncTopToBottom = rafThrottle(() => {
      bottomScroll.scrollLeft = topScroll.scrollLeft;
    });

    const syncBottomToTop = rafThrottle(() => {
      topScroll.scrollLeft = bottomScroll.scrollLeft;
    });

    topScroll.addEventListener('scroll', syncTopToBottom, { passive: true });
    bottomScroll.addEventListener('scroll', syncBottomToTop, { passive: true });

    this.scrollHandlers.set('horizontal-top', { element: topScroll, handler: syncTopToBottom });
    this.scrollHandlers.set('horizontal-bottom', { element: bottomScroll, handler: syncBottomToTop });
  }

  /**
   * Handle tree toggle click
   */
  _handleTreeToggle(event, toggleElement) {
    event.stopPropagation();

    const nodeId = toggleElement.dataset.nodeId;
    const isExpanded = !toggleElement.classList.contains('collapsed');

    // Update state
    if (isExpanded) {
      this.state.expandedNodes.delete(nodeId);
      toggleElement.classList.add('collapsed');
    } else {
      this.state.expandedNodes.add(nodeId);
      toggleElement.classList.remove('collapsed');
    }

    // Toggle child rows
    this._toggleNodeChildren(nodeId, !isExpanded);

    // Sync row heights after DOM update
    requestAnimationFrame(() => {
      this._syncRowHeights();
    });
  }

  /**
   * Toggle visibility of child rows
   */
  _toggleNodeChildren(nodeId, show) {
    const leftBody = this.state.domRefs?.leftTbody || document.getElementById('left-tbody');
    const rightBody = this.state.domRefs?.rightTbody || document.getElementById('right-tbody');

    const selector = `[data-parent-id="${nodeId}"]`;
    const leftChildren = leftBody.querySelectorAll(selector);
    const rightChildren = rightBody.querySelectorAll(selector);

    const display = show ? '' : 'none';

    leftChildren.forEach((row) => {
      row.style.display = display;

      // Recursively hide/show descendants if this node is collapsed
      if (!show) {
        const childId = row.dataset.nodeId;
        if (childId) {
          this._toggleNodeChildren(childId, false);
        }
      }
    });

    rightChildren.forEach((row) => {
      row.style.display = display;
    });
  }

  /**
   * Handle row selection (optional feature)
   */
  _handleRowSelection(event, cellElement) {
    const row = cellElement.closest('tr');
    if (!row) return;

    // Toggle selected state
    row.classList.toggle('row-selected');

    // Sync with right panel
    const rowIndex = row.dataset.rowIndex;
    if (rowIndex) {
      const rightRow = document.querySelector(
        `.right-panel-scroll tr[data-row-index="${rowIndex}"]`
      );
      if (rightRow) {
        rightRow.classList.toggle('row-selected');
      }
    }
  }

  /**
   * Handle cell click (select cell)
   */
  _handleCellClick(event, cellElement) {
    // Remove selection from other cells
    document.querySelectorAll('.time-cell.selected').forEach((cell) => {
      cell.classList.remove('selected');
    });

    // Select this cell
    cellElement.classList.add('selected');
  }

  /**
   * Handle cell double-click (enter edit mode)
   */
  _handleCellDoubleClick(event, cellElement) {
    event.preventDefault();

    // Check if already in edit mode
    if (cellElement.classList.contains('editing')) {
      return;
    }

    // Enter edit mode
    this._enterEditMode(cellElement);
  }

  /**
   * Enter edit mode for a cell
   */
  _enterEditMode(cellElement) {
    const currentValue = cellElement.dataset.value || '0';

    // Create input element
    const input = document.createElement('input');
    input.type = 'number';
    input.className = 'cell-input';
    input.value = currentValue;
    input.min = '0';
    input.max = '100';
    input.step = '0.1';

    // Clear cell and add input
    cellElement.innerHTML = '';
    cellElement.appendChild(input);
    cellElement.classList.add('editing');

    // Focus and select
    input.focus();
    input.select();
  }

  /**
   * Handle cell input (real-time validation)
   */
  _handleCellInput(event, inputElement) {
    const cellElement = inputElement.closest('.time-cell');
    if (!cellElement) return;

    // Real-time validation is handled on blur to avoid performance issues
    // But we can add visual feedback for obviously invalid input
    const value = parseFloat(inputElement.value);

    if (!isNaN(value)) {
      if (value < 0 || value > 100) {
        cellElement.classList.add('validation-warning');
      } else {
        cellElement.classList.remove('validation-warning');
      }
    }
  }

  /**
   * Handle cell blur (validate and save)
   */
  _handleCellBlur(event, inputElement) {
    const cellElement = inputElement.closest('.time-cell');
    if (!cellElement) return;

    // Validate the input
    const validationResult = handleCellValidation(event, cellElement, this.state);

    // Exit edit mode
    this._exitEditMode(cellElement, validationResult.value);

    // Update state
    const cellKey = cellElement.dataset.cellId;
    if (cellKey) {
      this.state.modifiedCells = this.state.modifiedCells || new Map();
      this.state.modifiedCells.set(cellKey, validationResult.value);

      // Mark as dirty
      this.state.isDirty = true;

      // Calculate and update total progress for this pekerjaan
      const [pekerjaanId] = cellKey.split('-');
      this._updatePekerjaanProgress(pekerjaanId);
    }
  }

  /**
   * Exit edit mode and restore cell display
   */
  _exitEditMode(cellElement, value) {
    cellElement.classList.remove('editing');
    cellElement.dataset.value = value;

    // Restore display
    const formattedValue = value === 0 ? '-' : `${value}%`;
    cellElement.innerHTML = `<span class="cell-value">${formattedValue}</span>`;
  }

  /**
   * Handle keyboard navigation in cells
   */
  _handleCellKeydown(event, inputElement) {
    const cellElement = inputElement.closest('.time-cell');
    if (!cellElement) return;

    switch (event.key) {
      case 'Enter':
        event.preventDefault();
        inputElement.blur(); // Will trigger blur handler
        this._navigateToNextCell(cellElement, 'down');
        break;

      case 'Escape':
        event.preventDefault();
        // Restore original value
        const originalValue = cellElement.dataset.originalValue || '0';
        inputElement.value = originalValue;
        inputElement.blur();
        break;

      case 'Tab':
        event.preventDefault();
        inputElement.blur();
        const direction = event.shiftKey ? 'left' : 'right';
        this._navigateToNextCell(cellElement, direction);
        break;

      case 'ArrowUp':
        if (event.ctrlKey) {
          event.preventDefault();
          inputElement.blur();
          this._navigateToNextCell(cellElement, 'up');
        }
        break;

      case 'ArrowDown':
        if (event.ctrlKey) {
          event.preventDefault();
          inputElement.blur();
          this._navigateToNextCell(cellElement, 'down');
        }
        break;
    }
  }

  /**
   * Navigate to next cell (keyboard navigation)
   */
  _navigateToNextCell(currentCell, direction) {
    const row = currentCell.closest('tr');
    if (!row) return;

    let nextCell = null;

    switch (direction) {
      case 'right':
        nextCell = currentCell.nextElementSibling;
        while (nextCell && !nextCell.classList.contains('editable')) {
          nextCell = nextCell.nextElementSibling;
        }
        break;

      case 'left':
        nextCell = currentCell.previousElementSibling;
        while (nextCell && !nextCell.classList.contains('editable')) {
          nextCell = nextCell.previousElementSibling;
        }
        break;

      case 'down':
        const nextRow = row.nextElementSibling;
        if (nextRow) {
          const cellIndex = Array.from(row.children).indexOf(currentCell);
          nextCell = nextRow.children[cellIndex];
        }
        break;

      case 'up':
        const prevRow = row.previousElementSibling;
        if (prevRow) {
          const cellIndex = Array.from(row.children).indexOf(currentCell);
          nextCell = prevRow.children[cellIndex];
        }
        break;
    }

    if (nextCell && nextCell.classList.contains('editable')) {
      this._enterEditMode(nextCell);
    }
  }

  /**
   * Update total progress for a pekerjaan
   */
  _updatePekerjaanProgress(pekerjaanId) {
    const modifiedCells = this.state.modifiedCells || new Map();
    const timeColumns = this.state.timeColumns || [];

    let total = 0;

    timeColumns.forEach((col) => {
      const cellKey = `${pekerjaanId}-${col.id}`;
      const value = modifiedCells.get(cellKey) || 0;
      total += parseFloat(value) || 0;
    });

    // Update progress indicator (if validation-utils is available)
    if (typeof this.helpers.updateProgressIndicator === 'function') {
      this.helpers.updateProgressIndicator(pekerjaanId, total);
    }
  }

  /**
   * Sync row heights between left and right panels
   */
  _syncRowHeights() {
    const leftBody = this.state.domRefs?.leftTbody || document.getElementById('left-tbody');
    const rightBody = this.state.domRefs?.rightTbody || document.getElementById('right-tbody');

    if (!leftBody || !rightBody) return;

    const leftRows = leftBody.querySelectorAll('tr');
    const rightRows = rightBody.querySelectorAll('tr');

    leftRows.forEach((leftRow, index) => {
      const rightRow = rightRows[index];
      if (!rightRow) return;

      // Reset heights
      leftRow.style.height = '';
      rightRow.style.height = '';

      // Get natural heights
      const leftHeight = leftRow.offsetHeight;
      const rightHeight = rightRow.offsetHeight;

      // Set to max
      const maxHeight = Math.max(leftHeight, rightHeight);
      leftRow.style.height = `${maxHeight}px`;
      rightRow.style.height = `${maxHeight}px`;
    });
  }

  /**
   * Clean up all event listeners
   */
  cleanup() {
    // Clean up event delegation managers
    for (const manager of this.eventManagers.values()) {
      manager.destroy();
    }
    this.eventManagers.clear();

    // Clean up scroll handlers
    for (const { element, handler } of this.scrollHandlers.values()) {
      if (handler.cancel) {
        handler.cancel();
      }
      element.removeEventListener('scroll', handler);
    }
    this.scrollHandlers.clear();
  }
}

/**
 * Factory function to create and attach grid events
 *
 * @param {Object} state - Application state
 * @param {Object} helpers - Helper functions
 * @returns {GridEventManager} Event manager instance
 *
 * @example
 * const eventManager = attachGridEvents(state, {
 *   updateProgressIndicator: (id, total) => { ... },
 *   showToast: (msg, type) => { ... },
 * });
 *
 * // Later, cleanup:
 * eventManager.cleanup();
 */
export function attachGridEvents(state, helpers = {}) {
  const manager = new GridEventManager(state, helpers);
  manager.attachEvents();
  return manager;
}
