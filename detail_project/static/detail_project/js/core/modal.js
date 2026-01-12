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
        },
        { once: true },
      );

      if (window.bootstrap) {
        modalInstance = window.bootstrap.Modal.getOrCreateInstance(modalEl);
        modalInstance.show();
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

  DP.core.modal = { show, confirm, alert };
  DP.modal = DP.core.modal;
})();
