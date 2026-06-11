// /static/detail_project/js/core/modal.js
// Simple Bootstrap modal helper for confirm/alert dialogs (no native browser popups).
(() => {
  'use strict';

  const DP = (window.DP = window.DP || {});
  DP.core = DP.core || {};

  if (DP.core.modal) return;

  const MODAL_ID = 'dp-core-modal';
  const TITLE_ID = 'dp-core-modal-title';
  const BODY_ID = 'dp-core-modal-body';

  let modalInstance = null;
  let pendingResolve = null;

  function isVolumePageNoBackdropMode() {
    return String(document.body?.dataset?.page || '') === 'volume_pekerjaan';
  }

  /** Remove orphan backdrops when more exist than open modals */
  function cleanupOrphanBackdrops() {
    const doCleanup = () => {
      const openModals = document.querySelectorAll('.modal.show');
      const backdrops = document.querySelectorAll('.modal-backdrop');
      const noBackdrop = isVolumePageNoBackdropMode();
      if (noBackdrop && backdrops.length) {
        backdrops.forEach((bd) => bd.remove());
      }
      const expected = openModals.length;
      if (!noBackdrop && backdrops.length > expected) {
        for (let i = backdrops.length - 1; i >= expected; i--) {
          backdrops[i].remove();
        }
      }
      if (expected === 0) {
        document.body.classList.remove('modal-open');
        document.body.style.removeProperty('overflow');
        document.body.style.removeProperty('padding-right');
      }
    };
    // Run at multiple intervals to catch Bootstrap's async backdrop removal
    setTimeout(doCleanup, 50);
    setTimeout(doCleanup, 300);
    setTimeout(doCleanup, 600);
  }

  // Global listener: clean up orphan backdrops whenever ANY modal closes
  document.addEventListener('hidden.bs.modal', () => {
    cleanupOrphanBackdrops();
  });

  function ensureModal() {
    let modalEl = document.getElementById(MODAL_ID);
    if (modalEl) return modalEl;

    const wrapper = document.createElement('div');
    wrapper.innerHTML = `
      <div class="modal fade" id="${MODAL_ID}" tabindex="-1" aria-labelledby="${TITLE_ID}" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title" id="${TITLE_ID}">Konfirmasi</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Tutup"></button>
            </div>
            <div class="modal-body" id="${BODY_ID}"></div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" data-dp-cancel data-bs-dismiss="modal">Batal</button>
              <button type="button" class="btn btn-primary" data-dp-confirm>OK</button>
            </div>
          </div>
        </div>
      </div>
    `.trim();

    modalEl = wrapper.firstElementChild;
    document.body.appendChild(modalEl);
    return modalEl;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatMessage(message) {
    const raw = Array.isArray(message) ? message.join('\n') : String(message || '');
    return escapeHtml(raw).replace(/\n/g, '<br>');
  }

  function show(options = {}) {
    const modalEl = ensureModal();
    const titleEl = modalEl.querySelector(`#${TITLE_ID}`);
    const bodyEl = modalEl.querySelector(`#${BODY_ID}`);
    const confirmBtn = modalEl.querySelector('[data-dp-confirm]');
    const cancelBtn = modalEl.querySelector('[data-dp-cancel]');
    const headerEl = modalEl.querySelector('.modal-header');

    const {
      title = 'Konfirmasi',
      message = '',
      confirmText = 'OK',
      cancelText = 'Batal',
      showCancel = true,
      confirmClass = null,
      cancelClass = null,
      headerClass = '',
      resolveOnClose = null,
    } = options;

    if (titleEl) titleEl.textContent = title;
    if (bodyEl) bodyEl.innerHTML = formatMessage(message);
    if (confirmBtn) confirmBtn.textContent = confirmText;
    if (cancelBtn) cancelBtn.textContent = cancelText;
    if (cancelBtn) cancelBtn.classList.toggle('d-none', !showCancel);

    if (confirmBtn) {
      confirmBtn.className = confirmClass || 'btn btn-primary';
    }
    if (cancelBtn) {
      cancelBtn.className = cancelClass || 'btn btn-secondary';
    }

    if (headerEl) {
      headerEl.className = 'modal-header';
      if (headerClass) headerEl.classList.add(...headerClass.split(' '));
    }

    if (pendingResolve) {
      pendingResolve(false);
      pendingResolve = null;
    }

    return new Promise((resolve) => {
      pendingResolve = resolve;
      let confirmed = false;
      const resolveWhenHidden = resolveOnClose !== null ? resolveOnClose : !showCancel;

      if (confirmBtn) {
        confirmBtn.onclick = () => {
          confirmed = true;
          if (pendingResolve) {
            pendingResolve(true);
            pendingResolve = null;
          }
          modalInstance?.hide();
        };
      }

      if (cancelBtn) {
        cancelBtn.onclick = () => {
          confirmed = false;
        };
      }

      modalEl.addEventListener(
        'hidden.bs.modal',
        () => {
          if (pendingResolve) {
            pendingResolve(confirmed || resolveWhenHidden);
            pendingResolve = null;
          }
          // Clean up orphan backdrops from stacked modal scenario
          cleanupOrphanBackdrops();
        },
        { once: true },
      );

      if (window.bootstrap) {
        const noBackdrop = isVolumePageNoBackdropMode();
        modalEl.setAttribute('data-bs-backdrop', noBackdrop ? 'false' : 'true');
        modalInstance = window.bootstrap.Modal.getOrCreateInstance(modalEl, {
          backdrop: noBackdrop ? false : true,
        });
        if (modalInstance?._config) {
          modalInstance._config.backdrop = noBackdrop ? false : true;
        }
        // Boost z-index if another modal is already open (e.g. formula editor)
        const otherOpen = document.querySelector('.modal.show:not(#' + MODAL_ID + ')');
        if (otherOpen) {
          const otherZ = parseInt(getComputedStyle(otherOpen).zIndex, 10) || 1050;
          modalEl.style.zIndex = String(otherZ + 5);
          // Boost backdrop after it's added to DOM
          modalEl.addEventListener('shown.bs.modal', () => {
            const backdrops = document.querySelectorAll('.modal-backdrop');
            if (backdrops.length > 0) {
              backdrops[backdrops.length - 1].style.zIndex = String(otherZ + 4);
            }
          }, { once: true });
        }
        modalInstance.show();
        if (noBackdrop) {
          setTimeout(cleanupOrphanBackdrops, 0);
        }
      } else {
        if (pendingResolve) {
          pendingResolve(false);
          pendingResolve = null;
        }
      }
    });
  }

  function confirm(message, options = {}) {
    return show({
      ...options,
      message,
      showCancel: true,
      resolveOnClose: false,
    });
  }

  function alert(message, options = {}) {
    return show({
      ...options,
      message,
      showCancel: false,
      confirmText: options.confirmText || 'OK',
      resolveOnClose: true,
    });
  }

  // U17 (UAT 2026-06-10): saat modal Bootstrap mana pun mulai ditutup dengan
  // fokus masih di dalamnya, Bootstrap memberi aria-hidden pada elemen yang
  // memuat fokus -> browser memunculkan warning "Blocked aria-hidden".
  // Lepaskan fokus lebih dulu; berlaku global untuk semua modal.
  document.addEventListener('hide.bs.modal', function (event) {
    const active = document.activeElement;
    if (active && event.target.contains(active) && typeof active.blur === 'function') {
      active.blur();
    }
  });

  DP.core.modal = { show, confirm, alert };
  DP.modal = DP.core.modal;
})();
