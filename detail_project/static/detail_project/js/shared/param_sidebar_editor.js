/**
 * param_sidebar_editor.js — Shared self-contained parameter sidebar widget.
 *
 * Provides full CRUD for base & computed parameters: render tables, add/edit/delete,
 * import/export (JSON/CSV/XLSX), debounced server sync, search, tab switch, resize.
 *
 * Usage:
 *   ParamSidebarEditor.init(config);
 *   ParamSidebarEditor.onParamsChanged(cb);
 *   ParamSidebarEditor.getSnapshot();
 *   ParamSidebarEditor.refresh();
 *   ParamSidebarEditor.destroy();
 */
(function () {
  'use strict';

  const G = (typeof window !== 'undefined') ? window : globalThis;

  // ── Constants ──────────────────────────────────────────────────────────
  const STORE_PLACES = 12;
  const DISPLAY_PLACES = 6;
  const PARAM_SYNC_DELAY = 2000;
  const MAX_IMPORT_SIZE_BYTES = 5 * 1024 * 1024;
  const FORMULA_ALLOWED_FUNCTIONS = Object.freeze([
    'sum', 'min', 'max', 'round', 'avg', 'abs', 'floor', 'ceil', 'pow',
  ]);
  const FORMULA_ALLOWED_FUNCTION_SET = new Set(FORMULA_ALLOWED_FUNCTIONS);

  // ── State ──────────────────────────────────────────────────────────────
  let cfg = null;             // config object
  let variables = {};         // { bp_1: 10, ... }
  let varLabels = {};         // { bp_1: "Panjang", ... }
  let computedParams = {};    // { cp_1: { expression, label, unit, description } }
  let computedValues = {};    // { cp_1: 125.5 }
  let computedErrors = {};    // { cp_1: "Error msg" }
  let baseParamSyncAt = null;
  let computedParamSyncAt = null;
  let paramSyncTimer = null;
  let computedSyncTimer = null;
  let syncConflictPromptOpen = false;
  let sidebarSearchQuery = '';
  let changeCallbacks = [];
  let destroyed = false;

  // DOM element cache
  let $container = null;
  let $varTable = null;
  let $cParamTable = null;
  let $btnVarAdd = null;
  let $btnCParamAdd = null;
  let $paramCount = null;
  let $cParamCount = null;
  let $tabBaseCount = null;
  let $tabComputedCount = null;
  let $searchInput = null;
  let $searchClear = null;
  let $syncIndicator = null;
  let paneTabs = [];
  let panes = [];

  // ── Utility Helpers ────────────────────────────────────────────────────
  function getCsrf() {
    if (cfg && typeof cfg.csrf === 'function') return cfg.csrf();
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (m) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[m]));
  }

  function roundHalfUp(x, places) {
    const p = Math.max(0, Math.min(20, places | 0));
    const factor = Math.pow(10, p);
    return (x >= 0)
      ? Math.floor(x * factor + 0.5) / factor
      : Math.ceil(x * factor - 0.5) / factor;
  }

  function formatIdSmart(num) {
    const n = Number(num || 0);
    const hasFrac = Math.abs(n - Math.trunc(n)) > 1e-12;
    const fracLen = hasFrac
      ? Math.min(String(n.toFixed(DISPLAY_PLACES)).split('.')[1]?.replace(/0+$/, '').length || 0, DISPLAY_PLACES)
      : 0;
    try {
      return new Intl.NumberFormat('id-ID', {
        minimumFractionDigits: fracLen,
        maximumFractionDigits: DISPLAY_PLACES,
      }).format(n);
    } catch {
      return n.toFixed(fracLen);
    }
  }

  function normalizeLocaleNumericString(input) {
    const N = G.Numeric || null;
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
    const N = G.Numeric || null;
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
    if (cfg && cfg.opaqueIdEnabled) return isBaseOpaqueCode(safe);
    if (isComputedOpaqueCode(safe)) return false;
    return isLegacyParamCode(safe) || isBaseOpaqueCode(safe);
  }

  function isValidComputedParamCode(code) {
    const safe = String(code || '').trim().toLowerCase();
    if (cfg && cfg.opaqueIdEnabled) return isComputedOpaqueCode(safe);
    if (isBaseOpaqueCode(safe)) return false;
    return isLegacyParamCode(safe) || isComputedOpaqueCode(safe);
  }

  function normalizeSuggestKeyword(text) {
    return String(text || '').toLowerCase().replace(/[_\s]+/g, ' ').trim();
  }

  function compactSuggestKeyword(text) {
    return normalizeSuggestKeyword(text).replace(/\s+/g, '');
  }

  function tsCompact() {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}`;
  }

  // ── HTTP Helper ────────────────────────────────────────────────────────
  const HTTP = {
    async jget(url) {
      const h = (G.DP && G.DP.core && G.DP.core.http) ? G.DP.core.http : null;
      if (h && h.jfetch) return h.jfetch(url, { method: 'GET', normalize: false });
      const r = await fetch(url, { credentials: 'same-origin' });
      if (!r.ok) throw new Error(r.statusText);
      return r.json();
    },
    async jpost(url, data) {
      const h = (G.DP && G.DP.core && G.DP.core.http) ? G.DP.core.http : null;
      if (h && h.jfetchJson) return h.jfetchJson(url, { method: 'POST', data });
      const r = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
        credentials: 'same-origin',
        body: JSON.stringify(data),
      });
      const body = await r.json().catch(() => ({}));
      return { ok: r.ok, status: r.status, data: body, errors: body?.errors || [] };
    },
  };

  // ── Toast Helper ───────────────────────────────────────────────────────
  function TOAST_ok(msg) {
    if (cfg && typeof cfg.toast === 'function') { cfg.toast(msg, 'success'); return; }
    const api = G.DP && G.DP.toast;
    if (api) { api.success(msg); return; }
    console.log('[ParamSidebar]', msg);
  }
  function TOAST_warn(msg) {
    if (cfg && typeof cfg.toast === 'function') { cfg.toast(msg, 'warning'); return; }
    const api = G.DP && G.DP.toast;
    if (api) { api.warning(msg); return; }
    console.warn('[ParamSidebar]', msg);
  }
  function TOAST_err(msg) {
    if (cfg && typeof cfg.toast === 'function') { cfg.toast(msg, 'danger'); return; }
    const api = G.DP && G.DP.toast;
    if (api) { api.error(msg); return; }
    console.error('[ParamSidebar]', msg);
  }
  function TOAST_action(msg, actions) {
    const api = G.DP && G.DP.toast;
    if (api && typeof api.action === 'function') { api.action(msg, actions); return; }
    // Fallback: simple log
    TOAST_ok(msg);
  }

  // ── Modal Helper ───────────────────────────────────────────────────────
  function getModalApi() {
    return (G.DP && G.DP.core && G.DP.core.modal) ? G.DP.core.modal : null;
  }

  function confirmModal(message, options) {
    if (cfg && typeof cfg.confirmModal === 'function') {
      return Promise.resolve(cfg.confirmModal(message, options));
    }
    const modalApi = getModalApi();
    if (modalApi && modalApi.confirm) return Promise.resolve(modalApi.confirm(message, options));
    const title = String((options && options.title) || '').trim();
    const promptText = title ? `${title}\n\n${message}` : String(message || '');
    try { return Promise.resolve(window.confirm(promptText)); } catch { }
    return Promise.resolve(false);
  }

  function alertModal(message, options) {
    const modalApi = getModalApi();
    if (modalApi && typeof modalApi.alert === 'function') return Promise.resolve(modalApi.alert(message, options));
    window.alert(message);
    return Promise.resolve();
  }

  // ── Computed Param Evaluation ──────────────────────────────────────────
  function evaluateComputedParams() {
    const defs = computedParams || {};
    const names = Object.keys(defs);
    const resolved = {};
    const errors = {};
    if (!names.length) {
      computedValues = resolved;
      computedErrors = errors;
      return;
    }
    const pending = new Set(names);
    let guard = 0;
    while (pending.size && guard < names.length + 5) {
      guard += 1;
      let progressed = false;
      for (const code of Array.from(pending)) {
        const def = defs[code] || {};
        const rawExpr = String(def.expression || '').trim();
        if (!rawExpr) { errors[code] = 'Formula kosong'; pending.delete(code); continue; }
        const expr = rawExpr.startsWith('=') ? rawExpr : `=${rawExpr}`;
        const scope = { ...variables, ...resolved };
        try {
          if (typeof G.VolFormula === 'undefined' || !G.VolFormula.evaluate) throw new Error('Formula engine tidak tersedia');
          let val = G.VolFormula.evaluate(expr, scope, { clampMinZero: false });
          if (!Number.isFinite(val) || val < 0) val = 0;
          resolved[code] = roundHalfUp(val, STORE_PLACES);
          pending.delete(code);
          progressed = true;
        } catch (err) {
          const msg = String(err?.message || err || 'Formula tidak valid');
          const unknown = extractUnknownVarName(msg);
          if (unknown && pending.has(unknown) && unknown !== code) continue;
          errors[code] = msg;
          pending.delete(code);
        }
      }
      if (!progressed) break;
    }
    if (pending.size) {
      pending.forEach((code) => {
        errors[code] = errors[code] || 'Dependensi formula tidak bisa diselesaikan (cek siklus/urutan variabel)';
      });
    }
    computedValues = resolved;
    computedErrors = errors;
  }

  function extractUnknownVarName(message) {
    const m = String(message || '').match(/Variabel tidak dikenal:\s*(.+)$/i);
    return m ? String(m[1] || '').trim().toLowerCase() : '';
  }

  // ── Scope Builders ─────────────────────────────────────────────────────
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

  function buildComputedParamScope(excludeCode) {
    const scopeValues = { ...variables };
    const scopeLabels = { ...varLabels };
    Object.keys(computedParams || {}).forEach((code) => {
      if (code === excludeCode) return;
      if (computedValues[code] != null) scopeValues[code] = computedValues[code];
      scopeLabels[code] = computedParams[code]?.label || code;
    });
    return { scopeValues, scopeLabels };
  }

  // ── Formula Preview Helpers ────────────────────────────────────────────
  function translateFormulaForPreview(rawExpr, options) {
    const mode = String((options && options.mode) || 'label');
    const scopeLabels = (options && options.scopeLabels) || {};
    const scopeValues = (options && options.scopeValues) || {};
    const expr = String(rawExpr || '').replace(/^=/, '').trim();
    if (!expr) return '';

    let translated = '';
    try {
      if (typeof G.VolFormula !== 'undefined' && G.VolFormula && typeof G.VolFormula.tokenize === 'function') {
        const tokens = G.VolFormula.tokenize(expr);
        if (Array.isArray(tokens) && tokens.length) {
          const pieces = [];
          tokens.forEach((tok) => {
            const type = String(tok?.type || '').toLowerCase();
            const rawValue = String(tok?.value || '');
            const value = rawValue.toLowerCase();
            if (type === 'id') {
              if (mode === 'value') {
                if (Object.prototype.hasOwnProperty.call(scopeValues, value)) {
                  pieces.push(formatIdSmart(Number(scopeValues[value] || 0)));
                  return;
                }
              } else {
                if (Object.prototype.hasOwnProperty.call(scopeLabels, value)) {
                  pieces.push(String(scopeLabels[value] || value));
                  return;
                }
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
    } catch { translated = ''; }

    if (translated) return translated;
    const fallbackMap = mode === 'value' ? scopeValues : scopeLabels;
    return expr.replace(/[A-Za-z_][A-Za-z0-9_]*/g, (token) => {
      const code = String(token || '').toLowerCase();
      if (!Object.prototype.hasOwnProperty.call(fallbackMap, code)) return token;
      if (mode === 'value') return formatIdSmart(Number(fallbackMap[code] || 0));
      return String(fallbackMap[code] || code);
    });
  }

  function buildFormulaChipHtml(expr, scopeLabels, options) {
    const labels = scopeLabels || getFormulaScopeLabels();
    const compact = !!(options && options.compact);
    let html = '';
    try {
      if (typeof G.VolFormula !== 'undefined' && G.VolFormula && typeof G.VolFormula.tokenize === 'function') {
        const tokens = G.VolFormula.tokenize(expr);
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
              return `<span class="${chipClass}" title="${escapeHtml(label)}">${escapeHtml(label)}</span>`;
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
    } catch { html = ''; }
    if (!html) html = `<span class="vp-formula-chip-raw">${escapeHtml(expr)}</span>`;
    return html;
  }

  function humanizeFormulaError(msg, labels) {
    const text = String(msg || '');
    return text.replace(/\b(bp_[1-9][0-9]*|cp_[1-9][0-9]*)\b/gi, (tok) => {
      const code = tok.toLowerCase();
      if (labels && labels[code]) return `"${labels[code]}"`;
      return tok;
    });
  }

  // ── Usage / Delete Warning ─────────────────────────────────────────────
  const FORMULA_RESERVED_IDS = new Set([
    ...FORMULA_ALLOWED_FUNCTIONS,
    'pi', 'e', 'true', 'false',
  ]);

  function parseFormulaIdentifierSet(rawExpr) {
    const out = new Set();
    const expr = String(rawExpr || '').trim();
    if (!expr) return out;
    try {
      if (typeof G.VolFormula !== 'undefined' && G.VolFormula && typeof G.VolFormula.tokenize === 'function') {
        const tokens = G.VolFormula.tokenize(expr);
        if (Array.isArray(tokens)) {
          tokens.forEach((tok) => {
            const type = String(tok?.type || '').toLowerCase();
            const value = String(tok?.value || '').trim().toLowerCase();
            if (type !== 'id' || !value || FORMULA_RESERVED_IDS.has(value)) return;
            out.add(value);
          });
          return out;
        }
      }
    } catch { /* fallback regex */ }
    const matches = expr.match(/[A-Za-z_][A-Za-z0-9_]*/g) || [];
    matches.forEach((m) => {
      const code = String(m || '').trim().toLowerCase();
      if (!code || FORMULA_RESERVED_IDS.has(code)) return;
      out.add(code);
    });
    return out;
  }

  function collectFormulaUsageMap() {
    const usageMap = {};
    const ensureBucket = (code) => {
      const key = String(code || '').trim().toLowerCase();
      if (!key) return null;
      if (!usageMap[key]) usageMap[key] = { computedRefs: new Set(), rowRefs: new Map() };
      return usageMap[key];
    };
    Object.keys(computedParams || {}).forEach((ownerCode) => {
      const def = computedParams[ownerCode] || {};
      const deps = parseFormulaIdentifierSet(def.expression || '');
      deps.forEach((depCode) => {
        if (depCode === ownerCode) return;
        const bucket = ensureBucket(depCode);
        if (bucket) bucket.computedRefs.add(ownerCode);
      });
    });
    return usageMap;
  }

  function summarizeFormulaUsage(code, usageMap) {
    const key = String(code || '').trim().toLowerCase();
    const bucket = (usageMap && usageMap[key]) ? usageMap[key] : null;
    const computedCodes = bucket ? Array.from(bucket.computedRefs || []) : [];
    computedCodes.sort((a, b) => (computedParams[a]?.label || a).localeCompare((computedParams[b]?.label || b), 'id'));
    const computedLabels = computedCodes.map((c) => computedParams[c]?.label || varLabels[c] || c);
    const total = computedCodes.length;
    const tooltipParts = [];
    if (computedCodes.length) tooltipParts.push(`Formula turunan: ${computedCodes.length}`);
    return {
      code: key, total,
      computedCount: computedCodes.length, rowCount: 0,
      computedCodes, rowRefs: [],
      computedLabels, rowLabels: [],
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
    const baseLine = kind === 'computed'
      ? `Hapus formula turunan "${label}"?`
      : `Hapus parameter "${label}"?`;
    if (!usage || usage.total <= 0) return baseLine;
    const lines = [baseLine, '', `Item ini dipakai di ${usage.total} formula:`];
    if (usage.computedCount > 0) {
      const preview = usage.computedLabels.slice(0, 3).join(', ');
      const tail = usage.computedCount > 3 ? ` (+${usage.computedCount - 3} lainnya)` : '';
      lines.push(`- Formula turunan (${usage.computedCount}): ${preview}${tail}`);
    }
    lines.push('', 'Jika tetap dihapus, formula terkait bisa menjadi error. Lanjutkan?');
    return lines.join('\n');
  }

  // ── Search ─────────────────────────────────────────────────────────────
  function sidebarSearchQueryText() {
    return String(sidebarSearchQuery || '').trim();
  }

  function matchesSidebarSearch(item) {
    const query = sidebarSearchQueryText();
    if (!query) return true;
    const qNorm = normalizeSuggestKeyword(query);
    const qCompact = compactSuggestKeyword(query);
    if (!qNorm && !qCompact) return true;
    const candidates = [item.code, item.label, item.expression, item.preview];
    return candidates.some((raw) => {
      const text = String(raw || '').trim();
      if (!text) return false;
      const tNorm = normalizeSuggestKeyword(text);
      const tCompact = compactSuggestKeyword(text);
      return (!!qNorm && tNorm.includes(qNorm)) || (!!qCompact && tCompact.includes(qCompact));
    });
  }

  // ── Sync Indicator ─────────────────────────────────────────────────────
  function showSyncStatus(status) {
    if (!$syncIndicator) return;
    $syncIndicator.classList.remove('sync-pending', 'sync-synced', 'sync-error', 'sync-stale');
    if (status === 'pending') {
      $syncIndicator.classList.add('sync-pending');
      $syncIndicator.title = 'Menyimpan parameter...';
      $syncIndicator.innerHTML = '<i class="bi bi-cloud-arrow-up"></i>';
    } else if (status === 'synced') {
      $syncIndicator.classList.add('sync-synced');
      $syncIndicator.title = 'Parameter tersimpan';
      $syncIndicator.innerHTML = '<i class="bi bi-cloud-check"></i>';
      setTimeout(() => {
        if ($syncIndicator) { $syncIndicator.classList.remove('sync-synced'); $syncIndicator.innerHTML = ''; }
      }, 2000);
    } else if (status === 'error') {
      $syncIndicator.classList.add('sync-error');
      $syncIndicator.title = 'Gagal menyimpan parameter ke server';
      $syncIndicator.innerHTML = '<i class="bi bi-cloud-slash"></i>';
    }
  }

  // ── Normalize Computed Shape ───────────────────────────────────────────
  function normalizeComputedParamsShape(rawObj) {
    const out = {};
    if (!rawObj || typeof rawObj !== 'object') return out;
    Object.keys(rawObj).forEach((k) => {
      const code = normalizeOpaqueCode(k);
      if (!isValidComputedParamCode(code)) return;
      const v = rawObj[k];
      if (typeof v === 'string') { out[code] = { expression: v, label: code, unit: '', description: '' }; return; }
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
    if (changed) console.warn('[ParamSidebar] Removed computed param(s) conflicting with base param codes.');
  }

  // ── Render: Base Parameters Table ──────────────────────────────────────
  function renderVarTable() {
    if (!$varTable) return;
    const tbody = $varTable.querySelector('tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    const allCodes = Object.keys(variables);
    const usageMap = collectFormulaUsageMap();
    const filteredCodes = allCodes.filter((code) => matchesSidebarSearch({
      code, label: varLabels[code] || code, expression: '', preview: '',
    }));

    if ($paramCount) {
      if (sidebarSearchQueryText()) {
        $paramCount.textContent = `${filteredCodes.length}/${allCodes.length}`;
        $paramCount.setAttribute('title', `Menampilkan ${filteredCodes.length} dari ${allCodes.length} parameter`);
      } else {
        $paramCount.textContent = String(allCodes.length);
        $paramCount.removeAttribute('title');
      }
    }
    if ($tabBaseCount) $tabBaseCount.textContent = String(allCodes.length);

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
          <input type="text" class="form-control form-control-sm var-value" value="${formatIdSmart(val)}" aria-label="Nilai parameter" readonly>
        </td>
        <td class="text-end">
          <div class="btn-group btn-group-sm">
            <button type="button" class="btn btn-outline-secondary var-edit" title="Ubah" aria-label="Ubah"><i class="bi bi-pencil"></i></button>
            <button type="button" class="btn btn-outline-danger var-del" title="Hapus" aria-label="Hapus"><i class="bi bi-trash"></i></button>
          </div>
        </td>`;

      // Row highlight on click
      tr.addEventListener('click', () => {
        tbody.querySelectorAll('tr').forEach(r => r.classList.remove('table-primary'));
        tr.classList.add('table-primary');
        tr.scrollIntoView({ block: 'nearest' });
      });

      // Edit toggle
      const btnEdit = tr.querySelector('.var-edit');
      if (btnEdit) {
        btnEdit.addEventListener('click', (e) => {
          e.stopPropagation();
          const labelEl = tr.querySelector('.var-label');
          const valueEl = tr.querySelector('.var-value');
          const isEditing = tr.classList.toggle('is-editing');
          const icon = btnEdit.querySelector('i');
          if (isEditing) {
            labelEl.readOnly = false; valueEl.readOnly = false;
            labelEl.dataset.prev = labelEl.value; valueEl.dataset.prev = valueEl.value;
            if (icon) icon.className = 'bi bi-check-lg';
            btnEdit.setAttribute('title', 'Simpan'); btnEdit.setAttribute('aria-label', 'Simpan');
            labelEl.focus();
          } else {
            const nextLabel = String(labelEl.value || '').trim();
            const n = parseNumberOrEmpty(valueEl.value);
            let ok = true;
            if (!nextLabel) { ok = false; labelEl.classList.add('is-invalid'); setTimeout(() => labelEl.classList.remove('is-invalid'), 1200); labelEl.value = varLabels[code] || code; }
            if (n === '') { ok = false; valueEl.classList.add('is-invalid'); setTimeout(() => valueEl.classList.remove('is-invalid'), 1200); valueEl.value = formatIdSmart(variables[code]); }
            if (ok) {
              varLabels[code] = nextLabel;
              variables[code] = roundHalfUp(Number(n), STORE_PLACES);
              persistBaseParams();
            }
            labelEl.readOnly = true; valueEl.readOnly = true;
            if (icon) icon.className = 'bi bi-pencil';
            btnEdit.setAttribute('title', 'Ubah'); btnEdit.setAttribute('aria-label', 'Ubah');
          }
        });
      }

      // Delete
      tr.querySelector('.var-del').addEventListener('click', async (e) => {
        e.stopPropagation();
        const nm = varLabels[code] || code;
        const usage = summarizeFormulaUsage(code, collectFormulaUsageMap());
        const message = buildDeleteWarningMessage('base', nm, code, usage);
        const ok = await confirmModal(message, {
          title: 'Hapus Parameter', confirmText: 'Hapus', cancelText: 'Batal', confirmClass: 'btn btn-danger',
        });
        if (!ok) return;
        delete variables[code];
        delete varLabels[code];
        persistBaseParams();
        renderVarTable();
      });

      tbody.appendChild(tr);
    });
  }

  // ── Render: Computed Parameters Table ──────────────────────────────────
  function renderComputedTable() {
    if (!$cParamTable) return;
    const tbody = $cParamTable.querySelector('tbody');
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
      const preview = translateFormulaForPreview(expression, { mode: 'label', scopeLabels: labels, scopeValues });
      return matchesSidebarSearch({ code, label, expression, preview });
    });

    if ($cParamCount) {
      if (sidebarSearchQueryText()) {
        $cParamCount.textContent = `${filteredCodes.length}/${allCodes.length}`;
        $cParamCount.setAttribute('title', `Menampilkan ${filteredCodes.length} dari ${allCodes.length} formula turunan`);
      } else {
        $cParamCount.textContent = String(allCodes.length);
        $cParamCount.removeAttribute('title');
      }
    }
    if ($tabComputedCount) $tabComputedCount.textContent = String(allCodes.length);

    if (!allCodes.length) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td colspan="3" class="text-muted text-center py-3">Belum ada formula turunan.</td>`;
      tbody.appendChild(tr);
      return;
    }
    if (!filteredCodes.length) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td colspan="3" class="text-muted text-center py-3">Tidak ada formula turunan yang cocok dengan kata kunci.</td>`;
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
      const exprLabelPreview = translateFormulaForPreview(expression, { mode: 'label', scopeLabels: labels, scopeValues });
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
            ${err ? escapeHtml(errText) : formatIdSmart(Number(val || 0))}
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

      // Edit formula via FormulaEditorModal
      editBtn?.addEventListener('click', () => {
        if (G.FormulaEditorModal) {
          G.FormulaEditorModal.openForComputed(code, { enableNameEdit: true });
        }
      });
      formulaCell?.addEventListener('click', () => {
        if (G.FormulaEditorModal) {
          G.FormulaEditorModal.openForComputed(code);
        }
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
            computedParams[code] = { ...computedParams[code], label: nextLabel };
            persistComputedParams();
          }
          labelEl.readOnly = true;
        };
        labelEl.addEventListener('blur', saveLabel, { once: true });
        labelEl.addEventListener('keydown', (e) => {
          if (e.key === 'Enter') { e.preventDefault(); labelEl.blur(); }
          if (e.key === 'Escape') { labelEl.value = label; labelEl.readOnly = true; }
        });
      });

      // Delete
      delBtn?.addEventListener('click', async () => {
        const usage = summarizeFormulaUsage(code, collectFormulaUsageMap());
        const message = buildDeleteWarningMessage('computed', label, code, usage);
        const ok = await confirmModal(message, {
          title: 'Hapus Formula Turunan', confirmText: 'Hapus', cancelText: 'Batal', confirmClass: 'btn btn-danger',
        });
        if (!ok) return;
        delete computedParams[code];
        persistComputedParams();
      });

      tbody.appendChild(tr);
    });
  }

  // ── Add Base Parameter (inline row) ────────────────────────────────────
  function handleAddBaseParam() {
    if (!$varTable) return;
    const tbody = $varTable.querySelector('tbody');
    const existing = tbody.querySelector('tr.ps-var-inline');
    if (existing) { existing.querySelector('.var-label')?.focus(); return; }

    const opaqueEnabled = cfg && cfg.opaqueIdEnabled;
    const tr = document.createElement('tr');
    tr.className = 'ps-var-inline';
    tr.innerHTML = `
      <td>
        <input type="text" class="form-control form-control-sm var-label" placeholder="mis. Panjang Dinding">
        <div class="invalid-feedback">Label tidak boleh kosong.</div>
        <small class="text-muted d-block mt-1">${opaqueEnabled ? 'Kode opaque dibuat otomatis di server.' : 'Kode parameter dibuat otomatis dari label di server.'}</small>
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

      const ep = cfg.endpoints.parameters;
      const res = await HTTP.jpost(ep, {
        value: roundHalfUp(Number(n), STORE_PLACES),
        label, unit: '', description: '',
      });
      if (!(res.ok && res.data?.ok && res.data?.parameter?.name)) {
        const errMsg = (res.data?.errors && res.data.errors[0]?.message)
          || res.data?.message
          || 'Gagal menyimpan parameter ke server.';
        TOAST_err(errMsg);
        return;
      }
      const created = res.data.parameter;
      const code = String(created.name || '').trim();
      if (!isValidBaseParamCode(code)) {
        TOAST_err('Server mengembalikan kode parameter tidak valid.');
        return;
      }
      variables[code] = Number(created.value ?? 0) || 0;
      varLabels[code] = String(created.label || label).trim() || label;
      if (res.data?.synced_at) baseParamSyncAt = String(res.data.synced_at);
      tr.remove();
      persistBaseParams();
      renderVarTable();
    };

    tr.querySelector('.var-save').addEventListener('click', doSave);
    tr.querySelector('.var-cancel').addEventListener('click', doCancel);
    [labelEl, valEl].forEach(el => el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') doSave();
      if (e.key === 'Escape') doCancel();
    }));
  }

  // ── Add Computed Parameter (inline row + formula editor) ───────────────
  function handleAddComputedParam() {
    if (!$cParamTable) return;
    const tbody = $cParamTable.querySelector('tbody');
    if (!tbody) return;
    const existing = tbody.querySelector('tr.ps-cparam-inline');
    if (existing) { existing.querySelector('.cparam-label')?.focus(); return; }

    let pendingExpression = '';
    const opaqueEnabled = cfg && cfg.opaqueIdEnabled;

    const tr = document.createElement('tr');
    tr.className = 'ps-cparam-inline';
    tr.innerHTML = `
      <td>
        <input type="text" class="form-control form-control-sm cparam-label" placeholder="mis. Area L1">
        <small class="text-muted d-block mt-1">${opaqueEnabled ? 'Kode dibuat otomatis.' : 'Kode dibuat dari label.'}</small>
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
      const labelPreview = translateFormulaForPreview(pendingExpression, { mode: 'label', scopeLabels, scopeValues });
      if (exprDisplayEl) exprDisplayEl.textContent = labelPreview || pendingExpression;
      if (chipPreviewEl) chipPreviewEl.innerHTML = buildFormulaChipHtml(
        pendingExpression.replace(/^=/, '').trim(), scopeLabels, { compact: true }
      );
      // Evaluate
      try {
        const evalExpr = pendingExpression.startsWith('=') ? pendingExpression : `=${pendingExpression}`;
        const result = G.VolFormula && G.VolFormula.evaluate(evalExpr, scopeValues);
        if (valuePrevEl) {
          if (Number.isFinite(result)) {
            valuePrevEl.textContent = formatIdSmart(result);
            valuePrevEl.className = 'small text-success cparam-value-preview';
          } else {
            valuePrevEl.textContent = 'Error';
            valuePrevEl.className = 'small text-danger cparam-value-preview';
          }
        }
      } catch {
        if (valuePrevEl) { valuePrevEl.textContent = 'Error'; valuePrevEl.className = 'small text-danger cparam-value-preview'; }
      }
      if (openEditorBtn) {
        openEditorBtn.innerHTML = '<i class="bi bi-pencil-square"></i> Edit Formula';
        openEditorBtn.classList.remove('btn-outline-secondary');
        openEditorBtn.classList.add('btn-primary');
      }
    };

    openEditorBtn?.addEventListener('click', () => {
      const lbl = String(labelEl?.value || '').trim() || 'Baru';
      if (G.FormulaEditorModal) {
        G.FormulaEditorModal.openForComputed('', {
          isNew: true, label: lbl, expression: pendingExpression,
          onCreated: (exprBody) => { updateExprDisplay(exprBody); },
        });
      }
    });

    const doCancel = () => tr.remove();
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
      const ep = cfg.endpoints.computedParameters;
      const res = await HTTP.jpost(ep, {
        label, expression: pendingExpression, unit: '', description: '',
      });
      if (!(res.ok && res.data?.ok && res.data?.computed_parameter?.name)) {
        const errMsg = (res.data?.errors && res.data.errors[0]?.message)
          || res.data?.message
          || 'Gagal menyimpan formula turunan ke server.';
        TOAST_err(errMsg);
        return;
      }
      const created = res.data.computed_parameter;
      const code = String(created.name || '').trim();
      if (!isValidComputedParamCode(code)) {
        TOAST_err('Server mengembalikan kode formula turunan tidak valid.');
        return;
      }
      computedParams[code] = {
        expression: String(created.expression || pendingExpression),
        label: String(created.label || label).trim() || label,
        unit: String(created.unit || '').trim(),
        description: String(created.description || '').trim(),
      };
      if (res.data?.synced_at) computedParamSyncAt = String(res.data.synced_at);
      tr.remove();
      persistComputedParams();
    };

    saveBtn?.addEventListener('click', doSave);
    tr.querySelector('.cparam-cancel')?.addEventListener('click', doCancel);
    labelEl?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); openEditorBtn?.click(); }
      if (e.key === 'Escape') doCancel();
    });
  }

  // ── Persist + Sync to Server ───────────────────────────────────────────
  function persistBaseParams() {
    scheduleServerSync();
    evaluateComputedParams();
    renderComputedTable();
    emitParamsChanged();
  }

  function persistComputedParams() {
    dropComputedNameConflicts();
    scheduleComputedServerSync();
    evaluateComputedParams();
    renderComputedTable();
    emitParamsChanged();
  }

  function scheduleServerSync() {
    if (paramSyncTimer) clearTimeout(paramSyncTimer);
    showSyncStatus('pending');
    paramSyncTimer = setTimeout(() => { syncParamsToServer(); }, PARAM_SYNC_DELAY);
  }

  function scheduleComputedServerSync() {
    if (computedSyncTimer) clearTimeout(computedSyncTimer);
    showSyncStatus('pending');
    computedSyncTimer = setTimeout(() => { syncComputedParamsToServer(); }, PARAM_SYNC_DELAY);
  }

  async function promptSyncConflict(kind, serverUpdatedAt) {
    if (syncConflictPromptOpen) return;
    syncConflictPromptOpen = true;
    try {
      const kindLabel = kind === 'computed' ? 'formula turunan' : 'parameter';
      const tsInfo = serverUpdatedAt ? `\nWaktu update server: ${serverUpdatedAt}` : '';
      const ok = await confirmModal(
        `Terdeteksi konflik sinkronisasi ${kindLabel} (data di server lebih baru).${tsInfo}\n\nReload data dari server sekarang?`,
        { title: 'Konflik Sinkronisasi', confirmText: 'Reload', cancelText: 'Tetap Lokal', confirmClass: 'btn btn-warning' }
      );
      if (ok) {
        await loadParamsFromServer({ force: true });
        await loadComputedParamsFromServer({ force: true });
        return;
      }
      TOAST_warn('Perubahan lokal dipertahankan sementara. Lakukan sinkronisasi ulang setelah review.');
    } finally {
      syncConflictPromptOpen = false;
    }
  }

  async function syncParamsToServer() {
    if (!cfg) return;
    try {
      const params = {};
      for (const code of Object.keys(variables)) {
        params[code] = { value: variables[code], label: varLabels[code] || code };
      }
      const res = await HTTP.jpost(cfg.endpoints.parametersSync, {
        parameters: params, mode: 'replace', last_sync_at: baseParamSyncAt || null,
      });
      if (res.status === 409 || res.data?.error === 'conflict') {
        showSyncStatus('error');
        await promptSyncConflict('base', res.data?.server_updated_at || '');
        return;
      }
      if (res.ok && res.data?.ok) {
        if (res.data?.synced_at) baseParamSyncAt = String(res.data.synced_at);
        showSyncStatus('synced');
      } else {
        console.warn('[ParamSidebar] Base param sync failed:', res);
        showSyncStatus('error');
      }
    } catch (err) {
      console.error('[ParamSidebar] Base param sync error:', err);
      showSyncStatus('error');
    }
  }

  async function syncComputedParamsToServer() {
    if (!cfg) return;
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
      const res = await HTTP.jpost(cfg.endpoints.computedParametersSync, {
        computed_parameters: payload, mode: 'replace', last_sync_at: computedParamSyncAt || null,
      });
      if (res.status === 409 || res.data?.error === 'conflict') {
        showSyncStatus('error');
        await promptSyncConflict('computed', res.data?.server_updated_at || '');
        return;
      }
      if (res.ok && res.data?.ok) {
        if (res.data?.synced_at) computedParamSyncAt = String(res.data.synced_at);
        showSyncStatus('synced');
      } else {
        console.warn('[ParamSidebar] Computed param sync failed:', res);
        showSyncStatus('error');
      }
    } catch (err) {
      console.error('[ParamSidebar] Computed param sync error:', err);
      showSyncStatus('error');
    }
  }

  // ── Load from Server ───────────────────────────────────────────────────
  async function loadParamsFromServer(options) {
    if (!cfg) return { ok: false };
    const force = !!(options && options.force);
    try {
      const data = await HTTP.jget(cfg.endpoints.parameters);
      if (data?.ok && Array.isArray(data.parameters)) {
        const serverVars = {};
        const serverLabels = {};
        for (const p of data.parameters) {
          const code = normalizeOpaqueCode(p?.name || '');
          if (!isValidBaseParamCode(code)) continue;
          serverVars[code] = Number(p.value) || 0;
          serverLabels[code] = p.label || code;
        }
        variables = serverVars;
        varLabels = serverLabels;
        dropComputedNameConflicts();
        if (data?.synced_at) baseParamSyncAt = String(data.synced_at);
        evaluateComputedParams();
        renderVarTable();
        renderComputedTable();
        showSyncStatus('synced');
        emitParamsChanged();
        return { ok: true, source: 'server', total: Object.keys(serverVars).length };
      }
      return { ok: false, source: 'server', reason: 'invalid_response' };
    } catch (err) {
      console.warn('[ParamSidebar] Failed to load params from server:', err);
      return { ok: false, source: 'server', error: String(err?.message || err || '') };
    }
  }

  async function loadComputedParamsFromServer(options) {
    if (!cfg) return { ok: false };
    try {
      const data = await HTTP.jget(cfg.endpoints.computedParameters);
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
        if (data?.synced_at) computedParamSyncAt = String(data.synced_at);
        evaluateComputedParams();
        renderComputedTable();
        showSyncStatus('synced');
        emitParamsChanged();
        return { ok: true, source: 'server', total: Object.keys(defs).length };
      }
      return { ok: false, source: 'server', reason: 'invalid_response' };
    } catch (err) {
      console.warn('[ParamSidebar] Failed to load computed params from server:', err);
      return { ok: false, source: 'server', error: String(err?.message || err || '') };
    }
  }

  // ── Import/Export ──────────────────────────────────────────────────────
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

  function csvEscapeCell(value) {
    const raw = String(value ?? '');
    if (!/[",;\t\r\n]/.test(raw)) return raw;
    return `"${raw.replace(/"/g, '""')}"`;
  }

  function csvJoinRow(cells) {
    return (cells || []).map((cell) => csvEscapeCell(cell)).join(',');
  }

  function csvFromVarsAndComputed(varsObj, labelsObj, computedObj) {
    const lines = ['# Base Parameters', csvJoinRow(['Kode', 'Nama', 'Nilai'])];
    const baseCodes = Object.keys(varsObj || {}).sort((a, b) => (labelsObj[a] || a).localeCompare(labelsObj[b] || b, 'id'));
    baseCodes.forEach((code) => {
      lines.push(csvJoinRow([code, String(labelsObj[code] || code), String(varsObj[code])]));
    });
    const computedCodes = Object.keys(computedObj || {}).sort((a, b) => {
      const la = String(computedObj[a]?.label || a);
      const lb = String(computedObj[b]?.label || b);
      return la.localeCompare(lb, 'id');
    });
    if (computedCodes.length) {
      lines.push('', '# Computed Parameters', csvJoinRow(['Kode', 'Nama', 'Formula', 'Unit', 'Deskripsi']));
      computedCodes.forEach((code) => {
        const def = computedObj[code] || {};
        lines.push(csvJoinRow([code, String(def.label || code), String(def.expression || ''), String(def.unit || ''), String(def.description || '')]));
      });
    }
    return `${lines.join('\n')}\n`;
  }

  function exportAsJSON() {
    try {
      const data = JSON.stringify(buildUnifiedParameterPayload(), null, 2);
      const blob = new Blob([data], { type: 'application/json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `parameter_${cfg.projectId}_${tsCompact()}.json`;
      document.body.appendChild(a); a.click(); a.remove();
      TOAST_ok('Parameter diekspor (JSON).');
    } catch { TOAST_err('Gagal export JSON.'); }
  }

  function exportAsCSV() {
    try {
      const csv = csvFromVarsAndComputed(variables, varLabels, computedParams);
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `parameter_${cfg.projectId}_${tsCompact()}.csv`;
      document.body.appendChild(a); a.click(); a.remove();
      TOAST_ok('Parameter diekspor (CSV).');
    } catch { TOAST_err('Gagal export CSV.'); }
  }

  function exportAsXLSX() {
    if (!(G.XLSX && G.XLSX.utils && G.XLSX.writeFile)) {
      TOAST_warn('Export XLSX butuh SheetJS (window.XLSX). Fallback ke CSV.');
      exportAsCSV(); return;
    }
    try {
      const rows = Object.keys(variables)
        .sort((a, b) => (varLabels[a] || a).localeCompare(varLabels[b] || b, 'id'))
        .map((code) => ({ Kode: code, Nama: (varLabels[code] || code), Nilai: variables[code] }));
      const ws = G.XLSX.utils.json_to_sheet(rows, { header: ['Kode', 'Nama', 'Nilai'] });
      const wb = G.XLSX.utils.book_new();
      G.XLSX.utils.book_append_sheet(wb, ws, 'Parameter');
      const cpRows = Object.keys(computedParams || {})
        .sort((a, b) => {
          const la = String(computedParams[a]?.label || a);
          const lb = String(computedParams[b]?.label || b);
          return la.localeCompare(lb, 'id');
        })
        .map((code) => {
          const def = computedParams[code] || {};
          return { Kode: code, Nama: String(def.label || code), Formula: String(def.expression || ''), Unit: String(def.unit || ''), Deskripsi: String(def.description || '') };
        });
      if (cpRows.length) {
        const wsC = G.XLSX.utils.json_to_sheet(cpRows, { header: ['Kode', 'Nama', 'Formula', 'Unit', 'Deskripsi'] });
        G.XLSX.utils.book_append_sheet(wb, wsC, 'Computed Parameter');
      }
      G.XLSX.writeFile(wb, `parameter_${cfg.projectId}_${tsCompact()}.xlsx`);
      TOAST_ok('Parameter diekspor (XLSX).');
    } catch { TOAST_err('Gagal export XLSX.'); }
  }

  async function copyJSONToClipboard() {
    try {
      const data = JSON.stringify(buildUnifiedParameterPayload(), null, 2);
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(data);
      } else {
        const ta = document.createElement('textarea');
        ta.value = data; document.body.appendChild(ta); ta.select();
        document.execCommand('copy'); ta.remove();
      }
      TOAST_ok('JSON disalin ke clipboard.');
    } catch { TOAST_err('Gagal menyalin JSON.'); }
  }

  // ── Import Parsers ─────────────────────────────────────────────────────
  function splitDelimitedLine(line) {
    const text = String(line || '');
    const cells = [];
    let current = '';
    let inQuotes = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      const next = text[i + 1];
      if (ch === '"') {
        if (inQuotes && next === '"') { current += '"'; i++; continue; }
        inQuotes = !inQuotes; continue;
      }
      if (!inQuotes && /[,;\t]/.test(ch)) { cells.push(current.trim()); current = ''; continue; }
      current += ch;
    }
    cells.push(current.trim());
    return cells;
  }

  function toImportRowRef(labelValue, codeValue, idx) {
    const labelText = String(labelValue || '').trim();
    const codeText = normalizeOpaqueCode(codeValue || '');
    if (!labelText) return `Baris ${idx + 1}`;
    if (/^(?:bp|cp)_[1-9][0-9]*$/i.test(labelText)) return `Baris ${idx + 1}`;
    if (codeText && labelText.toLowerCase() === codeText) return `Baris ${idx + 1}`;
    return labelText;
  }

  function parseJSONToVarsLabels(rawText) {
    const obj = JSON.parse(rawText);
    let srcVars = {}, srcLabels = {}, srcComputed = null;
    if (obj && typeof obj === 'object' && obj._format === 'vp-vars-v2') {
      srcVars = (obj.variables && typeof obj.variables === 'object') ? obj.variables : {};
      srcLabels = (obj.labels && typeof obj.labels === 'object') ? obj.labels : {};
      if (obj.computed_parameters && typeof obj.computed_parameters === 'object') srcComputed = obj.computed_parameters;
    } else if (obj && typeof obj === 'object') {
      Object.keys(obj).forEach(code => { srcVars[code] = obj[code]; srcLabels[code] = code; });
    } else throw new Error('format');
    const errors = [], outVars = {}, outLabels = {}, outComputed = {};
    Object.keys(srcVars).forEach((code, idx) => {
      const safe = normalizeOpaqueCode(code);
      const importLabel = String((srcLabels && srcLabels[code]) || '').trim();
      const displayRef = toImportRowRef(importLabel, safe, idx);
      if (!isValidBaseParamCode(safe)) { errors.push(`${displayRef}: format parameter tidak valid`); return; }
      const val = parseNumberOrEmpty(srcVars[code]);
      if (val === '') { errors.push(`${displayRef}: Nilai tidak valid`); return; }
      outVars[safe] = roundHalfUp(Number(val), STORE_PLACES);
      outLabels[safe] = String((srcLabels && srcLabels[code]) || code || '').trim() || safe;
    });
    if (srcComputed && typeof srcComputed === 'object') {
      Object.keys(srcComputed).forEach((code, idx) => {
        const safe = normalizeOpaqueCode(code);
        const def = srcComputed[code] || {};
        const label = String(def.label || safe).trim() || safe;
        const expression = String(def.expression || '').trim();
        const displayRef = toImportRowRef(label, safe, idx);
        if (!isComputedOpaqueCode(safe)) { errors.push(`${displayRef}: format formula parameter tidak valid`); return; }
        if (!expression) { errors.push(`${displayRef}: Formula kosong`); return; }
        outComputed[safe] = { expression, label, unit: String(def.unit || '').trim(), description: String(def.description || '').trim() };
      });
    }
    return { vars: outVars, labels: outLabels, errors, computed: Object.keys(outComputed).length ? outComputed : null };
  }

  function parseCSVToVarsLabels(rawText) {
    const errors = [], nextVars = {}, nextLabels = {}, nextComputed = {};
    const lines = String(rawText || '').split(/\r?\n/);
    let mode = 'base';
    let hasData = false;
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
      const isBaseHeader = /^(kode|code|nama|label)$/.test(c0) && /^(nama|label|nilai|value)$/.test(c1);
      const isComputedHeader = /^(kode|code)$/.test(c0) && /^(nama|label)$/.test(c1) && /^(formula|expression)$/.test(c2);
      if (isBaseHeader) { mode = 'base'; return; }
      if (isComputedHeader) { mode = 'computed'; return; }

      if (mode === 'computed') {
        const code = normalizeOpaqueCode(cells[0] || '');
        const label = String(cells[1] || code || '').trim();
        const expression = String(cells[2] || '').trim();
        const unit = String(cells[3] || '').trim();
        const description = String(cells[4] || '').trim();
        const displayRef = toImportRowRef(label, code, idx);
        if (!isComputedOpaqueCode(code)) { errors.push(`${displayRef}: Format formula parameter tidak sesuai`); return; }
        if (!label) { errors.push(`Baris ${idx + 1}: Label formula parameter kosong`); return; }
        if (!expression) { errors.push(`Baris ${idx + 1}: Formula kosong`); return; }
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
      nextVars[code] = roundHalfUp(Number(n), STORE_PLACES);
      nextLabels[code] = label;
      hasData = true;
    });
    if (!hasData) throw new Error('csv-empty');
    if (!Object.keys(nextVars).length && !Object.keys(nextComputed).length) throw new Error('csv-none');
    return { vars: nextVars, labels: nextLabels, errors, computed: Object.keys(nextComputed).length ? nextComputed : null };
  }

  async function parseXLSXToVarsLabels(file) {
    if (!(G.XLSX && G.XLSX.read)) throw new Error('no-xlsx-lib');
    const ab = await file.arrayBuffer();
    const wb = G.XLSX.read(ab);
    const errors = [], nextVars = {}, nextLabels = {}, nextComputed = {};

    const baseSheetName = wb.SheetNames[0];
    const baseWs = wb.Sheets[baseSheetName];
    const baseArr = G.XLSX.utils.sheet_to_json(baseWs, { header: 1 });
    const baseRows = baseArr.filter((r) => r && (r[0] != null || r[1] != null));
    const baseBody = (baseRows[0] && /kode|code|nama|label/i.test(String(baseRows[0][0] || '')) && /nama|label|nilai|value/i.test(String(baseRows[0][1] || '')))
      ? baseRows.slice(1) : baseRows;

    baseBody.forEach((r, idx) => {
      const code = normalizeOpaqueCode(r[0] ?? '');
      const hasLabelCol = (r[2] != null);
      const label = String((hasLabelCol ? (r[1] ?? code) : code)).trim();
      const displayRef = toImportRowRef(label, code, idx);
      const n = parseNumberOrEmpty(hasLabelCol ? r[2] : r[1]);
      if (!isValidBaseParamCode(code)) { errors.push(`${displayRef}: Format parameter tidak sesuai`); return; }
      if (!label) { errors.push(`Baris ${idx + 1}: Label kosong`); return; }
      if (n === '') { errors.push(`Baris ${idx + 1}: Nilai bukan angka`); return; }
      nextVars[code] = roundHalfUp(Number(n), STORE_PLACES);
      nextLabels[code] = label;
    });

    for (const sheetName of wb.SheetNames.slice(1)) {
      const ws = wb.Sheets[sheetName];
      const arr = G.XLSX.utils.sheet_to_json(ws, { header: 1 });
      const rows = arr.filter((r) => r && (r[0] != null || r[1] != null || r[2] != null));
      if (!rows.length) continue;
      const maybeHeader = rows[0];
      const isComputedHeader = /kode|code/i.test(String(maybeHeader[0] || '')) && /nama|label/i.test(String(maybeHeader[1] || '')) && /formula|expression/i.test(String(maybeHeader[2] || ''));
      if (!isComputedHeader) continue;
      rows.slice(1).forEach((r, idx) => {
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
      break;
    }

    if (!Object.keys(nextVars).length && !Object.keys(nextComputed).length) throw new Error('xlsx-none');
    return { vars: nextVars, labels: nextLabels, errors, computed: Object.keys(nextComputed).length ? nextComputed : null };
  }

  async function handleUnifiedImport(file) {
    if (!file) return;
    if (file.size > MAX_IMPORT_SIZE_BYTES) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
      TOAST_warn(`File terlalu besar (${sizeMB} MB). Maksimal ${MAX_IMPORT_SIZE_BYTES / (1024 * 1024)} MB.`);
      return;
    }
    const name = file.name || '';
    const ext = (/\.(\w+)$/.exec(name)?.[1] || '').toLowerCase();
    try {
      let parsed = { vars: {}, labels: {}, errors: [] };
      if (ext === 'json') { parsed = parseJSONToVarsLabels(await file.text()); }
      else if (ext === 'csv') { parsed = parseCSVToVarsLabels(await file.text()); }
      else if (ext === 'xlsx') { parsed = await parseXLSXToVarsLabels(file); }
      else throw new Error('format');

      if (parsed.errors && parsed.errors.length) {
        const errText = 'Beberapa baris diabaikan:\n' + parsed.errors.slice(0, 10).join('\n') + (parsed.errors.length > 10 ? '\n...' : '');
        await alertModal(errText, { title: 'Import Parameter' });
      }
      const nextVars = parsed.vars, nextLabels = parsed.labels;
      const existingCodes = new Set(Object.keys(variables));
      const codes = Object.keys(nextVars);
      const adds = codes.filter(c => !existingCodes.has(c)).length;
      const updates = codes.filter(c => existingCodes.has(c)).length;
      const summary = `Ditemukan ${codes.length} parameter.\nTambah: ${adds}\nPerbarui: ${updates}.\nPilih Merge untuk gabungkan atau Replace untuk mengganti.`;
      const doMerge = await confirmModal(summary, {
        title: 'Konfirmasi Import', confirmText: 'Merge', cancelText: 'Replace',
      });
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
      }

      persistBaseParams();
      if (cpCount) persistComputedParams();
      renderVarTable();

      const msg = cpCount
        ? `Parameter diimport (${Object.keys(nextVars).length} base + ${cpCount} computed).`
        : 'Parameter diimport.';
      TOAST_action(msg, [{
        label: 'Undo', class: 'btn-outline-warning',
        onClick: () => {
          variables = prevVars; varLabels = prevLabels; computedParams = prevComputed;
          persistBaseParams(); persistComputedParams();
          renderVarTable();
          TOAST_ok('Import dibatalkan (Undo).');
        },
      }]);
    } catch (e) {
      if (String(e.message).includes('no-xlsx-lib')) TOAST_warn('Import XLSX butuh SheetJS (window.XLSX). Gunakan CSV/JSON.');
      else if (String(e.message).includes('format')) TOAST_err('Format file tidak dikenali.');
      else TOAST_err('Gagal import.');
    }
  }

  // ── Template XLSX Generator ────────────────────────────────────────────
  function generateTemplateXLSX() {
    if (!(G.XLSX && G.XLSX.utils && G.XLSX.writeFile)) {
      TOAST_warn('Butuh SheetJS untuk XLSX');
      return;
    }
    const rows = [
      { Kode: 'bp_1', Nama: 'Panjang', Nilai: 0 },
      { Kode: 'bp_2', Nama: 'Lebar', Nilai: 0 },
      { Kode: 'bp_3', Nama: 'Tinggi', Nilai: 0 },
    ];
    const ws = G.XLSX.utils.json_to_sheet(rows, { header: ['Kode', 'Nama', 'Nilai'] });
    const wb = G.XLSX.utils.book_new();
    G.XLSX.utils.book_append_sheet(wb, ws, 'Parameter');
    G.XLSX.writeFile(wb, 'parameters_template.xlsx');
  }

  // ── Event Callbacks ────────────────────────────────────────────────────
  function emitParamsChanged() {
    const snapshot = getSnapshot();
    changeCallbacks.forEach(cb => {
      try { cb(snapshot); } catch (err) { console.error('[ParamSidebar] callback error:', err); }
    });
  }

  // ── Tabs ───────────────────────────────────────────────────────────────
  function setActiveSidebarPane(paneName) {
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
  }

  // ── Sidebar Search Init ────────────────────────────────────────────────
  function initSidebarSearch() {
    if (!$searchInput) return;
    sidebarSearchQuery = String($searchInput.value || '').trim();
    syncSidebarSearchClearButton();

    let timer = null;
    $searchInput.addEventListener('input', () => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => {
        sidebarSearchQuery = String($searchInput.value || '').trim();
        syncSidebarSearchClearButton();
        renderVarTable();
        renderComputedTable();
        timer = null;
      }, 120);
    });
    $searchInput.addEventListener('keydown', (ev) => {
      if (ev.key !== 'Escape') return;
      if (!$searchInput.value) return;
      ev.preventDefault();
      $searchInput.value = '';
      sidebarSearchQuery = '';
      syncSidebarSearchClearButton();
      renderVarTable();
      renderComputedTable();
      $searchInput.focus();
    });
    if ($searchClear) {
      $searchClear.addEventListener('click', () => {
        if (!$searchInput.value) return;
        $searchInput.value = '';
        sidebarSearchQuery = '';
        syncSidebarSearchClearButton();
        renderVarTable();
        renderComputedTable();
        $searchInput.focus();
      });
    }
  }

  function syncSidebarSearchClearButton() {
    if ($searchClear) $searchClear.hidden = sidebarSearchQueryText() === '';
  }

  // ── Resize Handle ──────────────────────────────────────────────────────
  function initResizeHandle() {
    const resizer = $container ? $container.querySelector('.dp-resizer') : null;
    if (!resizer) return;
    let startX = 0, startW = 0;
    const onMouseMove = (e) => {
      const dx = startX - e.clientX;
      const newW = Math.max(280, Math.min(800, startW + dx));
      $container.style.width = `${newW}px`;
    };
    const onMouseUp = () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      document.body.style.userSelect = '';
    };
    resizer.addEventListener('mousedown', (e) => {
      e.preventDefault();
      startX = e.clientX;
      startW = $container.offsetWidth;
      document.body.style.userSelect = 'none';
      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
    });
  }

  // ── Init & DOM Binding ─────────────────────────────────────────────────
  function bindDOM() {
    if (!$container) return;
    $varTable = $container.querySelector('#ta-var-table') || $container.querySelector('[id$="-var-table"]');
    $cParamTable = $container.querySelector('#ta-cparam-table') || $container.querySelector('[id$="-cparam-table"]');
    $btnVarAdd = $container.querySelector('#ta-var-add') || $container.querySelector('[id$="-var-add"]');
    $btnCParamAdd = $container.querySelector('#ta-cparam-add') || $container.querySelector('[id$="-cparam-add"]');
    $paramCount = $container.querySelector('#ta-param-count') || $container.querySelector('[id$="-param-count"]');
    $cParamCount = $container.querySelector('#ta-cparam-count') || $container.querySelector('[id$="-cparam-count"]');
    $tabBaseCount = $container.querySelector('#ta-tab-base-count') || $container.querySelector('[id$="-tab-base-count"]');
    $tabComputedCount = $container.querySelector('#ta-tab-computed-count') || $container.querySelector('[id$="-tab-computed-count"]');
    $searchInput = $container.querySelector('#ta-sidebar-search') || $container.querySelector('[id$="-sidebar-search"]');
    $searchClear = $container.querySelector('#ta-sidebar-search-clear') || $container.querySelector('[id$="-sidebar-search-clear"]');
    $syncIndicator = $container.querySelector('#ta-param-sync-status') || $container.querySelector('[id$="-param-sync-status"]');
    paneTabs = Array.from($container.querySelectorAll('.dp-ps-pane-tab'));
    panes = Array.from($container.querySelectorAll('.dp-ps-pane'));
  }

  function bindEvents() {
    // Tab clicks
    paneTabs.forEach((btn) => {
      btn.addEventListener('click', () => setActiveSidebarPane(btn.dataset.pane || 'base'));
    });

    // Add base parameter
    if ($btnVarAdd) {
      $btnVarAdd.addEventListener('click', handleAddBaseParam);
    }

    // Add computed parameter
    if ($btnCParamAdd) {
      $btnCParamAdd.addEventListener('click', handleAddComputedParam);
    }

    // Import
    const btnImport = $container.querySelector('#ta-var-import-btn');
    const fileInput = $container.querySelector('#ta-var-import');
    if (btnImport && fileInput) {
      btnImport.addEventListener('click', () => fileInput.click());
      fileInput.addEventListener('change', (e) => {
        const f = e.target.files && e.target.files[0];
        try { handleUnifiedImport(f); } finally { fileInput.value = ''; }
      });
    }

    // Export
    const bindExport = (id, fn) => {
      const el = $container.querySelector(`#${id}`) || document.getElementById(id);
      if (el) el.addEventListener('click', fn);
    };
    bindExport('ta-export-json', exportAsJSON);
    bindExport('ta-export-csv', exportAsCSV);
    bindExport('ta-export-xlsx', exportAsXLSX);
    bindExport('ta-export-copy-json', copyJSONToClipboard);

    // Template XLSX generator
    const btnTemplate = $container.querySelector('#ta-template-xlsx-gen') || document.getElementById('ta-template-xlsx-gen');
    if (btnTemplate) btnTemplate.addEventListener('click', generateTemplateXLSX);

    // Close sidebar button
    const closeBtn = $container.querySelector('[data-action="close-param-sidebar"]');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        $container.classList.remove('is-open');
        $container.classList.remove('is-visible');
        $container.setAttribute('aria-hidden', 'true');
      });
    }

    // Search
    initSidebarSearch();

    // Resize
    initResizeHandle();
  }

  // ── Public API ─────────────────────────────────────────────────────────
  function init(config) {
    if (!config) throw new Error('ParamSidebarEditor.init() requires config');
    cfg = config;
    destroyed = false;
    $container = config.container;
    if (!$container) {
      console.warn('[ParamSidebarEditor] container not found');
      return;
    }
    bindDOM();
    bindEvents();

    // Load from server
    loadParamsFromServer({ force: true }).then(() => {
      loadComputedParamsFromServer({ force: true });
    });
  }

  function destroy() {
    destroyed = true;
    if (paramSyncTimer) clearTimeout(paramSyncTimer);
    if (computedSyncTimer) clearTimeout(computedSyncTimer);
    changeCallbacks = [];
    cfg = null;
    $container = null;
  }

  function getSnapshot() {
    evaluateComputedParams();
    return { ...variables, ...computedValues };
  }

  function getBaseVariables() {
    return { ...variables };
  }

  function getBaseLabels() {
    return { ...varLabels };
  }

  function getComputedParams() {
    return JSON.parse(JSON.stringify(computedParams || {}));
  }

  function getComputedValues() {
    evaluateComputedParams();
    return { ...computedValues };
  }

  async function refresh() {
    await loadParamsFromServer({ force: true });
    await loadComputedParamsFromServer({ force: true });
  }

  function onParamsChanged(cb) {
    if (typeof cb === 'function') changeCallbacks.push(cb);
  }

  // Expose for FormulaEditorModal
  function updateComputedParam(code, def) {
    computedParams[code] = def;
    persistComputedParams();
  }

  function deleteComputedParam(code) {
    delete computedParams[code];
    persistComputedParams();
  }

  // ── Expose global ──────────────────────────────────────────────────────
  G.ParamSidebarEditor = {
    init,
    destroy,
    getSnapshot,
    getBaseVariables,
    getBaseLabels,
    getComputedParams,
    getComputedValues,
    refresh,
    onParamsChanged,
    // Internal API for FormulaEditorModal
    _getFormulaScopeValues: getFormulaScopeValues,
    _getFormulaScopeLabels: getFormulaScopeLabels,
    _buildComputedParamScope: buildComputedParamScope,
    _evaluateComputedParams: evaluateComputedParams,
    _updateComputedParam: updateComputedParam,
    _deleteComputedParam: deleteComputedParam,
    _renderVarTable: renderVarTable,
    _renderComputedTable: renderComputedTable,
    _escapeHtml: escapeHtml,
    _formatIdSmart: formatIdSmart,
    _humanizeFormulaError: humanizeFormulaError,
    _translateFormulaForPreview: translateFormulaForPreview,
    _buildFormulaChipHtml: buildFormulaChipHtml,
    _confirmModal: confirmModal,
    _TOAST_ok: TOAST_ok,
    _TOAST_warn: TOAST_warn,
    _TOAST_err: TOAST_err,
  };
})();
