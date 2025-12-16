import { StateManager } from '@modules/core/state-manager.js';

/**
 * AppInitializer - Builds initial state and DOM references for Jadwal Kegiatan
 *
 * This class is responsible for:
 * - Creating the initial application state object with all default values
 * - Building DOM references for all UI elements
 * - Maintaining backward compatibility with window.kelolaTahapanPageState
 *
 * Minimal behavior change: mirrors previous _setupState and _setupDomRefs logic.
 *
 * @class AppInitializer
 * @example
 * const initializer = new AppInitializer();
 * const state = initializer.buildState({ projectId: 123 });
 * const domRefs = initializer.buildDomRefs(state);
 */
export class AppInitializer {
  /**
   * Create a new AppInitializer instance
   * @param {StateManager|null} stateManager - Optional StateManager instance (defaults to singleton)
   */
  constructor(stateManager = null) {
    this.stateManager = stateManager || StateManager.getInstance();
  }

  /**
   * Build initial state object (without side effects beyond window exposure).
   *
   * Creates a complete state object with all necessary properties for the Jadwal Kegiatan page.
   * Includes dual-mode state (planned/actual), DOM refs, API endpoints, and configuration.
   *
   * @param {Object} config - Configuration object
   * @param {number} [config.projectId] - Project ID
   * @param {string} [config.projectName] - Project name
   * @param {string} [config.projectStart] - Project start date (ISO format)
   * @param {string} [config.projectEnd] - Project end date (ISO format)
   * @param {boolean} [config.disableUnifiedTable] - Disable TanStack unified table
   * @param {boolean} [config.enableLegacyGantt] - Enable legacy Frappe Gantt
   * @param {boolean} [config.debugUnifiedTable] - Enable unified table debug logs
   * @param {Object} [config.initialState] - Additional state properties to merge
   * @param {Object|null} existingState - Existing state to merge (for hot reload)
   * @param {Object} options - Additional options
   * @param {Function} options.createTimeColumnIndex - Function to create time column index
   * @returns {Object} Complete state object with all properties initialized
   *
   * @example
   * const state = initializer.buildState({
   *   projectId: 123,
   *   projectName: 'Construction Project',
   *   projectStart: '2025-01-01',
   *   projectEnd: '2025-12-31'
   * });
   */
  buildState(config = {}, existingState = null, options = {}) {
    const createTimeColumnIndex =
      typeof options.createTimeColumnIndex === 'function'
        ? options.createTimeColumnIndex
        : () => ({});

    const state = Object.assign(
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
        progressMode: 'planned',
        displayMode: 'percentage',
        useUnifiedTable: config.disableUnifiedTable ? false : true,
        keepLegacyGantt: config.enableLegacyGantt ? true : false,
        dependencies: [],
        debugUnifiedTable: Boolean(config.debugUnifiedTable || window.DEBUG_UNIFIED_TABLE),

        // Phase 0.3: StateManager reference
        stateManager: this.stateManager,

        // Mode-specific non-cell data
        plannedState: {
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

        // Backward compatibility placeholders
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
    window.kelolaTahapanPageState = state;

    // Build time column index early
    state.timeColumnIndex = createTimeColumnIndex(state.timeColumns);

    return state;
  }

  /**
   * Build DOM references (pure function).
   *
   * Queries the DOM for all required UI elements and stores references in state.domRefs.
   * This is called once during initialization to avoid repeated DOM queries.
   *
   * @param {Object} state - Application state object
   * @param {Object} config - Configuration object
   * @param {Object} [config.domRefs] - Additional DOM refs to merge
   * @returns {Object} DOM references object with all UI elements
   *
   * @property {HTMLElement} root - Main app container (#tahapan-grid-app)
   * @property {HTMLButtonElement} saveButton - Save button (#save-button)
   * @property {HTMLButtonElement} refreshButton - Refresh button (#refresh-button)
   * @property {HTMLButtonElement} resetButton - Reset progress button (#btn-reset-progress)
   * @property {HTMLElement} tanstackGridContainer - TanStack grid container
   * @property {HTMLElement} tanstackGridBody - TanStack grid body
   * @property {HTMLElement} scurveChart - S-Curve chart container
   * @property {HTMLElement} ganttChart - Gantt chart container
   * @property {HTMLElement} statusBar - Status bar element
   * @property {HTMLElement} weekStartSelect - Week start day select
   * @property {HTMLElement} weekEndSelect - Week end day select
   *
   * @example
   * const domRefs = initializer.buildDomRefs(state);
   * domRefs.saveButton.addEventListener('click', handleSave);
   */
  buildDomRefs(state, config = {}) {
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

    state.domRefs = domRefs;
    return domRefs;
  }
}
