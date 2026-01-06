/*
# =====================================================================
# 6. FRONTEND EXPORT MANAGER (ExportManager.js)
# =====================================================================

*/
// detail_project/static/detail_project/js/export/ExportManager.js


/**
 * ExportManager - Reusable Export Handler
 * Handles CSV, PDF, and Word exports via backend API
 *
 * Usage:
 *   const exporter = new ExportManager(projectId, 'rekap-rab');
 *   await exporter.exportAs('csv');
 *
 * With modal loading:
 *   const exporter = new ExportManager(projectId, 'rekap-rab', { modalId: 'myExportModal' });
 *   await exporter.exportAs('csv');
 */
class ExportManager {
  constructor(projectId, pageType, options = {}) {
    this.projectId = projectId;
    this.pageType = pageType;
    this.baseUrl = `/detail_project/api/project/${projectId}/export/${pageType}/`;

    // Modal loading support
    this.modalId = options.modalId || null;
    this.modalInstance = null;
    this.modalLabelEl = null;
    this.modalTextEl = null;
    this._modalTimeout = null;  // Safety timeout to prevent stuck modal

    console.log(`[ExportManager] Initialized for project ${projectId}, page: ${pageType}`);

    if (this.modalId) {
      this._initModal();
    }
  }

  /**
   * Initialize modal loading elements
   * @private
   */
  _initModal() {
    const modalEl = document.getElementById(this.modalId);
    if (!modalEl) {
      console.warn(`[ExportManager] Modal element #${this.modalId} not found`);
      return;
    }

    // Try to find label and text elements (common patterns)
    const modalIdPrefix = this.modalId.replace(/Modal$/, '');
    this.modalLabelEl = document.getElementById(`${modalIdPrefix}Label`) ||
                        document.getElementById(`${modalIdPrefix}LoadingLabel`);
    this.modalTextEl = document.getElementById(`${modalIdPrefix}Text`) ||
                       document.getElementById(`${modalIdPrefix}LoadingText`);

    console.log(`[ExportManager] Modal initialized: #${this.modalId}`);
  }

  /**
   * Export data in specified format
   * @param {string} format - 'csv', 'pdf', 'word', or 'xlsx'
   * @param {object} options - Optional export options (e.g., { parameters: {...} })
   * @returns {Promise<void>}
   */
  async exportAs(format, options = {}) {
    let url = `${this.baseUrl}${format}/`;

    const attachments = options.attachments || [];

    // Append parameters if provided (for volume_pekerjaan)
    if (options.parameters && Object.keys(options.parameters).length > 0) {
      const paramsJson = JSON.stringify(options.parameters);
      const separator = url.includes('?') ? '&' : '?';
      url += `${separator}params=${encodeURIComponent(paramsJson)}`;
      console.log(`[ExportManager] Including parameters:`, options.parameters);
    }

    // Optional orientation override (for pages that support it)
    try {
      const raw = options.orientation || (this.pageType === 'rincian-ahsp' ? localStorage.getItem('rincian_ahsp_export_orientation') : null);
      const ori = (raw || '').toLowerCase();
      if (ori === 'portrait' || ori === 'landscape') {
        const separator = url.includes('?') ? '&' : '?';
        url += `${separator}orientation=${encodeURIComponent(ori)}`;
        console.log(`[ExportManager] Orientation: ${ori}`);
      }
    } catch (e) {
      // ignore orientation errors
    }

    if (options.query && typeof options.query === 'object') {
      const query = new URLSearchParams();
      Object.entries(options.query).forEach(([key, value]) => {
        if (value === undefined || value === null || value === '') return;
        if (Array.isArray(value)) {
          if (value.length) {
            query.append(key, value.join(','));
          }
        } else {
          query.append(key, value);
        }
      });
      const qs = query.toString();
      if (qs) {
        const separator = url.includes('?') ? '&' : '?';
        url += `${separator}${qs}`;
      }
    }

    console.log(`[ExportManager] Starting ${format.toUpperCase()} export...`);
    console.log(`[ExportManager] URL: ${url}`);

    try {
      console.log(`[ExportManager] Showing loading state...`);
      this._showLoading(format);

      const isPost = attachments.length > 0;
      const fetchOptions = {
        method: isPost ? 'POST' : 'GET',
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
      };

      if (isPost) {
        fetchOptions.headers['Content-Type'] = 'application/json';
        fetchOptions.headers['X-CSRFToken'] = this._getCsrfToken();
        fetchOptions.body = JSON.stringify({ attachments });
      }

      console.log(`[ExportManager] Fetching from server...`);
      const response = await fetch(url, fetchOptions);
      console.log(`[ExportManager] Server response received: ${response.status} ${response.statusText}`);

      if (!response.ok) {
        let errorMsg = `HTTP ${response.status}: ${response.statusText}`;
        const contentType = response.headers.get('content-type');

        if (contentType && contentType.includes('application/json')) {
          try {
            const error = await response.json();
            errorMsg = error.error || error.detail || errorMsg;
          } catch (e) {
            console.warn('[ExportManager] Could not parse error JSON');
          }
        }

        throw new Error(errorMsg);
      }

      // Download file
      console.log(`[ExportManager] Creating blob and downloading file...`);
      const blob = await response.blob();
      this._downloadBlob(blob, format, response);

      this._showSuccess(format);
      console.log(`[ExportManager] ${format.toUpperCase()} export completed successfully`);

    } catch (error) {
      console.error(`[ExportManager] ${format.toUpperCase()} export failed:`, error);
      this._showError(format, error.message);
    } finally {
      console.log(`[ExportManager] Hiding loading state...`);
      this._hideLoading(format);
      console.log(`[ExportManager] Export process finished`);
    }
  }

  /**
   * Download blob as file
   * @private
   */
  _downloadBlob(blob, format, response) {
    // Try to get filename from Content-Disposition header
    let filename = this._getFilename(format);
    const disposition = response.headers.get('Content-Disposition');

    if (disposition) {
      const filenameMatch = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1].replace(/['"]/g, '');
      }
    }

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = filename;

    document.body.appendChild(a);
    a.click();

    // Cleanup
    setTimeout(() => {
      window.URL.revokeObjectURL(url);
      if (document.body.contains(a)) {
        document.body.removeChild(a);
      }
    }, 100);
  }

  /**
   * Generate default filename
   * @private
   */
  _getFilename(format) {
    const date = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    const extensions = { csv: 'csv', pdf: 'pdf', word: 'docx', xlsx: 'xlsx', json: 'json' };
    const pageTitle = this.pageType.replace(/-/g, '_').toUpperCase();
    return `${pageTitle}_${this.projectId}_${date}.${extensions[format]}`;
  }

  /**
   * Show loading state on button and modal
   * @private
   */
  _showLoading(format) {
    // Show button loading state
    const btn = this._getButton(format);
    if (btn) {
      // Store original HTML only if not already loading
      if (!btn.dataset.originalHtml) {
        btn.dataset.originalHtml = btn.innerHTML;
      }
      btn.disabled = true;

      const spinner = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>';
      const label = format.toUpperCase();
      btn.innerHTML = `${spinner}Exporting ${label}...`;
    }

    // Show modal loading if configured
    if (this.modalId) {
      this._showModalLoading(format);
    }
  }

  /**
   * Show modal loading
   * @private
   */
  _showModalLoading(format) {
    const modalEl = document.getElementById(this.modalId);
    if (!modalEl) return;

    // Update modal text
    const formatLabel = format.toUpperCase();
    if (this.modalLabelEl) {
      this.modalLabelEl.textContent = 'Memproses Export';
    }
    if (this.modalTextEl) {
      this.modalTextEl.textContent = `Membuat file ${formatLabel}...`;
    }

    // Show modal using Bootstrap
    if (typeof bootstrap !== 'undefined') {
      this.modalInstance = bootstrap.Modal.getOrCreateInstance(modalEl);
      this.modalInstance.show();
      console.log(`[ExportManager] Modal shown for ${formatLabel} export`);
    } else {
      console.warn('[ExportManager] Bootstrap not found, cannot show modal');
    }

    // Safety timeout: Force close modal after 60 seconds
    if (this._modalTimeout) {
      clearTimeout(this._modalTimeout);
    }
    this._modalTimeout = setTimeout(() => {
      console.warn('[ExportManager] Modal timeout reached - force closing modal');
      this._forceCloseModal();
    }, 60000);  // 60 seconds
  }

  /**
   * Hide loading state on button and modal
   * @private
   */
  _hideLoading(format) {
    // Hide button loading state
    const btn = this._getButton(format);
    if (btn) {
      btn.disabled = false;

      // Restore original HTML, or use fallback
      if (btn.dataset.originalHtml) {
        btn.innerHTML = btn.dataset.originalHtml;
        delete btn.dataset.originalHtml;
      } else {
        // Fallback: reconstruct button content
        const labelMap = { csv: 'CSV', pdf: 'PDF', word: 'Word', xlsx: 'Excel', json: 'JSON' };
        const iconMap = { csv: 'file-earmark-spreadsheet', pdf: 'file-earmark-pdf', word: 'file-earmark-word', xlsx: 'file-earmark-excel', json: 'filetype-json' };
        const colorMap = { csv: 'text-success', pdf: 'text-danger', word: 'text-primary', xlsx: 'text-success', json: 'text-warning' };

        const label = labelMap[format] || format.toUpperCase();
        const icon = iconMap[format] || 'download';
        const color = colorMap[format] || '';

        btn.innerHTML = `<i class="bi bi-${icon} ${color} me-2"></i>Export ${label}`;
      }
    }

    // Hide modal loading if configured
    if (this.modalId) {
      console.log(`[ExportManager] Attempting to hide modal: ${this.modalId}, instance exists: ${!!this.modalInstance}`);
      this._hideModalLoading();
    }
  }

  /**
   * Hide modal loading
   * @private
   */
  _hideModalLoading() {
    // Clear safety timeout
    if (this._modalTimeout) {
      clearTimeout(this._modalTimeout);
      this._modalTimeout = null;
    }

    let modalClosed = false;

    // Try method 1: Use stored modalInstance
    if (this.modalInstance) {
      try {
        console.log('[ExportManager] Hiding modal using stored instance');
        this.modalInstance.hide();
        this.modalInstance = null;
        modalClosed = true;
        console.log('[ExportManager] Modal closed successfully via instance');
      } catch (e) {
        console.error('[ExportManager] Error hiding modal via instance:', e);
      }
    }

    // Try method 2: Get fresh instance and hide
    if (!modalClosed && this.modalId) {
      try {
        const modalEl = document.getElementById(this.modalId);
        if (modalEl && typeof bootstrap !== 'undefined') {
          console.log('[ExportManager] Hiding modal using fresh getInstance');
          const freshInstance = bootstrap.Modal.getInstance(modalEl);
          if (freshInstance) {
            freshInstance.hide();
            this.modalInstance = null;
            modalClosed = true;
            console.log('[ExportManager] Modal closed successfully via fresh instance');
          }
        }
      } catch (e) {
        console.error('[ExportManager] Error hiding modal via fresh instance:', e);
      }
    }

    // Try method 3: Force close with DOM manipulation
    if (!modalClosed) {
      console.warn('[ExportManager] Bootstrap hide failed, using force close');
      this._forceCloseModal();
      modalClosed = true;
    }

    // CRITICAL: Always cleanup backdrop and body styles, regardless of which method succeeded
    // This ensures no leftover backdrop even if Bootstrap hide() was called
    setTimeout(() => {
      this._cleanupModalBackdrop();
    }, 300);  // Wait for Bootstrap animation to finish
  }

  /**
   * Cleanup modal backdrop and body styles (always safe to call)
   * @private
   */
  _cleanupModalBackdrop() {
    try {
      // CRITICAL: Close the modal element itself
      const modalEl = document.getElementById(this.modalId);
      if (modalEl) {
        // Remove Bootstrap show class and hide modal
        const wasVisible = modalEl.classList.contains('show');
        modalEl.classList.remove('show');
        modalEl.style.display = 'none';
        modalEl.setAttribute('aria-hidden', 'true');
        modalEl.removeAttribute('aria-modal');
        modalEl.removeAttribute('role');

        if (wasVisible) {
          console.log('[ExportManager] Modal element closed');
        }
      }

      // Remove all modal backdrops (in case multiple exist)
      const backdrops = document.querySelectorAll('.modal-backdrop');
      if (backdrops.length > 0) {
        console.log(`[ExportManager] Cleaning up ${backdrops.length} backdrop(s)`);
        backdrops.forEach(backdrop => backdrop.remove());
      }

      // Remove body modal styles
      if (document.body.classList.contains('modal-open')) {
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
        console.log('[ExportManager] Body modal styles cleaned up');
      }

      // Reset instance
      this.modalInstance = null;
    } catch (e) {
      console.error('[ExportManager] Error cleaning up backdrop:', e);
    }
  }

  /**
   * Force close modal using DOM manipulation (fallback)
   * @private
   */
  _forceCloseModal() {
    try {
      const modalEl = document.getElementById(this.modalId);
      if (modalEl) {
        // Remove Bootstrap classes
        modalEl.classList.remove('show');
        modalEl.style.display = 'none';
        modalEl.setAttribute('aria-hidden', 'true');
        modalEl.removeAttribute('aria-modal');
        modalEl.removeAttribute('role');

        // Remove backdrop
        const backdrop = document.querySelector('.modal-backdrop');
        if (backdrop) {
          backdrop.remove();
        }

        // Remove body styles
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';

        console.log('[ExportManager] Modal force-closed using DOM manipulation');
      }

      // Reset instance
      this.modalInstance = null;
    } catch (e) {
      console.error('[ExportManager] Error in force close modal:', e);
    }
  }

  /**
   * Show success message
   * @private
   */
  _showSuccess(format) {
    const message = `Export ${format.toUpperCase()} berhasil! File sedang diunduh...`;
    this._toast(message, 'success');
  }

  /**
   * Show error message
   * @private
   */
  _showError(format, message) {
    const msg = `Export ${format.toUpperCase()} gagal: ${message}`;
    this._toast(msg, 'danger');
  }

  _getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  }

  /**
   * Show toast notification
   * @private
   */
  _toast(message, type = 'info') {
    // Check for existing toast system
    if (window.TOAST) {
      if (type === 'success') {
        window.TOAST.ok(message);
      } else if (type === 'danger' || type === 'error') {
        window.TOAST.err(message);
      } else {
        window.TOAST.info && window.TOAST.info(message);
      }
    } else {
      // Fallback: create simple toast
      this._showSimpleToast(message, type);
    }
  }

  /**
   * Simple toast fallback (if no toast system available)
   * @private
   */
  _showSimpleToast(message, type) {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'danger' ? 'danger' : type === 'success' ? 'success' : 'info'} position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);';
    toast.textContent = message;
    toast.role = 'alert';

    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s';
      setTimeout(() => {
        if (document.body.contains(toast)) {
          document.body.removeChild(toast);
        }
      }, 300);
    }, 3000);
  }

  /**
   * Get export button element
   * @private
   */
  _getButton(format) {
    const map = {
      csv: 'btn-export-csv',
      pdf: 'btn-export-pdf',
      word: 'btn-export-word',
      xlsx: 'btn-export-xlsx',
      json: 'btn-export-json',
    };
    const id = map[format] || `btn-export-${format}`;
    return document.getElementById(id);
  }
}

// Make available globally
window.ExportManager = ExportManager;
console.log('[ExportManager] Class loaded and available globally');
