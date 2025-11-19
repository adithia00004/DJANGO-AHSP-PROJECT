/**
 * Build column definitions for AG Grid (dynamic time columns)
 */

/**
 * @param {Array} timeColumns
 * @returns {Array}
 */
export function buildColumnDefs(timeColumns = []) {
  const baseColumns = [
    {
      headerName: 'Kode',
      field: 'code',
      width: 150,
      pinned: 'left',
      suppressSizeToFit: true,
      cellClass: 'ag-code-col',
    },
    {
      headerName: 'Pekerjaan',
      field: 'name',
      minWidth: 240,
      flex: 1.2,
      pinned: 'left',
      cellRenderer: pekerjaanCellRenderer,
      cellClass: 'ag pekerjaan-col',
    },
  ];

  const dynamicColumns = (timeColumns || []).map((column) => {
    const field = column.fieldId || column.id || 'periode';
    return {
      headerName: column.label || column.id || 'Periode',
      field,
      minWidth: 120,
      flex: 1,
      type: 'numericColumn',
      editable: true,
      cellEditor: 'agNumberCellEditor',
      cellClass: 'ag-time-col',
      valueFormatter: (params) => {
        if (params.value === null || typeof params.value === 'undefined' || params.value === '') {
          return '-';
        }
        return `${params.value}`;
      },
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
