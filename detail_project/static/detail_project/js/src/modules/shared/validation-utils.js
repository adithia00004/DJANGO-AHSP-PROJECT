/**
 * Validation Utilities Module
 * Provides real-time validation with visual feedback for jadwal kegiatan
 * License: MIT
 */

/**
 * Validation result structure
 * @typedef {Object} ValidationResult
 * @property {boolean} isValid - Whether validation passed
 * @property {string} message - Validation message
 * @property {string} level - Severity level: 'error', 'warning', 'info'
 * @property {any} value - Validated/corrected value
 */

/**
 * Validates a single cell percentage value
 *
 * @param {any} value - Value to validate
 * @param {Object} options - Validation options
 * @param {number} options.min - Minimum value (default: 0)
 * @param {number} options.max - Maximum value (default: 100)
 * @param {number} options.precision - Decimal precision (default: 1)
 * @returns {ValidationResult}
 *
 * @example
 * const result = validateCellValue('95.5', { min: 0, max: 100 });
 * if (!result.isValid) {
 *   showToast(result.message, 'danger');
 * }
 */
export function validateCellValue(value, options = {}) {
  const { min = 0, max = 100, precision = 1 } = options;

  // Handle empty values
  if (value === null || value === undefined || value === '') {
    return {
      isValid: true,
      message: '',
      level: 'info',
      value: 0,
    };
  }

  // Convert to number
  const numValue = parseFloat(value);

  // Check if it's a valid number
  if (isNaN(numValue)) {
    return {
      isValid: false,
      message: `Nilai harus berupa angka (0-${max})`,
      level: 'error',
      value: 0,
    };
  }

  // Check range
  if (numValue < min) {
    return {
      isValid: false,
      message: `Nilai tidak boleh kurang dari ${min}`,
      level: 'error',
      value: min,
    };
  }

  if (numValue > max) {
    return {
      isValid: false,
      message: `Nilai tidak boleh lebih dari ${max}`,
      level: 'error',
      value: max,
    };
  }

  // Round to precision
  const roundedValue = Math.round(numValue * Math.pow(10, precision)) / Math.pow(10, precision);

  return {
    isValid: true,
    message: '',
    level: 'info',
    value: roundedValue,
  };
}

/**
 * Validates total progress across all weeks for a single pekerjaan
 *
 * @param {Array<number>} weeklyValues - Array of weekly percentage values
 * @param {Object} options - Validation options
 * @param {number} options.maxTotal - Maximum total (default: 100)
 * @param {number} options.tolerance - Tolerance for rounding errors (default: 0.1)
 * @returns {ValidationResult}
 *
 * @example
 * const weekValues = [20, 30, 25, 25]; // Total = 100
 * const result = validateTotalProgress(weekValues);
 * if (result.level === 'warning') {
 *   showWarningIndicator(pekerjaanId, result.message);
 * }
 */
export function validateTotalProgress(weeklyValues, options = {}) {
  const { maxTotal = 100, tolerance = 0.1 } = options;

  const total = weeklyValues.reduce((sum, val) => sum + (parseFloat(val) || 0), 0);
  const roundedTotal = Math.round(total * 10) / 10;

  // Perfect total
  if (Math.abs(roundedTotal - maxTotal) < tolerance) {
    return {
      isValid: true,
      message: `Total: ${roundedTotal}%`,
      level: 'info',
      value: roundedTotal,
    };
  }

  // Over 100%
  if (roundedTotal > maxTotal) {
    return {
      isValid: false,
      message: `Total melebihi ${maxTotal}% (${roundedTotal}%)`,
      level: 'error',
      value: roundedTotal,
    };
  }

  // Under 100%
  if (roundedTotal < maxTotal - tolerance) {
    return {
      isValid: false,
      message: `Total kurang dari ${maxTotal}% (${roundedTotal}%)`,
      level: 'warning',
      value: roundedTotal,
    };
  }

  return {
    isValid: true,
    message: `Total: ${roundedTotal}%`,
    level: 'info',
    value: roundedTotal,
  };
}

/**
 * Applies visual feedback to a cell based on validation result
 *
 * @param {HTMLElement} cellElement - Cell DOM element
 * @param {ValidationResult} validationResult - Validation result
 * @param {Object} options - Display options
 * @param {boolean} options.showTooltip - Show tooltip with message
 * @param {number} options.tooltipDuration - Duration to show tooltip (ms)
 *
 * @example
 * const cell = document.querySelector('.time-cell');
 * const result = validateCellValue(95.5);
 * applyValidationFeedback(cell, result, { showTooltip: true });
 */
export function applyValidationFeedback(cellElement, validationResult, options = {}) {
  const { showTooltip = true, tooltipDuration = 3000 } = options;

  // Remove existing validation classes
  cellElement.classList.remove(
    'validation-error',
    'validation-warning',
    'validation-success'
  );

  // Remove existing tooltip
  const existingTooltip = cellElement.querySelector('.validation-tooltip');
  if (existingTooltip) {
    existingTooltip.remove();
  }

  // Apply new validation class
  if (!validationResult.isValid) {
    if (validationResult.level === 'error') {
      cellElement.classList.add('validation-error');
    } else if (validationResult.level === 'warning') {
      cellElement.classList.add('validation-warning');
    }

    // Show tooltip if enabled and there's a message
    if (showTooltip && validationResult.message) {
      const tooltip = document.createElement('div');
      tooltip.className = `validation-tooltip validation-tooltip-${validationResult.level}`;
      tooltip.textContent = validationResult.message;

      cellElement.style.position = 'relative';
      cellElement.appendChild(tooltip);

      // Auto-remove after duration
      if (tooltipDuration > 0) {
        setTimeout(() => {
          tooltip.remove();
        }, tooltipDuration);
      }
    }
  } else {
    cellElement.classList.add('validation-success');
  }
}

/**
 * Updates progress indicator for a pekerjaan row
 *
 * @param {string} pekerjaanId - Pekerjaan ID
 * @param {number} totalProgress - Total progress percentage
 * @param {Object} state - Application state object
 *
 * @example
 * updateProgressIndicator('pekerjaan-123', 95.5, state);
 */
export function updateProgressIndicator(pekerjaanId, totalProgress, state) {
  const row = document.querySelector(`[data-pekerjaan-id="${pekerjaanId}"]`);
  if (!row) return;

  const indicator = row.querySelector('.progress-indicator') || createProgressIndicator(row);

  const validationResult = validateTotalProgress([totalProgress], { maxTotal: 100 });

  // Update indicator appearance
  indicator.textContent = `${totalProgress.toFixed(1)}%`;
  indicator.className = 'progress-indicator';

  if (validationResult.level === 'error') {
    indicator.classList.add('progress-error');
  } else if (validationResult.level === 'warning') {
    indicator.classList.add('progress-warning');
  } else {
    indicator.classList.add('progress-success');
  }

  // Update state
  if (state && state.progressTotals) {
    state.progressTotals.set(pekerjaanId, totalProgress);
  }
}

/**
 * Creates a progress indicator element if it doesn't exist
 *
 * @param {HTMLElement} rowElement - Row element
 * @returns {HTMLElement} Progress indicator element
 */
function createProgressIndicator(rowElement) {
  const nameCell = rowElement.querySelector('.name-cell');
  if (!nameCell) return null;

  const indicator = document.createElement('span');
  indicator.className = 'progress-indicator';
  nameCell.appendChild(indicator);

  return indicator;
}

/**
 * Batch validates all cells in the grid
 *
 * @param {Map} modifiedCells - Map of cell changes (cellKey -> value)
 * @param {Object} state - Application state
 * @returns {Object} Validation summary
 *
 * @example
 * const summary = batchValidateGrid(state.modifiedCells, state);
 * if (summary.errorCount > 0) {
 *   showToast(`${summary.errorCount} error(s) found`, 'danger');
 *   return false;
 * }
 */
export function batchValidateGrid(modifiedCells, state) {
  const summary = {
    totalCells: 0,
    validCells: 0,
    errorCount: 0,
    warningCount: 0,
    errors: [],
    warnings: [],
  };

  // Group cells by pekerjaan ID for total progress validation
  const pekerjaanGroups = new Map();

  for (const [cellKey, value] of modifiedCells.entries()) {
    const [pekerjaanId, weekId] = cellKey.split('-');

    // Validate individual cell
    const cellResult = validateCellValue(value);
    summary.totalCells++;

    if (cellResult.isValid) {
      summary.validCells++;
    } else {
      if (cellResult.level === 'error') {
        summary.errorCount++;
        summary.errors.push({ cellKey, message: cellResult.message });
      } else if (cellResult.level === 'warning') {
        summary.warningCount++;
        summary.warnings.push({ cellKey, message: cellResult.message });
      }
    }

    // Group by pekerjaan
    if (!pekerjaanGroups.has(pekerjaanId)) {
      pekerjaanGroups.set(pekerjaanId, []);
    }
    pekerjaanGroups.get(pekerjaanId).push(cellResult.value);
  }

  // Validate total progress for each pekerjaan
  for (const [pekerjaanId, values] of pekerjaanGroups.entries()) {
    const totalResult = validateTotalProgress(values);

    if (!totalResult.isValid) {
      if (totalResult.level === 'error') {
        summary.errorCount++;
        summary.errors.push({
          cellKey: pekerjaanId,
          message: `Pekerjaan ${pekerjaanId}: ${totalResult.message}`,
        });
      } else if (totalResult.level === 'warning') {
        summary.warningCount++;
        summary.warnings.push({
          cellKey: pekerjaanId,
          message: `Pekerjaan ${pekerjaanId}: ${totalResult.message}`,
        });
      }
    }

    // Update visual indicator
    updateProgressIndicator(pekerjaanId, totalResult.value, state);
  }

  return summary;
}

/**
 * Shows validation summary in a toast notification
 *
 * @param {Object} summary - Validation summary from batchValidateGrid
 * @param {Function} showToast - Toast notification function
 *
 * @example
 * const summary = batchValidateGrid(state.modifiedCells, state);
 * showValidationSummary(summary, window.showToast);
 */
export function showValidationSummary(summary, showToast) {
  if (summary.errorCount > 0) {
    const errorMessages = summary.errors.slice(0, 3).map((e) => e.message).join('<br>');
    const more = summary.errorCount > 3 ? `<br>...dan ${summary.errorCount - 3} error lainnya` : '';

    showToast(`❌ ${summary.errorCount} Error:<br>${errorMessages}${more}`, 'danger', 5000);
    return false;
  }

  if (summary.warningCount > 0) {
    showToast(`⚠️ ${summary.warningCount} Warning - periksa total progress`, 'warning', 4000);
  } else {
    showToast(`✅ Validasi sukses (${summary.totalCells} sel)`, 'success', 2000);
  }

  return true;
}

/**
 * Real-time cell validation handler (use with event delegation)
 *
 * @param {Event} event - Input event
 * @param {HTMLElement} cellElement - Cell element
 * @param {Object} state - Application state
 *
 * @example
 * eventManager.on('blur', '.time-cell input', (event, target) => {
 *   const cell = target.closest('.time-cell');
 *   handleCellValidation(event, cell, state);
 * });
 */
export function handleCellValidation(event, cellElement, state) {
  const input = event.target;
  const value = input.value;

  // Validate the cell value
  const result = validateCellValue(value);

  // Apply visual feedback
  applyValidationFeedback(cellElement, result, {
    showTooltip: !result.isValid,
    tooltipDuration: 3000,
  });

  // Update the value to validated/corrected value
  if (result.isValid || result.value !== parseFloat(value)) {
    input.value = result.value;

    // Update state
    const cellKey = cellElement.dataset.cellId;
    if (cellKey && state.modifiedCells) {
      state.modifiedCells.set(cellKey, result.value);
    }
  }

  // Show toast for errors
  if (!result.isValid && result.level === 'error') {
    if (typeof window.showToast === 'function') {
      window.showToast(result.message, 'danger', 3000);
    }
  }

  return result;
}
