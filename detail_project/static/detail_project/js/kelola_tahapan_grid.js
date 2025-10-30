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

  function getGridModule() {
    return (window.KelolaTahapanPageModules && window.KelolaTahapanPageModules.grid) || null;
  }

  function getGanttModule() {
    return (window.KelolaTahapanPageModules && window.KelolaTahapanPageModules.gantt) || null;
  }

  function getKurvaSModule() {
    return (window.KelolaTahapanPageModules && window.KelolaTahapanPageModules.kurvaS) || null;
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


  // =========================================================================
  // DATA LOADING
  // =========================================================================

  async function loadAllData(options = {}) {
    state.cache = state.cache || {};
    if (state.cache.initialLoadInProgress) {
      logger.info('Kelola Tahapan Page: loadAllData skipped (already in progress).');
      return null;
    }
    if (!options.force && state.cache.initialLoadCompleted && options.skipIfLoaded) {
      logger.info('Kelola Tahapan Page: loadAllData skipped (already completed).');
      return state.cache.initialLoadResult || null;
    }

    state.cache.initialLoadInProgress = true;
    emitPageEvent('data-load:start', {
      projectId,
      timeScale: state.timeScale,
      displayMode: state.displayMode,
    });
    try {
      // Step 1: Load base data
      showLoading('Loading project data...', 'Fetching tahapan, pekerjaan, and volumes');
      await Promise.all([
        loadTahapan(),
        loadPekerjaan(),
        loadVolumes()
      ]);

      // Step 2: Generate time columns
      showLoading('Generating time columns...', 'Mapping tahapan to grid structure');
      generateTimeColumns();

      // Step 3: Load assignments
      showLoading('Loading assignments...', 'Fetching progress data for all pekerjaan');
      await loadAssignments();

      // Step 4: Render grid
      showLoading('Rendering grid...', 'Building table structure');
      renderGrid();
      updateStatusBar();

      showToast('Data loaded successfully', 'success');
      state.cache.initialLoadCompleted = true;
      state.cache.initialLoadResult = {
        completedAt: Date.now(),
        tahapanCount: state.tahapanList.length,
        pekerjaanCount: state.flatPekerjaan.filter(node => node.type === 'pekerjaan').length,
      };
      emitPageEvent('data-load:success', {
        projectId,
        result: state.cache.initialLoadResult,
        stateSnapshot: {
          timeScale: state.timeScale,
          displayMode: state.displayMode,
        },
      });
    } catch (error) {
      console.error('Load data failed:', error);
      showToast('Failed to load data: ' + error.message, 'danger');
      state.cache.initialLoadError = error;
      emitPageEvent('data-load:error', { projectId, error });
    } finally {
      state.cache.initialLoadInProgress = false;
      showLoading(false);
    }
  }

  async function loadTahapan() {
    try {
      const data = await apiCall(apiBase);
      state.tahapanList = (data.tahapan || []).sort((a, b) => a.urutan - b.urutan);

      const detectedMode = deriveTimeScaleFromTahapan(state.tahapanList, state.timeScale || 'weekly');
      state.timeScale = detectedMode;
      updateTimeScaleControls(detectedMode);

      return state.tahapanList;
    } catch (error) {
      console.error('Failed to load tahapan:', error);
      throw error;
    }
  }

  async function loadPekerjaan() {
    try {
      const response = await apiCall(`/detail_project/api/project/${projectId}/list-pekerjaan/tree/`);

      // Build hierarchical tree
      const tree = buildPekerjaanTree(response);
      state.pekerjaanTree = tree;

      // Flatten for easy access
      state.flatPekerjaan = flattenTree(tree);
      initialiseExpandedNodes(tree);

      return state.pekerjaanTree;
    } catch (error) {
      console.error('Failed to load pekerjaan:', error);
      throw error;
    }
  }

  function buildPekerjaanTree(response) {
    const tree = [];
    const data = response.klasifikasi || response;

    if (!Array.isArray(data)) return tree;

    data.forEach(klas => {
      const klasNode = {
        id: `klas-${klas.id || klas.nama}`,
        type: 'klasifikasi',
        nama: klas.name || klas.nama || 'Klasifikasi',
        children: [],
        level: 0,
        expanded: true
      };

      if (klas.sub && Array.isArray(klas.sub)) {
        klas.sub.forEach(sub => {
          const subNode = {
            id: `sub-${sub.id || sub.nama}`,
            type: 'sub-klasifikasi',
            nama: sub.name || sub.nama || 'Sub-Klasifikasi',
            children: [],
            level: 1,
            expanded: true
          };

          if (sub.pekerjaan && Array.isArray(sub.pekerjaan)) {
            sub.pekerjaan.forEach(pkj => {
              const pkjNode = {
                id: pkj.id || pkj.pekerjaan_id,
                type: 'pekerjaan',
                kode: pkj.snapshot_kode || pkj.kode || '',
                nama: pkj.snapshot_uraian || pkj.uraian || '',
                volume: pkj.volume || 0,
                satuan: pkj.snapshot_satuan || pkj.satuan || '-',
                level: 2
              };
              subNode.children.push(pkjNode);
            });
          }

          klasNode.children.push(subNode);
        });
      }

      tree.push(klasNode);
    });

    return tree;
  }

  function flattenTree(tree, result = []) {
    tree.forEach(node => {
      result.push(node);
      if (node.children && node.children.length > 0) {
        flattenTree(node.children, result);
      }
    });
    return result;
  }

  async function loadVolumes() {
    try {
      const data = await apiCall(`/detail_project/api/project/${projectId}/volume-pekerjaan/list/`);
      state.volumeMap.clear();

      const volumes = data.items || data.volumes || data.data || [];
      if (Array.isArray(volumes)) {
        volumes.forEach(v => {
          const pkjId = v.pekerjaan_id || v.id;
          const qty = parseFloat(v.quantity || v.volume || v.qty) || 0;
          if (pkjId) {
            state.volumeMap.set(pkjId, qty);
          }
        });
      }

      return state.volumeMap;
    } catch (error) {
      console.error('Failed to load volumes:', error);
      return state.volumeMap;
    }
  }

  async function loadAssignments() {
    try {
      state.assignmentMap.clear();
      console.log('Loading assignments for pekerjaan...');

      // Load assignments for all pekerjaan
      const promises = state.flatPekerjaan
        .filter(node => node.type === 'pekerjaan')
        .map(async (node) => {
          try {
            const data = await apiCall(`/detail_project/api/project/${projectId}/pekerjaan/${node.id}/assignments/`);

            if (data.assignments && Array.isArray(data.assignments)) {
              console.log(`  Pekerjaan ${node.id} has ${data.assignments.length} assignments:`, data.assignments);
              data.assignments.forEach(a => {
                const tahapanId = a.tahapan_id;
                const proporsi = parseFloat(a.proporsi) || 0;

                // Map tahapanId to corresponding timeColumns
                state.timeColumns.forEach(col => {
                  if (col.tahapanId === tahapanId) {
                    // Use cellKey format: "pekerjaanId-colId"
                    const cellKey = `${node.id}-${col.id}`;
                    console.log(`    Mapped: ${cellKey} = ${proporsi}`);
                    state.assignmentMap.set(cellKey, proporsi);
                  }
                });
              });
            }
          } catch (error) {
            console.warn(`Failed to load assignments for pekerjaan ${node.id}:`, error);
          }
        });

      await Promise.all(promises);
      console.log(`Total assignments loaded: ${state.assignmentMap.size}`);
      console.log('Assignment map:', Array.from(state.assignmentMap.entries()));
      return state.assignmentMap;
    } catch (error) {
      console.error('Failed to load assignments:', error);
      return state.assignmentMap;
    }
  }

  // =========================================================================
  // TIME COLUMNS GENERATION
  // =========================================================================

  /**
   * Generate time columns from loaded tahapan data
   *
   * Maps database tahapan to grid time columns based on current time scale mode.
   *
   * FILTERING LOGIC:
   * - daily/weekly/monthly: Shows ONLY auto-generated tahapan with matching generation_mode
   * - custom: Shows ALL tahapan (both auto-generated and manually created)
   *
   * CRITICAL: Each column MUST have tahapanId for save functionality to work!
   * Without tahapanId, assignments cannot be linked to database tahapan.
   */
  function generateTimeColumns() {
    state.timeColumns = [];

    // Check current time scale mode
    const timeScale = state.timeScale || 'custom';
    console.log(`Generating time columns for mode: ${timeScale}`);
    console.log(`  Available tahapan in database: ${state.tahapanList.length}`);

    // ALL modes now pull from database tahapan (loaded in state.tahapanList)
    // Backend has already created the appropriate tahapan for each mode
    // We just map tahapan to time columns with proper tahapanId

    state.tahapanList.forEach((tahap, index) => {
      // For daily/weekly/monthly modes, only include tahapan with matching generation_mode
      // For custom mode, include all tahapan
      let shouldInclude = false;

      if (timeScale === 'custom') {
        // Custom mode: include all tahapan
        shouldInclude = true;
      } else {
        // Daily/weekly/monthly: only include AUTO-GENERATED tahapan with matching generation_mode
        // This filters out old custom tahapan when in auto-generated modes
        shouldInclude = (
          tahap.is_auto_generated === true &&
          tahap.generation_mode === timeScale
        );
      }

      if (shouldInclude) {
        const startDate = tahap.tanggal_mulai ? new Date(tahap.tanggal_mulai) : null;
        const endDate = tahap.tanggal_selesai ? new Date(tahap.tanggal_selesai) : null;
        let label = tahap.nama || `Tahap ${index + 1}`;
        let rangeLabel = '';
        let tooltip = label;
        let weekNumber = null;


        if (
          tahap.is_auto_generated === true &&
          tahap.generation_mode === 'weekly' &&
          startDate &&
          endDate
        ) {
          const baseIndex = Number.isInteger(tahap.urutan) ? tahap.urutan : state.timeColumns.length;
          weekNumber = baseIndex + 1;
          const shortStart = formatDayMonth(startDate);
          const shortEnd = formatDayMonth(endDate);
          label = `Week ${weekNumber}`;
          rangeLabel = `( ${shortStart} - ${shortEnd} )`;

          const longStart = startDate.toLocaleDateString('id-ID', {
            weekday: 'long',
            day: '2-digit',
            month: 'long',
            year: 'numeric'
          });
          const longEnd = endDate.toLocaleDateString('id-ID', {
            weekday: 'long',
            day: '2-digit',
            month: 'long',
            year: 'numeric'
          });
          tooltip = `Week ${weekNumber}: ${longStart} - ${longEnd}`;
        }

        const column = {
          id: `tahap-${tahap.tahapan_id}`,
          tahapanId: tahap.tahapan_id,  // Γ£à CRITICAL: Link to database tahapan!
          label,
          rangeLabel,
          tooltip,
          type: tahap.generation_mode || 'custom',
          isAutoGenerated: tahap.is_auto_generated || false,
          generationMode: tahap.generation_mode || 'custom',
          index: state.timeColumns.length,
          weekNumber,
          startDate: startDate,
          endDate: endDate,
          urutan: tahap.urutan || index
        };

        state.timeColumns.push(column);
      }
    });

    // FALLBACK: If no columns generated, show all tahapan
    // This can happen if user is in daily/weekly/monthly mode but hasn't generated tahapan yet
    if (state.timeColumns.length === 0 && state.tahapanList.length > 0) {
      console.warn(`  [fallback] No auto-generated tahapan found for mode "${timeScale}".`);
      console.warn(`  Showing all ${state.tahapanList.length} tahapan as fallback.`);
      console.warn(`  [tip] Use the ${timeScale} mode switcher to regenerate auto tahapan before editing.`);

      state.tahapanList.forEach((tahap, index) => {
        const startDate = tahap.tanggal_mulai ? new Date(tahap.tanggal_mulai) : null;
        const endDate = tahap.tanggal_selesai ? new Date(tahap.tanggal_selesai) : null;
        let label = tahap.nama || `Tahap ${index + 1}`;
        let rangeLabel = '';
        let tooltip = label;
        let weekNumber = null;

        if (
          tahap.is_auto_generated === true &&
          tahap.generation_mode === 'weekly' &&
          startDate &&
          endDate
        ) {
          const baseIndex = Number.isInteger(tahap.urutan) ? tahap.urutan : index;
          weekNumber = baseIndex + 1;
          const shortStart = formatDayMonth(startDate);
          const shortEnd = formatDayMonth(endDate);
          label = `Week ${weekNumber}`;
          rangeLabel = `( ${shortStart} - ${shortEnd} )`;

          const longStart = startDate.toLocaleDateString('id-ID', {
            weekday: 'long',
            day: '2-digit',
            month: 'long',
            year: 'numeric'
          });
          const longEnd = endDate.toLocaleDateString('id-ID', {
            weekday: 'long',
            day: '2-digit',
            month: 'long',
            year: 'numeric'
          });
          tooltip = `Week ${weekNumber}: ${longStart} - ${longEnd}`;
        }

        const column = {
          id: `tahap-${tahap.tahapan_id}`,
          tahapanId: tahap.tahapan_id,
          label,
          rangeLabel,
          tooltip,
          type: tahap.generation_mode || 'custom',
          isAutoGenerated: tahap.is_auto_generated || false,
          generationMode: tahap.generation_mode || 'custom',
          index: index,
          weekNumber,
          startDate: startDate,
          endDate: endDate,
          urutan: tahap.urutan || index
        };

        state.timeColumns.push(column);
      });
    }

    console.log(`Generated ${state.timeColumns.length} time columns with tahapanId`);

    // Debug: Show breakdown by generation_mode
    const modeBreakdown = {};
    state.timeColumns.forEach(col => {
      const mode = col.generationMode || 'unknown';
      modeBreakdown[mode] = (modeBreakdown[mode] || 0) + 1;
    });
    console.log(`  Breakdown:`, modeBreakdown);
  }

  function generateDailyColumns() {
    const { start, end } = getProjectTimeline();
    console.log(`  Daily mode: ${formatDate(start, 'iso')} to ${formatDate(end, 'iso')}`);

    let currentDate = new Date(start);
    let dayNum = 1;

    while (currentDate <= end) {
      const column = {
        id: `day-${dayNum}`,
        tahapanId: null, // Will be mapped to actual tahapan
        label: `Day ${dayNum}`,
        sublabel: formatDate(currentDate, 'short'),
        type: 'daily',
        index: dayNum - 1,
        startDate: new Date(currentDate),
        endDate: new Date(currentDate),
        dateKey: formatDate(currentDate, 'iso')
      };

      state.timeColumns.push(column);
      currentDate = addDays(currentDate, 1);
      dayNum++;
    }
  }

  function generateWeeklyColumns() {
    const { start, end } = getProjectTimeline();
    const weekEndDay = state.weekEndDay || 0; // 0 = Sunday (default)

    console.log(`  Weekly mode: ${formatDate(start, 'iso')} to ${formatDate(end, 'iso')}`);

    let currentStart = new Date(start);
    let weekNum = 1;

    while (currentStart <= end) {
      // Find end of week (next occurrence of weekEndDay)
      let currentEnd = new Date(currentStart);
      const daysUntilWeekEnd = (weekEndDay - currentStart.getDay() + 7) % 7;

      if (daysUntilWeekEnd === 0 && currentStart.getDay() === weekEndDay) {
        // Already on week end day - this is a 1-day week
        currentEnd = new Date(currentStart);
      } else {
        currentEnd = addDays(currentStart, daysUntilWeekEnd);
      }

      // Don't exceed project end
      if (currentEnd > end) {
        currentEnd = new Date(end);
      }

      const startDay = currentStart.getDate().toString().padStart(2, '0');
      const endDay = currentEnd.getDate().toString().padStart(2, '0');
      const startMonthNum = (currentStart.getMonth() + 1).toString().padStart(2, '0');
      const endMonthNum = (currentEnd.getMonth() + 1).toString().padStart(2, '0');

      const rangeLabel = `( ${startDay}/${startMonthNum} - ${endDay}/${endMonthNum} )`;
      const longRange = `${startDay}/${startMonthNum}/${currentStart.getFullYear()} - ${endDay}/${endMonthNum}/${currentEnd.getFullYear()}`;
      const label = `Week ${weekNum}`;

      const column = {
        id: `week-${weekNum}`,
        tahapanId: null,
        label: label,
        rangeLabel,
        tooltip: `Week ${weekNum}: ${longRange}`, // full date range for hover
        type: 'weekly',
        index: weekNum - 1,
        startDate: new Date(currentStart),
        endDate: new Date(currentEnd),
        weekNumber: weekNum
      };

      state.timeColumns.push(column);

      // Move to day after week end
      currentStart = addDays(currentEnd, 1);
      weekNum++;

      // Safety check
      if (weekNum > 100) break; // Prevent infinite loop
    }
  }

  function generateMonthlyColumns() {
    const { start, end } = getProjectTimeline();
    console.log(`  Monthly mode: ${formatDate(start, 'iso')} to ${formatDate(end, 'iso')}`);

    let currentDate = new Date(start);
    let monthNum = 1;

    while (currentDate <= end) {
      // Start of month (or project start if mid-month)
      const monthStart = new Date(currentDate);

      // End of month
      const monthEnd = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);

      // Don't exceed project end
      const actualEnd = monthEnd > end ? new Date(end) : monthEnd;

      const monthName = currentDate.toLocaleString('id-ID', { month: 'long' });
      const year = currentDate.getFullYear();

      const column = {
        id: `month-${monthNum}`,
        tahapanId: null,
        label: `${monthName} ${year}`,
        type: 'monthly',
        index: monthNum - 1,
        startDate: new Date(monthStart),
        endDate: new Date(actualEnd),
        monthNumber: monthNum
      };

      state.timeColumns.push(column);

      // Move to first day of next month
      currentDate = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1);
      monthNum++;

      // Safety check
      if (monthNum > 24) break; // Max 2 years
    }
  }

  function generateCustomColumns() {
    // Generate from user-defined tahapan
    console.log(`  Custom mode: Generating from ${state.tahapanList.length} tahapan`);

    state.tahapanList.forEach((tahap, index) => {
      const column = {
        id: `tahap-${tahap.tahapan_id}`,
        tahapanId: tahap.tahapan_id,  // Γ£à Link to tahapan
        label: tahap.nama || `Tahap ${index + 1}`,
        type: 'custom',
        isAutoGenerated: tahap.is_auto_generated || false,
        generationMode: tahap.generation_mode || 'custom',
        index: index,
        startDate: tahap.tanggal_mulai ? new Date(tahap.tanggal_mulai) : null,
        endDate: tahap.tanggal_selesai ? new Date(tahap.tanggal_selesai) : null,
        urutan: tahap.urutan || index
      };

      console.log(`  Column ${index}: ${column.id} (tahapanId=${column.tahapanId}, label="${column.label}")`);
      state.timeColumns.push(column);
    });
  }

  function generateWeeklyColumns() {
    // Generate 52 weeks starting from project start date or current date
    const startDate = getProjectStartDate();
    const weeksToGenerate = 52; // 1 year

    for (let i = 0; i < weeksToGenerate; i++) {
      const weekStart = new Date(startDate);
      weekStart.setDate(weekStart.getDate() + (i * 7));

      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekEnd.getDate() + 6);

      // Format: "W1 (01-07 Jan)"
      const weekNum = i + 1;
      const startDay = weekStart.getDate().toString().padStart(2, '0');
      const endDay = weekEnd.getDate().toString().padStart(2, '0');
      const startMonth = weekStart.toLocaleString('id-ID', { month: 'short' });
      const endMonth = weekEnd.toLocaleString('id-ID', { month: 'short' });

      let label;
      if (startMonth === endMonth) {
        label = `W${weekNum} (${startDay}-${endDay} ${startMonth})`;
      } else {
        label = `W${weekNum} (${startDay} ${startMonth}-${endDay} ${endMonth})`;
      }

      state.timeColumns.push({
        id: `week-${weekNum}`,
        label: label,
        type: 'week',
        index: i,
        startDate: new Date(weekStart),
        endDate: new Date(weekEnd)
      });
    }
  }

  function getProjectStartDate() {
    // Try to get from first tahapan
    if (state.tahapanList.length > 0 && state.tahapanList[0].tanggal_mulai) {
      return new Date(state.tahapanList[0].tanggal_mulai);
    }

    // Default to start of current year
    const now = new Date();
    return new Date(now.getFullYear(), 0, 1); // Jan 1st
  }

  function generateDailyColumns() {
    // TODO: Implement daily view
    generateWeeklyColumns(); // Fallback for now
  }

  function generateMonthlyColumns() {
    const startDate = getProjectStartDate();
    const monthsToGenerate = 12; // 1 year

    for (let i = 0; i < monthsToGenerate; i++) {
      const monthStart = new Date(startDate.getFullYear(), startDate.getMonth() + i, 1);
      const monthEnd = new Date(startDate.getFullYear(), startDate.getMonth() + i + 1, 0);

      const monthName = monthStart.toLocaleString('id-ID', { month: 'long' });
      const year = monthStart.getFullYear();

      state.timeColumns.push({
        id: `month-${i}`,
        label: `${monthName} ${year}`,
        type: 'month',
        index: i,
        startDate: new Date(monthStart),
        endDate: new Date(monthEnd)
      });
    }
  }

  function generateCustomColumns() {
    // TODO: Implement custom date range
    generateWeeklyColumns(); // Fallback for now
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

  /**
   * Calculate total progress for a pekerjaan
   * @param {string} pekerjaanId - Pekerjaan ID
   * @param {Object} pendingChanges - Optional pending changes not yet saved
   * @returns {number} Total progress percentage
   */
  function calculateTotalProgress(pekerjaanId, pendingChanges = {}) {
    let total = 0;

    // Add all saved values
    state.assignmentMap.forEach((value, key) => {
      if (key.startsWith(`${pekerjaanId}-`)) {
        total += parseFloat(value) || 0;
      }
    });

    // Add pending modified values (replace saved values)
    state.modifiedCells.forEach((value, key) => {
      if (key.startsWith(`${pekerjaanId}-`)) {
        // Subtract old value if exists
        const savedValue = state.assignmentMap.get(key);
        if (savedValue) {
          total -= parseFloat(savedValue) || 0;
        }
        // Add new value
        total += parseFloat(value) || 0;
      }
    });

    // Add additional pending changes
    Object.entries(pendingChanges).forEach(([tahapanId, value]) => {
      const key = `${pekerjaanId}-tahap-${tahapanId}`;
      // If not already counted in modifiedCells
      if (!state.modifiedCells.has(key)) {
        const savedValue = state.assignmentMap.get(key);
        if (savedValue) {
          total -= parseFloat(savedValue) || 0;
        }
        total += parseFloat(value) || 0;
      }
    });

    return Math.round(total * 100) / 100; // Round to 2 decimals
  }

  /**
   * Validate and apply visual feedback for progress totals
   * @param {Map} changesByPekerjaan - Map of pekerjaan changes
   * @returns {Object} Validation result {isValid, errors}
   */
  function validateProgressTotals(changesByPekerjaan) {
    const errors = [];
    const warnings = [];

    changesByPekerjaan.forEach((assignments, pekerjaanId) => {
      const total = calculateTotalProgress(pekerjaanId, assignments);

      if (total > 100) {
        errors.push({
          pekerjaanId,
          total,
          message: `Pekerjaan ${pekerjaanId}: Total ${total.toFixed(2)}% melebihi 100%`
        });
      } else if (total < 100 && total > 0) {
        warnings.push({
          pekerjaanId,
          total,
          message: `Pekerjaan ${pekerjaanId}: Total ${total.toFixed(2)}% kurang dari 100%`
        });
      }
    });

    return {
      isValid: errors.length === 0,
      errors,
      warnings
    };
  }

  /**
   * Update visual feedback (border colors) for pekerjaan rows
   * @param {string} pekerjaanId - Pekerjaan ID
   * @param {number} total - Total progress percentage
   */
  function updateProgressVisualFeedback(pekerjaanId, total) {
    const leftRow = document.querySelector(`#left-tbody tr[data-node-id="${pekerjaanId}"]`);
    const rightRow = document.querySelector(`#right-tbody tr[data-node-id="${pekerjaanId}"]`);

    if (!leftRow || !rightRow) return;

    // Remove all status classes
    leftRow.classList.remove('progress-over-100', 'progress-under-100', 'progress-complete-100');
    rightRow.classList.remove('progress-over-100', 'progress-under-100', 'progress-complete-100');

    // Apply appropriate class
    if (total > 100) {
      leftRow.classList.add('progress-over-100');
      rightRow.classList.add('progress-over-100');
    } else if (total < 100 && total > 0) {
      leftRow.classList.add('progress-under-100');
      rightRow.classList.add('progress-under-100');
    } else if (total === 100) {
      leftRow.classList.add('progress-complete-100');
      rightRow.classList.add('progress-complete-100');
    }
  }

  async function saveAllChanges() {
    console.log('Save All clicked. Modified cells:', state.modifiedCells.size);
    console.log('Modified cells map:', Array.from(state.modifiedCells.entries()));

    if (state.modifiedCells.size === 0) {
      showToast('No changes to save', 'warning');
      return;
    }

    try {
      // Step 1: Group changes by pekerjaan
      showLoading('Preparing changes...', `Processing ${state.modifiedCells.size} modified cell(s)`);
      const changesByPekerjaan = new Map();

      state.modifiedCells.forEach((value, key) => {
        // Parse cellKey: format is "pekerjaanId-colId" where colId may contain dashes (e.g., "322-tahap-841")
        // Split only on FIRST dash to separate pekerjaanId from colId
        const firstDashIndex = key.indexOf('-');
        if (firstDashIndex === -1) {
          console.warn(`Invalid cellKey format: ${key}`);
          return;
        }

        const pekerjaanId = key.substring(0, firstDashIndex);
        const colId = key.substring(firstDashIndex + 1);

        if (!changesByPekerjaan.has(pekerjaanId)) {
          changesByPekerjaan.set(pekerjaanId, {});
        }

        // Find tahapan ID from column
        const column = state.timeColumns.find(c => c.id === colId);
        if (column && column.tahapanId) {
          changesByPekerjaan.get(pekerjaanId)[column.tahapanId] = value;
        } else {
          console.warn(`Column not found for colId: ${colId}, or missing tahapanId`);
        }
      });

      console.log('Changes grouped by pekerjaan:', Array.from(changesByPekerjaan.entries()));

      // Step 2: Validate total progress Γëñ 100%
      showLoading('Validating...', 'Checking progress totals');
      const validation = validateProgressTotals(changesByPekerjaan);

      // Update visual feedback for all affected pekerjaan
      changesByPekerjaan.forEach((assignments, pekerjaanId) => {
        const total = calculateTotalProgress(pekerjaanId, assignments);
        updateProgressVisualFeedback(pekerjaanId, total);
      });

      // Show warnings (don't block save)
      if (validation.warnings.length > 0) {
        console.warn('Progress warnings:', validation.warnings);
        // Show toast but don't block
        showToast(
          `ΓÜá∩╕Å ${validation.warnings.length} pekerjaan memiliki progress < 100%`,
          'warning'
        );
      }

      // Block save if errors
      if (!validation.isValid) {
        showLoading(false);
        const errorMessages = validation.errors.map(e => e.message).join('\n');
        showToast(
          `Γ¥î Tidak bisa menyimpan!\n\n${errorMessages}\n\nTotal progress tidak boleh melebihi 100%`,
          'danger'
        );
        console.error('Validation errors:', validation.errors);
        return; // Don't save
      }

      // Step 3: Save each pekerjaan with progress updates
      const totalPekerjaan = changesByPekerjaan.size;
      let successCount = 0;

      for (const [pekerjaanId, assignments] of changesByPekerjaan.entries()) {
        showLoading(
          `Saving changes...`,
          `Pekerjaan ${successCount + 1} of ${totalPekerjaan}`
        );
        console.log(`Saving pekerjaan ${pekerjaanId}:`, assignments);
        await savePekerjaanAssignments(pekerjaanId, assignments);
        successCount++;
      }

      console.log(`Successfully saved ${successCount} pekerjaan assignments`);

      // Step 3: Update UI
      showLoading('Updating UI...', 'Applying saved changes to grid');

      // SUCCESS: Move modified values to assignmentMap
      state.modifiedCells.forEach((value, key) => {
        state.assignmentMap.set(key, value);

        // Update cell data-saved-value attribute
        // Parse cellKey: format is "pekerjaanId-colId" where colId may contain dashes
        const firstDashIndex = key.indexOf('-');
        if (firstDashIndex === -1) return;

        const pekerjaanId = key.substring(0, firstDashIndex);
        const colId = key.substring(firstDashIndex + 1);

        const cell = document.querySelector(
          `.time-cell[data-node-id="${pekerjaanId}"][data-col-id="${colId}"]`
        );
        if (cell) {
          cell.dataset.savedValue = value;

          // Update classes: remove modified, add saved if value > 0
          cell.classList.remove('modified');
          if (value > 0) {
            cell.classList.add('saved');
          } else {
            cell.classList.remove('saved');
          }
        }
      });

      // Clear modified cells after successful save
      state.modifiedCells.clear();

      showToast(`All changes saved successfully (${successCount} pekerjaan)`, 'success');
      updateStatusBar();

    } catch (error) {
      console.error('Save failed:', error);
      showToast('Failed to save: ' + error.message, 'danger');
    } finally {
      showLoading(false);
    }
  }

  async function savePekerjaanAssignments(pekerjaanId, assignments) {
    // IMPORTANT: Save to CANONICAL STORAGE (weekly) for lossless data preservation!
    // Strategy:
    // 1. Convert tahapan assignments to weekly format (different logic for each mode)
    // 2. Save to PekerjaanProgressWeekly (canonical)
    // 3. Backend will automatically sync to PekerjaanTahapan (view layer)

    const weeklyAssignments = [];
    const projectStart = getProjectStartDate();

    console.log(`  Converting ${state.timeScale} mode assignments to weekly canonical format...`);

    if (state.timeScale === 'weekly') {
      // WEEKLY MODE: Direct 1:1 mapping
      for (const [tahapanId, proporsi] of Object.entries(assignments)) {
        if (parseFloat(proporsi) < 0) continue;  // Allow 0 to clear assignments

        const tahapan = state.tahapanList.find(t => t.tahapan_id == tahapanId);
        if (!tahapan || !tahapan.tanggal_mulai) {
          console.warn(`Tahapan ${tahapanId} not found, skipping`);
          continue;
        }

        const column = state.timeColumns.find(col => col.tahapanId == tahapan.tahapan_id);
        let weekNumber = column?.weekNumber;

        if (!weekNumber && typeof column?.urutan === 'number') {
          weekNumber = column.urutan + 1;
        }

        if (!weekNumber && typeof tahapan.urutan === 'number') {
          weekNumber = tahapan.urutan + 1;
        }

        if (!weekNumber) {
          const tahapStart = new Date(tahapan.tanggal_mulai);
          weekNumber = getWeekNumberForDate(tahapStart, projectStart);
        }

        console.log(`  - Week ${weekNumber}: ${proporsi}%`);

        weeklyAssignments.push({
          pekerjaan_id: parseInt(pekerjaanId),
          week_number: weekNumber,
          proportion: parseFloat(proporsi),
          notes: `Saved from ${state.timeScale} mode`
        });
      }

    } else if (state.timeScale === 'daily') {
      // DAILY MODE: Aggregate days into weeks
      console.log(`  Aggregating ${Object.keys(assignments).length} daily values into weeks...`);

      // Group daily assignments by week
      const weeklyProportions = new Map();

      for (const [tahapanId, proporsi] of Object.entries(assignments)) {
        if (parseFloat(proporsi) < 0) continue;  // Allow 0 to clear assignments

        const tahapan = state.tahapanList.find(t => t.tahapan_id == tahapanId);
        if (!tahapan || !tahapan.tanggal_mulai) continue;

        // Calculate which week this day belongs to
        const dayDate = new Date(tahapan.tanggal_mulai);
        const weekNumber = getWeekNumberForDate(dayDate, projectStart);

        // Accumulate proportions for this week
        const current = weeklyProportions.get(weekNumber) || 0;
        weeklyProportions.set(weekNumber, current + parseFloat(proporsi));

        console.log(`  - Day ${tahapan.nama} ΓåÆ Week ${weekNumber}: +${proporsi}%`);
      }

      // Convert accumulated weekly proportions to assignments
      weeklyProportions.forEach((proportion, weekNumber) => {
        console.log(`  ΓåÆ Week ${weekNumber}: ${proportion.toFixed(2)}% (aggregated from daily)`);
        weeklyAssignments.push({
          pekerjaan_id: parseInt(pekerjaanId),
          week_number: weekNumber,
          proportion: Math.round(proportion * 100) / 100, // Round to 2 decimals
          notes: `Saved from ${state.timeScale} mode (aggregated from daily)`
        });
      });

    } else if (state.timeScale === 'monthly') {
      // MONTHLY MODE: Split monthly to daily, then aggregate to weekly
      console.log(`  Splitting ${Object.keys(assignments).length} monthly values to daily, then aggregating to weekly...`);

      const weeklyProportions = new Map();

      for (const [tahapanId, proporsi] of Object.entries(assignments)) {
        if (parseFloat(proporsi) < 0) continue;  // Allow 0 to clear assignments

        const tahapan = state.tahapanList.find(t => t.tahapan_id == tahapanId);
        if (!tahapan || !tahapan.tanggal_mulai || !tahapan.tanggal_selesai) continue;

        const monthStart = new Date(tahapan.tanggal_mulai);
        const monthEnd = new Date(tahapan.tanggal_selesai);

        // Calculate days in this month
        const daysInMonth = Math.floor((monthEnd - monthStart) / (1000 * 60 * 60 * 24)) + 1;
        const dailyProportion = parseFloat(proporsi) / daysInMonth;

        console.log(`  - Month ${tahapan.nama}: ${proporsi}% / ${daysInMonth} days = ${dailyProportion.toFixed(4)}% per day`);

        // Distribute to each day, then aggregate to weeks
        let currentDate = new Date(monthStart);
        while (currentDate <= monthEnd) {
          const weekNumber = getWeekNumberForDate(currentDate, projectStart);

          const current = weeklyProportions.get(weekNumber) || 0;
          weeklyProportions.set(weekNumber, current + dailyProportion);

          currentDate.setDate(currentDate.getDate() + 1);
        }
      }

      // Convert accumulated weekly proportions to assignments
      weeklyProportions.forEach((proportion, weekNumber) => {
        console.log(`  ΓåÆ Week ${weekNumber}: ${proportion.toFixed(2)}% (aggregated from monthlyΓåÆdaily)`);
        weeklyAssignments.push({
          pekerjaan_id: parseInt(pekerjaanId),
          week_number: weekNumber,
          proportion: Math.round(proportion * 100) / 100, // Round to 2 decimals
          notes: `Saved from ${state.timeScale} mode (split from monthly)`
        });
      });

    } else {
      // CUSTOM MODE: Use week-based calculation as fallback
      console.warn('  Custom mode: Using week-based calculation');
      for (const [tahapanId, proporsi] of Object.entries(assignments)) {
        if (parseFloat(proporsi) < 0) continue;  // Allow 0 to clear assignments

        const tahapan = state.tahapanList.find(t => t.tahapan_id == tahapanId);
        if (!tahapan || !tahapan.tanggal_mulai) continue;

        const tahapStart = new Date(tahapan.tanggal_mulai);
        const weekNumber = getWeekNumberForDate(tahapStart, projectStart);

        weeklyAssignments.push({
          pekerjaan_id: parseInt(pekerjaanId),
          week_number: weekNumber,
          proportion: parseFloat(proporsi),
          notes: `Saved from ${state.timeScale} mode`
        });
      }
    }

    console.log(`  - Saving ${weeklyAssignments.length} weekly assignments to canonical storage`);

    if (weeklyAssignments.length === 0) {
      console.warn(`  - No assignments to save for pekerjaan ${pekerjaanId}`);
      return;
    }

    // Save to canonical storage (API V2)
    const url = `/detail_project/api/v2/project/${projectId}/assign-weekly/`;
    const payload = {
      assignments: weeklyAssignments,
      mode: state.timeScale,        // tell backend which grid view is active so it can sync PekerjaanTahapan
      week_end_day: state.weekEndDay
    };
    console.log(`  - POST ${url}`, payload);

    const response = await apiCall(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify(payload)
    });

    console.log(`  - Weekly canonical save response:`, response);

    if (!response.ok) {
      throw new Error(response.error || 'Failed to save to canonical storage');
    }

    console.log(`  Γ£ô Successfully saved to canonical storage: ${response.created_count} created, ${response.updated_count} updated`);

    // After saving to canonical, sync to view layer (PekerjaanTahapan)
    // This is done automatically by the backend when mode switching happens,
    // but we can trigger an explicit sync here if needed
    console.log(`  Γ£ô View layer will be synced on next mode operation`);
  }

  // =========================================================================
  // RESET PROGRESS FUNCTIONALITY
  // =========================================================================

  async function resetAllProgress() {
    // Confirm with user before resetting
    const confirmMessage = 'Apakah Anda yakin ingin mereset semua progress pekerjaan ke 0?\n\n' +
                          'Tindakan ini akan menghapus semua data progress yang telah disimpan.\n\n' +
                          'Data tidak dapat dikembalikan setelah direset!';

    if (!confirm(confirmMessage)) {
      return;
    }

    try {
      showLoading('Resetting all progress...', 'Please wait while we reset all pekerjaan progress');

      // Call API to reset progress
      const response = await apiCall(`/detail_project/api/v2/project/${projectId}/reset-progress/`, {
        method: 'POST',
        body: JSON.stringify({})
      });

      if (response.ok) {
        console.log('Progress reset successful:', response);

        // Clear all assignments and modified cells
        state.assignmentMap.clear();
        state.modifiedCells.clear();

        // Re-render grid to show empty progress
        renderGrid();

        showToast(
          `Progress reset berhasil! ${response.deleted_count || 0} record dihapus.`,
          'success'
        );
        updateStatusBar();
      } else {
        throw new Error(response.error || 'Failed to reset progress');
      }

    } catch (error) {
      console.error('Reset progress error:', error);
      showToast(`Error resetting progress: ${error.message}`, 'error');
    } finally {
      showLoading(false);
    }
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

  // Time scale toggle
  document.querySelectorAll('input[name="timeScale"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
      const newMode = e.target.value;

      // Check for unsaved changes
      const hasUnsavedChanges = state.modifiedCells.size > 0;

      let confirmMsg;
      if (hasUnsavedChanges) {
        // Show detailed warning about unsaved changes
        confirmMsg = `ΓÜá∩╕Å WARNING: You have ${state.modifiedCells.size} unsaved change(s).\n\n` +
                     `Switching to ${newMode} mode will:\n` +
                     `  ΓÇó Regenerate tahapan based on the new time scale\n` +
                     `  ΓÇó Convert existing assignments to the new mode\n` +
                     `  ΓÇó DISCARD all unsaved changes\n\n` +
                     `Do you want to continue?\n\n` +
                     `≡ƒÆí TIP: Click "Cancel", then "Save All Changes" to save your work first.`;
      } else {
        // Standard confirmation for mode switch
        confirmMsg = `Switch to ${newMode} mode?\n\n` +
                     `This will regenerate tahapan and convert existing assignments ` +
                     `to the new time scale.`;
      }

      if (confirm(confirmMsg)) {
        switchTimeScaleMode(newMode);
      } else {
        // Revert radio selection
        updateTimeScaleControls(state.timeScale);
      }
    });
  });

  // Display mode toggle
  document.querySelectorAll('input[name="displayMode"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
      state.displayMode = e.target.value;
      renderGrid();
    });
  });

  // Collapse/Expand all
  document.getElementById('btn-collapse-all')?.addEventListener('click', () => {
    state.expandedNodes.clear();
    renderGrid();
  });

  document.getElementById('btn-expand-all')?.addEventListener('click', () => {
    state.flatPekerjaan.forEach(node => {
      if (node.children && node.children.length > 0) {
        state.expandedNodes.add(node.id);
      }
    });
    renderGrid();
  });

  // Save button
  document.getElementById('btn-save-all')?.addEventListener('click', saveAllChanges);

  // Reset progress button
  document.getElementById('btn-reset-progress')?.addEventListener('click', resetAllProgress);

  // Tab switch events
  document.getElementById('gantt-tab')?.addEventListener('shown.bs.tab', () => {
    if (!state.ganttInstance) {
      initGanttChart();
    }
  });

  document.getElementById('scurve-tab')?.addEventListener('shown.bs.tab', () => {
    if (!state.scurveChart) {
      initScurveChart();
    } else {
      state.scurveChart.resize();
    }
  });

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
  // PANEL SCROLL SHADOW EFFECT
  // =========================================================================

  const $leftThead = document.getElementById('left-thead');
  const $rightThead = document.getElementById('right-thead');

  /**
   * Handle shadow effect when content scrolls under table headers
   * Headers are sticky to panel top (not viewport)
   * Toolbar sticky handled by dp-sticky-topbar class (pure CSS)
   */
  function handlePanelScrollShadow() {
    if ($leftPanelScroll && $leftThead) {
      const scrollTop = $leftPanelScroll.scrollTop;
      $leftThead.classList.toggle('scrolled', scrollTop > 0);
    }

    if ($rightPanelScroll && $rightThead) {
      const scrollTop = $rightPanelScroll.scrollTop;
      $rightThead.classList.toggle('scrolled', scrollTop > 0);
    }
  }

  // Attach panel scroll listeners for shadow effect
  if ($leftPanelScroll) {
    $leftPanelScroll.addEventListener('scroll', handlePanelScrollShadow, { passive: true });
  }
  if ($rightPanelScroll) {
    $rightPanelScroll.addEventListener('scroll', handlePanelScrollShadow, { passive: true });
  }

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
          helpers: Object.assign({ showToast, updateStatusBar }, context.helpers || {}),
        });
      },
      enterEditMode: (cell, initialValue = '', context = {}) => {
        if (!gridHelpers || typeof gridHelpers.enterEditMode !== 'function') return;
        return gridHelpers.enterEditMode(
          cell,
          {
            state,
            utils: Object.assign({ formatNumber, escapeHtml }, context.utils || {}),
            helpers: Object.assign({ showToast, updateStatusBar }, context.helpers || {}),
          },
          initialValue
        );
      },
      exitEditMode: (cell, input, context = {}) => {
        if (!gridHelpers || typeof gridHelpers.exitEditMode !== 'function') return;
        return gridHelpers.exitEditMode(cell, input, {
          state,
          utils: Object.assign({ formatNumber, escapeHtml }, context.utils || {}),
          helpers: Object.assign({ showToast, updateStatusBar }, context.helpers || {}),
        });
      },
      navigateCell: (direction, context = {}) => {
        if (!gridHelpers || typeof gridHelpers.navigateCell !== 'function') return;
        return gridHelpers.navigateCell({
          state,
          utils: Object.assign({ formatNumber, escapeHtml }, context.utils || {}),
          helpers: Object.assign({ showToast, updateStatusBar }, context.helpers || {}),
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
    }),
    kurvaS: Object.assign({}, (window.KelolaTahapanPage && window.KelolaTahapanPage.kurvaS) || {}, {
      init: (context = {}) => {
        if (!kurvaHelpers || typeof kurvaHelpers.init !== 'function') return null;
        return kurvaHelpers.init(Object.assign({ state }, context || {}));
      },
      resize: (context = {}) => {
        if (!kurvaHelpers || typeof kurvaHelpers.resize !== 'function') return null;
        return kurvaHelpers.resize(Object.assign({ state }, context || {}));
      },
      getChart: () => {
        if (!kurvaHelpers || typeof kurvaHelpers.getChart !== 'function') return state.scurveChart;
        return kurvaHelpers.getChart({ state });
      },
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



