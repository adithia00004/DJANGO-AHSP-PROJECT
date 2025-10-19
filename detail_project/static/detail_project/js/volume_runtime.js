/* volume_runtime.js — SSOT mode (sidebar only, no layout writes)
   - Tidak menulis var global maupun vp-* untuk layout offset.
   - Sidebar: toggle/hover/ESC/click-outside/resizer + persist width (localStorage).
   - Emit event kompatibel: lp:sidebar:open/opened/close/closed/resize
*/
(function () {
  'use strict';

  const doc = document;
  const qs  = (s, c = doc) => c.querySelector(s);

  /* =========================
     Sidebar driver (overlay)
     ========================= */
  function initSidebar() {
    const sidebar   = doc.getElementById('vp-sidebar');
    if (!sidebar) return;

    const panel     = qs('.dp-sidebar-inner, .lp-sidebar-inner', sidebar) || sidebar;
    const toggleBtn = doc.getElementById('btn-vp-sidebar-toggle') || qs('.js-vp-sidebar-toggle');
    const hotspot   = qs('.vp-overlay-hotspot, .lp-overlay-hotspot');

    // Hindari injeksi kelas dp-*; cukup atribut data-side
    if (!sidebar.dataset.side) sidebar.setAttribute('data-side', 'right');

    const HOVERCLOSE   = sidebar.getAttribute('data-hoverclose') !== '0';
    const RESIZE_SENSE = (sidebar.getAttribute('data-resize-sense') || 'east').toLowerCase();

    const projectId = document.getElementById('vol-app')?.dataset?.projectId || '0';
    const WIDTH_STORAGE_KEY = `vp_sidebar_w:${projectId}`;
    const MIN_W = 320, MAX_W = 760;

    let pinned = false;      // pinned = dibuka via tombol
    let closeTimer = null;
    let lastFocused = null;  // elemen fokus sebelum overlay dibuka
    let trapKeydown = null;  // handler untuk focus trap

    const isOpen = () =>
      sidebar.classList.contains('is-open') || sidebar.getAttribute('aria-hidden') === 'false';

    function emit(name, detail) {
      doc.dispatchEvent(new CustomEvent(`lp:sidebar:${name}`, {
        detail: Object.assign({ id: 'vp-sidebar' }, detail || {})
      }));
    }

    function applyAria(open) {
      sidebar.setAttribute('aria-hidden', open ? 'false' : 'true');
      sidebar.setAttribute('role', open ? 'dialog' : 'complementary');
      if (open) sidebar.setAttribute('aria-modal', 'true');
      else sidebar.removeAttribute('aria-modal');
      if (toggleBtn) toggleBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      doc.dispatchEvent(new CustomEvent('lp:overlay:change', { detail: { id: 'vp-sidebar', open } }));
      // toggle backdrop sibling jika ada
      const backdrop = sidebar.parentElement?.querySelector('.dp-sidebar__backdrop');
      if (backdrop) {
         backdrop.style.opacity = open ? '1' : '';
         backdrop.style.pointerEvents = open ? 'auto' : 'none';
        }
    }

    function openSidebar({ by = 'program', pin = false } = {}) {
      if (closeTimer) { clearTimeout(closeTimer); closeTimer = null; }
      emit('open', { by });
      // simpan elemen fokus saat ini untuk dipulihkan saat close
      try { lastFocused = doc.activeElement || null; } catch { lastFocused = null; }
      sidebar.classList.add('is-open');
      applyAria(true);
      if (pin) pinned = true;
      hotspot?.classList.add('is-open'); // jangan intercept pointer saat terbuka
      // Pindahkan fokus ke panel hanya jika bukan dibuka via hover
      if (by !== 'hover') {
        const closeBtn = qs('.js-vp-sidebar-close, [data-action="close-sidebar"]', sidebar);
        const titleEl  = qs('#vpSidebarTitle', sidebar);
        const bodyEl   = qs('.dp-sidebar-body, .lp-sidebar-body, .dp-sidebar-inner, .lp-sidebar-inner', sidebar);
        const target   = closeBtn || titleEl || bodyEl || sidebar;
        if (target && typeof target.focus === 'function') {
          if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1');
          try { target.focus(); } catch {}
        }
        startFocusTrap();
      }
      requestAnimationFrame(() => emit('opened', { by }));
    }

    function closeSidebar({ by = 'program', force = false } = {}) {
      if (!isOpen()) return;
      if (!force && pinned && by !== 'button') return; // pinned: hanya tombol yang menutup
      emit('close', { by });
      sidebar.classList.remove('is-open');
      applyAria(false);
      if (by === 'button') pinned = false;
      hotspot?.classList.remove('is-open');
      // hentikan focus trap & pulihkan fokus
      stopFocusTrap();
      try {
        if (toggleBtn && typeof toggleBtn.focus === 'function') toggleBtn.focus();
        else if (lastFocused && typeof lastFocused.focus === 'function') lastFocused.focus();
      } catch {}
      lastFocused = null;
      requestAnimationFrame(() => emit('closed', { by }));
    }

    function scheduleClose(ms = 160) {
      if (!HOVERCLOSE || pinned) return;
      if (closeTimer) clearTimeout(closeTimer);
      closeTimer = setTimeout(() => closeSidebar({ by: 'hover' }), ms);
    }

    // Toggle button
    if (toggleBtn && !toggleBtn.dataset.bound) {
      toggleBtn.addEventListener('click', (e) => {
        e.preventDefault();
        if (isOpen() && pinned) closeSidebar({ by: 'button', force: true });
        else openSidebar({ by: 'button', pin: true });
      });
      toggleBtn.dataset.bound = '1';
    }

    // Close button inside sidebar header
    const closeBtn = qs('.js-vp-sidebar-close, [data-action="close-sidebar"]', sidebar);
    if (closeBtn && !closeBtn.dataset.bound) {
      closeBtn.addEventListener('click', (e) => {
        e.preventDefault();
        closeSidebar({ by: 'button', force: true });
      });
      closeBtn.dataset.bound = '1';
    }

    // Hotspot hover (desktop)
    if (hotspot && !hotspot.dataset.bound) {
      const hasHover = window.matchMedia?.('(hover: hover)').matches;
      if (hasHover) {
        hotspot.addEventListener('mouseenter', () => openSidebar({ by: 'hover', pin: false }));
        hotspot.addEventListener('mouseleave', () => scheduleClose(180));
      }
      hotspot.dataset.bound = '1';
    }

    // Auto-close on leave (unpinned)
    sidebar.addEventListener('mouseenter', () => { if (closeTimer) { clearTimeout(closeTimer); closeTimer = null; } });
    sidebar.addEventListener('mouseleave', () => { if (!pinned) scheduleClose(180); });

    // ESC & click-outside
    doc.addEventListener('keydown', (e) => {
      if (e.key !== 'Escape' || !isOpen()) return;
      if (doc.body.classList.contains('modal-open')) return; // hormati modal BS
      closeSidebar({ by: 'esc', force: true });
    });
    doc.addEventListener('mousedown', (e) => {
      if (!isOpen() || pinned) return;
      const inside   = sidebar.contains(e.target);
      const onToggle = toggleBtn ? toggleBtn.contains(e.target) : false;
      const onHot    = hotspot ? hotspot.contains(e.target) : false;
      const onBackdrop = e.target?.classList?.contains('dp-sidebar__backdrop');
      if ((!inside && !onToggle && !onHot) || onBackdrop) closeSidebar({ by: 'outside' });
    });

    // Click pada area overlay (di luar panel) menutup, tanpa perlu backdrop terpisah
    sidebar.addEventListener('click', (e) => {
      if (!isOpen() || pinned) return; // hormati mode pinned: hanya tombol menutup
      const panelInner = qs('.dp-sidebar-inner, .lp-sidebar-inner', sidebar) || sidebar;
      if (panelInner && !panelInner.contains(e.target)) {
        closeSidebar({ by: 'outside' });
      }
    });

    // =============== Focus Trap (aksesibilitas) ===============
    function getFocusable(container) {
      const nodes = container.querySelectorAll(
        'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      return Array.from(nodes).filter(el => {
        const cs = window.getComputedStyle(el);
        return cs.visibility !== 'hidden' && cs.display !== 'none';
      });
    }

    function startFocusTrap() {
      if (trapKeydown) return; // sudah aktif
      trapKeydown = (e) => {
        if (e.key !== 'Tab' || !isOpen()) return;
        const focusables = getFocusable(sidebar);
        if (!focusables.length) return;
        const first = focusables[0];
        const last  = focusables[focusables.length - 1];
        if (e.shiftKey && doc.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && doc.activeElement === last) { e.preventDefault(); first.focus(); }
      };
      doc.addEventListener('keydown', trapKeydown, true);
    }

    function stopFocusTrap() {
      if (!trapKeydown) return;
      doc.removeEventListener('keydown', trapKeydown, true);
      trapKeydown = null;
    }

    // Restore width (scoped ke elemen sidebar → tidak global)
    (function restoreWidth() {
      try {
        const saved = parseInt(localStorage.getItem(WIDTH_STORAGE_KEY) || '', 10);
        const w = Number.isFinite(saved) ? Math.min(MAX_W, Math.max(MIN_W, saved)) : 486;
        sidebar.style.setProperty('--lp-sidebar-w', `${w}px`);
        emit('resize', { width: w });
      } catch {}
    })();

    // Ensure resizer exists
    let resizer = qs('.dp-resizer, .lp-resizer', sidebar);
    if (!resizer) {
      resizer = doc.createElement('div');
      resizer.className = 'dp-resizer lp-resizer';
      panel.appendChild(resizer);
    }

    // Drag resize (tulis var hanya pada elemen sidebar)
    if (resizer && !resizer.dataset.bound) {
      let dragging = false, startX = 0, startW = 0;
      const clamp = (w) => Math.min(MAX_W, Math.max(MIN_W, w));

      const onMove = (ev) => {
        if (!dragging) return;
        const x = ev.touches ? ev.touches[0].clientX : ev.clientX;
        const dx = x - startX;
        const raw = RESIZE_SENSE === 'east' ? startW - dx : startW + dx;
        const w = clamp(raw);
        sidebar.style.setProperty('--lp-sidebar-w', `${Math.round(w)}px`);
        try { localStorage.setItem(WIDTH_STORAGE_KEY, String(Math.round(w))); } catch {}
        emit('resize', { width: w });
      };

      const onUp = () => {
        if (!dragging) return;
        dragging = false;
        doc.body.classList.remove('user-resizing');
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('touchmove', onMove);
        window.removeEventListener('mouseup', onUp);
        window.removeEventListener('touchend', onUp);
      };

      const onDown = (ev) => {
        ev.preventDefault();
        dragging = true;
        startX = ev.touches ? ev.touches[0].clientX : ev.clientX;
        startW = panel.getBoundingClientRect().width;
        doc.body.classList.add('user-resizing');
        window.addEventListener('mousemove', onMove, { passive: false });
        window.addEventListener('touchmove', onMove, { passive: false });
        window.addEventListener('mouseup', onUp, { passive: true });
        window.addEventListener('touchend', onUp, { passive: true });
      };

      resizer.addEventListener('mousedown', onDown);
      resizer.addEventListener('touchstart', onDown, { passive: false });
      resizer.dataset.bound = '1';
    }

    // Init ARIA default tertutup
    applyAria(false);

    // Optional: ekspor API minimal
    window.vpSidebar = {
      open: () => openSidebar({ by: 'api' }),
      close: () => closeSidebar({ by: 'api', force: true }),
      toggle: () => (isOpen() ? closeSidebar({ by: 'api', force: true }) : openSidebar({ by: 'api', pin: true }))
    };
  }

  // Boot
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSidebar, { once: true });
  } else {
    initSidebar();
  }
})();
