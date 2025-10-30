// static/detail_project/js/jadwal_pekerjaan/kelola_tahapan/time_column_generator_module.js
// Time Column Generator Module for Kelola Tahapan Page

(function() {
  'use strict';

  const bootstrap = window.KelolaTahapanPageApp || window.JadwalPekerjaanApp;
  const manifest = window.KelolaTahapanModuleManifest;

  if (!bootstrap || !manifest) {
    console.error('[TimeColumnGenerator] Bootstrap or manifest not found');
    return;
  }

  const meta = {
    id: 'kelolaTahapanTimeColumnGenerator',
    namespace: 'kelola_tahapan.time_column_generator',
    label: 'Kelola Tahapan - Time Column Generator',
    description: 'Generates time columns for different modes: daily, weekly, monthly, custom'
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
  const moduleStore = globalModules.timeColumnGenerator = Object.assign({}, globalModules.timeColumnGenerator || {});

  const ONE_DAY_MS = 24 * 60 * 60 * 1000;

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

  function getProjectTimeline(state) {
    const today = new Date();
    const projectData = window.projectData || {};

    const start = projectData.tanggal_mulai
      ? new Date(projectData.tanggal_mulai)
      : (state.projectStart ? new Date(state.projectStart) : today);

    const end = projectData.tanggal_selesai
      ? new Date(projectData.tanggal_selesai)
      : (state.projectEnd ? new Date(state.projectEnd) : new Date(start.getFullYear(), 11, 31));

    return { start, end };
  }

  function getProjectStartDate(state) {
    if (state.tahapanList && state.tahapanList.length > 0 && state.tahapanList[0].tanggal_mulai) {
      return new Date(state.tahapanList[0].tanggal_mulai);
    }

    if (state.projectStart) {
      const date = new Date(state.projectStart);
      if (!Number.isNaN(date.getTime())) {
        return date;
      }
    }

    const now = new Date();
    return new Date(now.getFullYear(), 0, 1);
  }

  function addDays(date, days) {
    const result = new Date(date);
    result.setDate(result.getDate() + days);
    return result;
  }

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

  function formatDayMonth(date) {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
      return '';
    }
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    return `${day}/${month}`;
  }

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

    const weekEndDay = 6; // Default Sunday

    const firstWeekEnd = new Date(projectStart);
    const offsetToEnd = (weekEndDay - projectStart.getDay() + 7) % 7;
    firstWeekEnd.setDate(firstWeekEnd.getDate() + offsetToEnd);

    if (targetDate <= firstWeekEnd) {
      return 1;
    }

    const daysAfterFirst = Math.floor((targetDate - firstWeekEnd) / ONE_DAY_MS);
    return 1 + Math.floor((daysAfterFirst + 6) / 7);
  }

  // =========================================================================
  // TIME COLUMN GENERATION
  // =========================================================================

  /**
   * Generate time columns from loaded tahapan data
   * Maps database tahapan to grid time columns based on current time scale mode.
   *
   * FILTERING LOGIC:
   * - daily/weekly/monthly: Shows ONLY auto-generated tahapan with matching generation_mode
   * - custom: Shows ALL tahapan (both auto-generated and manually created)
   *
   * CRITICAL: Each column MUST have tahapanId for save functionality to work!
   * Without tahapanId, assignments cannot be linked to database tahapan.
   *
   * @param {Object} context - Context with state
   * @returns {Array} Generated time columns
   */
  function generateTimeColumns(context = {}) {
    const state = resolveState(context.state);
    if (!state) {
      throw new Error('[TimeColumnGenerator] State is required');
    }

    state.timeColumns = [];

    const timeScale = state.timeScale || 'custom';
    bootstrap.log.info(`TimeColumnGenerator: Generating columns for mode: ${timeScale}`);
    bootstrap.log.info(`TimeColumnGenerator: Available tahapan in database: ${state.tahapanList.length}`);

    // ALL modes pull from database tahapan (loaded in state.tahapanList)
    // Backend has already created the appropriate tahapan for each mode
    // We just map tahapan to time columns with proper tahapanId

    state.tahapanList.forEach((tahap, index) => {
      // For daily/weekly/monthly modes, only include tahapan with matching generation_mode
      // For custom mode, include all tahapan
      let shouldInclude = false;

      if (timeScale === 'custom') {
        // Custom mode: include all tahapan
        shouldInclude = true;
      } else {
        // Daily/weekly/monthly: only include AUTO-GENERATED tahapan with matching generation_mode
        // This filters out old custom tahapan when in auto-generated modes
        shouldInclude = (
          tahap.is_auto_generated === true &&
          tahap.generation_mode === timeScale
        );
      }

      if (shouldInclude) {
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
          const baseIndex = Number.isInteger(tahap.urutan) ? tahap.urutan : state.timeColumns.length;
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

        const column = {
          id: `tahap-${tahap.tahapan_id}`,
          tahapanId: tahap.tahapan_id,  // CRITICAL: Link to database tahapan!
          label,
          rangeLabel,
          tooltip,
          type: tahap.generation_mode || 'custom',
          isAutoGenerated: tahap.is_auto_generated || false,
          generationMode: tahap.generation_mode || 'custom',
          index: state.timeColumns.length,
          weekNumber,
          startDate: startDate,
          endDate: endDate,
          urutan: tahap.urutan || index
        };

        state.timeColumns.push(column);
      }
    });

    // FALLBACK: If no columns generated, show all tahapan
    // This can happen if user is in daily/weekly/monthly mode but hasn't generated tahapan yet
    if (state.timeColumns.length === 0 && state.tahapanList.length > 0) {
      bootstrap.log.warn(`TimeColumnGenerator: [fallback] No auto-generated tahapan found for mode "${timeScale}".`);
      bootstrap.log.warn(`TimeColumnGenerator: Showing all ${state.tahapanList.length} tahapan as fallback.`);
      bootstrap.log.warn(`TimeColumnGenerator: [tip] Use the ${timeScale} mode switcher to regenerate auto tahapan before editing.`);

      state.tahapanList.forEach((tahap, index) => {
        const startDate = tahap.tanggal_mulai ? new Date(tahap.tanggal_mulai) : null;
        const endDate = tahap.tanggal_selesai ? new Date(tahap.tanggal_selesai) : null;
        let label = tahap.nama || `Tahap ${index + 1}`;
        let rangeLabel = '';
        let tooltip = label;
        let weekNumber = null;

        if (
          tahap.is_auto_generated === true &&
          tahap.generation_mode === 'weekly' &&
          startDate &&
          endDate
        ) {
          const baseIndex = Number.isInteger(tahap.urutan) ? tahap.urutan : index;
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

        const column = {
          id: `tahap-${tahap.tahapan_id}`,
          tahapanId: tahap.tahapan_id,
          label,
          rangeLabel,
          tooltip,
          type: tahap.generation_mode || 'custom',
          isAutoGenerated: tahap.is_auto_generated || false,
          generationMode: tahap.generation_mode || 'custom',
          index: index,
          weekNumber,
          startDate: startDate,
          endDate: endDate,
          urutan: tahap.urutan || index
        };

        state.timeColumns.push(column);
      });
    }

    bootstrap.log.info(`TimeColumnGenerator: Generated ${state.timeColumns.length} time columns with tahapanId`);

    // Debug: Show breakdown by generation_mode
    const modeBreakdown = {};
    state.timeColumns.forEach(col => {
      const mode = col.generationMode || 'unknown';
      modeBreakdown[mode] = (modeBreakdown[mode] || 0) + 1;
    });
    bootstrap.log.info(`TimeColumnGenerator: Breakdown:`, modeBreakdown);

    return state.timeColumns;
  }

  /**
   * Generate daily columns (legacy, for reference)
   */
  function generateDailyColumns(context = {}) {
    const state = resolveState(context.state);
    if (!state) return [];

    const { start, end } = getProjectTimeline(state);
    bootstrap.log.info(`TimeColumnGenerator: Daily mode: ${formatDate(start, 'iso')} to ${formatDate(end, 'iso')}`);

    const columns = [];
    let currentDate = new Date(start);
    let dayNum = 1;

    while (currentDate <= end) {
      const column = {
        id: `day-${dayNum}`,
        tahapanId: null,
        label: `Day ${dayNum}`,
        sublabel: formatDate(currentDate, 'short'),
        type: 'daily',
        index: dayNum - 1,
        startDate: new Date(currentDate),
        endDate: new Date(currentDate),
        dateKey: formatDate(currentDate, 'iso')
      };

      columns.push(column);
      currentDate = addDays(currentDate, 1);
      dayNum++;
    }

    return columns;
  }

  /**
   * Generate weekly columns (legacy, for reference)
   */
  function generateWeeklyColumns(context = {}) {
    const state = resolveState(context.state);
    if (!state) return [];

    const { start, end } = getProjectTimeline(state);
    const weekEndDay = state.weekEndDay || 6;

    bootstrap.log.info(`TimeColumnGenerator: Weekly mode: ${formatDate(start, 'iso')} to ${formatDate(end, 'iso')}`);

    const columns = [];
    let currentStart = new Date(start);
    let weekNum = 1;

    while (currentStart <= end) {
      let currentEnd = new Date(currentStart);
      const daysUntilWeekEnd = (weekEndDay - currentStart.getDay() + 7) % 7;

      if (daysUntilWeekEnd === 0 && currentStart.getDay() === weekEndDay) {
        currentEnd = new Date(currentStart);
      } else {
        currentEnd = addDays(currentStart, daysUntilWeekEnd);
      }

      if (currentEnd > end) {
        currentEnd = new Date(end);
      }

      const startDay = currentStart.getDate().toString().padStart(2, '0');
      const endDay = currentEnd.getDate().toString().padStart(2, '0');
      const startMonthNum = (currentStart.getMonth() + 1).toString().padStart(2, '0');
      const endMonthNum = (currentEnd.getMonth() + 1).toString().padStart(2, '0');

      const rangeLabel = `( ${startDay}/${startMonthNum} - ${endDay}/${endMonthNum} )`;
      const longRange = `${startDay}/${startMonthNum}/${currentStart.getFullYear()} - ${endDay}/${endMonthNum}/${currentEnd.getFullYear()}`;
      const label = `Week ${weekNum}`;

      const column = {
        id: `week-${weekNum}`,
        tahapanId: null,
        label: label,
        rangeLabel,
        tooltip: `Week ${weekNum}: ${longRange}`,
        type: 'weekly',
        index: weekNum - 1,
        startDate: new Date(currentStart),
        endDate: new Date(currentEnd),
        weekNumber: weekNum
      };

      columns.push(column);

      currentStart = addDays(currentEnd, 1);
      weekNum++;

      if (weekNum > 100) break; // Safety check
    }

    return columns;
  }

  /**
   * Generate monthly columns (legacy, for reference)
   */
  function generateMonthlyColumns(context = {}) {
    const state = resolveState(context.state);
    if (!state) return [];

    const { start, end } = getProjectTimeline(state);
    bootstrap.log.info(`TimeColumnGenerator: Monthly mode: ${formatDate(start, 'iso')} to ${formatDate(end, 'iso')}`);

    const columns = [];
    let currentDate = new Date(start);
    let monthNum = 1;

    while (currentDate <= end) {
      const monthStart = new Date(currentDate);
      const monthEnd = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);
      const actualEnd = monthEnd > end ? new Date(end) : monthEnd;

      const monthName = currentDate.toLocaleString('id-ID', { month: 'long' });
      const year = currentDate.getFullYear();

      const column = {
        id: `month-${monthNum}`,
        tahapanId: null,
        label: `${monthName} ${year}`,
        type: 'monthly',
        index: monthNum - 1,
        startDate: new Date(monthStart),
        endDate: new Date(actualEnd),
        monthNumber: monthNum
      };

      columns.push(column);

      currentDate = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1);
      monthNum++;

      if (monthNum > 24) break; // Max 2 years
    }

    return columns;
  }

  // =========================================================================
  // MODULE EXPORTS
  // =========================================================================

  Object.assign(moduleStore, {
    resolveState,
    generateTimeColumns,
    generateDailyColumns,
    generateWeeklyColumns,
    generateMonthlyColumns,
    // Utilities
    getProjectTimeline,
    getProjectStartDate,
    getWeekNumberForDate,
    addDays,
    formatDate,
    formatDayMonth,
  });

  // Register module with bootstrap
  bootstrap.registerModule(meta.id, {
    namespace: meta.namespace,
    pageId: manifest.pageId,
    description: meta.description,
    onRegister(context) {
      bootstrap.log.info('TimeColumnGenerator module registered successfully');
      if (context && context.emit) {
        context.emit('kelola_tahapan.time_column_generator:registered', { meta });
      }
    },
    // Public API
    generateTimeColumns: (context) => moduleStore.generateTimeColumns(context),
    generateDailyColumns: (context) => moduleStore.generateDailyColumns(context),
    generateWeeklyColumns: (context) => moduleStore.generateWeeklyColumns(context),
    generateMonthlyColumns: (context) => moduleStore.generateMonthlyColumns(context),
    getProjectTimeline: (state) => moduleStore.getProjectTimeline(state),
    getProjectStartDate: (state) => moduleStore.getProjectStartDate(state),
  });

  bootstrap.log.info('[TimeColumnGenerator] Module initialized');
})();
