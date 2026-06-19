/**
 * VP-A1 guard — strict id-ID quantity parsing.
 *
 * The old `canonFromUIQty` heuristic treated `^\d{1,3}[.,]\d{3}$` as a thousands
 * group, so "0,123" / "0.123" became 123 — a silent 1000x volume error. The fix
 * makes comma ALWAYS the decimal separator and lets the dot form thousands groups
 * only with a non-zero 3-digit lead (matching the app's own id-ID display).
 *
 * Behavioural coverage runs against the twin copy exposed by
 * volume_numeric_patch.js (window.VolumeNumeric.getCanonValue); a source-grep
 * parity guard pins the primary copy in volume_pekerjaan.js (which drives the
 * value actually saved).
 */
import { describe, test, expect, beforeAll } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const patchSrc = readFileSync(resolve(__dirname, '..', 'volume_numeric_patch.js'), 'utf-8');
const mainSrc = readFileSync(resolve(__dirname, '..', 'volume_pekerjaan.js'), 'utf-8');

describe('VP-A1 behavioural - volume_numeric_patch.js getCanonValue', () => {
  beforeAll(() => {
    // Stub the Numeric lib with identity enforceDp so we assert the raw canon.
    window.Numeric = { enforceDp: (s) => String(s), formatForUI: (s) => String(s) };
    document.body.innerHTML = '<div id="vol-app"></div>';
    // Execute the IIFE patch against the current window/document.
    // eslint-disable-next-line no-new-func
    new Function(patchSrc)();
  });

  const canon = (v) => window.VolumeNumeric.getCanonValue({ value: v });

  test('comma is always the decimal separator (id-ID)', () => {
    expect(canon('0,123')).toBe('0.123');   // was 123 (the 1000x bug)
    expect(canon('1,234')).toBe('1.234');
    expect(canon('2,5')).toBe('2.5');
    expect(canon('12,345')).toBe('12.345');
  });

  test('dot forms thousands groups only with a non-zero 3-digit lead', () => {
    expect(canon('1.234')).toBe('1234');
    expect(canon('12.345.678')).toBe('12345678');
    expect(canon('0.123')).toBe('0.123');       // leading zero -> decimal, not 123
    expect(canon('1.25')).toBe('1.25');          // 2 digits -> decimal
    expect(canon('1234.567')).toBe('1234.567');  // 4-digit lead -> not grouping
  });

  test('mixed notation: the last separator is the decimal', () => {
    expect(canon('1.234,5')).toBe('1234.5');     // id-ID
    expect(canon('1,234.56')).toBe('1234.56');   // US paste still parses
  });

  test('plain integers, formulas and invalid input', () => {
    expect(canon('1234')).toBe('1234');
    expect(canon('1,234,567')).toBe('');   // multi-comma decimal = malformed
    expect(canon('abc')).toBe('');
    expect(canon('=bp_1*2')).toBe('');     // formula is not coerced to a number
  });
});

describe('VP-A1 parity - volume_pekerjaan.js canonFromUIQty stays strict id-ID', () => {
  test('comma-only branch maps to decimal (no thousands collapse)', () => {
    expect(mainSrc).toContain("} else if (hasComma) {");
    expect(mainSrc).toMatch(/comma-only = decimal separator[\s\S]*s = s\.replace\(\/,\/g, '\.'\);/);
    // The old comma thousands-grouping heuristic must be gone.
    expect(mainSrc).not.toMatch(/commaGrouping\s*=\s*\/\^\\d\{1,3\}/);
  });

  test('dot grouping requires a non-zero 3-digit lead', () => {
    expect(mainSrc).toContain('/^[1-9]\\d{0,2}(\\.\\d{3})+$/');
  });
});
