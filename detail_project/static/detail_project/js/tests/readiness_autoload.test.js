/* WP-B4 inc-3 — readiness autoload behaviour tests (happy-dom + mocked fetch).
   The bundle-agnostic loader used by Jadwal & Rekap Kebutuhan. */
import { describe, expect, test, afterEach } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';
import '../shared/readiness_banner.js'; // window.ReadinessBanner
import '../shared/readiness_autoload.js'; // window.ReadinessAutoload

const { render } = globalThis.ReadinessAutoload;
const origFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = origFetch;
  document.body.innerHTML = '';
});

function mockReadiness(readiness) {
  globalThis.fetch = () => Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true, readiness }) });
}

describe('ReadinessAutoload.render', () => {
  test('fills the host with a banner when readiness has problems', async () => {
    document.body.innerHTML = '<div id="h" class="d-none" data-readiness-endpoint="/x/readiness/"></div>';
    mockReadiness({ missing_price: [{ kode: 'BHN-1' }], missing_volume: [] });

    await render(document.getElementById('h'));

    const host = document.getElementById('h');
    expect(host.classList.contains('d-none')).toBe(false);
    expect(host.classList.contains('alert')).toBe(true);
    expect(host.innerHTML).toContain('belum diisi');
    expect(host.innerHTML).toContain('BHN-1');
  });

  test('clears the host (hidden) when readiness is clean', async () => {
    document.body.innerHTML = '<div id="h" data-readiness-endpoint="/x/readiness/"></div>';
    mockReadiness({ missing_price: [], missing_volume: [], expansion_not_ready: [] });

    await render(document.getElementById('h'));

    const host = document.getElementById('h');
    expect(host.innerHTML).toBe('');
    expect(host.classList.contains('d-none')).toBe(true);
  });

  test('escapes dynamic codes (XSS-safe) end-to-end', async () => {
    document.body.innerHTML = '<div id="h" data-readiness-endpoint="/x/readiness/"></div>';
    mockReadiness({ missing_price: [{ kode: '<img src=x onerror=alert(1)>' }] });

    await render(document.getElementById('h'));

    const host = document.getElementById('h');
    expect(host.innerHTML).not.toContain('<img src=x');
    expect(host.innerHTML).toContain('&lt;img src=x');
  });

  test('no-op without a data-readiness-endpoint', async () => {
    document.body.innerHTML = '<div id="h"></div>';
    await render(document.getElementById('h'));
    expect(document.getElementById('h').innerHTML).toBe('');
  });

  test('fetch failure never throws (advisory only)', async () => {
    document.body.innerHTML = '<div id="h" data-readiness-endpoint="/x/readiness/"></div>';
    globalThis.fetch = () => Promise.reject(new Error('network'));
    await expect(render(document.getElementById('h'))).resolves.toBeUndefined();
  });
});

describe('readiness autoload consumer wiring', () => {
  const templateRoot = resolve(__dirname, '..', '..', '..', '..', 'templates', 'detail_project');
  const consumers = [
    'kelola_tahapan_grid_modern.html',
    'rekap_kebutuhan.html',
  ];

  for (const file of consumers) {
    test(`${file} declares the endpoint and loads builder before autoload`, () => {
      const source = readFileSync(resolve(templateRoot, file), 'utf-8');
      const builderAt = source.indexOf('js/shared/readiness_banner.js');
      const autoloadAt = source.indexOf('js/shared/readiness_autoload.js');

      expect(source).toContain('data-readiness-endpoint=');
      expect(builderAt).toBeGreaterThanOrEqual(0);
      expect(autoloadAt).toBeGreaterThan(builderAt);
    });
  }
});
