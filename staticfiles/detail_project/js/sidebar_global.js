// static/detail_project/js/sidebar_global.js
/* =======================================================================
   Tier-0 Drop-in — No-Conflict Sidebar Controller (Enhanced)
   - Trigger baru: [data-lp-toggle="sidebar"] (opt-in)
   - Kompat lama : #dp-sidebadge, #dp-sidebar-toggle
   - Hover-edge  : .lp-sidebar-hotspot (opsional)
   - State lama  : dp-sidebar-open / dp-sidebar-peek / dp-sidebar-pinned
   - A11y        : aria-controls/expanded/hidden; focus trap saat mobile open
   - CustomEvt   : dp:sidebar:open/close/pinned:change/peek:start/peek:end/change
   - Persist     : pinned (desktop) via localStorage (kunci: dp.sidebar.pinned)
   - Autobind    : MutationObserver untuk trigger yang muncul belakangan
   - No-conflict : tidak stopPropagation; preventDefault hanya anchor dummy
   - Guard       : anti double-binding
   ======================================================================= */
(() => {
  const $  = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const mm = (q) => window.matchMedia(q);
  const isDesktop = () => mm('(min-width: 992px)').matches;

  const body     = document.body;
  const sidebar  = $('#dp-sidebar');
  if (!sidebar) return; // tidak ada sidebar di halaman ini

  const backdrop = document.querySelector('.dp-sidebar__backdrop');

  const triggerSelNew = '[data-lp-toggle="sidebar"]';
  const triggerSelOld = '#dp-sidebadge, #dp-sidebar-toggle';
  const hotspot       = $('.lp-sidebar-hotspot'); // opsional

  const bound = new WeakSet();
  const STORAGE_PIN = 'dp.sidebar.pinned';

  // ===== Utilities =====
  const dispatch = (type, detail = {}) => {
    document.dispatchEvent(new CustomEvent(type, { detail, bubbles: true }));
    document.dispatchEvent(new CustomEvent('dp:sidebar:change', { detail: { type, ...detail }, bubbles: true }));
  };

  function isAnchorDummy(el) {
    const tag = el.tagName?.toLowerCase();
    const href = (el.getAttribute('href') || '').trim();
    const role = (el.getAttribute('role') || '').trim();
    return (tag === 'a' && (href === '' || href === '#')) || role === 'button';
  }

  function getTopbarHeight() {
    // Base detail sudah set CSS var; ini fallback kalau belum
    const tb = $('#dp-topbar');
    const h = tb ? Math.ceil(tb.getBoundingClientRect().height) : 64;
    return Number(getComputedStyle(document.documentElement).getPropertyValue('--dp-topbar-h').replace('px','')) || h;
  }

  // ===== State helpers =====
  const isOpenMobile = () => body.classList.contains('dp-sidebar-open');
  const isPeek       = () => body.classList.contains('dp-sidebar-peek');
  const isPinned     = () => body.classList.contains('dp-sidebar-pinned');
  const anyOpen      = () => isOpenMobile() || isPeek() || isPinned();

  // ===== ARIA & role =====
  function ensureAriaControlsOnTriggers(triggers) {
    triggers.forEach(t => {
      if (!t.hasAttribute('aria-controls')) t.setAttribute('aria-controls', 'dp-sidebar');
      if (!t.hasAttribute('aria-expanded')) t.setAttribute('aria-expanded', 'false');
    });
  }
  function applySidebarRole() {
    // Mobile open → dialog modal; Desktop peek/pinned → complementary
    if (isOpenMobile()) {
      sidebar.setAttribute('role', 'dialog');
      sidebar.setAttribute('aria-modal', 'true');
    } else {
      sidebar.setAttribute('role', 'complementary');
      sidebar.removeAttribute('aria-modal');
    }
  }
  function syncAria() {
    const open = anyOpen();
    sidebar.setAttribute('aria-hidden', open ? 'false' : 'true');
    applySidebarRole();
    getAllTriggers().forEach(t => t.setAttribute('aria-expanded', open ? 'true' : 'false'));
  }

  // ===== Focus trap (mobile open) =====
  const TABBABLE = 'a[href], area[href], input:not([disabled]), select:not([disabled]), ' +
                   'textarea:not([disabled]), button:not([disabled]), [tabindex]:not([tabindex="-1"])';
  let lastActiveBeforeOpen = null;
  function firstTabbable(root) {
    return $(TABBABLE, root) || root;
  }
  function trapKeydown(e) {
    if (!isOpenMobile()) return;
    if (e.key !== 'Tab') return;
    const focusable = $$(TABBABLE, sidebar).filter(el => el.offsetParent !== null);
    if (focusable.length === 0) { e.preventDefault(); return; }
    const first = focusable[0];
    const last  = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault(); last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault(); first.focus();
    }
  }
  function onOpenFocusTrap() {
    lastActiveBeforeOpen = document.activeElement;
    setTimeout(() => { firstTabbable(sidebar)?.focus?.(); }, 0);
    document.addEventListener('keydown', trapKeydown, true);
  }
  function onCloseFocusTrap() {
    document.removeEventListener('keydown', trapKeydown, true);
    if (lastActiveBeforeOpen && lastActiveBeforeOpen.focus) {
      setTimeout(() => { try { lastActiveBeforeOpen.focus(); } catch {} }, 0);
    }
    lastActiveBeforeOpen = null;
  }

  // ===== Desktop/Mobile actions =====
  function openMobile()  {
    body.classList.add('dp-sidebar-open');
    syncAria(); onOpenFocusTrap();
    dispatch('dp:sidebar:open', { mode: 'mobile' });
  }
  function closeMobile() {
    if (!isOpenMobile()) return;
    body.classList.remove('dp-sidebar-open');
    syncAria(); onCloseFocusTrap();
    dispatch('dp:sidebar:close', { mode: 'mobile' });
  }
  function toggleMobile() { isOpenMobile() ? closeMobile() : openMobile(); }

  function openPeek()    {
    body.classList.add('dp-sidebar-peek');
    syncAria();
    dispatch('dp:sidebar:peek:start', { mode: 'desktop' });
  }
  function hidePeek()    {
    if (!isPeek()) return;
    body.classList.remove('dp-sidebar-peek');
    syncAria();
    dispatch('dp:sidebar:peek:end', { mode: 'desktop' });
  }
  function openPinned()  {
    body.classList.add('dp-sidebar-peek','dp-sidebar-pinned');
    try { localStorage.setItem(STORAGE_PIN, '1'); } catch {}
    syncAria();
    dispatch('dp:sidebar:pinned:change', { pinned: true });
  }
  function closeDesktop(){
    body.classList.remove('dp-sidebar-peek','dp-sidebar-pinned');
    try { localStorage.removeItem(STORAGE_PIN); } catch {}
    syncAria();
    dispatch('dp:sidebar:pinned:change', { pinned: false });
  }
  function togglePinned(){ isPinned() ? closeDesktop() : openPinned(); }

  // ===== Trigger binding =====
  function getAllTriggers() {
    const set = new Set([...$$(triggerSelOld), ...$$(triggerSelNew)]);
    return Array.from(set).filter(el => el && el.offsetParent !== null);
  }
  function bindClickTriggers() {
    const triggers = getAllTriggers();
    ensureAriaControlsOnTriggers(triggers);
    triggers.forEach(el => {
      if (bound.has(el)) return;
      bound.add(el);
      el.addEventListener('click', (e) => {
        if (isAnchorDummy(el)) e.preventDefault(); // tidak ganggu handler lain
        if (isDesktop()) togglePinned(); else toggleMobile();
      }, false);
    });
  }

  // Autobind untuk trigger yang ditambahkan dinamis
  const mo = new MutationObserver((mut) => {
    for (const m of mut) {
      if (m.type === 'childList') {
        if (m.addedNodes?.length) bindClickTriggers();
      }
    }
  });
  mo.observe(document.body, { childList: true, subtree: true });

  // ===== Hover-edge (opsional) =====
  let hideTimer = null;
  function setupHoverEdge() {
    if (!hotspot) return;
    const ENTER_DELAY = 30, LEAVE_DELAY = 180;
    hotspot.addEventListener('mouseenter', () => {
      if (document.body.classList.contains('lp-overlay-open')) return;
      if (isDesktop() && !isPinned()) { clearTimeout(hideTimer); openPeek(); }
    }, { passive: true });
    hotspot.addEventListener('mouseleave', () => {
      if (document.body.classList.contains('lp-overlay-open')) return;
      if (isDesktop() && !isPinned()) { clearTimeout(hideTimer); hidePeek(); }
    }, { passive: true });
    sidebar.addEventListener('mouseenter', () => {
      if (document.body.classList.contains('lp-overlay-open')) return;
      if (isDesktop() && !isPinned()) { clearTimeout(hideTimer); openPeek(); }
    }, { passive: true });
    sidebar.addEventListener('mouseleave', () => {
      if (document.body.classList.contains('lp-overlay-open')) return;
      if (isDesktop() && !isPinned()) {
        clearTimeout(hideTimer);
        hideTimer = setTimeout(hidePeek, LEAVE_DELAY);
      }
    }, { passive: true });
  }

  // ===== Backdrop / ESC / Outside click =====

  // tombol close di header sidebar (mobile & desktop)
  const closeBtn = sidebar.querySelector('.btn-close,[data-action="sidebar-close"]');
  closeBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    if (isDesktop()) {
      if (isPinned()) closeDesktop();
      else if (isPeek()) hidePeek();
    } else {
      closeMobile();
    }
  });


  backdrop?.addEventListener('click', closeMobile);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (isDesktop()) {
        if (isPinned()) closeDesktop();
        else if (isPeek()) hidePeek();
      } else {
        closeMobile();
      }
    }
  });
  document.addEventListener('click', (e) => {
    const inside = sidebar.contains(e.target);
    const isTrig = e.target.closest?.(triggerSelOld + ', ' + triggerSelNew);
    if (isDesktop() && !isPinned() && isPeek() && !inside && !isTrig) hidePeek();
  }, false);

  // ===== Resize & top offset sync =====
  let resizeT;
  function onResize() {
    clearTimeout(resizeT);
    resizeT = setTimeout(() => {
      // Reset state saat breakpoint berubah
      if (isDesktop()) {
        body.classList.remove('dp-sidebar-open');
        // apply pinned preferensi
        try { if (localStorage.getItem(STORAGE_PIN) === '1') openPinned(); } catch {}
      } else {
        body.classList.remove('dp-sidebar-peek','dp-sidebar-pinned');
      }
      // update top offset (fallback)
      const top = getTopbarHeight();
      sidebar.style.setProperty('--dp-topbar-h', top + 'px');
      syncAria();
    }, 100);
  }
  window.addEventListener('resize', onResize);
  new ResizeObserver(() => onResize()).observe(document.documentElement);
  mm('(min-width: 992px)').addEventListener?.('change', onResize);
  mm('(min-width: 992px)').addListener?.(onResize);

  // ===== Init =====
  // Terapkan preferensi pinned (desktop) saat load
  try { if (isDesktop() && localStorage.getItem(STORAGE_PIN) === '1') openPinned(); } catch {}
  // Pastikan ARIA reflect state yg sudah ter-apply
  syncAria();
  // Fallback set top offset awal
  sidebar.style.setProperty('--dp-topbar-h', getTopbarHeight() + 'px');

  document.documentElement.style.setProperty('--dp-topbar-h', getTopbarHeight() + 'px');

  bindClickTriggers();
  setupHoverEdge();
  document.addEventListener('lp:overlay:change', (e) => {
    const open = !!e.detail?.open;
    if (!isDesktop()) return;       // fokus kita desktop (peek/pinned)
    if (open) {
      if (!isPinned() && isPeek()) hidePeek(); // tutup peek sementara
    } else {
      // no-op; kalau user pengen peek lagi, tinggal gerakkan mouse ke kiri
    }
  });
  // Fallback: jika class body lp-overlay-open berubah (tanpa event),
  // pastikan peek tertutup saat overlay aktif.
  const moBody = new MutationObserver(() => {
    if (!isDesktop()) return;
    const overlayOpen = document.body.classList.contains('lp-overlay-open');
    if (overlayOpen && !isPinned() && isPeek()) hidePeek();
  });
  moBody.observe(document.body, { attributes: true, attributeFilter: ['class'] });
  // === Hover-edge kanan (global) → prioritas #vpVarOffcanvas lalu #dp-sidebar
  (function(){
    var edge = document.querySelector('.dp-hover-edge');
    if (!edge) return;
    // Desktop only
    if (!mm('(hover:hover) and (pointer:fine)').matches) return;

    // Tentukan target panel prioritas:
    // 1) custom via body[data-edge-target], boleh comma-separated selectors
    // 2) #vpVarOffcanvas (offcanvas parameter di Volume)
    // 3) fallback #dp-sidebar
    function resolveTarget(){
      var manual = document.body.getAttribute('data-edge-target');
      if (manual){
        var sels = manual.split(',').map(s => s.trim()).filter(Boolean);
        for (var i=0;i<sels.length;i++){
          var el = document.querySelector(sels[i]);
          if (el) return el;
        }
      }
      var off = document.getElementById('vpVarOffcanvas');
      if (off) return off;
      return document.getElementById('dp-sidebar');
    }

    var target = resolveTarget();
    if (!target) return;

    function setInert(on){
      var main = document.getElementById('vp-app') || document.querySelector('main') || document.body;
      if (!main) return;
      if (on) main.setAttribute('inert',''); else main.removeAttribute('inert');
    }

    var isOffcanvas = target.classList.contains('offcanvas');
    var offApi = null;
    if (isOffcanvas){
      try { offApi = (window.bootstrap && bootstrap.Offcanvas) ? bootstrap.Offcanvas.getOrCreateInstance(target) : null; } catch(e){}
    }

    function openPanel(){
      if (isOffcanvas){
        if (offApi) offApi.show();
        else { target.classList.add('show'); target.style.visibility = 'visible'; }
      } else {
        if (isDesktop()) openPeek(); else openMobile();
      }
      setInert(true);
    }
    function closePanel(){
      if (isOffcanvas){
        if (offApi) offApi.hide();
        else { target.classList.remove('show'); target.style.visibility = ''; }
      } else {
        if (isDesktop()) { if (!isPinned()) hidePeek(); } else closeMobile();
      }
      setInert(false);
    }

    if (isOffcanvas && offApi){
      target.addEventListener('hidden.bs.offcanvas', function(){ setInert(false); });
    }

    var timer = null;
    edge.addEventListener('mouseenter', function(){ timer = setTimeout(openPanel, 80); }, {passive:true});
    edge.addEventListener('mouseleave', function(){ if (timer){ clearTimeout(timer); timer=null; } }, {passive:true});
    // Tutup ketika mouse keluar dari panel (opsional aman)
    target.addEventListener('mouseleave', function(){ closePanel(); }, {passive:true});

    document.addEventListener('keydown', function(e){
      if (e.key === 'Escape') closePanel();
    }, false);
  })();

  /* === Adapter standar: DP.side + trigger [data-toggle="side-right"] === */
window.DP = window.DP || {};
DP.side = DP.side || (function(){
  const bus = (type) => document.dispatchEvent(new CustomEvent(type, { bubbles:true }));
  function getRight()    { return document.getElementById('lp-sidebar'); }
  function isStdRight(s) { return !!(s && s.classList.contains('dp-sidebar') && s.dataset.side === 'right'); }

  function openRight(){
    const s = getRight();
    if (!s) return;
    if (isStdRight(s)) {
      s.classList.add('is-open');
      document.documentElement.classList.add('lp-side-open');
      // backdrop standar (data-for="lp-sidebar")
      const bd = document.querySelector('.dp-sidebar-backdrop[data-for="lp-sidebar"]');
      if (bd) bd.hidden = false;
      // ARIA
      s.setAttribute('aria-hidden','false');
      document.querySelectorAll('[data-toggle="side-right"][aria-controls="lp-sidebar"]')
        .forEach(el => el.setAttribute('aria-expanded','true'));
      // beri tahu ekosistem lama (LP)
      bus('lp:overlay:change'); // tidak merugikan yang lama
    } else {
      bus('dp:side:right:open'); // overlay LP lama akan menangani
    }
  }
  function closeRight(){
    const s = getRight();
    if (!s) return;
    if (isStdRight(s)) {
      s.classList.remove('is-open');
      document.documentElement.classList.remove('lp-side-open');
      const bd = document.querySelector('.dp-sidebar-backdrop[data-for="lp-sidebar"]');
      if (bd) bd.hidden = true;
      s.setAttribute('aria-hidden','true');
      document.querySelectorAll('[data-toggle="side-right"][aria-controls="lp-sidebar"]')
        .forEach(el => el.setAttribute('aria-expanded','false'));
      bus('lp:overlay:change');
    } else {
      bus('dp:side:right:close');
    }
  }
  function toggleRight(){ (isOpenRight() ? closeRight() : openRight()); }
  function isOpenRight(){
    const s = getRight();
    if (!s) return false;
    return isStdRight(s) ? s.classList.contains('is-open') : false; // overlay lama ditangani oleh file LP
  }
  return {
    open(side){ if (side === 'right') openRight(); /* left handled elsewhere */ },
    close(side){ if (side === 'right') closeRight(); },
    toggle(side){ if (side === 'right') toggleRight(); },
    isOpen(side){ return side === 'right' ? isOpenRight() : false; }
  };
})();

  // Bind trigger generik untuk kanan
  (function bindRightTriggers(){
    const sel = '[data-toggle="side-right"]';
    const bound = new WeakSet();
    function wire(root=document){
      root.querySelectorAll(sel).forEach(el=>{
        if (bound.has(el)) return;
        bound.add(el);
        if (!el.hasAttribute('aria-controls')) el.setAttribute('aria-controls','lp-sidebar');
        if (!el.hasAttribute('aria-expanded')) el.setAttribute('aria-expanded','false');
        el.addEventListener('click', (e)=>{
          // aman untuk <a href="#"> dsb
          const href = (el.getAttribute('href')||'').trim();
          const role = (el.getAttribute('role')||'').trim();
          if (el.tagName.toLowerCase()==='a' && (href===''||href==='#')) e.preventDefault();
          if (role==='button') e.preventDefault();
          DP.side.toggle('right');
        }, false);
      });
    }
    wire();
    new MutationObserver(m=>m.forEach(x=>x.addedNodes&&wire(document))).observe(document.body,{childList:true,subtree:true});
  })();
  

  
  syncAria();
})();
