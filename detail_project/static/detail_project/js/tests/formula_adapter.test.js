import { describe, test, expect, beforeAll } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

beforeAll(() => {
    const enginePath = resolve(__dirname, '..', 'vol_formula_engine.js');
    const adapterPath = resolve(__dirname, '..', 'shared', 'formula_adapter.js');
    const engineCode = readFileSync(enginePath, 'utf-8');
    const adapterCode = readFileSync(adapterPath, 'utf-8');

    const loadEngine = new Function(engineCode);
    loadEngine();
    const loadAdapter = new Function(adapterCode);
    loadAdapter();
});

describe('FormulaAdapter.evaluate', () => {
    test('evaluates basic arithmetic operators (+ - * / ^)', () => {
        const range = { min: -999999, max: 999999 };

        expect(globalThis.FormulaAdapter.evaluate('=2+3', {}, range)).toEqual({
            ok: true,
            value: 5,
        });
        expect(globalThis.FormulaAdapter.evaluate('=10-4', {}, range)).toEqual({
            ok: true,
            value: 6,
        });
        expect(globalThis.FormulaAdapter.evaluate('=6*7', {}, range)).toEqual({
            ok: true,
            value: 42,
        });
        expect(globalThis.FormulaAdapter.evaluate('=15/3', {}, range)).toEqual({
            ok: true,
            value: 5,
        });
        expect(globalThis.FormulaAdapter.evaluate('=2^5', {}, range)).toEqual({
            ok: true,
            value: 32,
        });
    });

    test('evaluates bp_* and cp_* variables', () => {
        const snapshot = { bp_1: 10, bp_2: 5, cp_1: 3 };
        const result = globalThis.FormulaAdapter.evaluate('=bp_1 + bp_2 * cp_1', snapshot, {
            min: -999999,
            max: 999999,
        });
        expect(result.ok).toBe(true);
        expect(result.value).toBe(25);
    });

    test('returns out_of_range when result exceeds koef bounds', () => {
        const result = globalThis.FormulaAdapter.evaluate('=bp_1*2', { bp_1: 10 }, {
            min: 0.000001,
            max: 5,
        });
        expect(result.ok).toBe(false);
        expect(result.code).toBe('out_of_range');
        expect(String(result.error || '')).toMatch(/di luar range/i);
    });

    test('returns missing_identifier when variable is not found', () => {
        const result = globalThis.FormulaAdapter.evaluate('=bp_999+1', { bp_1: 2 }, {
            min: -999999,
            max: 999999,
        });
        expect(result.ok).toBe(false);
        expect(result.code).toBe('missing_identifier');
        expect(String(result.error || '')).toMatch(/variabel|identifier|unknown/i);
    });
});
