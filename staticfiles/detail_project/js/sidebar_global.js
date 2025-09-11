// detail_project/static/detail_project/js/sidebar_global.js
(() => {
  const log = (...a) => console.debug('[dp-sidebar]', ...a);
  const qs  = (s, r = document) => r.querySelector(s);
  const isDesktop = () => window.matchMedia('(min-width: 992px)').matches;

  let hideTimer = null;

  function openMobile() {
    document.body.classList.add('dp-sidebar-open');
    qs('#dp-sidebar')?.setAttribute('aria-hidden', 'false');
  }
  function closeMobile() {
    document.body.classList.remove('dp-sidebar-open');
    qs('#dp-sidebar')?.setAttribute('aria-hidden', 'true');
  }
  function toggleMobile() {
    if (document.body.classList.contains('dp-sidebar-open')) closeMobile();
    else openMobile();
  }

  function showPeek() {
    if (!isDesktop()) return;
    clearTimeout(hideTimer);
    document.body.classList.add('dp-sidebar-peek');
  }
  function scheduleHidePeek() {
    if (!isDesktop()) return;
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => {
      document.body.classList.remove('dp-sidebar-peek');
    }, 180);
  }

  function init() {
    const badge = qs('#dp-sidebadge');
    const sidebar = qs('#dp-sidebar');
    const backdrop = qs('#dp-sidebar .dp-sidebar__backdrop');

    // Hover desktop → peek
    if (badge) {
      badge.addEventListener('mouseenter', showPeek);
      badge.addEventListener('mouseleave', scheduleHidePeek);
      // Click badge → mobile open/close
      badge.addEventListener('click', (e) => {
        if (!isDesktop()) {
          e.preventDefault();
          toggleMobile();
        }
      });
    }
    if (sidebar) {
      sidebar.addEventListener('mouseenter', showPeek);
      sidebar.addEventListener('mouseleave', scheduleHidePeek);
    }
    backdrop?.addEventListener('click', closeMobile);

    // ESC untuk menutup mobile
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeMobile();
    });

    // Saat resize ke desktop, pastikan mobile close
    window.addEventListener('resize', () => {
      if (isDesktop()) closeMobile();
    });

    // Sync aria-expanded
    const syncAria = () => {
      const expanded = document.body.classList.contains('dp-sidebar-open');
      badge?.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    };
    const obs = new MutationObserver(syncAria);
    obs.observe(document.body, { attributes: true, attributeFilter: ['class'] });
    syncAria();

    log('initialized');
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
