// /static/detail_project/js/list_pekerjaan.js
/* =====================================================================
   List Pekerjaan — JS (Drop-in Replace, v2 → feel v1)
   Target: Batch 2, tapi memaksa layout & workflow mirip Batch 1 (legacy)
   - Otomatis "migrasi" layout bila template masih punya tabel global #lp-table:
     * Buat <div id="klas-list" class="vstack gap-3"> setelah tabel
     * Sembunyikan wrapper tabel global → kartu per Klas/Sub tampil seperti v1
   - Kompatibel: jQuery 3.7, Select2 4.1, Bootstrap 5
   - Sidebar: Overlay (aktif), Hover-Edge kanan (desktop), fokus/shortcuts aman
   - Payload & kontrak API: TANPA perubahan (SSOT)

   Catatan: Bila di kemudian hari kamu sudah menghapus tabel global dari template
   (mengikuti rekomendasi), bagian migrasi layout akan otomatis no-op.
   ===================================================================== */

(function () {
  // ========= [UTILITIES] Logging & Guards ====================================
  const __DEBUG__ = false; // set true untuk log/diagnostic

  const log  = (...a) => __DEBUG__ && console.debug('[LP]', ...a);
  const warn = (...a) => __DEBUG__ && console.warn('[LP]', ...a);
  const err  = (...a) => console.error('[LP]', ...a); // error tetap tampil

  // jQuery alias (boleh null jika belum ter-load saat eval; cek dilakukan runtime)
  const $ = window.jQuery || window.$;
  const HAS_JQ = !!$;
  const HAS_S2 = !!($ && $.fn && $.fn.select2);

  // Global error diagnostics (tidak mengubah flow normal)
  window.addEventListener('error', (e) => {
    err('GlobalError:', e.message, 'at', e.filename + ':' + e.lineno + ':' + e.colno, e.error);
  });
  window.addEventListener('unhandledrejection', (e) => {
    err('UnhandledPromise:', e.reason);
  });

  // ========= [CORE SHORTCUTS] jfetch & toast =================================
  const jfetch = (window.DP && DP.core && DP.core.http && DP.core.http.jfetch)
    ? DP.core.http.jfetch
    : async function(url, opts = {}) {
        const res  = await fetch(url, { credentials: 'same-origin', ...opts });
        const ok   = res.ok;
        const ctyp = res.headers.get('content-type') || '';
        const body = ctyp.includes('application/json') ? await res.json() : await res.text();
        if (!ok) {
          const e = new Error('HTTP ' + res.status);
          e.status = res.status; e.body = body;
          throw e;
        }
        return body;
      };

  const tShow = (window.DP && DP.core && DP.core.toast && DP.core.toast.show)
    ? DP.core.toast.show
    : (msg)=>alert(msg);

  // ========= [DOM REFS] Sidebar & Area Utama =================================
  const edgeSidebar    = document.getElementById('lpSidebar'); // (hover-edge) — nonaktif khusus halaman
  const overlaySidebar = document.getElementById('lp-sidebar'); // Overlay (aktif)
  const overlayPanel   = overlaySidebar?.querySelector('.lp-sidebar-inner');
  const rightHotspot   = document.querySelector('.lp-overlay-hotspot'); // hotspot kanan (baru)
  const HOVER_AUTO_CLOSE = (overlaySidebar?.dataset.hoverclose ?? '1') !== '0';
  let overlayOpenMode = null; // 'hover' | 'manual' | null
  const mainArea = document.querySelector('.lp-main'); // untuk ARIA hide saat overlay terbuka

  // ========= [DOM REFS] Root & Anchors =======================================
  const root = document.getElementById('lp-app');

  // --- [LEGACY FEEL MIGRATION] -----------------------------------------------
  // Batch 2 template menaruh #klas-list di <tbody> dalam #lp-table.
  // Agar mirip Batch 1, kita buat DIV container baru dan sembunyikan tabel global.
  function ensureLegacyLayoutContainer() {
    // Cari elemen-elemen potensial
    const tableWrap = document.querySelector('.lp-table-wrap');
    const table     = document.getElementById('lp-table');
    let   klasList  = document.getElementById('klas-list');

    // Jika #klas-list sudah berupa DIV card container → tidak perlu migrasi
    if (klasList && klasList.tagName !== 'TBODY') {
      return klasList;
    }

    // Jika tidak ada tabel global → kemungkinan template sudah legacy-friendly
    if (!table || !tableWrap) {
      // pastikan #klas-list ada, kalau tidak buat
      if (!klasList) {
        klasList = document.createElement('div');
        klasList.id = 'klas-list';
        klasList.className = 'vstack gap-3';
        (mainArea || document.body).appendChild(klasList);
      } else if (klasList.tagName === 'TBODY') {
        // konversi tbody → div
        const newDiv = document.createElement('div');
        newDiv.id = 'klas-list';
        newDiv.className = 'vstack gap-3';
        klasList.replaceWith(newDiv);
        klasList = newDiv;
      }
      return klasList;
    }

    // Ada tabel global dan #klas-list berada di TBODY → migrasikan
    const newDiv = document.createElement('div');
    newDiv.id = 'klas-list';
    newDiv.className = 'vstack gap-3';

    // Sisipkan setelah wrapper tabel agar tata letak tidak lompat
    tableWrap.insertAdjacentElement('afterend', newDiv);

    // Sembunyikan wrapper tabel global (feel seperti v1)
    tableWrap.style.display = 'none';

    // Kembalikan container baru
    return newDiv;
  }

  // Buat/ambil container list yang benar (DIV seperti v1)
  let klasWrap = ensureLegacyLayoutContainer();

  // Tombol (kanonik + alias class)
  const btnAddKlasAll    = Array.from(document.querySelectorAll('#btn-add-klas, .js-add-klas'));
  const btnSaveAll       = Array.from(document.querySelectorAll('#btn-save, .js-save'));
  const btnCompactAll    = Array.from(document.querySelectorAll('#btn-compact, .js-compact'));
  const btnSidebarTogAll = Array.from(document.querySelectorAll('#btn-sidebar-toggle, .js-sidebar-toggle, .btn-sidebar-toggle'));

  // Sidebar Nav anchors
  const navWrap           = document.getElementById('lp-nav');
  const navSearchSide     = document.getElementById('lp-nav-search-side');
  const navSearchToolbar  = document.getElementById('lp-nav-search');
  const navAnnounce       = document.getElementById('lp-nav-announce');
  const tbAnnounce        = document.getElementById('lp-toolbar-announce');
  const btnExpandAllAll   = Array.from(document.querySelectorAll('.lp-nav-expand-all, #lp-nav-expand-all'));
  const btnCollapseAllAll = Array.from(document.querySelectorAll('.lp-nav-collapse-all, #lp-nav-collapse-all'));

  // ========= [A11Y] Live region ==============================================
  let live = document.getElementById('lp-live');
  if (!live) {
    live = document.createElement('div');
    live.id = 'lp-live';
    live.setAttribute('aria-live', 'polite');
    live.setAttribute('aria-atomic', 'true');
    live.className = 'visually-hidden';
    document.body.appendChild(live);
  }
  const say = (t) => { live.textContent = t; };

  // ========= [DIAGNOSTICS] Cek Anchor Wajib ==================================
  const REQUIRED = [
    ['#lp-app', !!root],
    ['#klas-list (DIV legacy)', !!klasWrap && klasWrap.tagName !== 'TBODY'],
    ['#btn-add-klas', btnAddKlasAll.length > 0],
    ['#btn-save', btnSaveAll.length > 0],
    ['#btn-compact', btnCompactAll.length > 0],
    ['#lp-nav', !!navWrap],
    ['#lp-nav-search-side', !!navSearchSide],
    ['.lp-nav-expand-all/#lp-nav-expand-all', btnExpandAllAll.length > 0],
    ['.lp-nav-collapse-all/#lp-nav-collapse-all', btnCollapseAllAll.length > 0],
  ];
  function injectDiagBanner(missingKeys) {
    if (!root) return;
    const id = 'lp-diag-banner';
    if (document.getElementById(id)) return;
    const box = document.createElement('div');
    box.id = id;
    box.style.cssText = 'position:sticky;top:64px;z-index:2000;margin:12px;padding:10px 12px;border-radius:8px;background:#fff3cd;border:1px solid #ffec99;color:#664d03;font:14px/1.4 system-ui;';
    box.innerHTML = `<b>LP Diagnostic:</b> Anchor wajib belum lengkap: <code>${missingKeys.join(', ')}</code>. Fitur terkait dinonaktifkan supaya tidak crash.`;
    root.prepend(box);
  }
  const missing = REQUIRED.filter(([k, ok]) => !ok).map(([k]) => k);
  if (missing.length) {
    warn('Missing required anchors:', missing);
    injectDiagBanner(missing);
  } else {
    log('All required anchors OK');
  }

  // ========= [SIDEBAR-EDGE (STUB)] Dinonaktifkan di halaman ini ==============
  function openEdge() {}
  function closeEdge() {}
  function isEdgeOpen(){ return false; }

  // ========= [HOVER-EDGE KANAN] untuk Overlay lokal (desktop) =================
  function setupRightHoverEdge(){
    if (!rightHotspot || !overlaySidebar) return;
    const isDesktop = () => window.matchMedia('(min-width: 992px)').matches;
    const panel = overlayPanel || overlaySidebar;   // penting: pakai panel, bukan aside
    let tIn = null, tOut = null;
    const ENTER_DELAY = 10, LEAVE_DELAY = 120;

    rightHotspot.addEventListener('mouseenter', () => {
      if (!isDesktop()) return;
      clearTimeout(tOut);
      tIn = setTimeout(() => setOverlayVisible(true, {autofocus:false, mode:'hover'}), ENTER_DELAY);
    }, { passive:true });

    rightHotspot.addEventListener('mouseleave', () => {
      if (!isDesktop()) return;
      clearTimeout(tIn);
      if (HOVER_AUTO_CLOSE && overlayOpenMode === 'hover' && !panel.matches(':hover')) {
        tOut = setTimeout(() => setOverlayVisible(false), LEAVE_DELAY);
      }
    }, { passive:true });

    panel.addEventListener('mouseenter', () => { clearTimeout(tOut); }, { passive:true });

    panel.addEventListener('mouseleave', () => {
      if (!isDesktop()) return;
      if (HOVER_AUTO_CLOSE && overlayOpenMode === 'hover' && !rightHotspot.matches(':hover')) {
        tOut = setTimeout(() => setOverlayVisible(false), LEAVE_DELAY);
      }
    }, { passive:true });
  }
  try { setupRightHoverEdge(); } catch(_){}

  // ========= [OVERLAY SIDEBAR] Open/Close & Focus Trap =======================
  let lastFocusBeforeOpen = null;

  // [TDZ-SAFE] Predeclare suggest boxes agar aman ketika overlay ditutup cepat
  let sideSuggest = null;
  let tbSuggest   = null;

  function setOverlayVisible(show, opts = {}){
    const { autofocus = true, mode = null } = opts;
    if (!overlaySidebar) return;

    overlaySidebar.classList.toggle('show', show);
    overlaySidebar.classList.toggle('is-open', show);
    document.body.classList.toggle('lp-overlay-open', show);
    btnSidebarTogAll.forEach(btn => btn.setAttribute('aria-expanded', String(show)));

    // Sinkronkan trigger standar (data-toggle="side-right")
    document.querySelectorAll('[data-toggle="side-right"][aria-controls="lp-sidebar"]')
      .forEach(el => el.setAttribute('aria-expanded', String(show)));
    document.querySelectorAll('[data-open="lp-sidebar"]').forEach(el => {
      el.setAttribute('aria-expanded', String(show));
    });

    // ARIA sync & announce
    overlaySidebar.setAttribute('aria-hidden', show ? 'false' : 'true');
    if (mainArea) {
      if (show) mainArea.setAttribute('aria-hidden','true');
      else mainArea.removeAttribute('aria-hidden');
    }
    try {
      document.dispatchEvent(new CustomEvent('lp:overlay:change', { detail: { open: !!show } }));
    } catch(_){}

    if (show) {
      overlayOpenMode = mode || overlayOpenMode || 'manual';
      lastFocusBeforeOpen = document.activeElement;
      if (autofocus) requestAnimationFrame(()=> navSearchSide?.focus());
      startFocusTrap();
      try { localStorage.setItem('lp_sidebar_open', '1'); } catch {}
    } else {
      overlayOpenMode = null;
      stopFocusTrap();
      if (navSearchSide) { navSearchSide.value = ''; }
      if (sideSuggest) { hideSuggestions(sideSuggest); } // TDZ-safe
      try { localStorage.setItem('lp_sidebar_open', '0'); } catch {}
      if (lastFocusBeforeOpen && document.contains(lastFocusBeforeOpen)) lastFocusBeforeOpen.focus();
      else btnSidebarTogAll[0]?.focus();
    }
  }

  function isOverlayOpen(){
    return !!(overlaySidebar &&
      (overlaySidebar.classList.contains('show') || overlaySidebar.classList.contains('is-open')));
  }

  (function restoreOverlayState(){
    if (!overlaySidebar) return;
    try {
      const pref = localStorage.getItem('lp_sidebar_open');
      if (pref === '1') setOverlayVisible(true);
    } catch {}
  })();

  btnSidebarTogAll.forEach(btn=>{
    btn.addEventListener('click', (e)=>{
      e.preventDefault();
      if (isOverlayOpen()) setOverlayVisible(false);
      else setOverlayVisible(true, { mode: 'manual' });
    });
  });

  // Delegasi global: tombol apapun yang punya data-open="lp-sidebar"
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-open="lp-sidebar"]');
    if (!t) return;
    e.preventDefault();
    setOverlayVisible(!isOverlayOpen(), { mode: 'manual' });
  }, false);

  // Shortcuts umum (ESC, '/'), dengan pengecualian untuk Select2
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && window.jQuery && jQuery(e.target).closest('.select2-container').length) {
      return; // biarkan Select2 handle ESC saat dropdown aktif
    }
    if (e.key === '/' && isOverlayOpen()) {
      const t = e.target;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
      e.preventDefault();
      navSearchSide?.focus();
      return;
    }
    if (e.key === 'Escape' && isOverlayOpen()) {
      setOverlayVisible(false);
    }
  });

  // Menelan shortcut app-level saat Select2 fokus/terbuka
  document.addEventListener('keydown', (e) => {
    const $jq = window.jQuery;
    if ($jq && $jq(e.target).closest('.select2-dropdown, .select2-container--open').length) {
      const key = e.key.toLowerCase();
      const meta = e.ctrlKey || e.metaKey;
      if (key === '/' || (meta && (key === 'f' || key === 's'))) {
        e.stopImmediatePropagation();
      }
    }
  }, true);

  // Klik backdrop overlay menutup panel
  overlaySidebar?.addEventListener('click', (e) => {
    const panel = overlaySidebar.querySelector('.lp-sidebar-inner');
    if (!panel) return;
    if (!panel.contains(e.target)) setOverlayVisible(false);
  });
  overlaySidebar?.querySelector('[data-action="close-sidebar"]')
    ?.addEventListener('click', () => setOverlayVisible(false));

  // ========= [FOCUS TRAP] ====================================================
  let trapKeydown = null;
  function getFocusable(container) {
    return Array.from(container.querySelectorAll(
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
    )).filter(el => {
      const cs = window.getComputedStyle(el);
      return cs.visibility !== 'hidden' && cs.display !== 'none';
    });
  }
  function startFocusTrap(){
    if (!overlaySidebar) return;
    const cont = overlaySidebar;
    trapKeydown = (e)=>{
      if (!isOverlayOpen()) return;
      if (e.key !== 'Tab') return;
      const focusables = getFocusable(cont);
      if (!focusables.length) return;
      const first = focusables[0], last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', trapKeydown, true);
  }
  function stopFocusTrap(){
    if (trapKeydown) document.removeEventListener('keydown', trapKeydown, true);
    trapKeydown = null;
  }

  // ========= [APP GUARDS] Root & Project Id ==================================
  if (!root || !klasWrap) {
    err('Abort: #lp-app atau #klas-list tidak ditemukan.');
    return;
  }
  const projectId = root.dataset.projectId;
  const REF_YEAR  = root.dataset.refYear || null;

  // ========= [HELPERS] Umum ===================================================
  const uid = () => Math.random().toString(36).slice(2, 9);
  function renum(tbody) {
    if (!tbody) return;
    Array.from(tbody.children).forEach((tr, i) => {
      const first = tr.firstElementChild;
      if (first) first.textContent = i + 1;
    });
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, m => ({'&': '&amp;','<': '&lt;','>': '&gt;','"': '&quot;',"'": '&#39;'}[m]));
  }
  function truncateText(str, n = 100) {
    const arr = Array.from(String(str || ""));
    return arr.length > n ? arr.slice(0, n).join('') + '…' : String(str || "");
  }
  function buildSourceLabel(src) {
    if (src === 'ref')          return REF_YEAR ? `Ref AHSP ${REF_YEAR}` : 'Ref';
    if (src === 'ref_modified') return REF_YEAR ? `AHSP ${REF_YEAR} (modified)` : 'Ref (modified)';
    return 'Kustom';
  }

  // Mapper aman untuk berbagai format respons API → {id, text}
  function mapToSelect2Results(input){
    try{
      if (!input) return [];
      if (Array.isArray(input)) {
        return input.map(it => ({
          id:  String(it.id   ?? it.value ?? it.kode_ahsp ?? it.kode ?? it.uid ?? ''),
          text:String(it.text ?? it.label ?? it.nama_ahsp ?? it.nama ?? it.name ?? it.uraian ?? '')
        })).filter(x => x.id && x.text);
      }
      if (Array.isArray(input.results)) return input.results;
      if (Array.isArray(input.items)) {
        return input.items.map(it => ({
          id:  String(it.id   ?? it.value ?? it.kode_ahsp ?? it.kode ?? it.uid ?? ''),
          text:String(it.text ?? it.label ?? it.nama_ahsp ?? it.nama ?? it.name ?? it.uraian ?? '')
        })).filter(x => x.id && x.text);
      }
      const src = Array.isArray(input.data) ? input.data : Object.values(input);
      if (Array.isArray(src) && src.length && typeof src[0] === 'object') {
        return src.map(it => ({
          id:  String(it.id   ?? it.pk ?? it.value ?? it.kode_ahsp ?? it.kode ?? it.uid ?? ''),
          text:String(it.text ?? it.label
                 ?? (it.kode_ahsp && it.nama_ahsp
                      ? `${it.kode_ahsp} — ${it.nama_ahsp}`
                      : (it.nama_ahsp ?? it.nama ?? it.name ?? it.uraian ?? '')))
        })).filter(x => x.id && x.text);
      }
      return [];
    }catch(_){ return []; }
  }

  function escRe(s){ return String(s).replace(/[.*+?^${}()|[\]\\]/g,'\\$&'); }
  function highlightLabel(raw, kw){
    if (!kw) return escapeHtml(raw);
    const re = new RegExp(`(${escRe(kw)})`, 'ig');
    return escapeHtml(raw).replace(re, '<span class="lp-hit">$1</span>');
  }

  // ========= [URAIAN] Preview 2-baris & Edit =================================
  function autoResize(ta){ if(!ta) return; ta.style.height='auto'; ta.style.height = Math.max(ta.scrollHeight, ta.offsetHeight) + 'px'; }
  function syncPreview(td){
    const ta = td?.querySelector('.uraian');
    const pv = td?.querySelector('.lp-urai-preview');
    if (!ta || !pv) return;
    pv.textContent = (ta.value || '').replace(/\s+$/g,'');
  }
  function enterEdit(td){
    if (!td) return;
    td.classList.add('is-editing');
    const ta = td.querySelector('.uraian');
    if (!ta) return;
    requestAnimationFrame(()=>{
      ta.focus();
      try{ const n = ta.value?.length || 0; ta.setSelectionRange(n,n); }catch{}
      autoResize(ta);
    });
  }
  function applyUraianGate(td){
    const tr  = td.closest('tr'); if (!tr) return;
    const src = tr.dataset.sourceType || '';
    const ta  = td.querySelector('.uraian');
    const pv  = td.querySelector('.lp-urai-preview');
    if (!ta || !pv) return;

    const editable = (src === 'custom' || src === 'ref_modified');
    ta.readOnly = !editable;
    ta.tabIndex = editable ? 0 : -1;
    pv.style.cursor = editable ? 'text' : 'default';
  }
  function setupUraianInteractivity(scope = document){
    // dukung selector lama (td.col-urai) dan baru
    scope.querySelectorAll('td.col-urai, #lp-table tbody td:nth-child(4)').forEach((td)=>{
      const ta = td.querySelector('.uraian');
      let pv = td.querySelector('.lp-urai-preview');
      if (!ta) return;
      if (!pv) { pv = document.createElement('div'); pv.className = 'lp-urai-preview'; td.prepend(pv); }
      syncPreview(td); autoResize(ta); applyUraianGate(td);
      pv.onclick = ()=> enterEdit(td);
      ta.addEventListener('input', ()=>{ autoResize(ta); syncPreview(td); });
      ta.addEventListener('focus', ()=> td.classList.add('is-editing'));
      ta.addEventListener('blur',  ()=> { td.classList.remove('is-editing'); syncPreview(td); });
    });
  }
  document.addEventListener('DOMContentLoaded', ()=>{
    setupUraianInteractivity(document);
    try { setupRightHoverEdge(); } catch(_){}
  });

  // ========= [BUILDERS] Klas / Sub / Row =====================================
  let kCounter = 0;

  function newKlas(prefillName = null) {
    kCounter++;
    const id = `k_${Date.now()}_${uid()}`;
    const div = document.createElement('div');
    div.className = 'card shadow-sm';
    div.id = id;
    div.dataset.anchorId = id;

    div.innerHTML = `
      <div class="card-header d-flex gap-2 align-items-center">
        <input class="form-control klas-name" placeholder="Nama Klasifikasi (auto: Klasifikasi ${kCounter})" value="${prefillName ? escapeHtml(prefillName) : ''}">
        <button class="btn btn-primary btn-add-sub lp-btn lp-btn-wide" type="button">
          <i class="bi bi-plus-circle"></i> Sub-Klasifikasi
        </button>
        <button class="btn btn-outline-danger btn-del lp-btn" type="button">Hapus</button>
      </div>
      <div class="card-body vstack gap-2 sub-wrap"></div>`;

    div.dataset.tempId = `k${kCounter}_${Date.now()}`;
    const subWrap = div.querySelector('.sub-wrap');
    div.querySelector('.btn-add-sub').onclick = () => { addSub(subWrap); scheduleSidebarRebuild(); };
    div.querySelector('.btn-del').onclick     = () => { div.remove(); scheduleSidebarRebuild(); };
    div.querySelector('.klas-name').addEventListener('input', scheduleSidebarRebuild);

    klasWrap.appendChild(div);
    requestAnimationFrame(()=>{
      div.scrollIntoView({ behavior:'smooth', block:'start' });
      div.classList.add('lp-flash');
      const inp = div.querySelector('.klas-name'); inp?.focus();
      say('Klasifikasi ditambahkan'); tbAnnounce && (tbAnnounce.textContent = 'Klasifikasi ditambahkan');
    });
    lastKlasTarget = div;
    scheduleSidebarRebuild();
    return div;
  }

  function addSub(container, options = {}) {
    const { name = null } = options;
    const id = `s_${Date.now()}_${uid()}`;
    const block = document.createElement('div');
    block.className = 'border rounded p-2';
    block.id = id;
    block.dataset.anchorId = id;

    block.innerHTML = `
    <div class="d-flex gap-2 align-items-center mb-2">
      <input class="form-control sub-name" placeholder="Nama Sub-Klasifikasi (mis. 1.1)" value="${name ? escapeHtml(name) : ''}">
      <button class="btn btn-primary btn-add-pekerjaan lp-btn lp-btn-wide" type="button">
        <i class="bi bi-plus-circle"></i> Pekerjaan
      </button>
      <button class="btn btn-outline-danger btn-del" type="button">Hapus</button>
    </div>
    <table class="table mb-0 list-pekerjaan lp-table">
      <!-- SSOT: kolom & rasio pakai colgroup; CSS memberi width via var -->
      <colgroup>
        <col class="col-num">
        <col class="col-mode">
        <col class="col-ref">
        <col class="col-urai">
        <col class="col-sat">
        <col class="col-act">
      </colgroup>
      <thead>
        <tr>
          <th class="col-num">No</th>
          <th class="col-mode">Sumber</th>
          <th class="col-ref">Referensi AHSP</th>
          <th class="col-urai">Uraian Pekerjaan</th>
          <th class="col-sat">Satuan</th>
          <th class="col-act"></th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>`;

    block.dataset.tempId = `s${Date.now()}_${Math.random().toString(16).slice(2)}`;
    const tbody = block.querySelector('tbody');
    block.querySelector('.btn-add-pekerjaan').onclick = () => { addPekerjaan(tbody); scheduleSidebarRebuild(); };
    block.querySelector('.btn-del').onclick           = () => { block.remove(); scheduleSidebarRebuild(); };
    block.querySelector('.sub-name').addEventListener('input', scheduleSidebarRebuild);

    container.appendChild(block);
    requestAnimationFrame(()=>{
      block.scrollIntoView({ behavior:'smooth', block:'start' });
      block.classList.add('lp-flash');
      const inp = block.querySelector('.sub-name'); inp?.focus();
      say('Sub-Klasifikasi ditambahkan'); tbAnnounce && (tbAnnounce.textContent = 'Sub-Klasifikasi ditambahkan');
    });
    scheduleSidebarRebuild();
    return block;
  }

  function preselectSelect2($sel, id, labelText) {
    if (!id) return;
    const text = labelText || String(id);
    const opt = new Option(text, String(id), true, true);
    $sel.empty().append(opt).trigger('change');
  }

  function addPekerjaan(tbody, preset = {}, opts = {}) {
    const { autofocus = true } = opts;
    const {
      mode = 'ref',
      ref_id = null,
      ref_label = null,
      uraian = '',
      satuan = '',
      snapshot_kode = null,
      snapshot_uraian = null
    } = preset;

    const S2_TRUNC = 150;
    const pid = `p_${Date.now()}_${uid()}`;
    let row;

    const tpl = document.getElementById('tpl-pekerjaan-row-table');
    if (tpl && tpl.content) {
      row = tpl.content.firstElementChild.cloneNode(true);
      row.id = pid;
      row.dataset.anchorId = pid;
      row.querySelector('.current-ref')?.remove();
    } else {
      row = document.createElement('tr');
      row.id = pid;
      row.dataset.anchorId = pid;
      row.innerHTML = `
        <td class="col-num"></td>
        <td class="col-mode">
          <div class="vstack gap-1">
            <select class="form-select src" aria-label="Pilih sumber pekerjaan">
              <option value="ref">Referensi</option>
              <option value="ref_modified">Referensi (Dimodifikasi)</option>
              <option value="custom">Kustom</option>
            </select>
            <span class="source-badge badge rounded-pill text-bg-secondary source-hint"></span>
          </div>
        </td>
        <td class="col-ref">
          <div class="vstack gap-1">
            <div class="select2-host">
              <select class="form-select ref-select native-select" style="width:100%" aria-label="Cari referensi AHSP"></select>
            </div>
          </div>
        </td>
        <td class="col-urai">
          <div class="lp-urai-preview"></div>
          <textarea class="form-control uraian" rows="2" placeholder="Uraian pekerjaan"></textarea>
        </td>
        <td class="col-sat">
          <input class="form-control satuan" placeholder="cth: m, m2, m3, unit">
        </td>
        <td class="col-act">
          <button class="btn btn-outline-danger btn-del" title="Hapus baris">
            <i class="bi bi-x-lg" aria-hidden="true"></i>
            <span class="visually-hidden">Hapus</span>
          </button>
        </td>`;
    }

    // gate editing via dataset
    row.dataset.sourceType = mode || 'ref';
    if (ref_id) row.dataset.refId = String(ref_id);

    if (tbody) tbody.appendChild(row);
    renum(tbody);

    row.querySelector('.btn-del')?.addEventListener('click', () => {
      row.remove(); renum(tbody); scheduleSidebarRebuild();
    });

    const srcSel = row.querySelector('.src');
    if (srcSel) srcSel.value = mode;

    // ----- Select2 init (dengan guard jQuery/Select2) -----
    let host, $sel;
    const selEl       = row.querySelector('.ref-select');
    const ajaxUrl     = selEl?.dataset.ajaxUrl || '/referensi/api/search';
    const minLen      = Number(selEl?.dataset.minlength || 2);
    const placeholder = selEl?.dataset.placeholder || 'Cari referensi kode/nama…';

    if (HAS_JQ) {
      host = $(row).find('.select2-host');
      $sel = $(row).find('.ref-select');
    }

    if (HAS_S2 && $sel && $sel.length) {
      $sel.select2({
        width: '100%',
        placeholder,
        allowClear: false,
        minimumInputLength: minLen,
        dropdownAutoWidth: true,
        dropdownParent: host,
        ajax: {
          delay: 140,
          transport: function (params, success, failure) {
            const q = params.data && params.data.q ? params.data.q : '';
            fetch(`${ajaxUrl}?q=${encodeURIComponent(q)}`, { credentials: 'same-origin' })
              .then(r => r.json())
              .then(json => success({ results: mapToSelect2Results(json) }))
              .catch(failure);
          },
          processResults: function (data) { return data; }
        },
        closeOnSelect: true,
        templateResult: function(item) {
          if (item.loading) return item.text;
          return $(
            `<div class="s2-option">
              <div class="s2-title">${escapeHtml(item.text || '')}</div>
            </div>`
          );
        },
        templateSelection: function(item) {
          const full = item.text || '';
          const short = truncateText(full, S2_TRUNC);
          return $(`<div class="s2-selection-wrap" title="${escapeHtml(full)}">${escapeHtml(short)}</div>`);
        },
        dropdownCssClass: 's2-dropdown-wrap',
        selectionCssClass: 's2-selection-compact'
      });

      $sel.on('select2:open', function () {
        $('.select2-host.s2-open').removeClass('s2-open');
        host.addClass('s2-open');
        setTimeout(() => { try { $('.select2-container--open .select2-search__field').trigger('focus'); } catch{} }, 0);

        // blokir Enter agar tidak bentrok dengan shortcut global
        const $input = $('.select2-container--open .select2-search__field');
        $input.on('keydown.lpEnter', (ev) => {
          if (ev.key === 'Enter') { ev.stopImmediatePropagation(); }
        });
        $sel.one('select2:close', () => $input.off('keydown.lpEnter'));
      });

      $sel.on('select2:close', function () { host.removeClass('s2-open'); });

      row.querySelector('.ref-select')?.classList.add('is-enhanced');

      // Clear via Delete/Backspace pada selection
      const $selection = host.find('.select2-selection');
      $selection.on('keydown', function(e){
        if ((e.key === 'Delete' || e.key === 'Backspace') && $sel.val()) {
          $sel.val(null).trigger('change'); e.preventDefault(); e.stopPropagation();
        }
      });

      $sel.on('select2:open', function(){
        const $input = $('.select2-container--open .select2-search__field');
        const onKey = (e) => {
          if ((e.key === 'Delete' || e.key === 'Backspace') && !$input.val() && $sel.val()) {
            $sel.val(null).trigger('change'); $sel.select2('close'); e.preventDefault(); e.stopPropagation();
          }
        };
        $input.on('keydown.lpClear', onKey);
        $sel.one('select2:close', () => $input.off('keydown.lpClear', onKey));
      });

      // set dataset.refId & seed uraian saat ref_modified
      $sel.on('select2:select', function () {
        const v = $sel.val();
        if (v) row.dataset.refId = String(v);
        const srcNow = srcSel?.value;
        const ta = row.querySelector('.uraian');
        if (srcNow === 'ref_modified' && ta && !ta.value) {
          const item = $sel.select2('data')[0];
          const full = item?.text ? String(item.text) : '';
          const parts = full.split('—');
          const ura  = parts.length > 1 ? parts.slice(1).join('—').trim() : '';
          if (ura) { ta.value = ura; }
          const td = row.querySelector('td.col-urai, #lp-table tbody td:nth-child(4)'); 
          syncPreview(td || row);
          autoResize(ta);
        }
      });
      // kosongkan dataset.refId saat clear
      $sel.on('change', function () {
        if (!$sel.val()) { delete row.dataset.refId; }
      });

    } else {
      // Tanpa jQuery/Select2: biarkan native select terlihat & aktif
      if (selEl) {
        selEl.classList.remove('is-enhanced');
        selEl.removeAttribute('style');
        selEl.disabled = false;
      }
      warn('Select2 belum tersedia saat init baris; lanjut tanpa enhance');
    }

    // Preselect jika ada ref_id
    if (ref_id) {
      const lbl = ref_label
        || (snapshot_kode && snapshot_uraian
              ? `${snapshot_kode || ''}${snapshot_kode && snapshot_uraian ? ' — ' : ''}${snapshot_uraian || ''}`
              : null);
      if (HAS_S2 && $sel && $sel.length) {
        preselectSelect2($sel, ref_id, lbl);
      } else if (selEl) {
        const opt = document.createElement('option');
        opt.value = String(ref_id); opt.textContent = lbl || String(ref_id);
        opt.selected = true;
        selEl.innerHTML = ''; selEl.appendChild(opt);
      }
    }

    const uraianInput  = row.querySelector('.uraian');
    const satuanInput  = row.querySelector('.satuan');
    const sourceHint   = row.querySelector('.source-hint');

    if (uraian && uraianInput) uraianInput.value = uraian;
    if (satuan && satuanInput) satuanInput.value = satuan;

    function syncFields() {
      const v = srcSel?.value;
      const oldSourceType = row.dataset.sourceType;  // Save old value before update
      row.dataset.sourceType = v || '';
      const isCustom  = (v === 'custom');
      const isRefLike = (v === 'ref' || v === 'ref_modified');

      // AUTO-RESET: Reset uraian/satuan when changing FROM custom TO ref/ref_modified
      // User expects fields to clear when switching from CUSTOM to REF
      if (oldSourceType === 'custom' && isRefLike) {
        if (uraianInput) {
          uraianInput.value = '';
          autoResize(uraianInput);  // Resize textarea after clear
        }
        if (satuanInput) satuanInput.value = '';
        // Trigger preview update
        const td = row.querySelector('td.col-urai, #lp-table tbody td:nth-child(4)');
        if (td) syncPreview(td);
      }

      if (uraianInput) uraianInput.readOnly = !(isCustom || v === 'ref_modified');
      if (satuanInput) satuanInput.readOnly = !isCustom;

      if (HAS_S2 && $sel && $sel.length) {
        $sel.prop('disabled', !isRefLike).trigger('change.select2');
        if (!isRefLike && $sel.val()) {
          $sel.val(null).trigger('change');
          delete row.dataset.refId;
        }
      } else if (selEl) {
        selEl.disabled = !isRefLike;
        if (!isRefLike && selEl.value) {
          selEl.value = '';
          delete row.dataset.refId;
        }
      }

      if (sourceHint) sourceHint.textContent = buildSourceLabel(v);
      row.querySelector('.current-ref')?.remove();

      const td = row.querySelector('td.col-urai, #lp-table tbody td:nth-child(4)');
      if (td) { applyUraianGate(td); syncPreview(td); }
    }

    // Interaksi kolom uraian
    setupUraianInteractivity(row);

    // Autofocus UX saat tambah baru (bukan saat loadTree)
    if (autofocus) {
      requestAnimationFrame(()=>{
        row.scrollIntoView({ behavior:'smooth', block:'nearest' });
        const srcNow = srcSel?.value;
        if (srcNow === 'ref' || srcNow === 'ref_modified') {
          if (HAS_JQ) {
            const $selEl = $(row).find('.ref-select');
            $selEl.select2 ? $selEl.select2('open') : row.querySelector('.ref-select')?.focus();
          } else {
            row.querySelector('.ref-select')?.focus();
          }
        } else {
          row.querySelector('.uraian')?.focus();
        }
        row.classList.add('lp-flash');
        say('Pekerjaan ditambahkan');
        tbAnnounce && (tbAnnounce.textContent = 'Pekerjaan ditambahkan');
      });
    }

    if (HAS_S2 && $sel && $sel.length) {
      $sel.on('select2:select', function () {
        if (srcSel?.value === 'ref_modified' && uraianInput && !uraianInput.value) {
          const item = $sel.select2('data')[0];
          const text = item?.text ? String(item.text) : '';
          const parts = text.split('—');
          const ura  = parts.length > 1 ? parts.slice(1).join('—').trim() : '';
          if (ura) uraianInput.value = ura;
          const td = row.querySelector('td.col-urai, #lp-table tbody td:nth-child(4)');
          if (td) { syncPreview(td); autoResize(uraianInput); }
        }
      });
    }

    srcSel?.addEventListener('change', syncFields);
    syncFields();

    uraianInput?.addEventListener('input', scheduleSidebarRebuild);
    satuanInput?.addEventListener('input', scheduleSidebarRebuild);

    scheduleSidebarRebuild();
    return row;
  }

  // ========= [SIDEBAR TREE] Konstruksi, Search, dan Suggest ==================
  function el(tag, cls, html) { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function setNodeOpen(node, open) {
    node.classList.toggle('open', open);
    node.querySelector(':scope > .lp-node__header')?.setAttribute('aria-expanded', String(open));
    node.querySelectorAll(':scope > .lp-node__header .lp-node__toggle').forEach(t => t.textContent = open ? '▾' : '▸');
    const kids = node.querySelector(':scope > .lp-node__children');
    if (kids) kids.style.display = open ? '' : 'none';
  }
  function setNavAll(open) {
    if (!navWrap) return;
    navWrap.querySelectorAll('.lp-node').forEach(n => setNodeOpen(n, open));
    say(open ? 'Semua bagian terbuka' : 'Semua bagian tertutup');
  }

  function collectTree() {
    const data = [];
    if (!klasWrap) return data;
    const kCards = Array.from(klasWrap.children).filter(el => el?.querySelector && el.querySelector('.sub-wrap'));
    kCards.forEach((kc, ki) => {
      const kName = kc.querySelector('.klas-name')?.value?.trim()
        || kc.dataset.title || kc.getAttribute?.('data-title') || `Klasifikasi ${ki+1}`;
      const kAnchor = kc.dataset.anchorId || kc.id || `k_auto_${ki+1}`;
      const nodeK = { id: kAnchor, name: kName, sub: [] };

      const subWrap = kc.querySelector('.sub-wrap');
      Array.from(subWrap?.children || []).forEach((sb, si) => {
        const sName = sb.querySelector('.sub-name')?.value?.trim() || `Sub ${ki+1}.${si+1}`;
        const sAnchor = sb.dataset.anchorId || sb.id || `s_auto_${ki+1}_${si+1}`;
        const nodeS = { id: sAnchor, name: sName, pekerjaan: [] };

        const rows = sb.querySelectorAll('tbody tr');
        Array.from(rows || []).forEach((tr, pi) => {
          const uraian = tr.querySelector('.uraian')?.value?.trim()
            || tr.querySelector('.current-ref .ref-uraian')?.textContent?.trim()
            || `Pekerjaan ${pi+1}`;
          const pAnchor = tr.dataset.anchorId || tr.id || `p_auto_${ki+1}_${si+1}_${pi+1}`;
          nodeS.pekerjaan.push({ id: pAnchor, name: uraian });
        });

        nodeK.sub.push(nodeS);
      });

      data.push(nodeK);
    });
    return data;
  }

  function scheduleSidebarRebuild() {
    if (!navWrap) return;
    clearTimeout(scheduleSidebarRebuild._tid);
    scheduleSidebarRebuild._tid = setTimeout(buildSidebar, 120);
  }

  // ====== Autocomplete (grouped) =============================================
  function ensureSuggest(container, id) {
    // Cari global dulu untuk mencegah duplikat ID
    let box = document.getElementById(id);
    if (!box) {
      box = document.createElement('div');
      box.id = id;
      box.className = 'lp-autocomplete d-none';
      (container || document.body).appendChild(box);
    } else if (container && box.parentElement !== container) {
      container.appendChild(box);
    }
    return box;
  }

  function rankText(s, q){
    const t = s.toLowerCase(), qq = q.toLowerCase();
    const idx = t.indexOf(qq);
    if (idx === -1) return Infinity;
    return idx + Math.abs(s.length - qq.length)*0.01;
  }
  function buildGroupedSuggestions(tree, q){
    const out = { klas: [], sub: [], pekerjaan: [] };
    if (!q || q.length < 2) return out;
    tree.forEach(K=>{
      const rk = rankText(K.name, q);
      if (Number.isFinite(rk)) out.klas.push({ id: K.id, name: K.name, r: rk });
      (K.sub||[]).forEach(S=>{
        const rs = rankText(S.name, q);
        if (Number.isFinite(rs)) out.sub.push({ id: S.id, name: S.name, r: rs });
        (S.pekerjaan||[]).forEach(P=>{
          const rp = rankText(P.name, q);
          if (Number.isFinite(rp)) out.pekerjaan.push({ id: P.id, name: P.name, r: rp });
        });
      });
    });
    out.klas.sort((a,b)=>a.r-b.r); out.sub.sort((a,b)=>a.r-b.r); out.pekerjaan.sort((a,b)=>a.r-b.r);
    return out;
  }
  function renderSuggest(box, groups, q){
    if (!box) return;
    if (!q || q.length < 2 || (!groups.klas.length && !groups.sub.length && !groups.pekerjaan.length)) {
      hideSuggestions(box); return;
    }
    const makeGroup = (title, arr)=> arr.length ? `
      <div class="lp-ac-group">
        <div class="lp-ac-title">${title}</div>
        ${arr.slice(0, 8).map(i=>`<div class="lp-ac-item" data-id="${escapeHtml(i.id)}">${escapeHtml(i.name)}</div>`).join('')}
      </div>` : '';
    box.innerHTML = [
      makeGroup('Klasifikasi', groups.klas),
      makeGroup('Sub-Klasifikasi', groups.sub),
      makeGroup('Pekerjaan', groups.pekerjaan),
    ].join('');
    box.classList.remove('d-none');
    if (box === sideSuggest)  { navSearchSide?.setAttribute('aria-expanded', 'true'); }
    if (box === tbSuggest)    { navSearchToolbar?.setAttribute('aria-expanded', 'true'); }
    const total = groups.klas.length + groups.sub.length + groups.pekerjaan.length;
    const msg = total ? `${total} hasil` : 'Tidak ada hasil';
    if (box === sideSuggest) { navAnnounce && (navAnnounce.textContent = msg); }
    if (box === tbSuggest)   { tbAnnounce && (tbAnnounce.textContent = msg); }

    box.querySelectorAll('.lp-ac-item').forEach(it=>{
      it.addEventListener('click', ()=>{
        const id = it.getAttribute('data-id');
        if (id) {
          scrollToAnchor(id);
          if (box === sideSuggest) setOverlayVisible(false);
        }
      });
    });
  }
  function hideSuggestions(box){
    if (!box) return;
    box.classList.add('d-none');
    if (box === sideSuggest)  { navSearchSide?.setAttribute('aria-expanded', 'false'); }
    if (box === tbSuggest)    { navSearchToolbar?.setAttribute('aria-expanded', 'false'); }
  }

  function handleSearchInput(which){
    const q = which === 'side' ? (navSearchSide?.value || '') : (navSearchToolbar?.value || '');
    const tree = collectTree();
    const groups = buildGroupedSuggestions(tree, q);
    if (which === 'side') renderSuggest(sideSuggest, groups, q);
    else renderSuggest(tbSuggest, groups, q);
  }
  function commitSearch(which){
    const box = which === 'side' ? sideSuggest : tbSuggest;
    const first = box && !box.classList.contains('d-none') ? box.querySelector('.lp-ac-item') : null;
    if (first) {
      const id = first.getAttribute('data-id');
      if (id) {
        scrollToAnchor(id);
        if (which === 'side') setOverlayVisible(false);
        return true;
      }
    }
    return false;
  }

  // === Wiring event pada input & tombol Cari (toolbar & sidebar) =============
  navSearchSide?.addEventListener('input', () => handleSearchInput('side'));
  navSearchToolbar?.addEventListener('input', () => handleSearchInput('toolbar'));
  navSearchSide?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); commitSearch('side'); }
  });
  navSearchToolbar?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); commitSearch('toolbar'); }
  });
  document.getElementById('lp-toolbar-find')
    ?.addEventListener('click', () => { commitSearch('toolbar') || handleSearchInput('toolbar'); });

  function buildSidebar() {
    if (!navWrap) return;
    try {
      const data = collectTree();

      navWrap.innerHTML = '';
      btnExpandAllAll.forEach(b => b.onclick = () => setNavAll(true));
      btnCollapseAllAll.forEach(b => b.onclick = () => setNavAll(false));

      if (!Array.isArray(data) || data.length === 0) {
        navWrap.innerHTML = '<div class="text-muted small" style="padding:.5rem .75rem;">Belum ada klasifikasi/sub/pekerjaan.</div>';
        hideSuggestions(sideSuggest); hideSuggestions(tbSuggest);
        return;
      }

      const keywords = (navSearchSide?.value || '').trim().toLowerCase();
      const match = (s) => !keywords || s.toLowerCase().includes(keywords);

      navWrap.setAttribute('role', 'tree');
      navWrap.setAttribute('aria-label', 'Navigasi List Pekerjaan');

      data.forEach((K) => {
        const node = el('div', 'lp-node');
        const head = el('div', 'lp-node__header');
        const toggle = el('span', 'lp-node__toggle', '▸');
        const label = document.createElement('a');
        label.className = 'lp-node__label';
        label.innerHTML = highlightLabel(K.name, keywords);
        label.href = `#${K.id}`;
        label.addEventListener('click', (ev) => { ev.preventDefault(); scrollToAnchor(K.id); });
        const count = el('span', 'lp-node__count', `${(K.sub||[]).length} sub`);

        head.appendChild(toggle); head.appendChild(label); head.appendChild(count);
        head.setAttribute('role','treeitem'); head.setAttribute('aria-expanded','false');
        node.appendChild(head);

        const children = el('div', 'lp-node__children');
        children.setAttribute('role','group');
        node.appendChild(children);

        head.addEventListener('click', (e) => {
          if (e.target.closest('a')) return;
          setNodeOpen(node, !node.classList.contains('open'));
        });

        let openK = false;
        (K.sub || []).forEach((S) => {
          const nodeS = el('div', 'lp-node');
          const headS = el('div', 'lp-node__header');
          const toggleS = el('span', 'lp-node__toggle', '▸');
          const labelS = document.createElement('a');
          labelS.className = 'lp-node__label';
          labelS.innerHTML = highlightLabel(S.name, keywords);
          labelS.href = `#${S.id}`;
          labelS.addEventListener('click', (ev) => { ev.preventDefault(); scrollToAnchor(S.id); });
          const countS = el('span', 'lp-node__count', `${(S.pekerjaan || []).length}`);

          headS.appendChild(toggleS); headS.appendChild(labelS); headS.appendChild(countS);
          headS.setAttribute('role','treeitem'); headS.setAttribute('aria-expanded','false');
          nodeS.appendChild(headS);

          const childrenS = el('div', 'lp-node__children');
          childrenS.setAttribute('role','group');
          nodeS.appendChild(childrenS);

          let openS = false;
          (S.pekerjaan || []).forEach((P) => {
            const hit = match(K.name) || match(S.name) || match(P.name);
            if (!keywords || hit) openK = openS = true;

            const item = el('div', 'lp-node');
            const headP = el('div', 'lp-node__header');
            const bullet = el('span', 'lp-node__toggle', '•');
            const labelP = document.createElement('a');
            labelP.className = 'lp-node__label';
            labelP.innerHTML = highlightLabel(P.name, keywords);
            labelP.href = `#${P.id}`;
            labelP.addEventListener('click', (ev) => { ev.preventDefault(); scrollToAnchor(P.id); });

            headP.appendChild(bullet); headP.appendChild(labelP);
            headP.setAttribute('role','treeitem');
            item.appendChild(headP);
            childrenS.appendChild(item);
          });

          setNodeOpen(nodeS, openS);
          children.appendChild(nodeS);

          headS.addEventListener('click', (e) => {
            if (e.target.tagName === 'A') return;
            setNodeOpen(nodeS, !nodeS.classList.contains('open'));
          });
        });

        setNodeOpen(node, openK);
        navWrap.appendChild(node);
      });

      if (!navWrap.querySelector('.lp-node')) {
        navWrap.innerHTML = '<div class="text-muted small" style="padding:.5rem .75rem;">Tidak ada hasil yang cocok.</div>';
      }
    } catch (e) {
      err('buildSidebar failed:', e);
    }
  }

  // Inisialisasi suggest container SETELAH fungsi di atas siap
  sideSuggest = navSearchSide
    ? ensureSuggest(navSearchSide.closest('.lp-sidebar-search') || overlayPanel || document.body, 'lp-nav-suggest')
    : null;
  tbSuggest   = navSearchToolbar
    ? ensureSuggest(navSearchToolbar.closest('.lp-toolbar-search') || document.body, 'lp-nav-suggest-toolbar')
    : null;

  function scrollToAnchor(anchorId) {
    const target = document.getElementById(anchorId);
    if (!target) return;
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    target.classList.remove('lp-flash'); void target.offsetWidth; target.classList.add('lp-flash');
    if (isEdgeOpen()) closeEdge();
    if (isOverlayOpen()) setOverlayVisible(false);
  }

  // ========= [LOAD & SAVE] ====================================================
  async function loadTree() {
    try {
      if (!projectId) {
        if (!klasWrap.querySelector('.sub-wrap')) newKlas();
        scheduleSidebarRebuild();
        return;
      }

      const url = `/detail_project/api/project/${projectId}/list-pekerjaan/tree/`;
      const data = await jfetch(url, { method: 'GET' });
      const list = data?.klasifikasi;

      if (!list || !Array.isArray(list) || list.length === 0) {
        if (!klasWrap.querySelector('.sub-wrap')) newKlas();
        scheduleSidebarRebuild();
        return;
      }

      list.forEach(k => {
        const kCard = newKlas(k.name || null);
        if (k.id) kCard.dataset.id = k.id;
        const subWrap = kCard.querySelector('.sub-wrap');
        (k.sub || []).forEach(s => {
          const subBlock = addSub(subWrap, { name: s.name || null });
          if (s.id) subBlock.dataset.id = s.id;
          const tbody = subBlock.querySelector('tbody');
          (s.pekerjaan || []).forEach(p => {
            const row = addPekerjaan(tbody, {
              mode: p.source_type || 'ref',
              ref_id: p.ref_id || null,
              ref_label: (p.snapshot_kode || p.snapshot_uraian)
                ? `${p.snapshot_kode || ''}${p.snapshot_kode && p.snapshot_uraian ? ' — ' : ''}${p.snapshot_uraian || ''}`
                : null,
              uraian: p.snapshot_uraian || '',
              satuan: p.snapshot_satuan || '',
              snapshot_kode: p.snapshot_kode || null,
              snapshot_uraian: p.snapshot_uraian || null
            },
            { autofocus:false });
            if (p.id) row.dataset.id = p.id;
          });
        });
      });

      if (!klasWrap.querySelector('.sub-wrap')) newKlas();
      scheduleSidebarRebuild();

      setupScrollSpy();
    } catch (e) {
      err(e);
      tShow('Gagal memuat data.', 'danger');
      if (!klasWrap.querySelector('.sub-wrap')) newKlas();
      scheduleSidebarRebuild();
    }
  }

  async function handleSave() {
    if (!projectId) { alert('Project ID tidak ditemukan.'); return; }

    const btn  = document.querySelector('#btn-save');
    const orig = btn?.textContent;
    btn?.setAttribute('disabled', 'true');
    if (btn) btn.textContent = 'Menyimpan…';

    const payload = { klasifikasi: [] };
    let hasError = false;
    let globalOrder = 0; // ordering_index global per project (server mengharapkan ini)

    const kCards = Array.from(klasWrap.children).filter(el => el?.querySelector && el.querySelector('.sub-wrap'));

    kCards.forEach((kc, ki) => {
      const subWrap  = kc.querySelector('.sub-wrap');
      const kNameRaw = (kc.querySelector('.klas-name')?.value || '').trim();
      const hasAnySub = subWrap && subWrap.children.length > 0;
      if (!hasAnySub && !kNameRaw) return;

      const kCode = `K${ki + 1}`;
      const kName = kNameRaw || kCode;

      const k = {
        id: kc.dataset.id ? parseInt(kc.dataset.id, 10) : undefined,
        temp_id: kc.dataset.tempId,
        name: kName,
        ordering_index: ki + 1,
        sub: []
      };

      Array.from(subWrap?.children || []).forEach((sb, si) => {
        const rows     = sb.querySelectorAll('tbody tr');
        const sNameRaw = (sb.querySelector('.sub-name')?.value || '').trim();
        if (!rows.length && !sNameRaw) return;

        const sName = sNameRaw || `${kCode}.${si + 1}`;

        const s = {
          id: sb.dataset.id ? parseInt(sb.dataset.id, 10) : undefined,
          temp_id: sb.dataset.tempId,
          name: sName,
          ordering_index: si + 1,
          pekerjaan: []
        };

        rows.forEach(tr => {
          const src    = tr.querySelector('.src')?.value;

          // Baca nilai select2/native tanpa bergantung pada jQuery
          let refRaw;
          if (HAS_JQ) {
            refRaw = $(tr).find('.ref-select').val();
          } else {
            refRaw = tr.querySelector('.ref-select')?.value ?? '';
          }

          const uraian = (tr.querySelector('.uraian')?.value || '').trim();
          const satuan = (tr.querySelector('.satuan')?.value || '').trim();

          let invalid = false;
          let refIdNum = null;

          if (src === 'custom') {
            if (!uraian) invalid = true;
          } else {
            if (refRaw == null || refRaw === '') invalid = true;
            else {
              refIdNum = Number.parseInt(String(refRaw), 10);
              if (Number.isNaN(refIdNum)) invalid = true;
            }
          }

          if (invalid) {
            hasError = true;
            tr.classList.add('table-danger');
            return;
          } else {
            tr.classList.remove('table-danger');
          }

          globalOrder += 1;

          const existingId    = tr.dataset.id ? parseInt(tr.dataset.id, 10) : undefined;
          const originalRefId = (tr.dataset.refId ?? null); // di-seed saat load & saat select2:select
          const isRefChanged  = (refIdNum != null) && (String(refIdNum) !== String(originalRefId ?? ''));

          const p = {
            id: existingId,
            temp_id: `p_${ki}_${si}_${globalOrder}`,
            source_type: src,
            ordering_index: globalOrder
          };

          if (src === 'custom') {
            p.snapshot_uraian = uraian;
            if (satuan) p.snapshot_satuan = satuan;
          } else if (src === 'ref_modified') {
            if (!existingId || isRefChanged) p.ref_id = refIdNum;
            if (uraian) p.snapshot_uraian = uraian;
            if (satuan) p.snapshot_satuan = satuan;
          } else { // 'ref'
            if (!existingId || isRefChanged) p.ref_id = refIdNum;
          }

          s.pekerjaan.push(p);
        });

        if (s.pekerjaan.length) k.sub.push(s);
      });

      if (k.sub.length) payload.klasifikasi.push(k);
    });

    if (!payload.klasifikasi.length) {
      alert('Tidak ada data yang layak disimpan.');
      if (btn) { btn.disabled = false; btn.textContent = orig; }
      return;
    }
    if (hasError) {
      alert('❌ Periksa baris merah. Pastikan ref_id numerik & nama K/Sub tidak kosong (fallback Kx/Kx.y aktif).');
      if (btn) { btn.disabled = false; btn.textContent = orig; }
      return;
    }

    try {
      await jfetch(`/detail_project/api/project/${projectId}/list-pekerjaan/upsert/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      alert('✅ Perubahan tersimpan.');
      tbAnnounce && (tbAnnounce.textContent = 'Perubahan tersimpan');
      await reloadAfterSave();
    } catch (e) {
      const raw = (e && e.body && typeof e.body === 'string') ? e.body : (e?.message || '');
      const clean = String(raw).replace(/<[^>]+>/g, '').slice(0, 800);
      alert(`❌ Gagal simpan (${e?.status || ''}). ${clean || 'Cek log server.'}`);
      console.error('[LP] Save failed:', e);
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = orig; }
    }
  }

  async function reloadAfterSave() { klasWrap.innerHTML = ''; await loadTree(); }

  // ========= [BINDING] Toolbar & Sidebar Buttons =============================
  btnAddKlasAll.forEach(b => b.addEventListener('click', () => newKlas()));
  btnSaveAll.forEach(b  => b.addEventListener('click', () => handleSave()));

  // Track "klas terakhir yang disentuh" di views utama
  let lastKlasTarget = null;
  klasWrap.addEventListener('click', (e) => {
    const header = e.target.closest('.card-header');
    if (header?.parentElement?.classList.contains('card')) {
      lastKlasTarget = header.parentElement;
    }
  });

  // Sidebar buttons (+Klas / +Sub)
  const btnAddKlasSide = document.getElementById('btn-add-klas--sidebar');
  const btnAddSubSide  = document.getElementById('btn-add-sub--sidebar');

  btnAddKlasSide?.addEventListener('click', () => {
    const card = newKlas();
    lastKlasTarget = card;
  });

  btnAddSubSide?.addEventListener('click', () => {
    let container = null;

    if (lastKlasTarget?.isConnected) {
      container = lastKlasTarget.querySelector('.sub-wrap');
    }

    if (!container) {
      const activeLink = navWrap?.querySelector('.lp-node--active a.lp-node__label');
      const anchorId = activeLink ? (activeLink.getAttribute('href') || '').slice(1) : null;
      if (anchorId) {
        const el = document.getElementById(anchorId);
        const klasCard = el?.closest('.card.shadow-sm');
        if (klasCard) container = klasCard.querySelector('.sub-wrap');
      }
    }

    if (!container) {
      let lastKlas = klasWrap?.querySelector('.card.shadow-sm:last-of-type');
      if (!lastKlas) lastKlas = newKlas();
      container = lastKlas.querySelector('.sub-wrap');
    }

    addSub(container);
    scheduleSidebarRebuild();
  });

  // ========= [UI PREFERENCES] Compact Toggle =================================
  (function setupCompactToggle(){
    const KEY = 'lp_compact_v2';
    const app = root;
    const saved  = localStorage.getItem(KEY);
    const defOn  = (app.dataset.compactDefault === '1');
    const initialOn = saved === '1' ? true : saved === '0' ? false : defOn;

    applyCompact(initialOn);
    btnCompactAll.forEach(btn=>{
      btn.setAttribute('aria-pressed', String(initialOn));
      btn.addEventListener('click', (e) => { e.preventDefault(); applyCompact(!app.classList.contains('compact')); });
    });

    function applyCompact(on) {
      app.classList.toggle('compact', on);
      try { localStorage.setItem(KEY, on ? '1' : '0'); } catch {}
      btnCompactAll.forEach(b=> b.setAttribute('aria-pressed', String(on)));
    }
  })();

  // FAB klik = klik save utama
  document.getElementById('btn-save-fab')?.addEventListener('click', () => {
    document.querySelector('#btn-save')?.click();
  });

  // ========= [SCROLL SPY] Sinkron active node di tree ========================
  function setupScrollSpy(){
    if (setupScrollSpy._done) return;
    const io = new IntersectionObserver(entries=>{
      const vis = entries.filter(e=>e.isIntersecting)
                         .sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top)[0];
      if (!vis) return;
      const id = vis.target.id || vis.target.dataset.anchorId;
      if (!id) return;
      navWrap?.querySelectorAll('.lp-node--active').forEach(n=>n.classList.remove('lp-node--active'));
      const link = navWrap?.querySelector(`a.lp-node__label[href="#${CSS.escape(id)}"]`);
      link?.closest('.lp-node')?.classList.add('lp-node--active');
    }, { rootMargin: '-45% 0px -50% 0px', threshold: 0.01 });
    document.querySelectorAll('[data-anchor-id]').forEach(el=> io.observe(el));
    setupScrollSpy._done = true;
  }

  // ========= [OVERLAY RESIZE] Persist width ==================================
  (function enableOverlayResize(){
    const aside = overlaySidebar;
    const panel = overlayPanel;
    if (!aside || !panel) return;
    let resizer = panel.querySelector('.lp-resizer');
    if (!resizer) { resizer = document.createElement('div'); resizer.className = 'lp-resizer'; panel.appendChild(resizer); }
    // preferensi arah: 'east' (drag kanan membesar) atau 'west' (drag kiri membesar)
    const RESIZE_SENSE = (overlaySidebar?.dataset.resizeSense || 'west').toLowerCase();
    try{
      const saved = localStorage.getItem('lp_sidebar_w');
      if (saved) {
        document.documentElement.style.setProperty('--lp-sidebar-w', `${parseInt(saved,10)}px`);
      } else {
        document.documentElement.style.setProperty('--lp-sidebar-w', `486px`);
      }
    }catch{}
    let drag=false, startX=0, startW=0;
    resizer.addEventListener('mousedown', (e)=>{
      drag=true; startX=e.clientX; startW=panel.getBoundingClientRect().width; e.preventDefault();
      document.body.style.userSelect='none';
    });
    window.addEventListener('mousemove', (e)=>{
      if (!drag) return;
      const MIN_W = 320, MAX_W = 760;
      const dx = e.clientX - startX;
      const wRaw = (RESIZE_SENSE === 'east') ? (startW - dx) : (startW + dx);
      const w    = Math.min(Math.max(wRaw, MIN_W), MAX_W);
      document.documentElement.style.setProperty('--lp-sidebar-w', `${w}px`);
    });
    window.addEventListener('mouseup', ()=>{
      if (!drag) return; drag=false; document.body.style.userSelect='';
      const v = getComputedStyle(document.documentElement).getPropertyValue('--lp-sidebar-w');
      const w = parseInt(v, 10);
      if (Number.isFinite(w)) { try{ localStorage.setItem('lp_sidebar_w', String(w)); }catch{} }
    });
  })();

  // ========= [TOPBAR OFFSET] Sinkron CSS var =================================
  (function syncTopbarOffset(){
    function recalc(){
      const tb = document.getElementById('dp-topbar') || document.querySelector('#dp-topbar');
      if (!tb) return;
      const rect = tb.getBoundingClientRect();
      const h = Math.ceil(rect.height) + 1;
      document.documentElement.style.setProperty('--lp-topbar-h', `${h}px`);
      document.documentElement.style.setProperty('--dp-topbar-h', `${h}px`); // bridge ke core
    }
    recalc();
    window.addEventListener('resize', recalc);
    window.addEventListener('load', recalc);
  })();

  // ========= [START] Bootstrap module ========================================
  (async function start(){
    if (!projectId) warn('data-project-id pada #lp-app kosong; sebagian fitur (load/save) non-aktif.');
    if (typeof $ === 'undefined') warn('jQuery belum tersedia saat init awal (defer race?), lanjut saja.');
    if (typeof $?.fn?.select2 !== 'function') warn('Select2 belum terpasang; dropdown ref tetap jalan tanpa enhance.');

    btnExpandAllAll.forEach(b => b.onclick = () => setNavAll(true));
    btnCollapseAllAll.forEach(b => b.onclick = () => setNavAll(false));

    // Keyboard shortcuts (scoped ke #lp-app)
    try {
      const { bindMap } = window.DP.core.keys;
      bindMap(document, {
        'Ctrl+S': () => handleSave(),
        'Cmd+S':  () => handleSave(),
        'Esc':    () => { if (isOverlayOpen()) setOverlayVisible(false); },
        '/':      () => { if (isOverlayOpen()) navSearchSide?.focus(); else navSearchToolbar?.focus(); }
      }, { scopeSelector: '#lp-app' });
    } catch(_){ /* no-op jika core belum siap */ }

    await loadTree();
    setupRightHoverEdge();
  })();

  // ========= [DEBUG] =========================================================
  window.LP_DEBUG = {
    newKlas, addSub, addPekerjaan, handleSave, scheduleSidebarRebuild,
    report(){
      const map = {
        '#lp-app': !!root,
        '#klas-list (DIV)': !!klasWrap && klasWrap.tagName !== 'TBODY',
        '#btn-add-klas': btnAddKlasAll.length,
        '#btn-save': btnSaveAll.length,
        '#btn-compact': btnCompactAll.length,
        'toggle canonical/alias': btnSidebarTogAll.length,
        '#lp-sidebar (overlay)': !!overlaySidebar,
        '#lpSidebar (edge)': !!edgeSidebar,
        '#lp-nav': !!navWrap,
        '#lp-nav-search-side': !!navSearchSide,
        '#lp-nav-search (toolbar)': !!navSearchToolbar,
        '.lp-nav-expand-all/#lp-nav-expand-all': btnExpandAllAll.length,
        '.lp-nav-collapse-all/#lp-nav-collapse-all': btnCollapseAllAll.length,
      };
      console.table(map);
      return map;
    }
  };
})();
