// /static/detail_project/js/core/toast.js
(() => {
  const DP = (window.DP = window.DP || {}); 
  DP.core = DP.core || {};
  if (DP.core.toast) return;

  const STATE = { max: 3 }; // batasi stack agar tidak menumpuk

  function ensureArea() {
    let area = document.getElementById('dp-toast-area');
    if (!area) {
      area = document.createElement('div');
      area.id = 'dp-toast-area';
      area.className = 'position-fixed top-0 end-0 p-3';
      area.style.zIndex = '13100'; // Above modal for always-visible feedback
      area.setAttribute('role', 'region');
      area.setAttribute('aria-label', 'Notifications');
      area.setAttribute('aria-live', 'polite');
      document.body.appendChild(area);
    }
    return area;
  }

  function normalizeInput(a, b, c) {
    // Back-compat: show(msg, variant='success', delay=1600)
    if (typeof a === 'string') {
      return { message: a, variant: b || 'success', autohide: true, delay: (typeof c === 'number' ? c : 1600) };
    }
    // New shape: show({ message, title?, variant?, autohide?, delay? })
    const o = a || {};
    return {
      message: o.message ?? '',
      title: o.title ?? '',
      variant: o.variant || 'success',
      autohide: (typeof o.autohide === 'boolean') ? o.autohide : true,
      delay: (typeof o.delay === 'number') ? o.delay : 1600
    };
  }

  function clampStack(area) {
    const items = area.querySelectorAll('.toast');
    const over = items.length - STATE.max;
    for (let i = 0; i < over; i++) {
      const el = items[i];
      try {
        const inst = bootstrap.Toast.getOrCreateInstance(el);
        inst.hide();
      } catch (_) { /* ignore */ }
      el.remove();
    }
  }

  function buildToast({ message, title, variant, autohide, delay }) {
    const el = document.createElement('div');
    el.className = `toast align-items-center text-bg-${variant} border-0`;
    el.setAttribute('role', 'alert');
    el.setAttribute('aria-atomic', 'true');
    // Atur aria-live per tingkat urgensi
    el.setAttribute('aria-live', variant === 'danger' ? 'assertive' : 'polite');

    const wrap = document.createElement('div');
    wrap.className = 'd-flex';

    const body = document.createElement('div');
    body.className = 'toast-body';
    // Aman dari XSS: gunakan textContent
    if (title) {
      const strong = document.createElement('strong');
      strong.className = 'me-2';
      strong.textContent = title;
      body.appendChild(strong);
    }
    const span = document.createElement('span');
    span.textContent = message ?? '';
    body.appendChild(span);

    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = `btn-close ${variant === 'light' ? '' : 'btn-close-white'} me-2 m-auto`;
    closeBtn.setAttribute('data-bs-dismiss', 'toast');
    closeBtn.setAttribute('aria-label', 'Close');

    wrap.appendChild(body);
    wrap.appendChild(closeBtn);
    el.appendChild(wrap);

    const t = bootstrap.Toast.getOrCreateInstance(el, { delay, autohide });
    // Cleanup saat selesai
    el.addEventListener('hidden.bs.toast', () => el.remove(), { once: true });
    return { el, instance: t };
  }

  function show(a, b, c) {
    const cfg = normalizeInput(a, b, c);
    const area = ensureArea();
    clampStack(area);

    const { el, instance } = buildToast(cfg);
    area.appendChild(el);
    try { instance.show(); } catch (_) { /* ignore if bootstrap not ready */ }
    return el;
  }

  function clear() {
    const area = document.getElementById('dp-toast-area');
    if (!area) return;
    area.querySelectorAll('.toast').forEach(el => {
      try { bootstrap.Toast.getOrCreateInstance(el).hide(); } catch (_) {}
      el.remove();
    });
  }

  function setMax(n) {
    if (typeof n === 'number' && n >= 1 && n <= 10) STATE.max = n | 0;
  }

  DP.core.toast = { show, clear, setMax };
})();
