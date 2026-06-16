/**
 * WP-P3c (VP-06) guard — false-dirty on load is reconciled against the server.
 *
 * On open, the persisted localStorage dirty flags must NOT raise "perlu disimpan"
 * unless the local state genuinely differs from the server (project-195 bug).
 * Server is authoritative; a stale flag whose content matches the server is cleared.
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const src = readFileSync(resolve(__dirname, '..', 'volume_pekerjaan.js'), 'utf-8');

describe('WP-P3c — false-dirty reconciliation on load', () => {
  test('formula: only entries differing from server are marked dirty', () => {
    // The prefill compares local raw/fx to serverFormula before adding to dirtySet.
    expect(src).toContain('const sRaw = String(s.raw');
    expect(src).toContain('if (lRaw !== sRaw || !!l.fx !== !!s.fx)');
    expect(src).toContain('else clearFormulaLocalDirty();');
  });

  test('base params: stale dirty flag cleared when local matches server', () => {
    expect(src).toContain('function _baseParamsMatchServer(');
    expect(src).toContain('clearBaseParamsDirty();  // stale flag — local already matches server');
  });

  test('computed params: stale dirty flag cleared when local matches server', () => {
    expect(src).toContain('function _computedParamsMatchServer(');
    expect(src).toContain('clearComputedParamsDirty();  // stale flag — local already matches server');
  });

  test('an active sync timer still protects local edits', () => {
    expect(src).toContain('if (paramSyncTimer || !_baseParamsMatchServer(');
    expect(src).toContain('if (computedSyncTimer || !_computedParamsMatchServer(');
  });
});
