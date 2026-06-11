/**
 * Shared formula editor modal for computed parameters in Template AHSP.
 * Aligned to Volume modal UX/class hooks (vp-*).
 */
(function () {
  'use strict';

  const G = (typeof window !== 'undefined') ? window : globalThis;
  const PSE = () => G.ParamSidebarEditor;
  let FORMULA_LABEL_ONLY_UI_ENABLED = true;
  const RESERVED = new Set(['sum', 'min', 'max', 'round', 'avg', 'abs', 'floor', 'ceil', 'pow', 'pi', 'e', 'true', 'false']);
  const ALLOWED_FUNCS = new Set(['sum', 'min', 'max', 'round', 'avg', 'abs', 'floor', 'ceil', 'pow']);
  const FN_SUGGEST = [
    { name: 'sum', label: 'SUM()', hint: 'Jumlah', insertText: 'SUM()', caretOffset: 4 },
    { name: 'min', label: 'MIN()', hint: 'Nilai minimum', insertText: 'MIN()', caretOffset: 4 },
    { name: 'max', label: 'MAX()', hint: 'Nilai maksimum', insertText: 'MAX()', caretOffset: 4 },
    { name: 'round', label: 'ROUND()', hint: 'Pembulatan', insertText: 'ROUND()', caretOffset: 6 },
    { name: 'avg', label: 'AVG()', hint: 'Rata-rata', insertText: 'AVG()', caretOffset: 4 },
    { name: 'abs', label: 'ABS()', hint: 'Nilai absolut', insertText: 'ABS()', caretOffset: 4 },
    { name: 'floor', label: 'FLOOR()', hint: 'Bulat ke bawah', insertText: 'FLOOR()', caretOffset: 6 },
    { name: 'ceil', label: 'CEIL()', hint: 'Bulat ke atas', insertText: 'CEIL()', caretOffset: 5 },
    { name: 'pow', label: 'POW()', hint: 'Pangkat', insertText: 'POW()', caretOffset: 4 }
  ];

  let modalId = 'taFormulaEditorModal';
  let paletteModalId = 'taParamPaletteModal';
  let prefix = 'ta-fe-';
  let palettePrefix = 'ta-palette-';

  let bsModal = null;
  let bsPaletteModal = null;
  let ctx = null;
  let undoExpression = '';
  let resolverToken = '';
  let hasBlockingError = false;
  let showInlineValues = true;
  let viewMode = 'raw';

  let $modal = null;
  let $metaEl = null;
  let $nameWrap = null;
  let $nameInput = null;
  let $inputEl = null;
  let $highlightLayer = null;
  let $highlightContent = null;
  let $chipPreview = null;
  let $previewEl = null;
  let $blockEl = null;
  let $blockText = null;
  let $resolverEl = null;
  let $resolverText = null;
  let $resolveBtn = null;
  let $applyBtn = null;
  let $undoBtn = null;
  let $toggleViewBtn = null;
  let $paletteSearch = null;
  let $paletteList = null;

  let suggest = { box: null, ul: null, items: [], idx: -1 };
  const formulaInputMaskState = new WeakMap();

  function escapeHtml(s) {
    return PSE()?._escapeHtml?.(s)
      || String(s).replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  }
  function formatIdSmart(n) { return PSE()?._formatIdSmart?.(n) || String(n); }
  function translateFormulaForPreview(expr, opts) { return PSE()?._translateFormulaForPreview?.(expr, opts) || expr; }
  function buildFormulaChipHtml(expr, labels, opts) { return PSE()?._buildFormulaChipHtml?.(expr, labels, opts) || escapeHtml(expr); }
  function humanizeFormulaError(msg, labels) { return PSE()?._humanizeFormulaError?.(msg, labels) || msg; }

  function normKey(s) { return String(s || '').toLowerCase().replace(/[_\s]+/g, ' ').trim(); }
  function compactKey(s) { return normKey(s).replace(/\s+/g, ''); }

  function getScopeValues(excludeCode) {
    if (excludeCode && PSE()?._buildComputedParamScope) return PSE()._buildComputedParamScope(excludeCode).scopeValues;
    return PSE()?._getFormulaScopeValues?.() || {};
  }
  function getScopeLabels(excludeCode) {
    if (excludeCode && PSE()?._buildComputedParamScope) return PSE()._buildComputedParamScope(excludeCode).scopeLabels;
    return PSE()?._getFormulaScopeLabels?.() || {};
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
    const labels = options.labels || {};
    const rawWithEq = normalizeFormulaLeadingEquals(source, { forceFormula });
    const rawBody = rawWithEq.startsWith('=') ? rawWithEq.slice(1) : rawWithEq;
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
      if (tokenStart > rawPos) display += rawBody.slice(rawPos, tokenStart);

      if (Object.prototype.hasOwnProperty.call(labels, tokenLower)) {
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

  function getCurrentScopeLabels(excludeCode = '') {
    return getScopeLabels(excludeCode);
  }

  function setInputFormulaRaw(inputEl, rawExpr, options = {}) {
    if (!inputEl) return String(rawExpr || '');
    const rawText = String(rawExpr || '');
    if (!FORMULA_LABEL_ONLY_UI_ENABLED) {
      formulaInputMaskState.delete(inputEl);
      const normalized = normalizeFormulaLeadingEquals(rawText, {
        forceFormula: options.forceFormula === true || rawText.trim().startsWith('='),
      });
      inputEl.value = normalized;
      return normalized;
    }
    const labels = options.labels || getCurrentScopeLabels(options.excludeCode || '');
    const normalized = normalizeFormulaLeadingEquals(rawText, {
      forceFormula: options.forceFormula === true || rawText.trim().startsWith('='),
    });
    const state = buildFormulaLabelMaskState(normalized, {
      forceFormula: true,
      labels,
    });
    formulaInputMaskState.set(inputEl, state);
    inputEl.value = String(state.display || '').replace(/=/g, '');
    if (Number.isFinite(options.caretRawPos)) {
      const dispPos = rawPosToDisplayPos(options.caretRawPos, state);
      inputEl.setSelectionRange(dispPos, dispPos);
    } else if (options.focusEnd) {
      const end = state.display.length;
      inputEl.setSelectionRange(end, end);
    }
    return state.raw;
  }

  function getInputFormulaRaw(inputEl, fallback = '', options = {}) {
    if (!inputEl) return String(fallback || '');
    if (!FORMULA_LABEL_ONLY_UI_ENABLED) return String(inputEl.value || fallback || '');
    const state = formulaInputMaskState.get(inputEl);
    if (state && typeof state.raw === 'string') {
      return normalizeFormulaLeadingEquals(state.raw, { forceFormula: true });
    }
    const next = setInputFormulaRaw(inputEl, fallback || inputEl.value || '', {
      forceFormula: true,
      excludeCode: options.excludeCode || '',
    });
    return String(next || '');
  }

  function syncMaskedInputFromDisplayEdit(inputEl, options = {}) {
    if (!inputEl) return '';
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
      prefix < prevDisplay.length &&
      prefix < nextDisplay.length &&
      prevDisplay[prefix] === nextDisplay[prefix]
    ) {
      prefix++;
    }

    let suffix = 0;
    while (
      suffix < (prevDisplay.length - prefix) &&
      suffix < (nextDisplay.length - prefix) &&
      prevDisplay[prevDisplay.length - 1 - suffix] === nextDisplay[nextDisplay.length - 1 - suffix]
    ) {
      suffix++;
    }

    const prevChangedEnd = prevDisplay.length - suffix;
    const nextChangedEnd = nextDisplay.length - suffix;
    const inserted = nextDisplay.slice(prefix, nextChangedEnd);

    const overlapSpans = state.spans.filter((span) => (prefix < span.displayEnd && prevChangedEnd > span.displayStart));
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
    return setInputFormulaRaw(inputEl, nextRaw, {
      forceFormula: true,
      caretRawPos,
      excludeCode: options.excludeCode || '',
    });
  }

  function insertRawTokenIntoMaskedInput(inputEl, rawToken, options = {}) {
    if (!FORMULA_LABEL_ONLY_UI_ENABLED || !inputEl) return false;
    const insertText = String(rawToken || '');
    if (!insertText) return false;
    const fallbackRaw = getInputFormulaRaw(inputEl, inputEl.value || '', { excludeCode: options.excludeCode || '' });
    const labels = getCurrentScopeLabels(options.excludeCode || '');
    const state = formulaInputMaskState.get(inputEl)
      || buildFormulaLabelMaskState(fallbackRaw, { forceFormula: true, labels });
    formulaInputMaskState.set(inputEl, state);

    const caret = getCaretWord();
    const displayStart = caret ? caret.start : (inputEl.selectionStart ?? state.display.length);
    const displayEnd = caret ? caret.end : displayStart;
    const rawStart = displayPosToRawPos(displayStart, state);
    const rawEnd = displayPosToRawPos(displayEnd, state);
    const nextRawBody = state.rawBody.slice(0, rawStart) + insertText + state.rawBody.slice(rawEnd);
    const nextRaw = normalizeFormulaLeadingEquals(nextRawBody, { forceFormula: true });
    const caretOffset = Number.isFinite(options.caretOffset)
      ? Math.max(0, Math.min(Number(options.caretOffset), insertText.length))
      : insertText.length;
    const caretRawPos = rawStart + caretOffset;
    setInputFormulaRaw(inputEl, nextRaw, {
      forceFormula: true,
      caretRawPos,
      excludeCode: options.excludeCode || '',
    });
    return true;
  }

  function isRangeInsideAnySpan(start, end, spans = []) {
    return spans.some((span) => start >= span.displayStart && end <= span.displayEnd);
  }

  function bindDOM() {
    $modal = document.getElementById(modalId);
    if (!$modal) return;
    const $ = (id) => document.getElementById(`${prefix}${id}`);
    $metaEl = $('meta');
    $nameWrap = $('computed-name-wrap');
    $nameInput = $('computed-name');
    $inputEl = $('input');
    $highlightLayer = $('highlight-layer');
    $highlightContent = $('highlight');
    $chipPreview = $('chip-preview');
    $previewEl = $('preview');
    $blockEl = $('block');
    $blockText = $('block-text');
    $resolverEl = $('resolver');
    $resolverText = $('resolver-text');
    $resolveBtn = $('resolve-btn');
    $applyBtn = $('apply');
    $undoBtn = $('undo');
    $toggleViewBtn = $('toggle-view');
    $paletteSearch = document.getElementById(`${palettePrefix}search`);
    $paletteList = document.getElementById(`${palettePrefix}list`);
  }

  function ensureModal() {
    if (bsModal) return bsModal;
    $modal = document.getElementById(modalId);
    if (!$modal || !G.bootstrap?.Modal) return null;
    bsModal = G.bootstrap.Modal.getOrCreateInstance($modal, { backdrop: false, keyboard: true });
    return bsModal;
  }
  function ensurePaletteModal() {
    if (bsPaletteModal) return bsPaletteModal;
    const el = document.getElementById(paletteModalId);
    if (!el || !G.bootstrap?.Modal) return null;
    bsPaletteModal = G.bootstrap.Modal.getOrCreateInstance(el, { backdrop: false, keyboard: true });
    return bsPaletteModal;
  }

  function syncHighlightScroll() {
    if (!$inputEl || !$highlightContent) return;
    $highlightContent.style.transform = `translate(${-($inputEl.scrollLeft || 0)}px, ${-($inputEl.scrollTop || 0)}px)`;
  }

  function setPreviewState(state, opts = {}) {
    if (!$previewEl) return;
    const label = $previewEl.querySelector('.fx-preview-label-text');
    const value = $previewEl.querySelector('.fx-preview-value-text');
    const err = $previewEl.querySelector('.fx-preview-error-line');
    $previewEl.dataset.previewState = state;
    if (state === 'success') {
      if (label) label.textContent = opts.label || '-';
      if (value) value.textContent = opts.value || '-';
      if (err) { err.textContent = ''; err.classList.add('d-none'); }
      return;
    }
    if (label) label.textContent = '-';
    if (value) value.textContent = '-';
    if (state === 'error') {
      if (err) { err.textContent = opts.error || 'Error'; err.classList.remove('d-none'); }
    } else if (err) {
      err.textContent = '';
      err.classList.add('d-none');
    }
  }

  function setBlockState(blocked, reason = '') {
    hasBlockingError = !!blocked;
    const msg = String(reason || '').trim();
    if ($applyBtn) {
      $applyBtn.disabled = hasBlockingError;
      $applyBtn.setAttribute('title', hasBlockingError ? msg : '');
    }
    if ($blockEl && $blockText) {
      const active = hasBlockingError && !!msg;
      $blockEl.classList.toggle('d-none', !active);
      $blockText.textContent = active ? msg : '';
    }
  }

  function setResolverState(token = '', message = '') {
    resolverToken = String(token || '').trim().toLowerCase();
    if (!$resolverEl || !$resolverText || !$resolveBtn) return;
    const hasToken = !!resolverToken;
    const info = String(message || '').trim();
    const active = hasToken || !!info;
    $resolverEl.classList.toggle('d-none', !active);
    if (!active) {
      $resolverText.textContent = '';
      $resolveBtn.disabled = true;
      $resolveBtn.classList.add('d-none');
      return;
    }
    $resolverText.textContent = info || `Token "${resolverToken}" belum dikenali. Pilih parameter pengganti.`;
    $resolveBtn.disabled = !hasToken;
    $resolveBtn.classList.toggle('d-none', !hasToken);
  }
  function updateUndoButtonState() {
    if ($undoBtn) $undoBtn.disabled = !undoExpression;
  }

  function renderInvalidOverlay(tokens = []) {
    if (!$highlightContent || !$inputEl) return;
    const text = String($inputEl.value || '');
    if (!text) {
      $highlightContent.innerHTML = '&nbsp;';
      syncHighlightScroll();
      return;
    }
    const spans = tokens.slice().sort((a, b) => a.start - b.start);
    const html = [];
    let cursor = 0;
    spans.forEach((span) => {
      const start = Math.max(cursor, Number(span.start) || 0);
      const end = Math.max(start, Number(span.end) || start);
      if (start > cursor) html.push(escapeHtml(text.slice(cursor, start)));
      if (end > start) html.push(`<mark class="vp-fe-invalid-token">${escapeHtml(text.slice(start, end))}</mark>`);
      cursor = Math.max(cursor, end);
    });
    if (cursor < text.length) html.push(escapeHtml(text.slice(cursor)));
    $highlightContent.innerHTML = html.join('') || '&nbsp;';
    syncHighlightScroll();
  }

  function collectInvalidTokens(displayText, excludeCode) {
    const input = String(displayText || '');
    if (!input) return [];
    const scopeLabels = getScopeLabels(excludeCode);
    const scopeValues = getScopeValues(excludeCode);
    const known = new Set([...Object.keys(scopeLabels), ...Object.keys(scopeValues)].map((c) => String(c || '').toLowerCase()));
    const state = formulaInputMaskState.get($inputEl);
    const spans = Array.isArray(state?.spans) ? state.spans : [];
    const bad = [];
    const re = /[A-Za-z_][A-Za-z0-9_'-]*/g;
    let m;
    while ((m = re.exec(input)) !== null) {
      const token = String(m[0] || '');
      const start = m.index;
      const end = start + token.length;
      if (isRangeInsideAnySpan(start, end, spans)) continue;
      const safe = token.replace(/'/g, '').toLowerCase();
      const nextChars = input.slice(end);
      const nextNonSpace = (nextChars.match(/\S/) || [])[0] || '';
      if (ALLOWED_FUNCS.has(safe) && nextNonSpace === '(') continue;
      if (RESERVED.has(safe)) continue;
      if (known.has(safe)) continue;
      bad.push({ token, start, end });
    }
    return bad.sort((a, b) => a.start - b.start);
  }

  function renderChipPreview(rawExpr, scopeLabels) {
    if (!$chipPreview) return;
    const expr = String(rawExpr || '').replace(/^=/, '').trim();
    if (!expr) {
      $chipPreview.classList.add('is-empty');
      $chipPreview.innerHTML = escapeHtml('Chip preview: pilih parameter agar formula lebih mudah dibaca.');
      return;
    }
    $chipPreview.classList.remove('is-empty');
    $chipPreview.innerHTML = buildFormulaChipHtml(expr, scopeLabels, { compact: false });
  }

  function setViewMode(mode, opts = {}) {
    viewMode = mode === 'chip' ? 'chip' : 'raw';
    const isRaw = viewMode === 'raw';
    const wrap = $modal?.querySelector('.vp-fe-input-wrap');
    if (wrap) wrap.classList.toggle('d-none', !isRaw);
    if ($highlightLayer) $highlightLayer.classList.toggle('d-none', !isRaw);
    if ($chipPreview) {
      $chipPreview.classList.toggle('d-none', isRaw);
      $chipPreview.classList.toggle('is-clickable', !isRaw);
      $chipPreview.setAttribute('role', 'button');
      $chipPreview.setAttribute('tabindex', '0');
      $chipPreview.setAttribute('title', 'Klik untuk edit formula');
    }
    if ($toggleViewBtn) {
      $toggleViewBtn.setAttribute('aria-pressed', isRaw ? 'true' : 'false');
      $toggleViewBtn.innerHTML = isRaw
        ? '<i class="bi bi-eye me-1"></i>Lihat Chip'
        : '<i class="bi bi-pencil-square me-1"></i>Edit Formula';
    }
    if (opts.focus && isRaw && $inputEl) {
      const preserve = opts.caret === 'preserve';
      const start = $inputEl.selectionStart;
      const end = $inputEl.selectionEnd;
      $inputEl.focus();
      if (preserve && Number.isInteger(start) && Number.isInteger(end)) $inputEl.setSelectionRange(start, end);
      else {
        const len = $inputEl.value.length;
        $inputEl.setSelectionRange(len, len);
      }
      syncHighlightScroll();
    }
  }

  function updatePreview() {
    if (!ctx || !$inputEl) return;
    const excludeCode = ctx.contextType === 'computed' ? ctx.code : '';
    const rawValue = FORMULA_LABEL_ONLY_UI_ENABLED
      ? syncMaskedInputFromDisplayEdit($inputEl, { excludeCode })
      : String($inputEl.value || '');
    const raw = String(rawValue || '').trim();
    const scopeLabels = getScopeLabels(excludeCode);
    const scopeValues = getScopeValues(excludeCode);
    const invalid = collectInvalidTokens(String($inputEl.value || ''), excludeCode);

    renderInvalidOverlay(invalid);
    renderChipPreview(raw, scopeLabels);
    updateUndoButtonState();

    if (!raw || raw === '=') {
      setResolverState('', '');
      setPreviewState('empty');
      setBlockState(false, '');
      return;
    }

    if (invalid.length) {
      const tokenList = invalid.slice(0, 3).map((t) => `"${t.token}"`).join(', ');
      const suffix = invalid.length > 3 ? '...' : '';
      const msg = `Token tidak valid: ${tokenList}${suffix}. Hapus/ganti token lalu pilih dari autosuggestion.`;
      setPreviewState('error', { error: msg });
      setResolverState('', msg);
      setBlockState(true, msg);
      return;
    }

    const expr = raw.startsWith('=') ? raw : `=${raw}`;
    try {
      if (!G.VolFormula || typeof G.VolFormula.evaluate !== 'function') throw new Error('Formula engine tidak tersedia');
      const value = G.VolFormula.evaluate(expr, scopeValues);
      if (!Number.isFinite(value)) throw new Error('Hasil formula tidak valid (NaN)');
      const labelPreview = translateFormulaForPreview(raw, {
        mode: 'label',
        scopeLabels,
        scopeValues,
        includeInlineValues: showInlineValues
      });
      setPreviewState('success', { label: labelPreview, value: formatIdSmart(value) });
      setResolverState('', '');
      setBlockState(false, '');
    } catch (err) {
      const message = String(err?.message || 'Formula tidak valid');
      setPreviewState('error', { error: humanizeFormulaError(message, scopeLabels) });
      const unknown = message.match(/Variabel tidak dikenal:\s*(.+)$/i);
      if (unknown) {
        const token = String(unknown[1] || '').trim().toLowerCase();
        setResolverState(token, 'Parameter pada formula tidak ditemukan. Pilih parameter pengganti dari palette.');
        setBlockState(true, 'Parameter pada formula tidak ditemukan.');
      } else {
        setResolverState('', message);
        setBlockState(true, message);
      }
    }
  }

  function getCaretWord() {
    if (!$inputEl) return { word: '', start: 0, end: 0 };
    const text = String($inputEl.value || '');
    const pos = $inputEl.selectionStart || 0;
    let start = pos;
    let end = pos;
    while (start > 0 && /[A-Za-z0-9_]/.test(text[start - 1])) start--;
    while (end < text.length && /[A-Za-z0-9_]/.test(text[end])) end++;
    return { word: text.slice(start, end), start, end };
  }

  function shouldShowSuggestionsForEmptyQuery() {
    if (!$inputEl) return false;
    const text = String($inputEl.value || '');
    const pos = $inputEl.selectionStart || text.length;
    const left = text.slice(0, pos).replace(/\s+$/, '');
    if (!left) return false;
    return /[=+\-*/,(]/.test(left[left.length - 1] || '');
  }
  function buildSuggestionItems(excludeCode) {
    const labels = getScopeLabels(excludeCode);
    const values = getScopeValues(excludeCode);
    const items = Object.keys(labels).map((code) => {
      const label = String(labels[code] || code).trim() || code;
      const kind = code.startsWith('cp_') ? 'formula-parameter' : 'parameter';
      return {
        kind,
        code,
        label,
        value: Number(values[code] || 0),
        meta: kind === 'formula-parameter' ? 'Formula Parameter' : 'Parameter',
        insertText: code,
        caretOffset: code.length,
        searchKeys: [label, code]
      };
    });
    FN_SUGGEST.forEach((fn) => {
      items.push({
        kind: 'operation',
        code: fn.name,
        label: fn.label,
        value: NaN,
        meta: 'Operasi',
        hint: fn.hint,
        insertText: fn.insertText,
        caretOffset: fn.caretOffset,
        searchKeys: [fn.label, fn.name, fn.hint]
      });
    });
    return items;
  }

  function scoreSuggestion(item, queryWord) {
    const qNorm = normKey(queryWord);
    if (!qNorm) return 1;
    const qCompact = compactKey(queryWord);
    const qWords = qNorm.split(' ').filter(Boolean);
    const keys = Array.isArray(item.searchKeys) ? item.searchKeys : [item.label || item.code || ''];
    let best = -1;
    keys.forEach((kRaw) => {
      const kNorm = normKey(kRaw);
      const kCompact = compactKey(kRaw);
      if (!kNorm) return;
      if (kNorm === qNorm) best = Math.max(best, 1400);
      if (kNorm.startsWith(qNorm)) best = Math.max(best, 1300);
      const idxNorm = kNorm.indexOf(qNorm);
      if (idxNorm >= 0) best = Math.max(best, 1200 - Math.min(idxNorm, 250));
      if (qCompact) {
        if (kCompact === qCompact) best = Math.max(best, 1380);
        else if (kCompact.startsWith(qCompact)) best = Math.max(best, 1280);
        else {
          const idxCompact = kCompact.indexOf(qCompact);
          if (idxCompact >= 0) best = Math.max(best, 1180 - Math.min(idxCompact, 250));
        }
      }
      if (qWords.length && qWords.every((w) => kNorm.includes(w))) best = Math.max(best, 1160);
    });
    return best;
  }

  function ensureSuggestBox() {
    if (suggest.box && suggest.ul) return;
    suggest.box = document.createElement('div');
    suggest.box.className = 'vp-suggest vp-suggest-modal';
    suggest.box.style.display = 'none';
    suggest.box.style.opacity = '0';
    suggest.ul = document.createElement('ul');
    suggest.box.appendChild(suggest.ul);
    document.body.appendChild(suggest.box);
  }

  function hideSuggestions() {
    if (!suggest.box) return;
    suggest.box.style.opacity = '0';
    suggest.items = [];
    suggest.idx = -1;
    suggest.ul.innerHTML = '';
    setTimeout(() => {
      if (suggest.box) {
        suggest.box.style.display = 'none';
        suggest.box.style.left = '';
        suggest.box.style.top = '';
        suggest.box.style.width = '';
        suggest.box.style.maxHeight = '';
      }
    }, 120);
  }

  function positionSuggest() {
    if (!suggest.box || !$inputEl) return;
    const rect = $inputEl.getBoundingClientRect();
    const menuH = suggest.box.offsetHeight || 240;
    const gap = 6;
    const spaceBelow = window.innerHeight - rect.bottom;
    const placeDown = spaceBelow >= Math.min(menuH, 160);
    const width = Math.max(220, Math.round(rect.width));
    const maxWidth = Math.max(220, window.innerWidth - 16);
    const clamped = Math.min(width, maxWidth);
    const maxLeft = Math.max(8, window.innerWidth - clamped - 8);
    const left = Math.min(Math.max(8, Math.round(rect.left)), maxLeft);
    suggest.box.style.position = 'fixed';
    suggest.box.style.left = `${left}px`;
    suggest.box.style.width = `${clamped}px`;
    if (placeDown) {
      suggest.box.style.top = `${Math.round(rect.bottom + gap)}px`;
      suggest.box.style.maxHeight = `${Math.max(120, Math.min(menuH, Math.floor(spaceBelow - gap)))}px`;
    } else {
      const spaceAbove = rect.top;
      const mh = Math.max(120, Math.min(menuH, Math.floor(spaceAbove - gap)));
      suggest.box.style.maxHeight = `${mh}px`;
      suggest.box.style.top = `${Math.max(8, Math.round(rect.top - gap - mh))}px`;
    }
  }

  function showSuggestions(forceOpen) {
    if (!$inputEl) return;
    const caret = getCaretWord();
    const q = String(caret.word || '').trim();
    const allowEmpty = shouldShowSuggestionsForEmptyQuery();
    if (!forceOpen && !q && !allowEmpty) { hideSuggestions(); return; }
    const excludeCode = ctx?.contextType === 'computed' ? ctx.code : '';
    const all = buildSuggestionItems(excludeCode);
    const scored = all
      .map((it) => ({ ...it, _score: scoreSuggestion(it, q) }))
      .filter((it) => it._score >= 0)
      .sort((a, b) => b._score - a._score)
      .slice(0, 8)
      .map(({ _score, ...rest }) => rest);

    ensureSuggestBox();
    suggest.items = scored;
    suggest.idx = scored.length ? 0 : -1;
    suggest.ul.innerHTML = '';

    if (!scored.length) {
      const li = document.createElement('li');
      li.className = 'text-muted';
      li.textContent = q
        ? 'Tidak ada parameter/formula/operasi tersimpan. Hapus kata ini atau buat parameter baru.'
        : 'Ketik parameter atau operasi untuk melihat saran.';
      suggest.ul.appendChild(li);
    } else {
      const groups = [
        { kind: 'parameter', label: 'Parameter' },
        { kind: 'formula-parameter', label: 'Formula Parameter' },
        { kind: 'operation', label: 'Operasi' }
      ];
      groups.forEach((g) => {
        const rows = suggest.items.map((it, i) => ({ ...it, __i: i })).filter((it) => it.kind === g.kind);
        if (!rows.length) return;
        const head = document.createElement('li');
        head.className = 's-group';
        head.textContent = g.label;
        suggest.ul.appendChild(head);
        rows.forEach((it) => {
          const li = document.createElement('li');
          li.setAttribute('data-item-idx', String(it.__i));
          if (it.__i === suggest.idx) li.classList.add('active');
          const meta = String(it.meta || '').trim();
          const hint = String(it.hint || '').trim();
          const valueHtml = Number.isFinite(it.value)
            ? `<span class="s-value">${formatIdSmart(it.value)}</span>`
            : `<span class="s-value s-value-muted">${escapeHtml(hint || meta || '')}</span>`;
          li.innerHTML = `<span class="s-main"><span class="s-name">${escapeHtml(it.label)}</span>${meta ? `<span class="s-meta">${escapeHtml(meta)}</span>` : ''}</span><span class="d-flex flex-column align-items-end gap-1">${valueHtml}<span class="s-shortcut">Enter/Tab</span></span>`;
          li.addEventListener('mousedown', (ev) => {
            ev.preventDefault();
            applySuggestion(suggest.items[it.__i]);
          });
          suggest.ul.appendChild(li);
        });
      });
      const hint = document.createElement('li');
      hint.className = 's-hint-row';
      hint.textContent = 'Shortcut: Ctrl+Space buka autosuggestion, Enter/Tab pilih, Esc tutup.';
      suggest.ul.appendChild(hint);
    }

    suggest.box.style.display = 'block';
    suggest.box.style.opacity = '0';
    requestAnimationFrame(() => {
      positionSuggest();
      suggest.box.style.opacity = '1';
    });
  }

  function applySuggestion(item) {
    if (!$inputEl || !item) return;
    const insertText = String(item.insertText || item.code || '');
    const excludeCode = ctx?.contextType === 'computed' ? ctx.code : '';
    if (FORMULA_LABEL_ONLY_UI_ENABLED) {
      insertRawTokenIntoMaskedInput($inputEl, insertText, {
        caretOffset: Number.isFinite(item.caretOffset) ? Number(item.caretOffset) : insertText.length,
        excludeCode,
      });
    } else {
      const caret = getCaretWord();
      const text = String($inputEl.value || '');
      $inputEl.value = text.slice(0, caret.start) + insertText + text.slice(caret.end);
      const pos = caret.start + (Number.isFinite(item.caretOffset) ? Number(item.caretOffset) : insertText.length);
      $inputEl.selectionStart = $inputEl.selectionEnd = pos;
    }
    $inputEl.focus();
    hideSuggestions();
    updatePreview();
  }

  function navigateSuggestion(step) {
    if (!suggest.items.length || !suggest.ul) return;
    suggest.idx = (suggest.idx + step + suggest.items.length) % suggest.items.length;
    suggest.ul.querySelectorAll('[data-item-idx]').forEach((el) => {
      const i = Number(el.getAttribute('data-item-idx'));
      el.classList.toggle('active', i === suggest.idx);
    });
  }

  function acceptSuggestion() {
    if (suggest.idx < 0 || !suggest.items[suggest.idx]) return false;
    applySuggestion(suggest.items[suggest.idx]);
    return true;
  }
  function buildPaletteItems(excludeCode) {
    const labels = getScopeLabels(excludeCode);
    const values = getScopeValues(excludeCode);
    return Object.keys(labels)
      .map((code) => ({
        code,
        label: String(labels[code] || code).trim() || code,
        value: Number(values[code] || 0),
        type: code.startsWith('cp_') ? 'Turunan' : 'Parameter'
      }))
      .sort((a, b) => a.label.localeCompare(b.label, 'id'));
  }

  function renderPaletteList(query = '') {
    if (!$paletteList) return;
    const excludeCode = ctx?.contextType === 'computed' ? ctx.code : '';
    const all = buildPaletteItems(excludeCode);
    const qNorm = normKey(query);
    const qCompact = compactKey(query);
    const filtered = !qNorm
      ? all
      : all.filter((it) => {
        const lNorm = normKey(it.label);
        const lCompact = compactKey(it.label);
        return lNorm.includes(qNorm) || (qCompact && lCompact.includes(qCompact));
      });
    if (!filtered.length) {
      $paletteList.innerHTML = '<div class="vp-palette-empty">Tidak ada parameter/formula parameter yang cocok.</div>';
      return;
    }
    $paletteList.innerHTML = filtered.map((it) => `
      <button type="button" class="vp-palette-row" data-code="${escapeHtml(it.code)}">
        <span class="vp-palette-main"><span class="vp-palette-label">${escapeHtml(it.label)}</span></span>
        <span class="vp-palette-meta"><span class="vp-palette-badge">${escapeHtml(it.type)}</span><span>${formatIdSmart(it.value)}</span></span>
      </button>`).join('');
  }

  function openPalette(options = {}) {
    if (!ctx || !$inputEl) return;
    const modal = ensurePaletteModal();
    if (!modal) return;
    const nextQuery = String(options.query ?? $paletteSearch?.value ?? '').trim();
    if ($paletteSearch) $paletteSearch.value = nextQuery;
    renderPaletteList(nextQuery);
    modal.show();
    setTimeout(() => {
      $paletteSearch?.focus();
      if ($paletteSearch && nextQuery) {
        const len = $paletteSearch.value.length;
        $paletteSearch.setSelectionRange(len, len);
      }
    }, 80);
  }

  function insertFromPalette(code) {
    if (!$inputEl || !code) return;
    const excludeCode = ctx?.contextType === 'computed' ? ctx.code : '';
    if (FORMULA_LABEL_ONLY_UI_ENABLED) {
      insertRawTokenIntoMaskedInput($inputEl, String(code || '').toLowerCase(), {
        caretOffset: String(code || '').length,
        excludeCode,
      });
    } else {
      const text = String($inputEl.value || '');
      const pos = $inputEl.selectionStart || text.length;
      const before = text.slice(0, pos);
      const after = text.slice(pos);
      const needSpace = before.length > 0 && !/[\s(=+\-*/,]$/.test(before);
      const insertCode = (needSpace ? ' ' : '') + code;
      $inputEl.value = before + insertCode + after;
      $inputEl.selectionStart = $inputEl.selectionEnd = pos + insertCode.length;
    }
    $inputEl.focus();
    updatePreview();
  }

  function replaceIdentifierToken(rawExpr, targetToken, replacementCode) {
    const source = String(rawExpr || '');
    const target = String(targetToken || '').trim().toLowerCase();
    const replacement = String(replacementCode || '').trim().toLowerCase();
    if (!source || !target || !replacement || target === replacement) return source;
    return source.replace(/[A-Za-z_][A-Za-z0-9_]*/g, (token) => (String(token || '').toLowerCase() === target ? replacement : token));
  }

  function applyFormula() {
    if (!ctx || !$inputEl || hasBlockingError) return;
    const excludeCode = ctx.contextType === 'computed' ? ctx.code : '';
    const rawValue = FORMULA_LABEL_ONLY_UI_ENABLED
      ? getInputFormulaRaw($inputEl, $inputEl.value || '', { excludeCode })
      : String($inputEl.value || '');
    const raw = String(rawValue || '').trim();
    const exprBody = raw.startsWith('=') ? raw.slice(1).trim() : raw;
    if (!exprBody) { PSE()?._TOAST_warn?.('Formula kosong.'); return; }

    if (ctx.contextType === 'computed-new') {
      if (typeof ctx.onCreated === 'function') ctx.onCreated(exprBody);
      closeModal();
      return;
    }

    if (ctx.contextType === 'computed') {
      const code = ctx.code;
      if (!code) return;
      const nextDef = { ...PSE()?.getComputedParams()?.[code] };
      nextDef.expression = exprBody;
      if (ctx.allowNameEdit && $nameInput) {
        const nextLabel = String($nameInput.value || '').trim();
        if (nextLabel) nextDef.label = nextLabel;
      }
      PSE()?._updateComputedParam?.(code, nextDef);
      PSE()?._renderVarTable?.();
      PSE()?._renderComputedTable?.();
      closeModal();
      PSE()?._TOAST_ok?.('Formula diterapkan.');
    }
  }

  function closeModal() {
    hideSuggestions();
    if (bsPaletteModal) bsPaletteModal.hide();
    if (bsModal) bsModal.hide();
    ctx = null;
    resolverToken = '';
  }

  function openForComputed(code, options = {}) {
    const isNew = options.isNew === true;
    const pse = PSE();
    if (!pse) return;
    bindDOM();
    const modal = ensureModal();
    if (!modal || !$inputEl) return;

    const cpAll = pse.getComputedParams() || {};
    if (!isNew && (!code || !cpAll[code])) return;

    const def = isNew ? {} : (cpAll[code] || {});
    const expression = String(options.expression || def.expression || '');
    const label = String(options.label || def.label || code || 'Baru');
    const allowNameEdit = !isNew && options.enableNameEdit === true;

    ctx = isNew
      ? { contextType: 'computed-new', code: '', label, onCreated: options.onCreated || null, allowNameEdit: false }
      : { contextType: 'computed', code, originalExpression: expression, label, allowNameEdit };

    if ($nameWrap) $nameWrap.classList.toggle('d-none', !allowNameEdit);
    if ($nameInput && allowNameEdit) $nameInput.value = label;

    if ($metaEl) {
      $metaEl.textContent = isNew
        ? `Formula Turunan Baru: ${label}`
        : `Formula Turunan: ${label}`;
    }

    const raw = expression.trim() ? (expression.trim().startsWith('=') ? expression : `=${expression}`) : '';
    setInputFormulaRaw($inputEl, raw, {
      forceFormula: true,
      excludeCode: isNew ? '' : code,
    });
    undoExpression = isNew ? '' : raw;

    renderInvalidOverlay([]);
    syncHighlightScroll();
    updatePreview();
    hideSuggestions();
    setResolverState('', '');
    setViewMode('raw');
    setBlockState(false, '');

    modal.show();
    setTimeout(() => {
      setViewMode('raw', { focus: true, caret: 'end' });
      syncHighlightScroll();
    }, 80);
  }

  let eventsBound = false;
  function bindEvents() {
    if (eventsBound) return;
    eventsBound = true;

    document.addEventListener('input', (e) => {
      if (e.target === $inputEl) {
        updatePreview();
        showSuggestions(false);
      }
      if (e.target && e.target.id === `${palettePrefix}search`) renderPaletteList(e.target.value || '');
    });

    document.addEventListener('scroll', (e) => {
      if (e.target === $inputEl) syncHighlightScroll();
    }, true);

    document.addEventListener('keydown', (e) => {
      if (e.target === $inputEl) {
        if ((e.ctrlKey || e.metaKey) && e.key === ' ') { e.preventDefault(); showSuggestions(true); return; }
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); applyFormula(); return; }
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'z') {
          e.preventDefault();
          if (undoExpression) {
            const excludeCode = ctx?.contextType === 'computed' ? ctx.code : '';
            if (FORMULA_LABEL_ONLY_UI_ENABLED) {
              setInputFormulaRaw($inputEl, undoExpression, { forceFormula: true, excludeCode });
            } else {
              $inputEl.value = undoExpression;
            }
            undoExpression = '';
            updatePreview();
          }
          return;
        }
        if (suggest.items.length) {
          if (e.key === 'ArrowDown') { e.preventDefault(); navigateSuggestion(1); return; }
          if (e.key === 'ArrowUp') { e.preventDefault(); navigateSuggestion(-1); return; }
          if ((e.key === 'Enter' || e.key === 'Tab') && acceptSuggestion()) { e.preventDefault(); return; }
          if (e.key === 'Escape') { e.preventDefault(); hideSuggestions(); return; }
        }
      }
      if (e.target && e.target.closest && e.target.closest(`#${prefix}chip-preview.is-clickable`) && (e.key === 'Enter' || e.key === ' ')) {
        e.preventDefault();
        setViewMode('raw', { focus: true });
      }
    });

    document.addEventListener('click', (e) => {
      if (e.target.closest(`#${prefix}apply`)) { e.preventDefault(); applyFormula(); return; }
      if (e.target.closest(`#${prefix}undo`)) {
        e.preventDefault();
        if (undoExpression && $inputEl) {
          const excludeCode = ctx?.contextType === 'computed' ? ctx.code : '';
          if (FORMULA_LABEL_ONLY_UI_ENABLED) {
            setInputFormulaRaw($inputEl, undoExpression, { forceFormula: true, excludeCode });
          } else {
            $inputEl.value = undoExpression;
          }
          undoExpression = '';
          updatePreview();
        }
        return;
      }
      if (e.target.closest(`#${prefix}toggle-view`)) { e.preventDefault(); setViewMode(viewMode === 'raw' ? 'chip' : 'raw', { focus: true }); return; }
      if (e.target.closest(`#${prefix}open-palette`) || e.target.closest(`#${prefix}resolve-btn`)) { e.preventDefault(); openPalette(); return; }
      if (e.target.closest(`#${prefix}chip-preview.is-clickable`)) { e.preventDefault(); setViewMode('raw', { focus: true }); return; }

      const row = e.target.closest('.vp-palette-row');
      if (row) {
        const listEl = document.getElementById(`${palettePrefix}list`);
        if (listEl && listEl.contains(row)) {
          const code = row.dataset.code;
          if (code) {
            if (resolverToken && $inputEl) {
              const excludeCode = ctx?.contextType === 'computed' ? ctx.code : '';
              const currentRaw = FORMULA_LABEL_ONLY_UI_ENABLED
                ? getInputFormulaRaw($inputEl, $inputEl.value || '', { excludeCode })
                : String($inputEl.value || '');
              const nextRaw = replaceIdentifierToken(currentRaw, resolverToken, code);
              if (FORMULA_LABEL_ONLY_UI_ENABLED) {
                setInputFormulaRaw($inputEl, nextRaw, { forceFormula: true, excludeCode });
              } else {
                $inputEl.value = nextRaw;
              }
              setResolverState('', '');
              updatePreview();
            } else {
              insertFromPalette(code);
            }
            if (bsPaletteModal) bsPaletteModal.hide();
            $inputEl?.focus();
          }
        }
      }
    });

    document.addEventListener('change', (e) => {
      if (e.target && e.target.id === `${prefix}show-values`) {
        showInlineValues = !!e.target.checked;
        updatePreview();
      }
    });

    document.addEventListener('mousedown', (e) => {
      if (suggest.box?.parentElement && !suggest.box.contains(e.target) && e.target !== $inputEl) hideSuggestions();
    });
  }

  function init(config) {
    if (config) {
      if (config.formulaEditorModalId) modalId = config.formulaEditorModalId;
      if (config.paramPaletteModalId) paletteModalId = config.paramPaletteModalId;
      if (config.idPrefix) prefix = config.idPrefix;
      if (config.paletteIdPrefix) palettePrefix = config.paletteIdPrefix;
      if (typeof config.formulaLabelOnlyUiEnabled === 'boolean') {
        FORMULA_LABEL_ONLY_UI_ENABLED = config.formulaLabelOnlyUiEnabled;
      }
    }
    bindDOM();
    bindEvents();
  }

  function close() {
    closeModal();
  }

  G.FormulaEditorModal = {
    init,
    openForComputed,
    close,
  };
})();
