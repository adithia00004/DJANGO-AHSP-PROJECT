/**
 * UI Integration Layer
 * Connects old ExportManager interface with new Export Offscreen System
 *
 * This module provides backward compatibility while using the new
 * offscreen rendering system under the hood.
 *
 * @module export/ui-integration
 */

import { exportReport, EXPORT_CONFIG } from './export-coordinator.js';
import { generateRekapReport } from './reports/rekap-report.js';
import { generateMonthlyReport } from './reports/monthly-report.js';
import { generateWeeklyReport } from './reports/weekly-report.js';

/**
 * Export Manager with New System Integration
 * Drop-in replacement for old ExportManager class
 */
export class ExportManagerNew {
  constructor(projectId, pageType) {
    this.projectId = projectId;
    this.pageType = pageType;
    this.baseUrl = `/detail_project/api/project/${projectId}/export/${pageType}/`;

    console.log(`[ExportManagerNew] Initialized for project ${projectId}, page: ${pageType}`);
    console.log(`[ExportManagerNew] Using NEW Export Offscreen Rendering System`);
  }

  /**
   * Export data using new offscreen rendering system
   * @param {string} format - 'json', 'pdf', 'word', or 'xlsx'
   * @param {object} options - Export options
   * @returns {Promise<void>}
   */
  async exportAs(format, options = {}) {
    console.log(`[ExportManagerNew] Starting ${format.toUpperCase()} export with NEW SYSTEM...`);

    try {
      this._showLoading(format);

      // Check if this is Jadwal Pekerjaan page
      if (this.pageType === 'jadwal-pekerjaan' || this.pageType === 'kelola-tahapan') {
        await this._exportJadwalPekerjaan(format, options);
      } else {
        // Fall back to old system for other pages
        await this._exportViaOldSystem(format, options);
      }

    } catch (error) {
      console.error(`[ExportManagerNew] Export failed:`, error);
      this._showError(format, error);
    } finally {
      this._hideLoading();
    }
  }

  /**
   * Export Jadwal Pekerjaan using new offscreen system
   */
  async _exportJadwalPekerjaan(format, options = {}) {
    console.log('[ExportManagerNew] Preparing Jadwal Pekerjaan export...');

    // Get application state from global window object (set by TanStackGridManager)
    const state = this._getApplicationState();

    if (!state) {
      throw new Error('Application state not available. Please ensure grid is loaded.');
    }

    console.log('[ExportManagerNew] State loaded:', {
      rows: state.hierarchyRows?.length || 0,
      weeks: state.weekColumns?.length || 0,
      kurvaSData: state.kurvaSData?.length || 0
    });

    // Determine report type (default to rekap)
    const reportType = options.reportType || 'rekap';

    // Map format to internal format
    const formatMap = {
      'pdf': EXPORT_CONFIG.formats.PDF,
      'word': EXPORT_CONFIG.formats.WORD,
      'xlsx': EXPORT_CONFIG.formats.EXCEL,
      'json': EXPORT_CONFIG.formats.JSON
    };

    const internalFormat = formatMap[format] || format;

    // Generate report based on type
    let result;

    if (reportType === 'monthly') {
      const month = options.month || 1;
      const { generateMonthlyReport, exportMonthlyReport } = await import('./reports/monthly-report.js');

      console.log(`[ExportManagerNew] Generating Monthly Report (Month ${month})...`);
      await exportMonthlyReport(state, internalFormat, month, options);

    } else if (reportType === 'weekly') {
      const week = options.week || 1;
      const { generateWeeklyReport, exportWeeklyReport } = await import('./reports/weekly-report.js');

      console.log(`[ExportManagerNew] Generating Weekly Report (Week ${week})...`);
      await exportWeeklyReport(state, internalFormat, week, options);

    } else {
      // Default: Laporan Rekap
      const { generateRekapReport, exportRekapReport } = await import('./reports/rekap-report.js');

      console.log(`[ExportManagerNew] Generating Rekap Report...`);
      await exportRekapReport(state, internalFormat, options);
    }

    console.log(`[ExportManagerNew] ${format.toUpperCase()} export completed!`);
  }

  /**
   * Get application state from window (set by grid manager)
   */
  _getApplicationState() {
    // Try to get from window.jadwalApp (set by TanStackGridManager)
    if (window.jadwalApp && window.jadwalApp.getExportState) {
      return window.jadwalApp.getExportState();
    }

    // Try to get from global state object
    if (window.exportState) {
      return window.exportState;
    }

    // Try to construct from available data
    return this._constructStateFromDOM();
  }

  /**
   * Construct state from DOM elements (fallback)
   */
  _constructStateFromDOM() {
    console.warn('[ExportManagerNew] Constructing state from DOM (fallback mode)');

    // This is a fallback - ideally the grid manager should provide this
    const state = {
      hierarchyRows: [],
      weekColumns: [],
      plannedProgress: {},
      actualProgress: {},
      kurvaSData: [],
      projectName: document.querySelector('.toolbar-subtitle')?.textContent?.replace('Project: ', '') || 'Project',
      projectOwner: 'N/A',
      projectLocation: 'N/A',
      projectBudget: 0
    };

    return state;
  }

  /**
   * Export using old system (for non-Jadwal pages)
   */
  async _exportViaOldSystem(format, options = {}) {
    console.log('[ExportManagerNew] Using old export system for', this.pageType);

    let url = `${this.baseUrl}${format}/`;
    const attachments = options.attachments || [];

    // Append parameters if provided
    if (options.parameters && Object.keys(options.parameters).length > 0) {
      const paramsJson = JSON.stringify(options.parameters);
      const separator = url.includes('?') ? '&' : '?';
      url += `${separator}params=${encodeURIComponent(paramsJson)}`;
    }

    // Optional orientation override
    try {
      const raw = options.orientation || (this.pageType === 'rincian-ahsp' ? localStorage.getItem('rincian_ahsp_export_orientation') : null);
      const ori = (raw || '').toLowerCase();
      if (ori === 'portrait' || ori === 'landscape') {
        const separator = url.includes('?') ? '&' : '?';
        url += `${separator}orientation=${encodeURIComponent(ori)}`;
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
      const text = await response.text();
      throw new Error(`Export failed: ${response.status} ${response.statusText}\n${text}`);
    }

    const blob = await response.blob();
    const filename = this._getFilenameFromResponse(response, format);
    this._downloadBlob(blob, filename);
  }

  /**
   * Get CSRF token from cookies
   */
  _getCsrfToken() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      const [key, value] = cookie.trim().split('=');
      if (key === name) {
        return decodeURIComponent(value);
      }
    }
    return '';
  }

  /**
   * Extract filename from Content-Disposition header
   */
  _getFilenameFromResponse(response, format) {
    const disposition = response.headers.get('Content-Disposition');
    if (disposition && disposition.includes('filename=')) {
      const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      if (match && match[1]) {
        return match[1].replace(/['"]/g, '');
      }
    }

    const extensions = {
      'json': 'json',
      'pdf': 'pdf',
      'word': 'docx',
      'xlsx': 'xlsx'
    };

    const ext = extensions[format] || format;
    const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
    return `export_${this.pageType}_${timestamp}.${ext}`;
  }

  /**
   * Download blob as file
   */
  _downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  /**
   * Show loading indicator
   */
  _showLoading(format) {
    const btn = document.querySelector(`#btn-export-${format}, #btn-export-excel, .btn-export`);
    if (btn) {
      btn.disabled = true;
      btn.dataset.originalText = btn.innerHTML;
      btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Exporting...';
    }

    // Show toast notification
    if (window.bootstrap && window.bootstrap.Toast) {
      const toastHtml = `
        <div class="toast align-items-center text-white bg-primary border-0" role="alert" aria-live="assertive" aria-atomic="true">
          <div class="d-flex">
            <div class="toast-body">
              <i class="bi bi-hourglass-split"></i> Generating ${format.toUpperCase()} export...
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
          </div>
        </div>
      `;

      let container = document.querySelector('.toast-container');
      if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(container);
      }

      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = toastHtml;
      const toastElement = tempDiv.firstElementChild;
      container.appendChild(toastElement);

      const toast = new window.bootstrap.Toast(toastElement);
      toast.show();
    }
  }

  /**
   * Hide loading indicator
   */
  _hideLoading() {
    const btn = document.querySelector('[data-original-text]');
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = btn.dataset.originalText;
      delete btn.dataset.originalText;
    }
  }

  /**
   * Show error message
   */
  _showError(format, error) {
    console.error(`[ExportManagerNew] ${format} export error:`, error);

    const message = error.message || 'Unknown error occurred';

    if (window.bootstrap && window.bootstrap.Toast) {
      const toastHtml = `
        <div class="toast align-items-center text-white bg-danger border-0" role="alert" aria-live="assertive" aria-atomic="true">
          <div class="d-flex">
            <div class="toast-body">
              <i class="bi bi-exclamation-triangle"></i> Export failed: ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
          </div>
        </div>
      `;

      let container = document.querySelector('.toast-container');
      if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(container);
      }

      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = toastHtml;
      const toastElement = tempDiv.firstElementChild;
      container.appendChild(toastElement);

      const toast = new window.bootstrap.Toast(toastElement, { autohide: false });
      toast.show();
    } else {
      alert(`Export failed: ${message}`);
    }
  }
}

/**
 * Helper function to wire up export buttons
 * Call this from your main app initialization
 */
export function initializeExportButtons(projectId, pageType = 'jadwal-pekerjaan') {
  console.log('[UI Integration] Initializing export buttons with NEW SYSTEM...');

  const exporter = new ExportManagerNew(projectId, pageType);

  // Wire up export button
  const exportBtn = document.querySelector('#btn-export-excel, .btn-export');
  if (exportBtn) {
    exportBtn.addEventListener('click', async () => {
      // Show format selection modal or export directly
      // For now, export as Excel (rekap)
      await exporter.exportAs('xlsx', { reportType: 'rekap' });
    });

    console.log('[UI Integration] Export button wired up');
  }

  // Store exporter globally for console access
  window.exportManager = exporter;

  console.log('[UI Integration] Export manager available as window.exportManager');
  console.log('[UI Integration] Usage: window.exportManager.exportAs("pdf", { reportType: "rekap" })');
}

// Export for backward compatibility
export { EXPORT_CONFIG } from './export-coordinator.js';
