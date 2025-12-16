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
 */
class ExportManager {
  constructor(projectId, pageType) {
    this.projectId = projectId;
    this.pageType = pageType;
    this.baseUrl = `/detail_project/api/project/${projectId}/export/${pageType}/`;
    
    console.log(`[ExportManager] Initialized for project ${projectId}, page: ${pageType}`);
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

    try {
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

      const response = await fetch(url, fetchOptions);
      
      if (!response.ok) {
        let errorMsg = `HTTP ${response.status}: ${response.statusText}`;
        const contentType = response.headers.get('content-type');
        
        if (contentType && contentType.includes('application/json')) {
          try {
            const error = await response.json();
            errorMsg = error.error || error.detail || errorMsg;
          } catch(e) {
            console.warn('[ExportManager] Could not parse error JSON');
          }
        }
        
        throw new Error(errorMsg);
      }
      
      // Download file
      const blob = await response.blob();
      this._downloadBlob(blob, format, response);
      
      this._showSuccess(format);
      console.log(`[ExportManager] ${format.toUpperCase()} export completed`);
      
    } catch (error) {
      console.error(`[ExportManager] ${format.toUpperCase()} export failed:`, error);
      this._showError(format, error.message);
    } finally {
      this._hideLoading(format);
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
    const extensions = { csv: 'csv', pdf: 'pdf', word: 'docx', xlsx: 'xlsx' };
    const pageTitle = this.pageType.replace(/-/g, '_').toUpperCase();
    return `${pageTitle}_${this.projectId}_${date}.${extensions[format]}`;
  }
  
  /**
   * Show loading state on button
   * @private
   */
  _showLoading(format) {
    const btn = this._getButton(format);
    if (!btn) return;
    
    btn.disabled = true;
    btn.dataset.originalHtml = btn.innerHTML;
    
    const spinner = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>';
    const label = format.toUpperCase();
    btn.innerHTML = `${spinner}Exporting ${label}...`;
  }
  
  /**
   * Hide loading state on button
   * @private
   */
  _hideLoading(format) {
    const btn = this._getButton(format);
    if (!btn || !btn.dataset.originalHtml) return;
    
    btn.disabled = false;
    btn.innerHTML = btn.dataset.originalHtml;
    delete btn.dataset.originalHtml;
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
    };
    const id = map[format] || `btn-export-${format}`;
    return document.getElementById(id);
  }
}

// Make available globally
window.ExportManager = ExportManager;
console.log('[ExportManager] Class loaded and available globally');
