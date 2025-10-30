// static/detail_project/js/kelola_tahapan_grid.js
// Excel-like Grid View for Project Scheduling with Gantt & S-Curve

(function() {
  'use strict';

  const appContext = window.KelolaTahapanPageApp || window.JadwalPekerjaanApp || null;
  const moduleManifest = window.KelolaTahapanModuleManifest || null;
  const logger = appContext && appContext.log ? appContext.log : console;
  const EVENT_NAMESPACE = {
    primary: 'kelolaTahapan',
    legacy: 'jadwal',
  };

  function emitPageEvent(eventKey, payload) {
    if (!appContext || typeof appContext.emit !== 'function') {
      return;
    }
    const primaryEvent = `${EVENT_NAMESPACE.primary}:${eventKey}`;
    const aliasMap = (appContext && appContext.constants && appContext.constants.events && appContext.constants.events.LEGACY_ALIASES)
      ? appContext.constants.events.LEGACY_ALIASES
      : {};
    const eventsToEmit = [primaryEvent];

    if (!aliasMap[primaryEvent] && EVENT_NAMESPACE.legacy) {
      eventsToEmit.push(`${EVENT_NAMESPACE.legacy}:${eventKey}`);
    }

    eventsToEmit.forEach((eventName) => {
      try {
        appContext.emit(eventName, payload);
      } catch (error) {
        logger.error('Kelola Tahapan Page emit error for event', eventName, error);
      }
    });
  }

  function getModuleMeta(key, fallback) {
    if (moduleManifest && moduleManifest.modules && moduleManifest.modules[key]) {
      return moduleManifest.modules[key];
    }
    return fallback;
  }

  const hasRegisteredModule = (id) => {
    if (!appContext) return false;
    if (typeof appContext.hasModule === 'function') {
      return appContext.hasModule(id);
    }
    if (appContext.modules instanceof Map) {
      return appContext.modules.has(id);
    }
    return false;
  };

  function ensureStateShape(baseState) {
    const target = (baseState && typeof baseState === 'object') ? baseState : {};

    const arrayKeys = [
      'tahapanList',
      'pekerjaanTree',
      'flatPekerjaan',
      'timeColumns',
      'ganttTasks',
    ];
    arrayKeys.forEach((key) => {
      if (!Array.isArray(target[key])) {
        target[key] = [];
      }
    });

    if (!(target.volumeMap instanceof Map)) target.volumeMap = new Map();
    if (!(target.assignmentMap instanceof Map)) target.assignmentMap = new Map();
    if (!(target.expandedNodes instanceof Set)) target.expandedNodes = new Set();
    if (!(target.modifiedCells instanceof Map)) target.modifiedCells = new Map();
    if (!(target.tahapanProgressMap instanceof Map)) target.tahapanProgressMap = new Map();

    if (typeof target.weekStartDay !== 'number') target.weekStartDay = 0;
    if (typeof target.weekEndDay !== 'number') target.weekEndDay = 6;
    if (!target.timeScale) target.timeScale = 'weekly';
    if (!target.displayMode) target.displayMode = 'percentage';

    if (!Object.prototype.hasOwnProperty.call(target, 'currentCell')) target.currentCell = null;
    if (!Object.prototype.hasOwnProperty.call(target, 'ganttInstance')) target.ganttInstance = null;
    if (!Object.prototype.hasOwnProperty.call(target, 'scurveChart')) target.scurveChart = null;
    if (!(target.flags instanceof Map)) target.flags = new Map();
    if (!target.domRefs || typeof target.domRefs !== 'object') target.domRefs = {};
    if (!target.cache || typeof target.cache !== 'object') target.cache = {};

    return target;
  }

  // =========================================================================
  // MODULE ACCESSORS
  // =========================================================================

  function getGridModule() {
    return (window.KelolaTahapanPageModules && window.KelolaTahapanPageModules.grid) || null;
  }

  function getGanttModule() {
    return (window.KelolaTahapanPageModules && window.KelolaTahapanPageModules.gantt) || null;
  }

  function getKurvaSModule() {
    return (window.KelolaTahapanPageModules && window.KelolaTahapanPageModules.kurvaS) || null;
  }

  function getDataLoaderModule() {
    return (window.KelolaTahapanPageModules && window.KelolaTahapanPageModules.dataLoader) || null;
  }

  function getTimeColumnGeneratorModule() {
    return (window.KelolaTahapanPageModules && window.KelolaTahapanPageModules.timeColumnGenerator) || null;
  }

  function getValidationModule() {
    return (window.KelolaTahapanPageModules && window.KelolaTahapanPageModules.validation) || null;
  }

  function getSaveHandlerModule() {
    return (window.KelolaTahapanPageModules && window.KelolaTahapanPageModules.saveHandler) || null;
  }

  // =========================================================================
  // CONFIGURATION & STATE
  // =========================================================================

  const app = document.getElementById('tahapan-grid-app');
  if (!app) {
    if (appContext) {
      logger.warn('Kelola Tahapan Page: root app element not found, aborting init.');
    }
    return;
  }

  const projectId = parseInt(app.dataset.projectId);
  const apiBase = app.dataset.apiBase;

  const ONE_DAY_MS = 24 * 60 * 60 * 1000;

  // Project data for canonical storage calculations
  window.projectData = {
    id: projectId,
    nama: app.dataset.projectName || '',
    tanggal_mulai: app.dataset.projectStart,
    tanggal_selesai: app.dataset.projectEnd
  };

  // State Management
  const state = ensureStateShape(appContext ? appContext.state : null);
  state.projectId = projectId;
  state.apiBase = apiBase;
  state.projectStart = app.dataset.projectStart;
  state.projectEnd = app.dataset.projectEnd;
  state.domRefs = state.domRefs || {};
  state.meta = state.meta || {};
  state.meta.project = Object.assign({}, state.meta.project, {
    id: projectId,
    tanggal_mulai: app.dataset.projectStart,
    tanggal_selesai: app.dataset.projectEnd,
    name: app.dataset.projectName || '',
  });

  if (appContext) {
    appContext.state = state;
  }

  // Expose state to window for debugging and backwards compatibility
  window.kelolaTahapanPageState = state;
  window.jadwalPekerjaanState = state;

  // DOM Elements
  const $leftTable = document.getElementById('left-table');
  const $rightTable = document.getElementById('right-table');
  const $leftTbody = document.getElementById('left-tbody');
  const $rightTbody = document.getElementById('right-tbody');
  const $timeHeaderRow = document.getElementById('time-header-row');
  const $leftPanelScroll = document.querySelector('.left-panel-scroll');
  const $rightPanelScroll = document.querySelector('.right-panel-scroll');
  const $itemCount = document.getElementById('item-count');
  const $modifiedCount = document.getElementById('modified-count');
  const $totalProgress = document.getElementById('total-progress');
  const $statusMessage = document.getElementById('status-message');
  const $loadingOverlay = document.getElementById('loading-overlay');

  const domRefs = {
    app,
    leftThead: document.getElementById('left-thead'),
    rightThead: document.getElementById('right-thead'),
    leftTable: $leftTable,
    rightTable: $rightTable,
    leftTbody: $leftTbody,
    rightTbody: $rightTbody,
    timeHeaderRow: $timeHeaderRow,
    leftPanelScroll: $leftPanelScroll,
    rightPanelScroll: $rightPanelScroll,
    itemCount: $itemCount,
    modifiedCount: $modifiedCount,
    totalProgress: $totalProgress,
    statusMessage: $statusMessage,
    loadingOverlay: $loadingOverlay,
  };

  state.domRefs = Object.assign({}, state.domRefs, domRefs);
  if (appContext) {
    appContext.state.domRefs = state.domRefs;
    emitPageEvent('dom-ready', { domRefs, state });
  }

  // =========================================================================
  // UTILITY FUNCTIONS
  // =========================================================================

  /**
   * Show/hide loading overlay with optional custom messages
   * @param {boolean|string} show - true/false to show/hide, or string message to show with loading
   * @param {string} submessage - Optional secondary message (shown in smaller text)
   */
  function showLoading(show = true, submessage = '') {
    if (!$loadingOverlay) return;

    const $message = document.getElementById('loading-message');
    const $submessage = document.getElementById('loading-submessage');
    state.cache = state.cache || {};

    const previousMessage = state.cache.lastLoadingMessage || ($message ? $message.textContent : 'Processing...') || 'Processing...';
    const previousSubmessage = state.cache.lastLoadingSubmessage || ($submessage ? $submessage.textContent : '') || '';

    if (show === false) {
      $loadingOverlay.classList.add('d-none');
      if ($submessage) {
        $submessage.classList.add('d-none');
      }
      state.cache.lastLoadingVisible = false;
      emitPageEvent('loading', {
        visible: false,
        message: previousMessage,
        submessage: previousSubmessage,
      });
      return;
    }

    $loadingOverlay.classList.remove('d-none');

    let messageText = previousMessage;
    if (typeof show === 'string' && $message) {
      $message.textContent = show;
      messageText = show;
    } else if ($message && !$message.textContent) {
      $message.textContent = 'Processing...';
      messageText = $message.textContent;
    }

    let activeSubmessage = submessage || '';
    if (activeSubmessage && $submessage) {
      $submessage.textContent = activeSubmessage;
      $submessage.classList.remove('d-none');
    } else if ($submessage) {
      $submessage.classList.add('d-none');
    }

    state.cache.lastLoadingMessage = messageText;
    state.cache.lastLoadingSubmessage = activeSubmessage;
    state.cache.lastLoadingVisible = true;

    emitPageEvent('loading', {
      visible: true,
      message: messageText,
      submessage: activeSubmessage,
    });
  }

  function deriveTimeScaleFromTahapan(tahapanList, fallbackMode = 'weekly') {
    if (!Array.isArray(tahapanList) || tahapanList.length === 0) {
      return fallbackMode;
    }

    const autoCounts = { daily: 0, weekly: 0, monthly: 0 };
    let autoTotal = 0;
    let manualCount = 0;

    tahapanList.forEach((tahap) => {
      if (tahap && tahap.is_auto_generated && typeof tahap.generation_mode === 'string') {
        const mode = tahap.generation_mode.toLowerCase();
        if (autoCounts.hasOwnProperty(mode)) {
          autoCounts[mode] += 1;
          autoTotal += 1;
        }
      } else {
        manualCount += 1;
      }
    });

    if (autoTotal > 0) {
      const dominantMode = Object.entries(autoCounts).reduce((bestMode, entry) => {
        const [mode, count] = entry;
        if (!bestMode) return mode;
        if (count > autoCounts[bestMode]) return mode;
        return bestMode;
      }, '');

      if (dominantMode && autoCounts[dominantMode] > 0) {
        return dominantMode;
      }
    }

    if (manualCount > 0) {
      return 'custom';
    }

    return fallbackMode;
  }

  function updateTimeScaleControls(mode) {
    const radio = document.querySelector(`input[name="timeScale"][value="${mode}"]`);
    if (radio) {
      radio.checked = true;
    }

    const modeBadge = document.getElementById('current-mode-badge');
    if (modeBadge) {
      const modeNames = {
        daily: 'Daily',
        weekly: 'Weekly',
        monthly: 'Monthly',
        custom: 'Custom',
      };
      modeBadge.textContent = `Mode: ${modeNames[mode] || mode}`;
    }
  }

  function initialiseExpandedNodes(tree) {
    if (!Array.isArray(tree) || tree.length === 0) {
      return;
    }

    if (!(state.expandedNodes instanceof Set)) {
      state.expandedNodes = new Set();
    }

    if (state.expandedNodes.size > 0) {
      return;
    }

    const collectIds = (nodes) => {
      nodes.forEach((node) => {
        if (!node || !node.id) return;
        if (node.children && node.children.length > 0) {
          state.expandedNodes.add(node.id);
          collectIds(node.children);
        }
      });
    };

    collectIds(tree);
  }

  function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const toastBody = document.getElementById('toast-body');
    if (!toast || !toastBody) return;

    toast.classList.remove('text-bg-success', 'text-bg-danger', 'text-bg-warning');
    toast.classList.add(`text-bg-${type}`);
    toastBody.textContent = message;

    const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
    bsToast.show();
  }

  async function apiCall(url, options = {}) {
    // Add CSRF token for POST/PUT/DELETE/PATCH requests
    const method = (options.method || 'GET').toUpperCase();
    const needsCSRF = ['POST', 'PUT', 'DELETE', 'PATCH'].includes(method);

    if (needsCSRF) {
      options.headers = options.headers || {};
      options.headers['X-CSRFToken'] = getCookie('csrftoken');
    }

    const response = await fetch(url, {
      credentials: 'same-origin',
      ...options
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  function formatNumber(num, decimals = 2) {
    if (num === null || num === undefined || num === '') return '-';
    const n = parseFloat(num);
    if (isNaN(n)) return '-';
    return n.toLocaleString('id-ID', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
  }

  // =========================================================================
  // DATE UTILITY FUNCTIONS (for time scale modes)
  // =========================================================================

  function getProjectTimeline() {
    // Get from app context or use defaults
    const today = new Date();

    // Try to get from project data passed via context
    const projectData = window.projectData || {};

    const start = projectData.tanggal_mulai
      ? new Date(projectData.tanggal_mulai)
      : today;

    const end = projectData.tanggal_selesai
      ? new Date(projectData.tanggal_selesai)
      : new Date(start.getFullYear(), 11, 31); // Dec 31

    return { start, end };
  }

  function addDays(date, days) {
    const result = new Date(date);
    result.setDate(result.getDate() + days);
    return result;
  }

  function formatDate(date, format = 'short') {
    if (format === 'short') {
      const day = date.getDate().toString().padStart(2, '0');
      const month = date.toLocaleString('id-ID', { month: 'short' });
      return `${day} ${month}`;
    } else if (format === 'iso') {
      return date.toISOString().split('T')[0];
    }
    return date.toLocaleDateString('id-ID');
  }

  function getWeekNumberForDate(targetDate, projectStart = getProjectStartDate()) {
    if (!(targetDate instanceof Date) || Number.isNaN(targetDate.getTime())) {
      return 1;
    }

    if (!(projectStart instanceof Date) || Number.isNaN(projectStart.getTime())) {
      return 1;
    }

    if (targetDate <= projectStart) {
      return 1;
    }

    const weekEndDay = typeof state.weekEndDay === 'number' ? state.weekEndDay : 6; // Default Sunday

    const firstWeekEnd = new Date(projectStart);
    const offsetToEnd = (weekEndDay - projectStart.getDay() + 7) % 7;
    firstWeekEnd.setDate(firstWeekEnd.getDate() + offsetToEnd);

    if (targetDate <= firstWeekEnd) {
      return 1;
    }

    const daysAfterFirst = Math.floor((targetDate - firstWeekEnd) / ONE_DAY_MS);
    return 1 + Math.floor((daysAfterFirst + 6) / 7);
  }

  function getMonthName(date) {
    return date.toLocaleString('id-ID', { month: 'long', year: 'numeric' });
  }

  function formatDayMonth(date) {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
      return '';
    }
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    return `${day}/${month}`;
  }

  function normalizeToISODate(value, fallbackISO) {
    if (!value) {
      return fallbackISO || null;
    }
    if (value instanceof Date) {
      if (Number.isNaN(value.getTime())) {
        return fallbackISO || null;
      }
      return value.toISOString().split('T')[0];
    }
    if (typeof value === 'string') {
      const parsed = new Date(value);
      if (!Number.isNaN(parsed.getTime())) {
        return parsed.toISOString().split('T')[0];
      }
    }
    return fallbackISO || null;
  }

  function calculateTahapanProgress(options = {}) {
    const ganttModule = getGanttModule();
    if (!ganttModule || typeof ganttModule.calculateProgress !== 'function') {
      logger.error('Kelola Tahapan Page: gantt module unavailable for calculateProgress');
      return state.tahapanProgressMap instanceof Map ? state.tahapanProgressMap : new Map();
    }

    try {
      const result = ganttModule.calculateProgress({
        state,
        utils: {
          formatNumber,
          escapeHtml,
          normalizeToISODate,
        },
        options,
      });

      if (result instanceof Map) {
        state.tahapanProgressMap = result;
        return result;
      }

      logger.warn('Kelola Tahapan Page: gantt module returned non-Map progress result');
      return state.tahapanProgressMap instanceof Map ? state.tahapanProgressMap : new Map();
    } catch (error) {
      logger.error('Kelola Tahapan Page: calculateProgress threw an error', error);
      return state.tahapanProgressMap instanceof Map ? state.tahapanProgressMap : new Map();
    }
  }

  function buildGanttTasks(options = {}) {
    const ganttModule = getGanttModule();
    if (!ganttModule || typeof ganttModule.buildTasks !== 'function') {
      logger.error('Kelola Tahapan Page: gantt module unavailable for buildTasks');
      return Array.isArray(state.ganttTasks) ? state.ganttTasks : [];
    }

    try {
      const tasks = ganttModule.buildTasks({
        state,
        utils: {
          normalizeToISODate,
          getProjectStartDate,
        },
        options,
      });
      if (Array.isArray(tasks)) {
        state.ganttTasks = tasks;
        logger.info('Kelola Tahapan Page: buildGanttTasks completed', {
          taskCount: tasks.length,
        });
        return tasks;
      }
      logger.warn('Kelola Tahapan Page: gantt module returned non-array tasks');
      return Array.isArray(state.ganttTasks) ? state.ganttTasks : [];
    } catch (error) {
      logger.error('Kelola Tahapan Page: buildTasks threw an error', error);
      return Array.isArray(state.ganttTasks) ? state.ganttTasks : [];
    }
  }

  function updateGanttChart(forceRecreate = false) {
    const ganttModule = getGanttModule();
    if (!ganttModule || typeof ganttModule.refresh !== 'function') {
      logger.error('Kelola Tahapan Page: gantt module unavailable for refresh');
      return null;
    }

    try {
      return ganttModule.refresh({
        state,
        utils: {
          escapeHtml,
          normalizeToISODate,
          getProjectStartDate,
        },
        options: {
          forceRecreate,
        },
      });
    } catch (error) {
      logger.error('Kelola Tahapan Page: refresh gantt threw an error', error);
      return null;
    }
  }

  function normalizeGanttViewMode(mode) {
    if (!mode) return 'Week';
    const value = String(mode).trim().toLowerCase();
    if (value === 'day') return 'Day';
    if (value === 'month') return 'Month';
    return 'Week';
  }

  function getGanttViewMode() {
    const ganttModule = getGanttModule();
    if (ganttModule && typeof ganttModule.getViewMode === 'function') {
      try {
        return normalizeGanttViewMode(ganttModule.getViewMode({ state }));
      } catch (error) {
        logger.warn('Kelola Tahapan Page: failed to read gantt view mode', error);
      }
    }
    if (state.cache && state.cache.ganttViewMode) {
      return normalizeGanttViewMode(state.cache.ganttViewMode);
    }
    return 'Week';
  }

  function refreshGanttView({ reason = 'manual', rebuildTasks = true, forceRecreate = false } = {}) {
    let shouldRebuild = rebuildTasks;
    if (!Array.isArray(state.ganttTasks) || state.ganttTasks.length === 0) {
      shouldRebuild = true;
    }
    if (shouldRebuild) {
      buildGanttTasks({ reason });
    }
    logger.info('Kelola Tahapan Page: refreshGanttView', {
      reason,
      rebuildTasks: shouldRebuild,
      existingTaskCount: Array.isArray(state.ganttTasks) ? state.ganttTasks.length : 0,
      viewMode: getGanttViewMode(),
    });
    const result = updateGanttChart(forceRecreate);
    updateGanttToolbarActive(getGanttViewMode());
    return result;
  }

  function refreshKurvaS({ reason = 'manual', rebuild = true } = {}) {
    const kurvaModule = getKurvaSModule();
    if (!kurvaModule || typeof kurvaModule.refresh !== 'function') {
      logger.error('Kelola Tahapan Page: kurva S module unavailable for refresh');
      return null;
    }

    try {
      return kurvaModule.refresh({
        state,
        options: {
          reason,
          rebuild,
        },
      });
    } catch (error) {
      logger.error('Kelola Tahapan Page: refresh kurva S threw an error', error);
      return null;
    }
  }

  function handleProgressChange(event = {}) {
    const reason = event.reason || 'cell-edit';
    refreshGanttView({ reason, rebuildTasks: true });
    refreshKurvaS({ reason, rebuild: true });
  }

  function setGanttViewMode(mode, { refresh = true, rebuildTasks = false } = {}) {
    const normalized = normalizeGanttViewMode(mode);
    const ganttModule = getGanttModule();
    try {
      if (ganttModule && typeof ganttModule.setViewMode === 'function') {
        ganttModule.setViewMode(normalized, {
          state,
          refresh: false,
        });
      } else {
        state.cache = state.cache || {};
        state.cache.ganttViewMode = normalized;
      }
    } catch (error) {
      logger.error('Kelola Tahapan Page: setViewMode failed', error);
    }

    state.cache = state.cache || {};
    state.cache.ganttViewMode = normalized;

    if (refresh) {
      refreshGanttView({ reason: 'view-switch', rebuildTasks, forceRecreate: true });
    }
    return normalized;
  }

  function updateGanttToolbarActive(mode, buttonList) {
    const buttons = buttonList || document.querySelectorAll('.gantt-toolbar [data-gantt-view]');
    if (!buttons || typeof buttons.forEach !== 'function') {
      return;
    }
    const normalized = normalizeGanttViewMode(mode);
    buttons.forEach((button) => {
      if (!button || typeof button.getAttribute !== 'function') return;
      const buttonMode = normalizeGanttViewMode(button.getAttribute('data-gantt-view'));
      if (buttonMode === normalized) {
        button.classList.add('active');
      } else {
        button.classList.remove('active');
      }
    });
  }


  // =========================================================================
  // DATA LOADING (Delegated to data_loader_module.js)
  // =========================================================================

  /**
   * Load all data for the page
   * MIGRATED: Delegates to data_loader_module.js
   */
  async function loadAllData(options = {}) {
    const dataLoader = getDataLoaderModule();
    if (!dataLoader) {
      logger.error('Data loader module not available');
      throw new Error('Data loader module not available');
    }

    try {
      const result = await dataLoader.loadAllData({
        state,
        options,
        helpers: {
          showLoading,
          emitEvent: emitPageEvent,
          updateTimeScaleControls,
        }
      });

      // Step 4: Render grid (not handled by dataLoader)
      showLoading('Rendering grid...', 'Building table structure');
      renderGrid();
      updateStatusBar();
      refreshGanttView({ reason: 'initial-load', rebuildTasks: true, forceRecreate: true });
      refreshKurvaS({ reason: 'initial-load', rebuild: true });

      showToast('Data loaded successfully', 'success');
      return result;
    } catch (error) {
      logger.error('Load data failed:', error);
      showToast('Failed to load data: ' + error.message, 'danger');
      throw error;
    } finally {
      showLoading(false);
    }
  }

  /**
   * Legacy wrapper functions for backward compatibility
   * These delegate to data_loader_module.js
   */
  async function loadTahapan() {
    const dataLoader = getDataLoaderModule();
    return dataLoader ? dataLoader.loadTahapan({ state, helpers: { updateTimeScaleControls } }) : null;
  }

  async function loadPekerjaan() {
    const dataLoader = getDataLoaderModule();
    return dataLoader ? dataLoader.loadPekerjaan({ state }) : null;
  }

  async function loadVolumes() {
    const dataLoader = getDataLoaderModule();
    return dataLoader ? dataLoader.loadVolumes({ state }) : null;
  }

  async function loadAssignments(options = {}) {
    const dataLoader = getDataLoaderModule();
    return dataLoader ? dataLoader.loadAssignments({
      state,
      helpers: { showLoading },
      options,
    }) : null;
  }

  function buildPekerjaanTree(response) {
    const dataLoader = getDataLoaderModule();
    return dataLoader ? dataLoader.buildPekerjaanTree(response) : [];
  }

  function flattenTree(tree, result = []) {
    const dataLoader = getDataLoaderModule();
    return dataLoader ? dataLoader.flattenTree(tree, result) : result || [];
  }

  // =========================================================================
  // TIME COLUMNS GENERATION (Delegated to time_column_generator_module.js)
  // =========================================================================

  /**
   * Generate time columns from loaded tahapan data
   * MIGRATED: Delegates to time_column_generator_module.js
   */
  function generateTimeColumns() {
    const timeColumnGen = getTimeColumnGeneratorModule();
    if (!timeColumnGen) {
      logger.error('Time column generator module not available');
      return [];
    }
    return timeColumnGen.generateTimeColumns({ state });
  }

  /**
   * Legacy wrapper functions for backward compatibility
   * These delegate to time_column_generator_module.js
   */
  function generateDailyColumns() {
    const timeColumnGen = getTimeColumnGeneratorModule();
    return timeColumnGen ? timeColumnGen.generateDailyColumns({ state }) : [];
  }

  function generateWeeklyColumns() {
    const timeColumnGen = getTimeColumnGeneratorModule();
    return timeColumnGen ? timeColumnGen.generateWeeklyColumns({ state }) : [];
  }

  function generateMonthlyColumns() {
    const timeColumnGen = getTimeColumnGeneratorModule();
    return timeColumnGen ? timeColumnGen.generateMonthlyColumns({ state }) : [];
  }

  function getProjectStartDate() {
    const timeColumnGen = getTimeColumnGeneratorModule();
    return timeColumnGen ? timeColumnGen.getProjectStartDate(state) : new Date();
  }

  // =========================================================================
  // GRID RENDERING
  // =========================================================================

  function renderGrid() {
    if (!$leftTbody || !$rightTbody || !$timeHeaderRow) return;

    const gridModule = getGridModule();
    if (!gridModule || typeof gridModule.renderTables !== 'function') {
      logger.error('Kelola Tahapan Page: grid module unavailable for renderTables.');
      showToast('Gagal menampilkan grid jadwal.', 'danger');
      return;
    }

    let gridRenderResult;
    try {
      gridRenderResult = gridModule.renderTables({
        state,
        utils: {
          formatNumber,
          escapeHtml,
        },
      });
    } catch (error) {
      logger.error('Kelola Tahapan Page: grid_module.renderTables failed', error);
      showToast('Gagal menampilkan grid jadwal.', 'danger');
      return;
    }

    if (!gridRenderResult || typeof gridRenderResult !== 'object') {
      logger.error('Kelola Tahapan Page: grid module returned invalid render result.');
      showToast('Gagal menampilkan grid jadwal.', 'danger');
      return;
    }

    const leftHTML = typeof gridRenderResult.leftHTML === 'string' ? gridRenderResult.leftHTML : '';
    const rightHTML = typeof gridRenderResult.rightHTML === 'string' ? gridRenderResult.rightHTML : '';

    $leftTbody.innerHTML = leftHTML;
    $rightTbody.innerHTML = rightHTML;

    if (gridModule && typeof gridModule.renderTimeHeaders === 'function') {
      try {
        gridModule.renderTimeHeaders({
          state,
          utils: {
            escapeHtml,
          },
        });
      } catch (error) {
        logger.error('Kelola Tahapan Page: grid_module.renderTimeHeaders failed', error);
      }
    }
    syncHeaderHeights();
    syncRowHeights();
    setupScrollSync();
    attachGridEvents();
  }

  function syncHeaderHeights() {
    const gridModule = getGridModule();
    if (gridModule && typeof gridModule.syncHeaderHeights === 'function') {
      gridModule.syncHeaderHeights(state);
      return;
    }

    const leftHeaderRow = document.querySelector('#left-thead tr');
    const rightHeaderRow = document.querySelector('#right-thead tr');

    if (!leftHeaderRow || !rightHeaderRow) return;

    leftHeaderRow.style.height = '';
    rightHeaderRow.style.height = '';

    const maxHeight = Math.max(leftHeaderRow.offsetHeight, rightHeaderRow.offsetHeight);
    leftHeaderRow.style.height = `${maxHeight}px`;
    rightHeaderRow.style.height = `${maxHeight}px`;
  }

  function syncRowHeights() {
    const gridModule = getGridModule();
    if (gridModule && typeof gridModule.syncRowHeights === 'function') {
      gridModule.syncRowHeights(state);
      return;
    }

    const leftRows = $leftTbody.querySelectorAll('tr');
    const rightRows = $rightTbody.querySelectorAll('tr');

    leftRows.forEach((leftRow, index) => {
      const rightRow = rightRows[index];
      if (!rightRow) return;

      leftRow.style.height = '';
      rightRow.style.height = '';

      const leftHeight = leftRow.offsetHeight;
      const rightHeight = rightRow.offsetHeight;
      const maxHeight = Math.max(leftHeight, rightHeight);

      leftRow.style.height = `${maxHeight}px`;
      rightRow.style.height = `${maxHeight}px`;
    });
  }

  function setupScrollSync() {
    const gridModule = getGridModule();
    if (gridModule && typeof gridModule.setupScrollSync === 'function') {
      gridModule.setupScrollSync(state);
      return;
    }

    const domCache = state.domRefs || {};
    const leftPanel = domCache.leftPanelScroll || document.querySelector('.left-panel-scroll');
    const rightPanel = domCache.rightPanelScroll || document.querySelector('.right-panel-scroll');

    if (!leftPanel || !rightPanel) {
      return;
    }

    state.cache = state.cache || {};
    if (state.cache.legacyScrollSyncBound) {
      return;
    }

    const syncFromRight = () => {
      if (leftPanel.scrollTop !== rightPanel.scrollTop) {
        leftPanel.scrollTop = rightPanel.scrollTop;
      }
    };

    const syncFromLeft = () => {
      if (rightPanel.scrollTop !== leftPanel.scrollTop) {
        rightPanel.scrollTop = leftPanel.scrollTop;
      }
    };

    rightPanel.addEventListener('scroll', syncFromRight, { passive: true });
    leftPanel.addEventListener('scroll', syncFromLeft, { passive: true });

    state.cache.legacyScrollSyncBound = {
      syncFromRight,
      syncFromLeft,
    };
  }

  // =========================================================================
  // EVENT HANDLERS
  // =========================================================================

  function attachGridEvents() {
    const gridModule = getGridModule();
    if (!gridModule || typeof gridModule.attachEvents !== 'function') {
      logger.error('Kelola Tahapan Page: grid module unavailable for attachEvents.');
      return;
    }

    try {
      gridModule.attachEvents({
        state,
        utils: {
          formatNumber,
          escapeHtml,
        },
        helpers: {
          showToast,
          updateStatusBar,
          onProgressChange: handleProgressChange,
        },
      });
    } catch (error) {
      logger.error('Kelola Tahapan Page: grid_module.attachEvents failed', error);
    }
  }

  // =========================================================================
  // STATUS BAR & STATISTICS
  // =========================================================================

  function updateStatusBar() {
    if ($itemCount) {
      const pekerjaanCount = state.flatPekerjaan.filter(n => n.type === 'pekerjaan').length;
      $itemCount.textContent = pekerjaanCount;
    }

    if ($modifiedCount) {
      $modifiedCount.textContent = state.modifiedCells.size;
    }

    if ($totalProgress) {
      // Calculate overall progress
      let totalPercent = 0;
      let count = 0;

      state.flatPekerjaan.filter(n => n.type === 'pekerjaan').forEach(node => {
        const assignments = state.assignmentMap.get(node.id) || {};
        const sum = Object.values(assignments).reduce((a, b) => a + b, 0);
        totalPercent += sum;
        count++;
      });

      const avgProgress = count > 0 ? (totalPercent / count).toFixed(1) : 0;
      $totalProgress.textContent = `${avgProgress}%`;
    }
  }

  // =========================================================================
  // SAVE FUNCTIONALITY
  // =========================================================================

  // =========================================================================
  // VALIDATION (Delegated to validation_module.js)
  // =========================================================================

  /**
   * Calculate total progress for a pekerjaan
   * MIGRATED: Delegates to validation_module.js
   */
  function calculateTotalProgress(pekerjaanId, pendingChanges = {}) {
    const validation = getValidationModule();
    if (!validation) {
      logger.error('Validation module not available');
      return 0;
    }
    return validation.calculateTotalProgress(pekerjaanId, pendingChanges, state);
  }

  /**
   * Validate and apply visual feedback for progress totals
   * MIGRATED: Delegates to validation_module.js
   */
  function validateProgressTotals(changesByPekerjaan) {
    const validation = getValidationModule();
    if (!validation) {
      logger.error('Validation module not available');
      return { isValid: true, errors: [], warnings: [] };
    }
    return validation.validateProgressTotals(changesByPekerjaan, state);
  }

  /**
   * Update visual feedback (border colors) for pekerjaan rows
   * MIGRATED: Delegates to validation_module.js
   */
  function updateProgressVisualFeedback(pekerjaanId, total) {
    const validation = getValidationModule();
    if (!validation) {
      logger.warn('Validation module not available');
      return;
    }
    return validation.updateProgressVisualFeedback(pekerjaanId, total);
  }

  // =========================================================================
  // SAVE FUNCTIONALITY (Delegated to save_handler_module.js)
  // =========================================================================
  //
  // OVERVIEW:
  // All save operations are now handled by the save_handler_module.js for better
  // code organization and reusability. This section contains thin wrapper functions
  // that delegate to the module while maintaining backward compatibility.
  //
  // ARCHITECTURE:
  // - saveAllChanges(): Main entry point for saving all modified cells
  // - savePekerjaanAssignments(): Save single pekerjaan (used internally)
  // - resetAllProgress(): Clear all progress data (dangerous operation!)
  //
  // DELEGATION PATTERN:
  // Each function:
  // 1. Gets the save_handler_module instance
  // 2. Checks if module is available (fail-fast if not)
  // 3. Delegates to module with proper context (state + helpers)
  // 4. Returns result directly to caller
  //
  // WHY DELEGATION?
  // - Keeps main file clean and focused on orchestration
  // - Allows independent testing of save logic
  // - Enables reuse in other pages/components
  // - Makes debugging easier (module has single responsibility)
  //
  // =========================================================================

  /**
   * Save all changes to server with validation and canonical storage conversion
   *
   * FLOW:
   * 1. Checks if there are modified cells
   * 2. Groups changes by pekerjaan ID
   * 3. Validates total progress <= 100% for each pekerjaan
   * 4. Saves each pekerjaan with canonical weekly storage conversion
   * 5. Updates UI to reflect saved state
   *
   * CANONICAL STORAGE:
   * All modes (daily/weekly/monthly/custom) are converted to weekly format before
   * saving to ensure lossless data preservation. See save_handler_module.js for
   * detailed conversion logic.
   *
   * ERROR HANDLING:
   * - Shows user-friendly error messages
   * - Blocks save if validation fails (total > 100%)
   * - Allows save with warnings if total < 100% (incomplete)
   *
   * @async
   * @returns {Promise<Object|null>} Save result with success count, or null if no changes
   *
   * @example
   * // Called when user clicks "Save All" button
   * await saveAllChanges();
   * // Returns: { success: true, savedCount: 5, totalPekerjaan: 5 }
   *
   * @throws {Error} If save_handler_module is not available or save operation fails
   *
   * @see save_handler_module.js for implementation details
   * @see validation_module.js for validation logic
   */
  async function saveAllChanges() {
    // Get the save handler module
    const saveHandler = getSaveHandlerModule();

    // Fail-fast if module not loaded
    if (!saveHandler) {
      logger.error('SaveHandler module not available. Ensure save_handler_module.js is loaded.');
      showToast('System error: Save module not available', 'danger');
      return null;
    }

    // Delegate to module with all required context
    // The module will handle:
    // - Validation
    // - Grouping changes
    // - Converting to canonical storage
    // - API calls
    // - UI updates
    const result = await saveHandler.saveAllChanges({
      state,  // Current application state
      helpers: {
        showLoading,      // Loading overlay helper
        showToast,        // Notification helper
        updateStatusBar   // Status bar update helper
      }
    });

    refreshGanttView({ reason: 'save-all', rebuildTasks: true });
    refreshKurvaS({ reason: 'save-all', rebuild: true });
    return result;
  }

  /**
   * Save assignments for a single pekerjaan with canonical storage conversion
   *
   * INTERNAL FUNCTION:
   * This function is typically called by saveAllChanges() for each pekerjaan.
   * It can also be called directly if you need to save a single pekerjaan.
   *
   * CANONICAL STORAGE CONVERSION:
   * Converts assignments from current mode to weekly canonical format:
   * - Weekly: Direct 1:1 mapping (no conversion needed)
   * - Daily: Aggregates daily values into weekly totals
   * - Monthly: Splits monthly evenly to daily, then aggregates to weekly
   * - Custom: Calculates week number from tahapan dates
   *
   * WHY WEEKLY CANONICAL?
   * - Lossless: Can reconstruct any view (daily/weekly/monthly) from weekly data
   * - Efficient: Balanced granularity (not too fine, not too coarse)
   * - Standard: Industry standard for project scheduling
   *
   * @async
   * @param {string|number} pekerjaanId - ID of the pekerjaan to save
   * @param {Object} assignments - Assignments by tahapan ID { tahapanId: proportion }
   * @returns {Promise<void>}
   *
   * @example
   * // Save progress for pekerjaan 123
   * await savePekerjaanAssignments(123, {
   *   841: 50,  // Tahapan 841: 50% progress
   *   842: 30   // Tahapan 842: 30% progress
   * });
   *
   * @throws {Error} If save_handler_module not available or API call fails
   *
   * @see save_handler_module.js#savePekerjaanAssignments for conversion details
   */
  async function savePekerjaanAssignments(pekerjaanId, assignments) {
    // Get the save handler module
    const saveHandler = getSaveHandlerModule();

    // Fail-fast if module not loaded
    if (!saveHandler) {
      logger.error('SaveHandler module not available');
      throw new Error('SaveHandler module not available. Cannot save pekerjaan assignments.');
    }

    // Delegate to module
    // The module will:
    // - Convert assignments to weekly canonical format
    // - Call API endpoint with proper payload
    // - Handle errors gracefully
    return await saveHandler.savePekerjaanAssignments(pekerjaanId, assignments, {
      state,
      helpers: {}  // This function doesn't need UI helpers (called internally)
    });
  }

  // =========================================================================
  // RESET PROGRESS FUNCTIONALITY (Delegated to save_handler_module.js)
  // =========================================================================
  //
  // DANGER ZONE!
  // This operation is IRREVERSIBLE and will delete ALL progress data for ALL
  // pekerjaan in the current project.
  //
  // SAFETY MEASURES:
  // 1. Requires user confirmation via browser confirm() dialog
  // 2. Shows clear warning message about data loss
  // 3. Logs all operations for audit trail
  //
  // USE CASES:
  // - Starting over with fresh data
  // - Fixing corrupted data
  // - Testing/development scenarios
  //
  // ALTERNATIVES:
  // - If you only want to clear specific pekerjaan, use cell editing (set to 0)
  // - If you want to preserve old data, consider creating a backup first
  //
  // =========================================================================

  /**
   * Reset all progress to 0 for all pekerjaan (DANGEROUS OPERATION!)
   *
   * DANGER: This operation is IRREVERSIBLE!
   * All progress data will be permanently deleted from the database.
   *
   * FLOW:
   * 1. Shows confirmation dialog with clear warning
   * 2. If confirmed, calls API to delete all progress records
   * 3. Clears in-memory state (assignmentMap, modifiedCells)
   * 4. Re-renders grid to show empty state
   *
   * WHAT GETS DELETED:
   * - All PekerjaanProgressWeekly records (canonical storage)
   * - All PekerjaanTahapan records (view layer)
   * - All in-memory progress data
   *
   * WHAT IS PRESERVED:
   * - Pekerjaan definitions (uraian, volume, satuan)
   * - Tahapan definitions (dates, names)
   * - Project metadata
   *
   * @async
   * @returns {Promise<Object|null>} Reset result with deleted count, or null if cancelled
   *
   * @example
   * // Called when user clicks "Reset All Progress" button
   * const result = await resetAllProgress();
   * // Returns: { success: true, deletedCount: 450 }
   * // Or null if user cancelled
   *
   * @throws {Error} If save_handler_module not available or API call fails
   *
   * @see save_handler_module.js#resetAllProgress for implementation
   */
  async function resetAllProgress() {
    // Get the save handler module
    const saveHandler = getSaveHandlerModule();

    // Fail-fast if module not loaded
    if (!saveHandler) {
      logger.error('SaveHandler module not available');
      showToast('System error: Save module not available', 'danger');
      return null;
    }

    // Delegate to module
    // The module will:
    // - Show confirmation dialog
    // - Call reset API endpoint
    // - Clear state maps
    // - Trigger grid re-render
    const result = await saveHandler.resetAllProgress({
      state,
      helpers: {
        showLoading,      // Loading overlay
        showToast,        // Notifications
        updateStatusBar,  // Status bar
        renderGrid        // Grid re-render function
      }
    });

    refreshGanttView({ reason: 'reset-progress', rebuildTasks: true, forceRecreate: true });
    refreshKurvaS({ reason: 'reset-progress', rebuild: true });
    return result;
  }

  // =========================================================================
  // GANTT CHART
  // =========================================================================

  function initGanttChart() {
    const ganttModule = getGanttModule();
    if (ganttModule && typeof ganttModule.init === 'function') {
      try {
        const result = ganttModule.init({
          state,
          utils: {
            normalizeToISODate,
            getProjectStartDate,
            escapeHtml,
          },
        });
        if (result !== 'legacy') {
          return result;
        }
      } catch (error) {
        logger.error('Kelola Tahapan Page: init gantt via module failed', error);
      }
    }
    logger.warn('Kelola Tahapan Page: gantt module requested legacy fallback, but legacyInitGanttChart is no longer available.');
    showToast('Gagal menampilkan Gantt chart: modul tidak siap.', 'warning');
    return null;
  }

  // =========================================================================
  // KURVA S CHART
  // =========================================================================

  function initScurveChart(context = {}) {
    const kurvaModule = getKurvaSModule();
    if (kurvaModule && typeof kurvaModule.init === 'function') {
      try {
        const result = kurvaModule.init({
          state,
          option: context.option,
          getDefaultOption: context.getDefaultOption,
        });
        if (result !== 'legacy') {
          refreshKurvaS({ reason: context.reason || 'init', rebuild: true });
          return result;
        }
      } catch (error) {
        logger.error('Kelola Tahapan Page: init Kurva S via module failed', error);
      }
    }
    logger.warn('Kelola Tahapan Page: kurva S module requested legacy fallback, but legacyInitScurveChart is no longer available.');
    showToast('Kurva S tidak dapat dimuat: modul tidak siap.', 'warning');
    return null;
  }

  // =========================================================================
  // TIME SCALE MODE SWITCHING (with backend regeneration)
  // =========================================================================

  async function switchTimeScaleMode(newMode) {
    console.log(`Switching time scale mode to: ${newMode}`);

    try {
      // Step 1: Regenerate tahapan on backend
      showLoading(`Switching to ${newMode} mode...`, 'Regenerating tahapan and syncing from canonical storage');

      // IMPORTANT: Use API V2 for lossless mode switching!
      // API V2 syncs from PekerjaanProgressWeekly (canonical storage)
      // instead of converting from PekerjaanTahapan (view layer)
      const response = await apiCall(`/detail_project/api/v2/project/${projectId}/regenerate-tahapan/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mode: newMode,
          week_start_day: state.weekStartDay || 0,  // Default: Monday
          week_end_day: state.weekEndDay || 6       // Default: Sunday
          // NOTE: No convert_assignments flag - V2 always syncs from canonical!
        })
      });

      console.log(`Regenerate response:`, response);

      if (response.ok) {
        // Update state
        state.timeScale = newMode;
        updateTimeScaleControls(newMode);

        // Step 2: Reload tahapan list
        showLoading(`Switching to ${newMode} mode...`, 'Loading updated tahapan list');
        await loadTahapan();

        // Step 3: Regenerate time columns
        showLoading(`Switching to ${newMode} mode...`, 'Generating time columns');
        generateTimeColumns();

        // Step 4: Reload assignments
        showLoading(`Switching to ${newMode} mode...`, 'Loading converted assignments');
        await loadAssignments();

        // Step 5: Re-render grid
        showLoading(`Switching to ${newMode} mode...`, 'Rendering updated grid');
        renderGrid();
        updateStatusBar();
        refreshGanttView({ reason: 'time-scale-switch', rebuildTasks: true, forceRecreate: true });
        refreshKurvaS({ reason: 'time-scale-switch', rebuild: true });

        // Show success message
        showToast(`Mode switched to ${newMode}. ${response.message || ''}`, 'success');
      } else {
        console.error('Failed to regenerate tahapan:', response.error);
        showToast(`Error: ${response.error || 'Failed to switch mode'}`, 'danger');
      }

    } catch (error) {
      console.error('Error switching mode:', error);
      showToast(`Error switching mode: ${error.message}`, 'danger');
    } finally {
      showLoading(false);
    }
  }

  // =========================================================================
  // EVENT BINDINGS
  // =========================================================================
  // Moved to tab-specific modules (grid_tab.js, gantt_tab.js, kurva_s_tab.js)
  // Prevent accidental page closure with unsaved changes
  window.addEventListener('beforeunload', (e) => {
    if (state.modifiedCells.size > 0) {
      // Show browser's standard "unsaved changes" warning
      e.preventDefault();
      e.returnValue = ''; // Chrome requires returnValue to be set
      return ''; // Some browsers show this message
    }
  });

  // =========================================================================

  if (appContext && typeof appContext.registerModule === 'function') {
    const gridMeta = getModuleMeta('grid', { id: 'kelolaTahapanGridView', namespace: 'kelola_tahapan.grid' });
    if (!hasRegisteredModule(gridMeta.id)) {
      appContext.registerModule(gridMeta.id, {
        namespace: gridMeta.namespace || 'kelola_tahapan.grid',
        pageId: moduleManifest?.pageId || 'kelola_tahapan',
        description: gridMeta.description,
        init: () => loadAllData(),
        refresh: renderGrid,
        updateStatusBar,
        updateTimeScaleControls,
        saveAllChanges,
        resetAllProgress,
        switchTimeScaleMode,
        getState: () => state,
        getAssignments: () => state.assignmentMap,
      });
    } else {
      logger.info('Kelola Tahapan Page: grid module already provided. Skipping auto registration.');
    }

    const ganttMeta = getModuleMeta('gantt', { id: 'kelolaTahapanGanttView', namespace: 'kelola_tahapan.gantt' });
    if (!hasRegisteredModule(ganttMeta.id)) {
      appContext.registerModule(ganttMeta.id, {
        namespace: ganttMeta.namespace || 'kelola_tahapan.gantt',
        pageId: moduleManifest?.pageId || 'kelola_tahapan',
        description: ganttMeta.description,
        init: initGanttChart,
        refresh: updateGanttChart,
        setViewMode: (mode, options) => setGanttViewMode(mode, Object.assign({ refresh: true, rebuildTasks: false }, options || {})),
        getViewMode: getGanttViewMode,
        getTasks: () => state.ganttTasks.slice(),
        getProgressMap: () => state.tahapanProgressMap,
      });
    } else {
      logger.info('Kelola Tahapan Page: gantt module already provided. Skipping auto registration.');
    }

    const kurvaMeta = getModuleMeta('kurvaS', { id: 'kelolaTahapanKurvaSView', namespace: 'kelola_tahapan.kurva_s' });
    if (!hasRegisteredModule(kurvaMeta.id)) {
      appContext.registerModule(kurvaMeta.id, {
        namespace: kurvaMeta.namespace || 'kelola_tahapan.kurva_s',
        pageId: moduleManifest?.pageId || 'kelola_tahapan',
        description: kurvaMeta.description,
        init: initScurveChart,
        resize() {
          if (state.scurveChart) {
            state.scurveChart.resize();
          }
        },
        getChart: () => state.scurveChart,
      });
    } else {
      logger.info('Kelola Tahapan Page: kurva S module already provided. Skipping auto registration.');
    }

    emitPageEvent('modules-registered', { state, manifest: moduleManifest });

    // Initialize tab controller modules after registration
    // This ensures button event bindings are attached after facade is ready
    if (typeof requestAnimationFrame !== 'undefined') {
      requestAnimationFrame(() => {
        const tabModuleIds = ['kelolaTahapanGridTab', 'kelolaTahapanGanttTab', 'kelolaTahapanKurvaSTab'];
        tabModuleIds.forEach((moduleId) => {
          const mod = appContext.getModule(moduleId);
          if (mod && typeof mod.init === 'function') {
            try {
              mod.init();
              logger.info(`Kelola Tahapan Page: Initialized tab module ${moduleId}`);
            } catch (error) {
              logger.error(`Kelola Tahapan Page: Failed to init ${moduleId}`, error);
            }
          }
        });
      });
    }
  }

  const gridHelpers = getGridModule();
  const ganttHelpers = getGanttModule();
  const kurvaHelpers = getKurvaSModule();

  window.KelolaTahapanPage = Object.assign({}, window.KelolaTahapanPage || {}, {
    pageId: 'kelola_tahapan',
    manifest: moduleManifest,
    getState: () => state,
    state,
    grid: Object.assign({}, (window.KelolaTahapanPage && window.KelolaTahapanPage.grid) || {}, {
      loadAllData,
      renderGrid,
      updateStatusBar,
      updateTimeScaleControls,
      switchTimeScaleMode,
      saveAllChanges,
      resetAllProgress,
      getState: () => state,
      getAssignments: () => state.assignmentMap,
      syncHeaderHeights: () => gridHelpers && gridHelpers.syncHeaderHeights ? gridHelpers.syncHeaderHeights(state) : undefined,
      syncRowHeights: () => gridHelpers && gridHelpers.syncRowHeights ? gridHelpers.syncRowHeights(state) : undefined,
      setupScrollSync: () => gridHelpers && gridHelpers.setupScrollSync ? gridHelpers.setupScrollSync(state) : undefined,
      attachEvents: (context = {}) => {
        if (!gridHelpers || typeof gridHelpers.attachEvents !== 'function') return;
        return gridHelpers.attachEvents({
          state,
          utils: Object.assign({ formatNumber, escapeHtml }, context.utils || {}),
          helpers: Object.assign({ showToast, updateStatusBar, onProgressChange: handleProgressChange }, context.helpers || {}),
        });
      },
      enterEditMode: (cell, initialValue = '', context = {}) => {
        if (!gridHelpers || typeof gridHelpers.enterEditMode !== 'function') return;
        return gridHelpers.enterEditMode(
          cell,
          {
            state,
            utils: Object.assign({ formatNumber, escapeHtml }, context.utils || {}),
            helpers: Object.assign({ showToast, updateStatusBar, onProgressChange: handleProgressChange }, context.helpers || {}),
          },
          initialValue
        );
      },
      exitEditMode: (cell, input, context = {}) => {
        if (!gridHelpers || typeof gridHelpers.exitEditMode !== 'function') return;
        return gridHelpers.exitEditMode(cell, input, {
          state,
          utils: Object.assign({ formatNumber, escapeHtml }, context.utils || {}),
          helpers: Object.assign({ showToast, updateStatusBar, onProgressChange: handleProgressChange }, context.helpers || {}),
        });
      },
      navigateCell: (direction, context = {}) => {
        if (!gridHelpers || typeof gridHelpers.navigateCell !== 'function') return;
        return gridHelpers.navigateCell({
          state,
          utils: Object.assign({ formatNumber, escapeHtml }, context.utils || {}),
          helpers: Object.assign({ showToast, updateStatusBar, onProgressChange: handleProgressChange }, context.helpers || {}),
        }, direction);
      },
      renderTables: (context = {}) => {
        if (!gridHelpers || typeof gridHelpers.renderTables !== 'function') return null;
        return gridHelpers.renderTables(Object.assign({ state }, context || {}));
      },
    }),
    gantt: Object.assign({}, (window.KelolaTahapanPage && window.KelolaTahapanPage.gantt) || {}, {
      init: (context = {}) => {
        if (!ganttHelpers || typeof ganttHelpers.init !== 'function') return null;
        return ganttHelpers.init(Object.assign({ state }, context || {}));
      },
      refresh: (context = {}) => {
        if (!ganttHelpers || typeof ganttHelpers.refresh !== 'function') return null;
        return ganttHelpers.refresh(Object.assign({ state }, context || {}));
      },
      buildTasks: (context = {}) => buildGanttTasks(context),
      calculateProgress: (context = {}) => calculateTahapanProgress(context),
      getTasks: () => state.ganttTasks.slice(),
      getProgressMap: () => state.tahapanProgressMap,
      setViewMode: (mode, options) => setGanttViewMode(mode, Object.assign({ refresh: true }, options || {})),
      getViewMode: getGanttViewMode,
      refreshView: (options = {}) => refreshGanttView(Object.assign({ rebuildTasks: false }, options)),
    }),
    kurvaS: Object.assign({}, (window.KelolaTahapanPage && window.KelolaTahapanPage.kurvaS) || {}, {
      init: (context = {}) => {
        if (!kurvaHelpers || typeof kurvaHelpers.init !== 'function') return null;
        return kurvaHelpers.init(Object.assign({ state }, context || {}));
      },
      refresh: (context = {}) => {
        if (!kurvaHelpers || typeof kurvaHelpers.refresh !== 'function') return null;
        return kurvaHelpers.refresh(Object.assign({ state }, context || {}));
      },
      resize: (context = {}) => {
        if (!kurvaHelpers || typeof kurvaHelpers.resize !== 'function') return null;
        return kurvaHelpers.resize(Object.assign({ state }, context || {}));
      },
      getChart: () => {
        if (!kurvaHelpers || typeof kurvaHelpers.getChart !== 'function') return state.scurveChart;
        return kurvaHelpers.getChart({ state });
      },
      refreshView: (options = {}) => refreshKurvaS(Object.assign({ rebuild: true }, options)),
    }),
    shared: Object.assign({}, (window.KelolaTahapanPage && window.KelolaTahapanPage.shared) || {}, {
      emit: emitPageEvent,
      manifest: moduleManifest,
      bootstrap: appContext,
    }),
    events: Object.assign({}, (window.KelolaTahapanPage && window.KelolaTahapanPage.events) || {}, {
      emit: emitPageEvent,
    }),
  });


  // =========================================================================
  // INITIALIZATION
  // =========================================================================

  loadAllData();
})();
