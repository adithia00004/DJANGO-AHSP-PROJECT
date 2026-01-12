/**
 * Time Column Generator Module (ES6 Modern Version)
 * Generates time columns for different modes: daily, weekly, monthly, custom
 *
 * Migrated from: jadwal_pekerjaan/kelola_tahapan/time_column_generator_module.js
 * Date: 2025-11-19
 */

import { StateManager } from './state-manager.js';

// =========================================================================
// CONSTANTS
// =========================================================================

const ONE_DAY_MS = 24 * 60 * 60 * 1000;

// =========================================================================
// UTILITY FUNCTIONS
// =========================================================================

/**
 * Format date to short format (DD MMM)
 * @param {Date} date - Date to format
 * @returns {string} Formatted date
 */
function formatDayMonth(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
    return '';
  }
  const day = date.getDate().toString().padStart(2, '0');
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  return `${day}/${month}`;
}

/**
 * Format date for display
 * @param {Date} date - Date to format
 * @param {string} format - Format type (short|iso|long)
 * @returns {string} Formatted date
 */
function formatDate(date, format = 'short') {
  if (format === 'short') {
    const day = date.getDate().toString().padStart(2, '0');
    const month = date.toLocaleString('id-ID', { month: 'short' });
    return `${day} ${month}`;
  } else if (format === 'iso') {
    return date.toISOString().split('T')[0];
  }
  return date.toLocaleDateString('id-ID');
}

/**
 * Get week number for a date relative to project start
 * @param {Date} targetDate - Target date
 * @param {Date} projectStart - Project start date
 * @param {Object} options - Additional options
 * @param {number} options.weekEndDay - JS weekday (0=Sunday) marking end of week
 * @returns {number} Week number (1-based)
 */
function getWeekNumberForDate(targetDate, projectStart, options = {}) {
  if (!(targetDate instanceof Date) || Number.isNaN(targetDate.getTime())) {
    return 1;
  }

  if (!(projectStart instanceof Date) || Number.isNaN(projectStart.getTime())) {
    return 1;
  }

  if (targetDate <= projectStart) {
    return 1;
  }

  const resolvedWeekEnd =
    Number.isInteger(options.weekEndDay) && !Number.isNaN(options.weekEndDay)
      ? ((options.weekEndDay % 7) + 7) % 7
      : 0; // Default: Sunday

  // Calculate first week end
  const firstWeekEnd = new Date(projectStart);
  const offsetToEnd = (resolvedWeekEnd - projectStart.getDay() + 7) % 7;
  firstWeekEnd.setDate(firstWeekEnd.getDate() + offsetToEnd);

  if (targetDate <= firstWeekEnd) {
    return 1;
  }

  // Calculate week number
  const daysAfterFirst = Math.floor((targetDate - firstWeekEnd) / ONE_DAY_MS);
  return 1 + Math.floor((daysAfterFirst + 6) / 7);
}

// =========================================================================
// TIME COLUMN GENERATOR CLASS
// =========================================================================

/**
 * TimeColumnGenerator class - generates time columns from tahapan data
 */
export class TimeColumnGenerator {
  constructor(state) {
    if (!state) {
      throw new Error('[TimeColumnGenerator] State is required');
    }

    this.state = state;
  }

  /**
   * Generate time columns from loaded tahapan data
   * Maps database tahapan to grid time columns based on current time scale mode.
   *
   * FILTERING LOGIC:
   * - daily/weekly/monthly: Shows ONLY auto-generated tahapan with matching generation_mode
   * - custom: Shows ALL tahapan (both auto-generated and manually created)
   *
   * CRITICAL: Each column MUST have tahapanId for save functionality to work!
   *
   * @returns {Array} Generated time columns
   */
  generate() {
    this.state.timeColumns = [];
    this._projectStartCache = undefined;
    this._jsWeekEndDayCache = undefined;

    const timeScale = this.state.timeScale || 'custom';
    const tahapanList = this.state.tahapanList || [];

    console.log(`[TimeColumnGenerator] Generating columns for mode: ${timeScale}`);
    console.log(`[TimeColumnGenerator] Available tahapan in database: ${tahapanList.length}`);

    // Map tahapan to time columns
    tahapanList.forEach((tahap, index) => {
      // For daily/weekly/monthly modes, only include tahapan with matching generation_mode
      // For custom mode, include all tahapan
      let shouldInclude = false;

      if (timeScale === 'custom') {
        // Custom mode: include all tahapan
        shouldInclude = true;
      } else {
        // Daily/weekly/monthly: only include AUTO-GENERATED tahapan with matching generation_mode
        shouldInclude = (
          tahap.is_auto_generated === true &&
          tahap.generation_mode === timeScale
        );
      }

      if (shouldInclude) {
        const column = this._createColumn(tahap, index);
        this.state.timeColumns.push(column);
      }
    });

    // FALLBACK: If no columns generated, show all tahapan
    if (this.state.timeColumns.length === 0 && tahapanList.length > 0) {
      console.warn(`[TimeColumnGenerator] No auto-generated tahapan found for mode "${timeScale}"`);
      console.warn(`[TimeColumnGenerator] Showing all ${tahapanList.length} tahapan as fallback`);

      tahapanList.forEach((tahap, index) => {
        const column = this._createColumn(tahap, index);
        this.state.timeColumns.push(column);
      });
    }

    console.log(`[TimeColumnGenerator] ✅ Generated ${this.state.timeColumns.length} time columns`);

    // Single source of truth: Update StateManager
    try {
      const stateManager = StateManager.getInstance();
      stateManager.setTimeColumns(this.state.timeColumns);
    } catch (e) {
      console.warn('[TimeColumnGenerator] Could not update StateManager:', e.message);
    }

    return this.state.timeColumns;
  }

  /**
   * Create a column object from tahapan data
   * @param {Object} tahap - Tahapan data
   * @param {number} index - Index in list
   * @returns {Object} Column object
   * @private
   */
  _createColumn(tahap, index) {
    const startDate = tahap.tanggal_mulai ? new Date(tahap.tanggal_mulai) : null;
    const endDate = tahap.tanggal_selesai ? new Date(tahap.tanggal_selesai) : null;

    let label = tahap.nama || `Tahap ${index + 1}`;
    let rangeLabel = '';
    let rangeText = '';
    let tooltip = label;
    let weekNumber = null;
    let shortStart = '';
    let shortEnd = '';
    const resolvedOrder =
      Number.isInteger(tahap.urutan) && tahap.urutan >= 0 ? tahap.urutan : index;

    const isWeeklyMode =
      (this.state.timeScale || '').toLowerCase() === 'weekly' ||
      (tahap.generation_mode || '').toLowerCase() === 'weekly';
    const projectStartDate = this._getProjectStartDate();
    const jsWeekEndDay = this._getJsWeekEndDay();
    const computedWeekNumber =
      isWeeklyMode && startDate && projectStartDate
        ? getWeekNumberForDate(startDate, projectStartDate, { weekEndDay: jsWeekEndDay })
        : null;

    // Special formatting for weekly mode
    if (
      tahap.is_auto_generated === true &&
      tahap.generation_mode === 'weekly' &&
      startDate &&
      endDate
    ) {
      weekNumber = computedWeekNumber ?? resolvedOrder + 1;

      shortStart = formatDayMonth(startDate);
      shortEnd = formatDayMonth(endDate);

      label = `Week ${weekNumber}`;
      rangeLabel = `( ${shortStart} - ${shortEnd} )`;
      rangeText = `${shortStart}\u00A0-\u00A0${shortEnd}`;

      const longStart = startDate.toLocaleDateString('id-ID', {
        weekday: 'long',
        day: '2-digit',
        month: 'long',
        year: 'numeric'
      });
      const longEnd = endDate.toLocaleDateString('id-ID', {
        weekday: 'long',
        day: '2-digit',
        month: 'long',
        year: 'numeric'
      });

      tooltip = `Week ${weekNumber}: ${longStart} - ${longEnd}`;
    } else if (startDate && endDate) {
      shortStart = formatDayMonth(startDate);
      shortEnd = formatDayMonth(endDate);
      rangeLabel = `( ${shortStart} - ${shortEnd} )`;
      rangeText = `${shortStart}\u00A0-\u00A0${shortEnd}`;
    }

    if (!weekNumber && isWeeklyMode) {
      weekNumber = computedWeekNumber ?? resolvedOrder + 1;
    }

    const safeTahapanId = tahap.tahapan_id || tahap.id || resolvedOrder;
    const fieldId = `col_${safeTahapanId}`;

    return {
      id: `tahap-${safeTahapanId}`,
      fieldId,
      tahapanId: tahap.tahapan_id,  // CRITICAL: Link to database tahapan!
      label,
      rangeLabel,
      rangeText,
      tooltip,
      type: tahap.generation_mode || 'custom',
      isAutoGenerated: tahap.is_auto_generated || false,
      generationMode: tahap.generation_mode || 'custom',
      index: resolvedOrder,
      weekNumber,
      startDate,
      endDate,
      urutan: tahap.urutan || index
    };
  }

  /**
   * Get column by ID
   * @param {string} columnId - Column ID
   * @returns {Object|null} Column object
   */
  getColumnById(columnId) {
    return this.state.timeColumns.find(col => col.id === columnId) || null;
  }

  /**
   * Get column by tahapan ID
   * @param {number} tahapanId - Tahapan ID
   * @returns {Object|null} Column object
   */
  getColumnByTahapanId(tahapanId) {
    return this.state.timeColumns.find(col => col.tahapanId === tahapanId) || null;
  }

  /**
   * Get columns for date range
   * @param {Date} startDate - Start date
   * @param {Date} endDate - End date
   * @returns {Array} Columns in range
   */
  getColumnsInRange(startDate, endDate) {
    return this.state.timeColumns.filter(col => {
      if (!col.startDate || !col.endDate) return false;
      return col.startDate <= endDate && col.endDate >= startDate;
    });
  }

  /**
   * Regenerate columns (refresh from tahapan list)
   * @returns {Array} New time columns
   */
  regenerate() {
    console.log('[TimeColumnGenerator] Regenerating columns...');
    return this.generate();
  }

  _getProjectStartDate() {
    if (typeof this._projectStartCache !== 'undefined') {
      return this._projectStartCache;
    }
    const raw = this.state.projectStart;
    if (!raw) {
      this._projectStartCache = null;
      return this._projectStartCache;
    }
    if (raw instanceof Date) {
      this._projectStartCache = Number.isNaN(raw.getTime()) ? null : raw;
      return this._projectStartCache;
    }
    const parsed = new Date(raw);
    this._projectStartCache = Number.isNaN(parsed.getTime()) ? null : parsed;
    return this._projectStartCache;
  }

  _getJsWeekEndDay() {
    if (typeof this._jsWeekEndDayCache !== 'undefined') {
      return this._jsWeekEndDayCache;
    }
    const pyWeekEnd = Number(this.state.weekEndDay);
    const normalizedPy = Number.isFinite(pyWeekEnd) ? ((pyWeekEnd % 7) + 7) % 7 : 6;
    this._jsWeekEndDayCache = (normalizedPy + 1) % 7; // Convert Monday-based to JS Sunday-based
    return this._jsWeekEndDayCache;
  }
}

// Export utilities
export {
  formatDate,
  formatDayMonth,
  getWeekNumberForDate
};
