/**
 * UndoManager - Manages undo/redo operations for state changes
 *
 * Provides:
 * - Undo/Redo stack (configurable size)
 * - Integration with StateManager
 * - Keyboard shortcuts (Ctrl+Z, Ctrl+Y)
 * - State change listeners
 *
 * @module UndoManager
 */

import { createLogger } from '@modules/shared/logger.js';

const logger = createLogger('UndoManager');

/**
 * UndoManager - Handles undo/redo operations with 5-level stack
 *
 * @class UndoManager
 * @example
 * const undoManager = new UndoManager(stateManager, { maxSize: 5 });
 * undoManager.recordChange('cell-edit', oldValue, newValue);
 * undoManager.undo();
 * undoManager.redo();
 */
export class UndoManager {
  /**
   * Create a new UndoManager instance
   * @param {Object} stateManager - StateManager instance
   * @param {Object} options - Configuration options
   * @param {number} [options.maxSize=5] - Maximum stack size (default: 5 levels)
   */
  constructor(stateManager, options = {}) {
    this.stateManager = stateManager;
    this.maxSize = options.maxSize || 5;

    /**
     * Undo stack (stores past states)
     * @type {Array<Object>}
     */
    this.undoStack = [];

    /**
     * Redo stack (stores future states)
     * @type {Array<Object>}
     */
    this.redoStack = [];

    /**
     * Event listeners for stack changes
     * @type {Set<Function>}
     */
    this.listeners = new Set();

    /**
     * Flag to prevent recording during undo/redo
     * @type {boolean}
     */
    this._isUndoRedoing = false;

    logger.info(`Initialized with max ${this.maxSize} levels`);
  }

  /**
   * Record a state change
   *
   * @param {string} type - Change type ('cell-edit', 'bulk-edit', 'delete', etc.)
   * @param {any} before - State before change
   * @param {any} after - State after change
   * @param {Object} metadata - Additional metadata
   *
   * @example
   * undoManager.recordChange('cell-edit', {
   *   cellKey: '123-col_1',
   *   oldValue: 50,
   *   newValue: 75
   * });
   */
  recordChange(type, before, after, metadata = {}) {
    // Skip recording during undo/redo operations
    if (this._isUndoRedoing) {
      return;
    }

    const change = {
      type,
      before,
      after,
      metadata,
      timestamp: Date.now(),
      mode: this.stateManager.currentMode
    };

    // Add to undo stack
    this.undoStack.push(change);

    // Limit stack size
    if (this.undoStack.length > this.maxSize) {
      this.undoStack.shift(); // Remove oldest
    }

    // Clear redo stack (new action invalidates future)
    this.redoStack = [];

    logger.debug(`Recorded ${type} change`, { stackSize: this.undoStack.length });
    this._notifyListeners();
  }

  /**
   * Undo last change
   * @returns {boolean} True if undo was performed
   */
  undo() {
    if (!this.canUndo()) {
      logger.warn('Cannot undo: stack is empty');
      return false;
    }

    this._isUndoRedoing = true;

    try {
      const change = this.undoStack.pop();
      logger.info(`Undoing ${change.type}`, change);

      // Switch to correct mode if needed
      if (change.mode !== this.stateManager.currentMode) {
        this.stateManager.switchMode(change.mode);
      }

      // Apply the before state
      this._applyChange(change.before, change.type);

      // Move to redo stack
      this.redoStack.push(change);

      // Limit redo stack size
      if (this.redoStack.length > this.maxSize) {
        this.redoStack.shift();
      }

      this._notifyListeners();
      return true;

    } finally {
      this._isUndoRedoing = false;
    }
  }

  /**
   * Redo last undone change
   * @returns {boolean} True if redo was performed
   */
  redo() {
    if (!this.canRedo()) {
      logger.warn('Cannot redo: stack is empty');
      return false;
    }

    this._isUndoRedoing = true;

    try {
      const change = this.redoStack.pop();
      logger.info(`Redoing ${change.type}`, change);

      // Switch to correct mode if needed
      if (change.mode !== this.stateManager.currentMode) {
        this.stateManager.switchMode(change.mode);
      }

      // Apply the after state
      this._applyChange(change.after, change.type);

      // Move back to undo stack
      this.undoStack.push(change);

      this._notifyListeners();
      return true;

    } finally {
      this._isUndoRedoing = false;
    }
  }

  /**
   * Check if undo is available
   * @returns {boolean} True if can undo
   */
  canUndo() {
    return this.undoStack.length > 0;
  }

  /**
   * Check if redo is available
   * @returns {boolean} True if can redo
   */
  canRedo() {
    return this.redoStack.length > 0;
  }

  /**
   * Clear all undo/redo history
   */
  clear() {
    this.undoStack = [];
    this.redoStack = [];
    logger.info('Cleared undo/redo history');
    this._notifyListeners();
  }

  /**
   * Clear stacks after successful save
   * (saved changes become the new baseline)
   */
  clearAfterSave() {
    this.clear();
    logger.debug('Cleared after save');
  }

  /**
   * Add event listener for stack changes
   * @param {Function} callback - Listener callback
   */
  addEventListener(callback) {
    if (typeof callback === 'function') {
      this.listeners.add(callback);
    }
  }

  /**
   * Remove event listener
   * @param {Function} callback - Listener callback
   */
  removeEventListener(callback) {
    this.listeners.delete(callback);
  }

  /**
   * Get current stack info
   * @returns {Object} Stack information
   */
  getInfo() {
    return {
      undoCount: this.undoStack.length,
      redoCount: this.redoStack.length,
      canUndo: this.canUndo(),
      canRedo: this.canRedo(),
      maxSize: this.maxSize
    };
  }

  /**
   * Apply a change to StateManager
   * @private
   * @param {any} changeData - Change data
   * @param {string} type - Change type
   */
  _applyChange(changeData, type) {
    if (type === 'cell-edit' && changeData.cellKey) {
      // Single cell edit
      const [pekerjaanId, columnId] = changeData.cellKey.split('-');
      this.stateManager.setCellValue(pekerjaanId, columnId, changeData.value);

    } else if (type === 'bulk-edit' && Array.isArray(changeData.cells)) {
      // Bulk cell edit
      changeData.cells.forEach(({ cellKey, value }) => {
        const [pekerjaanId, columnId] = cellKey.split('-');
        this.stateManager.setCellValue(pekerjaanId, columnId, value);
      });

    } else {
      logger.warn(`Unknown change type: ${type}`);
    }
  }

  /**
   * Notify all listeners of stack change
   * @private
   */
  _notifyListeners() {
    const info = this.getInfo();
    this.listeners.forEach(callback => {
      try {
        callback(info);
      } catch (error) {
        logger.error('Listener error', error);
      }
    });
  }
}

/**
 * Helper function to record cell edit
 * @param {UndoManager} undoManager - UndoManager instance
 * @param {string} cellKey - Cell key (e.g., "123-col_1")
 * @param {number} oldValue - Old value
 * @param {number} newValue - New value
 */
export function recordCellEdit(undoManager, cellKey, oldValue, newValue) {
  undoManager.recordChange('cell-edit', {
    cellKey,
    value: oldValue
  }, {
    cellKey,
    value: newValue
  });
}

/**
 * Helper function to record bulk edit
 * @param {UndoManager} undoManager - UndoManager instance
 * @param {Array<Object>} changes - Array of { cellKey, oldValue, newValue }
 */
export function recordBulkEdit(undoManager, changes) {
  undoManager.recordChange('bulk-edit', {
    cells: changes.map(c => ({ cellKey: c.cellKey, value: c.oldValue }))
  }, {
    cells: changes.map(c => ({ cellKey: c.cellKey, value: c.newValue }))
  });
}

export default UndoManager;
