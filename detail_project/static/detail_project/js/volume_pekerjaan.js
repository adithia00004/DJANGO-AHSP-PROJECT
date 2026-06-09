/* volume_pekerjaan.js - Drop-in (sticky THEAD, autosave+undo, id-ID formatting)
 * - Header tabel sticky tepat di bawah searchbar (JS mengisi CSS vars)
 * - Format tampilan id-ID dinamis (maks 3 desimal)
 * - Autosave (debounce) + Undo batch terakhir via toast (Ctrl+Alt+Z)
 * - Import parameter JSON & CSV (Excel-friendly, "label,value")
 * - Keyboard: Enter/Shift+Enter nav | Ctrl/Cmd+S save | Ctrl/Cmd+Space param | Ctrl+D fill-down
 */

(function () {
  const root = document.getElementById('vol-app');
  if (!root) return;
  // Gunakan Numeric bila tersedia agar konsisten (koma <-> titik)
  const N = window.Numeric || null;

  // ---- Konteks dasar
  const projectId = root.dataset.projectId || root.dataset.pid;
  const OPAQUE_ID_ENABLED = String(root.dataset.opaqueIdEnabled || '1') === '1';
  const FORMULA_LABEL_ONLY_UI_ENABLED = String(root.dataset.formulaLabelOnlyUiEnabled || '0') === '1';
  const VP_DISABLE_MODAL_BACKDROP = true;
  // NEW: endpoint dari data-attribute (fallback ke pattern lama)
  const EP_SAVE = root.dataset.endpointSave
    || `/detail_project/api/project/${projectId}/volume-pekerjaan/save/`;
  // State formula (raw,is_fx) disimpan/diambil dari endpoint ini
  const EP_FORMULA_STATE = root.dataset.endpointFormula
    || `/detail_project/api/project/${projectId}/volume-formula-state/`;
  // Pohon data untuk membangun grup Klas/Sub/Pekerjaan
  const EP_TREE = root.dataset.endpointTree
    || `/detail_project/api/project/${projectId}/list-pekerjaan/tree/`;

  // PERF: bootstrap SSR (volume_list + formula_state) supaya prefill() tidak perlu
  // round-trip AJAX saat halaman dibuka. null jika tidak tersedia → fallback fetch.
  // Freshness payload dijamin oleh DetailProjectNoStoreMiddleware pada respons HTML.
  const VP_BOOTSTRAP = (() => {
    try {
      const el = document.getElementById('vp-bootstrap');
      if (!el) return null;
      const data = JSON.parse(el.textContent || 'null');
      return (data && typeof data === 'object') ? data : null;
    } catch (e) {
      console.warn('[VP] Gagal membaca bootstrap SSR:', e);
      return null;
    }
  })();

  // Presisi simpan quantity (DB 3dp), tampilan dinamis 0..3 dp
  const STORE_PLACES = 3;
  // Presisi simpan parameter/base-computed variable (DB 12dp)
  const PARAM_STORE_PLACES = 12;
  // Presisi tampilan sidebar parameter agar tidak terlalu panjang
  const PARAM_DISPLAY_PLACES = 6;

  // Debounce autosave (ms). Default 5 menit agar autosave tidak terlalu agresif.
  const DEFAULT_AUTOSAVE_MS = 5 * 60 * 1000;
  const AUTOSAVE_MS = Number(root.dataset.autosaveMs || DEFAULT_AUTOSAVE_MS);

  // Quantity column width (manual, persisted per-project)
  const QTY_COL_W_DEFAULT_CH = 48;
  const QTY_COL_W_MIN_CH = 28;
  const QTY_COL_W_MAX_CH = 96;
  const QTY_COL_W_STEP_CH = 4;
  const QTY_COL_W_STORAGE_KEY = `vp_qty_col_w:${projectId}`;
  let qtyColWidthCh = QTY_COL_W_DEFAULT_CH;

  // ---- State in-memory (global selector agar mendukung multi-tabel/di dalam card)
  let rows = Array.from(document.querySelectorAll('tr[data-pekerjaan-id]'));
  const originalValueById = {}; // nilai tersimpan di server (baseline)
  const rawInputById = {};      // string mentah di input
  const currentValueById = {};  // nilai numerik hasil parse/eval
  const fxModeById = {};        // mode formula per baris
  const dirtySet = new Set();   // id pekerjaan yang berubah
  // FIX: baris dengan edit yang masih menunggu debounce handleInputChange (120ms).
  // flushPendingQtyInputs WAJIB memproses ini saat simpan agar edit cepat tidak hilang.
  const pendingInputIds = new Set();
  const formulaDirtySet = new Set(); // id pekerjaan dengan formula state yang berubah
  const inputValidationErrorsById = new Map(); // id -> pesan validasi yang memblokir simpan

  // Autosave timer & guard
  let autosaveTimer = null;
  let saving = false;
  let saveRetryRequested = false;
  let lastQtyInputAt = 0;
  const AUTOSAVE_TYPING_GRACE_MS = 900;
  let allowUnload = false;
  let formulaEditorModal = null;
  let paramPaletteModal = null;
  let formulaEditorContext = null; // { contextType:'volume', id, tr, input, preview } | { contextType:'computed', code, originalExpression, label, allowNameEdit } | { contextType:'computed-new', code:'', label, onCreated, allowNameEdit }
  let formulaEditorOpenRaw = '';  // Sprint 3.1: snapshot of raw value when modal opened
  let formulaEditorOpenComputedLabel = '';
  let formulaEditorCloseBypassed = false; // Sprint 3.1: flag to bypass dirty check on confirmed close
  let suppressFormulaInputFocusOpen = false;
  let formulaPreviewMode = 'label';
  let formulaShowInlineValues = true;
  let formulaEditorViewMode = 'raw';
  let formulaResolverToken = '';
  let formulaSyncTimer = null;
  let formulaSyncInFlight = false;
  let formulaSyncAt = null;
  let formulaRemoteStaleAt = '';
  let formulaRemoteWatchTimer = null;
  let formulaRemotePromptedAt = '';
  let formulaLocalDirty = false;
  let formulaEditorHasBlockingError = false;
  let formulaEditorBlockingMessage = '';
  let formulaEditorInvalidTokens = [];
  let formulaEditorPreviewDebounceTimer = null;
  let formulaDraftPersistTimer = null;
  let formulaUndoInProgress = false;
  const formulaUndoById = new Map(); // id -> { raw, fx, updated_at }
  const knownFormulaStateIds = new Set(); // formula sidecars known from server/local
  let formulaDraftById = {};
  const rawInputTouchedAtById = {};
  const negativeClampNoticeById = new Set(); // non-blocking warning agar tidak spam
  const FORMULA_SYNC_DELAY = 1600;
  const FORMULA_REMOTE_WATCH_MS = 30000;
  const SUGGEST_HIDE_DELAY_MS = 200;
  const FORMULA_ALLOWED_FUNCTIONS = Object.freeze([
    'sum', 'min', 'max', 'round', 'avg', 'abs', 'floor', 'ceil', 'pow',
  ]);
  const FORMULA_ALLOWED_FUNCTION_SET = new Set(FORMULA_ALLOWED_FUNCTIONS);
  const FORMULA_FUNCTION_SUGGESTIONS = Object.freeze([
    { name: 'sum', label: 'SUM()', insertText: 'SUM()', caretOffset: 4, hint: 'Jumlah' },
    { name: 'min', label: 'MIN()', insertText: 'MIN()', caretOffset: 4, hint: 'Nilai minimum' },
    { name: 'max', label: 'MAX()', insertText: 'MAX()', caretOffset: 4, hint: 'Nilai maksimum' },
    { name: 'round', label: 'ROUND()', insertText: 'ROUND()', caretOffset: 6, hint: 'Pembulatan' },
    { name: 'avg', label: 'AVG()', insertText: 'AVG()', caretOffset: 4, hint: 'Rata-rata' },
    { name: 'abs', label: 'ABS()', insertText: 'ABS()', caretOffset: 4, hint: 'Nilai absolut' },
    { name: 'floor', label: 'FLOOR()', insertText: 'FLOOR()', caretOffset: 6, hint: 'Bulat ke bawah' },
    { name: 'ceil', label: 'CEIL()', insertText: 'CEIL()', caretOffset: 5, hint: 'Bulat ke atas' },
    { name: 'pow', label: 'POW()', insertText: 'POW()', caretOffset: 4, hint: 'Pangkat' },
  ]);

  // Undo stack (batch autosave/simpan terakhir)
  const undoStack = []; // item: { ts, changes:[{id,before,after}] }
  const UNDO_MAX = 10;

  // === Parameter (values & labels)
  let variables = {}; // { KODE: number }
  let varLabels = {}; // { KODE: label }
  // === Computed Parameter (derived formulas)
  let computedParams = {}; // { KODE: { expression, label, unit, description } }
  let computedValues = {}; // { KODE: number }
  let computedErrors = {}; // { KODE: "error message" }
  let baseParamsLocalDirty = false;
  let computedParamsLocalDirty = false;

  // ---- Elemen UI
  const btnSave = document.getElementById('btn-save-vol') || document.querySelector('.vp-fab-save');
  const btnSaveTop = null;
  const btnSaveSpin = document.getElementById('btn-save-spin') || (btnSave ? btnSave.querySelector('.spinner-border') : null);
  const saveStatusEl = document.getElementById('vp-save-status');
  let saveStatusTimer = null;

  function setSaveStatus(message, variant) {
    try {
      if (!saveStatusEl) return;
      saveStatusEl.textContent = message || '';
      saveStatusEl.classList.remove('text-success', 'text-warning', 'text-danger');
      if (variant === 'success') saveStatusEl.classList.add('text-success');
      else if (variant === 'warning') saveStatusEl.classList.add('text-warning');
      else if (variant === 'danger') saveStatusEl.classList.add('text-danger');
      if (saveStatusTimer) clearTimeout(saveStatusTimer);
      if (message) saveStatusTimer = setTimeout(() => {
        saveStatusEl.textContent = '';
        saveStatusEl.classList.remove('text-success', 'text-warning', 'text-danger');
      }, 3200);
    } catch { }
  }

  const varTable = document.getElementById('vp-var-table');
  const btnVarAdd = document.getElementById('vp-var-add');
  const fileVarImport = document.getElementById('vp-var-import');
  const cParamTable = document.getElementById('vp-cparam-table');
  const btnCParamAdd = document.getElementById('vp-cparam-add');
  const paneTabs = Array.from(document.querySelectorAll('#vp-sidebar .vp-pane-tab'));
  const panes = Array.from(document.querySelectorAll('#vp-sidebar .vp-pane'));
  const formulaEditorModalEl = document.getElementById('vpFormulaEditorModal');
  const formulaEditorMetaEl = document.getElementById('vp-fe-meta');
  const formulaEditorComputedNameWrapEl = document.getElementById('vp-fe-computed-name-wrap');
  const formulaEditorComputedNameEl = document.getElementById('vp-fe-computed-name');
  const formulaEditorViewToggleBtn = document.getElementById('vp-fe-toggle-view');
  const formulaEditorShowValuesEl = document.getElementById('vp-fe-show-values');
  const formulaEditorInputWrapEl = formulaEditorModalEl ? formulaEditorModalEl.querySelector('.vp-fe-input-wrap') : null;
  const formulaEditorInputEl = document.getElementById('vp-fe-input');
  const formulaEditorChipPreviewEl = document.getElementById('vp-fe-chip-preview');
  const formulaEditorPreviewEl = document.getElementById('vp-fe-preview');
  const formulaEditorResolverEl = document.getElementById('vp-fe-resolver');
  const formulaEditorResolverTextEl = document.getElementById('vp-fe-resolver-text');
  const formulaEditorResolveBtn = document.getElementById('vp-fe-resolve-btn');
  const formulaEditorBlockEl = document.getElementById('vp-fe-block');
  const formulaEditorBlockTextEl = document.getElementById('vp-fe-block-text');
  const formulaEditorHighlightLayerEl = document.getElementById('vp-fe-highlight-layer');
  const formulaEditorHighlightContentEl = document.getElementById('vp-fe-highlight');
  const formulaEditorApplyBtn = document.getElementById('vp-fe-apply');
  const formulaEditorUndoBtn = document.getElementById('vp-fe-undo');
  const formulaEditorOpenPaletteBtn = document.getElementById('vp-fe-open-palette');
  const formulaPreviewModeButtons = Array.from(document.querySelectorAll('#vpFormulaEditorModal [data-preview-mode]'));
  const paramPaletteModalEl = document.getElementById('vpParamPaletteModal');
  const paramPaletteSearchEl = document.getElementById('vp-palette-search');
  const paramPaletteListEl = document.getElementById('vp-palette-list');

  const searchInput = document.getElementById('vp-search');
  const searchDrop = document.getElementById('vp-search-results');
  const prefixBadge = document.getElementById('vp-search-prefix-badge');
  const sidebarSearchInput = document.getElementById('vp-sidebar-search');
  const sidebarSearchClearBtn = document.getElementById('vp-sidebar-search-clear');
  const btnColNarrow = document.getElementById('vp-col-narrow');
  const btnColWider = document.getElementById('vp-col-wider');
  const btnColReset = document.getElementById('vp-col-reset');
  const colWidthLabel = document.getElementById('vp-col-width-label');
  let sidebarSearchQuery = '';

  function sidebarPaneKey() { return `vp_sidebar_pane:${projectId}`; }
  function setActiveSidebarPane(paneName, { persist = true } = {}) {
    const next = paneName === 'computed' ? 'computed' : 'base';
    paneTabs.forEach((btn) => {
      const active = btn.dataset.pane === next;
      btn.classList.toggle('is-active', active);
      btn.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    panes.forEach((el) => {
      const active = el.dataset.pane === next;
      el.classList.toggle('is-active', active);
    });
    if (persist) {
      try { localStorage.setItem(sidebarPaneKey(), next); } catch { }
    }
  }
  function initSidebarPaneTabs() {
    if (!paneTabs.length || !panes.length) return;
    paneTabs.forEach((btn) => {
      if (btn.dataset.boundPaneTab) return;
      btn.addEventListener('click', () => setActiveSidebarPane(btn.dataset.pane || 'base'));
      btn.dataset.boundPaneTab = '1';
    });
    let saved = 'base';
    try { saved = localStorage.getItem(sidebarPaneKey()) || 'base'; } catch { }
    setActiveSidebarPane(saved, { persist: false });
  }

  function sidebarSearchQueryText() {
    return String(sidebarSearchQuery || '').trim();
  }

  function syncSidebarSearchClearButton() {
    if (!sidebarSearchClearBtn) return;
    sidebarSearchClearBtn.hidden = sidebarSearchQueryText() === '';
  }

  function matchesSidebarSearch(item = {}) {
    const query = sidebarSearchQueryText();
    if (!query) return true;
    const qNorm = normalizeSuggestKeyword(query);
    const qCompact = compactSuggestKeyword(query);
    if (!qNorm && !qCompact) return true;
    const candidates = [
      item.code,
      item.label,
      item.expression,
      item.preview,
    ];
    return candidates.some((raw) => {
      const text = String(raw || '').trim();
      if (!text) return false;
      const tNorm = normalizeSuggestKeyword(text);
      const tCompact = compactSuggestKeyword(text);
      return (!!qNorm && tNorm.includes(qNorm))
        || (!!qCompact && tCompact.includes(qCompact));
    });
  }

  function applySidebarSearch() {
    sidebarSearchQuery = sidebarSearchInput ? String(sidebarSearchInput.value || '').trim() : '';
    syncSidebarSearchClearButton();
    renderVarTable();
    renderComputedTable();
    refreshUsageBadges();
  }

  function initSidebarSearch() {
    if (!sidebarSearchInput) return;
    sidebarSearchQuery = String(sidebarSearchInput.value || '').trim();
    syncSidebarSearchClearButton();
    if (sidebarSearchInput.dataset.boundSidebarSearch === '1') return;

    let timer = null;
    sidebarSearchInput.addEventListener('input', () => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => {
        applySidebarSearch();
        timer = null;
      }, 120);
    });
    sidebarSearchInput.addEventListener('keydown', (ev) => {
      if (ev.key !== 'Escape') return;
      if (!sidebarSearchInput.value) return;
      ev.preventDefault();
      sidebarSearchInput.value = '';
      applySidebarSearch();
      sidebarSearchInput.focus();
    });
    if (sidebarSearchClearBtn) {
      sidebarSearchClearBtn.addEventListener('click', () => {
        if (!sidebarSearchInput.value) return;
        sidebarSearchInput.value = '';
        applySidebarSearch();
        sidebarSearchInput.focus();
      });
    }
    sidebarSearchInput.dataset.boundSidebarSearch = '1';
  }

  function clampQtyColWidth(ch) {
    const n = Number(ch);
    if (!Number.isFinite(n)) return QTY_COL_W_DEFAULT_CH;
    return Math.max(QTY_COL_W_MIN_CH, Math.min(QTY_COL_W_MAX_CH, Math.round(n)));
  }
  function loadQtyColWidth() {
    try {
      const raw = localStorage.getItem(QTY_COL_W_STORAGE_KEY);
      if (raw == null) return QTY_COL_W_DEFAULT_CH;
      return clampQtyColWidth(raw);
    } catch {
      return QTY_COL_W_DEFAULT_CH;
    }
  }
  function applyQtyColWidth(ch, { persist = false } = {}) {
    qtyColWidthCh = clampQtyColWidth(ch);
    const widthCss = `${qtyColWidthCh}ch`;
    root.style.setProperty('--vp-qty-col-w', widthCss);
    const previewCaptionCh = Math.max(10, Math.min(18, Math.round(qtyColWidthCh * 0.22)));
    root.style.setProperty('--vp-preview-caption-w', `${previewCaptionCh}ch`);
    root.dataset.vpQtyCompact = qtyColWidthCh <= 36 ? '1' : '0';

    // Apply to current rendered table(s)
    document.querySelectorAll('#vp-table .vp-table col.col-qty, #vp-table > colgroup > col.col-qty')
      .forEach((col) => { col.style.width = widthCss; });

    if (colWidthLabel) colWidthLabel.textContent = widthCss;
    if (persist) {
      try { localStorage.setItem(QTY_COL_W_STORAGE_KEY, String(qtyColWidthCh)); } catch { }
    }
  }
  function initQtyColWidthControl() {
    qtyColWidthCh = loadQtyColWidth();
    applyQtyColWidth(qtyColWidthCh, { persist: false });

    if (btnColNarrow && !btnColNarrow.dataset.bound) {
      btnColNarrow.addEventListener('click', () => applyQtyColWidth(qtyColWidthCh - QTY_COL_W_STEP_CH, { persist: true }));
      btnColNarrow.dataset.bound = '1';
    }
    if (btnColWider && !btnColWider.dataset.bound) {
      btnColWider.addEventListener('click', () => applyQtyColWidth(qtyColWidthCh + QTY_COL_W_STEP_CH, { persist: true }));
      btnColWider.dataset.bound = '1';
    }
    if (btnColReset && !btnColReset.dataset.bound) {
      btnColReset.addEventListener('click', () => applyQtyColWidth(QTY_COL_W_DEFAULT_CH, { persist: true }));
      btnColReset.dataset.bound = '1';
    }
  }

  // Init manual width control as early as possible so first render follows user preference.
  initQtyColWidthControl();

  // Reposition dropdown to always appear below toolbar and not cover the input
  function positionSearchDropdown() {
    try {
      if (!searchInput || !searchDrop) return;
      const wrap = searchInput.closest('.vp-searchbar') || searchInput.parentElement;
      const rect = wrap.getBoundingClientRect();
      // Place using fixed position relative to viewport to avoid being clipped by toolbar area
      searchDrop.style.position = 'fixed';
      searchDrop.style.left = `${Math.round(rect.left)}px`;
      searchDrop.style.width = `${Math.round(rect.width)}px`;
      // IMPORTANT: with position: fixed, use viewport coords directly (no scrollY)
      const top = rect.bottom + 6; // 6px gap below the sticky toolbar searchbar
      searchDrop.style.top = `${Math.round(top)}px`;
      searchDrop.style.maxHeight = '40vh';
      searchDrop.style.overflow = 'auto';
      // z-index diatur via CSS: var(--vp-z-search, calc(var(--dp-z-toolbar)+1))
      searchDrop.style.zIndex = 'var(--vp-z-search)';
    } catch { }
  }

  ['focus', 'input', 'keydown'].forEach(ev => {
    if (searchInput) searchInput.addEventListener(ev, positionSearchDropdown, { passive: true });
  });
  window.addEventListener('resize', positionSearchDropdown, { passive: true });
  window.addEventListener('scroll', (e) => {
    // keep dropdown anchored during scroll when visible
    if (searchDrop && !searchDrop.classList.contains('d-none')) positionSearchDropdown();
  }, { passive: true });

  // Toast (single) + multi-toasts (untuk Undo)
  const toastEl = document.getElementById('vp-toast');
  const toastBody = document.getElementById('vp-toast-body');
  const multiToasts = document.getElementById('vp-toasts');
  let toastRef = null;
  try { if (window.bootstrap && toastEl) toastRef = new bootstrap.Toast(toastEl, { delay: 1600 }); } catch { }

  function showToast(message, variant) {
    if (!toastEl || !toastBody || !toastRef) {
      if (!message) return;
      const type = variant === 'danger' ? 'error' : (variant || 'info');
      if (window.DP && DP.toast && DP.toast.show) {
        DP.toast.show(message, type);
        return;
      }
      if (window.DP && DP.core && DP.core.toast && DP.core.toast.show) {
        DP.core.toast.show(message, type);
        return;
      }
      if (typeof window.showToast === 'function') {
        window.showToast(message, type);
        return;
      }
      console.warn('[VP] Toast:', message);
      return;
    }
    toastEl.classList.remove('text-bg-success', 'text-bg-danger', 'text-bg-warning');
    toastEl.classList.add(variant === 'danger' ? 'text-bg-danger' : variant === 'warning' ? 'text-bg-warning' : 'text-bg-success');
    toastBody.textContent = message || 'OK';
    toastRef.show();
  }

  function showActionToast(message, actions = []) {
    if (!multiToasts || !window.bootstrap) { showToast(message); return; }
    const wrapper = document.createElement('div');
    wrapper.className = 'toast align-items-center text-bg-dark border-0';
    wrapper.setAttribute('role', 'alert');
    wrapper.setAttribute('aria-live', 'assertive');
    wrapper.setAttribute('aria-atomic', 'true');
    wrapper.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">${escapeHtml(message)}</div>
        <div class="d-flex align-items-center gap-1 me-2">
          ${actions.map((a, i) => `<button type="button" class="btn btn-sm ${a.class || 'btn-warning'}" data-i="${i}">${escapeHtml(a.label || 'OK')}</button>`).join('')}
          <button type="button" class="btn-close btn-close-white m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
      </div>
    `;
    multiToasts.appendChild(wrapper);
    const t = new bootstrap.Toast(wrapper, { delay: 4000 });
    actions.forEach((a, i) => {
      const btn = wrapper.querySelector(`[data-i="${i}"]`);
      if (btn) btn.addEventListener('click', () => { try { a.onClick?.(); } finally { t.hide(); } });
    });
    wrapper.addEventListener('hidden.bs.toast', () => wrapper.remove());
    t.show();
  }

  // ---- HTTP helper: gunakan DP.core.http bila ada
  const HTTP = (function () {
    const h = (window.DP && DP.core && DP.core.http) ? DP.core.http : null;
    async function jget(url) {
      if (h && h.jfetch) return h.jfetch(url, { method: 'GET', normalize: false });
      const r = await fetch(url, { credentials: 'same-origin' });
      if (!r.ok) throw new Error(r.statusText);
      return r.json();
    }
    async function jpost(url, data) {
      if (h && h.jfetchJson) return h.jfetchJson(url, { method: 'POST', data });
      const r = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
        credentials: 'same-origin',
        body: JSON.stringify(data)
      });
      const body = await r.json().catch(() => ({}));
      return { ok: r.ok, status: r.status, data: body, errors: body?.errors || [] };
    }
    return { jget, jpost };
  })();

  // ---- Toast helper: prefer global DP.toast, fallback to DP.core.toast
  const TOAST = (function () {
    const newApi = window.DP && window.DP.toast;
    const legacyApi = window.DP && window.DP.core && window.DP.core.toast;
    return {
      ok(msg) {
        if (newApi) return newApi.success(msg);
        if (legacyApi) return legacyApi.show({ message: msg, variant: 'success' });
        showToast(msg, 'success');
      },
      warn(msg) {
        if (newApi) return newApi.warning(msg);
        if (legacyApi) return legacyApi.show({ message: msg, variant: 'warning' });
        showToast(msg, 'warning');
      },
      err(msg) {
        if (newApi) return newApi.error(msg);
        if (legacyApi) return legacyApi.show({ message: msg, variant: 'danger' });
        showToast(msg, 'danger');
      },
      info(msg) {
        if (newApi) return newApi.info(msg);
        if (legacyApi) return legacyApi.show({ message: msg, variant: 'info' });
        showToast(msg, 'info');
      },
      action(msg, actions) { showActionToast(msg, actions); }
    };
  })();

  function getModalApi() {
    return (window.DP && DP.core && DP.core.modal) ? DP.core.modal : null;
  }
  function confirmModal(message, options = {}) {
    const modalApi = getModalApi();
    if (modalApi && modalApi.confirm) {
      const result = Promise.resolve(modalApi.confirm(message, options));
      // Boost z-index when called over formula editor modal
      boostConfirmModalZIndex();
      return result;
    }
    const title = String(options.title || '').trim();
    const promptText = title ? `${title}\n\n${message}` : String(message || '');
    try {
      if (typeof window.confirm === 'function') {
        return Promise.resolve(window.confirm(promptText));
      }
    } catch { }
    if (window.DP && DP.toast) DP.toast.warning('Konfirmasi tidak tersedia.');
    return Promise.resolve(false);
  }
  /** Boost z-index of the topmost visible .modal + .modal-backdrop above the formula editor */
  function boostConfirmModalZIndex() {
    const feOpen = formulaEditorModalEl && formulaEditorModalEl.classList.contains('show');
    if (!feOpen) return;
    const boost = () => {
      document.querySelectorAll('.modal.show').forEach((m) => {
        if (m.id === 'vpFormulaEditorModal') return;
        m.style.zIndex = '13055';
      });
      const backdrops = document.querySelectorAll('.modal-backdrop');
      if (backdrops.length > 1) {
        backdrops[backdrops.length - 1].style.zIndex = '13054';
      } else if (backdrops.length === 1) {
        backdrops[0].style.zIndex = '13054';
      }
    };
    requestAnimationFrame(boost);
    // Redundant fallback in case the modal DOM isn't ready within one rAF
    setTimeout(boost, 80);
    setTimeout(boost, 200);
  }

  function cleanupOrphanModalBackdrops() {
    const run = () => {
      const openModals = document.querySelectorAll('.modal.show');
      const activeAriaModal = document.querySelector('.modal[aria-modal="true"]');
      const backdrops = document.querySelectorAll('.modal-backdrop');
      if (VP_DISABLE_MODAL_BACKDROP && backdrops.length) {
        backdrops.forEach((bd) => bd.remove());
      }
      const expected = openModals.length;
      if (expected === 0 && activeAriaModal) {
        // A modal is still transitioning/opening; skip hard cleanup for this frame.
        return;
      }
      if (expected === 0 && backdrops.length) {
        backdrops.forEach((bd) => bd.remove());
      } else if (backdrops.length > expected) {
        for (let i = backdrops.length - 1; i >= expected; i--) {
          backdrops[i].remove();
        }
      }
      if (expected === 0) {
        document.body.classList.remove('modal-open');
        document.body.style.removeProperty('overflow');
        document.body.style.removeProperty('padding-right');
      }
    };
    setTimeout(run, 60);
    setTimeout(run, 200);
    setTimeout(run, 450);
  }

  function installModalBackdropWatchdog() {
    if (document.body.dataset.vpBackdropWatchdogBound) return;
    const checkAndClean = () => {
      const openModals = document.querySelectorAll('.modal.show');
      const activeAriaModal = document.querySelector('.modal[aria-modal="true"]');
      const backdrops = document.querySelectorAll('.modal-backdrop');
      if (VP_DISABLE_MODAL_BACKDROP && backdrops.length) {
        backdrops.forEach((bd) => bd.remove());
        return;
      }
      if (!openModals.length && !activeAriaModal && backdrops.length) {
        cleanupOrphanModalBackdrops();
      }
    };
    document.addEventListener('pointerdown', checkAndClean, true);
    document.addEventListener('keydown', checkAndClean, true);
    document.addEventListener('focusin', checkAndClean, true);
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') checkAndClean();
    });
    setInterval(checkAndClean, 2200);
    document.body.dataset.vpBackdropWatchdogBound = '1';
  }

  function installNoModalBackdropEnforcer() {
    if (!VP_DISABLE_MODAL_BACKDROP) return;
    if (document.body.dataset.vpNoBackdropEnforcerBound) return;
    const forceNoBackdropAttrs = () => {
      const modalIds = ['vpFormulaHelpModal', 'vpFormulaEditorModal', 'vpParamPaletteModal', 'dp-core-modal'];
      modalIds.forEach((id) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.setAttribute('data-bs-backdrop', 'false');
      });
    };
    const pruneBackdrops = () => {
      document.querySelectorAll('.modal-backdrop').forEach((node) => node.remove());
    };
    forceNoBackdropAttrs();
    pruneBackdrops();
    const observer = new MutationObserver((mutations) => {
      let shouldPrune = false;
      let shouldReapplyAttrs = false;
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (!(node instanceof HTMLElement)) return;
          if (node.classList?.contains('modal-backdrop')) shouldPrune = true;
          if (node.matches?.('.modal, #dp-core-modal') || node.querySelector?.('.modal, #dp-core-modal')) {
            shouldReapplyAttrs = true;
          }
        });
      });
      if (shouldReapplyAttrs) forceNoBackdropAttrs();
      if (shouldPrune) pruneBackdrops();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    document.body.dataset.vpNoBackdropEnforcerBound = '1';
  }

  if (!document.body.dataset.vpModalCleanupBound) {
    document.addEventListener('hidden.bs.modal', () => {
      cleanupOrphanModalBackdrops();
    });
    document.body.dataset.vpModalCleanupBound = '1';
  }
  installNoModalBackdropEnforcer();
  installModalBackdropWatchdog();

  function alertModal(message, options = {}) {
    const modalApi = getModalApi();
    if (modalApi && modalApi.alert) return Promise.resolve(modalApi.alert(message, options));
    const title = String(options.title || '').trim();
    const promptText = title ? `${title}\n\n${message}` : String(message || '');
    try {
      if (typeof window.alert === 'function') window.alert(promptText);
    } catch { }
    if (window.DP && DP.toast) DP.toast.info(String(message || ''));
    return Promise.resolve(true);
  }

  const sourceChange = window.DP?.sourceChange || null;
  const bannerEl = document.getElementById('vp-sync-banner');
  const bannerTextEl = document.getElementById('vp-sync-text');
  const bannerFocusBtn = document.getElementById('vp-sync-focus');
  let pendingVolumeJobs = new Set(
    sourceChange && projectId ? sourceChange.listVolumeJobs(projectId) : [],
  );
  let changeStatusPending = false;

  function updateVolumeWarnings() {
    rows.forEach((tr) => {
      const id = Number(tr.dataset.pekerjaanId);
      const needsWarning = pendingVolumeJobs.has(id);
      tr.classList.toggle('vp-row-needs-volume', needsWarning);
      const cell = tr.querySelector('.text-wrap');
      if (!cell) return;
      let pill = cell.querySelector('.vp-row-pill');
      if (needsWarning) {
        if (!pill) {
          pill = document.createElement('span');
          pill.className = 'vp-row-pill';
          pill.textContent = 'Perlu cek';
          cell.appendChild(pill);
        }
      } else if (pill) {
        pill.remove();
      }
    });
  }

  function updateVolumeBanner() {
    if (!bannerEl) return;
    const count = pendingVolumeJobs.size;
    const shouldShow = count > 0 || changeStatusPending;
    bannerEl.classList.toggle('d-none', !shouldShow);
    if (!shouldShow) return;
    if (bannerTextEl) {
      if (count > 0 && changeStatusPending) {
        bannerTextEl.textContent = `${count} pekerjaan perlu diperbarui setelah perubahan sumber. Perubahan data terbaru juga terdeteksi dari halaman lain.`;
      } else if (count > 0) {
        bannerTextEl.textContent = `${count} pekerjaan perlu diperbarui setelah perubahan sumber.`;
      } else {
        bannerTextEl.textContent = 'Perubahan data terbaru terdeteksi dari halaman lain. Disarankan muat ulang data sebelum melanjutkan.';
      }
    }
  }

  function resolveVolumeJobs(jobIds) {
    if (!jobIds || !jobIds.length) return;
    const resolved = jobIds.map((id) => Number(id)).filter((id) => pendingVolumeJobs.delete(id));
    if (!resolved.length) return;
    try {
      sourceChange?.markVolumeResolved(projectId, resolved);
    } catch (err) {
      console.warn('[Volume] Failed to update volume reset flags', err);
    }
    updateVolumeWarnings();
    updateVolumeBanner();
  }

  function jumpToFirstWarning() {
    const target = rows.find((tr) => tr.classList.contains('vp-row-needs-volume'));
    if (!target) {
      if (changeStatusPending) {
        TOAST.warn('Perubahan data terbaru terdeteksi. Gunakan sinkronisasi untuk memperbarui status.');
        return;
      }
      TOAST.warn('Tidak ada pekerjaan yang perlu diperbarui.');
      return;
    }
    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    target.classList.add('vp-row-highlight');
    setTimeout(() => target.classList.remove('vp-row-highlight'), 1500);
  }

  function acknowledgeGlobalSyncLed(flags = {}) {
    const pid = Number(projectId);
    if (!Number.isFinite(pid) || pid <= 0) return;
    try {
      window.dispatchEvent(new CustomEvent('dp:sync-led-ack', {
        detail: {
          projectId: pid,
          ahsp: !!flags.ahsp,
          harga: !!flags.harga,
          pekerjaan: !!flags.pekerjaan,
          volume: !!flags.volume,
          jadwal: !!flags.jadwal,
          payload: flags.payload || null,
        },
      }));
    } catch { }
  }

  updateVolumeWarnings();
  updateVolumeBanner();
  bannerFocusBtn?.addEventListener('click', (event) => {
    event.preventDefault();
    jumpToFirstWarning();
  });

  if (projectId && sourceChange) {
    window.addEventListener('dp:source-change', (event) => {
      const detail = event.detail || {};
      if (Number(detail.projectId) !== Number(projectId)) return;
      if (detail.state && detail.state.volume) {
        pendingVolumeJobs = new Set(
          Object.keys(detail.state.volume).map((key) => Number(key)).filter((id) => Number.isFinite(id))
        );
        updateVolumeWarnings();
        updateVolumeBanner();
      }
    });
  }

  if (projectId) {
    window.addEventListener('dp:change-status', (event) => {
      const detail = event.detail || {};
      if (Number(detail.projectId) !== Number(projectId)) return;
      if (detail.scope && detail.scope !== 'volume' && detail.scope !== 'global') return;
      if (typeof detail.hasChanges === 'undefined') return;
      changeStatusPending = !!detail.hasChanges;
      updateVolumeBanner();
    });

    window.addEventListener('dp:sync-refresh-request', (event) => {
      const detail = event.detail || {};
      if (Number(detail.projectId) !== Number(projectId)) return;
      if (detail.scope && detail.scope !== 'volume' && detail.scope !== 'global') return;

      event.preventDefault();
      const isAuto = detail.reason === 'auto';

      if (window.__vpDirty) {
        if (!isAuto) {
          TOAST.warn('Masih ada perubahan volume/formula yang belum disimpan. Simpan dulu sebelum sinkronisasi.');
        }
        return;
      }

      updateVolumeWarnings();
      updateVolumeBanner();
      syncSummaryBarWithCurrentFilter();

      Promise.allSettled([
        loadParamsFromServer({ force: false }),
        loadComputedParamsFromServer({ force: false }),
      ]).finally(() => {
        acknowledgeGlobalSyncLed({
          ahsp: true,
          harga: true,
          pekerjaan: true,
          volume: true,
          jadwal: true,
          payload: detail.payload || null,
        });
        if (!isAuto) {
          TOAST.info('Status sinkronisasi volume diperbarui. Tinjau pekerjaan yang ditandai.');
          jumpToFirstWarning();
        }
      });
    });
  }

  // ---- Utils
  function getCsrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }
  function roundHalfUp(x, places) {
    const p = Math.max(0, Math.min(20, places | 0));
    const factor = Math.pow(10, p);
    return (x >= 0)
      ? Math.floor(x * factor + 0.5) / factor
      : Math.ceil(x * factor - 0.5) / factor;
  }
  function formatIdSmartWithDp(num, places) {
    const safePlaces = Math.max(0, Math.min(20, Number(places) || 0));
    const n = Number(num || 0);
    const hasFrac = Math.abs(n - Math.trunc(n)) > 1e-12;
    const fracLen = hasFrac ? Math.min(String(n.toFixed(safePlaces)).split('.')[1]?.replace(/0+$/, '').length || 0, safePlaces) : 0;
    try {
      return new Intl.NumberFormat('id-ID', {
        minimumFractionDigits: fracLen,
        maximumFractionDigits: safePlaces
      }).format(n);
    } catch {
      return n.toFixed(fracLen);
    }
  }
  // Tampilan id-ID dinamis untuk quantity (maks 3dp)
  function formatIdSmart(num) {
    return formatIdSmartWithDp(num, STORE_PLACES);
  }
  // Tampilan id-ID dinamis untuk parameter (ringkas, maks 6dp)
  function formatParamSmart(num) {
    return formatIdSmartWithDp(num, PARAM_DISPLAY_PLACES);
  }

  function normalizeLocaleNumericString(input) {
    if (N) return (N.canonicalizeForAPI(input ?? '') || '');
    let s = String(input ?? '').trim();
    if (!s) return s;
    s = s.replace(/\s+/g, '').replace(/_/g, '');
    const hasComma = s.includes(','), hasDot = s.includes('.');
    if (hasComma && hasDot) { s = s.replace(/\./g, ''); s = s.replace(',', '.'); }
    else if (hasComma) { s = s.replace(',', '.'); }
    return s;
  }
  function parseNumberOrEmpty(val) {
    if (N) {
      const c = N.canonicalizeForAPI(val || '');
      if (!c) return '';
      const n = Number(c);
      return Number.isFinite(n) ? n : '';
    }
    const s = normalizeLocaleNumericString(val);
    if (!s) return '';
    const n = Number(s);
    return Number.isFinite(n) ? n : '';
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  }

  function setInputValidationError(id, message = '') {
    const numericId = Number(id);
    if (!Number.isFinite(numericId)) return;
    const text = String(message || '').trim();
    if (!text) {
      inputValidationErrorsById.delete(numericId);
      return;
    }
    inputValidationErrorsById.set(numericId, text);
    // Sprint 3.5: announce error to screen readers via aria-live
    try {
      let liveRegion = document.getElementById('vp-validation-live');
      if (!liveRegion) {
        liveRegion = document.createElement('div');
        liveRegion.id = 'vp-validation-live';
        liveRegion.setAttribute('aria-live', 'polite');
        liveRegion.setAttribute('aria-atomic', 'true');
        liveRegion.className = 'visually-hidden';
        document.body.appendChild(liveRegion);
      }
      liveRegion.textContent = text;
    } catch (_) { /* non-critical */ }
  }

  function markRawInputTouched(id) {
    const numericId = Number(id);
    if (!Number.isFinite(numericId)) return;
    rawInputTouchedAtById[numericId] = Date.now();
  }

  function getRawInputTouchedMs(id) {
    const numericId = Number(id);
    if (!Number.isFinite(numericId)) return 0;
    const ms = Number(rawInputTouchedAtById[numericId] || 0);
    return Number.isFinite(ms) ? ms : 0;
  }

  function notifyNegativeClamp(id) {
    const numericId = Number(id);
    if (!Number.isFinite(numericId)) return;
    if (negativeClampNoticeById.has(numericId)) return;
    negativeClampNoticeById.add(numericId);
    const msg = `Baris #${numericId}: hasil negatif diubah menjadi 0.`;
    setSaveStatus(msg, 'warning');
    try { TOAST.info(msg); } catch { }
  }

  function clearNegativeClampNotice(id) {
    const numericId = Number(id);
    if (!Number.isFinite(numericId)) return;
    negativeClampNoticeById.delete(numericId);
  }

  function getSortedInputValidationIssues() {
    return Array.from(inputValidationErrorsById.entries())
      .map(([id, message]) => ({ id: Number(id), message: String(message || '') }))
      .filter((it) => Number.isFinite(it.id) && it.message)
      .sort((a, b) => a.id - b.id);
  }

  function setBtnSaveEnabled() {
    const dirty = (dirtySet.size !== 0) || (formulaDirtySet.size !== 0);
    const hasBlockingError = (inputValidationErrorsById.size > 0) || formulaEditorHasBlockingError;
    const disabled = !dirty; // Allow click to show validation errors
    if (btnSave) {
      btnSave.disabled = disabled;
      btnSave.setAttribute('title', hasBlockingError ? 'Simpan diblokir: masih ada token/input invalid.' : '');
      // FAB Visibility Animation
      if (btnSave.classList.contains('vp-fab-save')) {
        btnSave.classList.toggle('is-visible', dirty);
        // Update badge count
        const badge = document.getElementById('vp-fab-badge');
        if (badge) {
          const count = (dirtySet.size + formulaDirtySet.size);
          badge.textContent = count > 0 ? count : '';
          badge.classList.toggle('d-none', count === 0);
        }
      }
    }
    // btnSaveTop removed
    window.__vpDirty = dirty || hasBlockingError;
  }

  // ===== Search Index & UI =====
  let searchIndex = []; // {type, id, label, el}
  let searchState = { items: [], activeIdx: -1 };

  // ===== Collapse (toggle Klas/Sub) =====
  const COLLAPSE_KEY = `vp_collapse:${projectId}`;
  let collapsed = { klas: {}, sub: {} };
  try { const raw = localStorage.getItem(COLLAPSE_KEY); if (raw) collapsed = Object.assign({ klas: {}, sub: {} }, JSON.parse(raw) || {}); } catch { }
  function saveCollapse() { try { localStorage.setItem(COLLAPSE_KEY, JSON.stringify(collapsed)); } catch { } }
  function slugKey(s) {
    return String(s || '').trim().toLowerCase().normalize('NFKD')
      .replace(/[^\w\s-]/g, '').replace(/\s+/g, '_').replace(/_+/g, '_').replace(/^_+|_+$/g, '') || '_';
  }
  function applyCollapseOnTable() {
    const tbody = document.querySelector('#vp-table tbody'); if (!tbody) return;
    let curK = null, curS = null;
    Array.from(tbody.rows).forEach(tr => {
      if (tr.classList.contains('vp-klass')) {
        curK = tr.getAttribute('data-klas-id') || slugKey(tr.textContent);
        tr.classList.toggle('is-collapsed', !!collapsed.klas[curK]);
        return;
      }
      if (tr.classList.contains('vp-sub')) {
        curS = tr.getAttribute('data-sub-id') || slugKey(tr.textContent);
        tr.classList.toggle('is-collapsed', !!collapsed.sub[curS] || !!collapsed.klas[curK]);
        return;
      }
      // baris pekerjaan
      const k = tr.getAttribute('data-klas-id') || curK;
      const s = tr.getAttribute('data-sub-id') || curS;
      tr.hidden = !!collapsed.klas[k] || !!collapsed.sub[s];
    });
  }

  function applyCollapseOnCards() {
    document.querySelectorAll('.vp-klas-card, .vp-sub-section').forEach(card => {
      const isKlas = card.classList.contains('vp-klas-card');
      const key = isKlas ? (card.getAttribute('data-klas-id') || slugKey(card.querySelector('.card-header')?.textContent))
        : (card.getAttribute('data-sub-id') || slugKey(card.querySelector('.card-header')?.textContent));
      const isCollapsed = isKlas ? !!collapsed.klas[key] : !!collapsed.sub[key];
      card.classList.toggle('is-collapsed', isCollapsed);
      const btn = card.querySelector('.vp-card-toggle');
      if (btn) {
        btn.setAttribute('aria-expanded', isCollapsed ? 'false' : 'true');
        const icon = btn.querySelector('i');
        if (icon) icon.className = `bi ${isCollapsed ? 'bi-caret-right-fill' : 'bi-caret-down-fill'}`;
      }
    });
  }

  // Delegasi klik toggle caret
  document.addEventListener('click', (e) => {
    // row-based (fallback dari builder EP_TREE)
    const btnRow = e.target.closest('.vp-toggle');
    if (btnRow) {
      const type = btnRow.getAttribute('data-type'); const key = btnRow.getAttribute('data-key');
      if (!type || !key) return;
      if (type === 'klas') collapsed.klas[key] = !collapsed.klas[key];
      else collapsed.sub[key] = !collapsed.sub[key];
      saveCollapse(); applyCollapseOnTable(); applyCollapseOnCards(); return;
    }
    // card-based (SSR / template)
    const btnCard = e.target.closest('.vp-card-toggle');
    if (btnCard) {
      const type = btnCard.getAttribute('data-type'); const key = btnCard.getAttribute('data-key');
      if (!type || !key) return;
      if (type === 'klas') collapsed.klas[key] = !collapsed.klas[key];
      else collapsed.sub[key] = !collapsed.sub[key];
      saveCollapse(); applyCollapseOnCards(); return;
    }
  });

  // PERBAIKAN #2: Expand All / Collapse All buttons (seperti list_pekerjaan)
  const btnExpandAll = document.getElementById('vp-expand-all');
  const btnCollapseAll = document.getElementById('vp-collapse-all');

  if (btnExpandAll) {
    btnExpandAll.addEventListener('click', () => {
      // Clear semua collapse state
      collapsed.klas = {};
      collapsed.sub = {};
      saveCollapse();
      applyCollapseOnTable();
      applyCollapseOnCards();

      // Visual feedback (optional)
      showToast('Semua klasifikasi dan sub-klasifikasi diperluas', 'info');
    });
  }

  if (btnCollapseAll) {
    btnCollapseAll.addEventListener('click', () => {
      // Collapse semua Klasifikasi dan Sub
      document.querySelectorAll('.vp-klas-card').forEach(card => {
        const key = card.getAttribute('data-klas-id') || slugKey(card.querySelector('.card-header')?.textContent);
        if (key) collapsed.klas[key] = true;
      });
      document.querySelectorAll('.vp-sub-card').forEach(card => {
        const key = card.getAttribute('data-sub-id') || slugKey(card.querySelector('.card-header')?.textContent);
        if (key) collapsed.sub[key] = true;
      });

      // Juga handle row-based (fallback)
      document.querySelectorAll('tr.vp-klass').forEach(tr => {
        const key = tr.getAttribute('data-klas-id') || slugKey(tr.textContent);
        if (key) collapsed.klas[key] = true;
      });
      document.querySelectorAll('tr.vp-sub').forEach(tr => {
        const key = tr.getAttribute('data-sub-id') || slugKey(tr.textContent);
        if (key) collapsed.sub[key] = true;
      });

      saveCollapse();
      applyCollapseOnTable();
      applyCollapseOnCards();

      // Visual feedback (optional)
      showToast('Semua klasifikasi dan sub-klasifikasi diciutkan', 'info');
    });
  }

  function typeBadgeClass(type) {
    if (type === 'Klasifikasi') return 'vp-type-klas';
    if (type === 'Sub') return 'vp-type-sub';
    return 'vp-type-pekerjaan';
  }
  function highlightLabel(text, query) {
    const q = String(query || '').trim();
    if (!q) return escapeHtml(text);
    const idx = text.toLowerCase().indexOf(q.toLowerCase());
    if (idx === -1) return escapeHtml(text);
    const before = text.slice(0, idx);
    const match = text.slice(idx, idx + q.length);
    const after = text.slice(idx + q.length);
    return `${escapeHtml(before)}<mark class="vp-mark">${escapeHtml(match)}</mark>${escapeHtml(after)}`;
  }

  function buildSearchIndex() {
    searchIndex = [];
    // Dukung 2 gaya header: versi <tr>.vp-klass/.vp-sub (table-group) & versi card (.vp-klas-card/.vp-sub-card)
    // 1) Header Klas/Sub versi CARD (list_pekerjaan-like)
    document.querySelectorAll('.vp-klas-card > .card-header').forEach((el, i) => {
      const label = el.textContent.trim();
      searchIndex.push({ type: 'Klasifikasi', id: `k_card_${i}`, label, el });
    });
    document.querySelectorAll('.vp-sub-card > .card-header').forEach((el, i) => {
      const label = el.textContent.trim();
      searchIndex.push({ type: 'Sub', id: `s_card_${i}`, label, el });
    });
    // 2) Header Klas/Sub versi ROW (fallback)
    document.querySelectorAll('tr.vp-klass').forEach((tr, i) => {
      const label = tr.textContent.trim();
      searchIndex.push({ type: 'Klasifikasi', id: `k_row_${i}`, label, el: tr });
    });
    document.querySelectorAll('tr.vp-sub').forEach((tr, i) => {
      const label = tr.textContent.trim();
      searchIndex.push({ type: 'Sub', id: `s_row_${i}`, label, el: tr });
    });
    // 3) Item pekerjaan (selalu ada)
    document.querySelectorAll('tr[data-pekerjaan-id]').forEach((tr) => {
      const kode = (tr.querySelector('.ux-mono, .text-monospace')?.textContent || '').trim();
      const uraian = (tr.querySelector('.text-wrap')?.textContent || '').trim();
      const label = (kode ? `${kode} - ` : '') + uraian;
      searchIndex.push({ type: 'Pekerjaan', id: tr.dataset.pekerjaanId, label, el: tr });
    });
  }

  function showSearchResults(items, q) {
    if (!searchDrop) return;
    searchState.items = items.slice(0, 15);
    searchState.activeIdx = searchState.items.length ? 0 : -1;

    if (!searchState.items.length) {
      searchDrop.innerHTML = '<div class="p-2 text-muted small">Tidak ada hasil</div>';
      searchDrop.classList.remove('d-none');
      searchDrop.setAttribute('aria-expanded', 'true');
      if (prefixBadge) prefixBadge.classList.add('d-none');
      return;
    }

    searchDrop.innerHTML = searchState.items.map((it, i) => {
      const id = `sr-${it.type}-${it.id}`;
      const badgeCls = typeBadgeClass(it.type);
      const labelHtml = highlightLabel(it.label, q);
      return `
        <div class="vp-search-item${i === 0 ? ' active' : ''}" id="${id}" role="option" aria-selected="${i === 0 ? 'true' : 'false'}" data-id="${it.id}" data-type="${it.type}">
          <span class="vp-search-badge ${badgeCls}">${it.type}</span>
          <span class="vp-search-label">${labelHtml}</span>
        </div>`;
    }).join('');
    searchDrop.classList.remove('d-none');
    searchDrop.setAttribute('aria-expanded', 'true');

    Array.from(searchDrop.querySelectorAll('.vp-search-item')).forEach((node, idx) => {
      node.addEventListener('mousedown', (e) => e.preventDefault());
      node.addEventListener('click', () => selectSearchIndex(idx));
    });
  }
  function setActiveIdx(nextIdx) {
    const nodes = searchDrop ? searchDrop.querySelectorAll('.vp-search-item') : [];
    if (!nodes.length) return;
    searchState.activeIdx = (nextIdx + nodes.length) % nodes.length;
    nodes.forEach((el, i) => {
      const active = i === searchState.activeIdx;
      el.classList.toggle('active', active);
      el.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    const activeEl = nodes[searchState.activeIdx];
    activeEl?.scrollIntoView?.({ block: 'nearest' });
    const id = activeEl?.id;
    if (id) searchDrop.setAttribute('aria-activedescendant', id);
  }
  function selectSearchIndex(idx) {
    const it = searchState.items[idx];
    if (!it || !it.el) return;
    it.el.scrollIntoView({ block: 'center' });
    it.el.classList.add('vp-jump');
    setTimeout(() => it.el.classList.remove('vp-jump'), 1800);
    searchDrop.classList.add('d-none');
    searchDrop.setAttribute('aria-expanded', 'false');
  }
  function updateSearch(q) {
    const s = String(q || '').trim().toLowerCase();
    if (prefixBadge) {
      if (!s) { prefixBadge.classList.add('d-none'); }
      else { prefixBadge.classList.remove('d-none'); prefixBadge.textContent = s.length > 18 ? s.slice(0, 17) + '...' : s; }
    }
    if (!s) {
      if (searchDrop) { searchDrop.classList.add('d-none'); searchDrop.setAttribute('aria-expanded', 'false'); }
      return;
    }
    const items = searchIndex.filter(it => it.label.toLowerCase().includes(s));
    showSearchResults(items, q);
  }
  if (searchInput) {
    searchInput.addEventListener('input', (e) => updateSearch(e.target.value));
    searchInput.addEventListener('keydown', (e) => {
      const visible = searchDrop && !searchDrop.classList.contains('d-none') && searchState.items.length > 0;
      if (!visible) {
        if (e.key === 'Enter') {
          const q = searchInput.value.trim().toLowerCase();
          const first = searchIndex.find(it => it.label.toLowerCase().includes(q));
          if (first && first.el) {
            e.preventDefault();
            first.el.scrollIntoView({ block: 'center' });
            first.el.classList.add('vp-jump');
            setTimeout(() => first.el.classList.remove('vp-jump'), 1800);
          }
        }
        if (e.key === 'Escape') {
          searchDrop?.classList.add('d-none');
          searchDrop?.setAttribute('aria-expanded', 'false');
        }
        return;
      }
      if (e.key === 'ArrowDown') { e.preventDefault(); setActiveIdx(searchState.activeIdx + 1); return; }
      if (e.key === 'ArrowUp') { e.preventDefault(); setActiveIdx(searchState.activeIdx - 1); return; }
      if (e.key === 'Enter') { e.preventDefault(); selectSearchIndex(searchState.activeIdx); return; }
      if (e.key === 'Escape') { e.preventDefault(); searchDrop.classList.add('d-none'); searchDrop.setAttribute('aria-expanded', 'false'); return; }
    });
    document.addEventListener('click', (e) => {
      if (!searchDrop) return;
      if (!searchDrop.contains(e.target) && e.target !== searchInput) {
        searchDrop.classList.add('d-none');
        searchDrop.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // ====== Suggestions (autocomplete parameter)
  const suggestState = new WeakMap();
  const formulaInputMaskState = new WeakMap();

  function isOpaqueIdentifier(token) {
    return /^(?:bp|cp)_[1-9][0-9]*$/i.test(String(token || '').trim());
  }

  function normalizeSuggestKeyword(text) {
    return String(text || '')
      .toLowerCase()
      .replace(/[_\s]+/g, ' ')
      .trim();
  }

  function compactSuggestKeyword(text) {
    return normalizeSuggestKeyword(text).replace(/\s+/g, '');
  }

  function escapeRegExp(source) {
    return String(source || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function buildFormulaLabelAliasEntries(scopeLabels = {}) {
    const entries = [];
    Object.keys(scopeLabels || {}).forEach((code) => {
      const safeCode = normalizeOpaqueCode(code);
      const label = String(scopeLabels[safeCode] || '').trim();
      if (!safeCode || !label) return;
      if (label.toLowerCase() === safeCode) return;
      const normalizedLabel = normalizeSuggestKeyword(label);
      if (!normalizedLabel) return;
      const words = normalizedLabel.split(' ').filter(Boolean);
      if (!words.length) return;
      const pattern = words.map((w) => escapeRegExp(w)).join('[\\s_\\-]+');
      entries.push({
        code: safeCode,
        normalizedLabel,
        pattern,
      });
    });
    entries.sort((a, b) => b.normalizedLabel.length - a.normalizedLabel.length);
    return entries;
  }

  function resolveDisplayFormulaAliases(rawExpr, scopeLabels = {}) {
    const source = String(rawExpr || '');
    if (!source.trim()) return source;
    const trimmedLeading = source.replace(/^\s+/, '');
    const hasLeadingEq = trimmedLeading.startsWith('=');
    let body = hasLeadingEq ? trimmedLeading.slice(1) : trimmedLeading;
    const aliases = buildFormulaLabelAliasEntries(scopeLabels);
    if (!aliases.length) return hasLeadingEq ? `=${body}` : body;

    aliases.forEach((entry) => {
      const re = new RegExp(`(^|[^A-Za-z0-9_])(${entry.pattern})(?=([^A-Za-z0-9_]|$))`, 'gi');
      body = body.replace(re, (full, prefix, matchedLabel, suffix, offset, fullText) => {
        const afterChar = fullText[offset + full.length] || '';
        const matchedNorm = normalizeSuggestKeyword(matchedLabel);
        // Keep formula function calls (e.g. SUM(), MIN()) untouched.
        if (FORMULA_ALLOWED_FUNCTION_SET.has(matchedNorm) && afterChar === '(') {
          return full;
        }
        return `${prefix}${entry.code}`;
      });
    });
    return hasLeadingEq ? `=${body}` : body;
  }

  function insertPastedFormulaText(inputEl, pastedText, options = {}) {
    if (!FORMULA_LABEL_ONLY_UI_ENABLED || !inputEl) return false;
    const text = String(pastedText || '');
    if (!text.trim()) return false;
    const scopeLabels = options.scopeLabels || getFormulaScopeLabels();
    const forceFormula = options.forceFormula === true
      || String(options.currentRaw || '').trim().startsWith('=')
      || /^\s*=/.test(text)
      || /[A-Za-z_]/.test(text);
    const normalizedIncoming = resolveDisplayFormulaAliases(
      normalizeFormulaLeadingEquals(text, { forceFormula }),
      scopeLabels
    );
    const incomingBody = String(normalizedIncoming || '').replace(/^=/, '');
    const currentRaw = String(options.currentRaw || getInputFormulaRaw(inputEl, inputEl.value || ''));
    const currentNormalized = normalizeFormulaLeadingEquals(currentRaw, { forceFormula: forceFormula || currentRaw.trim().startsWith('=') });
    const currentBody = currentNormalized.startsWith('=') ? currentNormalized.slice(1) : currentNormalized;
    const state = formulaInputMaskState.get(inputEl) || buildFormulaLabelMaskState(currentNormalized, {
      forceFormula: forceFormula || currentNormalized.trim().startsWith('='),
      labels: scopeLabels,
    });
    formulaInputMaskState.set(inputEl, state);
    const selStart = Number.isInteger(inputEl.selectionStart) ? inputEl.selectionStart : state.display.length;
    const selEnd = Number.isInteger(inputEl.selectionEnd) ? inputEl.selectionEnd : selStart;
    const rawStart = displayPosToRawPos(selStart, state);
    const rawEnd = displayPosToRawPos(selEnd, state);
    const nextBody = currentBody.slice(0, rawStart) + incomingBody + currentBody.slice(rawEnd);
    const caretRawPos = rawStart + incomingBody.length;
    setInputFormulaRaw(inputEl, `=${nextBody}`, {
      forceFormula: true,
      caretRawPos,
    });
    return true;
  }

  function normalizeFormulaLeadingEquals(rawExpr, options = {}) {
    const source = String(rawExpr || '');
    const forceFormula = options.forceFormula === true;
    const trimmedLeading = source.replace(/^\s+/, '');
    const hasLeadingEq = trimmedLeading.startsWith('=');
    if (!hasLeadingEq && !forceFormula) return source;
    const body = hasLeadingEq ? trimmedLeading.replace(/^=+/, '') : trimmedLeading;
    return `=${body}`;
  }

  function buildFormulaLabelMaskState(rawExpr, options = {}) {
    const source = String(rawExpr || '');
    const forceFormula = options.forceFormula === true;
    const rawWithEq = normalizeFormulaLeadingEquals(source, { forceFormula });
    const rawBody = rawWithEq.startsWith('=') ? rawWithEq.slice(1) : rawWithEq;
    const labels = options.labels || getFormulaScopeLabels();
    const spans = [];
    let display = '';
    let rawPos = 0;
    const re = /[A-Za-z_][A-Za-z0-9_]*/g;
    let m;

    while ((m = re.exec(rawBody)) !== null) {
      const token = String(m[0] || '');
      const tokenLower = token.toLowerCase();
      const tokenStart = m.index;
      const tokenEnd = tokenStart + token.length;
      if (tokenStart > rawPos) {
        display += rawBody.slice(rawPos, tokenStart);
      }
      if (isOpaqueIdentifier(tokenLower) && Object.prototype.hasOwnProperty.call(labels, tokenLower)) {
        const label = String(labels[tokenLower] || tokenLower);
        const displayStart = display.length;
        display += label;
        const displayEnd = display.length;
        spans.push({
          code: tokenLower,
          rawStart: tokenStart,
          rawEnd: tokenEnd,
          displayStart,
          displayEnd,
        });
      } else {
        display += token;
      }
      rawPos = tokenEnd;
    }
    if (rawPos < rawBody.length) display += rawBody.slice(rawPos);

    return { raw: rawWithEq, rawBody, display, spans };
  }

  function rawToDisplayText(rawExpr, labels = null) {
    const state = buildFormulaLabelMaskState(rawExpr, {
      forceFormula: String(rawExpr || '').trim().startsWith('='),
      labels: labels || undefined,
    });
    return state.display;
  }

  function displayToRaw(displayText, cursorMap) {
    const state = cursorMap || null;
    const display = String(displayText || '');
    if (!state || !Array.isArray(state.spans)) {
      return display.trim().startsWith('=') ? display : `=${display}`;
    }
    const spans = state.spans.slice().sort((a, b) => a.displayStart - b.displayStart);
    const out = [];
    let cursor = 0;
    for (const span of spans) {
      if (span.displayStart > cursor) out.push(display.slice(cursor, span.displayStart));
      out.push(state.rawBody.slice(span.rawStart, span.rawEnd));
      cursor = span.displayEnd;
    }
    if (cursor < display.length) out.push(display.slice(cursor));
    return `=${out.join('')}`;
  }

  function displayPosToRawPos(pos, state) {
    const safePos = Math.max(0, Math.min(Number(pos) || 0, state.display.length));
    let delta = 0;
    for (const span of state.spans) {
      if (safePos < span.displayStart) break;
      if (safePos < span.displayEnd) return span.rawStart;
      if (safePos === span.displayEnd) return span.rawEnd;
      delta += (span.rawEnd - span.rawStart) - (span.displayEnd - span.displayStart);
    }
    return safePos + delta;
  }

  function rawPosToDisplayPos(pos, state) {
    const safePos = Math.max(0, Math.min(Number(pos) || 0, state.rawBody.length));
    let delta = 0;
    for (const span of state.spans) {
      if (safePos < span.rawStart) break;
      if (safePos < span.rawEnd) return span.displayStart;
      if (safePos === span.rawEnd) return span.displayEnd;
      delta += (span.displayEnd - span.displayStart) - (span.rawEnd - span.rawStart);
    }
    return safePos + delta;
  }

  function setInputFormulaRaw(inputEl, rawExpr, options = {}) {
    const rawText = String(rawExpr || '');
    if (!FORMULA_LABEL_ONLY_UI_ENABLED) {
      formulaInputMaskState.delete(inputEl);
      const normalized = normalizeFormulaLeadingEquals(rawText, {
        forceFormula: options.forceFormula === true || rawText.trim().startsWith('='),
      });
      inputEl.value = normalized;
      return normalized;
    }
    const normalized = normalizeFormulaLeadingEquals(rawText, {
      forceFormula: options.forceFormula === true || rawText.trim().startsWith('='),
    });
    const state = buildFormulaLabelMaskState(normalized, { forceFormula: options.forceFormula === true });
    formulaInputMaskState.set(inputEl, state);
    inputEl.value = String(state.display || '').replace(/=/g, '');
    if (options.focusEnd) {
      const end = state.display.length;
      inputEl.setSelectionRange(end, end);
    } else if (Number.isFinite(options.caretRawPos)) {
      const dispPos = rawPosToDisplayPos(options.caretRawPos, state);
      inputEl.setSelectionRange(dispPos, dispPos);
    }
    return state.raw;
  }

  function getInputFormulaRaw(inputEl, fallback = '') {
    if (!FORMULA_LABEL_ONLY_UI_ENABLED) return String(inputEl.value || fallback || '');
    const state = formulaInputMaskState.get(inputEl);
    if (state && typeof state.raw === 'string') {
      return normalizeFormulaLeadingEquals(state.raw, { forceFormula: true });
    }
    const next = setInputFormulaRaw(inputEl, fallback || inputEl.value || '');
    return String(next || '');
  }

  function syncMaskedInputFromDisplayEdit(inputEl) {
    if (!FORMULA_LABEL_ONLY_UI_ENABLED) return String(inputEl.value || '');
    const state = formulaInputMaskState.get(inputEl);
    if (!state) return String(inputEl.value || '');

    let nextDisplay = String(inputEl.value || '');
    if (nextDisplay.includes('=')) {
      nextDisplay = nextDisplay.replace(/=/g, '');
      inputEl.value = nextDisplay;
    }
    const prevDisplay = state.display;
    if (nextDisplay === prevDisplay) return state.raw;

    let prefix = 0;
    while (
      prefix < prevDisplay.length
      && prefix < nextDisplay.length
      && prevDisplay[prefix] === nextDisplay[prefix]
    ) {
      prefix++;
    }

    let suffix = 0;
    while (
      suffix < (prevDisplay.length - prefix)
      && suffix < (nextDisplay.length - prefix)
      && prevDisplay[prevDisplay.length - 1 - suffix] === nextDisplay[nextDisplay.length - 1 - suffix]
    ) {
      suffix++;
    }

    const prevChangedEnd = prevDisplay.length - suffix;
    const nextChangedEnd = nextDisplay.length - suffix;
    const inserted = nextDisplay.slice(prefix, nextChangedEnd);

    const overlapSpans = state.spans.filter((span) => (
      prefix < span.displayEnd && prevChangedEnd > span.displayStart
    ));

    let rawStart = displayPosToRawPos(prefix, state);
    let rawEnd = displayPosToRawPos(prevChangedEnd, state);
    if (overlapSpans.length) {
      const minRawStart = Math.min(...overlapSpans.map((s) => s.rawStart));
      const maxRawEnd = Math.max(...overlapSpans.map((s) => s.rawEnd));
      rawStart = Math.min(rawStart, minRawStart);
      rawEnd = Math.max(rawEnd, maxRawEnd);
    }

    const nextRawBody = state.rawBody.slice(0, rawStart) + inserted + state.rawBody.slice(rawEnd);
    const nextRaw = normalizeFormulaLeadingEquals(nextRawBody, { forceFormula: true });
    const caretRawPos = rawStart + inserted.length;
    return setInputFormulaRaw(inputEl, nextRaw, { caretRawPos });
  }

  function insertRawTokenIntoMaskedInput(inputEl, rawToken, options = {}) {
    if (!FORMULA_LABEL_ONLY_UI_ENABLED) return false;
    const insertText = String(rawToken || '');
    if (!insertText) return false;

    const state = formulaInputMaskState.get(inputEl) || buildFormulaLabelMaskState(
      getInputFormulaRaw(inputEl, inputEl.value || ''),
      { forceFormula: true }
    );
    formulaInputMaskState.set(inputEl, state);

    const idf = getCaretIdentifier(inputEl);
    const caret = inputEl.selectionStart ?? state.display.length;
    const displayStart = idf ? idf.start : caret;
    const displayEnd = idf ? idf.end : caret;
    const rawStart = displayPosToRawPos(displayStart, state);
    const rawEnd = displayPosToRawPos(displayEnd, state);
    const nextRawBody = state.rawBody.slice(0, rawStart) + insertText + state.rawBody.slice(rawEnd);
    const nextRaw = normalizeFormulaLeadingEquals(nextRawBody, { forceFormula: true });
    const fallbackOffset = insertText.length;
    const caretOffset = Number.isFinite(options.caretOffset)
      ? Math.max(0, Math.min(Number(options.caretOffset), insertText.length))
      : fallbackOffset;
    const caretRawPos = rawStart + caretOffset;
    setInputFormulaRaw(inputEl, nextRaw, { caretRawPos });
    return true;
  }

  function insertOpaqueCodeIntoMaskedInput(inputEl, code) {
    const safeCode = normalizeOpaqueCode(code);
    if (!isOpaqueIdentifier(safeCode)) return false;
    return insertRawTokenIntoMaskedInput(inputEl, safeCode, { caretOffset: safeCode.length });
  }

  function getCaretIdentifier(inputEl) {
    const value = String(inputEl.value || '');
    const pos = inputEl.selectionStart ?? value.length;
    if (!FORMULA_LABEL_ONLY_UI_ENABLED && !value.trim().startsWith('=')) {
      // Still try to extract an identifier for suggestion matching (parameter hints)
      const hasAlpha = /[A-Za-z_]/.test(value);
      if (!hasAlpha) return null;
    }
    let start = pos, end = pos;
    const isPart = FORMULA_LABEL_ONLY_UI_ENABLED
      ? (c) => /[A-Za-z0-9_'-]/.test(c)
      : (c) => /[A-Za-z0-9_]/.test(c);
    while (start > 0 && isPart(value[start - 1])) start--;
    while (end < value.length && isPart(value[end])) end++;
    const word = value.slice(start, end);
    if (!word) return null;
    if (FORMULA_LABEL_ONLY_UI_ENABLED) {
      if (!/[A-Za-z0-9]/.test(word)) return null;
    } else if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(word)) {
      return null;
    }
    return { word, start, end };
  }

  function shouldShowSuggestionsForEmptyQuery(inputEl) {
    if (!inputEl) return false;
    const value = String(inputEl.value || '');
    const pos = inputEl.selectionStart ?? value.length;
    const left = value.slice(0, pos).replace(/\s+$/, '');
    if (!left) return false;
    const ch = left[left.length - 1] || '';
    return /[=+\-*/,(]/.test(ch);
  }

  function normalizeSuggestionItem(raw) {
    if (raw && typeof raw === 'object') return raw;
    const safeCode = normalizeOpaqueCode(raw);
    if (!safeCode) return null;
    return {
      kind: 'parameter',
      name: safeCode,
      label: safeCode,
      insertText: safeCode,
      caretOffset: safeCode.length,
      value: NaN,
      meta: '',
      searchKeys: [safeCode],
    };
  }

  function scoreFormulaSuggestionItem(item, queryWord) {
    const qNorm = normalizeSuggestKeyword(queryWord);
    if (!qNorm) return 1;
    const qCompact = compactSuggestKeyword(qNorm);
    const qWords = qNorm.split(' ').filter(Boolean);
    const keys = Array.isArray(item.searchKeys) ? item.searchKeys : [item.label || item.name || ''];
    let best = -1;
    keys.forEach((keyRaw) => {
      const keyNorm = normalizeSuggestKeyword(keyRaw);
      if (!keyNorm) return;
      const keyCompact = compactSuggestKeyword(keyRaw);

      if (keyNorm === qNorm) best = Math.max(best, 1400);
      if (keyNorm.startsWith(qNorm)) best = Math.max(best, 1300);
      const idxNorm = keyNorm.indexOf(qNorm);
      if (idxNorm >= 0) best = Math.max(best, 1200 - Math.min(idxNorm, 250));
      if (qCompact) {
        if (keyCompact === qCompact) best = Math.max(best, 1380);
        else if (keyCompact.startsWith(qCompact)) best = Math.max(best, 1280);
        else {
          const idxCompact = keyCompact.indexOf(qCompact);
          if (idxCompact >= 0) best = Math.max(best, 1180 - Math.min(idxCompact, 250));
        }
      }
      if (qWords.length && qWords.every((w) => keyNorm.includes(w))) best = Math.max(best, 1160);
    });
    return best;
  }

  function buildFormulaSuggestionItems(scopeValues = {}, scopeLabels = {}) {
    const codes = Object.keys(scopeLabels || {});
    const parameterItems = codes.map((code) => {
      const safeCode = normalizeOpaqueCode(code);
      const label = String(scopeLabels[safeCode] || safeCode).trim() || safeCode;
      const isComputed = Object.prototype.hasOwnProperty.call(computedParams || {}, safeCode);
      return {
        kind: isComputed ? 'formula-parameter' : 'parameter',
        name: safeCode,
        label,
        value: Number(scopeValues[safeCode] || 0),
        meta: isComputed ? 'Formula Parameter' : 'Parameter',
        insertText: safeCode,
        caretOffset: safeCode.length,
        searchKeys: [label],
      };
    });

    const operationItems = FORMULA_FUNCTION_SUGGESTIONS.map((op) => ({
      kind: 'operation',
      name: String(op.name || '').toLowerCase(),
      label: String(op.label || '').trim() || String(op.name || '').toUpperCase(),
      value: NaN,
      meta: 'Operasi',
      hint: String(op.hint || '').trim(),
      insertText: String(op.insertText || '').trim() || `${String(op.name || '').toUpperCase()}()`,
      caretOffset: Number(op.caretOffset || 0),
      searchKeys: [op.label, op.name, op.hint],
    }));

    return [...parameterItems, ...operationItems];
  }

  function getSuggestHost(inputEl) {
    if (!inputEl) return null;
    const modalHost = inputEl.closest('#vpFormulaEditorModal .vp-fe-input-wrap');
    if (modalHost) return modalHost;
    const cparamHost = inputEl.closest('#vp-pane-computed td');
    if (cparamHost) return cparamHost;
    return inputEl.closest('.vp-cell .flex-grow-1')
      || inputEl.closest('.flex-grow-1')
      || inputEl.parentElement;
  }

  function ensureSuggestBox(inputEl) {
    let state = suggestState.get(inputEl);
    const host = getSuggestHost(inputEl);
    const isModalHost = !!inputEl.closest('#vpFormulaEditorModal');
    if (state && state.box && state.ul) {
      state.host = host || state.host || null;
      state.isModalHost = isModalHost;
      state.box.classList.toggle('vp-suggest-modal', isModalHost);
      if (isModalHost) {
        if (state.box.parentElement !== document.body) document.body.appendChild(state.box);
      } else if (state.host && state.box.parentElement !== state.host) {
        state.host.appendChild(state.box);
      }
      return state;
    }

    const box = document.createElement('div');
    box.className = `vp-suggest${isModalHost ? ' vp-suggest-modal' : ''}`;
    box.style.display = 'none';
    box.style.opacity = '0';
    const ul = document.createElement('ul');
    box.appendChild(ul);
    if (isModalHost) {
      document.body.appendChild(box);
    } else {
      (host || inputEl.parentElement).appendChild(box);
    }
    state = {
      box,
      ul,
      host: host || null,
      isModalHost,
      items: [],
      activeIdx: -1,
      hideTimer: null,
    };
    suggestState.set(inputEl, state);
    return state;
  }
  function hideSuggest(inputEl) {
    const state = suggestState.get(inputEl);
    if (!state) return;
    if (state.hideTimer) {
      clearTimeout(state.hideTimer);
      state.hideTimer = null;
    }
    state.box.style.opacity = '0';
    state.items = [];
    state.activeIdx = -1;
    state.ul.innerHTML = '';
    state.hideTimer = setTimeout(() => {
      state.box.style.display = 'none';
      if (state.isModalHost) {
        state.box.style.left = '';
        state.box.style.top = '';
        state.box.style.bottom = '';
        state.box.style.width = '';
        state.box.style.maxHeight = '';
      }
      state.hideTimer = null;
    }, SUGGEST_HIDE_DELAY_MS);
  }
  function showSuggest(inputEl, items, options = {}) {
    const state = ensureSuggestBox(inputEl);
    if (state.hideTimer) {
      clearTimeout(state.hideTimer);
      state.hideTimer = null;
    }
    // Keep only one visible suggest menu at a time to avoid stale overlays.
    document.querySelectorAll('.vp-suggest').forEach((box) => {
      if (box === state.box) return;
      box.style.opacity = '0';
      box.style.display = 'none';
    });
    state.query = String(options.query || '').trim();
    state.items = items.slice(0, 8);
    state.activeIdx = state.items.length ? 0 : -1;
    state.ul.innerHTML = '';
    if (!state.items.length) {
      const li = document.createElement('li');
      li.className = 'text-muted';
      li.textContent = state.query
        ? 'Tidak ada parameter/formula/operasi tersimpan. Hapus kata ini atau buat parameter baru.'
        : 'Ketik parameter atau operasi untuk melihat saran.';
      state.ul.appendChild(li);
      state.box.style.display = 'block';
      requestAnimationFrame(() => { state.box.style.opacity = '1'; });
      return;
    }

    const groupOrder = [
      { kind: 'parameter', label: 'Parameter' },
      { kind: 'formula-parameter', label: 'Formula Parameter' },
      { kind: 'operation', label: 'Operasi' },
    ];

    const appendGroup = (kind, label) => {
      const grouped = state.items
        .map((it, idx) => ({ ...it, __idx: idx }))
        .filter((it) => String(it.kind || '') === kind);
      if (!grouped.length) return;

      const header = document.createElement('li');
      header.className = 's-group';
      header.textContent = label;
      state.ul.appendChild(header);

      grouped.forEach((it) => {
        const idx = Number(it.__idx);
        const li = document.createElement('li');
        li.setAttribute('data-item-idx', String(idx));
        li.className = idx === state.activeIdx ? 'active' : '';
        const meta = String(it.meta || '').trim();
        const hint = String(it.hint || '').trim();
        const valueHtml = Number.isFinite(it.value)
          ? `<span class="s-value">${formatIdSmart(it.value)}</span>`
          : `<span class="s-value s-value-muted">${escapeHtml(hint || meta || '')}</span>`;
        li.innerHTML = `
          <span class="s-main">
            <span class="s-name">${escapeHtml(it.label)}</span>
            ${meta ? `<span class="s-meta">${escapeHtml(meta)}</span>` : ''}
          </span>
          <span class="d-flex flex-column align-items-end gap-1">
            ${valueHtml}
            <span class="s-shortcut">Enter/Tab</span>
          </span>`;
        li.addEventListener('mousedown', (ev) => {
          ev.preventDefault();
          applySuggestion(inputEl, it);
        });
        state.ul.appendChild(li);
      });
    };

    groupOrder.forEach((group) => appendGroup(group.kind, group.label));
    const hintRow = document.createElement('li');
    hintRow.className = 's-hint-row';
    hintRow.textContent = 'Shortcut: Ctrl+Space buka autosuggestion, Enter/Tab pilih, Esc tutup.';
    state.ul.appendChild(hintRow);

    // Tampilkan lalu atur posisi (flip jika mendekati bawah viewport)
    state.box.style.display = 'block';
    state.box.style.opacity = '0';
    requestAnimationFrame(() => {
      try {
        const host = getSuggestHost(inputEl) || inputEl.parentElement;
        const isModalHost = !!inputEl.closest('#vpFormulaEditorModal');
        state.host = host || null;
        state.isModalHost = isModalHost;
        state.box.classList.toggle('vp-suggest-modal', isModalHost);

        if (isModalHost) {
          if (state.box.parentElement !== document.body) document.body.appendChild(state.box);
        } else if (host && state.box.parentElement !== host) {
          host.appendChild(state.box);
        }

        const rect = isModalHost
          ? inputEl.getBoundingClientRect()
          : host.getBoundingClientRect();
        const menuH = state.box.offsetHeight || 240;
        const gap = 6;
        const spaceBelow = window.innerHeight - rect.bottom;
        const spaceAbove = rect.top;
        const placeDown = spaceBelow >= Math.min(menuH, 160);

        // Reset anchors
        if (isModalHost) {
          state.box.style.position = 'fixed';
          state.box.style.right = 'auto';
          const width = Math.max(220, Math.round(rect.width));
          const maxWidth = Math.max(220, window.innerWidth - 16);
          const clampedWidth = Math.min(width, maxWidth);
          const maxLeft = Math.max(8, window.innerWidth - clampedWidth - 8);
          const left = Math.min(Math.max(8, Math.round(rect.left)), maxLeft);
          state.box.style.left = `${left}px`;
          state.box.style.width = `${clampedWidth}px`;
        } else {
          state.box.style.position = 'absolute';
          state.box.style.left = '0';
          state.box.style.right = '0';
          state.box.style.width = '';
        }
        state.box.style.maxHeight = '';
        state.box.style.top = '';
        state.box.style.bottom = '';
        if (placeDown) {
          state.box.style.top = isModalHost
            ? `${Math.round(rect.bottom + gap)}px`
            : `calc(100% + ${gap}px)`;
          state.box.style.bottom = 'auto';
          const mh = Math.max(120, Math.min(menuH, Math.floor(spaceBelow - gap)));
          state.box.style.maxHeight = `${mh}px`;
        } else {
          state.box.style.top = 'auto';
          if (isModalHost) {
            const mh = Math.max(120, Math.min(menuH, Math.floor(spaceAbove - gap)));
            state.box.style.maxHeight = `${mh}px`;
            state.box.style.top = `${Math.max(8, Math.round(rect.top - gap - mh))}px`;
            state.box.style.bottom = 'auto';
          } else {
            state.box.style.bottom = `calc(100% + ${gap}px)`;
            const mh = Math.max(120, Math.min(menuH, Math.floor(spaceAbove - gap)));
            state.box.style.maxHeight = `${mh}px`;
          }
        }
      } finally {
        state.box.style.opacity = '1';
      }
    });
  }

  // Robust UI->canonical parser for quantity (handles id-ID grouping)
  function canonFromUIQty(raw) {
    let s = String(raw ?? '').trim();
    if (!s) return '';
    s = s.replace(/\u00A0/g, ' ').replace(/\s+/g, '').replace(/_/g, '');
    const hasDot = s.includes('.');
    const hasComma = s.includes(',');
    if (hasDot && !hasComma) {
      const dotGrouping = /^\d{1,3}(\.\d{3})+$/;
      if (dotGrouping.test(s)) s = s.replace(/\./g, '');
      // else: treat dot as decimal (e.g., 1.25)
    } else if (hasComma && !hasDot) {
      const commaGrouping = /^\d{1,3}(,\d{3})+$/;
      if (commaGrouping.test(s)) s = s.replace(/,/g, '');
      else s = s.replace(/,/g, '.'); // comma as decimal
    } else if (hasDot && hasComma) {
      const lastComma = s.lastIndexOf(',');
      const lastDot = s.lastIndexOf('.');
      if (lastComma > lastDot) {
        // comma decimal, dot thousands
        s = s.replace(/\./g, '').replace(/,/g, '.');
      } else {
        // dot decimal, comma thousands
        s = s.replace(/,/g, '');
      }
    }
    // canonical integer/decimal
    if (!/^\-?\d+(\.\d+)?$/.test(s)) return '';
    return s;
  }
  function moveActive(inputEl, delta) {
    const state = suggestState.get(inputEl);
    if (!state || !state.items.length) return;
    state.activeIdx = (state.activeIdx + delta + state.items.length) % state.items.length;
    const lis = state.ul.querySelectorAll('li[data-item-idx]');
    lis.forEach((li) => {
      const idx = Number(li.getAttribute('data-item-idx'));
      li.classList.toggle('active', idx === state.activeIdx);
    });
  }
  function applyActiveSuggestion(inputEl, opts = {}) {
    const state = suggestState.get(inputEl);
    if (!state || state.activeIdx < 0) return false;
    const it = state.items[state.activeIdx];
    if (!it) return false;
    applySuggestion(inputEl, it, opts);
    return true;
  }
  function applySuggestion(inputEl, suggestion, opts = {}) {
    const item = normalizeSuggestionItem(suggestion);
    if (!item) { hideSuggest(inputEl); return; }
    const isOperation = item.kind === 'operation';
    const rawToken = isOperation
      ? String(item.insertText || '').trim() || `${String(item.name || '').toUpperCase()}()`
      : normalizeOpaqueCode(item.insertText || item.name || '');
    const caretOffset = Number.isFinite(item.caretOffset)
      ? Number(item.caretOffset)
      : rawToken.length;
    if (!rawToken) { hideSuggest(inputEl); return; }

    const currentRawValue = FORMULA_LABEL_ONLY_UI_ENABLED
      ? getInputFormulaRaw(inputEl, inputEl.value || '')
      : String(inputEl.value || '');
    const noEqPrefix = !String(currentRawValue || '').trim().startsWith('=');
    const displayValue = String(inputEl.value || '');
    const keywordOnlyNoEq = noEqPrefix && /^[A-Za-z0-9_\s'-]+$/.test(displayValue.trim());

    if (FORMULA_LABEL_ONLY_UI_ENABLED) {
      if (keywordOnlyNoEq) {
        setInputFormulaRaw(inputEl, `=${rawToken}`, {
          forceFormula: true,
          caretRawPos: Math.max(0, Math.min(caretOffset, rawToken.length)),
        });
      } else {
        const inserted = insertRawTokenIntoMaskedInput(inputEl, rawToken, { caretOffset });
        if (!inserted) { hideSuggest(inputEl); return; }
      }
    } else {
      const value = String(inputEl.value || '');
      const caret = inputEl.selectionStart ?? value.length;
      const idf = getCaretIdentifier(inputEl);
      // For plain keyword query (no "=" and no operators), replace entire query to avoid redundant leftovers.
      const before = keywordOnlyNoEq
        ? ''
        : (idf ? value.slice(0, idf.start) : (noEqPrefix ? '' : value.slice(0, caret)));
      const after = keywordOnlyNoEq
        ? ''
        : (idf ? value.slice(idf.end) : (noEqPrefix ? '' : value.slice(caret)));
      const ensureEq = noEqPrefix ? '=' : '';
      inputEl.value = ensureEq + before + rawToken + after;
      const pos = (ensureEq ? 1 : 0) + before.length + Math.max(0, Math.min(caretOffset, rawToken.length));
      inputEl.setSelectionRange(pos, pos);
    }
    if (typeof opts.onAfterInsert === 'function') {
      opts.onAfterInsert();
      hideSuggest(inputEl);
      return;
    }
    const id = Number(opts.id);
    if (Number.isFinite(id) && opts.previewEl) {
      handleInputChange(id, inputEl, opts.previewEl, false);
      hideSuggest(inputEl);
      return;
    }
    const tr = inputEl.closest('tr');
    if (!tr) {
      if (formulaEditorContext && inputEl === formulaEditorInputEl) {
        const id2 = Number(formulaEditorContext.id);
        if (Number.isFinite(id2)) {
          const rawDraft = FORMULA_LABEL_ONLY_UI_ENABLED
            ? getInputFormulaRaw(formulaEditorInputEl, '')
            : String(formulaEditorInputEl.value || '');
          const draftIsFx = String(rawDraft || '').trim().startsWith('=') || !!fxModeById[id2];
          setFormulaDraftEntry(id2, rawDraft, draftIsFx);
        }
        updateFormulaEditorPreview();
        syncFormulaEditorHighlightScroll();
      } else {
        inputEl.dispatchEvent(new Event('input', { bubbles: true }));
      }
      hideSuggest(inputEl);
      return;
    }
    const rowId = parseInt(tr.dataset.pekerjaanId, 10);
    const preview = tr.querySelector('.fx-preview');
    handleInputChange(rowId, inputEl, preview, false);
    hideSuggest(inputEl);
  }
  function getFormulaScopeValues() {
    evaluateComputedParams();
    return { ...variables, ...computedValues };
  }
  function getFormulaScopeLabels() {
    const labels = { ...varLabels };
    Object.keys(computedParams || {}).forEach((code) => {
      if (!labels[code]) labels[code] = computedParams[code]?.label || code;
    });
    return labels;
  }
  function normalizeFormulaPreviewMode(mode) {
    return String(mode || '').trim().toLowerCase() === 'value' ? 'value' : 'label';
  }
  function normalizeFormulaEditorViewMode(mode) {
    return String(mode || '').trim().toLowerCase() === 'raw' ? 'raw' : 'chip';
  }
  function setFormulaPreviewMode(mode, { persist = true } = {}) {
    formulaPreviewMode = normalizeFormulaPreviewMode(mode);
    formulaPreviewModeButtons.forEach((btn) => {
      const active = (btn.dataset.previewMode || '') === formulaPreviewMode;
      btn.classList.toggle('is-active', active);
      btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
    if (persist) {
      try { localStorage.setItem(storageKeyFormulaPreviewMode(), formulaPreviewMode); } catch { }
    }
    updateFormulaEditorPreview();
    refreshRowFormulaPreviews();
  }
  function setFormulaShowInlineValues(enabled, { persist = true } = {}) {
    formulaShowInlineValues = enabled !== false;
    if (formulaEditorShowValuesEl) formulaEditorShowValuesEl.checked = formulaShowInlineValues;
    if (persist) {
      try { localStorage.setItem(storageKeyFormulaInlineValueMode(), formulaShowInlineValues ? '1' : '0'); } catch { }
    }
    updateFormulaEditorPreview();
    refreshRowFormulaPreviews();
  }
  function loadFormulaShowInlineValues() {
    let saved = '1';
    try { saved = localStorage.getItem(storageKeyFormulaInlineValueMode()) || '1'; } catch { }
    setFormulaShowInlineValues(saved !== '0', { persist: false });
  }
  function setFormulaEditorViewMode(mode, { focus = false, caret = 'end' } = {}) {
    formulaEditorViewMode = normalizeFormulaEditorViewMode(mode);
    const isRaw = formulaEditorViewMode === 'raw';
    if (formulaEditorInputWrapEl) formulaEditorInputWrapEl.classList.toggle('d-none', !isRaw);
    if (formulaEditorHighlightLayerEl) formulaEditorHighlightLayerEl.classList.toggle('d-none', !isRaw);
    if (formulaEditorChipPreviewEl) {
      formulaEditorChipPreviewEl.classList.toggle('d-none', isRaw);
      formulaEditorChipPreviewEl.classList.toggle('is-clickable', !isRaw);
      formulaEditorChipPreviewEl.setAttribute('role', 'button');
      formulaEditorChipPreviewEl.setAttribute('tabindex', '0');
      formulaEditorChipPreviewEl.setAttribute('title', 'Klik untuk edit formula');
    }
    if (formulaEditorViewToggleBtn) {
      formulaEditorViewToggleBtn.setAttribute('aria-pressed', isRaw ? 'true' : 'false');
      formulaEditorViewToggleBtn.innerHTML = isRaw
        ? '<i class="bi bi-eye me-1"></i>Lihat Chip'
        : '<i class="bi bi-pencil-square me-1"></i>Edit Formula';
    }
    if (focus && isRaw && formulaEditorInputEl) {
      const preserveCaret = caret === 'preserve';
      const selectionStart = formulaEditorInputEl.selectionStart;
      const selectionEnd = formulaEditorInputEl.selectionEnd;
      formulaEditorInputEl.focus();
      if (preserveCaret && Number.isInteger(selectionStart) && Number.isInteger(selectionEnd)) {
        formulaEditorInputEl.setSelectionRange(selectionStart, selectionEnd);
      } else {
        const len = formulaEditorInputEl.value.length;
        formulaEditorInputEl.setSelectionRange(len, len);
      }
      syncFormulaEditorHighlightScroll();
    }
  }
  function setFormulaResolverState(token = '', message = '') {
    formulaResolverToken = normalizeOpaqueCode(token) || String(token || '').trim().toLowerCase();
    const infoMessage = String(message || '').trim();
    const hasResolvableToken = !!formulaResolverToken;
    const isActive = hasResolvableToken || !!infoMessage;
    if (!formulaEditorResolverEl || !formulaEditorResolverTextEl || !formulaEditorResolveBtn) return;
    formulaEditorResolverEl.classList.toggle('d-none', !isActive);
    if (!isActive) {
      formulaEditorResolverTextEl.textContent = '';
      formulaEditorResolveBtn.disabled = true;
      formulaEditorResolveBtn.classList.add('d-none');
      return;
    }
    const tokenText = formulaResolverToken;
    const fallbackText = FORMULA_LABEL_ONLY_UI_ENABLED
      ? 'Ada parameter yang belum dikenali. Pilih parameter pengganti.'
      : `Token "${tokenText}" belum dikenali. Pilih parameter pengganti.`;
    formulaEditorResolverTextEl.textContent = infoMessage || fallbackText;
    formulaEditorResolveBtn.disabled = !hasResolvableToken;
    formulaEditorResolveBtn.classList.toggle('d-none', !hasResolvableToken);
  }
  function loadFormulaPreviewMode() {
    let saved = 'label';
    try { saved = localStorage.getItem(storageKeyFormulaPreviewMode()) || 'label'; } catch { }
    setFormulaPreviewMode(saved, { persist: false });
  }
  function describeCodeWithLabel(code, scopeLabels = null) {
    const safe = normalizeOpaqueCode(code);
    const labels = scopeLabels || getFormulaScopeLabels();
    const label = String(labels[safe] || safe).trim() || safe;
    if (!FORMULA_LABEL_ONLY_UI_ENABLED) {
      if (!safe || label.toLowerCase() === safe) return safe;
      return `${label} (${safe})`;
    }
    if (!safe || label.toLowerCase() === safe) return 'parameter';
    return label;
  }
  function humanizeFormulaError(message, scopeLabels = null) {
    let text = String(message || '').trim();
    if (!text) return '';
    const labels = scopeLabels || getFormulaScopeLabels();
    text = text.replace(/\b(?:bp|cp)_[1-9][0-9]*\b/gi, (token) => describeCodeWithLabel(token, labels));

    const unknownMatch = text.match(/Variabel tidak dikenal:\s*(.+)$/i);
    if (unknownMatch) {
      const rawVar = String(unknownMatch[1] || '').trim();
      const safeVar = normalizeOpaqueCode(rawVar);
      if (safeVar && /^(?:bp|cp)_[1-9][0-9]*$/.test(safeVar)) {
        const label = String(labels[safeVar] || '').trim();
        if (FORMULA_LABEL_ONLY_UI_ENABLED) {
          const resolved = (label && label.toLowerCase() !== safeVar)
            ? label
            : 'parameter yang dipilih';
          text = text.replace(
            /Variabel tidak dikenal:\s*.+$/i,
            `Parameter tidak ditemukan: ${resolved}`
          );
        } else if (label && label.toLowerCase() !== safeVar) {
          text = text.replace(
            /Variabel tidak dikenal:\s*.+$/i,
            `Parameter tidak ditemukan: ${label} (${safeVar})`
          );
        } else {
          text = text.replace(
            /Variabel tidak dikenal:\s*.+$/i,
            'Parameter tidak ditemukan (mungkin sudah dihapus)'
          );
        }
      } else {
        text = text.replace(
          /Variabel tidak dikenal:\s*.+$/i,
          FORMULA_LABEL_ONLY_UI_ENABLED
            ? 'Parameter tidak ditemukan'
            : `Parameter tidak ditemukan: "${rawVar}"`
        );
      }
    }
    return text;
  }
  function extractUnknownTokenFromMessage(message) {
    const raw = String(message || '');
    const unknownMatch = raw.match(/Variabel tidak dikenal:\s*(.+)$/i);
    if (unknownMatch) return String(unknownMatch[1] || '').trim().toLowerCase();
    const fallbackMatch = raw.match(/Parameter tidak ditemukan:\s*"?([^"\n]+)"?/i);
    if (fallbackMatch) return String(fallbackMatch[1] || '').trim().toLowerCase();
    return '';
  }

  function buildUnknownIdentifierErrorMessage(token) {
    const safeToken = String(token || '').trim();
    if (!safeToken) {
      return 'Formula berisi token yang tidak dikenali. Hapus token tersebut atau pilih dari autosuggestion.';
    }
    return `Tidak ada parameter/formula parameter/operasi tersimpan untuk "${safeToken}". Hapus token ini atau buat parameter baru, lalu pilih dari autosuggestion.`;
  }

  function validateFormulaExpression(rawExpr, options = {}) {
    const initialSource = String(rawExpr || '').trim();
    const source = normalizeFormulaLeadingEquals(initialSource, {
      forceFormula: initialSource.startsWith('='),
    }).trim();
    const scopeValues = options.scopeValues || getFormulaScopeValues();
    const scopeLabels = options.scopeLabels || getFormulaScopeLabels();
    const sourceNoEq = source.replace(/^=/, '').trim();
    if (!sourceNoEq) {
      return { ok: false, message: 'Formula kosong.', invalidToken: '', canResolve: false };
    }
    if (typeof VolFormula === 'undefined' || !VolFormula.tokenize || !VolFormula.evaluate) {
      return { ok: false, message: 'Formula engine tidak tersedia.', invalidToken: '', canResolve: false };
    }
    const expr = source.startsWith('=') ? source : `=${source}`;

    const knownCodes = new Set([
      ...Object.keys(scopeLabels || {}),
      ...Object.keys(scopeValues || {}),
    ].map((code) => normalizeOpaqueCode(code)));

    let tokens = [];
    try {
      tokens = VolFormula.tokenize(expr) || [];
    } catch (err) {
      const rawMessage = String(err?.message || 'Formula tidak valid');
      const unknownToken = extractUnknownTokenFromMessage(rawMessage);
      return {
        ok: false,
        message: humanizeFormulaError(rawMessage, scopeLabels),
        invalidToken: unknownToken,
        canResolve: isOpaqueIdentifier(unknownToken),
      };
    }

    for (const tok of tokens) {
      const type = String(tok?.type || '').toLowerCase();
      const rawValue = String(tok?.value || '').trim();
      const value = normalizeOpaqueCode(rawValue);
      if (!rawValue) continue;

      if (type === 'func') {
        if (!FORMULA_ALLOWED_FUNCTION_SET.has(value)) {
          return {
            ok: false,
            message: `Operasi "${rawValue}" tidak didukung. Gunakan operasi yang tersedia di autosuggestion.`,
            invalidToken: value,
            canResolve: false,
          };
        }
        continue;
      }

      if (type === 'id') {
        const knownCode = knownCodes.has(value);
        if (!isOpaqueIdentifier(value) && !knownCode) {
          return {
            ok: false,
            message: buildUnknownIdentifierErrorMessage(rawValue),
            invalidToken: value,
            canResolve: false,
          };
        }
        if (!knownCode) {
          const label = String(scopeLabels[value] || '').trim();
          return {
            ok: false,
            message: label
              ? `Parameter tidak ditemukan: ${label}. Pilih pengganti dari autosuggestion.`
              : 'Parameter tidak ditemukan (mungkin sudah dihapus). Pilih pengganti dari autosuggestion.',
            invalidToken: value,
            canResolve: true,
          };
        }
      }
    }

    try {
      let val = VolFormula.evaluate(expr, scopeValues, { clampMinZero: false });
      let clampedNegative = false;
      if (!Number.isFinite(val)) val = 0;
      if (val < 0) {
        val = 0;
        clampedNegative = true;
      }
      const rounded = roundHalfUp(val, PARAM_STORE_PLACES);
      return { ok: true, expr, value: rounded, invalidToken: '', canResolve: false, clampedNegative };
    } catch (err) {
      const rawMessage = String(err?.message || 'Formula tidak valid');
      const unknownToken = extractUnknownTokenFromMessage(rawMessage);
      return {
        ok: false,
        message: humanizeFormulaError(rawMessage, scopeLabels),
        invalidToken: unknownToken,
        canResolve: isOpaqueIdentifier(unknownToken),
      };
    }
  }

  function translateFormulaForPreview(exprOrRaw, options = {}) {
    const mode = normalizeFormulaPreviewMode(options.mode || 'label');
    const expr = String(exprOrRaw || '').replace(/^=/, '').trim();
    if (!expr) return '';
    const scopeValues = options.scopeValues || getFormulaScopeValues();
    const scopeLabels = options.scopeLabels || getFormulaScopeLabels();
    const includeInlineValues = !!options.includeInlineValues;

    let translated = '';
    try {
      if (typeof VolFormula !== 'undefined' && VolFormula && typeof VolFormula.tokenize === 'function') {
        const tokens = VolFormula.tokenize(expr);
        if (Array.isArray(tokens) && tokens.length) {
          const pieces = [];
          tokens.forEach((tok) => {
            const type = String(tok?.type || '').toLowerCase();
            const rawValue = String(tok?.value || '');
            const value = rawValue.toLowerCase();
            if (type === 'id') {
              if (mode === 'value' && Object.prototype.hasOwnProperty.call(scopeValues, value)) {
                pieces.push(formatIdSmart(Number(scopeValues[value] || 0)));
                return;
              }
              if (mode === 'label' && Object.prototype.hasOwnProperty.call(scopeLabels, value)) {
                const label = String(scopeLabels[value] || value);
                if (includeInlineValues) {
                  if (Object.prototype.hasOwnProperty.call(scopeValues, value)) {
                    pieces.push(`${label} (${formatIdSmart(Number(scopeValues[value] || 0))})`);
                  } else {
                    pieces.push(`${label} (?)`);
                  }
                } else {
                  pieces.push(label);
                }
                return;
              }
              pieces.push(rawValue);
              return;
            }
            if (type === 'op') { pieces.push(` ${rawValue} `); return; }
            if (type === 'comma') { pieces.push(', '); return; }
            pieces.push(rawValue);
          });
          translated = pieces.join('')
            .replace(/\s+/g, ' ')
            .replace(/\(\s+/g, '(')
            .replace(/\s+\)/g, ')')
            .replace(/\s+,/g, ',')
            .trim();
        }
      }
    } catch {
      translated = '';
    }

    if (translated) return translated;
    const fallbackMap = mode === 'value' ? scopeValues : scopeLabels;
    return expr.replace(/[A-Za-z_][A-Za-z0-9_]*/g, (token) => {
      const code = String(token || '').toLowerCase();
      if (!Object.prototype.hasOwnProperty.call(fallbackMap, code)) return token;
      if (mode === 'value') return formatIdSmart(Number(fallbackMap[code] || 0));
      const label = String(fallbackMap[code] || code);
      if (includeInlineValues) {
        if (Object.prototype.hasOwnProperty.call(scopeValues, code)) {
          return `${label} (${formatIdSmart(Number(scopeValues[code] || 0))})`;
        }
        return `${label} (?)`;
      }
      return label;
    });
  }
  function buildFormulaChipHtml(expr, scopeLabels = null, options = {}) {
    const labels = scopeLabels || getFormulaScopeLabels();
    const compact = !!options.compact;
    let html = '';
    try {
      if (typeof VolFormula !== 'undefined' && VolFormula && typeof VolFormula.tokenize === 'function') {
        const tokens = VolFormula.tokenize(expr);
        if (Array.isArray(tokens) && tokens.length) {
          html = tokens.map((tok) => {
            const type = String(tok?.type || '').toLowerCase();
            const rawValue = String(tok?.value || '');
            const value = rawValue.toLowerCase();
            if (type === 'id' && Object.prototype.hasOwnProperty.call(labels, value)) {
              const label = String(labels[value] || value);
              const chipClass = value.startsWith('cp_')
                ? 'vp-formula-chip vp-chip-computed'
                : 'vp-formula-chip vp-chip-base';
              const titleText = FORMULA_LABEL_ONLY_UI_ENABLED
                ? escapeHtml(label)
                : escapeHtml(value);
              if (compact) {
                return `<span class="${chipClass}" title="${titleText}">${escapeHtml(label)}</span>`;
              }
              if (!FORMULA_LABEL_ONLY_UI_ENABLED) {
                return `<span class="${chipClass}" title="${titleText}">${escapeHtml(label)} <span class="chip-code">${escapeHtml(value)}</span></span>`;
              }
              return `<span class="${chipClass}" title="${titleText}">${escapeHtml(label)}</span>`;
            }
            if (type === 'func' && FORMULA_ALLOWED_FUNCTION_SET.has(value)) {
              return `<span class="vp-formula-chip vp-chip-operation" title="Operasi">${escapeHtml(rawValue.toUpperCase())}</span>`;
            }
            if (type === 'num') {
              return `<span class="vp-formula-chip vp-chip-number">${escapeHtml(rawValue)}</span>`;
            }
            if (type === 'op' || type === 'lp' || type === 'rp' || type === 'comma') {
              return `<span class="vp-formula-chip vp-chip-operator">${escapeHtml(rawValue)}</span>`;
            }
            return `<span class="vp-formula-chip-raw">${escapeHtml(rawValue)}</span>`;
          }).join('');
        }
      }
    } catch {
      html = '';
    }
    if (!html) html = `<span class="vp-formula-chip-raw">${escapeHtml(expr)}</span>`;
    return html;
  }

  function renderFormulaChipPreview(rawExpr, targetEl = formulaEditorChipPreviewEl, options = {}) {
    if (!targetEl) return;
    const expr = String(rawExpr || '').replace(/^=/, '').trim();
    const emptyText = options.emptyText ?? 'Chip preview: pilih parameter agar formula lebih mudah dibaca.';
    if (!expr) {
      targetEl.classList.add('is-empty');
      targetEl.innerHTML = escapeHtml(emptyText);
      if (options.hideWhenEmpty) targetEl.classList.add('d-none');
      return;
    }
    if (options.hideWhenEmpty) targetEl.classList.remove('d-none');
    targetEl.classList.remove('is-empty');
    targetEl.innerHTML = buildFormulaChipHtml(expr, options.scopeLabels || null, { compact: !!options.compact });
  }
  function extractUnknownVarName(message) {
    const m = String(message || '').match(/Variabel tidak dikenal:\s*(.+)$/i);
    return m ? String(m[1] || '').trim().toLowerCase() : '';
  }
  const FORMULA_RESERVED_IDS = new Set([
    ...FORMULA_ALLOWED_FUNCTIONS,
    'pi', 'e', 'true', 'false',
  ]);
  function parseFormulaIdentifierSet(rawExpr) {
    const out = new Set();
    const expr = String(rawExpr || '').trim();
    if (!expr) return out;

    let usedTokenizer = false;
    try {
      if (typeof VolFormula !== 'undefined' && VolFormula && typeof VolFormula.tokenize === 'function') {
        const tokens = VolFormula.tokenize(expr);
        if (Array.isArray(tokens)) {
          tokens.forEach((tok) => {
            const type = String(tok?.type || '').toLowerCase();
            const value = String(tok?.value || '').trim().toLowerCase();
            if (type !== 'id' || !value || FORMULA_RESERVED_IDS.has(value)) return;
            out.add(value);
          });
          usedTokenizer = true;
        }
      }
    } catch {
      // fallback regex below
    }

    if (!usedTokenizer) {
      const matches = expr.match(/[A-Za-z_][A-Za-z0-9_]*/g) || [];
      matches.forEach((m) => {
        const code = String(m || '').trim().toLowerCase();
        if (!code || FORMULA_RESERVED_IDS.has(code)) return;
        out.add(code);
      });
    }

    return out;
  }
  function collectFormulaUsageMap() {
    const usageMap = {};
    const ensureBucket = (code) => {
      const key = String(code || '').trim().toLowerCase();
      if (!key) return null;
      if (!usageMap[key]) {
        usageMap[key] = {
          computedRefs: new Set(),   // computed code that references this variable
          rowRefs: new Map(),        // pekerjaanId -> uraian
        };
      }
      return usageMap[key];
    };

    Object.keys(computedParams || {}).forEach((ownerCode) => {
      const def = computedParams[ownerCode] || {};
      const deps = parseFormulaIdentifierSet(def.expression || '');
      deps.forEach((depCode) => {
        if (depCode === ownerCode) return; // ignore self-reference for usage warnings
        const bucket = ensureBucket(depCode);
        if (!bucket) return;
        bucket.computedRefs.add(ownerCode);
      });
    });

    Object.keys(rawInputById || {}).forEach((rowKey) => {
      const rowId = Number(rowKey);
      const rawExpr = String(rawInputById[rowKey] || '');
      if (!rawExpr.trim()) return;
      if (!isFormulaMode(rowId, rawExpr)) return;
      const deps = parseFormulaIdentifierSet(rawExpr);
      if (!deps.size) return;

      const rowEl = rows.find((r) => Number(r?.dataset?.pekerjaanId) === rowId);
      const rowLabel = getRowUraianText(rowEl) || `Pekerjaan #${rowId}`;

      deps.forEach((depCode) => {
        const bucket = ensureBucket(depCode);
        if (!bucket) return;
        bucket.rowRefs.set(rowId, rowLabel);
      });
    });

    return usageMap;
  }
  function summarizeFormulaUsage(code, usageMap) {
    const key = String(code || '').trim().toLowerCase();
    const bucket = (usageMap && usageMap[key]) ? usageMap[key] : null;
    const computedCodes = bucket ? Array.from(bucket.computedRefs || []) : [];
    const rowRefs = bucket ? Array.from(bucket.rowRefs?.entries?.() || []).map(([id, label]) => ({ id, label })) : [];

    computedCodes.sort((a, b) => (computedParams[a]?.label || a).localeCompare((computedParams[b]?.label || b), 'id'));
    rowRefs.sort((a, b) => Number(a.id) - Number(b.id));

    const computedLabels = computedCodes.map((c) => computedParams[c]?.label || varLabels[c] || c);
    const rowLabels = rowRefs.map((r) => r.label);
    const total = computedCodes.length + rowRefs.length;
    const tooltipParts = [];
    if (computedCodes.length) tooltipParts.push(`Formula turunan: ${computedCodes.length}`);
    if (rowRefs.length) tooltipParts.push(`Formula volume: ${rowRefs.length}`);

    return {
      code: key,
      total,
      computedCount: computedCodes.length,
      rowCount: rowRefs.length,
      computedCodes,
      rowRefs,
      computedLabels,
      rowLabels,
      tooltip: tooltipParts.join(' | '),
    };
  }
  function buildUsageBadgeHtml(summary) {
    const code = summary?.code || '';
    const total = Number(summary?.total || 0);
    const tooltip = total > 0 ? (summary.tooltip || `Dipakai di ${total} formula`) : '';
    const text = total > 0 ? `Dipakai di ${total} formula` : '';
    const hiddenAttr = total > 0 ? '' : ' hidden';
    const titleAttr = tooltip ? ` title="${escapeHtml(tooltip)}"` : '';
    return `<small class="d-block mt-1"><span class="badge text-bg-warning vp-usage-badge" data-code="${escapeHtml(code)}"${hiddenAttr}${titleAttr}>${text}</span></small>`;
  }
  function buildDeleteWarningMessage(kind, label, code, usage) {
    const safeCode = String(code || '').trim();
    const baseLine = (() => {
      if (kind === 'computed') {
        if (!FORMULA_LABEL_ONLY_UI_ENABLED && safeCode) {
          return `Hapus formula turunan "${label}" (kode: ${safeCode})?`;
        }
        return `Hapus formula turunan "${label}"?`;
      }
      if (!FORMULA_LABEL_ONLY_UI_ENABLED && safeCode) {
        return `Hapus parameter "${label}" (kode: ${safeCode})?`;
      }
      return `Hapus parameter "${label}"?`;
    })();
    if (!usage || usage.total <= 0) return baseLine;

    const lines = [baseLine, '', `Item ini dipakai di ${usage.total} formula:`];
    if (usage.computedCount > 0) {
      const preview = usage.computedLabels.slice(0, 3).join(', ');
      const tail = usage.computedCount > 3 ? ` (+${usage.computedCount - 3} lainnya)` : '';
      lines.push(`- Formula turunan (${usage.computedCount}): ${preview}${tail}`);
    }
    if (usage.rowCount > 0) {
      const preview = usage.rowLabels.slice(0, 3).join(', ');
      const tail = usage.rowCount > 3 ? ` (+${usage.rowCount - 3} lainnya)` : '';
      lines.push(`- Formula volume pekerjaan (${usage.rowCount}): ${preview}${tail}`);
    }
    lines.push('', 'Jika tetap dihapus, formula terkait bisa menjadi error. Lanjutkan?');
    return lines.join('\n');
  }
  function refreshUsageBadges() {
    const usageMap = collectFormulaUsageMap();
    const badges = document.querySelectorAll('#vp-var-table .vp-usage-badge[data-code], #vp-cparam-table .vp-usage-badge[data-code]');
    badges.forEach((badge) => {
      const code = String(badge.getAttribute('data-code') || '').trim().toLowerCase();
      const summary = summarizeFormulaUsage(code, usageMap);
      if (!summary.total) {
        badge.hidden = true;
        badge.textContent = '';
        badge.removeAttribute('title');
        return;
      }
      badge.hidden = false;
      badge.textContent = `Dipakai di ${summary.total} formula`;
      badge.setAttribute('title', summary.tooltip || `Dipakai di ${summary.total} formula`);
    });
  }
  function evaluateComputedParams() {
    const defs = computedParams || {};
    const names = Object.keys(defs);
    const resolved = {};
    const errors = {};
    if (!names.length) {
      computedValues = resolved;
      computedErrors = errors;
      return { values: resolved, errors };
    }

    const pending = new Set(names);
    let guard = 0;
    while (pending.size && guard < names.length + 5) {
      guard += 1;
      let progressed = false;
      for (const code of Array.from(pending)) {
        const def = defs[code] || {};
        const rawExpr = String(def.expression || '').trim();
        if (!rawExpr) {
          errors[code] = 'Formula kosong';
          pending.delete(code);
          continue;
        }
        const expr = rawExpr.startsWith('=') ? rawExpr : `=${rawExpr}`;
        const scope = { ...variables, ...resolved };
        try {
          if (typeof VolFormula === 'undefined' || !VolFormula.evaluate) {
            throw new Error('Formula engine tidak tersedia');
          }
          let val = VolFormula.evaluate(expr, scope, { clampMinZero: false });
          if (!Number.isFinite(val) || val < 0) val = 0;
          resolved[code] = roundHalfUp(val, PARAM_STORE_PLACES);
          pending.delete(code);
          progressed = true;
        } catch (err) {
          const msg = String(err?.message || err || 'Formula tidak valid');
          const unknown = extractUnknownVarName(msg);
          // Delay error if dependency is another computed formula that is still pending.
          if (unknown && pending.has(unknown) && unknown !== code) {
            continue;
          }
          errors[code] = msg;
          pending.delete(code);
        }
      }
      if (!progressed) break;
    }

    // Mark unresolved leftovers as cyclic/unresolved dependency.
    if (pending.size) {
      const unresolvedCodes = Array.from(pending.values());
      const unresolvedLabels = unresolvedCodes
        .map((code) => String(defs[code]?.label || code))
        .filter(Boolean);
      const unresolvedHint = unresolvedLabels.slice(0, 4).join(', ');
      const suffix = unresolvedLabels.length > 4 ? ', ...' : '';
      pending.forEach((code) => {
        errors[code] = errors[code]
          || `Dependensi formula tidak bisa diselesaikan (cek siklus/urutan variabel): ${unresolvedHint}${suffix}`;
      });
    }

    computedValues = resolved;
    computedErrors = errors;
    return { values: resolved, errors };
  }
  function updateSuggestions(inputEl, id, options = {}) {
    const raw = String(inputEl.value || '');
    const trimmed = raw.trim();
    const isComputedCtx = options.isComputed === true;
    const inFxMode = isComputedCtx ? true : isFormulaMode(id, raw);
    // Also trigger suggestions when typing parameter-like text (letters) even without "="
    const hasAlphaInput = /[A-Za-z_]/.test(trimmed);
    if (!inFxMode && !hasAlphaInput) { hideSuggest(inputEl); return; }
    let scopeValues, scopeLabels;
    if (options.excludeCode) {
      const scope = buildComputedParamScope(options.excludeCode);
      scopeValues = scope.scopeValues;
      scopeLabels = scope.scopeLabels;
    } else {
      scopeValues = getFormulaScopeValues();
      scopeLabels = getFormulaScopeLabels();
    }
    const itemsAll = buildFormulaSuggestionItems(scopeValues, scopeLabels);
    if (!itemsAll.length) { hideSuggest(inputEl); return; }
    const idf = getCaretIdentifier(inputEl);
    const queryWord = String(idf?.word || '').trim();
    const forceOpen = options && options.forceOpen === true;
    const allowEmptyQuery = shouldShowSuggestionsForEmptyQuery(inputEl);
    if (!forceOpen && !queryWord && !allowEmptyQuery) { hideSuggest(inputEl); return; }
    const scored = itemsAll
      .map((it) => ({ ...it, _score: scoreFormulaSuggestionItem(it, queryWord) }))
      .filter((it) => it._score >= 0);

    scored.sort((a, b) => {
      if (b._score !== a._score) return b._score - a._score;
      const kindA = String(a.kind || '');
      const kindB = String(b.kind || '');
      if (kindA !== kindB) {
        const weight = (kind) => {
          if (kind === 'parameter') return 0;
          if (kind === 'formula-parameter') return 1;
          if (kind === 'operation') return 2;
          return 9;
        };
        return weight(kindA) - weight(kindB);
      }
      return String(a.label || '').localeCompare(String(b.label || ''), 'id');
    });

    const items = scored.map(({ _score, ...rest }) => rest);
    showSuggest(inputEl, items, { query: queryWord });
  }

  function parseIsoMs(raw) {
    const text = String(raw || '').trim();
    if (!text) return 0;
    const ms = Date.parse(text);
    return Number.isFinite(ms) ? ms : 0;
  }

  function formatIsoDateTime(raw) {
    const ms = parseIsoMs(raw);
    if (!ms) return '';
    try {
      return new Date(ms).toLocaleString('id-ID');
    } catch {
      return String(raw || '');
    }
  }

  function normalizeFormulaStateEntry(entry) {
    if (typeof entry === 'string') {
      const rawLegacy = String(entry || '');
      return {
        raw: rawLegacy,
        fx: rawLegacy.trim().startsWith('='),
        updated_at: null,
      };
    }
    if (!entry || typeof entry !== 'object') {
      return { raw: '', fx: false, updated_at: null };
    }
    const raw = String(entry.raw || '');
    const fx = typeof entry.fx === 'boolean'
      ? !!entry.fx
      : !!entry.is_fx;
    const updatedAt = String(entry.updated_at || '').trim();
    return {
      raw,
      fx,
      updated_at: updatedAt || null,
    };
  }

  function normalizeFormulaStateMap(input) {
    const out = {};
    if (!input || typeof input !== 'object') return out;
    Object.keys(input).forEach((key) => {
      const id = Number(key);
      if (!Number.isFinite(id)) return;
      out[id] = normalizeFormulaStateEntry(input[key]);
    });
    return out;
  }

  function shouldProtectLocalFormulaState() {
    return formulaLocalDirty || !!formulaSyncTimer || formulaSyncInFlight;
  }

  function mergeFormulaStateMaps(serverMap, localMap) {
    const server = normalizeFormulaStateMap(serverMap);
    const local = normalizeFormulaStateMap(localMap);
    const merged = {};
    const allIds = new Set([...Object.keys(server), ...Object.keys(local)]);
    allIds.forEach((idKey) => {
      const id = Number(idKey);
      const s = server[id];
      const l = local[id];
      if (!s && l) { merged[id] = l; return; }
      if (!l && s) { merged[id] = s; return; }
      if (!s && !l) return;
      const sMs = parseIsoMs(s?.updated_at);
      const lMs = parseIsoMs(l?.updated_at);
      if (sMs && lMs) {
        merged[id] = lMs >= sMs ? l : s;
        return;
      }
      if (lMs && !sMs) { merged[id] = l; return; }
      if (sMs && !lMs) { merged[id] = s; return; }
      merged[id] = (String(l?.raw || '').trim() || l?.fx) ? l : s;
    });
    return merged;
  }

  function resolveFormulaStateSnapshot(serverMap, localMap) {
    const local = normalizeFormulaStateMap(localMap);
    const server = normalizeFormulaStateMap(serverMap);
    if (shouldProtectLocalFormulaState()) {
      if (!Object.keys(local).length) return server;
      if (!Object.keys(server).length) return local;
      return mergeFormulaStateMaps(server, local);
    }
    if (!Object.keys(server).length) return local;
    if (!Object.keys(local).length) return server;
    return mergeFormulaStateMaps(server, local);
  }

  function hasFormulaStateValue(entry) {
    const normalized = normalizeFormulaStateEntry(entry);
    return !!(String(normalized.raw || '').trim() || normalized.fx);
  }

  function isFormulaStateFreshForVolume(entry, volumeUpdatedAt, hasStoredVolume) {
    if (!hasFormulaStateValue(entry)) return false;
    if (!hasStoredVolume) return true;
    const volumeMs = parseIsoMs(volumeUpdatedAt || '');
    if (!volumeMs) return true;
    const formulaMs = parseIsoMs(entry?.updated_at || '');
    return !!formulaMs && formulaMs >= volumeMs;
  }

  function forgetLocalFormulaState(id) {
    const numericId = Number(id);
    if (!Number.isFinite(numericId)) return;
    try {
      const map = loadFormulas();
      if (Object.prototype.hasOwnProperty.call(map, String(numericId)) || Object.prototype.hasOwnProperty.call(map, numericId)) {
        delete map[numericId];
        delete map[String(numericId)];
        saveFormulas(map);
      }
    } catch { }
    knownFormulaStateIds.delete(numericId);
    formulaDirtySet.delete(numericId);
  }

  function clearFormulaStateForNumericInput(id) {
    const numericId = Number(id);
    if (!Number.isFinite(numericId)) return;
    const localMap = loadFormulas();
    const hasLocal = Object.prototype.hasOwnProperty.call(localMap, String(numericId))
      || Object.prototype.hasOwnProperty.call(localMap, numericId);
    if (!hasLocal && !knownFormulaStateIds.has(numericId) && !fxModeById[numericId]) {
      return;
    }
    delete localMap[numericId];
    delete localMap[String(numericId)];
    saveFormulas(localMap);
    knownFormulaStateIds.delete(numericId);
    fxModeById[numericId] = false;
    formulaDirtySet.add(numericId);
    markFormulaLocalDirty();
    scheduleFormulaServerSync();
  }

  function markFormulaLocalDirty() {
    formulaLocalDirty = true;
    try { localStorage.setItem(storageKeyFormulaDirtyFlag(), '1'); } catch { }
  }

  function clearFormulaLocalDirty() {
    formulaLocalDirty = false;
    try { localStorage.removeItem(storageKeyFormulaDirtyFlag()); } catch { }
  }

  function clearFormulaLocalDirtyIfClean() {
    if (formulaDirtySet.size === 0) clearFormulaLocalDirty();
  }

  function setFormulaSyncAt(ts) {
    const value = String(ts || '').trim();
    if (!value) return;
    formulaSyncAt = value;
    try { localStorage.setItem(storageKeyFormulaSyncAt(), value); } catch { }
  }

  function collectFormulaSyncItems(ids = null) {
    const sourceIds = Array.isArray(ids) && ids.length
      ? ids
      : Array.from(formulaDirtySet.values());
    const normalizedIds = Array.from(new Set(
      sourceIds.map((id) => Number(id)).filter((id) => Number.isFinite(id))
    ));
    return normalizedIds.map((id) => {
      const raw = String(rawInputById[id] || '');
      const isFx = isFormulaMode(id, raw);
      return {
        pekerjaan_id: id,
        raw: isFx ? raw : '',
        is_fx: isFx,
      };
    });
  }

  function collectFormulaSyncValidationIssues(ids = null) {
    const sourceIds = Array.isArray(ids) && ids.length
      ? ids
      : Array.from(formulaDirtySet.values());
    const normalizedIds = Array.from(new Set(
      sourceIds.map((id) => Number(id)).filter((id) => Number.isFinite(id))
    ));
    if (!normalizedIds.length) return [];

    const scopeValues = getFormulaScopeValues();
    const scopeLabels = getFormulaScopeLabels();
    const issues = [];

    normalizedIds.forEach((id) => {
      const raw = String(rawInputById[id] || '').trim();
      if (!raw) {
        setInputValidationError(id, '');
        return;
      }
      if (!isFormulaMode(id, raw)) {
        const canonical = canonFromUIQty(raw);
        if (canonical === '') {
          const hasAlphabet = /[A-Za-z]/.test(raw);
          const msg = hasAlphabet && !raw.startsWith('=')
            ? 'Input tidak valid. Sepertinya ini formula, awali dengan "=" lalu pilih parameter/operasi dari autosuggestion.'
            : 'Input tidak valid. Hanya angka atau formula tersimpan yang diizinkan.';
          setInputValidationError(id, msg);
          issues.push({ id, message: msg });
        } else {
          setInputValidationError(id, '');
        }
        return;
      }
      const validation = validateFormulaExpression(raw, { scopeValues, scopeLabels });
      if (!validation.ok) {
        const msg = String(validation.message || 'Formula tidak valid.');
        setInputValidationError(id, msg);
        issues.push({ id, message: msg });
      } else {
        setInputValidationError(id, '');
      }
    });

    return issues;
  }

  async function syncFormulaStateToServer(ids = null, { reason = 'auto' } = {}) {
    const validationIssues = collectFormulaSyncValidationIssues(ids);
    if (validationIssues.length) {
      showFormulaSyncStatus('error');
      if (reason === 'manual') {
        const first = validationIssues[0];
        TOAST.warn(`Sinkron formula diblokir: baris #${first.id} masih invalid.`);
      }
      setBtnSaveEnabled();
      return { ok: false, blocked: true, synced: 0 };
    }

    const items = collectFormulaSyncItems(ids);
    if (!items.length) return { ok: true, skipped: true, synced: 0 };
    if (formulaSyncInFlight) return { ok: false, busy: true, synced: 0 };

    formulaSyncInFlight = true;
    showFormulaSyncStatus('pending');
    try {
      const res = await HTTP.jpost(EP_FORMULA_STATE, {
        items,
        last_sync_at: formulaSyncAt || null,
      });
      syncFormulaStateToServer._retries = 0;

      if (res.status === 409 || res.data?.error === 'conflict') {
        const staleAt = String(res.data?.server_updated_at || '').trim();
        formulaRemoteStaleAt = staleAt;
        formulaRemotePromptedAt = staleAt || formulaRemotePromptedAt;
        showFormulaSyncStatus('stale');
        const touchedRows = items
          .map((it) => Number(it.pekerjaan_id))
          .filter((it) => Number.isFinite(it))
          .slice(0, 4);
        const touchedText = touchedRows.length ? ` baris #${touchedRows.join(', #')}` : '';
        const staleText = staleAt ? ` (server update ${formatIsoDateTime(staleAt) || staleAt})` : '';
        TOAST.action(`Konflik sinkron formula pada${touchedText}${staleText}. Merge = pertahankan edit lokal + server, Reload = pakai versi server.`, [
          {
            label: 'Merge',
            class: 'btn-warning',
            onClick: () => { mergeFormulaChangesFromServer({ showNotice: true }); },
          },
          {
            label: 'Reload',
            class: 'btn-outline-light',
            onClick: () => { confirmReload('Data formula di server lebih baru.'); },
          },
        ]);
        return { ok: false, conflict: true, synced: 0 };
      }

      if (!(res.ok && res.data?.ok)) {
        showFormulaSyncStatus('error');
        if (reason === 'manual') {
          TOAST.warn('Sinkron formula ke server gagal. Coba simpan ulang.');
        }
        return { ok: false, synced: 0 };
      }

      items.forEach((item) => formulaDirtySet.delete(Number(item.pekerjaan_id)));
      clearFormulaLocalDirtyIfClean();
      if (res.data?.synced_at) setFormulaSyncAt(String(res.data.synced_at));
      formulaRemoteStaleAt = '';
      formulaRemotePromptedAt = '';
      showFormulaSyncStatus('synced');
      setBtnSaveEnabled();
      return { ok: true, synced: items.length };
    } catch (err) {
      console.warn('[VP] Formula sync error:', err);
      showFormulaSyncStatus('error');

      // Sprint 3.6: retry with exponential backoff for transient errors
      const retryCount = (syncFormulaStateToServer._retries || 0);
      if (retryCount < 3) {
        syncFormulaStateToServer._retries = retryCount + 1;
        const delay = Math.pow(2, retryCount) * 1000; // 1s, 2s, 4s
        console.log(`[VP] Retry sync #${retryCount + 1} in ${delay}ms`);
        setTimeout(() => syncFormulaStateToServer(ids, { reason }), delay);
        return { ok: false, retrying: true, synced: 0 };
      }

      syncFormulaStateToServer._retries = 0;
      if (reason === 'manual') {
        TOAST.action('Sinkron formula ke server gagal setelah 3 percobaan.', [{
          label: 'Coba Lagi',
          class: 'btn-warning',
          onClick: () => {
            syncFormulaStateToServer._retries = 0;
            syncFormulaStateToServer(ids, { reason: 'manual' });
          },
        }]);
      } else {
        TOAST.warn('Sinkron formula gagal. Coba simpan manual.');
      }
      return { ok: false, error: String(err?.message || err || ''), synced: 0 };
    } finally {
      formulaSyncInFlight = false;
    }
  }

  function scheduleFormulaServerSync() {
    if (formulaSyncTimer) clearTimeout(formulaSyncTimer);
    showFormulaSyncStatus('pending');
    formulaSyncTimer = setTimeout(async () => {
      formulaSyncTimer = null;
      await syncFormulaStateToServer(null, { reason: 'auto' });
    }, FORMULA_SYNC_DELAY);
  }

  async function fetchFormulaStateSnapshotFromServer() {
    try {
      const resp = await HTTP.jget(EP_FORMULA_STATE);
      if (!(resp && resp.ok && Array.isArray(resp.items))) return null;
      const map = {};
      resp.items.forEach((it) => {
        const id = Number(it?.pekerjaan_id);
        if (!Number.isFinite(id)) return;
        map[id] = {
          raw: String(it?.raw || ''),
          fx: !!it?.is_fx,
          updated_at: String(it?.updated_at || '').trim() || null,
        };
      });
      return {
        synced_at: String(resp.synced_at || '').trim() || null,
        map,
      };
    } catch {
      return null;
    }
  }

  function applyFormulaSnapshotToRows(formulaMap) {
    const snapshot = normalizeFormulaStateMap(formulaMap);
    rows.forEach((tr) => {
      const id = parseInt(tr.dataset.pekerjaanId, 10);
      if (!Number.isFinite(id)) return;
      if (formulaEditorContext && Number(formulaEditorContext.id) === id) return;
      const item = snapshot[id];
      if (!item || typeof item.raw !== 'string') return;
      const input = tr.querySelector('.qty-input');
      const preview = tr.querySelector('.fx-preview');
      if (!input) return;
      rawInputById[id] = item.raw;
      input.value = item.raw;
      setFxState(id, !!item.fx);
      handleInputChange(id, input, preview, false);
    });
    setBtnSaveEnabled();
  }

  async function mergeFormulaChangesFromServer(options = {}) {
    const result = await fetchFormulaStateSnapshotFromServer();
    if (!result) {
      TOAST.warn('Tidak bisa mengambil perubahan formula dari server.');
      return false;
    }
    const local = loadFormulas();
    const merged = mergeFormulaStateMaps(result.map, local);
    saveFormulas(merged);
    applyFormulaSnapshotToRows(merged);
    if (result.synced_at) setFormulaSyncAt(result.synced_at);
    formulaRemoteStaleAt = '';
    formulaRemotePromptedAt = '';
    showFormulaSyncStatus('synced');
    if (options.showNotice !== false) {
      TOAST.ok('Perubahan formula terbaru berhasil digabungkan.');
    }
    return true;
  }

  async function checkFormulaRemoteChanges(options = {}) {
    const force = options.force === true;
    if (!force && formulaSyncInFlight) return;
    const result = await fetchFormulaStateSnapshotFromServer();
    if (!result || !result.synced_at) return;
    const serverMs = parseIsoMs(result.synced_at);
    const localMs = parseIsoMs(formulaSyncAt);
    if (!serverMs) return;
    if (!localMs) {
      setFormulaSyncAt(result.synced_at);
      return;
    }
    if (serverMs <= localMs) return;

    formulaRemoteStaleAt = result.synced_at;
    showFormulaSyncStatus('stale');
    if (formulaRemotePromptedAt === result.synced_at) return;
    formulaRemotePromptedAt = result.synced_at;

    TOAST.action('Data formula berubah di server. Pilih merge atau reload.', [
      {
        label: 'Merge',
        class: 'btn-warning',
        onClick: () => { mergeFormulaChangesFromServer({ showNotice: true }); },
      },
      {
        label: 'Reload',
        class: 'btn-outline-light',
        onClick: () => { confirmReload('Data formula berubah di server.'); },
      },
    ]);
  }

  function startFormulaRemoteWatch() {
    if (formulaRemoteWatchTimer) clearInterval(formulaRemoteWatchTimer);
    formulaRemoteWatchTimer = setInterval(() => {
      if (document.hidden) return;
      checkFormulaRemoteChanges();
    }, FORMULA_REMOTE_WATCH_MS);
    window.addEventListener('focus', () => {
      checkFormulaRemoteChanges({ force: true });
    });
  }

  function persistRowFormula(id) {
    const nowIso = new Date().toISOString();
    const map = loadFormulas();
    map[id] = {
      raw: String(rawInputById[id] || ''),
      fx: !!fxModeById[id],
      updated_at: nowIso,
    };
    saveFormulas(map);
    knownFormulaStateIds.add(Number(id));
    formulaDirtySet.add(Number(id));
    markFormulaLocalDirty();
    scheduleFormulaServerSync();
  }

  // ==== Wiring baris pekerjaan
  function collectQtyInputs() {
    // Global: karena input bisa tersebar di beberapa sub-tabel dalam card
    return Array.from(document.querySelectorAll('.qty-input'));
  }

  function focusNextFrom(currentEl, delta) {
    const inputs = collectQtyInputs();
    const idx = inputs.indexOf(currentEl);
    if (idx === -1) return;
    let next = idx + delta;
    if (next < 0) next = 0;
    if (next >= inputs.length) next = inputs.length - 1;
    const tgt = inputs[next];
    if (tgt) { tgt.focus(); try { tgt.select(); } catch { } }
  }

  function setQtyInputInteractionMode(inputEl, isFormulaModeActive) {
    if (!inputEl) return;
    const formulaMode = !!isFormulaModeActive;
    inputEl.setAttribute('inputmode', formulaMode ? 'text' : 'decimal');
    inputEl.setAttribute(
      'title',
      formulaMode
        ? 'Mode formula aktif. Gunakan Ctrl+Space untuk autosuggestion atau buka editor formula (Alt+Enter).'
        : 'Ketik angka. Gunakan "=" untuk formula atau Ctrl+Space untuk autosuggestion.'
    );
  }

  function syncQtyInputInteractionModeForRow(id) {
    const numericId = Number(id);
    if (!Number.isFinite(numericId)) return;
    const tr = rows.find((r) => parseInt(r.dataset.pekerjaanId, 10) === numericId);
    if (!tr) return;
    const input = tr.querySelector('.qty-input');
    if (!input) return;
    const raw = String(rawInputById[numericId] || input.value || '');
    setQtyInputInteractionMode(input, isFormulaMode(numericId, raw));
  }

  function setFxState(id, nextState) {
    const on = !!nextState;
    fxModeById[id] = on;
    syncQtyInputInteractionModeForRow(id);
  }

  function ensureFormulaEditorModal() {
    if (!formulaEditorModalEl || !window.bootstrap) return null;
    if (!formulaEditorModal) {
      formulaEditorModal = bootstrap.Modal.getOrCreateInstance(formulaEditorModalEl, {
        backdrop: VP_DISABLE_MODAL_BACKDROP ? false : true,
      });
    }
    try {
      if (formulaEditorModal?._config) {
        formulaEditorModal._config.backdrop = VP_DISABLE_MODAL_BACKDROP ? false : true;
      }
    } catch { }
    if (VP_DISABLE_MODAL_BACKDROP) {
      formulaEditorModalEl.setAttribute('data-bs-backdrop', 'false');
    }
    return formulaEditorModal;
  }

  function isComputedFormulaEditorContext(ctx = formulaEditorContext) {
    const contextType = String(ctx?.contextType || '');
    return contextType === 'computed' || contextType === 'computed-new';
  }

  function normalizeComputedLabelInput(value, fallback = '') {
    const text = String(value ?? '').replace(/\s+/g, ' ').trim();
    if (text) return text;
    return String(fallback || '').replace(/\s+/g, ' ').trim();
  }

  function getFormulaEditorComputedLabelValue(fallback = '') {
    if (!formulaEditorComputedNameEl) return normalizeComputedLabelInput(fallback);
    return normalizeComputedLabelInput(formulaEditorComputedNameEl.value, fallback);
  }

  function setFormulaEditorComputedNameMode(options = {}) {
    if (!formulaEditorComputedNameWrapEl || !formulaEditorComputedNameEl) return;
    const visible = !!options.visible;
    formulaEditorComputedNameWrapEl.classList.toggle('d-none', !visible);
    formulaEditorComputedNameEl.disabled = !visible;
    formulaEditorComputedNameEl.readOnly = !!options.readOnly;
    formulaEditorComputedNameEl.classList.remove('is-invalid');
    if (!visible) {
      formulaEditorComputedNameEl.value = '';
      return;
    }
    const nextLabel = normalizeComputedLabelInput(options.label, options.fallback || '');
    formulaEditorComputedNameEl.value = nextLabel;
    if (options.focus) {
      setTimeout(() => {
        try { formulaEditorComputedNameEl.focus(); } catch { }
      }, 0);
    }
  }

  function getFormulaEditorDirtyState() {
    if (!formulaEditorContext || !formulaEditorInputEl) return false;
    const currentRaw = getFormulaEditorRawValue(formulaEditorOpenRaw || '');
    const rawDirty = String(currentRaw || '') !== String(formulaEditorOpenRaw || '');
    let labelDirty = false;
    if (isComputedFormulaEditorContext(formulaEditorContext) && formulaEditorContext.allowNameEdit) {
      const originalLabel = normalizeComputedLabelInput(
        formulaEditorOpenComputedLabel || formulaEditorContext.label || '',
      );
      const currentLabel = getFormulaEditorComputedLabelValue(originalLabel);
      labelDirty = String(currentLabel || '') !== String(originalLabel || '');
    }
    return rawDirty || labelDirty;
  }

  function getFormulaEditorRawValue(fallback = '') {
    if (!formulaEditorInputEl) return String(fallback || '');
    const raw = FORMULA_LABEL_ONLY_UI_ENABLED
      ? getInputFormulaRaw(formulaEditorInputEl, fallback || formulaEditorInputEl.value || '')
      : String(formulaEditorInputEl.value || fallback || '');
    const isComputedCtx = isComputedFormulaEditorContext(formulaEditorContext);
    const shouldForceFormula = !!formulaEditorContext
      && (isComputedCtx || (Number.isFinite(Number(formulaEditorContext.id))
      && (String(raw || '').trim().startsWith('=') || !!fxModeById[Number(formulaEditorContext.id)])));
    return normalizeFormulaLeadingEquals(raw, { forceFormula: shouldForceFormula });
  }

  function setFormulaEditorBackdropState(isStatic) {
    if (!formulaEditorModalEl) return;
    if (VP_DISABLE_MODAL_BACKDROP) {
      formulaEditorModalEl.setAttribute('data-bs-backdrop', 'false');
      try {
        const modalNoBackdrop = bootstrap?.Modal?.getInstance(formulaEditorModalEl);
        if (modalNoBackdrop && modalNoBackdrop._config) {
          modalNoBackdrop._config.backdrop = false;
        }
      } catch { }
      return;
    }
    const staticBackdrop = !!isStatic;
    formulaEditorModalEl.setAttribute('data-bs-backdrop', staticBackdrop ? 'static' : 'true');
    try {
      const modal = bootstrap?.Modal?.getInstance(formulaEditorModalEl);
      if (modal && modal._config) {
        modal._config.backdrop = staticBackdrop ? 'static' : true;
      }
    } catch { }
  }

  function syncFormulaEditorDirtyState() {
    if (!formulaEditorContext || !formulaEditorInputEl) {
      setFormulaEditorBackdropState(false);
      return;
    }
    const dirty = getFormulaEditorDirtyState();
    setFormulaEditorBackdropState(dirty);
  }

  function ensureParamPaletteModal() {
    if (!paramPaletteModalEl || !window.bootstrap) return null;
    if (!paramPaletteModal) {
      paramPaletteModal = bootstrap.Modal.getOrCreateInstance(paramPaletteModalEl, {
        backdrop: VP_DISABLE_MODAL_BACKDROP ? false : true,
      });
    }
    try {
      if (paramPaletteModal?._config) {
        paramPaletteModal._config.backdrop = VP_DISABLE_MODAL_BACKDROP ? false : true;
      }
    } catch { }
    if (VP_DISABLE_MODAL_BACKDROP) {
      paramPaletteModalEl.setAttribute('data-bs-backdrop', 'false');
    }
    return paramPaletteModal;
  }

  function buildParamPaletteItems() {
    const excludeCode = (formulaEditorContext?.contextType === 'computed' || formulaEditorContext?.contextType === 'computed-new') ? formulaEditorContext.code : '';
    let scopeValues, scopeLabels;
    if (excludeCode) {
      const scope = buildComputedParamScope(excludeCode);
      scopeValues = scope.scopeValues;
      scopeLabels = scope.scopeLabels;
    } else {
      scopeValues = getFormulaScopeValues();
      scopeLabels = getFormulaScopeLabels();
    }
    const codes = Object.keys(scopeLabels || {});
    return codes
      .map((code) => {
        const safe = normalizeOpaqueCode(code);
        const label = String(scopeLabels[safe] || safe).trim() || safe;
        return {
          code: safe,
          label,
          value: Number(scopeValues[safe] || 0),
          type: Object.prototype.hasOwnProperty.call(computedParams || {}, safe) ? 'Turunan' : 'Parameter',
        };
      })
      .sort((a, b) => a.label.localeCompare(b.label, 'id'));
  }

  function renderParamPaletteList(query = '') {
    if (!paramPaletteListEl) return;
    const qNorm = normalizeSuggestKeyword(query);
    const qCompact = compactSuggestKeyword(query);
    const all = buildParamPaletteItems();
    const filtered = !qNorm
      ? all
      : all.filter((item) => {
        const labelNorm = normalizeSuggestKeyword(item.label);
        const labelCompact = compactSuggestKeyword(item.label);
        return labelNorm.includes(qNorm) || (qCompact && labelCompact.includes(qCompact));
      });

    if (!filtered.length) {
      paramPaletteListEl.innerHTML = '<div class="vp-palette-empty">Tidak ada parameter/formula parameter yang cocok.</div>';
      return;
    }

    paramPaletteListEl.innerHTML = filtered.map((item) => `
      <button type="button" class="vp-palette-row" data-code="${escapeHtml(item.code)}">
        <span class="vp-palette-main">
          <span class="vp-palette-label">${escapeHtml(item.label)}</span>
        </span>
        <span class="vp-palette-meta">
          <span class="vp-palette-badge">${escapeHtml(item.type)}</span>
          <span>${formatIdSmart(item.value)}</span>
        </span>
      </button>
    `).join('');
  }

  function openParamPalette(options = {}) {
    if (!formulaEditorContext || !formulaEditorInputEl) return;
    const modal = ensureParamPaletteModal();
    if (!modal) return;
    const nextQuery = String(options.query ?? paramPaletteSearchEl?.value ?? '').trim();
    if (paramPaletteSearchEl) paramPaletteSearchEl.value = nextQuery;
    renderParamPaletteList(nextQuery);
    modal.show();
    setTimeout(() => {
      paramPaletteSearchEl?.focus();
      if (paramPaletteSearchEl && nextQuery) {
        const len = paramPaletteSearchEl.value.length;
        paramPaletteSearchEl.setSelectionRange(len, len);
      }
    }, 80);
  }

  function replaceIdentifierToken(rawExpr, targetToken, replacementCode) {
    const source = String(rawExpr || '');
    const target = String(targetToken || '').trim().toLowerCase();
    const replacement = String(replacementCode || '').trim().toLowerCase();
    if (!source || !target || !replacement || target === replacement) return source;
    return source.replace(/[A-Za-z_][A-Za-z0-9_]*/g, (token) => {
      return String(token || '').trim().toLowerCase() === target ? replacement : token;
    });
  }

  function applyFormulaResolverReplacement(replacementCode) {
    if (!formulaEditorInputEl || !formulaResolverToken) return false;
    const currentRaw = FORMULA_LABEL_ONLY_UI_ENABLED
      ? getInputFormulaRaw(formulaEditorInputEl, formulaEditorInputEl.value || '')
      : String(formulaEditorInputEl.value || '');
    const next = replaceIdentifierToken(currentRaw, formulaResolverToken, replacementCode);
    if (next === currentRaw) return false;
    if (FORMULA_LABEL_ONLY_UI_ENABLED) {
      setInputFormulaRaw(formulaEditorInputEl, next, { forceFormula: true });
    } else {
      formulaEditorInputEl.value = next;
    }
    setFormulaResolverState('', '');
    updateFormulaEditorPreview();
    if (formulaEditorContext) updateSuggestions(formulaEditorInputEl, formulaEditorContext.id);
    setFormulaEditorViewMode('raw', { focus: true });
    return true;
  }

  function updateInlineFormulaVisibility(tr, options = {}) {
    if (!tr) return;
    const id = parseInt(tr.dataset.pekerjaanId, 10);
    if (!Number.isFinite(id)) return;
    const input = tr.querySelector('.qty-input');
    const preview = tr.querySelector('.fx-preview');
    if (!input) return;

    const raw = String(rawInputById[id] || input.value || '');
    const formulaActive = isFormulaMode(id, raw);
    const showRaw = !formulaActive;

    input.classList.remove('d-none');
    input.classList.toggle('vp-input-hidden', !showRaw);
    if (!showRaw) {
      input.setAttribute('aria-hidden', 'true');
      input.setAttribute('tabindex', '-1');
      input.readOnly = true;
      if (document.activeElement === input) input.blur();
    } else {
      input.removeAttribute('aria-hidden');
      input.removeAttribute('tabindex');
      input.readOnly = false;
    }
    setQtyInputInteractionMode(input, formulaActive);
    if (preview) {
      preview.classList.toggle('d-none', !formulaActive && !hasDualPreviewContent(preview));
    }
  }

  function getRowUraianText(tr) {
    if (!tr) return '';
    const uraianTd = tr.querySelector('td.text-wrap');
    return String(uraianTd?.textContent || '').trim();
  }

  function syncFormulaEditorHighlightScroll() {
    if (!formulaEditorInputEl || !formulaEditorHighlightContentEl) return;
    const x = Number(formulaEditorInputEl.scrollLeft || 0);
    const y = Number(formulaEditorInputEl.scrollTop || 0);
    formulaEditorHighlightContentEl.style.transform = `translate(${-x}px, ${-y}px)`;
  }

  function isRangeInsideAnySpan(start, end, spans = []) {
    return spans.some((span) => start >= span.displayStart && end <= span.displayEnd);
  }

  function collectFormulaEditorInvalidTokens(rawExpr, options = {}) {
    const raw = String(rawExpr || '');
    const displayText = String(options.displayText ?? formulaEditorInputEl?.value ?? '');
    const state = options.state || formulaInputMaskState.get(formulaEditorInputEl) || { spans: [] };
    const isFormula = String(raw || '').trim().startsWith('=') || !!options.forceFormula;
    if (!isFormula) return [];

    const invalid = [];
    const spans = Array.isArray(state?.spans) ? state.spans : [];
    const knownCodes = new Set([
      ...Object.keys(getFormulaScopeLabels() || {}),
      ...Object.keys(getFormulaScopeValues() || {}),
    ].map((code) => normalizeOpaqueCode(code)));
    const reWord = /[A-Za-z_][A-Za-z0-9_'-]*/g;
    let m;
    while ((m = reWord.exec(displayText)) !== null) {
      const token = String(m[0] || '');
      const start = Number(m.index || 0);
      const end = start + token.length;
      if (isRangeInsideAnySpan(start, end, spans)) continue;

      const safeToken = normalizeOpaqueCode(token.replace(/'/g, ''));
      if (!safeToken) continue;
      const nextChars = displayText.slice(end);
      const nextNonSpace = (nextChars.match(/\S/) || [])[0] || '';
      if (FORMULA_ALLOWED_FUNCTION_SET.has(safeToken) && nextNonSpace === '(') continue;
      if (FORMULA_RESERVED_IDS.has(safeToken)) continue;
      if (knownCodes.has(safeToken)) continue;

      invalid.push({
        token,
        safeToken,
        start,
        end,
      });
    }
    return invalid.sort((a, b) => a.start - b.start);
  }

  function renderFormulaEditorInvalidOverlay(invalidTokens = []) {
    if (!formulaEditorHighlightContentEl || !formulaEditorInputEl) return;
    const text = String(formulaEditorInputEl.value || '');
    if (!text) {
      formulaEditorHighlightContentEl.innerHTML = '&nbsp;';
      syncFormulaEditorHighlightScroll();
      return;
    }
    const spans = Array.isArray(invalidTokens) ? invalidTokens.slice().sort((a, b) => a.start - b.start) : [];
    const html = [];
    let cursor = 0;
    spans.forEach((span) => {
      const start = Math.max(cursor, Number(span.start) || 0);
      const end = Math.max(start, Number(span.end) || start);
      if (start > cursor) html.push(escapeHtml(text.slice(cursor, start)));
      if (end > start) {
        html.push(`<mark class="vp-fe-invalid-token">${escapeHtml(text.slice(start, end))}</mark>`);
      }
      cursor = Math.max(cursor, end);
    });
    if (cursor < text.length) html.push(escapeHtml(text.slice(cursor)));
    formulaEditorHighlightContentEl.innerHTML = html.join('') || '&nbsp;';
    syncFormulaEditorHighlightScroll();
  }

  function setFormulaEditorBlockState(blocked, reason = '') {
    formulaEditorHasBlockingError = !!blocked;
    formulaEditorBlockingMessage = String(reason || '').trim();
    if (formulaEditorApplyBtn) {
      formulaEditorApplyBtn.disabled = formulaEditorHasBlockingError;
      formulaEditorApplyBtn.setAttribute('title', formulaEditorHasBlockingError ? formulaEditorBlockingMessage : '');
    }
    if (formulaEditorBlockEl && formulaEditorBlockTextEl) {
      const active = formulaEditorHasBlockingError && !!formulaEditorBlockingMessage;
      formulaEditorBlockEl.classList.toggle('d-none', !active);
      formulaEditorBlockTextEl.textContent = active ? formulaEditorBlockingMessage : '';
    }
    setBtnSaveEnabled();
  }

  function pushFormulaUndoSnapshot(id, prevRaw, prevFx) {
    const numericId = Number(id);
    if (!Number.isFinite(numericId)) return;
    formulaUndoById.set(numericId, {
      raw: String(prevRaw || ''),
      fx: !!prevFx,
      updated_at: new Date().toISOString(),
    });
  }

  function updateFormulaUndoButtonState() {
    if (!formulaEditorUndoBtn) return;
    const id = Number(formulaEditorContext?.id);
    const canUndo = Number.isFinite(id) && formulaUndoById.has(id);
    formulaEditorUndoBtn.disabled = !canUndo;
    formulaEditorUndoBtn.setAttribute('title', canUndo ? 'Kembalikan formula terakhir pada baris ini.' : 'Belum ada riwayat formula untuk dibatalkan.');
  }

  function setFormulaEditorPreviewState(state = 'empty', options = {}) {
    if (!formulaEditorPreviewEl) return;
    setDualPreviewState(formulaEditorPreviewEl, state, {
      label: options.label ?? '-',
      value: options.value ?? '-',
      error: options.error || '',
      forceVisible: true,
    });
  }

  function updateFormulaEditorPreview() {
    if (!formulaEditorContext || !formulaEditorPreviewEl || !formulaEditorInputEl) return;

    const isComputedCtx = formulaEditorContext.contextType === 'computed' || formulaEditorContext.contextType === 'computed-new';
    const { id } = formulaEditorContext;
    const fallbackRaw = isComputedCtx ? '' : (rawInputById[id] || '');
    let raw = FORMULA_LABEL_ONLY_UI_ENABLED
      ? getInputFormulaRaw(formulaEditorInputEl, fallbackRaw || formulaEditorInputEl.value || '')
      : String(formulaEditorInputEl.value || '');
    raw = normalizeFormulaLeadingEquals(raw, {
      forceFormula: isComputedCtx || String(raw || '').trim().startsWith('=') || !!fxModeById[id],
    });
    const trimmed = raw.trim();
    let scopeValues, scopeLabels;
    if (isComputedCtx) {
      const scope = buildComputedParamScope(formulaEditorContext.code);
      scopeValues = scope.scopeValues;
      scopeLabels = scope.scopeLabels;
    } else {
      scopeValues = getFormulaScopeValues();
      scopeLabels = getFormulaScopeLabels();
    }
    const maskState = formulaInputMaskState.get(formulaEditorInputEl);
    formulaEditorInvalidTokens = collectFormulaEditorInvalidTokens(trimmed, {
      displayText: formulaEditorInputEl.value || '',
      state: maskState,
      forceFormula: isComputedCtx || !!fxModeById[id] || trimmed.startsWith('='),
    });
    renderFormulaEditorInvalidOverlay(formulaEditorInvalidTokens);

    ensureDualPreviewSlots(formulaEditorPreviewEl);
    renderFormulaChipPreview(trimmed, formulaEditorChipPreviewEl, { scopeLabels });
    updateFormulaUndoButtonState();

    if (!trimmed) {
      setFormulaResolverState('', '');
      setFormulaEditorPreviewState('empty');
      setFormulaEditorBlockState(false, '');
      return;
    }

    const isFx = isComputedCtx || !!fxModeById[id] || trimmed.startsWith('=');
    if (!isFx) {
      setFormulaResolverState('', '');
      const normalized = normQty(trimmed);
      if (normalized) {
        setFormulaEditorPreviewState('success', { value: normalized });
        setFormulaEditorBlockState(false, '');
      } else {
        const msg = 'Input tidak valid. Masukkan angka atau gunakan formula dari autosuggestion.';
        setFormulaEditorPreviewState('error', { error: msg });
        setFormulaResolverState('', msg);
        setFormulaEditorBlockState(true, msg);
      }
      return;
    }

    if (formulaEditorInvalidTokens.length) {
      const tokenList = formulaEditorInvalidTokens
        .slice(0, 3)
        .map((tok) => `"${tok.token}"`)
        .join(', ');
      const suffix = formulaEditorInvalidTokens.length > 3 ? '...' : '';
      const msg = `Token tidak valid: ${tokenList}${suffix}. Hapus/ganti token lalu pilih dari autosuggestion.`;
      setFormulaEditorPreviewState('error', { error: msg });
      setFormulaResolverState('', msg);
      setFormulaEditorBlockState(true, msg);
      return;
    }

    const validation = validateFormulaExpression(trimmed, { scopeValues, scopeLabels });
    if (validation.ok) {
      const previewParts = buildCombinedFormulaPreviewParts(validation.expr, validation.value, scopeValues, {
        scopeLabels,
        includeInlineValues: formulaShowInlineValues,
      });
      setFormulaEditorPreviewState('success', {
        label: previewParts.labelPreview,
        value: previewParts.valuePreview,
      });
      if (validation.clampedNegative) {
        setFormulaResolverState('', 'Hasil formula negatif diubah menjadi 0.');
        notifyNegativeClamp(id);
      } else {
        setFormulaResolverState('', '');
        clearNegativeClampNotice(id);
      }
      setFormulaEditorBlockState(false, '');
      return;
    }

    clearNegativeClampNotice(id);
    setFormulaEditorPreviewState('error', {
      error: validation.message || 'Formula tidak valid.',
    });
    if (validation.canResolve && validation.invalidToken) {
      const resolverMsg = 'Parameter pada formula tidak ditemukan. Pilih parameter pengganti dari palette.';
      setFormulaResolverState(validation.invalidToken, resolverMsg);
      setFormulaEditorBlockState(true, resolverMsg);
    } else {
      setFormulaResolverState('', validation.message || '');
      setFormulaEditorBlockState(true, validation.message || 'Formula tidak valid.');
    }
  }

  function getFormulaDraftEntry(id) {
    const numericId = Number(id);
    if (!Number.isFinite(numericId)) return null;
    const draft = formulaDraftById[numericId];
    if (!draft || typeof draft !== 'object') return null;
    return {
      raw: String(draft.raw || ''),
      fx: !!draft.fx,
      updated_at: String(draft.updated_at || '').trim() || null,
    };
  }

  function setFormulaDraftEntry(id, raw, fx, options = {}) {
    const numericId = Number(id);
    if (!Number.isFinite(numericId)) return;
    formulaDraftById[numericId] = {
      raw: String(raw || ''),
      fx: !!fx,
      updated_at: new Date().toISOString(),
    };
    const debounce = !!options.debounce;
    const delay = Math.max(120, Number(options.delay || 360));
    if (!debounce) {
      if (formulaDraftPersistTimer) {
        clearTimeout(formulaDraftPersistTimer);
        formulaDraftPersistTimer = null;
      }
      saveFormulaDrafts(formulaDraftById);
      return;
    }
    if (formulaDraftPersistTimer) clearTimeout(formulaDraftPersistTimer);
    formulaDraftPersistTimer = setTimeout(() => {
      saveFormulaDrafts(formulaDraftById);
      formulaDraftPersistTimer = null;
    }, delay);
  }

  function clearFormulaDraftEntry(id) {
    const numericId = Number(id);
    if (!Number.isFinite(numericId)) return;
    if (!Object.prototype.hasOwnProperty.call(formulaDraftById, numericId)) return;
    delete formulaDraftById[numericId];
    if (formulaDraftPersistTimer) {
      clearTimeout(formulaDraftPersistTimer);
      formulaDraftPersistTimer = null;
    }
    saveFormulaDrafts(formulaDraftById);
  }

  function openFormulaEditorForRow(tr) {
    if (!tr) return;
    const id = parseInt(tr.dataset.pekerjaanId, 10);
    if (!Number.isFinite(id)) return;
    const input = tr.querySelector('.qty-input');
    const preview = tr.querySelector('.fx-preview');
    if (!input || !formulaEditorInputEl) return;

    const modal = ensureFormulaEditorModal();
    if (!modal) return;

    formulaEditorContext = { contextType: 'volume', id, tr, input, preview };
    formulaEditorOpenComputedLabel = '';
    setFormulaEditorComputedNameMode({ visible: false });
    tr.classList.remove('is-editing-formula');
    updateInlineFormulaVisibility(tr);
    const rowRawFromInput = FORMULA_LABEL_ONLY_UI_ENABLED
      ? getInputFormulaRaw(input, rawInputById[id] || input.value || '')
      : String(input.value || '');
    const rowRaw = normalizeFormulaLeadingEquals(
      String(rowRawFromInput || rawInputById[id] || ''),
      { forceFormula: String(rowRawFromInput || '').trim().startsWith('=') || !!fxModeById[id] }
    );
    const rowIsFx = isFormulaMode(id, rowRaw);
    const draft = getFormulaDraftEntry(id);
    const rowTouchedMs = getRawInputTouchedMs(id);
    const draftUpdatedMs = parseIsoMs(draft?.updated_at || '');
    const shouldUseDraft = !!(
      draft
      && draft.raw.trim()
      && draft.raw !== rowRaw
      && draftUpdatedMs >= rowTouchedMs
    );
    const raw = shouldUseDraft ? String(draft.raw || '') : rowRaw;
    const rawIsFx = String(raw || '').trim().startsWith('=') || !!(shouldUseDraft ? draft.fx : rowIsFx);
    if (FORMULA_LABEL_ONLY_UI_ENABLED && rawIsFx) {
      setInputFormulaRaw(formulaEditorInputEl, raw, { forceFormula: true });
    } else {
      formulaInputMaskState.delete(formulaEditorInputEl);
      formulaEditorInputEl.value = raw;
    }
    renderFormulaEditorInvalidOverlay([]);
    syncFormulaEditorHighlightScroll();
    if (shouldUseDraft) {
      TOAST.info(`Draft formula baris #${id} dipulihkan.`);
    }

    if (formulaEditorMetaEl) {
      const uraian = getRowUraianText(tr);
      formulaEditorMetaEl.textContent = uraian
        ? `Pekerjaan #${id} - ${uraian}`
        : `Pekerjaan #${id}`;
    }

    updateFormulaEditorPreview();
    hideSuggest(formulaEditorInputEl);
    hideSuggest(input);
    setFormulaEditorViewMode('raw');
    // Sprint 3.1: snapshot raw value for dirty check on close
    formulaEditorOpenRaw = getFormulaEditorRawValue(raw);
    setFormulaEditorBackdropState(false);
    formulaEditorCloseBypassed = false;
    modal.show();
    setTimeout(() => {
      setFormulaEditorViewMode('raw', { focus: true });
      syncFormulaEditorHighlightScroll();
    }, 80);
  }

  // --- Computed param scope helper (excludes self to prevent circular reference) ---
  function buildComputedParamScope(excludeCode) {
    const scopeLabels = { ...varLabels };
    const scopeValues = { ...variables };
    Object.keys(computedParams || {}).forEach((c) => {
      if (c === excludeCode) return;
      scopeLabels[c] = computedParams[c]?.label || c;
      scopeValues[c] = computedValues[c] ?? 0;
    });
    return { scopeLabels, scopeValues };
  }

  // --- Open formula editor modal for computed parameter expression ---
  // contextType: 'computed' (edit existing) or 'computed-new' (create new)
  function openFormulaEditorForComputed(code, options = {}) {
    const isNew = options.isNew === true;
    if (!isNew && (!code || !computedParams[code])) return;

    const def = isNew ? {} : (computedParams[code] || {});
    const expression = String(options.expression || def.expression || '');
    const label = String(options.label || def.label || code || 'Baru');
    const allowNameEdit = !isNew && options.enableNameEdit === true;

    const modal = ensureFormulaEditorModal();
    if (!modal || !formulaEditorInputEl) return;

    formulaEditorContext = isNew
      ? { contextType: 'computed-new', code: '', label, onCreated: options.onCreated || null, allowNameEdit: false }
      : { contextType: 'computed', code, originalExpression: expression, label, allowNameEdit };
    formulaEditorOpenComputedLabel = allowNameEdit ? normalizeComputedLabelInput(label, code) : '';
    setFormulaEditorComputedNameMode({
      visible: allowNameEdit,
      label,
      fallback: code,
    });

    const raw = expression.trim() ? (expression.trim().startsWith('=') ? expression : `=${expression}`) : '';
    if (FORMULA_LABEL_ONLY_UI_ENABLED && raw) {
      setInputFormulaRaw(formulaEditorInputEl, raw, { forceFormula: true });
    } else {
      formulaInputMaskState.delete(formulaEditorInputEl);
      formulaEditorInputEl.value = raw;
    }

    renderFormulaEditorInvalidOverlay([]);
    syncFormulaEditorHighlightScroll();

    if (formulaEditorMetaEl) {
      formulaEditorMetaEl.textContent = isNew
        ? `Formula Turunan Baru: ${label}`
        : `Formula Turunan: ${label}`;
    }

    updateFormulaEditorPreview();
    hideSuggest(formulaEditorInputEl);
    setFormulaEditorViewMode('raw');
    formulaEditorOpenRaw = getFormulaEditorRawValue(raw);
    setFormulaEditorBackdropState(false);
    formulaEditorCloseBypassed = false;
    modal.show();
    setTimeout(() => {
      setFormulaEditorViewMode('raw', { focus: true });
      syncFormulaEditorHighlightScroll();
    }, 80);
  }

  function applyFormulaEditorValueComputed() {
    if (!formulaEditorContext || !formulaEditorInputEl) return;
    if (formulaEditorPreviewDebounceTimer) {
      clearTimeout(formulaEditorPreviewDebounceTimer);
      formulaEditorPreviewDebounceTimer = null;
      updateFormulaEditorPreview();
    }
    const isNew = formulaEditorContext.contextType === 'computed-new';
    const code = formulaEditorContext.code || '';
    const allowNameEdit = formulaEditorContext.contextType === 'computed' && !!formulaEditorContext.allowNameEdit;
    let raw = FORMULA_LABEL_ONLY_UI_ENABLED
      ? getInputFormulaRaw(formulaEditorInputEl, formulaEditorInputEl.value || '')
      : String(formulaEditorInputEl.value || '');
    raw = normalizeFormulaLeadingEquals(raw, { forceFormula: true });
    const trimmed = raw.trim();
    const exprBody = trimmed.startsWith('=') ? trimmed.slice(1).trim() : trimmed;

    if (!exprBody) {
      setFormulaEditorPreviewState('error', { error: 'Expression tidak boleh kosong.' });
      setFormulaEditorViewMode('raw', { focus: true, caret: 'preserve' });
      return;
    }

    if (formulaEditorHasBlockingError) {
      setFormulaEditorViewMode('raw', { focus: true, caret: 'preserve' });
      return;
    }

    const scope = buildComputedParamScope(code);
    const validation = validateFormulaExpression(trimmed, {
      scopeValues: scope.scopeValues,
      scopeLabels: scope.scopeLabels,
    });
    if (!validation.ok) {
      setFormulaEditorPreviewState('error', {
        error: validation.message || 'Formula tidak valid.',
      });
      if (validation.canResolve && validation.invalidToken) {
        setFormulaResolverState(validation.invalidToken, 'Parameter pada formula tidak ditemukan. Pilih parameter pengganti dari palette.');
      } else {
        setFormulaResolverState('', validation.message || '');
      }
      setFormulaEditorViewMode('raw', { focus: true, caret: 'preserve' });
      return;
    }

    let nextLabel = normalizeComputedLabelInput(
      computedParams[code]?.label || formulaEditorContext.label || code,
      code,
    );
    if (allowNameEdit) {
      nextLabel = getFormulaEditorComputedLabelValue(nextLabel);
      if (!nextLabel) {
        setFormulaEditorPreviewState('error', { error: 'Nama formula parameter tidak boleh kosong.' });
        if (formulaEditorComputedNameEl) {
          formulaEditorComputedNameEl.classList.add('is-invalid');
          formulaEditorComputedNameEl.focus();
          setTimeout(() => formulaEditorComputedNameEl.classList.remove('is-invalid'), 1200);
        }
        return;
      }
    }

    if (isNew) {
      // Call onCreated callback with the validated expression
      if (typeof formulaEditorContext.onCreated === 'function') {
        formulaEditorContext.onCreated(exprBody);
      }
    } else {
      const nextDefs = { ...computedParams };
      nextDefs[code] = {
        ...nextDefs[code],
        expression: exprBody,
        ...(allowNameEdit ? { label: nextLabel } : {}),
      };
      computedParams = nextDefs;
      saveComputedParams();
    }

    hideSuggest(formulaEditorInputEl);
    formulaEditorOpenRaw = raw;
    formulaEditorOpenComputedLabel = allowNameEdit ? nextLabel : '';
    setFormulaEditorBackdropState(false);
    const modal = ensureFormulaEditorModal();
    modal && modal.hide();
  }

  function applyFormulaEditorValue() {
    if (!formulaEditorContext || !formulaEditorInputEl) return;
    if (formulaEditorContext.contextType === 'computed' || formulaEditorContext.contextType === 'computed-new') {
      return applyFormulaEditorValueComputed();
    }
    if (formulaEditorPreviewDebounceTimer) {
      clearTimeout(formulaEditorPreviewDebounceTimer);
      formulaEditorPreviewDebounceTimer = null;
      updateFormulaEditorPreview();
    }
    if (formulaDraftPersistTimer) {
      clearTimeout(formulaDraftPersistTimer);
      formulaDraftPersistTimer = null;
      saveFormulaDrafts(formulaDraftById);
    }
    const { id, tr, input, preview } = formulaEditorContext;
    let raw = FORMULA_LABEL_ONLY_UI_ENABLED
      ? getInputFormulaRaw(formulaEditorInputEl, rawInputById[id] || formulaEditorInputEl.value || '')
      : String(formulaEditorInputEl.value || '');
    raw = normalizeFormulaLeadingEquals(raw, {
      forceFormula: String(raw || '').trim().startsWith('=') || !!fxModeById[id],
    });
    const trimmed = raw.trim();
    const isFormulaInput = !!fxModeById[id] || trimmed.startsWith('=');
    const prevRaw = String(rawInputById[id] || input.value || '');
    const prevFx = !!fxModeById[id];
    let nextFx = prevFx;
    if (!trimmed) nextFx = false;
    else if (trimmed.startsWith('=')) nextFx = true;

    if (formulaEditorHasBlockingError) {
      setFormulaEditorViewMode('raw', { focus: true, caret: 'preserve' });
      return;
    }

    if (isFormulaInput) {
      const validation = validateFormulaExpression(trimmed, {
        scopeValues: getFormulaScopeValues(),
        scopeLabels: getFormulaScopeLabels(),
      });
      if (!validation.ok) {
        setFormulaEditorPreviewState('error', {
          error: validation.message || 'Formula tidak valid.',
        });
        if (validation.canResolve && validation.invalidToken) {
          setFormulaResolverState(validation.invalidToken, 'Parameter pada formula tidak ditemukan. Pilih parameter pengganti dari palette.');
        } else {
          setFormulaResolverState('', validation.message || '');
        }
        setFormulaEditorViewMode('raw', { focus: true, caret: 'preserve' });
        return;
      }
    } else if (!isFormulaInput && trimmed) {
      const canonical = canonFromUIQty(trimmed);
      if (canonical === '') {
        const hasAlphabet = /[A-Za-z]/.test(trimmed);
        const msg = hasAlphabet && !trimmed.startsWith('=')
          ? 'Input tidak valid. Sepertinya ini formula, awali dengan "=" lalu pilih parameter/operasi dari autosuggestion.'
          : 'Input tidak valid. Masukkan angka atau gunakan formula dari autosuggestion.';
        setFormulaEditorPreviewState('error', { error: msg });
        setFormulaResolverState('', msg);
        setFormulaEditorViewMode('raw', { focus: true, caret: 'preserve' });
        return;
      }
    }

    if (!formulaUndoInProgress && (prevRaw !== raw || prevFx !== nextFx)) {
      pushFormulaUndoSnapshot(id, prevRaw, prevFx);
    }

    formulaInputMaskState.delete(input);
    input.value = raw;
    rawInputById[id] = raw;
    markRawInputTouched(id);

    if (!trimmed) {
      setFxState(id, false);
    } else if (trimmed.startsWith('=')) {
      setFxState(id, true);
    } else {
      setFxState(id, false);
    }

    handleInputChange(id, input, preview, false);
    clearFormulaDraftEntry(id);
    hideSuggest(formulaEditorInputEl);
    hideSuggest(input);
    tr?.classList.remove('is-editing-formula');
    updateInlineFormulaVisibility(tr);
    updateFormulaUndoButtonState();

    const modal = ensureFormulaEditorModal();
    formulaEditorOpenRaw = raw;
    setFormulaEditorBackdropState(false);
    modal && modal.hide();
    if (input && !input.classList.contains('vp-input-hidden')) input.focus();
  }

  (function installFormulaEditorEvents() {
    if (!formulaEditorModalEl) return;

    if (formulaEditorInputEl && !formulaEditorInputEl.dataset.boundEditor) {
      formulaEditorInputEl.addEventListener('input', () => {
        if (FORMULA_LABEL_ONLY_UI_ENABLED && formulaEditorContext) {
          syncMaskedInputFromDisplayEdit(formulaEditorInputEl);
        }
        if (formulaEditorContext && formulaEditorContext.contextType === 'volume') {
          const id = Number(formulaEditorContext.id);
          const rawDraftRaw = FORMULA_LABEL_ONLY_UI_ENABLED
            ? getInputFormulaRaw(formulaEditorInputEl, '')
            : String(formulaEditorInputEl.value || '');
          const rawDraft = normalizeFormulaLeadingEquals(rawDraftRaw, {
            forceFormula: String(rawDraftRaw || '').trim().startsWith('=') || !!fxModeById[id],
          });
          const draftIsFx = String(rawDraft || '').trim().startsWith('=') || !!fxModeById[id];
          setFormulaDraftEntry(id, rawDraft, draftIsFx, { debounce: true, delay: 380 });
        }
        syncFormulaEditorDirtyState();
        if (formulaEditorPreviewDebounceTimer) clearTimeout(formulaEditorPreviewDebounceTimer);
        formulaEditorPreviewDebounceTimer = setTimeout(() => {
          updateFormulaEditorPreview();
          if (formulaEditorContext) {
            if (formulaEditorContext.contextType === 'computed' || formulaEditorContext.contextType === 'computed-new') {
              updateSuggestions(formulaEditorInputEl, formulaEditorContext.code || 'cparam-new', {
                isComputed: true,
                excludeCode: formulaEditorContext.code || '',
              });
            } else {
              const id = Number(formulaEditorContext.id);
              if (Number.isFinite(id)) updateSuggestions(formulaEditorInputEl, id);
            }
          }
          syncFormulaEditorHighlightScroll();
          formulaEditorPreviewDebounceTimer = null;
        }, 80);
      });
      formulaEditorInputEl.addEventListener('paste', (ev) => {
        if (!FORMULA_LABEL_ONLY_UI_ENABLED || !formulaEditorContext) return;
        const clipText = String(ev.clipboardData?.getData('text/plain') || '');
        if (!clipText.trim()) return;
        ev.preventDefault();
        const isComputedCtx = formulaEditorContext.contextType === 'computed' || formulaEditorContext.contextType === 'computed-new';
        const scopeLabels = isComputedCtx
          ? buildComputedParamScope(formulaEditorContext.code || '').scopeLabels
          : getFormulaScopeLabels();
        const currentRaw = getInputFormulaRaw(formulaEditorInputEl, formulaEditorInputEl.value || '');
        const inserted = insertPastedFormulaText(formulaEditorInputEl, clipText, {
          currentRaw,
          scopeLabels,
          forceFormula: true,
        });
        if (!inserted) return;
        formulaEditorInputEl.dispatchEvent(new Event('input', { bubbles: true }));
      });
      formulaEditorInputEl.addEventListener('blur', () => {
        if (formulaEditorPreviewDebounceTimer) {
          clearTimeout(formulaEditorPreviewDebounceTimer);
          formulaEditorPreviewDebounceTimer = null;
          updateFormulaEditorPreview();
        }
        if (formulaDraftPersistTimer) {
          clearTimeout(formulaDraftPersistTimer);
          formulaDraftPersistTimer = null;
          saveFormulaDrafts(formulaDraftById);
        }
        setTimeout(() => hideSuggest(formulaEditorInputEl), 200);
      });
      formulaEditorInputEl.addEventListener('scroll', syncFormulaEditorHighlightScroll);
      formulaEditorInputEl.addEventListener('keydown', (ev) => {
        if (!formulaEditorContext) return;
        const { id } = formulaEditorContext;
        const state = suggestState.get(formulaEditorInputEl);
        const suggestVisible = state && state.box && state.box.style.display !== 'none' && state.items.length > 0;

        if ((ev.ctrlKey || ev.metaKey) && ev.code === 'Space') {
          ev.preventDefault();
          if (FORMULA_LABEL_ONLY_UI_ENABLED) {
            const curRaw = getInputFormulaRaw(formulaEditorInputEl, '');
            if (!curRaw.trim().startsWith('=')) {
              setInputFormulaRaw(formulaEditorInputEl, `=${curRaw}`, { forceFormula: true });
            }
          } else {
            const cur = String(formulaEditorInputEl.value || '');
            if (!cur.trim().startsWith('=')) formulaEditorInputEl.value = `=${cur}`;
          }
          updateFormulaEditorPreview();
          if (formulaEditorContext.contextType === 'computed' || formulaEditorContext.contextType === 'computed-new') {
            updateSuggestions(formulaEditorInputEl, formulaEditorContext.code || 'cparam-new', {
              forceOpen: true, isComputed: true, excludeCode: formulaEditorContext.code || '',
            });
          } else {
            updateSuggestions(formulaEditorInputEl, id, { forceOpen: true });
          }
          return;
        }

        if (suggestVisible) {
          if (ev.key === 'ArrowDown') { ev.preventDefault(); moveActive(formulaEditorInputEl, +1); return; }
          if (ev.key === 'ArrowUp') { ev.preventDefault(); moveActive(formulaEditorInputEl, -1); return; }
          if (ev.key === 'Enter' || ev.key === 'Tab') {
            const ok = applyActiveSuggestion(formulaEditorInputEl, {
              id,
              onAfterInsert: () => {
                updateFormulaEditorPreview();
              }
            });
            if (ok) { ev.preventDefault(); return; }
          }
          if (ev.key === 'Escape') { ev.preventDefault(); hideSuggest(formulaEditorInputEl); return; }
        }

        if ((ev.ctrlKey || ev.metaKey) && ev.key === 'Enter') {
          ev.preventDefault();
          applyFormulaEditorValue();
        }

        if ((ev.ctrlKey || ev.metaKey) && ev.shiftKey && ev.key.toLowerCase() === 'z') {
          if (!formulaEditorUndoBtn || formulaEditorUndoBtn.disabled) return;
          ev.preventDefault();
          formulaEditorUndoBtn.click();
        }
      });
      formulaEditorInputEl.dataset.boundEditor = '1';
    }

    if (formulaEditorComputedNameEl && !formulaEditorComputedNameEl.dataset.boundEditor) {
      formulaEditorComputedNameEl.addEventListener('input', () => {
        formulaEditorComputedNameEl.classList.remove('is-invalid');
        syncFormulaEditorDirtyState();
      });
      formulaEditorComputedNameEl.addEventListener('keydown', (ev) => {
        if ((ev.ctrlKey || ev.metaKey) && ev.key === 'Enter') {
          ev.preventDefault();
          applyFormulaEditorValue();
        }
      });
      formulaEditorComputedNameEl.dataset.boundEditor = '1';
    }

    if (formulaEditorViewToggleBtn && !formulaEditorViewToggleBtn.dataset.boundEditor) {
      formulaEditorViewToggleBtn.addEventListener('click', () => {
        const nextMode = formulaEditorViewMode === 'raw' ? 'chip' : 'raw';
        setFormulaEditorViewMode(nextMode, { focus: nextMode === 'raw' });
      });
      formulaEditorViewToggleBtn.dataset.boundEditor = '1';
    }

    if (formulaEditorChipPreviewEl && !formulaEditorChipPreviewEl.dataset.boundEditor) {
      formulaEditorChipPreviewEl.addEventListener('click', () => {
        if (!formulaEditorContext) return;
        setFormulaEditorViewMode('raw', { focus: true });
      });
      formulaEditorChipPreviewEl.addEventListener('keydown', (ev) => {
        if (!formulaEditorContext) return;
        if (ev.key === 'Enter' || ev.key === ' ') {
          ev.preventDefault();
          setFormulaEditorViewMode('raw', { focus: true });
        }
      });
      formulaEditorChipPreviewEl.dataset.boundEditor = '1';
    }

    if (formulaEditorApplyBtn && !formulaEditorApplyBtn.dataset.boundEditor) {
      formulaEditorApplyBtn.addEventListener('click', applyFormulaEditorValue);
      formulaEditorApplyBtn.dataset.boundEditor = '1';
    }

    if (formulaEditorUndoBtn && !formulaEditorUndoBtn.dataset.boundEditor) {
      formulaEditorUndoBtn.addEventListener('click', () => {
        if (!formulaEditorContext) return;
        const id = Number(formulaEditorContext.id);
        if (!Number.isFinite(id)) return;
        const snap = formulaUndoById.get(id);
        if (!snap) return;
        formulaUndoInProgress = true;
        try {
          const { tr, input, preview } = formulaEditorContext;
          const raw = String(snap.raw || '');
          rawInputById[id] = raw;
          input.value = raw;
          setFxState(id, !!snap.fx);
          handleInputChange(id, input, preview, false);
          persistRowFormula(id);
          formulaUndoById.delete(id);
          if (FORMULA_LABEL_ONLY_UI_ENABLED && isFormulaMode(id, raw)) {
            setInputFormulaRaw(formulaEditorInputEl, raw, { forceFormula: true });
          } else {
            formulaInputMaskState.delete(formulaEditorInputEl);
            formulaEditorInputEl.value = raw;
          }
          clearFormulaDraftEntry(id);
          updateFormulaEditorPreview();
          updateSuggestions(formulaEditorInputEl, id);
          setFormulaEditorViewMode('raw', { focus: true });
        } finally {
          formulaUndoInProgress = false;
        }
      });
      formulaEditorUndoBtn.dataset.boundEditor = '1';
    }

    formulaPreviewModeButtons.forEach((btn) => {
      if (btn.dataset.boundEditor) return;
      btn.addEventListener('click', () => {
        setFormulaPreviewMode(btn.dataset.previewMode || 'label');
      });
      btn.dataset.boundEditor = '1';
    });

    if (formulaEditorShowValuesEl && !formulaEditorShowValuesEl.dataset.boundEditor) {
      formulaEditorShowValuesEl.addEventListener('change', () => {
        setFormulaShowInlineValues(!!formulaEditorShowValuesEl.checked);
      });
      formulaEditorShowValuesEl.dataset.boundEditor = '1';
    }

    if (formulaEditorOpenPaletteBtn && !formulaEditorOpenPaletteBtn.dataset.boundEditor) {
      formulaEditorOpenPaletteBtn.addEventListener('click', () => openParamPalette());
      formulaEditorOpenPaletteBtn.dataset.boundEditor = '1';
    }

    if (formulaEditorResolveBtn && !formulaEditorResolveBtn.dataset.boundEditor) {
      formulaEditorResolveBtn.addEventListener('click', () => {
        if (!formulaResolverToken) return;
        openParamPalette({ query: formulaResolverToken });
      });
      formulaEditorResolveBtn.dataset.boundEditor = '1';
    }

    // Sprint 3.1: intercept modal close if unsaved changes exist
    formulaEditorModalEl.addEventListener('hide.bs.modal', (e) => {
      if (formulaEditorCloseBypassed) {
        formulaEditorCloseBypassed = false;
        setFormulaEditorBackdropState(false);
        return; // allow close - user confirmed
      }
      if (!formulaEditorContext || !formulaEditorInputEl) return;
      const isDirty = getFormulaEditorDirtyState();
      setFormulaEditorBackdropState(isDirty);
      if (isDirty) {
        e.preventDefault();
        confirmModal('Perubahan belum diterapkan. Tutup tanpa menyimpan?', {
          title: 'Konfirmasi Tutup',
          confirmText: 'Tutup',
          cancelText: 'Kembali',
        }).then((confirmed) => {
          if (confirmed) {
            formulaEditorCloseBypassed = true;
            const modal = bootstrap.Modal.getInstance(formulaEditorModalEl);
            if (modal) modal.hide();
          }
        });
      }
    });

    formulaEditorModalEl.addEventListener('hidden.bs.modal', () => {
      setFormulaEditorBackdropState(false);
      hideSuggest(formulaEditorInputEl);
      formulaInputMaskState.delete(formulaEditorInputEl);
      renderFormulaEditorInvalidOverlay([]);
      formulaEditorInvalidTokens = [];
      setFormulaResolverState('', '');
      setFormulaEditorBlockState(false, '');
      setFormulaEditorViewMode('raw');
      if (formulaEditorContext?.tr) {
        formulaEditorContext.tr.classList.remove('is-editing-formula');
        updateInlineFormulaVisibility(formulaEditorContext.tr);
      }
      formulaEditorContext = null;
      formulaEditorOpenRaw = '';
      formulaEditorOpenComputedLabel = '';
      setFormulaEditorComputedNameMode({ visible: false });
      updateFormulaUndoButtonState();
      cleanupOrphanModalBackdrops();
    });

    if (paramPaletteModalEl && !paramPaletteModalEl.dataset.boundPaletteCleanup) {
      paramPaletteModalEl.addEventListener('hidden.bs.modal', () => {
        cleanupOrphanModalBackdrops();
        if (formulaEditorContext && formulaEditorInputEl) {
          setTimeout(() => {
            try { formulaEditorInputEl.focus(); } catch { }
          }, 0);
        }
      });
      paramPaletteModalEl.dataset.boundPaletteCleanup = '1';
    }

    if (paramPaletteSearchEl && !paramPaletteSearchEl.dataset.boundEditor) {
      paramPaletteSearchEl.addEventListener('input', () => {
        renderParamPaletteList(paramPaletteSearchEl.value || '');
      });
      paramPaletteSearchEl.dataset.boundEditor = '1';
    }

    if (paramPaletteListEl && !paramPaletteListEl.dataset.boundEditor) {
      paramPaletteListEl.addEventListener('click', (ev) => {
        const btn = ev.target.closest('[data-code]');
        if (!btn || !formulaEditorContext || !formulaEditorInputEl) return;
        const code = normalizeOpaqueCode(btn.getAttribute('data-code') || '');
        if (!code) return;
        const palette = ensureParamPaletteModal();
        const didResolveUnknown = applyFormulaResolverReplacement(code);
        if (!didResolveUnknown) {
          applySuggestion(formulaEditorInputEl, code, {
            id: formulaEditorContext.id,
            onAfterInsert: () => {
              updateFormulaEditorPreview();
              updateSuggestions(formulaEditorInputEl, formulaEditorContext.id);
            },
          });
        }
        palette && palette.hide();
        if (!didResolveUnknown) {
          formulaEditorInputEl.focus();
        }
      });
      paramPaletteListEl.dataset.boundEditor = '1';
    }
  })();

  function bindRow(tr) {
    if (tr.dataset.bound === '1') return;
    tr.dataset.bound = '1';

    const id = parseInt(tr.dataset.pekerjaanId, 10);
    const input = tr.querySelector('.qty-input');
    const editorBtn = tr.querySelector('.fx-editor-open');
    const preview = tr.querySelector('.fx-preview');
    if (preview) {
      ensureDualPreviewSlots(preview);
      setDualPreviewState(preview, 'empty', { forceVisible: false });
    }

    // Jika localStorage punya state awal, apply ringan (server akan override saat prefill)
    const initMap = loadFormulas();
    const f = initMap[id] || {};
    if (typeof f.fx === 'boolean') {
      setFxState(id, !!f.fx);
    } else { fxModeById[id] = false; }
    if (typeof f.raw === 'string' && f.raw.trim() && input && !input.value) {
      rawInputById[id] = f.raw;
      input.value = f.raw;
    }
    updateInlineFormulaVisibility(tr);

    // Mark initial empty/zero state
    if (input) {
      const raw0 = String(input.value || '').trim();
      tr.classList.toggle('vp-row-empty', !raw0);
      const c0 = canonFromUIQty(raw0);
      if (c0 !== '') tr.classList.toggle('vp-row-zero', Number(c0) === 0);
      tr.classList.remove('vp-row-invalid');
      setQtyInputInteractionMode(input, isFormulaMode(id, raw0));
    }

    editorBtn && editorBtn.addEventListener('click', () => openFormulaEditorForRow(tr));
    input && input.addEventListener('dblclick', () => openFormulaEditorForRow(tr));

    let debTimer = null;
    input && input.addEventListener('input', () => {
      lastQtyInputAt = Date.now();
      clearTimeout(debTimer);
      if (FORMULA_LABEL_ONLY_UI_ENABLED && isFormulaMode(id, rawInputById[id] || input.value || '')) {
        syncMaskedInputFromDisplayEdit(input);
      }
      const liveRawValue = (FORMULA_LABEL_ONLY_UI_ENABLED && isFormulaMode(id, rawInputById[id] || input.value || ''))
        ? getInputFormulaRaw(input, rawInputById[id] || input.value || '')
        : String(input.value || '');
      const liveRaw = normalizeFormulaLeadingEquals(liveRawValue, {
        forceFormula: isFormulaMode(id, rawInputById[id] || input.value || '') || String(liveRawValue || '').trim().startsWith('='),
      });
      rawInputById[id] = liveRaw;
      markRawInputTouched(id);
      pendingInputIds.add(id); // FIX: edit belum di-commit (menunggu debounce 120ms)

      // Auto-enable FX jika user mulai mengetik "="
      const valNow = String(input.value || '').trim();
      if (valNow.startsWith('=') && !fxModeById[id]) {
        setFxState(id, true);
      }
      if (!valNow.startsWith('=') && fxModeById[id] && !FORMULA_LABEL_ONLY_UI_ENABLED) {
        setFxState(id, false);
      }

      updateSuggestions(input, id);
      debTimer = setTimeout(() => handleInputChange(id, input, preview, false), 120);
    });
    input && input.addEventListener('paste', (ev) => {
      if (!FORMULA_LABEL_ONLY_UI_ENABLED) return;
      const clipText = String(ev.clipboardData?.getData('text/plain') || '');
      if (!clipText.trim()) return;
      const currentRaw = getInputFormulaRaw(input, rawInputById[id] || input.value || '');
      const shouldHandle = isFormulaMode(id, currentRaw) || /[A-Za-z_]/.test(clipText) || /^\s*=/.test(clipText);
      if (!shouldHandle) return;
      ev.preventDefault();
      const inserted = insertPastedFormulaText(input, clipText, {
        currentRaw,
        scopeLabels: getFormulaScopeLabels(),
        forceFormula: true,
      });
      if (!inserted) return;
      input.dispatchEvent(new Event('input', { bubbles: true }));
    });
    input && input.addEventListener('blur', () => {
      if (!isFormulaMode(id, input.value)) {
        formulaInputMaskState.delete(input);
        const normalized = normQty(input.value);
        if (normalized !== '') input.value = normalized;
        // Update row markers based on normalized numeric
        const tr2 = rows.find(r => parseInt(r.dataset.pekerjaanId, 10) === id);
        const c = canonFromUIQty(input.value);
        const isEmpty2 = !String(input.value || '').trim();
        const hasBlockingError = inputValidationErrorsById.has(Number(id));
        input.classList.toggle('vp-empty', isEmpty2);
        input.classList.toggle('is-invalid', hasBlockingError);
        if (tr2) {
          tr2.classList.toggle('vp-row-empty', isEmpty2);
          tr2.classList.toggle('vp-row-zero', (!hasBlockingError && !isEmpty2 && c !== '' && Number(c) === 0));
          tr2.classList.toggle('vp-row-invalid', hasBlockingError);
        }
      } else {
        // Formula mode: only toggle empty flag; vp-row-invalid handled in input handler
        input.classList.toggle('vp-empty', !String(input.value || '').trim());
        tr.classList.remove('is-editing-formula');
        updateInlineFormulaVisibility(tr);
      }
      setTimeout(() => hideSuggest(input), 200);
    });
    input && input.addEventListener('focus', () => {
      if (suppressFormulaInputFocusOpen) return;
      const rawNow = FORMULA_LABEL_ONLY_UI_ENABLED
        ? getInputFormulaRaw(input, rawInputById[id] || input.value || '')
        : String(input.value || '');
      updateSuggestions(input, id);
      setQtyInputInteractionMode(input, isFormulaMode(id, rawNow));
    });
    input && input.addEventListener('keydown', (ev) => {
      // Save
      if ((ev.ctrlKey || ev.metaKey) && (ev.key === 's' || ev.key === 'S')) {
        ev.preventDefault();
        if (btnSave && !btnSave.disabled) btnSave.click();
        else scheduleAutosave(300);
        return;
      }
      // Open detached editor
      if (ev.altKey && ev.key === 'Enter') {
        ev.preventDefault();
        openFormulaEditorForRow(tr);
        return;
      }
      // Toggle suggestion panel
      if ((ev.ctrlKey || ev.metaKey) && ev.code === 'Space') {
        ev.preventDefault();
        if (FORMULA_LABEL_ONLY_UI_ENABLED) {
          const curRaw = getInputFormulaRaw(input, rawInputById[id] || input.value || '');
          if (!curRaw.trim().startsWith('=')) {
            setInputFormulaRaw(input, `=${curRaw}`, { forceFormula: true });
          }
        } else {
          const cur = String(input.value || '');
          if (!cur.trim().startsWith('=')) input.value = '=' + cur;
        }
        if (!fxModeById[id]) {
          fxModeById[id] = true;
        }
        input.focus();
        updateSuggestions(input, id, { forceOpen: true });
        return;
      }

      // Suggest navigation
      const state = suggestState.get(input);
      const suggestVisible = state && state.box && state.box.style.display !== 'none' && state.items.length > 0;
      if (suggestVisible) {
        if (ev.key === 'ArrowDown') { ev.preventDefault(); moveActive(input, +1); return; }
        if (ev.key === 'ArrowUp') { ev.preventDefault(); moveActive(input, -1); return; }
        if (ev.key === 'Enter' || ev.key === 'Tab') { const ok = applyActiveSuggestion(input); if (ok) { ev.preventDefault(); return; } }
        if (ev.key === 'Escape') { hideSuggest(input); return; }
      }

      // Fill-down (Excel-like)
      if ((ev.ctrlKey || ev.metaKey) && (ev.key.toLowerCase() === 'd')) {
        ev.preventDefault();
        const sourceRaw = FORMULA_LABEL_ONLY_UI_ENABLED
          ? getInputFormulaRaw(input, rawInputById[id] || input.value || '')
          : String(rawInputById[id] || input.value || '');
        const sourceFx = isFormulaMode(id, sourceRaw);
        focusNextFrom(input, +1);
        const tgt = document.activeElement;
        if (tgt && tgt.classList.contains('qty-input')) {
          if (FORMULA_LABEL_ONLY_UI_ENABLED && sourceFx) {
            setInputFormulaRaw(tgt, sourceRaw, { forceFormula: true });
          } else {
            formulaInputMaskState.delete(tgt);
            tgt.value = sourceRaw;
          }
          tgt.classList.toggle('vp-empty', !String(tgt.value || '').trim());
          const tr2 = tgt.closest('tr');
          const id2 = parseInt(tr2.dataset.pekerjaanId, 10);
          const pv2 = tr2.querySelector('.fx-preview');
          if (Number.isFinite(id2)) {
            rawInputById[id2] = sourceRaw;
            markRawInputTouched(id2);
            setFxState(id2, sourceFx);
          }
          handleInputChange(id2, tgt, pv2, false);
        }
        return;
      }

      // Enter nav
      if (ev.key === 'Enter') { ev.preventDefault(); focusNextFrom(input, ev.shiftKey ? -1 : +1); }
    });
  }

  function isFormulaMode(id, rawStr) {
    const explicitFx = !!fxModeById[id];
    const startsEq = String(rawStr || '').trim().startsWith('=');
    return explicitFx || startsEq;
  }
  function normQty(val) {
    if (val === '' || val == null) return '';
    // Gunakan parser robust agar '1.000' (id-ID ribuan) tidak dibaca 1.000 (desimal)
    const c = canonFromUIQty(val);
    if (!c) return '';
    if (N) {
      return N.formatForUI(N.enforceDp(c, STORE_PLACES)); // tampilkan dengan format lokal
    }
    let num = Number(c);
    if (!Number.isFinite(num)) return '';
    if (num < 0) num = 0;
    const rounded = roundHalfUp(num, STORE_PLACES);
    return formatIdSmart(rounded);
  }
  function buildFormulaPreview(exprOrRaw, resultNumber, scopeValues, options = {}) {
    const expr = String(exprOrRaw || '').replace(/^=/, '').trim();
    const resultText = formatIdSmart(resultNumber);
    if (!expr) return resultText;
    const mode = normalizeFormulaPreviewMode(options.mode || 'value');
    const scopeVals = scopeValues || getFormulaScopeValues();
    const translated = translateFormulaForPreview(expr, {
      mode,
      scopeValues: scopeVals,
      scopeLabels: options.scopeLabels || getFormulaScopeLabels(),
      includeInlineValues: !!options.includeInlineValues,
    });
    return `${translated} = ${resultText}`;
  }
  function buildCombinedFormulaPreviewParts(exprOrRaw, resultNumber, scopeValues, options = {}) {
    const scopeLabels = options.scopeLabels || getFormulaScopeLabels();
    const labelPreview = buildFormulaPreview(exprOrRaw, resultNumber, scopeValues, {
      mode: 'label',
      scopeLabels,
      includeInlineValues: options.includeInlineValues !== false,
    });
    const valuePreview = buildFormulaPreview(exprOrRaw, resultNumber, scopeValues, {
      mode: 'value',
      scopeLabels,
      includeInlineValues: false,
    });
    return {
      labelPreview,
      valuePreview,
    };
  }

  function getPreviewCaptionPair(previewEl) {
    const compact = String(root?.getAttribute('data-vp-qty-compact') || '0') === '1';
    const inlineCellPreview = !!previewEl?.closest('.vp-cell');
    if (compact && inlineCellPreview) {
      return { label: 'Label:', value: 'Nilai:' };
    }
    return { label: 'Preview Label:', value: 'Preview Nilai:' };
  }

  function syncPreviewCaptions(previewEl, slots = null) {
    if (!previewEl) return;
    const pair = getPreviewCaptionPair(previewEl);
    const nextSlots = slots || {
      labelCaption: previewEl.querySelector('.fx-preview-label-line .fx-preview-caption'),
      valueCaption: previewEl.querySelector('.fx-preview-value-line .fx-preview-caption'),
    };
    if (nextSlots.labelCaption) nextSlots.labelCaption.textContent = pair.label;
    if (nextSlots.valueCaption) nextSlots.valueCaption.textContent = pair.value;
  }

  function ensureDualPreviewSlots(previewEl) {
    if (!previewEl) return null;
    let labelLine = previewEl.querySelector('.fx-preview-label-line');
    let valueLine = previewEl.querySelector('.fx-preview-value-line');
    let errorLine = previewEl.querySelector('.fx-preview-error-line');
    let labelText = previewEl.querySelector('.fx-preview-label-text');
    let valueText = previewEl.querySelector('.fx-preview-value-text');
    let labelCaption = previewEl.querySelector('.fx-preview-label-line .fx-preview-caption');
    let valueCaption = previewEl.querySelector('.fx-preview-value-line .fx-preview-caption');
    if (!labelLine || !valueLine || !errorLine || !labelText || !valueText) {
      previewEl.innerHTML = `
        <div class="fx-preview-label-line">
          <span class="fx-preview-caption">Preview Label:</span>
          <span class="fx-preview-label-text">-</span>
        </div>
        <div class="fx-preview-value-line">
          <span class="fx-preview-caption">Preview Nilai:</span>
          <span class="fx-preview-value-text">-</span>
        </div>
        <div class="fx-preview-error-line d-none"></div>
      `;
      labelLine = previewEl.querySelector('.fx-preview-label-line');
      valueLine = previewEl.querySelector('.fx-preview-value-line');
      errorLine = previewEl.querySelector('.fx-preview-error-line');
      labelText = previewEl.querySelector('.fx-preview-label-text');
      valueText = previewEl.querySelector('.fx-preview-value-text');
      labelCaption = previewEl.querySelector('.fx-preview-label-line .fx-preview-caption');
      valueCaption = previewEl.querySelector('.fx-preview-value-line .fx-preview-caption');
    }
    const slots = { labelLine, valueLine, errorLine, labelText, valueText, labelCaption, valueCaption };
    syncPreviewCaptions(previewEl, slots);
    return slots;
  }
  function setDualPreviewState(previewEl, state = 'empty', options = {}) {
    if (!previewEl) return;
    const slots = ensureDualPreviewSlots(previewEl);
    if (!slots) return;
    syncPreviewCaptions(previewEl, slots);
    const label = options.label ?? '-';
    const value = options.value ?? '-';
    const error = String(options.error || '').trim();
    const nextState = String(state || 'empty');

    slots.labelText.textContent = String(label || '-');
    slots.valueText.textContent = String(value || '-');
    slots.labelText.setAttribute('title', String(label || '-'));
    slots.valueText.setAttribute('title', String(value || '-'));
    slots.labelLine.classList.remove('d-none');
    slots.valueLine.classList.remove('d-none');
    slots.errorLine.textContent = '';
    slots.errorLine.removeAttribute('title');
    slots.errorLine.classList.add('d-none');

    previewEl.classList.remove('is-success', 'is-error', 'is-muted', 'text-success', 'text-danger', 'text-muted');
    if (nextState === 'success') {
      previewEl.classList.add('is-success');
      previewEl.dataset.previewState = 'success';
    } else if (nextState === 'error') {
      previewEl.classList.add('is-error');
      previewEl.dataset.previewState = 'error';
      if (error) {
        slots.errorLine.textContent = `Error: ${error}`;
        slots.errorLine.setAttribute('title', error);
        slots.errorLine.classList.remove('d-none');
      }
    } else {
      previewEl.classList.add('is-muted');
      previewEl.dataset.previewState = 'empty';
    }

    const hasContent = nextState === 'success' || nextState === 'error';
    previewEl.dataset.previewHasContent = hasContent ? '1' : '0';
    if (options.forceVisible === true) {
      previewEl.classList.remove('d-none');
    } else if (options.forceVisible === false) {
      previewEl.classList.toggle('d-none', !hasContent);
    } else if (hasContent) {
      previewEl.classList.remove('d-none');
    }
  }
  function hasDualPreviewContent(previewEl) {
    if (!previewEl) return false;
    return String(previewEl.dataset.previewHasContent || '0') === '1';
  }
  function setRowDirtyVisual(id, isDirty) {
    const tr = rows.find(r => parseInt(r.dataset.pekerjaanId, 10) === id);
    if (!tr) return;
    // Border-only indicator (no Bootstrap background)
    if (tr.classList.contains('table-warning')) tr.classList.remove('table-warning');
    tr.classList.toggle('vp-row-edited', !!isDirty);
  }
  function refreshRowFormulaPreviews() {
    const scopeValues = getFormulaScopeValues();
    const scopeLabels = getFormulaScopeLabels();
    rows.forEach((tr) => {
      const id = parseInt(tr.dataset.pekerjaanId, 10);
      if (!Number.isFinite(id)) return;
      const input = tr.querySelector('.qty-input');
      const preview = tr.querySelector('.fx-preview');
      if (!input || !preview) return;
      const raw = String(rawInputById[id] || input.value || '').trim();
      if (!isFormulaMode(id, raw) || !raw) return;
      const expr = raw.startsWith('=') ? raw : `=${raw}`;
      const validation = validateFormulaExpression(expr, { scopeValues, scopeLabels });
      if (!validation.ok) return;
      const previewParts = buildCombinedFormulaPreviewParts(validation.expr, validation.value, scopeValues, {
        scopeLabels,
        includeInlineValues: formulaShowInlineValues,
      });
      setDualPreviewState(preview, 'success', {
        label: previewParts.labelPreview,
        value: previewParts.valuePreview,
        forceVisible: true,
      });
    });
  }
  function markRowSaved(tr) {
    if (!tr) return;
    tr.classList.remove('vp-row-edited');
    tr.classList.add('vp-row-saved');
    setTimeout(() => tr.classList.remove('vp-row-saved'), 1800);
  }
  function handleInputChange(id, inputEl, previewEl) {
    pendingInputIds.delete(Number(id)); // FIX: edit ini sedang di-commit sekarang
    const formulaActive = isFormulaMode(id, rawInputById[id] || inputEl.value || '');
    const rawValue = (FORMULA_LABEL_ONLY_UI_ENABLED && formulaActive)
      ? getInputFormulaRaw(inputEl, rawInputById[id] || inputEl.value || '')
      : String(inputEl.value || '');
    const raw = normalizeFormulaLeadingEquals(rawValue, {
      forceFormula: formulaActive || String(rawValue || '').trim().startsWith('='),
    });
    rawInputById[id] = raw;
    markRawInputTouched(id);
    // flag kosong
    const isEmpty = raw.trim() === '';
    inputEl.classList.toggle('vp-empty', isEmpty);
    const tr = rows.find(r => parseInt(r.dataset.pekerjaanId, 10) === id);
    if (tr) tr.classList.toggle('vp-row-empty', isEmpty);

    inputEl.classList.remove('is-invalid', 'is-valid');
    inputEl.removeAttribute('title');
    if (previewEl) {
      setDualPreviewState(previewEl, 'empty', { forceVisible: false });
    }

    if (isFormulaMode(id, raw)) {
      const expr = raw.startsWith('=') ? raw : ('=' + raw);
      const scopeValues = getFormulaScopeValues();
      const scopeLabels = getFormulaScopeLabels();
      const validation = validateFormulaExpression(expr, { scopeValues, scopeLabels });
      if (validation.ok) {
        currentValueById[id] = validation.value;
        if (previewEl) {
          const previewParts = buildCombinedFormulaPreviewParts(validation.expr, validation.value, scopeValues, {
            scopeLabels,
            includeInlineValues: formulaShowInlineValues,
          });
          setDualPreviewState(previewEl, 'success', {
            label: previewParts.labelPreview,
            value: previewParts.valuePreview,
            forceVisible: true,
          });
        }
        inputEl.classList.add('is-valid');
        if (tr) {
          tr.classList.remove('vp-row-invalid');
          tr.classList.toggle('vp-row-zero', Number(validation.value) === 0);
        }
        if (validation.clampedNegative) notifyNegativeClamp(id);
        else clearNegativeClampNotice(id);
        setInputValidationError(id, '');
        updateDirty(id);
        persistRowFormula(id);
      } else {
        const msg = String(validation.message || 'Formula tidak valid.');
        inputEl.classList.add('is-invalid');
        inputEl.setAttribute('title', msg);
        if (previewEl) {
          setDualPreviewState(previewEl, 'error', {
            error: msg,
            forceVisible: true,
          });
        }
        if (tr) {
          tr.classList.add('vp-row-invalid');
          tr.classList.remove('vp-row-zero');
        }
        clearNegativeClampNotice(id);
        setInputValidationError(id, msg);
      }
    } else {
      formulaInputMaskState.delete(inputEl);
      // Robust parse to avoid "1.000" -> 1 error (id-ID grouping)
      const c = canonFromUIQty(raw);
      const n = c === '' ? '' : Number(c);
      const trimmedRaw = String(raw || '').trim();
      if (!trimmedRaw) {
        currentValueById[id] = 0;
        if (previewEl) setDualPreviewState(previewEl, 'empty', { forceVisible: false });
        if (tr) {
          tr.classList.remove('vp-row-invalid');
          tr.classList.remove('vp-row-zero');
        }
        clearNegativeClampNotice(id);
        setInputValidationError(id, '');
        clearFormulaStateForNumericInput(id);
      } else if (n === '') {
        const hasAlphabet = /[A-Za-z_]/.test(trimmedRaw);
        if (hasAlphabet && !trimmedRaw.startsWith('=')) {
          // Try showing suggestions instead of error — user might be typing a parameter name
          const scopeValuesHint = getFormulaScopeValues();
          const scopeLabelsHint = getFormulaScopeLabels();
          const hintItems = buildFormulaSuggestionItems(scopeValuesHint, scopeLabelsHint);
          const hintQuery = trimmedRaw.toLowerCase();
          const hasMatch = hintItems.some(it => {
            const code = String(it.name || '').toLowerCase();
            const label = String(it.label || '').toLowerCase();
            return code.includes(hintQuery) || label.includes(hintQuery) || hintQuery.includes(code);
          });
          const msg = hasMatch
            ? 'Ketik nama parameter, lalu pilih dari autosuggestion. Prefix "=" akan ditambahkan otomatis.'
            : 'Input tidak valid. Ketik nama parameter atau gunakan "=" untuk formula.';
          inputEl.classList.add('is-invalid');
          inputEl.setAttribute('title', msg);
          if (previewEl) {
            setDualPreviewState(previewEl, 'error', {
              error: msg,
              forceVisible: true,
            });
          }
          if (tr) {
            tr.classList.add('vp-row-invalid');
            tr.classList.remove('vp-row-zero');
          }
          clearNegativeClampNotice(id);
          setInputValidationError(id, msg);
          // Trigger suggestions for parameter-like text
          updateSuggestions(inputEl, id);
        } else {
          const msg = 'Input tidak valid. Hanya angka atau formula tersimpan yang diizinkan.';
          inputEl.classList.add('is-invalid');
          inputEl.setAttribute('title', msg);
          if (previewEl) {
            setDualPreviewState(previewEl, 'error', {
              error: msg,
              forceVisible: true,
            });
          }
          if (tr) {
            tr.classList.add('vp-row-invalid');
            tr.classList.remove('vp-row-zero');
          }
          clearNegativeClampNotice(id);
          setInputValidationError(id, msg);
        }
      } else {
        const clamped = n < 0 ? 0 : n;
        const rounded = roundHalfUp(clamped, STORE_PLACES);
        currentValueById[id] = rounded;
        inputEl.classList.add('is-valid');
        if (tr) {
          tr.classList.remove('vp-row-invalid');
          tr.classList.toggle('vp-row-zero', Number(rounded) === 0);
        }
        if (n < 0) notifyNegativeClamp(id);
        else clearNegativeClampNotice(id);
        if (previewEl) setDualPreviewState(previewEl, 'empty', { forceVisible: false });
        setInputValidationError(id, '');
        clearFormulaStateForNumericInput(id);
      }
      updateDirty(id);
    }

    setBtnSaveEnabled();
    scheduleAutosave();
    refreshUsageBadges();
    updateInlineFormulaVisibility(tr);
    syncSummaryBarWithCurrentFilter();
  }
  function updateDirty(id) {
    const cur = currentValueById[id];
    const base = originalValueById[id] ?? 0;
    const a = Number.isFinite(cur) ? roundHalfUp(cur, STORE_PLACES) : 0;
    const b = Number.isFinite(base) ? roundHalfUp(base, STORE_PLACES) : 0;
    const dirty = a !== b;
    if (dirty) dirtySet.add(id); else dirtySet.delete(id);
    setRowDirtyVisual(id, dirty);
  }

  function flushPendingQtyInputs() {
    // FIX: commit SEMUA edit yang masih menunggu debounce (120ms) sebelum simpan/reload.
    // rawInputById di-update SEKETIKA saat mengetik, jadi membandingkan input.value vs
    // rawInputById selalu sama dan TIDAK bisa mendeteksi edit pending (bug data-loss:
    // simpan dalam <120ms setelah mengetik membuat baris itu tak pernah masuk dirtySet).
    // Sumber kebenaran = pendingInputIds (diisi tiap keystroke, dibersihkan handleInputChange).
    if (pendingInputIds.size) {
      Array.from(pendingInputIds).forEach((id) => {
        const tr = rows.find((r) => parseInt(r.dataset.pekerjaanId, 10) === id)
          || document.querySelector(`tr[data-pekerjaan-id="${id}"]`);
        if (!tr) { pendingInputIds.delete(id); return; }
        const input = tr.querySelector('.qty-input');
        const preview = tr.querySelector('.fx-preview');
        if (!input) { pendingInputIds.delete(id); return; }
        handleInputChange(id, input, preview, false); // ikut menghapus id dari pendingInputIds
      });
    }
    setBtnSaveEnabled();
  }

  function reevaluateAllFormulas() {
    // Sprint 3.4: batch processing to avoid jank on large projects
    const BATCH_SIZE = 50;
    const allRows = Array.from(rows);
    let index = 0;
    function processBatch() {
      const end = Math.min(index + BATCH_SIZE, allRows.length);
      for (let i = index; i < end; i++) {
        const tr = allRows[i];
        const id = parseInt(tr.dataset.pekerjaanId, 10);
        const input = tr.querySelector('.qty-input');
        const preview = tr.querySelector('.fx-preview');
        const raw = String(rawInputById[id] || input.value || '');
        if (!raw.trim()) continue;
        if (isFormulaMode(id, raw)) handleInputChange(id, input, preview, false);
      }
      index = end;
      if (index < allRows.length) {
        requestAnimationFrame(processBatch);
      } else {
        setBtnSaveEnabled();
      }
    }
    if (allRows.length > 0) {
      requestAnimationFrame(processBatch);
    } else {
      setBtnSaveEnabled();
    }
  }

  // ===== Parameter table (Label & Kode)
  function normalizeOpaqueCode(s) {
    return String(s || '').trim().toLowerCase();
  }

  function isBaseOpaqueCode(code) {
    return /^bp_[1-9][0-9]*$/.test(String(code || '').trim().toLowerCase());
  }

  function isComputedOpaqueCode(code) {
    return /^cp_[1-9][0-9]*$/.test(String(code || '').trim().toLowerCase());
  }

  function isLegacyParamCode(code) {
    return /^[a-z_][a-z0-9_]*$/.test(String(code || '').trim().toLowerCase());
  }

  function isValidBaseParamCode(code) {
    const safe = String(code || '').trim().toLowerCase();
    if (OPAQUE_ID_ENABLED) return isBaseOpaqueCode(safe);
    if (isComputedOpaqueCode(safe)) return false;
    return isLegacyParamCode(safe) || isBaseOpaqueCode(safe);
  }

  function isValidComputedParamCode(code) {
    const safe = String(code || '').trim().toLowerCase();
    if (OPAQUE_ID_ENABLED) return isComputedOpaqueCode(safe);
    if (isBaseOpaqueCode(safe)) return false;
    return isLegacyParamCode(safe) || isComputedOpaqueCode(safe);
  }

  function baseCodeExpectedText() {
    return OPAQUE_ID_ENABLED ? 'bp_N' : 'legacy (a-z0-9_) atau bp_N';
  }

  function computedCodeExpectedText() {
    return OPAQUE_ID_ENABLED ? 'cp_N' : 'legacy (a-z0-9_) atau cp_N';
  }

  function renderVarTable() {
    if (!varTable) return;
    const tbody = varTable.querySelector('tbody');
    tbody.innerHTML = '';
    const allCodes = Object.keys(variables);
    const usageMap = collectFormulaUsageMap();
    const filteredCodes = allCodes.filter((code) => matchesSidebarSearch({
      code,
      label: varLabels[code] || code,
      expression: '',
      preview: '',
    }));

    // Update count display
    const countEl = document.getElementById('vp-param-count');
    if (countEl) {
      if (sidebarSearchQueryText()) {
        countEl.textContent = `${filteredCodes.length}/${allCodes.length}`;
        countEl.setAttribute('title', `Menampilkan ${filteredCodes.length} dari ${allCodes.length} parameter`);
      } else {
        countEl.textContent = String(allCodes.length);
        countEl.removeAttribute('title');
      }
    }
    const tabCountEl = document.getElementById('vp-tab-base-count');
    if (tabCountEl) tabCountEl.textContent = String(allCodes.length);

    if (allCodes.length === 0) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td colspan="3" class="text-muted text-center py-4">
        <i class="bi bi-box-seam d-block mb-2" style="font-size: 2rem; opacity: 0.5;"></i>
        Belum ada parameter.<br>
        <small class="text-muted">Klik "Tambah" untuk membuat parameter baru.</small>
      </td>`;
      tbody.appendChild(tr);
      return;
    }
    if (filteredCodes.length === 0) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td colspan="3" class="text-muted text-center py-4">
        Tidak ada parameter yang cocok dengan kata kunci.
      </td>`;
      tbody.appendChild(tr);
      return;
    }
    const codes = filteredCodes.sort((a, b) => (varLabels[a] || a).localeCompare(varLabels[b] || b, 'id'));
    codes.forEach(code => {
      const val = variables[code];
      const label = varLabels[code] || code;
      const usageSummary = summarizeFormulaUsage(code, usageMap);
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>
          <input type="text" class="form-control form-control-sm var-label" value="${escapeHtml(label)}" aria-label="Nama/Label parameter" readonly>
          ${buildUsageBadgeHtml(usageSummary)}
        </td>
        <td>
          <input type="text" class="form-control form-control-sm var-value" value="${formatParamSmart(val)}" aria-label="Nilai parameter" readonly>
        </td>
        <td class="text-end">
          <div class="btn-group btn-group-sm">
            <button type="button" class="btn btn-outline-secondary var-edit" title="Ubah" aria-label="Ubah"><i class="bi bi-pencil"></i></button>
            <button type="button" class="btn btn-outline-danger var-del" title="Hapus" aria-label="Hapus"><i class="bi bi-trash"></i></button>
          </div>
        </td>`;
      tr.addEventListener('click', () => {
        tbody.querySelectorAll('tr').forEach(r => r.classList.remove('table-primary'));
        tr.classList.add('table-primary');
        tr.scrollIntoView({ block: 'nearest' });
      });
      tr.querySelector('.var-label').addEventListener('change', e => {
        const nextLabel = String(e.target.value || '').trim();
        if (!nextLabel) {
          e.target.classList.add('is-invalid');
          setTimeout(() => e.target.classList.remove('is-invalid'), 1200);
          e.target.value = label;
          return;
        }
        varLabels[code] = nextLabel;
        saveVarLabels();
      });
      tr.querySelector('.var-value').addEventListener('change', e => {
        const n = parseNumberOrEmpty(e.target.value);
        if (n === '') {
          e.target.classList.add('is-invalid');
          setTimeout(() => e.target.classList.remove('is-invalid'), 1200);
          e.target.value = formatParamSmart(val);
          return;
        }
        variables[code] = roundHalfUp(Number(n), PARAM_STORE_PLACES);
        saveVars();
        reevaluateAllFormulas();
      });
      // Edit toggle button
      const btnEdit = tr.querySelector('.var-edit');
      if (btnEdit) {
        btnEdit.addEventListener('click', () => {
          const labelEl = tr.querySelector('.var-label');
          const valueEl = tr.querySelector('.var-value');
          const isEditing = tr.classList.toggle('is-editing');
          const icon = btnEdit.querySelector('i');
          if (isEditing) {
            // Enter edit mode
            labelEl.readOnly = false; valueEl.readOnly = false;
            labelEl.dataset.prev = labelEl.value; valueEl.dataset.prev = valueEl.value;
            if (icon) icon.className = 'bi bi-check-lg';
            btnEdit.setAttribute('title', 'Simpan'); btnEdit.setAttribute('aria-label', 'Simpan');
            labelEl.focus();
          } else {
            // Save and exit edit mode
            const nextLabel = String(labelEl.value || '').trim();
            const n = parseNumberOrEmpty(valueEl.value);
            let ok = true;
            if (!nextLabel) { ok = false; labelEl.classList.add('is-invalid'); setTimeout(() => labelEl.classList.remove('is-invalid'), 1200); labelEl.value = varLabels[code] || code; }
            if (n === '') { ok = false; valueEl.classList.add('is-invalid'); setTimeout(() => valueEl.classList.remove('is-invalid'), 1200); valueEl.value = formatParamSmart(variables[code]); }
            if (ok) {
              varLabels[code] = nextLabel; saveVarLabels();
              variables[code] = roundHalfUp(Number(n), PARAM_STORE_PLACES); saveVars();
              reevaluateAllFormulas();
            }
            labelEl.readOnly = true; valueEl.readOnly = true;
            if (icon) icon.className = 'bi bi-pencil';
            btnEdit.setAttribute('title', 'Ubah'); btnEdit.setAttribute('aria-label', 'Ubah');
          }
        });
      }
      tr.querySelector('.var-del').addEventListener('click', async () => {
        const nm = varLabels[code] || code;
        const usage = summarizeFormulaUsage(code, collectFormulaUsageMap());
        const message = buildDeleteWarningMessage('base', nm, code, usage);
        const ok = await confirmModal(message, {
          title: 'Hapus Parameter',
          confirmText: 'Hapus',
          cancelText: 'Batal',
          confirmClass: 'btn btn-danger',
        });
        if (!ok) return;
        delete variables[code];
        delete varLabels[code];
        saveVars();
        saveVarLabels();
        reevaluateAllFormulas();
        renderVarTable();
      });
      tbody.appendChild(tr);
    });
  }

  function normalizeComputedParamsShape(rawObj) {
    const out = {};
    if (!rawObj || typeof rawObj !== 'object') return out;
    Object.keys(rawObj).forEach((k) => {
      const code = normalizeOpaqueCode(k);
      if (!isValidComputedParamCode(code)) return;
      const v = rawObj[k];
      if (typeof v === 'string') {
        out[code] = { expression: v, label: code, unit: '', description: '' };
        return;
      }
      if (!v || typeof v !== 'object') return;
      const expression = String(v.expression || '').trim();
      if (!expression) return;
      out[code] = {
        expression,
        label: String(v.label || code).trim() || code,
        unit: String(v.unit || '').trim(),
        description: String(v.description || '').trim(),
      };
    });
    return out;
  }

  function dropComputedNameConflicts() {
    let changed = false;
    Object.keys(computedParams || {}).forEach((code) => {
      if (!Object.prototype.hasOwnProperty.call(variables, code)) return;
      delete computedParams[code];
      changed = true;
    });
    if (changed) {
      console.warn('[VP] Removed computed parameter(s) that conflict with base parameter codes.');
    }
  }

  function renderComputedTable() {
    if (!cParamTable) return;
    const tbody = cParamTable.querySelector('tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    const usageMap = collectFormulaUsageMap();
    const labels = getFormulaScopeLabels();
    const scopeValues = getFormulaScopeValues();

    const allCodes = Object.keys(computedParams || {});
    const filteredCodes = allCodes.filter((code) => {
      const def = computedParams[code] || {};
      const expression = String(def.expression || '');
      const label = String(def.label || code);
      const preview = translateFormulaForPreview(expression, {
        mode: 'label',
        scopeLabels: labels,
        scopeValues,
      });
      return matchesSidebarSearch({
        code,
        label,
        expression,
        preview,
      });
    });
    const countEl = document.getElementById('vp-cparam-count');
    if (countEl) {
      if (sidebarSearchQueryText()) {
        countEl.textContent = `${filteredCodes.length}/${allCodes.length}`;
        countEl.setAttribute('title', `Menampilkan ${filteredCodes.length} dari ${allCodes.length} formula turunan`);
      } else {
        countEl.textContent = String(allCodes.length);
        countEl.removeAttribute('title');
      }
    }
    const tabCountEl = document.getElementById('vp-tab-computed-count');
    if (tabCountEl) tabCountEl.textContent = String(allCodes.length);

    if (!allCodes.length) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td colspan="3" class="text-muted text-center py-3">
        Belum ada formula turunan.
      </td>`;
      tbody.appendChild(tr);
      return;
    }
    if (!filteredCodes.length) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td colspan="3" class="text-muted text-center py-3">
        Tidak ada formula turunan yang cocok dengan kata kunci.
      </td>`;
      tbody.appendChild(tr);
      return;
    }

    const codes = filteredCodes.sort((a, b) => (labels[a] || a).localeCompare((labels[b] || b), 'id'));
    codes.forEach((code) => {
      const def = computedParams[code] || {};
      const label = def.label || code;
      const expression = String(def.expression || '');
      const val = computedValues[code];
      const err = computedErrors[code];
      const errText = err ? humanizeFormulaError(err, labels) : '';
      const exprLabelPreview = translateFormulaForPreview(expression, {
        mode: 'label',
        scopeLabels: labels,
        scopeValues: getFormulaScopeValues(),
      });
      const exprChipPreview = buildFormulaChipHtml(String(expression || '').replace(/^=/, '').trim(), labels, { compact: true });
      const usageSummary = summarizeFormulaUsage(code, usageMap);

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>
          <input type="text" class="form-control form-control-sm cparam-label" value="${escapeHtml(label)}" readonly title="Double-click untuk ubah nama">
          ${buildUsageBadgeHtml(usageSummary)}
        </td>
        <td class="cparam-formula-cell">
          <div class="cparam-expression-label">${escapeHtml(exprLabelPreview || expression)}</div>
          <div class="cparam-expression-chip">${exprChipPreview}</div>
        </td>
        <td class="text-end cparam-actions-cell">
          <div class="cparam-value-display small ${err ? 'text-danger' : 'text-success'}">
            ${err ? escapeHtml(errText) : formatParamSmart(Number(val || 0))}
          </div>
          <div class="cparam-action-bar">
            <button type="button" class="btn btn-outline-primary btn-sm cparam-edit" title="Edit formula" aria-label="Edit formula">
              <i class="bi bi-pencil-square"></i>
            </button>
            <button type="button" class="btn btn-outline-danger btn-sm cparam-del" title="Hapus" aria-label="Hapus">
              <i class="bi bi-trash3"></i>
            </button>
          </div>
        </td>`;

      const labelEl = tr.querySelector('.cparam-label');
      const formulaCell = tr.querySelector('.cparam-formula-cell');
      const editBtn = tr.querySelector('.cparam-edit');
      const delBtn = tr.querySelector('.cparam-del');

      editBtn?.addEventListener('click', () => {
        openFormulaEditorForComputed(code, { enableNameEdit: true });
      });

      // Click formula cell to open formula editor
      formulaCell?.addEventListener('click', () => {
        openFormulaEditorForComputed(code);
      });

      // Double-click label for inline rename
      labelEl?.addEventListener('dblclick', () => {
        labelEl.readOnly = false;
        labelEl.focus();
        const saveLabel = () => {
          const nextLabel = String(labelEl.value || '').trim();
          if (!nextLabel) {
            labelEl.value = label;
          } else if (nextLabel !== label) {
            const nextDefs = { ...computedParams };
            nextDefs[code] = { ...nextDefs[code], label: nextLabel };
            computedParams = nextDefs;
            saveComputedParams();
          }
          labelEl.readOnly = true;
        };
        labelEl.addEventListener('blur', saveLabel, { once: true });
        labelEl.addEventListener('keydown', (e) => {
          if (e.key === 'Enter') { e.preventDefault(); labelEl.blur(); }
          if (e.key === 'Escape') { labelEl.value = label; labelEl.readOnly = true; }
        });
      });

      delBtn?.addEventListener('click', async () => {
        const usage = summarizeFormulaUsage(code, collectFormulaUsageMap());
        const message = buildDeleteWarningMessage('computed', label, code, usage);
        const ok = await confirmModal(message, {
          title: 'Hapus Formula Turunan',
          confirmText: 'Hapus',
          cancelText: 'Batal',
          confirmClass: 'btn btn-danger',
        });
        if (!ok) return;
        delete computedParams[code];
        saveComputedParams();
      });

      tbody.appendChild(tr);
    });
  }

  // Tambah Parameter (inline)
  if (btnVarAdd && !btnVarAdd.dataset.bound) {
    btnVarAdd.addEventListener('click', () => {
      if (!varTable) return;
      const tbody = varTable.querySelector('tbody');
      const existing = tbody.querySelector('tr.vp-var-inline');
      if (existing) { existing.querySelector('.var-label')?.focus(); return; }

      const tr = document.createElement('tr');
      tr.className = 'vp-var-inline';
      tr.innerHTML = `
        <td>
          <input type="text" class="form-control form-control-sm var-label" placeholder="mis. Panjang Dinding">
          <div class="invalid-feedback">Label tidak boleh kosong.</div>
          <small class="text-muted d-block mt-1">${OPAQUE_ID_ENABLED ? 'Kode opaque dibuat otomatis di server.' : 'Kode parameter dibuat otomatis dari label di server.'}</small>
        </td>
        <td>
          <input type="text" class="form-control form-control-sm var-value" placeholder="0">
          <div class="invalid-feedback">Nilai angka diperlukan.</div>
        </td>
        <td class="text-end">
          <div class="btn-group btn-group-sm">
            <button type="button" class="btn btn-success var-save">Simpan</button>
            <button type="button" class="btn btn-outline-secondary var-cancel">Batal</button>
          </div>
        </td>`;
      tbody.prepend(tr);

      const labelEl = tr.querySelector('.var-label');
      const valEl = tr.querySelector('.var-value');
      labelEl && labelEl.focus();

      const doCancel = () => tr.remove();
      const doSave = async () => {
        const label = String(labelEl.value || '').trim();
        const n = parseNumberOrEmpty(valEl.value);
        labelEl.classList.toggle('is-invalid', !label);
        valEl.classList.toggle('is-invalid', n === '');
        if (!label || n === '') return;

        const res = await HTTP.jpost(EP_PARAMS, {
          value: roundHalfUp(Number(n), PARAM_STORE_PLACES),
          label,
          unit: '',
          description: '',
        });
        if (!(res.ok && res.data?.ok && res.data?.parameter?.name)) {
          const errMsg = (res.data?.errors && res.data.errors[0]?.message)
            || res.data?.message
            || 'Gagal menyimpan parameter ke server.';
          TOAST.err(errMsg);
          return;
        }

        const created = res.data.parameter;
        const code = String(created.name || '').trim();
        if (!isValidBaseParamCode(code)) {
          TOAST.err('Server mengembalikan kode parameter tidak valid.');
          return;
        }
        variables[code] = Number(created.value ?? 0) || 0;
        varLabels[code] = String(created.label || label).trim() || label;
        if (res.data?.synced_at) setBaseParamSyncAt(String(res.data.synced_at));
        saveVars();
        saveVarLabels();
        tr.remove();
        renderVarTable();
        reevaluateAllFormulas();
      };

      tr.querySelector('.var-save').addEventListener('click', () => { doSave(); });
      tr.querySelector('.var-cancel').addEventListener('click', doCancel);
      [labelEl, valEl].forEach(el => el.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') doSave();
        if (e.key === 'Escape') doCancel();
      }));
    });
    btnVarAdd.dataset.bound = '1';
  }

  // Tambah Formula Turunan (inline label + modal expression)
  if (btnCParamAdd && !btnCParamAdd.dataset.bound) {
    btnCParamAdd.addEventListener('click', () => {
      if (!cParamTable) return;
      const tbody = cParamTable.querySelector('tbody');
      if (!tbody) return;
      const existing = tbody.querySelector('tr.vp-cparam-inline');
      if (existing) {
        existing.querySelector('.cparam-label')?.focus();
        return;
      }

      let pendingExpression = '';

      const tr = document.createElement('tr');
      tr.className = 'vp-cparam-inline';
      tr.innerHTML = `
        <td>
          <input type="text" class="form-control form-control-sm cparam-label" placeholder="mis. Area L1">
          <small class="text-muted d-block mt-1">${OPAQUE_ID_ENABLED ? 'Kode dibuat otomatis.' : 'Kode dibuat dari label.'}</small>
        </td>
        <td class="cparam-expr-cell">
          <button type="button" class="btn btn-outline-secondary btn-sm cparam-open-editor w-100" title="Buka editor formula">
            <i class="bi bi-pencil-square me-1"></i> Set Formula
          </button>
          <div class="cparam-expr-display small text-muted mt-1"></div>
          <div class="cparam-expr-chip-preview mt-1"></div>
        </td>
        <td class="text-end cparam-actions-cell">
          <div class="cparam-value-preview small text-muted mb-1">-</div>
          <div class="cparam-action-bar">
            <button type="button" class="btn btn-success btn-sm cparam-save" disabled>Simpan</button>
            <button type="button" class="btn btn-outline-secondary btn-sm cparam-cancel">Batal</button>
          </div>
        </td>`;
      tbody.prepend(tr);

      const labelEl = tr.querySelector('.cparam-label');
      const openEditorBtn = tr.querySelector('.cparam-open-editor');
      const exprDisplayEl = tr.querySelector('.cparam-expr-display');
      const chipPreviewEl = tr.querySelector('.cparam-expr-chip-preview');
      const valuePrevEl = tr.querySelector('.cparam-value-preview');
      const saveBtn = tr.querySelector('.cparam-save');
      labelEl?.focus();

      const updateExprDisplay = (expr) => {
        pendingExpression = expr || '';
        if (saveBtn) saveBtn.disabled = !pendingExpression;
        if (!pendingExpression) {
          if (exprDisplayEl) exprDisplayEl.textContent = 'Belum diset';
          if (chipPreviewEl) chipPreviewEl.innerHTML = '';
          if (valuePrevEl) valuePrevEl.textContent = '-';
          if (openEditorBtn) {
            openEditorBtn.innerHTML = '<i class="bi bi-pencil-square"></i> Set Formula';
            openEditorBtn.classList.remove('btn-primary');
            openEditorBtn.classList.add('btn-outline-secondary');
          }
          return;
        }
        const scopeLabels = getFormulaScopeLabels();
        const scopeValues = getFormulaScopeValues();
        const labelPreview = translateFormulaForPreview(pendingExpression, {
          mode: 'label', scopeLabels, scopeValues,
        });
        if (exprDisplayEl) exprDisplayEl.textContent = labelPreview || pendingExpression;
        if (chipPreviewEl) chipPreviewEl.innerHTML = buildFormulaChipHtml(
          pendingExpression.replace(/^=/, '').trim(), scopeLabels, { compact: true }
        );
        // Evaluate and show value
        const validation = validateFormulaExpression(`=${pendingExpression}`, { scopeValues, scopeLabels });
        if (valuePrevEl) {
          if (validation.ok) {
            valuePrevEl.textContent = formatParamSmart(validation.value);
            valuePrevEl.className = 'small text-success cparam-value-preview';
          } else {
            valuePrevEl.textContent = 'Error';
            valuePrevEl.className = 'small text-danger cparam-value-preview';
          }
        }
        if (openEditorBtn) {
          openEditorBtn.innerHTML = '<i class="bi bi-pencil-square"></i> Edit Formula';
          openEditorBtn.classList.remove('btn-outline-secondary');
          openEditorBtn.classList.add('btn-primary');
        }
      };

      openEditorBtn?.addEventListener('click', () => {
        const label = String(labelEl?.value || '').trim() || 'Baru';
        openFormulaEditorForComputed('', {
          isNew: true,
          label,
          expression: pendingExpression,
          onCreated: (exprBody) => {
            updateExprDisplay(exprBody);
          },
        });
      });

      const doCancel = () => { tr.remove(); };
      const doSave = async () => {
        const label = String(labelEl?.value || '').trim();
        labelEl?.classList.toggle('is-invalid', !label);
        if (!label || !pendingExpression) {
          if (!pendingExpression && openEditorBtn) {
            openEditorBtn.classList.add('btn-danger');
            setTimeout(() => openEditorBtn.classList.remove('btn-danger'), 1200);
          }
          return;
        }

        const res = await HTTP.jpost(EP_CPARAMS, {
          label,
          expression: pendingExpression,
          unit: '',
          description: '',
        });
        if (!(res.ok && res.data?.ok && res.data?.computed_parameter?.name)) {
          const errMsg = (res.data?.errors && res.data.errors[0]?.message)
            || res.data?.message
            || 'Gagal menyimpan formula turunan ke server.';
          TOAST.err(errMsg);
          return;
        }

        const created = res.data.computed_parameter;
        const code = String(created.name || '').trim();
        if (!isValidComputedParamCode(code)) {
          TOAST.err('Server mengembalikan kode formula turunan tidak valid.');
          return;
        }
        computedParams[code] = {
          expression: String(created.expression || pendingExpression),
          label: String(created.label || label).trim() || label,
          unit: String(created.unit || '').trim(),
          description: String(created.description || '').trim(),
        };
        if (res.data?.synced_at) setComputedParamSyncAt(String(res.data.synced_at));
        tr.remove();
        saveComputedParams();
      };

      saveBtn?.addEventListener('click', () => { doSave(); });
      tr.querySelector('.cparam-cancel')?.addEventListener('click', doCancel);
      labelEl?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); openEditorBtn?.click(); }
        if (e.key === 'Escape') doCancel();
      });
    });
    btnCParamAdd.dataset.bound = '1';
  }

  // === Unified Import/Export (JSON | CSV | XLSX*) ==================
  // *XLSX untuk import/export akan aktif jika SheetJS ada (window.XLSX)

  function splitDelimitedLine(line) {
    const text = String(line || '');
    const cells = [];
    let current = '';
    let inQuotes = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      const next = text[i + 1];
      if (ch === '"') {
        if (inQuotes && next === '"') {
          current += '"';
          i++;
          continue;
        }
        inQuotes = !inQuotes;
        continue;
      }
      if (!inQuotes && /[,;\t]/.test(ch)) {
        cells.push(current.trim());
        current = '';
        continue;
      }
      current += ch;
    }
    cells.push(current.trim());
    return cells;
  }

  function csvEscapeCell(value) {
    const raw = String(value ?? '');
    if (!/[",;\t\r\n]/.test(raw)) return raw;
    return `"${raw.replace(/"/g, '""')}"`;
  }

  function csvJoinRow(cells) {
    return (cells || []).map((cell) => csvEscapeCell(cell)).join(',');
  }

  function buildUnifiedParameterPayload() {
    const payload = { _format: 'vp-vars-v2', variables, labels: varLabels };
    const cpKeys = Object.keys(computedParams || {});
    if (cpKeys.length) {
      payload.computed_parameters = {};
      cpKeys.forEach((code) => {
        const def = computedParams[code] || {};
        payload.computed_parameters[code] = {
          expression: String(def.expression || ''),
          label: String(def.label || code),
          unit: String(def.unit || ''),
          description: String(def.description || ''),
        };
      });
    }
    return payload;
  }

  function csvFromVarsAndComputed(varsObj, labelsObj, computedObj = {}) {
    const lines = ['# Base Parameters', csvJoinRow(['Kode', 'Nama', 'Nilai'])];
    const baseCodes = Object.keys(varsObj || {})
      .sort((a, b) => (labelsObj[a] || a).localeCompare(labelsObj[b] || b, 'id'));
    baseCodes.forEach((code) => {
      lines.push(csvJoinRow([
        code,
        String(labelsObj[code] || code),
        String(varsObj[code]),
      ]));
    });

    const computedCodes = Object.keys(computedObj || {})
      .sort((a, b) => {
        const la = String(computedObj[a]?.label || a);
        const lb = String(computedObj[b]?.label || b);
        return la.localeCompare(lb, 'id');
      });
    if (computedCodes.length) {
      lines.push('');
      lines.push('# Computed Parameters');
      lines.push(csvJoinRow(['Kode', 'Nama', 'Formula', 'Unit', 'Deskripsi']));
      computedCodes.forEach((code) => {
        const def = computedObj[code] || {};
        lines.push(csvJoinRow([
          code,
          String(def.label || code),
          String(def.expression || ''),
          String(def.unit || ''),
          String(def.description || ''),
        ]));
      });
    }
    return `${lines.join('\n')}\n`;
  }

  function tsCompact() {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}`;
  }

  function ensureFileInputs() {
    // Reuse input yang sudah ada; set accept jadi gabungan
    const fileJson = document.getElementById('vp-var-import');
    if (fileJson) fileJson.setAttribute('accept', '.json,.csv,.xlsx');
    // Sembunyikan tombol import excel lama kalau ada
    const btnOld = document.getElementById('vp-var-import-excel-btn');
    const inpOld = document.getElementById('vp-var-import-excel');
    if (btnOld) btnOld.classList.add('d-none');
    if (inpOld) inpOld.classList.add('d-none');
  }

  // ---- EXPORTERS
  function exportAsJSON() {
    try {
      const payload = buildUnifiedParameterPayload();
      const data = JSON.stringify(payload, null, 2);
      const blob = new Blob([data], { type: 'application/json' });
      const a = document.createElement('a');
      const ts = tsCompact();
      a.href = URL.createObjectURL(blob);
      a.download = `parameter_${projectId}_${ts}.json`;
      document.body.appendChild(a); a.click(); a.remove();
      TOAST.ok('Parameter diekspor (JSON).');
    } catch { TOAST.err('Gagal export JSON.'); }
  }

  function exportAsCSV() {
    try {
      const csv = csvFromVarsAndComputed(variables, varLabels, computedParams);
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
      const a = document.createElement('a');
      const ts = tsCompact();
      a.href = URL.createObjectURL(blob);
      a.download = `parameter_${projectId}_${ts}.csv`;
      document.body.appendChild(a); a.click(); a.remove();
      TOAST.ok('Parameter diekspor (CSV).');
    } catch { TOAST.err('Gagal export CSV.'); }
  }

  function exportAsXLSX() {
    if (!(window.XLSX && XLSX.utils && XLSX.writeFile)) {
      TOAST.warn('Export XLSX butuh SheetJS (window.XLSX). Fallback ke CSV.');
      exportAsCSV(); return;
    }
    try {
      const rows = Object.keys(variables)
        .sort((a, b) => (varLabels[a] || a).localeCompare(varLabels[b] || b, 'id'))
        .map((code) => ({ Kode: code, Nama: (varLabels[code] || code), Nilai: variables[code] }));
      const ws = XLSX.utils.json_to_sheet(rows, { header: ['Kode', 'Nama', 'Nilai'] });
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Parameter');
      const cpRows = Object.keys(computedParams || {})
        .sort((a, b) => {
          const la = String(computedParams[a]?.label || a);
          const lb = String(computedParams[b]?.label || b);
          return la.localeCompare(lb, 'id');
        })
        .map((code) => {
          const def = computedParams[code] || {};
          return {
            Kode: code,
            Nama: String(def.label || code),
            Formula: String(def.expression || ''),
            Unit: String(def.unit || ''),
            Deskripsi: String(def.description || ''),
          };
        });
      if (cpRows.length) {
        const wsComputed = XLSX.utils.json_to_sheet(cpRows, {
          header: ['Kode', 'Nama', 'Formula', 'Unit', 'Deskripsi'],
        });
        XLSX.utils.book_append_sheet(wb, wsComputed, 'Computed Parameter');
      }
      const ts = tsCompact();
      XLSX.writeFile(wb, `parameter_${projectId}_${ts}.xlsx`);
      TOAST.ok('Parameter diekspor (XLSX).');
    } catch { TOAST.err('Gagal export XLSX.'); }
  }

  async function copyJSONToClipboard() {
    try {
      const payload = buildUnifiedParameterPayload();
      const data = JSON.stringify(payload, null, 2);
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(data);
      } else {
        const ta = document.createElement('textarea');
        ta.value = data; document.body.appendChild(ta); ta.select();
        document.execCommand('copy'); ta.remove();
      }
      TOAST.ok('JSON disalin ke clipboard.');
    } catch { TOAST.err('Gagal menyalin JSON.'); }
  }

  // Popup kecil di dekat tombol export untuk pilih format
  function showExportMenu(anchorBtn) {
    const menu = document.createElement('div');
    menu.className = 'dropdown-menu show';
    menu.style.position = 'absolute';
    menu.innerHTML = `
      <button class="dropdown-item" type="button" data-fmt="json">Export JSON</button>
      <button class="dropdown-item" type="button" data-fmt="csv">Export CSV</button>
      <button class="dropdown-item" type="button" data-fmt="xlsx">Export XLSX</button>
    `;
    document.body.appendChild(menu);
    const rect = anchorBtn.getBoundingClientRect();
    menu.style.left = `${rect.left}px`;
    menu.style.top = `${rect.bottom + window.scrollY}px`;

    const close = () => { document.removeEventListener('click', onDoc); menu.remove(); };
    const onDoc = (e) => { if (!menu.contains(e.target) && e.target !== anchorBtn) close(); };
    document.addEventListener('click', onDoc);

    menu.addEventListener('click', (e) => {
      const fmt = e.target && e.target.getAttribute('data-fmt');
      if (fmt === 'json') exportAsJSON();
      else if (fmt === 'csv') exportAsCSV();
      else if (fmt === 'xlsx') exportAsXLSX();
      close();
    });
  }

  // ---- IMPORTERS
  // --- Import parsers (parse-only; not applying state yet)
  function parseJSONToVarsLabels(rawText) {
    const obj = JSON.parse(rawText);
    let srcVars = {}, srcLabels = {}, srcComputed = null;
    if (obj && typeof obj === 'object' && obj._format === 'vp-vars-v2') {
      srcVars = (obj.variables && typeof obj.variables === 'object') ? obj.variables : {};
      srcLabels = (obj.labels && typeof obj.labels === 'object') ? obj.labels : {};
      // Sprint 3.3: parse computed parameters from JSON import
      if (obj.computed_parameters && typeof obj.computed_parameters === 'object') {
        srcComputed = obj.computed_parameters;
      }
    } else if (obj && typeof obj === 'object') {
      Object.keys(obj).forEach(code => {
        srcVars[code] = obj[code];
        srcLabels[code] = code;
      });
    } else throw new Error('format');
    const errors = [];
    const outVars = {}, outLabels = {}, outComputed = {};
    const toImportRowRef = (labelValue, codeValue, idx) => {
      const labelText = String(labelValue || '').trim();
      const codeText = normalizeOpaqueCode(codeValue || '');
      if (!labelText) return `Baris ${idx + 1}`;
      if (/^(?:bp|cp)_[1-9][0-9]*$/i.test(labelText)) return `Baris ${idx + 1}`;
      if (codeText && labelText.toLowerCase() === codeText) return `Baris ${idx + 1}`;
      return labelText;
    };
    Object.keys(srcVars).forEach((code, idx) => {
      const safe = normalizeOpaqueCode(code);
      const importLabel = String((srcLabels && srcLabels[code]) || '').trim();
      const displayRef = toImportRowRef(importLabel, safe, idx);
      if (!isValidBaseParamCode(safe)) {
        errors.push(`${displayRef}: format parameter tidak valid`);
        return;
      }
      const val = parseNumberOrEmpty(srcVars[code]);
      if (val === '') { errors.push(`${displayRef}: Nilai tidak valid`); return; }
      outVars[safe] = roundHalfUp(Number(val), PARAM_STORE_PLACES);
      const lbl = String((srcLabels && srcLabels[code]) || code || '').trim();
      outLabels[safe] = lbl || safe;
    });
    if (srcComputed && typeof srcComputed === 'object') {
      Object.keys(srcComputed).forEach((code, idx) => {
        const safe = normalizeOpaqueCode(code);
        const def = srcComputed[code] || {};
        const label = String(def.label || safe).trim() || safe;
        const expression = String(def.expression || '').trim();
        const displayRef = toImportRowRef(label, safe, idx);
        if (!isComputedOpaqueCode(safe)) {
          errors.push(`${displayRef}: format formula parameter tidak valid`);
          return;
        }
        if (!expression) {
          errors.push(`${displayRef}: Formula kosong`);
          return;
        }
        outComputed[safe] = {
          expression,
          label,
          unit: String(def.unit || '').trim(),
          description: String(def.description || '').trim(),
        };
      });
    }
    return {
      vars: outVars,
      labels: outLabels,
      errors,
      computed: Object.keys(outComputed).length ? outComputed : null,
    };
  }

  function parseCSVToVarsLabels(rawText) {
    const errors = [];
    const nextVars = {}, nextLabels = {}, nextComputed = {};
    const lines = String(rawText || '').split(/\r?\n/);
    let mode = 'base';
    let hasData = false;
    const toImportRowRef = (labelValue, codeValue, idx) => {
      const labelText = String(labelValue || '').trim();
      const codeText = normalizeOpaqueCode(codeValue || '');
      if (!labelText) return `Baris ${idx + 1}`;
      if (/^(?:bp|cp)_[1-9][0-9]*$/i.test(labelText)) return `Baris ${idx + 1}`;
      if (codeText && labelText.toLowerCase() === codeText) return `Baris ${idx + 1}`;
      return labelText;
    };
    lines.forEach((line, idx) => {
      const trimmed = String(line || '').trim();
      if (!trimmed) return;
      if (trimmed.startsWith('#')) {
        const marker = trimmed.toLowerCase();
        if (/computed|turunan|formula/.test(marker)) mode = 'computed';
        else if (/base|parameter/.test(marker)) mode = 'base';
        return;
      }
      const cells = splitDelimitedLine(line).map((c) => String(c || '').trim());
      if (!cells.length || cells.every((c) => !c)) return;
      const c0 = String(cells[0] || '').toLowerCase();
      const c1 = String(cells[1] || '').toLowerCase();
      const c2 = String(cells[2] || '').toLowerCase();
      const isBaseHeader = (
        /^(kode|code|nama|label)$/.test(c0)
        && /^(nama|label|nilai|value)$/.test(c1)
      );
      const isComputedHeader = (
        /^(kode|code)$/.test(c0)
        && /^(nama|label)$/.test(c1)
        && /^(formula|expression)$/.test(c2)
      );
      if (isBaseHeader) {
        mode = 'base';
        return;
      }
      if (isComputedHeader) {
        mode = 'computed';
        return;
      }

      if (mode === 'computed') {
        const code = normalizeOpaqueCode(cells[0] || '');
        const label = String(cells[1] || code || '').trim();
        const expression = String(cells[2] || '').trim();
        const unit = String(cells[3] || '').trim();
        const description = String(cells[4] || '').trim();
        const displayRef = toImportRowRef(label, code, idx);
        if (!isComputedOpaqueCode(code)) {
          errors.push(`${displayRef}: Format formula parameter tidak sesuai`);
          return;
        }
        if (!label) {
          errors.push(`Baris ${idx + 1}: Label formula parameter kosong`);
          return;
        }
        if (!expression) {
          errors.push(`Baris ${idx + 1}: Formula kosong`);
          return;
        }
        nextComputed[code] = { expression, label, unit, description };
        hasData = true;
        return;
      }

      const code = normalizeOpaqueCode(cells[0] || '');
      const hasLabelCol = (cells.length >= 3);
      const label = String((hasLabelCol ? (cells[1] || code) : code)).trim();
      const displayRef = toImportRowRef(label, code, idx);
      const n = parseNumberOrEmpty(hasLabelCol ? cells[2] : cells[1]);
      if (!isValidBaseParamCode(code)) { errors.push(`${displayRef}: Format parameter tidak sesuai`); return; }
      if (!label) { errors.push(`Baris ${idx + 1}: Label kosong`); return; }
      if (n === '') { errors.push(`Baris ${idx + 1}: Nilai bukan angka`); return; }
      nextVars[code] = roundHalfUp(Number(n), PARAM_STORE_PLACES);
      nextLabels[code] = label;
      hasData = true;
    });
    if (!hasData) throw new Error('csv-empty');
    if (!Object.keys(nextVars).length && !Object.keys(nextComputed).length) throw new Error('csv-none');
    return {
      vars: nextVars,
      labels: nextLabels,
      errors,
      computed: Object.keys(nextComputed).length ? nextComputed : null,
    };
  }

  async function parseXLSXToVarsLabels(file) {
    if (!(window.XLSX && XLSX.read)) throw new Error('no-xlsx-lib');
    const ab = await file.arrayBuffer();
    const wb = XLSX.read(ab);
    const errors = [];
    const nextVars = {}, nextLabels = {}, nextComputed = {};
    const toImportRowRef = (labelValue, codeValue, idx) => {
      const labelText = String(labelValue || '').trim();
      const codeText = normalizeOpaqueCode(codeValue || '');
      if (!labelText) return `Baris ${idx + 1}`;
      if (/^(?:bp|cp)_[1-9][0-9]*$/i.test(labelText)) return `Baris ${idx + 1}`;
      if (codeText && labelText.toLowerCase() === codeText) return `Baris ${idx + 1}`;
      return labelText;
    };

    const baseSheetName = wb.SheetNames[0];
    const baseWs = wb.Sheets[baseSheetName];
    const baseArr = XLSX.utils.sheet_to_json(baseWs, { header: 1 });
    const baseRows = baseArr.filter((r) => r && (r[0] != null || r[1] != null));
    const baseBody = (
      baseRows[0]
      && /kode|code|nama|label/i.test(String(baseRows[0][0] || ''))
      && /nama|label|nilai|value/i.test(String(baseRows[0][1] || ''))
    ) ? baseRows.slice(1) : baseRows;

    baseBody.forEach((r, idx) => {
      const code = normalizeOpaqueCode(r[0] ?? '');
      const hasLabelCol = (r[2] != null);
      const label = String((hasLabelCol ? (r[1] ?? code) : code)).trim();
      const displayRef = toImportRowRef(label, code, idx);
      const n = parseNumberOrEmpty(hasLabelCol ? r[2] : r[1]);
      if (!isValidBaseParamCode(code)) { errors.push(`${displayRef}: Format parameter tidak sesuai`); return; }
      if (!label) { errors.push(`Baris ${idx + 1}: Label kosong`); return; }
      if (n === '') { errors.push(`Baris ${idx + 1}: Nilai bukan angka`); return; }
      nextVars[code] = roundHalfUp(Number(n), PARAM_STORE_PLACES);
      nextLabels[code] = label;
    });

    const computedSheetNames = wb.SheetNames.slice(1);
    let computedBody = null;
    for (const sheetName of computedSheetNames) {
      const ws = wb.Sheets[sheetName];
      const arr = XLSX.utils.sheet_to_json(ws, { header: 1 });
      const rows = arr.filter((r) => r && (r[0] != null || r[1] != null || r[2] != null));
      if (!rows.length) continue;
      const maybeHeader = rows[0];
      const isComputedHeader = (
        /kode|code/i.test(String(maybeHeader[0] || ''))
        && /nama|label/i.test(String(maybeHeader[1] || ''))
        && /formula|expression/i.test(String(maybeHeader[2] || ''))
      );
      if (!isComputedHeader) continue;
      computedBody = rows.slice(1);
      break;
    }

    if (Array.isArray(computedBody)) {
      computedBody.forEach((r, idx) => {
        const code = normalizeOpaqueCode(r[0] ?? '');
        const label = String((r[1] ?? code)).trim();
        const expression = String(r[2] ?? '').trim();
        const unit = String(r[3] ?? '').trim();
        const description = String(r[4] ?? '').trim();
        const displayRef = toImportRowRef(label, code, idx);
        if (!isComputedOpaqueCode(code)) { errors.push(`${displayRef}: Format formula parameter tidak sesuai`); return; }
        if (!label) { errors.push(`Baris ${idx + 1}: Label formula parameter kosong`); return; }
        if (!expression) { errors.push(`Baris ${idx + 1}: Formula kosong`); return; }
        nextComputed[code] = { expression, label, unit, description };
      });
    }

    if (!Object.keys(nextVars).length && !Object.keys(nextComputed).length) throw new Error('xlsx-none');
    return {
      vars: nextVars,
      labels: nextLabels,
      errors,
      computed: Object.keys(nextComputed).length ? nextComputed : null,
    };
  }

  const MAX_IMPORT_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB

  async function handleUnifiedImport(file) {
    if (!file) return;

    // Sprint 2.4: File size limit guard
    if (file.size > MAX_IMPORT_SIZE_BYTES) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
      TOAST.warn(`File terlalu besar (${sizeMB} MB). Maksimal ${MAX_IMPORT_SIZE_BYTES / (1024 * 1024)} MB.`);
      return;
    }

    const name = file.name || '';
    const ext = (/\.(\w+)$/.exec(name)?.[1] || '').toLowerCase();
    try {
      let parsed = { vars: {}, labels: {}, errors: [] };
      if (ext === 'json') {
        const txt = await file.text();
        parsed = parseJSONToVarsLabels(txt);
      } else if (ext === 'csv') {
        const txt = await file.text();
        parsed = parseCSVToVarsLabels(txt);
      } else if (ext === 'xlsx') {
        parsed = await parseXLSXToVarsLabels(file);
      } else {
        throw new Error('format');
      }
      if (parsed.errors && parsed.errors.length) {
        const errText = 'Beberapa baris diabaikan:\n'
          + parsed.errors.slice(0, 10).join('\n')
          + (parsed.errors.length > 10 ? '\n...' : '');
        await alertModal(errText, { title: 'Import Parameter' });
      }
      const nextVars = parsed.vars, nextLabels = parsed.labels;
      const existingCodes = new Set(Object.keys(variables));
      const codes = Object.keys(nextVars);
      const adds = codes.filter(c => !existingCodes.has(c)).length;
      const updates = codes.filter(c => existingCodes.has(c)).length;
      const summary = `Ditemukan ${codes.length} parameter.\nTambah: ${adds}\nPerbarui: ${updates}.\nPilih Merge untuk gabungkan atau Replace untuk mengganti.`;
      const doMerge = await confirmModal(summary, {
        title: 'Konfirmasi Import',
        confirmText: 'Merge',
        cancelText: 'Replace',
      });
      // Sprint 3.2: snapshot for undo
      const prevVars = { ...variables };
      const prevLabels = { ...varLabels };
      const prevComputed = { ...computedParams };

      if (doMerge) {
        variables = { ...variables, ...nextVars };
        varLabels = { ...varLabels, ...nextLabels };
      } else {
        variables = { ...nextVars };
        varLabels = { ...nextLabels };
      }

      // Sprint 3.3: apply imported computed parameters (JSON/CSV/XLSX when available)
      let cpCount = 0;
      if (parsed.computed && typeof parsed.computed === 'object') {
        Object.keys(parsed.computed).forEach(code => {
          const safe = normalizeOpaqueCode(code);
          if (!isComputedOpaqueCode(safe)) return;
          const src = parsed.computed[code] || {};
          computedParams[safe] = {
            expression: String(src.expression || ''),
            label: String(src.label || safe),
            unit: String(src.unit || ''),
            description: String(src.description || ''),
          };
          cpCount++;
        });
        if (cpCount) {
          try { localStorage.setItem(storageKeyComputed(), JSON.stringify(computedParams)); } catch { }
        }
      }

      saveVars(); saveVarLabels(); renderVarTable(); reevaluateAllFormulas();

      // Sprint 3.2: show toast with Undo button
      const msg = cpCount
        ? `Parameter diimport (${Object.keys(nextVars).length} base + ${cpCount} computed).`
        : 'Parameter diimport.';
      TOAST.action(msg, [{
        label: 'Undo',
        class: 'btn-outline-warning',
        onClick: () => {
          variables = prevVars;
          varLabels = prevLabels;
          computedParams = prevComputed;
          saveVars(); saveVarLabels();
          try { localStorage.setItem(storageKeyComputed(), JSON.stringify(computedParams)); } catch { }
          renderVarTable(); reevaluateAllFormulas();
          TOAST.ok('Import dibatalkan (Undo).');
        },
      }]);
    } catch (e) {
      if (String(e.message).includes('no-xlsx-lib')) {
        TOAST.warn('Import XLSX butuh SheetJS (window.XLSX). Gunakan CSV/JSON.');
      } else if (String(e.message).includes('format')) {
        TOAST.err('Format file tidak dikenali.');
      } else {
        TOAST.err('Gagal import.');
      }
    }
  }

  // Hook tombol Import/Export lama -> Unified
  (function installUnifiedIO() {
    ensureFileInputs();
    const btnImport = document.getElementById('vp-var-import-btn');
    const fileInput = document.getElementById('vp-var-import');
    const btnExport = document.getElementById('vp-var-export-btn');

    if (btnImport && fileInput && !btnImport.dataset.boundUnified) {
      btnImport.addEventListener('click', () => fileInput.click());
      fileInput.addEventListener('change', (e) => {
        const f = e.target.files && e.target.files[0];
        try { handleUnifiedImport(f); }
        finally { fileInput.value = ''; }
      });
      btnImport.dataset.boundUnified = '1';
      btnImport.setAttribute('title', 'Import JSON/CSV/XLSX');
    }

    if (btnExport && !btnExport.dataset.boundUnified) {
      const bind = (id, fn) => { const el = document.getElementById(id); if (el) el.addEventListener('click', fn); };
      bind('vp-export-json', exportAsJSON);
      bind('vp-export-csv', exportAsCSV);
      bind('vp-export-xlsx', exportAsXLSX);
      bind('vp-export-copy-json', copyJSONToClipboard);
      btnExport.dataset.boundUnified = '1';
      btnExport.setAttribute('title', 'Export JSON/CSV/XLSX');
    }
  })();

  // Generate XLSX template (no static file needed)
  (function installTemplateGen() {
    const btn = document.getElementById('vp-template-xlsx-gen');
    if (!btn) return;
    btn.addEventListener('click', () => {
      if (!(window.XLSX && XLSX.utils && XLSX.writeFile)) { TOAST.warn('Butuh SheetJS untuk XLSX'); return; }
      const rows = [
        { Kode: 'bp_1', Nama: 'Panjang', Nilai: 0 },
        { Kode: 'bp_2', Nama: 'Lebar', Nilai: 0 },
        { Kode: 'bp_3', Nama: 'Tinggi', Nilai: 0 },
      ];
      const ws = XLSX.utils.json_to_sheet(rows, { header: ['Kode', 'Nama', 'Nilai'] });
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Parameter');
      XLSX.writeFile(wb, 'parameters_template.xlsx');
    });
  })();

  // ===== Build table dari tree
  async function enhanceWithGroups() {
    try {
      // Jika SSR sudah menyediakan baris pekerjaan, tidak perlu rebuild via API
      if (document.querySelector('tr[data-pekerjaan-id]')) {
        rows = Array.from(document.querySelectorAll('tr[data-pekerjaan-id]'));
        applyQtyColWidth(qtyColWidthCh, { persist: false });
        buildSearchIndex();
        // applyCollapseOnTable aman dipanggil; akan no-op jika tidak ada baris .vp-klass/.vp-sub
        applyCollapseOnTable();
        return;
      }
      const resp = await HTTP.jget(EP_TREE);
      if (!resp || !Array.isArray(resp.klasifikasi)) return;

      const tbody = document.querySelector('#vp-table tbody');
      tbody.innerHTML = '';
      rows.length = 0;

      let counter = 0;
      resp.klasifikasi.forEach(k => {
        const kKey = String(k.id ?? slugKey(k.name));
        const trK = document.createElement('tr');
        trK.className = 'vp-klass';
        trK.setAttribute('data-klas-id', kKey);
        trK.innerHTML = `
          <td colspan="5">
            <button type="button" class="btn btn-link btn-sm vp-toggle" data-type="klas" data-key="${escapeHtml(kKey)}" aria-expanded="${!collapsed.klas[kKey]}">
              <i class="bi ${collapsed.klas[kKey] ? 'bi-caret-right-fill' : 'bi-caret-down-fill'}"></i>
            </button>
            <strong>${escapeHtml(k.name || '(Tanpa Klasifikasi)')}</strong>
          </td>`;
        tbody.appendChild(trK);

        (k.sub || []).forEach(s => {
          const sKey = String(s.id ?? (kKey + ':' + slugKey(s.name)));
          const trS = document.createElement('tr');
          trS.className = 'vp-sub';
          trS.setAttribute('data-sub-id', sKey);
          trS.setAttribute('data-klas-id', kKey);
          trS.innerHTML = `
            <td colspan="5">
              <button type="button" class="btn btn-link btn-sm vp-toggle" data-type="sub" data-key="${escapeHtml(sKey)}" aria-expanded="${!(collapsed.sub[sKey] || collapsed.klas[kKey])}">
                <i class="bi ${(collapsed.sub[sKey] || collapsed.klas[kKey]) ? 'bi-caret-right-fill' : 'bi-caret-down-fill'}"></i>
              </button>
              ${escapeHtml(s.name || '(Tanpa Sub)')}
            </td>`;
          tbody.appendChild(trS);

          (s.pekerjaan || []).forEach(p => {
            counter += 1;
            const tr = document.createElement('tr');
            tr.dataset.pekerjaanId = p.id;
            tr.setAttribute('data-klas-id', kKey);
            tr.setAttribute('data-sub-id', sKey);
            tr.innerHTML = `
              <td>${counter}</td>
              <td class="text-monospace ux-mono">${escapeHtml(p.snapshot_kode || '')}</td>
              <td class="text-wrap">${escapeHtml(p.snapshot_uraian || '')}</td>
              <td>${escapeHtml(p.snapshot_satuan || '-')}</td>
              <td>
                <div class="d-flex align-items-start gap-2 vp-cell">
                  <button type="button" class="btn btn-outline-secondary btn-sm fx-editor-open"
                          title="Buka editor formula (Alt+Enter)"
                          aria-label="Buka editor formula"><i class="bi bi-arrows-angle-expand"></i></button>
                  <div class="flex-grow-1">
                    <input type="text" inputmode="decimal" class="form-control form-control-sm qty-input"
                      aria-label="Quantity. Ketik = untuk formula. Ctrl+Space untuk autosuggestion."
                      title="Ketik angka, atau awali dengan = untuk formula. Ctrl+Space menampilkan autosuggestion.">
                    <div class="form-text fx-preview small d-none" data-preview-state="empty" style="min-height:1rem;">
                      <div class="fx-preview-label-line">
                        <span class="fx-preview-caption">Preview Label:</span>
                        <span class="fx-preview-label-text">-</span>
                      </div>
                      <div class="fx-preview-value-line">
                        <span class="fx-preview-caption">Preview Nilai:</span>
                        <span class="fx-preview-value-text">-</span>
                      </div>
                      <div class="fx-preview-error-line d-none"></div>
                    </div>
                  </div>
                </div>
              </td>`;
            tbody.appendChild(tr);
            rows.push(tr);
            bindRow(tr);
          });
        });
      });

      buildSearchIndex();
      applyQtyColWidth(qtyColWidthCh, { persist: false });
      applyCollapseOnTable();
      applyCollapseOnCards();
    } catch (e) {
      console.warn('enhanceWithGroups() gagal', e);
    }
  }

  // ===== Prefill: rekap volume + (opsional) server formula state
  (async function prefill() {
    try {
      // 1) Prefill volume: coba dari volume list (paling tepat), fallback ke rekap
      const volMap = {};
      const volHasMap = {};
      const volUpdatedMap = {};
      try {
        // PERF: pakai bootstrap SSR jika tersedia agar tidak round-trip saat buka halaman.
        const vlist = VP_BOOTSTRAP?.volume_list
          || await HTTP.jget(`/detail_project/api/project/${projectId}/volume-pekerjaan/list/`);
        if (vlist && Array.isArray(vlist.items)) {
          vlist.items.forEach(it => {
            const id = Number(it.pekerjaan_id);
            const v = N ? Number(N.canonicalizeForAPI(it.quantity ?? '0'))
              : Number(String(it.quantity || '0').replace(',', '.'));
            if (Number.isFinite(id) && Number.isFinite(v)) {
              volMap[id] = v;
              volHasMap[id] = it.has_quantity === true;
              volUpdatedMap[id] = String(it.updated_at || '').trim();
            }
          });
        }
      } catch { }
      if (Object.keys(volMap).length === 0) {
        const rekap = await HTTP.jget(`/detail_project/api/project/${projectId}/rekap/`).catch(() => ({}));
        if (rekap && Array.isArray(rekap.rows)) {
          rekap.rows.forEach(r => {
            if (r && typeof r.pekerjaan_id === 'number') {
              const v = N ? Number(N.canonicalizeForAPI(r.volume ?? 0))
                : Number(r.volume || 0);
              volMap[r.pekerjaan_id] = Number.isFinite(v) ? v : 0;
              volHasMap[r.pekerjaan_id] = true;
              volUpdatedMap[r.pekerjaan_id] = String(r.updated_at || '').trim();
            }
          });
        }
      }
      // 2) Pastikan baris ada: pakai SSR jika tersedia; jika tidak -> fallback ke EP_TREE
      if (!document.querySelector('tr[data-pekerjaan-id]')) {
        await enhanceWithGroups();
      }
      rows = Array.from(document.querySelectorAll('tr[data-pekerjaan-id]'));
      rows.forEach(tr => bindRow(tr));

      // 3) Ambil formula state dari server; kalau error -> pakai localStorage
      let serverFormula = null;
      try {
        // PERF: pakai bootstrap SSR jika tersedia agar tidak round-trip saat buka halaman.
        const resp = VP_BOOTSTRAP?.formula_state || await HTTP.jget(EP_FORMULA_STATE);
        if (resp && resp.ok && Array.isArray(resp.items)) {
          if (resp.synced_at) setFormulaSyncAt(String(resp.synced_at));
          serverFormula = {};
          resp.items.forEach(it => {
            serverFormula[it.pekerjaan_id] = {
              raw: it.raw || '',
              fx: !!it.is_fx,
              updated_at: String(it.updated_at || '').trim() || null,
            };
          });
        }
      } catch { }
      const localFormula = loadFormulas();
      if (formulaLocalDirty) {
        Object.keys(localFormula).forEach((id) => {
          const parsedId = Number(id);
          if (Number.isFinite(parsedId)) formulaDirtySet.add(parsedId);
        });
        if (formulaDirtySet.size) showFormulaSyncStatus('pending');
        else clearFormulaLocalDirty();
      }
      const formulaState = resolveFormulaStateSnapshot(serverFormula, localFormula);

      // 4) Render nilai & formula preview
      rows.forEach(tr => {
        const id = parseInt(tr.dataset.pekerjaanId, 10);
        const input = tr.querySelector('.qty-input');
        const preview = tr.querySelector('.fx-preview');
        const base = Number(volMap[id] || 0);
        const hasStoredVolume = volHasMap[id] === true || base !== 0;

        originalValueById[id] = roundHalfUp(base, STORE_PLACES);
        currentValueById[id] = originalValueById[id];

        input.value = hasStoredVolume ? formatIdSmart(base) : '';
        input.classList.toggle('vp-empty', !input.value.trim());
        // Sync row markers for numeric (non-formula) rows after prefill
        tr.classList.toggle('vp-row-empty', !input.value.trim());
        tr.classList.toggle('vp-row-zero', (!!input.value.trim() && Number(base) === 0));
        tr.classList.remove('vp-row-invalid');

        const f = formulaState[id];
        if (f && hasFormulaStateValue(f)) {
          knownFormulaStateIds.add(id);
        }
        if (f && typeof f.raw === 'string' && f.raw.trim() && isFormulaStateFreshForVolume(f, volUpdatedMap[id], hasStoredVolume)) {
          input.value = f.raw;
          fxModeById[id] = !!f.fx;
          handleInputChange(id, input, preview, false);
        } else if (f && hasFormulaStateValue(f)) {
          forgetLocalFormulaState(id);
        }
        setRowDirtyVisual(id, false);
        if (!tr.classList.contains('vp-row-invalid')) {
          setInputValidationError(id, '');
        }
      });

      setBtnSaveEnabled();
      buildSearchIndex();
      // Terapkan state collapse untuk kedua mode (row/card)
      applyCollapseOnTable();
      applyCollapseOnCards();
      syncSummaryBarWithCurrentFilter();
      if (formulaDirtySet.size) scheduleFormulaServerSync();
      checkFormulaRemoteChanges();
    } catch (e) {
      console.warn('Prefill rekap gagal', e);
      await enhanceWithGroups();
      rows.forEach(tr => {
        const id = parseInt(tr.dataset.pekerjaanId, 10);
        originalValueById[id] = 0;
        currentValueById[id] = 0;
        setRowDirtyVisual(id, false);
        setInputValidationError(id, '');
      });
      setBtnSaveEnabled();
      syncSummaryBarWithCurrentFilter();
    }
  })();

  // ===== Autosave + Undo =====
  function scheduleAutosave(ms = AUTOSAVE_MS) {
    if (autosaveTimer) clearTimeout(autosaveTimer);
    if (dirtySet.size === 0) return;
    autosaveTimer = setTimeout(() => {
      if (formulaEditorContext) {
        scheduleAutosave(Math.max(1000, Number(ms) || AUTOSAVE_MS));
        return;
      }
      if (saving) {
        saveRetryRequested = true;
        scheduleAutosave(700);
        return;
      }
      const elapsedFromLastTyping = Date.now() - Number(lastQtyInputAt || 0);
      const activeEl = document.activeElement;
      const activeIsQtyInput = !!(activeEl && activeEl.classList && activeEl.classList.contains('qty-input'));
      if (activeIsQtyInput && elapsedFromLastTyping < AUTOSAVE_TYPING_GRACE_MS) {
        const nextDelay = Math.max(350, AUTOSAVE_TYPING_GRACE_MS - elapsedFromLastTyping + 200);
        scheduleAutosave(nextDelay);
        return;
      }
      if (dirtySet.size > 0) saveDirty({ reason: 'autosave' });
    }, ms);
  }

  async function saveDirty({ reason = 'manual' } = {}) {
    if (saving) {
      saveRetryRequested = true;
      if (reason === 'manual') {
        setSaveStatus('Sedang menyimpan. Perubahan terbaru akan disimpan otomatis setelah proses selesai.', 'warning');
      }
      return;
    }
    if (reason !== 'manual' && formulaEditorContext) return;
    if (formulaEditorHasBlockingError) {
      const msg = formulaEditorBlockingMessage || 'Simpan diblokir: editor formula masih memiliki token invalid.';
      if (reason === 'manual') TOAST.warn(msg);
      setSaveStatus(msg, 'warning');
      return;
    }
    flushPendingQtyInputs();
    const postingIds = Array.from(dirtySet.values());
    const pendingFormulaIds = Array.from(formulaDirtySet.values());
    const hasVolumeChanges = postingIds.length > 0;
    if (!hasVolumeChanges && !pendingFormulaIds.length) return;

    const precheckIds = Array.from(new Set([...postingIds, ...pendingFormulaIds]));
    collectFormulaSyncValidationIssues(precheckIds);

    // Hard block: ada token/input invalid yang belum dibersihkan.
    const blockingIssues = getSortedInputValidationIssues();
    if (blockingIssues.length) {
      const first = blockingIssues[0];
      const tr = rows.find((r) => parseInt(r.dataset.pekerjaanId, 10) === first.id);
      const input = tr?.querySelector('.qty-input');
      if (input) {
        input.classList.add('is-invalid');
        input.setAttribute('title', first.message);
        if (reason === 'manual') {
          suppressFormulaInputFocusOpen = true;
          input.focus();
          setTimeout(() => { suppressFormulaInputFocusOpen = false; }, 0);
        }
      }
      if (reason === 'manual') {
        TOAST.warn(`Simpan diblokir: baris #${first.id} masih invalid. Hapus token yang tidak termuat atau pilih dari autosuggestion.`);
        setSaveStatus(`Simpan diblokir: baris #${first.id} masih invalid.`, 'warning');
      } else {
        setSaveStatus(`Autosave ditunda: baris #${first.id} masih invalid.`, 'warning');
      }
      return;
    }

    const changes = postingIds.map(id => ({
      id,
      before: Number(originalValueById[id] ?? 0),
      after: Number(currentValueById[id] ?? 0)
    }));

    const items = changes.map(({ id, after }) => {
      let q = after;
      if (!Number.isFinite(q)) q = 0;
      const rounded = roundHalfUp(q, STORE_PLACES);
      return { pekerjaan_id: id, quantity: rounded };
    });
    const sentQuantityById = {};
    items.forEach((it) => {
      const sentId = Number(it.pekerjaan_id);
      const sentQty = Number(it.quantity);
      if (Number.isFinite(sentId) && Number.isFinite(sentQty)) {
        sentQuantityById[sentId] = roundHalfUp(sentQty, STORE_PLACES);
      }
    });

    saving = true;
    if (reason === 'manual' && btnSaveSpin) btnSaveSpin.hidden = false;
    if (reason === 'manual') {
      if (btnSave) btnSave.disabled = true;
      if (btnSaveTop) btnSaveTop.disabled = true;
    }

    try {
      const markErrors = (json) => {
        if (!json || !Array.isArray(json.errors)) return;
        const re = /items\[(\d+)\]\.(quantity|pekerjaan_id)/;
        json.errors.forEach(e => {
          const m = e && e.path ? re.exec(e.path) : null;
          if (!m) return;
          const idx = parseInt(m[1], 10);
          const id = postingIds[idx];
          const tr = rows.find(r => parseInt(r.dataset.pekerjaanId, 10) === id);
          const input = tr?.querySelector('.qty-input');
          if (input) { input.classList.add('is-invalid'); if (e.message) input.setAttribute('title', e.message); }
        });
      };

      let json = {};
      let savedIdSet = new Set();
      if (hasVolumeChanges) {
        const res = await HTTP.jpost(EP_SAVE, { items });
        json = res?.data || {};
        const errCount = Array.isArray(json.errors) ? json.errors.length : 0;
        // FIX(#A): tentukan baris yang BENAR-BENAR tersimpan dari server.
        // Hanya baris ini yang boleh di-commit; sisanya tetap dirty (input dipertahankan).
        // Penting: partial-save kini balas 207 (res.ok tetap true), jadi kita TIDAK boleh
        // mengandalkan res.ok saja — selalu cek json.errors & saved_job_ids.
        if (Array.isArray(json.saved_job_ids)) {
          savedIdSet = new Set(json.saved_job_ids.map(Number));
        } else if (res.ok && errCount === 0) {
          savedIdSet = new Set(postingIds.map(Number));
        }
        if (!res.ok || errCount > 0) {
          markErrors(json);
          const savedCount = savedIdSet.size;
          const failedCount = postingIds.length - savedCount;
          const msg = `${failedCount} baris gagal disimpan — input dipertahankan. Tersimpan: ${savedCount}.`;
          TOAST.err(msg);
          setSaveStatus(msg, 'danger');
        }
      }
      const volumeSaved = savedIdSet.size > 0;

      if (formulaSyncTimer) {
        clearTimeout(formulaSyncTimer);
        formulaSyncTimer = null;
      }
      const formulaResult = formulaDirtySet.size
        ? await syncFormulaStateToServer(null, { reason })
        : { ok: true, skipped: true, synced: 0 };

      if (!hasVolumeChanges) {
        if (formulaResult.ok && formulaResult.synced > 0) {
          setSaveStatus(`Formula tersimpan (${formulaResult.synced}).`, 'success');
          if (reason === 'manual') TOAST.ok(`Formula tersimpan (${formulaResult.synced}).`);
        } else if (!formulaResult.ok && reason === 'manual') {
          setSaveStatus('Sinkron formula gagal.', 'danger');
        }
        return;
      }

      if (!volumeSaved) {
        if (formulaResult.ok && formulaResult.synced > 0) {
          TOAST.warn(`Formula tersimpan (${formulaResult.synced}), tetapi volume belum tersimpan.`);
        }
        return;
      }

      // OK - commit baseline & visuals
      let pendingAfterSaveCount = 0;
      postingIds.forEach(id => {
        // FIX(#A): baris yang TIDAK ada di saved_job_ids = gagal/ditolak server.
        // Jangan sentuh baseline & jangan hapus dirty → input dipertahankan, tombol Simpan
        // tetap aktif, dan beforeunload tetap memperingatkan. User perbaiki lalu simpan ulang.
        if (!savedIdSet.has(Number(id))) {
          return;
        }
        const sentQty = Number(sentQuantityById[id]);
        if (Number.isFinite(sentQty)) originalValueById[id] = roundHalfUp(sentQty, STORE_PLACES);
        else originalValueById[id] = currentValueById[id] ?? 0;
        updateDirty(id);
        const stillDirty = dirtySet.has(id);
        const tr = rows.find(r => parseInt(r.dataset.pekerjaanId, 10) === id);
        if (stillDirty) {
          pendingAfterSaveCount += 1;
          return;
        }
        if (tr) {
          const input = tr.querySelector('.qty-input');
          if (input) {
            input.classList.remove('is-invalid');
            input.classList.add('is-valid');
            setTimeout(() => input.classList.remove('is-valid'), 900);
          }
          // Clear invalid/empty and saved pulse; zero is allowed
          tr.classList.remove('vp-row-invalid', 'vp-row-empty', 'vp-row-zero');
          markRowSaved(tr);
        }
        setRowDirtyVisual(id, false);
      });
      setBtnSaveEnabled();
      resolveVolumeJobs(postingIds);
      acknowledgeGlobalSyncLed({ volume: true });
      if (pendingAfterSaveCount > 0) scheduleAutosave(700);

      const realChanges = changes.filter(c => savedIdSet.has(Number(c.id)) && roundHalfUp(c.before, STORE_PLACES) !== roundHalfUp(c.after, STORE_PLACES));
      if (pendingAfterSaveCount > 0) {
        if (!formulaResult.ok && pendingFormulaIds.length) {
          setSaveStatus(`Tersimpan ${realChanges.length} item. ${pendingAfterSaveCount} perubahan terbaru masih pending dan formula belum tersinkron.`, 'warning');
        } else {
          setSaveStatus(`Tersimpan ${realChanges.length} item. ${pendingAfterSaveCount} perubahan terbaru masih pending autosave.`, 'warning');
        }
      } else if (!formulaResult.ok && pendingFormulaIds.length) {
        setSaveStatus(`Volume tersimpan ${realChanges.length} item, formula belum tersinkron.`, 'warning');
      } else {
        setSaveStatus(`Tersimpan ${realChanges.length} item.`, 'success');
      }

      if (realChanges.length) {
        undoStack.push({ ts: Date.now(), changes: realChanges });
        if (undoStack.length > UNDO_MAX) undoStack.shift();
        TOAST.action(`Tersimpan ${realChanges.length} item.`, [
          { label: 'Undo', class: 'btn-warning', onClick: tryUndoLast }
        ]);
        if (!formulaResult.ok && pendingFormulaIds.length) {
          TOAST.warn('Volume tersimpan, tetapi sinkron formula gagal.');
        }
      } else if (reason === 'manual') {
        if (!formulaResult.ok && pendingFormulaIds.length) {
          TOAST.warn('Volume tidak berubah, dan sinkron formula gagal.');
          setSaveStatus('Volume tidak berubah, sinkron formula gagal.', 'danger');
        } else if (formulaResult.synced > 0) {
          TOAST.ok(`Formula tersimpan (${formulaResult.synced}).`);
        } else {
          TOAST.warn('Tidak ada perubahan.');
          setSaveStatus('Tidak ada perubahan.', 'warning');
        }
      }

      if (typeof json.decimal_places === 'number' && json.decimal_places !== STORE_PLACES) {
        console.info('Server decimal_places =', json.decimal_places);
      }
    } catch (e) {
      console.error(e);
      TOAST.err('Gagal simpan (network/server error).');
      setSaveStatus('Gagal simpan (network/server error).', 'danger');
    } finally {
      if (reason === 'manual' && btnSaveSpin) btnSaveSpin.hidden = true;
      if (reason === 'manual') {
        if (btnSave) btnSave.disabled = false;
        if (btnSaveTop) btnSaveTop.disabled = false;
      }
      saving = false;
      if (saveRetryRequested) {
        saveRetryRequested = false;
        scheduleAutosave(450);
      }
    }
  }

  async function tryUndoLast() {
    const last = undoStack.pop();
    if (!last || !last.changes || !last.changes.length) { showToast('Tidak ada yang bisa di-undo.', 'warning'); return; }

    // Apply "before" ke state & UI lalu kirim simpan
    last.changes.forEach(({ id, before }) => {
      currentValueById[id] = roundHalfUp(Number(before), STORE_PLACES);
      const tr = rows.find(r => parseInt(r.dataset.pekerjaanId, 10) === id);
      const input = tr?.querySelector('.qty-input');
      const preview = tr?.querySelector('.fx-preview');
      if (input) {
        input.value = formatIdSmart(currentValueById[id]);
        input.classList.add('is-valid'); setTimeout(() => input.classList.remove('is-valid'), 700);
        input.classList.toggle('vp-empty', !String(input.value || '').trim());
      }
      if (preview) setDualPreviewState(preview, 'empty', { forceVisible: false });
      updateDirty(id);
    });
    await saveDirty({ reason: 'manual' });
  }

  // Save manual (dua tombol: toolbar atas dan footer bawah)
  btnSave && btnSave.addEventListener('click', () => saveDirty({ reason: 'manual' }));
  btnSaveTop && btnSaveTop.addEventListener('click', () => saveDirty({ reason: 'manual' }));

  // Undo hotkey global: Ctrl+Alt+Z
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.altKey && e.key.toLowerCase() === 'z') {
      e.preventDefault(); tryUndoLast();
    }
  });

  function doSafeReload() {
    allowUnload = true;
    window.location.reload();
  }

  async function confirmReload(reason) {
    flushPendingQtyInputs();
    if (!window.__vpDirty) {
      doSafeReload();
      return true;
    }
    const modalApi = getModalApi();
    if (!modalApi || !modalApi.confirm) return false;
    const message = reason
      ? `${reason}\n\nPerubahan volume/formula yang belum disimpan akan hilang jika Anda melanjutkan.`
      : 'Perubahan volume/formula yang belum disimpan akan hilang jika Anda melanjutkan reload halaman.';
    const ok = await modalApi.confirm(message, {
      title: 'Konfirmasi Reload',
      confirmText: 'Reload',
      cancelText: 'Batal',
      confirmClass: 'btn btn-danger',
    });
    if (ok) {
      doSafeReload();
    }
    return ok;
  }

  // Guard before unload
  window.addEventListener('beforeunload', (e) => {
    flushPendingQtyInputs();
    if (window.__vpDirty && !allowUnload) { e.preventDefault(); e.returnValue = ''; return ''; }
  });

  window.addEventListener('keydown', (e) => {
    flushPendingQtyInputs();
    if (!window.__vpDirty) return;
    const key = String(e.key || '').toLowerCase();
    const isReload = e.key === 'F5' || ((e.ctrlKey || e.metaKey) && key === 'r');
    if (!isReload) return;
    const modalApi = getModalApi();
    if (!modalApi || !modalApi.confirm) return;
    e.preventDefault();
    confirmReload('Anda akan memuat ulang halaman.');
  });

  // ===== Storage helpers
  function storageKeyVars() { return `volvars:${projectId}`; }
  function storageKeyVarLabels() { return `volvars_labels:${projectId}`; }
  function storageKeyComputed() { return `volcparams:${projectId}`; }
  function storageKeyForms() { return `volform:${projectId}`; }
  function storageKeyBaseSyncAt() { return `volvars_sync_at:${projectId}`; }
  function storageKeyComputedSyncAt() { return `volcparams_sync_at:${projectId}`; }
  function storageKeyFormulaSyncAt() { return `volform_sync_at:${projectId}`; }
  function storageKeyFormulaDrafts() { return `volform_draft:${projectId}`; }
  function storageKeyBaseDirtyFlag() { return `volvars_dirty:${projectId}`; }
  function storageKeyComputedDirtyFlag() { return `volcparams_dirty:${projectId}`; }
  function storageKeyFormulaDirtyFlag() { return `volform_dirty:${projectId}`; }
  function storageKeyFormulaPreviewMode() { return `vp_formula_preview_mode:${projectId}`; }
  function storageKeyFormulaInlineValueMode() { return `vp_formula_inline_values:${projectId}`; }
  function storageKeyOpaqueMigrationFlag() { return `opaque_migrated:${projectId}:v2`; }

  // API endpoints for parameter sync
  const EP_PARAMS = `/detail_project/api/project/${projectId}/parameters/`;
  const EP_PARAMS_SYNC = `/detail_project/api/project/${projectId}/parameters/sync/`;
  const EP_CPARAMS = `/detail_project/api/project/${projectId}/computed-parameters/`;
  const EP_CPARAMS_SYNC = `/detail_project/api/project/${projectId}/computed-parameters/sync/`;

  // Debounce timer for server sync
  let paramSyncTimer = null;
  let computedSyncTimer = null;
  const PARAM_SYNC_DELAY = 2000; // 2 seconds debounce
  let syncConflictPromptOpen = false;
  let baseParamSyncAt = null;
  let computedParamSyncAt = null;

  function setBaseParamSyncAt(ts) {
    const value = String(ts || '').trim();
    if (!value) return;
    baseParamSyncAt = value;
    localStorage.setItem(storageKeyBaseSyncAt(), value);
  }

  function setComputedParamSyncAt(ts) {
    const value = String(ts || '').trim();
    if (!value) return;
    computedParamSyncAt = value;
    localStorage.setItem(storageKeyComputedSyncAt(), value);
  }

  function loadSyncMarkers() {
    try { baseParamSyncAt = localStorage.getItem(storageKeyBaseSyncAt()); } catch { baseParamSyncAt = null; }
    try { computedParamSyncAt = localStorage.getItem(storageKeyComputedSyncAt()); } catch { computedParamSyncAt = null; }
    try { formulaSyncAt = localStorage.getItem(storageKeyFormulaSyncAt()); } catch { formulaSyncAt = null; }
    try { baseParamsLocalDirty = localStorage.getItem(storageKeyBaseDirtyFlag()) === '1'; } catch { baseParamsLocalDirty = false; }
    try { computedParamsLocalDirty = localStorage.getItem(storageKeyComputedDirtyFlag()) === '1'; } catch { computedParamsLocalDirty = false; }
    try { formulaLocalDirty = localStorage.getItem(storageKeyFormulaDirtyFlag()) === '1'; } catch { formulaLocalDirty = false; }
  }

  function markBaseParamsDirty() {
    baseParamsLocalDirty = true;
    try { localStorage.setItem(storageKeyBaseDirtyFlag(), '1'); } catch { }
  }

  function clearBaseParamsDirty() {
    baseParamsLocalDirty = false;
    try { localStorage.removeItem(storageKeyBaseDirtyFlag()); } catch { }
  }

  function markComputedParamsDirty() {
    computedParamsLocalDirty = true;
    try { localStorage.setItem(storageKeyComputedDirtyFlag(), '1'); } catch { }
  }

  function clearComputedParamsDirty() {
    computedParamsLocalDirty = false;
    try { localStorage.removeItem(storageKeyComputedDirtyFlag()); } catch { }
  }

  function shouldProtectLocalBaseState() {
    return baseParamsLocalDirty || !!paramSyncTimer;
  }

  function shouldProtectLocalComputedState() {
    return computedParamsLocalDirty || !!computedSyncTimer;
  }

  function loadVars() {
    try {
      const raw = localStorage.getItem(storageKeyVars());
      variables = raw ? JSON.parse(raw) : {};
      if (typeof variables !== 'object' || !variables) variables = {};
      const normalized = {};
      Object.keys(variables).forEach((code) => {
        const safe = normalizeOpaqueCode(code);
        if (!isValidBaseParamCode(safe)) return;
        normalized[safe] = Number(variables[code]) || 0;
      });
      variables = normalized;
    } catch { variables = {}; }
  }

  function saveVars() {
    // Save to localStorage immediately
    localStorage.setItem(storageKeyVars(), JSON.stringify(variables));
    markBaseParamsDirty();
    // Debounced sync to server
    scheduleServerSync();
    evaluateComputedParams();
    renderComputedTable();
    reevaluateAllFormulas();
    refreshUsageBadges();
  }

  function loadVarLabels() {
    try {
      const raw = localStorage.getItem(storageKeyVarLabels());
      varLabels = raw ? JSON.parse(raw) : {};
      if (!varLabels || typeof varLabels !== 'object') varLabels = {};
      const normalized = {};
      Object.keys(varLabels).forEach((code) => {
        const safe = normalizeOpaqueCode(code);
        if (!isValidBaseParamCode(safe)) return;
        normalized[safe] = String(varLabels[code] || safe).trim() || safe;
      });
      varLabels = normalized;
    } catch { varLabels = {}; }
  }

  function saveVarLabels() {
    // Save to localStorage immediately
    localStorage.setItem(storageKeyVarLabels(), JSON.stringify(varLabels));
    markBaseParamsDirty();
    // Debounced sync to server
    scheduleServerSync();
    renderComputedTable();
  }

  function loadComputedParams() {
    try {
      const raw = localStorage.getItem(storageKeyComputed());
      const parsed = raw ? JSON.parse(raw) : {};
      computedParams = normalizeComputedParamsShape(parsed);
    } catch {
      computedParams = {};
    }
    dropComputedNameConflicts();
    evaluateComputedParams();
  }

  function saveComputedParams() {
    dropComputedNameConflicts();
    localStorage.setItem(storageKeyComputed(), JSON.stringify(computedParams));
    markComputedParamsDirty();
    scheduleComputedServerSync();
    evaluateComputedParams();
    renderComputedTable();
    reevaluateAllFormulas();
    refreshUsageBadges();
  }

  // Schedule a debounced sync to server
  function scheduleServerSync() {
    if (paramSyncTimer) clearTimeout(paramSyncTimer);
    showParamSyncStatus('pending');
    paramSyncTimer = setTimeout(() => {
      syncParamsToServer();
    }, PARAM_SYNC_DELAY);
  }

  function scheduleComputedServerSync() {
    if (computedSyncTimer) clearTimeout(computedSyncTimer);
    showParamSyncStatus('pending');
    computedSyncTimer = setTimeout(() => {
      syncComputedParamsToServer();
    }, PARAM_SYNC_DELAY);
  }
  async function promptSyncConflict(kind, serverUpdatedAt) {
    if (syncConflictPromptOpen) return;
    syncConflictPromptOpen = true;
    try {
      const kindLabel = kind === 'computed'
        ? 'formula turunan'
        : (kind === 'formula' ? 'formula volume' : 'parameter');
      const tsInfo = serverUpdatedAt ? `\nWaktu update server: ${serverUpdatedAt}` : '';
      const ok = await confirmModal(
        `Terdeteksi konflik sinkronisasi ${kindLabel} (data di server lebih baru).${tsInfo}\n\nReload data dari server sekarang?`,
        {
          title: 'Konflik Sinkronisasi',
          confirmText: 'Reload',
          cancelText: 'Tetap Lokal',
          confirmClass: 'btn btn-warning',
        }
      );
      if (ok) {
        window.location.reload();
        return;
      }
      TOAST.warn('Perubahan lokal dipertahankan sementara. Lakukan sinkronisasi ulang setelah review.');
    } finally {
      syncConflictPromptOpen = false;
    }
  }

  function summarizeSyncWarnings(warnings) {
    if (!Array.isArray(warnings) || !warnings.length) return '';
    return warnings.slice(0, 3).map((w, idx) => {
      const warningIndex = Number(w?.index);
      if (Number.isInteger(warningIndex) && warningIndex >= 0) return `item #${warningIndex + 1}`;
      return `item #${idx + 1}`;
    }).join(', ');
  }

  // Sync current parameters to server
  async function syncParamsToServer() {
    try {
      // Build parameters object with values and labels
      const params = {};
      for (const code of Object.keys(variables)) {
        params[code] = {
          value: variables[code],
          label: varLabels[code] || code,
        };
      }

      const res = await HTTP.jpost(EP_PARAMS_SYNC, {
        parameters: params,
        mode: 'replace',
        last_sync_at: baseParamSyncAt || null,
      });

      if (res.status === 409 || res.data?.error === 'conflict') {
        showParamSyncStatus('error');
        await promptSyncConflict('base', res.data?.server_updated_at || '');
        return;
      }

      if (res.ok && res.data?.ok) {
        console.log('[VP] Params synced to server:', {
          created: Number(res.data?.created || 0),
          updated: Number(res.data?.updated || 0),
          deleted: Number(res.data?.deleted || 0),
          warnings: Array.isArray(res.data?.warnings) ? res.data.warnings.length : 0,
        });
        if (res.data?.synced_at) setBaseParamSyncAt(String(res.data.synced_at));
        clearBaseParamsDirty();
        if (Array.isArray(res.data?.warnings) && res.data.warnings.length) {
          const detail = summarizeSyncWarnings(res.data.warnings);
          const suffix = detail ? `: ${detail}` : '';
          TOAST.warn(`${res.data.warnings.length} parameter di-skip${suffix}.`);
        }
        // Show subtle sync indicator
        showParamSyncStatus('synced');
      } else {
        console.warn('[VP] Param sync failed:', res);
        showParamSyncStatus('error');
      }
    } catch (err) {
      console.error('[VP] Param sync error:', err);
      showParamSyncStatus('error');
    }
  }

  async function syncComputedParamsToServer() {
    try {
      const payload = {};
      Object.keys(computedParams || {}).forEach((code) => {
        const def = computedParams[code] || {};
        if (!def.expression) return;
        payload[code] = {
          expression: String(def.expression || ''),
          label: String(def.label || code),
          unit: String(def.unit || ''),
          description: String(def.description || ''),
        };
      });
      const res = await HTTP.jpost(EP_CPARAMS_SYNC, {
        computed_parameters: payload,
        mode: 'replace',
        last_sync_at: computedParamSyncAt || null,
      });
      if (res.status === 409 || res.data?.error === 'conflict') {
        showParamSyncStatus('error');
        await promptSyncConflict('computed', res.data?.server_updated_at || '');
        return;
      }
      if (res.ok && res.data?.ok) {
        console.log('[VP] Computed params synced to server:', {
          created: Number(res.data?.created || 0),
          updated: Number(res.data?.updated || 0),
          deleted: Number(res.data?.deleted || 0),
          warnings: Array.isArray(res.data?.warnings) ? res.data.warnings.length : 0,
        });
        if (res.data?.synced_at) setComputedParamSyncAt(String(res.data.synced_at));
        clearComputedParamsDirty();
        if (Array.isArray(res.data?.warnings) && res.data.warnings.length) {
          const detail = summarizeSyncWarnings(res.data.warnings);
          const suffix = detail ? `: ${detail}` : '';
          TOAST.warn(`${res.data.warnings.length} formula turunan di-skip${suffix}.`);
        }
        showParamSyncStatus('synced');
      } else {
        console.warn('[VP] Computed param sync failed:', res);
        showParamSyncStatus('error');
      }
    } catch (err) {
      console.error('[VP] Computed param sync error:', err);
      showParamSyncStatus('error');
    }
  }

  // Load parameters from server and replace localStorage snapshot
  async function loadParamsFromServer(options = {}) {
    const force = !!options.force;
    if (!force && shouldProtectLocalBaseState()) {
      TOAST.warn('Perubahan lokal parameter belum tersinkron. Data server tidak diterapkan agar edit lokal aman.');
      return { ok: false, source: 'localStorage', reason: 'local_dirty' };
    }
    try {
      const data = await HTTP.jget(EP_PARAMS);
      if (data?.ok && Array.isArray(data.parameters)) {
        const serverParams = {};
        const serverLabels = {};

        for (const p of data.parameters) {
          const code = normalizeOpaqueCode(p?.name || '');
          if (!isValidBaseParamCode(code)) continue;
          serverParams[code] = Number(p.value) || 0;
          serverLabels[code] = p.label || code;
        }

        // Server is authoritative on successful fetch.
        // This prevents duplicate params from stale localStorage entries.
        variables = serverParams;
        varLabels = serverLabels;
        dropComputedNameConflicts();

        // Persist authoritative snapshot back to localStorage
        localStorage.setItem(storageKeyVars(), JSON.stringify(variables));
        localStorage.setItem(storageKeyVarLabels(), JSON.stringify(varLabels));
        if (data?.synced_at) setBaseParamSyncAt(String(data.synced_at));
        clearBaseParamsDirty();

        console.log('[VP] Loaded params from server:', Object.keys(serverParams).length);
        evaluateComputedParams();
        renderVarTable();
        renderComputedTable();
        reevaluateAllFormulas();
        refreshUsageBadges();
        showParamSyncStatus('synced');
        return { ok: true, source: 'server', total: Object.keys(serverParams).length };
      }
      return { ok: false, source: 'server', reason: 'invalid_response' };
    } catch (err) {
      console.warn('[VP] Failed to load params from server, using localStorage:', err);
      return { ok: false, source: 'localStorage', error: String(err?.message || err || '') };
    }
  }

  async function loadComputedParamsFromServer(options = {}) {
    const force = !!options.force;
    if (!force && shouldProtectLocalComputedState()) {
      TOAST.warn('Perubahan lokal formula turunan belum tersinkron. Data server tidak diterapkan agar edit lokal aman.');
      return { ok: false, source: 'localStorage', reason: 'local_dirty' };
    }
    try {
      const data = await HTTP.jget(EP_CPARAMS);
      if (data?.ok && Array.isArray(data.computed_parameters)) {
        const defs = {};
        data.computed_parameters.forEach((p) => {
          const code = normalizeOpaqueCode(p?.name || '');
          if (!isValidComputedParamCode(code)) return;
          defs[code] = {
            expression: String(p?.expression || '').trim(),
            label: String(p?.label || code).trim() || code,
            unit: String(p?.unit || '').trim(),
            description: String(p?.description || '').trim(),
          };
        });
        computedParams = normalizeComputedParamsShape(defs);
        dropComputedNameConflicts();
        localStorage.setItem(storageKeyComputed(), JSON.stringify(computedParams));
        if (data?.synced_at) setComputedParamSyncAt(String(data.synced_at));
        clearComputedParamsDirty();
        evaluateComputedParams();
        renderComputedTable();
        reevaluateAllFormulas();
        refreshUsageBadges();
        showParamSyncStatus('synced');
        return { ok: true, source: 'server', total: Object.keys(defs).length };
      }
      return { ok: false, source: 'server', reason: 'invalid_response' };
    } catch (err) {
      console.warn('[VP] Failed to load computed params from server, using localStorage:', err);
      return { ok: false, source: 'localStorage', error: String(err?.message || err || '') };
    }
  }

  function showCloudSyncStatus(indicatorId, status, options = {}) {
    const indicator = document.getElementById(indicatorId);
    if (!indicator) return;

    const pendingTitle = options.pendingTitle || 'Menyimpan...';
    const syncedTitle = options.syncedTitle || 'Tersimpan';
    const errorTitle = options.errorTitle || 'Gagal menyimpan ke server';
    const staleTitle = options.staleTitle || 'Ada perubahan baru di server';
    const autoClearMs = Number(options.autoClearMs || 2000);

    indicator.classList.remove('sync-pending', 'sync-synced', 'sync-error', 'sync-stale');

    if (status === 'pending') {
      indicator.classList.add('sync-pending');
      indicator.title = pendingTitle;
      indicator.innerHTML = '<i class="bi bi-cloud-arrow-up"></i>';
      return;
    }
    if (status === 'synced') {
      indicator.classList.add('sync-synced');
      indicator.title = syncedTitle;
      indicator.innerHTML = '<i class="bi bi-cloud-check"></i>';
      setTimeout(() => {
        indicator.classList.remove('sync-synced');
        indicator.innerHTML = '';
      }, autoClearMs);
      return;
    }
    if (status === 'error') {
      indicator.classList.add('sync-error');
      indicator.title = errorTitle;
      indicator.innerHTML = '<i class="bi bi-cloud-slash"></i>';
      return;
    }
    if (status === 'stale') {
      indicator.classList.add('sync-stale');
      indicator.title = staleTitle;
      indicator.innerHTML = '<i class="bi bi-cloud-exclamation"></i>';
    }
  }

  // Show sync status in sidebar
  function showParamSyncStatus(status) {
    showCloudSyncStatus('vp-param-sync-status', status, {
      pendingTitle: 'Menyimpan parameter...',
      syncedTitle: 'Parameter tersimpan',
      errorTitle: 'Gagal menyimpan parameter ke server',
      autoClearMs: 2000,
    });
  }

  function showFormulaSyncStatus(status) {
    showCloudSyncStatus('vp-formula-sync-status', status, {
      pendingTitle: 'Menyimpan formula...',
      syncedTitle: 'Formula tersimpan',
      errorTitle: 'Gagal menyimpan formula ke server',
      staleTitle: 'Ada perubahan formula baru di server',
      autoClearMs: 2000,
    });
  }

  function loadFormulaDrafts() {
    try {
      const raw = localStorage.getItem(storageKeyFormulaDrafts());
      const parsed = raw ? JSON.parse(raw) : {};
      if (!parsed || typeof parsed !== 'object') return {};
      const normalized = {};
      Object.keys(parsed).forEach((idKey) => {
        const id = Number(idKey);
        if (!Number.isFinite(id)) return;
        const entry = parsed[idKey];
        if (!entry || typeof entry !== 'object') return;
        const rawExpr = String(entry.raw || '');
        if (!rawExpr.trim()) return;
        normalized[id] = {
          raw: rawExpr,
          fx: !!entry.fx,
          updated_at: String(entry.updated_at || '').trim() || null,
        };
      });
      return normalized;
    } catch {
      return {};
    }
  }

  function saveFormulaDrafts(map) {
    try {
      const normalized = {};
      Object.keys(map || {}).forEach((idKey) => {
        const id = Number(idKey);
        if (!Number.isFinite(id)) return;
        const entry = map[idKey];
        if (!entry || typeof entry !== 'object') return;
        const rawExpr = String(entry.raw || '');
        if (!rawExpr.trim()) return;
        normalized[id] = {
          raw: rawExpr,
          fx: !!entry.fx,
          updated_at: String(entry.updated_at || '').trim() || null,
        };
      });
      localStorage.setItem(storageKeyFormulaDrafts(), JSON.stringify(normalized));
    } catch { }
  }

  function loadFormulas() {
    try {
      const raw = localStorage.getItem(storageKeyForms());
      const obj = raw ? JSON.parse(raw) : {};
      return normalizeFormulaStateMap(obj);
    } catch { return {}; }
  }
  function saveFormulas(map) {
    const normalized = normalizeFormulaStateMap(map);
    localStorage.setItem(storageKeyForms(), JSON.stringify(normalized));
  }

  async function runOpaqueMigrationLoadOnce() {
    const flagKey = storageKeyOpaqueMigrationFlag();
    if (localStorage.getItem(flagKey)) return false;

    const snapshot = {
      vars: localStorage.getItem(storageKeyVars()),
      labels: localStorage.getItem(storageKeyVarLabels()),
      computed: localStorage.getItem(storageKeyComputed()),
    };

    const restoreSnapshot = () => {
      if (snapshot.vars !== null) localStorage.setItem(storageKeyVars(), snapshot.vars);
      if (snapshot.labels !== null) localStorage.setItem(storageKeyVarLabels(), snapshot.labels);
      if (snapshot.computed !== null) localStorage.setItem(storageKeyComputed(), snapshot.computed);
    };

    const retryLoad = () => Promise.all([
      loadParamsFromServer({ force: true }),
      loadComputedParamsFromServer({ force: true }),
    ]);

    try {
      localStorage.removeItem(storageKeyVars());
      localStorage.removeItem(storageKeyVarLabels());
      localStorage.removeItem(storageKeyComputed());
      const [baseRes, computedRes] = await retryLoad();
      if (!(baseRes?.ok && computedRes?.ok)) {
        throw new Error('migration-load-invalid');
      }
      clearBaseParamsDirty();
      clearComputedParamsDirty();
      localStorage.setItem(flagKey, Date.now().toString());
      return true;
    } catch (err) {
      restoreSnapshot();
      console.warn('[VP] Opaque migration load gagal, restore snapshot lama:', err);
      TOAST.warn('Sinkronisasi migration gagal. Sistem akan retry otomatis.');
      setTimeout(() => {
        retryLoad()
          .then(([baseRes, computedRes]) => {
            if (baseRes?.ok && computedRes?.ok) {
              clearBaseParamsDirty();
              clearComputedParamsDirty();
              localStorage.setItem(flagKey, Date.now().toString());
            }
          })
          .catch(() => { });
      }, 3000);
      return false;
    }
  }

  // ==== Init: load variables, render table, bind baris existing (SSR)
  loadVars();
  loadVarLabels();
  loadComputedParams();
  loadSyncMarkers();
  formulaDraftById = loadFormulaDrafts();
  Object.keys(variables).forEach(code => { if (!varLabels[code]) varLabels[code] = code; });
  localStorage.setItem(storageKeyVarLabels(), JSON.stringify(varLabels));
  initSidebarSearch();
  renderVarTable();
  renderComputedTable();
  refreshUsageBadges();
  initSidebarPaneTabs();
  loadFormulaPreviewMode();
  loadFormulaShowInlineValues();
  startFormulaRemoteWatch();

  // Load from server (async - will replace local snapshot and re-render)
  runOpaqueMigrationLoadOnce().then((didMigrateLoad) => {
    if (!didMigrateLoad) {
      loadParamsFromServer();
      loadComputedParamsFromServer();
    }
  });

  // Bind baris yang sudah dirender server agar fitur aktif sebelum tree di-load
  rows.forEach(tr => bindRow(tr));

  // ===== EXPORT INITIALIZATION =====
  // Initialize unified export (XLSX/PDF/Word/JSON) via ExportManager
  let exportInitAttempts = 0;
  const MAX_EXPORT_INIT_ATTEMPTS = 20;
  let exportInitDone = false;

  function initExportButtons() {
    if (exportInitDone) return;

    if (typeof ExportManager === 'undefined') {
      exportInitAttempts += 1;
      if (exportInitAttempts <= MAX_EXPORT_INIT_ATTEMPTS) {
        setTimeout(initExportButtons, 150);
        return;
      }
      console.warn('[Volume] ExportManager not loaded - export buttons disabled');
      return;
    }

    try {
      const exporter = new ExportManager(projectId, 'volume-pekerjaan');
      let isExporting = false;

      function getExportParameters() {
        try {
          return getFormulaScopeValues();
        } catch (err) {
          console.warn('[Volume] Failed to build export parameters:', err);
          return { ...variables };
        }
      }

      async function handleExport(format, e, useAsync = false) {
        e.preventDefault();
        e.stopImmediatePropagation();
        if (isExporting) return;
        isExporting = true;
        try {
          const options = {
            parameters: getExportParameters(),
            allowSyncFallback: true,
            asyncStartTimeoutMs: 12000,
          };
          if (useAsync || format === 'pdf' || format === 'word') {
            const asyncOk = await exporter.exportAsAsync(format, options);
            if (asyncOk === false) {
              await exporter.exportAs(format, options);
            }
          } else {
            await exporter.exportAs(format, options);
          }
        } finally {
          isExporting = false;
        }
      }

      const btnXLSX = document.getElementById('btn-export-xlsx');
      const btnPDF = document.getElementById('btn-export-pdf');
      const btnWord = document.getElementById('btn-export-word');
      const btnJSON = document.getElementById('btn-export-json');

      if (btnXLSX) btnXLSX.addEventListener('click', (e) => handleExport('xlsx', e));
      if (btnPDF) btnPDF.addEventListener('click', (e) => handleExport('pdf', e, true));
      if (btnWord) btnWord.addEventListener('click', (e) => handleExport('word', e, true));
      if (btnJSON) btnJSON.addEventListener('click', (e) => handleExport('json', e));

      exportInitDone = true;
      console.log('[Volume] Export buttons initialized');
    } catch (err) {
      console.error('[Volume] Export initialization failed:', err);
    }
  }

  // Run export initialization after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initExportButtons);
  } else {
    initExportButtons();
  }

  // ===== SUMMARY STATISTICS & FILTER BAR =====
  // ===== CONSOLIDATED SUMMARY & FILTER BAR =====
  const summaryBar = document.getElementById('vp-summary-bar');
  const filterBar = summaryBar; // Consolidated

  function getActiveSummaryFilter() {
    if (!summaryBar) return 'all';
    const activeBtn = summaryBar.querySelector('[data-filter].active');
    return String(activeBtn?.dataset?.filter || 'all');
  }

  function getSummaryCounterEl(filter) {
    const byId = {
      all: 'vp-stat-total',
      filled: 'vp-stat-filled',
      empty: 'vp-stat-empty',
      formula: 'vp-stat-formula',
    };
    const id = byId[filter];
    if (id) {
      const el = document.getElementById(id);
      if (el) return el;
    }
    const btn = summaryBar?.querySelector?.(`[data-filter="${filter}"]`);
    if (!btn) return null;
    return btn.querySelector('.badge, .fw-bold, [data-stat]') || null;
  }

  function getRowQtySummaryState(row) {
    const input = row?.querySelector?.('.qty-input');
    if (!input) return null;
    const id = parseInt(row.dataset.pekerjaanId, 10);
    const rawVal = Number.isFinite(id)
      ? String(rawInputById[id] || input.value || '').trim()
      : String(input.value || '').trim();
    const displayVal = String(input.value || '').trim();
    const hasFormula = Number.isFinite(id)
      ? isFormulaMode(id, rawVal)
      : rawVal.startsWith('=');
    // Formula row tetap dianggap "terisi" bila raw formula tidak kosong,
    // walau field input disembunyikan/di-mask.
    const isFilled = hasFormula ? (rawVal.length > 0) : (displayVal.length > 0);
    return { isFilled, hasFormula };
  }

  /**
   * Update summary statistics badges (and buttons)
   */
  function updateSummaryBarCounts() {
    if (!summaryBar) return;

    const allRows = document.querySelectorAll('tr[data-pekerjaan-id]');
    let total = 0, filled = 0, empty = 0, formula = 0;

    allRows.forEach(row => {
      const state = getRowQtySummaryState(row);
      if (!state) return;
      total++;
      if (state.isFilled) {
        filled++;
      } else {
        empty++;
      }
      if (state.hasFormula) formula++;
    });

    // Update badge values in buttons
    const setBadge = (filter, count) => {
      const target = getSummaryCounterEl(filter);
      if (target) target.textContent = String(count);
    };

    setBadge('all', total);
    setBadge('filled', filled);
    setBadge('empty', empty);
    setBadge('formula', formula);
  }

  function updateSummaryStats() {
    updateSummaryBarCounts();
  }

  function syncSummaryBarWithCurrentFilter() {
    updateSummaryBarCounts();
    const activeFilter = getActiveSummaryFilter();
    if (activeFilter && activeFilter !== 'all') {
      applyRowFilter(activeFilter);
    }
  }

  /**
   * Apply row filter based on filter type
   */
  function applyRowFilter(filter) {
    const allRows = document.querySelectorAll('tr[data-pekerjaan-id]');
    let visibleCount = 0;

    allRows.forEach(row => {
      const state = getRowQtySummaryState(row);
      if (!state) return;
      const hasFormula = state.hasFormula;
      const isEmpty = !state.isFilled;
      let show = true;

      switch (filter) {
        case 'filled':
          show = !isEmpty;
          break;
        case 'empty':
          show = isEmpty;
          break;
        case 'formula':
          show = hasFormula;
          break;
        case 'all':
        default:
          show = true;
      }

      row.style.display = show ? '' : 'none';
      if (show) visibleCount++;
    });

    // Update stats after filter
    updateSummaryBarCounts();

    return visibleCount;
  }

  // Filter bar click handler
  if (summaryBar) {
    summaryBar.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-filter]');
      if (!btn) return;

      const filter = btn.dataset.filter;

      // Toggle active state
      summaryBar.querySelectorAll('.btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      // Apply filter
      const count = applyRowFilter(filter);
    });
  }

  // Initial stats update
  syncSummaryBarWithCurrentFilter();

  // Update stats when input changes (hook into existing input handler)
  document.addEventListener('input', (e) => {
    if (e.target.classList.contains('qty-input')) {
      // Debounce stats update
      clearTimeout(window._vpStatsTimer);
      window._vpStatsTimer = setTimeout(syncSummaryBarWithCurrentFilter, 300);
    }
  });

  // Expose for external use
  window.vpUpdateStats = updateSummaryStats;

  // Expose variables for export (base + computed resolved values)
  window.vpGetVariables = () => ({ ...getFormulaScopeValues() });
  window.vpFormulaLabelMask = {
    rawToDisplayText,
    displayToRaw,
  };

})();
