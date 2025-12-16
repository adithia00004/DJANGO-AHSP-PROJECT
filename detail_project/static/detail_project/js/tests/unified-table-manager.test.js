/**
 * Unit Tests for UnifiedTableManager
 *
 * Tests the core data building and overlay management logic
 * for the Unified Gantt Overlay system.
 *
 * To run: npm run test:frontend
 */

import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { UnifiedTableManager } from '../src/modules/unified/UnifiedTableManager.js';

describe('UnifiedTableManager', () => {
  let manager;
  let mockState;
  let mockOptions;
  let mockTanStackGrid;

  beforeEach(() => {
    // Mock StateManager
    const mockStateManager = {
      currentMode: 'planned',
      states: {
        planned: {
          assignmentMap: new Map(),
          modifiedCells: new Map(),
        },
        actual: {
          assignmentMap: new Map(),
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
    };

    mockState = {
      debugUnifiedTable: false,
      progressMode: 'planned',
      stateManager: mockStateManager,
      stateManagerInstance: mockStateManager,
      flatPekerjaan: [],
      timeColumns: [],
    };

    mockOptions = {
      debugUnifiedTable: false,
    };

    // Mock TanStackGridManager
    mockTanStackGrid = {
      mount: vi.fn(),
      updateData: vi.fn(),
      setCellRenderer: vi.fn(),
      currentRows: [],
      currentColumns: [],
    };

    manager = new UnifiedTableManager(mockState, mockOptions);
    manager.tanstackGrid = mockTanStackGrid;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Constructor and Initialization', () => {
    test('initializes with default state', () => {
      expect(manager.state).toBe(mockState);
      expect(manager.options).toBe(mockOptions);
      expect(manager.currentMode).toBe('grid');
      expect(manager.overlays.gantt).toBeNull();
      expect(manager.overlays.kurva).toBeNull();
    });

    test('initializes with debug mode from state', () => {
      const debugState = { ...mockState, debugUnifiedTable: true };
      const debugManager = new UnifiedTableManager(debugState, mockOptions);
      expect(debugManager.debug).toBe(true);
    });

    test('initializes with debug mode from options', () => {
      const debugOptions = { debugUnifiedTable: true };
      const debugManager = new UnifiedTableManager(mockState, debugOptions);
      expect(debugManager.debug).toBe(true);
    });
  });

  describe('mount()', () => {
    test('creates TanStackGridManager and mounts to container', () => {
      const container = document.createElement('div');
      const domTargets = {};

      manager.tanstackGrid = null; // Reset
      manager.mount(container, domTargets);

      expect(manager.tanstackGrid).toBeTruthy();
    });

    test('sets initial cell renderer to input mode', () => {
      const container = document.createElement('div');
      manager.mount(container, {});

      expect(mockTanStackGrid.setCellRenderer).toHaveBeenCalledWith('input');
    });
  });

  describe('updateData()', () => {
    test('forwards data to tanstackGrid', () => {
      const payload = {
        tree: [{ pekerjaanId: 123, name: 'Task 1' }],
        timeColumns: [{ id: 'col_1', meta: { timeColumn: true } }],
        dependencies: [],
      };

      manager.updateData(payload);

      expect(mockTanStackGrid.updateData).toHaveBeenCalledWith(payload);
    });

    test('refreshes gantt overlay when in gantt mode', () => {
      manager.currentMode = 'gantt';
      manager.overlays.gantt = {
        renderBars: vi.fn(),
        renderDependencies: vi.fn(),
      };

      const payload = {
        tree: [{ pekerjaanId: 123, name: 'Task 1' }],
        timeColumns: [{ id: 'col_1', meta: { timeColumn: true } }],
        dependencies: [],
      };

      manager.updateData(payload);

      expect(manager.overlays.gantt.renderBars).toHaveBeenCalled();
      expect(manager.overlays.gantt.renderDependencies).toHaveBeenCalledWith([]);
    });

    test('does nothing if tanstackGrid is null', () => {
      manager.tanstackGrid = null;

      expect(() => {
        manager.updateData({ tree: [], timeColumns: [] });
      }).not.toThrow();
    });
  });

  describe('switchMode()', () => {
    test('switches from grid to gantt mode', () => {
      expect(manager.currentMode).toBe('grid');

      manager.switchMode('gantt');

      expect(manager.currentMode).toBe('gantt');
      expect(mockTanStackGrid.setCellRenderer).toHaveBeenCalledWith('gantt');
    });

    test('switches from gantt to grid mode', () => {
      manager.currentMode = 'gantt';
      manager.overlays.gantt = {
        hide: vi.fn(),
        show: vi.fn(),
      };

      manager.switchMode('grid');

      expect(manager.currentMode).toBe('grid');
      expect(manager.overlays.gantt.hide).toHaveBeenCalled();
      expect(mockTanStackGrid.setCellRenderer).toHaveBeenCalledWith('input');
    });

    test('ignores switch to same mode', () => {
      manager.switchMode('grid');

      expect(mockTanStackGrid.setCellRenderer).not.toHaveBeenCalled();
    });

    test('creates gantt overlay on first switch to gantt', () => {
      expect(manager.overlays.gantt).toBeNull();

      manager.switchMode('gantt');

      expect(manager.overlays.gantt).toBeTruthy();
    });

    test('shows gantt overlay when switching to gantt mode', () => {
      manager.overlays.gantt = {
        show: vi.fn(),
        hide: vi.fn(),
      };

      manager.switchMode('gantt');

      expect(manager.overlays.gantt.show).toHaveBeenCalled();
    });

    test('switches to kurva mode with readonly renderer', () => {
      manager.switchMode('kurva');

      expect(manager.currentMode).toBe('kurva');
      expect(mockTanStackGrid.setCellRenderer).toHaveBeenCalledWith('readonly');
    });
  });

  describe('_buildBarData()', () => {
    beforeEach(() => {
      // Setup state with cell data
      mockState.stateManager.states.planned.assignmentMap.set('123-col_1', 50);
      mockState.stateManager.states.actual.assignmentMap.set('123-col_1', 75);
    });

    test('builds bar data from payload', () => {
      const payload = {
        tree: [
          {
            pekerjaanId: 123,
            name: 'Task 1',
            subRows: [],
          },
        ],
        timeColumns: [
          {
            id: 'col_1',
            fieldId: 'col_1',
            meta: {
              timeColumn: true,
              columnMeta: { id: 'col_1' },
            },
          },
        ],
      };

      const barData = manager._buildBarData(payload);

      expect(barData.length).toBeGreaterThan(0);
      expect(barData[0]).toHaveProperty('pekerjaanId');
      expect(barData[0]).toHaveProperty('columnId');
      expect(barData[0]).toHaveProperty('planned');
      expect(barData[0]).toHaveProperty('actual');
      expect(barData[0]).toHaveProperty('variance');
    });

    test('fallbacks to tanstackGrid rows when payload tree is empty', () => {
      mockTanStackGrid.currentRows = [
        { pekerjaanId: 456, name: 'Task 2', subRows: [] },
      ];
      mockTanStackGrid.currentColumns = [
        {
          id: 'col_2',
          fieldId: 'col_2',
          meta: { timeColumn: true, columnMeta: { id: 'col_2' } },
        },
      ];
      mockState.stateManager.states.planned.assignmentMap.set('456-col_2', 60);

      const payload = { tree: [], timeColumns: [] };
      const barData = manager._buildBarData(payload);

      // Should use tanstackGrid data
      expect(barData.length).toBeGreaterThan(0);
      expect(barData[0].pekerjaanId).toBe('456');
    });

    test('fallbacks to state.flatPekerjaan when grid is empty', () => {
      mockState.flatPekerjaan = [
        { id: 789, nama: 'Task 3' },
      ];
      mockState.timeColumns = [
        { id: 'col_3', fieldId: 'col_3', generationMode: 'weekly' },
      ];
      mockState.stateManager.states.planned.assignmentMap.set('789-col_3', 40);

      const payload = { tree: [], timeColumns: [] };
      const barData = manager._buildBarData(payload);

      expect(barData.length).toBeGreaterThan(0);
      expect(barData[0].pekerjaanId).toBe('789');
    });

    test('converts all IDs to strings for type safety', () => {
      const payload = {
        tree: [{ pekerjaanId: 123, name: 'Task 1', subRows: [] }],
        timeColumns: [
          {
            id: 'col_1',
            fieldId: 'col_1',
            meta: { timeColumn: true, columnMeta: { id: 'col_1' } },
          },
        ],
      };

      const barData = manager._buildBarData(payload);

      expect(typeof barData[0].pekerjaanId).toBe('string');
      expect(typeof barData[0].columnId).toBe('string');
    });

    test('calculates variance correctly', () => {
      mockState.stateManager.states.planned.assignmentMap.set('123-col_1', 50);
      mockState.stateManager.states.actual.assignmentMap.set('123-col_1', 75);

      const payload = {
        tree: [{ pekerjaanId: 123, name: 'Task 1', subRows: [] }],
        timeColumns: [
          {
            id: 'col_1',
            fieldId: 'col_1',
            meta: { timeColumn: true, columnMeta: { id: 'col_1' } },
          },
        ],
      };

      const barData = manager._buildBarData(payload);

      expect(barData[0].planned).toBe(50);
      expect(barData[0].actual).toBe(75);
      expect(barData[0].variance).toBe(25); // 75 - 50
    });

    test('includes bars even with zero values (for continuity)', () => {
      mockState.stateManager.states.planned.assignmentMap.set('123-col_1', 0);
      mockState.stateManager.states.actual.assignmentMap.set('123-col_1', 0);
      mockState.stateManager.states.planned.assignmentMap.set('123-col_2', 50);

      const payload = {
        tree: [{ pekerjaanId: 123, name: 'Task 1', subRows: [] }],
        timeColumns: [
          {
            id: 'col_1',
            fieldId: 'col_1',
            meta: { timeColumn: true, columnMeta: { id: 'col_1' } },
          },
          {
            id: 'col_2',
            fieldId: 'col_2',
            meta: { timeColumn: true, columnMeta: { id: 'col_2' } },
          },
        ],
      };

      const barData = manager._buildBarData(payload);

      // Should include both bars (col_1 with 0 and col_2 with 50)
      expect(barData.length).toBe(2);
      const col1Bar = barData.find((b) => b.columnId === 'col_1');
      const col2Bar = barData.find((b) => b.columnId === 'col_2');
      expect(col1Bar.planned).toBe(0);
      expect(col2Bar.planned).toBe(50);
    });

    test('handles nested tree structure', () => {
      const payload = {
        tree: [
          {
            pekerjaanId: 100,
            name: 'Parent',
            subRows: [
              { pekerjaanId: 101, name: 'Child 1', subRows: [] },
              { pekerjaanId: 102, name: 'Child 2', subRows: [] },
            ],
          },
        ],
        timeColumns: [
          {
            id: 'col_1',
            fieldId: 'col_1',
            meta: { timeColumn: true, columnMeta: { id: 'col_1' } },
          },
        ],
      };

      mockState.stateManager.states.planned.assignmentMap.set('100-col_1', 30);
      mockState.stateManager.states.planned.assignmentMap.set('101-col_1', 40);
      mockState.stateManager.states.planned.assignmentMap.set('102-col_1', 50);

      const barData = manager._buildBarData(payload);

      // Should include all 3 tasks (parent + 2 children)
      expect(barData.length).toBe(3);
      const ids = barData.map((b) => b.pekerjaanId);
      expect(ids).toContain('100');
      expect(ids).toContain('101');
      expect(ids).toContain('102');
    });
  });

  describe('_flattenRows()', () => {
    test('flattens tree with subRows', () => {
      const tree = [
        {
          pekerjaanId: 1,
          name: 'Parent',
          subRows: [
            { pekerjaanId: 2, name: 'Child 1', subRows: [] },
            { pekerjaanId: 3, name: 'Child 2', subRows: [] },
          ],
        },
      ];

      const flattened = manager._flattenRows(tree);

      expect(flattened.length).toBe(3);
      expect(flattened[0].pekerjaanId).toBe(1);
      expect(flattened[1].pekerjaanId).toBe(2);
      expect(flattened[2].pekerjaanId).toBe(3);
    });

    test('flattens tree with children property', () => {
      const tree = [
        {
          pekerjaanId: 1,
          name: 'Parent',
          children: [
            { pekerjaanId: 2, name: 'Child 1', children: [] },
          ],
        },
      ];

      const flattened = manager._flattenRows(tree);

      expect(flattened.length).toBe(2);
    });

    test('handles deeply nested structure', () => {
      const tree = [
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
                  subRows: [],
                },
              ],
            },
          ],
        },
      ];

      const flattened = manager._flattenRows(tree);

      expect(flattened.length).toBe(3);
    });

    test('returns empty array for empty input', () => {
      expect(manager._flattenRows([]).length).toBe(0);
      expect(manager._flattenRows(null).length).toBe(0);
      expect(manager._flattenRows(undefined).length).toBe(0);
    });
  });

  describe('_resolveColumnMeta()', () => {
    test('resolves meta from column.meta.columnMeta', () => {
      const col = {
        meta: {
          timeColumn: true,
          columnMeta: { id: 'col_1', fieldId: 'col_1' },
        },
      };

      const meta = manager._resolveColumnMeta(col);

      expect(meta).toBeTruthy();
      expect(meta.timeColumn).toBe(true);
      expect(meta.id).toBe('col_1');
    });

    test('resolves meta from column.meta directly', () => {
      const col = {
        meta: {
          timeColumn: true,
          id: 'col_2',
        },
      };

      const meta = manager._resolveColumnMeta(col);

      expect(meta).toBeTruthy();
      expect(meta.timeColumn).toBe(true);
    });

    test('infers time column from generationMode', () => {
      const col = {
        id: 'col_3',
        generationMode: 'weekly',
      };

      const meta = manager._resolveColumnMeta(col);

      expect(meta).toBeTruthy();
      expect(meta.timeColumn).toBe(true);
    });

    test('infers time column from type property', () => {
      const col = {
        id: 'col_4',
        type: 'monthly',
      };

      const meta = manager._resolveColumnMeta(col);

      expect(meta).toBeTruthy();
      expect(meta.timeColumn).toBe(true);
    });

    test('infers time column from rangeLabel', () => {
      const col = {
        id: 'col_5',
        rangeLabel: 'Week 1',
      };

      const meta = manager._resolveColumnMeta(col);

      expect(meta).toBeTruthy();
      expect(meta.timeColumn).toBe(true);
    });

    test('returns null for non-time columns', () => {
      const col = {
        id: 'col_6',
        type: 'text',
      };

      const meta = manager._resolveColumnMeta(col);

      expect(meta).toBeNull();
    });

    test('returns null for null input', () => {
      expect(manager._resolveColumnMeta(null)).toBeNull();
      expect(manager._resolveColumnMeta(undefined)).toBeNull();
    });
  });

  describe('_mergeModeState()', () => {
    test('merges assignmentMap and modifiedCells', () => {
      const modeState = {
        assignmentMap: new Map([
          ['123-col_1', 30],
          ['123-col_2', 40],
        ]),
        modifiedCells: new Map([
          ['123-col_2', 50], // Override
          ['123-col_3', 20], // New
        ]),
      };

      const merged = manager._mergeModeState(modeState);

      expect(merged.size).toBe(3);
      expect(merged.get('123-col_1')).toBe(30);
      expect(merged.get('123-col_2')).toBe(50); // Modified value wins
      expect(merged.get('123-col_3')).toBe(20);
    });

    test('returns empty Map for null input', () => {
      const merged = manager._mergeModeState(null);

      expect(merged).toBeInstanceOf(Map);
      expect(merged.size).toBe(0);
    });

    test('handles missing modifiedCells', () => {
      const modeState = {
        assignmentMap: new Map([['123-col_1', 30]]),
      };

      const merged = manager._mergeModeState(modeState);

      expect(merged.size).toBe(1);
      expect(merged.get('123-col_1')).toBe(30);
    });
  });

  describe('_resolveValue()', () => {
    test('returns value from map if exists', () => {
      const map = new Map([['key1', 42]]);

      expect(manager._resolveValue(map, 'key1', 0)).toBe(42);
    });

    test('returns fallback if key not found', () => {
      const map = new Map([['key1', 42]]);

      expect(manager._resolveValue(map, 'key2', 99)).toBe(99);
    });

    test('returns fallback for non-finite values', () => {
      const map = new Map([['key1', NaN]]);

      expect(manager._resolveValue(map, 'key1', 10)).toBe(10);
    });

    test('returns fallback for null map', () => {
      expect(manager._resolveValue(null, 'key1', 5)).toBe(5);
    });
  });

  describe('_log()', () => {
    test('logs when debug is enabled', () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation();
      manager.debug = true;

      manager._log('test-event', { foo: 'bar' });

      expect(consoleSpy).toHaveBeenCalledWith(
        '[UnifiedTable] test-event',
        { foo: 'bar' }
      );

      consoleSpy.mockRestore();
    });

    test('does not log when debug is disabled', () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation();
      manager.debug = false;

      manager._log('test-event', { foo: 'bar' });

      expect(consoleSpy).not.toHaveBeenCalled();

      consoleSpy.mockRestore();
    });

    test('respects window.DEBUG_UNIFIED_TABLE flag', () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation();
      manager.debug = false;
      window.DEBUG_UNIFIED_TABLE = true;

      manager._log('test-event', {});

      expect(consoleSpy).toHaveBeenCalled();

      window.DEBUG_UNIFIED_TABLE = false;
      consoleSpy.mockRestore();
    });
  });
});
