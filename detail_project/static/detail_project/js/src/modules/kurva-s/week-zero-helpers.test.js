import { describe, it, expect } from 'vitest';

import {
  ensureWeekZeroDataset,
  prependZeroDetails,
  createZeroWeekEntry,
} from './week-zero-helpers.js';

describe('week-zero-helpers', () => {
  it('prepends Week 0 for progress view', () => {
    const dataset = {
      labels: ['Week 1', 'Week 2'],
      planned: [50, 100],
      actual: [20, 80],
      details: [{ label: 'Week 1', planned: 50, actual: 20 }],
    };

    const result = ensureWeekZeroDataset(dataset);

    expect(result.labels[0]).toBe('Week 0');
    expect(result.planned[0]).toBe(0);
    expect(result.actual[0]).toBe(0);
    expect(result.details[0].label).toBe('Week 0');
    expect(result.details[0].planned).toBe(0);
  });

  it('prepends W0 for cost view including acSeries and metadata', () => {
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
    expect(result.labels[0]).toBe('W0');
    expect(result.acSeries[0]).toBe(0);
    expect(result.details.weeks[0].week_number).toBe(0);
    expect(result.details.actualWeeks[0].week_number).toBe(0);
  });

  it('keeps non-array details untouched when not cost view', () => {
    const obj = { foo: 'bar' };
    const result = prependZeroDetails(obj, 'Week 0', false);
    expect(result).toEqual(obj);
  });

  it('returns zeroed structure for createZeroWeekEntry', () => {
    const entry = createZeroWeekEntry();
    expect(entry.week_number).toBe(0);
    expect(entry.cumulative_percent).toBe(0);
    expect(entry.pekerjaan_breakdown).toEqual({});
  });
});
