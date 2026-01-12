/**
 * ModeState - Holds state for a single progress mode (planned or actual)
 *
 * Phase 0.2: StateManager Architecture
 *
 * This class encapsulates all data for one mode:
 * - assignmentMap: Saved data from backend (Map<cellKey, value>)
 * - modifiedCells: Unsaved changes from user input (Map<cellKey, value>)
 * - isDirty: Flag indicating if cache needs invalidation
 *
 * @class ModeState
 */
export class ModeState {
  /**
   * Create a new ModeState
   */
  constructor() {
    /**
     * Saved assignment values from backend
     * Key format: "{pekerjaanId}-{columnId}"
     * Value: number (percentage 0-100)
     * @type {Map<string, number>}
     */
    this.assignmentMap = new Map();

    /**
     * Modified cell values (unsaved changes)
     * Key format: "{pekerjaanId}-{columnId}"
     * Value: number (percentage 0-100)
     * @type {Map<string, number>}
     */
    this.modifiedCells = new Map();

    /**
     * Saved actual cost values (only applicable for actual mode but shared API)
     * Key format: "{pekerjaanId}-{columnId}"
     * Value: number (rupiah)
     * @type {Map<string, number>}
     */
    this.costAssignmentMap = new Map();

    /**
     * Modified actual cost values waiting to be saved
     * Key format: "{pekerjaanId}-{columnId}"
     * Value: number (rupiah)
     * @type {Map<string, number>}
     */
    this.costModifiedCells = new Map();

    /**
     * Dirty flag for cache invalidation
     * Set to true when modifiedCells changes
     * @type {boolean}
     */
    this.isDirty = false;
  }

  /**
   * Serialize state to JSON
   * Useful for debugging and persistence
   * @returns {Object}
   */
  toJSON() {
    return {
      assignmentMap: Array.from(this.assignmentMap.entries()),
      modifiedCells: Array.from(this.modifiedCells.entries()),
      costAssignmentMap: Array.from(this.costAssignmentMap.entries()),
      costModifiedCells: Array.from(this.costModifiedCells.entries()),
      isDirty: this.isDirty
    };
  }

  /**
   * Deserialize state from JSON
   * @param {Object} data - Serialized state data
   * @returns {ModeState}
   */
  static fromJSON(data) {
    const state = new ModeState();

    if (data.assignmentMap && Array.isArray(data.assignmentMap)) {
      state.assignmentMap = new Map(data.assignmentMap);
    }

    if (data.modifiedCells && Array.isArray(data.modifiedCells)) {
      state.modifiedCells = new Map(data.modifiedCells);
    }

    if (data.costAssignmentMap && Array.isArray(data.costAssignmentMap)) {
      state.costAssignmentMap = new Map(data.costAssignmentMap);
    }

    if (data.costModifiedCells && Array.isArray(data.costModifiedCells)) {
      state.costModifiedCells = new Map(data.costModifiedCells);
    }

    if (typeof data.isDirty === 'boolean') {
      state.isDirty = data.isDirty;
    }

    return state;
  }

  /**
   * Get statistics about this mode state
   * @returns {Object}
   */
  getStats() {
    return {
      assignmentCount: this.assignmentMap.size,
      modifiedCount: this.modifiedCells.size,
      costAssignmentCount: this.costAssignmentMap.size,
      costModifiedCount: this.costModifiedCells.size,
      isDirty: this.isDirty,
      hasUnsavedChanges: this.modifiedCells.size > 0 || this.costModifiedCells.size > 0
    };
  }

  /**
   * Clear all data from this mode state
   */
  clear() {
    this.assignmentMap.clear();
    this.modifiedCells.clear();
    this.costAssignmentMap.clear();
    this.costModifiedCells.clear();
    this.isDirty = true;
  }

  /**
   * Clone this mode state (deep copy)
   * @returns {ModeState}
   */
  clone() {
    const cloned = new ModeState();
    cloned.assignmentMap = new Map(this.assignmentMap);
    cloned.modifiedCells = new Map(this.modifiedCells);
    cloned.costAssignmentMap = new Map(this.costAssignmentMap);
    cloned.costModifiedCells = new Map(this.costModifiedCells);
    cloned.isDirty = this.isDirty;
    return cloned;
  }
}

export default ModeState;
