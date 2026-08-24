import { describe, expect, it } from 'vitest';

import { TimeColumnGenerator } from '../src/modules/core/time-column-generator.js';

function localDateParts(value) {
  return [value.getFullYear(), value.getMonth() + 1, value.getDate()];
}

describe('TimeColumnGenerator without persisted tahapan', () => {
  it('creates editable weekly columns from the project date range', () => {
    const state = {
      timeScale: 'weekly',
      tahapanList: [],
      projectStart: '2026-07-31',
      projectEnd: '2026-12-31',
      weekStartDay: 0,
      weekEndDay: 6,
    };

    const columns = new TimeColumnGenerator(state).generate();

    expect(columns).toHaveLength(23);
    expect(columns[0]).toMatchObject({
      fieldId: 'col_virtual_week_1',
      label: 'Week 1',
      generationMode: 'weekly',
      weekNumber: 1,
      isVirtual: true,
      tahapanId: null,
    });
    expect(localDateParts(columns[0].startDate)).toEqual([2026, 7, 31]);
    expect(localDateParts(columns[0].endDate)).toEqual([2026, 8, 2]);
    expect(localDateParts(columns[22].startDate)).toEqual([2026, 12, 28]);
    expect(localDateParts(columns[22].endDate)).toEqual([2026, 12, 31]);
  });

  it('does not create virtual columns without a complete project range', () => {
    const state = {
      timeScale: 'weekly',
      tahapanList: [],
      projectStart: '2026-07-31',
      projectEnd: null,
      weekStartDay: 0,
      weekEndDay: 6,
    };

    expect(new TimeColumnGenerator(state).generate()).toEqual([]);
  });
});
