/* =====================================================================
   WP-B4 — Readiness autoload (display-only, bundle-agnostic).

   For consumer pages whose JS is a built bundle (Jadwal) or that we don't
   want to touch (Rekap Kebutuhan). Drop an anchor element carrying
   data-readiness-endpoint; this self-initializes on DOMContentLoaded,
   fetches the canonical readiness, and renders the shared banner into it.

     <div data-readiness-endpoint="/detail_project/api/project/1/readiness/"></div>

   The page never recomputes readiness; it only shows the server verdict.
   Requires shared/readiness_banner.js (window.ReadinessBanner) loaded first.
   ===================================================================== */
(function () {
  function render(host) {
    const url = host.getAttribute('data-readiness-endpoint');
    if (!url) return Promise.resolve();
    return fetch(url, { credentials: 'same-origin' })
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => {
        if (!j || !j.ok) return;
        const html = (window.ReadinessBanner && window.ReadinessBanner.buildReadinessBannerHTML)
          ? window.ReadinessBanner.buildReadinessBannerHTML(j.readiness)
          : null;
        if (!html) {
          host.innerHTML = '';
          host.classList.add('d-none');
          return;
        }
        host.classList.remove('d-none');
        host.className = 'alert alert-warning py-2 px-3 small mb-2';
        host.setAttribute('role', 'status');
        host.innerHTML = html;
      })
      .catch(() => { /* advisory only — never block the page */ });
  }

  function init() {
    document.querySelectorAll('[data-readiness-endpoint]').forEach(render);
  }

  if (document.readyState !== 'loading') init();
  else document.addEventListener('DOMContentLoaded', init);

  // Exposed so a page can refresh after its own mutations if desired.
  if (typeof window !== 'undefined') {
    window.ReadinessAutoload = { render, init };
  }
})();
