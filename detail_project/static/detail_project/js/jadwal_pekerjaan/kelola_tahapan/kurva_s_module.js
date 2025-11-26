(function() {
  'use strict';

  const bootstrap = window.KelolaTahapanPageApp || window.JadwalPekerjaanApp;
  const manifest = window.KelolaTahapanModuleManifest;
  if (!bootstrap || !manifest || !manifest.modules || !manifest.modules.kurvaS) {
    return;
  }

  const meta = manifest.modules.kurvaS;
  const noop = () => undefined;
  const hasModule = typeof bootstrap.hasModule === 'function'
    ? (id) => bootstrap.hasModule(id)
    : (id) => bootstrap.modules && bootstrap.modules.has
      ? bootstrap.modules.has(id)
      : false;

  if (hasModule(meta.id)) {
    return;
  }

  const bridge = () => {
    const facade = window[manifest.globals.facade];
    if (!facade || !facade.kurvaS) {
      return {};
    }
    return facade.kurvaS;
  };

  const globalModules = window.KelolaTahapanPageModules = window.KelolaTahapanPageModules || {};
  const moduleStore = globalModules.kurvaS = Object.assign({}, globalModules.kurvaS || {});

  const ONE_DAY_MS = 24 * 60 * 60 * 1000;

  function resolveState(stateOverride) {
    const state = stateOverride || window.kelolaTahapanPageState || (bootstrap && bootstrap.state) || null;
    if (!state) return null;
    if (!state.domRefs || typeof state.domRefs !== 'object') {
      state.domRefs = {};
    }
    return state;
  }

  function resolveDom(state) {
    const domRefs = state.domRefs || {};
    const chartDom = domRefs.scurveChart || document.getElementById('scurve-chart');
    if (!domRefs.scurveChart && chartDom) {
      domRefs.scurveChart = chartDom;
    }
    return chartDom;
  }

  function getThemeColors() {
    const theme = document.documentElement.getAttribute('data-bs-theme') || 'light';
    if (theme === 'dark') {
      return {
        text: '#f8fafc',
        axis: '#cbd5f5',
        plannedLine: '#60a5fa',
        plannedArea: 'rgba(96, 165, 250, 0.15)',
        actualLine: '#34d399',
        actualArea: 'rgba(52, 211, 153, 0.18)',
        gridLine: '#334155',
      };
    }
    return {
      text: '#1f2937',
      axis: '#374151',
      plannedLine: '#0d6efd',
      plannedArea: 'rgba(13, 110, 253, 0.12)',
      actualLine: '#198754',
      actualArea: 'rgba(25, 135, 84, 0.12)',
      gridLine: '#e5e7eb',
    };
  }

  function getColumns(state) {
    const columns = Array.isArray(state.timeColumns) ? state.timeColumns.slice() : [];
    columns.sort((a, b) => {
      const aStart = a.startDate instanceof Date ? a.startDate : (a.startDate ? new Date(a.startDate) : null);
      const bStart = b.startDate instanceof Date ? b.startDate : (b.startDate ? new Date(b.startDate) : null);
      if (aStart && bStart) return aStart.getTime() - bStart.getTime();
      return (a.index || 0) - (b.index || 0);
    });
    return columns;
  }

  function buildVolumeLookup(state) {
    const lookup = new Map();
    const setVolume = (key, value) => {
      const numericKey = Number(key);
      const volume = Number.isFinite(value) && value > 0 ? value : null;
      if (volume === null) return;
      lookup.set(String(key), volume);
      if (!Number.isNaN(numericKey)) {
        lookup.set(String(numericKey), volume);
      }
    };

    if (state.volumeMap instanceof Map) {
      state.volumeMap.forEach((value, key) => {
        const vol = parseFloat(value);
        setVolume(key, vol);
      });
    } else if (state.volumeMap && typeof state.volumeMap === 'object') {
      Object.entries(state.volumeMap).forEach(([key, value]) => {
        const vol = parseFloat(value);
        setVolume(key, vol);
      });
    }

    return lookup;
  }

  function getVolumeForPekerjaan(volumeLookup, pekerjaanId, fallback = 1) {
    const idVariants = [
      String(pekerjaanId),
      String(Number(pekerjaanId)),
    ];
    for (const variant of idVariants) {
      if (volumeLookup.has(variant)) {
        return volumeLookup.get(variant);
      }
    }
    return fallback;
  }

  /**
   * Build harga (cost) lookup map from state
   * Phase 2F.0: Kurva S should use HARGA (Rupiah) instead of volume
   *
   * @param {Object} state - Application state
   * @returns {Map<string, number>} Map of pekerjaanId → total harga (Rp)
   */
  function buildHargaLookup(state) {
    const lookup = new Map();
    const setHarga = (key, value) => {
      const numericKey = Number(key);
      const harga = Number.isFinite(value) && value >= 0 ? value : null;
      if (harga === null) return;
      lookup.set(String(key), harga);
      if (!Number.isNaN(numericKey)) {
        lookup.set(String(numericKey), harga);
      }
    };

    if (state.hargaMap instanceof Map) {
      state.hargaMap.forEach((value, key) => {
        const harga = parseFloat(value);
        setHarga(key, harga);
      });
    } else if (state.hargaMap && typeof state.hargaMap === 'object') {
      Object.entries(state.hargaMap).forEach(([key, value]) => {
        const harga = parseFloat(value);
        setHarga(key, harga);
      });
    }

    return lookup;
  }

  /**
   * Get harga for a specific pekerjaan
   * Phase 2F.0: Used for harga-weighted Kurva S calculation
   *
   * @param {Map} hargaLookup - Lookup map from buildHargaLookup()
   * @param {string|number} pekerjaanId - Pekerjaan ID
   * @param {number} fallback - Fallback value if not found (default: 0)
   * @returns {number} Total harga (Rp) for the pekerjaan
   */
  function getHargaForPekerjaan(hargaLookup, pekerjaanId, fallback = 0) {
    const idVariants = [
      String(pekerjaanId),
      String(Number(pekerjaanId)),
    ];
    for (const variant of idVariants) {
      if (hargaLookup.has(variant)) {
        return hargaLookup.get(variant);
      }
    }
    return fallback;
  }

  function buildCellValueMap(state) {
    const map = new Map();

    const assignValue = (key, value) => {
      const numeric = parseFloat(value);
      map.set(String(key), Number.isFinite(numeric) ? numeric : 0);
    };

    if (state.assignmentMap instanceof Map) {
      state.assignmentMap.forEach((value, key) => assignValue(key, value));
    } else if (state.assignmentMap && typeof state.assignmentMap === 'object') {
      Object.entries(state.assignmentMap).forEach(([key, value]) => assignValue(key, value));
    }

    if (state.modifiedCells instanceof Map) {
      state.modifiedCells.forEach((value, key) => assignValue(key, value));
    } else if (state.modifiedCells && typeof state.modifiedCells === 'object') {
      Object.entries(state.modifiedCells).forEach(([key, value]) => assignValue(key, value));
    }

    return map;
  }

  function collectPekerjaanIds(state, cellValues) {
    const ids = new Set();

    if (Array.isArray(state.flatPekerjaan)) {
      state.flatPekerjaan.forEach((node) => {
        if (node && (node.type === 'pekerjaan' || typeof node.type === 'undefined')) {
          ids.add(String(node.id));
        }
      });
    }

    cellValues.forEach((_, key) => {
      const [pekerjaanId] = String(key).split('-');
      if (pekerjaanId) {
        ids.add(pekerjaanId);
      }
    });

    return ids;
  }

  /**
   * Calculate volume-based planned curve from pekerjaan assignments
   *
   * ALGORITHM:
   * For each time period (column):
   *   1. Identify pekerjaan that have assignments in this period
   *   2. Sum their TOTAL volumes (not progress, full volume)
   *   3. Accumulate to get cumulative planned volume
   *   4. Convert to percentage of total project volume
   *
   * ASSUMPTION:
   * If a pekerjaan is assigned to a period (even with partial progress),
   * we assume the FULL volume of that pekerjaan should be completed
   * by the end of that period according to the plan.
   *
   * EXAMPLE:
   * Project with 3 pekerjaan (100m², 200m², 100m² = 400m² total)
   * - Pekerjaan A (100m²) assigned to Column 0
   * - Pekerjaan B (200m²) assigned to Column 1
   * - Pekerjaan C (100m²) assigned to Column 2
   *
   * Result:
   * - Column 0: 25% (100/400)
   * - Column 1: 75% (300/400)
   * - Column 2: 100% (400/400)
   *
   * @param {Array} columns - Array of time column objects
   * @param {Map} volumeLookup - Map of pekerjaanId → volume
   * @param {Map} cellValues - Map of cellKey → percentage value
   * @param {number} totalVolume - Total project volume
   * @param {Function} getVolumeForPekerjaan - Helper to get volume
   * @returns {Array<number>} Array of cumulative planned percentages
   */
  function calculateVolumeBasedPlannedCurve(columns, volumeLookup, cellValues, totalVolume, getVolumeForPekerjaan) {
    // Build mapping of column index to assigned pekerjaan IDs
    const columnIndexById = new Map();
    columns.forEach((col, index) => {
      columnIndexById.set(String(col.id), index);
    });

    const columnAssignments = new Map(); // columnIndex → Set<pekerjaanId>

    // Iterate through all cell assignments
    cellValues.forEach((value, key) => {
      const [pekerjaanId, columnId] = String(key).split('-');
      const columnIndex = columnIndexById.get(columnId);

      if (columnIndex !== undefined && pekerjaanId) {
        if (!columnAssignments.has(columnIndex)) {
          columnAssignments.set(columnIndex, new Set());
        }
        columnAssignments.get(columnIndex).add(pekerjaanId);
      }
    });

    // Calculate cumulative planned volume for each column
    let cumulativePlannedVolume = 0;
    const plannedSeries = [];
    const assignedPekerjaan = new Set(); // Track already counted pekerjaan

    columns.forEach((col, index) => {
      // Get pekerjaan assigned to this column
      const assignedInThisColumn = columnAssignments.get(index) || new Set();

      // Add volumes of newly assigned pekerjaan (not counted before)
      assignedInThisColumn.forEach((pekerjaanId) => {
        if (!assignedPekerjaan.has(pekerjaanId)) {
          const volume = getVolumeForPekerjaan(volumeLookup, pekerjaanId, 1);
          cumulativePlannedVolume += volume;
          assignedPekerjaan.add(pekerjaanId);
        }
      });

      // Calculate percentage
      const plannedPercent = totalVolume > 0
        ? Math.min(100, Math.max(0, (cumulativePlannedVolume / totalVolume) * 100))
        : 0;

      plannedSeries.push(Number(plannedPercent.toFixed(2)));
    });

    return plannedSeries;
  }

  /**
   * Calculate ideal S-Curve using sigmoid (logistic) function
   *
   * MATHEMATICAL FORMULA:
   * P(t) = 100 / (1 + e^(-k*(t - t₀)))
   *
   * Where:
   * - t = time period index (0 to n-1)
   * - t₀ = midpoint of timeline (n/2)
   * - k = steepness factor (controls curve shape)
   * - P(t) = cumulative percentage at time t
   *
   * CURVE PROPERTIES:
   * - Starts near 0% (slow ramp-up phase)
   * - Accelerates in middle (peak productivity)
   * - Slows down near 100% (completion/tapering)
   * - Smooth continuous curve (realistic S-shape)
   *
   * STEEPNESS FACTOR (k):
   * - k = 0.5: Gentle S-curve (gradual progress)
   * - k = 0.8: Moderate S-curve (default, balanced)
   * - k = 1.2: Steep S-curve (aggressive schedule)
   *
   * USE CASE:
   * This is used when no assignment data exists (new projects)
   * to provide a realistic planned curve based on typical project
   * progress patterns.
   *
   * @param {Array} columns - Array of time column objects
   * @param {number} steepnessFactor - Controls curve steepness (default: 0.8)
   * @returns {Array<number>} Array of cumulative planned percentages
   */
  function calculateIdealSCurve(columns, steepnessFactor = 0.8) {
    const n = columns.length;
    if (n === 0) return [];

    const midpoint = n / 2;
    const plannedSeries = [];

    // Apply sigmoid function to each time period
    columns.forEach((col, index) => {
      const t = index;
      // Sigmoid formula: 100 / (1 + e^(-k*(t - midpoint)))
      const exponent = -steepnessFactor * (t - midpoint);
      const sigmoid = 100 / (1 + Math.exp(exponent));
      plannedSeries.push(Number(sigmoid.toFixed(2)));
    });

    return plannedSeries;
  }

  /**
   * Calculate linear planned curve (fallback method)
   *
   * ALGORITHM:
   * Divides 100% equally across all time periods.
   * Progress increases linearly: Period 1 = n%, Period 2 = 2n%, etc.
   *
   * FORMULA:
   * P(t) = (100 / n) * (t + 1)
   *
   * Where:
   * - n = total number of periods
   * - t = period index (0-based)
   * - P(t) = cumulative percentage at period t
   *
   * USE CASE:
   * Used as last resort fallback when other methods cannot be applied.
   * Not realistic but provides basic functionality.
   *
   * @param {Array} columns - Array of time column objects
   * @returns {Array<number>} Array of cumulative planned percentages
   */
  function calculateLinearPlannedCurve(columns) {
    const plannedStep = columns.length > 0 ? 100 / columns.length : 0;
    const plannedSeries = [];

    columns.forEach((col, index) => {
      const plannedPercent = Math.min(100, Math.max(0, plannedStep * (index + 1)));
      plannedSeries.push(Number(plannedPercent.toFixed(2)));
    });

    return plannedSeries;
  }

  /**
   * Calculate planned curve using best available method
   *
   * STRATEGY (Hybrid Approach):
   * 1. If assignments exist → Volume-based calculation (most accurate)
   * 2. If no assignments → Ideal S-curve (realistic for new projects)
   * 3. Fallback → Linear distribution (backwards compatible)
   *
   * WHY HYBRID?
   * - Volume-based: Reflects actual project plan when data available
   * - Ideal S-curve: Provides realistic curve for new/empty projects
   * - Linear fallback: Ensures functionality in all edge cases
   *
   * DECISION FLOW:
   * ```
   * Has assignments? ─Yes→ Volume-based planned curve
   *        │
   *        No
   *        ↓
   * Use ideal curve? ─Yes→ Sigmoid S-curve
   *        │
   *        No
   *        ↓
   * Linear fallback
   * ```
   *
   * @param {Array} columns - Array of time column objects
   * @param {Map} volumeLookup - Map of pekerjaanId → volume
   * @param {Map} cellValues - Map of cellKey → percentage value
   * @param {number} totalVolume - Total project volume
   * @param {Function} getVolumeForPekerjaan - Helper to get volume
   * @param {Object} options - Configuration options
   * @param {boolean} [options.useIdealCurve=true] - Use sigmoid if no assignments
   * @param {number} [options.steepnessFactor=0.8] - Sigmoid steepness (0.5-1.5)
   * @param {boolean} [options.fallbackToLinear=true] - Use linear as last resort
   * @returns {Array<number>} Array of cumulative planned percentages
   */
  function calculatePlannedCurve(columns, volumeLookup, cellValues, totalVolume, getVolumeForPekerjaan, options = {}) {
    // Default options
    const useIdealCurve = options.useIdealCurve !== false;
    const steepnessFactor = options.steepnessFactor || 0.8;
    const fallbackToLinear = options.fallbackToLinear !== false;

    // Strategy 1: Volume-based (if assignments exist)
    const hasAssignments = cellValues && cellValues.size > 0;

    if (hasAssignments) {
      const volumeBased = calculateVolumeBasedPlannedCurve(
        columns,
        volumeLookup,
        cellValues,
        totalVolume,
        getVolumeForPekerjaan
      );

      // Validate result (should have values and reach reasonable progress)
      if (volumeBased.length > 0 && volumeBased[volumeBased.length - 1] > 0) {
        return volumeBased;
      }
    }

    // Strategy 2: Ideal S-curve (for new projects or when preferred)
    if (useIdealCurve) {
      return calculateIdealSCurve(columns, steepnessFactor);
    }

    // Strategy 3: Linear fallback (last resort)
    if (fallbackToLinear) {
      return calculateLinearPlannedCurve(columns);
    }

    // Ultimate fallback: empty array
    return [];
  }

  function buildDataset(state, context = {}) {
    const columns = getColumns(state);
    if (!columns.length) {
      return null;
    }

    // Phase 2F.0: Use HARGA (cost) instead of volume
    const hargaLookup = buildHargaLookup(state);
    const volumeLookup = buildVolumeLookup(state); // Keep for planned curve (backward compatibility)
    const cellValues = buildCellValueMap(state);
    const pekerjaanIds = collectPekerjaanIds(state, cellValues);

    // Calculate total biaya from state (provided by API)
    let totalBiaya = parseFloat(state.totalBiayaProject || 0);

    // Fallback: calculate from hargaLookup if not provided
    if (!totalBiaya || totalBiaya <= 0) {
      pekerjaanIds.forEach((id) => {
        totalBiaya += getHargaForPekerjaan(hargaLookup, id, 0);
      });
    }

    // Legacy fallback: use volume if harga data not available
    let totalVolume = 0;
    const useHargaCalculation = totalBiaya > 0 && hargaLookup.size > 0;

    if (!useHargaCalculation) {
      // Fallback to volume-based calculation (legacy mode)
      pekerjaanIds.forEach((id) => {
        totalVolume += getVolumeForPekerjaan(volumeLookup, id, 1);
      });
      if (!Number.isFinite(totalVolume) || totalVolume <= 0) {
        totalVolume = pekerjaanIds.size || 1;
      }
    }

    const columnIndexById = new Map();
    columns.forEach((col, index) => {
      columnIndexById.set(String(col.id), index);
    });

    // Phase 2F.0: Calculate column totals using HARGA
    const columnTotals = new Array(columns.length).fill(0);
    cellValues.forEach((value, key) => {
      const [pekerjaanId, columnId] = String(key).split('-');
      const columnIndex = columnIndexById.get(columnId);
      if (columnIndex === undefined) {
        return;
      }
      const percent = parseFloat(value);
      if (!Number.isFinite(percent) || percent <= 0) {
        return;
      }

      if (useHargaCalculation) {
        // NEW: Harga-weighted calculation (Phase 2F.0)
        // Formula: (Total Harga Pekerjaan × Input Progress%) / Total Biaya × 100%
        const pekerjaanHarga = getHargaForPekerjaan(hargaLookup, pekerjaanId, 0);
        columnTotals[columnIndex] += pekerjaanHarga * (percent / 100);
      } else {
        // LEGACY: Volume-weighted calculation (fallback)
        const pekerjaanVolume = getVolumeForPekerjaan(volumeLookup, pekerjaanId, 1);
        columnTotals[columnIndex] += pekerjaanVolume * (percent / 100);
      }
    });

    const labels = columns.map((col, index) => {
      if (col.label) return col.label;
      if (col.rangeLabel) return `${col.label || ''} ${col.rangeLabel}`.trim();
      return `Week ${index + 1}`;
    });

    // Calculate PLANNED curve using hybrid approach
    // This will automatically choose the best method based on available data
    const plannedSeries = calculatePlannedCurve(
      columns,
      volumeLookup,
      cellValues,
      totalVolume,
      getVolumeForPekerjaan,
      context.scurveOptions || {}
    );

    // Calculate ACTUAL curve
    // Phase 2F.0: Use HARGA (cost) instead of volume
    const actualSeries = [];
    let cumulativeActual = 0;

    columns.forEach((col, index) => {
      cumulativeActual += columnTotals[index] || 0;

      let actualPercent = 0;
      if (useHargaCalculation && totalBiaya > 0) {
        // NEW: Harga-weighted percentage (Phase 2F.0)
        actualPercent = Math.min(100, Math.max(0, (cumulativeActual / totalBiaya) * 100));
      } else if (totalVolume > 0) {
        // LEGACY: Volume-weighted percentage (fallback)
        actualPercent = Math.min(100, Math.max(0, (cumulativeActual / totalVolume) * 100));
      }

      actualSeries.push(Number(actualPercent.toFixed(2)));
    });

    // Build detailed data for tooltips
    const details = [];
    columns.forEach((col, index) => {
      details.push({
        label: labels[index],
        planned: plannedSeries[index] || 0,
        actual: actualSeries[index] || 0,
        variance: Number(((actualSeries[index] || 0) - (plannedSeries[index] || 0)).toFixed(2)),
        start: col.startDate instanceof Date ? col.startDate : (col.startDate ? new Date(col.startDate) : null),
        end: col.endDate instanceof Date ? col.endDate : (col.endDate ? new Date(col.endDate) : null),
        tooltip: col.tooltip || labels[index],
      });
    });

    return {
      labels,
      planned: plannedSeries,
      actual: actualSeries,
      details,
      totalVolume, // Legacy (for backward compatibility)
      totalBiaya, // Phase 2F.0: Total project cost
      columnTotals,
      useHargaCalculation, // Phase 2F.0: Flag indicating which calculation method used
    };
  }

  function buildFallbackDataset() {
    return {
      labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
      planned: [0, 33, 66, 100],
      actual: [0, 20, 45, 70],
      details: [],
      totalVolume: 1,
      columnTotals: [],
    };
  }

  function formatDateLabel(date) {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
      return '';
    }
    return date.toLocaleDateString('id-ID', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  }

  /**
   * Format number as Indonesian Rupiah
   * Phase 2F.0: Display currency in Kurva S tooltips
   *
   * @param {number} amount - Amount in Rupiah
   * @returns {string} Formatted currency string (e.g., "Rp 1.234.567")
   */
  function formatRupiah(amount) {
    if (!Number.isFinite(amount)) return 'Rp 0';

    // Format with thousand separators (Indonesian style)
    const formatted = Math.round(amount).toLocaleString('id-ID');
    return `Rp ${formatted}`;
  }

  function createChartOption(dataset) {
    const colors = getThemeColors();
    const data = dataset || buildFallbackDataset();

    return {
      backgroundColor: 'transparent',
      color: [colors.plannedLine, colors.actualLine],
      tooltip: {
        trigger: 'axis',
        formatter: (params) => {
          if (!params || !params.length) return '';
          const index = params[0].dataIndex;
          const detail = data.details[index] || {};
          const label = detail.label || data.labels[index];
          const planned = data.planned[index] ?? 0;
          const actual = data.actual[index] ?? 0;
          const variance = detail.variance ?? (actual - planned);
          const start = formatDateLabel(detail.start);
          const end = formatDateLabel(detail.end);

          // Phase 2F.0: Calculate currency amounts if using harga calculation
          const useHarga = data.useHargaCalculation && data.totalBiaya > 0;
          let plannedAmount = '';
          let actualAmount = '';

          if (useHarga) {
            const plannedRp = (data.totalBiaya * planned) / 100;
            const actualRp = (data.totalBiaya * actual) / 100;
            plannedAmount = formatRupiah(plannedRp);
            actualAmount = formatRupiah(actualRp);
          }

          // Determine variance status and color
          let varianceText = '';
          let varianceColor = '';
          if (variance > 5) {
            varianceText = `+${variance.toFixed(1)}% (Ahead of schedule)`;
            varianceColor = '#22c55e'; // Green
          } else if (variance < -5) {
            varianceText = `${variance.toFixed(1)}% (Behind schedule)`;
            varianceColor = '#ef4444'; // Red
          } else {
            varianceText = `${variance >= 0 ? '+' : ''}${variance.toFixed(1)}% (On track)`;
            varianceColor = '#3b82f6'; // Blue
          }

          return [
            `<strong>${label}</strong>`,
            start && end ? `<div style="font-size:0.85em;color:#6b7280;margin:4px 0;">Periode: ${start} - ${end}</div>` : '',
            '<div style="margin-top:8px;">',
            useHarga
              ? `<div style="margin:4px 0;">Rencana: <strong>${planned.toFixed(1)}%</strong> <span style="font-size:0.9em;color:#6b7280;">(${plannedAmount})</span></div>`
              : `<div style="margin:4px 0;">Rencana: <strong>${planned.toFixed(1)}%</strong></div>`,
            useHarga
              ? `<div style="margin:4px 0;">Aktual: <strong>${actual.toFixed(1)}%</strong> <span style="font-size:0.9em;color:#6b7280;">(${actualAmount})</span></div>`
              : `<div style="margin:4px 0;">Aktual: <strong>${actual.toFixed(1)}%</strong></div>`,
            `<div style="margin:4px 0;color:${varianceColor};">Variance: <strong>${varianceText}</strong></div>`,
            '</div>',
          ].filter(Boolean).join('');
        },
      },
      legend: {
        data: ['Planned', 'Actual'],
        textStyle: {
          color: colors.text,
        },
      },
      grid: {
        left: '4%',
        right: '4%',
        top: '12%',
        bottom: '6%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: data.labels,
        axisLabel: {
          color: colors.axis,
        },
        axisLine: {
          lineStyle: {
            color: colors.gridLine,
          },
        },
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        axisLabel: {
          formatter: '{value}%',
          color: colors.axis,
        },
        splitLine: {
          lineStyle: {
            color: colors.gridLine,
            type: 'dashed',
          },
        },
      },
      series: [
        {
          name: 'Planned',
          type: 'line',
          smooth: true,
          data: data.planned,
          lineStyle: {
            color: colors.plannedLine,
            width: 2,
            type: 'dashed',
          },
          areaStyle: {
            color: colors.plannedArea,
          },
          symbolSize: 6,
        },
        {
          name: 'Actual',
          type: 'line',
          smooth: true,
          data: data.actual,
          lineStyle: {
            color: colors.actualLine,
            width: 3,
          },
          areaStyle: {
            color: colors.actualArea,
          },
          symbolSize: 7,
        },
      ],
    };
  }

  function ensureChartInstance(state) {
    if (!window.echarts) {
      return 'legacy';
    }
    const chartDom = resolveDom(state);
    if (!chartDom) {
      return 'legacy';
    }

    if (!state.scurveChart) {
      state.scurveChart = echarts.init(chartDom);
    }
    return state.scurveChart;
  }

  function refresh(context = {}) {
    const state = resolveState(context.state);
    if (!state) {
      return 'legacy';
    }

    const chart = ensureChartInstance(state);
    if (chart === 'legacy') {
      return 'legacy';
    }

    const dataset = buildDataset(state, context) || buildFallbackDataset();
    const option = createChartOption(dataset);

    chart.setOption(option, true);
    moduleStore.dataset = dataset;
    moduleStore.option = option;

    return chart;
  }

  function init(context = {}) {
    return refresh(context);
  }

  function resize(context = {}) {
    const state = resolveState(context.state);
    if (!state || !state.scurveChart) {
      return 'legacy';
    }
    try {
      state.scurveChart.resize();
    } catch (error) {
      bootstrap.log.warn('Kelola Tahapan Kurva S: resize failed', error);
    }
    return state.scurveChart;
  }

  function getChart(context = {}) {
    const state = resolveState(context.state);
    if (!state) return null;
    return state.scurveChart || null;
  }

  Object.assign(moduleStore, {
    resolveState,
    resolveDom,
    buildDataset,
    refresh,
    init,
    resize,
    getChart,
  });

  bootstrap.registerModule(meta.id, {
    namespace: meta.namespace,
    pageId: manifest.pageId,
    description: meta.description,
    onRegister(context) {
      bootstrap.log.info('Kelola Tahapan Kurva-S module registered.');
      if (context && context.emit) {
        context.emit('kelola_tahapan.kurva_s:registered', { manifest, meta });
      }
    },
    init: (...args) => (moduleStore.init || bridge().init || noop)(...args),
    refresh: (...args) => (moduleStore.refresh || bridge().refresh || noop)(...args),
    resize: (...args) => (moduleStore.resize || bridge().resize || noop)(...args),
    getChart: (...args) => (moduleStore.getChart || bridge().getChart || noop)(...args),
  });
})();
