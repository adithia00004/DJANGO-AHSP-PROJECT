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

  it('applies server work-period metadata to virtual weekly columns', () => {
    const state = {
      timeScale: 'weekly',
      tahapanList: [],
      projectStart: '2026-09-06',
      projectEnd: '2026-09-20',
      weekStartDay: 0,
      weekEndDay: 6,
      contractEndDate: '2026-09-07',
      workPeriodMeta: {
        contract_end: '2026-09-07',
        additional_start: '2026-09-08',
        additional_end: '2026-09-20',
        contract_boundary_week: 2,
        extension_week_numbers: [3],
      },
    };

    const columns = new TimeColumnGenerator(state).generate();

    expect(columns).toHaveLength(3);
    expect(columns[1]).toMatchObject({
      weekNumber: 2,
      isBoundaryWeek: true,
      isExtensionWeek: false,
      workEndDate: '2026-09-07',
    });
    expect(columns[2]).toMatchObject({
      weekNumber: 3,
      isBoundaryWeek: false,
      isExtensionWeek: true,
      containsAdditionalWork: true,
    });
  });

  it('uses server markers and date-only local dates for persisted weekly stages', () => {
    const state = {
      timeScale: 'weekly',
      projectStart: '2026-09-06',
      projectEnd: '2026-09-20',
      weekEndDay: 6,
      workPeriodMeta: {
        contract_end: '2026-09-07',
        additional_end: '2026-09-20',
      },
      tahapanList: [{
        tahapan_id: 22,
        nama: 'Week 2',
        urutan: 1,
        generation_mode: 'weekly',
        is_auto_generated: true,
        tanggal_mulai: '2026-09-07',
        tanggal_selesai: '2026-09-13',
        week_number: 2,
        is_boundary_week: true,
        is_extension_week: false,
        work_end_date: '2026-09-07',
        contains_additional_period: true,
      }],
    };

    const [column] = new TimeColumnGenerator(state).generate();
    expect(localDateParts(column.startDate)).toEqual([2026, 9, 7]);
    expect(localDateParts(column.endDate)).toEqual([2026, 9, 13]);
    expect(column).toMatchObject({
      weekNumber: 2,
      isBoundaryWeek: true,
      isExtensionWeek: false,
      containsAdditionalWork: true,
    });
  });
});
