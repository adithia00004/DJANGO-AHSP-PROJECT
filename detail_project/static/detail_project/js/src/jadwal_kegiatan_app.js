/**
 * Jadwal Kegiatan Main Entry Point
 * Modern modular implementation with Vite bundling
 * License: MIT
 */
/* global ExportManager */

import { attachGridEvents } from '@modules/grid/grid-event-handlers.js';
import { AGGridManager } from '@modules/grid/ag-grid-setup.js';
import { updateProgressIndicator } from '@modules/shared/validation-utils.js';
import { DataLoader } from '@modules/core/data-loader.js';
import { TimeColumnGenerator } from '@modules/core/time-column-generator.js';
import { GridRenderer } from '@modules/grid/grid-renderer.js';
import { SaveHandler } from '@modules/core/save-handler.js';
import { KurvaSChart } from '@modules/kurva-s/echarts-setup.js';
import { GanttChart } from '@modules/gantt/frappe-gantt-setup.js';

/**
 * Initialize Jadwal Kegiatan Grid Application
 */
class JadwalKegiatanApp {
  constructor() {
    this.state = null;
    this.eventManager = null;
    this.initialized = false;
    this.agGridManager = null;

    // Modern modules
    this.dataLoader = null;
    this.timeColumnGenerator = null;
    this.gridRenderer = null;
    this.saveHandler = null;

    // Chart modules
    this.kurvaSChart = null;
    this.ganttChart = null;

    this._weekBoundarySaveTimer = null;
    this._pendingWeekBoundary = null;
    this._isRegeneratingTimeline = false;
    this._queuedRegeneratePayload = null;
    this._isEnforcingWeekly = false;
    this._exportManagerInstance = null;
    this._exportBindingsAttached = false;
  }

  _getProjectDateRange() {
    let start = null;
    let end = null;
    if (this.state?.projectStart) {
      const parsed = new Date(this.state.projectStart);
      if (!Number.isNaN(parsed.getTime())) {
        start = parsed;
      }
    }
    if (this.state?.projectEnd) {
      const parsedEnd = new Date(this.state.projectEnd);
      if (!Number.isNaN(parsedEnd.getTime())) {
        end = parsedEnd;
      }
    }
    if (start && (!end || Number.isNaN(end.getTime()))) {
      end = new Date(start.getFullYear(), 11, 31);
    }
    return { start, end };
  }

  _estimateExpectedWeeklyColumns() {
    const { start, end } = this._getProjectDateRange();
    if (!start || !end || Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
      return 0;
    }
    const msPerDay = 1000 * 60 * 60 * 24;
    const diffDays = Math.max(0, Math.floor((end - start) / msPerDay)) + 1;
    return Math.max(1, Math.ceil(diffDays / 7));
  }

  _countWeeklyColumns() {
    if (!Array.isArray(this.state.timeColumns)) {
      return 0;
    }
    return this.state.timeColumns.filter((col) => {
      const mode = (col.generationMode || col.type || '').toLowerCase();
      if (mode === 'weekly' || mode === 'week' || mode === 'wk') {
        return true;
      }
      return Number.isFinite(Number(col.weekNumber ?? col.week_number));
    }).length;
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
        // Shared state (mode-independent)
        pekerjaanTree: [],
        timeColumns: [],
        tahapanList: [],
        timeColumnIndex: {},
        expandedNodes: new Set(),
        volumeMap: new Map(),
        isLoading: false,
        error: null,
        domRefs: {},
        apiEndpoints: {},
        projectId: null,
        projectName: '',
        projectStart: null,
        projectEnd: null,
        useAgGrid: false,
        timeScale: 'weekly',
        inputMode: 'percentage',
        saveMode: 'weekly',
        weekStartDay: 0,
        weekEndDay: 6,
        displayScale: null,
        progressMode: 'planned',  // Phase 2E.1: Current active mode
        displayMode: 'percentage', // Phase 2E.1: 'percentage' or 'volume'

        // Phase 2E.1: Dual state structure - separate state per progress mode
        plannedState: {
          modifiedCells: new Map(),
          assignmentMap: new Map(),
          progressTotals: new Map(),
          volumeTotals: new Map(),
          cellVolumeOverrides: new Map(),
          cellValidationMap: new Map(),
          failedRows: new Set(),
          autoWarningRows: new Set(),
          volumeWarningRows: new Set(),
          validationWarningRows: new Set(),
          saveErrorRows: new Set(),
          apiFailedRows: new Set(),
          showCompletionWarnings: false,
          isDirty: false,
        },
        actualState: {
          modifiedCells: new Map(),
          assignmentMap: new Map(),
          progressTotals: new Map(),
          volumeTotals: new Map(),
          cellVolumeOverrides: new Map(),
          cellValidationMap: new Map(),
          failedRows: new Set(),
          autoWarningRows: new Set(),
          volumeWarningRows: new Set(),
          validationWarningRows: new Set(),
          saveErrorRows: new Set(),
          apiFailedRows: new Set(),
          showCompletionWarnings: false,
          isDirty: false,
        },

        // Backward compatibility: Legacy properties point to current mode
        // These will be dynamically updated via getters
        modifiedCells: null,  // Will be replaced by getter
        progressTotals: null,
        volumeTotals: null,
        cellVolumeOverrides: null,
        cellValidationMap: null,
        failedRows: null,
        autoWarningRows: null,
        volumeWarningRows: null,
        validationWarningRows: null,
        saveErrorRows: null,
        apiFailedRows: null,
        showCompletionWarnings: false,
        isDirty: false,
      },
      existingState || {},
      config.initialState || {}
    );

    // Expose to window for backwards compatibility
    window.kelolaTahapanPageState = this.state;

    this.state.timeColumnIndex = this._createTimeColumnIndex(this.state.timeColumns);
    this._ensureStateCollections();
    if (!this.state.displayScale) {
      this.state.displayScale = this.state.timeScale || 'weekly';
    }

    // Phase 2E.1: Setup property delegation for backward compatibility
    this._setupStateDelegation();
  }

  /**
   * Setup property delegation for backward compatibility.
   * Maps legacy state properties to current mode's state.
   */
  _setupStateDelegation() {
    const getCurrentState = () => {
      return this.state.progressMode === 'actual'
        ? this.state.actualState
        : this.state.plannedState;
    };

    // Define getters/setters for backward compatibility
    // These delegate to the current mode's state
    Object.defineProperty(this.state, 'modifiedCells', {
      get: () => getCurrentState().modifiedCells,
      configurable: true
    });

    Object.defineProperty(this.state, 'assignmentMap', {
      get: () => getCurrentState().assignmentMap,
      configurable: true
    });

    Object.defineProperty(this.state, 'progressTotals', {
      get: () => getCurrentState().progressTotals,
      configurable: true
    });

    Object.defineProperty(this.state, 'volumeTotals', {
      get: () => getCurrentState().volumeTotals,
      configurable: true
    });

    Object.defineProperty(this.state, 'cellVolumeOverrides', {
      get: () => getCurrentState().cellVolumeOverrides,
      configurable: true
    });

    Object.defineProperty(this.state, 'cellValidationMap', {
      get: () => getCurrentState().cellValidationMap,
      configurable: true
    });

    Object.defineProperty(this.state, 'isDirty', {
      get: () => getCurrentState().isDirty,
      set: (value) => { getCurrentState().isDirty = value; },
      configurable: true
    });

    console.log('[JadwalKegiatanApp] State delegation setup complete');
  }

  /**
   * Get the current mode's state object.
   * @returns {Object} Current mode state (plannedState or actualState)
   */
  _getCurrentModeState() {
    return this.state.progressMode === 'actual'
      ? this.state.actualState
      : this.state.plannedState;
  }

  _updateSaveButtonState() {
    const saveButton = this.state?.domRefs?.saveButton;
    if (!saveButton) {
      return;
    }
    const hasFailures = this.state?.failedRows instanceof Set && this.state.failedRows.size > 0;
    saveButton.disabled = false;
    saveButton.classList.toggle('btn-outline-danger', Boolean(hasFailures));
    saveButton.classList.toggle('btn-success', !hasFailures);
    if (hasFailures) {
      saveButton.setAttribute(
        'title',
        'Ada baris dengan peringatan (>100%/volume). Klik untuk melihat detail dan perbaiki.'
      );
    } else {
      saveButton.removeAttribute('title');
    }
  }

  _ensureStateCollections() {
    if (!(this.state.failedRows instanceof Set)) {
      this.state.failedRows = new Set();
    }
    if (!(this.state.autoWarningRows instanceof Set)) {
      this.state.autoWarningRows = new Set();
    }
    if (!(this.state.volumeWarningRows instanceof Set)) {
      this.state.volumeWarningRows = new Set();
    }
    if (!(this.state.validationWarningRows instanceof Set)) {
      this.state.validationWarningRows = new Set();
    }
    if (!(this.state.saveErrorRows instanceof Set)) {
      this.state.saveErrorRows = new Set();
    }
    if (!(this.state.apiFailedRows instanceof Set)) {
      this.state.apiFailedRows = new Set();
    }
    if (!(this.state.progressTotals instanceof Map)) {
      this.state.progressTotals = new Map();
    }
    if (!(this.state.volumeTotals instanceof Map)) {
      this.state.volumeTotals = new Map();
    }
    if (!(this.state.cellVolumeOverrides instanceof Map)) {
      this.state.cellVolumeOverrides = new Map();
    }
    if (!(this.state.cellValidationMap instanceof Map)) {
      this.state.cellValidationMap = new Map();
    }
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
        rightPanelScroll:
          document.getElementById('right-panel-scroll-bottom') ||
          document.querySelector('.right-panel-scroll'),
        rightTable: document.getElementById('right-table'),
        horizontalScrollTop: document.getElementById('right-panel-scroll-top'),
        horizontalScrollInner: document.getElementById('right-panel-scroll-inner'),
        timeHeaderRow: document.getElementById('time-header-row'),
        saveButton: document.getElementById('save-button') || document.getElementById('btn-save-all'),
        refreshButton: document.getElementById('refresh-button'),
        resetButton: document.getElementById('btn-reset-progress'),
        agGridContainer: document.getElementById('ag-grid-container'),
        agGridTopScroll: document.getElementById('ag-grid-scroll-top'),
        agGridTopScrollInner: document.getElementById('ag-grid-scroll-inner'),
        scurveChart: document.getElementById('scurve-chart'),
        ganttChart: document.getElementById('gantt-chart'),
        statusBar: document.querySelector('.status-bar'),
        statusMessageEl: document.getElementById('status-message'),
        itemCountEl: document.getElementById('item-count'),
        modifiedCountEl: document.getElementById('modified-count'),
        totalProgressEl: document.getElementById('total-progress'),
        weekStartSelect: document.getElementById('week-start-day-select'),
        weekEndSelect: document.getElementById('week-end-day-select'),
      },
      config.domRefs || {}
    );

    this.state.domRefs = domRefs;
    this._updateSaveButtonState();

    if (!domRefs.root) {
      throw new Error('Root container #tahapan-grid-app tidak ditemukan');
    }

    this._applyDataset(domRefs.root);

    if (this.state.useAgGrid) {
      if (!domRefs.agGridContainer) {
        throw new Error('AG Grid container #ag-grid-container tidak ditemukan');
      }
    } else {
      if (!domRefs.leftTbody || !domRefs.rightTbody) {
        throw new Error('Critical DOM elements not found (leftTbody, rightTbody)');
      }
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

    const allowedTimeScales = new Set(['daily', 'weekly', 'monthly', 'custom']);
    const datasetScale =
      (dataset.defaultTimeScale ||
        dataset.timeScale ||
        dataset.saveMode ||
        this.state.timeScale ||
        this.state.saveMode ||
        '')
        .toString()
        .toLowerCase();
    if (allowedTimeScales.has(datasetScale)) {
      this.state.timeScale = datasetScale;
      this.state.saveMode = datasetScale;
    } else if (!this.state.timeScale) {
      this.state.timeScale = this.state.saveMode || 'weekly';
    }
    this.state.displayScale = this.state.timeScale || 'weekly';

    const datasetInputMode =
      (dataset.defaultInputMode || dataset.inputMode || dataset.displayMode || this.state.inputMode || 'percentage')
        .toString()
        .toLowerCase();
    const allowedInputModes = new Set(['percentage', 'volume']);
    this.state.inputMode = allowedInputModes.has(datasetInputMode) ? datasetInputMode : 'percentage';

    const parsedWeekEndDay = Number.parseInt(
      dataset.weekEndDay ?? dataset.weekend ?? dataset.weekEnd ?? dataset.week_end_day ?? '',
      10
    );
    if (!Number.isNaN(parsedWeekEndDay)) {
      this.state.weekEndDay = parsedWeekEndDay;
    }

    const parsedWeekStartDay = Number.parseInt(
      dataset.weekStartDay ?? dataset.week_start_day ?? '',
      10
    );
    if (!Number.isNaN(parsedWeekStartDay)) {
      const normalized = ((parsedWeekStartDay % 7) + 7) % 7;
      this.state.weekStartDay = normalized;
    } else if (!Number.isNaN(parsedWeekEndDay)) {
      this.state.weekStartDay = (this.state.weekEndDay + 1) % 7;
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
        weekBoundary: dataset.apiWeekBoundary || '',
        regenerateTahapan: dataset.apiRegenerateTahapan || '',
        reset: dataset.apiResetProgress || (this.state.apiEndpoints && this.state.apiEndpoints.reset) || '',
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
    const resetButton = this.state.domRefs.resetButton;

    if (saveButton) {
      saveButton.addEventListener('click', () => this.saveChanges());
    }

    if (refreshButton) {
      refreshButton.addEventListener('click', () => this.refresh());
    }

    if (resetButton) {
      resetButton.addEventListener('click', () => this._handleResetProgress());
    }

    this._syncToolbarRadios();
    this._attachRadioGroupHandler('displayMode', (value) => this._handleDisplayModeChange(value));
    this._attachRadioGroupHandler('progressMode', (value) => this._handleProgressModeChange(value));  // Phase 2E.1
    this._attachRadioGroupHandler('timeScale', (value) => this._handleTimeScaleChange(value));
    this._setupWeekBoundaryControls();
    this._setupExportButtons();
  }

  _setupExportButtons() {
    if (this._exportBindingsAttached) {
      return;
    }
    if (typeof ExportManager === 'undefined') {
      console.warn('[JadwalKegiatanApp] ExportManager is not loaded; export buttons disabled');
      return;
    }
    if (!this.state?.projectId) {
      return;
    }

    try {
      this._exportManagerInstance = new ExportManager(this.state.projectId, 'jadwal-pekerjaan');
      const formats = ['csv', 'pdf', 'word', 'xlsx'];
      formats.forEach((format) => {
        const button = document.getElementById(`btn-export-${format}`);
        if (!button) {
          return;
        }
        button.addEventListener('click', () => {
          this._exportManagerInstance.exportAs(format);
        });
      });
      this._exportBindingsAttached = true;
    } catch (error) {
      console.error('[JadwalKegiatanApp] Failed to initialize export buttons', error);
    }
  }

  _attachRadioGroupHandler(groupName, handler) {
    const radios = document.querySelectorAll(`input[name="${groupName}"]`);
    if (!radios || radios.length === 0) {
      return;
    }

    radios.forEach((radio) => {
      radio.addEventListener('change', (event) => {
        if (!event.target.checked) {
          return;
        }
        handler(event.target.value);
      });
    });
  }

  _setupWeekBoundaryControls() {
    const { weekStartSelect, weekEndSelect } = this.state.domRefs || {};
    if (!weekStartSelect || !weekEndSelect) {
      return;
    }

    this._syncWeekBoundaryControls();

    weekStartSelect.addEventListener('change', (event) => {
      const nextStart = this._normalizePythonWeekday(event.target.value, this._getWeekStartDay());
      const derivedEnd = (nextStart + 6) % 7;
      this._handleWeekBoundaryChange({ weekStartDay: nextStart, weekEndDay: derivedEnd, source: 'start' });
    });

    weekEndSelect.addEventListener('change', (event) => {
      const nextEnd = this._normalizePythonWeekday(event.target.value, this._getWeekEndDay());
      const derivedStart = (nextEnd + 1) % 7;
      this._handleWeekBoundaryChange({ weekStartDay: derivedStart, weekEndDay: nextEnd, source: 'end' });
    });
  }

  async _handleResetProgress() {
    const endpoint = this.state.apiEndpoints?.reset;
    if (!endpoint) {
      this.showToast('Endpoint reset tidak tersedia', 'danger', 3200);
      return;
    }

    // Phase 2E.1: Mode-aware reset
    const progressMode = this.state.progressMode || 'planned';
    const modeLabel = progressMode === 'planned' ? 'Perencanaan' : 'Realisasi';

    const confirmed = window.confirm(
      `Reset semua progress ${modeLabel} ke 0%?\n\n` +
      `Data ${modeLabel === 'Perencanaan' ? 'Realisasi' : 'Perencanaan'} tidak akan terpengaruh.\n\n` +
      `Operasi ini dapat di-undo dengan memasukkan ulang data.`
    );
    if (!confirmed) {
      return;
    }

    try {
      this.state.isLoading = true;
      this._updateStatusBar(`Mereset progress ${modeLabel}...`);

      const response = await fetch(endpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this._getCsrfToken(),
        },
        body: JSON.stringify({ mode: progressMode }),  // Phase 2E.1: Send mode parameter
      });

      if (!response.ok) {
        const text = await response.text().catch(() => '');
        throw new Error(text || `HTTP ${response.status}`);
      }

      const result = await response.json().catch(() => ({}));
      this._resetEditedCellsState();
      if (this.state.assignmentMap instanceof Map) {
        this.state.assignmentMap.clear();
      } else {
        this.state.assignmentMap = new Map();
      }
      this._clearFailedRows();
      this.state.isDirty = false;

      const message =
        result?.message || 'Progress berhasil direset. Silakan input ulang jadwal pekerjaan.';
      this.showToast(message, 'success', 3400);

      await this._loadInitialData({ forceReload: true });
    } catch (error) {
      console.error('[JadwalKegiatanApp] Failed to reset progress', error);
      this.showToast('Gagal mereset progress. Coba lagi atau hubungi admin.', 'danger', 3600);
    } finally {
      this.state.isLoading = false;
      this._updateStatusBar();
    }
  }

  _syncWeekBoundaryControls() {
    const { weekStartSelect, weekEndSelect } = this.state.domRefs || {};
    if (weekStartSelect) {
      weekStartSelect.value = String(this._getWeekStartDay());
    }
    if (weekEndSelect) {
      weekEndSelect.value = String(this._getWeekEndDay());
    }
  }

  _handleWeekBoundaryChange({ weekStartDay, weekEndDay, source }) {
    const normalizedEnd = this._normalizePythonWeekday(weekEndDay, this._getWeekEndDay());
    const normalizedStart = this._normalizePythonWeekday(weekStartDay, (normalizedEnd + 1) % 7);
    if (normalizedStart === this._getWeekStartDay() && normalizedEnd === this._getWeekEndDay()) {
      this._syncWeekBoundaryControls();
      return;
    }

    this.state.weekStartDay = normalizedStart;
    this.state.weekEndDay = normalizedEnd;
    this._syncWeekBoundaryControls();

    const label = `${this._formatWeekdayLabel(normalizedStart)} → ${this._formatWeekdayLabel(normalizedEnd)}`;
    const prefix = source === 'start' ? 'Week start disetel ke' : 'Week end disetel ke';
    this.showToast(`${prefix} ${label}`, 'info', 2400);

    this._regenerateColumnsForWeekBoundary();
    this._persistWeekBoundarySettings(normalizedStart, normalizedEnd);
  }

  _regenerateColumnsForWeekBoundary() {
    if (!Array.isArray(this.state.tahapanList) || this.state.tahapanList.length === 0) {
      return;
    }

    if (!this.timeColumnGenerator) {
      this.timeColumnGenerator = new TimeColumnGenerator(this.state);
    }

    try {
      this.timeColumnGenerator.generate();
      this.state.timeColumnIndex = this._createTimeColumnIndex(this.state.timeColumns);
      this._syncGridViews();
      this._recalculateAllProgressTotals();
    } catch (error) {
      console.error('[JadwalKegiatanApp] Failed to regenerate columns for week boundary change', error);
      this.showToast('Gagal menerapkan pengaturan minggu', 'danger', 3200);
    }
  }

  _invalidateCachedDataset() {
    this.state.pekerjaanTree = [];
    this.state.tahapanList = [];
    this.state.timeColumns = [];
    this.state.flatPekerjaan = [];
    this.state.timeColumnIndex = {};
    this.state.assignmentMap = new Map();
    this._resetEditedCellsState();
  }

  _resetEditedCellsState() {
    if (this.state.modifiedCells instanceof Map) {
      this.state.modifiedCells.clear();
    } else {
      this.state.modifiedCells = new Map();
    }
    if (this.state.cellVolumeOverrides instanceof Map) {
      this.state.cellVolumeOverrides.clear();
    } else {
      this.state.cellVolumeOverrides = new Map();
    }
    if (this.state.cellValidationMap instanceof Map) {
      this.state.cellValidationMap.clear();
    } else {
      this.state.cellValidationMap = new Map();
    }
    if (this.state.validationWarningRows instanceof Set) {
      this.state.validationWarningRows.clear();
    } else {
      this.state.validationWarningRows = new Set();
    }
    if (this.state.saveErrorRows instanceof Set) {
      this.state.saveErrorRows.clear();
    } else {
      this.state.saveErrorRows = new Set();
    }
    this.state.showCompletionWarnings = false;
  }

  _persistWeekBoundarySettings(weekStartDay, weekEndDay) {
    const endpoint = this.state.apiEndpoints?.weekBoundary;
    if (!endpoint) {
      return;
    }

    if (this._weekBoundarySaveTimer) {
      clearTimeout(this._weekBoundarySaveTimer);
    }
    this._pendingWeekBoundary = { weekStartDay, weekEndDay };

    this._weekBoundarySaveTimer = window.setTimeout(() => {
      this._weekBoundarySaveTimer = null;
      const payload = this._pendingWeekBoundary || { weekStartDay, weekEndDay };
      this._pendingWeekBoundary = null;
      const body = JSON.stringify({
        week_start_day: payload.weekStartDay,
        week_end_day: payload.weekEndDay,
      });

      fetch(endpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this._getCsrfToken(),
        },
        body,
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          return response.json();
        })
        .then((data) => {
          const resolvedStart =
            typeof data?.week_start_day !== 'undefined' ? data.week_start_day : payload.weekStartDay;
          const resolvedEnd =
            typeof data?.week_end_day !== 'undefined' ? data.week_end_day : payload.weekEndDay;
          this.state.weekStartDay = resolvedStart;
          this.state.weekEndDay = resolvedEnd;
          this._regenerateTimeline({
            mode: 'weekly',
            weekStartDay: resolvedStart,
            weekEndDay: resolvedEnd,
          });
        })
        .catch((error) => {
          console.warn('[JadwalKegiatanApp] Failed to persist week boundary setting', error);
        });
    }, 500);
  }

  async _regenerateTimeline(options = {}) {
    const { mode = 'weekly', weekStartDay, weekEndDay } = options;
    const endpoint = this.state.apiEndpoints?.regenerateTahapan;
    if (!endpoint) {
      return;
    }

    if (this._isRegeneratingTimeline) {
      this._queuedRegeneratePayload = { mode, weekStartDay, weekEndDay };
      return;
    }

    if (this.state.isDirty && this.state.modifiedCells instanceof Map && this.state.modifiedCells.size > 0) {
      const confirmed = window.confirm(
        'Mengubah batas minggu akan me-refresh data dan membatalkan perubahan yang belum disimpan. Lanjutkan?'
      );
      if (!confirmed) {
        return;
      }
      this._resetEditedCellsState();
      this.state.isDirty = false;
    }

    this._isRegeneratingTimeline = true;
    this.state.isLoading = true;
    const statusLabel = mode === 'monthly' ? 'Mengatur ulang struktur bulanan...' : 'Mengatur ulang struktur minggu...';
    this._updateStatusBar(statusLabel);
    const toastLabel =
      mode === 'monthly'
        ? 'Mengatur ulang kolom monthly...'
        : 'Mengatur ulang kolom weekly sesuai preferensi Anda...';
    this.showToast(toastLabel, 'info', 2400);

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this._getCsrfToken(),
        },
        body: JSON.stringify({
          mode,
          ...(mode === 'weekly'
            ? {
                week_start_day:
                  typeof weekStartDay === 'number' ? weekStartDay : this._getWeekStartDay(),
                week_end_day:
                  typeof weekEndDay === 'number' ? weekEndDay : this._getWeekEndDay(),
              }
            : {}),
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      this._invalidateCachedDataset();
      await this._loadInitialData({ forceReload: true });
      const successMessage =
        mode === 'monthly' ? 'Struktur monthly diperbarui (read-only)' : 'Periode minggu diperbarui';
      this.showToast(successMessage, 'success', 2200);
    } catch (error) {
      console.error('[JadwalKegiatanApp] Failed to regenerate weekly structure', error);
      this.showToast('Gagal memperbarui struktur waktu', 'danger', 3200);
    } finally {
      this.state.isLoading = false;
      this._updateStatusBar();
      this._isRegeneratingTimeline = false;
      if (this._queuedRegeneratePayload) {
        const next = this._queuedRegeneratePayload;
        this._queuedRegeneratePayload = null;
        this._regenerateTimeline(next);
      }
    }
  }

  _formatWeekdayLabel(pyDay) {
    const names = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu'];
    const normalized = this._normalizePythonWeekday(pyDay, 0);
    return names[normalized] || `Day ${normalized}`;
  }

  _syncToolbarRadios() {
    const displayMode = this.state.inputMode || 'percentage';
    document.querySelectorAll('input[name="displayMode"]').forEach((radio) => {
      radio.checked = radio.value === displayMode;
    });

    const timeScale = this.state.displayScale || this.state.timeScale || 'weekly';
    document.querySelectorAll('input[name="timeScale"]').forEach((radio) => {
      radio.checked = radio.value === timeScale;
    });
  }

  _handleDisplayModeChange(mode) {
    const normalized = (mode || '').toLowerCase();
    const allowed = new Set(['percentage', 'volume']);
    if (!allowed.has(normalized) || this.state.inputMode === normalized) {
      return;
    }

    this.state.inputMode = normalized;
    this.state.displayMode = normalized;  // Phase 2E.1: Keep displayMode in sync

    if (this.agGridManager) {
      this.agGridManager.setInputMode(normalized);
    }

    this._syncGridViews();

    const label = normalized === 'percentage' ? 'Persentase' : 'Volume';
    this.showToast(`Mode input diubah ke ${label}`, 'info', 2200);
  }

  /**
   * Handle progress mode change (Phase 2E.1: Planned vs Actual)
   * @param {string} mode - 'planned' or 'actual'
   */
  _handleProgressModeChange(mode) {
    const normalized = (mode || '').toLowerCase();
    const allowed = new Set(['planned', 'actual']);

    if (!allowed.has(normalized) || this.state.progressMode === normalized) {
      return;
    }

    const oldMode = this.state.progressMode;
    console.log(`[ModeChange] Switching progress mode from ${oldMode} to ${normalized}`);

    // Phase 2E.1: Save state sizes before switch for debugging
    const oldState = this._getCurrentModeState();
    const oldModifiedSize = oldState.modifiedCells.size;
    const oldAssignmentSize = oldState.assignmentMap.size;

    // Switch mode - property delegation will now point to new mode's state
    this.state.progressMode = normalized;

    // Log new state after switch
    const newState = this._getCurrentModeState();
    console.log(`[ModeChange] State switch complete:`);
    console.log(`  - Old ${oldMode.toUpperCase()}: ${oldModifiedSize} modified, ${oldAssignmentSize} assignments`);
    console.log(`  - New ${normalized.toUpperCase()}: ${newState.modifiedCells.size} modified, ${newState.assignmentMap.size} assignments`);

    // Update mode indicator badge
    const indicator = document.getElementById('progress-mode-indicator');
    if (indicator) {
      const label = normalized === 'planned' ? 'Perencanaan' : 'Realisasi';
      const bgClass = normalized === 'planned' ? 'bg-info' : 'bg-warning';
      indicator.textContent = `Mode: ${label}`;
      indicator.className = `badge ${bgClass} ms-2`;
      indicator.style.cssText = 'font-size: 0.75rem; vertical-align: middle;';
    }

    // Reload data with the new progress mode (will load from new mode's state)
    this._syncGridViews();

    const label = normalized === 'planned' ? 'Perencanaan' : 'Realisasi';
    this.showToast(`Mode progress diubah ke ${label}`, 'info', 2200);
  }

  _handleTimeScaleChange(nextScale) {
    const normalized = (nextScale || '').toLowerCase();
    const allowed = new Set(['weekly', 'monthly']);
    if (!allowed.has(normalized)) {
      this._syncToolbarRadios();
      this.showToast('Mode waktu ini belum aktif pada fase saat ini', 'warning', 3200);
      return;
    }

    if ((this.state.displayScale || this.state.timeScale || 'weekly') === normalized) {
      this._syncToolbarRadios();
      return;
    }

    this.state.displayScale = normalized;
    this._syncToolbarRadios();
    this._syncGridViews();
    this._renderGrid();
    this._updateCharts();

    if (normalized === 'weekly') {
      this.showToast('Time scale diatur ke Weekly', 'info', 2000);
    } else {
      this.showToast('Time scale diatur ke Monthly (akumulasi 4 minggu, read-only)', 'info', 2600);
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
        getCellValidationState: (cellKey) => this._getCellValidationState(cellKey),
      });
      this.agGridManager.mount(container);
    }
  }

  /**
   * Load initial data from server
   */
  async _loadInitialData(options = {}) {
    const { forceReload = false } = options;
    // Check if data is already loaded (from Django template)
    if (!forceReload && this.state.pekerjaanTree?.length > 0) {
      console.log('[JadwalKegiatanApp] Using template dataset');
      console.log('Preloaded pekerjaanTree items:', this.state.pekerjaanTree.length);
      console.log('Preloaded tahapanList items:', this.state.tahapanList?.length || 0);
      console.log('Preloaded timeColumns items:', this.state.timeColumns?.length || 0);
      this._recalculateAllProgressTotals();
      this._syncGridViews();
      return;
    }

    // Initialize modern modules
    this.state.apiBase = this.state.apiEndpoints?.tahapan || `/detail_project/api/project/${this.state.projectId}/tahapan/`;
    this.dataLoader = new DataLoader(this.state);
    this.timeColumnGenerator = new TimeColumnGenerator(this.state);
    this.gridRenderer = new GridRenderer(this.state);
    this.saveHandler = new SaveHandler(this.state, {
      apiUrl: this.state.apiEndpoints?.save || `/detail_project/api/project/${this.state.projectId}/pekerjaan/assign_weekly/`,
      onSuccess: (result) => this._onSaveSuccess(result),
      onError: (error) => this._onSaveError(error),
      showToast: (msg, type) => this.showToast(msg, type)
    });

    this.state.isLoading = true;

    try {
      console.log('[JadwalKegiatanApp] Loading data using modern DataLoader...');

      // Step 1: Load all base data (tahapan, pekerjaan, volumes)
      await this.dataLoader.loadAllData({ skipIfLoaded: false });

      // Step 2: Generate time columns from loaded tahapan
      this.timeColumnGenerator.generate();
      const normalizedDisplayScale = (this.state.displayScale || this.state.timeScale || 'weekly').toLowerCase();
      if (!this._isEnforcingWeekly && normalizedDisplayScale === 'weekly') {
        const weeklyCount = this._countWeeklyColumns();
        const expectedWeeks = this._estimateExpectedWeeklyColumns();
        const firstColumnMode =
          (this.state.timeColumns?.[0]?.generationMode || this.state.timeColumns?.[0]?.type || '').toLowerCase();

        const shouldForceWeekly =
          weeklyCount === 0 ||
          firstColumnMode === 'monthly' ||
          (expectedWeeks > 0 && weeklyCount > 0 && weeklyCount < expectedWeeks);

        if (shouldForceWeekly) {
          console.warn('[JadwalKegiatanApp] Weekly columns incomplete; regenerating weekly structure based on project timeline...');
          this._isEnforcingWeekly = true;
          await this._regenerateTimeline({
            mode: 'weekly',
            weekStartDay: this._getWeekStartDay(),
            weekEndDay: this._getWeekEndDay(),
          });
          this._isEnforcingWeekly = false;
          return;
        }
      }

      // Step 3: Load assignments (depends on time columns)
      await this.dataLoader.loadAssignments();
      this._recalculateAllProgressTotals();

      // Step 3.5: Load Kurva S harga data (Phase 2F.0)
      await this._loadKurvaSData();

      // Build time column index for quick lookup
      this.state.timeColumnIndex = this._createTimeColumnIndex(this.state.timeColumns);

      console.log(
        `[JadwalKegiatanApp] ✅ Data loaded successfully:`,
        `${this.state.flatPekerjaan?.length || 0} pekerjaan,`,
        `${this.state.tahapanList?.length || 0} tahapan,`,
        `${this.state.timeColumns?.length || 0} columns`
      );

      // Step 4: Render grid
      this._renderGrid();

      // Step 5: Initialize and update charts
      this._initializeCharts();
      this._updateCharts();

    } catch (error) {
      console.error('[JadwalKegiatanApp] ❌ Failed to load data:', error);
      this.state.error = error;
      this.showToast('Gagal memuat data: ' + error.message, 'danger');
    } finally {
      this.state.isLoading = false;
      this._syncGridViews();
    }
  }

  /**
   * Load Kurva S harga data from API (Phase 2F.0)
   *
   * Loads harga-based data for Kurva S chart instead of volume-based.
   * This fixes the calculation to use cost (Rupiah) instead of physical volume.
   *
   * @private
   */
  async _loadKurvaSData() {
    try {
      const apiUrl = `/detail_project/api/v2/project/${this.state.projectId}/kurva-s-data/`;

      console.log('[JadwalKegiatanApp] Loading Kurva S harga data from:', apiUrl);

      const response = await fetch(apiUrl, {
        credentials: 'same-origin',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      // Store harga data in state
      this.state.hargaMap = new Map(
        Object.entries(data.hargaMap || {}).map(([k, v]) => [k, parseFloat(v) || 0])
      );
      this.state.totalBiayaProject = parseFloat(data.totalBiayaProject || 0);
      this.state.pekerjaanMeta = data.pekerjaanMeta || {};

      // Update volumeMap if needed (backward compatibility)
      if (data.volumeMap && Object.keys(data.volumeMap).length > 0) {
        const existingSize = this.state.volumeMap?.size || 0;
        if (existingSize === 0) {
          this.state.volumeMap = new Map(
            Object.entries(data.volumeMap).map(([k, v]) => [k, parseFloat(v) || 0])
          );
        }
      }

      console.log('[JadwalKegiatanApp] ✅ Kurva S data loaded:', {
        hargaCount: this.state.hargaMap.size,
        totalBiaya: this.state.totalBiayaProject,
        totalBiayaFormatted: `Rp ${this.state.totalBiayaProject.toLocaleString('id-ID')}`,
      });

    } catch (error) {
      console.error('[JadwalKegiatanApp] ⚠️ Failed to load Kurva S data:', error);
      // Fallback: use empty maps (Kurva S will use fallback calculation)
      this.state.hargaMap = this.state.hargaMap || new Map();
      this.state.totalBiayaProject = this.state.totalBiayaProject || 0;
      this.state.pekerjaanMeta = this.state.pekerjaanMeta || {};

      // Don't show error toast - this is non-critical, Kurva S has fallback
      console.warn('[JadwalKegiatanApp] Kurva S will use fallback calculation');
    }
  }

  /**
   * Render grid using GridRenderer
   * @private
   */
  _renderGrid() {
    if (!this.gridRenderer) {
      console.warn('[JadwalKegiatanApp] GridRenderer not initialized');
      return;
    }

    this.state.activeTimeColumns = this._getDisplayTimeColumns();

    console.log('[JadwalKegiatanApp] Rendering grid...');

    // Render tables
    const rendered = this.gridRenderer.renderTables();
    if (!rendered) {
      console.warn('[JadwalKegiatanApp] Grid rendering returned null');
      return;
    }

    const { leftHTML, rightHTML } = rendered;

    // Update DOM
    const leftTbody = this.state.domRefs?.leftTbody || document.getElementById('left-tbody');
    const rightTbody = this.state.domRefs?.rightTbody || document.getElementById('right-tbody');

    if (leftTbody) {
      leftTbody.innerHTML = leftHTML;
    }

    if (rightTbody) {
      rightTbody.innerHTML = rightHTML;
    }

    // Render time headers
    const timeHeaderRow = this.state.domRefs?.timeHeaderRow || document.getElementById('time-header-row');
    if (timeHeaderRow) {
      this.gridRenderer.renderTimeHeader(timeHeaderRow);
    }

    // Sync row heights
    this.gridRenderer.syncRowHeights(this.state.domRefs || {});
    this._updateLegacyHorizontalScroll();

    console.log('[JadwalKegiatanApp] ✅ Grid rendered');

    this._updateStatusBar();
  }

  /**
   * Initialize chart modules
   * @private
   */
  _initializeCharts() {
    console.log('[JadwalKegiatanApp] Initializing charts...');

    // Initialize Kurva-S Chart
    if (this.state.domRefs?.scurveChart) {
      try {
        this.kurvaSChart = new KurvaSChart(this.state, {
          useIdealCurve: true,
          steepnessFactor: 0.8,
          smoothCurves: true,
          showArea: true,
        });
        const success = this.kurvaSChart.initialize(this.state.domRefs.scurveChart);
        if (success) {
          console.log('[JadwalKegiatanApp] ✅ Kurva-S chart initialized');
        }
      } catch (error) {
        console.warn('[JadwalKegiatanApp] Failed to initialize Kurva-S chart:', error);
      }
    }

    // Initialize Gantt Chart
    if (this.state.domRefs?.ganttChart) {
      try {
        this.ganttChart = new GanttChart(this.state, {
          viewMode: 'Week',
          enableThemeObserver: true,
        });
        const success = this.ganttChart.initialize(this.state.domRefs.ganttChart);
        if (success) {
          console.log('[JadwalKegiatanApp] ✅ Gantt chart initialized');
        }
      } catch (error) {
        console.warn('[JadwalKegiatanApp] Failed to initialize Gantt chart:', error);
      }
    }
  }

  /**
   * Update charts with current data
   * @private
   */
  _updateCharts() {
    console.log('[JadwalKegiatanApp] Updating charts...');

    // Update Kurva-S Chart
    if (this.kurvaSChart) {
      try {
        this.kurvaSChart.update();
        console.log('[JadwalKegiatanApp] ✅ Kurva-S chart updated');
      } catch (error) {
        console.warn('[JadwalKegiatanApp] Failed to update Kurva-S chart:', error);
      }
    }

    // Update Gantt Chart
    if (this.ganttChart) {
      try {
        this.ganttChart.update();
        console.log('[JadwalKegiatanApp] ✅ Gantt chart updated');
      } catch (error) {
        console.warn('[JadwalKegiatanApp] Failed to update Gantt chart:', error);
      }
    }
  }

  /**
   * Save changes to server (using modern SaveHandler)
   */
  async saveChanges() {
    if (!this.saveHandler) {
      console.error('[JadwalKegiatanApp] SaveHandler not initialized');
      return;
    }

    if (!this._validateRowTotalsBeforeSave()) {
      return;
    }

    // Delegate to SaveHandler
    const result = await this.saveHandler.save();

    // Re-render grid after save
    if (result.success) {
      this._renderGrid();
      this._recalculateAllProgressTotals();
    }
  }

  /**
   * Handle successful save
   * @param {Object} result - Save result
   * @private
   */
  _onSaveSuccess(result) {
    console.log('[JadwalKegiatanApp] Save completed successfully');
    this.state.isDirty = false;
    this._clearSaveErrorRows();

    // Update status bar if exists
    this._updateStatusBar('Perubahan tersimpan');
    this._clearApiFailedRows();

    // Re-render grid to update UI
    this._renderGrid();
    this._recalculateAllProgressTotals();

    // Update charts with new data
    this._updateCharts();
  }

  /**
   * Handle save error
   * @param {Error} error - Error object
   * @private
   */
  _onSaveError(error) {
    console.error('[JadwalKegiatanApp] Save failed:', error);
    // Error toast already shown by SaveHandler
    this._markFailedRowsFromError(error);
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
    this._resetEditedCellsState();
    this.state.isDirty = false;

    await this._loadInitialData({ forceReload: true });
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
    const displayColumns = this._getDisplayTimeColumns();
    this.state.activeTimeColumns = displayColumns;

    if (this.agGridManager) {
      this.agGridManager.updateData({
        tree: this.state.pekerjaanTree || [],
        timeColumns: displayColumns,
        inputMode: this.state.inputMode || 'percentage',
        timeScale: this.state.displayScale || this.state.timeScale || 'weekly',
      });
      if (typeof this.agGridManager.updateTopScrollMetrics === 'function') {
        this.agGridManager.updateTopScrollMetrics();
      }
    }
    this._updateLegacyHorizontalScroll();
  }

  _updateLegacyHorizontalScroll() {
    const domRefs = this.state?.domRefs || {};
    const scrollTop = domRefs.horizontalScrollTop;
    const scrollInner = domRefs.horizontalScrollInner;
    const rightTable = domRefs.rightTable;
    if (!scrollTop || !scrollInner || !rightTable) {
      return;
    }
    window.requestAnimationFrame(() => {
      scrollInner.style.width = `${rightTable.scrollWidth}px`;
    });
  }

  _clearApiFailedRows() {
    if (this.state.apiFailedRows instanceof Set && this.state.apiFailedRows.size > 0) {
      this.state.apiFailedRows.clear();
      this._refreshFailedRowsUnion();
    }
  }

  _markFailedRowsFromIds(idSet) {
    if (!(idSet instanceof Set) || idSet.size === 0) {
      this._clearApiFailedRows();
      return;
    }
    this.state.apiFailedRows = new Set(Array.from(idSet));
    this._refreshFailedRowsUnion();
  }

  _setSaveErrorRows(idSet) {
    if (!(this.state.saveErrorRows instanceof Set)) {
      this.state.saveErrorRows = new Set();
    }
    const normalized = idSet instanceof Set ? Array.from(idSet) : [];
    this.state.saveErrorRows = new Set(normalized.map((id) => Number(id)));
    if (this.agGridManager && typeof this.agGridManager.refreshRowStyles === 'function') {
      this.agGridManager.refreshRowStyles();
    }
  }

  _clearSaveErrorRows() {
    if (this.state.saveErrorRows instanceof Set && this.state.saveErrorRows.size > 0) {
      this.state.saveErrorRows.clear();
      if (this.agGridManager && typeof this.agGridManager.refreshRowStyles === 'function') {
        this.agGridManager.refreshRowStyles();
      }
    }
  }

  _clearSaveErrorForRow(pekerjaanId) {
    if (
      !pekerjaanId ||
      !(this.state.saveErrorRows instanceof Set) ||
      this.state.saveErrorRows.size === 0
    ) {
      return;
    }
    const removed = this.state.saveErrorRows.delete(Number(pekerjaanId));
    if (removed && this.agGridManager && typeof this.agGridManager.refreshRowStyles === 'function') {
      this.agGridManager.refreshRowStyles();
    }
  }

  _markFailedRowsFromError(error) {
    const ids = this._extractPekerjaanIdsFromError(error);
    this._markFailedRowsFromIds(ids);
  }

  _extractPekerjaanIdsFromError(error) {
    const idSet = new Set();
    const collect = (items = []) => {
      items.forEach((item) => {
        const pekerjaanId =
          item?.pekerjaan_id ||
          item?.pekerjaanId ||
          item?.item?.pekerjaan_id ||
          item?.item?.pekerjaanId ||
          null;
        if (pekerjaanId) {
          idSet.add(Number(pekerjaanId));
        }
      });
    };

    if (Array.isArray(error?.validationErrors)) {
      collect(error.validationErrors);
    }
    if (Array.isArray(error?.details)) {
      collect(error.details);
    }

    return idSet;
  }

  _getContainerValue(container, key) {
    if (!container || !key) {
      return null;
    }
    if (container instanceof Map) {
      return container.has(key) ? container.get(key) : null;
    }
    if (typeof container === 'object') {
      return Object.prototype.hasOwnProperty.call(container, key) ? container[key] : null;
    }
    return null;
  }

  _calculateRowTotalPercent(pekerjaanId) {
    if (!pekerjaanId) {
      return 0;
    }
    const columns = this.state.timeColumns || [];
    const modifiedCells = this.state.modifiedCells instanceof Map ? this.state.modifiedCells : null;
    const assignmentMap = this.state.assignmentMap;
    let total = 0;

    columns.forEach((col) => {
      const fieldKey = col.fieldId || col.id;
      if (!fieldKey) {
        return;
      }
      const cellKey = `${pekerjaanId}-${fieldKey}`;
      let value = null;
      if (modifiedCells && modifiedCells.has(cellKey)) {
        value = modifiedCells.get(cellKey);
      } else {
        value = this._getContainerValue(assignmentMap, cellKey);
      }
      const numeric = Number(value);
      if (Number.isFinite(numeric)) {
        total += numeric;
      }
    });

    return Number(total.toFixed(2));
  }

  _calculateRowTotalVolume(pekerjaanId) {
    if (!pekerjaanId) {
      return 0;
    }
    const kapasitas = this._getRowVolume(pekerjaanId);
    const columns = Array.isArray(this.state.timeColumns) ? this.state.timeColumns : [];
    const modifiedCells = this.state.modifiedCells instanceof Map ? this.state.modifiedCells : null;
    const assignmentMap = this.state.assignmentMap;
    const overrides = this.state.cellVolumeOverrides instanceof Map ? this.state.cellVolumeOverrides : null;

    let totalVolume = 0;
    columns.forEach((col) => {
      const fieldKey = col.fieldId || col.id;
      if (!fieldKey) {
        return;
      }
      const cellKey = `${pekerjaanId}-${fieldKey}`;
      let volumeValue = null;

      if (overrides && overrides.has(cellKey)) {
        const overrideValue = Number(overrides.get(cellKey));
        if (Number.isFinite(overrideValue)) {
          volumeValue = overrideValue;
        }
      }

      if (volumeValue === null) {
        let percentValue = null;
        if (modifiedCells && modifiedCells.has(cellKey)) {
          percentValue = Number(modifiedCells.get(cellKey));
        } else if (assignmentMap) {
          percentValue = Number(this._getContainerValue(assignmentMap, cellKey));
        }

        if (Number.isFinite(percentValue) && Number.isFinite(kapasitas) && kapasitas > 0) {
          volumeValue = (percentValue / 100) * kapasitas;
        }
      }

      if (Number.isFinite(volumeValue)) {
        totalVolume += volumeValue;
      }
    });

    return Number(totalVolume.toFixed(3));
  }

  _setCellVolumeOverride(cellKey, volumeValue) {
    if (!cellKey) {
      return;
    }
    if (!(this.state.cellVolumeOverrides instanceof Map)) {
      this.state.cellVolumeOverrides = new Map();
    }
    const numeric = Number(volumeValue);
    if (Number.isFinite(numeric)) {
      this.state.cellVolumeOverrides.set(cellKey, Number(numeric.toFixed(3)));
    } else if (this.state.cellVolumeOverrides.has(cellKey)) {
      this.state.cellVolumeOverrides.delete(cellKey);
    }
  }

  _clearCellVolumeOverride(cellKey) {
    if (
      !cellKey ||
      !(this.state.cellVolumeOverrides instanceof Map) ||
      this.state.cellVolumeOverrides.size === 0
    ) {
      return;
    }
    this.state.cellVolumeOverrides.delete(cellKey);
  }

  _updateCellValidationState(cellKey, validationResult) {
    if (!cellKey) {
      return;
    }
    if (!(this.state.cellValidationMap instanceof Map)) {
      this.state.cellValidationMap = new Map();
    }
    const current = this.state.cellValidationMap.get(cellKey) || null;
    const nextState =
      validationResult && validationResult.isValid === false
        ? validationResult.level === 'warning'
          ? 'warning'
          : 'error'
        : null;
    let changed = false;
    if (nextState) {
      if (current !== nextState) {
        this.state.cellValidationMap.set(cellKey, nextState);
        changed = true;
      }
    } else if (current) {
      this.state.cellValidationMap.delete(cellKey);
      changed = true;
    }
    if (changed && this.agGridManager && typeof this.agGridManager.refreshCells === 'function') {
      this.agGridManager.refreshCells();
    }
  }

  _getCellValidationState(cellKey) {
    if (!cellKey || !(this.state.cellValidationMap instanceof Map)) {
      return null;
    }
    return this.state.cellValidationMap.get(cellKey) || null;
  }

  _updateProgressTotals(pekerjaanId) {
    if (!pekerjaanId) {
      return 0;
    }
    if (!(this.state.progressTotals instanceof Map)) {
      this.state.progressTotals = new Map();
    }
    const total = this._calculateRowTotalPercent(pekerjaanId);
    this.state.progressTotals.set(Number(pekerjaanId), total);
    this._updateAutoWarningRows(Number(pekerjaanId), total);
    this._updateCompletionWarningRows(Number(pekerjaanId), total);
    this._updateStatusBar();
    return total;
  }

  _updateVolumeTotals(pekerjaanId, percentOverride = null, options = {}) {
    if (!pekerjaanId) {
      return;
    }
    if (!(this.state.volumeTotals instanceof Map)) {
      this.state.volumeTotals = new Map();
    }
    const totalVolume = this._calculateRowTotalVolume(pekerjaanId);
    this.state.volumeTotals.set(Number(pekerjaanId), totalVolume);

    const percentTotal =
      Number.isFinite(percentOverride) && percentOverride !== null
        ? Number(percentOverride)
        : this.state.progressTotals instanceof Map
          ? this.state.progressTotals.get(Number(pekerjaanId))
          : null;

    const kapasitas = this._getRowVolume(pekerjaanId);
    const derivedPercent =
      !Number.isFinite(percentTotal) && Number.isFinite(totalVolume) && Number.isFinite(kapasitas) && kapasitas > 0
        ? (totalVolume / kapasitas) * 100
        : percentTotal;

    this._updateVolumeWarningRows(Number(pekerjaanId), totalVolume, {
      percentTotal: derivedPercent,
      deferRefresh: options.deferRefresh,
    });
  }

  _recalculateAllProgressTotals() {
    if (!(this.state.progressTotals instanceof Map)) {
      this.state.progressTotals = new Map();
    } else {
      this.state.progressTotals.clear();
    }
    if (!(this.state.volumeTotals instanceof Map)) {
      this.state.volumeTotals = new Map();
    } else {
      this.state.volumeTotals.clear();
    }
    if (!(this.state.cellVolumeOverrides instanceof Map)) {
      this.state.cellVolumeOverrides = new Map();
    } else {
      this.state.cellVolumeOverrides.clear();
    }
    this.state.autoWarningRows = new Set();
    this.state.volumeWarningRows = new Set();
    this.state.validationWarningRows = new Set();
    this.state.saveErrorRows = new Set();

    const pekerjaanNodes = Array.isArray(this.state.flatPekerjaan)
      ? this.state.flatPekerjaan.filter((node) => node?.type === 'pekerjaan' && node.id)
      : [];

    pekerjaanNodes.forEach((node) => {
      const total = this._calculateRowTotalPercent(node.id);
      this.state.progressTotals.set(Number(node.id), total);
      this._updateAutoWarningRows(Number(node.id), total, { deferRefresh: true });
      this._updateCompletionWarningRows(Number(node.id), total, { deferRefresh: true });
      this._updateVolumeTotals(Number(node.id), total, { deferRefresh: true });
    });

    this._refreshFailedRowsUnion();
    if (this.state.showCompletionWarnings && this.agGridManager) {
      this.agGridManager.refreshRowStyles();
    }
    this._updateStatusBar();
  }

  _refreshFailedRowsUnion() {
    const union = new Set();
    if (this.state.autoWarningRows instanceof Set) {
      this.state.autoWarningRows.forEach((id) => union.add(Number(id)));
    }
    if (this.state.volumeWarningRows instanceof Set) {
      this.state.volumeWarningRows.forEach((id) => union.add(Number(id)));
    }
    if (this.state.apiFailedRows instanceof Set) {
      this.state.apiFailedRows.forEach((id) => union.add(Number(id)));
    }
    if (this.state.saveErrorRows instanceof Set) {
      this.state.saveErrorRows.forEach((id) => union.add(Number(id)));
    }
    this.state.failedRows = union;
    this._updateSaveButtonState();
    if (this.agGridManager && typeof this.agGridManager.refreshRowStyles === 'function') {
      this.agGridManager.refreshRowStyles();
    }
  }

  _updateAutoWarningRows(pekerjaanId, totalPercent, options = {}) {
    if (!pekerjaanId) {
      return;
    }
    if (!(this.state.autoWarningRows instanceof Set)) {
      this.state.autoWarningRows = new Set();
    }
    const tolerance = 0.01;
    let changed = false;
    if (totalPercent > 100 + tolerance) {
      if (!this.state.autoWarningRows.has(pekerjaanId)) {
        this.state.autoWarningRows.add(pekerjaanId);
        changed = true;
      }
    } else if (this.state.autoWarningRows.has(pekerjaanId)) {
      this.state.autoWarningRows.delete(pekerjaanId);
      changed = true;
    }

    if (changed && !options.deferRefresh) {
      this._refreshFailedRowsUnion();
    }
  }

  _updateCompletionWarningRows(pekerjaanId, totalPercent, options = {}) {
    if (!pekerjaanId) {
      return;
    }
    if (!(this.state.validationWarningRows instanceof Set)) {
      this.state.validationWarningRows = new Set();
    }
    const tolerance = 0.01;
    const upperBound = 100 - tolerance;
    const shouldWarn =
      this.state.showCompletionWarnings &&
      Number.isFinite(totalPercent) &&
      totalPercent > tolerance &&
      totalPercent < upperBound;

    let changed = false;
    if (shouldWarn) {
      if (!this.state.validationWarningRows.has(pekerjaanId)) {
        this.state.validationWarningRows.add(pekerjaanId);
        changed = true;
      }
    } else if (this.state.validationWarningRows.has(pekerjaanId)) {
      this.state.validationWarningRows.delete(pekerjaanId);
      changed = true;
    }

    if (changed && !options.deferRefresh && this.agGridManager) {
      this.agGridManager.refreshRowStyles();
    }
  }

  _recomputeCompletionWarnings() {
    if (!(this.state.validationWarningRows instanceof Set)) {
      this.state.validationWarningRows = new Set();
    } else {
      this.state.validationWarningRows.clear();
    }
    if (!(this.state.progressTotals instanceof Map)) {
      if (this.agGridManager) {
        this.agGridManager.refreshRowStyles();
      }
      return;
    }
    this.state.progressTotals.forEach((total, pekerjaanId) => {
      this._updateCompletionWarningRows(Number(pekerjaanId), total, { deferRefresh: true });
    });
    if (this.agGridManager) {
      this.agGridManager.refreshRowStyles();
    }
  }

  _updateVolumeWarningRows(pekerjaanId, totalVolume, options = {}) {
    if (!pekerjaanId) {
      return;
    }
    if (!(this.state.volumeWarningRows instanceof Set)) {
      this.state.volumeWarningRows = new Set();
    }

    const capacity = this._getRowVolume(pekerjaanId);
    const percentReference =
      options && Number.isFinite(options.percentTotal)
        ? Number(options.percentTotal)
        : this.state.progressTotals instanceof Map
          ? this.state.progressTotals.get(Number(pekerjaanId))
          : null;

    const tolerance = Number.isFinite(capacity) && capacity > 0 ? Math.max(capacity * 0.001, 0.01) : 0.01;
    let shouldWarn = false;
    if (Number.isFinite(capacity) && capacity > 0) {
      shouldWarn = Number.isFinite(totalVolume) && totalVolume > capacity + tolerance;
    } else if (Number.isFinite(percentReference)) {
      shouldWarn = percentReference > tolerance;
    }

    let changed = false;
    if (shouldWarn) {
      if (!this.state.volumeWarningRows.has(pekerjaanId)) {
        this.state.volumeWarningRows.add(pekerjaanId);
        changed = true;
      }
    } else if (this.state.volumeWarningRows.has(pekerjaanId)) {
      this.state.volumeWarningRows.delete(pekerjaanId);
      changed = true;
    }

    if (changed && !options.deferRefresh) {
      this._refreshFailedRowsUnion();
    }
  }

  _clearFailedRows() {
    if (this.state.autoWarningRows instanceof Set) {
      this.state.autoWarningRows.clear();
    }
    if (this.state.volumeWarningRows instanceof Set) {
      this.state.volumeWarningRows.clear();
    }
    if (this.state.failedRows instanceof Set) {
      this.state.failedRows.clear();
    }
    if (this.state.saveErrorRows instanceof Set) {
      this.state.saveErrorRows.clear();
    }
    this._refreshFailedRowsUnion();
  }

  _getRowVolume(pekerjaanId) {
    const volumeMap = this.state?.volumeMap;
    const numericId = Number(pekerjaanId);
    if (volumeMap instanceof Map && volumeMap.has(numericId)) {
      return Number(volumeMap.get(numericId)) || 0;
    }
    if (volumeMap && typeof volumeMap === 'object') {
      const key = String(numericId);
      if (Object.prototype.hasOwnProperty.call(volumeMap, key)) {
        return Number(volumeMap[key]) || 0;
      }
    }
    const fallbackNode =
      Array.isArray(this.state.flatPekerjaan) &&
      this.state.flatPekerjaan.find((node) => Number(node.id) === numericId);
    if (fallbackNode && typeof fallbackNode.volume !== 'undefined') {
      return Number(fallbackNode.volume) || 0;
    }
    return 0;
  }

  _validateRowTotalsBeforeSave() {
    if (!(this.state.progressTotals instanceof Map)) {
      return true;
    }
    if (!this.state.showCompletionWarnings) {
      this.state.showCompletionWarnings = true;
    }
    this._recomputeCompletionWarnings();
    const percentTolerance = 0.01;
    const percentViolations = [];

    this.state.progressTotals.forEach((totalPercent, pekerjaanId) => {
      if (!Number.isFinite(totalPercent)) {
        return;
      }
      if (totalPercent > 100 + percentTolerance) {
        percentViolations.push({
          type: 'percent',
          pekerjaan_id: pekerjaanId,
          total: totalPercent,
        });
      }
    });

    const volumeViolations = [];
    if (this.state.volumeTotals instanceof Map) {
      this.state.volumeTotals.forEach((totalVolume, pekerjaanId) => {
        const capacity = this._getRowVolume(pekerjaanId);
        const volumeTolerance = Number.isFinite(capacity) && capacity > 0 ? Math.max(capacity * 0.001, 0.01) : 0.01;
        const percentTotal =
          this.state.progressTotals instanceof Map && this.state.progressTotals.has(pekerjaanId)
            ? this.state.progressTotals.get(pekerjaanId)
            : null;
        const effectivePercent =
          Number.isFinite(percentTotal) && percentTotal !== null
            ? Number(percentTotal)
            : Number.isFinite(totalVolume) && Number.isFinite(capacity) && capacity > 0
              ? (Number(totalVolume) / Number(capacity)) * 100
              : null;
        if (Number.isFinite(capacity) && capacity > 0) {
          if (Number.isFinite(totalVolume) && totalVolume > capacity + volumeTolerance) {
            volumeViolations.push({
              type: 'volume',
              pekerjaan_id: pekerjaanId,
              total: totalVolume,
              capacity,
            });
          }
        } else {
          if (Number.isFinite(effectivePercent) && effectivePercent > volumeTolerance) {
            volumeViolations.push({
              type: 'volume',
              pekerjaan_id: pekerjaanId,
              total: totalVolume,
              capacity: capacity || 0,
              missingCapacity: true,
            });
          }
        }
      });
    }

    if (percentViolations.length === 0 && volumeViolations.length === 0) {
      this._clearFailedRows();
      this._clearSaveErrorRows();
      return true;
    }

    const ids = new Set();
    const combined = percentViolations.concat(volumeViolations);
    const messages = combined.slice(0, 3).map((item) => {
      ids.add(Number(item.pekerjaan_id));
      if (item.type === 'volume') {
        if (item.missingCapacity) {
          return `- Pekerjaan ${item.pekerjaan_id}: volume tidak dapat disimpan karena master volume 0`;
        }
        return `- Pekerjaan ${item.pekerjaan_id}: total volume ${item.total.toFixed(3)} > kapasitas ${item.capacity.toFixed(3)}`;
      }
      return `- Pekerjaan ${item.pekerjaan_id}: total ${item.total.toFixed(2)}% > 100%`;
    });

    if (combined.length > 3) {
      messages.push(`(+${combined.length - 3} lagi)`);
    }

    this._markFailedRowsFromIds(ids);
    this._setSaveErrorRows(ids);
    this.showToast(`Tidak dapat menyimpan:\n${messages.join('\n')}`, 'danger', 5000);
    return false;
  }

  _updateStatusBar(message = 'Ready') {
    const domRefs = this.state?.domRefs || {};
    const hasElements =
      domRefs.statusMessageEl || domRefs.itemCountEl || domRefs.modifiedCountEl || domRefs.totalProgressEl;
    if (!hasElements) {
      return;
    }

    if (domRefs.statusMessageEl && typeof message === 'string') {
      domRefs.statusMessageEl.textContent = message;
    }

    if (domRefs.itemCountEl) {
      const pekerjaanCount = Array.isArray(this.state?.flatPekerjaan)
        ? this.state.flatPekerjaan.filter((node) => node?.type === 'pekerjaan').length
        : 0;
      domRefs.itemCountEl.textContent = pekerjaanCount.toLocaleString('id-ID');
    }

    if (domRefs.modifiedCountEl) {
      const modifiedCount = this.state?.modifiedCells instanceof Map ? this.state.modifiedCells.size : 0;
      domRefs.modifiedCountEl.textContent = modifiedCount.toLocaleString('id-ID');
    }

    if (domRefs.totalProgressEl) {
      const totalProgress = this._calculateProjectProgress();
      domRefs.totalProgressEl.textContent =
        totalProgress === null
          ? '-'
          : `${totalProgress.toLocaleString('id-ID', { maximumFractionDigits: 1 })}%`;
    }
  }

  _calculateProjectProgress() {
    if (this.state?.progressTotals instanceof Map && this.state.progressTotals.size > 0) {
      let aggregate = 0;
      this.state.progressTotals.forEach((value) => {
        aggregate += Number(value) || 0;
      });
      const avg = aggregate / this.state.progressTotals.size;
      return Math.round(avg * 10) / 10;
    }

    if (this.state?.assignmentMap instanceof Map && this.state.assignmentMap.size > 0) {
      const pekerjaanTotals = new Map();
      this.state.assignmentMap.forEach((value, cellKey) => {
        const [pekerjaanId] = `${cellKey}`.split('-');
        const numericValue = Number(value) || 0;
        const current = pekerjaanTotals.get(pekerjaanId) || 0;
        pekerjaanTotals.set(pekerjaanId, current + numericValue);
      });

      if (pekerjaanTotals.size > 0) {
        let sum = 0;
        pekerjaanTotals.forEach((value) => {
          sum += value;
        });
        const avg = sum / pekerjaanTotals.size;
        return Math.round(avg * 10) / 10;
      }
    }

    return null;
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

  _normalizePythonWeekday(value, fallback = 0) {
    const fallbackSafe = Number.isFinite(fallback) ? ((fallback % 7) + 7) % 7 : 0;
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      return fallbackSafe;
    }
    const normalized = parsed % 7;
    return normalized < 0 ? normalized + 7 : normalized;
  }

  _getWeekStartDay() {
    if (Number.isFinite(Number(this.state?.weekStartDay))) {
      return this._normalizePythonWeekday(this.state.weekStartDay, (this._getWeekEndDay() + 1) % 7);
    }
    return (this._getWeekEndDay() + 1) % 7;
  }

  _getWeekEndDay() {
    return this._normalizePythonWeekday(this.state?.weekEndDay, 6);
  }

  _getDisplayTimeColumns() {
    const baseColumns = Array.isArray(this.state.timeColumns) ? this.state.timeColumns : [];
    const scale = (this.state.displayScale || this.state.timeScale || 'weekly').toLowerCase();
    if (scale !== 'monthly') {
      return baseColumns;
    }

    const isWeeklyColumn = (col) => {
      const mode = (col.generationMode || col.type || '').toLowerCase();
      if (mode === 'monthly') {
        return false;
      }
      if (mode === 'weekly' || mode === 'week' || mode === 'wk') {
        return true;
      }
      if (Number.isFinite(Number(col.weekNumber ?? col.week_number))) {
        return true;
      }
      const label = (col.label || '').toLowerCase();
      return label.includes('week') || label.includes('minggu');
    };

    const weeklyColumns = baseColumns.filter((col) => isWeeklyColumn(col));
    const sourceColumns = weeklyColumns.length > 0 ? weeklyColumns : baseColumns;

    const blockSize = 4;
    const aggregated = [];
    for (let i = 0; i < sourceColumns.length; i += blockSize) {
      const blockColumns = sourceColumns.slice(i, i + blockSize);
      if (!blockColumns.length) {
        continue;
      }
      const blockIndex = aggregated.length;
      const startWeek = blockColumns[0]?.weekNumber ?? blockColumns[0]?.order ?? i + 1;
      const endWeek = blockColumns[blockColumns.length - 1]?.weekNumber ?? startWeek + blockColumns.length - 1;
      const startLabel = blockColumns[0]?.rangeLabel || blockColumns[0]?.label || '';
      const endLabel = blockColumns[blockColumns.length - 1]?.rangeLabel || blockColumns[blockColumns.length - 1]?.label || '';
      const label = `Month ${blockIndex + 1}`;
      const rangeLabel = `Week ${startWeek}-${endWeek}`;

      aggregated.push({
        id: `month-${blockIndex + 1}`,
        fieldId: `month_${blockIndex + 1}`,
        label,
        rangeLabel,
        tooltip: startLabel && endLabel ? `${startLabel} → ${endLabel}` : `${label}: Week ${startWeek}-${endWeek}`,
        generationMode: 'monthly',
        type: 'monthly',
        index: blockIndex,
        childColumns: blockColumns,
      });
    }

    return aggregated;
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
  _handleAgGridCellChange({
    cellKey,
    value,
    columnMeta,
    displayValue,
    isVolumeMode,
    validation,
    pekerjaanId,
    columnId,
  }) {
    if (!cellKey) {
      return;
    }

    if (validation) {
      this._updateCellValidationState(cellKey, validation);
    }

    let normalizedValue = value;
    if (typeof normalizedValue === 'string') {
      normalizedValue = parseFloat(normalizedValue);
    }
    if (Number.isNaN(normalizedValue)) {
      normalizedValue = 0;
    }

    // Phase 2E.1: Get current mode's state for isolated data tracking
    const modeState = this._getCurrentModeState();
    const progressMode = this.state.progressMode || 'planned';

    console.log(`[CellChange] Mode: ${progressMode.toUpperCase()}, Cell: ${cellKey}, Value: ${normalizedValue}`);

    // Write to mode-specific state (isolated from other mode)
    modeState.modifiedCells.set(cellKey, normalizedValue);
    modeState.isDirty = true;

    if (columnMeta?.fieldId && this.state.timeColumnIndex) {
      this.state.timeColumnIndex[columnMeta.fieldId] =
        columnMeta || this.state.timeColumnIndex[columnMeta.fieldId];
    }

    if (isVolumeMode) {
      this._setCellVolumeOverride(cellKey, displayValue);
    } else {
      this._clearCellVolumeOverride(cellKey);
    }

    const parsed = this._parseCellKey(cellKey);
    const resolvedPekerjaanId = pekerjaanId || parsed?.pekerjaanId;
    if (resolvedPekerjaanId) {
      this._clearSaveErrorForRow(Number(resolvedPekerjaanId));
      const percentTotal = this._updateProgressTotals(Number(resolvedPekerjaanId));
      this._updateVolumeTotals(Number(resolvedPekerjaanId), percentTotal);
    }

    console.log(`[CellChange] ${progressMode.toUpperCase()} modifiedCells size: ${modeState.modifiedCells.size}`);
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
