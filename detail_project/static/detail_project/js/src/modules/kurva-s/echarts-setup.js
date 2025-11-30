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
import { ensureWeekZeroDataset } from './week-zero-helpers.js';

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
  enableCostView: true,  // Phase 1: Enable cost-based view toggle
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

    // Phase 1: Cost view support
    this.viewMode = 'progress';  // 'progress' or 'cost'
    this.costData = null;        // Cost data from API
    this.isLoadingCostData = false;

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
   * Phase 1: Fetch cost data from API
   * @returns {Promise<Object|null>} Cost data or null if failed
   */
  async fetchCostData() {
    if (!this.options.enableCostView) {
      console.log(LOG_PREFIX, 'Cost view disabled');
      return null;
    }

    const projectId = this.state.projectId;
    if (!projectId) {
      console.warn(LOG_PREFIX, 'No project ID available');
      return null;
    }

    if (this.isLoadingCostData) {
      console.log(LOG_PREFIX, 'Cost data already loading...');
      return null;
    }

    try {
      this.isLoadingCostData = true;
      console.log(LOG_PREFIX, `Fetching cost data for project ${projectId}...`);

      const url = `/detail_project/api/v2/project/${projectId}/kurva-s-harga/`;
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      // Cache cost data
      this.costData = data;

      console.log(LOG_PREFIX, 'Cost data loaded:', {
        totalCost: formatRupiah(data.summary?.total_project_cost || 0),
        weeks: data.summary?.total_weeks || 0,
        plannedWeeks: data.weeklyData?.planned?.length || 0,
        actualWeeks: data.weeklyData?.actual?.length || 0,
      });

      return data;
    } catch (error) {
      console.error(LOG_PREFIX, 'Failed to fetch cost data:', error);
      return null;
    } finally {
      this.isLoadingCostData = false;
    }
  }

  /**
   * Phase 1: Toggle between progress and cost view
   * @param {string} mode - 'progress' or 'cost'
   * @returns {boolean} Success status
   */
  async toggleView(mode = null) {
    if (!this.options.enableCostView) {
      console.warn(LOG_PREFIX, 'Cost view not enabled');
      return false;
    }

    // Auto-toggle if no mode specified
    const newMode = mode || (this.viewMode === 'progress' ? 'cost' : 'progress');

    if (newMode !== 'progress' && newMode !== 'cost') {
      console.error(LOG_PREFIX, 'Invalid view mode:', newMode);
      return false;
    }

    console.log(LOG_PREFIX, `Switching view: ${this.viewMode} → ${newMode}`);

    // If switching to cost view, fetch cost data first
    if (newMode === 'cost' && !this.costData) {
      const costData = await this.fetchCostData();
      if (!costData) {
        console.error(LOG_PREFIX, 'Failed to load cost data, staying in progress view');
        return false;
      }
    }

    // Update view mode
    this.viewMode = newMode;

    // Re-render chart
    if (newMode === 'progress') {
      // Use existing progress dataset
      this.update();
    } else {
      // Use cost dataset
      this.update(this._buildCostDataset());
    }

    console.log(LOG_PREFIX, `View switched to: ${newMode}`);
    return true;
  }

  /**
   * Phase 1: Build dataset for cost view
   * @returns {Object} Cost dataset for chart
   * @private
   */
  _buildCostDataset() {
    if (!this.costData) {
      console.error(LOG_PREFIX, 'No cost data available');
      return null;
    }

    const weeklyData = this.costData.weeklyData;
    const summary = this.costData.summary;
    const evm = this.costData.evm;

    if (evm && Array.isArray(evm.labels) && evm.labels.length > 0) {
      const totalCost = evm.summary?.bac || summary?.total_project_cost || 0;
      return ensureWeekZeroDataset({
        labels: evm.labels,
        planned: evm.pv_percent || [],
        actual: evm.ev_percent || [],
        acSeries: evm.ac_percent || evm.ev_percent || [],
        details: {
          totalCost,
          weeks: weeklyData?.planned || [],
          actualWeeks: weeklyData?.actual || [],
          evmSummary: evm.summary,
          evm,
        },
        evm,
        totalBiaya: totalCost,
        useHargaCalculation: true,
        viewMode: 'cost',
      });
    }

    // Extract labels (week identifiers)
    const labels = (weeklyData.planned || []).map((w) => `W${w.week_number}`);

    // Extract planned cumulative cost percentages
    const plannedSeries = (weeklyData.planned || []).map((w) => w.cumulative_percent);

    // Extract actual cumulative cost percentages
    const actualSeries = (weeklyData.actual || []).map((w) => w.cumulative_percent);
    const acSeries = actualSeries.length ? actualSeries : (weeklyData.earned || []).map((w) => w.cumulative_percent);

    // Build details for tooltips
    const details = {
      totalCost: summary?.total_project_cost || 0,
      plannedCost: summary?.planned_cost || 0,
      actualCost: summary?.actual_cost || 0,
      weeks: weeklyData.planned || [],
      actualWeeks: weeklyData.actual || [],
      viewMode: 'cost',
    };

    console.log(LOG_PREFIX, 'Cost dataset built:', {
      labels: labels.length,
      plannedPoints: plannedSeries.length,
      actualPoints: actualSeries.length,
      totalCost: formatRupiah(details.totalCost),
    });

    return ensureWeekZeroDataset({
      labels,
      planned: plannedSeries,
      actual: actualSeries,
      acSeries,
      details,
      totalBiaya: details.totalCost,
      useHargaCalculation: true,
      viewMode: 'cost',
    });
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

    // Phase 0.5: Use StateManager.getAllCellsForMode() instead of buildCellValueMap()
    // StateManager handles merging assignmentMap + modifiedCells with smart caching
    // Planned curve = data from 'planned' mode
    // Actual curve = data from 'actual' mode
    const stateManager = this.state.stateManager;

    if (!stateManager) {
      console.error(LOG_PREFIX, 'StateManager not available, falling back to direct state access');
      // Fallback for backward compatibility (should not happen after Phase 0.3)
      const plannedState = this.state.plannedState || this.state;
      const actualState = this.state.actualState || this.state;
      var plannedCellValues = buildCellValueMap(plannedState);
      var actualCellValues = buildCellValueMap(actualState);
    } else {
      // Phase 0.5: Use StateManager's optimized merge
      var plannedCellValues = stateManager.getAllCellsForMode('planned');
      var actualCellValues = stateManager.getAllCellsForMode('actual');
    }

    // Debug logging
    console.log(LOG_PREFIX, 'Planned cell values:', plannedCellValues.size, 'cells');
    console.log(LOG_PREFIX, 'Actual cell values:', actualCellValues.size, 'cells');

    if (stateManager) {
      // Phase 0.5: Log StateManager stats
      const stats = stateManager.getStats();
      console.log(LOG_PREFIX, 'StateManager stats:', {
        currentMode: stats.currentMode,
        planned: `${stats.planned.assignmentCount} assignments, ${stats.planned.modifiedCount} modified`,
        actual: `${stats.actual.assignmentCount} assignments, ${stats.actual.modifiedCount} modified`
      });
    }

    if (plannedCellValues.size > 0) {
      console.log(LOG_PREFIX, 'Sample planned values:', Array.from(plannedCellValues.entries()).slice(0, 3));
    }
    if (actualCellValues.size > 0) {
      console.log(LOG_PREFIX, 'Sample actual values:', Array.from(actualCellValues.entries()).slice(0, 3));
    }

    // Collect all pekerjaan IDs from both modes
    const pekerjaanIds = new Set([
      ...collectPekerjaanIds(this.state, plannedCellValues),
      ...collectPekerjaanIds(this.state, actualCellValues)
    ]);

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

    // Generate labels
    const labels = this._generateLabels(columns);

    // Calculate planned curve using Perencanaan mode data
    // Phase 2F.0: Pass harga lookup and calculation mode for planned curve
    const plannedSeries = this._calculatePlannedCurve(
      columns,
      volumeLookup,
      hargaLookup,
      plannedCellValues,  // Data from Perencanaan mode
      useHargaCalculation ? totalBiaya : totalVolume,
      columnIndexById,
      useHargaCalculation
    );

    // Calculate actual curve using Realisasi mode data
    // Phase 2F.0: Calculate column totals from actual cell values
    const actualColumnTotals = this._calculateColumnTotals(
      columns,
      actualCellValues,  // Data from Realisasi mode
      volumeLookup,
      hargaLookup,
      columnIndexById,
      useHargaCalculation
    );

    const actualSeries = this._calculateActualCurve(
      columns,
      actualColumnTotals,
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

    return ensureWeekZeroDataset({
      labels,
      planned: plannedSeries,
      actual: actualSeries,
      details,
      totalVolume,           // Legacy (for backward compatibility)
      totalBiaya,            // Phase 2F.0: Total project cost
      columnTotals: actualColumnTotals,  // Use actual column totals for display
      useHargaCalculation,   // Phase 2F.0: Flag indicating calculation method
    });
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
    return ensureWeekZeroDataset({
      labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
      planned: [0, 33, 66, 100],
      actual: [0, 20, 45, 70],
      details: [],
      totalVolume: 1,
      columnTotals: [],
    });
  }


  // =========================================================================
  // PRIVATE METHODS - S-CURVE CALCULATIONS
  // =========================================================================

  /**
   * Calculate planned curve using best available strategy
   * Phase 2F.0: Updated to support harga-based calculation
   *
   * @private
   * @param {Array} columns - Time columns
   * @param {Map} volumeLookup - Volume lookup map
   * @param {Map} hargaLookup - Harga lookup map (Phase 2F.0)
   * @param {Map} cellValues - Cell values map (from grid input)
   * @param {number} total - Total project volume or harga
   * @param {Map} columnIndexById - Column ID to index mapping
   * @param {boolean} useHargaCalculation - Whether to use harga-weighted calculation
   * @returns {Array<number>} Planned percentages
   */
  _calculatePlannedCurve(columns, volumeLookup, hargaLookup, cellValues, total, columnIndexById, useHargaCalculation) {
    // Phase 2F.0: Check if we have planned data from grid
    // Planned data should come from state.plannedState (Perencanaan mode)
    const hasPlannedData = cellValues && cellValues.size > 0;

    if (hasPlannedData) {
      // Strategy 1: Calculate from grid input (Perencanaan mode data)
      // Use same harga-weighted calculation as actual curve
      console.log(LOG_PREFIX, 'Calculating planned curve from grid input (Perencanaan mode)');

      return this._calculateGridBasedPlannedCurve(
        columns,
        cellValues,
        volumeLookup,
        hargaLookup,
        columnIndexById,
        total,
        useHargaCalculation
      );
    }

    // Strategy 2: Ideal S-curve (for new projects without data)
    if (this.options.useIdealCurve) {
      console.log(LOG_PREFIX, 'Using ideal sigmoid S-curve (no planned data yet)');
      return this._calculateIdealSCurve(columns, this.options.steepnessFactor);
    }

    // Strategy 3: Linear fallback
    if (this.options.fallbackToLinear) {
      console.log(LOG_PREFIX, 'Using linear fallback curve');
      return this._calculateLinearPlannedCurve(columns);
    }

    // Ultimate fallback: empty curve
    console.warn(LOG_PREFIX, 'No calculation strategy available, returning empty curve');
    return new Array(columns.length).fill(0);
  }

  /**
   * Calculate planned curve from grid input data (Perencanaan mode)
   * Phase 2F.0: Uses same harga-weighted logic as actual curve
   *
   * ALGORITHM:
   * For each time period (column):
   *   1. Get all cell assignments for this period from grid
   *   2. Calculate weighted progress using harga or volume
   *   3. Accumulate to get cumulative planned progress
   *   4. Convert to percentage of total project cost/volume
   *
   * This ensures planned and actual curves use consistent calculation method.
   *
   * @private
   * @param {Array} columns - Time columns
   * @param {Map} cellValues - Cell values map (from Perencanaan mode)
   * @param {Map} volumeLookup - Volume lookup map
   * @param {Map} hargaLookup - Harga lookup map
   * @param {Map} columnIndexById - Column ID to index mapping
   * @param {number} total - Total project volume or harga
   * @param {boolean} useHargaCalculation - Whether to use harga-weighted calculation
   * @returns {Array<number>} Planned percentages
   */
  _calculateGridBasedPlannedCurve(columns, cellValues, volumeLookup, hargaLookup, columnIndexById, total, useHargaCalculation) {
    // Calculate column totals (same logic as actual curve)
    const columnTotals = this._calculateColumnTotals(
      columns,
      cellValues,
      volumeLookup,
      hargaLookup,
      columnIndexById,
      useHargaCalculation
    );

    // Calculate cumulative planned curve
    const plannedSeries = [];
    let cumulativePlanned = 0;

    columns.forEach((col, index) => {
      cumulativePlanned += columnTotals[index] || 0;
      const plannedPercent = total > 0
        ? Math.min(100, Math.max(0, (cumulativePlanned / total) * 100))
        : 0;
      plannedSeries.push(Number(plannedPercent.toFixed(2)));
    });

    return plannedSeries;
  }

  /**
   * Calculate volume-based planned curve from pekerjaan assignments
   * DEPRECATED: Kept for backward compatibility, but not recommended.
   * Use _calculateGridBasedPlannedCurve() instead.
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

    const isCostView = data.viewMode === 'cost';
    const legendPrefix = isCostView ? 'Cost ' : '';
    const yAxisLabel = isCostView ? '% of Total Cost' : 'Progress %';

    const palette = [colors.plannedLine, colors.actualLine];
    const legendEntries = [];
    const seriesEntries = [];

    if (isCostView && Array.isArray(data.acSeries)) {
      const plannedName = 'Rencana (PV)';
      const actualName = 'Realisasi (AC)';

      legendEntries.push(plannedName);
      legendEntries.push(actualName);

      seriesEntries.push({
        name: plannedName,
        type: 'line',
        smooth: this.options.smoothCurves,
        data: data.planned,
        lineStyle: {
          color: colors.plannedLine,
          width: 2,
          type: 'dashed',
        },
        areaStyle: this.options.showArea ? { color: colors.plannedArea } : undefined,
        symbolSize: 6,
      });

      const costColor = colors.costActualLine || colors.actualLine;
      palette.push(costColor);
      seriesEntries.push({
        name: actualName,
        type: 'line',
        smooth: this.options.smoothCurves,
        data: data.acSeries,
        lineStyle: {
          color: costColor,
          width: 3,
        },
        areaStyle: this.options.showArea ? { color: colors.costActualArea || colors.actualArea } : undefined,
        symbolSize: 7,
      });
    } else {
      const plannedName = `${legendPrefix}Planned`;
      const actualName = `${legendPrefix}Actual`;
      legendEntries.push(plannedName, actualName);

      seriesEntries.push({
        name: plannedName,
        type: 'line',
        smooth: this.options.smoothCurves,
        data: data.planned,
        lineStyle: {
          color: colors.plannedLine,
          width: 2,
          type: 'dashed',
        },
        areaStyle: this.options.showArea ? { color: colors.plannedArea } : undefined,
        symbolSize: 6,
      });

      seriesEntries.push({
        name: actualName,
        type: 'line',
        smooth: this.options.smoothCurves,
        data: data.actual,
        lineStyle: {
          color: colors.actualLine,
          width: 3,
        },
        areaStyle: this.options.showArea ? { color: colors.actualArea } : undefined,
        symbolSize: 7,
      });
    }

    return {
      backgroundColor: 'transparent',
      color: palette,

      tooltip: {
        trigger: 'axis',
        formatter: (params) => this._formatTooltip(params, data, colors),
      },

      legend: {
        data: legendEntries,
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
        name: yAxisLabel,  // Phase 1: Dynamic Y-axis label
        nameLocation: 'middle',
        nameGap: 50,
        nameTextStyle: {
          color: colors.axis,
          fontSize: 12,
        },
      },

      series: seriesEntries,
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
    const isCostView = data.viewMode === 'cost';

    // Phase 1: Cost view uses different detail structure
    let detail, label, planned, actual, start, end;
    const actualLabel = isCostView ? 'Realisasi' : 'Aktual';

    if (isCostView) {
      // Cost view: details from API response
      const plannedWeek = data.details.weeks?.[index] || {};

      label = data.labels[index];
      planned = data.planned[index] ?? 0;
      const acValue = Array.isArray(data.acSeries) ? data.acSeries[index] : null;
      actual = acValue ?? data.actual?.[index] ?? 0;
      start = plannedWeek.week_start;
      end = plannedWeek.week_end;
    } else {
      // Progress view: existing detail structure
      detail = data.details[index] || {};
      label = detail.label || data.labels[index];
      planned = data.planned[index] ?? 0;
      actual = data.actual[index] ?? 0;
      start = this._formatDateLabel(detail.start);
      end = this._formatDateLabel(detail.end);
    }

    const variance = (actual - planned);

    // Phase 2F.0: Calculate currency amounts if using harga calculation
    const useHarga = (data.useHargaCalculation && data.totalBiaya > 0) || isCostView;
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
        ? `<div style="margin:4px 0;">${actualLabel}: <strong>${actual.toFixed(1)}%</strong> <span style="font-size:0.9em;color:#6b7280;">(${actualAmount})</span></div>`
        : `<div style="margin:4px 0;">${actualLabel}: <strong>${actual.toFixed(1)}%</strong></div>`,
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
