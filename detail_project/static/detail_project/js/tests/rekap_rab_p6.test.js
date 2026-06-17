/**
 * WP-P6 guard — Rekap RAB correctness + reliability fixes (source-grep; DOM-heavy page).
 *  - P6a/RR-09: single price contract (unit_price_after_markup / G), no silent pre-markup
 *    fallback; "belum siap" marker when the final price is missing.
 *  - P6b/RR-05: footer total always reflects the whole project, not the search subset.
 *  - P6c/RR-03/04/14: client print module deprecated → Print button uses the server PDF.
 *  - P6e/RR-06: pricing autosave validates the response + shows status + flush on blur.
 *  - P6f/RR-15/16: SheetJS CDN + client ExcelExporter removed.
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const js = readFileSync(resolve(__dirname, '..', 'rekap_rab.js'), 'utf-8');
const tpl = readFileSync(
  resolve(__dirname, '..', '..', '..', '..', 'templates', 'detail_project', 'rekap_rab.html'),
  'utf-8',
);

describe('WP-P6a — single price contract (RR-09)', () => {
  test('uses unit_price_after_markup / G only', () => {
    expect(js).toContain('r.unit_price_after_markup ?? r.G');
  });
  test('no silent fallback to pre-markup HSP/unit_price', () => {
    expect(js).not.toContain('r.G ?? r.harga_satuan ?? r.HSP ?? r.unit_price');
  });
  test('renders a "belum siap" marker when price not ready', () => {
    expect(js).toContain('hargaReady');
    expect(js).toContain('belum siap');
  });
});

describe('WP-P6b — footer total ignores search (RR-05)', () => {
  test('footer uses the full-project total', () => {
    expect(js).toContain('recalcFooter(projectTotalD)');
    expect(js).toContain('computeTotalsFiltered(fullModel, () => true)');
  });
});

describe('WP-P6c — client print deprecated → server PDF (RR-03/04/14)', () => {
  test('Print button routed to the async PDF export', () => {
    expect(tpl).toContain("btnPrint.addEventListener('click', (e) => handleExport('pdf', 'PDF', e, true))");
  });
  test('RekapRABPrint client module no longer imported', () => {
    expect(tpl).not.toContain('initRekapRABPrint');
  });
});

describe('WP-P6e — pricing autosave reliability (RR-06)', () => {
  test('validates response and shows status', () => {
    expect(js).toContain('function doSavePricing');
    expect(js).toContain('setPricingStatus');
    expect(js).toContain("'Menyimpan");
  });
  test('flushes the pending save on blur', () => {
    expect(js).toContain('function flushPricing');
    expect(js).toContain("inpPPN?.addEventListener('blur', flushPricing)");
  });
});

describe('WP-P6f — SheetJS/client Excel removed (RR-15/16)', () => {
  test('SheetJS CDN no longer loaded', () => {
    expect(tpl).not.toContain('cdn.sheetjs.com');
  });
  test('client ExcelExporter no longer loaded', () => {
    expect(tpl).not.toContain('export/ExcelExporter.js');
  });
});

describe('WP-P6g — refresh race + single export initializer (RR-12/14)', () => {
  test('loadData guarded by a sequence token', () => {
    expect(js).toContain('const seq = ++_loadSeq');
    expect(js).toContain('if (seq !== _loadSeq) return;');
  });
  test('export buttons bound once, no clone-replace', () => {
    expect(tpl).not.toContain('const cleanButton');
    expect(tpl).not.toContain('cloneNode(true)');
  });
});

describe('WP-P6h — markup override indicator (D-RR-06)', () => {
  test('rekap row carries markupIsOverride; row shows an override badge', () => {
    expect(js).toContain('markupIsOverride');
    expect(js).toContain('markup_is_override');
    expect(js).toContain('ovrBadge');
  });
});

describe('WP-P6i — empty-state + safe error (RR-13/25)', () => {
  test('rich empty-state shown only when project truly empty', () => {
    expect(js).toContain("getElementById('rab-empty')");
    expect(js).toContain('projectIsEmpty');
  });
  test('load-error message is escaped before innerHTML', () => {
    expect(js).toContain('escapeHtml(e.message');
  });
});
