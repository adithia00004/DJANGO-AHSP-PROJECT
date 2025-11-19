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
  }

  updateData({ tree = [], timeColumns = [] } = {}) {
    if (!this.gridApi) {
      return;
    }

    const columnDefs = buildColumnDefs(timeColumns);
    this.currentColumns = timeColumns;

    this.gridApi.setGridOption('columnDefs', columnDefs);
    const rowData = this._buildRowData(tree, timeColumns);
    this.gridApi.setGridOption('rowData', rowData);
  }

  destroy() {
    if (this.gridApi) {
      this.gridApi.destroy();
      this.gridApi = null;
      this.columnApi = null;
    }
  }

  _createGridOptions() {
    return {
      columnDefs: buildColumnDefs([]),
      rowData: [],
      animateRows: true,
      suppressAggFuncInHeader: true,
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

        const row = {
          id: node.id || node.pekerjaan_id || `node-${rowPath.join('-')}`,
          name: label,
          code: kode,
          path: rowPath,
          level: depth,
          raw: node,
        };

        if (safeColumns.length > 0) {
          safeColumns.forEach((col) => {
            const assignmentMap =
              node.assignments ||
              node.assignment_map ||
              node.assignmentMap ||
              node[col.fieldId];

            let value = '';
            if (assignmentMap && typeof assignmentMap === 'object') {
              const directValue =
                assignmentMap[col.id] ??
                assignmentMap[col.fieldId] ??
                assignmentMap[col.label];
              value = directValue ?? '';
            } else if (typeof node[col.fieldId] !== 'undefined') {
              value = node[col.fieldId];
            }

            row[col.fieldId || col.id] = value ?? '';
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

    const validation = validateCellValue(event.newValue, { min: 0, max: 100, precision: 1 });
    if (!validation.isValid && validation.message && typeof this.helpers.showToast === 'function') {
      const toastType = validation.level === 'error' ? 'danger' : 'warning';
      this.helpers.showToast(validation.message, toastType);
    }

    const normalizedValue = validation.value ?? 0;

    if (event.node) {
      event.node.setDataValue(field, normalizedValue);
    }

    const columnMeta =
      (this.currentColumns || []).find((col) => (col.fieldId || col.id) === field) || null;

    const cellKey = `${pekerjaanId}-${field}`;
    if (typeof this.helpers.onCellChange === 'function') {
      this.helpers.onCellChange({
        cellKey,
        value: normalizedValue,
        pekerjaanId,
        columnId: field,
        columnMeta,
      });
    }
  }
}
