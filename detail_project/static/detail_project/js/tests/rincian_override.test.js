/**
 * WP-P5 guard — Rincian AHSP override parser + reset-all + error surfacing.
 *
 * Source-grep guard (DOM-heavy, bootstrapped on a real page):
 *  - P5a/RA-04: percentage parser keeps a single dot as a decimal ("12.5"→12.5),
 *    no longer strips all dots (which turned 12.5 into 125);
 *  - P5d/RA-05: reset-all-overrides is wired to the (now enabled) Reset button;
 *  - P5f/RA-10: saveOverride throws the actual server message, not a generic string.
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const src = readFileSync(resolve(__dirname, '..', 'rincian_ahsp.js'), 'utf-8');

describe('WP-P5a — override percentage parser (RA-04)', () => {
  test('parsePctUI treats a single dot as a decimal point', () => {
    // The fixed body normalizes comma→dot and validates, instead of stripping dots.
    expect(src).toContain("s = s.replace(',', '.');");
    expect(src).toContain("/^-?\\d*\\.?\\d+$/.test(s)");
  });

  test('parsePctUI no longer strips all dots before parsing', () => {
    // The old bug line must be gone from the percentage parser.
    expect(src).not.toContain("s = s.replace(/\\./g, '').replace(',', '.'); // \"12.500,5\" -> \"12500.5\"");
  });
});

describe('WP-P5d — reset-all overrides (RA-05)', () => {
  test('reads the reset-all endpoint and wires the Reset button', () => {
    expect(src).toContain('ROOT.dataset.epResetAllOverrides');
    expect(src).toContain("ROOT.querySelector('#rk-btn-reset')");
  });

  test('confirms before resetting and reloads after', () => {
    expect(src).toMatch(/raConfirm\([\s\S]*Reset SEMUA override/);
    expect(src).toContain('reset_count');
  });
});

describe('WP-P5f — surface backend override error (RA-10)', () => {
  test('saveOverride throws the server-provided message', () => {
    expect(src).toContain('j.errors[0].message');
    expect(src).not.toContain("throw new Error('save override fail')");
  });
});
