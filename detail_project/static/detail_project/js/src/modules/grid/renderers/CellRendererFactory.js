import { InputCellRenderer } from './InputCellRenderer.js';
import { GanttCellRenderer } from './GanttCellRenderer.js';
import { ReadonlyCellRenderer } from './ReadonlyCellRenderer.js';

export class CellRendererFactory {
  static create(mode = 'input') {
    const normalized = (mode || 'input').toLowerCase();
    switch (normalized) {
      case 'input':
        return new InputCellRenderer();
      case 'gantt-cell':
      case 'gantt':
        return new GanttCellRenderer();
      case 'readonly':
      case 'kurva':
        return new ReadonlyCellRenderer();
      default:
        return new InputCellRenderer();
    }
  }
}
