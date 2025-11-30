/**
 * StateManager - Singleton for managing dual-mode progress state
 *
 * Phase 0.2: StateManager Architecture
 *
 * This class replaces the fragmented state management pattern with a single
 * source of truth. It manages both 'planned' and 'actual' progress states
 * and provides a clean API for reading/writing cell values.
 *
 * Key features:
 * - Singleton pattern (one instance per application)
 * - Dual state architecture (planned vs actual)
 * - Smart caching with automatic invalidation
 * - Event-driven updates (pub/sub pattern)
 * - Thread-safe state switching
 *
 * @class StateManager
 */

import { ModeState } from './mode-state.js';

const LOG_PREFIX = '[StateManager]';

export class StateManager {
  /**
   * Singleton instance
   * @private
   * @static
   * @type {StateManager|null}
   */
  static instance = null;

  /**
   * Get singleton instance
   * @returns {StateManager}
   */
  static getInstance() {
    if (!StateManager.instance) {
      StateManager.instance = new StateManager();
      console.log(LOG_PREFIX, 'Singleton instance created');
    }
    return StateManager.instance;
  }

  /**
   * Private constructor (use getInstance() instead)
   * @private
   */
  constructor() {
    if (StateManager.instance) {
      throw new Error('StateManager is a singleton. Use StateManager.getInstance()');
    }

    /**
     * Current progress mode ('planned' or 'actual')
     * @type {string}
     */
    this.currentMode = 'planned';

    /**
     * Mode-specific state storage
     * @type {Object}
     */
    this.states = {
      planned: new ModeState(),
      actual: new ModeState()
    };

    /**
     * Merged cell values cache
     * Key: "cells:{mode}"
     * Value: Map<cellKey, number>
     * @private
     * @type {Map<string, Map<string, number>>}
     */
    this._mergedCellsCache = new Map();

    /**
     * Event listeners for state changes
     * @private
     * @type {Set<Function>}
     */
    this._listeners = new Set();

    console.log(LOG_PREFIX, 'Initialized with dual state architecture');
  }

  /**
   * Get value for a specific cell
   * Reads from modifiedCells first, then assignmentMap
   *
   * @param {number|string} pekerjaanId - Pekerjaan ID
   * @param {string} columnId - Column ID (e.g., "col_123")
   * @returns {number} Cell value (0 if not found)
   */
  getCellValue(pekerjaanId, columnId) {
    const state = this._getCurrentState();
    const cellKey = `${pekerjaanId}-${columnId}`;

    // Priority: modifiedCells > assignmentMap > 0
    return state.modifiedCells.get(cellKey) ??
           state.assignmentMap.get(cellKey) ??
           0;
  }

  /**
   * Get all cell values for a specific mode (merged view)
   * Returns assignmentMap + modifiedCells combined
   * Uses cache for performance
   *
   * @param {string} mode - 'planned' or 'actual'
   * @returns {Map<string, number>} Merged cell values
   */
  getAllCellsForMode(mode) {
    const modeState = this.states[mode];
    if (!modeState) {
      console.error(LOG_PREFIX, `Invalid mode: ${mode}`);
      return new Map();
    }

    const cacheKey = `cells:${mode}`;

    // Return cached if available and not dirty
    if (this._mergedCellsCache.has(cacheKey) && !modeState.isDirty) {
      return this._mergedCellsCache.get(cacheKey);
    }

    // Build merged map: assignmentMap + modifiedCells
    const merged = new Map(modeState.assignmentMap);

    // Override with modified cells
    modeState.modifiedCells.forEach((value, key) => {
      merged.set(key, value);
    });

    // Cache it
    this._mergedCellsCache.set(cacheKey, merged);
    modeState.isDirty = false;

    console.log(LOG_PREFIX, `Built merged cells for ${mode.toUpperCase()}: ${merged.size} cells`);

    return merged;
  }

  /**
   * Set value for a specific cell (user input)
   * Writes to modifiedCells, invalidates cache
   *
   * @param {number|string} pekerjaanId - Pekerjaan ID
   * @param {string} columnId - Column ID
   * @param {number|string} value - Cell value (percentage)
   */
  setCellValue(pekerjaanId, columnId, value) {
    const state = this._getCurrentState();
    const cellKey = `${pekerjaanId}-${columnId}`;
    const numericValue = parseFloat(value);

    if (Number.isNaN(numericValue)) {
      console.warn(LOG_PREFIX, `Invalid value for cell ${cellKey}:`, value);
      return;
    }

    // Write to modifiedCells
    state.modifiedCells.set(cellKey, numericValue);

    // Invalidate cache
    this._invalidateCache(this.currentMode);

    // Mark as dirty
    state.isDirty = true;

    console.log(LOG_PREFIX, `Cell ${cellKey} = ${numericValue}% (${this.currentMode.toUpperCase()} mode)`);
  }

  /**
   * Switch to a different progress mode
   * @param {string} newMode - 'planned' or 'actual'
   */
  switchMode(newMode) {
    if (newMode !== 'planned' && newMode !== 'actual') {
      console.error(LOG_PREFIX, `Invalid mode: ${newMode}`);
      return;
    }

    if (this.currentMode === newMode) {
      console.log(LOG_PREFIX, `Already in ${newMode.toUpperCase()} mode`);
      return;
    }

    const oldMode = this.currentMode;
    this.currentMode = newMode;

    console.log(LOG_PREFIX, `Switched: ${oldMode.toUpperCase()} → ${newMode.toUpperCase()}`);

    // Notify listeners
    this._notifyListeners({
      type: 'mode-switch',
      oldMode,
      newMode
    });
  }

  /**
   * Commit modified cells to assignmentMap (after save)
   * Clears modifiedCells and invalidates cache
   */
  commitChanges() {
    const state = this._getCurrentState();

    // Move modifiedCells → assignmentMap
    state.modifiedCells.forEach((value, key) => {
      state.assignmentMap.set(key, value);
    });

    // Move costModifiedCells → costAssignmentMap (used for actual mode)
    state.costModifiedCells.forEach((value, key) => {
      if (value === null || typeof value === 'undefined') {
        state.costAssignmentMap.delete(key);
        return;
      }
      const numeric = Number(value);
      if (Number.isFinite(numeric) && numeric >= 0) {
        state.costAssignmentMap.set(key, numeric);
      } else {
        state.costAssignmentMap.delete(key);
      }
    });

    const count = state.modifiedCells.size + state.costModifiedCells.size;
    state.modifiedCells.clear();
    state.costModifiedCells.clear();

    // Invalidate cache
    this._invalidateCache(this.currentMode);

    console.log(LOG_PREFIX, `Committed ${count} changes to ${this.currentMode.toUpperCase()} assignmentMap`);

    // Notify listeners
    this._notifyListeners({
      type: 'commit',
      mode: this.currentMode,
      count
    });
  }

  /**
   * Load initial data into assignmentMap
   * Used by DataLoader after fetching from backend
   *
   * @param {string} mode - 'planned' or 'actual'
   * @param {Map<string, number>} dataMap - Cell key → value map
   */
  loadData(mode, dataMap, costDataMap = new Map()) {
    const state = this.states[mode];
    if (!state) {
      console.error(LOG_PREFIX, `Invalid mode: ${mode}`);
      return;
    }

    // Replace assignmentMap
    state.assignmentMap = new Map(dataMap);
    if (costDataMap instanceof Map) {
      state.costAssignmentMap = new Map(costDataMap);
    }

    // Clear modified cells
    state.modifiedCells.clear();
    state.costModifiedCells.clear();

    // Invalidate cache
    this._invalidateCache(mode);

    console.log(LOG_PREFIX, `Loaded ${dataMap.size} assignments into ${mode.toUpperCase()} state`);
  }

  /**
   * Set initial value for a cell (from backend data)
   * Used during data loading phase
   *
   * @param {number|string} pekerjaanId
   * @param {string} columnId
   * @param {number} plannedValue
   * @param {number} actualValue
   */
  setInitialValue(pekerjaanId, columnId, plannedValue = 0, actualValue = 0, options = {}) {
    const cellKey = `${pekerjaanId}-${columnId}`;

    // Set planned value
    if (Number.isFinite(plannedValue) && plannedValue > 0) {
      this.states.planned.assignmentMap.set(cellKey, plannedValue);
    }

    // Set actual value
    if (Number.isFinite(actualValue) && actualValue > 0) {
      this.states.actual.assignmentMap.set(cellKey, actualValue);
    }

    const hasCostProp =
      Object.prototype.hasOwnProperty.call(options || {}, 'actualCost') ||
      Object.prototype.hasOwnProperty.call(options || {}, 'actual_cost') ||
      Object.prototype.hasOwnProperty.call(options || {}, 'cost');
    const actualCost = Number(options?.actualCost ?? options?.cost ?? options?.actual_cost);
    if (Number.isFinite(actualCost) && actualCost >= 0) {
      this.states.actual.costAssignmentMap.set(cellKey, actualCost);
    } else if (hasCostProp) {
      this.states.actual.costAssignmentMap.delete(cellKey);
    }
  }

  /**
   * Add event listener for state changes
   * @param {Function} callback - Listener function
   */
  addEventListener(callback) {
    if (typeof callback !== 'function') {
      console.error(LOG_PREFIX, 'Event listener must be a function');
      return;
    }

    this._listeners.add(callback);
    console.log(LOG_PREFIX, `Added event listener (total: ${this._listeners.size})`);
  }

  /**
   * Remove event listener
   * @param {Function} callback - Listener function
   */
  removeEventListener(callback) {
    this._listeners.delete(callback);
  }

  /**
   * Check if there are unsaved changes in current mode
   * @returns {boolean}
   */
  hasUnsavedChanges() {
    const state = this._getCurrentState();
    return (
      (state.modifiedCells && state.modifiedCells.size > 0) ||
      (state.costModifiedCells && state.costModifiedCells.size > 0)
    );
  }

  /**
   * Get statistics about state manager
   * @returns {Object}
   */
  getStats() {
    return {
      currentMode: this.currentMode,
      planned: this.states.planned.getStats(),
      actual: this.states.actual.getStats(),
      cacheSize: this._mergedCellsCache.size,
      listenerCount: this._listeners.size
    };
  }

  /**
   * Get current mode state
   * @private
   * @returns {ModeState}
   */
  _getCurrentState() {
    return this.states[this.currentMode];
  }

  /**
   * Invalidate cache for a specific mode
   * @private
   * @param {string} mode
   */
  _invalidateCache(mode) {
    const cacheKey = `cells:${mode}`;
    this._mergedCellsCache.delete(cacheKey);

    const state = this.states[mode];
    if (state) {
      state.isDirty = true;
    }
  }

  /**
   * Notify all event listeners
   * @private
   * @param {Object} event - Event data
   */
  _notifyListeners(event) {
    this._listeners.forEach(listener => {
      try {
        listener(event);
      } catch (error) {
        console.error(LOG_PREFIX, 'Listener error:', error);
      }
    });
  }

  /**
   * Clear all data (use with caution)
   */
  reset() {
    this.states.planned.clear();
    this.states.actual.clear();
    this._mergedCellsCache.clear();
    this.currentMode = 'planned';

    console.log(LOG_PREFIX, 'State reset');

    this._notifyListeners({ type: 'reset' });
  }

  /**
   * Export state for debugging
   * @returns {Object}
   */
  exportState() {
    return {
      currentMode: this.currentMode,
      planned: this.states.planned.toJSON(),
      actual: this.states.actual.toJSON(),
      stats: this.getStats()
    };
  }
}

// Phase 0: Export to global scope for testing and debugging
if (typeof window !== 'undefined') {
  window.StateManager = StateManager;
}

export default StateManager;
