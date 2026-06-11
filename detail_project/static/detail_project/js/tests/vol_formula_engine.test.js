/**
 * Unit Tests for vol_formula_engine.js
 *
 * Sprint 2.1: Comprehensive test suite for the formula evaluation engine.
 *
 * The engine is an IIFE that attaches to globalThis.VolFormula.
 * We load it by executing the script before tests.
 *
 * Run: npm run test:frontend -- vol_formula_engine.test.js
 */

import { describe, test, expect, beforeAll } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

// Load the IIFE engine by evaluating it in the global scope
beforeAll(() => {
    const enginePath = resolve(
        __dirname,
        '..',
        'vol_formula_engine.js'
    );
    const engineCode = readFileSync(enginePath, 'utf-8');
    // Execute in global scope so VolFormula attaches to globalThis
    const fn = new Function(engineCode);
    fn();
});

// Helper: shorthand for evaluate
function evaluate(expr, vars = {}, opts = {}) {
    return globalThis.VolFormula.evaluate(expr, vars, opts);
}

// ============================================================
// 1. BASIC LITERALS & ARITHMETIC
// ============================================================
describe('Basic Literals & Arithmetic', () => {
    test('plain number', () => {
        expect(evaluate('=42')).toBe(42);
    });

    test('decimal number', () => {
        expect(evaluate('=3.14')).toBeCloseTo(3.14);
    });

    test('negative number (unary minus)', () => {
        expect(evaluate('=-5')).toBe(-5);
    });

    test('addition', () => {
        expect(evaluate('=2 + 3')).toBe(5);
    });

    test('subtraction', () => {
        expect(evaluate('=10 - 4')).toBe(6);
    });

    test('multiplication', () => {
        expect(evaluate('=6 * 7')).toBe(42);
    });

    test('division', () => {
        expect(evaluate('=15 / 3')).toBe(5);
    });

    test('power operator', () => {
        expect(evaluate('=2 ^ 10')).toBe(1024);
    });

    test('operator precedence (* before +)', () => {
        expect(evaluate('=2 + 3 * 4')).toBe(14);
    });

    test('parentheses override precedence', () => {
        expect(evaluate('=(2 + 3) * 4')).toBe(20);
    });

    test('nested parentheses', () => {
        expect(evaluate('=((1 + 2) * (3 + 4))')).toBe(21);
    });

    test('complex expression', () => {
        expect(evaluate('=(10 + 5) * 2 - 3')).toBe(27);
    });

    test('expression without = prefix', () => {
        expect(evaluate('42')).toBe(42);
    });
});

// ============================================================
// 2. ID-ID LOCALE NUMBERS
// ============================================================
describe('Localized Number Parsing (id-ID)', () => {
    test('comma as decimal separator: 1000,25', () => {
        expect(evaluate('=1000,25')).toBeCloseTo(1000.25);
    });

    test('dot thousands + comma decimal: 1.000,25', () => {
        expect(evaluate('=1.000,25')).toBeCloseTo(1000.25);
    });

    test('underscore thousands: 1_000.25', () => {
        expect(evaluate('=1_000.25')).toBeCloseTo(1000.25);
    });
});

// ============================================================
// 3. VARIABLES
// ============================================================
describe('Variables', () => {
    test('single variable', () => {
        expect(evaluate('=bp_1', { bp_1: 10 })).toBe(10);
    });

    test('variable arithmetic', () => {
        expect(evaluate('=bp_1 * bp_2', { bp_1: 3, bp_2: 5 })).toBe(15);
    });

    test('case-insensitive variable lookup', () => {
        expect(evaluate('=BP_1 + bp_2', { bp_1: 10, bp_2: 20 })).toBe(30);
    });

    test('computed parameter (cp_N)', () => {
        expect(evaluate('=cp_1 + bp_1', { cp_1: 100, bp_1: 50 })).toBe(150);
    });

    test('built-in constant: pi', () => {
        expect(evaluate('=pi')).toBeCloseTo(Math.PI);
    });

    test('built-in constant: e', () => {
        expect(evaluate('=e')).toBeCloseTo(Math.E);
    });

    test('unknown variable throws', () => {
        expect(() => evaluate('=xyz_999')).toThrow(/tidak dikenal|unknown/i);
    });

    test('non-numeric variable throws', () => {
        expect(() => evaluate('=bp_1', { bp_1: 'abc' })).toThrow(/bukan angka/i);
    });
});

// ============================================================
// 4. FUNCTIONS
// ============================================================
describe('Functions', () => {
    test('sum()', () => {
        expect(evaluate('=sum(1, 2, 3)')).toBe(6);
    });

    test('min()', () => {
        expect(evaluate('=min(5, 2, 8)')).toBe(2);
    });

    test('max()', () => {
        expect(evaluate('=max(5, 2, 8)')).toBe(8);
    });

    test('avg()', () => {
        expect(evaluate('=avg(10, 20, 30)')).toBe(20);
    });

    test('abs()', () => {
        expect(evaluate('=abs(-42)')).toBe(42);
    });

    test('round() default (0 decimals)', () => {
        expect(evaluate('=round(3.7)')).toBe(4);
    });

    test('round() with decimals', () => {
        expect(evaluate('=round(3.14159, 2)')).toBeCloseTo(3.14);
    });

    test('ceil()', () => {
        expect(evaluate('=ceil(3.2)')).toBe(4);
    });

    test('floor()', () => {
        expect(evaluate('=floor(3.9)')).toBe(3);
    });

    test('pow()', () => {
        expect(evaluate('=pow(2, 3)')).toBe(8);
    });

    test('nested function calls', () => {
        expect(evaluate('=round(sum(1, 2, 3.7), 0)')).toBe(7);
    });

    test('case-insensitive function names', () => {
        expect(evaluate('=SUM(1, 2, 3)')).toBe(6);
        expect(evaluate('=Min(5, 1)')).toBe(1);
    });

    test('unknown function throws', () => {
        expect(() => evaluate('=unknown_func(1)')).toThrow(/tidak dikenal|unknown/i);
    });
});

// ============================================================
// 5. ERROR HANDLING
// ============================================================
describe('Error Handling', () => {
    test('division by zero throws', () => {
        expect(() => evaluate('=1 / 0')).toThrow(/pembagian|nol|zero/i);
    });

    test('empty expression throws', () => {
        expect(() => evaluate('=')).toThrow();
    });

    test('whitespace-only expression throws', () => {
        expect(() => evaluate('=   ')).toThrow();
    });

    test('null expression throws', () => {
        expect(() => evaluate(null)).toThrow(/kosong/i);
    });

    test('unbalanced parentheses throws', () => {
        expect(() => evaluate('=(1 + 2')).toThrow(/kurung/i);
    });

    test('missing operand throws', () => {
        expect(() => evaluate('=+')).toThrow();
    });

    test('min() without args throws', () => {
        expect(() => evaluate('=min()')).toThrow();
    });
});

// ============================================================
// 6. OPTIONS
// ============================================================
describe('Options', () => {
    test('clampMinZero clamps negative result to 0', () => {
        expect(evaluate('=1 - 10', {}, { clampMinZero: true })).toBe(0);
    });

    test('clampMinZero does not affect positive result', () => {
        expect(evaluate('=10 - 1', {}, { clampMinZero: true })).toBe(9);
    });
});

// ============================================================
// 7. REAL-WORLD FORMULA PATTERNS
// ============================================================
describe('Real-world Formula Patterns', () => {
    test('volume calculation: panjang * lebar * tinggi', () => {
        const vars = { bp_1: 10, bp_2: 5, bp_3: 3 };
        expect(evaluate('=bp_1 * bp_2 * bp_3', vars)).toBe(150);
    });

    test('circular area: pi * r^2', () => {
        const vars = { bp_1: 5 }; // radius = 5
        const result = evaluate('=pi * bp_1 ^ 2', vars);
        expect(result).toBeCloseTo(Math.PI * 25);
    });

    test('complex multi-operation formula', () => {
        const vars = { bp_1: 100, bp_2: 0.2, cp_1: 50 };
        // (100 * 0.2) + 50 = 70
        expect(evaluate('=(bp_1 * bp_2) + cp_1', vars)).toBe(70);
    });

    test('formula with round and sum', () => {
        const vars = { bp_1: 3.456, bp_2: 2.789 };
        const result = evaluate('=round(sum(bp_1, bp_2), 1)', vars);
        expect(result).toBeCloseTo(6.2);
    });
});
