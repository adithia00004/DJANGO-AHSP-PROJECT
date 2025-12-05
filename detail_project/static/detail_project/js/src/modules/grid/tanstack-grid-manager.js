import {
  createTable,
  getCoreRowModel,
  getExpandedRowModel,
  getSortedRowModel,
} from '@tanstack/table-core';
import {
  Virtualizer,
  observeElementRect,
  observeElementOffset,
  elementScroll,
} from '@tanstack/virtual-core';
import { validateCellValue } from '@modules/shared/validation-utils.js';
import { StateManager } from '@modules/core/state-manager.js';

const DEFAULT_ROW_HEIGHT = 56;

const flexRender = (template, context) => {
  if (typeof template === 'function') {
    return template(context);
  }
  return template ?? '';
};

export class TanStackGridManager {
  constructor(state, options = {}) {
    this.state = state;
    this.options = options;
    this.stateManager = state?.stateManager || StateManager.getInstance();
    this.table = null;
    this.container = null;
    this.headerContainer = null;
    this.headerInner = null;
    this.bodyScroll = null;
    this.bodyInner = null;
    this.virtualizer = null;
    this.currentColumns = [];
    this.currentRows = [];
    this.rowHeight = options.rowHeight || DEFAULT_ROW_HEIGHT;
    this.inputMode = (state?.inputMode || 'percentage').toLowerCase();
    this.topScroll = null;
    this.topScrollInner = null;
    this._handleScroll = this._handleScroll.bind(this);
    this._handleTopScroll = this._handleTopScroll.bind(this);
    this._syncingBodyScroll = false;
    this._syncingTopScroll = false;
    this.activeEditor = null;
    this._editorNavDirection = null;
    this.totalColumnWidth = 0;
    this._lastScrollLeft = 0;
    this.tableState = {
      expanded: true,
      columnPinning: { left: [], right: [] },
    };
  }

  mount(container, domTargets = {}) {
    if (!container) {
      throw new Error('[TanStackGridManager] Container element is required');
    }

    this.container = container;
    this.headerContainer = document.createElement('div');
    this.headerContainer.className = 'tanstack-grid-header';
    this.headerInner = document.createElement('div');
    this.headerInner.className = 'tanstack-grid-header-inner';
    this.headerContainer.appendChild(this.headerInner);

    this.bodyScroll = domTargets.body || document.createElement('div');
    this.bodyScroll.classList.add('tanstack-grid-body');
    this.bodyInner = document.createElement('div');
    this.bodyInner.className = 'tanstack-grid-virtual-container';
    this.bodyScroll.appendChild(this.bodyInner);

    this.topScroll = domTargets.topScroll || null;
    this.topScrollInner = domTargets.topScrollInner || null;

    this.container.innerHTML = '';
    this.container.appendChild(this.headerContainer);
    this.container.appendChild(this.bodyScroll);

    if (domTargets.topScroll && domTargets.topScrollInner) {
      domTargets.topScroll.classList.remove('d-none');
    }

    this.bodyScroll.addEventListener('scroll', this._handleScroll, { passive: true });

    if (this.topScroll) {
      this.topScroll.addEventListener('scroll', this._handleTopScroll, { passive: true });
    }
  }

  updateData({ tree = [], timeColumns = [], inputMode, timeScale } = {}) {
    if (!this.container) {
      return;
    }

    if (typeof inputMode === 'string') {
      this.inputMode = inputMode.toLowerCase();
    }
    this.state.timeScale = timeScale || this.state.timeScale;
    this.currentColumns = this._defineColumns(timeColumns);
    this.totalColumnWidth = this._calculateTotalWidth(this.currentColumns);
    this.currentRows = this._transformTree(tree);
    this._ensureTableStateDefaults();

    this.table = createTable({
      data: this.currentRows,
      columns: this.currentColumns,
      getCoreRowModel: getCoreRowModel(),
      getExpandedRowModel: getExpandedRowModel(),
      getSortedRowModel: getSortedRowModel(),
      state: this.tableState,
      onExpandedChange: (updater) => {
        this._updateTableState('expanded', updater);
        this._renderTable();
      },
      getSubRows: (row) => row.subRows || [],
    });

    this._renderTable();
    this._updateTopScrollWidth();
  }

  setInputMode(mode) {
    if (typeof mode === 'string') {
      this.inputMode = mode.toLowerCase();
      this._renderTable();
    }
  }

  updateTopScrollMetrics() {
    this._updateTopScrollWidth();
  }

  refreshRowStyles() {
    this._renderRowsOnly();
  }

  refreshCells() {
    this._renderRowsOnly();
  }

  destroy() {
    if (this.bodyScroll) {
      this.bodyScroll.removeEventListener('scroll', this._handleScroll);
    }
    if (this.topScroll) {
      this.topScroll.removeEventListener('scroll', this._handleTopScroll);
    }
    this.table = null;
    this.virtualizer = null;
    this.container = null;
  }

  _handleScroll() {
    if (this.virtualizer) {
      this.virtualizer.measure();
      this._renderVirtualRows();
    }
    if (this.topScroll && !this._syncingTopScroll) {
      this._syncingBodyScroll = true;
      this.topScroll.scrollLeft = this.bodyScroll.scrollLeft;
      this._syncingBodyScroll = false;
    }
    this._syncHeaderScroll();
  }

  _handleTopScroll() {
    if (this._syncingBodyScroll || !this.bodyScroll) {
      return;
    }
    this._syncingTopScroll = true;
    this.bodyScroll.scrollLeft = this.topScroll.scrollLeft;
    this._syncingTopScroll = false;
    this._syncHeaderScroll();
  }

  _defineColumns(timeColumns = []) {
    let pinnedOffset = 0;
    const createPinnedColumn = (colDef) => {
      const width = colDef.meta?.width || 120;
      const meta = {
        ...colDef.meta,
        width,
        pinned: true,
        stickyOffset: pinnedOffset,
      };
      pinnedOffset += width;
      return {
        ...colDef,
        meta,
      };
    };

    const pinnedColumns = [
      {
        id: 'name',
        header: 'Pekerjaan',
        meta: { width: 280, align: 'start' },
        accessorKey: 'name',
      },
      {
        id: 'volume',
        header: 'Volume',
        meta: { width: 90, align: 'end' },
        accessorFn: (row) => row.volume,
      },
      {
        id: 'unit',
        header: 'Satuan',
        meta: { width: 80, align: 'center' },
        accessorFn: (row) => row.unit || '-',
      },
    ].map(createPinnedColumn);

    const dynamicColumns = (timeColumns || []).map((col) => {
      const width = Number(col?.width) || 120;
      const isAggregated = Array.isArray(col?.childColumns) && col.childColumns.length > 0;
      return {
        id: col.fieldId || col.id,
        header: () => col.label || col.id || 'Periode',
        accessorFn: () => null,
        meta: {
          width,
          timeColumn: true,
          columnMeta: col,
          pinned: false,
          readOnly: Boolean(col?.readOnly || isAggregated),
        },
      };
    });

    return [...pinnedColumns, ...dynamicColumns];
  }

  _transformTree(tree = []) {
    const walk = (nodes = [], level = 0, parentKey = '') => {
      return nodes.map((node, index) => {
        const rowId = this._resolveRowId(node, parentKey, index);
        const children = this._getChildren(node);

        const formatted = {
          id: rowId,
          name: node.snapshot_uraian || node.uraian || node.nama || node.name || 'Pekerjaan',
          code: node.snapshot_kode || node.kode || '',
          unit: node.snapshot_satuan || node.satuan || node.unit || '',
          volume: this._getVolume(node),
          raw: node,
          level,
          pekerjaanId: node.pekerjaan_id || node.id || rowId,
        };

        if (children.length > 0) {
          formatted.subRows = walk(children, level + 1, `${rowId}`);
        }
        return formatted;
      });
    };

    return walk(tree, 0);
  }

  _getChildren(node) {
    if (!node) {
      return [];
    }
    if (Array.isArray(node.children) && node.children.length) {
      return node.children;
    }
    if (Array.isArray(node.sub) && node.sub.length) {
      return node.sub;
    }
    return [];
  }

  _resolveRowId(node, parentKey, index) {
    if (!node) {
      return `${parentKey || 'row'}-${index}`;
    }
    return node.id || node.pekerjaan_id || `${parentKey || 'row'}-${index}`;
  }

  _getVolume(node) {
    const nodeId = node?.id || node?.pekerjaan_id;
    if (nodeId && this.state.volumeMap instanceof Map && this.state.volumeMap.has(nodeId)) {
      return this.state.volumeMap.get(nodeId);
    }
    return node.volume || node.qty || '-';
  }

  _renderTable() {
    if (!this.table) {
      return;
    }
    this._renderHeader();
    this._setupVirtualizer();
    this._renderVirtualRows();
  }

  _renderHeader() {
    if (!this.headerInner || !this.table) {
      return;
    }
    this.headerInner.innerHTML = '';
    const headerGroups = this.table.getHeaderGroups();
    headerGroups.forEach((headerGroup) => {
      const rowEl = document.createElement('div');
      rowEl.className = 'tanstack-grid-header-row';
      rowEl.style.minWidth = `${this.totalColumnWidth}px`;
      headerGroup.headers.forEach((header) => {
        if (header.isPlaceholder) {
          return;
        }
        const cellEl = document.createElement('div');
        cellEl.className = 'tanstack-grid-header-cell';
        const width = header.column.columnDef.meta?.width || header.getSize() || 120;
        cellEl.style.width = `${width}px`;
        cellEl.style.minWidth = `${width}px`;
        this._applyPinnedStyles(cellEl, header.column.columnDef);
        const content = flexRender(header.column.columnDef.header, header.getContext());
        const labelText = typeof content === 'string' ? content : header.column.columnDef.header;
        if (header.column.columnDef.meta?.timeColumn) {
          const titleEl = document.createElement('div');
          titleEl.className = 'tanstack-header-title';
          titleEl.textContent = labelText;
          cellEl.appendChild(titleEl);

          const rangeText = this._formatHeaderRange(header.column.columnDef.meta?.columnMeta);
          if (rangeText) {
            const rangeEl = document.createElement('div');
            rangeEl.className = 'tanstack-header-range';
            rangeEl.textContent = rangeText;
            cellEl.appendChild(rangeEl);
          }
        } else {
          cellEl.textContent = labelText;
        }
        rowEl.appendChild(cellEl);
      });
      this.headerInner.appendChild(rowEl);
    });
    if (this.headerInner) {
      this.headerInner.style.width = `${this.totalColumnWidth}px`;
    }
    this._syncHeaderScroll();
  }

  _setupVirtualizer() {
    const rows = this.table.getRowModel().rows || [];

    this.virtualizer = new Virtualizer({
      count: rows.length,
      getScrollElement: () => this.bodyScroll,
      estimateSize: () => this.rowHeight,
      overscan: 8,
      scrollToFn: elementScroll,
      observeElementRect,
      observeElementOffset,
      onChange: () => this._renderVirtualRows(),
    });
    this.virtualizer.measure();
  }

  _renderVirtualRows() {
    if (!this.table || !this.virtualizer) {
      return;
    }

    const rows = this.table.getRowModel().rows || [];
    const virtualItems = this.virtualizer.getVirtualItems();
    const itemsToRender = virtualItems.length
      ? virtualItems
      : rows.map((_, index) => ({
          index,
          start: index * this.rowHeight,
          size: this.rowHeight,
        }));

    this.bodyInner.innerHTML = '';
    const totalSize = this.virtualizer.getTotalSize() || rows.length * this.rowHeight;
    this.bodyInner.style.height = `${totalSize}px`;
    if (this.totalColumnWidth > 0) {
      this.bodyInner.style.minWidth = `${this.totalColumnWidth}px`;
    }

    itemsToRender.forEach((virtualRow) => {
      const row = rows[virtualRow.index];
      if (!row) {
        return;
      }
      const rowEl = document.createElement('div');
      rowEl.className = 'tanstack-grid-virtual-row';
      rowEl.style.transform = `translateY(${virtualRow.start}px)`;
      rowEl.style.height = `${virtualRow.size || this.rowHeight}px`;
      rowEl.style.display = 'flex';
      rowEl.style.minWidth = `${this.totalColumnWidth}px`;
      const derivedRowId = row.original?.pekerjaanId || row.original?.id || row.id;
      rowEl.dataset.rowId = derivedRowId;
      this._applyRowStateClasses(rowEl, row);

      row.getVisibleCells().forEach((cell) => {
        const cellEl = document.createElement('div');
        cellEl.className = 'tanstack-grid-cell';
        const width = cell.column.columnDef.meta?.width || cell.column.getSize?.() || 120;
        cellEl.style.width = `${width}px`;
        cellEl.style.minWidth = `${width}px`;
        this._applyPinnedStyles(cellEl, cell.column.columnDef);
        cellEl.dataset.columnId = cell.column.columnDef.id || '';
        cellEl.dataset.rowId = rowEl.dataset.rowId;

        if (cell.column.columnDef.id === 'name') {
          this._renderTreeCell(cellEl, row);
        } else if (cell.column.columnDef.meta?.timeColumn) {
          const pekerjaanId = row.original?.pekerjaanId || row.original?.id;
          const columnId = this._getColumnId(cell.column.columnDef.meta?.columnMeta, cell.column.columnDef);
          this._renderTimeCell(cellEl, row, pekerjaanId, columnId, cell.column.columnDef.meta?.columnMeta, cell.column.columnDef);
        } else {
          this._renderPinnedCell(cellEl, cell, row);
        }
        rowEl.appendChild(cellEl);
      });

      this.bodyInner.appendChild(rowEl);
    });
  }

  _renderTreeCell(cellEl, row) {
    cellEl.classList.add('tree-cell');
    const level = row.original?.level || 0;
    cellEl.style.paddingLeft = `${16 + level * 18}px`;

    const labelSpan = document.createElement('span');
    labelSpan.className = 'tree-label-text';
    labelSpan.textContent = row.original?.name || row.original?.raw?.nama || row.getValue?.() || '-';
    cellEl.appendChild(labelSpan);

    if ((row.subRows || []).length > 0) {
      const toggle = document.createElement('span');
      toggle.className = 'tanstack-grid-toggle';
      toggle.textContent = row.getIsExpanded() ? '▾' : '▸';
      toggle.addEventListener('click', (event) => {
        event.stopPropagation();
        row.toggleExpanded();
        this._renderTable();
      });
      cellEl.prepend(toggle);
    }
  }

  _renderPinnedCell(cellEl, cell, row) {
    const align = cell.column.columnDef.meta?.align;
    if (align === 'end') {
      cellEl.style.justifyContent = 'flex-end';
    } else if (align === 'center') {
      cellEl.style.justifyContent = 'center';
    }
    const value = typeof cell.getValue === 'function' ? cell.getValue() : cell.value;
    cellEl.textContent = this._formatCellValue(value, cell.column.columnDef);
  }

  _renderTimeCell(cellEl, row, pekerjaanId, columnId, columnMeta, columnDef) {
    cellEl.classList.add('time-cell');
    const rawValue = this._getRawCellValue(pekerjaanId, columnId, columnMeta);
    const displayValue = this._formatTimeCellDisplay(rawValue, row, columnMeta);
    const cellKey = this._getCellKey(pekerjaanId, columnId);

    cellEl.textContent = displayValue;
    cellEl.dataset.cellId = cellKey;
    cellEl.dataset.pekerjaanId = pekerjaanId;
    cellEl.dataset.columnId = columnId;
    const rowEditable = this._isRowEditable(row);
    const isEditable = rowEditable && this._isColumnEditable(columnDef);
    cellEl.tabIndex = isEditable ? 0 : -1;
    if (isEditable) {
      cellEl.classList.add('editable');
    } else {
      cellEl.classList.add('readonly');
    }

    if (this._isCellModified(pekerjaanId, columnId)) {
      cellEl.classList.add('modified');
    }
    this._applyValidationClasses(cellEl, cellKey);

    if (isEditable) {
      const baseContext = {
        row,
        pekerjaanId,
        columnId,
        columnMeta,
        columnDef,
      };

      const editHandler = (event) => {
        event.preventDefault();
        this._beginEditCell(cellEl, baseContext);
      };

      cellEl.addEventListener('dblclick', editHandler);
      cellEl.addEventListener('keydown', (event) => {
        if (cellEl.classList.contains('editing')) {
          return;
        }
        if (event.key === 'Enter') {
          editHandler(event);
        } else if (event.key === 'Tab') {
          event.preventDefault();
          const direction = event.shiftKey ? 'prev' : 'next';
          this._focusSiblingCell(baseContext, direction);
        } else if (this._shouldAutoBeginEditFromKey(event)) {
          event.preventDefault();
          this._beginEditCell(cellEl, baseContext);
          this._seedEditorValueFromKey(event);
        }
      });
    }
  }

  _renderRowsOnly() {
    if (this.virtualizer) {
      this.virtualizer.measure();
      this._renderVirtualRows();
    }
  }

  _getRawCellValue(pekerjaanId, columnId, columnMeta) {
    if (!pekerjaanId || !columnId || !this.stateManager) {
      return 0;
    }
    if (Array.isArray(columnMeta?.childColumns) && columnMeta.childColumns.length > 0) {
      return columnMeta.childColumns.reduce((sum, childMeta) => {
        const childId = this._resolveColumnMetaId(childMeta);
        if (!childId) {
          return sum;
        }
        return sum + this._getRawCellValue(pekerjaanId, childId, childMeta);
      }, 0);
    }
    if (this.inputMode === 'cost') {
      return this._getCostValue(pekerjaanId, columnId);
    }
    if (typeof this.stateManager.getCellValue === 'function') {
      return this.stateManager.getCellValue(pekerjaanId, columnId) || 0;
    }
    return 0;
  }

  _getCostValue(pekerjaanId, columnId) {
    const actualState = this.stateManager?.states?.actual;
    if (!actualState) {
      return 0;
    }
    const cellKey = this._getCellKey(pekerjaanId, columnId);
    return actualState.costModifiedCells.get(cellKey) ?? actualState.costAssignmentMap.get(cellKey) ?? 0;
  }

  _formatTimeCellDisplay(rawValue, row, columnMeta) {
    if (this.inputMode === 'volume') {
      const rowVolume = this._getRowVolume(row);
      const volumeValue = this._percentToVolume(rawValue, rowVolume);
      if (!Number.isFinite(volumeValue) || volumeValue === 0) {
        return '-';
      }
      return volumeValue.toLocaleString('id-ID', { maximumFractionDigits: 3 });
    }
    if (this.inputMode === 'cost') {
      const numericValue = Number(rawValue || 0);
      if (!Number.isFinite(numericValue) || numericValue === 0) {
        return '-';
      }
      return numericValue.toLocaleString('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 });
    }
    const numericRaw = Number(rawValue);
    if (!Number.isFinite(numericRaw) || numericRaw === 0) {
      return '-';
    }
    return numericRaw.toFixed(1);
  }

  _getCellKey(pekerjaanId, columnId) {
    return `${pekerjaanId}-${columnId}`;
  }

  _applyValidationClasses(cellEl, cellKey) {
    if (!cellEl) {
      return;
    }
    cellEl.classList.remove('invalid', 'warning');
    const state = typeof this.options.getCellValidationState === 'function'
      ? this.options.getCellValidationState(cellKey)
      : null;
    if (state === 'error') {
      cellEl.classList.add('invalid');
    } else if (state === 'warning') {
      cellEl.classList.add('warning');
    }
  }

  _isCellModified(pekerjaanId, columnId) {
    const cellKey = this._getCellKey(pekerjaanId, columnId);
    const currentState = this.stateManager?._getCurrentState?.();
    if (!currentState) {
      return false;
    }
    if (this.inputMode === 'cost') {
      return currentState.costModifiedCells?.has(cellKey) || false;
    }
    return currentState.modifiedCells?.has(cellKey) || false;
  }

  _beginEditCell(cellEl, context) {
    if (!cellEl || !context) {
      return;
    }
    const columnDef = context.columnDef || (context.columnMeta ? { meta: context.columnMeta } : null);
    if (!this._isRowEditable(context.row) || (columnDef && !this._isColumnEditable(columnDef))) {
      return;
    }
    const progressMode = (this.state?.progressMode || this.stateManager?.currentMode || 'planned').toLowerCase();
    if (this.inputMode === 'cost' && progressMode !== 'actual') {
      this._showValidationToast({
        isValid: false,
        message: 'Biaya aktual hanya bisa diedit pada mode Realisasi',
        level: 'warning',
      });
      return;
    }
    if (this.activeEditor && this.activeEditor.cellEl !== cellEl) {
      this._finishEdit(true);
    } else if (cellEl.classList.contains('editing')) {
      return;
    }

    const input = document.createElement('input');
    input.type = 'number';
    input.inputMode = 'decimal';
    input.className = 'tanstack-cell-editor form-control form-control-sm';
    input.value = this._getEditorInitialValue(context);

    cellEl.classList.add('editing');
    cellEl.innerHTML = '';
    cellEl.appendChild(input);
    input.focus();
    input.select();

    this.activeEditor = { cellEl, input, context };

    input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        this._editorNavDirection = event.shiftKey ? 'up' : 'down';
        this._finishEdit(true);
      } else if (event.key === 'Tab') {
        event.preventDefault();
        this._editorNavDirection = event.shiftKey ? 'prev' : 'next';
        this._finishEdit(true);
      } else if (event.key === 'Escape') {
        event.preventDefault();
        this._editorNavDirection = null;
        this._finishEdit(false);
      }
    });
    input.addEventListener('blur', () => {
      this._editorNavDirection = null;
      this._finishEdit(true);
    });
  }

  _finishEdit(save) {
    if (!this.activeEditor) {
      return;
    }
    const { cellEl, input, context } = this.activeEditor;
    this.activeEditor = null;

    const newValue = input.value;
    cellEl.classList.remove('editing');
    cellEl.innerHTML = '';

    let committed = false;
    if (save) {
      committed = this._commitEditorValue(context, newValue);
    }

    this._renderRowsOnly();
    if (committed && this._editorNavDirection) {
      this._focusSiblingCell(context, this._editorNavDirection, { autoEdit: true });
    }
    this._editorNavDirection = null;
  }

  _commitEditorValue(context, rawInput) {
    if (!context) {
      return false;
    }
    const pekerjaanId = context.pekerjaanId;
    const columnId = context.columnId;
    const rowVolume = this._getRowVolume(context.row);
    const isVolumeMode = this.inputMode === 'volume';
    const isCostMode = this.inputMode === 'cost';

    let validationResult = null;
    let canonicalValue = 0;
    let displayValue = rawInput;

    if (isCostMode) {
      validationResult = this._validateCostValue(rawInput);
      if (!validationResult.isValid) {
        this._showValidationToast(validationResult);
        return false;
      }
      canonicalValue = validationResult.value;
      displayValue = validationResult.value;
    } else {
      validationResult = validateCellValue(rawInput, {
        min: 0,
        max: isVolumeMode ? rowVolume || 0 : 100,
        precision: isVolumeMode ? 3 : 1,
      });
      if (!validationResult.isValid && validationResult.message) {
        this._showValidationToast(validationResult);
      }
      const fallbackValue = validationResult.value ?? parseFloat(rawInput);
      canonicalValue = Number.isFinite(fallbackValue) ? fallbackValue : 0;
      displayValue = validationResult.value ?? canonicalValue;
    }

    let valueType = 'percentage';
    if (isVolumeMode) {
      valueType = 'volume';
      const numericDisplay = Number(displayValue);
      canonicalValue = this._volumeToPercent(numericDisplay, rowVolume);
      displayValue = numericDisplay;
    } else if (isCostMode) {
      valueType = 'cost';
    }

    if (typeof this.options.onCellChange === 'function') {
      this.options.onCellChange({
        cellKey: this._getCellKey(pekerjaanId, columnId),
        value: Number.isFinite(canonicalValue) ? canonicalValue : 0,
        columnMeta: context.columnMeta,
        displayValue,
        isVolumeMode,
        validation: validationResult,
        pekerjaanId,
        columnId,
        valueType,
      });
    }
    return true;
  }

  _getEditorInitialValue(context) {
    if (!context) {
      return '';
    }
    const rawValue = this._getRawCellValue(context.pekerjaanId, context.columnId);
    if (this.inputMode === 'volume') {
      const rowVolume = this._getRowVolume(context.row);
      const volumeValue = this._percentToVolume(rawValue, rowVolume);
      return Number.isFinite(volumeValue) ? volumeValue.toString() : '';
    }
    if (this.inputMode === 'cost') {
      return Number.isFinite(rawValue) ? rawValue.toString() : '';
    }
    return Number.isFinite(rawValue) ? rawValue.toString() : '';
  }

  _validateCostValue(rawInput) {
    if (rawInput === null || typeof rawInput === 'undefined' || rawInput === '') {
      return {
        isValid: true,
        message: '',
        level: 'info',
        value: 0,
      };
    }
    const numericValue = Number(rawInput);
    if (!Number.isFinite(numericValue) || numericValue < 0) {
      return {
        isValid: false,
        message: 'Nilai biaya harus berupa angka positif',
        level: 'error',
        value: 0,
      };
    }
    return {
      isValid: true,
      message: '',
      level: 'info',
      value: numericValue,
    };
  }

  _showValidationToast(validationResult) {
    if (!validationResult || !validationResult.message) {
      return;
    }
    if (typeof this.options.showToast === 'function') {
      const type = validationResult.level === 'warning' ? 'warning' : 'danger';
      this.options.showToast(validationResult.message, type);
    }
  }

  _volumeToPercent(volumeValue, totalVolume) {
    const numericVolume = Number(volumeValue);
    const numericTotal = Number(totalVolume);
    if (!Number.isFinite(numericVolume) || numericVolume < 0 || !Number.isFinite(numericTotal) || numericTotal <= 0) {
      return 0;
    }
    const percent = (numericVolume / numericTotal) * 100;
    return Math.min(100, Math.max(0, percent));
  }

  _percentToVolume(percent, totalVolume) {
    const numericPercent = Number(percent);
    const numericVolume = Number(totalVolume);
    if (!Number.isFinite(numericPercent) || !Number.isFinite(numericVolume)) {
      return 0;
    }
    return (numericPercent / 100) * numericVolume;
  }

  _getRowVolume(row) {
    return Number(row?.original?.volume) || 0;
  }

  _getColumnId(columnMeta, columnDef) {
    return columnMeta?.fieldId || columnMeta?.id || columnDef?.id;
  }

  _getColumnWidth(columnDef) {
    return Number(columnDef?.meta?.width) || 120;
  }

  _calculateTotalWidth(columns = []) {
    if (!Array.isArray(columns) || !columns.length) {
      return 0;
    }
    return columns.reduce((total, col) => total + this._getColumnWidth(col), 0);
  }

  _resolveColumnMetaId(columnMeta) {
    if (!columnMeta) {
      return null;
    }
    return columnMeta.fieldId || columnMeta.field_id || columnMeta.id || columnMeta.columnId || columnMeta.column_id || columnMeta.tahapanId || columnMeta.tahapan_id || null;
  }

  _applyPinnedStyles(element, columnDef) {
    if (!element || !columnDef) {
      return;
    }
    if (columnDef.meta?.pinned) {
      const offset = columnDef.meta?.stickyOffset || 0;
      element.classList.add('pinned');
      element.style.left = `${offset}px`;
      element.style.position = 'sticky';
      element.style.zIndex = columnDef.meta?.timeColumn ? 2 : 4;
    } else {
      element.classList.remove('pinned');
      element.style.left = '';
    }
  }

  _applyRowStateClasses(rowEl, row) {
    if (!rowEl || !row) {
      return;
    }
    rowEl.classList.remove('row-save-error', 'row-warning');
    const pekerjaanId = row.original?.pekerjaanId || row.original?.id;
    const numericId = Number(pekerjaanId);
    if (!Number.isFinite(numericId)) {
      return;
    }
    if (this.state?.saveErrorRows instanceof Set && this.state.saveErrorRows.has(numericId)) {
      rowEl.classList.add('row-save-error');
      return;
    }
    const warningSets = [
      this.state?.autoWarningRows,
      this.state?.volumeWarningRows,
      this.state?.validationWarningRows,
      this.state?.failedRows,
    ];
    const hasWarning = warningSets.some((set) => set instanceof Set && set.has(numericId));
    if (hasWarning) {
      rowEl.classList.add('row-warning');
    }
  }

  _getRowById(rowId) {
    if (!this.table || typeof rowId === 'undefined' || rowId === null) {
      return null;
    }
    const rows = this.table.getRowModel()?.rows || [];
    const target = String(rowId);
    return rows.find((row) => {
      const candidate = row.original?.pekerjaanId || row.original?.id || row.id;
      return String(candidate) === target;
    }) || null;
  }

  _queryCellElement(rowId, columnId) {
    if (!this.bodyInner || !rowId || !columnId) {
      return null;
    }
    const safeRowId = typeof CSS !== 'undefined' && typeof CSS.escape === 'function'
      ? CSS.escape(String(rowId))
      : rowId;
    const safeColumnId = typeof CSS !== 'undefined' && typeof CSS.escape === 'function'
      ? CSS.escape(String(columnId))
      : columnId;
    return this.bodyInner.querySelector(
      `.tanstack-grid-cell[data-row-id="${safeRowId}"][data-column-id="${safeColumnId}"]`
    );
  }

  _autoEditCell(rowId, columnDef) {
    if (!rowId || !columnDef) {
      return;
    }
    const row = this._getRowById(rowId);
    if (!row) {
      return;
    }
    if (!this._isRowEditable(row) || !this._isColumnEditable(columnDef)) {
      return;
    }
    const cellEl = this._queryCellElement(rowId, columnDef.id);
    if (cellEl) {
      this._beginEditCell(cellEl, {
        row,
        pekerjaanId: rowId,
        columnId: columnDef.id,
        columnMeta: columnDef.meta?.columnMeta,
        columnDef,
      });
    }
  }

  _shouldAutoBeginEditFromKey(event) {
    if (!event || event.altKey || event.metaKey || event.ctrlKey) {
      return false;
    }
    if (event.key === 'Backspace' || event.key === 'Delete') {
      return true;
    }
    return event.key.length === 1 && /[0-9.,]/.test(event.key);
  }

  _seedEditorValueFromKey(event) {
    if (!event || !this.activeEditor || !this.activeEditor.input) {
      return;
    }
    const input = this.activeEditor.input;
    if (event.key === 'Backspace' || event.key === 'Delete') {
      input.value = '';
      return;
    }
    if (event.key.length === 1) {
      const normalized = event.key === ',' ? '.' : event.key;
      input.value = normalized;
      const caret = normalized.length;
      input.setSelectionRange(caret, caret);
    }
  }

  _formatHeaderRange(columnMeta) {
    if (!columnMeta) {
      return '';
    }
    if (typeof columnMeta.rangeText === 'string' && columnMeta.rangeText.trim().length > 0) {
      return columnMeta.rangeText.replace(/\u00A0/g, ' ');
    }
    const start = this._formatHeaderDate(columnMeta.startDate || columnMeta.start_date);
    const end = this._formatHeaderDate(columnMeta.endDate || columnMeta.end_date);
    if (start && end) {
      return `${start} - ${end}`;
    }
    return start || end || '';
  }

  _formatHeaderDate(value) {
    if (!value) {
      return '';
    }
    const date = value instanceof Date ? value : new Date(value);
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
      return '';
    }
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    return `${day}/${month}`;
  }

  _ensureTableStateDefaults() {
    if (!this.tableState || typeof this.tableState !== 'object') {
      this.tableState = {};
    }
    const pinning = this.tableState.columnPinning || {};
    this.tableState.columnPinning = {
      left: Array.isArray(pinning.left) ? pinning.left : [],
      right: Array.isArray(pinning.right) ? pinning.right : [],
    };
    if (typeof this.tableState.expanded === 'undefined') {
      this.tableState.expanded = true;
    }
  }

  _updateTableState(key, updater) {
    if (!key) {
      return;
    }
    this._ensureTableStateDefaults();
    const previousValue = this.tableState[key];
    const nextValue = typeof updater === 'function' ? updater(previousValue) : updater;
    if (typeof nextValue === 'undefined') {
      return;
    }
    this.tableState = {
      ...this.tableState,
      [key]: nextValue,
    };
    if (this.table && typeof this.table.setOptions === 'function') {
      this.table.setOptions((prev) => ({
        ...prev,
        state: this.tableState,
      }));
    } else if (this.table && this.table.options) {
      this.table.options.state = this.tableState;
    }
  }

  _focusSiblingCell(context, direction, options = {}) {
    if (!context || !direction) {
      return;
    }
    const columns = this.currentColumns || [];
    const rows = this.table?.getRowModel()?.rows || [];
    const currentId = context.columnId || this._getColumnId(context.columnMeta, { id: context.columnId });
    const ids = columns.map((col) => col.id);
    const currentIndex = ids.indexOf(currentId);
    const rowId = context.row?.original?.pekerjaanId || context.row?.original?.id;
    if (currentIndex === -1) {
      return;
    }

    const horizontalDirections = new Set(['next', 'prev']);
    if (horizontalDirections.has(direction)) {
      const step = direction === 'prev' ? -1 : 1;
      let targetIndex = currentIndex + step;
      while (targetIndex >= 0 && targetIndex < columns.length) {
        const targetColumn = columns[targetIndex];
        if (this._isColumnEditable(targetColumn)) {
          this._focusCell(rowId, targetColumn.id);
          if (options.autoEdit) {
            this._autoEditCell(rowId, targetColumn);
          }
          return;
        }
        targetIndex += step;
      }
      return;
    }

    if (!rowId) {
      return;
    }
    const currentRowIndex = rows.findIndex((row) => {
      const candidateId = row.original?.pekerjaanId || row.original?.id || row.id;
      return String(candidateId) === String(rowId);
    });
    if (currentRowIndex === -1) {
      return;
    }
    const delta = direction === 'up' ? -1 : 1;
    let nextIndex = currentRowIndex + delta;
    while (nextIndex >= 0 && nextIndex < rows.length) {
      const targetRow = rows[nextIndex];
      const candidateId = targetRow.original?.pekerjaanId || targetRow.original?.id || targetRow.id;
      if (candidateId && this._isRowEditable(targetRow)) {
        const targetColumn = columns[currentIndex] || columns.find((col) => col.id === currentId);
        if (!targetColumn) {
          return;
        }
        this._focusCell(candidateId, targetColumn.id);
        if (options.autoEdit) {
          this._autoEditCell(candidateId, targetColumn);
        }
        return;
      }
      nextIndex += delta;
    }
  }

  _isColumnEditable(columnDef) {
    if (!columnDef?.meta?.timeColumn) {
      return false;
    }
    if (columnDef.meta?.readOnly || columnDef.meta?.columnMeta?.readOnly) {
      return false;
    }
    return true;
  }

  _isRowEditable(row) {
    if (!row || !row.original) {
      return true;
    }
    const nodeType = row.original?.raw?.type || row.original?.type || '';
    if (!nodeType) {
      return true;
    }
    return nodeType === 'pekerjaan';
  }

  _focusCell(rowId, columnId) {
    if (!rowId || !columnId || !this.bodyInner) {
      return;
    }
    const safeRowId = typeof CSS !== 'undefined' && typeof CSS.escape === 'function' ? CSS.escape(rowId) : rowId;
    const safeColumnId = typeof CSS !== 'undefined' && typeof CSS.escape === 'function' ? CSS.escape(columnId) : columnId;
    const selector = `.tanstack-grid-cell[data-row-id="${safeRowId}"][data-column-id="${safeColumnId}"]`;
    const target = this.bodyInner.querySelector(selector);
    if (target) {
      target.focus();
    }
  }

  _updateTopScrollWidth() {
    if (!this.topScrollInner || !this.bodyInner) {
      return;
    }
    window.requestAnimationFrame(() => {
      this.topScrollInner.style.width = `${this.bodyInner.scrollWidth}px`;
      this._syncHeaderScroll();
    });
  }

  _syncHeaderScroll() {
    if (!this.headerInner || !this.bodyScroll) {
      return;
    }
    const scrollLeft = this.bodyScroll.scrollLeft || 0;
    if (scrollLeft === this._lastScrollLeft) {
      return;
    }
    this._lastScrollLeft = scrollLeft;
    this.headerInner.style.marginLeft = `-${scrollLeft}px`;
  }

  _formatCellValue(value, columnDef) {
    const numericValue = Number(value);
    if (
      value === null ||
      typeof value === 'undefined' ||
      (Number.isFinite(numericValue) && numericValue === 0)
    ) {
      return '-';
    }
    if (columnDef?.meta?.timeColumn) {
      const mode = this.inputMode;
      if (mode === 'volume') {
        return Number(value || 0).toLocaleString('id-ID', { maximumFractionDigits: 2 });
      }
      return `${value}`;
    }
    if (typeof value === 'number') {
      return value.toLocaleString('id-ID', { maximumFractionDigits: 2 });
    }
    return String(value);
  }
}

export default TanStackGridManager;
