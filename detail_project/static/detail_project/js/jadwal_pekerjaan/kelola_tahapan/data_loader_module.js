// static/detail_project/js/jadwal_pekerjaan/kelola_tahapan/data_loader_module.js
// Data Loading Module for Kelola Tahapan Page

(function() {
  'use strict';

  const bootstrap = window.KelolaTahapanPageApp || window.JadwalPekerjaanApp;
  const manifest = window.KelolaTahapanModuleManifest;

  if (!bootstrap || !manifest) {
    console.error('[DataLoader] Bootstrap or manifest not found');
    return;
  }

  const meta = {
    id: 'kelolaTahapanDataLoader',
    namespace: 'kelola_tahapan.data_loader',
    label: 'Kelola Tahapan - Data Loader',
    description: 'Handles all data loading operations: tahapan, pekerjaan, volumes, assignments'
  };

  const noop = () => undefined;
  const hasModule = typeof bootstrap.hasModule === 'function'
    ? (id) => bootstrap.hasModule(id)
    : (id) => bootstrap.modules && bootstrap.modules.has
      ? bootstrap.modules.has(id)
      : false;

  if (hasModule(meta.id)) {
    return;
  }

  const globalModules = window.KelolaTahapanPageModules = window.KelolaTahapanPageModules || {};
  const moduleStore = globalModules.dataLoader = Object.assign({}, globalModules.dataLoader || {});

  // =========================================================================
  // UTILITY FUNCTIONS
  // =========================================================================

  function resolveState(stateOverride) {
    if (stateOverride) {
      return stateOverride;
    }
    if (window.kelolaTahapanPageState) {
      return window.kelolaTahapanPageState;
    }
    if (bootstrap && bootstrap.state) {
      return bootstrap.state;
    }
    return null;
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

  async function apiCall(url, options = {}) {
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

  function initialiseExpandedNodes(tree, state) {
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

  // =========================================================================
  // DATA LOADING FUNCTIONS
  // =========================================================================

  /**
   * Load all data for the page
   * @param {Object} context - Context object with state, options, helpers
   * @returns {Object} Load result with metadata
   */
  async function loadAllData(context = {}) {
    const state = resolveState(context.state);
    if (!state) {
      throw new Error('[DataLoader] State is required');
    }

    state.cache = state.cache || {};

    // Prevent duplicate loading
    if (state.cache.initialLoadInProgress) {
      bootstrap.log.info('DataLoader: loadAllData skipped (already in progress).');
      return null;
    }

    // Skip if already loaded and skipIfLoaded is true
    if (!context.options?.force && state.cache.initialLoadCompleted && context.options?.skipIfLoaded) {
      bootstrap.log.info('DataLoader: loadAllData skipped (already completed).');
      return state.cache.initialLoadResult || null;
    }

    state.cache.initialLoadInProgress = true;

    const showLoading = context.helpers?.showLoading || (() => {});
    const emitEvent = context.helpers?.emitEvent || (() => {});

    emitEvent('data-load:start', {
      projectId: state.projectId,
      timeScale: state.timeScale,
      displayMode: state.displayMode,
    });

    try {
      // Step 1: Load base data
      showLoading('Loading project data...', 'Fetching tahapan, pekerjaan, and volumes');
      await Promise.all([
        loadTahapan({ state, helpers: context.helpers }),
        loadPekerjaan({ state, helpers: context.helpers }),
        loadVolumes({ state, helpers: context.helpers })
      ]);

      // Step 2: Generate time columns (delegated to time_column_generator module)
      showLoading('Generating time columns...', 'Mapping tahapan to grid structure');
      const timeColumnGenerator = globalModules.timeColumnGenerator;
      if (timeColumnGenerator && typeof timeColumnGenerator.generateTimeColumns === 'function') {
        timeColumnGenerator.generateTimeColumns({ state });
      } else {
        bootstrap.log.warn('DataLoader: time_column_generator module not available');
      }

      // Step 3: Load assignments
      showLoading('Loading assignments...', 'Fetching progress data for all pekerjaan');
      await loadAssignments({ state, helpers: context.helpers });

      state.cache.initialLoadCompleted = true;
      state.cache.initialLoadResult = {
        completedAt: Date.now(),
        tahapanCount: state.tahapanList.length,
        pekerjaanCount: state.flatPekerjaan.filter(node => node.type === 'pekerjaan').length,
      };

      emitEvent('data-load:success', {
        projectId: state.projectId,
        result: state.cache.initialLoadResult,
        stateSnapshot: {
          timeScale: state.timeScale,
          displayMode: state.displayMode,
        },
      });

      return state.cache.initialLoadResult;

    } catch (error) {
      bootstrap.log.error('DataLoader: Load data failed', error);
      state.cache.initialLoadError = error;
      emitEvent('data-load:error', { projectId: state.projectId, error });
      throw error;
    } finally {
      state.cache.initialLoadInProgress = false;
      showLoading(false);
    }
  }

  /**
   * Load tahapan data from API
   * @param {Object} context - Context with state and helpers
   * @returns {Array} List of tahapan
   */
  async function loadTahapan(context = {}) {
    const state = resolveState(context.state);
    if (!state) {
      throw new Error('[DataLoader] State is required');
    }

    try {
      const data = await apiCall(state.apiBase);
      state.tahapanList = (data.tahapan || []).sort((a, b) => a.urutan - b.urutan);

      // Auto-detect time scale mode from tahapan
      const detectedMode = deriveTimeScaleFromTahapan(state.tahapanList, state.timeScale || 'weekly');
      state.timeScale = detectedMode;

      // Update UI controls if helper is available
      if (context.helpers && typeof context.helpers.updateTimeScaleControls === 'function') {
        context.helpers.updateTimeScaleControls(detectedMode);
      }

      bootstrap.log.info(`DataLoader: Loaded ${state.tahapanList.length} tahapan, mode: ${detectedMode}`);
      return state.tahapanList;
    } catch (error) {
      bootstrap.log.error('DataLoader: Failed to load tahapan', error);
      throw error;
    }
  }

  /**
   * Load pekerjaan tree data from API
   * @param {Object} context - Context with state and helpers
   * @returns {Array} Pekerjaan tree
   */
  async function loadPekerjaan(context = {}) {
    const state = resolveState(context.state);
    if (!state) {
      throw new Error('[DataLoader] State is required');
    }

    try {
      const response = await apiCall(`/detail_project/api/project/${state.projectId}/list-pekerjaan/tree/`);

      // Build hierarchical tree
      const tree = buildPekerjaanTree(response);
      state.pekerjaanTree = tree;

      // Flatten for easy access
      state.flatPekerjaan = flattenTree(tree);
      initialiseExpandedNodes(tree, state);

      bootstrap.log.info(`DataLoader: Loaded ${state.flatPekerjaan.length} pekerjaan nodes`);
      return state.pekerjaanTree;
    } catch (error) {
      bootstrap.log.error('DataLoader: Failed to load pekerjaan', error);
      throw error;
    }
  }

  /**
   * Build hierarchical pekerjaan tree from API response
   * @param {Object} response - API response
   * @returns {Array} Tree structure
   */
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

  /**
   * Flatten tree structure for easy access
   * @param {Array} tree - Hierarchical tree
   * @param {Array} result - Accumulator
   * @returns {Array} Flattened list
   */
  function flattenTree(tree, result = []) {
    tree.forEach(node => {
      result.push(node);
      if (node.children && node.children.length > 0) {
        flattenTree(node.children, result);
      }
    });
    return result;
  }

  /**
   * Load volume data for all pekerjaan
   * @param {Object} context - Context with state and helpers
   * @returns {Map} Volume map
   */
  async function loadVolumes(context = {}) {
    const state = resolveState(context.state);
    if (!state) {
      throw new Error('[DataLoader] State is required');
    }

    try {
      const data = await apiCall(`/detail_project/api/project/${state.projectId}/volume-pekerjaan/list/`);
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

      bootstrap.log.info(`DataLoader: Loaded ${state.volumeMap.size} volume entries`);
      return state.volumeMap;
    } catch (error) {
      bootstrap.log.error('DataLoader: Failed to load volumes', error);
      return state.volumeMap;
    }
  }

  /**
   * Load assignments (progress data) for all pekerjaan
   * @param {Object} context - Context with state and helpers
   * @returns {Map} Assignment map
   */
  async function loadAssignments(context = {}) {
    const state = resolveState(context.state);
    if (!state) {
      throw new Error('[DataLoader] State is required');
    }

    const helpers = context.helpers || {};
    const showLoading = typeof helpers.showLoading === 'function' ? helpers.showLoading : null;
    const options = context.options || {};

    try {
      state.assignmentMap.clear();
      bootstrap.log.info('DataLoader: Loading assignments for pekerjaan...');

      const pekerjaanNodes = state.flatPekerjaan.filter(node => node.type === 'pekerjaan');
      const totalNodes = pekerjaanNodes.length;
      if (totalNodes === 0) {
        bootstrap.log.info('DataLoader: No pekerjaan nodes found for assignments.');
        return state.assignmentMap;
      }

      const maxConcurrency = Math.min(
        Math.max(Number(options.assignmentConcurrency) || 6, 1),
        10
      );
      let completed = 0;
      let cursor = 0;
      const progressStep = Math.max(1, Math.floor(totalNodes / 10));

      const updateProgress = () => {
        if (!showLoading) return;
        showLoading('Loading assignments...', `Loaded ${completed} / ${totalNodes} pekerjaan`);
      };

      const worker = async () => {
        // eslint-disable-next-line no-constant-condition
        while (true) {
          const index = cursor;
          if (index >= totalNodes) {
            return;
          }
          cursor += 1;
          const node = pekerjaanNodes[index];
          try {
            const data = await apiCall(`/detail_project/api/project/${state.projectId}/pekerjaan/${node.id}/assignments/`);

            if (data.assignments && Array.isArray(data.assignments)) {
              data.assignments.forEach(a => {
                const tahapanId = a.tahapan_id;
                const proporsi = parseFloat(a.proporsi) || 0;

                state.timeColumns.forEach(col => {
                  if (col.tahapanId === tahapanId) {
                    const cellKey = `${node.id}-${col.id}`;
                    state.assignmentMap.set(cellKey, proporsi);
                  }
                });
              });
            }
          } catch (error) {
            bootstrap.log.warn(`DataLoader: Failed to load assignments for pekerjaan ${node.id}`, error);
          } finally {
            completed += 1;
            if (completed === totalNodes || (completed % progressStep === 0)) {
              updateProgress();
            }
          }
        }
      };

      const workerCount = Math.min(maxConcurrency, totalNodes) || 1;
      const workers = Array.from({ length: workerCount }, () => worker());
      await Promise.all(workers);

      bootstrap.log.info(`DataLoader: Total assignments loaded: ${state.assignmentMap.size}`);
      return state.assignmentMap;
    } catch (error) {
      bootstrap.log.error('DataLoader: Failed to load assignments', error);
      return state.assignmentMap;
    }
  }

  // =========================================================================
  // MODULE EXPORTS
  // =========================================================================

  Object.assign(moduleStore, {
    resolveState,
    loadAllData,
    loadTahapan,
    loadPekerjaan,
    loadVolumes,
    loadAssignments,
    buildPekerjaanTree,
    flattenTree,
    deriveTimeScaleFromTahapan,
    initialiseExpandedNodes,
    // Expose utilities
    apiCall,
    getCookie,
  });

  // Register module with bootstrap
  bootstrap.registerModule(meta.id, {
    namespace: meta.namespace,
    pageId: manifest.pageId,
    description: meta.description,
    onRegister(context) {
      bootstrap.log.info('DataLoader module registered successfully');
      if (context && context.emit) {
        context.emit('kelola_tahapan.data_loader:registered', { meta });
      }
    },
    // Public API
    loadAllData: (context) => moduleStore.loadAllData(context),
    loadTahapan: (context) => moduleStore.loadTahapan(context),
    loadPekerjaan: (context) => moduleStore.loadPekerjaan(context),
    loadVolumes: (context) => moduleStore.loadVolumes(context),
    loadAssignments: (context) => moduleStore.loadAssignments(context),
    apiCall: (url, options) => moduleStore.apiCall(url, options),
  });

  bootstrap.log.info('[DataLoader] Module initialized');
})();
