// Template AHSP - JS (selaras SSOT + gaya aksi seperti VP)
// - Hapus handler tombol toolbar "+ Tambah Baris" (sudah dihilangkan dari HTML)
// - Simpan: tombol success + neon + spinner (mirip VP) -> #ta-btn-save & #ta-btn-save-spin
// - "+ Baris kosong" per-segmen tetap aktif dengan guard mode read-only & Select2 di LAIN

(function () {
  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));

  // ---------- STATE ----------
  const app = $('#ta-app');
  if (!app) return;

  const endpoints = {
    get: app.dataset.endpointGetPattern,       // .../<pid>/detail-ahsp/0/   -> replace 0
    save: app.dataset.endpointSavePattern,     // .../<pid>/detail-ahsp/0/save/
    reset: app.dataset.endpointResetPattern,   // .../<pid>/detail-ahsp/0/reset-to-ref/
    searchAhsp: app.dataset.endpointSearchAhsp,
    parameters: app.dataset.endpointParameters,
    computedParameters: app.dataset.endpointComputedParameters,
    readiness: app.dataset.endpointReadiness,  // WP-B4: dedicated readiness GET
    syncReference: app.dataset.endpointSyncReference,  // WP-B7d: manual master sync
  };
  const locale = app.dataset.locale || 'id-ID';

  // WP-B4 inc-3 (fan-out): readiness diagnostics (display-only). Fetched from the
  // dedicated endpoint; HTML built by the shared ReadinessBanner module. The page
  // SHOWS the server verdict and never recomputes it.
  function renderReadiness(readiness) {
    let box = document.getElementById('ta-readiness');
    const html = (window.ReadinessBanner && window.ReadinessBanner.buildReadinessBannerHTML)
      ? window.ReadinessBanner.buildReadinessBannerHTML(readiness)
      : null;
    if (!html) { if (box) box.remove(); return; }
    if (!box) {
      box = document.createElement('div');
      box.id = 'ta-readiness';
      box.className = 'alert alert-warning py-2 px-3 small mb-2';
      box.setAttribute('role', 'status');
      const toolbar = document.getElementById('ta-toolbar');
      if (toolbar) toolbar.insertAdjacentElement('afterend', box);
      else app.prepend(box);
    }
    box.innerHTML = html;
    renderSyncReferenceAction(box, readiness);
  }

  // WP-B7e: when readiness reports outdated master references, offer a one-click
  // manual sync (D-05: user-initiated, never silent). Rebuilds expanded storage
  // from the current master while preserving the user's bundle koefisien.
  function renderSyncReferenceAction(box, readiness) {
    const stale = (readiness && readiness.reference_update_available) || [];
    if (!stale.length || !endpoints.syncReference) return;

    const bar = document.createElement('div');
    bar.className = 'mt-2 d-flex align-items-center gap-2';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn btn-sm btn-warning';
    btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> Sinkronkan referensi';
    const status = document.createElement('span');
    status.className = 'text-muted';
    bar.appendChild(btn);
    bar.appendChild(status);
    box.appendChild(bar);

    btn.addEventListener('click', async () => {
      const n = stale.length;
      if (!window.confirm(
        `Sinkronkan ${n} bundle ke versi master AHSP terbaru? ` +
        'Komponen hasil ekspansi akan dibangun ulang; koefisien bundle yang Anda input tidak berubah.'
      )) return;
      btn.disabled = true;
      status.textContent = 'Menyinkronkan…';
      try {
        const resp = await fetch(endpoints.syncReference, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
          body: '{}',
        });
        const j = await resp.json().catch(() => null);
        if (!resp.ok || !j || !j.ok) {
          throw new Error((j && j.user_message) || 'Sinkronisasi gagal.');
        }
        status.textContent = `Tersinkronkan ${j.count} pekerjaan.`;
        refreshReadiness();  // verdict refresh removes the outdated-reference line
      } catch (err) {
        btn.disabled = false;
        status.textContent = err && err.message ? err.message : 'Sinkronisasi gagal.';
      }
    });
  }

  function refreshReadiness() {
    if (!endpoints.readiness) return;
    fetch(endpoints.readiness, { credentials: 'same-origin' })
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => { if (j && j.ok) renderReadiness(j.readiness); })
      .catch(() => { /* advisory only — never block the editor */ });
  }

  // P1 FIX: Cache TTL to prevent stale data
  const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes - balance between performance and freshness

  let activeJobId = null;
  let activeSource = null;     // 'ref' | 'ref_modified' | 'custom'
  let activeSourceLabel = null;
  let readOnly = false;
  let dirty = false;
  let kategoriMeta = [];       // [{code,label}]
  const rowsByJob = {};        // { jobId: [{kategori,kode,uraian,satuan,koefisien}] }
  const projectId = Number(app.dataset.projectId);
  const sourceChange = window.DP?.sourceChange || null;
  const bannerEl = $('#ta-sync-banner');
  const bannerTextEl = $('#ta-sync-banner-text');
  const bannerReloadBtn = $('#ta-banner-reload');
  const editorBlocker = $('#ta-editor-blocker');
  const editorReloadBtn = $('#ta-editor-reload');
  const paramSidebarEl = $('#ta-param-sidebar');
  const paramSidebarToggleBtn = $('#ta-btn-param-sidebar-toggle');
  const paramSidebarHotspotEl = $('.ta-param-overlay-hotspot');
  let paramSidebarEditor = null;
  let pendingReloadJobs = new Set(
    sourceChange && projectId ? sourceChange.listReloadJobs(projectId) : [],
  );
  let changeStatusPending = false;
  let reloadInFlight = false;
  let reloadQueue = Promise.resolve();
  let autoReloadPendingTimer = null;
  let autoReloadPendingInFlight = false;

  function formatSourceLabel(sourceType, sourceLabel, ahspSumber) {
    const label = String(sourceLabel || '').trim();
    if (label) return label;
    const source = String(sourceType || '').trim().toLowerCase();
    const sumber = String(ahspSumber || '').trim();
    if (source === 'ref_modified') return sumber ? `${sumber} (modified)` : 'AHSP (modified)';
    if (source === 'ref') return sumber || 'AHSP';
    if (source === 'custom') return 'Kustom';
    return '-';
  }

  function renderActiveSource() {
    const el = $('#ta-active-source');
    if (!el) return;
    el.innerHTML = `<span class="badge">${escapeHtml(formatSourceLabel(activeSource, activeSourceLabel, ''))}</span>`;
  }

  // === Koefisien numeric helpers (dp=12)
  const __NUM = window.Numeric || null;
  const __KOEF_DP = 12;
  const MIN_KOEF = 0.000000000001;
  // Use JS-safe upper bound slightly below backend hard limit to avoid float mismatch.
  const MAX_KOEF = 999999.999999999;
  const DEFAULT_KOEF_CANON = __NUM ? __NUM.enforceDp('1', __KOEF_DP) : '1.000000000000';
  const PARAM_REFRESH_INTERVAL_MS = 15000;
  const KOEF_INPUT_DEBOUNCE_MS = 300;
  let lastParamRefreshAt = 0;
  const koefInputEvalTimers = new WeakMap();
  const formulaEvalSnapshotByJob = {};
  const paramSnapshotByJob = {};
  function __koefToCanon(v) {
    if (!__NUM) return (v ?? '').toString().trim();
    const s = __NUM.canonicalizeForAPI(v ?? '');
    return s ? __NUM.enforceDp(s, __KOEF_DP) : '';
  }
  function __koefToUI(canon) {
    if (!__NUM) return canon ?? '';
    return __NUM.formatForUI(__NUM.enforceDp(canon ?? '', __KOEF_DP));
  }
  function normalizeParamSnapshot(snapshot) {
    const normalized = {};
    Object.entries(snapshot || {}).forEach(([name, value]) => {
      const key = String(name || '').trim().toLowerCase();
      const num = Number(value);
      if (!key || !Number.isFinite(num)) return;
      normalized[key] = num;
    });
    return normalized;
  }
  function getCurrentParamSnapshot() {
    if (paramSidebarEditor && typeof paramSidebarEditor.getSnapshot === 'function') {
      return normalizeParamSnapshot(paramSidebarEditor.getSnapshot());
    }
    if (window.SharedParamStore?.getSnapshot) {
      return normalizeParamSnapshot(window.SharedParamStore.getSnapshot());
    }
    return {};
  }
  function areParamSnapshotsEqual(left, right) {
    const l = left || {};
    const r = right || {};
    const lKeys = Object.keys(l).sort();
    const rKeys = Object.keys(r).sort();
    if (lKeys.length !== rKeys.length) return false;
    for (let i = 0; i < lKeys.length; i += 1) {
      if (lKeys[i] !== rKeys[i]) return false;
      if (Number(l[lKeys[i]]) !== Number(r[rKeys[i]])) return false;
    }
    return true;
  }
  function buildFormulaRowSnapshotFromDom() {
    const snapshot = {};
    $$('tr.ta-row').forEach((tr, idx) => {
      const raw = String(tr.dataset.koefFormulaRaw || '').trim();
      if (tr.dataset.koefIsFx !== '1' || !raw) return;
      const kode = String($('input[data-field="kode"]', tr)?.value || '').trim();
      const key = kode ? `kode:${kode}` : `idx:${idx}`;
      const koefInput = $('input[data-field="koefisien"]', tr);
      const koefCanon = __koefToCanon(koefInput?.value || tr.dataset.lastKoefCanon || '');
      snapshot[key] = {
        kode,
        raw,
        koefCanon: koefCanon || '',
      };
    });
    return snapshot;
  }
  function rememberFormulaEvalSnapshot(jobId, paramSnapshot) {
    if (!jobId) return;
    formulaEvalSnapshotByJob[jobId] = buildFormulaRowSnapshotFromDom();
    if (paramSnapshot) {
      paramSnapshotByJob[jobId] = normalizeParamSnapshot(paramSnapshot);
    }
  }
  function detectFormulaChangeDueToParamUpdate(jobId, latestParamSnapshot) {
    const baselineFormula = formulaEvalSnapshotByJob[jobId] || {};
    const currentFormula = buildFormulaRowSnapshotFromDom();
    const baselineParams = paramSnapshotByJob[jobId] || {};
    const latestParams = normalizeParamSnapshot(latestParamSnapshot || {});
    const paramsChanged = !areParamSnapshotsEqual(baselineParams, latestParams);
    const changedRows = [];

    Object.entries(currentFormula).forEach(([key, current]) => {
      const previous = baselineFormula[key];
      if (!previous) return;
      if (previous.raw !== current.raw) return;
      if ((previous.koefCanon || '') === (current.koefCanon || '')) return;
      changedRows.push({
        key,
        kode: current.kode || previous.kode || '-',
        before: previous.koefCanon || '-',
        after: current.koefCanon || '-',
      });
    });

    return { paramsChanged, changedRows };
  }
  function notifyFormulaDiffIfNeeded(jobId, latestParamSnapshot) {
    if (!jobId) return;
    const { paramsChanged, changedRows } = detectFormulaChangeDueToParamUpdate(jobId, latestParamSnapshot);
    if (!paramsChanged) return;
    if (!changedRows.length) {
      toast('Parameter berubah sejak load. Formula sudah dievaluasi ulang sebelum simpan.', 'info', 3500);
      return;
    }
    const sample = changedRows
      .slice(0, 3)
      .map((row) => `${row.kode}: ${row.before} -> ${row.after}`)
      .join(' | ');
    const suffix = changedRows.length > 3 ? ` (+${changedRows.length - 3} baris)` : '';
    toast(`Nilai parameter berubah. ${changedRows.length} koef formula diperbarui: ${sample}${suffix}`, 'info', 5500);
  }
  function clearKoefInputDebounce(inputEl) {
    const timerId = koefInputEvalTimers.get(inputEl);
    if (timerId) {
      clearTimeout(timerId);
      koefInputEvalTimers.delete(inputEl);
    }
  }
  function scheduleKoefFormulaEvaluate(inputEl, tr) {
    clearKoefInputDebounce(inputEl);
    const raw = String(inputEl?.value || '').trim();
    if (!raw.startsWith('=')) return;

    const timerId = setTimeout(async () => {
      if (!document.body.contains(inputEl)) return;
      const latestRaw = String(inputEl.value || '').trim();
      if (!latestRaw.startsWith('=')) return;
      try {
        const snapshot = await ensureParamSnapshot();
        await evaluateFormulaForKoefInput(tr, latestRaw, { snapshot });
      } catch (err) {
        console.warn('[TA] Debounced formula evaluation failed:', err);
      }
    }, KOEF_INPUT_DEBOUNCE_MS);
    koefInputEvalTimers.set(inputEl, timerId);
  }
  function ensureFxBadge(tr, show, rawFormula) {
    const koefTd = tr.querySelector('td.col-koef');
    if (!koefTd) return;
    let badge = koefTd.querySelector('.ta-fx-badge');
    if (!show) {
      if (badge) badge.remove();
      return;
    }
    if (!badge) {
      badge = document.createElement('span');
      badge.className = 'ta-fx-badge';
      badge.textContent = 'fx';
      koefTd.appendChild(badge);
    }
    badge.title = rawFormula ? `Formula aktif: ${rawFormula}` : 'Formula aktif';
  }
  function applyKoefVisualState(tr, opts = {}) {
    const input = $('input[data-field="koefisien"]', tr);
    if (!input) return;
    const isFx = !!opts.isFx;
    const level = String(opts.level || '').toLowerCase();
    const message = String(opts.message || '').trim();
    const rawFormula = String(opts.rawFormula || '').trim();

    tr.classList.remove('ta-koef-warning', 'ta-koef-error');
    if (level === 'warning') tr.classList.add('ta-koef-warning');
    if (level === 'error') tr.classList.add('ta-koef-error');

    ensureFxBadge(tr, isFx, rawFormula);
    const titleParts = [];
    if (rawFormula) titleParts.push(rawFormula);
    if (message) titleParts.push(message);
    if (titleParts.length) input.title = titleParts.join(' | ');
    else input.removeAttribute('title');
  }
  function clearKoefFormulaState(tr) {
    tr.dataset.koefFormulaRaw = '';
    tr.dataset.koefIsFx = '0';
    tr.dataset.koefFormulaLevel = '';
    tr.dataset.koefFormulaMessage = '';
    applyKoefVisualState(tr, { isFx: false });
  }
  function syncKoefVisualStateFromDataset(tr) {
    const rawFormula = String(tr.dataset.koefFormulaRaw || '').trim();
    const isFx = tr.dataset.koefIsFx === '1' && !!rawFormula;
    const level = String(tr.dataset.koefFormulaLevel || '');
    const message = String(tr.dataset.koefFormulaMessage || '');
    applyKoefVisualState(tr, { isFx, level, message, rawFormula });
  }
  async function refreshParamSnapshot(options = {}) {
    const { force = false } = options;
    if (paramSidebarEditor) {
      if (force && typeof paramSidebarEditor.refresh === 'function') {
        await paramSidebarEditor.refresh();
      }
      lastParamRefreshAt = Date.now();
      return getCurrentParamSnapshot();
    }
    if (!window.SharedParamStore || !endpoints.parameters || !endpoints.computedParameters) {
      return {};
    }
    const now = Date.now();
    const meta = (window.SharedParamStore.getMeta && window.SharedParamStore.getMeta()) || {};
    const staleByTime = !lastParamRefreshAt || ((now - lastParamRefreshAt) > PARAM_REFRESH_INTERVAL_MS);
    const shouldReload = !!force || !meta.loadedAt || staleByTime;
    if (shouldReload) {
      if (meta.loadedAt && typeof window.SharedParamStore.refresh === 'function') {
        await window.SharedParamStore.refresh();
      } else {
        await window.SharedParamStore.load(projectId, {
          parameters: endpoints.parameters,
          computedParameters: endpoints.computedParameters,
        });
      }
      lastParamRefreshAt = now;
    }
    const snapshot = window.SharedParamStore.getSnapshot ? window.SharedParamStore.getSnapshot() : {};
    return normalizeParamSnapshot(snapshot);
  }
  async function ensureParamSnapshot() {
    try {
      return await refreshParamSnapshot({ quiet: true });
    } catch (err) {
      console.warn('[TA] Failed to refresh parameter snapshot:', err);
      return getCurrentParamSnapshot();
    }
  }
  async function evaluateFormulaForKoefInput(tr, rawFormula, options = {}) {
    const input = $('input[data-field="koefisien"]', tr);
    if (!input) return { ok: false, hardError: true, message: "Input koefisien tidak ditemukan" };

    const formulaText = String(rawFormula || '').trim();
    let fallbackCanon = (tr.dataset.lastKoefCanon || "").trim();
    if (!fallbackCanon) fallbackCanon = __koefToCanon(input.value);
    if (!fallbackCanon || isNaN(parseFloat(fallbackCanon))) fallbackCanon = DEFAULT_KOEF_CANON;

    if (!window.FormulaAdapter || typeof window.FormulaAdapter.evaluate !== "function") {
      return { ok: false, hardError: true, message: "Formula adapter tidak tersedia" };
    }

    let snapshot = options.snapshot || null;
    try {
      if (!snapshot) snapshot = await ensureParamSnapshot();
    } catch (err) {
      return {
        ok: false,
        hardError: true,
        message: (err && err.message) ? err.message : "Gagal memuat snapshot parameter",
      };
    }

    tr.dataset.koefFormulaRaw = formulaText;
    tr.dataset.koefIsFx = "1";

    const result = window.FormulaAdapter.evaluate(formulaText, snapshot, { min: MIN_KOEF, max: MAX_KOEF });
    if (result.ok) {
      const canon = __koefToCanon(String(result.value));
      input.value = __koefToUI(canon);
      tr.dataset.lastKoefCanon = canon || fallbackCanon;
      tr.dataset.koefFormulaLevel = "";
      tr.dataset.koefFormulaMessage = "";
      applyKoefVisualState(tr, { isFx: true, rawFormula: formulaText });
      return { ok: true };
    }

    if (result.code === "missing_identifier") {
      input.value = __koefToUI(fallbackCanon);
      tr.dataset.lastKoefCanon = fallbackCanon;
      const warnMessage = `${result.error}. Koefisien memakai nilai terakhir (${fallbackCanon}).`;
      tr.dataset.koefFormulaLevel = "warning";
      tr.dataset.koefFormulaMessage = warnMessage;
      applyKoefVisualState(tr, {
        isFx: true,
        level: 'warning',
        message: warnMessage,
        rawFormula: formulaText,
      });
      return {
        ok: true,
        warning: true,
        message: warnMessage,
      };
    }

    input.value = __koefToUI(fallbackCanon);
    tr.dataset.lastKoefCanon = fallbackCanon;
    const errorMessage = result.error || "Formula tidak valid";
    tr.dataset.koefFormulaLevel = "error";
    tr.dataset.koefFormulaMessage = errorMessage;
    applyKoefVisualState(tr, {
      isFx: true,
      level: 'error',
      message: errorMessage,
      rawFormula: formulaText,
    });
    return { ok: false, hardError: true, message: errorMessage };
  }
  async function reevaluateAllKoefFormulaRows(options = {}) {
    const { snapshot = null, silent = true } = options;
    const rows = $$('tr.ta-row').filter((tr) => {
      const raw = String(tr.dataset.koefFormulaRaw || '').trim();
      return tr.dataset.koefIsFx === '1' && !!raw;
    });
    if (!rows.length) return { ok: true, warnings: 0, errors: 0 };

    let activeSnapshot = snapshot;
    if (!activeSnapshot) activeSnapshot = await ensureParamSnapshot();

    let warnings = 0;
    let errors = 0;
    for (const tr of rows) {
      const raw = String(tr.dataset.koefFormulaRaw || '').trim();
      if (!raw) continue;
      const evalRes = await evaluateFormulaForKoefInput(tr, raw, { snapshot: activeSnapshot });
      if (!evalRes.ok) errors += 1;
      else if (evalRes.warning) warnings += 1;
    }

    if (!silent) {
      if (errors > 0) toast(`${errors} formula koefisien masih error.`, 'warning');
      else if (warnings > 0) toast(`${warnings} formula memakai fallback karena parameter hilang.`, 'warning');
    }
    return { ok: errors === 0, warnings, errors };
  }
  // Auto-format + formula evaluation on blur
  document.addEventListener("blur", async (e) => {
    const el = e.target;
    if (!(el instanceof HTMLInputElement)) return;
    if (!el.classList.contains("num")) return;
    if (el.dataset.field !== "koefisien") return;
    clearKoefInputDebounce(el);
    const tr = el.closest(".ta-row");
    if (!tr) return;

    const rawInput = String(el.value || "").trim();
    if (rawInput.startsWith("=")) {
      const evalRes = await evaluateFormulaForKoefInput(tr, rawInput);
      if (!evalRes.ok) {
        toast(`⚠️ ${evalRes.message || "Formula tidak valid"}`, "warning");
      } else if (evalRes.warning) {
        toast(`⚠️ ${evalRes.message}`, "warning");
      }
      setDirty(true);
      return;
    }

    const canon = __koefToCanon(el.value);
    const num = parseFloat(canon);
    if (isNaN(num) || num < MIN_KOEF) {
      toast(`⚠️ Koefisien harus >= ${MIN_KOEF} (positif)`, "warning");
      el.value = __koefToUI(DEFAULT_KOEF_CANON);
      tr.dataset.lastKoefCanon = DEFAULT_KOEF_CANON;
      clearKoefFormulaState(tr);
      setDirty(true);
    } else if (num > MAX_KOEF) {
      toast(`⚠️ Koefisien maksimal ${MAX_KOEF}`, "warning");
      el.value = __koefToUI(String(MAX_KOEF));
      tr.dataset.lastKoefCanon = __koefToCanon(String(MAX_KOEF));
      clearKoefFormulaState(tr);
      setDirty(true);
    } else {
      el.value = __koefToUI(canon);
      tr.dataset.lastKoefCanon = canon;
      clearKoefFormulaState(tr);
    }
  }, true);

  // --- CSRF helper ---
  function getCookie(name) {
    return document.cookie.split('; ').find(r => r.startsWith(name + '='))?.split('=')[1] || '';
  }
  const CSRF = getCookie('csrftoken');

  // ---------- UTILS ----------
  function urlFor(pattern, id) {
    return pattern.replace(/\/0(\/|$)/, `/${id}$1`);
  }
  async function parseJsonPayload(response, contextLabel) {
    const contentType = String(response?.headers?.get('content-type') || '').toLowerCase();
    const isJson = contentType.includes('application/json');
    let payload = null;

    if (isJson) {
      try {
        payload = await response.json();
      } catch (_err) {
        throw new Error(`${contextLabel} mengembalikan JSON tidak valid.`);
      }
    }

    if (!response.ok) {
      const serverMessage = payload && typeof payload === 'object'
        ? (payload.user_message || payload.message || payload.error || '')
        : '';
      throw new Error(serverMessage || `${contextLabel} gagal (HTTP ${response.status}).`);
    }

    if (!isJson || !payload || typeof payload !== 'object') {
      throw new Error(`${contextLabel} mengembalikan format yang tidak didukung.`);
    }

    return payload;
  }
  function triggerSelectJobInternal(li, id, forceRefresh = false, options = {}) {
    if (!li || !id) return;
    selectJobInternal(li, id, forceRefresh, options).catch((err) => {
      console.warn('[LOAD] Ignored async selection error:', err);
    });
  }
  function setDirty(v) {
    dirty = !!v;
    $('#ta-dirty-dot').hidden = !dirty;
    $('#ta-dirty-text').hidden = !dirty;
    $('#ta-btn-save').disabled = dirty ? false : true;
  }
  function normKoefStrToSend(s) {
    if (s == null) return '';
    return String(s).trim();
  }
  function formatIndex() {
    $$('.ta-row').forEach((tr, i) => $('.row-index', tr).textContent = (i + 1));
  }
  function clearTable(seg) {
    const body = $(`#seg-${seg}-body`);
    body.innerHTML = `<tr class="ta-empty"><td colspan="5">Belum ada item.</td></tr>`;
  }

  function renderRows(seg, rows) {
    const body = $(`#seg-${seg}-body`);
    body.innerHTML = '';
    const tpl = $('#ta-row-template');

    if (!rows.length) {
      body.innerHTML = `<tr class="ta-empty"><td colspan="5">Belum ada item.</td></tr>`;
      return;
    }

    rows.forEach(r => {
      const tr = tpl.content.firstElementChild.cloneNode(true);
      $('.cell-wrap', tr).textContent = r.uraian || '';
      $('input[data-field="kode"]', tr).value = r.kode || '';
      $('input[data-field="satuan"]', tr).value = r.satuan || '';
      // UI koef pakai locale
      const koefInput = $('input[data-field="koefisien"]', tr);
      const koefCanon = __koefToCanon(String(r.koefisien ?? ''));
      koefInput.value = __koefToUI(koefCanon);
      tr.dataset.lastKoefCanon = koefCanon || DEFAULT_KOEF_CANON;
      const formulaRaw = String(r.koef_formula_raw || '').trim();
      const isFx = !!(r.koef_is_fx && formulaRaw);
      tr.dataset.koefFormulaRaw = isFx ? formulaRaw : '';
      tr.dataset.koefIsFx = isFx ? '1' : '0';
      tr.dataset.koefFormulaLevel = '';
      tr.dataset.koefFormulaMessage = '';
      syncKoefVisualStateFromDataset(tr);

      // Hidden ref_ahsp_id dari GET (kalau ada)
      const hid = $('input[data-field="ref_ahsp_id"]', tr);
      if (hid) hid.value = (r.ref_ahsp_id != null ? String(r.ref_ahsp_id) : '');
      // Tandai bundle di LAIN
      if (seg === 'LAIN') {
        const isBundle = !!(hid && hid.value);
        const kodeTd = $('input[data-field="kode"]', tr).closest('td');
        if (isBundle && kodeTd && !kodeTd.querySelector('.tag-bundle')) {
          kodeTd.insertAdjacentHTML('beforeend', ' <span class="tag-bundle">Bundle</span>');
        }
      }

      tr.dataset.kategori = r.kategori;
      // tambahkan checkbox seleksi di kolom nomor
      try { ensureSelectAffordance(tr); } catch (_) { }
      body.appendChild(tr);
    });

    formatIndex();

    // Autocomplete khusus LAIN + sumber CUSTOM
    if (seg === 'LAIN' && activeSource === 'custom') {
      enhanceLAINAutocomplete(body);
    }
  }

  // Tambah checkbox seleksi di kolom nomor jika belum ada
  function ensureSelectAffordance(tr) {
    const noCell = tr.querySelector('td.col-no');
    if (!noCell) return;
    if (noCell.querySelector('.ta-row-check')) return;
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.className = 'form-check-input ta-row-check me-2';
    noCell.prepend(cb);
  }

  // Hitung & tampilkan jumlah baris terseleksi per segmen
  function updateDelState(seg) {
    const body = $(`#seg-${seg}-body`);
    if (!body) return;
    const selected = body.querySelectorAll('.ta-row-check:checked').length;
    const cnt = document.querySelector(`.ta-del-count[data-for="${seg}"]`);
    if (cnt) cnt.textContent = String(selected);
    const btn = document.querySelector(`.ta-seg-del-selected[data-target-seg="${seg}"]`);
    if (btn) btn.disabled = selected === 0;
  }

  function gatherRows() {
    const segs = ['TK', 'BHN', 'ALT', 'LAIN'];
    const out = [];
    segs.forEach(seg => {
      $(`#seg-${seg}-body`)?.querySelectorAll('tr.ta-row')?.forEach(tr => {
        const formulaRaw = (tr.dataset.koefFormulaRaw || '').trim();
        const isFx = tr.dataset.koefIsFx === '1' && !!formulaRaw;
        const base = {
          kategori: seg,
          uraian: $('.cell-wrap', tr).textContent.trim(),
          kode: $('input[data-field="kode"]', tr).value.trim(),
          satuan: $('input[data-field="satuan"]', tr).value.trim(),
          koefisien: normKoefStrToSend($('input[data-field="koefisien"]', tr).value),
          koef_formula_raw: isFx ? formulaRaw : '',
          koef_is_fx: isFx,
        };
        if (seg === 'LAIN' && activeSource === 'custom') {
          const rk = $('input[data-field="ref_kind"]', tr).value.trim();
          const rid = $('input[data-field="ref_id"]', tr).value.trim();
          if (rk && rid) { base.ref_kind = rk; base.ref_id = rid; }
          else {
            const refId = $('input[data-field="ref_ahsp_id"]', tr).value.trim();
            if (refId) base.ref_ahsp_id = refId;
          }
        }
        out.push(base);
      });
    });
    return out;
  }

  // P1.1 FIX: Strengthened client validation
  function validateClient(rows) {
    const errors = [];
    const seen = new Set();
    const MAX_URAIAN_LEN = 500;
    const MAX_KODE_LEN = 100;
    const MAX_SATUAN_LEN = 50;
    const MIN_KOEF = 0.000000000001;  // positive only
    const MAX_KOEF = 999999.999999999;

    rows.forEach((r, i) => {
      // Uraian validation
      if (!r.uraian || !r.uraian.trim()) {
        errors.push({ path: `rows[${i}].uraian`, message: 'Uraian wajib diisi' });
      } else if (r.uraian.length > MAX_URAIAN_LEN) {
        errors.push({ path: `rows[${i}].uraian`, message: `Maksimal ${MAX_URAIAN_LEN} karakter` });
      }

      // Kode validation
      if (!r.kode || !r.kode.trim()) {
        errors.push({ path: `rows[${i}].kode`, message: 'Kode wajib diisi' });
      } else {
        if (r.kode.length > MAX_KODE_LEN) {
          errors.push({ path: `rows[${i}].kode`, message: `Maksimal ${MAX_KODE_LEN} karakter` });
        }
        // Check duplicate
        const key = r.kode.trim();
        if (seen.has(key)) {
          errors.push({ path: `rows[${i}].kode`, message: 'Kode duplikat' });
        }
        seen.add(key);
      }

      // Satuan validation
      if (!r.satuan || !r.satuan.trim()) {
        errors.push({ path: `rows[${i}].satuan`, message: 'Satuan wajib diisi' });
      } else if (r.satuan.length > MAX_SATUAN_LEN) {
        errors.push({ path: `rows[${i}].satuan`, message: `Maksimal ${MAX_SATUAN_LEN} karakter` });
      }

      // Koefisien validation - enhanced numeric check
      if (r.koefisien === '' || r.koefisien == null) {
        errors.push({ path: `rows[${i}].koefisien`, message: 'Koefisien wajib diisi' });
      } else {
        const koefStr = String(r.koefisien).trim();
        const koefNum = parseFloat(__koefToCanon(koefStr));

        if (isNaN(koefNum)) {
          errors.push({ path: `rows[${i}].koefisien`, message: 'Koefisien harus berupa angka' });
        } else if (koefNum < MIN_KOEF) {
          errors.push({ path: `rows[${i}].koefisien`, message: `Koefisien minimal ${MIN_KOEF} (harus positif)` });
        } else if (koefNum > MAX_KOEF) {
          errors.push({ path: `rows[${i}].koefisien`, message: `Koefisien maksimal ${MAX_KOEF}` });
        }
      }

      // Kategori validation
      if (!r.kategori || !['TK', 'BHN', 'ALT', 'LAIN'].includes(r.kategori)) {
        errors.push({ path: `rows[${i}].kategori`, message: 'Kategori tidak valid' });
      }
    });

    return errors;
  }

  // Mode editor berdasarkan sumber row (lock/unlock)
  function setEditorModeBySource() {
    const canSave = (activeSource === 'ref_modified' || activeSource === 'custom') && !readOnly;
    const canReset = (activeSource === 'ref_modified') && !readOnly;

    $('#ta-btn-save').hidden = !canSave;
    $('#ta-btn-save').disabled = !canSave || !dirty;

    const resetBtnEl = $('#ta-btn-reset');
    if (resetBtnEl) resetBtnEl.hidden = !canReset;

    // CACHE FIX: Enable reload button whenever a job is active
    const reloadBtnEl = $('#ta-btn-reload');
    if (reloadBtnEl) {
      reloadBtnEl.disabled = !activeJobId; // Enable if job selected
    }

    const editable = canSave;

    // Enable/disable input & contenteditable
    $$('.ta-row input, .ta-row .cell-wrap').forEach(el => {
      if (editable) {
        el.removeAttribute('disabled');
        if (el.tagName === 'DIV') el.setAttribute('contenteditable', 'true');
      } else {
        if (el.tagName === 'DIV') el.setAttribute('contenteditable', 'false');
        else el.setAttribute('disabled', 'true');
      }
    });

    // Kunci tombol penambah baris saat tidak editable
    const lockBtns = [
      ...$$('.ta-seg-add-catalog'),
      ...$$('.ta-seg-add-empty')
    ].filter(Boolean);
    lockBtns.forEach(btn => { btn.disabled = !editable; });

    document.body.classList.toggle('ta-readonly', !editable);

    // Sinkronkan Select2 (kalau ada)
    if (window.jQuery && jQuery.fn.select2) {
      $$('#seg-LAIN-body input[data-field="kode"]').forEach(inp => {
        const $inp = jQuery(inp);
        if ($inp.data('select2')) {
          $inp.prop('disabled', !editable);
          $inp.trigger('change.select2');
        }
      });
    }
  }

  function enhanceLAINAutocomplete(scopeEl) {
    if (!window.jQuery || !jQuery.fn.select2 || !endpoints.searchAhsp) return;
    const scope = scopeEl || document;
    const selector = scopeEl
      ? '.ta-row input[data-field="kode"]'
      : '#seg-LAIN-body .ta-row input[data-field="kode"]';

    $$(selector, scope).forEach(input => {
      const tr = input.closest('tr.ta-row');
      const $input = jQuery(input);
      if ($input.data('hasSelect2')) return;

      function localProjectOptions(term) {
        const q = String(term || '').toLowerCase();
        const items = [];
        document.querySelectorAll('#ta-job-list .ta-job-item').forEach(li => {
          const id = parseInt(li.getAttribute('data-pekerjaan-id') || '0', 10);
          const kode = (li.querySelector('.kode')?.textContent || '').trim();
          const uraian = (li.querySelector('.uraian')?.textContent || '').trim();
          const satuan = (li.querySelector('.satuan')?.textContent || '').trim();
          if (!id) return;
          const hay = `${kode} ${uraian}`.toLowerCase();
          if (q && !hay.includes(q)) return;
          const badge = formatSourceLabel(
            li.getAttribute('data-source-type'),
            li.getAttribute('data-source-label'),
            li.getAttribute('data-ahsp-sumber')
          );
          items.push({
            id: `job:${id}`,
            text: `[${badge || 'JOB'}] ${kode} - ${uraian}`,
            kode_job: kode,
            nama_job: uraian,
            satuan: satuan || ''
          });
        });
        return items.slice(0, 20);
      }

      $input.select2({
        ajax: {
          url: endpoints.searchAhsp,
          delay: 250,
          data: params => ({ q: params.term }),
          processResults: (data, params) => {
            const remote = (data.results || []).map(x => {
              // Extract year/version from sumber (e.g., "AHSP SNI 2025" -> "SNI 2025")
              const sumberLabel = x.sumber ? ` (${x.sumber.replace(/^AHSP\s*/i, '')})` : '';
              return {
                id: `ahsp:${x.id}`,
                text: `${x.kode_ahsp} - ${x.nama_ahsp}${sumberLabel}`,
                kode_ahsp: x.kode_ahsp,
                nama_ahsp: x.nama_ahsp,
                satuan: x.satuan || '',
                sumber: x.sumber || ''
              };
            });
            const local = localProjectOptions(params?.term);
            const groups = [];
            if (local.length) groups.push({ text: 'Pekerjaan Proyek', children: local });
            if (remote.length) groups.push({ text: 'Master AHSP', children: remote });
            return { results: groups.length ? groups : [] };
          }
        },
        minimumInputLength: 1,
        width: 'resolve',
        placeholder: 'Cari AHSP atau Pekerjaan...',
        dropdownAutoWidth: true
      });

      $input.on('select2:select', async (e) => {
        const d = e.params.data || {};
        let kind = 'ahsp';
        let refId = '';
        let kode = '';
        let nama = '';
        let sat = d.satuan || '';
        const sid = String(d.id || '');
        if (sid.startsWith('job:')) {
          kind = 'job';
          refId = sid.split(':')[1] || '';
          kode = d.kode_job || '';
          nama = d.nama_job || '';
        } else {
          kind = 'ahsp';
          refId = sid.split(':')[1] || sid;
          kode = d.kode_ahsp || '';
          nama = d.nama_ahsp || '';
        }

        // P1.2 FIX: Add loading state during bundle validation
        if (kind === 'job' && refId) {
          // Show loading toast
          const loadingMsg = `ðŸ” Memeriksa bundle "${kode}"...`;
          toast(loadingMsg, 'info', 0); // No auto-dismiss during loading

          try {
            // Fetch job details to validate it has components with timeout
            const validateUrl = urlFor(endpoints.get, parseInt(refId));
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 sec timeout

            const resp = await fetch(validateUrl, {
              credentials: 'same-origin',
              signal: controller.signal
            });
            clearTimeout(timeoutId);

            const data = await resp.json();

            if (data.ok && (!data.items || data.items.length === 0)) {
              // Bundle is empty - show warning and prevent selection
              toast(`âš ï¸ Bundle Kosong: "${nama}" belum memiliki komponen AHSP.\n\nSilakan isi detail AHSP untuk pekerjaan tersebut terlebih dahulu sebelum menggunakan sebagai bundle.`, 'warning', 5000);
              console.warn('[BUNDLE_VALIDATION] Empty bundle detected:', kode, nama);

              // Clear the selection
              $input.val(null).trigger('change');
              return; // Don't proceed with selection
            }

            console.log('[BUNDLE_VALIDATION] Bundle valid:', kode, 'has', data.items?.length || 0, 'components');
            toast(`âœ… Bundle "${kode}" valid (${data.items?.length || 0} komponen)`, 'success', 2000);

          } catch (err) {
            if (err.name === 'AbortError') {
              console.error('[BUNDLE_VALIDATION] Timeout validating bundle:', kode);
              toast('â±ï¸ Timeout saat validasi bundle. Lanjutkan dengan hati-hati.', 'warning', 4000);
            } else {
              console.error('[BUNDLE_VALIDATION] Error validating bundle:', err);
              toast('âš ï¸ Tidak dapat validasi bundle. Lanjutkan dengan hati-hati.', 'warning', 4000);
            }
            // Don't block - let backend handle validation
          }
        }

        // AHSP bundles are now supported! Backend will expand them recursively

        input.value = kode;
        $('.cell-wrap', tr).textContent = nama;
        $('input[data-field="satuan"]', tr).value = sat;
        $('input[data-field="ref_kind"]', tr).value = kind;
        $('input[data-field="ref_id"]', tr).value = String(refId || '');
        $('input[data-field="ref_ahsp_id"]', tr).value = (kind === 'ahsp' ? String(refId || '') : '');
        // FIX: Set default koefisien = 1 jika kosong (prevent validation error)
        const koefInput = $('input[data-field="koefisien"]', tr);
        if (!koefInput.value.trim()) {
          koefInput.value = __koefToUI(DEFAULT_KOEF_CANON);
        }
        tr.dataset.lastKoefCanon = __koefToCanon(koefInput.value) || DEFAULT_KOEF_CANON;
        clearKoefFormulaState(tr);
        const kodeTd = input.closest('td');
        if (kodeTd && !kodeTd.querySelector('.tag-bundle')) {
          kodeTd.insertAdjacentHTML('beforeend', ' <span class="tag-bundle">Bundle</span>');
        }
        setDirty(true);
      });

      // Edit manual kode â†’ kosongkan ref id
      input.addEventListener('input', () => {
        $('input[data-field="ref_ahsp_id"]', tr).value = '';
        $('input[data-field="ref_kind"]', tr).value = '';
        $('input[data-field="ref_id"]', tr).value = '';
        const b = tr.querySelector('.tag-bundle');
        if (b) b.remove();
      });

      $input.data('hasSelect2', true);
    });
  }

  // ---------- LOAD ----------
  function selectJob(li) {
    const id = +li.dataset.pekerjaanId;
    if (!id || id === activeJobId) return;

    // P0.1 FIX: Promise-based auto-save - no more race condition!
    if (dirty && activeJobId) {
      const currentJobEl = $(`.ta-job-item[data-pekerjaan-id="${activeJobId}"]`);
      const currentKode = currentJobEl?.querySelector('.kode')?.textContent?.trim() || 'pekerjaan ini';
      const targetKode = li.querySelector('.kode')?.textContent?.trim() || 'pekerjaan lain';

      const confirmMsg = `âš ï¸ PERUBAHAN BELUM TERSIMPAN!\n\nAnda memiliki perubahan yang belum disimpan pada "${currentKode}".\n\nPilih tindakan:\nâ€¢ OK = Simpan dulu, lalu pindah ke "${targetKode}"\nâ€¢ Cancel = Tetap di "${currentKode}"`;

      if (!confirm(confirmMsg)) {
        console.log('[SELECT_JOB] User cancelled job switch due to unsaved changes');
        return; // Stay on current job
      }

      // User chose to save first - use Promise to wait for completion
      console.log('[SELECT_JOB] Auto-saving before job switch...');
      toast('ðŸ’¾ Menyimpan perubahan...', 'info', 2000);

      doSave(activeJobId).then(() => {
        console.log('[SELECT_JOB] Save completed successfully, switching job...');
        toast('âœ… Tersimpan! Beralih ke pekerjaan lain...', 'success', 1500);
        // Wait a bit for user to see success message
        setTimeout(() => triggerSelectJobInternal(li, id), 500);
      }).catch((err) => {
        console.error('[SELECT_JOB] Save failed:', err);
        toast('âŒ Gagal menyimpan. Tetap di pekerjaan ini.', 'error');
        // Stay on current job if save fails
      });
      return;
    }

    // P2 FIX: Auto-reload stale jobs silently in background
    // No more invasive blocker - just seamless refresh
    const requiresReload = jobNeedsReload(id);
    if (requiresReload) {
      console.log('[SELECT_JOB] Job requires reload - auto-reloading silently');
      toast('ðŸ”„ Memuat data terbaru...', 'info', 2000);
    }

    // Proceed with job selection - forceRefresh will be handled by selectJobInternal
    triggerSelectJobInternal(li, id, requiresReload);
  }

  // Internal function to actually perform job selection (without checks)
  // forceRefresh: if true, bypass cache and fetch fresh data from server
  function selectJobInternal(li, id, forceRefresh = false, options = {}) {
    const skipFormulaReeval = !!options.skipFormulaReeval;
    activeJobId = id;
    activeSource = li.dataset.sourceType;
    activeSourceLabel = li.dataset.sourceLabel || formatSourceLabel(
      li.dataset.sourceType,
      '',
      li.dataset.ahspSumber
    );
    $$('.ta-job-item').forEach(n => n.classList.toggle('is-active', n === li));
    $('#ta-active-kode').textContent = $('.kode', li)?.textContent?.trim() || '-';
    $('#ta-active-uraian').textContent = $('.uraian', li)?.textContent?.trim() || '-';
    $('#ta-active-satuan').textContent = $('.satuan', li)?.textContent?.trim() || '-';
    renderActiveSource();
    setDirty(false);
    const flaggedBefore = jobNeedsReload(id);
    const requiresReload = forceRefresh || flaggedBefore;
    const hasCache = !!rowsByJob[id];

    // P1 FIX: Check cache expiry - prevent stale data
    const cache = rowsByJob[id];
    const cacheExpired = cache && cache.cachedAt
      ? (Date.now() - cache.cachedAt > CACHE_TTL_MS)
      : false;

    if (cacheExpired) {
      console.log('[CACHE] Cache expired for job', id, '- age:', Math.round((Date.now() - cache.cachedAt) / 1000), 'seconds');
    }

    const needsFetch = requiresReload || !hasCache || cacheExpired;

    // Use cache only when fresh and no reload requested
    if (!needsFetch && hasCache) {
      console.log('[CACHE] Using fresh cache for job', id, '- age:', Math.round((Date.now() - cache.cachedAt) / 1000), 'seconds');
      paint(rowsByJob[id].items);
      kategoriMeta = rowsByJob[id].kategoriMeta || kategoriMeta;
      readOnly = rowsByJob[id].readOnly || false;
      activeSourceLabel = rowsByJob[id].sourceLabel || activeSourceLabel;
      renderActiveSource();
      setEditorModeBySource();
      toggleEditorBlocker(false);
      if (skipFormulaReeval) {
        return Promise.resolve();
      }
      return refreshParamSnapshot({ quiet: true })
        .then((snapshot) => reevaluateAllKoefFormulaRows({ snapshot, silent: true }))
        .then((reevalRes) => {
          rememberFormulaEvalSnapshot(id, getCurrentParamSnapshot());
          return reevalRes;
        })
        .catch((err) => {
          console.warn('[TA] Skipping formula re-evaluation (cache path):', err);
        });
    }

    // P2 FIX: Show loading placeholder, but NO invasive blocker
    if (!hasCache || requiresReload) {
      showLoadingPlaceholder();
    }

    // fetch
    const url = urlFor(endpoints.get, id);
    return fetch(url, { credentials: 'same-origin' }).then((r) => parseJsonPayload(r, 'Muat detail pekerjaan')).then(js => {
      if (!js.ok) throw new Error(js.user_message || 'Gagal memuat detail pekerjaan.');
      const items = js.items || [];
      kategoriMeta = js.meta?.kategori_opts || kategoriMeta;
      readOnly = !!js.meta?.read_only;

      // OPTIMISTIC LOCKING: Store timestamp when data is loaded
      const updatedAt = js.pekerjaan?.updated_at || null;

      // P1 FIX: Store cache timestamp for TTL check
      rowsByJob[id] = {
        items,
        kategoriMeta,
        readOnly,
        sourceLabel: js.pekerjaan?.source_label || activeSourceLabel,
        updatedAt,
        cachedAt: Date.now() // Track when cache was created
      };
      activeSourceLabel = rowsByJob[id].sourceLabel;
      renderActiveSource();
      paint(items);
      setEditorModeBySource();
      if (flaggedBefore) {
        resolveReloadJob(id);
      }
      if (skipFormulaReeval) {
        return;
      }
      return refreshParamSnapshot({ quiet: true })
        .then((snapshot) => reevaluateAllKoefFormulaRows({ snapshot, silent: true }))
        .then((reevalRes) => {
          rememberFormulaEvalSnapshot(id, getCurrentParamSnapshot());
          return reevalRes;
        })
        .catch((err) => {
          console.warn('[TA] Skipping formula re-evaluation (fetch path):', err);
        });
    }).catch((err) => {
      // P2.2 FIX: Offer retry on network error
      console.error('[LOAD] Fetch failed:', err);
      const msg = err?.message || 'Gagal memuat data pekerjaan.';
      const retry = confirm(`Gagal memuat data pekerjaan.\n\n${msg}\n\nCoba lagi?`);
      if (retry) {
        console.log('[LOAD] User requested retry');
        return selectJobInternal(li, id, true); // Force refresh retry
      }
      toast(msg, 'error');
      throw err;
    });
  }

  function paint(items) {
    const by = { TK: [], BHN: [], ALT: [], LAIN: [] };
    (items || []).forEach(r => {
      const seg = by[r.kategori] ? r.kategori : 'LAIN';
      by[seg].push(r);
    });
    ['TK', 'BHN', 'ALT', 'LAIN'].forEach(seg => renderRows(seg, by[seg]));
    updateStats();
  }

  function showLoadingPlaceholder() {
    ['TK', 'BHN', 'ALT', 'LAIN'].forEach((seg) => {
      const body = $(`#seg-${seg}-body`);
      if (!body) return;
      body.innerHTML = `<tr class="ta-empty"><td colspan="5">Memuat data...</td></tr>`;
    });
  }

  function jobNeedsReload(id) {
    return pendingReloadJobs.has(Number(id));
  }

  function syncPendingState(state) {
    if (!state || !state.reload) {
      pendingReloadJobs = new Set();
      return;
    }
    pendingReloadJobs = new Set(
      Object.keys(state.reload).map((key) => Number(key)).filter((id) => Number.isFinite(id)),
    );
  }

  function updateJobBadges() {
    const items = $$('#ta-job-list .ta-job-item');
    items.forEach((li) => {
      const id = Number(li.dataset.pekerjaanId);
      const needsReload = jobNeedsReload(id);
      li.classList.toggle('ta-job-item--stale', needsReload);
      const meta = li.querySelector('.meta');
      if (!meta) return;
      let pill = meta.querySelector('.ta-job-pill');
      if (needsReload) {
        if (!pill) {
          pill = document.createElement('span');
          pill.className = 'ta-job-pill';
          pill.textContent = 'Perlu reload';
          meta.appendChild(pill);
        }
      } else if (pill) {
        pill.remove();
      }
    });
  }

  function updateBanner() {
    if (!bannerEl) return;
    const pendingCount = pendingReloadJobs.size;
    const shouldShow = pendingCount > 0 || changeStatusPending;
    bannerEl.classList.toggle('d-none', !shouldShow);
    if (!shouldShow) return;

    // P2 FIX: Friendlier banner messages - emphasize auto-reload
    const messages = [];
    if (pendingCount > 0) {
      messages.push(`${pendingCount} pekerjaan memiliki pembaruan. Data akan dimuat otomatis saat dibuka.`);
    }
    if (changeStatusPending) {
      messages.push('Ada perubahan terbaru pada Template AHSP.');
    }
    if (bannerTextEl) {
      bannerTextEl.textContent = messages.join(' ');
    }
  }

  function acknowledgePekerjaanSyncIfSettled() {
    if (pendingReloadJobs.size > 0) return;
    window.dispatchEvent(new CustomEvent('dp:sync-led-ack', {
      detail: {
        projectId,
        pekerjaan: true,
      },
    }));
    changeStatusPending = false;
    updateBanner();
  }

  function toggleEditorBlocker(show) {
    // P2 FIX: Blocker disabled - auto-reload is seamless now
    // Keep function for backward compatibility but don't actually block
    if (!editorBlocker) return;
    // Always keep it hidden
    editorBlocker.classList.add('d-none');
    console.log('[BLOCKER] Blocker toggle disabled - seamless reload enabled');
  }

  function setReloadButtonsState(isLoading) {
    [bannerReloadBtn, editorReloadBtn].forEach((btn) => {
      if (!btn) return;
      btn.classList.toggle('is-loading', !!isLoading);
      if (isLoading) {
        btn.setAttribute('disabled', 'disabled');
      } else {
        btn.removeAttribute('disabled');
      }
    });
  }

  function resolveReloadJob(jobId) {
    if (!jobNeedsReload(jobId)) return;
    pendingReloadJobs.delete(Number(jobId));
    try {
      sourceChange?.markReloaded(projectId, [jobId]);
    } catch (err) {
      console.warn('[TA] Failed to mark reload job resolved', err);
    }
    updateJobBadges();
    updateBanner();
    acknowledgePekerjaanSyncIfSettled();
    // P2 FIX: No more blocker toggle - auto-reload is seamless
  }

  async function reloadJobs(jobIds, options = {}) {
    const rawIds = Array.isArray(jobIds) ? jobIds : [];
    const uniqueIds = Array.from(new Set(rawIds.map((id) => Number(id)))).filter((id) => Number.isFinite(id));
    const isSilent = !!options.silent;
    const queueMode = !!options.queue || isSilent;
    if (!uniqueIds.length) {
      if (!isSilent) {
        toast('Tidak ada pekerjaan yang dipilih untuk dimuat ulang.', 'info');
      }
      return Promise.resolve();
    }
    if (reloadInFlight && !queueMode) {
      if (!isSilent) {
        toast('Proses muat ulang masih berjalan. Tunggu sebentar.', 'info');
      }
      return Promise.resolve();
    }

    const run = async () => {
      reloadInFlight = true;
      const manageButtons = !isSilent;
      if (manageButtons) {
        setReloadButtonsState(true);
      }
      const preserveSelection = options?.preserveSelection !== false;
      const originalJobId = preserveSelection ? activeJobId : null;
      const originalJobEl = originalJobId ? $(`.ta-job-item[data-pekerjaan-id="${originalJobId}"]`) : null;
      let successCount = 0;
      let failure = null;
      try {
        for (const id of uniqueIds) {
          const li = $(`.ta-job-item[data-pekerjaan-id="${id}"]`);
          if (!li) {
            console.warn('[TA] Tidak menemukan elemen pekerjaan untuk reload massal', id);
            resolveReloadJob(id);
            continue;
          }
          try {
            const skipFormulaReeval = !!(preserveSelection && originalJobId && id !== originalJobId);
            await selectJobInternal(li, id, true, { skipFormulaReeval });
            successCount += 1;
          } catch (err) {
            failure = err;
            break;
          }
        }
      } finally {
        reloadInFlight = false;
        if (manageButtons) {
          setReloadButtonsState(false);
        }
      }

      if (preserveSelection && originalJobEl && activeJobId !== originalJobId) {
        await selectJobInternal(originalJobEl, originalJobId, jobNeedsReload(originalJobId));
      }

      if (failure) {
        console.error('[TA] Reload jobs halted', failure);
        toast('Sebagian pekerjaan gagal dimuat ulang. Coba lagi.', 'error');
        throw failure;
      }
      if (!successCount) {
        if (!isSilent) {
          toast('Tidak ada pekerjaan yang perlu dimuat ulang.', 'info');
        }
        return;
      }
      if (!isSilent) {
        const msg = successCount === 1
          ? 'Pekerjaan berhasil dimuat ulang.'
          : `${successCount} pekerjaan berhasil dimuat ulang.`;
        toast(msg, 'success');
      }
    };

    if (queueMode) {
      const nextTask = reloadQueue.catch(() => { }).then(() => run());
      reloadQueue = nextTask.catch(() => { });
      return nextTask;
    }
    return run();
  }

  function forceReloadActiveJob() {
    if (!activeJobId) {
      toast('Pilih pekerjaan yang ingin dimuat ulang.', 'warning');
      return Promise.resolve();
    }
    const currentJobEl = $(`.ta-job-item[data-pekerjaan-id="${activeJobId}"]`);
    if (!currentJobEl) {
      toast('Pekerjaan tidak ditemukan.', 'error');
      return Promise.resolve();
    }
    return reloadJobs([activeJobId], { preserveSelection: true });
  }

  function scheduleAutoReloadPendingJobs(reason = 'open') {
    if (!pendingReloadJobs.size || dirty) return;
    if (autoReloadPendingTimer) {
      clearTimeout(autoReloadPendingTimer);
    }
    autoReloadPendingTimer = setTimeout(() => {
      autoReloadPendingTimer = null;
      autoReloadPendingJobs(reason).catch((err) => {
        console.warn('[TA] Auto reload pending jobs failed:', err);
      });
    }, 900);
  }

  async function autoReloadPendingJobs(reason = 'open') {
    if (autoReloadPendingInFlight || reloadInFlight || dirty || !pendingReloadJobs.size) return;
    autoReloadPendingInFlight = true;
    const targets = Array.from(pendingReloadJobs);
    try {
      console.info('[TA] Auto-reloading pending Template AHSP jobs', { reason, count: targets.length });
      await reloadJobs(targets, {
        preserveSelection: !!activeJobId,
        queue: true,
        silent: true,
      });
    } finally {
      autoReloadPendingInFlight = false;
    }
  }

  function updateStats() {
    const n = $$('.ta-row').length;
    $('#ta-row-stats').textContent = `${n} baris`;
  }

  function initParamOverlay() {
    const sidebar = paramSidebarEl;
    if (!sidebar) return;
    const panel = $('.dp-sidebar-inner', sidebar) || sidebar;
    const closeBtn = $('[data-action="close-param-sidebar"]', sidebar);
    const toggleBtn = paramSidebarToggleBtn;
    const hotspot = paramSidebarHotspotEl;
    const canHover = !!window.matchMedia && window.matchMedia('(hover: hover)').matches;
    let pinned = false;
    let closeTimer = null;

    const isOpen = () => sidebar.classList.contains('is-open') || sidebar.getAttribute('aria-hidden') === 'false';
    const applyAria = (open) => {
      sidebar.setAttribute('aria-hidden', open ? 'false' : 'true');
      sidebar.setAttribute('role', open ? 'dialog' : 'complementary');
      if (open) sidebar.setAttribute('aria-modal', 'true');
      else sidebar.removeAttribute('aria-modal');
      if (toggleBtn) toggleBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (hotspot) hotspot.classList.toggle('is-open', open);
    };
    const openSidebar = ({ by = 'api', pin = false } = {}) => {
      if (closeTimer) {
        clearTimeout(closeTimer);
        closeTimer = null;
      }
      sidebar.classList.add('is-open');
      applyAria(true);
      if (pin) pinned = true;
      if (by !== 'hover') {
        const focusTarget = closeBtn || panel || sidebar;
        if (focusTarget && !focusTarget.hasAttribute('tabindex')) focusTarget.setAttribute('tabindex', '-1');
        try { focusTarget?.focus?.(); } catch (_) { }
      }
    };
    const closeSidebar = ({ by = 'api', force = false } = {}) => {
      if (!isOpen()) return;
      if (pinned && by !== 'button' && !force) return;
      sidebar.classList.remove('is-open');
      applyAria(false);
      if (by === 'button' || force) pinned = false;
    };
    const scheduleClose = (ms = 180) => {
      if (!canHover || pinned) return;
      if (closeTimer) clearTimeout(closeTimer);
      closeTimer = setTimeout(() => closeSidebar({ by: 'hover' }), ms);
    };

    toggleBtn?.addEventListener('click', (event) => {
      event.preventDefault();
      if (isOpen() && pinned) closeSidebar({ by: 'button', force: true });
      else openSidebar({ by: 'button', pin: true });
    });
    closeBtn?.addEventListener('click', (event) => {
      event.preventDefault();
      closeSidebar({ by: 'button', force: true });
    });
    hotspot?.addEventListener('mouseenter', () => {
      if (!canHover) return;
      openSidebar({ by: 'hover', pin: false });
    });
    hotspot?.addEventListener('mouseleave', () => scheduleClose(220));
    sidebar.addEventListener('mouseenter', () => {
      if (closeTimer) {
        clearTimeout(closeTimer);
        closeTimer = null;
      }
    });
    sidebar.addEventListener('mouseleave', () => scheduleClose(220));
    sidebar.addEventListener('click', (event) => {
      if (pinned) return;
      if (panel && !panel.contains(event.target)) {
        closeSidebar({ by: 'outside' });
      }
    });
    document.addEventListener('mousedown', (event) => {
      if (!isOpen() || pinned) return;
      const insideSidebar = sidebar.contains(event.target);
      const onToggle = toggleBtn ? toggleBtn.contains(event.target) : false;
      const onHotspot = hotspot ? hotspot.contains(event.target) : false;
      if (!insideSidebar && !onToggle && !onHotspot) {
        closeSidebar({ by: 'outside' });
      }
    });
    document.addEventListener('keydown', (event) => {
      if (event.key !== 'Escape' || !isOpen()) return;
      closeSidebar({ by: 'esc', force: true });
    });

    applyAria(false);
    window.taParamSidebar = {
      open: () => openSidebar({ by: 'api' }),
      close: () => closeSidebar({ by: 'api', force: true }),
      toggle: () => (isOpen() ? closeSidebar({ by: 'api', force: true }) : openSidebar({ by: 'api', pin: true })),
    };
  }
  function mapSidebarToastType(type) {
    const safe = String(type || 'info').toLowerCase();
    if (safe === 'danger') return 'error';
    if (safe === 'warn') return 'warning';
    return safe;
  }
  function initParameterSidebarCrud() {
    if (!paramSidebarEl || !window.ParamSidebarEditor) return;

    if (window.FormulaEditorModal && typeof window.FormulaEditorModal.init === 'function') {
      window.FormulaEditorModal.init({
        formulaEditorModalId: 'taFormulaEditorModal',
        paramPaletteModalId: 'taParamPaletteModal',
        idPrefix: 'ta-fe-',
        paletteIdPrefix: 'ta-palette-',
        formulaLabelOnlyUiEnabled: true,
      });
    }

    try {
      window.ParamSidebarEditor.init({
        projectId,
        opaqueIdEnabled: String(app.dataset.opaqueIdEnabled || '1') === '1',
        container: paramSidebarEl,
        endpoints: {
          parameters: endpoints.parameters,
          parametersSync: app.dataset.endpointParametersSync || '',
          parameterDetail: app.dataset.endpointParameterDetailPattern || '',
          computedParameters: endpoints.computedParameters,
          computedParametersSync: app.dataset.endpointComputedParametersSync || '',
        },
        formulaEditorModalId: 'taFormulaEditorModal',
        paramPaletteModalId: 'taParamPaletteModal',
        toast: (msg, type = 'info', delay = 3000) => toast(msg, mapSidebarToastType(type), delay),
        csrf: () => CSRF,
      });
      paramSidebarEditor = window.ParamSidebarEditor;

      if (typeof paramSidebarEditor.onParamsChanged === 'function') {
        paramSidebarEditor.onParamsChanged((snapshot) => {
          if (!activeJobId) return;
          const normalized = normalizeParamSnapshot(snapshot || {});
          reevaluateAllKoefFormulaRows({ snapshot: normalized, silent: true })
            .then(() => rememberFormulaEvalSnapshot(activeJobId, normalized))
            .catch((err) => console.warn('[TA] Failed to auto re-evaluate koef after parameter change:', err));
        });
      }
    } catch (err) {
      console.error('[TA] Failed to initialize parameter sidebar editor:', err);
      toast('Gagal menginisialisasi sidebar parameter.', 'error');
    }
  }

  updateJobBadges();
  updateBanner();
  initParamOverlay();
  initParameterSidebarCrud();

  // ---------- EVENTS ----------
  // pilih pekerjaan
  $$('#ta-job-list .ta-job-item').forEach(li => {
    li.addEventListener('click', () => selectJob(li));
    li.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectJob(li); } });
  });

  if (projectId && sourceChange) {
    window.addEventListener('dp:source-change', (event) => {
      const detail = event.detail || {};
      if (Number(detail.projectId) !== projectId) return;
      if (detail.state) {
        syncPendingState(detail.state);
        updateJobBadges();
        updateBanner();
        scheduleAutoReloadPendingJobs('source-change-sync');
      }
    });
  }

  if (projectId) {
    window.addEventListener('dp:change-status', (event) => {
      const detail = event.detail || {};
      if (Number(detail.projectId) !== projectId) return;
      if (detail.scope && detail.scope !== 'template') return;
      if (typeof detail.hasChanges === 'undefined') return;
      changeStatusPending = !!detail.hasChanges;
      updateBanner();
    });

    window.addEventListener('dp:sync-refresh-request', (event) => {
      const detail = event.detail || {};
      if (Number(detail.projectId) !== projectId) return;
      if (detail.scope && detail.scope !== 'template' && detail.scope !== 'global') return;

      event.preventDefault();

      const isAuto = detail.reason === 'auto';
      const runReload = () => {
        const targets = pendingReloadJobs.size
          ? Array.from(pendingReloadJobs)
          : (activeJobId ? [activeJobId] : []);
        if (!targets.length) {
          if (!isAuto) toast('Semua pekerjaan sudah terbaru.', 'info');
          return Promise.resolve();
        }
        return reloadJobs(targets, {
          preserveSelection: !!activeJobId,
          queue: true,
          silent: isAuto,
        });
      };

      if (dirty && activeJobId) {
        if (isAuto) {
          toast('Simpan perubahan aktif sebelum sinkronisasi otomatis.', 'warning');
          return;
        }
        const confirmSync = confirm(
          'Anda memiliki perubahan yang belum disimpan.\n\nSimpan dulu lalu sinkronkan data terbaru?'
        );
        if (!confirmSync) return;
        doSave(activeJobId)
          .then(() => runReload())
          .catch(() => { });
        return;
      }

      runReload().catch(() => { });
    });
  }

  bannerReloadBtn?.addEventListener('click', (event) => {
    event.preventDefault();
    if (!pendingReloadJobs.size) {
      toast('Semua pekerjaan sudah terbaru.', 'info');
      return;
    }
    reloadJobs(Array.from(pendingReloadJobs), { preserveSelection: !!activeJobId }).catch(() => { });
  });
  editorReloadBtn?.addEventListener('click', (event) => {
    event.preventDefault();
    forceReloadActiveJob().catch(() => { });
  });

  // ===== Checkbox Filter (REF/MOD/CUS) =====
  const filterChecks = $$('.ta-filter-check');
  const countVisibleEl = $('#ta-count-visible');

  function getActiveSourceTypes() {
    const checked = $$('.ta-filter-check:checked');
    return checked.map(cb => cb.value);
  }

  function applyJobFilters() {
    const q = jobFilterEl?.value?.toLowerCase() || '';
    const activeTypes = getActiveSourceTypes();
    let visibleCount = 0;

    $$('#ta-job-list .ta-job-item').forEach(li => {
      const matchesText = li.textContent.toLowerCase().includes(q);
      const sourceType = li.dataset.sourceType || '';
      const matchesSource = activeTypes.length === 0 || activeTypes.includes(sourceType);
      const isVisible = matchesText && matchesSource;
      li.hidden = !isVisible;
      if (isVisible) visibleCount++;
    });

    // Update visible count badge
    if (countVisibleEl) countVisibleEl.textContent = visibleCount;
  }

  // Checkbox change event
  filterChecks.forEach(cb => {
    cb.addEventListener('change', applyJobFilters);
  });

  // Reset filter button
  const filterResetBtn = $('#ta-filter-reset');
  if (filterResetBtn) {
    filterResetBtn.addEventListener('click', () => {
      filterChecks.forEach(cb => cb.checked = true);
      if (jobFilterEl) jobFilterEl.value = '';
      applyJobFilters();
    });
  }

  // Text filter
  const jobFilterEl = $('#ta-job-search');
  if (jobFilterEl) {
    jobFilterEl.addEventListener('input', () => applyJobFilters());
  }

  // add empty row (per-segmen)
  $$('.ta-seg-add-empty').forEach(btn => {
    btn.addEventListener('click', () => {
      if (activeSource === 'ref') return; // read-only
      const seg = btn.dataset.targetSeg;
      const body = $(`#seg-${seg}-body`);
      const tpl = $('#ta-row-template');
      const tr = tpl.content.firstElementChild.cloneNode(true);
      tr.dataset.kategori = seg;
      if ($('.ta-empty', body)) body.innerHTML = '';
      try { ensureSelectAffordance(tr); } catch (_) { }
      // FIX: Set default koefisien = 1 untuk row baru (prevent validation error)
      const koefInput = $('input[data-field="koefisien"]', tr);
      if (koefInput) koefInput.value = __koefToUI(DEFAULT_KOEF_CANON);
      tr.dataset.lastKoefCanon = DEFAULT_KOEF_CANON;
      clearKoefFormulaState(tr);
      body.appendChild(tr);
      formatIndex();
      setDirty(true);
      setEditorModeBySource();
      if (seg === 'LAIN' && activeSource === 'custom') {
        enhanceLAINAutocomplete(body);
      }
      try { updateDelState(seg); } catch (_) { }
    });
  });

  // input change -> dirty
  app.addEventListener('input', (e) => {
    if (!e.target.closest('.ta-row')) return;
    if (activeSource === 'ref') return;
    if (e.target instanceof HTMLInputElement && e.target.dataset.field === 'koefisien') {
      const tr = e.target.closest('.ta-row');
      if (tr) {
        const rawInput = String(e.target.value || '').trim();
        if (rawInput.startsWith('=')) {
          tr.dataset.koefFormulaRaw = rawInput;
          tr.dataset.koefIsFx = '1';
          scheduleKoefFormulaEvaluate(e.target, tr);
          setDirty(true);
          return;
        }
        tr.dataset.lastKoefCanon = __koefToCanon(e.target.value) || tr.dataset.lastKoefCanon || DEFAULT_KOEF_CANON;
        clearKoefFormulaState(tr);
      }
    }
    setDirty(true);
  });
  app.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
      e.preventDefault();
      $('#ta-btn-save').click();
    }
  });

  // P0.1: Refactor save logic into reusable function
  async function doSave(jobId) {
    if (!jobId) return Promise.reject(new Error('No job selected'));

    let saveSnapshot = {};
    try {
      saveSnapshot = await refreshParamSnapshot({ force: true, quiet: true });
    } catch (err) {
      console.warn('[SAVE] Failed to refresh parameter snapshot before save:', err);
    }

    const formulaRows = $$('tr.ta-row').filter((tr) => {
      const input = $('input[data-field="koefisien"]', tr);
      const rawTyped = String(input?.value || '').trim();
      const rawStored = String(tr.dataset.koefFormulaRaw || '').trim();
      return rawTyped.startsWith('=') || (tr.dataset.koefIsFx === '1' && !!rawStored);
    });

    let warningCount = 0;
    for (const tr of formulaRows) {
      const input = $('input[data-field="koefisien"]', tr);
      const rawTyped = String(input?.value || '').trim();
      const rawFormula = rawTyped.startsWith('=') ? rawTyped : String(tr.dataset.koefFormulaRaw || '').trim();
      if (!rawFormula) continue;
      const evalRes = await evaluateFormulaForKoefInput(tr, rawFormula, { snapshot: saveSnapshot });
      if (!evalRes.ok) {
        toast(`⚠️ ${evalRes.message || 'Formula tidak valid'}`, 'warning');
        return Promise.reject(new Error('Formula evaluation failed'));
      }
      if (evalRes.warning) warningCount += 1;
    }
    notifyFormulaDiffIfNeeded(jobId, saveSnapshot);
    if (warningCount > 0) {
      toast(`⚠️ ${warningCount} formula memakai fallback karena parameter hilang.`, 'warning');
    }

    const hasInlineError = $$('tr.ta-row.ta-koef-error').length > 0;
    if (hasInlineError) {
      toast('⚠️ Masih ada formula koefisien yang error. Perbaiki dulu sebelum simpan.', 'warning');
      return Promise.reject(new Error('Formula row in error state'));
    }

    const rows = gatherRows();
    const errs = validateClient(rows);
    if (errs.length) {
      const firstErr = errs[0];
      const errMsg = `Periksa isian: ${firstErr.path} - ${firstErr.message}`;
      toast(errMsg, 'warn');
      console.warn('Validation errors:', errs);
      return Promise.reject(new Error('Validation failed'));
    }

    const rowsCanon = rows.map(r => ({ ...r, koefisien: __koefToCanon(r.koefisien) }));
    const url = urlFor(endpoints.save, jobId);

    // Keep the detail-scoped version token loaded with this pekerjaan.
    const currentCache = rowsByJob[jobId];
    if (false && currentCache && currentCache.updatedAt) {
      console.log('[SAVE] Checking cache freshness before save...');
      try {
        const freshCheckUrl = urlFor(endpoints.get, jobId);
        const freshResp = await fetch(freshCheckUrl, { credentials: 'same-origin', timeout: 5000 });
        const freshData = await freshResp.json();

        if (freshData.ok && freshData.pekerjaan?.updated_at) {
          if (freshData.pekerjaan.updated_at !== currentCache.updatedAt) {
            console.warn('[SAVE] Data changed since cache loaded!', {
              cached: currentCache.updatedAt,
              fresh: freshData.pekerjaan.updated_at
            });
            toast('âš ï¸ Data telah diubah sejak terakhir dimuat. Muat ulang dulu!', 'warning', 5000);

            // Offer to reload
            const reload = confirm('Data pekerjaan ini telah berubah sejak terakhir dimuat.\n\nMuat ulang data terbaru? Perubahan Anda akan hilang.');
            if (reload) {
              const jobEl = $(`.ta-job-item[data-pekerjaan-id="${jobId}"]`);
              if (jobEl) triggerSelectJobInternal(jobEl, jobId, true); // Force refresh
            }
            return Promise.reject(new Error('Stale cache - data changed'));
          }
          console.log('[SAVE] Cache is fresh - proceeding with save');
        }
      } catch (err) {
        console.warn('[SAVE] Freshness check failed - proceeding anyway:', err);
        // Don't block save if check fails (network issue etc)
      }
    }

    const payload = { rows: rowsCanon };
    // Application policy: last-write-wins. The request itself remains atomic.

    const btnSave = $('#ta-btn-save');
    const spin = $('#ta-btn-save-spin');
    if (spin) spin.hidden = false;
    if (btnSave) btnSave.disabled = true;

    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify(payload)
    }).then(r => {
      // DEBUG: Log response status
      console.log('[SAVE] HTTP Status:', r.status);
      if (!r.ok) {
        console.error('[SAVE] HTTP Error:', r.status, r.statusText);
      }
      return r.json();
    }).then(initialJs => {
      const js = initialJs;
      // DEBUG: Log full response
      console.log('[SAVE] Response:', js);

      // IMPROVED: Use user_message from server for better UX
      if (!js.ok) {
        // Server returned error with user-friendly message
        const userMsg = js.user_message || 'Gagal menyimpan data. Silakan coba lagi.';
        toast(userMsg, 'error');
        console.error('[SAVE] Server errors:', js.errors || []);
        // FIX (#1): REJECT pada gagal penuh agar pemanggil (auto-save sebelum pindah
        // pekerjaan / sebelum sinkronisasi) TIDAK menganggapnya sukses lalu berpindah —
        // yang akan menghilangkan input pengguna. dirty sengaja TIDAK di-reset.
        const error = new Error(userMsg);
        error.handled = true;
        return Promise.reject(error);
      }

      let userMsg = js.user_message || 'âœ… Data berhasil disimpan!';

        // ENHANCED: Show bundle expansion feedback
        const rawRows = js.saved_raw_rows || 0;
        const expandedRows = js.saved_expanded_rows || 0;

        if (expandedRows > rawRows) {
          // Bundles were expanded
          const bundleCount = rawRows - (rows.filter(r => r.kategori !== 'LAIN').length);
          const expandedCount = expandedRows - rawRows;
          if (bundleCount > 0) {
            userMsg += `\n\nðŸ“¦ ${bundleCount} bundle di-expand menjadi ${expandedCount} komponen tambahan.`;
          }
        }

      toast(userMsg, 'success');
      console.log('[SAVE] Success - Raw:', rawRows, 'Expanded:', expandedRows, 'Expansion:', expandedRows - rawRows);

      // Update state
      setDirty(false);

      // WP-B4: simpan detail dapat mengubah readiness (harga/expansion/koef) → refresh banner.
      refreshReadiness();

      // P0 FIX: Use response data directly instead of double fetch
      // Server already sends fresh data in save response - no need to fetch again!
      const hasExpansion = (js.saved_expanded_rows || 0) > (js.saved_raw_rows || 0);

      if (hasExpansion) {
        // Bundle expansion occurred - reload to get expanded components
        console.log('[SAVE] Bundle expansion detected - reloading to fetch expanded components');
        delete rowsByJob[activeJobId];
        reloadJobs([activeJobId], { preserveSelection: true, silent: true, queue: true }).catch(() => { });
      } else {
        // Simple save without expansion - update cache directly from response
        console.log('[SAVE] Updating cache directly from response (no expansion)');

        if (js.items && Array.isArray(js.items)) {
          // Server returned updated items - use them
          rowsByJob[activeJobId] = {
            items: js.items,
            kategoriMeta: rowsByJob[activeJobId]?.kategoriMeta || kategoriMeta,
            readOnly: rowsByJob[activeJobId]?.readOnly || readOnly,
            sourceLabel: js.pekerjaan?.source_label || rowsByJob[activeJobId]?.sourceLabel || activeSourceLabel,
            updatedAt: js.pekerjaan?.updated_at || null,
            cachedAt: Date.now()
          };
          activeSourceLabel = rowsByJob[activeJobId].sourceLabel;
          renderActiveSource();
          paint(js.items);
          reevaluateAllKoefFormulaRows({ snapshot: saveSnapshot, silent: true })
            .then(() => rememberFormulaEvalSnapshot(activeJobId, saveSnapshot))
            .catch(() => { });
          console.log('[SAVE] Cache updated with', js.items.length, 'items from response');
        } else {
          // Fallback: Server didn't return items - use what we sent
          rowsByJob[activeJobId] = {
            items: rowsCanon,
            kategoriMeta: rowsByJob[activeJobId]?.kategoriMeta || kategoriMeta,
            readOnly: rowsByJob[activeJobId]?.readOnly || readOnly,
            sourceLabel: js.pekerjaan?.source_label || rowsByJob[activeJobId]?.sourceLabel || activeSourceLabel,
            updatedAt: js.pekerjaan?.updated_at || null,
            cachedAt: Date.now()
          };
          activeSourceLabel = rowsByJob[activeJobId].sourceLabel;
          renderActiveSource();
          paint(rowsCanon);
          reevaluateAllKoefFormulaRows({ snapshot: saveSnapshot, silent: true })
            .then(() => rememberFormulaEvalSnapshot(activeJobId, saveSnapshot))
            .catch(() => { });
          console.log('[SAVE] Cache updated with sent data (server response had no items)');
        }
      }
    }).catch((err) => {
      // Network error or unexpected error
      console.error('[SAVE] Catch error:', err);
      console.error('[SAVE] Error stack:', err.stack);
      if (err.handled) {
        throw err;
      }
      toast('âŒ Gagal menyimpan. Periksa koneksi internet Anda dan coba lagi.', 'error');
      throw err;
    }).finally(() => {
      if (spin) spin.hidden = true;
      if (btnSave) btnSave.disabled = false;
    });
  }

  // SAVE button handler - use refactored doSave function
  $('#ta-btn-save').addEventListener('click', () => {
    if (!activeJobId) return;
    doSave(activeJobId).catch(() => {
      // Error already handled in doSave
    });
  });

  // WP-B4: tampilkan readiness saat halaman dibuka (display-only).
  refreshReadiness();

  // Hapus baris terseleksi per segmen (ENHANCED: with confirmation)
  document.addEventListener('click', (e) => {
    const delBtn = e.target.closest('.ta-seg-del-selected');
    if (!delBtn) return;
    if (activeSource === 'ref') return;
    const seg = delBtn.dataset.targetSeg;
    const body = document.getElementById(`seg-${seg}-body`);
    if (!body) return;
    const checked = body.querySelectorAll('.ta-row-check:checked');
    if (!checked.length) return;

    // CRITICAL IMPROVEMENT: Show confirmation with preview
    const count = checked.length;
    const items = Array.from(checked).map(cb => {
      const row = cb.closest('tr.ta-row');
      const kode = row?.querySelector('input[data-field="kode"]')?.value || '?';
      const uraian = row?.querySelector('.cell-wrap')?.textContent?.trim() || '?';
      return { kode, uraian };
    }).slice(0, 5); // Show max 5 items in preview

    const preview = items.map(item => `â€¢ ${item.kode}: ${item.uraian}`).join('\n');
    const moreText = count > 5 ? `\n... dan ${count - 5} baris lainnya` : '';

    const confirmMsg = `âš ï¸ HAPUS ${count} BARIS TERPILIH?\n\n${preview}${moreText}\n\nTindakan ini tidak bisa dibatalkan (belum ada undo).`;

    if (!confirm(confirmMsg)) {
      console.log('[DELETE] User cancelled deletion');
      return; // User cancelled
    }

    // Proceed with deletion
    console.log(`[DELETE] Deleting ${count} rows from segment ${seg}`);
    checked.forEach(cb => cb.closest('tr.ta-row')?.remove());
    if (!body.querySelector('tr.ta-row')) {
      body.innerHTML = `<tr class=\"ta-empty\"><td colspan=\"5\">Belum ada item.</td></tr>`;
    }
    formatIndex();
    setDirty(true);
    updateDelState(seg);

    // Show feedback toast
    toast(`ðŸ—‘ï¸ ${count} baris berhasil dihapus dari ${seg}`, 'info');
  });

  // Update state tombol hapus saat ceklis berubah
  document.addEventListener('change', (e) => {
    const cb = e.target.closest('.ta-row-check');
    if (!cb) return;
    const tr = cb.closest('tr.ta-row');
    const seg = tr?.dataset?.kategori;
    if (seg) updateDelState(seg);
  });

  // RESET (ref_modified)
  const resetBtn = $('#ta-btn-reset');
  if (resetBtn) {
    resetBtn.addEventListener('click', async () => {
      if (!activeJobId || activeSource !== 'ref_modified') return;
      if (!confirm('Reset rincian dari referensi? Perubahan lokal akan hilang.')) return;

      const url = urlFor(endpoints.reset, activeJobId);

      try {
        // Fetch with HTTP error checking
        const response = await fetch(url, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'X-CSRFToken': CSRF }
        });

        // Check HTTP status first
        if (!response.ok) {
          const text = await response.text();
          let errorMsg = 'Gagal reset. Silakan coba lagi.';

          if (response.status === 403) {
            errorMsg = 'â›” Anda tidak memiliki akses untuk reset pekerjaan ini.';
          } else if (response.status === 404) {
            errorMsg = 'âŒ Pekerjaan atau referensi tidak ditemukan.';
          } else if (response.status === 500) {
            errorMsg = 'âš ï¸ Server error. Hubungi administrator.';
          } else if (text) {
            errorMsg = `HTTP ${response.status}: ${text}`;
          }

          throw new Error(errorMsg);
        }

        const js = await response.json();

        // Check API response status
        if (!js.ok) {
          // Extract specific error from server
          const errorMsg = js.errors && js.errors.length > 0
            ? js.errors.map(e => e.message).join('; ')
            : js.user_message || 'Gagal reset. Silakan coba lagi.';
          throw new Error(errorMsg);
        }

        // Success: reload data
        const getResponse = await fetch(urlFor(endpoints.get, activeJobId), { credentials: 'same-origin' });
        const getData = await getResponse.json();

        // P1 FIX: Add cache timestamp
        rowsByJob[activeJobId] = {
          items: getData.items || [],
          kategoriMeta: getData.meta?.kategori_opts || [],
          readOnly: !!getData.meta?.read_only,
          sourceLabel: getData.pekerjaan?.source_label || activeSourceLabel,
          updatedAt: getData.pekerjaan?.updated_at || null,
          cachedAt: Date.now()
        };
        activeSourceLabel = rowsByJob[activeJobId].sourceLabel;
        renderActiveSource();

        paint(rowsByJob[activeJobId].items);
        refreshParamSnapshot({ quiet: true })
          .then((snapshot) => reevaluateAllKoefFormulaRows({ snapshot, silent: true }))
          .catch(() => { });
        setDirty(false);
        setEditorModeBySource();
        // Reset-to-reference rebuilds raw/expanded detail, so the project-level
        // readiness verdict may change even though this is not the normal save path.
        refreshReadiness();

        // Show success with item count
        const count = getData.items?.length || 0;
        toast(`âœ… Berhasil reset ${count} item dari referensi`, 'success');

      } catch (err) {
        // Comprehensive error handling
        console.error('[RESET ERROR]', err);

        let errorMsg = 'Gagal reset. Silakan coba lagi.';

        if (err.message) {
          if (err.message.includes('timeout') || err.message.includes('Failed to fetch')) {
            errorMsg = 'â±ï¸ Koneksi timeout. Periksa internet dan coba lagi.';
          } else if (err.message.includes('NetworkError') || err.message.includes('Network request failed')) {
            errorMsg = 'ðŸŒ Tidak ada koneksi internet. Periksa koneksi Anda.';
          } else {
            errorMsg = err.message; // Use specific error from server
          }
        }

        toast(errorMsg, 'error');
      }
    });
  }

  // RELOAD - Force refresh data dari server (CACHE FIX)
  const reloadBtn = $('#ta-btn-reload');
  if (reloadBtn) {
    reloadBtn.addEventListener('click', () => {
      if (!activeJobId) {
        toast('âš ï¸ Tidak ada pekerjaan yang dipilih', 'warning');
        return;
      }

      // Konfirmasi jika ada perubahan yang belum disimpan
      if (dirty) {
        const confirmMsg = (
          "âš ï¸ PERUBAHAN BELUM TERSIMPAN!\n\n" +
          "Anda memiliki perubahan yang belum disimpan.\n\n" +
          "Pilihan:\n" +
          "â€¢ OK = Buang perubahan dan muat ulang data terbaru dari server\n" +
          "â€¢ Cancel = Batalkan reload dan simpan dulu\n\n" +
          "âš ï¸ Perubahan yang belum disimpan akan hilang!"
        );

        if (!confirm(confirmMsg)) {
          console.log('[RELOAD] User cancelled reload - has unsaved changes');
          return;
        }
      }

      // Clear cache dan force refresh
      console.log('[RELOAD] Force refreshing data for pekerjaan:', activeJobId);
      delete rowsByJob[activeJobId]; // Clear cache

      // Re-fetch dari server dengan forceRefresh = true
      const currentJobEl = $(`.ta-job-item[data-pekerjaan-id="${activeJobId}"]`);
      if (currentJobEl) {
        toast('ðŸ”„ Memuat ulang data terbaru...', 'info');
        triggerSelectJobInternal(currentJobEl, activeJobId, true); // forceRefresh = true
      } else {
        toast('âŒ Pekerjaan tidak ditemukan', 'error');
      }
    });
  }

  // P3.1 FIX: Proper CSV export with escaping
  function escapeCSV(value) {
    const str = String(value || '');
    // If contains delimiter, quote, or newline, wrap in quotes and escape quotes
    if (str.includes(';') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  }

  // EXPORT CSV (koefisien format kanonik titik)
  $('#ta-btn-export').addEventListener('click', () => {
    if (!activeJobId) return;
    const rows = gatherRows();

    // UTF-8 BOM for Excel compatibility
    const BOM = '\uFEFF';
    const header = 'kategori;kode;uraian;satuan;koefisien';

    const csvRows = rows.map(r => {
      const koefCanon = __koefToCanon(r.koefisien || '');
      return [
        escapeCSV(r.kategori),
        escapeCSV(r.kode),
        escapeCSV(r.uraian),
        escapeCSV(r.satuan),
        escapeCSV(koefCanon)
      ].join(';');
    });

    const csv = BOM + [header, ...csvRows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);

    // Better filename with timestamp
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[: ]/g, '-');
    const jobKode = $('#ta-active-kode').textContent.trim() || activeJobId;
    a.download = `template_ahsp_${jobKode}_${timestamp}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
    toast('âœ… CSV berhasil di-export', 'success');
  });

  // toast notification - delegate to global DP.toast
  /**
   * Show toast notification with auto-dismiss
   * @param {string} msg - Message to display
   * @param {string} type - Type: 'success', 'error', 'warning', 'info', 'warn'
   * @param {number} delay - Auto-dismiss delay in ms (default: 3000)
   */
  function toast(msg, type = 'info', delay = 3000) {
    console.log(`[TOAST ${type.toUpperCase()}] ${msg}`);

    // Normalize type (warn -> warning)
    const normalizedType = type === 'warn' ? 'warning' : type;

    // Use new global toast API
    if (window.DP && window.DP.toast && window.DP.toast[normalizedType]) {
      return window.DP.toast[normalizedType](msg, delay);
    }

    // Fallback to legacy API
    if (window.DP && window.DP.core && window.DP.core.toast) {
      window.DP.core.toast.show(msg, normalizedType, delay);
      return;
    }

    // Fallback to inline implementation
    // P3.2 FIX: Toast stacking with max limit
    let container = document.getElementById('ta-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'ta-toast-container';
      container.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        z-index: 13100;
        display: flex;
        flex-direction: column;
        gap: 10px;
        max-width: 400px;
      `;
      document.body.appendChild(container);
    }

    // Remove oldest toasts if more than 5
    const existingToasts = container.querySelectorAll('.ta-toast');
    if (existingToasts.length >= 5) {
      existingToasts[0].remove(); // Remove oldest (first)
    }

    // Icon and color mapping
    const config = {
      success: { icon: 'bi-check-circle-fill', bg: '#28a745', color: '#fff' },
      error: { icon: 'bi-x-circle-fill', bg: '#dc3545', color: '#fff' },
      warning: { icon: 'bi-exclamation-triangle-fill', bg: '#ffc107', color: '#000' },
      info: { icon: 'bi-info-circle-fill', bg: '#17a2b8', color: '#fff' }
    };
    const cfg = config[type] || config.info;

    // Create toast element
    const toastEl = document.createElement('div');
    toastEl.className = 'ta-toast';
    toastEl.style.cssText = `
      background: ${cfg.bg};
      color: ${cfg.color};
      padding: 12px 16px;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 300px;
      animation: slideInRight 0.3s ease-out;
      font-size: 14px;
      line-height: 1.4;
    `;

    toastEl.innerHTML = `
      <i class="bi ${cfg.icon}" style="font-size: 20px; flex-shrink: 0;"></i>
      <span style="flex: 1;">${escapeHtml(msg)}</span>
      <button type="button" style="
        background: none;
        border: none;
        color: ${cfg.color};
        font-size: 20px;
        line-height: 1;
        cursor: pointer;
        padding: 0;
        opacity: 0.7;
        flex-shrink: 0;
      " aria-label="Close">&times;</button>
    `;

    // Close button
    const closeBtn = toastEl.querySelector('button');
    closeBtn.addEventListener('click', () => {
      toastEl.style.animation = 'slideOutRight 0.3s ease-in';
      setTimeout(() => toastEl.remove(), 300);
    });

    // Auto-dismiss after 5 seconds (error stays longer)
    const duration = type === 'error' ? 8000 : 5000;
    setTimeout(() => {
      if (toastEl.parentNode) {
        toastEl.style.animation = 'slideOutRight 0.3s ease-in';
        setTimeout(() => toastEl.remove(), 300);
      }
    }, duration);

    container.appendChild(toastEl);
  }

  // Helper: Escape HTML to prevent XSS
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Add animations via <style>
  if (!document.getElementById('ta-toast-animations')) {
    const style = document.createElement('style');
    style.id = 'ta-toast-animations';
    style.textContent = `
      @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
      @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
      }
    `;
    document.head.appendChild(style);
  }

  refreshParamSnapshot({ force: true, quiet: true })
    .catch((err) => console.warn('[TA] Failed to preload parameter snapshot:', err));

  // PERF: seed cache untuk pekerjaan pertama dari bootstrap SSR supaya tidak ada
  // round-trip AJAX + flash "Memuat data..." saat halaman Template baru dibuka.
  // selectJobInternal akan melihat cache fresh dan langsung paint tanpa fetch.
  // Freshness payload dijamin oleh DetailProjectNoStoreMiddleware pada respons HTML.
  (function seedBootstrapDetail() {
    try {
      const el = document.getElementById('ta-bootstrap-detail');
      if (!el) return;
      const js = JSON.parse(el.textContent || 'null');
      if (!js || !js.ok || !js.pekerjaan || js.pekerjaan.id == null) return;
      const id = Number(js.pekerjaan.id);
      if (!Number.isFinite(id)) return;
      kategoriMeta = js.meta?.kategori_opts || kategoriMeta;
      rowsByJob[id] = {
        items: js.items || [],
        kategoriMeta,
        readOnly: !!js.meta?.read_only,
        sourceLabel: js.pekerjaan?.source_label || null,
        updatedAt: js.pekerjaan?.updated_at || null,
        cachedAt: Date.now(),
      };
    } catch (err) {
      console.warn('[TA] Failed to seed bootstrap detail:', err);
    }
  })();

  // auto-select first job
  const first = $('#ta-job-list .ta-job-item:not([hidden])');
  if (first) selectJob(first);
  scheduleAutoReloadPendingJobs('page-open');

  // =========================
  // CRITICAL SAFETY: Warn before leaving page with unsaved changes
  // =========================
  window.addEventListener('beforeunload', (e) => {
    if (dirty) {
      // Modern browsers ignore custom message and show default warning
      // But we still need to set returnValue for compatibility
      const msg = 'Anda memiliki perubahan yang belum disimpan. Yakin ingin meninggalkan halaman?';
      e.preventDefault();
      e.returnValue = msg; // Required for Chrome/Firefox
      console.log('[BEFOREUNLOAD] Warned user about unsaved changes');
      return msg; // For older browsers
    }
  });

  // =========================
  // Sidebar Resizer (vertical)
  // =========================
  (function installResizer() {
    const res = document.getElementById('ta-resizer');
    const side = document.querySelector('.ta-sidebar');
    if (!res || !side) return;

    const pid = app.dataset.projectId || '0';
    const KEY = `ta_sidebar_w:${pid}`;
    const MIN_W = 280; const MAX_W = 720;

    // restore saved width
    try {
      const saved = parseInt(localStorage.getItem(KEY) || '', 10);
      if (Number.isFinite(saved)) {
        const w = Math.min(MAX_W, Math.max(MIN_W, saved));
        // set both legacy and new tokens for compatibility
        document.body.style.setProperty('--ta-sidebar-w', `${w}px`);
        document.body.style.setProperty('--ta-left-w', `${w}px`);
      }
    } catch { }

    let dragging = false, startX = 0, startW = 0;
    const clamp = (w) => Math.min(MAX_W, Math.max(MIN_W, w));
    const onMove = (ev) => {
      if (!dragging) return;
      const x = ev.touches ? ev.touches[0].clientX : ev.clientX;
      const dx = x - startX; // drag right grows sidebar
      const w = clamp(startW + dx);
      const wpx = `${Math.round(w)}px`;
      // update both tokens so whichever CSS wins will reflect change
      document.body.style.setProperty('--ta-sidebar-w', wpx);
      document.body.style.setProperty('--ta-left-w', wpx);
      try { localStorage.setItem(KEY, String(Math.round(w))); } catch { }
      ev.preventDefault();
    };
    const onUp = () => {
      if (!dragging) return;
      dragging = false;
      document.body.classList.remove('user-resizing');
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('touchmove', onMove);
      window.removeEventListener('mouseup', onUp);
      window.removeEventListener('touchend', onUp);
    };
    const onDown = (ev) => {
      dragging = true;
      startX = ev.touches ? ev.touches[0].clientX : ev.clientX;
      startW = side.getBoundingClientRect().width;
      document.body.classList.add('user-resizing');
      window.addEventListener('mousemove', onMove, { passive: false });
      window.addEventListener('touchmove', onMove, { passive: false });
      window.addEventListener('mouseup', onUp, { passive: true });
      window.addEventListener('touchend', onUp, { passive: true });
      ev.preventDefault();
    };
    res.addEventListener('mousedown', onDown);
    res.addEventListener('touchstart', onDown, { passive: false });
    // keyboard support
    res.addEventListener('keydown', (e) => {
      const step = (e.shiftKey ? 20 : 10);
      // prefer legacy token if present
      let cur = parseInt(getComputedStyle(document.body).getPropertyValue('--ta-left-w') || '0', 10);
      if (!Number.isFinite(cur) || cur <= 0) {
        cur = parseInt(getComputedStyle(document.body).getPropertyValue('--ta-sidebar-w') || '360', 10) || 360;
      }
      if (e.key === 'ArrowLeft' || e.key === 'Left') {
        const w = clamp(cur - step);
        const wpx = `${w}px`;
        document.body.style.setProperty('--ta-sidebar-w', wpx);
        document.body.style.setProperty('--ta-left-w', wpx);
        try { localStorage.setItem(KEY, String(w)); } catch { }
        e.preventDefault();
      } else if (e.key === 'ArrowRight' || e.key === 'Right') {
        const w = clamp(cur + step);
        const wpx = `${w}px`;
        document.body.style.setProperty('--ta-sidebar-w', wpx);
        document.body.style.setProperty('--ta-left-w', wpx);
        try { localStorage.setItem(KEY, String(w)); } catch { }
        e.preventDefault();
      }
    });
  })();
})();
