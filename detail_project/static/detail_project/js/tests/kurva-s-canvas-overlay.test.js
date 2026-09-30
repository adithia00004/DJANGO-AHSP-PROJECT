/**
 * Regression tests for KurvaSCanvasOverlay.syncWithTable().
 *
 * A ReferenceError in syncWithTable (undeclared `gridBounds` in the
 * work-period marker call) aborted the tab switch to Kurva S after the curve
 * was already drawn, so `state.displayMode` stayed on the previous tab and the
 * PNG download produced a Gantt chart instead of a Kurva S.
 */

import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { KurvaSCanvasOverlay } from '../src/modules/kurva-s/KurvaSCanvasOverlay.js';

function makeCtx() {
  return {
    clearRect: vi.fn(),
    fillRect: vi.fn(),
    strokeRect: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
    fill: vi.fn(),
    arc: vi.fn(),
    fillText: vi.fn(),
    save: vi.fn(),
    restore: vi.fn(),
    setLineDash: vi.fn(),
    fillStyle: '#000000',
    strokeStyle: '#000000',
    lineWidth: 1,
  };
}

describe('KurvaSCanvasOverlay.syncWithTable', () => {
  let parent;
  let bodyScroll;
  let ctx;
  let originalElementFromPoint;

  const cellRects = [
    { x: 200, y: 0, width: 100, height: 40, pekerjaanId: '1', columnId: 'col_1' },
    { x: 300, y: 0, width: 100, height: 40, pekerjaanId: '1', columnId: 'col_2' },
    { x: 200, y: 40, width: 100, height: 40, pekerjaanId: '2', columnId: 'col_1' },
    { x: 300, y: 40, width: 100, height: 40, pekerjaanId: '2', columnId: 'col_2' },
  ];

  const makeTableManager = (state = {}) => ({
    bodyScroll,
    options: {},
    state,
    currentColumns: [
      { meta: { timeColumn: true, columnMeta: { fieldId: 'col_1', startDate: '2026-01-01', endDate: '2026-01-07' } } },
      { meta: { timeColumn: true, columnMeta: { fieldId: 'col_2', startDate: '2026-01-08', endDate: '2026-01-14' } } },
    ],
    getAllCellBoundingRects: vi.fn(() => cellRects),
    getPinnedColumnsWidth: vi.fn(() => 200),
  });

  const curveData = {
    planned: [
      { columnId: 'col_1', weekNumber: 1, cumulativeProgress: 40 },
      { columnId: 'col_2', weekNumber: 2, cumulativeProgress: 100 },
    ],
    actual: [{ columnId: 'col_1', weekNumber: 1, cumulativeProgress: 30 }],
  };

  beforeEach(() => {
    parent = document.createElement('div');
    document.body.appendChild(parent);
    bodyScroll = document.createElement('div');
    parent.appendChild(bodyScroll);

    ctx = makeCtx();
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(ctx);
    originalElementFromPoint = document.elementFromPoint;
    document.elementFromPoint = vi.fn(() => null);
  });

  afterEach(() => {
    document.elementFromPoint = originalElementFromPoint;
    parent.remove();
    vi.restoreAllMocks();
  });

  test('does not throw for a project without an additional work period', () => {
    const overlay = new KurvaSCanvasOverlay(makeTableManager({}));
    overlay.curveData = curveData;

    expect(() => overlay.syncWithTable()).not.toThrow();
    expect(ctx.arc).toHaveBeenCalled();
  });

  test('draws no second (dashed) boundary line when an additional period exists', () => {
    const overlay = new KurvaSCanvasOverlay(makeTableManager({
      workPeriodMeta: { contract_end: '2026-01-10', additional_end: '2026-01-20' },
    }));
    overlay.curveData = curveData;

    expect(() => overlay.syncWithTable()).not.toThrow();
    // Owner decision: the grid's column-edge border is the only boundary
    // marker. The overlay must not add the old [6, 4] dashed line.
    expect(ctx.setLineDash).not.toHaveBeenCalledWith([6, 4]);
  });
});
