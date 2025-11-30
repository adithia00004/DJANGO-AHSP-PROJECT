import test from 'node:test';
import assert from 'node:assert/strict';

import {
  ensureWeekZeroDataset,
  prependZeroDetails,
  createZeroWeekEntry,
} from './week-zero-helpers.js';

test('ensureWeekZeroDataset prepends Week 0 for progress view', () => {
  const dataset = {
    labels: ['Week 1', 'Week 2'],
    planned: [50, 100],
    actual: [20, 80],
    details: [{ label: 'Week 1', planned: 50, actual: 20 }],
  };

  const result = ensureWeekZeroDataset(dataset);

  assert.equal(result.labels[0], 'Week 0');
  assert.equal(result.planned[0], 0);
  assert.equal(result.actual[0], 0);
  assert.equal(result.details[0].label, 'Week 0');
  assert.equal(result.details[0].planned, 0);
});

test('ensureWeekZeroDataset prepends W0 for cost view including acSeries and metadata', () => {
  const dataset = {
    viewMode: 'cost',
    labels: ['W1'],
    planned: [25],
    actual: [10],
    acSeries: [12],
    details: {
      weeks: [{ week_number: 1 }],
      actualWeeks: [{ week_number: 1 }],
    },
  };

  const result = ensureWeekZeroDataset(dataset);
  assert.equal(result.labels[0], 'W0');
  assert.equal(result.acSeries[0], 0);
  assert.equal(result.details.weeks[0].week_number, 0);
  assert.equal(result.details.actualWeeks[0].week_number, 0);
});

test('prependZeroDetails keeps non-array details untouched when not cost view', () => {
  const obj = { foo: 'bar' };
  const result = prependZeroDetails(obj, 'Week 0', false);
  assert.deepEqual(result, obj);
});

test('createZeroWeekEntry returns zeroed structure', () => {
  const entry = createZeroWeekEntry();
  assert.equal(entry.week_number, 0);
  assert.equal(entry.cumulative_percent, 0);
  assert.deepEqual(entry.pekerjaan_breakdown, {});
});
