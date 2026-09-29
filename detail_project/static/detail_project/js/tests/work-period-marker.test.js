import { describe, expect, it, vi } from 'vitest';
import {
  drawWorkPeriodEndMarker,
  findWorkPeriodEndMarker,
} from '../src/modules/shared/work-period-marker.js';

function fixture() {
  const startDate = new Date(2026, 8, 6);
  const endDate = new Date(2026, 8, 12);
  return {
    manager: {
      state: {
        workPeriodMeta: {
          contract_end: '2026-09-07',
          additional_end: '2026-09-20',
        },
      },
      currentColumns: [{
        id: 'col_week_2',
        meta: {
          timeColumn: true,
          columnMeta: {
            fieldId: 'col_week_2',
            isBoundaryWeek: true,
            startDate,
            endDate,
          },
        },
      }],
    },
    cellRects: [{ columnId: 'col_week_2', x: 100, width: 140 }],
  };
}

describe('work period end chart marker', () => {
  it('places the marker within the weekly column using the server contract date', () => {
    const { manager, cellRects } = fixture();
    const marker = findWorkPeriodEndMarker(manager, cellRects);
    expect(marker).toMatchObject({ columnId: 'col_week_2', x: 140, label: 'Akhir Waktu Kerja' });
  });

  it('does not draw when the project has no active additional period', () => {
    const { manager, cellRects } = fixture();
    manager.state.workPeriodMeta.additional_end = null;
    expect(findWorkPeriodEndMarker(manager, cellRects)).toBeNull();
  });

  it('draws a dashed vertical line in the chart canvas', () => {
    const { manager, cellRects } = fixture();
    const context = {
      canvas: { height: 200 },
      save: vi.fn(),
      restore: vi.fn(),
      setLineDash: vi.fn(),
      beginPath: vi.fn(),
      moveTo: vi.fn(),
      lineTo: vi.fn(),
      stroke: vi.fn(),
    };
    const marker = drawWorkPeriodEndMarker(context, manager, cellRects, {
      xOffset: 20,
      bottom: 180,
    });
    expect(marker.x).toBe(120);
    expect(context.setLineDash).toHaveBeenCalledWith([6, 4]);
    expect(context.moveTo).toHaveBeenCalledWith(120, 0);
    expect(context.lineTo).toHaveBeenCalledWith(120, 180);
    expect(context.stroke).toHaveBeenCalledOnce();
  });
});
