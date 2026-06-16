/**
 * WP-P1 frontend package guard — Harga Items conversion wiring.
 *
 * Locks the Model A flow on harga_items.js (source-level; the editor is DOM/modal
 * heavy):
 *  - conversions persist via the atomic main save (payload.conversions), not a
 *    separate commit endpoint (HI-02 end-to-end);
 *  - profile shape is backend-keyed (market_unit/market_price);
 *  - manual edit of a converted row signals clear_conversion (last-write-wins);
 *  - no localStorage conversion fallback (HI-08).
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const src = readFileSync(resolve(__dirname, '..', 'harga_items.js'), 'utf-8');

describe('WP-P1 — Harga Items conversion wiring', () => {
  test('no separate conversion-profile commit endpoint call (HI-02 e2e)', () => {
    expect(src).not.toContain('conversion-profile/save');
  });

  test('no localStorage conversion fallback (HI-08)', () => {
    expect(src).not.toMatch(/localStorage\.(get|set|remove)Item/);
    expect(src).not.toContain("'hiConv:'");
  });

  test('main save sends backend-keyed conversions from convStore', () => {
    expect(src).toContain('payload.conversions = conversions');
    expect(src).toContain('market_unit: p.market_unit');
    expect(src).toContain('market_price: p.market_price');
  });

  test('profile shape is backend-keyed (no legacy unit/price_market)', () => {
    expect(src).not.toContain('price_market:');
    expect(src).not.toContain('rememberServer');
  });

  test('manual override of a converted row signals clear_conversion (Model A)', () => {
    expect(src).toContain("tr.dataset.clearConv = '1'");
    expect(src).toContain('clear_conversion: true');
  });

  test('staged conversion marks the page dirty so Simpan persists it', () => {
    expect(src).toContain('convStore.set(convCtx.id, prof)');
    expect(src).toContain('setDirty(true)');
  });

  // WP-P1e — bulk paste computes base price (market÷factor) + confirms first (HI-07).
  test('paste with a factor computes the base price (market ÷ factor)', () => {
    expect(src).toContain('Number(harga) / Number(factor)');
    expect(src).toContain('input.value = toUI(p.basePrice)');
  });

  test('paste asks for confirmation before applying', () => {
    expect(src).toContain("title: 'Konfirmasi Tempel Massal'");
    expect(src).toMatch(/await confirmModal\(msg/);
    // the plan is built before any mutation (preview), then applied on confirm
    expect(src).toContain('if (!ok)');
  });
});
