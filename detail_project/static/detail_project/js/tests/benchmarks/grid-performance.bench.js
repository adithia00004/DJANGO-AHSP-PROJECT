import { afterAll, bench, describe } from 'vitest';
import { GridRenderer } from '../../src/modules/grid/grid-renderer.js';

const ONE_DAY_MS = 24 * 60 * 60 * 1000;
const originalConsole = {
  log: console.log,
  warn: console.warn,
};

console.log = () => {};
console.warn = () => {};

function createTimeColumns(weekCount) {
  const startDate = new Date('2025-01-01');
  const columns = [];

  for (let i = 0; i < weekCount; i += 1) {
    const start = new Date(startDate.getTime() + i * 7 * ONE_DAY_MS);
    const end = new Date(start.getTime() + 6 * ONE_DAY_MS);
    columns.push({
      id: `col_${i + 1}`,
      label: `W${i + 1}`,
      rangeLabel: `${start.toISOString().slice(0, 10)} - ${end.toISOString().slice(0, 10)}`,
      startDate: start,
      endDate: end,
    });
  }

  return columns;
}

function createMockState(rowCount, weekCount) {
  const pekerjaanTree = [];
  const flatPekerjaan = [];
  const volumeMap = new Map();
  const assignmentMap = new Map();
  const expandedNodes = new Set();

  const timeColumns = createTimeColumns(weekCount);

  for (let i = 0; i < rowCount; i += 1) {
    const id = i + 1;
    const node = {
      id: String(id),
      type: 'pekerjaan',
      nama: `Pekerjaan ${id}`,
      kode: `PKJ-${id.toString().padStart(4, '0')}`,
      volume: 100,
      satuan: 'unit',
      parent_id: null,
      level: 0,
      path: [`Pekerjaan ${id}`],
      children: [],
    };
    pekerjaanTree.push(node);
    flatPekerjaan.push(node);
    volumeMap.set(String(id), 100);
    expandedNodes.add(String(id));
  }

  flatPekerjaan.forEach((node, idx) => {
    timeColumns.forEach((column, colIdx) => {
      const pattern = ((idx + colIdx) % 4) * 10;
      if (pattern > 0) {
        assignmentMap.set(`${node.id}-${column.id}`, pattern);
      }
    });
  });

  return {
    pekerjaanTree,
    flatPekerjaan,
    timeColumns,
    volumeMap,
    assignmentMap,
    modifiedCells: new Map(),
    expandedNodes,
    volumeResetJobs: new Set(),
    displayMode: 'percentage',
    cache: {},
  };
}

describe('GridRenderer performance benchmarks', () => {
  afterAll(() => {
    console.log = originalConsole.log;
    console.warn = originalConsole.warn;
  });

  bench('render 100 rows × 52 weeks', () => {
    const state = createMockState(100, 52);
    const renderer = new GridRenderer(state);
    renderer.renderTables();
  }, { time: 500 });

  bench('render 500 rows × 52 weeks', () => {
    const state = createMockState(500, 52);
    const renderer = new GridRenderer(state);
    renderer.renderTables();
  }, { time: 500 });
});
