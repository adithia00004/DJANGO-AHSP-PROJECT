/* WP-B4 inc-3 — readiness banner builder behaviour tests (happy-dom).
   Real DOM/string-behaviour tests of the production module, not source grep. */
import { describe, expect, test } from 'vitest';
import '../shared/readiness_banner.js';

const { buildReadinessBannerHTML } = globalThis.ReadinessBanner;

describe('buildReadinessBannerHTML', () => {
  test('returns null for empty / clean readiness (no false "all clear")', () => {
    expect(buildReadinessBannerHTML(null)).toBeNull();
    expect(buildReadinessBannerHTML({})).toBeNull();
    expect(
      buildReadinessBannerHTML({
        missing_price: [],
        missing_volume: [],
        expansion_not_ready: [],
        invalid_coefficient: [],
      }),
    ).toBeNull();
  });

  test('escapes dynamic codes (XSS-safe)', () => {
    const html = buildReadinessBannerHTML({
      missing_price: [{ kode: '<img src=x onerror=alert(1)>' }],
    });
    expect(html).toBeTruthy();
    expect(html).not.toContain('<img src=x');
    expect(html).toContain('&lt;img src=x onerror=alert(1)&gt;');
  });

  test('renders a warning line per live signal with counts', () => {
    const html = buildReadinessBannerHTML({
      missing_price: [{ kode: 'BHN-1' }, { kode: 'BHN-2' }],
      missing_volume: [{ kode: 'P-1' }],
      expansion_not_ready: [{ kode: 'P-2' }],
      invalid_coefficient: [{ kode: 'P-3' }],
    });
    expect(html).toContain('harga item belum diisi');
    expect(html).toContain('pekerjaan belum punya volume');
    expect(html).toContain('belum sinkron dengan hasil ekspansi');
    expect(html).toContain('koefisien tidak valid');
    expect(html).toContain('<strong>2</strong>');
  });

  test('ignores pending jadwal signals — never treats null as done or clear', () => {
    // Only pending signals present (all live arrays empty) → no banner, and no
    // positive "ready/complete" text is ever emitted.
    const html = buildReadinessBannerHTML({
      missing_price: [],
      missing_volume: [],
      expansion_not_ready: [],
      invalid_coefficient: [],
      incomplete_planned_allocation: null,
      allocation_without_volume: null,
      timeline_stale: null,
      pending_signals: ['timeline_stale'],
    });
    expect(html).toBeNull();

    // A live problem still warns regardless of pending being null.
    const withProblem = buildReadinessBannerHTML({
      missing_price: [{ kode: 'BHN-1' }],
      timeline_stale: null,
    });
    expect(withProblem).toContain('belum diisi');
    expect(withProblem).not.toMatch(/siap|lengkap dan|semua data lengkap|all clear/i);
  });

  test('truncates long code lists with an ellipsis', () => {
    const many = Array.from({ length: 12 }, (_, i) => ({ kode: `K-${i}` }));
    const html = buildReadinessBannerHTML({ missing_price: many });
    expect(html).toContain('…');
    expect(html).not.toContain('K-9'); // beyond the max=8 window
  });
});
