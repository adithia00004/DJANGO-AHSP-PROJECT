// /static/detail_project/js/core/http.js
(() => {
  const DP = (window.DP = window.DP || {});
  DP.core = DP.core || {};

  if (DP.core.http) return; // guard

  // --- CSRF (Django default: 'csrftoken') ---
  const getCSRF = () =>
    document.cookie
      .split('; ')
      .find(c => c.startsWith('csrftoken='))?.split('=')[1] || '';

  // --- Util: cek JSON & parse body sesuai header ---
  const isJSON = (ct) => (ct || '').includes('application/json');

  async function parseBody(response) {
    const ct = response.headers.get('content-type') || '';
    try {
      return isJSON(ct) ? await response.json() : await response.text();
    } catch {
      // Fallback aman
      return await response.text().catch(() => '');
    }
  }

  // --- Util: bentuk respons terstruktur (opsional) ---
  function normalizeResponse(status, body, okFlag) {
    // Konvensi 207 partial errors
    if (status === 207) {
      const errors = Array.isArray(body?.errors) ? body.errors : [{ message: 'Partial error' }];
      return { ok: false, status, data: null, errors };
    }
    if (okFlag) return { ok: true, status, data: body, errors: [] };

    // Non-2xx umum → rangkum ke errors
    let errors = [];
    if (Array.isArray(body?.errors)) errors = body.errors;
    else if (typeof body === 'string' && body.trim()) errors = [{ message: body.trim() }];
    else if (body && typeof body === 'object') errors = [{ message: body.message || 'Request failed' }];
    else errors = [{ message: 'Request failed' }];

    return { ok: false, status, data: null, errors };
  }

  /**
   * jfetch(url, opts)
   * - Perilaku LAMA dipertahankan: default mengembalikan body mentah (JSON/text).
   * - Fitur baru:
   *   - opts.data: objek → dikirim sebagai JSON body (POST default bila method tidak di-set)
   *   - opts.normalize: true → kembalikan {ok,status,data,errors} (termasuk 207)
   *   - opts.timeout: ms → batasi waktu tunggu
   *   - headers default: Accept: application/json, X-Requested-With: XMLHttpRequest
   */
  async function jfetch(url, opts = {}) {
    const {
      method,
      headers,
      data,
      timeout,
      normalize,
      ...rest
    } = opts;

    const hdrs = {
      'X-Requested-With': 'XMLHttpRequest',
      'Accept': 'application/json',
      ...(headers || {}),
    };

    const init = {
      credentials: 'same-origin',
      method: method || (data ? 'POST' : undefined),
      headers: hdrs,
      ...rest,
    };

    // Payload JSON (opsional)
    if (data !== undefined) {
      if (!init.method) init.method = 'POST';
      if (!('Content-Type' in init.headers)) {
        init.headers['Content-Type'] = 'application/json';
      }
      init.body = JSON.stringify(data);
    }

    // CSRF untuk non-GET
    if (init.method && init.method.toUpperCase() !== 'GET' && !init.headers['X-CSRFToken']) {
      init.headers['X-CSRFToken'] = getCSRF();
    }

    // Timeout (opsional)
    let controller;
    if (typeof timeout === 'number' && timeout > 0) {
      controller = new AbortController();
      init.signal = controller.signal;
      setTimeout(() => controller.abort(), timeout);
    }

    let response, body;
    try {
      response = await fetch(url, init);
      body = await parseBody(response);
    } catch (e) {
      if (normalize) {
        return normalizeResponse(0, { message: e?.message || 'Network error' }, false);
      }
      // Perilaku lama: lempar error
      throw e;
    }

    if (!normalize) {
      // Perilaku lama: lempar kalau !ok
      if (!response.ok) {
        const err = Object.assign(new Error(response.statusText), { status: response.status, body });
        throw err;
      }
      return body;
    }

    // Mode normalize: selalu balikan objek terstruktur
    return normalizeResponse(response.status, body, response.ok);
  }

  // Alias yang SELALU normalize (praktis untuk halaman yang butuh panel error 207)
  function jfetchJson(url, opts = {}) {
    return jfetch(url, { ...opts, normalize: true });
  }

  DP.core.http = { jfetch, jfetchJson, getCSRF };
})();
