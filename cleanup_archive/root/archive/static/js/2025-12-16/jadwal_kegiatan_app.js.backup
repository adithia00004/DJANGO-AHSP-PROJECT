/**
 * Jadwal Kegiatan Main Entry Point
 * Modern modular implementation with Vite bundling
 * License: MIT
 */
/* global ExportManager */

import { TanStackGridManager } from '@modules/grid/tanstack-grid-manager.js';
import { UnifiedTableManager } from '@modules/unified/UnifiedTableManager.js';
import { DataLoader } from '@modules/core/data-loader.js';
import { TimeColumnGenerator } from '@modules/core/time-column-generator.js';
import { SaveHandler } from '@modules/core/save-handler.js';
// Chart modules now lazy loaded for better initial performance
// import { KurvaSChart } from '@modules/kurva-s/echarts-setup.js';
// import { GanttChart } from '@modules/gantt/frappe-gantt-setup.js'; // OLD - Frappe Gantt (deprecated)
// Gantt V2 (Frozen Column) now loaded lazily via dynamic import() - see _initializeFrozenGantt()
import { StateManager } from '@modules/core/state-manager.js'; // Phase 0.3: StateManager integration
import {
  KeyboardShortcuts,
  ButtonStateManager,
  Toast,
  initializeUXEnhancements
} from '@modules/shared/ux-enhancements.js'; // UX Enhancements

/**
 * Initialize Jadwal Kegiatan Grid Application
 */
class JadwalKegiatanApp {
  constructor() {
    this.state = null;
    this.initialized = false;
    this.gridManager = null;

    // Phase 0.3: StateManager for clean state management
    this.stateManager = StateManager.getInstance();

    // Modern modules
    this.dataLoader = null;
    this.timeColumnGenerator = null;
    this.saveHandler = null;
    this.unifiedManager = null;
    this._gridContainerParent = null;
    this._gridContainerNextSibling = null;

    // Chart modules (lazy loaded)
    this.kurvaSChart = null;
    this.ganttChart = null; // OLD Frappe Gantt (deprecated, not used)
    this.ganttFrozenGrid = null; // Gantt V2: Frozen column architecture (default)
    this._chartModulesLoaded = false;
    this._chartModulesLoading = false;

    // UX Enhancements
    this.keyboardShortcuts = null;

    this._weekBoundarySaveTimer = null;
    this._pendingWeekBoundary = null;
    this._isRegeneratingTimeline = false;
    this._queuedRegeneratePayload = null;
    this._isEnforcingWeekly = false;
    this._exportManagerInstance = null;
    this._exportBindingsAttached = false;
    this._costToggleBtn = null;
    this._costToggleBtnText = null;
    this._costToggleSpinner = null;
    this._costToggleBtnIcon = null;
    this._costViewAutoActivated = false;
    this._ganttScrollSyncHandlers = null;
    this._stateManagerListener = null;
    this._suppressStateManagerEvent = false;
    this._currencyFormatter = null;

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
        useUPlotKurva: true, // uPlot Kurva-S aktif secara default
        timeScale: 'weekly',
        inputMode: 'percentage',
        saveMode: 'weekly',
        weekStartDay: 0,
        weekEndDay: 6,
        displayScale: null,
        progressMode: 'planned',  // Phase 2E.1: Current active mode
        displayMode: 'percentage', // Phase 2E.1: 'percentage' or 'volume'
        useUnifiedTable: config.disableUnifiedTable ? false : true,
        // Default: legacy Gantt V2 tetap aktif; bisa dimatikan dengan config.disableLegacyGantt
        keepLegacyGantt: config.enableLegacyGantt ? true : false,
        dependencies: [],
        debugUnifiedTable: Boolean(config.debugUnifiedTable || window.DEBUG_UNIFIED_TABLE),

        // Phase 0.3: StateManager reference
        stateManager: this.stateManager,

        // Phase 0.3: Cell values now managed by StateManager
        // Keeping other mode-specific state here temporarily for non-cell data
        plannedState: {
          // modifiedCells: managed by StateManager
          // assignmentMap: managed by StateManager
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
          // modifiedCells: managed by StateManager
          // assignmentMap: managed by StateManager
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

        // Phase 0.3: Backward compatibility maintained via StateManager
        // Legacy properties for non-cell data still delegate to current mode
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
    this._bindStateManagerEvents();
  }

  /**
   * Setup property delegation for backward compatibility.
   * Phase 0.3: Cell data (modifiedCells, assignmentMap) now managed by StateManager
   * Other mode-specific properties still delegate to current mode state
   */
  _setupStateDelegation() {
    const getCurrentState = () => {
      return this.state.progressMode === 'actual'
        ? this.state.actualState
        : this.state.plannedState;
    };

    // Phase 0.3: modifiedCells and assignmentMap are now managed by StateManager
    // Add backward compatibility getters that delegate to StateManager
    Object.defineProperty(this.state, 'modifiedCells', {
      get: () => {
        // Return a Map-like object for backward compatibility
        // This is used by legacy code that expects Map operations
        const mode = this.state.progressMode;
        return this.stateManager.states[mode].modifiedCells;
      },
      configurable: true
    });

    Object.defineProperty(this.state, 'assignmentMap', {
      get: () => {
        // Return a Map-like object for backward compatibility
        const mode = this.state.progressMode;
        return this.stateManager.states[mode].assignmentMap;
      },
      configurable: true
    });

    Object.defineProperty(this.state, 'costAssignmentMap', {
      get: () => {
        const mode = this.state.progressMode;
        return this.stateManager.states[mode].costAssignmentMap;
      },
      configurable: true
    });

    Object.defineProperty(this.state, 'costModifiedCells', {
      get: () => {
        const mode = this.state.progressMode;
        return this.stateManager.states[mode].costModifiedCells;
      },
      configurable: true
    });

    // Other properties still delegate to current mode state (not managed by StateManager yet)
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
      get: () => getCurrentState().isDirty || this.stateManager.hasUnsavedChanges(),
      set: (value) => { getCurrentState().isDirty = value; },
      configurable: true
    });

    console.log('[JadwalKegiatanApp] Phase 0.3: State delegation setup with StateManager integration');
  }

  _bindStateManagerEvents() {
    if (!this.stateManager || this._stateManagerListener) {
      return;
    }
    this._stateManagerListener = (event) => this._handleStateManagerEvent(event);
    this.stateManager.addEventListener(this._stateManagerListener);
    console.log('[JadwalKegiatanApp] StateManager listener attached');
  }

  _unbindStateManagerEvents() {
    if (!this.stateManager || !this._stateManagerListener) {
      return;
    }
    this.stateManager.removeEventListener(this._stateManagerListener);
    this._stateManagerListener = null;
    console.log('[JadwalKegiatanApp] StateManager listener removed');
  }

  _handleStateManagerEvent(event = {}) {
    if (!event || typeof event !== 'object') {
      return;
    }
    switch (event.type) {
      case 'mode-switch':
        if (this._suppressStateManagerEvent) {
          return;
        }
        this._applyProgressModeSwitch(event.newMode, { showToast: false });
        break;
      case 'commit':
        this._handleStateCommitEvent(event);
        break;
      case 'reset':
        this._handleStateResetEvent();
        break;
      default:
        break;
    }
  }

  _handleStateCommitEvent(event = {}) {
    if (this.gridManager && typeof this.gridManager.refreshCells === 'function') {
      this.gridManager.refreshCells();
    }
    this._updateStatusBar();
    this._updateCharts();
    const modeLabel = (event.mode || this.state.progressMode || 'planned') === 'actual' ? 'Realisasi' : 'Perencanaan';
    console.log(`[StateManager] Commit event processed for mode: ${modeLabel}`);
  }

  _handleStateResetEvent() {
    console.log('[StateManager] Reset event received, syncing UI components');
    this.state.progressMode = this.stateManager?.currentMode || 'planned';
    this._syncToolbarRadios();
    this._syncGridViews();
    this._updateStatusBar('Ready');
    this._updateCharts();
  }

  /**
   * Get the current mode's state object.
   * Phase 0.3: Delegated to StateManager
   * @returns {Object} Current mode state (plannedState or actualState)
   */
  _getCurrentModeState() {
    const mode = this.state.progressMode === 'actual' ? 'actual' : 'planned';
    return this.stateManager.states[mode];
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
        saveButton: document.getElementById('save-button') || document.getElementById('btn-save-all'),
        refreshButton: document.getElementById('refresh-button'),
        resetButton: document.getElementById('btn-reset-progress'),
        tanstackGridContainer: document.getElementById('tanstack-grid-container'),
        tanstackGridBody: document.getElementById('tanstack-grid-body'),
        tanstackGridTopScroll: document.getElementById('tanstack-grid-scroll-top'),
        tanstackGridTopScrollInner: document.getElementById('tanstack-grid-scroll-inner'),
        scurveChart: document.getElementById('scurve-chart'),
        ganttChart: document.getElementById('gantt-chart'),
        ganttChartWrapper: document.getElementById('gantt-chart-wrapper'),
        ganttTreeBody: document.getElementById('gantt-tree-body'),
        ganttTreeScroll: document.getElementById('gantt-tree-scroll'),
        ganttSummaryTable: document.getElementById('gantt-summary-table'),
        ganttSummaryBody: document.getElementById('gantt-summary-body'),
        ganttSummaryTotal: document.getElementById('gantt-summary-total'),
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

    if (!domRefs.tanstackGridContainer) {
      throw new Error('TanStack grid container #tanstack-grid-container tidak ditemukan');
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
    const allowedInputModes = new Set(['percentage', 'volume', 'cost']);
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
    if (typeof dataset.enableUplotKurva !== 'undefined') {
      this.state.useUPlotKurva = dataset.enableUplotKurva !== 'false';
    }
  }

  /**
   * Attach event handlers using modern delegation pattern
   */
  _attachEvents() {
    // Attach toolbar events
    this._attachToolbarEvents();

    this._initTanStackGridIfNeeded();
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
    this._setupCostViewToggle();  // Phase 1: Cost view toggle button
    this._setupKeyboardShortcuts();  // UX Enhancement: Keyboard shortcuts
    this._setupUXEnhancements();  // UX Enhancement: Ripple effects, tooltips
  }

  /**
   * Setup keyboard shortcuts for power users
   */
  _setupKeyboardShortcuts() {
    // Initialize keyboard shortcuts manager
    this.keyboardShortcuts = new KeyboardShortcuts();

    // Ctrl+S: Save
    this.keyboardShortcuts.register('ctrl+s', () => {
      this.saveChanges();
      Toast.info('Saving changes... (Ctrl+S)');
    }, {
      description: 'Save all changes'
    });

    // Ctrl+R: Refresh (override browser default)
    this.keyboardShortcuts.register('ctrl+r', () => {
      this.refresh();
      Toast.info('Refreshing data... (Ctrl+R)');
    }, {
      description: 'Refresh data from server'
    });

    // Ctrl+Alt+P: Switch to Planned mode
    this.keyboardShortcuts.register('ctrl+alt+p', () => {
      const plannedRadio = document.getElementById('mode-planned');
      if (plannedRadio) {
        plannedRadio.checked = true;
        plannedRadio.dispatchEvent(new Event('change', { bubbles: true }));
        Toast.info('Switched to Perencanaan mode (Ctrl+Alt+P)');
      }
    }, {
      description: 'Switch to Perencanaan mode'
    });

    // Ctrl+Alt+A: Switch to Actual mode
    this.keyboardShortcuts.register('ctrl+alt+a', () => {
      const actualRadio = document.getElementById('mode-actual');
      if (actualRadio) {
        actualRadio.checked = true;
        actualRadio.dispatchEvent(new Event('change', { bubbles: true }));
        Toast.info('Switched to Realisasi mode (Ctrl+Alt+A)');
      }
    }, {
      description: 'Switch to Realisasi mode'
    });

    // Ctrl+Alt+1: Switch to Percentage display
    this.keyboardShortcuts.register('ctrl+alt+1', () => {
      const percentageRadio = document.getElementById('mode-percentage');
      if (percentageRadio && !percentageRadio.disabled) {
        percentageRadio.checked = true;
        percentageRadio.dispatchEvent(new Event('change', { bubbles: true }));
        Toast.info('Display: Percentage (Ctrl+Alt+1)');
      }
    }, {
      description: 'Switch to Percentage display'
    });

    // Ctrl+Alt+2: Switch to Volume display
    this.keyboardShortcuts.register('ctrl+alt+2', () => {
      const volumeRadio = document.getElementById('mode-volume');
      if (volumeRadio && !volumeRadio.disabled) {
        volumeRadio.checked = true;
        volumeRadio.dispatchEvent(new Event('change', { bubbles: true }));
        Toast.info('Display: Volume (Ctrl+Alt+2)');
      }
    }, {
      description: 'Switch to Volume display'
    });

    // Ctrl+Alt+3: Switch to Cost display (if enabled)
    this.keyboardShortcuts.register('ctrl+alt+3', () => {
      const costRadio = document.getElementById('mode-cost');
      if (costRadio && !costRadio.disabled) {
        costRadio.checked = true;
        costRadio.dispatchEvent(new Event('change', { bubbles: true }));
        Toast.info('Display: Cost (Ctrl+Alt+3)');
      } else {
        Toast.warning('Cost view only available in Realisasi mode');
      }
    }, {
      description: 'Switch to Cost display'
    });

    // Escape: Close modals/dropdowns
    this.keyboardShortcuts.register('escape', () => {
      // Close any open Bootstrap dropdowns
      const openDropdowns = document.querySelectorAll('.dropdown-menu.show');
      openDropdowns.forEach(dropdown => {
        const toggle = dropdown.previousElementSibling;
        if (toggle) {
          const bsDropdown = bootstrap.Dropdown.getInstance(toggle);
          if (bsDropdown) bsDropdown.hide();
        }
      });
    }, {
      description: 'Close open menus',
      preventDefault: false // Allow default Escape behavior
    });

    // Ctrl+?: Show keyboard shortcuts help
    this.keyboardShortcuts.register('ctrl+shift+/', () => {
      this._showKeyboardShortcutsHelp();
    }, {
      description: 'Show keyboard shortcuts help'
    });

    console.log('⌨️ Keyboard shortcuts registered:', this.keyboardShortcuts.getShortcuts());
  }

  /**
   * Setup UX enhancements (ripple effects, tooltips, etc.)
   */
  _setupUXEnhancements() {
    // Initialize general UX enhancements
    initializeUXEnhancements();

    // Add keyboard hint to Save button
    const saveButton = this.state.domRefs.saveButton;
    if (saveButton) {
      saveButton.setAttribute('data-keyboard-hint', 'Ctrl+S');
    }

    console.log('🎨 UX enhancements applied');
  }

  /**
   * Show keyboard shortcuts help modal
   */
  _showKeyboardShortcutsHelp() {
    const shortcuts = this.keyboardShortcuts.getShortcuts();
    const shortcutList = shortcuts.map(s => `
      <tr>
        <td><kbd>${s.key.replace(/\+/g, '</kbd> + <kbd>')}</kbd></td>
        <td>${s.description}</td>
      </tr>
    `).join('');

    const modalHtml = `
      <div class="modal fade" id="keyboardShortcutsModal" tabindex="-1">
        <div class="modal-dialog">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">
                <i class="bi bi-keyboard"></i> Keyboard Shortcuts
              </h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
              <table class="table table-sm">
                <thead>
                  <tr>
                    <th style="width: 40%">Shortcut</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  ${shortcutList}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    `;

    // Remove existing modal if any
    const existingModal = document.getElementById('keyboardShortcutsModal');
    if (existingModal) existingModal.remove();

    // Add modal to DOM
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('keyboardShortcutsModal'));
    modal.show();

    // Cleanup on hide
    document.getElementById('keyboardShortcutsModal').addEventListener('hidden.bs.modal', function() {
      this.remove();
    });
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

  /**
   * Phase 1: Setup Cost View Toggle Button
   * @private
   */
  _setupCostViewToggle() {
    const toggleBtn = document.getElementById('toggleCostViewBtn');
    const toggleBtnText = document.getElementById('toggleCostViewBtnText');
    const toggleBtnSpinner = document.getElementById('toggleCostViewBtnSpinner');
    const toggleBtnIcon = toggleBtn?.querySelector('i');

    if (!toggleBtn) {
      console.log('[JadwalKegiatanApp] Cost view toggle button not found (chart tab may not be active)');
      return;
    }

    if (!this.kurvaSChart) {
      console.warn('[JadwalKegiatanApp] Kurva S chart not initialized, cannot setup toggle');
      return;
    }

    if (this.kurvaSChart?.options?.enableCostView === false) {
      toggleBtn.classList.add('d-none');
      return;
    }

    this._costToggleBtn = toggleBtn;
    this._costToggleBtnText = toggleBtnText;
    this._costToggleSpinner = toggleBtnSpinner;
    this._costToggleBtnIcon = toggleBtnIcon;

    toggleBtn.addEventListener('click', async () => {
      toggleBtn.disabled = true;
      toggleBtnSpinner?.classList.remove('d-none');

      try {
        const success = await this.kurvaSChart.toggleView();
        if (success) {
          this._setCostToggleButtonState();
          console.log('[JadwalKegiatanApp] Switched Kurva-S view:', this.kurvaSChart.viewMode);
        } else {
          console.error('[JadwalKegiatanApp] Failed to toggle view');
        }
      } catch (error) {
        console.error('[JadwalKegiatanApp] Error toggling cost view:', error);
      } finally {
        toggleBtn.disabled = false;
        toggleBtnSpinner?.classList.add('d-none');
      }
    });

    this._setCostToggleButtonState();
    console.log('[JadwalKegiatanApp] Cost view toggle button setup complete');
  }

  _setCostToggleButtonState() {
    if (!this._costToggleBtn || !this.kurvaSChart) {
      return;
    }

    const isCostMode = this.kurvaSChart.viewMode === 'cost';
    const label = isCostMode ? 'Show Progress View' : 'Show Cost View';
    const iconClass = isCostMode ? 'fas fa-chart-line' : 'fas fa-money-bill-wave';

    if (this._costToggleBtnText) {
      this._costToggleBtnText.textContent = label;
    }
    if (this._costToggleBtnIcon) {
      this._costToggleBtnIcon.className = iconClass;
    }
  }
  async _activateDefaultCostView() {
    if (this._costViewAutoActivated) {
      this._setCostToggleButtonState();
      return;
    }

  if (!this.kurvaSChart) {
    return;
  }

  const chartOptions = this.kurvaSChart.options || {};
  if (!chartOptions.enableCostView) {
    return;
  }

  try {
    const success = await this.kurvaSChart.toggleView('cost');
    if (success) {
      this._costViewAutoActivated = true;
      this._setCostToggleButtonState();
      console.log('[JadwalKegiatanApp] Defaulted Kurva-S to cost view');
    }
  } catch (error) {
    console.warn('[JadwalKegiatanApp] Failed to enable cost view automatically:', error);
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

    const progressMode = this.state.progressMode || 'planned';
    document.querySelectorAll('input[name="progressMode"]').forEach((radio) => {
      const isChecked = radio.value === progressMode;
      if (radio.checked !== isChecked) {
        radio.checked = isChecked;
      }
      const label = radio.nextElementSibling;
      if (label && label.matches('.btn')) {
        label.setAttribute('aria-selected', String(isChecked));
      }
    });

    const timeScale = this.state.displayScale || this.state.timeScale || 'weekly';
    document.querySelectorAll('input[name="timeScale"]').forEach((radio) => {
      radio.checked = radio.value === timeScale;
    });

    this._updateCostToggleAvailability();
  }

  _handleDisplayModeChange(mode) {
    const normalized = (mode || '').toLowerCase();
    const allowed = new Set(['percentage', 'volume', 'cost']);
    if (!allowed.has(normalized) || this.state.inputMode === normalized) {
      return;
    }

    if (normalized === 'cost' && (this.state.progressMode || 'planned') !== 'actual') {
      this.showToast('Mode biaya hanya tersedia saat melihat Realisasi', 'warning', 2600);
      this._syncToolbarRadios();
      return;
    }

    this.state.inputMode = normalized;
    this.state.displayMode = normalized;  // Phase 2E.1: Keep displayMode in sync

    if (this.gridManager) {
      this.gridManager.setInputMode(normalized);
    }

    this._syncGridViews();

    let label = 'Persentase';
    if (normalized === 'volume') {
      label = 'Volume';
    } else if (normalized === 'cost') {
      label = 'Biaya';
    }
    this.showToast(`Mode input diubah ke ${label}`, 'info', 2200);
  }

  /**
   * Handle progress mode change (Phase 2E.1: Planned vs Actual)
   * Phase 0.3: Delegates to StateManager for mode switching
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

    // Phase 0.3: Get state sizes from StateManager
    const oldStats = this.stateManager.states[oldMode].getStats();

    // Phase 0.3: Switch mode in StateManager
    this._suppressStateManagerEvent = true;
    this.stateManager.switchMode(normalized);
    this._suppressStateManagerEvent = false;

    // Log new state after switch
    const newStats = this.stateManager.states[normalized].getStats();
    console.log(`[ModeChange] State switch complete:`);
    console.log(`  - Old ${oldMode.toUpperCase()}: ${oldStats.modifiedCount} modified, ${oldStats.assignmentCount} assignments`);
    console.log(`  - New ${normalized.toUpperCase()}: ${newStats.modifiedCount} modified, ${newStats.assignmentCount} assignments`);

    this._applyProgressModeSwitch(normalized, { showToast: true });
  }

  _applyProgressModeSwitch(nextMode, options = {}) {
    const normalized = nextMode === 'actual' ? 'actual' : 'planned';
    const previousInputMode = this.state.inputMode || 'percentage';
    this.state.progressMode = normalized;

    if (normalized !== 'actual' && this.state.inputMode === 'cost') {
      this.state.inputMode = 'percentage';
      this.state.displayMode = 'percentage';
    }

    if (this.gridManager && typeof this.gridManager.setInputMode === 'function') {
      const currentMode = this.state.inputMode || 'percentage';
      if (currentMode !== previousInputMode) {
        this.gridManager.setInputMode(currentMode);
      }
    }

    this._syncToolbarRadios();
    this._updateCostToggleAvailability();
    this._updateProgressModeIndicator(normalized);
    this._syncGridViews();
    this._updateCharts();

    if (options.showToast) {
      const label = normalized === 'planned' ? 'Rencana' : 'Realisasi';
      this.showToast(`Mode progress diubah ke ${label}`, 'info', 2200);
    }
  }

  _updateProgressModeIndicator(mode) {
    const indicator = document.getElementById('progress-mode-indicator');
    if (!indicator) {
      return;
    }
    const normalized = mode === 'actual' ? 'actual' : 'planned';
    const label = normalized === 'planned' ? 'Rencana' : 'Realisasi';
    const bgClass = normalized === 'planned' ? 'bg-info' : 'bg-warning';
    indicator.textContent = `Mode: ${label}`;
    indicator.className = `badge ${bgClass} ms-2`;
    indicator.style.cssText = 'font-size: 0.75rem; vertical-align: middle;';
  }

  _updateCostToggleAvailability() {
    const costRadio = document.getElementById('mode-cost');
    if (!costRadio) {
      return;
    }
    const isActual = (this.state.progressMode || 'planned') === 'actual';
    costRadio.disabled = !isActual;
    if (!isActual && costRadio.checked) {
      const percentageRadio = document.getElementById('mode-percentage');
      if (percentageRadio) {
        percentageRadio.checked = true;
      }
    }
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
   * Initialize TanStack Table grid when enabled
   */
  _initTanStackGridIfNeeded() {
    const container = this.state.domRefs.tanstackGridContainer;
    if (!container) {
      console.warn('[JadwalKegiatanApp] TanStack grid container not available');
      return;
    }

    if (!this._gridContainerParent) {
      this._gridContainerParent = container.parentNode || null;
      this._gridContainerNextSibling = container.nextSibling || null;
    }

    container.classList.remove('d-none');

    if (this.state.useUnifiedTable) {
      if (!this.unifiedManager) {
        this.unifiedManager = new UnifiedTableManager(this.state, {
          showToast: this.showToast.bind(this),
          onCellChange: (payload) => this._handleGridCellChange(payload),
          getCellValidationState: (cellKey) => this._getCellValidationState(cellKey),
          debugUnifiedTable: this.state.debugUnifiedTable,
        });
        this.unifiedManager.mount(container, {
          topScroll: this.state.domRefs.tanstackGridTopScroll,
          topScrollInner: this.state.domRefs.tanstackGridTopScrollInner,
          body: this.state.domRefs.tanstackGridBody,
        });
      }
    } else {
      if (!this.gridManager) {
        this.gridManager = new TanStackGridManager(this.state, {
          showToast: this.showToast.bind(this),
          onCellChange: (payload) => this._handleGridCellChange(payload),
          getCellValidationState: (cellKey) => this._getCellValidationState(cellKey),
        });
        this.gridManager.mount(container, {
          topScroll: this.state.domRefs.tanstackGridTopScroll,
          topScrollInner: this.state.domRefs.tanstackGridTopScrollInner,
          body: this.state.domRefs.tanstackGridBody,
        });
      }
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

      // Step 3.6: Ensure dependencies array exists (for unified Gantt overlay)
      this.state.dependencies = this.state.dependencies || [];

      // Build time column index for quick lookup
      this.state.timeColumnIndex = this._createTimeColumnIndex(this.state.timeColumns);

      console.log(
        `[JadwalKegiatanApp] ✅ Data loaded successfully:`,
        `${this.state.flatPekerjaan?.length || 0} pekerjaan,`,
        `${this.state.tahapanList?.length || 0} tahapan,`,
        `${this.state.timeColumns?.length || 0} columns`
      );

      // Step 4: Initialize and update charts
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
   * Lazy load chart modules for better initial performance
   * @private
   */
  async _loadChartModules() {
    if (this._chartModulesLoaded || this._chartModulesLoading) {
      return;
    }

    if (!this.state.useUPlotKurva) {
      console.warn('[JadwalKegiatanApp] uPlot dimatikan, melewati inisialisasi chart');
      return;
    }

    this._chartModulesLoading = true;
    console.log('📊 Loading chart modules (lazy)...');

    try {
      const kurvaSModule = await import('@modules/kurva-s/uplot-chart.js');

      // Store module classes
      this.KurvaSChartClass = kurvaSModule.KurvaSUPlotChart || kurvaSModule.default;

      this._chartModulesLoaded = true;
      this._chartModulesLoading = false;

      console.log('✅ Chart modules loaded');

      // Initialize charts after loading
      this._initializeChartsAfterLoad();
    } catch (error) {
      console.error('❌ Failed to load chart modules:', error);
      this._chartModulesLoading = false;
      Toast.error('Failed to load chart modules');
    }
  }

  /**
   * Initialize chart modules after lazy load
   * @private
   */
  _initializeChartsAfterLoad() {
    console.log('[JadwalKegiatanApp] Initializing charts after load...');

    // Initialize Kurva-S Chart
    if (this.state.domRefs?.scurveChart && this.KurvaSChartClass) {
      try {
        this.kurvaSChart = new this.KurvaSChartClass(this.state, {
          useIdealCurve: true,
          steepnessFactor: 0.8,
          smoothCurves: true,
          showArea: true,
          enableCostView: true,
        });
        const success = this.kurvaSChart.initialize(this.state.domRefs.scurveChart);
        if (success) {
          console.log('[JadwalKegiatanApp] Kurva-S chart initialized');
          const activatePromise = this._activateDefaultCostView();
          if (activatePromise && typeof activatePromise.catch === 'function') {
            activatePromise.catch((error) => {
              console.warn('[JadwalKegiatanApp] Failed to auto-enable cost view:', error);
            });
          }
        }
      } catch (error) {
        console.warn('[JadwalKegiatanApp] Failed to initialize Kurva-S chart:', error);
      }
    }

    // ========================================
    // OLD Gantt Chart (Frappe Gantt) - DISABLED
    // ========================================
    // The old Gantt Chart has been completely replaced with a new redesigned version.
    // All initialization code for the old Gantt has been removed to prevent conflicts.
    // See _initializeRedesignedGantt() method for the new implementation.

    console.log('[JadwalKegiatanApp] ⚠️ OLD Gantt Chart initialization SKIPPED (replaced by new design)');

    // NOTE: NEW Redesigned Gantt Chart will be initialized lazily when tab is clicked
    // See _setupLazyChartLoading() method
  }

  /**
   * Initialize Gantt Chart V2 (Frozen Column Architecture)
   * Called ONLY when Gantt tab is clicked for the first time
   * @private
   */
  async _initializeRedesignedGantt(retryCount = 0) {
    const MAX_RETRIES = 3;
    const RETRY_DELAY = 200; // ms

    if (this.state.useUnifiedTable && this.state.keepLegacyGantt === false) {
      console.log('[JadwalKegiatanApp] Unified mode active - rendering Gantt via unified table overlay');
      const ganttContainer = document.getElementById('gantt-redesign-container');
      if (!ganttContainer) {
        console.warn('[JadwalKegiatanApp] Gantt container not found for unified overlay');
        return;
      }
      await this._initializeUnifiedGanttOverlay(ganttContainer);
      return;
    }

    // Check if already initialized
    if (this.ganttFrozenGrid) {
      console.log('[JadwalKegiatanApp] Gantt already initialized, skipping');
      return;
    }

    // Wait a bit for DOM to be ready (Bootstrap tab transition)
    if (retryCount === 0) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    const ganttContainer = document.getElementById('gantt-redesign-container');

    if (!ganttContainer) {
      console.warn(`[JadwalKegiatanApp] ⏳ Gantt container not found (attempt ${retryCount + 1}/${MAX_RETRIES})`);

      // Retry if not max retries
      if (retryCount < MAX_RETRIES) {
        console.log(`[JadwalKegiatanApp] Retrying in ${RETRY_DELAY}ms...`);
        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
        return this._initializeRedesignedGantt(retryCount + 1);
      }

      console.error('[JadwalKegiatanApp] ❌ Gantt container not found after retries');
      console.error('[JadwalKegiatanApp] DOM state:', {
        ganttView: document.getElementById('gantt-view'),
        ganttTab: document.getElementById('gantt-tab')
      });
      Toast.error('Failed to find Gantt container');
      return;
    }

    try {
      // Initialize V2: Frozen Column Architecture (now default)
      console.log('🚀 Initializing Gantt V2 (Frozen Column)...');
      await this._initializeFrozenGantt(ganttContainer);

    } catch (error) {
      console.error('[JadwalKegiatanApp] ❌ Failed to initialize Gantt:', error);
      console.error('[JadwalKegiatanApp] Error stack:', error.stack);
      Toast.error('Failed to load Gantt Chart');
      throw error;
    }
  }

  /**
   * Initialize V2: Frozen Column Gantt (Now Default)
   * @private
   */
  async _initializeFrozenGantt(container) {
    console.log('[JadwalKegiatanApp] ✅ Container found:', container);

    // Lazy load V2 module
    const { GanttFrozenGrid } = await import('@modules/gantt-v2/gantt-frozen-grid.js');

    // Create Gantt instance
    this.ganttFrozenGrid = new GanttFrozenGrid(container, {
      rowHeight: 40,
      timeScale: 'week'
    });

    // Initialize with app context (provides StateManager, tahapanList, etc.)
    await this.ganttFrozenGrid.initialize(this);

    console.log('[JadwalKegiatanApp] ✅ Gantt V2 (Frozen Column) initialized successfully!');
    Toast.success('📊 Gantt Chart loaded', 2000);
  }

  async _initializeUnifiedGanttOverlay(ganttContainer) {
    if (!this.unifiedManager) {
      this._initTanStackGridIfNeeded();
    }
    if (!this.unifiedManager) {
      console.warn('[JadwalKegiatanApp] Unified manager not available for Gantt overlay');
      return;
    }

    const host = this._ensureGanttHost(ganttContainer);
    if (!host) {
      console.warn('[JadwalKegiatanApp] Unable to prepare Gantt host for unified overlay');
      return;
    }

    const gridPayload = {
      tree: this.state.pekerjaanTree || [],
      timeColumns: this._getDisplayTimeColumns(),
      inputMode: this.state.inputMode || 'percentage',
      timeScale: this.state.displayScale || this.state.timeScale || 'weekly',
      dependencies: this.state.dependencies || [],
    };
    if (this.state.debugUnifiedTable) {
      console.log('[UnifiedGanttOverlay] Apply payload', {
        rows: gridPayload.tree.length,
        columns: gridPayload.timeColumns.length,
        deps: gridPayload.dependencies.length,
      });
    }
    this.unifiedManager.updateData(gridPayload);
    this.unifiedManager.switchMode('gantt');
    this._applyGanttOverlayStyles(host);
  }

  _applyGanttOverlayStyles(host) {
    if (!host) return;
    host.classList.add('gantt-overlay-mode');
    const styleId = 'gantt-overlay-style';
    if (!document.getElementById(styleId)) {
      const style = document.createElement('style');
      style.id = styleId;
      style.textContent = `
        /* Biarkan header/frozen columns tetap tampil untuk konteks */
        .gantt-overlay-mode .tanstack-grid-header { display: block !important; }
        /* Sembunyikan konten text pada sel time-column saja, jangan menggangu pinned kolom */
        .gantt-overlay-mode .tanstack-grid-cell.time-cell { color: transparent; }
        .gantt-overlay-mode .tanstack-grid-cell.time-cell * { visibility: hidden; }
        .gantt-overlay-mode .tanstack-grid-cell.time-cell { pointer-events: none; }
        /* Izinkan scroll tetap berjalan */
        .gantt-overlay-mode .tanstack-grid-body { overflow: auto; }
      `;
      document.head.appendChild(style);
    }
  }

  _ensureGanttHost(ganttContainer) {
    if (!ganttContainer) {
      return null;
    }
    let host = ganttContainer.querySelector('.unified-gantt-host');
    if (!host) {
      host = document.createElement('div');
      host.className = 'unified-gantt-host';
      host.style.position = 'relative';
      host.style.minHeight = '420px';
      host.style.width = '100%';
      ganttContainer.innerHTML = '';
      ganttContainer.appendChild(host);
    } else {
      host.innerHTML = '';
    }

    this._moveGridContainerTo(host);
    return host;
  }

  _moveGridContainerTo(target) {
    const container = this.state?.domRefs?.tanstackGridContainer;
    if (!container || !target || container.parentNode === target) {
      return;
    }
    target.appendChild(container);
  }

  _restoreGridContainerPosition() {
    const container = this.state?.domRefs?.tanstackGridContainer;
    const parent = this._gridContainerParent;
    if (!container || !parent) {
      return;
    }
    if (container.parentNode === parent) {
      return;
    }
    if (this._gridContainerNextSibling && this._gridContainerNextSibling.parentNode === parent) {
      parent.insertBefore(container, this._gridContainerNextSibling);
    } else {
      parent.appendChild(container);
    }
  }

  /**
   * Prepare data for redesigned Gantt Chart
   * @private
   * @returns {Object} Gantt data structure
   */
  _prepareGanttData() {
    const data = [];

    // Transform hierarchical data from state (Phase 0.3: use flatPekerjaan from DataLoader)
    if (this.state?.flatPekerjaan && Array.isArray(this.state.flatPekerjaan)) {
      // ✅ FILTER: Only send pekerjaan nodes (actual tasks) to Gantt Chart
      // Pekerjaan nodes already have complete parent chain info (klasifikasi_name, sub_klasifikasi_name)
      const pekerjaanNodes = this.state.flatPekerjaan.filter(n => n.type === 'pekerjaan');

      console.log(`[JadwalKegiatanApp] Transforming ${pekerjaanNodes.length} pekerjaan nodes for Gantt (filtered from ${this.state.flatPekerjaan.length} total nodes)`);

      // DEBUG: Log first node structure
      if (pekerjaanNodes.length > 0) {
        console.log('[JadwalKegiatanApp] Sample pekerjaan node:', pekerjaanNodes[0]);
      }

      pekerjaanNodes.forEach(node => {
        // Get progress from StateManager for pekerjaan nodes
        let progressRencana = 0;
        let progressRealisasi = 0;

        if (this.stateManager) {
          // Calculate average progress across all tahapan for this pekerjaan
          const tahapanList = this.state.tahapanList || [];
          const tahapanCount = tahapanList.length;

          if (tahapanCount > 0) {
            let plannedSum = 0;
            let actualSum = 0;

            tahapanList.forEach(tahapan => {
              const plannedVal = this.stateManager.getCellValue(node.id, tahapan.column_id, 'planned');
              const actualVal = this.stateManager.getCellValue(node.id, tahapan.column_id, 'actual');
              plannedSum += plannedVal || 0;
              actualSum += actualVal || 0;
            });

            progressRencana = Math.round(plannedSum / tahapanCount);
            progressRealisasi = Math.round(actualSum / tahapanCount);
          }
        }

        // Pekerjaan nodes now have complete parent info from DataLoader (after fix)
        data.push({
          // Klasifikasi (parent level 1)
          klasifikasi_id: node.klasifikasi_id,
          klasifikasi_name: node.klasifikasi_name || 'Unknown Klasifikasi',
          klasifikasi_kode: node.klasifikasi_kode || '',

          // Sub-Klasifikasi (parent level 2)
          sub_klasifikasi_id: node.sub_klasifikasi_id,
          sub_klasifikasi_name: node.sub_klasifikasi_name || 'Unknown Sub-Klasifikasi',
          sub_klasifikasi_kode: node.sub_klasifikasi_kode || '',

          // Pekerjaan (leaf node / actual task) - use 'nama' property from DataLoader
          pekerjaan_id: node.id,
          pekerjaan_name: node.nama || node.name || 'Unknown Pekerjaan',
          pekerjaan_kode: node.kode || '',

          // Dates (use project dates as fallback)
          tgl_mulai_rencana: node.tgl_mulai_rencana || this.state.projectStart,
          tgl_selesai_rencana: node.tgl_selesai_rencana || this.state.projectEnd,
          tgl_mulai_realisasi: node.tgl_mulai_realisasi || this.state.projectStart,
          tgl_selesai_realisasi: node.tgl_selesai_realisasi || this.state.projectEnd,

          // Progress
          progress_rencana: progressRencana,
          progress_realisasi: progressRealisasi,

          // Volume info
          volume: node.volume || 0,
          satuan: node.satuan || ''
        });
      });
    } else {
      console.warn('[JadwalKegiatanApp] No flatPekerjaan data available for Gantt');
    }

    // Project metadata
    const projectMeta = {
      project_id: this.state.projectId,
      project_name: this.state.projectName || 'Project',
      start_date: this.state.projectStart,
      end_date: this.state.projectEnd
    };

    console.log(`[JadwalKegiatanApp] Prepared ${data.length} nodes for Gantt Chart`);

    return {
      data,
      project: projectMeta,
      milestones: [] // Future: Load from backend
    };
  }

  /**
   * Initialize chart modules (now lazy loaded on demand)
   * @private
   */
  _initializeCharts() {
    // Setup lazy loading for chart tabs
    this._setupLazyChartLoading();
    this._bindUnifiedTabSync();
  }

  /**
   * Setup lazy loading for chart tabs
   * @private
   */
  _setupLazyChartLoading() {
    // Find chart tab buttons - match actual IDs from template
    const scurveTab = document.querySelector('#scurve-tab') ||
                     document.querySelector('[data-bs-target="#scurve-view"]');

    const ganttTab = document.querySelector('#gantt-tab') ||
                    document.querySelector('[data-bs-target="#gantt-view"]');

    console.log('[LazyLoad] Found tabs:', { scurveTab, ganttTab });

    if (scurveTab) {
      scurveTab.addEventListener('shown.bs.tab', async () => {
        console.log('[LazyLoad] Kurva S tab shown');
        if (this.state.useUnifiedTable && this.unifiedManager) {
          this.unifiedManager.switchMode('kurva');
        }
        if (!this._chartModulesLoaded) {
          await this._loadChartModules();
        }
      }, { once: true });

      scurveTab.addEventListener('click', async () => {
        console.log('[LazyLoad] Kurva S tab clicked');
        if (this.state.useUnifiedTable && this.unifiedManager) {
          this.unifiedManager.switchMode('kurva');
        }
        if (!this._chartModulesLoaded && !this._chartModulesLoading) {
          await this._loadChartModules();
        }
      }, { once: true });
    }

    if (ganttTab) {
      // When Gantt tab is shown, initialize NEW Gantt Chart
      ganttTab.addEventListener('shown.bs.tab', async () => {
        console.log('[LazyLoad] 🎯 Gantt tab shown - initializing NEW Gantt Chart!');

        if (!this._chartModulesLoaded) {
          await this._loadChartModules();
        }

        // Initialize NEW Redesigned Gantt Chart
        await this._initializeRedesignedGantt();
      }, { once: true });

      ganttTab.addEventListener('click', async () => {
        console.log('[LazyLoad] 🎯 Gantt tab clicked');
        if (!this._chartModulesLoaded && !this._chartModulesLoading) {
          await this._loadChartModules();
        }
      }, { once: true });
    }

    console.log('📊 Chart lazy loading configured (with NEW Gantt initialization)');
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

    // Update Gantt V2 with latest data
    if (this.ganttFrozenGrid && typeof this.ganttFrozenGrid.update === 'function') {
      try {
        this.ganttFrozenGrid.update();
        console.log('[JadwalKegiatanApp] ✅ Gantt V2 chart updated');
      } catch (error) {
        console.warn('[JadwalKegiatanApp] Failed to update Gantt V2 chart:', error);
      }
    }
  }

  /**
   * Render Gantt summary table under the chart
   * OLD GANTT METHOD - DISABLED
   * @private
   * @deprecated Use new Gantt Chart instead
   */
  _renderGanttSummary() {
    console.log('[JadwalKegiatanApp] ⚠️ _renderGanttSummary() SKIPPED (old Gantt method)');
    return; // Method disabled - old Gantt Chart no longer used

    /* DISABLED CODE
    const bodyEl = this.state.domRefs?.ganttSummaryBody;
    const totalEl = this.state.domRefs?.ganttSummaryTotal;

    if (!bodyEl) {
      return;
    }

    const setEmptyState = (message) => {
      bodyEl.innerHTML = `
        <tr>
          <td colspan="5" class="text-muted text-center py-3">${message}</td>
        </tr>
      `;
      if (totalEl) {
        totalEl.textContent = '';
      }
    };

    if (!this.ganttChart) {
      setEmptyState('Gantt chart belum siap ditampilkan.');
      return;
    }

    const rows = this.ganttChart.getSummaryRows();
    const stats = typeof this.ganttChart.getSummaryStats === 'function'
      ? this.ganttChart.getSummaryStats()
      : { total: rows.length, complete: 0, inProgress: 0, notStarted: 0 };

    if (!rows.length) {
      setEmptyState('Tidak ada pekerjaan yang memiliki jadwal.');
      return;
    }

    const summaryHtml = rows.map((row) => {
      const safeName = this._escapeHtml(row.shortLabel || row.label || '-');
      const safePath = this._escapeHtml(row.pathLabel || '');
      const plannedBlock = row.planned?.hasData
        ? `
          <div class="gantt-summary-chip planned">
            <span class="chip-label">Rencana</span>
            <span>${this._escapeHtml(row.planned.progressLabel || '0%')}</span>
          </div>
          <div class="gantt-summary-range">${this._escapeHtml(row.planned.startLabel || '-')} s/d ${this._escapeHtml(row.planned.endLabel || '-')}</div>
        `
        : '<span class="text-muted small">Belum ada data</span>';

      const actualBlock = row.actual?.hasData
        ? `
          <div class="gantt-summary-chip actual">
            <span class="chip-label">Realisasi</span>
            <span>${this._escapeHtml(row.actual.progressLabel || '0%')}</span>
          </div>
          <div class="gantt-summary-range">${this._escapeHtml(row.actual.startLabel || '-')} s/d ${this._escapeHtml(row.actual.endLabel || '-')}</div>
        `
        : '<span class="text-muted small">Belum ada data</span>';

      let deltaClass = 'text-muted';
      if (row.delta > 0) {
        deltaClass = 'text-danger';
      } else if (row.delta < 0) {
        deltaClass = 'text-success';
      }

      const deltaLabel = this._escapeHtml(row.deltaLabel || '0%');

      return `
        <tr>
          <td class="text-muted">${row.index}</td>
          <td>
            <div class="gantt-summary-name">${safeName}</div>
            <div class="gantt-summary-path">${safePath}</div>
          </td>
          <td class="gantt-summary-dual">${plannedBlock}</td>
          <td class="gantt-summary-dual">${actualBlock}</td>
          <td>
            <div class="${deltaClass} fw-semibold">${deltaLabel}</div>
          </td>
        </tr>
      `;
    }).join('');

    bodyEl.innerHTML = summaryHtml;

    if (totalEl) {
      totalEl.textContent = `${stats.total} pekerjaan • ${stats.complete} selesai • ${stats.inProgress} berjalan`;
    }
    */ // END DISABLED CODE
  }

  /**
   * Render klasifikasi tree untuk Gantt
   * OLD GANTT METHOD - DISABLED
   * @private
   * @deprecated Use new Gantt Chart instead
   */
  _renderGanttTree() {
    console.log('[JadwalKegiatanApp] ⚠️ _renderGanttTree() SKIPPED (old Gantt method)');
    return; // Method disabled - old Gantt Chart no longer used

    /* DISABLED CODE
    const bodyEl = this.state.domRefs?.ganttTreeBody;
    if (!bodyEl) {
      return;
    }

    if (!this.ganttChart) {
      bodyEl.innerHTML = '<div class="text-muted text-center py-3">Gantt chart belum siap ditampilkan.</div>';
      return;
    }

    const rows = this.ganttChart.getHierarchy();
    if (!rows.length) {
      bodyEl.innerHTML = '<div class="text-muted text-center py-3">Tidak ada pekerjaan untuk ditampilkan.</div>';
      return;
    }

    const rowHeight = Math.max(32, Math.round(this.ganttChart.getRowHeight()));
    bodyEl.style.setProperty('--gantt-tree-row-height', `${rowHeight}px`);

    const treeHtml = rows.map((row, index) => {
      const indentLevel = Math.max(0, (row.level || 0) - 1);
      const subtitleParts = Array.isArray(row.pathParts) ? row.pathParts.slice(0, -1) : [];
      const subtitle = subtitleParts.length > 0 ? subtitleParts.join(' / ') : '';
      const prefixDot = row.level > 0 ? '•'.repeat(Math.min(row.level, 3)) : '';

      return `
        <div class="gantt-tree-row" data-row-index="${index}">
          <span class="tree-prefix">${prefixDot}</span>
          <div class="tree-label" data-level="${row.level || 0}">
            <span style="--tree-indent:${indentLevel}">${this._escapeHtml(row.label || row.kode || 'Pekerjaan')}</span>
            ${subtitle ? `<small class="d-block text-muted">${this._escapeHtml(subtitle)}</small>` : ''}
          </div>
        </div>
      `;
    }).join('');

    bodyEl.innerHTML = treeHtml;
    this._attachGanttScrollSync();
    */ // END DISABLED CODE
  }

  /**
   * Sinkronisasi scroll antara panel tree dan chart
   * @private
   */
  _attachGanttScrollSync() {
    const treeScroll = this.state.domRefs?.ganttTreeScroll;
    const wrapper = this.state.domRefs?.ganttChartWrapper;
    if (!treeScroll || !wrapper) {
      return;
    }

    const chartScroll = wrapper.querySelector('.gantt-container');
    if (!chartScroll) {
      return;
    }

    if (this._ganttScrollSyncHandlers?.scrollEl && this._ganttScrollSyncHandlers.scrollEl !== chartScroll) {
      this._ganttScrollSyncHandlers.scrollEl.removeEventListener('scroll', this._ganttScrollSyncHandlers.scrollHandler);
      treeScroll.removeEventListener('wheel', this._ganttScrollSyncHandlers.wheelHandler);
      this._ganttScrollSyncHandlers = null;
    }

    if (this._ganttScrollSyncHandlers) {
      treeScroll.scrollTop = chartScroll.scrollTop;
      return;
    }

    const scrollHandler = () => {
      treeScroll.scrollTop = chartScroll.scrollTop;
    };
    const wheelHandler = (event) => {
      if (event.deltaY !== 0) {
        chartScroll.scrollTop += event.deltaY;
      }
    };

    chartScroll.addEventListener('scroll', scrollHandler);
    treeScroll.addEventListener('wheel', wheelHandler, { passive: true });
    this._ganttScrollSyncHandlers = {
      scrollEl: chartScroll,
      scrollHandler,
      wheelHandler,
    };
  }

  _escapeHtml(value) {
    if (value === null || value === undefined) {
      return '';
    }
    return String(value).replace(/[&<>"']/g, (char) => {
      const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      };
      return map[char] || char;
    });
  }

  /**
   * Save changes to server (using modern SaveHandler)
   */
  async saveChanges() {
    if (!this.saveHandler) {
      console.error('[JadwalKegiatanApp] SaveHandler not initialized');
      Toast.error('Save handler not initialized');
      return;
    }

    if (!this._validateRowTotalsBeforeSave()) {
      Toast.warning('Please fix validation errors before saving');
      return;
    }

    const saveButton = this.state.domRefs.saveButton;

    // Set button to loading state
    if (saveButton) {
      ButtonStateManager.setLoading(saveButton, 'Saving...');
    }

    try {
      // Delegate to SaveHandler
      const result = await this.saveHandler.save();

      // Re-render grid after save
      if (result.success) {
        this._renderGrid();
        this._recalculateAllProgressTotals();

        // Set button to success state
        if (saveButton) {
          ButtonStateManager.setSuccess(saveButton, 2000);
        }

        Toast.success('Changes saved successfully!');
      } else {
        // Set button to error state
        if (saveButton) {
          ButtonStateManager.setError(saveButton, 2000);
        }

        Toast.error(result.message || 'Failed to save changes');
      }
    } catch (error) {
      console.error('[JadwalKegiatanApp] Save error:', error);

      // Set button to error state
      if (saveButton) {
        ButtonStateManager.setError(saveButton, 2000);
      }

      Toast.error('An error occurred while saving');
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
    const progressMode = (this.state.progressMode || 'planned').toLowerCase();
    const statusLabel = progressMode === 'actual'
      ? 'Perubahan realisasi tersimpan'
      : 'Perubahan perencanaan tersimpan';
    this._updateStatusBar(statusLabel);
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
    this.state.dependencies = this.state.dependencies || [];

    const gridPayload = {
      tree: this.state.pekerjaanTree || [],
      timeColumns: displayColumns,
      inputMode: this.state.inputMode || 'percentage',
      timeScale: this.state.displayScale || this.state.timeScale || 'weekly',
      dependencies: this.state.dependencies || [],
    };

    if (this.state.useUnifiedTable && this.unifiedManager) {
      if (this.state.debugUnifiedTable) {
        console.log('[UnifiedTab] Sync grid payload', {
          rows: gridPayload.tree.length,
          columns: gridPayload.timeColumns.length,
          deps: gridPayload.dependencies.length,
          mode: this.state.progressMode,
          displayScale: this.state.displayScale || this.state.timeScale,
        });
      }
      this.unifiedManager.updateData(gridPayload);
    } else if (this.gridManager) {
      this.gridManager.updateData(gridPayload);
      if (typeof this.gridManager.updateTopScrollMetrics === 'function') {
        this.gridManager.updateTopScrollMetrics();
      }
    }
    this._updateStatusBar();
  }

  _renderGrid() {
    if (this.state.useUnifiedTable) {
      if (!this.unifiedManager) {
        this._initTanStackGridIfNeeded();
      }
      if (this.unifiedManager) {
        this._syncGridViews();
        return;
      }
    }
    if (this.gridManager) {
      this._syncGridViews();
      return;
    }
    if (typeof this._renderLegacyGrid === 'function') {
      this._renderLegacyGrid();
    }
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
    if (this.gridManager && typeof this.gridManager.refreshRowStyles === 'function') {
      this.gridManager.refreshRowStyles();
    }
  }

  _clearSaveErrorRows() {
    if (this.state.saveErrorRows instanceof Set && this.state.saveErrorRows.size > 0) {
      this.state.saveErrorRows.clear();
      if (this.gridManager && typeof this.gridManager.refreshRowStyles === 'function') {
        this.gridManager.refreshRowStyles();
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
    if (removed && this.gridManager && typeof this.gridManager.refreshRowStyles === 'function') {
      this.gridManager.refreshRowStyles();
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
    if (changed && this.gridManager && typeof this.gridManager.refreshCells === 'function') {
      this.gridManager.refreshCells();
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
    if (this.state.showCompletionWarnings && this.gridManager) {
      this.gridManager.refreshRowStyles();
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
    if (this.gridManager && typeof this.gridManager.refreshRowStyles === 'function') {
      this.gridManager.refreshRowStyles();
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

    if (changed && !options.deferRefresh && this.gridManager) {
      this.gridManager.refreshRowStyles();
    }
  }

  _recomputeCompletionWarnings() {
    if (!(this.state.validationWarningRows instanceof Set)) {
      this.state.validationWarningRows = new Set();
    } else {
      this.state.validationWarningRows.clear();
    }
    if (!(this.state.progressTotals instanceof Map)) {
      if (this.gridManager) {
        this.gridManager.refreshRowStyles();
      }
      return;
    }
    this.state.progressTotals.forEach((total, pekerjaanId) => {
      this._updateCompletionWarningRows(Number(pekerjaanId), total, { deferRefresh: true });
    });
    if (this.gridManager) {
      this.gridManager.refreshRowStyles();
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

  _getRowCostCapacity(pekerjaanId) {
    const hargaMap = this.state?.hargaMap;
    const numericId = Number(pekerjaanId);
    if (hargaMap instanceof Map && hargaMap.has(numericId)) {
      return Number(hargaMap.get(numericId)) || 0;
    }
    if (hargaMap && typeof hargaMap === 'object') {
      const key = String(numericId);
      if (Object.prototype.hasOwnProperty.call(hargaMap, key)) {
        return Number(hargaMap[key]) || 0;
      }
    }
    const fallbackNode =
      Array.isArray(this.state.flatPekerjaan) &&
      this.state.flatPekerjaan.find((node) => Number(node.id) === numericId);
    if (fallbackNode) {
      const costFields = [
        'budgeted_cost',
        'total_biaya',
        'totalBiaya',
        'total_cost',
        'biaya',
      ];
      for (const field of costFields) {
        if (typeof fallbackNode[field] !== 'undefined') {
          const numeric = Number(fallbackNode[field]);
          if (Number.isFinite(numeric)) {
            return numeric;
          }
        }
      }
    }
    return 0;
  }

  _getMergedCostCells(modeState) {
    const merged = new Map();
    if (modeState?.costAssignmentMap instanceof Map) {
      modeState.costAssignmentMap.forEach((value, key) => {
        const numeric = Number(value);
        if (Number.isFinite(numeric)) {
          merged.set(key, numeric);
        }
      });
    }
    if (modeState?.costModifiedCells instanceof Map) {
      modeState.costModifiedCells.forEach((value, key) => {
        const numeric = Number(value);
        if (Number.isFinite(numeric)) {
          merged.set(key, numeric);
        }
      });
    }
    return merged;
  }

  _calculateAllCostTotals() {
    const totals = new Map();
    const modeState = this._getCurrentModeState();
    if (!modeState) {
      return totals;
    }
    const merged = this._getMergedCostCells(modeState);
    merged.forEach((value, cellKey) => {
      const pekerjaanId = parseInt((cellKey || '').split('-')[0], 10);
      if (!Number.isFinite(pekerjaanId)) {
        return;
      }
      totals.set(pekerjaanId, (totals.get(pekerjaanId) || 0) + Number(value));
    });
    return totals;
  }

  _formatCurrency(value) {
    const numeric = Number(value) || 0;
    if (!this._currencyFormatter && typeof Intl !== 'undefined') {
      this._currencyFormatter = new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        maximumFractionDigits: 0,
      });
    }
    if (this._currencyFormatter) {
      return this._currencyFormatter.format(numeric);
    }
    return `Rp ${numeric.toLocaleString('id-ID')}`;
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

    const costViolations = [];
    const normalizedMode = (this.state.progressMode || 'planned').toLowerCase();
    if (normalizedMode === 'actual') {
      const costTotals = this._calculateAllCostTotals();
      costTotals.forEach((totalCost, pekerjaanId) => {
        if (!Number.isFinite(totalCost)) {
          return;
        }
        const capacity = this._getRowCostCapacity(pekerjaanId);
        const tolerance = Number.isFinite(capacity) && capacity > 0 ? Math.max(capacity * 0.001, 1) : 1;
        if (Number.isFinite(capacity) && capacity > 0) {
          if (totalCost > capacity + tolerance) {
            costViolations.push({
              type: 'cost',
              pekerjaan_id: pekerjaanId,
              total: totalCost,
              capacity,
            });
          }
        } else if (totalCost > tolerance) {
          costViolations.push({
            type: 'cost',
            pekerjaan_id: pekerjaanId,
            total: totalCost,
            capacity: 0,
            missingCapacity: true,
          });
        }
      });
    }

    if (percentViolations.length === 0 && volumeViolations.length === 0 && costViolations.length === 0) {
      this._clearFailedRows();
      this._clearSaveErrorRows();
      return true;
    }

    const ids = new Set();
    const combined = percentViolations.concat(volumeViolations, costViolations);
    const messages = combined.slice(0, 3).map((item) => {
      ids.add(Number(item.pekerjaan_id));
      if (item.type === 'volume') {
        if (item.missingCapacity) {
          return `- Pekerjaan ${item.pekerjaan_id}: volume tidak dapat disimpan karena master volume 0`;
        }
        return `- Pekerjaan ${item.pekerjaan_id}: total volume ${item.total.toFixed(3)} > kapasitas ${item.capacity.toFixed(3)}`;
      }
      if (item.type === 'cost') {
        if (item.missingCapacity) {
          return `- Pekerjaan ${item.pekerjaan_id}: biaya aktual tidak dapat disimpan karena master biaya 0`;
        }
        return `- Pekerjaan ${item.pekerjaan_id}: total biaya ${this._formatCurrency(item.total)} > batas ${this._formatCurrency(item.capacity)}`;
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
    return this._buildMonthlyColumns(sourceColumns);
  }

  _buildMonthlyColumns(sourceColumns) {
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
      const startDate = this._coerceDate(blockColumns[0]?.startDate || blockColumns[0]?.start_date);
      const endDate = this._coerceDate(blockColumns[blockColumns.length - 1]?.endDate || blockColumns[blockColumns.length - 1]?.end_date);
      const rangeText = this._formatShortRange(startDate, endDate);

      aggregated.push({
        id: `month-${blockIndex + 1}`,
        fieldId: `month_${blockIndex + 1}`,
        label,
        rangeLabel: rangeText || rangeLabel,
        rangeText,
        startDate,
        endDate,
        tooltip: startLabel && endLabel ? `${startLabel} \u2014 ${endLabel}` : `${label}: Week ${startWeek}-${endWeek}`,
        generationMode: 'monthly',
        type: 'monthly',
        index: blockIndex,
        childColumns: blockColumns,
        readOnly: true,
      });
    }

    return aggregated;
  }

  _coerceDate(value) {
    if (!value) {
      return null;
    }
    if (value instanceof Date) {
      return Number.isNaN(value.getTime()) ? null : value;
    }
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  _formatShortRange(startDate, endDate) {
    const format = (date) => {
      if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
        return '';
      }
      const day = String(date.getDate()).padStart(2, '0');
      const month = String(date.getMonth() + 1).padStart(2, '0');
      return `${day}/${month}`;
    };
    const start = format(startDate);
    const end = format(endDate);
    if (start && end) {
      return `${start} - ${end}`;
    }
    return start || end || '';
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
  _handleGridCellChange({
    cellKey,
    value,
    columnMeta,
    displayValue,
    isVolumeMode,
    validation,
    pekerjaanId,
    columnId,
    valueType = 'percentage',
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
    const normalizedValueType = (valueType || (isVolumeMode ? 'volume' : 'percentage')).toLowerCase();
    const isCostMode = normalizedValueType === 'cost';

    console.log(`[CellChange] Mode: ${progressMode.toUpperCase()}, Cell: ${cellKey}, Value: ${normalizedValue}`);

    if (isCostMode) {
      if (progressMode !== 'actual') {
        this.showToast('Biaya aktual hanya bisa diedit pada mode Realisasi', 'warning', 2600);
        return;
      }
      modeState.costModifiedCells.set(cellKey, normalizedValue);
      modeState.isDirty = true;
    } else {
      // Write to mode-specific state (isolated from other mode)
      modeState.modifiedCells.set(cellKey, normalizedValue);
      modeState.isDirty = true;
    }

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

    if (!isCostMode) {
      console.log(`[CellChange] ${progressMode.toUpperCase()} modifiedCells size: ${modeState.modifiedCells.size}`);
      // Phase 2F.0: Real-time Kurva S update on cell change (before save)
      // This allows users to see chart changes immediately as they type
      this._updateCharts();
      console.log(`[CellChange] Real-time Kurva-S chart updated`);
    } else {
      console.log(`[CellChange] Cost map size: ${modeState.costModifiedCells.size}`);
    }
  }

  _bindUnifiedTabSync() {
    if (!this.state.useUnifiedTable) {
      return;
    }
    const scurveTab =
      document.querySelector('#scurve-tab') ||
      document.querySelector('[data-bs-target="#scurve-view"]');
    const ganttTab =
      document.querySelector('#gantt-tab') ||
      document.querySelector('[data-bs-target="#gantt-view"]');
    const gridTab =
      document.querySelector('#grid-tab') ||
      document.querySelector('[data-bs-target="#grid-view"]');

    if (scurveTab) {
      const handler = () => {
        this._restoreGridContainerPosition();
        if (this.unifiedManager) {
          this.unifiedManager.switchMode('kurva');
          if (this.state.debugUnifiedTable) {
            console.log('[UnifiedTab] Switch -> kurva');
          }
        }
      };
      scurveTab.addEventListener('shown.bs.tab', handler);
      scurveTab.addEventListener('click', handler);
    }

    if (ganttTab) {
      const handler = () => {
        const ganttContainer = document.getElementById('gantt-redesign-container');
        if (ganttContainer) {
          this._initializeUnifiedGanttOverlay(ganttContainer);
        } else if (this.unifiedManager) {
          this.unifiedManager.switchMode('gantt');
          if (this.state.debugUnifiedTable) {
            console.log('[UnifiedTab] Switch -> gantt (no overlay host)');
          }
        }
      };
      ganttTab.addEventListener('shown.bs.tab', handler);
      ganttTab.addEventListener('click', handler);
    }

    if (gridTab) {
      const handler = () => {
        this._restoreGridContainerPosition();
        if (this.unifiedManager) {
          this.unifiedManager.switchMode('grid');
          if (this.state.debugUnifiedTable) {
            console.log('[UnifiedTab] Switch -> grid');
          }
        }
      };
      gridTab.addEventListener('shown.bs.tab', handler);
      gridTab.addEventListener('click', handler);
    }
  }

  /**
   * Cleanup and destroy the application
   */
  destroy() {
    this._unbindStateManagerEvents();

    if (this.gridManager) {
      this.gridManager.destroy();
      this.gridManager = null;
    }
    this.unifiedManager = null;

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

