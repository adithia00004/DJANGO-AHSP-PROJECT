/**
 * Build column definitions for AG Grid (dynamic time columns)
 */

/**
 * @param {Array} timeColumns
 * @param {Object} options
 * @returns {Array}
 */
export function buildColumnDefs(timeColumns = [], options = {}) {
  const editableChecker =
    typeof options.isEditableFn === 'function' ? options.isEditableFn : defaultEditableChecker;
  const inputMode = (options.inputMode || 'percentage').toLowerCase();
  const validationStateGetter =
    typeof options.getCellValidationState === 'function' ? options.getCellValidationState : null;

  const baseColumns = [
    {
      headerName: 'Pekerjaan',
      field: 'name',
      minWidth: 280,
      flex: 1.2,
      pinned: 'left',
      cellRenderer: pekerjaanCellRenderer,
      cellClass: 'ag pekerjaan-col',
      wrapText: true,
      autoHeight: true,
    },
    {
      headerName: 'Volume',
      field: 'volume',
      width: 70,
      pinned: 'left',
      resizable: false,
      editable: false,
      suppressHeaderMenuButton: true,
      cellClass: 'ag-volume-col text-end',
      valueFormatter: (params) => formatVolume(params.value),
    },
    {
      headerName: 'Satuan',
      field: 'unit',
      width: 70,
      pinned: 'left',
      resizable: false,
      editable: false,
      suppressHeaderMenuButton: true,
      cellClass: 'ag-unit-col text-center',
    },
  ];

  const dynamicColumns = (timeColumns || []).map((column) => {
    const field = column.fieldId || column.id || 'periode';
    const headerTitle = column.label || column.id || 'Periode';
    const rangeText =
      column.rangeText ||
      (column.rangeLabel ? column.rangeLabel.replace(/[()]/g, '').trim() : '');
    const headerName = rangeText ? `${headerTitle}\n${rangeText}` : headerTitle;
    const getCellKey = (params) => {
      const rowId =
        params?.data?.raw?.id ||
        params?.data?.id ||
        params?.node?.data?.raw?.id ||
        params?.node?.data?.id;
      if (!rowId) {
        return null;
      }
      return `${rowId}-${field}`;
    };

    const cellClassRules = {
      'ag-cell-readonly': (params) => !editableChecker(params),
    };

    if (validationStateGetter) {
      cellClassRules['ag-cell-invalid'] = (params) => {
        const cellKey = getCellKey(params);
        return cellKey ? validationStateGetter(cellKey) === 'error' : false;
      };
      cellClassRules['ag-cell-warning'] = (params) => {
        const cellKey = getCellKey(params);
        return cellKey ? validationStateGetter(cellKey) === 'warning' : false;
      };
    }

    return {
      headerName,
      field,
      minWidth: 100,
      flex: 1,
      type: 'numericColumn',
      cellDataType: 'number',
      editable: (params) => editableChecker(params),
      cellEditor: 'agNumberCellEditor',
      valueParser: (params) => parseNumericValue(params.newValue),
      cellClass: 'ag-time-col',
      cellClassRules,
      headerClass: 'ag-time-header',
      valueFormatter: (params) => formatTimeCellValue(params.value, inputMode),
    };
  });

  return baseColumns.concat(dynamicColumns);
}

function pekerjaanCellRenderer(params) {
  const value = params.value || '';
  const level = params.data?.level || 0;
  const wrapper = document.createElement('div');
  wrapper.className = 'ag-pekerjaan-label';
  wrapper.style.paddingLeft = `${level * 16}px`;
  wrapper.textContent = value;
  return wrapper;
}

function formatVolume(value) {
  if (value === null || typeof value === 'undefined' || value === '') {
    return '-';
  }
  const numericValue = Number(value);
  if (Number.isNaN(numericValue)) {
    return value;
  }
  return numericValue.toLocaleString('id-ID', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

function defaultEditableChecker(params) {
  const rowType = params?.data?.rowType || params?.data?.raw?.type;
  return rowType === 'pekerjaan';
}

function formatTimeCellValue(value, mode = 'percentage') {
  if (value === null || typeof value === 'undefined' || value === '') {
    return '-';
  }

  if (mode === 'volume') {
    const numericValue = Number(value);
    if (Number.isNaN(numericValue)) {
      return value;
    }
    return numericValue.toLocaleString('id-ID', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 3,
    });
  }

  return `${value}`;
}

function parseNumericValue(rawValue) {
  if (rawValue === null || typeof rawValue === 'undefined' || rawValue === '') {
    return null;
  }

  if (typeof rawValue === 'number') {
    return Number.isFinite(rawValue) ? rawValue : null;
  }

  const parsed = parseFloat(rawValue);
  return Number.isFinite(parsed) ? parsed : null;
}
