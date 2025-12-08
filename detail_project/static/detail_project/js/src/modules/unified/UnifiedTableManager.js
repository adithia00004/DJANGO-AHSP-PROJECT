import { TanStackGridManager } from '../grid/tanstack-grid-manager.js';
import { GanttCanvasOverlay } from '../gantt/GanttCanvasOverlay.js';

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
    }
  }

  switchMode(newMode) {
    if (!newMode || newMode === this.currentMode || !this.tanstackGrid) {
      return;
    }
    const oldMode = this.currentMode;
    const rendererMap = {
      grid: 'input',
      gantt: 'gantt',
      kurva: 'readonly',
    };
    const targetRenderer = rendererMap[newMode] || 'input';

    // hide existing overlays
    if (this.currentMode === 'gantt' && this.overlays.gantt) {
      this.overlays.gantt.hide();
    }
    if (this.currentMode === 'kurva' && this.overlays.kurva) {
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
    this.tanstackGrid.setCellRenderer(targetRenderer);

    if (newMode === 'gantt') {
      if (!this.overlays.gantt) {
        this.overlays.gantt = new GanttCanvasOverlay(this.tanstackGrid);
      }
      this.overlays.gantt.show();
      this._refreshGanttOverlay();
    }

    if (newMode === 'kurva') {
      // Placeholder: kurva chart overlay can be initialized here later
      if (this.overlays.kurva && typeof this.overlays.kurva.show === 'function') {
        this.overlays.kurva.show();
      }
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
    let tree = Array.isArray(payload.tree) ? payload.tree : [];
    let columns = Array.isArray(payload.timeColumns) ? payload.timeColumns : [];
    const gridRows = this.tanstackGrid?.currentRows || [];
    const gridColumns = this.tanstackGrid?.currentColumns || [];
    const flatRows = Array.isArray(this.state?.flatPekerjaan) ? this.state.flatPekerjaan : [];

    if ((!tree.length || tree.length <= 1) && gridRows.length > tree.length) {
      tree = gridRows;
    }
    if ((!tree.length || tree.length <= 1) && flatRows.length) {
      tree = flatRows.map((row) => ({
        pekerjaanId: row.id || row.pekerjaan_id,
        name: row.nama || row.name,
        raw: row,
        subRows: [],
      }));
    }

    const hasTimeMeta = columns.some((c) => c?.meta?.timeColumn);
    if ((!columns.length || !hasTimeMeta) && gridColumns.length) {
      columns = gridColumns;
    }
    if (!columns.length && Array.isArray(this.state?.timeColumns)) {
      columns = this.state.timeColumns.map((col) => ({
        id: col.id,
        fieldId: col.fieldId,
        meta: { timeColumn: true, columnMeta: col },
      }));
    }

    const barData = [];
    const stateManager = this.state?.stateManager || this.state?.stateManagerInstance || this.options?.stateManager;
    const mergedPlanned = typeof stateManager?.getAllCellsForMode === 'function'
      ? stateManager.getAllCellsForMode('planned')
      : this._mergeModeState(stateManager?.states?.planned);
    const mergedActual = typeof stateManager?.getAllCellsForMode === 'function'
      ? stateManager.getAllCellsForMode('actual')
      : this._mergeModeState(stateManager?.states?.actual);
    const activeMode = (this.state?.progressMode || stateManager?.currentMode || 'planned').toLowerCase();
    this._log('buildBarData:start', {
      rows: tree.length,
      cols: columns.length,
      plannedSize: mergedPlanned?.size || 0,
      actualSize: mergedActual?.size || 0,
      activeMode,
      timeColumnsWithMeta: columns.filter((c) => c.meta?.timeColumn).length,
      sampleColumns: columns.slice(0, 5).map((c) => c.fieldId || c.id || c.meta?.columnMeta?.fieldId || c.meta?.columnMeta?.id),
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
    columns.forEach((col) => {
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

  _log(event, payload) {
    const enabled = this.debug || Boolean(window.DEBUG_UNIFIED_TABLE);
    if (!enabled) return;
    console.log(`[UnifiedTable] ${event}`, payload);
  }
}
