/**
 * Unit Tests for TanStackGridManager
 *
 * Tests for the grid manager including virtual cell rect calculation.
 *
 * To run: npm run test:frontend
 */

import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { TanStackGridManager } from '../src/modules/grid/tanstack-grid-manager.js';

describe('TanStackGridManager', () => {
    let manager;
    let mockState;
    let container;

    beforeEach(() => {
        // Create mock container
        container = document.createElement('div');
        document.body.appendChild(container);

        // Mock state
        mockState = {
            timeScale: 'weekly',
            inputMode: 'percentage',
            volumeMap: new Map(),
            stateManager: {
                currentMode: 'planned',
                getCellValue: vi.fn(() => 0),
                states: {
                    planned: { assignmentMap: new Map(), modifiedCells: new Map() },
                    actual: { assignmentMap: new Map(), modifiedCells: new Map() },
                },
            },
        };

        manager = new TanStackGridManager(mockState, {});
        manager.mount(container, {});
    });

    afterEach(() => {
        if (manager) {
            manager.destroy();
        }
        if (container && document.body.contains(container)) {
            document.body.removeChild(container);
        }
        vi.clearAllMocks();
    });

    describe('Constructor and Initialization', () => {
        test('initializes with default row height', () => {
            expect(manager.rowHeight).toBe(44);
        });

        test('initializes with empty currentColumns', () => {
            expect(manager.currentColumns).toEqual([]);
        });

        test('initializes with empty currentRows', () => {
            expect(manager.currentRows).toEqual([]);
        });

        test('mounts to container', () => {
            expect(manager.container).toBe(container);
            expect(manager.bodyScroll).toBeTruthy();
            expect(manager.headerContainer).toBeTruthy();
        });
    });

    describe('updateData()', () => {
        test('updates currentColumns with time columns', () => {
            const timeColumns = [
                { id: 'col_1', fieldId: 'col_1', label: 'Week 1' },
                { id: 'col_2', fieldId: 'col_2', label: 'Week 2' },
            ];

            manager.updateData({ tree: [], timeColumns });

            // Should have pinned columns + time columns
            expect(manager.currentColumns.length).toBeGreaterThan(0);
            const timeColumnsDefs = manager.currentColumns.filter(c => c.meta?.timeColumn);
            expect(timeColumnsDefs.length).toBe(2);
        });

        test('updates currentRows with tree data', () => {
            const tree = [
                { id: 1, nama: 'Task 1', pekerjaan_id: 1 },
                { id: 2, nama: 'Task 2', pekerjaan_id: 2 },
            ];

            manager.updateData({ tree, timeColumns: [] });

            expect(manager.currentRows.length).toBe(2);
            expect(manager.currentRows[0].name).toBe('Task 1');
        });

        test('handles nested tree structure', () => {
            const tree = [
                {
                    id: 1,
                    nama: 'Parent',
                    pekerjaan_id: 1,
                    children: [
                        { id: 2, nama: 'Child 1', pekerjaan_id: 2 },
                        { id: 3, nama: 'Child 2', pekerjaan_id: 3 },
                    ],
                },
            ];

            manager.updateData({ tree, timeColumns: [] });

            expect(manager.currentRows.length).toBe(1); // Only root in flat rows
            expect(manager.currentRows[0].subRows.length).toBe(2);
        });
    });

    describe('getAllCellBoundingRects()', () => {
        beforeEach(() => {
            // Setup test data
            const tree = [
                { id: 1, nama: 'Task 1', pekerjaan_id: 1 },
                { id: 2, nama: 'Task 2', pekerjaan_id: 2 },
                { id: 3, nama: 'Task 3', pekerjaan_id: 3 },
            ];

            const timeColumns = [
                { id: 'col_1', fieldId: 'col_1', label: 'Week 1' },
                { id: 'col_2', fieldId: 'col_2', label: 'Week 2' },
                { id: 'col_3', fieldId: 'col_3', label: 'Week 3' },
            ];

            manager.updateData({ tree, timeColumns });
        });

        test('returns rects for all row x column combinations', () => {
            const rects = manager.getAllCellBoundingRects();

            // 3 rows x 3 time columns = 9 rects
            expect(rects.length).toBe(9);
        });

        test('each rect has required properties', () => {
            const rects = manager.getAllCellBoundingRects();

            rects.forEach(rect => {
                expect(rect).toHaveProperty('pekerjaanId');
                expect(rect).toHaveProperty('columnId');
                expect(rect).toHaveProperty('x');
                expect(rect).toHaveProperty('y');
                expect(rect).toHaveProperty('width');
                expect(rect).toHaveProperty('height');
            });
        });

        test('X positions are calculated correctly', () => {
            const rects = manager.getAllCellBoundingRects();

            // Group by column
            const byColumn = {};
            rects.forEach(r => {
                if (!byColumn[r.columnId]) byColumn[r.columnId] = [];
                byColumn[r.columnId].push(r);
            });

            // Each column should have consistent X position
            Object.values(byColumn).forEach(colRects => {
                const xValues = colRects.map(r => r.x);
                const allSame = xValues.every(x => x === xValues[0]);
                expect(allSame).toBe(true);
            });
        });

        test('Y positions are calculated based on row height', () => {
            const rects = manager.getAllCellBoundingRects();
            const rowHeight = manager.rowHeight;

            // Group by pekerjaan
            const byRow = {};
            rects.forEach(r => {
                if (!byRow[r.pekerjaanId]) byRow[r.pekerjaanId] = [];
                byRow[r.pekerjaanId].push(r);
            });

            // Each row should have consistent Y position
            const yValues = Object.entries(byRow).map(([id, rowRects]) => ({
                id,
                y: rowRects[0].y,
            }));

            // Y values should be multiples of rowHeight
            yValues.forEach((row, idx) => {
                expect(row.y).toBe(idx * rowHeight);
            });
        });

        test('height matches rowHeight', () => {
            const rects = manager.getAllCellBoundingRects();

            rects.forEach(rect => {
                expect(rect.height).toBe(manager.rowHeight);
            });
        });

        test('returns empty array when no table', () => {
            manager.table = null;
            const rects = manager.getAllCellBoundingRects();
            expect(rects).toEqual([]);
        });

        test('only includes time columns (not pinned)', () => {
            const rects = manager.getAllCellBoundingRects();

            // All rects should have columnId starting with col_
            rects.forEach(rect => {
                expect(rect.columnId).toMatch(/^col_/);
            });
        });
    });
});
