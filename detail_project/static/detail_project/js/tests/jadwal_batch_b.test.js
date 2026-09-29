/**
 * WP-P7 Batch B guard — Vite source (jadwal). Source-grep: these modules are bundled
 * into dist/ (rebuilt by the owner); this guard locks the intent in the SOURCE so a
 * future edit/rebuild can't silently regress it.
 *
 *  - P7i (B6e/R2): no silent auto-regenerate on page-open; advisory notice instead.
 *  - P7j (JDW-04): loadAssignments propagates load errors (no empty-map masking).
 *  - P7k (KS-02/JDW-13D): Kurva S weight is harga-only; no silent volume/equal-weight fallback.
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const SRC = resolve(__dirname, '..', 'src');
const read = (rel) => readFileSync(resolve(SRC, rel), 'utf-8');

const orchestrator = read('modules/app/DataOrchestrator.js');
const app = read('jadwal_kegiatan_app.js');
const dataLoader = read('modules/core/data-loader.js');
const datasetBuilder = read('modules/kurva-s/dataset-builder.js');
const template = readFileSync(
  resolve(__dirname, '..', '..', '..', '..', 'templates', 'detail_project', 'kelola_tahapan_grid_modern.html'),
  'utf-8'
);

describe('WP-P7i — no silent auto-regenerate on page-open (B6e/R2)', () => {
  test('DataOrchestrator flags advisory instead of auto-regenerating', () => {
    expect(orchestrator).toContain('app.state.timelineNeedsRegen = true');
    expect(orchestrator).toContain('WP-P7i');
    // the auto-mutation (await regenerateTimeline immediately on incomplete weeks) is gone
    expect(orchestrator).not.toMatch(/shouldForceWeekly\)\s*\{[\s\S]*?await this\.regenerateTimeline/);
  });
  test('jadwal_kegiatan_app flags advisory instead of auto-regenerating', () => {
    expect(app).toContain('this.state.timelineNeedsRegen = true');
    expect(app).not.toMatch(/shouldForceWeekly\)\s*\{[\s\S]*?await this\._regenerateTimeline/);
  });
});

describe('JDW-11/JDW-15 - boundary confirmation and project identity metadata', () => {
  test('week boundary changes confirm before mutating/persisting when dirty', () => {
    expect(app).toMatch(/async _handleWeekBoundaryChange/);
    expect(app).toContain("title: 'Ubah batas minggu?'");
    expect(app).toContain("confirmLabel: 'Ubah batas minggu'");
    expect(app).toMatch(/if \(!confirmed\) \{[\s\S]*?this\.state\.weekStartDay = previousStart;[\s\S]*?this\.state\.weekEndDay = previousEnd;[\s\S]*?return;/);

    const handlerStart = app.indexOf('async _handleWeekBoundaryChange');
    const confirmIdx = app.indexOf("title: 'Ubah batas minggu?'", handlerStart);
    const mutateIdx = app.indexOf('this.state.weekStartDay = normalizedStart;', handlerStart);
    const persistIdx = app.indexOf('this._persistWeekBoundarySettings(normalizedStart, normalizedEnd);', handlerStart);

    expect(confirmIdx).toBeGreaterThan(handlerStart);
    expect(mutateIdx).toBeGreaterThan(confirmIdx);
    expect(persistIdx).toBeGreaterThan(mutateIdx);
  });

  test('week boundary API asks before moving planned values and can cancel cleanly', () => {
    expect(app).toContain("data?.code === 'week_boundary_moves_plan_into_extension'");
    expect(app).toContain("saveBoundary('move_planned_to_boundary')");
    expect(app).toContain('Realisasi dan biaya aktual tetap di minggu asal.');
    expect(app).toContain('this.state.weekStartDay = data.old_week_start_day;');
    expect(app).toContain('this.state.weekEndDay = data.old_week_end_day;');
  });

  test('week boundary change is rejected visibly if it would hide progress rows', () => {
    expect(app).toContain("data?.code === 'week_boundary_excludes_progress'");
    expect(app).toContain('this._regenerateColumnsForWeekBoundary();');
    expect(app).toContain('this.showToast(data.error ||');
  });

  test('active template reads project location from lokasi_project', () => {
    expect(template).toContain('data-project-location="{{ project.lokasi_project|default:\'-\' }}"');
    expect(template).not.toContain('data-project-location="{{ project.lokasi|default:\'-\' }}"');
  });

  test('initialization reload control is CSP-safe (no inline onclick)', () => {
    expect(template).not.toContain('onclick="window.location.reload()"');
    expect(template).toContain('href="{{ request.get_full_path }}"');
  });
});

describe('Tambahan Waktu Kerja - toolbar, preview, and edit guard', () => {
  test('toolbar button and date dialog are wired for actual mode only', () => {
    expect(template).toContain('id="btn-work-extension"');
    expect(template).toContain('id="workExtensionModal"');
    expect(template).toContain('id="work-extension-end-date"');
    expect(app).toContain("this._syncWorkExtensionButtonVisibility(normalized);");
    expect(app).toContain("(mode || 'planned') !== 'actual'");
  });

  test('dialog previews on the server and refuses to open with unsaved grid edits', () => {
    expect(app).toContain('Simpan atau batalkan perubahan di grid terlebih dahulu. Perpanjangan waktu kerja membentuk ulang kolom minggu.');
    expect(app).toContain("target_field: 'tanggal_akhir_tambahan'");
    expect(app).toContain('this.state.apiEndpoints?.timelinePreview');
    expect(app).toContain('this.state.apiEndpoints?.timelineCommit');
  });
});

describe('WP-P7j — loadAssignments propagates errors (JDW-04)', () => {
  test('error sets a flag and re-throws (no empty-map masking)', () => {
    expect(dataLoader).toContain('this.state.assignmentsLoadError = error');
    expect(dataLoader).toMatch(/this\.state\.assignmentsLoadError = error;\s*\n\s*throw error;/);
  });
});

describe('WP-P7k — Kurva S harga-only weighting (KS-02/JDW-13D)', () => {
  test('no silent volume/equal-weight fallback; honest weightsReady flag', () => {
    expect(datasetBuilder).not.toContain('totalVolume = pekerjaanIds.size');
    expect(datasetBuilder).toContain('weightsReady: false');
    expect(datasetBuilder).toContain('JDW-13D');
  });
});
