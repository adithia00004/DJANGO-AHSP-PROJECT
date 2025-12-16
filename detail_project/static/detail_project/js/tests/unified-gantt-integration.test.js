/**
 * Integration Tests for Unified Gantt Overlay System
 *
 * Tests the complete workflow: data flow, mode switching,
 * overlay rendering, and state synchronization.
 *
 * To run: npm run test:frontend
 */

import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { UnifiedTableManager } from '../src/modules/unified/UnifiedTableManager.js';
import { GanttCanvasOverlay } from '../src/modules/gantt/GanttCanvasOverlay.js';

describe('Unified Gantt Overlay Integration', () => {
  let manager;
  let mockState;
  let mockStateManager;
  let container;
  let bodyScroll;

  beforeEach(() => {
    // Create DOM containers
    container = document.createElement('div');
    bodyScroll = document.createElement('div');
    bodyScroll.style.width = '1000px';
    bodyScroll.style.height = '800px';
    // Use Object.defineProperty to make scrollWidth/scrollHeight writable
    Object.defineProperties(bodyScroll, {
      scrollWidth: { value: 1200, writable: true, configurable: true },
      scrollHeight: { value: 1000, writable: true, configurable: true },
    });
    document.body.appendChild(container);
    document.body.appendChild(bodyScroll);

    // Mock canvas for GanttCanvasOverlay
    const mockCanvasCtx = {
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

    const originalCreateElement = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tag) => {
      if (tag === 'canvas') {
        const canvas = originalCreateElement('canvas');
        canvas.getContext = vi.fn(() => mockCanvasCtx);
        canvas.getBoundingClientRect = vi.fn(() => ({
          left: 0,
          top: 0,
          width: 1200,
          height: 1000,
        }));
        return canvas;
      }
      return originalCreateElement(tag);
    });

    // Mock StateManager with realistic data
    mockStateManager = {
      currentMode: 'planned',
      states: {
        planned: {
          assignmentMap: new Map([
            ['123-col_1', 30],
            ['123-col_2', 50],
            ['456-col_1', 40],
            ['456-col_2', 60],
          ]),
          modifiedCells: new Map(),
        },
        actual: {
          assignmentMap: new Map([
            ['123-col_1', 45],
            ['123-col_2', 65],
            ['456-col_1', 35],
            ['456-col_2', 55],
          ]),
          modifiedCells: new Map(),
        },
      },
      getAllCellsForMode: vi.fn((mode) => {
        const merged = new Map();
        const state = mockStateManager.states[mode];
        if (state) {
          state.assignmentMap.forEach((v, k) => merged.set(k, v));
          state.modifiedCells.forEach((v, k) => merged.set(k, v));
        }
        return merged;
      }),
      switchMode: vi.fn((mode) => {
        mockStateManager.currentMode = mode;
      }),
      addEventListener: vi.fn(),
    };

    mockState = {
      debugUnifiedTable: false,
      progressMode: 'planned',
      stateManager: mockStateManager,
      stateManagerInstance: mockStateManager,
      flatPekerjaan: [
        { id: 123, nama: 'Foundation Work', pekerjaan_id: 123 },
        { id: 456, nama: 'Structural Work', pekerjaan_id: 456 },
      ],
      timeColumns: [
        {
          id: 'col_1',
          fieldId: 'col_1',
          generationMode: 'weekly',
          rangeLabel: 'Week 1',
        },
        {
          id: 'col_2',
          fieldId: 'col_2',
          generationMode: 'weekly',
          rangeLabel: 'Week 2',
        },
      ],
    };

    manager = new UnifiedTableManager(mockState, {});

    // Mock TanStackGrid with realistic implementation
    manager.tanstackGrid = {
      mount: vi.fn(),
      updateData: vi.fn(),
      setCellRenderer: vi.fn(),
      bodyScroll,
      currentRows: [
        {
          pekerjaanId: 123,
          id: 123,
          name: 'Foundation Work',
          raw: { id: 123, nama: 'Foundation Work' },
          subRows: [],
        },
        {
          pekerjaanId: 456,
          id: 456,
          name: 'Structural Work',
          raw: { id: 456, nama: 'Structural Work' },
          subRows: [],
        },
      ],
      currentColumns: [
        {
          id: 'col_1',
          fieldId: 'col_1',
          meta: {
            timeColumn: true,
            columnMeta: { id: 'col_1', fieldId: 'col_1' },
          },
        },
        {
          id: 'col_2',
          fieldId: 'col_2',
          meta: {
            timeColumn: true,
            columnMeta: { id: 'col_2', fieldId: 'col_2' },
          },
        },
      ],
      getCellBoundingRects: vi.fn(() => [
        {
          x: 200,
          y: 50,
          width: 150,
          height: 40,
          pekerjaanId: '123',
          columnId: 'col_1',
        },
        {
          x: 350,
          y: 50,
          width: 150,
          height: 40,
          pekerjaanId: '123',
          columnId: 'col_2',
        },
        {
          x: 200,
          y: 100,
          width: 150,
          height: 40,
          pekerjaanId: '456',
          columnId: 'col_1',
        },
        {
          x: 350,
          y: 100,
          width: 150,
          height: 40,
          pekerjaanId: '456',
          columnId: 'col_2',
        },
      ]),
    };
  });

  afterEach(() => {
    if (manager && manager.overlays && manager.overlays.gantt) {
      manager.overlays.gantt.hide();
    }
    if (container && document.body.contains(container)) {
      document.body.removeChild(container);
    }
    if (bodyScroll && document.body.contains(bodyScroll)) {
      document.body.removeChild(bodyScroll);
    }
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe('Complete Data Flow', () => {
    test('builds bar data from state and payload', () => {
      const payload = {
        tree: mockState.flatPekerjaan.map((p) => ({
          pekerjaanId: p.id,
          name: p.nama,
          raw: p,
          subRows: [],
        })),
        timeColumns: mockState.timeColumns.map((col) => ({
          id: col.id,
          fieldId: col.fieldId,
          meta: {
            timeColumn: true,
            columnMeta: col,
          },
        })),
        dependencies: [],
      };

      const barData = manager._buildBarData(payload);

      // Should have 4 bars (2 tasks × 2 columns)
      expect(barData.length).toBe(4);

      // Verify data structure
      barData.forEach((bar) => {
        expect(bar).toHaveProperty('pekerjaanId');
        expect(bar).toHaveProperty('columnId');
        expect(bar).toHaveProperty('planned');
        expect(bar).toHaveProperty('actual');
        expect(bar).toHaveProperty('variance');
        expect(typeof bar.pekerjaanId).toBe('string');
        expect(typeof bar.columnId).toBe('string');
      });
    });

    test('updateData triggers bar data rebuild and overlay refresh', () => {
      manager.currentMode = 'gantt';
      manager.overlays.gantt = new GanttCanvasOverlay(manager.tanstackGrid);
      const renderBarsSpy = vi.spyOn(manager.overlays.gantt, 'renderBars');

      const payload = {
        tree: mockState.flatPekerjaan.map((p) => ({
          pekerjaanId: p.id,
          name: p.nama,
          subRows: [],
        })),
        timeColumns: mockState.timeColumns.map((col) => ({
          id: col.id,
          fieldId: col.fieldId,
          meta: { timeColumn: true, columnMeta: col },
        })),
        dependencies: [],
      };

      manager.updateData(payload);

      expect(manager.tanstackGrid.updateData).toHaveBeenCalledWith(payload);
      expect(renderBarsSpy).toHaveBeenCalled();
      expect(manager.overlays.gantt.barData.length).toBeGreaterThan(0);
    });

    test('bar data matches cell rectangles', () => {
      const payload = {
        tree: manager.tanstackGrid.currentRows,
        timeColumns: manager.tanstackGrid.currentColumns,
      };

      const barData = manager._buildBarData(payload);
      const cellRects = manager.tanstackGrid.getCellBoundingRects();

      // Each bar should have a matching cell rect
      barData.forEach((bar) => {
        const matchingRect = cellRects.find(
          (rect) =>
            String(rect.pekerjaanId) === String(bar.pekerjaanId) &&
            String(rect.columnId) === String(bar.columnId)
        );
        expect(matchingRect).toBeTruthy();
      });
    });
  });

  describe('Mode Switching Integration', () => {
    test('complete grid -> gantt -> grid cycle', () => {
      // Start in grid mode
      expect(manager.currentMode).toBe('grid');

      // Switch to gantt
      manager.switchMode('gantt');
      expect(manager.currentMode).toBe('gantt');
      expect(manager.overlays.gantt).toBeTruthy();
      expect(manager.tanstackGrid.setCellRenderer).toHaveBeenCalledWith('gantt');

      // Switch back to grid
      manager.switchMode('grid');
      expect(manager.currentMode).toBe('grid');
      expect(manager.tanstackGrid.setCellRenderer).toHaveBeenCalledWith('input');
    });

    test('gantt overlay shows and hides correctly', () => {
      manager.switchMode('gantt');
      const overlay = manager.overlays.gantt;

      expect(overlay.visible).toBe(true);
      expect(bodyScroll.contains(overlay.canvas)).toBe(true);

      manager.switchMode('grid');

      expect(overlay.visible).toBe(false);
      expect(bodyScroll.contains(overlay.canvas)).toBe(false);
    });

    test('switching modes preserves data', () => {
      const payload = {
        tree: manager.tanstackGrid.currentRows,
        timeColumns: manager.tanstackGrid.currentColumns,
      };

      manager.updateData(payload);
      const initialBarData = manager._buildBarData(payload);

      // Switch to gantt
      manager.switchMode('gantt');
      const ganttBarData = manager.overlays.gantt.barData;

      // Switch to kurva
      manager.switchMode('kurva');

      // Switch back to gantt
      manager.switchMode('gantt');

      // Data should be preserved
      expect(manager.overlays.gantt.barData).toEqual(ganttBarData);
    });

    test('overlay syncs with table on mode switch', () => {
      manager.switchMode('gantt');
      const syncSpy = vi.spyOn(manager.overlays.gantt, 'syncWithTable');

      const payload = {
        tree: manager.tanstackGrid.currentRows,
        timeColumns: manager.tanstackGrid.currentColumns,
      };

      manager.updateData(payload);

      expect(syncSpy).toHaveBeenCalled();
    });
  });

  describe('State Manager Integration', () => {
    test('bar data reflects state manager changes', () => {
      const payload = {
        tree: manager.tanstackGrid.currentRows,
        timeColumns: manager.tanstackGrid.currentColumns,
      };

      const initialBarData = manager._buildBarData(payload);

      // Modify state
      mockStateManager.states.planned.modifiedCells.set('123-col_1', 80);

      const updatedBarData = manager._buildBarData(payload);

      // Should reflect the change
      const changedBar = updatedBarData.find(
        (b) => b.pekerjaanId === '123' && b.columnId === 'col_1'
      );
      expect(changedBar.planned).toBe(80);
    });

    test('switches between planned and actual modes', () => {
      mockStateManager.currentMode = 'planned';
      const payload = {
        tree: manager.tanstackGrid.currentRows,
        timeColumns: manager.tanstackGrid.currentColumns,
      };

      const plannedBarData = manager._buildBarData(payload);

      mockStateManager.currentMode = 'actual';
      manager.state.progressMode = 'actual';

      const actualBarData = manager._buildBarData(payload);

      // Planned and actual should have different values
      expect(plannedBarData[0].planned).not.toBe(actualBarData[0].actual);
    });

    test('getAllCellsForMode is called correctly', () => {
      const payload = {
        tree: manager.tanstackGrid.currentRows,
        timeColumns: manager.tanstackGrid.currentColumns,
      };

      manager._buildBarData(payload);

      expect(mockStateManager.getAllCellsForMode).toHaveBeenCalledWith('planned');
      expect(mockStateManager.getAllCellsForMode).toHaveBeenCalledWith('actual');
    });
  });

  describe('Canvas Rendering Integration', () => {
    test('bars render on canvas after data update', () => {
      manager.switchMode('gantt');
      const overlay = manager.overlays.gantt;

      const payload = {
        tree: manager.tanstackGrid.currentRows,
        timeColumns: manager.tanstackGrid.currentColumns,
        dependencies: [],
      };

      manager.updateData(payload);

      // Canvas should be sized
      expect(overlay.canvas.width).toBeGreaterThan(0);
      expect(overlay.canvas.height).toBeGreaterThan(0);

      // Bars should be stored
      expect(overlay.barData.length).toBeGreaterThan(0);

      // Bar rects should be created for hit testing
      expect(overlay.barRects.length).toBeGreaterThan(0);
    });

    test('dependencies render correctly', () => {
      manager.switchMode('gantt');
      const overlay = manager.overlays.gantt;

      const payload = {
        tree: manager.tanstackGrid.currentRows,
        timeColumns: manager.tanstackGrid.currentColumns,
        dependencies: [
          {
            fromPekerjaanId: '123',
            fromColumnId: 'col_1',
            toPekerjaanId: '456',
            toColumnId: 'col_2',
            color: '#94a3b8',
          },
        ],
      };

      manager.updateData(payload);

      expect(overlay.dependencies.length).toBe(1);
    });

    test('canvas clears and redraws on data update', () => {
      manager.switchMode('gantt');
      const overlay = manager.overlays.gantt;
      const clearSpy = vi.spyOn(overlay.ctx, 'clearRect');

      const payload = {
        tree: manager.tanstackGrid.currentRows,
        timeColumns: manager.tanstackGrid.currentColumns,
      };

      manager.updateData(payload);

      expect(clearSpy).toHaveBeenCalled();
    });
  });

  describe('Fallback Data Sources', () => {
    test('uses tanstackGrid rows when payload is empty', () => {
      const emptyPayload = { tree: [], timeColumns: [] };
      const barData = manager._buildBarData(emptyPayload);

      // Should still generate bars from tanstackGrid data
      expect(barData.length).toBeGreaterThan(0);
    });

    test('uses state.flatPekerjaan as last resort', () => {
      // Clear tanstackGrid data
      manager.tanstackGrid.currentRows = [];
      manager.tanstackGrid.currentColumns = [];

      const emptyPayload = { tree: [], timeColumns: [] };
      const barData = manager._buildBarData(emptyPayload);

      // Should fall back to flatPekerjaan
      expect(barData.length).toBeGreaterThan(0);
    });

    test('uses state.timeColumns when no columns provided', () => {
      manager.tanstackGrid.currentColumns = [];

      const payload = {
        tree: manager.tanstackGrid.currentRows,
        timeColumns: [],
      };

      const barData = manager._buildBarData(payload);

      expect(barData.length).toBeGreaterThan(0);
    });
  });

  describe('Performance and Edge Cases', () => {
    test('handles large dataset efficiently', () => {
      // Create 100 tasks with 52 columns each (1 year of weeks)
      const largeFlatPekerjaan = Array.from({ length: 100 }, (_, i) => ({
        id: i + 1000,
        nama: `Task ${i}`,
      }));

      const largeTimeColumns = Array.from({ length: 52 }, (_, i) => ({
        id: `week_${i}`,
        fieldId: `week_${i}`,
        generationMode: 'weekly',
      }));

      // Populate state with data
      largeFlatPekerjaan.forEach((task) => {
        largeTimeColumns.forEach((col) => {
          const key = `${task.id}-${col.id}`;
          mockStateManager.states.planned.assignmentMap.set(key, Math.random() * 100);
          mockStateManager.states.actual.assignmentMap.set(key, Math.random() * 100);
        });
      });

      const payload = {
        tree: largeFlatPekerjaan.map((p) => ({
          pekerjaanId: p.id,
          name: p.nama,
          subRows: [],
        })),
        timeColumns: largeTimeColumns.map((col) => ({
          id: col.id,
          fieldId: col.fieldId,
          meta: { timeColumn: true, columnMeta: col },
        })),
      };

      const startTime = performance.now();
      const barData = manager._buildBarData(payload);
      const endTime = performance.now();

      expect(barData.length).toBeGreaterThan(0);
      expect(endTime - startTime).toBeLessThan(500); // Should complete in < 500ms
    });

    test('handles empty state gracefully', () => {
      mockStateManager.states.planned.assignmentMap.clear();
      mockStateManager.states.actual.assignmentMap.clear();

      const payload = {
        tree: manager.tanstackGrid.currentRows,
        timeColumns: manager.tanstackGrid.currentColumns,
      };

      const barData = manager._buildBarData(payload);

      expect(barData.length).toBe(0);
    });

    test('handles null/undefined values gracefully', () => {
      const payload = {
        tree: [
          { pekerjaanId: null, name: 'Invalid', subRows: [] },
          { pekerjaanId: 123, name: 'Valid', subRows: [] },
        ],
        timeColumns: [
          { id: null, fieldId: 'invalid' },
          {
            id: 'col_1',
            fieldId: 'col_1',
            meta: { timeColumn: true, columnMeta: { id: 'col_1' } },
          },
        ],
      };

      expect(() => {
        manager._buildBarData(payload);
      }).not.toThrow();
    });

    test('handles deeply nested tree structure', () => {
      const deepTree = [
        {
          pekerjaanId: 1,
          name: 'Level 1',
          subRows: [
            {
              pekerjaanId: 2,
              name: 'Level 2',
              subRows: [
                {
                  pekerjaanId: 3,
                  name: 'Level 3',
                  subRows: [
                    {
                      pekerjaanId: 4,
                      name: 'Level 4',
                      subRows: [],
                    },
                  ],
                },
              ],
            },
          ],
        },
      ];

      mockStateManager.states.planned.assignmentMap.set('1-col_1', 25);
      mockStateManager.states.planned.assignmentMap.set('2-col_1', 25);
      mockStateManager.states.planned.assignmentMap.set('3-col_1', 25);
      mockStateManager.states.planned.assignmentMap.set('4-col_1', 25);

      const payload = {
        tree: deepTree,
        timeColumns: manager.tanstackGrid.currentColumns,
      };

      const barData = manager._buildBarData(payload);

      expect(barData.length).toBe(4); // All 4 levels flattened
    });
  });

  describe('Type Safety', () => {
    test('converts numeric IDs to strings consistently', () => {
      const payload = {
        tree: [
          { pekerjaanId: 123, name: 'Task 1', subRows: [] }, // Number
          { pekerjaanId: '456', name: 'Task 2', subRows: [] }, // String
        ],
        timeColumns: [
          {
            id: 'col_1',
            fieldId: 'col_1',
            meta: { timeColumn: true, columnMeta: { id: 'col_1' } },
          },
        ],
      };

      mockStateManager.states.planned.assignmentMap.set('123-col_1', 50);
      mockStateManager.states.planned.assignmentMap.set('456-col_1', 60);

      const barData = manager._buildBarData(payload);

      // All IDs should be strings
      barData.forEach((bar) => {
        expect(typeof bar.pekerjaanId).toBe('string');
        expect(typeof bar.columnId).toBe('string');
      });
    });

    test('matches bars to cells despite type differences', () => {
      const cellRects = [
        { x: 100, y: 50, width: 200, height: 40, pekerjaanId: 123, columnId: 'col_1' }, // Number
      ];

      const barData = [
        { pekerjaanId: '123', columnId: 'col_1', planned: 50, actual: 75 }, // String
      ];

      manager.switchMode('gantt');
      manager.overlays.gantt.barData = barData;
      manager.overlays.gantt._drawBars(cellRects);

      // Should match and draw despite type difference
      expect(manager.overlays.gantt.barRects.length).toBeGreaterThan(0);
    });
  });
});
