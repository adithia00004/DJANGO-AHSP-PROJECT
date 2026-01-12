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

    /**
     * Single source of truth: Flat list of all pekerjaan rows
     * @type {Array<Object>}
     */
    this.flatPekerjaan = [];

    /**
     * Single source of truth: Time columns configuration
     * @type {Array<Object>}
     */
    this.timeColumns = [];

    /**
     * Chart data cache (from SSoT API)
     * Key: "{timescale}:{mode}" e.g. "weekly:both"
     * @type {Map<string, Object>}
     * @private
     */
    this._chartDataCache = new Map();

    /**
     * Project ID for API calls
     * @type {number|null}
     */
    this.projectId = null;

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

    // Also invalidate chart data cache (SSoT API data needs refresh)
    this.invalidateChartCache();

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
   * Set flat pekerjaan rows (single source of truth for all modes)
   * @param {Array<Object>} rows - Flat list of pekerjaan objects
   */
  setFlatPekerjaan(rows) {
    this.flatPekerjaan = Array.isArray(rows) ? rows : [];
    console.log(LOG_PREFIX, `Set ${this.flatPekerjaan.length} pekerjaan rows`);
  }

  /**
   * Get flat pekerjaan rows
   * @returns {Array<Object>}
   */
  getFlatPekerjaan() {
    return this.flatPekerjaan;
  }

  /**
   * Set time columns configuration (single source of truth for all modes)
   * @param {Array<Object>} columns - Time columns array
   */
  setTimeColumns(columns) {
    this.timeColumns = Array.isArray(columns) ? columns : [];
    console.log(LOG_PREFIX, `Set ${this.timeColumns.length} time columns`);
  }

  /**
   * Get time columns configuration
   * @returns {Array<Object>}
   */
  getTimeColumns() {
    return this.timeColumns;
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
   * Fetch chart data from SSoT API (with caching)
   * @param {string} timescale - 'weekly' or 'monthly'
   * @param {string} mode - 'planned', 'actual', or 'both'
   * @returns {Promise<Object>} Chart data from API
   */
  async fetchChartData(timescale = 'weekly', mode = 'both') {
    const cacheKey = `${timescale}:${mode}`;

    // Return cached data if available
    if (this._chartDataCache.has(cacheKey)) {
      console.log(LOG_PREFIX, 'Using cached chart data for:', cacheKey);
      return this._chartDataCache.get(cacheKey);
    }

    if (!this.projectId) {
      console.warn(LOG_PREFIX, 'No projectId set, cannot fetch chart data');
      return null;
    }

    try {
      console.log(LOG_PREFIX, 'Fetching chart data from API:', cacheKey);

      const response = await fetch(
        `/detail_project/api/v2/project/${this.projectId}/chart-data/?timescale=${timescale}&mode=${mode}`,
        {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
          },
          credentials: 'same-origin'
        }
      );

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();

      // Cache the response
      this._chartDataCache.set(cacheKey, data);

      console.log(LOG_PREFIX, 'Chart data fetched:', {
        timescale,
        columns: data.columns?.length || 0,
        rows: data.rows?.length || 0
      });

      // Notify listeners
      this._notifyListeners({
        type: 'chartDataLoaded',
        timescale,
        mode,
        data
      });

      return data;

    } catch (error) {
      console.error(LOG_PREFIX, 'Failed to fetch chart data:', error);
      return null;
    }
  }

  /**
   * Get cached chart data (synchronous)
   * @param {string} timescale - 'weekly' or 'monthly'
   * @param {string} mode - 'planned', 'actual', or 'both'
   * @returns {Object|null} Cached chart data or null
   */
  getChartData(timescale = 'weekly', mode = 'both') {
    const cacheKey = `${timescale}:${mode}`;
    return this._chartDataCache.get(cacheKey) || null;
  }

  /**
   * Invalidate chart data cache (call after save or data change)
   * @param {string} [timescale] - Specific timescale to invalidate, or all if omitted
   */
  invalidateChartCache(timescale = null) {
    if (timescale) {
      // Remove specific timescale entries
      for (const key of this._chartDataCache.keys()) {
        if (key.startsWith(timescale + ':')) {
          this._chartDataCache.delete(key);
        }
      }
      console.log(LOG_PREFIX, 'Chart cache invalidated for timescale:', timescale);
    } else {
      // Clear all
      this._chartDataCache.clear();
      console.log(LOG_PREFIX, 'All chart cache invalidated');
    }
  }

  /**
   * Set project ID for API calls
   * @param {number} projectId
   */
  setProjectId(projectId) {
    this.projectId = projectId;
    console.log(LOG_PREFIX, 'Project ID set:', projectId);
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
