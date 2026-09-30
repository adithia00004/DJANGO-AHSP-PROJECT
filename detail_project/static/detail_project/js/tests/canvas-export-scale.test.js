import { describe, expect, it } from 'vitest';
import {
  getCanvasPixelSize,
  getSafeCanvasScale,
} from '../src/export/core/canvas-export-scale.js';

describe('PNG export canvas scale', () => {
  it('keeps ordinary Kurva S PNGs at three times the logical pixel size', () => {
    const scale = getSafeCanvasScale(1200, 600, 3);
    expect(scale).toBe(3);
    expect(getCanvasPixelSize(1200, 600, scale)).toEqual({
      width: 3600,
      height: 1800,
      scale: 3,
    });
  });

  it('reduces scale for very large images instead of exceeding canvas limits', () => {
    const scale = getSafeCanvasScale(14000, 4000, 3);
    const output = getCanvasPixelSize(14000, 4000, scale);
    expect(scale).toBeLessThan(3);
    expect(output.width).toBeLessThanOrEqual(16384);
    expect(output.height).toBeLessThanOrEqual(16384);
    expect(output.width * output.height).toBeLessThanOrEqual(64 * 1024 * 1024);
  });

  it('can downscale an already oversized logical canvas to stay within browser limits', () => {
    const scale = getSafeCanvasScale(20000, 20000, 3);
    const output = getCanvasPixelSize(20000, 20000, scale);
    expect(scale).toBeLessThan(1);
    expect(output.width).toBeLessThanOrEqual(16384);
    expect(output.height).toBeLessThanOrEqual(16384);
    expect(output.width * output.height).toBeLessThanOrEqual(64 * 1024 * 1024);
  });

  it('falls back to one-to-one dimensions for invalid scale inputs', () => {
    expect(getSafeCanvasScale(0, 600, 3)).toBe(1);
    expect(getCanvasPixelSize(1200, 600, Number.NaN)).toEqual({
      width: 1200,
      height: 600,
      scale: 1,
    });
  });
});
