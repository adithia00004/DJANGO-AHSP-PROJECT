/**
 * Time Column Generator Module (ES6 Modern Version)
 * Generates time columns for different modes: daily, weekly, monthly, custom
 *
 * Migrated from: jadwal_pekerjaan/kelola_tahapan/time_column_generator_module.js
 * Date: 2025-11-19
 */

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
 * @returns {number} Week number (1-based)
 */
function getWeekNumberForDate(targetDate, projectStart) {
  if (!(targetDate instanceof Date) || Number.isNaN(targetDate.getTime())) {
    return 1;
  }

  if (!(projectStart instanceof Date) || Number.isNaN(projectStart.getTime())) {
    return 1;
  }

  if (targetDate <= projectStart) {
    return 1;
  }

  const weekEndDay = 6; // Sunday (0 = Sunday, 6 = Saturday in JS)

  // Calculate first week end
  const firstWeekEnd = new Date(projectStart);
  const offsetToEnd = (weekEndDay - projectStart.getDay() + 7) % 7;
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
    let tooltip = label;
    let weekNumber = null;

    // Special formatting for weekly mode
    if (
      tahap.is_auto_generated === true &&
      tahap.generation_mode === 'weekly' &&
      startDate &&
      endDate
    ) {
      const baseIndex = Number.isInteger(tahap.urutan) ? tahap.urutan : this.state.timeColumns.length;
      weekNumber = baseIndex + 1;

      const shortStart = formatDayMonth(startDate);
      const shortEnd = formatDayMonth(endDate);

      label = `Week ${weekNumber}`;
      rangeLabel = `( ${shortStart} - ${shortEnd} )`;

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
    }

    return {
      id: `tahap-${tahap.tahapan_id}`,
      tahapanId: tahap.tahapan_id,  // CRITICAL: Link to database tahapan!
      label,
      rangeLabel,
      tooltip,
      type: tahap.generation_mode || 'custom',
      isAutoGenerated: tahap.is_auto_generated || false,
      generationMode: tahap.generation_mode || 'custom',
      index: this.state.timeColumns.length,
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
}

// Export utilities
export {
  formatDate,
  formatDayMonth,
  getWeekNumberForDate
};
