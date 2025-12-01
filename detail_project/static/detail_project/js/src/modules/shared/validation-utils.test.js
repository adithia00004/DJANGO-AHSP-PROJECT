import { describe, it, expect } from 'vitest';

import {
  validateCellValue,
  validateTotalProgress,
} from './validation-utils.js';

describe('validation-utils', () => {
  describe('validateCellValue', () => {
    it('accepts numeric input within range', () => {
      const result = validateCellValue('45.34');
      expect(result.isValid).toBe(true);
      expect(result.value).toBeCloseTo(45.3, 1);
    });

    it('rejects numbers above max', () => {
      const result = validateCellValue(120);
      expect(result.isValid).toBe(false);
      expect(result.message).toContain('lebih dari 100');
      expect(result.value).toBe(100);
    });

    it('rejects non numeric input', () => {
      const result = validateCellValue('abc');
      expect(result.isValid).toBe(false);
      expect(result.message).toContain('angka');
    });
  });

  describe('validateTotalProgress', () => {
    it('returns info when total equals 100', () => {
      const result = validateTotalProgress([25, 25, 25, 25]);
      expect(result.isValid).toBe(true);
      expect(result.value).toBeCloseTo(100);
      expect(result.level).toBe('info');
    });

    it('returns error when total exceeds 100', () => {
      const result = validateTotalProgress([60, 50]);
      expect(result.isValid).toBe(false);
      expect(result.level).toBe('error');
      expect(result.message).toContain('melebihi 100');
    });

    it('returns warning when total is below 100', () => {
      const result = validateTotalProgress([10, 20]);
      expect(result.isValid).toBe(false);
      expect(result.level).toBe('warning');
      expect(result.message).toContain('kurang');
    });
  });
});
