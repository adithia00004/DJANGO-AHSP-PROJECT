/**
 * RR-22 a11y guard for the Rekap RAB page.
 *  - the Subtotal and Compact (density) toggles are stateful buttons, so they
 *    must expose aria-pressed (not only a visual `.active` class);
 *  - the JS keeps aria-pressed in sync on click AND on init/restore.
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const tpl = readFileSync(
  resolve(__dirname, '..', '..', '..', '..', 'templates', 'detail_project', 'rekap_rab.html'),
  'utf-8',
);
const js = readFileSync(resolve(__dirname, '..', 'rekap_rab.js'), 'utf-8');

describe('Rekap RAB a11y - view-mode toggles (RR-22)', () => {
  test('template toggles declare an initial aria-pressed', () => {
    expect(tpl).toMatch(/id="btn-subtotal"[\s\S]*?aria-pressed="false"/);
    expect(tpl).toMatch(/id="btn-density"[\s\S]*?aria-pressed="false"/);
  });

  test('subtotal toggle syncs aria-pressed on click and init', () => {
    // every place that flips the `.active` class on the subtotal button must
    // also write aria-pressed (click handler + init/restore path).
    const activeToggles = js.match(/btnSubtotal\??\.classList\.toggle\('active'/g) || [];
    const pressedWrites = js.match(/btnSubtotal\??\.setAttribute\('aria-pressed'/g) || [];
    expect(activeToggles.length).toBeGreaterThanOrEqual(2);
    expect(pressedWrites.length).toBeGreaterThanOrEqual(activeToggles.length);
  });

  test('density toggle syncs aria-pressed from its single source of truth', () => {
    // applyDenseUI() is called on both click and init, so one write there covers both.
    expect(js).toContain("btnDensity?.setAttribute('aria-pressed', String(dense))");
  });
});
