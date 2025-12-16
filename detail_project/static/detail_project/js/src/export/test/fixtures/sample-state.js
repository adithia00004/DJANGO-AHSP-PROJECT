/**
 * Sample Application State
 * Complete application state mock untuk testing
 */

import {
  sampleHierarchyRows,
  sampleWeekColumns,
  samplePlannedProgress,
  sampleActualProgress,
  sampleKurvaSData,
  smallDataset,
  mediumDataset,
  generateLargeDataset
} from './sample-data.js';

/**
 * Complete application state (medium dataset)
 * Ready untuk testing semua report types
 */
export const completeState = {
  // Hierarchy rows
  hierarchyRows: sampleHierarchyRows,

  // Week columns
  weekColumns: sampleWeekColumns,

  // Progress maps
  plannedProgress: samplePlannedProgress,
  actualProgress: sampleActualProgress,

  // Kurva S cumulative data
  kurvaSData: sampleKurvaSData,

  // Project metadata
  projectName: 'Pembangunan Gedung Kantor',
  projectLocation: 'Jakarta Selatan',
  projectStartDate: '2025-01-06',
  projectEndDate: '2025-07-06',
  projectOwner: 'PT. Contoh Indonesia',
  contractor: 'PT. Bangun Jaya',

  // User metadata
  exportedBy: 'Admin User',
  exportedAt: new Date().toISOString(),
  version: '1.0.0'
};

/**
 * Small state untuk quick testing
 * 10 rows, 12 weeks
 */
export const smallState = {
  hierarchyRows: smallDataset.rows,
  weekColumns: smallDataset.weeks,
  plannedProgress: smallDataset.planned,
  actualProgress: smallDataset.actual,
  kurvaSData: smallDataset.kurvaS,
  projectName: 'Test Project (Small)',
  exportedBy: 'Test User',
  exportedAt: new Date().toISOString()
};

/**
 * Medium state untuk integration testing
 * 30 rows, 26 weeks (same as completeState)
 */
export const mediumState = completeState;

/**
 * Large state untuk performance testing
 * 100 rows, 52 weeks
 */
export const largeState = (() => {
  const dataset = generateLargeDataset(100, 52);
  return {
    hierarchyRows: dataset.rows,
    weekColumns: dataset.weeks,
    plannedProgress: dataset.planned,
    actualProgress: dataset.actual,
    kurvaSData: dataset.kurvaS,
    projectName: 'Test Project (Large - 100 tasks, 52 weeks)',
    exportedBy: 'Performance Test',
    exportedAt: new Date().toISOString()
  };
})();

/**
 * Edge case: Minimal state (1 row, 1 week)
 */
export const minimalState = {
  hierarchyRows: [
    {
      id: 1,
      type: 'klasifikasi',
      level: 0,
      parentId: null,
      name: 'Pekerjaan Tunggal'
    },
    {
      id: 2,
      type: 'pekerjaan',
      level: 1,
      parentId: 1,
      name: 'Task Tunggal'
    }
  ],
  weekColumns: [
    { week: 1, startDate: '2025-01-06T00:00:00Z', endDate: '2025-01-12T23:59:59Z' }
  ],
  plannedProgress: {
    2: { 1: 50 }
  },
  actualProgress: {
    2: { 1: 45 }
  },
  kurvaSData: [
    { week: 1, planned: 50, actual: 45 }
  ],
  projectName: 'Minimal Test',
  exportedBy: 'Edge Case Test',
  exportedAt: new Date().toISOString()
};

/**
 * Edge case: Empty actual progress (planned only)
 */
export const plannedOnlyState = {
  ...completeState,
  actualProgress: {},
  kurvaSData: completeState.kurvaSData.map(d => ({ ...d, actual: 0 })),
  projectName: 'Planned Only Test (No Actual Progress)'
};

/**
 * Edge case: With gaps (progress terputus)
 */
export const withGapsState = {
  hierarchyRows: [
    { id: 1, type: 'klasifikasi', level: 0, parentId: null, name: 'Test Gaps' },
    { id: 2, type: 'pekerjaan', level: 1, parentId: 1, name: 'Task dengan Gap' }
  ],
  weekColumns: sampleWeekColumns.slice(0, 10),
  plannedProgress: {
    2: { 1: 20, 2: 40, 5: 60, 6: 80, 9: 100 } // Gaps di W3-W4, W7-W8
  },
  actualProgress: {
    2: { 1: 18, 2: 35, 5: 55, 6: 75, 9: 95 }
  },
  kurvaSData: [
    { week: 1, planned: 20, actual: 18 },
    { week: 2, planned: 40, actual: 35 },
    { week: 3, planned: 40, actual: 35 }, // Gap (no progress)
    { week: 4, planned: 40, actual: 35 }, // Gap (no progress)
    { week: 5, planned: 60, actual: 55 },
    { week: 6, planned: 80, actual: 75 },
    { week: 7, planned: 80, actual: 75 }, // Gap
    { week: 8, planned: 80, actual: 75 }, // Gap
    { week: 9, planned: 100, actual: 95 },
    { week: 10, planned: 100, actual: 95 }
  ],
  projectName: 'Gap Test (Segmented Bars)',
  exportedBy: 'Edge Case Test'
};

/**
 * Edge case: Deep hierarchy (4 levels)
 * Note: Current implementation supports 3 levels max, this tests edge case
 */
export const deepHierarchyState = {
  hierarchyRows: [
    { id: 1, type: 'klasifikasi', level: 0, parentId: null, name: 'Level 0: Klasifikasi' },
    { id: 2, type: 'sub-klasifikasi', level: 1, parentId: 1, name: 'Level 1: Sub-klasifikasi' },
    { id: 3, type: 'pekerjaan', level: 2, parentId: 2, name: 'Level 2: Pekerjaan' },
    // Level 3 (not officially supported but should not break)
    { id: 4, type: 'pekerjaan', level: 3, parentId: 3, name: 'Level 3: Sub-pekerjaan (edge case)' }
  ],
  weekColumns: sampleWeekColumns.slice(0, 4),
  plannedProgress: {
    3: { 1: 25, 2: 50, 3: 75, 4: 100 },
    4: { 1: 20, 2: 45, 3: 70, 4: 95 }
  },
  actualProgress: {
    3: { 1: 22, 2: 48, 3: 72, 4: 98 },
    4: { 1: 18, 2: 42, 3: 68, 4: 92 }
  },
  kurvaSData: sampleKurvaSData.slice(0, 4),
  projectName: 'Deep Hierarchy Test (4 levels)',
  exportedBy: 'Edge Case Test'
};

/**
 * Test state for pagination edge cases
 */
export const paginationTestState = {
  // Exactly 15 rows (test orphaned header at boundary)
  hierarchyRows: [
    { id: 1, type: 'klasifikasi', level: 0, parentId: null, name: 'Klas A' },
    ...Array.from({ length: 13 }, (_, i) => ({
      id: i + 2,
      type: 'pekerjaan',
      level: 1,
      parentId: 1,
      name: `Pekerjaan ${i + 1}`
    })),
    { id: 15, type: 'klasifikasi', level: 0, parentId: null, name: 'Klas B (should not be orphaned)' }
  ],
  weekColumns: sampleWeekColumns.slice(0, 16), // 16 weeks for column pagination test
  plannedProgress: Object.fromEntries(
    Array.from({ length: 13 }, (_, i) => [
      i + 2,
      { 1: 10, 2: 20, 3: 30, 4: 40, 5: 50, 6: 60, 7: 70, 8: 80, 9: 90, 10: 100 }
    ])
  ),
  actualProgress: {},
  kurvaSData: sampleKurvaSData.slice(0, 16),
  projectName: 'Pagination Edge Case Test',
  exportedBy: 'Pagination Test'
};

/**
 * Get state by name
 * @param {string} name - State name
 * @returns {Object} State object
 */
export function getStateByName(name) {
  const states = {
    complete: completeState,
    small: smallState,
    medium: mediumState,
    large: largeState,
    minimal: minimalState,
    plannedOnly: plannedOnlyState,
    withGaps: withGapsState,
    deepHierarchy: deepHierarchyState,
    paginationTest: paginationTestState
  };

  return states[name] || completeState;
}

/**
 * Get all available state names
 * @returns {Array<string>} State names
 */
export function getAvailableStates() {
  return [
    'complete',
    'small',
    'medium',
    'large',
    'minimal',
    'plannedOnly',
    'withGaps',
    'deepHierarchy',
    'paginationTest'
  ];
}
