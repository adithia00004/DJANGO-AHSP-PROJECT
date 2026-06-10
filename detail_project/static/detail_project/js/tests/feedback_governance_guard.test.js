/**
 * Feedback Governance Guard — Kontrak Feedback UI Seragam
 * (docs/AUDIT_UI_UX_20260610.md §10, disetujui 2026-06-10)
 *
 * Menegakkan dua aturan pada SEMUA JS aplikasi (detail_project, referensi,
 * dashboard) di luar js/core/:
 *
 *  1. TIDAK ADA z-index literal >= 1000 yang di-set dari JS
 *     (style.zIndex = '99999' dsb.) — lapisan feedback diatur token
 *     --dp-z-* di core.css.
 *
 *  2. Budget confirm()/alert() native TIDAK BOLEH NAIK. Baseline di bawah
 *     adalah snapshot migrasi (U11). Mengurangi = silakan (perbarui angka
 *     turun). Menambah = test gagal → pakai DP.modal.confirm / DP.toast.
 *
 * Pola guard ini meniru xss_governance_guard.test.js.
 */

import { describe, test, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'fs';
import { resolve, join, relative, sep } from 'path';

const REPO_ROOT = resolve(__dirname, '..', '..', '..', '..', '..');

const SCAN_ROOTS = [
  'detail_project/static/detail_project/js',
  'referensi/static/referensi/js',
  'dashboard/static/dashboard/js',
];

// Dikecualikan dari kedua aturan.
const EXCLUDED_SEGMENTS = ['tests', 'vendor', 'dist', 'node_modules'];
const EXCLUDED_FILES = [/\.test\.js$/, /\.min\.js$/, /\.umd\.js$/];
// js/core/ adalah implementasi kanonik (toast/modal) — boleh memakai
// primitive yang dilarang di tempat lain.
const CORE_SEGMENT = `js${sep}core`;

function collectJsFiles(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      if (!EXCLUDED_SEGMENTS.includes(entry)) collectJsFiles(full, out);
    } else if (entry.endsWith('.js') && !EXCLUDED_FILES.some((re) => re.test(entry))) {
      out.push(full);
    }
  }
  return out;
}

function appJsFiles() {
  const files = [];
  for (const root of SCAN_ROOTS) {
    collectJsFiles(resolve(REPO_ROOT, root), files);
  }
  return files.filter((f) => !f.includes(CORE_SEGMENT));
}

function relPath(file) {
  return relative(REPO_ROOT, file).split(sep).join('/');
}

// ---------------------------------------------------------------------------
// Aturan 1: tanpa z-index literal tinggi dari JS
// ---------------------------------------------------------------------------

const Z_LITERAL_RE = /\.style\.zIndex\s*=\s*['"`]?\d{4,}/;

describe('Kontrak Feedback UI — z-index', () => {
  test('tidak ada style.zIndex literal >= 1000 di luar js/core/', () => {
    const offenders = [];
    for (const file of appJsFiles()) {
      const lines = readFileSync(file, 'utf-8').split('\n');
      lines.forEach((line, idx) => {
        if (Z_LITERAL_RE.test(line)) {
          offenders.push(`${relPath(file)}:${idx + 1} -> ${line.trim()}`);
        }
      });
    }
    expect(
      offenders,
      `z-index literal ditemukan. Pakai token: el.style.zIndex = 'var(--dp-z-toast, 13100)'.\n${offenders.join('\n')}`
    ).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Aturan 2: budget confirm()/alert() native (snapshot U11 — hanya boleh turun)
// ---------------------------------------------------------------------------

// Match pemanggilan native: `confirm(`, `window.confirm(`, `alert(` —
// bukan member call lain seperti DP.modal.confirm( atau obj.alert(.
const NATIVE_DIALOG_RE = /(?:^|[^.\w])(?:window\.)?(confirm|alert)\s*\(/g;

function countNativeDialogs(content) {
  // Buang string + komentar secara kasar agar dokumentasi tidak ikut terhitung.
  const stripped = content
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/(^|[^:])\/\/.*$/gm, '$1');
  let count = 0;
  let m;
  NATIVE_DIALOG_RE.lastIndex = 0;
  while ((m = NATIVE_DIALOG_RE.exec(stripped)) !== null) count += 1;
  return count;
}

// Baseline migrasi U11 (2026-06-10). Turunkan angka saat callsite dimigrasi
// ke DP.modal; JANGAN menaikkan; file baru tidak boleh muncul di sini.
const NATIVE_DIALOG_BUDGET = {
  'detail_project/static/detail_project/js/template_ahsp.js': 9,
  'detail_project/static/detail_project/js/detail_ahsp_gabungan.js': 4,
  'detail_project/static/detail_project/js/volume_pekerjaan.js': 3,
  'detail_project/static/detail_project/js/shared/param_sidebar_editor.js': 3,
  'detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js': 3,
  'detail_project/static/detail_project/js/jadwal_pekerjaan/kelola_tahapan/save_handler_module.js': 2,
  'referensi/static/referensi/js/ahsp_database.js': 2,
  'referensi/static/referensi/js/ahsp_database_v2.js': 1,
  'referensi/static/referensi/js/ahsp_database_api.js': 1,
  'detail_project/static/detail_project/js/rincian_ahsp.js': 1,
  'detail_project/static/detail_project/js/list_pekerjaan.js': 1,
  'detail_project/static/detail_project/js/orphan_cleanup.js': 1,
  'detail_project/static/detail_project/js/print/RekapRABPrint.js': 1,
  'detail_project/static/detail_project/js/print/PrintComponents.js': 1,
  'detail_project/static/detail_project/js/export/ExcelExporter.js': 1,
  'detail_project/static/detail_project/js/jadwal_pekerjaan/kelola_tahapan/grid_tab.js': 1,
  'detail_project/static/detail_project/js/src/export/ui-integration.js': 1,
  'detail_project/static/detail_project/js/src/modules/app/DataOrchestrator.js': 1,
};

describe('Kontrak Feedback UI — confirm()/alert() native', () => {
  test('jumlah callsite per file tidak melebihi budget U11', () => {
    const violations = [];
    const actual = {};

    for (const file of appJsFiles()) {
      const n = countNativeDialogs(readFileSync(file, 'utf-8'));
      if (n > 0) actual[relPath(file)] = n;
    }

    for (const [file, n] of Object.entries(actual)) {
      const budget = NATIVE_DIALOG_BUDGET[file];
      if (budget === undefined) {
        violations.push(`${file}: ${n} callsite BARU (budget tidak ada) — pakai DP.modal/DP.toast`);
      } else if (n > budget) {
        violations.push(`${file}: ${n} > budget ${budget} — pakai DP.modal/DP.toast`);
      }
    }

    expect(
      violations,
      `Pelanggaran Kontrak Feedback UI (§10):\n${violations.join('\n')}`
    ).toEqual([]);
  });
});
