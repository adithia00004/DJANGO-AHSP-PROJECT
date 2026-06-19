/**
 * WP-P4d/P4e guard - List Pekerjaan destructive-impact confirmation + UF-007/008.
 *
 * Source-grep guard (the file is DOM-heavy and bootstrapped on a real page). It locks
 * the contract that:
 *  - a save previews destructive impact and confirms before deleting (P4d/LP-04);
 *  - the confirm flow blocks when a deletion is a bundle target (C1) and fails open
 *    if the preview endpoint/modal is unavailable;
 *  - changing any pekerjaan source mode clears stale manual text (UF-007/UF-012);
 *  - the sidebar prefers a real label before the generic placeholder (UF-008).
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const src = readFileSync(resolve(__dirname, '..', 'list_pekerjaan.js'), 'utf-8');
const tpl = readFileSync(
  resolve(__dirname, '..', '..', '..', '..', 'templates', 'detail_project', 'list_pekerjaan.html'),
  'utf-8',
);

describe('WP-P4d - destructive-impact confirmation before save', () => {
  test('handleSave consults the impact preview and aborts on cancel', () => {
    expect(src).toContain('const proceed = await confirmDestructiveImpact(payload);');
    expect(src).toContain('if (!proceed) {');
  });

  test('confirmDestructiveImpact calls the destructive-impact endpoint', () => {
    expect(src).toContain('list-pekerjaan/destructive-impact/');
  });

  test('nothing destructive (no delete AND no reset) -> proceed without a modal', () => {
    expect(src).toContain('if (!data || (!data.has_destructive && !data.has_reset)) return true;');
  });

  test('blocked bundle-target deletions stop the save', () => {
    expect(src).toContain('if (data.has_blocked) {');
    expect(src).toMatch(/Tidak Bisa Menghapus/);
  });

  test('uses a destructive (danger) confirm for genuine deletions', () => {
    expect(src).toContain("confirmClass: 'btn btn-danger'");
    expect(src).toMatch(/Hapus & Simpan/);
  });

  test('fails open when the preview request fails (does not block saving)', () => {
    expect(src).toMatch(/proceeding without confirmation[\s\S]*return true;/);
  });
});

describe('N2 - source-change reset is surfaced in the confirmation', () => {
  test('confirm flow reads the reset category from the preview', () => {
    expect(src).toContain('data.has_reset');
    expect(src).toContain('data.to_reset');
    expect(src).toContain('data.reset_totals');
  });

  test('modal explains that source/reference change resets derived data', () => {
    expect(src).toMatch(/Akan MERESET/);
    expect(src).toMatch(/sumber\/referensi AHSP-nya berubah/);
  });

  test('warns when the reset also affects a Pekerjaan Gabungan', () => {
    expect(src).toContain('affects_bundle');
    expect(src).toMatch(/Pekerjaan Gabungan yang memakainya/);
  });

  test('confirm label adapts to reset-only saves', () => {
    expect(src).toContain("data.has_destructive ? 'Hapus & Simpan' : 'Reset & Simpan'");
  });

  test('reset confirmation surfaces the budgeted_cost (BAC) that will be cleared', () => {
    expect(src).toContain('rt.budgeted_cost');
    expect(src).toMatch(/Baseline biaya\/BAC Rp/);
    expect(src).toMatch(/Kurva S akan memakai nilai hitung ulang dari RAB/);
  });
});

describe('N5 - Export Template JSON respects the dirty-save guard', () => {
  test('template export link has an id the JS can bind to', () => {
    expect(tpl).toContain('id="btn-export-template-json"');
  });

  test('template export saves first when dirty, then downloads', () => {
    expect(src).toContain("document.getElementById('btn-export-template-json')");
    expect(src).toMatch(/if \(!isDirty\) return;[\s\S]*await handleSave\(\);/);
    expect(src).toContain('window.location.href = url');
  });

  test('template export aborts if changes could not be saved', () => {
    expect(src).toMatch(/Export dibatalkan karena perubahan belum berhasil disimpan/);
  });
});

describe('N3 (Opsi B) - post-save id sync guards against structural mismatch', () => {
  test('validates DOM/server structure before stamping ids by position', () => {
    expect(src).toContain('function treeStructureMatches(');
    expect(src).toContain('if (!treeStructureMatches(savable, serverKlas)) {');
  });

  test('savable projection drops empty subs/klas (mirrors handleSave filter)', () => {
    expect(src).toContain('function buildSavableDomTree(');
    expect(src).toMatch(/if \(rows\.length === 0\) return;/);
    expect(src).toMatch(/if \(subNodes\.length === 0\) return;/);
  });

  test('on mismatch it reloads the authoritative tree instead of mis-stamping', () => {
    expect(src).toMatch(/treeStructureMatches[\s\S]*await reloadAfterSave\(\);[\s\S]*return;/);
    expect(src).toMatch(/Struktur berubah saat sinkronisasi, halaman dimuat ulang agar data tetap aman/);
  });

  test('on match it still stamps ids ordinally over the savable nodes', () => {
    expect(src).toContain('stampRowIdentity(tr, sSrv?.pekerjaan?.[pi]?.id)');
  });
});

describe('N3 (Opsi A) - temp_id->id map stamps by identity, falls back to Opsi B', () => {
  test('handleSave persists the per-row temp_id on the DOM row', () => {
    expect(src).toContain('tr.dataset.tempId = pekerjaanTempId');
  });

  test('save passes the response id_map into the id sync', () => {
    expect(src).toContain('await syncTreeIdsFromServer(response?.id_map)');
  });

  test('the map is only used when it covers every savable node', () => {
    expect(src).toContain('function idMapCovers(');
    expect(src).toContain('if (idMap && idMapCovers(savable, idMap)) {');
  });

  test('Opsi A stamps klas/sub/pekerjaan ids by temp_id lookup', () => {
    expect(src).toContain('idMap.klas[kNode.el.dataset.tempId]');
    expect(src).toContain('idMap.sub[sNode.el.dataset.tempId]');
    expect(src).toContain('stampRowIdentity(tr, idMap.pekerjaan[tr.dataset.tempId])');
  });

  test('an incomplete/absent map degrades to the validated positional fallback', () => {
    // idMapCovers returns false on any missing entry, so the code path continues
    // to the /tree/ fetch + treeStructureMatches reload guard (Opsi B).
    expect(src).toMatch(/idMapCovers[\s\S]*list-pekerjaan\/tree\/[\s\S]*treeStructureMatches/);
  });
});

describe('WP-P4e - UF-007/UF-008 cosmetics', () => {
  test('UF-007/UF-012: every real source mode change clears stale manual text', () => {
    expect(src).toContain('function clearManualOverrideFields()');
    expect(src).toContain('if (oldSourceType && oldSourceType !== v) clearManualOverrideFields();');
  });

  test('UF-008: sidebar prefers the selected reference label before placeholder', () => {
    expect(src).toContain('|| refText');
    expect(src).toContain('`Pekerjaan ${pi + 1}`');
  });
});

describe('List Pekerjaan runtime UI copy guard', () => {
  test('page sources do not contain common mojibake markers', () => {
    expect(`${src}\n${tpl}`).not.toMatch(/[âÃð]|š|ï/);
  });

  test('tooltip uses plain text instead of HTML tooltip content', () => {
    expect(tpl).not.toContain('data-bs-html="true"');
    expect(tpl).toContain('Drag & Drop: perubahan urutan');
  });

  test('import file confirmation uses DP modal, not native confirm', () => {
    expect(src).toContain("title: 'Konfirmasi Import'");
    expect(src).not.toContain('if (!confirm(msg)) return;');
  });
});
