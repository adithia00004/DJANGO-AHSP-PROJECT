/**
 * Kurva S and Gantt overlays must line up with the grid cells.
 *
 * The grid container has viewport-relative padding (0.5vw / 0.5vh), so the
 * table body does not start at the container edge. Overlays used to position
 * their clip viewport from the container edge (+ header height), which shifted
 * the curve ~9px left on a 1800px window and a different amount on other
 * widths. The origin is now the measured body position.
 */

import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { KurvaSCanvasOverlay } from '../src/modules/kurva-s/KurvaSCanvasOverlay.js';
import { GanttCanvasOverlay } from '../src/modules/gantt/GanttCanvasOverlay.js';
import { getBodyOffsetInContainer } from '../src/modules/shared/canvas-utils.js';

const PINNED = 200;
// Container at (100, 50) with a 1px border; body starts after 9px padding
// and a 60px header.
const CONTAINER_RECT = { left: 100, top: 50, width: 1000, height: 700, x: 100, y: 50 };
const BODY_RECT = { left: 110, top: 115, width: 980, height: 600, x: 110, y: 115 };
const EXPECTED_BODY = { left: 110 - 100 - 1, top: 115 - 50 - 1 };

function makeCtx() {
  const fn = () => vi.fn();
  return {
    clearRect: fn(), fillRect: fn(), strokeRect: fn(), beginPath: fn(), moveTo: fn(),
    lineTo: fn(), stroke: fn(), fill: fn(), arc: fn(), fillText: fn(), save: fn(),
    restore: fn(), setLineDash: fn(), rect: fn(), clip: fn(), closePath: fn(),
    measureText: vi.fn(() => ({ width: 10 })),
    fillStyle: '#000', strokeStyle: '#000', lineWidth: 1,
  };
}

describe('overlay alignment with padded grid container', () => {
  let container;
  let bodyScroll;
  let tableManager;
  let originalElementFromPoint;

  beforeEach(() => {
    container = document.createElement('div');
    Object.defineProperty(container, 'clientLeft', { value: 1, configurable: true });
    Object.defineProperty(container, 'clientTop', { value: 1, configurable: true });
    vi.spyOn(container, 'getBoundingClientRect').mockReturnValue(CONTAINER_RECT);
    document.body.appendChild(container);

    bodyScroll = document.createElement('div');
    vi.spyOn(bodyScroll, 'getBoundingClientRect').mockReturnValue(BODY_RECT);
    container.appendChild(bodyScroll);

    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(makeCtx());
    originalElementFromPoint = document.elementFromPoint;
    document.elementFromPoint = vi.fn(() => null);

    tableManager = {
      bodyScroll,
      options: {},
      state: {},
      currentColumns: [],
      getPinnedColumnsWidth: vi.fn(() => PINNED),
      getAllCellBoundingRects: vi.fn(() => [
        { x: PINNED, y: 0, width: 150, height: 40, pekerjaanId: '1', columnId: 'col_1' },
        { x: PINNED + 150, y: 0, width: 150, height: 40, pekerjaanId: '1', columnId: 'col_2' },
      ]),
      getCellBoundingRects: vi.fn(() => []),
    };
  });

  afterEach(() => {
    document.elementFromPoint = originalElementFromPoint;
    container.remove();
    vi.restoreAllMocks();
  });

  test('body offset is measured inside the container padding box', () => {
    expect(getBodyOffsetInContainer(container, bodyScroll)).toEqual(EXPECTED_BODY);
  });

  test('Kurva S: canvas x=0 sits exactly on the frozen-column boundary of the body', () => {
    const overlay = new KurvaSCanvasOverlay(tableManager);
    overlay.curveData = {
      planned: [{ columnId: 'col_1', weekNumber: 1, cumulativeProgress: 50 }],
      actual: [],
    };
    overlay.syncWithTable();

    const clipLeft = parseFloat(overlay.clipViewport.style.left);
    const canvasLeft = parseFloat(overlay.canvas.style.left);
    expect(clipLeft + canvasLeft).toBe(EXPECTED_BODY.left + PINNED);
    expect(parseFloat(overlay.clipViewport.style.top)).toBe(EXPECTED_BODY.top);
  });

  test('Gantt: canvas x=0 sits exactly on the frozen-column boundary of the body', () => {
    const overlay = new GanttCanvasOverlay(tableManager);
    overlay.show = overlay.show.bind(overlay);
    overlay.syncWithTable();

    const clipLeft = parseFloat(overlay.clipViewport.style.left);
    const canvasLeft = parseFloat(overlay.canvas.style.left || '0');
    expect(clipLeft + canvasLeft).toBe(EXPECTED_BODY.left + PINNED);
    expect(parseFloat(overlay.clipViewport.style.top) + parseFloat(overlay.canvas.style.top || '0'))
      .toBe(EXPECTED_BODY.top);
  });
});
