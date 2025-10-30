// static/detail_project/js/jadwal_pekerjaan/kelola_tahapan/validation_module.js
// Validation Module for Kelola Tahapan Page

(function() {
  'use strict';

  const bootstrap = window.KelolaTahapanPageApp || window.JadwalPekerjaanApp;
  const manifest = window.KelolaTahapanModuleManifest;

  if (!bootstrap || !manifest) {
    console.error('[Validation] Bootstrap or manifest not found');
    return;
  }

  const meta = {
    id: 'kelolaTahapanValidation',
    namespace: 'kelola_tahapan.validation',
    label: 'Kelola Tahapan - Validation',
    description: 'Validates progress totals, cell values, and provides visual feedback'
  };

  const noop = () => undefined;
  const hasModule = typeof bootstrap.hasModule === 'function'
    ? (id) => bootstrap.hasModule(id)
    : (id) => bootstrap.modules && bootstrap.modules.has
      ? bootstrap.modules.has(id)
      : false;

  if (hasModule(meta.id)) {
    return;
  }

  const globalModules = window.KelolaTahapanPageModules = window.KelolaTahapanPageModules || {};
  const moduleStore = globalModules.validation = Object.assign({}, globalModules.validation || {});

  // =========================================================================
  // UTILITY FUNCTIONS
  // =========================================================================

  function resolveState(stateOverride) {
    if (stateOverride) {
      return stateOverride;
    }
    if (window.kelolaTahapanPageState) {
      return window.kelolaTahapanPageState;
    }
    if (bootstrap && bootstrap.state) {
      return bootstrap.state;
    }
    return null;
  }

  // =========================================================================
  // VALIDATION FUNCTIONS
  // =========================================================================

  /**
   * Calculate total progress for a pekerjaan
   * @param {string} pekerjaanId - Pekerjaan ID
   * @param {Object} pendingChanges - Optional pending changes not yet saved
   * @param {Object} state - State object
   * @returns {number} Total progress percentage
   */
  function calculateTotalProgress(pekerjaanId, pendingChanges = {}, state = null) {
    state = state || resolveState();
    if (!state) {
      throw new Error('[Validation] State is required');
    }

    let total = 0;

    // Add all saved values
    state.assignmentMap.forEach((value, key) => {
      if (key.startsWith(`${pekerjaanId}-`)) {
        total += parseFloat(value) || 0;
      }
    });

    // Add pending modified values (replace saved values)
    state.modifiedCells.forEach((value, key) => {
      if (key.startsWith(`${pekerjaanId}-`)) {
        // Subtract old value if exists
        const savedValue = state.assignmentMap.get(key);
        if (savedValue) {
          total -= parseFloat(savedValue) || 0;
        }
        // Add new value
        total += parseFloat(value) || 0;
      }
    });

    // Add additional pending changes
    Object.entries(pendingChanges).forEach(([tahapanId, value]) => {
      const key = `${pekerjaanId}-tahap-${tahapanId}`;
      // If not already counted in modifiedCells
      if (!state.modifiedCells.has(key)) {
        const savedValue = state.assignmentMap.get(key);
        if (savedValue) {
          total -= parseFloat(savedValue) || 0;
        }
        total += parseFloat(value) || 0;
      }
    });

    return Math.round(total * 100) / 100; // Round to 2 decimals
  }

  /**
   * Validate and apply visual feedback for progress totals
   * @param {Map} changesByPekerjaan - Map of pekerjaan changes
   * @param {Object} state - State object
   * @returns {Object} Validation result {isValid, errors, warnings}
   */
  function validateProgressTotals(changesByPekerjaan, state = null) {
    state = state || resolveState();
    if (!state) {
      throw new Error('[Validation] State is required');
    }

    const errors = [];
    const warnings = [];

    changesByPekerjaan.forEach((assignments, pekerjaanId) => {
      const total = calculateTotalProgress(pekerjaanId, assignments, state);

      if (total > 100) {
        errors.push({
          pekerjaanId,
          total,
          message: `Pekerjaan ${pekerjaanId}: Total ${total.toFixed(2)}% melebihi 100%`
        });
      } else if (total < 100 && total > 0) {
        warnings.push({
          pekerjaanId,
          total,
          message: `Pekerjaan ${pekerjaanId}: Total ${total.toFixed(2)}% kurang dari 100%`
        });
      }
    });

    return {
      isValid: errors.length === 0,
      errors,
      warnings
    };
  }

  /**
   * Update visual feedback (border colors) for pekerjaan rows
   * @param {string} pekerjaanId - Pekerjaan ID
   * @param {number} total - Total progress percentage
   * @param {Object} context - Context with DOM references
   */
  function updateProgressVisualFeedback(pekerjaanId, total, context = {}) {
    const leftRow = document.querySelector(`#left-tbody tr[data-node-id="${pekerjaanId}"]`);
    const rightRow = document.querySelector(`#right-tbody tr[data-node-id="${pekerjaanId}"]`);

    if (!leftRow || !rightRow) return;

    // Remove all status classes
    leftRow.classList.remove('progress-over-100', 'progress-under-100', 'progress-complete-100');
    rightRow.classList.remove('progress-over-100', 'progress-under-100', 'progress-complete-100');

    // Apply appropriate class
    if (total > 100) {
      leftRow.classList.add('progress-over-100');
      rightRow.classList.add('progress-over-100');
    } else if (total < 100 && total > 0) {
      leftRow.classList.add('progress-under-100');
      rightRow.classList.add('progress-under-100');
    } else if (total === 100) {
      leftRow.classList.add('progress-complete-100');
      rightRow.classList.add('progress-complete-100');
    }
  }

  /**
   * Validate a single cell value
   * @param {number} value - Value to validate
   * @param {Object} options - Validation options
   * @returns {Object} Validation result {isValid, error}
   */
  function validateCellValue(value, options = {}) {
    const min = options.min !== undefined ? options.min : 0;
    const max = options.max !== undefined ? options.max : 100;
    const allowEmpty = options.allowEmpty !== undefined ? options.allowEmpty : true;

    // Check if value is empty
    if (value === null || value === undefined || value === '') {
      if (allowEmpty) {
        return { isValid: true, value: 0 };
      } else {
        return { isValid: false, error: 'Value cannot be empty' };
      }
    }

    // Parse value
    const parsedValue = parseFloat(value);

    // Check if value is a valid number
    if (Number.isNaN(parsedValue)) {
      return { isValid: false, error: 'Value must be a number' };
    }

    // Check if value is within range
    if (parsedValue < min) {
      return { isValid: false, error: `Value must be at least ${min}` };
    }

    if (parsedValue > max) {
      return { isValid: false, error: `Value must be at most ${max}` };
    }

    return { isValid: true, value: parsedValue };
  }

  /**
   * Validate all changes before save
   * @param {Object} context - Context with state and changesByPekerjaan
   * @returns {Object} Validation result
   */
  function validateBeforeSave(context = {}) {
    const state = resolveState(context.state);
    if (!state) {
      throw new Error('[Validation] State is required');
    }

    const changesByPekerjaan = context.changesByPekerjaan;
    if (!changesByPekerjaan) {
      return {
        isValid: true,
        errors: [],
        warnings: []
      };
    }

    // Step 1: Validate cell values
    const cellErrors = [];
    state.modifiedCells.forEach((value, key) => {
      const validation = validateCellValue(value);
      if (!validation.isValid) {
        cellErrors.push({
          cellKey: key,
          value,
          error: validation.error
        });
      }
    });

    if (cellErrors.length > 0) {
      return {
        isValid: false,
        errors: cellErrors.map(e => ({
          message: `Cell ${e.cellKey}: ${e.error}`
        })),
        warnings: []
      };
    }

    // Step 2: Validate progress totals
    const progressValidation = validateProgressTotals(changesByPekerjaan, state);

    // Step 3: Update visual feedback for all affected pekerjaan
    changesByPekerjaan.forEach((assignments, pekerjaanId) => {
      const total = calculateTotalProgress(pekerjaanId, assignments, state);
      updateProgressVisualFeedback(pekerjaanId, total, context);
    });

    return progressValidation;
  }

  /**
   * Get validation summary for display
   * @param {Object} validationResult - Validation result
   * @returns {string} Summary text
   */
  function getValidationSummary(validationResult) {
    if (!validationResult) {
      return '';
    }

    const parts = [];

    if (validationResult.errors && validationResult.errors.length > 0) {
      const errorMessages = validationResult.errors.map(e => e.message).join('\n');
      parts.push(`❌ Errors:\n${errorMessages}`);
    }

    if (validationResult.warnings && validationResult.warnings.length > 0) {
      const warningCount = validationResult.warnings.length;
      parts.push(`⚠️ ${warningCount} pekerjaan memiliki progress < 100%`);
    }

    return parts.join('\n\n');
  }

  /**
   * Clear all visual feedback
   * @param {Object} state - State object
   */
  function clearVisualFeedback(state = null) {
    state = state || resolveState();
    if (!state) return;

    const leftRows = document.querySelectorAll('#left-tbody tr[data-node-id]');
    const rightRows = document.querySelectorAll('#right-tbody tr[data-node-id]');

    leftRows.forEach(row => {
      row.classList.remove('progress-over-100', 'progress-under-100', 'progress-complete-100');
    });

    rightRows.forEach(row => {
      row.classList.remove('progress-over-100', 'progress-under-100', 'progress-complete-100');
    });
  }

  /**
   * Validate all pekerjaan progress and update visual feedback
   * @param {Object} state - State object
   * @returns {Object} Summary of validation results
   */
  function validateAllProgress(state = null) {
    state = state || resolveState();
    if (!state) {
      throw new Error('[Validation] State is required');
    }

    const summary = {
      total: 0,
      complete: 0,
      incomplete: 0,
      over: 0
    };

    state.flatPekerjaan
      .filter(node => node.type === 'pekerjaan')
      .forEach(node => {
        const total = calculateTotalProgress(node.id, {}, state);
        summary.total++;

        if (total === 100) {
          summary.complete++;
          updateProgressVisualFeedback(node.id, total);
        } else if (total > 100) {
          summary.over++;
          updateProgressVisualFeedback(node.id, total);
        } else if (total > 0) {
          summary.incomplete++;
          updateProgressVisualFeedback(node.id, total);
        }
      });

    return summary;
  }

  // =========================================================================
  // MODULE EXPORTS
  // =========================================================================

  Object.assign(moduleStore, {
    resolveState,
    calculateTotalProgress,
    validateProgressTotals,
    updateProgressVisualFeedback,
    validateCellValue,
    validateBeforeSave,
    getValidationSummary,
    clearVisualFeedback,
    validateAllProgress,
  });

  // Register module with bootstrap
  bootstrap.registerModule(meta.id, {
    namespace: meta.namespace,
    pageId: manifest.pageId,
    description: meta.description,
    onRegister(context) {
      bootstrap.log.info('Validation module registered successfully');
      if (context && context.emit) {
        context.emit('kelola_tahapan.validation:registered', { meta });
      }
    },
    // Public API
    calculateTotalProgress: (pekerjaanId, pendingChanges, state) =>
      moduleStore.calculateTotalProgress(pekerjaanId, pendingChanges, state),
    validateProgressTotals: (changesByPekerjaan, state) =>
      moduleStore.validateProgressTotals(changesByPekerjaan, state),
    updateProgressVisualFeedback: (pekerjaanId, total, context) =>
      moduleStore.updateProgressVisualFeedback(pekerjaanId, total, context),
    validateCellValue: (value, options) =>
      moduleStore.validateCellValue(value, options),
    validateBeforeSave: (context) =>
      moduleStore.validateBeforeSave(context),
    getValidationSummary: (validationResult) =>
      moduleStore.getValidationSummary(validationResult),
    clearVisualFeedback: (state) =>
      moduleStore.clearVisualFeedback(state),
    validateAllProgress: (state) =>
      moduleStore.validateAllProgress(state),
  });

  bootstrap.log.info('[Validation] Module initialized');
})();
