/**
 * XSS Render Guard — WP-A1 regression lock for LP-01 / RR-01 / RR-18.
 *
 * Complements xss_governance_guard.test.js (which covers volume_pekerjaan.js).
 * This guard locks the user-data → innerHTML escaping fixes on:
 *   - list_pekerjaan.js  (LP-01: Template Library preview)
 *   - rekap_rab.js       (RR-01: hierarchy label/kode render + search highlight)
 *   - print/RekapRABPrint.js (RR-18: print reinjection of extracted text)
 *
 * If any of these regress (raw user data back into innerHTML), this FAILS.
 *
 * Run: npm run test:frontend -- xss_render_guard.test.js
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const read = (rel) => readFileSync(resolve(__dirname, '..', rel), 'utf-8');

describe('LP-01 — List Pekerjaan template preview', () => {
  const src = read('list_pekerjaan.js');

  test('escapeHtml helper exists', () => {
    expect(src).toContain('function escapeHtml');
  });

  test('preview escapes klasifikasi and sub names', () => {
    expect(src).toContain('${escapeHtml(k.name)}');
    expect(src).toContain('${escapeHtml(s.name)}');
  });

  test('no raw ${k.name} / ${s.name} remains', () => {
    expect(src).not.toContain('${k.name}');
    expect(src).not.toContain('${s.name}');
  });
});

describe('RR-01 — Rekap RAB hierarchy render', () => {
  const src = read('rekap_rab.js');

  test('escapeHtml helper exists', () => {
    expect(src).toContain('const escapeHtml');
  });

  test('name/label/kode are escaped in both search and non-search branches', () => {
    expect(src).toContain('highlightMatch(escapeHtml(node.name)');
    expect(src).toContain('highlightMatch(escapeHtml(node.label)');
    expect(src).toContain('highlightMatch(escapeHtml(node.kode)');
    expect(src).toContain(': escapeHtml(node.name)');
    expect(src).toContain(': escapeHtml(node.label)');
    expect(src).toContain(': escapeHtml(node.kode');
  });

  test('no raw node.name/label fallthrough into render', () => {
    expect(src).not.toContain(': node.name;');
    expect(src).not.toContain(': node.label;');
  });
});

describe('RR-18 — Rekap RAB print reinjection', () => {
  const src = read('print/RekapRABPrint.js');

  test('escapeHtml helper exists', () => {
    expect(src).toContain('const escapeHtml');
  });

  test('print escapes klasifikasi name and project identity', () => {
    expect(src).toContain('${escapeHtml(item.name)}');
    expect(src).toContain('${escapeHtml(info.projectName');
  });

  test('no raw ${info.*} / ${item.*} reinjection remains', () => {
    expect(src).not.toMatch(/\$\{info\.[a-zA-Z]/);
    expect(src).not.toMatch(/\$\{item\.[a-zA-Z]/);
  });
});
