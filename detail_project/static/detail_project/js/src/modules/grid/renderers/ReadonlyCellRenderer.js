export class ReadonlyCellRenderer {
  renderTimeCell(context) {
    const { manager, cellEl, row, pekerjaanId, columnId, columnMeta, columnDef } = context;
    // Reuse legacy renderer but marked readonly to preserve current Kurva-S behaviour.
    cellEl.classList.add('readonly');
    return manager._renderTimeCellLegacy(cellEl, row, pekerjaanId, columnId, columnMeta, columnDef);
  }
}
