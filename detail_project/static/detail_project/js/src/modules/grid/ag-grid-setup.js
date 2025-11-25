import { createGrid } from 'ag-grid-community';
import { buildColumnDefs } from './column-definitions.js';
import { validateCellValue } from '@modules/shared/validation-utils.js';

/**
 * AGGridManager
 * Membungkus inisialisasi AG Grid agar mudah diintegrasikan bertahap
 */
export class AGGridManager {
  constructor(state, helpers = {}) {
    this.state = state;
    this.helpers = helpers;
    this.gridApi = null;
    this.columnApi = null;
    this.gridOptions = null;
    this.container = null;
    this.currentColumns = [];
    this.themeObserver = null;
    this.inputMode = (state?.inputMode || 'percentage').toLowerCase();
    this.topScroll = null;
    this.topScrollInner = null;
    this.bottomHorizontalViewport = null;
    this.horizontalScrollHandlers = [];
    this._isSyncingHorizontalScroll = false;
  }

  mount(containerElement) {
    if (!containerElement) {
      console.warn('[AGGridManager] Container not provided');
      return;
    }

    this.container = containerElement;
    this.gridOptions = this._createGridOptions();

    this.gridApi = createGrid(containerElement, this.gridOptions);
    if (typeof this.gridApi.getColumnApi === 'function') {
      this.columnApi = this.gridApi.getColumnApi();
    }

    containerElement.classList.add('ag-grid-initialized');
    this._applyThemeClass();
    this._setupThemeWatcher();
    this._setupHorizontalScrollProxy();
    this._updateTopScrollWidth();
  }

  updateData({ tree = [], timeColumns = [], inputMode } = {}) {
    if (!this.gridApi) {
      return;
    }

    if (typeof inputMode === 'string') {
      this.inputMode = inputMode.toLowerCase();
    }

    const columnDefs = buildColumnDefs(timeColumns, this._getColumnOptions());
    this.currentColumns = timeColumns;

    this.gridApi.setGridOption('columnDefs', columnDefs);
    const rowData = this._buildRowData(tree, timeColumns);
    this.gridApi.setGridOption('rowData', rowData);
    this._updateTopScrollWidth();
  }

  destroy() {
    if (this.gridApi) {
      this.gridApi.destroy();
      this.gridApi = null;
      this.columnApi = null;
    }
    if (this.themeObserver) {
      this.themeObserver.disconnect();
      this.themeObserver = null;
    }
    this._teardownHorizontalScrollProxy();
  }

  _createGridOptions() {
    return {
      columnDefs: buildColumnDefs([], this._getColumnOptions()),
      rowData: [],
      animateRows: true,
      suppressAggFuncInHeader: true,
      rowHeight: 60,
      headerHeight: 44,
      defaultColDef: {
        resizable: true,
        sortable: false,
        flex: 1,
        minWidth: 120,
      },
      onCellValueChanged: (event) => this._handleCellValueChanged(event),
    };
  }

  _buildRowData(tree = [], timeColumns = []) {
    const rows = [];
    const safeColumns = timeColumns || [];

    const normalizeNodes = (nodes) => {
      if (Array.isArray(nodes)) {
        return nodes;
      }
      if (nodes && typeof nodes === 'object') {
        return Object.values(nodes).filter(Boolean);
      }
      return [];
    };

    const getChildren = (node) => {
      if (!node || typeof node !== 'object') {
        return [];
      }
      const candidates = ['children', 'sub', 'pekerjaan', 'items', 'nodes'];
      for (const key of candidates) {
        if (Array.isArray(node[key]) && node[key].length > 0) {
          return node[key];
        }
      }
      return [];
    };

    const walk = (nodes, parentPath = [], depth = 0) => {
      const iterable = normalizeNodes(nodes);
      if (!iterable.length) {
        return;
      }

      iterable.forEach((node, index) => {
        if (!node) return;

        const label =
          node.snapshot_uraian ||
          node.uraian ||
          node.nama ||
          node.name ||
          `Node ${parentPath.length + index + 1}`;

        const kode = node.snapshot_kode || node.kode || node.code || '';
        const rowPath = parentPath.concat(label);

        const rowType =
          node.type ||
          node.rowType ||
          (node.children && node.children.length > 0 ? 'klasifikasi' : 'pekerjaan');

        const rowId = node.id || node.pekerjaan_id || `node-${rowPath.join('-')}`;
        const failedRows = this.state?.failedRows;
        const isFailed = failedRows instanceof Set && failedRows.has(rowId);

        const rowClasses = [];
        if (rowType) {
          rowClasses.push(`row-${rowType}`);
        }
        if (isFailed) {
          rowClasses.push('row-has-error');
        }

        const row = {
          id: rowId,
          name: label,
          code: kode,
          path: rowPath,
          level: depth,
          raw: node,
          rowType,
          isEditable: rowType === 'pekerjaan',
          rowClass: rowClasses.join(' '),
          unit:
            node.snapshot_satuan ||
            node.satuan ||
            node.unit ||
            node.snapshot_unit ||
            '',
          volume: this._resolveVolumeValue(node),
        };

        if (safeColumns.length > 0) {
          safeColumns.forEach((col) => {
            const columnField = col.fieldId || col.id;
            if (!columnField) {
              return;
            }

            const assignmentMap =
              node.assignments ||
              node.assignment_map ||
              node.assignmentMap ||
              node[columnField];

            let value = null;
            if (assignmentMap && typeof assignmentMap === 'object') {
              const directValue =
                assignmentMap[col.id] ??
                assignmentMap[col.fieldId] ??
                assignmentMap[col.label];
              value = this._normalizeCellValue(directValue);
            } else if (typeof node[columnField] !== 'undefined') {
              value = this._normalizeCellValue(node[columnField]);
            }

            if ((value === null || typeof value === 'undefined') && this.state?.assignmentMap) {
              value = this._fetchAssignmentValue(rowId, columnField);
            }

            let displayValue = value;
            if (this.inputMode === 'volume') {
              displayValue = this._percentToVolume(displayValue, row.volume);
            }

            row[columnField] = displayValue;
          });
        }

        rows.push(row);

        const childNodes = getChildren(node);
        if (childNodes.length > 0) {
          walk(childNodes, rowPath, depth + 1);
        }
      });
    };

    walk(tree, []);
    if (typeof console !== 'undefined') {
      console.log(
        '[AGGridManager] updateData',
        rows.length,
        'rows,',
        safeColumns.length + 2,
        'columns'
      );
    }
    return rows;
  }

  _handleCellValueChanged(event) {
    const colDef = event?.colDef;
    const field = colDef?.field;
    if (!field) {
      return;
    }

    const rowData = event?.data;
    const pekerjaanId = rowData?.raw?.id || rowData?.id;
    if (!pekerjaanId) {
      return;
    }

    if (!this._isCellEditable(rowData)) {
      if (typeof this.helpers.showToast === 'function') {
        this.helpers.showToast('Progress hanya dapat diisi pada baris pekerjaan', 'warning');
      }
      if (event.node) {
        event.node.setDataValue(field, event.oldValue);
      }
      return;
    }

    const isVolumeMode = this.inputMode === 'volume';
    const rowVolume = Number(rowData?.volume) || 0;
    const validation = validateCellValue(event.newValue, {
      min: 0,
      max: isVolumeMode ? (rowVolume || 0) : 100,
      precision: isVolumeMode ? 3 : 1,
    });
    if (!validation.isValid && validation.message && typeof this.helpers.showToast === 'function') {
      const toastType = validation.level === 'error' ? 'danger' : 'warning';
      this.helpers.showToast(validation.message, toastType);
    }

    let displayValue = validation.value ?? 0;
    let canonicalValue = displayValue;

    if (isVolumeMode) {
      canonicalValue = this._volumeToPercent(displayValue, rowVolume);
    }

    canonicalValue = Number.isFinite(canonicalValue) ? Number(canonicalValue.toFixed(2)) : 0;

    if (event.node) {
      event.node.setDataValue(field, displayValue);
    }

    const columnMeta =
      (this.currentColumns || []).find((col) => (col.fieldId || col.id) === field) || null;

    const cellKey = `${pekerjaanId}-${field}`;
    if (typeof this.helpers.onCellChange === 'function') {
      this.helpers.onCellChange({
        cellKey,
        value: canonicalValue,
        pekerjaanId,
        columnId: field,
        columnMeta,
      });
    }
  }

  _resolveVolumeValue(node) {
    const nodeId = node?.id || node?.pekerjaan_id;
    const volumeMap = this.state?.volumeMap;
    if (volumeMap instanceof Map && nodeId && volumeMap.has(nodeId)) {
      return volumeMap.get(nodeId);
    }
    if (volumeMap && typeof volumeMap === 'object' && nodeId && volumeMap[nodeId]) {
      return volumeMap[nodeId];
    }
    return (
      node.volume ||
      node.qty ||
      node.jumlah ||
      node.volume_total ||
      node.total_volume ||
      ''
    );
  }

  updateTopScrollMetrics() {
    this._updateTopScrollWidth();
  }

  _fetchAssignmentValue(pekerjaanId, columnField) {
    if (!pekerjaanId || !columnField || !this.state?.assignmentMap) {
      return null;
    }

    const cellKey = `${pekerjaanId}-${columnField}`;
    const assignmentMap = this.state.assignmentMap;

    if (assignmentMap instanceof Map) {
      if (assignmentMap.has(cellKey)) {
        return this._normalizeCellValue(assignmentMap.get(cellKey));
      }
      return null;
    }

    if (typeof assignmentMap === 'object' && assignmentMap !== null) {
      if (Object.prototype.hasOwnProperty.call(assignmentMap, cellKey)) {
        return this._normalizeCellValue(assignmentMap[cellKey]);
      }
    }

    return null;
  }

  _percentToVolume(percent, totalVolume) {
    const numericPercent = Number(percent);
    const numericVolume = Number(totalVolume);
    if (!Number.isFinite(numericPercent) || !Number.isFinite(numericVolume)) {
      return percent;
    }
    return (numericPercent / 100) * numericVolume;
  }

  _volumeToPercent(volumeValue, totalVolume) {
    const numericVolume = Number(volumeValue);
    const numericTotal = Number(totalVolume);
    if (!Number.isFinite(numericVolume) || numericVolume < 0) {
      return 0;
    }
    if (!Number.isFinite(numericTotal) || numericTotal <= 0) {
      return 0;
    }
    const percent = (numericVolume / numericTotal) * 100;
    return Math.min(100, Math.max(0, percent));
  }

  _applyThemeClass() {
    if (!this.container) {
      return;
    }
    const theme = document.documentElement?.getAttribute('data-bs-theme') || 'light';
    const isDark = theme.toLowerCase() === 'dark';
    this.container.classList.remove('ag-theme-alpine', 'ag-theme-alpine-dark');
    this.container.classList.add(isDark ? 'ag-theme-alpine-dark' : 'ag-theme-alpine');
  }

  setInputMode(mode) {
    if (!mode) {
      return;
    }
    const normalized = mode.toLowerCase();
    if (this.inputMode === normalized) {
      return;
    }
    this.inputMode = normalized;
    if (this.gridApi) {
      const columnDefs = buildColumnDefs(this.currentColumns, this._getColumnOptions());
      this.gridApi.setGridOption('columnDefs', columnDefs);
      this.gridApi.refreshCells({ force: true });
    }
  }

  _getColumnOptions() {
    return {
      inputMode: this.inputMode || 'percentage',
      isEditableFn: (params) => this._isCellEditable(params?.data || params),
    };
  }

  _isCellEditable(target) {
    if (!target) {
      return false;
    }
    const rowData = target.data || target;
    const rowType = rowData?.rowType || rowData?.raw?.type;
    return rowType === 'pekerjaan';
  }

  _normalizeCellValue(value) {
    if (value === null || typeof value === 'undefined' || value === '') {
      return null;
    }
    if (typeof value === 'number') {
      return Number.isFinite(value) ? value : null;
    }
    if (typeof value === 'string') {
      const trimmed = value.trim();
      if (trimmed === '') {
        return null;
      }
      const parsed = parseFloat(trimmed.replace(',', '.'));
      return Number.isFinite(parsed) ? parsed : null;
    }
    return null;
  }

  _setupHorizontalScrollProxy() {
    const topScroll = document.getElementById('ag-grid-scroll-top');
    const topInner = document.getElementById('ag-grid-scroll-inner');
    if (!topScroll || !topInner) {
      return;
    }

    const bottomViewport =
      this.container?.querySelector('.ag-body-horizontal-scroll-viewport') ||
      this.container?.querySelector('.ag-center-cols-viewport');
    if (!bottomViewport) {
      return;
    }

    this.topScroll = topScroll;
    this.topScrollInner = topInner;
    this.bottomHorizontalViewport = bottomViewport;

    const syncTop = () => {
      if (this._isSyncingHorizontalScroll) return;
      this._isSyncingHorizontalScroll = true;
      bottomViewport.scrollLeft = topScroll.scrollLeft;
      this._isSyncingHorizontalScroll = false;
    };

    const syncBottom = () => {
      if (this._isSyncingHorizontalScroll) return;
      this._isSyncingHorizontalScroll = true;
      topScroll.scrollLeft = bottomViewport.scrollLeft;
      this._isSyncingHorizontalScroll = false;
    };

    topScroll.addEventListener('scroll', syncTop, { passive: true });
    bottomViewport.addEventListener('scroll', syncBottom, { passive: true });
    this.horizontalScrollHandlers.push({ element: topScroll, handler: syncTop });
    this.horizontalScrollHandlers.push({ element: bottomViewport, handler: syncBottom });
    setTimeout(() => this._updateTopScrollWidth(), 0);
  }

  _teardownHorizontalScrollProxy() {
    this.horizontalScrollHandlers.forEach(({ element, handler }) => {
      element.removeEventListener('scroll', handler);
    });
    this.horizontalScrollHandlers = [];
    this.topScroll = null;
    this.topScrollInner = null;
    this.bottomHorizontalViewport = null;
  }

  _updateTopScrollWidth() {
    if (!this.topScrollInner || !this.container) {
      return;
    }
    const centerContainer = this.container.querySelector('.ag-center-cols-container');
    if (!centerContainer) {
      return;
    }
    const width = centerContainer.scrollWidth;
    if (width > 0) {
      this.topScrollInner.style.width = `${width}px`;
    }
  }

  refreshRowStyles() {
    if (this.gridApi) {
      this.gridApi.refreshCells({ force: true });
    }
  }

  _setupThemeWatcher() {
    if (this.themeObserver || typeof MutationObserver === 'undefined') {
      return;
    }
    this.themeObserver = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (
          mutation.type === 'attributes' &&
          mutation.attributeName === 'data-bs-theme'
        ) {
          this._applyThemeClass();
        }
      });
    });
    this.themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-bs-theme'],
    });
  }
}
