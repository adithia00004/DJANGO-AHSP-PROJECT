/**
 * Unit Tests for StateManager
 *
 * Phase 0.2: StateManager Architecture
 *
 * To run tests:
 * npm test -- state-manager.test.js
 *
 * Or with Jest directly:
 * npx jest detail_project/static/detail_project/js/tests/state-manager.test.js
 */

import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { StateManager } from '../src/modules/core/state-manager.js';
import { ModeState } from '../src/modules/core/mode-state.js';

const jest = {
  fn: vi.fn,
  spyOn: vi.spyOn,
};

describe('StateManager', () => {
  let stateManager;

  beforeEach(() => {
    // Reset singleton before each test
    StateManager.instance = null;
    stateManager = StateManager.getInstance();
  });

  afterEach(() => {
    // Cleanup
    if (stateManager) {
      stateManager.reset();
    }
  });

  describe('Singleton Pattern', () => {
    test('getInstance returns same instance', () => {
      const instance1 = StateManager.getInstance();
      const instance2 = StateManager.getInstance();

      expect(instance1).toBe(instance2);
    });

    test('constructor throws error when called directly', () => {
      // Reset singleton
      StateManager.instance = null;
      StateManager.getInstance(); // Create first instance

      // Try to create another instance directly
      expect(() => new StateManager()).toThrow('StateManager is a singleton');
    });

    test('instance has expected initial state', () => {
      expect(stateManager.currentMode).toBe('planned');
      expect(stateManager.states).toHaveProperty('planned');
      expect(stateManager.states).toHaveProperty('actual');
      expect(stateManager.states.planned).toBeInstanceOf(ModeState);
      expect(stateManager.states.actual).toBeInstanceOf(ModeState);
    });
  });

  describe('Cell Value Management', () => {
    test('getCellValue returns 0 for empty cell', () => {
      const value = stateManager.getCellValue(123, 'col_456');
      expect(value).toBe(0);
    });

    test('getCellValue reads from assignmentMap', () => {
      // Add value to assignmentMap
      stateManager.states.planned.assignmentMap.set('123-col_456', 50);

      const value = stateManager.getCellValue(123, 'col_456');
      expect(value).toBe(50);
    });

    test('getCellValue prioritizes modifiedCells over assignmentMap', () => {
      // Add value to assignmentMap
      stateManager.states.planned.assignmentMap.set('123-col_456', 50);

      // Add different value to modifiedCells
      stateManager.states.planned.modifiedCells.set('123-col_456', 75);

      const value = stateManager.getCellValue(123, 'col_456');
      expect(value).toBe(75); // Should return modified value
    });

    test('setCellValue updates modifiedCells', () => {
      stateManager.setCellValue(123, 'col_456', 60);

      const value = stateManager.states.planned.modifiedCells.get('123-col_456');
      expect(value).toBe(60);
    });

    test('setCellValue invalidates cache', () => {
      // Pre-populate cache
      stateManager.getAllCellsForMode('planned');
      expect(stateManager._mergedCellsCache.has('cells:planned')).toBe(true);

      // Modify cell
      stateManager.setCellValue(123, 'col_456', 60);

      // Cache should be invalidated
      expect(stateManager.states.planned.isDirty).toBe(true);
    });

    test('setCellValue handles invalid values gracefully', () => {
      stateManager.setCellValue(123, 'col_456', 'invalid');

      const value = stateManager.getCellValue(123, 'col_456');
      expect(value).toBe(0); // Should return default 0
    });
  });

  describe('Mode Switching', () => {
    test('switchMode changes currentMode', () => {
      expect(stateManager.currentMode).toBe('planned');

      stateManager.switchMode('actual');

      expect(stateManager.currentMode).toBe('actual');
    });

    test('switchMode preserves state isolation', () => {
      // Add value to planned mode
      stateManager.switchMode('planned');
      stateManager.setCellValue(123, 'col_456', 50);

      // Switch to actual mode
      stateManager.switchMode('actual');
      stateManager.setCellValue(123, 'col_456', 75);

      // Switch back to planned mode
      stateManager.switchMode('planned');

      // Planned value should still be 50
      const plannedValue = stateManager.getCellValue(123, 'col_456');
      expect(plannedValue).toBe(50);

      // Actual value should be 75
      stateManager.switchMode('actual');
      const actualValue = stateManager.getCellValue(123, 'col_456');
      expect(actualValue).toBe(75);
    });

    test('switchMode notifies listeners', () => {
      const listener = jest.fn();
      stateManager.addEventListener(listener);

      stateManager.switchMode('actual');

      expect(listener).toHaveBeenCalledWith({
        type: 'mode-switch',
        oldMode: 'planned',
        newMode: 'actual'
      });
    });

    test('switchMode ignores invalid mode', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

      stateManager.switchMode('invalid');

      expect(stateManager.currentMode).toBe('planned'); // Should stay planned
      expect(consoleSpy).toHaveBeenCalled();

      consoleSpy.mockRestore();
    });

    test('switchMode ignores same mode', () => {
      const listener = jest.fn();
      stateManager.addEventListener(listener);

      stateManager.switchMode('planned'); // Already in planned mode

      expect(listener).not.toHaveBeenCalled();
    });
  });

  describe('getAllCellsForMode', () => {
    test('returns merged Map with assignmentMap + modifiedCells', () => {
      // Add to assignmentMap
      stateManager.states.planned.assignmentMap.set('123-col_1', 30);
      stateManager.states.planned.assignmentMap.set('123-col_2', 40);

      // Add to modifiedCells
      stateManager.states.planned.modifiedCells.set('123-col_2', 50); // Override
      stateManager.states.planned.modifiedCells.set('123-col_3', 20); // New

      const merged = stateManager.getAllCellsForMode('planned');

      expect(merged.size).toBe(3);
      expect(merged.get('123-col_1')).toBe(30); // From assignmentMap
      expect(merged.get('123-col_2')).toBe(50); // Modified (overrides assignmentMap)
      expect(merged.get('123-col_3')).toBe(20); // From modifiedCells
    });

    test('returns cached result on second call', () => {
      stateManager.states.planned.assignmentMap.set('123-col_1', 30);

      const merged1 = stateManager.getAllCellsForMode('planned');
      const merged2 = stateManager.getAllCellsForMode('planned');

      // Should return same cached Map reference
      expect(merged1).toBe(merged2);
    });

    test('cache invalidates on cell change', () => {
      const merged1 = stateManager.getAllCellsForMode('planned');

      // Modify cell
      stateManager.setCellValue(123, 'col_456', 60);

      const merged2 = stateManager.getAllCellsForMode('planned');

      // Should return new Map (not cached)
      expect(merged1).not.toBe(merged2);
      expect(merged2.has('123-col_456')).toBe(true);
    });

    test('handles invalid mode gracefully', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

      const result = stateManager.getAllCellsForMode('invalid');

      expect(result).toBeInstanceOf(Map);
      expect(result.size).toBe(0);
      expect(consoleSpy).toHaveBeenCalled();

      consoleSpy.mockRestore();
    });
  });

  describe('commitChanges', () => {
    test('moves modifiedCells to assignmentMap', () => {
      stateManager.setCellValue(123, 'col_1', 50);
      stateManager.setCellValue(456, 'col_2', 75);

      expect(stateManager.states.planned.modifiedCells.size).toBe(2);
      expect(stateManager.states.planned.assignmentMap.size).toBe(0);

      stateManager.commitChanges();

      expect(stateManager.states.planned.modifiedCells.size).toBe(0);
      expect(stateManager.states.planned.assignmentMap.size).toBe(2);
      expect(stateManager.states.planned.assignmentMap.get('123-col_1')).toBe(50);
      expect(stateManager.states.planned.assignmentMap.get('456-col_2')).toBe(75);
    });

    test('clears modifiedCells after commit', () => {
      stateManager.setCellValue(123, 'col_1', 50);
      stateManager.commitChanges();

      expect(stateManager.states.planned.modifiedCells.size).toBe(0);
    });

    test('invalidates cache after commit', () => {
      stateManager.setCellValue(123, 'col_1', 50);
      stateManager.getAllCellsForMode('planned'); // Populate cache

      stateManager.commitChanges();

      expect(stateManager.states.planned.isDirty).toBe(true);
    });

    test('notifies listeners after commit', () => {
      const listener = jest.fn();
      stateManager.addEventListener(listener);

      stateManager.setCellValue(123, 'col_1', 50);
      stateManager.commitChanges();

      expect(listener).toHaveBeenCalledWith({
        type: 'commit',
        mode: 'planned',
        count: 1
      });
    });
  });

  describe('Event Listeners', () => {
    test('addEventListener registers callback', () => {
      const listener = jest.fn();
      stateManager.addEventListener(listener);

      expect(stateManager._listeners.has(listener)).toBe(true);
      expect(stateManager._listeners.size).toBe(1);
    });

    test('removeEventListener unregisters callback', () => {
      const listener = jest.fn();
      stateManager.addEventListener(listener);
      stateManager.removeEventListener(listener);

      expect(stateManager._listeners.has(listener)).toBe(false);
      expect(stateManager._listeners.size).toBe(0);
    });

    test('listeners notified on mode switch', () => {
      const listener = jest.fn();
      stateManager.addEventListener(listener);

      stateManager.switchMode('actual');

      expect(listener).toHaveBeenCalledTimes(1);
    });

    test('listeners notified on commitChanges', () => {
      const listener = jest.fn();
      stateManager.addEventListener(listener);

      stateManager.setCellValue(123, 'col_1', 50);
      stateManager.commitChanges();

      expect(listener).toHaveBeenCalledTimes(1);
    });

    test('listener errors are caught and logged', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      const badListener = jest.fn(() => {
        throw new Error('Listener error');
      });

      stateManager.addEventListener(badListener);
      stateManager.switchMode('actual');

      // Should not throw, just log error
      expect(consoleSpy).toHaveBeenCalled();

      consoleSpy.mockRestore();
    });

    test('addEventListener rejects non-function', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

      stateManager.addEventListener('not a function');

      expect(stateManager._listeners.size).toBe(0);
      expect(consoleSpy).toHaveBeenCalled();

      consoleSpy.mockRestore();
    });
  });

  describe('Utility Methods', () => {
    test('hasUnsavedChanges returns true with modified cells', () => {
      stateManager.setCellValue(123, 'col_1', 50);

      expect(stateManager.hasUnsavedChanges()).toBe(true);
    });

    test('hasUnsavedChanges returns false after commit', () => {
      stateManager.setCellValue(123, 'col_1', 50);
      stateManager.commitChanges();

      expect(stateManager.hasUnsavedChanges()).toBe(false);
    });

    test('getStats returns correct statistics', () => {
      stateManager.setCellValue(123, 'col_1', 50);
      stateManager.states.planned.assignmentMap.set('456-col_2', 75);

      const stats = stateManager.getStats();

      expect(stats.currentMode).toBe('planned');
      expect(stats.planned.modifiedCount).toBe(1);
      expect(stats.planned.assignmentCount).toBe(1);
    });

    test('reset clears all data', () => {
      stateManager.setCellValue(123, 'col_1', 50);
      stateManager.switchMode('actual');
      stateManager.setCellValue(456, 'col_2', 75);

      stateManager.reset();

      expect(stateManager.currentMode).toBe('planned');
      expect(stateManager.states.planned.assignmentMap.size).toBe(0);
      expect(stateManager.states.planned.modifiedCells.size).toBe(0);
      expect(stateManager.states.actual.assignmentMap.size).toBe(0);
      expect(stateManager.states.actual.modifiedCells.size).toBe(0);
    });

    test('exportState returns serializable object', () => {
      stateManager.setCellValue(123, 'col_1', 50);

      const exported = stateManager.exportState();

      expect(exported).toHaveProperty('currentMode');
      expect(exported).toHaveProperty('planned');
      expect(exported).toHaveProperty('actual');
      expect(exported).toHaveProperty('stats');
      expect(JSON.stringify(exported)).toBeTruthy(); // Should be serializable
    });
  });

  describe('Data Loading', () => {
    test('loadData replaces assignmentMap', () => {
      const dataMap = new Map([
        ['123-col_1', 30],
        ['456-col_2', 50]
      ]);

      stateManager.loadData('planned', dataMap);

      expect(stateManager.states.planned.assignmentMap.size).toBe(2);
      expect(stateManager.states.planned.assignmentMap.get('123-col_1')).toBe(30);
    });

    test('loadData clears modifiedCells', () => {
      stateManager.setCellValue(123, 'col_1', 50);

      const dataMap = new Map([['456-col_2', 75]]);
      stateManager.loadData('planned', dataMap);

      expect(stateManager.states.planned.modifiedCells.size).toBe(0);
    });

    test('setInitialValue sets values for both modes', () => {
      stateManager.setInitialValue(123, 'col_1', 50, 75);

      expect(stateManager.states.planned.assignmentMap.get('123-col_1')).toBe(50);
      expect(stateManager.states.actual.assignmentMap.get('123-col_1')).toBe(75);
    });

    test('setInitialValue skips zero values', () => {
      stateManager.setInitialValue(123, 'col_1', 0, 0);

      expect(stateManager.states.planned.assignmentMap.has('123-col_1')).toBe(false);
      expect(stateManager.states.actual.assignmentMap.has('123-col_1')).toBe(false);
    });
  });
});

describe('ModeState', () => {
  let modeState;

  beforeEach(() => {
    modeState = new ModeState();
  });

  test('initializes with empty maps', () => {
    expect(modeState.assignmentMap).toBeInstanceOf(Map);
    expect(modeState.modifiedCells).toBeInstanceOf(Map);
    expect(modeState.assignmentMap.size).toBe(0);
    expect(modeState.modifiedCells.size).toBe(0);
    expect(modeState.isDirty).toBe(false);
  });

  test('toJSON serializes state', () => {
    modeState.assignmentMap.set('123-col_1', 50);
    modeState.modifiedCells.set('456-col_2', 75);
    modeState.isDirty = true;

    const json = modeState.toJSON();

    expect(json.assignmentMap).toEqual([['123-col_1', 50]]);
    expect(json.modifiedCells).toEqual([['456-col_2', 75]]);
    expect(json.isDirty).toBe(true);
  });

  test('fromJSON deserializes state', () => {
    const json = {
      assignmentMap: [['123-col_1', 50]],
      modifiedCells: [['456-col_2', 75]],
      isDirty: true
    };

    const restored = ModeState.fromJSON(json);

    expect(restored.assignmentMap.get('123-col_1')).toBe(50);
    expect(restored.modifiedCells.get('456-col_2')).toBe(75);
    expect(restored.isDirty).toBe(true);
  });

  test('getStats returns correct statistics', () => {
    modeState.assignmentMap.set('123-col_1', 50);
    modeState.modifiedCells.set('456-col_2', 75);

    const stats = modeState.getStats();

    expect(stats.assignmentCount).toBe(1);
    expect(stats.modifiedCount).toBe(1);
    expect(stats.hasUnsavedChanges).toBe(true);
  });

  test('clear removes all data', () => {
    modeState.assignmentMap.set('123-col_1', 50);
    modeState.modifiedCells.set('456-col_2', 75);

    modeState.clear();

    expect(modeState.assignmentMap.size).toBe(0);
    expect(modeState.modifiedCells.size).toBe(0);
    expect(modeState.isDirty).toBe(true);
  });

  test('clone creates deep copy', () => {
    modeState.assignmentMap.set('123-col_1', 50);
    modeState.modifiedCells.set('456-col_2', 75);

    const cloned = modeState.clone();

    // Should have same data
    expect(cloned.assignmentMap.get('123-col_1')).toBe(50);
    expect(cloned.modifiedCells.get('456-col_2')).toBe(75);

    // But different Map instances
    expect(cloned.assignmentMap).not.toBe(modeState.assignmentMap);
    expect(cloned.modifiedCells).not.toBe(modeState.modifiedCells);
  });
});
