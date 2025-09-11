/* volume_pekerjaan.js — Drop-in (sticky THEAD, autosave+undo, id-ID formatting)
 * - Header tabel sticky tepat di bawah searchbar (JS mengisi CSS vars)
 * - Format tampilan id-ID dinamis (maks 3 desimal)
 * - Autosave (debounce) + Undo batch terakhir via toast (Ctrl+Alt+Z)
 * - Import parameter JSON & CSV (Excel-friendly, "label,value")
 * - Keyboard: Enter/Shift+Enter nav • Ctrl/⌘+S save • Ctrl/⌘+Space param • Ctrl+D fill-down
 */

(function () {
  const root = document.getElementById('vol-app');
  if (!root) return;

  // ---- Konteks dasar
  const projectId = root.dataset.projectId || root.dataset.pid;

  // Presisi simpan (DB 3dp), tampilan dinamis 0..3 dp
  const STORE_PLACES = 3;

  // Debounce autosave (ms)
  const AUTOSAVE_MS = 1200;

  // ---- State in-memory
  let rows = Array.from(root.querySelectorAll('#vp-table tbody tr[data-pekerjaan-id]'));
  const originalValueById = {}; // nilai tersimpan di server (baseline)
  const rawInputById = {};      // string mentah di input
  const currentValueById = {};  // nilai numerik hasil parse/eval
  const fxModeById = {};        // mode formula per baris
  const dirtySet = new Set();   // id pekerjaan yang berubah

  // Autosave timer & guard
  let autosaveTimer = null;
  let saving = false;

  // Undo stack (batch autosave/simpan terakhir)
  const undoStack = []; // item: { ts, changes:[{id,before,after}] }
  const UNDO_MAX = 10;

  // === Parameter (values & labels)
  let variables = {}; // { KODE: number }
  let varLabels = {}; // { KODE: label }

  // ---- Elemen UI
  const btnSave = document.getElementById('btn-save-vol');
  const btnSaveSpin = document.getElementById('btn-save-spin');

  const varTable = document.getElementById('vp-var-table');
  const btnVarAdd = document.getElementById('vp-var-add');
  const btnVarImportBtn = document.getElementById('vp-var-import-btn');
  const btnVarExportBtn = document.getElementById('vp-var-export-btn');
  const fileVarImport = document.getElementById('vp-var-import');
  const offcanvasEl = document.getElementById('vpVarOffcanvas');

  const searchInput = document.getElementById('vp-search');
  const searchDrop = document.getElementById('vp-search-results');
  const prefixBadge = document.getElementById('vp-search-prefix-badge');
  const topbarEl = document.getElementById('dp-topbar');
  const toolbarEl = document.getElementById('vp-toolbar');

  // Toast (single) + multi-toasts (untuk Undo)
  const toastEl = document.getElementById('vp-toast');
  const toastBody = document.getElementById('vp-toast-body');
  const multiToasts = document.getElementById('vp-toasts');
  let toastRef = null;
  try { if (window.bootstrap && toastEl) toastRef = new bootstrap.Toast(toastEl, { delay: 1600 }); } catch {}

  function showToast(message, variant) {
    if (!toastEl || !toastBody || !toastRef) { if (message) alert(message); return; }
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
          ${actions.map((a,i)=>`<button type="button" class="btn btn-sm ${a.class||'btn-warning'}" data-i="${i}">${escapeHtml(a.label||'OK')}</button>`).join('')}
          <button type="button" class="btn-close btn-close-white m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
      </div>
    `;
    multiToasts.appendChild(wrapper);
    const t = new bootstrap.Toast(wrapper, { delay: 4000 });
    actions.forEach((a,i)=>{
      const btn = wrapper.querySelector(`[data-i="${i}"]`);
      if (btn) btn.addEventListener('click', () => { try{ a.onClick?.(); }finally{ t.hide(); } });
    });
    wrapper.addEventListener('hidden.bs.toast', ()=> wrapper.remove());
    t.show();
  }

  // ---- Utils
  function getCsrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }
  function roundHalfUp(x, places) {
    const p = Math.max(0, Math.min(20, places|0));
    const factor = Math.pow(10, p);
    return (x >= 0)
      ? Math.floor(x * factor + 0.5) / factor
      : Math.ceil(x * factor - 0.5) / factor;
  }
  // Tampilan id-ID dinamis (maks 3 dp—tanpa trailing bila .000)
  function formatIdSmart(num) {
    const n = Number(num || 0);
    const hasFrac = Math.abs(n - Math.trunc(n)) > 1e-12;
    const fracLen = hasFrac ? Math.min(String(n.toFixed(STORE_PLACES)).split('.')[1]?.replace(/0+$/,'').length || 0, STORE_PLACES) : 0;
    try {
      return new Intl.NumberFormat('id-ID', {
        minimumFractionDigits: fracLen,
        maximumFractionDigits: STORE_PLACES
      }).format(n);
    } catch {
      return n.toFixed(fracLen);
    }
  }
  function normalizeLocaleNumericString(input) {
    let s = String(input ?? '').trim();
    if (!s) return s;
    s = s.replace(/\s+/g, '').replace(/_/g, '');
    const hasComma = s.includes(','), hasDot = s.includes('.');
    if (hasComma && hasDot) { s = s.replace(/\./g, ''); s = s.replace(',', '.'); }
    else if (hasComma) { s = s.replace(',', '.'); }
    return s;
  }
  function parseNumberOrEmpty(val) {
    const s = normalizeLocaleNumericString(val);
    if (!s) return '';
    const n = Number(s);
    return Number.isFinite(n) ? n : '';
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (m)=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  }

  function setBtnSaveEnabled() {
    const dirty = dirtySet.size !== 0;
    if (btnSave) btnSave.disabled = !dirty;
    window.__vpDirty = dirty;
  }

  // ---- CSS Vars sync (topbar/toolbar/thead)
  function setTopOffsets() {
    try {
      const topbarH  = topbarEl  ? Math.round(topbarEl.getBoundingClientRect().height)  : 0;
      const toolbarH = toolbarEl ? Math.round(toolbarEl.getBoundingClientRect().height) : 42;
      const rootStyle = document.documentElement.style;
      rootStyle.setProperty('--vp-top-offset', `${topbarH}px`);
      rootStyle.setProperty('--vp-toolbar-h', `${toolbarH}px`);

      const thead = document.querySelector('#vp-table thead');
      const thOrHead = thead?.querySelector('tr') || thead;
      const theadH = thOrHead ? Math.round(thOrHead.getBoundingClientRect().height) : 36;
      rootStyle.setProperty('--vp-thead-h', `${theadH}px`);
    } catch {}
  }
  setTopOffsets();
  if (document.fonts && document.fonts.ready) { document.fonts.ready.then(setTopOffsets).catch(()=>{}); }
  window.addEventListener('load', setTopOffsets, { once: true });
  window.addEventListener('resize', setTopOffsets);
  if (toolbarEl) toolbarEl.addEventListener('transitionend', setTopOffsets);
  if (searchInput) ['focus','blur','input'].forEach(ev => searchInput.addEventListener(ev, setTopOffsets));
  ['shown.bs.offcanvas','hidden.bs.offcanvas','shown.bs.modal','hidden.bs.modal'].forEach(evt => { document.addEventListener(evt, setTopOffsets); });
  (function observeTopbarResize() {
    try {
      const navEl = document.getElementById('dp-topbar') || document.querySelector('body > nav');
      if (!navEl || typeof ResizeObserver === 'undefined') return;
      const ro = new ResizeObserver(() => setTopOffsets());
      ro.observe(navEl);
    } catch {}
  })();

  // ===== Search Index & UI =====
  let searchIndex = []; // {type, id, label, el}
  let searchState = { items: [], activeIdx: -1 };

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
    const match  = text.slice(idx, idx + q.length);
    const after  = text.slice(idx + q.length);
    return `${escapeHtml(before)}<mark class="vp-mark">${escapeHtml(match)}</mark>${escapeHtml(after)}`;
  }
  function buildSearchIndex() {
    searchIndex = [];
    document.querySelectorAll('#vp-table tbody tr.vp-klass').forEach((tr, i) => {
      const label = tr.textContent.trim();
      searchIndex.push({ type: 'Klasifikasi', id: `k${i}`, label, el: tr });
    });
    document.querySelectorAll('#vp-table tbody tr.vp-sub').forEach((tr, i) => {
      const label = tr.textContent.trim();
      searchIndex.push({ type: 'Sub', id: `s${i}`, label, el: tr });
    });
    document.querySelectorAll('#vp-table tbody tr[data-pekerjaan-id]').forEach((tr) => {
      const kode = (tr.querySelector('.text-monospace')?.textContent || '').trim();
      const uraian = (tr.querySelector('.text-wrap')?.textContent || '').trim();
      const label = (kode ? `${kode} — ` : '') + uraian;
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
        <div class="vp-search-item${i===0?' active':''}" id="${id}" role="option" aria-selected="${i===0?'true':'false'}" data-id="${it.id}" data-type="${it.type}">
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
      else { prefixBadge.classList.remove('d-none'); prefixBadge.textContent = s.length > 18 ? s.slice(0, 17) + '…' : s; }
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
      if (e.key === 'ArrowUp')   { e.preventDefault(); setActiveIdx(searchState.activeIdx - 1); return; }
      if (e.key === 'Enter')     { e.preventDefault(); selectSearchIndex(searchState.activeIdx); return; }
      if (e.key === 'Escape')    { e.preventDefault(); searchDrop.classList.add('d-none'); searchDrop.setAttribute('aria-expanded','false'); return; }
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
  function getCaretIdentifier(inputEl) {
    const value = String(inputEl.value || '');
    const pos = inputEl.selectionStart ?? value.length;
    if (!value.trim().startsWith('=')) return null;
    let start = pos, end = pos;
    const isPart = c => /[A-Za-z0-9_]/.test(c);
    while (start > 0 && isPart(value[start - 1])) start--;
    while (end < value.length && isPart(value[end])) end++;
    const word = value.slice(start, end);
    if (!word) return null;
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(word)) return null;
    return { word, start, end };
  }
  function ensureSuggestBox(inputEl) {
    let state = suggestState.get(inputEl);
    if (state && state.box && state.ul) return state;
    const wrap = inputEl.closest('.flex-grow-1') || inputEl.parentElement;
    const box = document.createElement('div');
    box.className = 'vp-suggest';
    box.style.display = 'none';
    box.style.opacity = '0';
    const ul = document.createElement('ul');
    box.appendChild(ul);
    wrap.appendChild(box);
    state = { box, ul, items: [], activeIdx: -1 };
    suggestState.set(inputEl, state);
    return state;
  }
  function hideSuggest(inputEl) {
    const state = suggestState.get(inputEl);
    if (!state) return;
    state.box.style.opacity = '0';
    state.items = [];
    state.activeIdx = -1;
    state.ul.innerHTML = '';
    setTimeout(() => { state.box.style.display = 'none'; }, 80);
  }
  function showSuggest(inputEl, items) {
    const state = ensureSuggestBox(inputEl);
    state.items = items.slice(0, 8);
    state.activeIdx = state.items.length ? 0 : -1;
    state.ul.innerHTML = '';
    if (!state.items.length) {
      const li = document.createElement('li'); li.className = 'text-muted'; li.textContent = 'Tidak ada parameter cocok';
      state.ul.appendChild(li);
      state.box.style.display = 'block';
      requestAnimationFrame(() => { state.box.style.opacity = '1'; });
      return;
    }
    state.items.forEach((it, idx) => {
      const li = document.createElement('li');
      li.className = idx === state.activeIdx ? 'active' : '';
      li.innerHTML = `
        <span class="s-name">${escapeHtml(it.label)} <span class="text-muted">(${escapeHtml(it.name)})</span></span>
        <span class="s-value">${formatIdSmart(it.value)}</span>`;
      li.addEventListener('mousedown', (ev) => {
        ev.preventDefault();
        applySuggestion(inputEl, it.name);
      });
      state.ul.appendChild(li);
    });
    state.box.style.display = 'block';
    requestAnimationFrame(() => { state.box.style.opacity = '1'; });
  }
  function moveActive(inputEl, delta) {
    const state = suggestState.get(inputEl);
    if (!state || !state.items.length) return;
    state.activeIdx = (state.activeIdx + delta + state.items.length) % state.items.length;
    const lis = state.ul.querySelectorAll('li');
    lis.forEach((li, i) => li.classList.toggle('active', i === state.activeIdx));
  }
  function applyActiveSuggestion(inputEl) {
    const state = suggestState.get(inputEl);
    if (!state || state.activeIdx < 0) return false;
    const it = state.items[state.activeIdx];
    if (!it) return false;
    applySuggestion(inputEl, it.name);
    return true;
  }
  function applySuggestion(inputEl, varCode) {
    const value = String(inputEl.value || '');
    const caret = inputEl.selectionStart ?? value.length;
    const idf = getCaretIdentifier(inputEl);
    let before, after;
    if (idf) { before = value.slice(0, idf.start); after = value.slice(idf.end); }
    else { before = value.slice(0, caret); after = value.slice(caret); }
    const ensureEq = value.trim().startsWith('=') ? '' : '=';
    inputEl.value = ensureEq + before + varCode + after;
    const pos = (ensureEq ? 1 : 0) + before.length + varCode.length;
    inputEl.setSelectionRange(pos, pos);
    const tr = inputEl.closest('tr');
    const id = parseInt(tr.dataset.pekerjaanId, 10);
    const preview = tr.querySelector('.fx-preview');
    handleInputChange(id, inputEl, preview, false);
    hideSuggest(inputEl);
  }
  function updateSuggestions(inputEl, id) {
    const raw = String(inputEl.value || '');
    if (!isFormulaMode(id, raw)) { hideSuggest(inputEl); return; }
    const codes = Object.keys(variables || {});
    if (!codes.length) { hideSuggest(inputEl); return; }
    const itemsAll = codes.map(code => ({
      name: code,
      label: varLabels[code] || code,
      value: Number(variables[code] || 0),
    }));
    const idf = getCaretIdentifier(inputEl);
    let items = itemsAll;
    if (idf) {
      const q = idf.word.toLowerCase();
      items = itemsAll.filter(it => it.name.toLowerCase().startsWith(q));
    }
    items.sort((a,b) => (varLabels[a.name]||a.name).localeCompare(varLabels[b.name]||b.name, 'id'));
    showSuggest(inputEl, items);
  }

  // ==== Wiring baris pekerjaan
  const formulaState = loadFormulas();

  function collectQtyInputs() {
    return Array.from(document.querySelectorAll('#vp-table .qty-input'));
  }
  function focusNextFrom(currentEl, delta) {
    const inputs = collectQtyInputs();
    const idx = inputs.indexOf(currentEl);
    if (idx === -1) return;
    let next = idx + delta;
    if (next < 0) next = 0;
    if (next >= inputs.length) next = inputs.length - 1;
    const tgt = inputs[next];
    if (tgt) { tgt.focus(); try { tgt.select(); } catch{} }
  }

  function bindRow(tr) {
    const id = parseInt(tr.dataset.pekerjaanId, 10);
    const input = tr.querySelector('.qty-input');
    const fxBtn = tr.querySelector('.fx-toggle');
    const preview = tr.querySelector('.fx-preview');

    try { if (window.bootstrap && fxBtn) new bootstrap.Tooltip(fxBtn); } catch {}

    const f = formulaState[id] || {};
    if (typeof f.fx === 'boolean') {
      fxModeById[id] = !!f.fx;
      fxBtn.setAttribute('aria-pressed', String(!!f.fx));
      fxBtn.classList.toggle('active', !!f.fx);
    } else { fxModeById[id] = false; }
    if (typeof f.raw === 'string' && f.raw.trim()) {
      rawInputById[id] = f.raw;
      input.value = f.raw;
    }

    fxBtn.addEventListener('click', () => {
      const newState = !fxModeById[id];
      fxModeById[id] = newState;
      fxBtn.setAttribute('aria-pressed', String(newState));
      fxBtn.classList.toggle('active', newState);
      if (newState) {
        const cur = String(input.value || '').trim();
        if (!cur.startsWith('=')) input.value = '=' + cur;
        input.focus();
        updateSuggestions(input, id);
      } else {
        hideSuggest(input);
      }
      handleInputChange(id, input, preview, true);
      persistRowFormula(id);
      updateSuggestions(input, id);
    });

    let debTimer = null;
    input.addEventListener('input', () => {
      clearTimeout(debTimer);
      updateSuggestions(input, id);
      debTimer = setTimeout(() => handleInputChange(id, input, preview, false), 120);
    });
    input.addEventListener('blur', () => {
      if (!isFormulaMode(id, input.value)) {
        const normalized = normQty(input.value);
        if (normalized !== '') input.value = normalized;
      }
      setTimeout(() => hideSuggest(input), 120);
    });
    input.addEventListener('focus', () => updateSuggestions(input, id));
    input.addEventListener('keydown', (ev) => {
      // Save
      if ((ev.ctrlKey || ev.metaKey) && (ev.key === 's' || ev.key === 'S')) {
        ev.preventDefault();
        if (btnSave && !btnSave.disabled) btnSave.click();
        else scheduleAutosave(300);
        return;
      }
      // Toggle suggestion panel
      if ((ev.ctrlKey || ev.metaKey) && ev.code === 'Space') {
        ev.preventDefault();
        const cur = String(input.value || '');
        if (!cur.trim().startsWith('=')) input.value = '=' + cur;
        if (!fxModeById[id]) {
          fxModeById[id] = true;
          fxBtn.setAttribute('aria-pressed', 'true');
          fxBtn.classList.add('active');
          persistRowFormula(id);
        }
        input.focus();
        updateSuggestions(input, id);
        return;
      }

      // Suggest navigation
      const state = suggestState.get(input);
      const suggestVisible = state && state.box && state.box.style.display !== 'none' && state.items.length > 0;
      if (suggestVisible) {
        if (ev.key === 'ArrowDown') { ev.preventDefault(); moveActive(input, +1); return; }
        if (ev.key === 'ArrowUp')   { ev.preventDefault(); moveActive(input, -1); return; }
        if (ev.key === 'Enter')     { const ok = applyActiveSuggestion(input); if (ok) { ev.preventDefault(); return; } }
        if (ev.key === 'Escape')    { hideSuggest(input); return; }
      }

      // Fill-down (Excel-like)
      if ((ev.ctrlKey || ev.metaKey) && (ev.key.toLowerCase() === 'd')) {
        ev.preventDefault();
        const val = String(input.value || '');
        focusNextFrom(input, +1);
        const tgt = document.activeElement;
        if (tgt && tgt.classList.contains('qty-input')) {
          tgt.value = val;
          const tr2 = tgt.closest('tr');
          const id2 = parseInt(tr2.dataset.pekerjaanId, 10);
          const pv2 = tr2.querySelector('.fx-preview');
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
  function persistRowFormula(id) {
    const map = loadFormulas();
    map[id] = { raw: rawInputById[id] || '', fx: !!fxModeById[id] };
    saveFormulas(map);
  }
  function normQty(val) {
    if (val === '' || val == null) return '';
    const s = normalizeLocaleNumericString(val);
    let num = Number(s);
    if (!Number.isFinite(num)) return '';
    if (num < 0) num = 0;
    const rounded = roundHalfUp(num, STORE_PLACES);
    return formatIdSmart(rounded);
  }
  function setRowDirtyVisual(id, isDirty) {
    const tr = rows.find(r => parseInt(r.dataset.pekerjaanId, 10) === id);
    if (!tr) return;
    tr.classList.toggle('table-warning', !!isDirty);
    tr.classList.toggle('vp-row-edited', !!isDirty);
  }
  function markRowSaved(tr) {
    if (!tr) return;
    tr.classList.remove('vp-row-edited');
    tr.classList.add('vp-row-saved');
    setTimeout(() => tr.classList.remove('vp-row-saved'), 1800);
  }
  function handleInputChange(id, inputEl, previewEl) {
    const raw = String(inputEl.value || '');
    rawInputById[id] = raw;

    inputEl.classList.remove('is-invalid', 'is-valid');
    inputEl.removeAttribute('title');
    if (previewEl) previewEl.textContent = '';

    if (isFormulaMode(id, raw)) {
      const expr = raw.startsWith('=') ? raw : ('=' + raw);
      try {
        if (typeof VolFormula === 'undefined' || !VolFormula.evaluate) throw new Error('Formula engine tidak tersedia');
        let val = VolFormula.evaluate(expr, variables, { clampMinZero: true });
        if (!Number.isFinite(val) || val < 0) val = 0;
        const rounded = roundHalfUp(val, STORE_PLACES);
        currentValueById[id] = rounded;
        if (previewEl) previewEl.textContent = `${expr}  →  ${formatIdSmart(rounded)}`;
        inputEl.classList.add('is-valid');
        updateDirty(id);
      } catch (e) {
        inputEl.classList.add('is-invalid');
        const msg = (e && e.message) ? e.message : 'Formula error';
        inputEl.setAttribute('title', msg);
      }
    } else {
      const n = parseNumberOrEmpty(raw);
      if (n === '') {
        if (previewEl) previewEl.textContent = '';
      } else {
        const clamped = n < 0 ? 0 : n;
        const rounded = roundHalfUp(clamped, STORE_PLACES);
        currentValueById[id] = rounded;
        inputEl.classList.add('is-valid');
      }
      updateDirty(id);
    }

    setBtnSaveEnabled();
    scheduleAutosave();
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
  function reevaluateAllFormulas() {
    rows.forEach(tr => {
      const id = parseInt(tr.dataset.pekerjaanId, 10);
      const input = tr.querySelector('.qty-input');
      const preview = tr.querySelector('.fx-preview');
      const raw = String(rawInputById[id] || input.value || '');
      if (!raw.trim()) return;
      if (isFormulaMode(id, raw)) handleInputChange(id, input, preview, false);
    });
    setBtnSaveEnabled();
  }

  // ===== Parameter table (Label & Kode)
  function slugifyName(s) {
    let t = String(s || '').trim();
    if (!t) return '';
    t = t.normalize('NFKD').replace(/[^\w\s]/g, '').replace(/\s+/g, '_');
    if (/^[0-9]/.test(t)) t = '_' + t;
    t = t.replace(/_+/g, '_').replace(/^_+|_+$/g, '');
    return t || '_param';
  }

  function renderVarTable() {
    if (!varTable) return;
    const tbody = varTable.querySelector('tbody');
    tbody.innerHTML = '';
    const codes = Object.keys(variables);
    if (codes.length === 0) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td colspan="3" class="text-muted">Belum ada parameter.</td>`;
      tbody.appendChild(tr);
      return;
    }
    codes.sort((a,b) => (varLabels[a] || a).localeCompare(varLabels[b] || b, 'id'));
    codes.forEach(code => {
      const val = variables[code];
      const label = varLabels[code] || code;
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>
          <input type="text" class="form-control form-control-sm var-label" value="${escapeHtml(label)}" aria-label="Nama/Label parameter">
          <small class="text-muted d-block mt-1">Kode: <code>${escapeHtml(code)}</code></small>
        </td>
        <td>
          <input type="text" class="form-control form-control-sm var-value" value="${formatIdSmart(val)}" aria-label="Nilai parameter">
        </td>
        <td class="text-end">
          <button type="button" class="btn btn-sm btn-outline-danger var-del">Hapus</button>
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
          e.target.value = formatIdSmart(val);
          return;
        }
        variables[code] = roundHalfUp(Number(n), STORE_PLACES);
        saveVars();
        reevaluateAllFormulas();
      });
      tr.querySelector('.var-del').addEventListener('click', () => {
        const nm = varLabels[code] || code;
        if (!confirm(`Hapus parameter "${nm}" (kode: ${code})?`)) return;
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
          <small class="text-muted d-block mt-1">Kode dibuat otomatis dari label.</small>
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
      const valEl   = tr.querySelector('.var-value');
      labelEl && labelEl.focus();

      const doCancel = () => tr.remove();
      const doSave = () => {
        const label = String(labelEl.value || '').trim();
        const n = parseNumberOrEmpty(valEl.value);
        labelEl.classList.toggle('is-invalid', !label);
        valEl.classList.toggle('is-invalid', n === '');
        if (!label || n === '') return;

        const code = slugifyName(label);
        if (Object.prototype.hasOwnProperty.call(variables, code)) {
          labelEl.classList.add('is-invalid');
          const help = labelEl.parentElement.querySelector('.invalid-feedback');
          if (help) help.textContent = 'Label menghasilkan kode duplikat. Ubah label.';
          return;
        }
        variables[code] = roundHalfUp(Number(n), STORE_PLACES);
        varLabels[code] = label;
        saveVars(); saveVarLabels();
        tr.remove();
        renderVarTable();
        reevaluateAllFormulas();
      };

      tr.querySelector('.var-save').addEventListener('click', doSave);
      tr.querySelector('.var-cancel').addEventListener('click', doCancel);
      [labelEl, valEl].forEach(el => el.addEventListener('keydown', e => {
        if (e.key === 'Enter') doSave();
        if (e.key === 'Escape') doCancel();
      }));
    });
    btnVarAdd.dataset.bound = '1';
  }

  // Export / Import (JSON + CSV)
  function exportVariables() {
    try {
      const payload = { _format: 'vp-vars-v2', variables, labels: varLabels };
      const data = JSON.stringify(payload, null, 2);
      const blob = new Blob([data], { type: 'application/json' });
      const a = document.createElement('a');
      const ts = new Date().toISOString().slice(0,19).replace(/[:T]/g,'-');
      a.href = URL.createObjectURL(blob);
      a.download = `parameter_${projectId}_${ts}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      showToast('Parameter diekspor.', 'success');
    } catch { showToast('Gagal export parameter.', 'danger'); }
  }

  function parseCSV(text) {
    // Sederhana: pisah baris, split koma/semicolon/tab
    const lines = String(text || '').split(/\r?\n/).map(l=>l.trim()).filter(Boolean);
    const out = [];
    for (const line of lines) {
      const cells = line.split(/[,;\t]/).map(s=>s.trim());
      if (cells.length < 2) continue;
      out.push({ label: cells[0], value: cells[1] });
    }
    return out;
  }

  function importVariablesFromFile(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const rawText = String(reader.result || '{}');
        const isCsv = /\.csv$/i.test(file.name) || file.type === 'text/csv';
        if (isCsv) {
          const rowsCsv = parseCSV(rawText);
          if (!rowsCsv.length) throw new Error('csv-empty');
          const nextVars = {};
          const nextLabels = {};
          rowsCsv.forEach(r => {
            const label = String(r.label || '').trim();
            const n = parseNumberOrEmpty(r.value);
            if (!label || n === '') return;
            let code = slugifyName(label);
            if (!code) return;
            if (nextVars[code] != null || variables[code] != null) {
              // pecahkan duplikat sederhana
              let i = 2;
              while (nextVars[code] != null || variables[code] != null) code = `${slugifyName(label)}_${i++}`;
            }
            nextVars[code] = roundHalfUp(Number(n), STORE_PLACES);
            nextLabels[code] = label;
          });
          if (!Object.keys(nextVars).length) throw new Error('csv-none');
          variables = { ...variables, ...nextVars };
          varLabels = { ...varLabels, ...nextLabels };
          saveVars(); saveVarLabels();
          renderVarTable();
          reevaluateAllFormulas();
          showToast('Parameter CSV diimport.', 'success');
          return;
        }

        // JSON
        const obj = JSON.parse(rawText);
        let nextVars = {}, nextLabels = {};
        if (obj && typeof obj === 'object' && obj._format === 'vp-vars-v2') {
          nextVars = (obj.variables && typeof obj.variables === 'object') ? obj.variables : {};
          nextLabels = (obj.labels && typeof obj.labels === 'object') ? obj.labels : {};
        } else if (obj && typeof obj === 'object') {
          Object.keys(obj).forEach(code => {
            const n = parseNumberOrEmpty(obj[code]);
            if (n !== '') { nextVars[code] = Number(n); nextLabels[code] = code; }
          });
        } else throw new Error('format');

        const normalizedVars = {};
        const normalizedLabels = {};
        Object.keys(nextVars).forEach(code => {
          let safe = String(code || '').trim();
          safe = safe.normalize('NFKD').replace(/[^\w]/g, '_').replace(/_+/g,'_').replace(/^_+|_+$/g,'');
          if (/^[0-9]/.test(safe)) safe = '_' + safe;
          if (!safe) return;
          const val = parseNumberOrEmpty(nextVars[code]);
          if (val === '') return;
          normalizedVars[safe] = roundHalfUp(Number(val), STORE_PLACES);
          const lbl = String((nextLabels && nextLabels[code]) || code || '').trim();
          normalizedLabels[safe] = lbl || safe;
        });

        if (Object.keys(normalizedVars).length === 0) {
          showToast('File JSON tidak berisi parameter valid.', 'warning'); return;
        }
        variables = { ...variables, ...normalizedVars };
        varLabels = { ...varLabels, ...normalizedLabels };
        saveVars(); saveVarLabels();
        renderVarTable();
        reevaluateAllFormulas();
        showToast('Parameter diimport.', 'success');
      } catch {
        showToast('Gagal import.', 'danger');
      }
    };
    reader.onerror = () => showToast('Gagal membaca file.', 'danger');
    reader.readAsText(file);
  }

  if (btnVarExportBtn) btnVarExportBtn.addEventListener('click', exportVariables);
  if (btnVarImportBtn && fileVarImport) {
    btnVarImportBtn.addEventListener('click', () => fileVarImport.click());
    fileVarImport.addEventListener('change', (e) => {
      const f = e.target.files && e.target.files[0];
      importVariablesFromFile(f);
      fileVarImport.value = '';
    });
  }

  // ===== Enhance table (groups) + Prefill volume
  async function enhanceWithGroups() {
    try {
      const res = await fetch(`/detail_project/api/project/${projectId}/list-pekerjaan/tree/`, { credentials: 'same-origin' });
      const json = await res.json().catch(() => ({}));
      if (!json || !json.ok || !Array.isArray(json.klasifikasi)) return;
      const tbody = document.querySelector('#vp-table tbody');
      tbody.innerHTML = '';
      rows.length = 0; // reset list row references

      let counter = 0;
      json.klasifikasi.forEach(k => {
        const trK = document.createElement('tr');
        trK.className = 'vp-klass';
        trK.innerHTML = `<td colspan="5">${escapeHtml(k.name || '(Tanpa Klasifikasi)')}</td>`;
        tbody.appendChild(trK);
        (k.sub || []).forEach(s => {
          const trS = document.createElement('tr');
          trS.className = 'vp-sub';
          trS.innerHTML = `<td colspan="5">${escapeHtml(s.name || '(Tanpa Sub)')}</td>`;
          tbody.appendChild(trS);
          (s.pekerjaan || []).forEach(p => {
            counter += 1;
            const tr = document.createElement('tr');
            tr.dataset.pekerjaanId = p.id;
            tr.innerHTML = `
              <td>${counter}</td>
              <td class="text-monospace">${escapeHtml(p.snapshot_kode || '')}</td>
              <td class="text-wrap">${escapeHtml(p.snapshot_uraian || '')}</td>
              <td>${escapeHtml(p.snapshot_satuan || '')}</td>
              <td>
                <div class="d-flex align-items-start gap-2 vp-cell" style="overflow: visible;">
                  <button type="button" class="btn btn-outline-secondary btn-sm fx-toggle"
                          title="Mode formula: awali dengan '=' atau tekan Ctrl+Space"
                          aria-pressed="false">fx</button>
                  <div class="flex-grow-1" style="position: relative;">
                    <input type="text" inputmode="decimal" class="form-control form-control-sm qty-input" aria-label="Quantity">
                    <div class="form-text fx-preview text-muted small" style="min-height:1rem;"></div>
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
      setTopOffsets();
    } catch (e) {
      console.warn('Enhance groups gagal', e);
    }
  }

  (async function prefill() {
    try {
      const res = await fetch(`/detail_project/api/project/${projectId}/rekap/`, { credentials: 'same-origin' });
      const json = await res.json().catch(() => ({}));
      const volMap = {};
      if (json && json.rows && Array.isArray(json.rows)) {
        json.rows.forEach(r => {
          if (r && typeof r.pekerjaan_id === 'number') {
            const v = Number(r.volume || 0);
            volMap[r.pekerjaan_id] = Number.isFinite(v) ? v : 0;
          }
        });
      }
      await enhanceWithGroups();

      rows.forEach(tr => {
        const id = parseInt(tr.dataset.pekerjaanId, 10);
        const input = tr.querySelector('.qty-input');
        const preview = tr.querySelector('.fx-preview');
        const base = Number(volMap[id] || 0);
        originalValueById[id] = roundHalfUp(base, STORE_PLACES);
        currentValueById[id] = originalValueById[id];

        // Render tampilan: jika integer → "1.000", jika ada pecahan → sesuai
        input.value = base ? formatIdSmart(base) : '';

        const f = formulaState[id];
        if (f && typeof f.raw === 'string' && f.raw.trim()) {
          input.value = f.raw;
          handleInputChange(id, input, preview, false);
        }
        setRowDirtyVisual(id, false);
      });

      setBtnSaveEnabled();
      buildSearchIndex();
      setTopOffsets();
    } catch (e) {
      console.warn('Prefill rekap gagal', e);
      await enhanceWithGroups();
      rows.forEach(tr => {
        const id = parseInt(tr.dataset.pekerjaanId, 10);
        originalValueById[id] = 0;
        currentValueById[id] = 0;
        setRowDirtyVisual(id, false);
      });
      setBtnSaveEnabled();
      setTopOffsets();
    }
  })();

  // ===== Autosave + Undo =====
  function scheduleAutosave(ms = AUTOSAVE_MS) {
    if (autosaveTimer) clearTimeout(autosaveTimer);
    if (dirtySet.size === 0) return;
    autosaveTimer = setTimeout(() => {
      if (dirtySet.size > 0) saveDirty({ reason: 'autosave' });
    }, ms);
  }

  async function saveDirty({ reason = 'manual' } = {}) {
    if (saving) return;
    const postingIds = Array.from(dirtySet.values());
    if (!postingIds.length) return;

    // Kumpulkan batch (before/after) untuk Undo
    const changes = postingIds.map(id => ({
      id,
      before: Number(originalValueById[id] ?? 0),
      after: Number(currentValueById[id] ?? 0)
    }));

    // Build payload
    const items = changes.map(({id, after}) => {
      let q = after;
      if (!Number.isFinite(q)) q = 0;
      const rounded = roundHalfUp(q, STORE_PLACES);
      return { pekerjaan_id: id, quantity: rounded };
    });

    // UI state
    saving = true;
    if (reason === 'manual' && btnSaveSpin) btnSaveSpin.classList.remove('d-none');
    if (reason === 'manual') btnSave.disabled = true;

    try {
      const res = await fetch(`/detail_project/api/project/${projectId}/volume-pekerjaan/save/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
        credentials: 'same-origin',
        body: JSON.stringify({ items })
      });
      const json = await res.json().catch(() => ({}));

      const markErrors = () => {
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

      if (!res.ok || json.ok === false) {
        markErrors();
        const saved = (json && typeof json.saved === 'number') ? json.saved : 0;
        showToast(`Sebagian/semua gagal disimpan. Tersimpan: ${saved}`, 'danger');
        return;
      }

      // Success → commit baseline & visuals
      postingIds.forEach(id => {
        originalValueById[id] = currentValueById[id] ?? 0;
        const tr = rows.find(r => parseInt(r.dataset.pekerjaanId, 10) === id);
        if (tr) {
          const input = tr.querySelector('.qty-input');
          if (input) {
            input.classList.remove('is-invalid');
            input.classList.add('is-valid');
            setTimeout(() => input.classList.remove('is-valid'), 900);
          }
          markRowSaved(tr);
        }
        dirtySet.delete(id);
        setRowDirtyVisual(id, false);
      });
      setBtnSaveEnabled();

      // Simpan ke undo stack (hanya bila ada perubahan nyata)
      const realChanges = changes.filter(c => roundHalfUp(c.before, STORE_PLACES) !== roundHalfUp(c.after, STORE_PLACES));
      if (realChanges.length) {
        undoStack.push({ ts: Date.now(), changes: realChanges });
        if (undoStack.length > UNDO_MAX) undoStack.shift();
        showActionToast(`Tersimpan ${realChanges.length} item.`, [
          { label: 'Undo', class: 'btn-warning', onClick: tryUndoLast }
        ]);
      } else if (reason === 'manual') {
        showToast('Tidak ada perubahan.', 'warning');
      }
    } catch (e) {
      console.error(e);
      showToast('Gagal simpan (network/server error).', 'danger');
    } finally {
      if (reason === 'manual' && btnSaveSpin) btnSaveSpin.classList.add('d-none');
      if (reason === 'manual') btnSave.disabled = false;
      saving = false;
    }
  }

  async function tryUndoLast() {
    const last = undoStack.pop();
    if (!last || !last.changes || !last.changes.length) { showToast('Tidak ada yang bisa di-undo.', 'warning'); return; }

    // Apply "before" ke state & UI lalu kirim simpan
    last.changes.forEach(({id, before}) => {
      currentValueById[id] = roundHalfUp(Number(before), STORE_PLACES);
      const tr = rows.find(r => parseInt(r.dataset.pekerjaanId, 10) === id);
      const input = tr?.querySelector('.qty-input');
      const preview = tr?.querySelector('.fx-preview');
      if (input) {
        input.value = formatIdSmart(currentValueById[id]);
        input.classList.add('is-valid'); setTimeout(()=>input.classList.remove('is-valid'), 700);
      }
      if (preview) preview.textContent = '';
      updateDirty(id);
    });
    await saveDirty({ reason: 'manual' });
  }

  // Save manual
  btnSave && btnSave.addEventListener('click', () => saveDirty({ reason: 'manual' }));

  // Undo hotkey global: Ctrl+Alt+Z (tidak mengganggu undo bawaan input)
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.altKey && e.key.toLowerCase() === 'z') {
      e.preventDefault(); tryUndoLast();
    }
  });

  // Guard before unload
  window.addEventListener('beforeunload', (e) => {
    if (window.__vpDirty) { e.preventDefault(); e.returnValue = ''; return ''; }
  });

  // ===== Storage helpers
  function storageKeyVars() { return `volvars:${projectId}`; }
  function storageKeyVarLabels() { return `volvars_labels:${projectId}`; }
  function storageKeyForms() { return `volform:${projectId}`; }

  function loadVars() {
    try {
      const raw = localStorage.getItem(storageKeyVars());
      variables = raw ? JSON.parse(raw) : {};
      if (typeof variables !== 'object' || !variables) variables = {};
    } catch { variables = {}; }
  }
  function saveVars() { localStorage.setItem(storageKeyVars(), JSON.stringify(variables)); }
  function loadVarLabels() {
    try {
      const raw = localStorage.getItem(storageKeyVarLabels());
      varLabels = raw ? JSON.parse(raw) : {};
      if (!varLabels || typeof varLabels !== 'object') varLabels = {};
    } catch { varLabels = {}; }
  }
  function saveVarLabels() { localStorage.setItem(storageKeyVarLabels(), JSON.stringify(varLabels)); }

  function loadFormulas() {
    try {
      const raw = localStorage.getItem(storageKeyForms());
      const obj = raw ? JSON.parse(raw) : {};
      return obj && typeof obj === 'object' ? obj : {};
    } catch { return {}; }
  }
  function saveFormulas(map) { localStorage.setItem(storageKeyForms(), JSON.stringify(map)); }

  // ---- Angkat offcanvas ke body (hindari clipping)
  (function liftOffcanvasToBody() {
    try { if (offcanvasEl && offcanvasEl.parentElement !== document.body) document.body.appendChild(offcanvasEl); } catch {}
  })();

  // ==== Init: load variables, render table
  loadVars();
  loadVarLabels();
  Object.keys(variables).forEach(code => { if (!varLabels[code]) varLabels[code] = code; });
  saveVarLabels();
  renderVarTable();

})();
