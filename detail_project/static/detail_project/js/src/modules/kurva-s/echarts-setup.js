/**
 * Kurva-S (S-Curve) Chart Module
 * Modern ES6 implementation for project progress visualization
 *
 * Displays planned vs. actual progress curves over time periods.
 * Supports multiple calculation strategies:
 * - Volume-based: Real data from pekerjaan assignments
 * - Sigmoid: Mathematical S-curve interpolation
 * - Linear: Simple linear distribution fallback
 *
 * Migrated from: kurva_s_module.js
 * Date: 2025-11-20
 */

import * as echarts from 'echarts';
import {
  getThemeColors,
  setupThemeObserver,
  normalizeDate,
  getSortedColumns,
  buildVolumeLookup,
  getVolumeForPekerjaan,
  buildHargaLookup,
  getHargaForPekerjaan,
  buildCellValueMap,
  collectPekerjaanIds,
  formatPercentage,
  formatRupiah,
  createResizeHandler,
  setupResizeObserver,
} from '../shared/chart-utils.js';

// =========================================================================
// CONSTANTS
// =========================================================================

const LOG_PREFIX = '[KurvaSChart]';
const DEFAULT_OPTIONS = {
  useIdealCurve: true,
  steepnessFactor: 0.8,
  fallbackToLinear: true,
  smoothCurves: true,
  showArea: true,
  responsive: true,
};

// =========================================================================
// KURVA-S CHART CLASS
// =========================================================================

/**
 * KurvaSChart - S-Curve chart visualization
 *
 * @class
 * @example
 * const chart = new KurvaSChart(state, {
 *   useIdealCurve: true,
 *   steepnessFactor: 0.8
 * });
 * chart.initialize(containerElement);
 * chart.update(newData);
 */
export class KurvaSChart {
  /**
   * Create a new KurvaSChart instance
   *
   * @param {Object} state - Application state
   * @param {Object} options - Chart configuration options
   */
  constructor(state, options = {}) {
    this.state = state;
    this.options = { ...DEFAULT_OPTIONS, ...options };

    // Chart instance and observers
    this.chartInstance = null;
    this.themeObserver = null;
    this.resizeObserver = null;
    this.resizeHandler = null;

    // Data cache
    this.currentDataset = null;
    this.currentOption = null;

    console.log(LOG_PREFIX, 'Chart instance created with options:', this.options);
  }

  /**
   * Initialize chart with container element
   *
   * @param {HTMLElement} container - DOM element to render chart
   * @returns {boolean} Success status
   */
  initialize(container) {
    if (!container) {
      console.error(LOG_PREFIX, 'Container element is required');
      return false;
    }

    if (!window.echarts) {
      console.error(LOG_PREFIX, 'ECharts library not loaded');
      return false;
    }

    try {
      // Initialize ECharts instance
      this.chartInstance = echarts.init(container);
      console.log(LOG_PREFIX, 'ECharts instance initialized');

      // Setup theme observer
      this._setupThemeObserver();

      // Setup resize handling
      if (this.options.responsive) {
        this._setupResizeHandling(container);
      }

      // Initial render
      this.update();

      return true;
    } catch (error) {
      console.error(LOG_PREFIX, 'Initialization failed:', error);
      return false;
    }
  }

  /**
   * Update chart with new data
   *
   * @param {Object} data - Optional data override
   * @returns {boolean} Success status
   */
  update(data = null) {
    if (!this.chartInstance) {
      console.error(LOG_PREFIX, 'Chart not initialized. Call initialize() first.');
      return false;
    }

    try {
      // Build dataset from state or use provided data
      const dataset = data || this._buildDataset();

      if (!dataset) {
        console.warn(LOG_PREFIX, 'No data available, using fallback dataset');
        const fallbackDataset = this._buildFallbackDataset();
        this._renderChart(fallbackDataset);
        return false;
      }

      // Render chart with dataset
      this._renderChart(dataset);

      // Cache current data
      this.currentDataset = dataset;

      console.log(LOG_PREFIX, 'Chart updated successfully');
      return true;
    } catch (error) {
      console.error(LOG_PREFIX, 'Update failed:', error);
      return false;
    }
  }

  /**
   * Dispose chart and cleanup resources
   */
  dispose() {
    console.log(LOG_PREFIX, 'Disposing chart...');

    // Dispose ECharts instance
    if (this.chartInstance) {
      this.chartInstance.dispose();
      this.chartInstance = null;
    }

    // Disconnect theme observer
    if (this.themeObserver) {
      this.themeObserver.disconnect();
      this.themeObserver = null;
    }

    // Disconnect resize observer
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
      this.resizeObserver = null;
    }

    // Remove resize handler
    if (this.resizeHandler) {
      window.removeEventListener('resize', this.resizeHandler);
      this.resizeHandler = null;
    }

    // Clear cache
    this.currentDataset = null;
    this.currentOption = null;

    console.log(LOG_PREFIX, 'Chart disposed');
  }

  /**
   * Resize chart (call when container size changes)
   */
  resize() {
    if (this.chartInstance) {
      try {
        this.chartInstance.resize();
        console.log(LOG_PREFIX, 'Chart resized');
      } catch (error) {
        console.error(LOG_PREFIX, 'Resize failed:', error);
      }
    }
  }

  /**
   * Get current chart instance
   *
   * @returns {Object|null} ECharts instance
   */
  getChartInstance() {
    return this.chartInstance;
  }

  /**
   * Get current dataset
   *
   * @returns {Object|null} Current dataset
   */
  getCurrentDataset() {
    return this.currentDataset;
  }

  // =========================================================================
  // PRIVATE METHODS - SETUP
  // =========================================================================

  /**
   * Setup theme observer for automatic theme switching
   * @private
   */
  _setupThemeObserver() {
    this.themeObserver = setupThemeObserver((theme) => {
      console.log(LOG_PREFIX, 'Theme changed to:', theme);

      // Re-render chart with new theme colors
      if (this.currentDataset) {
        this._renderChart(this.currentDataset);
      }
    });
  }

  /**
   * Setup resize handling for responsive charts
   * @private
   */
  _setupResizeHandling(container) {
    // Debounced window resize handler
    this.resizeHandler = createResizeHandler(() => {
      this.resize();
    }, 150);

    window.addEventListener('resize', this.resizeHandler);

    // ResizeObserver for container size changes
    this.resizeObserver = setupResizeObserver(container, () => {
      this.resize();
    });
  }

  // =========================================================================
  // PRIVATE METHODS - DATA BUILDING
  // =========================================================================

  /**
   * Build dataset from state
   * @private
   * @returns {Object|null} Dataset or null if insufficient data
   */
  _buildDataset() {
    const columns = getSortedColumns(this.state.timeColumns);

    if (!columns || columns.length === 0) {
      console.warn(LOG_PREFIX, 'No time columns available');
      return null;
    }

    // Phase 2F.0: Build both volume and harga lookups
    const volumeLookup = buildVolumeLookup(this.state);
    const hargaLookup = buildHargaLookup(this.state);
    const cellValues = buildCellValueMap(this.state);
    const pekerjaanIds = collectPekerjaanIds(this.state, cellValues);

    // Phase 2F.0: Calculate total biaya from state (provided by API)
    let totalBiaya = parseFloat(this.state.totalBiayaProject || 0);

    // Fallback: calculate from hargaLookup if not provided
    if (!totalBiaya || totalBiaya <= 0) {
      pekerjaanIds.forEach((id) => {
        totalBiaya += getHargaForPekerjaan(hargaLookup, id, 0);
      });
    }

    // Determine if we should use harga calculation
    const useHargaCalculation = totalBiaya > 0 && hargaLookup.size > 0;

    // Legacy fallback: calculate total volume
    let totalVolume = 0;
    if (!useHargaCalculation) {
      pekerjaanIds.forEach((id) => {
        totalVolume += getVolumeForPekerjaan(volumeLookup, id, 1);
      });

      if (!Number.isFinite(totalVolume) || totalVolume <= 0) {
        totalVolume = pekerjaanIds.size || 1;
      }
    }

    console.log(LOG_PREFIX, 'Calculation mode:', useHargaCalculation ? 'HARGA-BASED' : 'VOLUME-BASED (fallback)');
    if (useHargaCalculation) {
      console.log(LOG_PREFIX, `Total biaya: Rp ${totalBiaya.toLocaleString('id-ID')}`);
    }

    // Build column index mapping
    const columnIndexById = new Map();
    columns.forEach((col, index) => {
      columnIndexById.set(String(col.id), index);
    });

    // Calculate column totals (weighted actual progress)
    // Phase 2F.0: Pass harga lookup and calculation mode
    const columnTotals = this._calculateColumnTotals(
      columns,
      cellValues,
      volumeLookup,
      hargaLookup,
      columnIndexById,
      useHargaCalculation
    );

    // Generate labels
    const labels = this._generateLabels(columns);

    // Calculate planned curve using best strategy
    const plannedSeries = this._calculatePlannedCurve(
      columns,
      volumeLookup,
      cellValues,
      totalVolume || totalBiaya  // Use biaya for weighting if harga mode
    );

    // Calculate actual curve
    // Phase 2F.0: Pass totalBiaya and calculation mode
    const actualSeries = this._calculateActualCurve(
      columns,
      columnTotals,
      useHargaCalculation ? totalBiaya : totalVolume,
      useHargaCalculation
    );

    // Build detail data for tooltips
    const details = this._buildDetailData(
      columns,
      labels,
      plannedSeries,
      actualSeries
    );

    return {
      labels,
      planned: plannedSeries,
      actual: actualSeries,
      details,
      totalVolume,           // Legacy (for backward compatibility)
      totalBiaya,            // Phase 2F.0: Total project cost
      columnTotals,
      useHargaCalculation,   // Phase 2F.0: Flag indicating calculation method
    };
  }

  /**
   * Calculate column totals (weighted actual progress)
   * Phase 2F.0: Support both volume and harga-based calculation
   * @private
   */
  _calculateColumnTotals(columns, cellValues, volumeLookup, hargaLookup, columnIndexById, useHargaCalculation) {
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
        // Phase 2F.0: Harga-weighted calculation
        const pekerjaanHarga = getHargaForPekerjaan(hargaLookup, pekerjaanId, 0);
        columnTotals[columnIndex] += pekerjaanHarga * (percent / 100);
      } else {
        // Legacy: Volume-weighted calculation
        const pekerjaanVolume = getVolumeForPekerjaan(volumeLookup, pekerjaanId, 1);
        columnTotals[columnIndex] += pekerjaanVolume * (percent / 100);
      }
    });

    return columnTotals;
  }

  /**
   * Generate labels for x-axis
   * @private
   */
  _generateLabels(columns) {
    return columns.map((col, index) => {
      if (col.label) return col.label;
      if (col.rangeLabel) return `${col.label || ''} ${col.rangeLabel}`.trim();
      return `Week ${index + 1}`;
    });
  }

  /**
   * Build detail data for tooltips
   * @private
   */
  _buildDetailData(columns, labels, plannedSeries, actualSeries) {
    const details = [];

    columns.forEach((col, index) => {
      details.push({
        label: labels[index],
        planned: plannedSeries[index] || 0,
        actual: actualSeries[index] || 0,
        variance: Number(((actualSeries[index] || 0) - (plannedSeries[index] || 0)).toFixed(2)),
        start: normalizeDate(col.startDate),
        end: normalizeDate(col.endDate),
        tooltip: col.tooltip || labels[index],
      });
    });

    return details;
  }

  /**
   * Build fallback dataset (when no data available)
   * @private
   */
  _buildFallbackDataset() {
    return {
      labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
      planned: [0, 33, 66, 100],
      actual: [0, 20, 45, 70],
      details: [],
      totalVolume: 1,
      columnTotals: [],
    };
  }

  // =========================================================================
  // PRIVATE METHODS - S-CURVE CALCULATIONS
  // =========================================================================

  /**
   * Calculate planned curve using best available strategy
   * @private
   * @param {Array} columns - Time columns
   * @param {Map} volumeLookup - Volume lookup map
   * @param {Map} cellValues - Cell values map
   * @param {number} totalVolume - Total project volume
   * @returns {Array<number>} Planned percentages
   */
  _calculatePlannedCurve(columns, volumeLookup, cellValues, totalVolume) {
    // Strategy 1: Volume-based (if assignments exist)
    const hasAssignments = cellValues && cellValues.size > 0;

    if (hasAssignments) {
      const volumeBased = this._calculateVolumeBasedPlannedCurve(
        columns,
        volumeLookup,
        cellValues,
        totalVolume
      );

      // Validate result
      if (volumeBased.length > 0 && volumeBased[volumeBased.length - 1] > 0) {
        console.log(LOG_PREFIX, 'Using volume-based planned curve');
        return volumeBased;
      }
    }

    // Strategy 2: Ideal S-curve (for new projects)
    if (this.options.useIdealCurve) {
      console.log(LOG_PREFIX, 'Using ideal sigmoid S-curve');
      return this._calculateIdealSCurve(columns, this.options.steepnessFactor);
    }

    // Strategy 3: Linear fallback
    if (this.options.fallbackToLinear) {
      console.log(LOG_PREFIX, 'Using linear fallback curve');
      return this._calculateLinearPlannedCurve(columns);
    }

    // Ultimate fallback
    console.warn(LOG_PREFIX, 'No calculation strategy available');
    return [];
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
   * @private
   * @param {Array} columns - Time columns
   * @param {Map} volumeLookup - Volume lookup map
   * @param {Map} cellValues - Cell values map
   * @param {number} totalVolume - Total project volume
   * @returns {Array<number>} Planned percentages
   */
  _calculateVolumeBasedPlannedCurve(columns, volumeLookup, cellValues, totalVolume) {
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
   * @private
   * @param {Array} columns - Time columns
   * @param {number} steepnessFactor - Curve steepness (default: 0.8)
   * @returns {Array<number>} Planned percentages
   */
  _calculateIdealSCurve(columns, steepnessFactor = 0.8) {
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
   * @private
   * @param {Array} columns - Time columns
   * @returns {Array<number>} Planned percentages
   */
  _calculateLinearPlannedCurve(columns) {
    const plannedStep = columns.length > 0 ? 100 / columns.length : 0;
    const plannedSeries = [];

    columns.forEach((col, index) => {
      const plannedPercent = Math.min(100, Math.max(0, plannedStep * (index + 1)));
      plannedSeries.push(Number(plannedPercent.toFixed(2)));
    });

    return plannedSeries;
  }

  /**
   * Calculate actual curve (weighted from assignments)
   * Phase 2F.0: Support both volume and harga-weighted calculation
   *
   * ALGORITHM:
   * For each column, calculate weighted actual progress:
   * 1. Weight each pekerjaan's progress by its volume OR harga
   * 2. Sum to get total actual volume/harga for this period
   * 3. Accumulate across periods for cumulative curve
   * 4. Convert to percentage of total project volume/harga
   *
   * @private
   * @param {Array} columns - Time columns
   * @param {Array<number>} columnTotals - Weighted progress per column
   * @param {number} total - Total project volume or harga
   * @param {boolean} useHargaCalculation - Whether using harga mode
   * @returns {Array<number>} Actual percentages
   */
  _calculateActualCurve(columns, columnTotals, total, useHargaCalculation = false) {
    const actualSeries = [];
    let cumulativeActual = 0;

    columns.forEach((col, index) => {
      cumulativeActual += columnTotals[index] || 0;
      const actualPercent = total > 0
        ? Math.min(100, Math.max(0, (cumulativeActual / total) * 100))
        : 0;
      actualSeries.push(Number(actualPercent.toFixed(2)));
    });

    return actualSeries;
  }

  // =========================================================================
  // PRIVATE METHODS - CHART RENDERING
  // =========================================================================

  /**
   * Render chart with dataset
   * @private
   * @param {Object} dataset - Chart dataset
   */
  _renderChart(dataset) {
    const option = this._createChartOption(dataset);
    this.chartInstance.setOption(option, true);
    this.currentOption = option;
  }

  /**
   * Create ECharts option object
   * @private
   * @param {Object} dataset - Chart dataset
   * @returns {Object} ECharts option
   */
  _createChartOption(dataset) {
    const colors = getThemeColors();
    const data = dataset || this._buildFallbackDataset();

    return {
      backgroundColor: 'transparent',
      color: [colors.plannedLine, colors.actualLine],

      tooltip: {
        trigger: 'axis',
        formatter: (params) => this._formatTooltip(params, data, colors),
      },

      legend: {
        data: ['Planned', 'Actual'],
        textStyle: {
          color: colors.text,
        },
        top: '2%',
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
          rotate: data.labels.length > 10 ? 45 : 0,
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
          smooth: this.options.smoothCurves,
          data: data.planned,
          lineStyle: {
            color: colors.plannedLine,
            width: 2,
            type: 'dashed',
          },
          areaStyle: this.options.showArea ? {
            color: colors.plannedArea,
          } : undefined,
          symbolSize: 6,
        },
        {
          name: 'Actual',
          type: 'line',
          smooth: this.options.smoothCurves,
          data: data.actual,
          lineStyle: {
            color: colors.actualLine,
            width: 3,
          },
          areaStyle: this.options.showArea ? {
            color: colors.actualArea,
          } : undefined,
          symbolSize: 7,
        },
      ],
    };
  }

  /**
   * Format tooltip content
   * Phase 2F.0: Show currency amounts if using harga calculation
   * @private
   */
  _formatTooltip(params, data, colors) {
    if (!params || !params.length) return '';

    const index = params[0].dataIndex;
    const detail = data.details[index] || {};
    const label = detail.label || data.labels[index];
    const planned = data.planned[index] ?? 0;
    const actual = data.actual[index] ?? 0;
    const variance = detail.variance ?? (actual - planned);

    // Format dates
    const start = this._formatDateLabel(detail.start);
    const end = this._formatDateLabel(detail.end);

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

    // Build tooltip HTML
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
  }

  /**
   * Format date for tooltip display
   * @private
   */
  _formatDateLabel(date) {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
      return '';
    }

    return date.toLocaleDateString('id-ID', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  }
}

// =========================================================================
// FACTORY FUNCTION
// =========================================================================

/**
 * Create a new KurvaSChart instance
 *
 * @param {Object} state - Application state
 * @param {Object} options - Chart options
 * @returns {KurvaSChart} Chart instance
 */
export function createKurvaSChart(state, options = {}) {
  return new KurvaSChart(state, options);
}

// =========================================================================
// EXPORTS
// =========================================================================

export default KurvaSChart;
