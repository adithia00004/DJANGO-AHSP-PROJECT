/**
 * Unit Tests for GanttCanvasOverlay
 *
 * Tests canvas rendering, bar drawing, and overlay interactions
 * for the Gantt chart visualization.
 *
 * To run: npm run test:frontend
 */

import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { GanttCanvasOverlay } from '../src/modules/gantt/GanttCanvasOverlay.js';

describe('GanttCanvasOverlay', () => {
  let overlay;
  let mockTableManager;
  let mockBodyScroll;
  let mockCanvas;

  beforeEach(() => {
    // Create mock body scroll container
    mockBodyScroll = document.createElement('div');
    // Use Object.defineProperty to make scrollWidth/scrollHeight writable
    Object.defineProperties(mockBodyScroll, {
      scrollWidth: { value: 1200, writable: true, configurable: true },
      scrollHeight: { value: 1000, writable: true, configurable: true },
      scrollLeft: { value: 0, writable: true, configurable: true },
      clientWidth: { value: 1000, writable: true, configurable: true },
    });
    mockBodyScroll.style.width = '1000px';
    mockBodyScroll.style.height = '800px';
    document.body.appendChild(mockBodyScroll);
    mockBodyScroll.addEventListener = vi.fn();
    mockBodyScroll.removeEventListener = vi.fn();

    // Mock canvas context
    const mockCtx = {
      clearRect: vi.fn(),
      fillRect: vi.fn(),
      strokeRect: vi.fn(),
      beginPath: vi.fn(),
      moveTo: vi.fn(),
      lineTo: vi.fn(),
      stroke: vi.fn(),
      closePath: vi.fn(),
      fill: vi.fn(),
      fillStyle: '#000000',
      strokeStyle: '#000000',
      lineWidth: 1,
    };

    // Mock canvas
    mockCanvas = document.createElement('canvas');
    vi.spyOn(mockCanvas, 'getBoundingClientRect').mockReturnValue({
      left: 0,
      top: 0,
      width: 1200,
      height: 1000,
    });
    mockCanvas.getContext = vi.fn(() => mockCtx);

    // Override createElement for canvas
    const originalCreateElement = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tag) => {
      if (tag === 'canvas') {
        return mockCanvas;
      }
      return originalCreateElement(tag);
    });

    mockTableManager = {
      bodyScroll: mockBodyScroll,
      options: { debugUnifiedTable: false },
      state: { debugUnifiedTable: false },
      getCellBoundingRects: vi.fn(() => []),
      getPinnedColumnsWidth: vi.fn(() => 0),
    };

    overlay = new GanttCanvasOverlay(mockTableManager);
  });

  afterEach(() => {
    if (overlay && overlay.visible) {
      overlay.hide();
    }
    if (mockBodyScroll && document.body.contains(mockBodyScroll)) {
      document.body.removeChild(mockBodyScroll);
    }
    if (window?.GanttOverlayMetrics) {
      delete window.GanttOverlayMetrics;
    }
    vi.restoreAllMocks();
  });

  describe('Constructor and Initialization', () => {
    test('initializes with canvas element', () => {
      expect(overlay.canvas).toBeTruthy();
      expect(overlay.canvas.className).toBe('gantt-canvas-overlay');
    });

    test('initializes with 2D context', () => {
      expect(overlay.ctx).toBeTruthy();
    });

    test('initializes with empty state', () => {
      expect(overlay.visible).toBe(false);
      expect(overlay.barData).toEqual([]);
      expect(overlay.dependencies).toEqual([]);
      expect(overlay.barRects).toEqual([]);
      expect(overlay.tooltip).toBeNull();
    });

    test('enables debug mode from tableManager options', () => {
      const debugTableManager = {
        ...mockTableManager,
        options: { debugUnifiedTable: true },
      };
      const debugOverlay = new GanttCanvasOverlay(debugTableManager);

      expect(debugOverlay.debug).toBe(true);
    });

    test('enables debug mode from window flag', () => {
      window.DEBUG_UNIFIED_TABLE = true;
      const debugOverlay = new GanttCanvasOverlay(mockTableManager);

      expect(debugOverlay.debug).toBe(true);
      window.DEBUG_UNIFIED_TABLE = false;
    });

    test('binds scroll listener to bodyScroll', () => {
      const scrollListenerCount = mockBodyScroll.addEventListener.mock?.calls?.length || 0;
      expect(scrollListenerCount).toBeGreaterThan(0);
    });
  });

  describe('show()', () => {
    test('appends canvas to bodyScroll', () => {
      overlay.show();

      expect(mockBodyScroll.contains(overlay.canvas)).toBe(true);
    });

    test('sets visible flag to true', () => {
      overlay.show();

      expect(overlay.visible).toBe(true);
    });

    test('calls syncWithTable after showing', () => {
      const syncSpy = vi.spyOn(overlay, 'syncWithTable');
      overlay.show();

      expect(syncSpy).toHaveBeenCalled();
    });

    test('does nothing if already visible', () => {
      overlay.show();
      const initialParent = overlay.canvas.parentNode;

      overlay.show(); // Call again

      expect(overlay.canvas.parentNode).toBe(initialParent);
    });

    test('does nothing if bodyScroll is null', () => {
      const noScrollManager = { ...mockTableManager, bodyScroll: null };
      const noScrollOverlay = new GanttCanvasOverlay(noScrollManager);

      expect(() => {
        noScrollOverlay.show();
      }).not.toThrow();
    });

    test('applies clip-path based on pinned columns', () => {
      mockTableManager.getPinnedColumnsWidth.mockReturnValue(150);
      const pinnedOverlay = new GanttCanvasOverlay(mockTableManager);
      pinnedOverlay.show();

      expect(pinnedOverlay.canvas.style.clipPath).toBe('inset(0px 0px 0px 150px)');
      pinnedOverlay.hide();
    });

    test('publishes metrics for automation checks', () => {
      expect(window.GanttOverlayMetrics).toBeUndefined();
      const metricsOverlay = new GanttCanvasOverlay(mockTableManager);
      metricsOverlay.barData = [];
      metricsOverlay.show();

      expect(window.GanttOverlayMetrics).toBeDefined();
      expect(window.GanttOverlayMetrics).toMatchObject({
        pinnedWidth: expect.any(Number),
        clipLeft: expect.any(Number),
        viewportLeft: expect.any(Number),
        viewportWidth: expect.any(Number),
        barsDrawn: expect.any(Number),
        barsSkipped: expect.any(Number),
      });
      metricsOverlay.hide();
      mockTableManager.getPinnedColumnsWidth.mockReturnValue(0);
    });
  });

  describe('hide()', () => {
    test('removes canvas from DOM', () => {
      overlay.show();
      expect(mockBodyScroll.contains(overlay.canvas)).toBe(true);

      overlay.hide();

      expect(mockBodyScroll.contains(overlay.canvas)).toBe(false);
    });

    test('sets visible flag to false', () => {
      overlay.show();
      overlay.hide();

      expect(overlay.visible).toBe(false);
    });

    test('hides tooltip', () => {
      overlay.show();
      overlay._ensureTooltip();
      overlay.tooltip.style.display = 'block';

      overlay.hide();

      expect(overlay.tooltip.style.display).toBe('none');
    });

    test('does nothing if already hidden', () => {
      overlay.hide(); // Call when already hidden

      expect(overlay.visible).toBe(false);
    });
  });

  describe('syncWithTable()', () => {
    test('sets canvas dimensions to scroll area dimensions', () => {
      overlay.show();
      overlay.syncWithTable();

      expect(overlay.canvas.width).toBe(mockBodyScroll.scrollWidth);
      expect(overlay.canvas.height).toBe(mockBodyScroll.scrollHeight);
    });

    test('clears canvas before drawing', () => {
      overlay.show();
      overlay.syncWithTable();

      expect(overlay.ctx.clearRect).toHaveBeenCalledWith(
        0,
        0,
        mockBodyScroll.scrollWidth,
        mockBodyScroll.scrollHeight
      );
    });

    test('resets barRects array', () => {
      overlay.barRects = [{ x: 0, y: 0 }];
      overlay.show();
      overlay.syncWithTable();

      expect(overlay.barRects).toEqual([]);
    });

    test('calls getCellBoundingRects from tableManager', () => {
      overlay.show();
      overlay.syncWithTable();

      expect(mockTableManager.getCellBoundingRects).toHaveBeenCalled();
    });

    test('draws debug skeleton grid when debug enabled', () => {
      overlay.debug = true;
      mockTableManager.getCellBoundingRects.mockReturnValue([
        { x: 0, y: 0, width: 100, height: 50, pekerjaanId: '123', columnId: 'col_1' },
      ]);

      overlay.show();
      overlay.syncWithTable();

      expect(overlay.ctx.strokeRect).toHaveBeenCalledWith(0, 0, 100, 50);
    });

    test('logs error when bars exist but no cell rects', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation();
      overlay.barData = [{ pekerjaanId: '123', columnId: 'col_1' }];
      mockTableManager.getCellBoundingRects.mockReturnValue([]);

      overlay.show();
      overlay.syncWithTable();

      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    });
  });

  describe('renderBars()', () => {
    test('stores bar data', () => {
      const barData = [
        { pekerjaanId: '123', columnId: 'col_1', planned: 50, actual: 75 },
      ];

      overlay.renderBars(barData);

      expect(overlay.barData).toEqual(barData);
    });

    test('converts non-array to empty array', () => {
      overlay.renderBars(null);
      expect(overlay.barData).toEqual([]);

      overlay.renderBars(undefined);
      expect(overlay.barData).toEqual([]);

      overlay.renderBars('invalid');
      expect(overlay.barData).toEqual([]);
    });

    test('triggers syncWithTable if visible', () => {
      const syncSpy = vi.spyOn(overlay, 'syncWithTable');
      overlay.show();

      overlay.renderBars([]);

      expect(syncSpy).toHaveBeenCalled();
    });

    test('does not trigger sync if hidden', () => {
      const syncSpy = vi.spyOn(overlay, 'syncWithTable');

      overlay.renderBars([]);

      expect(syncSpy).not.toHaveBeenCalled();
    });
  });

  describe('renderDependencies()', () => {
    test('stores dependency data', () => {
      const deps = [
        {
          fromPekerjaanId: '123',
          fromColumnId: 'col_1',
          toPekerjaanId: '456',
          toColumnId: 'col_2',
        },
      ];

      overlay.renderDependencies(deps);

      expect(overlay.dependencies).toEqual(deps);
    });

    test('converts non-array to empty array', () => {
      overlay.renderDependencies(null);
      expect(overlay.dependencies).toEqual([]);
    });

    test('triggers syncWithTable if visible', () => {
      const syncSpy = vi.spyOn(overlay, 'syncWithTable');
      overlay.show();

      overlay.renderDependencies([]);

      expect(syncSpy).toHaveBeenCalled();
    });
  });

  describe('_drawBars()', () => {
    test('draws bars for matching cell rects', () => {
      const cellRects = [
        {
          x: 100,
          y: 50,
          width: 200,
          height: 40,
          pekerjaanId: '123',
          columnId: 'col_1',
        },
      ];

      overlay.barData = [
        {
          pekerjaanId: '123',
          columnId: 'col_1',
          planned: 50,
          actual: 75,
          variance: 25,
          label: 'Task 1',
          color: '#4dabf7',
        },
      ];

      overlay.show();
      overlay._drawBars(cellRects);

      // Should draw 2 bars (planned + actual)
      expect(overlay.ctx.fillRect).toHaveBeenCalled();
      const fillRectCalls = overlay.ctx.fillRect.mock.calls.length;
      expect(fillRectCalls).toBeGreaterThan(0);
    });

    test('skips bars without matching cell rects', () => {
      const cellRects = [
        { x: 100, y: 50, width: 200, height: 40, pekerjaanId: '123', columnId: 'col_1' },
      ];

      overlay.barData = [
        { pekerjaanId: '456', columnId: 'col_2', planned: 50, actual: 75 },
      ];

      overlay.show();
      overlay._drawBars(cellRects);

      // No matching cells, so no bars drawn
      expect(overlay.ctx.fillRect).not.toHaveBeenCalled();
    });

    test('creates barRects for hit testing', () => {
      const cellRects = [
        { x: 100, y: 50, width: 200, height: 40, pekerjaanId: '123', columnId: 'col_1' },
      ];

      overlay.barData = [
        {
          pekerjaanId: '123',
          columnId: 'col_1',
          planned: 50,
          actual: 75,
          variance: 25,
          label: 'Task 1',
        },
      ];

      overlay.show();
      overlay._drawBars(cellRects);

      expect(overlay.barRects.length).toBeGreaterThan(0);
      expect(overlay.barRects[0]).toHaveProperty('x');
      expect(overlay.barRects[0]).toHaveProperty('y');
      expect(overlay.barRects[0]).toHaveProperty('width');
      expect(overlay.barRects[0]).toHaveProperty('height');
    });

    test('draws stacked bars (planned bottom, actual top)', () => {
      const cellRects = [
        { x: 100, y: 50, width: 200, height: 40, pekerjaanId: '123', columnId: 'col_1' },
      ];

      overlay.barData = [
        { pekerjaanId: '123', columnId: 'col_1', planned: 50, actual: 75 },
      ];

      overlay.show();
      overlay._drawBars(cellRects);

      const fillRectCalls = overlay.ctx.fillRect.mock.calls;
      expect(fillRectCalls.length).toBe(2); // Planned + Actual

      // First call (planned) should be in bottom half
      const [, plannedY, , plannedHeight] = fillRectCalls[0];
      // Second call (actual) should be in top half
      const [, actualY] = fillRectCalls[1];

      expect(actualY).toBeLessThan(plannedY); // Actual is above planned
    });

    test('handles zero values correctly', () => {
      const cellRects = [
        { x: 100, y: 50, width: 200, height: 40, pekerjaanId: '123', columnId: 'col_1' },
      ];

      overlay.barData = [
        { pekerjaanId: '123', columnId: 'col_1', planned: 0, actual: 50 },
      ];

      overlay.show();
      overlay._drawBars(cellRects);

      // Should still draw (only actual bar)
      expect(overlay.ctx.fillRect).toHaveBeenCalled();
    });

    test('does nothing with empty cell rects', () => {
      overlay.barData = [
        { pekerjaanId: '123', columnId: 'col_1', planned: 50, actual: 75 },
      ];

      overlay._drawBars([]);

      expect(overlay.ctx.fillRect).not.toHaveBeenCalled();
    });

    test('does nothing with empty bar data', () => {
      const cellRects = [
        { x: 100, y: 50, width: 200, height: 40, pekerjaanId: '123', columnId: 'col_1' },
      ];

      overlay.barData = [];
      overlay._drawBars(cellRects);

      expect(overlay.ctx.fillRect).not.toHaveBeenCalled();
    });

    test('skips bars that live entirely under pinned columns', () => {
      mockTableManager.getPinnedColumnsWidth.mockReturnValue(120);
      const cellRects = [
        { x: 10, y: 20, width: 40, height: 30, pekerjaanId: '123', columnId: 'col_1' },
      ];

      overlay.barData = [
        { pekerjaanId: '123', columnId: 'col_1', planned: 50, actual: 50 },
      ];

      overlay.show();
      overlay.ctx.fillRect.mockClear();
      overlay._drawBars(cellRects);

      expect(overlay.ctx.fillRect).not.toHaveBeenCalled();
      expect(overlay.lastDrawMetrics.barsSkipped).toBeGreaterThan(0);

      mockTableManager.getPinnedColumnsWidth.mockReturnValue(0);
    });

    test('skips bars that fall outside the viewport bounds', () => {
      mockBodyScroll.scrollLeft = 1000;
      const cellRects = [
        { x: 2100, y: 20, width: 40, height: 30, pekerjaanId: '123', columnId: 'col_1' },
      ];

      overlay.barData = [
        { pekerjaanId: '123', columnId: 'col_1', planned: 50, actual: 50 },
      ];

      overlay.show();
      overlay.ctx.fillRect.mockClear();
      overlay._drawBars(cellRects);

      expect(overlay.ctx.fillRect).not.toHaveBeenCalled();
      expect(overlay.lastDrawMetrics.barsSkipped).toBeGreaterThan(0);

      mockBodyScroll.scrollLeft = 0;
    });

    test('matches bars using string IDs', () => {
      const cellRects = [
        { x: 100, y: 50, width: 200, height: 40, pekerjaanId: 123, columnId: 'col_1' },
      ];

      overlay.barData = [
        { pekerjaanId: '123', columnId: 'col_1', planned: 50, actual: 75 },
      ];

      overlay.show();
      overlay._drawBars(cellRects);

      // Should match despite type difference (123 vs '123')
      expect(overlay.ctx.fillRect).toHaveBeenCalled();
    });
  });

  describe('_drawDependencies()', () => {
    test('draws dependency arrows between tasks', () => {
      const cellRects = [
        { x: 100, y: 50, width: 100, height: 40, pekerjaanId: '123', columnId: 'col_1' },
        { x: 300, y: 100, width: 100, height: 40, pekerjaanId: '456', columnId: 'col_2' },
      ];

      overlay.dependencies = [
        {
          fromPekerjaanId: '123',
          fromColumnId: 'col_1',
          toPekerjaanId: '456',
          toColumnId: 'col_2',
          color: '#94a3b8',
        },
      ];

      overlay._drawDependencies(cellRects);

      expect(overlay.ctx.beginPath).toHaveBeenCalled();
      expect(overlay.ctx.moveTo).toHaveBeenCalled();
      expect(overlay.ctx.lineTo).toHaveBeenCalled();
      expect(overlay.ctx.stroke).toHaveBeenCalled();
    });

    test('draws arrow head at destination', () => {
      const cellRects = [
        { x: 100, y: 50, width: 100, height: 40, pekerjaanId: '123', columnId: 'col_1' },
        { x: 300, y: 100, width: 100, height: 40, pekerjaanId: '456', columnId: 'col_2' },
      ];

      overlay.dependencies = [
        {
          fromPekerjaanId: '123',
          fromColumnId: 'col_1',
          toPekerjaanId: '456',
          toColumnId: 'col_2',
        },
      ];

      overlay._drawDependencies(cellRects);

      expect(overlay.ctx.fill).toHaveBeenCalled(); // Arrow head
    });

    test('skips dependencies with missing source', () => {
      const cellRects = [
        { x: 300, y: 100, width: 100, height: 40, pekerjaanId: '456', columnId: 'col_2' },
      ];

      overlay.dependencies = [
        {
          fromPekerjaanId: '123',
          fromColumnId: 'col_1',
          toPekerjaanId: '456',
          toColumnId: 'col_2',
        },
      ];

      overlay._drawDependencies(cellRects);

      // Should not draw anything
      expect(overlay.ctx.stroke).not.toHaveBeenCalled();
    });

    test('skips dependencies with missing destination', () => {
      const cellRects = [
        { x: 100, y: 50, width: 100, height: 40, pekerjaanId: '123', columnId: 'col_1' },
      ];

      overlay.dependencies = [
        {
          fromPekerjaanId: '123',
          fromColumnId: 'col_1',
          toPekerjaanId: '456',
          toColumnId: 'col_2',
        },
      ];

      overlay._drawDependencies(cellRects);

      expect(overlay.ctx.stroke).not.toHaveBeenCalled();
    });

    test('uses default color if not specified', () => {
      const cellRects = [
        { x: 100, y: 50, width: 100, height: 40, pekerjaanId: '123', columnId: 'col_1' },
        { x: 300, y: 100, width: 100, height: 40, pekerjaanId: '456', columnId: 'col_2' },
      ];

      overlay.dependencies = [
        {
          fromPekerjaanId: '123',
          fromColumnId: 'col_1',
          toPekerjaanId: '456',
          toColumnId: 'col_2',
        },
      ];

      overlay._drawDependencies(cellRects);

      expect(overlay.ctx.strokeStyle).toBe('#94a3b8');
    });
  });

  describe('Color Resolution', () => {
    test('_getPlannedColor returns CSS variable if available', () => {
      // Mock getComputedStyle to return CSS variable
      const originalGetComputedStyle = window.getComputedStyle;
      window.getComputedStyle = vi.fn(() => ({
        getPropertyValue: (name) => {
          if (name === '--gantt-bar-fill') return '#3b82f6';
          return '';
        },
      }));

      const color = overlay._getPlannedColor();

      expect(color).toBe('#3b82f6');
      window.getComputedStyle = originalGetComputedStyle;
    });

    test('_getPlannedColor returns fallback if CSS var not available', () => {
      const color = overlay._getPlannedColor();

      expect(color).toBeTruthy();
      expect(typeof color).toBe('string');
    });

    test('_resolveActualColor returns CSS variable if available', () => {
      const originalGetComputedStyle = window.getComputedStyle;
      window.getComputedStyle = vi.fn(() => ({
        getPropertyValue: (name) => {
          if (name === '--gantt-actual-fill') return '#f59e0b';
          return '';
        },
      }));

      const color = overlay._resolveActualColor(0);

      expect(color).toBe('#f59e0b');
      window.getComputedStyle = originalGetComputedStyle;
    });

    test('_resolveVarianceColor returns red for negative variance', () => {
      const color = overlay._resolveVarianceColor(-5);

      expect(color).toBe('#ef4444'); // Red
    });

    test('_resolveVarianceColor returns green for positive variance', () => {
      const color = overlay._resolveVarianceColor(5);

      expect(color).toBe('#22c55e'); // Green
    });

    test('_resolveVarianceColor returns blue for zero variance', () => {
      const color = overlay._resolveVarianceColor(0);

      expect(color).toBe('#3b82f6'); // Blue
    });
  });

  describe('Tooltip', () => {
    test('_hitTest finds bar at coordinates', () => {
      overlay.barRects = [
        { x: 100, y: 50, width: 200, height: 40, pekerjaanId: '123' },
      ];

      const hit = overlay._hitTest(150, 60);

      expect(hit).toBeTruthy();
      expect(hit.pekerjaanId).toBe('123');
    });

    test('_hitTest returns undefined when no hit', () => {
      overlay.barRects = [
        { x: 100, y: 50, width: 200, height: 40 },
      ];

      const hit = overlay._hitTest(500, 500);

      expect(hit).toBeUndefined();
    });

    test('_ensureTooltip creates tooltip element', () => {
      const tooltip = overlay._ensureTooltip();

      expect(tooltip).toBeTruthy();
      expect(tooltip.className).toBe('gantt-overlay-tooltip');
      expect(document.body.contains(tooltip)).toBe(true);
    });

    test('_ensureTooltip returns existing tooltip', () => {
      const tooltip1 = overlay._ensureTooltip();
      const tooltip2 = overlay._ensureTooltip();

      expect(tooltip1).toBe(tooltip2);
    });

    test('_showTooltip displays tooltip with bar info', () => {
      const hit = {
        label: 'Task 1',
        columnId: 'col_1',
        planned: 50,
        value: 75,
        variance: 25,
      };

      overlay._showTooltip(100, 100, hit);

      expect(overlay.tooltip).toBeTruthy();
      expect(overlay.tooltip.style.display).toBe('block');
      expect(overlay.tooltip.innerHTML).toContain('Task 1');
      expect(overlay.tooltip.innerHTML).toContain('50%');
      expect(overlay.tooltip.innerHTML).toContain('75%');
    });

    test('_hideTooltip hides tooltip', () => {
      overlay._ensureTooltip();
      overlay.tooltip.style.display = 'block';

      overlay._hideTooltip();

      expect(overlay.tooltip.style.display).toBe('none');
    });
  });

  describe('_log()', () => {
    test('logs when debug enabled', () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation();
      overlay.debug = true;

      overlay._log('test-event', { foo: 'bar' });

      expect(consoleSpy).toHaveBeenCalledWith('[GanttOverlay] test-event', { foo: 'bar' });
      consoleSpy.mockRestore();
    });

    test('does not log when debug disabled', () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation();
      overlay.debug = false;

      overlay._log('test-event', {});

      expect(consoleSpy).not.toHaveBeenCalled();
      consoleSpy.mockRestore();
    });
  });
});
