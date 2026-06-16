/**
 * WP-P3b guard — Volume autosave consolidation + save-on-leave.
 *
 * Locks: the three autosave subsystems share ONE 5-minute cadence (no per-second
 * background syncs), and a save-on-leave flush (visibilitychange/pagehide,
 * keepalive) is the durability net for the relaxed window.
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const src = readFileSync(resolve(__dirname, '..', 'volume_pekerjaan.js'), 'utf-8');

describe('WP-P3b — Volume autosave cadence + save-on-leave', () => {
  test('formula & parameter sync share the 5-minute autosave cadence', () => {
    expect(src).toContain('const FORMULA_SYNC_DELAY = AUTOSAVE_MS');
    expect(src).toContain('const PARAM_SYNC_DELAY = AUTOSAVE_MS');
    expect(src).toContain('DEFAULT_AUTOSAVE_MS = 5 * 60 * 1000');
  });

  test('jpost supports keepalive for unload-surviving flushes', () => {
    expect(src).toContain('jpost(url, data, opts = {})');
    expect(src).toContain('keepalive: !!opts.keepalive');
  });

  test('save-on-leave flush is bound to visibilitychange and pagehide', () => {
    expect(src).toContain('function flushSavesOnLeave()');
    expect(src).toMatch(/visibilitychange[\s\S]*?flushSavesOnLeave/);
    expect(src).toContain("addEventListener('pagehide'");
  });

  test('leave flush sends keepalive saves for pending changes', () => {
    expect(src).toContain("saveDirty({ reason: 'leave', keepalive: true })");
    expect(src).toContain('syncParamsToServer({ keepalive: true })');
    expect(src).toContain('syncComputedParamsToServer({ keepalive: true })');
  });
});
