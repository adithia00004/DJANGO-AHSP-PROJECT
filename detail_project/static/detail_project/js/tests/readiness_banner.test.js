/* WP-B4 inc-3 — readiness banner builder behaviour tests (happy-dom).
   Real DOM/string-behaviour tests of the production module, not source grep. */
import { describe, expect, test } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';
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

  test('renders jadwal-derived signals (inc-4a)', () => {
    const html = buildReadinessBannerHTML({
      allocation_without_volume: [{ kode: 'P-A' }],
      incomplete_planned_allocation: [{ kode: 'P-B' }, { kode: 'P-C' }],
      timeline_stale: true,
    });
    expect(html).toContain('dijadwalkan tanpa volume');
    expect(html).toContain('jadwalnya belum 100%');
    expect(html).toContain('tidak sesuai rentang tanggal proyek');
    expect(html).toContain('P-A');
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

// WP-B4 inc-3 — consumer wiring guard (display-only, server-authoritative).
// Each readiness consumer must (a) read readiness from the server response and
// (b) render via the shared ReadinessBanner module — never recompute. Grows as
// the fan-out adds consumers.
describe('readiness consumer wiring', () => {
  const read = (rel) => readFileSync(resolve(__dirname, '..', rel), 'utf-8');
  const consumers = [
    { file: 'rekap_rab.js', readinessField: 'rRes.data.readiness' },
    { file: 'rincian_ahsp.js', readinessField: 'j.readiness' },
    { file: 'template_ahsp.js', readinessField: 'j.readiness' },
  ];
  for (const { file, readinessField } of consumers) {
    test(`${file} renders server readiness via ReadinessBanner (no recompute)`, () => {
      const src = read(file);
      expect(src).toContain('ReadinessBanner');
      expect(src).toContain('renderReadiness(');
      expect(src).toContain(readinessField);
    });
  }

  test('Template AHSP refreshes readiness after save and reset mutations', () => {
    const src = read('template_ahsp.js');
    expect(src.match(/refreshReadiness\(\);/g)?.length || 0).toBeGreaterThanOrEqual(3);
    expect(src).toContain('Reset-to-reference rebuilds raw/expanded detail');
  });
});
