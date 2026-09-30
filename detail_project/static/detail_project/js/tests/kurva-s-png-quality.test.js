import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const SRC = resolve(__dirname, '..', 'src');
const renderer = readFileSync(resolve(SRC, 'export/core/kurva-s-renderer.js'), 'utf-8');
const app = readFileSync(resolve(SRC, 'jadwal_kegiatan_app.js'), 'utf-8');

describe('Kurva S PNG export resolution', () => {
  it('renders the offscreen uPlot chart at target pixels before encoding PNG', () => {
    expect(renderer).toContain('getSafeCanvasScale(width, height, dpi / BASE_DPI)');
    expect(renderer).toContain('width: physicalWidth');
    expect(renderer).toContain('height: physicalHeight');
    expect(renderer).toContain('ctx.drawImage(canvas, 0, 0, canvas.width, canvas.height, 0, 0, physicalWidth, physicalHeight)');
    expect(renderer).not.toContain('ctx.scale(SCALE, SCALE)');
  });

  it('renders the downloadable full Kurva S PNG with an adaptive high-resolution canvas', () => {
    expect(app).toContain('getSafeCanvasScale(canvasWidth, canvasHeight, 3)');
    expect(app).toContain('const pixelSize = getCanvasPixelSize(canvasWidth, canvasHeight, exportScale)');
    expect(app).toContain('ctx.scale(exportScale, exportScale)');
  });
});
