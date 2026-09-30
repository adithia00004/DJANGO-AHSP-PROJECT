import { afterEach, describe, expect, it, vi } from 'vitest';

import JadwalKegiatanApp from '../src/jadwal_kegiatan_app.js';
import { progressToY } from '../src/modules/shared/chart-png-layout.js';

afterEach(() => vi.restoreAllMocks());

describe('Kurva S PNG follows the preview', () => {
  it('draws the preview weighted values while retaining 3x export resolution', async () => {
    const context = Object.fromEntries([
      'scale', 'fillRect', 'fillText', 'strokeRect', 'save', 'setLineDash',
      'beginPath', 'moveTo', 'lineTo', 'stroke', 'restore', 'arc', 'fill',
    ].map((method) => [method, vi.fn()]));
    context.measureText = (text) => ({ width: String(text).length * 5 });

    const canvas = {
      getContext: () => context,
      toDataURL: vi.fn(() => 'data:image/png;base64,test'),
      width: 0,
      height: 0,
    };
    const createElement = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tag) => (
      tag === 'canvas' ? canvas : createElement(tag)
    ));

    const app = Object.create(JadwalKegiatanApp.prototype);
    app.unifiedManager = {
      overlays: {
        kurva: {
          curveData: {
            // Weighted project progress, as already computed for the preview.
            planned: [
              { columnId: 'col_1', weekNumber: 1, cumulativeProgress: 10, label: 'W1' },
              { columnId: 'col_2', weekNumber: 2, cumulativeProgress: 55, label: 'W2' },
            ],
            actual: [],
          },
        },
      },
    };

    const png = await app._renderKurvaSFullImage({
      hierarchyRows: [{ id: 1, type: 'pekerjaan', name: 'Pekerjaan A' }],
      weekColumns: [{ week: 1 }, { week: 2 }],
      plannedProgress: { 1: { 1: 100, 2: 50 } },
    });

    expect(png).toBe('data:image/png;base64,test');
    expect([canvas.width, canvas.height]).toEqual([444 * 3, 350 * 3]);
    expect(context.scale).toHaveBeenCalledWith(3, 3);
    expect(context.lineTo).toHaveBeenCalledWith(350, progressToY(10, 90, 240));
    expect(context.lineTo).toHaveBeenCalledWith(400, progressToY(55, 90, 240));
  });
});
