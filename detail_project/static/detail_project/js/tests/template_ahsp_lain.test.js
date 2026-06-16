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
    // direct rows never get a reference picker
    expect(js).toContain("tr.dataset.refMode === 'direct'");
    // bundle picker scoped per mode
    expect(js).toContain("refMode !== 'ahsp'");
    expect(js).toContain("refMode !== 'job'");
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
  });
});

describe('WP-P2d (UF-010) — no eager mass auto-reload on page-open', () => {
  const js = read('template_ahsp.js');

  test('page-open does not trigger a bulk auto-reload', () => {
    expect(js).not.toContain("scheduleAutoReloadPendingJobs('page-open')");
  });

  test('stale jobs are still resolved lazily on selection', () => {
    // selectJobInternal fetches fresh detail when a flagged job is opened.
    expect(js).toContain('jobNeedsReload(id)');
    expect(js).toContain('const needsFetch =');
  });
});
