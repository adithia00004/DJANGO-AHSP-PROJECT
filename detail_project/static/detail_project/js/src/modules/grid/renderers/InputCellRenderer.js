export class InputCellRenderer {
  renderTimeCell(context) {
    const { manager, cellEl, row, pekerjaanId, columnId, columnMeta, columnDef } = context;
    return manager._renderTimeCellLegacy(cellEl, row, pekerjaanId, columnId, columnMeta, columnDef);
  }
}
