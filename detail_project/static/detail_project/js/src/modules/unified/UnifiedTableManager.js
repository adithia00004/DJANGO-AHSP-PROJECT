import { TanStackGridManager } from '../grid/tanstack-grid-manager.js';
import { GanttCanvasOverlay } from '../gantt/GanttCanvasOverlay.js';
import { KurvaSCanvasOverlay } from '../kurva-s/KurvaSCanvasOverlay.js';
import { buildProgressDataset } from '../kurva-s/dataset-builder.js';
import { buildHargaLookup, getHargaForPekerjaan } from '../shared/chart-utils.js';
import StateManager from '../core/state-manager.js';

export class UnifiedTableManager {
  constructor(state, options = {}) {
    this.state = state || {};
    this.options = options;
    this.currentMode = 'grid';
    this.debug = Boolean(this.state?.debugUnifiedTable || this.options?.debugUnifiedTable);
    this.tanstackGrid = null;
    this.overlays = {
      gantt: null,
      kurva: null, // placeholder for future integration
    };
  }

  mount(container, domTargets = {}) {
    this.tanstackGrid = new TanStackGridManager(this.state, this.options);
    this.tanstackGrid.mount(container, domTargets);
    this.tanstackGrid.setCellRenderer('input');
    this._log('mount', { containerMounted: Boolean(container), debug: this.debug });
  }

  updateData(payload) {
    if (this.tanstackGrid) {
      this._log('updateData', {
        rows: payload?.tree?.length || this.tanstackGrid.currentRows?.length || 0,
        cols: payload?.timeColumns?.length || this.tanstackGrid.currentColumns?.length || 0,
        deps: payload?.dependencies?.length || 0,
      });
      this.tanstackGrid.updateData(payload);
      this._refreshGanttOverlay(payload);
      this._refreshKurvaSOverlay(payload);
    }
  }

  switchMode(newMode) {
    if (!newMode || newMode === this.currentMode || !this.tanstackGrid) {
      this._log('switchMode:skip', { newMode, currentMode: this.currentMode, hasGrid: !!this.tanstackGrid });
      return;
    }
    const oldMode = this.currentMode;
    const rendererMap = {
      grid: 'input',
      gantt: 'gantt',
      kurva: 'readonly',
    };
    const targetRenderer = rendererMap[newMode] || 'input';

    // ALWAYS hide ALL overlays first (regardless of current mode)
    if (this.overlays.gantt) {
      this.overlays.gantt.hide();
    }
    if (this.overlays.kurva) {
      this.overlays.kurva.hide?.();
    }

    this.currentMode = newMode;
    this._log('switchMode', {
      from: oldMode,
      to: newMode,
      renderer: targetRenderer,
      rows: this.tanstackGrid.currentRows?.length || 0,
      cols: this.tanstackGrid.currentColumns?.length || 0,
    });

    // Set cell renderer for the new mode
    this.tanstackGrid.setCellRenderer(targetRenderer);

    // Show only the relevant overlay for the new mode
    if (newMode === 'grid') {
      // Grid mode: ensure content is visible by triggering refresh
      if (typeof this.tanstackGrid.refresh === 'function') {
        this.tanstackGrid.refresh();
      }
    } else if (newMode === 'gantt') {
      if (!this.overlays.gantt) {
        this.overlays.gantt = new GanttCanvasOverlay(this.tanstackGrid);
      }
      this.overlays.gantt.show();
      this._refreshGanttOverlay();
    } else if (newMode === 'kurva') {
      if (!this.overlays.kurva) {
        const projectId = this.state?.projectId || this.options?.projectId || null;
        this.overlays.kurva = new KurvaSCanvasOverlay(this.tanstackGrid, { projectId });
      }
      this.overlays.kurva.show();
      this._refreshKurvaSOverlay();
    }
  }

  _refreshGanttOverlay(payload = {}) {
    if (!this.overlays.gantt || !this.tanstackGrid) {
      return;
    }
    const barData = this._buildBarData(payload);
    const dependencyData = payload.dependencies || [];
    this._log('refreshGanttOverlay', {
      bars: barData.length,
      deps: dependencyData.length,
    });
    this.overlays.gantt.renderBars(barData);
    this.overlays.gantt.renderDependencies(dependencyData);
  }

  _buildBarData(payload = {}) {
    // Single source of truth: Get data from StateManager
    const stateManager = StateManager.getInstance();

    // Check display scale for monthly aggregation
    const displayScale = (this.state?.displayScale || 'weekly').toLowerCase();
    const isMonthly = displayScale === 'monthly';

    // Priority 1: StateManager (single source of truth)
    // Priority 2: payload (for backward compatibility)
    // Priority 3: this.state (fallback)
    let flatRows = stateManager.getFlatPekerjaan();
    // CRITICAL: Always use StateManager columns for data lookup
    // Data in StateManager is keyed by weekly column IDs (e.g., "123-col_5")
    // For monthly mode, we aggregate weekly data into monthly buckets for OUTPUT
    let columns = stateManager.getTimeColumns();

    console.log(`[BuildBarData] MODE: ${displayScale}, columns=${columns.length}`);

    // Fallback if StateManager is empty
    if (!flatRows.length) {
      flatRows = Array.isArray(this.state?.flatPekerjaan) ? this.state.flatPekerjaan : [];
    }
    if (!columns.length) {
      columns = Array.isArray(this.state?.timeColumns) ? this.state.timeColumns : [];
      console.log('[BuildBarData] FALLBACK columns used:', columns.length);
    }

    // Convert flatRows to tree format for backward compatibility
    const tree = flatRows.map((row) => ({
      pekerjaanId: row.id || row.pekerjaan_id,
      name: row.nama || row.name,
      raw: row,
      subRows: row.children || [],
    }));

    // Wrap columns with meta for compatibility
    const wrappedColumns = columns.map((col) => ({
      id: col.id,
      fieldId: col.fieldId,
      meta: { timeColumn: true, columnMeta: col },
    }));

    const barData = [];
    // Use already-acquired stateManager from above
    const mergedPlanned = stateManager.getAllCellsForMode('planned');
    const mergedActual = stateManager.getAllCellsForMode('actual');
    const activeMode = (this.state?.progressMode || stateManager?.currentMode || 'planned').toLowerCase();


    this._log('buildBarData:start', {
      rows: tree.length,
      cols: wrappedColumns.length,
      plannedSize: mergedPlanned?.size || 0,
      actualSize: mergedActual?.size || 0,
      activeMode,
      displayScale,
      timeColumnsWithMeta: wrappedColumns.filter((c) => c.meta?.timeColumn).length,
      sampleColumns: wrappedColumns.slice(0, 5).map((c) => c.fieldId || c.id || c.meta?.columnMeta?.fieldId || c.meta?.columnMeta?.id),
      sampleRows: tree.slice(0, 3).map((r) => r.pekerjaanId || r.id || r.raw?.pekerjaan_id),
    });

    const rowsForBars = this._flattenRows(tree);

    const rowIndex = new Map();
    rowsForBars.forEach((row) => {
      const pekerjaanId = row.pekerjaanId || row.id || row.raw?.pekerjaan_id;
      if (!pekerjaanId) return;
      rowIndex.set(String(pekerjaanId), {
        label: row.name || row.raw?.nama || pekerjaanId,
      });
    });

    const columnIndex = new Map();
    wrappedColumns.forEach((col) => {
      const meta = this._resolveColumnMeta(col);
      if (!meta?.timeColumn) return;
      const columnId = col.fieldId || col.id || meta.fieldId || meta.id || meta.columnId || meta.column_id;
      if (!columnId) return;
      columnIndex.set(String(columnId), meta);
    });

    // Build week-to-month mapping for monthly mode
    // Grid uses 1-indexed: month_1, month_2, ... month_12 (not month_0!)
    const weekToMonthMap = new Map();
    if (isMonthly) {
      wrappedColumns.forEach((col, idx) => {
        const colId = col.fieldId || col.id;
        if (!colId) return;
        // 1-indexed: weeks 0-3 → month_1, weeks 4-7 → month_2, etc.
        const monthNumber = Math.floor(idx / 4) + 1;  // +1 for 1-indexed
        weekToMonthMap.set(String(colId), `month_${monthNumber}`);
      });

      // Debug: log the mapping
      this._log('buildBarData:monthlyMapping', {
        totalWeeks: wrappedColumns.length,
        totalMonths: Math.ceil(wrappedColumns.length / 4),
        sampleMapping: Array.from(weekToMonthMap.entries()).slice(0, 8),
        sampleColumnIds: Array.from(columnIndex.keys()).slice(0, 8),
      });
    }

    const allKeys = new Set([
      ...Array.from(mergedPlanned?.keys?.() || []),
      ...Array.from(mergedActual?.keys?.() || []),
    ]);

    // For monthly mode: aggregate into monthly buckets
    // Key: "pekerjaanId-monthIndex", Value: {planned, actual, lastColumnId (for positioning)}
    const monthlyAggregator = new Map();

    allKeys.forEach((cellKey) => {
      const [pkjIdRaw, colIdRaw] = String(cellKey).split('-');
      const pekerjaanId = String(pkjIdRaw || '').trim();
      const columnId = String(colIdRaw || '').trim();
      if (!pekerjaanId || !columnId) {
        return;
      }
      const rowInfo = rowIndex.get(pekerjaanId);
      const colMeta = columnIndex.get(columnId);
      if (!rowInfo || !colMeta) {
        return;
      }
      const plannedValue = this._resolveValue(mergedPlanned, cellKey, 0);
      const actualValue = this._resolveValue(mergedActual, cellKey, plannedValue);
      if (!Number.isFinite(plannedValue) && !Number.isFinite(actualValue)) {
        return;
      }

      if (isMonthly) {
        // Monthly aggregation: group by month
        const monthId = weekToMonthMap.get(columnId);
        if (!monthId) return;

        const aggKey = `${pekerjaanId}-${monthId}`;
        if (!monthlyAggregator.has(aggKey)) {
          monthlyAggregator.set(aggKey, {
            pekerjaanId,
            monthId,
            // Store the actual column ID (will update to last week of month)
            lastColumnId: columnId,
            lastColumnIndex: -1,
            planned: 0,
            actual: 0,
            label: rowInfo.label,
          });
        }
        const agg = monthlyAggregator.get(aggKey);

        // Track which column is the "last" in this month (highest index)
        const currentColIndex = wrappedColumns.findIndex(c =>
          (c.fieldId || c.id) === columnId
        );
        if (currentColIndex > agg.lastColumnIndex) {
          agg.lastColumnIndex = currentColIndex;
          agg.lastColumnId = columnId;  // Update to use last-week column ID
        }

        // Use MAX value within month (cumulative progress)
        agg.planned = Math.max(agg.planned, Number(plannedValue) || 0);
        agg.actual = Math.max(agg.actual, Number(actualValue) || 0);
      } else {
        // Weekly mode: add directly
        const variance = (Number(actualValue) || 0) - (Number(plannedValue) || 0);
        barData.push({
          pekerjaanId,
          columnId,
          value: Number(actualValue) || 0,
          planned: Number(plannedValue) || 0,
          actual: Number(actualValue) || 0,
          variance,
          label: rowInfo.label,
        });
      }
    });

    // Finalize monthly aggregation
    if (isMonthly) {
      monthlyAggregator.forEach((agg) => {
        const variance = agg.actual - agg.planned;
        barData.push({
          pekerjaanId: agg.pekerjaanId,
          // Use monthId (month_1, month_2...) to match grid cellRects
          columnId: agg.monthId,
          value: agg.actual,
          planned: agg.planned,
          actual: agg.actual,
          variance,
          label: agg.label,
        });
      });

      // Debug: show aggregation result
      this._log('buildBarData:monthlyResult', {
        aggregatedBars: barData.length,
        sampleBars: barData.slice(0, 5).map(b => ({
          pkj: b.pekerjaanId,
          col: b.columnId,
          planned: b.planned,
          actual: b.actual,
        })),
      });
    }

    if (barData.length === 0 && (mergedPlanned?.size > 0 || mergedActual?.size > 0)) {
      this._log('buildBarData:noMatch', {
        plannedSize: mergedPlanned?.size || 0,
        actualSize: mergedActual?.size || 0,
        treeLength: tree.length,
        columnsLength: columns.length,
        displayScale,
      });
      this._log('buildBarData:debug', {
        plannedKeys: mergedPlanned ? Array.from(mergedPlanned.keys()).slice(0, 5) : [],
        actualKeys: mergedActual ? Array.from(mergedActual.keys()).slice(0, 5) : [],
        columnIds: columns.map((c) => c.fieldId || c.id || c.meta?.columnMeta?.fieldId || c.meta?.columnMeta?.id || c.meta?.columnId || c.meta?.column_id || c.id).slice(0, 5),
      });
    }

    this._log('buildBarData:done', { bars: barData.length, displayScale });

    // DEBUG: Final result
    console.log(`[BuildBarData] FINAL: displayScale=${displayScale}, totalBars=${barData.length}`);
    if (barData.length > 0) {
      console.log('[BuildBarData] Sample bar columnIds:', barData.slice(0, 5).map(b => b.columnId));
    } else {
      console.log('[BuildBarData] ⚠️ NO BARS GENERATED!');
    }

    return barData;
  }

  _flattenRows(nodes = []) {
    const result = [];
    const stack = Array.isArray(nodes) ? [...nodes] : [];
    while (stack.length) {
      const node = stack.shift();
      if (!node) continue;
      result.push(node);
      if (Array.isArray(node.subRows) && node.subRows.length) {
        stack.push(...node.subRows);
      } else if (Array.isArray(node.children) && node.children.length) {
        stack.push(...node.children);
      } else if (Array.isArray(node.sub) && node.sub.length) {
        stack.push(...node.sub);
      }
    }
    return result;
  }

  _resolveColumnMeta(col) {
    if (!col) return null;
    if (col.meta?.columnMeta && col.meta?.timeColumn) {
      return { ...col.meta.columnMeta, timeColumn: true };
    }
    if (col.meta?.timeColumn) {
      return { ...(col.meta.columnMeta || col.meta), timeColumn: true };
    }
    const mode = (col.generationMode || col.type || '').toLowerCase();
    const isTime = mode === 'weekly' || mode === 'monthly' || Boolean(col.rangeLabel || col.weekNumber);
    if (isTime) {
      return { ...col, timeColumn: true, columnMeta: col };
    }
    return null;
  }

  _mergeModeState(modeState) {
    if (!modeState) {
      return new Map();
    }
    const merged = new Map(modeState.assignmentMap || []);
    (modeState.modifiedCells || new Map()).forEach((value, key) => {
      merged.set(key, value);
    });
    return merged;
  }

  _resolveValue(map, key, fallback) {
    if (map && map.has && map.has(key)) {
      const val = map.get(key);
      if (Number.isFinite(val)) {
        return val;
      }
    }
    return fallback;
  }

  _refreshKurvaSOverlay(payload = {}) {
    if (!this.overlays.kurva || !this.tanstackGrid) {
      return;
    }

    // Build curve data using StateManager - SAME data source as Gantt
    // This ensures consistency between Gantt bar data and Kurva S curve
    const curveData = this._buildCurveData(payload);
    this._log('refreshKurvaSOverlay', {
      plannedPoints: curveData.planned.length,
      actualPoints: curveData.actual.length,
    });

    this.overlays.kurva.renderCurve(curveData);
  }

  // Exposed for KurvaSCanvasOverlay progress refresh
  updateCurvaS(payload = {}) {
    this._refreshKurvaSOverlay(payload);
  }

  // PHASE 4 FIX: Set Kurva-S mode (progress or cost)
  async setKurvaMode(mode) {
    if (!this.overlays.kurva) {
      console.warn('[UnifiedTable] Cannot set Kurva mode: overlay not initialized');
      return;
    }

    this._log('setKurvaMode', { mode });
    await this.overlays.kurva.setMode(mode);
  }

  // PHASE 3 FIX: Use dataset-builder.js with volume/harga weighting instead of simple average
  _buildCurveData(payload = {}) {
    // Check display scale
    const displayScale = (this.state?.displayScale || 'weekly').toLowerCase();
    const isMonthly = displayScale === 'monthly';

    // For MONTHLY mode: Use same data source as Gantt (StateManager cell data)
    // This bypasses grid columns which change with display mode
    if (isMonthly) {
      console.log('[BuildCurveData] MONTHLY - Using StateManager data directly (like Gantt)');
      return this._buildMonthlyCurveFromStateManager();
    }

    // WEEKLY mode: Use original grid column approach (unchanged)
    let columns = Array.isArray(payload.timeColumns) ? payload.timeColumns : [];
    const gridColumns = this.tanstackGrid?.currentColumns || [];

    if (!columns.length && gridColumns.length) {
      columns = gridColumns;
    }

    console.log(`[BuildCurveData] WEEKLY - Grid columns: ${columns.length}`);

    // Fallback if empty
    if (!columns.length && Array.isArray(this.state?.timeColumns)) {
      columns = this.state.timeColumns;
    }

    // Filter to time columns only
    const timeColumns = columns.filter((col) => {
      const meta = this._resolveColumnMeta(col);
      return meta?.timeColumn;
    });

    console.log(`[BuildCurveData] After filter: ${timeColumns.length} time columns`);

    if (timeColumns.length === 0) {
      this._log('buildCurveData:noTimeColumns', { columnsTotal: columns.length });
      return { planned: [], actual: [] };
    }

    // Get state data
    const stateManager = this.state?.stateManager || this.state?.stateManagerInstance || this.options?.stateManager;

    // PHASE 3 FIX: Build state object for dataset-builder.js
    // PHASE 4 FIX: Include hargaMap and flatPekerjaan for weighted calculations
    const datasetState = {
      timeColumns: timeColumns,
      stateManager: stateManager,
      tree: this.state?.tree || payload?.tree || [],
      totalBiayaProject: this.state?.totalBiayaProject || payload?.totalBiayaProject || 0,
      // AUDIT FIX: Pass hargaMap for BOBOT-WEIGHTED calculation consistency
      hargaMap: this.state?.hargaMap || payload?.hargaMap || {},
      flatPekerjaan: this.state?.flatPekerjaan || payload?.flatPekerjaan || [],
      pekerjaanMeta: this.state?.pekerjaanMeta || payload?.pekerjaanMeta || {},
    };

    this._log('buildCurveData:state', {
      timeColumns: timeColumns.length,
      tree: datasetState.tree.length,
      totalBiaya: datasetState.totalBiayaProject,
      // AUDIT FIX: Debug hargaMap availability
      hargaMapType: typeof datasetState.hargaMap,
      hargaMapSize: datasetState.hargaMap instanceof Map
        ? datasetState.hargaMap.size
        : Object.keys(datasetState.hargaMap || {}).length,
    });

    // PHASE 3 FIX: Use buildProgressDataset with weighted calculations
    const dataset = buildProgressDataset(datasetState);

    if (!dataset) {
      this._log('buildCurveData:noDataset', { state: datasetState });
      return { planned: [], actual: [] };
    }

    // Convert dataset format to curve points format
    let plannedCurve = this._convertDatasetToCurvePoints(dataset, 'planned');
    let actualCurve = this._convertDatasetToCurvePoints(dataset, 'actual');

    // Monthly aggregation: group every 4 weeks, take max cumulative value
    // (isMonthly already declared at top of function)

    // Monthly aggregation: group every 4 weeks, take max cumulative value
    if (isMonthly) {
      // DEBUG: log weekly points before aggregation WITH progress values
      console.log(`[BuildCurveData] BEFORE aggregation: planned=${plannedCurve.length}, actual=${actualCurve.length}`);
      console.log('[BuildCurveData] WEEKLY progress:', plannedCurve.slice(0, 8).map(p => ({
        col: p.columnId,
        cum: p.cumulativeProgress,
      })));

      plannedCurve = this._aggregateCurveToMonthly(plannedCurve);
      actualCurve = this._aggregateCurveToMonthly(actualCurve);

      console.log(`[BuildCurveData] AFTER aggregation: planned=${plannedCurve.length}, actual=${actualCurve.length}`);
      console.log('[BuildCurveData] MONTHLY progress:', plannedCurve.map(p => ({
        col: p.columnId,
        cum: p.cumulativeProgress,
      })));
    }

    this._log('buildCurveData:result', {
      plannedPoints: plannedCurve.length,
      actualPoints: actualCurve.length,
      useHargaCalculation: dataset.useHargaCalculation,
      totalBiaya: dataset.totalBiaya,
      totalVolume: dataset.totalVolume,
      displayScale,
    });

    // DEBUG: Log curve data for visibility
    console.log(`[BuildCurveData] MODE: ${displayScale}, planned=${plannedCurve.length}, actual=${actualCurve.length}`);
    if (plannedCurve.length > 0) {
      console.log('[BuildCurveData] Sample planned columnIds:', plannedCurve.slice(0, 5).map(p => p.columnId));
    }

    return {
      planned: plannedCurve,
      actual: actualCurve,
    };
  }

  // Monthly aggregation helper for curve data
  // Groups every 4 weeks, takes the last cumulative value per month
  _aggregateCurveToMonthly(curvePoints) {
    if (!Array.isArray(curvePoints) || curvePoints.length === 0) return [];

    const monthlyPoints = [];

    // Start with week 0 if present - map to month_1 (first month)
    const week0 = curvePoints.find(p => p.weekNumber === 0);
    if (week0) {
      monthlyPoints.push({
        // Use month_1 format to match grid cellRects
        columnId: 'month_1',
        weekNumber: 0,
        monthNumber: 1,
        cumulativeProgress: week0.cumulativeProgress,
        weekProgress: week0.weekProgress,
        label: 'M1',
      });
    }

    // Group remaining weeks into months (every 4 weeks)
    // Grid uses 1-indexed: month_1, month_2, ... month_12
    const nonZeroPoints = curvePoints.filter(p => p.weekNumber > 0);
    for (let i = 0; i < nonZeroPoints.length; i += 4) {
      const monthNumber = Math.floor(i / 4) + 1;  // 1-indexed
      const monthPoints = nonZeroPoints.slice(i, i + 4);
      if (monthPoints.length > 0) {
        // Take the last point's cumulative progress (end of month value)
        const lastPoint = monthPoints[monthPoints.length - 1];
        // Sum week progress for the month
        const monthWeekProgress = monthPoints.reduce((sum, p) => sum + (p.weekProgress || 0), 0);

        monthlyPoints.push({
          // Use month_X format (1-indexed) to match grid cellRects
          columnId: `month_${monthNumber}`,
          weekNumber: lastPoint.weekNumber,
          monthNumber: monthNumber,
          cumulativeProgress: lastPoint.cumulativeProgress,
          weekProgress: monthWeekProgress,
          label: `M${monthNumber}`,
        });
      }
    }

    return monthlyPoints;
  }

  // PHASE 3 FIX: Convert dataset-builder.js format to curve points format
  _convertDatasetToCurvePoints(dataset, seriesKey) {
    const series = dataset[seriesKey] || [];
    const labels = dataset.labels || [];
    const details = dataset.details || [];

    return series.map((cumulativeProgress, index) => {
      const detail = details[index] || {};
      const label = labels[index] || `Week ${index}`;

      // AUDIT FIX: Use weekNumber from detail (set by buildDetailData/prependZeroDetails)
      // After ensureWeekZeroDataset, index 0 = Week 0, index 1 = Week 1, etc.
      const weekNumber = detail?.weekNumber ?? index;

      // Extract column ID from detail or label
      const columnId = detail?.metadata?.id ||
        detail?.metadata?.fieldId ||
        detail?.metadata?.columnId ||
        `week_${weekNumber}`;

      return {
        columnId: String(columnId),
        weekNumber: weekNumber,
        // AUDIT FIX: Use week-only progress (not cumulative) for tooltip
        weekProgress: seriesKey === 'planned'
          ? (detail.plannedWeekProgress ?? detail.planned ?? 0)
          : (detail.actualWeekProgress ?? detail.actual ?? 0),
        cumulativeProgress: cumulativeProgress,
        label: label,
      };
    });
  }

  // Monthly curve calculation using StateManager data directly
  // Extracts column IDs from cell keys (always fresh!) and uses hargaMap for proper weighting
  _buildMonthlyCurveFromStateManager() {
    const stateManager = StateManager.getInstance();
    const mergedPlanned = stateManager.getAllCellsForMode('planned');
    const mergedActual = stateManager.getAllCellsForMode('actual');
    const flatPekerjaan = stateManager.getFlatPekerjaan();

    // Build hargaLookup using SAME function as weekly mode
    // This ensures consistent calculation
    const hargaLookup = buildHargaLookup(this.state || {});
    let totalBiaya = Number(this.state?.totalBiayaProject) || 0;

    console.log(`[BuildMonthlyCurve] planned=${mergedPlanned?.size}, actual=${mergedActual?.size}, pekerjaan=${flatPekerjaan.length}`);
    console.log(`[BuildMonthlyCurve] totalBiaya=${totalBiaya}, hargaLookup size=${hargaLookup.size}`);

    if (!flatPekerjaan.length) {
      return { planned: [], actual: [] };
    }

    // Step 1: Extract unique column IDs from cell keys (FRESH from actual data!)
    // Cell keys format: "pekerjaanId-columnId" e.g., "123-col_5"
    const columnIdSet = new Set();
    const allCellKeys = [
      ...Array.from(mergedPlanned?.keys() || []),
      ...Array.from(mergedActual?.keys() || []),
    ];

    allCellKeys.forEach(key => {
      const parts = String(key).split('-');
      if (parts.length >= 2) {
        // Handle cases like "123-col_5" or "123-tahap-2681"
        const colId = parts.slice(1).join('-');  // Everything after first dash
        if (colId) columnIdSet.add(colId);
      }
    });

    // Sort column IDs by week number (extract number from "col_5" or similar)
    const sortedColumnIds = Array.from(columnIdSet).sort((a, b) => {
      const numA = parseInt(a.replace(/\D/g, '')) || 0;
      const numB = parseInt(b.replace(/\D/g, '')) || 0;
      return numA - numB;
    });

    console.log(`[BuildMonthlyCurve] Extracted ${sortedColumnIds.length} unique column IDs`);
    console.log('[BuildMonthlyCurve] Sample column IDs:', sortedColumnIds.slice(0, 5));

    if (sortedColumnIds.length === 0) {
      return { planned: [], actual: [] };
    }

    // Step 2: Build harga weight map using getHargaForPekerjaan (SAME as weekly)
    // Weight = harga_pekerjaan / total_biaya_project
    const weightMap = new Map();

    // If totalBiaya not set, calculate from hargaLookup
    if (!totalBiaya || totalBiaya <= 0) {
      flatPekerjaan.forEach(row => {
        const id = String(row.id || row.pekerjaan_id);
        totalBiaya += getHargaForPekerjaan(hargaLookup, id, 0);
      });
    }

    flatPekerjaan.forEach(row => {
      const id = String(row.id || row.pekerjaan_id);
      // Use getHargaForPekerjaan - SAME function as weekly mode
      const harga = getHargaForPekerjaan(hargaLookup, id, 0);
      const weight = totalBiaya > 0 ? harga / totalBiaya : 0;
      weightMap.set(id, weight);
    });

    // DEBUG: Show weight distribution
    const weights = Array.from(weightMap.values());
    console.log('[BuildMonthlyCurve] Total weights sum:', weights.reduce((a, b) => a + b, 0).toFixed(4));
    console.log('[BuildMonthlyCurve] Sample weights:', weights.slice(0, 5).map(w => w.toFixed(4)));
    console.log('[BuildMonthlyCurve] Sample weights:', weights.slice(0, 5).map(w => w.toFixed(4)));

    // Step 3: Calculate weighted progress per column
    const weeklyPlanned = [];
    const weeklyActual = [];
    let cumulativePlanned = 0;
    let cumulativeActual = 0;

    sortedColumnIds.forEach((colId, idx) => {
      let weekPlanned = 0;
      let weekActual = 0;

      // Sum weighted progress for this column across all pekerjaan
      flatPekerjaan.forEach(row => {
        const pekerjaanId = String(row.id || row.pekerjaan_id);
        const weight = weightMap.get(pekerjaanId) || 0;

        const cellKey = `${pekerjaanId}-${colId}`;
        const plannedVal = Number(mergedPlanned?.get(cellKey)) || 0;
        const actualVal = Number(mergedActual?.get(cellKey)) || 0;

        // Progress contribution = input_progress * weight (harga/totalBiaya)
        weekPlanned += (plannedVal / 100) * weight * 100;  // Convert back to percentage
        weekActual += (actualVal / 100) * weight * 100;
      });

      cumulativePlanned += weekPlanned;
      cumulativeActual += weekActual;

      weeklyPlanned.push({
        columnId: colId,
        weekNumber: idx,
        weekProgress: weekPlanned,
        cumulativeProgress: cumulativePlanned,
      });

      weeklyActual.push({
        columnId: colId,
        weekNumber: idx,
        weekProgress: weekActual,
        cumulativeProgress: cumulativeActual,
      });
    });

    console.log(`[BuildMonthlyCurve] Weekly: planned=${weeklyPlanned.length}, actual=${weeklyActual.length}`);
    console.log('[BuildMonthlyCurve] Sample weekly cumulative:', weeklyPlanned.slice(0, 8).map(p => p.cumulativeProgress.toFixed(2)));

    // Step 4: Aggregate to monthly (every 4 weeks)
    const monthlyPlanned = this._aggregateCurveToMonthly(weeklyPlanned);
    const monthlyActual = this._aggregateCurveToMonthly(weeklyActual);

    console.log(`[BuildMonthlyCurve] Monthly: planned=${monthlyPlanned.length}, actual=${monthlyActual.length}`);
    console.log('[BuildMonthlyCurve] Sample monthly cumulative:', monthlyPlanned.slice(0, 4).map(p => p.cumulativeProgress.toFixed(2)));

    return {
      planned: monthlyPlanned,
      actual: monthlyActual,
    };
  }

  _log(event, payload) {
    const enabled = this.debug || Boolean(window.DEBUG_UNIFIED_TABLE);
    if (!enabled) return;
    console.log(`[UnifiedTable] ${event}`, payload);
  }
}
