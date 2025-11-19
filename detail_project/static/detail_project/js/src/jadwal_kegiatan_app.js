/**
 * Jadwal Kegiatan Main Entry Point
 * Modern modular implementation with Vite bundling
 * License: MIT
 */

import { attachGridEvents } from '@modules/grid/grid-event-handlers.js';
import { AGGridManager } from '@modules/grid/ag-grid-setup.js';
import { updateProgressIndicator } from '@modules/shared/validation-utils.js';

/**
 * Initialize Jadwal Kegiatan Grid Application
 */
class JadwalKegiatanApp {
  constructor() {
    this.state = null;
    this.eventManager = null;
    this.initialized = false;
    this.agGridManager = null;
  }

  /**
   * Initialize the application
   *
   * @param {Object} config - Configuration options
   * @param {Object} config.initialState - Initial application state
   * @param {Object} config.domRefs - DOM element references
   */
  async initialize(config = {}) {
    if (this.initialized) {
      console.warn('JadwalKegiatanApp already initialized');
      return;
    }

    console.log('🚀 Initializing Jadwal Kegiatan App (Vite Build)');

    try {
      // Setup state
      this._setupState(config);

      // Setup DOM references
      this._setupDomRefs(config);

      // Attach event handlers
      this._attachEvents();

      // Load initial data
      await this._loadInitialData();

      this.initialized = true;
      console.log('✅ Jadwal Kegiatan App initialized successfully');

      // Expose to window for backwards compatibility
      window.JadwalKegiatanApp = this;
    } catch (error) {
      console.error('❌ Failed to initialize Jadwal Kegiatan App:', error);
      throw error;
    }
  }

  /**
   * Setup application state
   */
  _setupState(config) {
    // Check if there's existing global state (backwards compatibility)
    const existingState = window.kelolaTahapanPageState || window.JadwalPekerjaanApp?.state;

    this.state = Object.assign(
      {
        pekerjaanTree: [],
        timeColumns: [],
        tahapanList: [],
        timeColumnIndex: {},
        expandedNodes: new Set(),
        modifiedCells: new Map(),
        progressTotals: new Map(),
        isDirty: false,
        isLoading: false,
        error: null,
        domRefs: {},
        apiEndpoints: {},
        projectId: null,
        projectName: '',
        projectStart: null,
        projectEnd: null,
        useAgGrid: false,
        saveMode: 'weekly',
        weekEndDay: 6,
      },
      existingState || {},
      config.initialState || {}
    );

    // Expose to window for backwards compatibility
    window.kelolaTahapanPageState = this.state;

    this.state.timeColumnIndex = this._createTimeColumnIndex(this.state.timeColumns);
  }

  /**
   * Setup DOM references
   */
  _setupDomRefs(config) {
    const domRefs = Object.assign(
      {
        root: document.getElementById('tahapan-grid-app'),
        leftThead: document.getElementById('left-thead'),
        rightThead: document.getElementById('right-thead'),
        leftTbody: document.getElementById('left-tbody'),
        rightTbody: document.getElementById('right-tbody'),
        leftPanelScroll: document.querySelector('.left-panel-scroll'),
        rightPanelScroll: document.querySelector('.right-panel-scroll'),
        timeHeaderRow: document.getElementById('time-header-row'),
        saveButton: document.getElementById('save-button') || document.getElementById('btn-save-all'),
        refreshButton: document.getElementById('refresh-button'),
        agGridContainer: document.getElementById('ag-grid-container'),
      },
      config.domRefs || {}
    );

    this.state.domRefs = domRefs;

    if (!domRefs.root) {
      throw new Error('Root container #tahapan-grid-app tidak ditemukan');
    }

    this._applyDataset(domRefs.root);

    // Validate critical elements
    if (!domRefs.leftTbody || !domRefs.rightTbody) {
      throw new Error('Critical DOM elements not found (leftTbody, rightTbody)');
    }
  }

  /**
   * Apply dataset attributes from root container into state
   */
  _applyDataset(rootElement) {
    if (!rootElement || !rootElement.dataset) {
      return;
    }

    const { dataset } = rootElement;

    this.state.projectId = Number(dataset.projectId || this.state.projectId || 0) || this.state.projectId;
    this.state.projectName = dataset.projectName || this.state.projectName;
    this.state.projectStart = dataset.projectStart || this.state.projectStart;
    this.state.projectEnd = dataset.projectEnd || this.state.projectEnd;
    this.state.saveMode = dataset.saveMode || dataset.timeScale || this.state.saveMode;

    const parsedWeekEndDay = Number.parseInt(
      dataset.weekEndDay ?? dataset.weekend ?? dataset.weekEnd ?? dataset.week_end_day ?? '',
      10
    );
    if (!Number.isNaN(parsedWeekEndDay)) {
      this.state.weekEndDay = parsedWeekEndDay;
    }

    const endpoints = Object.assign(
      {
        base: dataset.apiBase || '',
        tahapan: dataset.apiTahapan || dataset.apiBase || '',
        listPekerjaan: dataset.apiListPekerjaan || '',
        volume: dataset.apiVolume || '',
        assignmentsBase: dataset.apiAssignmentsBase || '',
        save:
          dataset.apiSave ||
          (this.state.apiEndpoints && this.state.apiEndpoints.save) ||
          this._getDefaultSaveEndpoint(),
      },
      this.state.apiEndpoints || {}
    );

    this.state.apiEndpoints = endpoints;
    this.state.useAgGrid = dataset.enableAgGrid === 'true' || this.state.useAgGrid;
  }

  /**
   * Attach event handlers using modern delegation pattern
   */
  _attachEvents() {
    const helpers = {
      updateProgressIndicator: (pekerjaanId, total) => {
        updateProgressIndicator(pekerjaanId, total, this.state);
      },
      showToast: this.showToast.bind(this),
    };

    if (!this.state.useAgGrid) {
      this.eventManager = attachGridEvents(this.state, helpers);
    } else if (this.eventManager) {
      this.eventManager.cleanup();
      this.eventManager = null;
    }

    // Attach toolbar events
    this._attachToolbarEvents();

    // Initialize AG Grid when enabled
    this._initAgGridIfNeeded();
  }

  /**
   * Attach toolbar button events
   */
  _attachToolbarEvents() {
    const saveButton = this.state.domRefs.saveButton;
    const refreshButton = this.state.domRefs.refreshButton;

    if (saveButton) {
      saveButton.addEventListener('click', () => this.saveChanges());
    }

    if (refreshButton) {
      refreshButton.addEventListener('click', () => this.refresh());
    }
  }

  /**
   * Initialize AG Grid when enabled
   */
  _initAgGridIfNeeded() {
    if (!this.state.useAgGrid) {
      return;
    }

    const container = this.state.domRefs.agGridContainer;
    if (!container) {
      console.warn('[JadwalKegiatanApp] AG Grid container not available');
      return;
    }

    if (!this.agGridManager) {
      this.agGridManager = new AGGridManager(this.state, {
        showToast: this.showToast.bind(this),
        onCellChange: (payload) => this._handleAgGridCellChange(payload),
      });
      this.agGridManager.mount(container);
    }
  }

  /**
   * Load initial data from server
   */
  async _loadInitialData() {
    // Check if data is already loaded (from Django template)
    if (this.state.pekerjaanTree?.length > 0) {
      const hasConsoleGroup = typeof console.groupCollapsed === 'function';
      if (hasConsoleGroup) {
        console.groupCollapsed('[JadwalKegiatanApp] Using template dataset');
      }
      console.log('Preloaded pekerjaanTree items:', this.state.pekerjaanTree.length);
      console.log('Preloaded tahapanList items:', this.state.tahapanList?.length || 0);
      console.log('Preloaded timeColumns items:', this.state.timeColumns?.length || 0);
      if (hasConsoleGroup) {
        console.groupEnd();
      }
      this._syncGridViews();
      return;
    }

    // Otherwise, fetch from API
    const { apiEndpoints, projectId } = this.state;
    if (!apiEndpoints?.tahapan || !apiEndpoints?.listPekerjaan) {
      console.warn('[JadwalKegiatanApp] API endpoints belum dikonfigurasi.');
      return;
    }

    const logLabel = `[JadwalKegiatanApp] API Load (project ${projectId || 'unknown'})`;
    const canGroup = typeof console.groupCollapsed === 'function';
    if (canGroup) {
      console.groupCollapsed(logLabel);
    } else {
      console.log(logLabel);
    }
    console.log('GET tahapan URL:', apiEndpoints.tahapan);
    console.log('GET list-pekerjaan URL:', apiEndpoints.listPekerjaan);

    console.log('Loading data from API...');
    this.state.isLoading = true;

    try {
      const [tahapanData, pekerjaanData] = await Promise.all([
        this._fetchJson(apiEndpoints.tahapan),
        this._fetchJson(apiEndpoints.listPekerjaan),
      ]);

      const tahapanList = Array.isArray(tahapanData)
        ? tahapanData
        : tahapanData.tahapan ||
          tahapanData.results ||
          tahapanData.data ||
          tahapanData.items ||
          [];

      const pekerjaanTree = Array.isArray(pekerjaanData)
        ? pekerjaanData
        : pekerjaanData.tree ||
          pekerjaanData.klasifikasi ||
          pekerjaanData.data ||
          pekerjaanData.results ||
          [];

      if (tahapanData && typeof tahapanData === 'object') {
        console.log('Tahapan payload keys:', Object.keys(tahapanData));
      } else {
        console.log('Tahapan payload type:', typeof tahapanData);
      }
      console.log('Resolved tahapanList length:', tahapanList.length);
      if (tahapanList.length) {
        console.log('Sample tahapan item:', tahapanList[0]);
      }

      if (pekerjaanData && typeof pekerjaanData === 'object') {
        console.log('Pekerjaan payload keys:', Object.keys(pekerjaanData));
      } else {
        console.log('Pekerjaan payload type:', typeof pekerjaanData);
      }
      console.log('Resolved pekerjaanTree length:', pekerjaanTree.length);
      if (pekerjaanTree.length) {
        console.log('Sample pekerjaan branch:', pekerjaanTree[0]);
      }

      this.state.tahapanList = tahapanList;
      this.state.pekerjaanTree = pekerjaanTree;
      this.state.timeColumns = this._buildTimeColumns(tahapanList);
      this.state.timeColumnIndex = this._createTimeColumnIndex(this.state.timeColumns);

      console.log(
        `[JadwalKegiatanApp] Loaded ${pekerjaanTree.length} pekerjaan, ${tahapanList.length} tahapan for project ${projectId}`
      );
    } catch (error) {
      console.error('Failed to load data:', error);
      this.state.error = error;
      this.showToast('Gagal memuat data', 'danger');
      console.log('Generated timeColumns:', this.state.timeColumns.length);
    } finally {
      if (canGroup) {
        console.groupEnd();
      }
      this.state.isLoading = false;
      this._syncGridViews();
    }
  }

  /**
   * Save changes to server
   */
  async saveChanges() {
    if (!this.state.modifiedCells || this.state.modifiedCells.size === 0) {
      this.showToast('Tidak ada perubahan untuk disimpan', 'info');
      return;
    }

    const assignments = this._buildAssignmentsPayload();
    if (assignments.length === 0) {
      this.showToast('Tidak ada assignments valid untuk disimpan', 'warning');
      return;
    }

    console.log(
      `[JadwalKegiatanApp] Saving ${assignments.length} assignments (${this.state.modifiedCells.size} cells)`
    );

    try {
      const saveUrl = this.state.apiEndpoints?.save || this._getDefaultSaveEndpoint();
      const payload = {
        assignments,
        mode: this._getSaveMode(),
        week_end_day: this._getWeekEndDay(),
      };

      const response = await fetch(saveUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this._getCsrfToken(),
        },
        credentials: 'same-origin',
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();

      // Clear modified cells
      this.state.modifiedCells.clear();
      this.state.isDirty = false;

      this.showToast('Perubahan berhasil disimpan', 'success');
      console.log('[JadwalKegiatanApp] Save successful:', result);
    } catch (error) {
      console.error('Save failed:', error);
      this.showToast('Gagal menyimpan: ' + error.message, 'danger');
    }
  }

  /**
   * Refresh data from server
   */
  async refresh() {
    if (this.state.isDirty) {
      const confirmed = confirm(
        'Ada perubahan yang belum disimpan. Yakin ingin refresh?'
      );
      if (!confirmed) return;
    }

    console.log('Refreshing data...');
    this.state.modifiedCells.clear();
    this.state.isDirty = false;

    await this._loadInitialData();
    this.showToast('Data berhasil di-refresh', 'success');
  }

  /**
   * Show toast notification
   */
  showToast(message, type = 'info', duration = 3000) {
    // Use existing toast system if available
    if (typeof window.showToast === 'function') {
      window.showToast(message, type, duration);
      return;
    }

    // Fallback toast implementation
    console.log(`[${type.toUpperCase()}] ${message}`);

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('show');
    }, 10);

    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  /**
   * Build normalized time columns from tahapan list
   */
  _buildTimeColumns(tahapanList = []) {
    if (!Array.isArray(tahapanList)) {
      return [];
    }

    return tahapanList.map((tahap, index) => {
      const rawId = tahap?.id ?? `tahapan-${index + 1}`;
      const safeId = String(rawId).replace(/[^a-zA-Z0-9_-]/g, '_');
      const fieldId = `col_${safeId}`;
      const label = tahap?.nama || tahap?.name || `Tahapan ${index + 1}`;
      const order =
        typeof tahap?.urutan === 'number'
          ? tahap.urutan
          : Number.parseInt(tahap?.urutan, 10) || index;
      const weekNumber = order + 1;
      return {
        id: rawId,
        fieldId,
        label,
        order,
        weekNumber,
        startDate: tahap?.tanggal_mulai || tahap?.start_date || tahap?.startDate || null,
        endDate: tahap?.tanggal_selesai || tahap?.end_date || tahap?.endDate || null,
        isAutoGenerated: Boolean(tahap?.is_auto_generated),
        generationMode: tahap?.generation_mode || null,
      };
    });
  }

  _createTimeColumnIndex(columns = []) {
    const index = {};
    (columns || []).forEach((col) => {
      const key = col.fieldId || col.id;
      if (key) {
        index[key] = col;
      }
    });
    return index;
  }

  _getDefaultSaveEndpoint() {
    const projectId = this.state?.projectId;
    if (!projectId) {
      return '';
    }
    return `/detail_project/api/v2/project/${projectId}/assign-weekly/`;
  }

  /**
   * Fetch JSON helper with sane defaults
   */
  async _fetchJson(url, options = {}) {
    if (!url) {
      throw new Error('URL tidak boleh kosong saat memanggil _fetchJson');
    }

    const response = await fetch(url, {
      credentials: 'same-origin',
      ...options,
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => '');
      throw new Error(errorText || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Sync rendered grids (AG Grid + future legacy bridging)
   */
  _syncGridViews() {
    if (this.agGridManager) {
      this.agGridManager.updateData({
        tree: this.state.pekerjaanTree || [],
        timeColumns: this.state.timeColumns || [],
      });
    }
  }

  _buildAssignmentsPayload() {
    if (!this.state.modifiedCells || this.state.modifiedCells.size === 0) {
      return [];
    }

    const assignments = [];
    const columnIndex = this.state.timeColumnIndex || {};

    this.state.modifiedCells.forEach((value, cellKey) => {
      const parsed = this._parseCellKey(cellKey);
      if (!parsed?.pekerjaanId || !parsed.fieldId) {
        return;
      }

      const columnMeta = columnIndex[parsed.fieldId];
      if (!columnMeta) {
        console.warn('[JadwalKegiatanApp] Column metadata not found for', parsed.fieldId);
        return;
      }

      const proportion = parseFloat(value);
      if (Number.isNaN(proportion)) {
        return;
      }

      const weekNumber = columnMeta.weekNumber || columnMeta.order + 1 || 1;

      assignments.push({
        pekerjaan_id: Number(parsed.pekerjaanId),
        week_number: weekNumber,
        proportion: Number(proportion.toFixed(2)),
        tahapan_id: columnMeta.id || null,
      });
    });

    return assignments;
  }

  _getSaveMode() {
    const normalized = (this.state?.saveMode || 'weekly').toLowerCase();
    const allowed = new Set(['daily', 'weekly', 'monthly', 'custom']);
    return allowed.has(normalized) ? normalized : 'weekly';
  }

  _getWeekEndDay() {
    const raw = Number(this.state?.weekEndDay);
    if (Number.isFinite(raw) && raw >= 0 && raw <= 6) {
      return raw;
    }
    return 6;
  }

  _parseCellKey(cellKey) {
    if (!cellKey || typeof cellKey !== 'string') {
      return null;
    }
    const separatorIndex = cellKey.indexOf('-');
    if (separatorIndex === -1) {
      return { pekerjaanId: cellKey, fieldId: null };
    }

    return {
      pekerjaanId: cellKey.slice(0, separatorIndex),
      fieldId: cellKey.slice(separatorIndex + 1),
    };
  }

  /**
   * Get CSRF token from cookie
   */
  _getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;

    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + '=') {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }

    return cookieValue;
  }

  /**
   * Handle AG Grid cell change
   */
  _handleAgGridCellChange({ cellKey, value, columnMeta }) {
    if (!cellKey) {
      return;
    }

    let normalizedValue = value;
    if (typeof normalizedValue === 'string') {
      normalizedValue = parseFloat(normalizedValue);
    }
    if (Number.isNaN(normalizedValue)) {
      normalizedValue = 0;
    }

    this.state.modifiedCells = this.state.modifiedCells || new Map();
    this.state.modifiedCells.set(cellKey, normalizedValue);
    this.state.isDirty = true;

    if (columnMeta?.fieldId && this.state.timeColumnIndex) {
      this.state.timeColumnIndex[columnMeta.fieldId] =
        columnMeta || this.state.timeColumnIndex[columnMeta.fieldId];
    }
  }

  /**
   * Cleanup and destroy the application
   */
  destroy() {
    if (this.eventManager) {
      this.eventManager.cleanup();
      this.eventManager = null;
    }

    if (this.agGridManager) {
      this.agGridManager.destroy();
      this.agGridManager = null;
    }

    this.state = null;
    this.initialized = false;

    console.log('JadwalKegiatanApp destroyed');
  }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    const app = new JadwalKegiatanApp();
    app.initialize();
  });
} else {
  // DOM already loaded
  const app = new JadwalKegiatanApp();
  app.initialize();
}

// Export for manual initialization
export default JadwalKegiatanApp;
