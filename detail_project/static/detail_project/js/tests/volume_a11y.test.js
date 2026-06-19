/**
 * T-series a11y guard for the Volume Pekerjaan page.
 *  - T1: a <main> landmark wraps the primary table.
 *  - T3: table headers carry scope="col".
 *  - T4: sidebar tabs ↔ panes are related via aria-controls / role=tabpanel.
 *  - T11: qty input validation is exposed via aria-invalid (not only the visual class).
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const tpl = readFileSync(
  resolve(__dirname, '..', '..', '..', '..', 'templates', 'detail_project', 'volume_pekerjaan.html'),
  'utf-8',
);
const js = readFileSync(resolve(__dirname, '..', 'volume_pekerjaan.js'), 'utf-8');

describe('Volume a11y - landmarks & tables (T1/T3)', () => {
  test('T1: a <main> landmark wraps the primary table', () => {
    expect(tpl).toMatch(/<main[^>]*id="vp-page"/);
    expect(tpl).toContain('</main>');
  });

  test('T3: the work table and sidebar tables use scope="col" headers', () => {
    expect(tpl).toContain('<th scope="col" class="text-center">No</th>');
    expect(tpl).toMatch(/<th scope="col"[^>]*>Nama<\/th>/);
    // No bare <th> without scope should remain in the audited theads.
    expect(tpl).not.toContain('<th>Satuan</th>');
    expect(tpl).not.toContain('<th>Quantity</th>');
  });
});

describe('Volume a11y - tab/panel relation (T4)', () => {
  test('tabs reference their panels via aria-controls', () => {
    expect(tpl).toContain('aria-controls="vp-pane-base"');
    expect(tpl).toContain('aria-controls="vp-pane-computed"');
  });

  test('panes are tabpanels labelled by their tab', () => {
    expect(tpl).toMatch(/id="vp-pane-base"[\s\S]*role="tabpanel"[\s\S]*aria-labelledby="vp-tab-base"/);
    expect(tpl).toMatch(/id="vp-pane-computed"[\s\S]*role="tabpanel"[\s\S]*aria-labelledby="vp-tab-computed"/);
  });
});

describe('Volume a11y - validation exposure (T11)', () => {
  test('qty input reflects validation via aria-invalid', () => {
    expect(js).toContain('function setQtyAriaInvalid(');
    expect(js).toContain("input.setAttribute('aria-invalid', 'true')");
    expect(js).toContain("input.removeAttribute('aria-invalid')");
    expect(js).toContain('setQtyAriaInvalid(numericId, true)');
    expect(js).toContain('setQtyAriaInvalid(numericId, false)');
  });
});
