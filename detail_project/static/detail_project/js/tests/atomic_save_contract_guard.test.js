import { describe, expect, test } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const read = (rel) => readFileSync(resolve(__dirname, '..', rel), 'utf-8');

describe('WP-B3 frontend contract', () => {
  test('Harga Items keeps every submitted row dirty after atomic rejection', () => {
    const src = read('harga_items.js');
    const failed = src.slice(
      src.indexOf('if (!res.ok || !j.ok)'),
      src.indexOf('} else {', src.indexOf('if (!res.ok || !j.ok)')),
    );

    expect(failed).not.toContain('setRowDirtyVisual(tr, false)');
    expect(failed).not.toContain('tr.dataset.origCanon = canon');
    expect(src).not.toContain('client_updated_at');
    expect(src).not.toContain('j.conflict');
  });

  test('Template AHSP has no stale-write retry flow', () => {
    const src = read('template_ahsp.js');

    expect(src).not.toContain('client_updated_at');
    expect(src).not.toContain('force_overwrite');
    expect(src).not.toContain('js.conflict');
    expect(src).not.toContain('status 207');
  });

  test('Volume sync does not send stale tokens or show conflict prompts', () => {
    const src = read('volume_pekerjaan.js');

    expect(src).not.toContain('last_sync_at');
    expect(src).not.toContain('status === 409');
    expect(src).not.toContain('promptSyncConflict');
    expect(src).not.toContain('partial-save kini balas 207');
    expect(src).toContain('if (hasVolumeChanges && !volumeSaved)');
  });

  test('Harga Items preserves NULL "belum diisi" and never coerces empty to 0.00 (UF-011)', () => {
    const src = read('harga_items.js');
    // Render: a NULL price must stay empty, not become "0.00".
    expect(src).not.toContain("r.harga_canon === '' ? '0.00'");
    expect(src).toContain('const isUnfilled =');
    // Save: an empty field must be sent as null (HI-01), not coerced to "0.00".
    expect(src).not.toContain("if (!canon) canon = '0.00';");
    expect(src).toContain('harga_satuan: null');
    // Clearing an existing value is a valid dirty change, not an invalid number.
    expect(src).toContain("if (raw === '') {");
    expect(src).toContain("const isDirty = orig !== '';");
    expect(src).toContain("if (isDirty || $bukInput?.value !== toUI2(bukCanonLoaded))");
  });
});
