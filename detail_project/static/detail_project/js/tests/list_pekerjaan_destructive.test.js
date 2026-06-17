/**
 * WP-P4d/P4e guard — List Pekerjaan destructive-impact confirmation + UF-007/008.
 *
 * Source-grep guard (the file is DOM-heavy and bootstrapped on a real page). It locks
 * the contract that:
 *  - a save previews destructive impact and confirms before deleting (P4d/LP-04);
 *  - the confirm flow blocks when a deletion is a bundle target (C1) and fails open
 *    if the preview endpoint/modal is unavailable;
 *  - reverting ref_modified→ref clears the stale modified name (UF-007);
 *  - the sidebar prefers a real label before the generic placeholder (UF-008).
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const src = readFileSync(resolve(__dirname, '..', 'list_pekerjaan.js'), 'utf-8');

describe('WP-P4d — destructive-impact confirmation before save', () => {
  test('handleSave consults the impact preview and aborts on cancel', () => {
    expect(src).toContain('const proceed = await confirmDestructiveImpact(payload);');
    expect(src).toContain('if (!proceed) {');
  });

  test('confirmDestructiveImpact calls the destructive-impact endpoint', () => {
    expect(src).toContain('list-pekerjaan/destructive-impact/');
  });

  test('nothing being deleted → proceed without a modal', () => {
    expect(src).toContain('if (!data || !data.has_destructive) return true;');
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

describe('WP-P4e — UF-007/UF-008 cosmetics', () => {
  test('UF-007: ref_modified→ref clears the stale modified name', () => {
    expect(src).toContain("(oldSourceType === 'ref_modified' && v === 'ref')");
  });

  test('UF-008: sidebar prefers the selected reference label before placeholder', () => {
    expect(src).toContain('|| refText');
    expect(src).toContain('`Pekerjaan ${pi + 1}`');
  });
});
