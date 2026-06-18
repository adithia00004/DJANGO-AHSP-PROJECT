/**
 * WP-P3c / UF-014 guard: stale localStorage dirty flags are reconciled against
 * the server on page load.
 *
 * Server state is authoritative when the Volume page opens. localStorage is
 * allowed to protect only an active in-session autosave draft, not a persisted
 * dirty flag left by an older browser session.
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const src = readFileSync(resolve(__dirname, '..', 'volume_pekerjaan.js'), 'utf-8');

describe('WP-P3c / UF-014 - server-authoritative parameter load', () => {
  test('formula: only entries differing from server are marked dirty', () => {
    // The prefill compares local raw/fx to serverFormula before adding to dirtySet.
    expect(src).toContain('const sRaw = String(s.raw');
    expect(src).toContain('if (lRaw !== sRaw || !!l.fx !== !!s.fx)');
    expect(src).toContain('else clearFormulaLocalDirty();');
  });

  test('base and computed params are bootstrapped from the server', () => {
    expect(src).toContain('volume_list + formula_state + parameters +');
    expect(src).toContain('VP_BOOTSTRAP?.parameters');
    expect(src).toContain('VP_BOOTSTRAP?.computed_parameters');
    expect(src).toContain('loadParamsFromServer({ data: VP_BOOTSTRAP.parameters });');
    expect(src).toContain('loadComputedParamsFromServer({ data: VP_BOOTSTRAP.computed_parameters });');
  });

  test('persisted dirty flags are cleared instead of blocking server load', () => {
    expect(src).toContain('function _baseParamsMatchServer(');
    expect(src).toContain('function _computedParamsMatchServer(');
    expect(src).toContain('clearBaseParamsDirty();  // stale persisted flag cannot block server on load');
    expect(src).toContain('clearComputedParamsDirty();  // stale persisted flag cannot block server on load');
  });

  test('only active autosave timers protect real local drafts', () => {
    expect(src).toContain('function hasBaseParamContent(');
    expect(src).toContain('function hasComputedParamContent(');
    expect(src).toContain('if (paramSyncTimer && hasLocalDraft && !_baseParamsMatchServer(');
    expect(src).toContain('if (computedSyncTimer && hasLocalDraft && !_computedParamsMatchServer(');
  });
});
