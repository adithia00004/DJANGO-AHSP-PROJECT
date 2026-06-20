/**
 * Rincian AHSP page-scope a11y guard (RA-13).
 *
 * Source-grep guard for DOM-heavy bundle expansion code:
 *  - bundle rows are keyboard reachable and announce expanded state;
 *  - expansion close button is wired through addEventListener, not inline onclick;
 *  - loading scopes expose aria-busy.
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const src = readFileSync(resolve(__dirname, '..', 'rincian_ahsp.js'), 'utf-8');

describe('RA-13 bundle expansion accessibility', () => {
  test('bundle rows are keyboard-accessible disclosure controls', () => {
    expect(src).toContain("tr.setAttribute('role', 'button');");
    expect(src).toContain("tr.setAttribute('tabindex', '0');");
    expect(src).toContain("tr.setAttribute('aria-expanded', 'false');");
    expect(src).toContain("this.setAttribute('aria-expanded', 'true');");
    expect(src).toContain("row.addEventListener('keydown'");
    expect(src).toContain("e.key !== 'Enter' && e.key !== ' '");
  });

  test('bundle expansion close action does not use inline onclick', () => {
    expect(src).toContain("function closeBundleExpansion(row)");
    expect(src).toContain("expansionRow.querySelector('.js-bundle-close')?.addEventListener('click'");
    expect(src).not.toContain('onclick="this.closest');
  });

  test('list and detail loading states expose aria-busy', () => {
    expect(src).toContain("$list.setAttribute('aria-busy', on ? 'true' : 'false');");
    expect(src).toContain("$editor.setAttribute('aria-busy', on ? 'true' : 'false');");
    expect(src).toContain("this.setAttribute('aria-busy', 'true');");
    expect(src).toContain("this.setAttribute('aria-busy', 'false');");
  });
});
