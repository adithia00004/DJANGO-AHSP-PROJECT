/**
 * Unified Global Toast Notification System
 *
 * KONTRAK (T-1, docs/RENCANA_PERAPIAN_PROYEK_20261001.md §5.2):
 * - Bentuk pemanggilan yang didukung:
 *     DP.toast.show({message, type, duration, title, closable, icon})
 *     DP.toast.show(message, type, durationOrOptions)
 *     DP.toast.success|error|warning|info|danger|warn(message, durationOrOptions)
 *     DP.core.toast.show(...), window.showToast(message, type, durationOrOptions)
 *   durationOrOptions = angka ms ATAU objek {duration}. (Dulu objek {duration,
 *   position} terbaca sebagai durasi tak valid -> toast tidak pernah hilang.)
 * - Jenis: success, info, warning, error, loading. Alias: danger->error,
 *   warn->warning. Jenis tak dikenal -> info.
 * - Durasi: sukses/info 3 dtk, peringatan 5 dtk, error 6 dtk (+ tombol tutup).
 *   Angka > 0 dipakai (maks 60 dtk). 0/negatif/NaN/bukan angka -> default
 *   jenisnya: TIDAK ADA toast biasa yang menetap (keluhan owner 2026-10-01).
 * - loading menetap sampai DP.toast.dismiss(handle); batas aman 60 dtk.
 * - Deduplikasi: toast jenis+judul+pesan sama yang masih tampil tidak
 *   digandakan; timernya diulang dan diberi penanda "x2", "x3" (textContent).
 *   loading tidak dideduplikasi (tiap operasi punya handle sendiri).
 * - Maks 3 toast tampil TERMASUK yang baru; yang tertua (non-loading dulu)
 *   digusur.
 * - Setiap pemanggilan mengembalikan elemen toast sebagai handle.
 *
 * @module DP.toast
 */

(() => {
  'use strict';

  const DP = (window.DP = window.DP || {});

  // Prevent double initialization
  if (DP.toast && DP.toast._initialized) return;

  // ===== CONFIGURATION =====
  const CONFIG = {
    maxVisible: 3,
    defaultDuration: 3000,
    position: 'top-right', // top-right, top-center, bottom-right
    zIndex: 13100,
  };

  const DEFAULT_DURATION = { success: 3000, info: 3000, warning: 5000, error: 6000 };
  const TYPE_ALIASES = { danger: 'error', warn: 'warning' };
  const MAX_DURATION = 60000;
  const LOADING_SAFETY_MS = 60000;

  // ===== ICONS =====
  const ICONS = {
    success: 'bi-check-circle-fill',
    error: 'bi-x-circle-fill',
    warning: 'bi-exclamation-triangle-fill',
    info: 'bi-info-circle-fill',
    loading: 'bi-arrow-repeat',
  };

  const EMOJIS = {
    success: '✅',
    error: '❌',
    warning: '⚠️',
    info: 'ℹ️',
    loading: '🔄',
    export: '📄',
    download: '⬇️',
    network: '📵',
    networkOk: '🌐',
  };

  // ===== STATE =====
  let toastArea = null;
  const active = new Map(); // dedupe key -> toast element

  // ===== SETUP TOAST AREA =====
  function ensureToastArea() {
    if (toastArea && document.body.contains(toastArea)) return toastArea;

    toastArea = document.createElement('div');
    toastArea.id = 'dp-toast-area';
    toastArea.className = 'dp-toast-area dp-toast-' + CONFIG.position;
    toastArea.style.zIndex = CONFIG.zIndex;
    toastArea.setAttribute('role', 'region');
    toastArea.setAttribute('aria-label', 'Notifications');
    toastArea.setAttribute('aria-live', 'polite');
    document.body.appendChild(toastArea);

    return toastArea;
  }

  // ===== NORMALISASI =====
  function normalizeType(type) {
    let t = String(type || 'info').toLowerCase();
    t = TYPE_ALIASES[t] || t;
    if (!ICONS[t]) {
      if (window.console) console.warn('[DP.toast] jenis tidak dikenal:', type);
      t = 'info';
    }
    return t;
  }

  function resolveDuration(type, raw) {
    if (type === 'loading') return 0;
    const value = raw && typeof raw === 'object' ? raw.duration : raw;
    if (typeof value !== 'number' || !Number.isFinite(value) || value <= 0) {
      return DEFAULT_DURATION[type] || CONFIG.defaultDuration;
    }
    return Math.min(value, MAX_DURATION);
  }

  function normalizeOptions(options, typeArg, durationArg) {
    let opts;
    if (options && typeof options === 'object') {
      opts = Object.assign({}, options);
    } else {
      opts = { message: options, type: typeArg, duration: durationArg };
      if (durationArg && typeof durationArg === 'object') {
        // show(message, type, {duration, title, closable, icon})
        opts = Object.assign({}, durationArg, opts, { duration: durationArg.duration });
      }
    }
    const type = normalizeType(opts.type);
    let closable = opts.closable !== false;
    if (type === 'error') closable = true;
    if (type === 'loading') closable = opts.closable === true;
    return {
      message: opts.message == null ? '' : String(opts.message),
      title: opts.title ? String(opts.title) : '',
      type,
      duration: resolveDuration(type, opts.duration),
      closable,
      icon: opts.icon || null,
    };
  }

  // ===== TIMER =====
  function schedule(toast, duration) {
    clearTimeout(toast._dpTimer);
    const delay = toast._dpType === 'loading' ? LOADING_SAFETY_MS : duration;
    if (delay > 0) {
      toast._dpTimer = setTimeout(() => removeToast(toast), delay);
    }
  }

  // ===== CLAMP VISIBLE TOASTS (sesudah toast baru masuk) =====
  function clampToasts(area) {
    const visible = Array.from(area.querySelectorAll('.dp-toast:not(.dp-toast-hide)'));
    let excess = visible.length - CONFIG.maxVisible;
    if (excess <= 0) return;
    const ordered = visible
      .filter((t) => t._dpType !== 'loading')
      .concat(visible.filter((t) => t._dpType === 'loading'));
    for (const toast of ordered) {
      if (excess <= 0) break;
      removeToast(toast);
      excess -= 1;
    }
  }

  // ===== CREATE TOAST ELEMENT =====
  function createToast(opts) {
    const { message, title, type, closable, icon } = opts;

    const toast = document.createElement('div');
    toast.className = `dp-toast dp-toast-${type}`;
    toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
    toast.setAttribute('aria-atomic', 'true');
    toast._dpType = type;
    toast._dpCount = 1;

    // Icon
    const iconClass = icon || ICONS[type] || ICONS.info;
    const iconHtml = `<span class="dp-toast-icon"><i class="bi ${iconClass}"></i></span>`;

    // Content
    let contentHtml = '';
    if (title) {
      contentHtml += `<div class="dp-toast-title">${escapeHtml(title)}</div>`;
    }
    contentHtml += `<div class="dp-toast-message">${escapeHtml(message)}<span class="dp-toast-count" hidden></span></div>`;

    // Close button
    const closeHtml = closable
      ? `<button type="button" class="dp-toast-close" aria-label="Tutup"><i class="bi bi-x"></i></button>`
      : '';

    toast.innerHTML = `
      ${iconHtml}
      <div class="dp-toast-content">${contentHtml}</div>
      ${closeHtml}
    `;

    // Add loading animation for loading type
    if (type === 'loading') {
      const iconEl = toast.querySelector('.dp-toast-icon i');
      if (iconEl) iconEl.classList.add('dp-spin');
    }

    // Close button event
    const closeBtn = toast.querySelector('.dp-toast-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => removeToast(toast));
    }

    return toast;
  }

  // ===== REMOVE TOAST =====
  function removeToast(toast) {
    if (!toast || !toast.parentNode) return;
    clearTimeout(toast._dpTimer);
    if (toast._dpKey && active.get(toast._dpKey) === toast) {
      active.delete(toast._dpKey);
    }
    if (toast.classList.contains('dp-toast-hide')) return;

    toast.classList.add('dp-toast-hide');
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 300);
  }

  // ===== UTILITY =====
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // ===== MAIN SHOW FUNCTION =====
  function show(options, typeArg, durationArg) {
    const opts = normalizeOptions(options, typeArg, durationArg);
    const area = ensureToastArea();

    // Deduplikasi: pesan sama yang masih tampil -> perpanjang + penanda xN.
    const key = opts.type === 'loading' ? null : `${opts.type}|${opts.title}|${opts.message}`;
    const existing = key ? active.get(key) : null;
    if (existing && existing.parentNode && !existing.classList.contains('dp-toast-hide')) {
      existing._dpCount += 1;
      const badge = existing.querySelector('.dp-toast-count');
      if (badge) {
        badge.textContent = ` ×${existing._dpCount}`;
        badge.hidden = false;
      }
      schedule(existing, opts.duration);
      return existing;
    }

    const toast = createToast(opts);
    if (key) {
      toast._dpKey = key;
      active.set(key, toast);
    }
    area.appendChild(toast);
    schedule(toast, opts.duration);
    clampToasts(area);

    // Trigger animation
    requestAnimationFrame(() => {
      toast.classList.add('dp-toast-show');
    });

    return toast;
  }

  // ===== SHORTCUT METHODS =====
  function success(message, duration) {
    return show(message, 'success', duration);
  }

  function error(message, duration) {
    return show(message, 'error', duration);
  }

  function warning(message, duration) {
    return show(message, 'warning', duration);
  }

  function info(message, duration) {
    return show(message, 'info', duration);
  }

  function loading(message) {
    return show({ message: message || 'Memuat...', type: 'loading' });
  }

  // ===== CRUD PRESETS =====
  const crud = {
    created(entity) {
      return success(`${EMOJIS.success} ${entity} berhasil dibuat`);
    },
    updated(entity) {
      return success(`${EMOJIS.success} ${entity} berhasil diperbarui`);
    },
    deleted(entity) {
      return success(`${EMOJIS.success} ${entity} berhasil dihapus`);
    },
    saved(entity) {
      return success(`${EMOJIS.success} ${entity || 'Data'} berhasil disimpan`);
    },
    saveFailed(reason) {
      return error(`${EMOJIS.error} Gagal menyimpan${reason ? ': ' + reason : '. Silakan coba lagi.'}`);
    },
    loadFailed(reason) {
      return error(`${EMOJIS.error} Gagal memuat data${reason ? ': ' + reason : ''}`);
    },
    deleteFailed(reason) {
      return error(`${EMOJIS.error} Gagal menghapus${reason ? ': ' + reason : ''}`);
    },
    noChanges() {
      return info(`${EMOJIS.info} Tidak ada perubahan untuk disimpan`);
    },
    validationError(message) {
      return warning(`${EMOJIS.warning} ${message || 'Periksa input Anda'}`);
    },
  };

  // ===== EXPORT PRESETS =====
  const exportToast = {
    started(format) {
      return show({
        message: `${EMOJIS.export} Memproses export ${format || 'file'}...`,
        type: 'loading',
        duration: 0,
        closable: false,
      });
    },
    success(format) {
      return success(`${EMOJIS.success} Export ${format || 'file'} berhasil`);
    },
    failed(format, reason) {
      return error(`${EMOJIS.error} Export ${format || 'file'} gagal${reason ? ': ' + reason : ''}`);
    },
    downloading() {
      return info(`${EMOJIS.download} Mengunduh file...`);
    },
  };

  // ===== NETWORK PRESETS =====
  const network = {
    offline() {
      return warning(`${EMOJIS.network} Koneksi terputus. Beberapa fitur mungkin tidak tersedia.`, 5000);
    },
    online() {
      return success(`${EMOJIS.networkOk} Koneksi tersambung kembali`, 3000);
    },
    timeout() {
      return error(`⏱️ Request timeout. Silakan coba lagi.`, 5000);
    },
    error(message) {
      return error(`${EMOJIS.error} ${message || 'Terjadi kesalahan jaringan'}`, 5000);
    },
  };

  // ===== CLEAR ALL =====
  function clear() {
    const area = document.getElementById('dp-toast-area');
    if (!area) return;

    area.querySelectorAll('.dp-toast').forEach(toast => {
      removeToast(toast);
    });
  }

  // ===== DISMISS SPECIFIC TOAST =====
  function dismiss(toast) {
    removeToast(toast);
  }

  // ===== PUBLIC API =====
  DP.toast = {
    // Core
    show,
    clear,
    dismiss,

    // Shortcuts
    success,
    error,
    warning,
    info,
    loading,
    // Alias agar wrapper dinamis DP.toast[type] ikut benar (T-F5).
    danger: error,
    warn: warning,

    // Presets
    crud,
    export: exportToast,
    network,

    // Config
    config: CONFIG,

    // Flag
    _initialized: true,
  };

  // ===== BACKWARD COMPATIBILITY =====
  // Keep DP.core.toast for backward compatibility
  DP.core = DP.core || {};
  DP.core.toast = {
    show: show,
    clear: clear,
    setMax: (n) => {
      if (typeof n === 'number' && n >= 1 && n <= 10) {
        CONFIG.maxVisible = n;
      }
    },
  };

  // ===== GLOBAL ALIAS =====
  // Allow window.showToast for easy migration
  if (typeof window.showToast === 'undefined') {
    window.showToast = function (message, type, duration) {
      return show(message, type, duration);
    };
  }

})();
