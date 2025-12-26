import { TanStackGridManager } from '../grid/tanstack-grid-manager.js';
import { GanttCanvasOverlay } from '../gantt/GanttCanvasOverlay.js';
import { KurvaSCanvasOverlay } from '../kurva-s/KurvaSCanvasOverlay.js';
import { buildProgressDataset } from '../kurva-s/dataset-builder.js';
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

    // Priority 1: StateManager (single source of truth)
    // Priority 2: payload (for backward compatibility)
    // Priority 3: this.state (fallback)
    let flatRows = stateManager.getFlatPekerjaan();
    let columns = stateManager.getTimeColumns();

    // Fallback if StateManager is empty
    if (!flatRows.length) {
      flatRows = Array.isArray(this.state?.flatPekerjaan) ? this.state.flatPekerjaan : [];
    }
    if (!columns.length) {
      columns = Array.isArray(this.state?.timeColumns) ? this.state.timeColumns : [];
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

    console.log('[UnifiedTable] 🔍 BuildBarData DEBUG:', {
      rows: tree.length,
      cols: wrappedColumns.length,
      plannedSize: mergedPlanned?.size || 0,
      actualSize: mergedActual?.size || 0,
      activeMode,
      samplePlannedKeys: mergedPlanned ? Array.from(mergedPlanned.keys()).slice(0, 5) : [],
      sampleActualKeys: mergedActual ? Array.from(mergedActual.keys()).slice(0, 5) : [],
      samplePlannedValues: mergedPlanned ? Array.from(mergedPlanned.entries()).slice(0, 3) : [],
      sampleActualValues: mergedActual ? Array.from(mergedActual.entries()).slice(0, 3) : [],
    });

    this._log('buildBarData:start', {
      rows: tree.length,
      cols: wrappedColumns.length,
      plannedSize: mergedPlanned?.size || 0,
      actualSize: mergedActual?.size || 0,
      activeMode,
      timeColumnsWithMeta: wrappedColumns.filter((c) => c.meta?.timeColumn).length,
      sampleColumns: wrappedColumns.slice(0, 5).map((c) => c.fieldId || c.id || c.meta?.columnMeta?.fieldId || c.meta?.columnMeta?.id),
      sampleRows: tree.slice(0, 3).map((r) => r.pekerjaanId || r.id || r.raw?.pekerjaan_id),
    });

    const rowsForBars = this._flattenRows(tree);

    // DEBUG: Log tree source and flatten result
    console.log('[UnifiedTable] 🌳 Tree source DEBUG:', {
      'payload.tree': Array.isArray(payload.tree) ? payload.tree.length : 'not array',
      'fromStateManager': flatRows.length,
      'treeBefore': tree.length,
      'treeAfter (flattened)': rowsForBars.length,
      'sampleTree': tree.slice(0, 2).map(r => ({
        id: r.pekerjaanId || r.id || r.raw?.pekerjaan_id,
        name: r.name || r.raw?.nama,
        subRows: r.subRows?.length || 0,
        children: r.children?.length || 0,
      })),
    });
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

    const allKeys = new Set([
      ...Array.from(mergedPlanned?.keys?.() || []),
      ...Array.from(mergedActual?.keys?.() || []),
    ]);

    // DEBUG: Log matching analysis
    const sampleCellKeys = Array.from(allKeys).slice(0, 5);
    const sampleRowIds = Array.from(rowIndex.keys()).slice(0, 5);
    const sampleColIds = Array.from(columnIndex.keys()).slice(0, 5);
    console.log('[UnifiedTable] 🔗 Matching DEBUG:', {
      'allKeys.size': allKeys.size,
      'rowIndex.size': rowIndex.size,
      'columnIndex.size': columnIndex.size,
      'sampleCellKeys': sampleCellKeys,
      'sampleRowIds': sampleRowIds,
      'sampleColIds': sampleColIds,
      // Check if first cell key matches
      'firstKeyMatch': sampleCellKeys.length > 0 ? {
        cellKey: sampleCellKeys[0],
        split: sampleCellKeys[0]?.split('-'),
        rowExists: rowIndex.has(sampleCellKeys[0]?.split('-')?.[0]),
        colExists: columnIndex.has(sampleCellKeys[0]?.split('-')?.[1]),
      } : null,
    });

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
      const variance = (Number(actualValue) || 0) - (Number(plannedValue) || 0);
      barData.push({
        pekerjaanId,
        columnId,
        value: Number(actualValue) || 0,
        planned: Number(plannedValue) || 0,
        actual: Number(actualValue) || 0,
        variance,
        label: rowInfo.label,
        color: '#4dabf7',
      });
    });

    if (barData.length === 0 && (mergedPlanned?.size > 0 || mergedActual?.size > 0)) {
      console.warn('[UnifiedTable] ⚠️ NO BAR DATA despite having cell values! Check:', {
        'mergedPlanned.size': mergedPlanned?.size || 0,
        'mergedActual.size': mergedActual?.size || 0,
        'tree.length': tree.length,
        'columns.length': columns.length,
        'timeColumnsWithMeta': columns.filter((c) => c.meta?.timeColumn).length
      });
      this._log('buildBarData:debug', {
        plannedKeys: mergedPlanned ? Array.from(mergedPlanned.keys()).slice(0, 5) : [],
        actualKeys: mergedActual ? Array.from(mergedActual.keys()).slice(0, 5) : [],
        columnIds: columns.map((c) => c.fieldId || c.id || c.meta?.columnMeta?.fieldId || c.meta?.columnMeta?.id || c.meta?.columnId || c.meta?.column_id || c.id).slice(0, 5),
      });
    }

    this._log('buildBarData:done', { bars: barData.length });
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
    // Get columns and state
    let columns = Array.isArray(payload.timeColumns) ? payload.timeColumns : [];
    const gridColumns = this.tanstackGrid?.currentColumns || [];

    if (!columns.length && gridColumns.length) {
      columns = gridColumns;
    }
    if (!columns.length && Array.isArray(this.state?.timeColumns)) {
      columns = this.state.timeColumns;
    }

    // Filter to time columns only
    const timeColumns = columns.filter((col) => {
      const meta = this._resolveColumnMeta(col);
      return meta?.timeColumn;
    });

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
    const plannedCurve = this._convertDatasetToCurvePoints(dataset, 'planned');
    const actualCurve = this._convertDatasetToCurvePoints(dataset, 'actual');

    this._log('buildCurveData:result', {
      plannedPoints: plannedCurve.length,
      actualPoints: actualCurve.length,
      useHargaCalculation: dataset.useHargaCalculation,
      totalBiaya: dataset.totalBiaya,
      totalVolume: dataset.totalVolume,
    });

    return {
      planned: plannedCurve,
      actual: actualCurve,
    };
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

  _log(event, payload) {
    const enabled = this.debug || Boolean(window.DEBUG_UNIFIED_TABLE);
    if (!enabled) return;
    console.log(`[UnifiedTable] ${event}`, payload);
  }
}
