export class GanttCellRenderer {
  renderTimeCell(context) {
    const { manager, cellEl, row, pekerjaanId, columnId, columnMeta } = context;
    // Minimal cell for overlay: no text/input, only dimensions/datasets for overlay positioning.
    cellEl.classList.add('gantt-cell');
    const cellKey = manager._getCellKey(pekerjaanId, columnId);
    cellEl.dataset.cellId = cellKey;
    cellEl.dataset.pekerjaanId = String(pekerjaanId);
    cellEl.dataset.columnId = String(columnId);
    cellEl.tabIndex = -1;
    // Preserve validation/modified styling for overlay hints (optional)
    if (manager._isCellModified(pekerjaanId, columnId)) {
      cellEl.classList.add('modified');
    }
    manager._applyValidationClasses(cellEl, cellKey);
    // Do not render text or attach editors; overlay canvas handles visuals.
  }
}
