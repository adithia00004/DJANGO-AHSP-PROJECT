/**
 * WP-P8 guard — Rekap Kebutuhan presentation contract.
 *
 * Locks the active cleanup decisions:
 * - conversion profiles are server-authoritative; no stale hiConv/localStorage fallback;
 * - Tahapan is retired as a Rekap Kebutuhan page filter;
 * - legacy "month" value remains only as backend-compatible 4-week alias, while
 *   user-facing text says "Periode 4 Minggu".
 */
import { describe, expect, test } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const js = readFileSync(resolve(__dirname, '..', 'rekap_kebutuhan.js'), 'utf-8');
const tpl = readFileSync(
  resolve(__dirname, '..', '..', '..', '..', 'templates', 'detail_project', 'rekap_kebutuhan.html'),
  'utf-8'
);

describe('WP-P8 — Rekap Kebutuhan cleanup guards', () => {
  test('conversion display does not use stale browser conversion cache', () => {
    expect(js).not.toContain('hiConv:');
    expect(js).not.toContain('LS_CONV_PREFIX');
    expect(js).not.toContain('price_market');
    expect(js).not.toContain('falling back to localStorage');
  });

  test('page init no longer loads retired Tahapan filter', () => {
    expect(js).not.toContain('await loadTahapan();');
    expect(js).not.toContain('params.tahapan_id = currentFilter.tahapan_id');
  });

  test('4-week period is user-facing, while legacy month alias stays internal', () => {
    expect(js).toContain('Periode 4 Minggu');
    expect(tpl).toContain('Periode 4 Minggu');
    expect(tpl).not.toContain('Bulanan');
    expect(tpl).not.toContain('Bulan Tertentu');
  });
});
