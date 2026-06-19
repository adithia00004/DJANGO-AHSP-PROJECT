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
const templateSrc = readFileSync(
  resolve(__dirname, '..', '..', '..', '..', 'templates', 'detail_project', 'volume_pekerjaan.html'),
  'utf-8',
);

describe('WP-P3c / UF-014 - server-authoritative parameter load', () => {
  test('persisted formula dirty flags are cleared when server formula loads', () => {
    expect(src).toContain('const localFormula = serverFormula ? {} : loadFormulas();');
    expect(src).toContain('server-loaded formulas into fake unsaved edits');
    expect(src).toContain('formulaDirtySet.clear();');
    expect(src).toContain('clearFormulaLocalDirty();');
  });

  test('base and computed params are bootstrapped from the server', () => {
    expect(src).toContain('volume_list + formula_state + parameters +');
    expect(src).toContain('VP_BOOTSTRAP?.parameters');
    expect(src).toContain('VP_BOOTSTRAP?.computed_parameters');
    expect(src).toContain('initialHydrationTasks.push(loadParamsFromServer({ data: VP_BOOTSTRAP.parameters }));');
    expect(src).toContain('initialHydrationTasks.push(loadComputedParamsFromServer({ data: VP_BOOTSTRAP.computed_parameters }));');
  });

  test('volume formula prefill runs after server parameter bootstrap', () => {
    const prefillDefinition = src.indexOf('async function prefillVolumeRows()');
    const serverParamBootstrap = src.indexOf('initialHydrationTasks.push(loadParamsFromServer({ data: VP_BOOTSTRAP.parameters }));');
    const summaryBarInit = src.indexOf("const summaryBar = document.getElementById('vp-summary-bar');");
    const hydrationBarrier = src.indexOf('const initialHydrationComplete = Promise.allSettled(initialHydrationTasks)');
    const prefillCall = src.indexOf('.then(() => prefillVolumeRows());');
    expect(prefillDefinition).toBeGreaterThan(-1);
    expect(serverParamBootstrap).toBeGreaterThan(-1);
    expect(summaryBarInit).toBeGreaterThan(-1);
    expect(hydrationBarrier).toBeGreaterThan(-1);
    expect(prefillCall).toBeGreaterThan(-1);
    expect(serverParamBootstrap).toBeLessThan(prefillCall);
    expect(summaryBarInit).toBeLessThan(prefillCall);
    expect(hydrationBarrier).toBeLessThan(prefillCall);
    expect(src).not.toContain('initialHydrationTasks.push(prefillVolumeRows());');
  });

  test('server-loaded formulas do not mark the page dirty', () => {
    expect(src).toContain('const updateDirtyOnChange = opts.updateDirty !== false;');
    expect(src).toContain('if (persistFormulaOnSuccess) persistRowFormula(id);');
    expect(src).toContain('handleInputChange(id, input, preview, { persistFormula: false, markTouched: false, updateDirty: false });');
    const nonDirtyReevaluations = src.match(/reevaluateAllFormulas\(\{ persistFormula: false, markTouched: false, updateDirty: false \}\);/g) || [];
    expect(nonDirtyReevaluations.length).toBeGreaterThanOrEqual(2);
  });

  test('initial hydration clears dirty state unless the user has edited', () => {
    expect(src).toContain('let initialHydrationActive = true;');
    expect(src).toContain('let userInteractedDuringInitialHydration = false;');
    expect(src).toContain('function clearInitialHydrationDirtyState(');
    expect(src).toContain('dirtySet.clear();');
    expect(src).toContain('formulaDirtySet.clear();');
    expect(src).toContain('const initialHydrationComplete = Promise.allSettled(initialHydrationTasks)');
    expect(src).toContain('markInitialHydrationUserInteraction();');
  });

  test('volume script is deferred after formula engine', () => {
    const formulaEngine = templateSrc.indexOf("detail_project/js/vol_formula_engine.js");
    const volumeScript = templateSrc.indexOf("detail_project/js/volume_pekerjaan.js");
    expect(formulaEngine).toBeGreaterThan(-1);
    expect(volumeScript).toBeGreaterThan(-1);
    expect(formulaEngine).toBeLessThan(volumeScript);
    expect(templateSrc).toContain(`<script defer src="{% static 'detail_project/js/volume_pekerjaan.js' %}"></script>`);
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

  test('volume reset warning explains trigger and recovery action', () => {
    expect(src).not.toContain("pill.textContent = 'Perlu cek'");
    expect(src).toContain("pill.textContent = 'Volume perlu diisi ulang'");
    expect(src).toContain('tipe/sumber/referensi berubah di List Pekerjaan');
    expect(src).toContain('isi atau simpan volume yang ditandai untuk menghapus penanda');
    expect(templateSrc).toContain('Volume perlu diperiksa ulang');
    expect(templateSrc).toContain('Periksa lalu simpan volume yang ditandai');
  });

  test('volume reset banner counts only rendered active pekerjaan rows', () => {
    expect(src).toContain('function pruneStalePendingVolumeJobs()');
    expect(src).toContain('sourceChange?.markVolumeResolved(projectId, staleIds)');
    expect(src).toContain('function pendingVisibleVolumeJobs()');
    expect(src).toContain('const count = pendingVisibleVolumeJobs().length;');
    expect(src).not.toContain('const count = pendingVolumeJobs.size;');
  });

  test('validation messages use pekerjaan labels instead of raw database ids', () => {
    expect(src).toContain('function getPekerjaanDisplayLabel(');
    expect(src).not.toContain('Simpan diblokir: baris #${first.id}');
    expect(src).not.toContain('Autosave ditunda: baris #${first.id}');
    expect(src).not.toContain('Sinkron formula diblokir: baris #${first.id}');
    expect(src).not.toContain('Draft formula baris #${id}');
    expect(src).toContain('getPekerjaanDisplayLabel(first.id)');
  });
});

describe('VP-A2 - leave-flush persists valid rows even when one row is invalid', () => {
  test('manual/autosave still block atomically, leave-flush does not', () => {
    // The hard-block (focus + warn + return) only applies when NOT a leave flush.
    expect(src).toContain("if (reason !== 'leave') {");
  });

  test('leave-flush drops invalid ids and saves the valid remainder', () => {
    expect(src).toContain('const invalidIds = new Set(blockingIssues.map((b) => Number(b.id)));');
    expect(src).toContain('postingIds = postingIds.filter((id) => !invalidIds.has(Number(id)));');
    expect(src).toContain('pendingFormulaIds = pendingFormulaIds.filter((id) => !invalidIds.has(Number(id)));');
    expect(src).toContain('hasVolumeChanges = postingIds.length > 0;');
  });

  test('posting buckets are mutable (let) so the leave filter can apply', () => {
    expect(src).toContain('let postingIds = Array.from(dirtySet.values());');
    expect(src).toContain('let pendingFormulaIds = Array.from(formulaDirtySet.values());');
    expect(src).toContain('let hasVolumeChanges = postingIds.length > 0;');
  });
});
