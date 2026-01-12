/**
 * Unified Global Toast Notification System
 * 
 * Features:
 * - Easy-to-use API: DP.toast.success(), DP.toast.error(), etc.
 * - CRUD presets: DP.toast.crud.created(), DP.toast.crud.updated(), etc.
 * - Export presets: DP.toast.export.started(), DP.toast.export.success(), etc.
 * - Network presets: DP.toast.network.offline(), etc.
 * - Premium styling with dark mode support
 * - Max 3 visible toasts with stacking
 * - Auto-dismiss with configurable duration
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

  // ===== CLAMP VISIBLE TOASTS =====
  function clampToasts() {
    const area = ensureToastArea();
    const toasts = area.querySelectorAll('.dp-toast');
    const excess = toasts.length - CONFIG.maxVisible;

    for (let i = 0; i < excess; i++) {
      const toast = toasts[i];
      removeToast(toast);
    }
  }

  // ===== CREATE TOAST ELEMENT =====
  function createToast(options) {
    const {
      message = '',
      title = '',
      type = 'info',
      duration = CONFIG.defaultDuration,
      closable = true,
      icon = null,
    } = options;

    const toast = document.createElement('div');
    toast.className = `dp-toast dp-toast-${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-atomic', 'true');

    // Icon
    const iconClass = icon || ICONS[type] || ICONS.info;
    const iconHtml = `<span class="dp-toast-icon"><i class="bi ${iconClass}"></i></span>`;

    // Content
    let contentHtml = '';
    if (title) {
      contentHtml += `<div class="dp-toast-title">${escapeHtml(title)}</div>`;
    }
    contentHtml += `<div class="dp-toast-message">${escapeHtml(message)}</div>`;

    // Close button
    const closeHtml = closable
      ? `<button type="button" class="dp-toast-close" aria-label="Close"><i class="bi bi-x"></i></button>`
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

    // Auto-dismiss
    if (duration > 0 && type !== 'loading') {
      setTimeout(() => removeToast(toast), duration);
    }

    return toast;
  }

  // ===== REMOVE TOAST =====
  function removeToast(toast) {
    if (!toast || !toast.parentNode) return;

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
  function show(options) {
    // Handle simple string call: show('message', 'success', 3000)
    if (typeof options === 'string') {
      options = {
        message: options,
        type: arguments[1] || 'info',
        duration: arguments[2] || CONFIG.defaultDuration,
      };
    }

    const area = ensureToastArea();
    clampToasts();

    const toast = createToast(options);
    area.appendChild(toast);

    // Trigger animation
    requestAnimationFrame(() => {
      toast.classList.add('dp-toast-show');
    });

    return toast;
  }

  // ===== SHORTCUT METHODS =====
  function success(message, duration) {
    return show({ message, type: 'success', duration: duration || 3000 });
  }

  function error(message, duration) {
    return show({ message, type: 'error', duration: duration || 5000 });
  }

  function warning(message, duration) {
    return show({ message, type: 'warning', duration: duration || 4000 });
  }

  function info(message, duration) {
    return show({ message, type: 'info', duration: duration || 3000 });
  }

  function loading(message) {
    return show({ message: message || 'Memuat...', type: 'loading', duration: 0, closable: false });
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
      return show({ message, type: type || 'info', duration: duration || 3000 });
    };
  }

  console.log('[Toast] Unified Global Toast System initialized');
})();
