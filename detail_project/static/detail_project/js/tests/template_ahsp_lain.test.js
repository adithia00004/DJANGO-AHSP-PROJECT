/**
 * WP-B8d guard — Template AHSP exposes the three D-08 LAIN add actions and
 * treats OTHER_DIRECT rows (no reference) distinctly from WORK_BUNDLE rows.
 *
 * Source-level guard (the editor is select2/DOM-heavy); locks the wiring so a
 * refactor can't silently drop the "Biaya Lain Langsung" path or the scoped
 * reference pickers.
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const read = (rel) => readFileSync(resolve(__dirname, '..', rel), 'utf-8');

describe('WP-B8d — LAIN three-action add', () => {
  const js = read('template_ahsp.js');

  test('addLainRow handles direct / ahsp / job modes', () => {
    expect(js).toContain('function addLainRow(mode)');
    expect(js).toContain("tr.dataset.refMode = mode");
    expect(js).toContain("tr.dataset.visualSeg = visualSeg");
    expect(js).toContain("const visualSeg = mode === 'direct' ? 'LAIN' : 'LAIN_BUNDLE'");
    // direct rows never get a reference picker
    expect(js).toContain("tr.dataset.refMode === 'direct'");
    // bundle picker scoped per mode
    expect(js).toContain("refMode !== 'ahsp'");
    expect(js).toContain("refMode !== 'job'");
  });

  test('custom mode visually splits OTHER_DIRECT and WORK_BUNDLE while saving both as LAIN', () => {
    expect(js).toContain("function visualSegToKategori(seg)");
    expect(js).toContain("seg === 'LAIN_BUNDLE' ? 'LAIN' : seg");
    expect(js).toContain("activeSource === 'custom' && r.kategori === 'LAIN' && isBundleRowData(r)");
    expect(js).toContain("const kategori = visualSegToKategori(seg)");
  });

  test('bundle rows cannot silently become Biaya Lain via manual kode edit', () => {
    expect(js).toContain("tr.dataset.visualSeg === 'LAIN_BUNDLE'");
    expect(js).toContain('Ubah referensi Pekerjaan Gabungan melalui picker');
    expect(js).toContain('input.dataset.bundleKode');
  });

  test('Template AHSP exposes backend rebuild action for missing/stale expansion', () => {
    expect(js).toContain('rebuildExpansion');
    expect(js).toContain('Bangun ulang ekspansi');
    expect(js).toContain('expansion_not_ready');
  });

  test('three add buttons are wired', () => {
    expect(js).toContain("$$('.ta-add-lain')");
    expect(js).toContain('btn.dataset.lainMode');
  });

  test('bundle actions are guarded to custom pekerjaan', () => {
    expect(js).toMatch(/Pekerjaan Gabungan hanya tersedia untuk pekerjaan custom/);
  });
});

describe('WP-B8d — template markup', () => {
  const html = read('../../../templates/detail_project/template_ahsp.html');

  test('three explicit LAIN add actions exist', () => {
    expect(html).toContain('data-lain-mode="direct"');
    expect(html).toContain('data-lain-mode="ahsp"');
    expect(html).toContain('data-lain-mode="job"');
    expect(html).toContain('id="seg-LAIN_BUNDLE-section"');
    expect(html).toContain('id="seg-LAIN_BUNDLE-body"');
    expect(html).toContain('Pekerjaan Gabungan');
    expect(html).toContain('Biaya Lain');
    expect(html).toContain('koefisien berarti jumlah/multiplier bundle');
    expect(html).toContain('data-endpoint-rebuild-expansion');
  });

  test('source-change reload banner exposes the JS targets', () => {
    expect(html).toContain('id="ta-sync-banner"');
    expect(html).toContain('id="ta-sync-banner-text"');
    expect(html).toContain('id="ta-banner-reload"');
    expect(html).toContain('Detail AHSP perlu dimuat ulang');
    expect(html).toContain('Muat ulang');
  });
});

describe('WP-P2d (UF-010) — no eager mass auto-reload on page-open', () => {
  const js = read('template_ahsp.js');

  test('no bulk auto-reload scheduler remains', () => {
    expect(js).not.toContain('function scheduleAutoReloadPendingJobs');
    expect(js).not.toContain('function autoReloadPendingJobs');
    expect(js).not.toContain('scheduleAutoReloadPendingJobs(');
    expect(js).not.toContain('Auto-reloading pending Template AHSP jobs');
  });

  test('stale jobs are still resolved lazily on selection', () => {
    // selectJobInternal fetches fresh detail when a flagged job is opened.
    expect(js).toContain('jobNeedsReload(id)');
    expect(js).toContain('const needsFetch =');
  });

  test('stale job labels are actionable, not vague reload copy', () => {
    expect(js).not.toContain("pill.textContent = 'Perlu reload'");
    expect(js).toContain("pill.textContent = 'Detail perlu dimuat ulang'");
    expect(js).toContain('Sumber pekerjaan berubah di List Pekerjaan');
  });

  test('stale reload flags for deleted jobs are pruned locally', () => {
    expect(js).toContain('function pruneStalePendingReloadJobs()');
    expect(js).toContain('sourceChange?.markReloaded(projectId, staleIds)');
    expect(js).toContain('pruneStalePendingReloadJobs();');
  });
});
