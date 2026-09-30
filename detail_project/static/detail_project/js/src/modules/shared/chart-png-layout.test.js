import { describe, expect, it } from 'vitest';

import {
  KURVA_PNG_MARGIN_Y,
  aggregateGanttToMonths,
  buildKurvaSPngSeries,
  progressToY,
  wrapTextToWidth,
} from './chart-png-layout.js';
import { KurvaSCanvasOverlay } from '../kurva-s/KurvaSCanvasOverlay.js';

// 1 character = 5px, enough to reason about widths without a real canvas.
const measure = (text) => text.length * 5;

describe('wrapTextToWidth', () => {
  it('keeps short text on one line', () => {
    expect(wrapTextToWidth('Galian tanah', 100, measure)).toEqual(['Galian tanah']);
  });

  it('wraps on words so no line is wider than the column', () => {
    const lines = wrapTextToWidth('Pekerjaan pasangan batu kali campuran', 60, measure);
    expect(lines.length).toBeGreaterThan(1);
    lines.forEach((line) => expect(measure(line)).toBeLessThanOrEqual(60));
    expect(lines.join(' ')).toBe('Pekerjaan pasangan batu kali campuran');
  });

  it('breaks a single word that is longer than the column instead of cutting it off', () => {
    const lines = wrapTextToWidth('Pembesian-kolom-struktur-utama', 50, measure);
    lines.forEach((line) => expect(measure(line)).toBeLessThanOrEqual(50));
    expect(lines.join('')).toBe('Pembesian-kolom-struktur-utama');
  });

  it('returns one empty line for empty text', () => {
    expect(wrapTextToWidth('', 100, measure)).toEqual(['']);
    expect(wrapTextToWidth(null, 100, measure)).toEqual(['']);
  });
});

describe('buildKurvaSPngSeries', () => {
  it('uses the overlay curve values as-is and drops the week-0 origin point', () => {
    const series = buildKurvaSPngSeries({
      planned: [
        { columnId: 'week_0', weekNumber: 0, cumulativeProgress: 0, label: 'W0' },
        { columnId: 'col_1', weekNumber: 1, cumulativeProgress: 12.5, label: 'W1' },
        { columnId: 'col_2', weekNumber: 2, cumulativeProgress: 60, label: 'W2' },
      ],
      actual: [
        { columnId: 'week_0', weekNumber: 0, cumulativeProgress: 0, label: 'W0' },
        { columnId: 'col_1', weekNumber: 1, cumulativeProgress: 8, label: 'W1' },
      ],
    });

    expect(series.columns.map((c) => c.label)).toEqual(['W1', 'W2']);
    expect(series.planned).toEqual([12.5, 60]);
    // No actual value yet for W2: the actual line stops at W1, not at 0%.
    expect(series.actual).toEqual([8, null]);
  });

  it('keeps monthly columns from the overlay (M1, M2...)', () => {
    const series = buildKurvaSPngSeries({
      planned: [
        { columnId: 'month_1', weekNumber: 4, cumulativeProgress: 30, label: 'M1' },
        { columnId: 'month_2', weekNumber: 8, cumulativeProgress: 100, label: 'M2' },
      ],
      actual: [],
    });
    expect(series.columns.map((c) => c.label)).toEqual(['M1', 'M2']);
    expect(series.planned).toEqual([30, 100]);
    expect(series.actual).toEqual([null, null]);
  });

  it('keeps the first monthly point when it is labelled week 0 by the preview', () => {
    const series = buildKurvaSPngSeries({
      planned: [{ columnId: 'month_1', weekNumber: 0, cumulativeProgress: 15, label: 'M1' }],
      actual: [],
    });
    expect(series.columns.map((column) => column.label)).toEqual(['M1']);
    expect(series.planned).toEqual([15]);
  });

  it('returns no columns when the overlay has no curve data', () => {
    expect(buildKurvaSPngSeries(undefined).columns).toEqual([]);
  });
});

describe('progressToY', () => {
  it('maps 0% and 100% to the same margins as the web overlay', () => {
    const top = 90;
    const height = 400;
    expect(progressToY(0, top, height)).toBe(top + height - KURVA_PNG_MARGIN_Y);
    expect(progressToY(100, top, height)).toBe(top + KURVA_PNG_MARGIN_Y);
    expect(progressToY(50, top, height)).toBe(top + height / 2);
  });

  it('clamps values outside 0-100 like the web overlay', () => {
    expect(progressToY(130, 0, 400)).toBe(progressToY(100, 0, 400));
    expect(progressToY(-5, 0, 400)).toBe(progressToY(0, 0, 400));
  });

  it('places weighted preview points at the same PNG percentages and heights', () => {
    // Two tasks with 10% and 90% cost weights: the first reaches 100% in W1,
    // the second reaches 50% in W2, so project progress is 10%, then 55%.
    const previewData = [
      { columnId: 'col_1', weekNumber: 1, cumulativeProgress: 10 },
      { columnId: 'col_2', weekNumber: 2, cumulativeProgress: 55 },
    ];
    const overlay = Object.create(KurvaSCanvasOverlay.prototype);
    overlay._log = () => {};
    overlay.gridBounds = { gridLeft: 200, gridHeight: 400 };
    const previewPoints = overlay._mapDataToCanvasPoints([
      { columnId: 'col_1', x: 200, width: 50 },
      { columnId: 'col_2', x: 250, width: 50 },
    ], previewData);
    const pngSeries = buildKurvaSPngSeries({ planned: previewData, actual: [] });

    expect(pngSeries.planned).toEqual([10, 55]);
    expect(previewPoints.map((point) => point.x)).toEqual([0, 50, 100]);
    expect(previewPoints.map((point) => point.y)).toEqual([
      progressToY(0, 0, 400),
      progressToY(pngSeries.planned[0], 0, 400),
      progressToY(pngSeries.planned[1], 0, 400),
    ]);
  });
});

describe('aggregateGanttToMonths', () => {
  it('groups weeks into 4-week months like the web monthly Gantt', () => {
    const columns = [1, 2, 3, 4, 5, 6, 7].map((week) => ({ week }));
    const result = aggregateGanttToMonths(
      columns,
      { 10: { 2: 40, 6: 60 } },
      { 10: { 7: 25 }, 11: { 1: 0 } },
    );
    expect(result.columns).toEqual([{ week: 1, label: 'M1' }, { week: 2, label: 'M2' }]);
    expect(result.planned).toEqual({ 10: { 1: 40, 2: 60 } });
    // Zero values draw no bar.
    expect(result.actual).toEqual({ 10: { 2: 25 } });
  });
});
