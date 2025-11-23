/**
 * Save Handler Module (ES6 Modern Version)
 * Handles saving modified cells to Django backend
 *
 * Migrated from: jadwal_pekerjaan/kelola_tahapan/save_handler_module.js
 * Date: 2025-11-19
 */

// =========================================================================
// UTILITY FUNCTIONS
// =========================================================================

/**
 * Get CSRF token from cookies
 * @returns {string|null} CSRF token
 */
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// =========================================================================
// SAVE HANDLER CLASS
// =========================================================================

/**
 * SaveHandler - Manages save operations for grid data
 * Handles building payloads, API calls, and state updates
 */
export class SaveHandler {
  /**
   * Create a SaveHandler instance
   * @param {Object} state - Application state
   * @param {Object} options - Configuration options
   * @param {string} options.apiUrl - API endpoint URL
   * @param {Function} options.onSuccess - Success callback
   * @param {Function} options.onError - Error callback
   * @param {Function} options.showToast - Toast notification function
   */
  constructor(state, options = {}) {
    if (!state) {
      throw new Error('[SaveHandler] State is required');
    }

    this.state = state;
    this.options = options;

    // API configuration
    this.apiUrl = options.apiUrl || `/detail_project/api/project/${state.projectId}/pekerjaan/assign_weekly/`;

    // Callbacks
    this.onSuccess = options.onSuccess || (() => {});
    this.onError = options.onError || ((err) => console.error(err));
    this.showToast = options.showToast || ((msg, type) => console.log(`[${type}] ${msg}`));

    // Save state
    this.isSaving = false;

    console.log('[SaveHandler] Initialized with API:', this.apiUrl);
  }

  // =======================================================================
  // MAIN SAVE OPERATION
  // =======================================================================

  /**
   * Save all modified cells to server
   * Main entry point for save operation
   * @returns {Promise<Object>} Save result
   */
  async save() {
    if (this.isSaving) {
      console.warn('[SaveHandler] Save already in progress');
      this.showToast('Penyimpanan sedang berlangsung...', 'warning');
      return { success: false, reason: 'already_saving' };
    }

    console.log('[SaveHandler] Starting save operation...');
    this.isSaving = true;

    try {
      // Check if there are any changes
      if (!this.state.modifiedCells || this.state.modifiedCells.size === 0) {
        console.warn('[SaveHandler] No modified cells to save');
        this.showToast('Tidak ada perubahan untuk disimpan', 'info');
        this.isSaving = false;
        return { success: false, reason: 'no_changes' };
      }

      // Build payload
      const payload = this._buildPayload();
      console.log(`[SaveHandler] Built payload with ${payload.items.length} items`);

      // Send to server
      const result = await this._sendToServer(payload);

      // Handle success
      this._handleSaveSuccess(result);

      this.isSaving = false;
      return { success: true, result };

    } catch (error) {
      // Handle error
      this._handleSaveError(error);
      this.isSaving = false;
      return { success: false, error };
    }
  }

  // =======================================================================
  // PAYLOAD BUILDING
  // =======================================================================

  /**
   * Build save payload from modified cells
   * Converts modifiedCells Map to API format
   * @returns {Object} Payload object
   * @private
   */
  _buildPayload() {
    const items = [];

    // Convert modifiedCells Map to array of assignments
    this.state.modifiedCells.forEach((value, cellKey) => {
      // Parse cellKey (format: "nodeId-columnId")
      const [pekerjaanId, tahapanId] = cellKey.split('-');

      if (!pekerjaanId || !tahapanId) {
        console.warn(`[SaveHandler] Invalid cell key: ${cellKey}`);
        return;
      }

      // Get numeric value
      const percentage = parseFloat(value);
      if (!Number.isFinite(percentage)) {
        console.warn(`[SaveHandler] Invalid value for ${cellKey}: ${value}`);
        return;
      }

      // Get column info for additional metadata
      const column = this.state.timeColumns?.find(col => col.id === tahapanId);

      // Build item
      const item = {
        pekerjaan_id: parseInt(pekerjaanId, 10),
        tahapan_id: parseInt(tahapanId, 10),
        percentage: percentage,
      };

      // Add column metadata if available
      if (column) {
        if (column.startDate) {
          item.week_start = this._formatDate(column.startDate);
        }
        if (column.endDate) {
          item.week_end = this._formatDate(column.endDate);
        }
        if (column.weekNumber) {
          item.week_number = column.weekNumber;
        }
      }

      items.push(item);
    });

    console.log(`[SaveHandler] Built ${items.length} assignment items`);

    return {
      items,
      mode: this.state.timeScale || 'weekly',
      project_id: this.state.projectId
    };
  }

  /**
   * Format date for API (YYYY-MM-DD)
   * @param {Date} date - Date to format
   * @returns {string} Formatted date
   * @private
   */
  _formatDate(date) {
    if (!(date instanceof Date)) {
      date = new Date(date);
    }
    if (Number.isNaN(date.getTime())) {
      return '';
    }
    return date.toISOString().split('T')[0];
  }

  // =======================================================================
  // API COMMUNICATION
  // =======================================================================

  /**
   * Send payload to server
   * @param {Object} payload - Payload to send
   * @returns {Promise<Object>} Server response
   * @private
   */
  async _sendToServer(payload) {
    console.log('[SaveHandler] Sending request to:', this.apiUrl);
    console.log('[SaveHandler] Payload:', payload);

    const csrfToken = getCookie('csrftoken');

    const response = await fetch(this.apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      credentials: 'same-origin',
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMsg = errorData.error || errorData.message || `HTTP ${response.status}`;
      throw new Error(errorMsg);
    }

    const result = await response.json();
    console.log('[SaveHandler] Server response:', result);

    return result;
  }

  // =======================================================================
  // RESPONSE HANDLING
  // =======================================================================

  /**
   * Handle successful save
   * @param {Object} result - Server response
   * @private
   */
  _handleSaveSuccess(result) {
    console.log('[SaveHandler] ✅ Save successful');

    // Update assignmentMap with saved values
    this._updateAssignmentMap();

    // Clear modified cells
    const modifiedCount = this.state.modifiedCells.size;
    this.state.modifiedCells.clear();

    // Update UI status
    if (this.state.cache) {
      this.state.cache.hasUnsavedChanges = false;
    }

    // Show success message
    const savedCount = result.saved_count || result.count || modifiedCount;
    const message = `Berhasil menyimpan ${savedCount} perubahan`;
    this.showToast(message, 'success');

    // Call success callback
    if (typeof this.onSuccess === 'function') {
      this.onSuccess(result);
    }

    console.log(`[SaveHandler] Saved ${savedCount} assignments, cleared ${modifiedCount} modified cells`);
  }

  /**
   * Handle save error
   * @param {Error} error - Error object
   * @private
   */
  _handleSaveError(error) {
    console.error('[SaveHandler] ❌ Save failed:', error);

    // Show error message
    const message = `Gagal menyimpan: ${error.message}`;
    this.showToast(message, 'danger');

    // Call error callback
    if (typeof this.onError === 'function') {
      this.onError(error);
    }
  }

  /**
   * Update assignmentMap with modified values
   * Moves modified values from modifiedCells to assignmentMap
   * @private
   */
  _updateAssignmentMap() {
    if (!this.state.assignmentMap) {
      this.state.assignmentMap = new Map();
    }

    this.state.modifiedCells.forEach((value, cellKey) => {
      const numericValue = parseFloat(value);
      if (Number.isFinite(numericValue)) {
        this.state.assignmentMap.set(cellKey, numericValue);
      }
    });

    console.log('[SaveHandler] Updated assignmentMap with modified values');
  }

  // =======================================================================
  // UTILITY METHODS
  // =======================================================================

  /**
   * Check if there are unsaved changes
   * @returns {boolean} True if has unsaved changes
   */
  hasUnsavedChanges() {
    return this.state.modifiedCells && this.state.modifiedCells.size > 0;
  }

  /**
   * Get count of modified cells
   * @returns {number} Number of modified cells
   */
  getModifiedCount() {
    return this.state.modifiedCells ? this.state.modifiedCells.size : 0;
  }

  /**
   * Validate payload before sending
   * @param {Object} payload - Payload to validate
   * @returns {Object} Validation result
   */
  validatePayload(payload) {
    const errors = [];
    const warnings = [];

    if (!payload || !Array.isArray(payload.items)) {
      errors.push('Invalid payload structure');
      return { isValid: false, errors, warnings };
    }

    if (payload.items.length === 0) {
      warnings.push('No items to save');
    }

    // Validate each item
    payload.items.forEach((item, index) => {
      if (!item.pekerjaan_id) {
        errors.push(`Item ${index}: Missing pekerjaan_id`);
      }
      if (!item.tahapan_id) {
        errors.push(`Item ${index}: Missing tahapan_id`);
      }
      if (!Number.isFinite(item.percentage)) {
        errors.push(`Item ${index}: Invalid percentage value`);
      }
      if (item.percentage < 0 || item.percentage > 100) {
        warnings.push(`Item ${index}: Percentage out of range (${item.percentage}%)`);
      }
    });

    const isValid = errors.length === 0;

    if (!isValid) {
      console.error('[SaveHandler] Payload validation failed:', errors);
    }

    if (warnings.length > 0) {
      console.warn('[SaveHandler] Payload validation warnings:', warnings);
    }

    return { isValid, errors, warnings };
  }

  /**
   * Cancel save operation
   */
  cancel() {
    if (this.isSaving) {
      console.log('[SaveHandler] Cancelling save operation...');
      this.isSaving = false;
      // Note: Cannot actually abort fetch request without AbortController
      // This just sets the flag
    }
  }

  /**
   * Get save statistics
   * @returns {Object} Save statistics
   */
  getStats() {
    return {
      modifiedCells: this.getModifiedCount(),
      isSaving: this.isSaving,
      hasUnsavedChanges: this.hasUnsavedChanges(),
      apiUrl: this.apiUrl
    };
  }
}

// Export utility functions
export {
  getCookie
};
