/**
 * TA-10 a11y guard for the Template AHSP page.
 *  - table headers carry scope="col";
 *  - sidebar tabs <-> panes related via aria-controls / role=tabpanel;
 *  - koefisien validation exposed via aria-invalid;
 *  - dynamic selection checkbox has an accessible name.
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const tpl = readFileSync(
  resolve(__dirname, '..', '..', '..', '..', 'templates', 'detail_project', 'template_ahsp.html'),
  'utf-8',
);
const js = readFileSync(resolve(__dirname, '..', 'template_ahsp.js'), 'utf-8');

describe('Template AHSP a11y - tables (TA-10)', () => {
  test('component table headers use scope="col"', () => {
    expect(tpl).toContain('<th scope="col" class="col-no">No</th>');
    expect(tpl).toContain('<th scope="col" class="col-koef">Koefisien</th>');
    // no bare component header should remain
    expect(tpl).not.toContain('<th class="col-no">No</th>');
    expect(tpl).not.toContain('<th class="col-koef">Koefisien</th>');
  });

  test('sidebar parameter tables use scope="col"', () => {
    expect(tpl).toMatch(/<th scope="col"[^>]*>Nama<\/th>/);
    expect(tpl).not.toContain('<th style="width:45%">Nama</th>');
  });
});

describe('Template AHSP a11y - tab/panel relation (TA-10)', () => {
  test('tabs reference their panels via aria-controls', () => {
    expect(tpl).toContain('aria-controls="ta-pane-base"');
    expect(tpl).toContain('aria-controls="ta-pane-computed"');
  });

  test('panes are tabpanels labelled by their tab', () => {
    expect(tpl).toMatch(/id="ta-pane-base"[\s\S]*role="tabpanel"[\s\S]*aria-labelledby="ta-tab-base"/);
    expect(tpl).toMatch(/id="ta-pane-computed"[\s\S]*role="tabpanel"[\s\S]*aria-labelledby="ta-tab-computed"/);
  });
});

describe('Template AHSP a11y - validation & controls (TA-10)', () => {
  test('koefisien input reflects validation via aria-invalid', () => {
    expect(js).toContain("input.setAttribute('aria-invalid', 'true')");
    expect(js).toContain("input.removeAttribute('aria-invalid')");
  });

  test('dynamic selection checkbox has an accessible name', () => {
    expect(js).toContain("cb.setAttribute('aria-label', 'Pilih baris untuk dihapus')");
  });
});
