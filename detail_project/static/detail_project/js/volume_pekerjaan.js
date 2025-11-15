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
  // Gunakan Numeric bila tersedia agar konsisten (koma <-> titik)
  const N = window.Numeric || null;

  // ---- Konteks dasar
  const projectId = root.dataset.projectId || root.dataset.pid;
  // NEW: endpoint dari data-attribute (fallback ke pattern lama)
  const EP_SAVE    = root.dataset.endpointSave
    || `/detail_project/api/project/${projectId}/volume-pekerjaan/save/`;
  // State formula (raw,is_fx) disimpan/diambil dari endpoint ini
  const EP_FORMULA_STATE = root.dataset.endpointFormula
    || `/detail_project/api/project/${projectId}/volume-formula-state/`;
  // Pohon data untuk membangun grup Klas/Sub/Pekerjaan 
  const EP_TREE    = root.dataset.endpointTree
    || `/detail_project/api/project/${projectId}/list-pekerjaan/tree/`;

  // Presisi simpan (DB 3dp), tampilan dinamis 0..3 dp
  const STORE_PLACES = 3;

  // Debounce autosave (ms)
  const AUTOSAVE_MS = Number(root.dataset.autosaveMs || 30000);

  // ---- State in-memory (global selector agar mendukung multi-tabel/di dalam card)
  let rows = Array.from(document.querySelectorAll('tr[data-pekerjaan-id]'));
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
  const btnSaveTop = document.getElementById('btn-save');
  const btnSaveSpin = document.getElementById('btn-save-spin');
  const saveStatusEl = document.getElementById('vp-save-status');
  let saveStatusTimer = null;

  function setSaveStatus(message, variant){
    try{
      if (!saveStatusEl) return;
      saveStatusEl.textContent = message || '';
      saveStatusEl.classList.remove('text-success','text-warning','text-danger');
      if (variant === 'success') saveStatusEl.classList.add('text-success');
      else if (variant === 'warning') saveStatusEl.classList.add('text-warning');
      else if (variant === 'danger') saveStatusEl.classList.add('text-danger');
      if (saveStatusTimer) clearTimeout(saveStatusTimer);
      if (message) saveStatusTimer = setTimeout(()=>{
        saveStatusEl.textContent = '';
        saveStatusEl.classList.remove('text-success','text-warning','text-danger');
      }, 3200);
    }catch{}
  }

  const varTable = document.getElementById('vp-var-table');
  const btnVarAdd = document.getElementById('vp-var-add');
  const btnVarImportBtn = document.getElementById('vp-var-import-btn');
  const btnVarExportBtn = document.getElementById('vp-var-export-btn');
  const fileVarImport = document.getElementById('vp-var-import');
  // Overlay sidebar (pengganti offcanvas)
  const sidebarEl = document.getElementById('vp-sidebar');

  const searchInput = document.getElementById('vp-search');
  const searchDrop = document.getElementById('vp-search-results');
  const prefixBadge = document.getElementById('vp-search-prefix-badge');

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
    } catch {}
  }

  ['focus','input','keydown'].forEach(ev => {
    if (searchInput) searchInput.addEventListener(ev, positionSearchDropdown, { passive: true });
  });
  window.addEventListener('resize', positionSearchDropdown, { passive: true });
  window.addEventListener('scroll', (e)=>{
    // keep dropdown anchored during scroll when visible
    if (searchDrop && !searchDrop.classList.contains('d-none')) positionSearchDropdown();
  }, { passive: true });

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

  // ---- HTTP helper: gunakan DP.core.http bila ada
  const HTTP = (function(){
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
      const body = await r.json().catch(()=> ({}));
      return { ok: r.ok, status: r.status, data: body, errors: body?.errors || [] };
    }
    return { jget, jpost };
  })();

  // ---- Toast helper: gunakan DP.core.toast bila ada
  const TOAST = (function(){
    const t = (window.DP && DP.core && DP.core.toast) ? DP.core.toast : null;
    return {
      ok(msg){ t ? t.show({message:msg, variant:'success'}) : showToast(msg, 'success'); },
      warn(msg){ t ? t.show({message:msg, variant:'warning'}) : showToast(msg, 'warning'); },
      err(msg){ t ? t.show({message:msg, variant:'danger'}) : showToast(msg, 'danger'); },
      action(msg, actions){ showActionToast(msg, actions); }
    };
  })();

  const sourceChange = window.DP?.sourceChange || null;
  const bannerEl = document.getElementById('vp-sync-banner');
  const bannerTextEl = document.getElementById('vp-sync-text');
  const bannerFocusBtn = document.getElementById('vp-sync-focus');
  let pendingVolumeJobs = new Set(
    sourceChange && projectId ? sourceChange.listVolumeJobs(projectId) : [],
  );

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
    const shouldShow = count > 0;
    bannerEl.classList.toggle('d-none', !shouldShow);
    if (!shouldShow) return;
    if (bannerTextEl) {
      bannerTextEl.textContent = `${count} pekerjaan perlu diperbarui setelah perubahan sumber.`;
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
      TOAST.warn('Tidak ada pekerjaan yang perlu diperbarui.');
      return;
    }
    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    target.classList.add('vp-row-highlight');
    setTimeout(() => target.classList.remove('vp-row-highlight'), 1500);
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


  // ===== Search Index & UI =====
  let searchIndex = []; // {type, id, label, el}
  let searchState = { items: [], activeIdx: -1 };

  // ===== Collapse (toggle Klas/Sub) =====
  const COLLAPSE_KEY = `vp_collapse:${projectId}`;
  let collapsed = { klas: {}, sub: {} };
  try { const raw = localStorage.getItem(COLLAPSE_KEY); if (raw) collapsed = Object.assign({klas:{},sub:{}}, JSON.parse(raw)||{}); } catch {}
  function saveCollapse(){ try{ localStorage.setItem(COLLAPSE_KEY, JSON.stringify(collapsed)); }catch{} }
  function slugKey(s){
    return String(s||'').trim().toLowerCase().normalize('NFKD')
      .replace(/[^\w\s-]/g,'').replace(/\s+/g,'_').replace(/_+/g,'_').replace(/^_+|_+$/g,'') || '_';
  }
  function applyCollapseOnTable(){
    const tbody = document.querySelector('#vp-table tbody'); if(!tbody) return;
    let curK = null, curS = null;
    Array.from(tbody.rows).forEach(tr=>{
      if(tr.classList.contains('vp-klass')){
        curK = tr.getAttribute('data-klas-id') || slugKey(tr.textContent);
        tr.classList.toggle('is-collapsed', !!collapsed.klas[curK]);
        return;
      }
      if(tr.classList.contains('vp-sub')){
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
    document.querySelectorAll('.vp-klas-card, .vp-sub-card').forEach(card => {
      const isKlas = card.classList.contains('vp-klas-card');
      const key = isKlas ? (card.getAttribute('data-klas-id') || slugKey(card.querySelector('.card-header')?.textContent))
                         : (card.getAttribute('data-sub-id')  || slugKey(card.querySelector('.card-header')?.textContent));
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
  document.addEventListener('click', (e)=>{
    // row-based (fallback dari builder EP_TREE)
    const btnRow = e.target.closest('.vp-toggle');
    if (btnRow) {
      const type = btnRow.getAttribute('data-type'); const key = btnRow.getAttribute('data-key');
      if(!type || !key) return;
      if(type==='klas') collapsed.klas[key] = !collapsed.klas[key];
      else collapsed.sub[key] = !collapsed.sub[key];
      saveCollapse(); applyCollapseOnTable(); applyCollapseOnCards(); return;
    }
    // card-based (SSR / template)
    const btnCard = e.target.closest('.vp-card-toggle');
    if (btnCard) {
      const type = btnCard.getAttribute('data-type'); const key = btnCard.getAttribute('data-key');
      if(!type || !key) return;
      if(type==='klas') collapsed.klas[key] = !collapsed.klas[key];
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
    const match  = text.slice(idx, idx + q.length);
    const after  = text.slice(idx + q.length);
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
    // Tampilkan lalu atur posisi (flip jika mendekati bawah viewport)
    state.box.style.display = 'block';
    state.box.style.opacity = '0';
    requestAnimationFrame(() => {
      try {
        const wrap = inputEl.closest('.flex-grow-1') || inputEl.parentElement;
        const rect = wrap.getBoundingClientRect();
        const menuH = state.box.offsetHeight || 240;
        const gap = 6;
        const spaceBelow = window.innerHeight - rect.bottom;
        const spaceAbove = rect.top;
        const placeDown = spaceBelow >= Math.min(menuH, 160);
        // Reset anchors
        state.box.style.left = '0';
        state.box.style.right = '0';
        state.box.style.maxHeight = '';
        state.box.style.top = '';
        state.box.style.bottom = '';
        if (placeDown) {
          state.box.style.top = `calc(100% + ${gap}px)`;
          state.box.style.bottom = 'auto';
          const mh = Math.max(120, Math.min(menuH, Math.floor(spaceBelow - gap)));
          state.box.style.maxHeight = `${mh}px`;
        } else {
          state.box.style.top = 'auto';
          state.box.style.bottom = `calc(100% + ${gap}px)`;
          const mh = Math.max(120, Math.min(menuH, Math.floor(spaceAbove - gap)));
          state.box.style.maxHeight = `${mh}px`;
        }
      } finally {
        state.box.style.opacity = '1';
      }
    });
  }

  // Robust UI->canonical parser for quantity (handles id-ID grouping)
  function canonFromUIQty(raw){
    let s = String(raw ?? '').trim();
    if (!s) return '';
    s = s.replace(/\u00A0/g,' ').replace(/\s+/g,'').replace(/_/g,'');
    const hasDot = s.includes('.');
    const hasComma = s.includes(',');
    if (hasDot && !hasComma){
      const dotGrouping = /^\d{1,3}(\.\d{3})+$/;
      if (dotGrouping.test(s)) s = s.replace(/\./g, '');
      // else: treat dot as decimal (e.g., 1.25)
    } else if (hasComma && !hasDot){
      const commaGrouping = /^\d{1,3}(,\d{3})+$/;
      if (commaGrouping.test(s)) s = s.replace(/,/g, '');
      else s = s.replace(/,/g, '.'); // comma as decimal
    } else if (hasDot && hasComma){
      const lastComma = s.lastIndexOf(',');
      const lastDot = s.lastIndexOf('.');
      if (lastComma > lastDot){
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

  // === Server-side persist untuk formula state (silent on fail)
  async function persistRowFormulaServer(id) {
    try {
      const payload = { items: [{ pekerjaan_id: id, raw: String(rawInputById[id] || ''), is_fx: !!fxModeById[id] }] };
      await HTTP.jpost(EP_FORMULA_STATE, payload);
    } catch {}
  }

  function persistRowFormula(id) {
    const map = loadFormulas();
    map[id] = { raw: rawInputById[id] || '', fx: !!fxModeById[id] };
    saveFormulas(map);
    persistRowFormulaServer(id);
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
    if (tgt) { tgt.focus(); try { tgt.select(); } catch{} }
  }

  function bindRow(tr) {
    if (tr.dataset.bound === '1') return;
    tr.dataset.bound = '1';

    const id = parseInt(tr.dataset.pekerjaanId, 10);
    const input = tr.querySelector('.qty-input');
    const fxBtn = tr.querySelector('.fx-toggle');
    const preview = tr.querySelector('.fx-preview');

    try { if (window.bootstrap && fxBtn) new bootstrap.Tooltip(fxBtn); } catch {}

    // Jika localStorage punya state awal, apply ringan (server akan override saat prefill)
    const initMap = loadFormulas();
    const f = initMap[id] || {};
    if (typeof f.fx === 'boolean') {
      fxModeById[id] = !!f.fx;
      if (fxBtn) {
        fxBtn.setAttribute('aria-pressed', String(!!f.fx));
        fxBtn.classList.toggle('active', !!f.fx);
      }
    } else { fxModeById[id] = false; }
    if (typeof f.raw === 'string' && f.raw.trim() && input && !input.value) {
      rawInputById[id] = f.raw;
      input.value = f.raw;
    }

    // Mark initial empty/zero state
    if (input) {
      const raw0 = String(input.value || '').trim();
      tr.classList.toggle('vp-row-empty', !raw0);
      const c0 = canonFromUIQty(raw0);
      if (c0 !== '') tr.classList.toggle('vp-row-zero', Number(c0) === 0);
      tr.classList.remove('vp-row-invalid');
    }

    fxBtn && fxBtn.addEventListener('click', () => {
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
    input && input.addEventListener('input', () => {
      clearTimeout(debTimer);

      // Auto-enable FX jika user mulai mengetik "="
      const valNow = String(input.value || '').trim();
      if (valNow.startsWith('=') && !fxModeById[id]) {
        fxModeById[id] = true;
        if (fxBtn) {
          fxBtn.setAttribute('aria-pressed', 'true');
          fxBtn.classList.add('active');
        }
        persistRowFormula(id);
      }

      updateSuggestions(input, id);
      debTimer = setTimeout(() => handleInputChange(id, input, preview, false), 120);
    });
    input && input.addEventListener('blur', () => {
      if (!isFormulaMode(id, input.value)) {
        const normalized = normQty(input.value);
        if (normalized !== '') input.value = normalized;
        // Update row markers based on normalized numeric
        const tr2 = rows.find(r => parseInt(r.dataset.pekerjaanId, 10) === id);
        const c = canonFromUIQty(input.value);
        const isEmpty2 = !String(input.value||'').trim();
        input.classList.toggle('vp-empty', isEmpty2);
        if (tr2){
          tr2.classList.toggle('vp-row-empty', isEmpty2);
          tr2.classList.toggle('vp-row-zero', (!isEmpty2 && c !== '' && Number(c) === 0));
          tr2.classList.remove('vp-row-invalid');
        }
      } else {
        // Formula mode: only toggle empty flag; vp-row-invalid handled in input handler
        input.classList.toggle('vp-empty', !String(input.value||'').trim());
      }
      setTimeout(() => hideSuggest(input), 120);
    });
    input && input.addEventListener('focus', () => updateSuggestions(input, id));
    input && input.addEventListener('keydown', (ev) => {
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
          if (fxBtn) {
            fxBtn.setAttribute('aria-pressed', 'true');
            fxBtn.classList.add('active');
          }
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
          tgt.classList.toggle('vp-empty', !String(tgt.value||'').trim());
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
  function setRowDirtyVisual(id, isDirty) {
    const tr = rows.find(r => parseInt(r.dataset.pekerjaanId, 10) === id);
    if (!tr) return;
    // Border-only indicator (no Bootstrap background)
    if (tr.classList.contains('table-warning')) tr.classList.remove('table-warning');
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
    // flag kosong
    const isEmpty = raw.trim() === '';
    inputEl.classList.toggle('vp-empty', isEmpty);
    const tr = rows.find(r => parseInt(r.dataset.pekerjaanId, 10) === id);
    if (tr) tr.classList.toggle('vp-row-empty', isEmpty);

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
        // Row indicators: valid formula clears invalid, set zero if 0
        if (tr) {
          tr.classList.remove('vp-row-invalid');
          tr.classList.toggle('vp-row-zero', Number(rounded) === 0);
        }
        updateDirty(id);
      } catch (e) {
        inputEl.classList.add('is-invalid');
        const msg = (e && e.message) ? e.message : 'Formula error';
        inputEl.setAttribute('title', msg);
        if (tr) tr.classList.add('vp-row-invalid');
      }
      persistRowFormula(id); // simpan raw & state fx setiap kali formula diproses
    } else {
      // Robust parse to avoid "1.000" -> 1 error (id-ID grouping)
      const c = canonFromUIQty(raw);
      const n = c === '' ? '' : Number(c);
      if (n === '') {
        if (previewEl) previewEl.textContent = '';
        if (tr) tr.classList.remove('vp-row-invalid');
      } else {
        const clamped = n < 0 ? 0 : n;
        const rounded = roundHalfUp(clamped, STORE_PLACES);
        currentValueById[id] = rounded;
        inputEl.classList.add('is-valid');
        if (tr) {
          tr.classList.remove('vp-row-invalid');
          tr.classList.toggle('vp-row-zero', Number(rounded) === 0);
        }
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
          <input type="text" class="form-control form-control-sm var-label" value="${escapeHtml(label)}" aria-label="Nama/Label parameter" readonly>
          <small class="text-muted d-block mt-1">Kode: <code>${escapeHtml(code)}</code></small>
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
            btnEdit.setAttribute('title','Simpan'); btnEdit.setAttribute('aria-label','Simpan');
            labelEl.focus();
          } else {
            // Save and exit edit mode
            const nextLabel = String(labelEl.value || '').trim();
            const n = parseNumberOrEmpty(valueEl.value);
            let ok = true;
            if (!nextLabel) { ok = false; labelEl.classList.add('is-invalid'); setTimeout(()=>labelEl.classList.remove('is-invalid'), 1200); labelEl.value = varLabels[code] || code; }
            if (n === '')     { ok = false; valueEl.classList.add('is-invalid'); setTimeout(()=>valueEl.classList.remove('is-invalid'), 1200); valueEl.value = formatIdSmart(variables[code]); }
            if (ok) {
              varLabels[code] = nextLabel; saveVarLabels();
              variables[code] = roundHalfUp(Number(n), STORE_PLACES); saveVars();
              reevaluateAllFormulas();
            }
            labelEl.readOnly = true; valueEl.readOnly = true;
            if (icon) icon.className = 'bi bi-pencil';
            btnEdit.setAttribute('title','Ubah'); btnEdit.setAttribute('aria-label','Ubah');
          }
        });
      }
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

  // === Unified Import/Export (JSON | CSV | XLSX*) ==================
  // *XLSX untuk import/export akan aktif jika SheetJS ada (window.XLSX)

  function parseCSV(text) {
    const lines = String(text || '').split(/\r?\n/).map(l=>l.trim()).filter(Boolean);
    const out = [];
    for (const line of lines) {
      const cells = line.split(/[,;\t]/).map(s=>s.trim());
      if (!cells.length) continue;
      // Toleransi header
      if (/^nama|label$/i.test(cells[0]) || /^nilai|value$/i.test(cells[1]||"")) continue;
      if (cells.length < 2) continue;
      out.push({ label: cells[0], value: cells[1] });
    }
    return out;
  }

  function csvFromVars(varsObj, labelsObj) {
    const codes = Object.keys(varsObj);
    const rows = codes
      .sort((a,b)=>(labelsObj[a]||a).localeCompare(labelsObj[b]||b, 'id'))
      .map(code => `${(labelsObj[code]||code).replace(/[\r\n,]/g,' ')} , ${String(varsObj[code])}`);
    return ['Nama,Nilai'].concat(rows).join("\n") + "\n";
  }

  function tsCompact() {
    const d = new Date();
    const pad = (n)=> String(n).padStart(2,'0');
    return `${d.getFullYear()}${pad(d.getMonth()+1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}`;
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
      const payload = { _format: 'vp-vars-v2', variables, labels: varLabels };
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
      const csv = csvFromVars(variables, varLabels);
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
        .sort((a,b)=>(varLabels[a]||a).localeCompare(varLabels[b]||b,'id'))
        .map(code => ({ Nama: (varLabels[code]||code), Nilai: variables[code] }));
      const ws = XLSX.utils.json_to_sheet(rows, { header: ['Nama','Nilai'] });
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Parameter');
      const ts = tsCompact();
      XLSX.writeFile(wb, `parameter_${projectId}_${ts}.xlsx`);
      TOAST.ok('Parameter diekspor (XLSX).');
    } catch { TOAST.err('Gagal export XLSX.'); }
  }

  async function copyJSONToClipboard() {
    try {
      const payload = { _format: 'vp-vars-v2', variables, labels: varLabels };
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
    const onDoc = (e) => { if (!menu.contains(e.target) && e.target!==anchorBtn) close(); };
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
    let srcVars = {}, srcLabels = {};
    if (obj && typeof obj === 'object' && obj._format === 'vp-vars-v2') {
      srcVars = (obj.variables && typeof obj.variables === 'object') ? obj.variables : {};
      srcLabels = (obj.labels && typeof obj.labels === 'object') ? obj.labels : {};
    } else if (obj && typeof obj === 'object') {
      Object.keys(obj).forEach(code => {
        srcVars[code] = obj[code];
        srcLabels[code] = code;
      });
    } else throw new Error('format');
    const errors = [];
    const outVars = {}, outLabels = {};
    Object.keys(srcVars).forEach(code => {
      let safe = String(code || '').trim();
      safe = safe.normalize('NFKD').replace(/[^\w]/g,'_').replace(/_+/g,'_').replace(/^_+|_+$/g,'');
      if (/^[0-9]/.test(safe)) safe = '_' + safe;
      if (!safe) return;
      const val = parseNumberOrEmpty(srcVars[code]);
      if (val === '') { errors.push(`Kode ${code}: Nilai tidak valid`); return; }
      outVars[safe] = roundHalfUp(Number(val), STORE_PLACES);
      const lbl = String((srcLabels && srcLabels[code]) || code || '').trim();
      outLabels[safe] = lbl || safe;
    });
    return { vars: outVars, labels: outLabels, errors };
  }

  function parseCSVToVarsLabels(rawText) {
    const rowsCsv = parseCSV(rawText);
    if (!rowsCsv.length) throw new Error('csv-empty');
    const errors = [];
    const nextVars = {}, nextLabels = {};
    rowsCsv.forEach((r, idx) => {
      const label = String(r.label || '').trim();
      const n = parseNumberOrEmpty(r.value);
      if (!label) { errors.push(`Baris ${idx+1}: Label kosong`); return; }
      if (n === '') { errors.push(`Baris ${idx+1}: Nilai bukan angka`); return; }
      let code = slugifyName(label);
      if (!code) { errors.push(`Baris ${idx+1}: Kode tidak valid`); return; }
      if (nextVars[code] != null || variables[code] != null) {
        let i = 2;
        while (nextVars[code] != null || variables[code] != null) code = `${slugifyName(label)}_${i++}`;
      }
      nextVars[code] = roundHalfUp(Number(n), STORE_PLACES);
      nextLabels[code] = label;
    });
    if (!Object.keys(nextVars).length) throw new Error('csv-none');
    return { vars: nextVars, labels: nextLabels, errors };
  }

  async function parseXLSXToVarsLabels(file) {
    if (!(window.XLSX && XLSX.read)) throw new Error('no-xlsx-lib');
    const ab = await file.arrayBuffer();
    const wb = XLSX.read(ab);
    const ws = wb.Sheets[wb.SheetNames[0]];
    const arr = XLSX.utils.sheet_to_json(ws, { header: 1 }); // 2D array
    const rows = arr.filter(r => r && (r[0] != null || r[1] != null));
    const body = (rows[0] && /nama|label/i.test(String(rows[0][0])) && /nilai|value/i.test(String(rows[0][1]||"")))
      ? rows.slice(1) : rows;
    const errors = [];
    const nextVars = {}, nextLabels = {};
    body.forEach((r, idx) => {
      const label = String((r[0] ?? '')).trim();
      const n = parseNumberOrEmpty(r[1]);
      if (!label) { errors.push(`Baris ${idx+1}: Label kosong`); return; }
      if (n === '') { errors.push(`Baris ${idx+1}: Nilai bukan angka`); return; }
      let code = slugifyName(label);
      if (nextVars[code] != null || variables[code] != null) {
        let i = 2; while (nextVars[code] != null || variables[code] != null) code = `${slugifyName(label)}_${i++}`;
      }
      nextVars[code] = roundHalfUp(Number(n), STORE_PLACES);
      nextLabels[code] = label;
    });
    if (!Object.keys(nextVars).length) throw new Error('xlsx-none');
    return { vars: nextVars, labels: nextLabels, errors };
  }

  async function handleUnifiedImport(file) {
    if (!file) return;
    const name = file.name || '';
    const ext = (/\.(\w+)$/.exec(name)?.[1] || '').toLowerCase();
    try {
      let parsed = { vars:{}, labels:{}, errors:[] };
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
        alert('Beberapa baris diabaikan:\n' + parsed.errors.slice(0,10).join('\n') + (parsed.errors.length>10?'\n…':'') );
      }
      const nextVars = parsed.vars, nextLabels = parsed.labels;
      const existingCodes = new Set(Object.keys(variables));
      const codes = Object.keys(nextVars);
      const adds = codes.filter(c => !existingCodes.has(c)).length;
      const updates = codes.filter(c => existingCodes.has(c)).length;
      const summary = `Ditemukan ${codes.length} parameter.\nTambah: ${adds}\nPerbarui: ${updates}.\nOK = Merge, Cancel = Replace`;
      const doMerge = window.confirm(summary);
      if (doMerge) {
        variables = { ...variables, ...nextVars };
        varLabels = { ...varLabels, ...nextLabels };
      } else {
        variables = { ...nextVars };
        varLabels = { ...nextLabels };
      }
      saveVars(); saveVarLabels(); renderVarTable(); reevaluateAllFormulas();
      TOAST.ok('Parameter diimport.');
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

  // Hook tombol Import/Export lama → Unified
  (function installUnifiedIO(){
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
  (function installTemplateGen(){
    const btn = document.getElementById('vp-template-xlsx-gen');
    if (!btn) return;
    btn.addEventListener('click', () => {
      if (!(window.XLSX && XLSX.utils && XLSX.writeFile)) { TOAST.warn('Butuh SheetJS untuk XLSX'); return; }
      const rows = [
        { Nama: 'Panjang', Nilai: 0 },
        { Nama: 'Lebar',   Nilai: 0 },
        { Nama: 'Tinggi',  Nilai: 0 },
      ];
      const ws = XLSX.utils.json_to_sheet(rows, { header: ['Nama','Nilai'] });
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
              <button type="button" class="btn btn-link btn-sm vp-toggle" data-type="sub" data-key="${escapeHtml(sKey)}" aria-expanded="${!(collapsed.sub[sKey]||collapsed.klas[kKey])}">
                <i class="bi ${(collapsed.sub[sKey]||collapsed.klas[kKey]) ? 'bi-caret-right-fill' : 'bi-caret-down-fill'}"></i>
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
                  <button type="button" class="btn btn-outline-secondary btn-sm fx-toggle"
                          title="Mode formula: awali dengan '=' atau tekan Ctrl+Space"
                          aria-pressed="false">fx</button>
                  <div class="flex-grow-1">
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
      try {
        const vlist = await HTTP.jget(`/detail_project/api/project/${projectId}/volume-pekerjaan/list/`);
        if (vlist && Array.isArray(vlist.items)) {
          vlist.items.forEach(it => {
            const id = Number(it.pekerjaan_id);
            const v  = N ? Number(N.canonicalizeForAPI(it.quantity ?? '0'))
                         : Number(String(it.quantity || '0').replace(',', '.'));
            if (Number.isFinite(id) && Number.isFinite(v)) volMap[id] = v;
          });
        }
      } catch {}
      if (Object.keys(volMap).length === 0) {
        const rekap = await HTTP.jget(`/detail_project/api/project/${projectId}/rekap/`).catch(()=> ({}));
        if (rekap && Array.isArray(rekap.rows)) {
          rekap.rows.forEach(r => {
            if (r && typeof r.pekerjaan_id === 'number') {
              const v = N ? Number(N.canonicalizeForAPI(r.volume ?? 0))
                          : Number(r.volume || 0);
              volMap[r.pekerjaan_id] = Number.isFinite(v) ? v : 0;
            }
          });
        }
      }
      // 2) Pastikan baris ada: pakai SSR jika tersedia; jika tidak → fallback ke EP_TREE
      if (!document.querySelector('tr[data-pekerjaan-id]')) {
        await enhanceWithGroups();
      }
      rows = Array.from(document.querySelectorAll('tr[data-pekerjaan-id]'));
      rows.forEach(tr => bindRow(tr));


      // 3) Ambil formula state dari server; kalau error → pakai localStorage
      let serverFormula = null;
      try {
        const resp = await HTTP.jget(EP_FORMULA_STATE);
        if (resp && resp.ok && Array.isArray(resp.items)) {
          serverFormula = {};
          resp.items.forEach(it => {
            serverFormula[it.pekerjaan_id] = { raw: it.raw || '', fx: !!it.is_fx };
          });
        }
      } catch {}
      const localFormula = loadFormulas();
      const formulaState = serverFormula || localFormula;

      // 4) Render nilai & formula preview
      rows.forEach(tr => {
        const id = parseInt(tr.dataset.pekerjaanId, 10);
        const input = tr.querySelector('.qty-input');
        const preview = tr.querySelector('.fx-preview');
        const fxBtn = tr.querySelector('.fx-toggle');
        const base = Number(volMap[id] || 0);

        originalValueById[id] = roundHalfUp(base, STORE_PLACES);
        currentValueById[id] = originalValueById[id];

        input.value = base ? formatIdSmart(base) : '';
        input.classList.toggle('vp-empty', !input.value.trim());
        // Sync row markers for numeric (non-formula) rows after prefill
        tr.classList.toggle('vp-row-empty', !input.value.trim());
        tr.classList.toggle('vp-row-zero', (!!input.value.trim() && Number(base) === 0));
        tr.classList.remove('vp-row-invalid');

        const f = formulaState[id];
        if (f && typeof f.raw === 'string' && f.raw.trim()) {
          input.value = f.raw;
          fxModeById[id] = !!f.fx;
          if (fxBtn) {
            fxBtn.setAttribute('aria-pressed', String(fxModeById[id]));
            fxBtn.classList.toggle('active', fxModeById[id]);
          }
          handleInputChange(id, input, preview, false);
        }
        setRowDirtyVisual(id, false);
      });

      setBtnSaveEnabled();
      buildSearchIndex();
     // Terapkan state collapse untuk kedua mode (row/card)
     applyCollapseOnTable();
     applyCollapseOnCards();
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

    const changes = postingIds.map(id => ({
      id,
      before: Number(originalValueById[id] ?? 0),
      after: Number(currentValueById[id] ?? 0)
    }));

    const items = changes.map(({id, after}) => {
      let q = after;
      if (!Number.isFinite(q)) q = 0;
      const rounded = roundHalfUp(q, STORE_PLACES);
      return { pekerjaan_id: id, quantity: rounded };
    });

    saving = true;
    if (reason === 'manual' && btnSaveSpin) btnSaveSpin.hidden = false;
    if (reason === 'manual') {
      if (btnSave) btnSave.disabled = true;
      if (btnSaveTop) btnSaveTop.disabled = true;
    }

    try {
      const res = await HTTP.jpost(EP_SAVE, { items });
      
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

      const json = res?.data || {};
      if (!res.ok) {
        markErrors(json);
        const saved = (typeof json.saved === 'number') ? json.saved : 0;
        TOAST.err(`Sebagian/semua gagal disimpan. Tersimpan: ${saved}`);
        setSaveStatus(`Sebagian/semua gagal disimpan. Tersimpan: ${saved}`,'danger');
        return;
      }

      // OK — commit baseline & visuals
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
          // Clear invalid/empty and saved pulse; zero is allowed
          tr.classList.remove('vp-row-invalid', 'vp-row-empty', 'vp-row-zero');
          markRowSaved(tr);
        }
        dirtySet.delete(id);
        setRowDirtyVisual(id, false);
      });
      setBtnSaveEnabled();
      resolveVolumeJobs(postingIds);

      const realChanges = changes.filter(c => roundHalfUp(c.before, STORE_PLACES) !== roundHalfUp(c.after, STORE_PLACES));
      setSaveStatus(`Tersimpan ${realChanges.length} item.`, 'success');
      if (realChanges.length) {
        undoStack.push({ ts: Date.now(), changes: realChanges });
        if (undoStack.length > UNDO_MAX) undoStack.shift();
        TOAST.action(`Tersimpan ${realChanges.length} item.`, [
          { label: 'Undo', class: 'btn-warning', onClick: tryUndoLast }
        ]);
      } else if (reason === 'manual') {
        TOAST.warn('Tidak ada perubahan.');
        setSaveStatus('Tidak ada perubahan.', 'warning');
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
        input.classList.toggle('vp-empty', !String(input.value||'').trim());
      }
      if (preview) preview.textContent = '';
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


  // ==== Init: load variables, render table, bind baris existing (SSR)
  loadVars();
  loadVarLabels();
  Object.keys(variables).forEach(code => { if (!varLabels[code]) varLabels[code] = code; });
  saveVarLabels();
  renderVarTable();

  // Bind baris yang sudah dirender server agar fitur aktif sebelum tree di-load
  rows.forEach(tr => bindRow(tr));

  // ===== EXPORT INITIALIZATION =====
  // Initialize unified export (CSV/PDF/Word) via ExportManager
  function initExportButtons() {
    if (typeof ExportManager === 'undefined') {
      console.warn('[Volume] ⚠️ ExportManager not loaded - export buttons disabled');
      return;
    }

    try {
      const exporter = new ExportManager(projectId, 'volume-pekerjaan');

      // Helper function to get current parameters from localStorage
      function getExportParameters() {
        try {
          const raw = localStorage.getItem(storageKeyVars());
          const params = raw ? JSON.parse(raw) : {};
          if (typeof params !== 'object' || !params) return {};
          console.log('[Volume] Loaded parameters for export:', params);
          return params;
        } catch (err) {
          console.warn('[Volume] Failed to load parameters:', err);
          return {};
        }
      }

      const btnCSV = document.getElementById('btn-export-csv');
      const btnPDF = document.getElementById('btn-export-pdf');
      const btnWord = document.getElementById('btn-export-word');

      if (btnCSV) {
        btnCSV.addEventListener('click', async (e) => {
          e.preventDefault();
          console.log('[Volume] 📥 CSV export requested');
          await exporter.exportAs('csv', { parameters: getExportParameters() });
        });
      }

      if (btnPDF) {
        btnPDF.addEventListener('click', async (e) => {
          e.preventDefault();
          console.log('[Volume] 📄 PDF export requested');
          await exporter.exportAs('pdf', { parameters: getExportParameters() });
        });
      }

      if (btnWord) {
        btnWord.addEventListener('click', async (e) => {
          e.preventDefault();
          console.log('[Volume] 📝 Word export requested');
          await exporter.exportAs('word', { parameters: getExportParameters() });
        });
      }

      console.log('[Volume] ✓ Export buttons initialized');
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

})();
