/**
 * Data Loader Module (ES6 Modern Version)
 * Handles all data loading operations for Jadwal Kegiatan page
 *
 * Migrated from: jadwal_pekerjaan/kelola_tahapan/data_loader_module.js
 * Date: 2025-11-19
 * Phase 0.3: Integrated with StateManager
 */

import { StateManager } from './state-manager.js';

// =========================================================================
// UTILITY FUNCTIONS
// =========================================================================

/**
 * Get CSRF token from cookies
 * @returns {string|null} CSRF token
 */
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

/**
 * Make API call with automatic CSRF handling
 * @param {string} url - API endpoint
 * @param {Object} options - Fetch options
 * @returns {Promise<any>} JSON response
 */
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

/**
 * Derive time scale mode from tahapan list
 * @param {Array} tahapanList - List of tahapan
 * @param {string} fallbackMode - Default mode if can't detect
 * @returns {string} Detected mode (daily|weekly|monthly|custom)
 */
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

  // If auto-generated tahapan exist, use dominant mode
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

  // If only manual tahapan exist, it's custom mode
  if (manualCount > 0) {
    return 'custom';
  }

  return fallbackMode;
}

/**
 * Initialize expanded nodes set for tree
 * @param {Array} tree - Pekerjaan tree
 * @param {Object} state - Application state
 */
function initialiseExpandedNodes(tree, state) {
  if (!Array.isArray(tree) || tree.length === 0) {
    return;
  }

  if (!(state.expandedNodes instanceof Set)) {
    state.expandedNodes = new Set();
  }

  // If already initialized, skip
  if (state.expandedNodes.size > 0) {
    return;
  }

  // Expand all nodes by default
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
              level: 2,
              budgeted_cost: Number.parseFloat(pkj.budgeted_cost ?? pkj.total_cost ?? 0) || 0
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

// =========================================================================
// DATA LOADER CLASS
// =========================================================================

/**
 * DataLoader class - handles all data loading operations
 */
export class DataLoader {
  constructor(state, options = {}) {
    if (!state) {
      throw new Error('[DataLoader] State is required');
    }

    this.state = state;
    this.options = options;
    this.projectId = state.projectId;

    // Phase 0.3: Initialize StateManager
    this.stateManager = StateManager.getInstance();

    // Initialize state maps if not exist
    if (!this.state.volumeMap) {
      this.state.volumeMap = new Map();
    }
    // Phase 0.3: assignmentMap now managed by StateManager
    // Legacy code may still access via this.state.assignmentMap (delegation getter)
    if (!this.state.cache) {
      this.state.cache = {};
    }

    console.log('[DataLoader] Phase 0.3: Initialized with StateManager');
  }

  /**
   * Load all data required for the page
   * @param {Object} options - Load options
   * @returns {Promise<Object>} Load result with metadata
   */
  async loadAllData(options = {}) {
    // Prevent duplicate loading
    if (this.state.cache.initialLoadInProgress) {
      console.info('[DataLoader] loadAllData skipped (already in progress)');
      return null;
    }

    // Skip if already loaded
    if (!options.force && this.state.cache.initialLoadCompleted && options.skipIfLoaded) {
      console.info('[DataLoader] loadAllData skipped (already completed)');
      return this.state.cache.initialLoadResult || null;
    }

    this.state.cache.initialLoadInProgress = true;

    try {
      console.log('[DataLoader] Loading all data...');

      // Step 1: Load base data in parallel
      await Promise.all([
        this.loadTahapan(),
        this.loadPekerjaan(),
        this.loadVolumes()
      ]);

      // Step 2: Time columns will be generated by TimeColumnGenerator
      // (We don't call it here, will be handled by main app)

      // Step 3: Load assignments (depends on time columns being generated)
      await this.loadAssignments();

      this.state.cache.initialLoadCompleted = true;
      this.state.cache.initialLoadResult = {
        completedAt: Date.now(),
        tahapanCount: this.state.tahapanList?.length || 0,
        pekerjaanCount: this.state.flatPekerjaan?.filter(node => node.type === 'pekerjaan').length || 0,
      };

      console.log('[DataLoader] ✅ All data loaded successfully:', this.state.cache.initialLoadResult);
      return this.state.cache.initialLoadResult;

    } catch (error) {
      console.error('[DataLoader] ❌ Load data failed:', error);
      this.state.cache.initialLoadError = error;
      throw error;
    } finally {
      this.state.cache.initialLoadInProgress = false;
    }
  }

  /**
   * Load tahapan data from API
   * @returns {Promise<Array>} List of tahapan
   */
  async loadTahapan() {
    try {
      const url = this.state.apiBase || `/detail_project/api/project/${this.projectId}/tahapan/`;
      const data = await apiCall(url);

      this.state.tahapanList = (data.tahapan || data || []).sort((a, b) => a.urutan - b.urutan);

      // Auto-detect time scale mode from tahapan
      const detectedMode = deriveTimeScaleFromTahapan(
        this.state.tahapanList,
        this.state.timeScale || 'weekly'
      );
      this.state.timeScale = detectedMode;

      console.log(`[DataLoader] ✅ Loaded ${this.state.tahapanList.length} tahapan, mode: ${detectedMode}`);
      return this.state.tahapanList;
    } catch (error) {
      console.error('[DataLoader] ❌ Failed to load tahapan:', error);
      throw error;
    }
  }

  /**
   * Load pekerjaan tree data from API
   * @returns {Promise<Array>} Pekerjaan tree
   */
  async loadPekerjaan() {
    try {
      const url = `/detail_project/api/project/${this.projectId}/list-pekerjaan/tree/`;
      const response = await apiCall(url);

      // Build hierarchical tree
      const tree = buildPekerjaanTree(response);
      this.state.pekerjaanTree = tree;

      // Flatten for easy access
      this.state.flatPekerjaan = flattenTree(tree);

      // Initialize expanded nodes
      initialiseExpandedNodes(tree, this.state);

      console.log(`[DataLoader] ✅ Loaded ${this.state.flatPekerjaan.length} pekerjaan nodes`);
      return this.state.pekerjaanTree;
    } catch (error) {
      console.error('[DataLoader] ❌ Failed to load pekerjaan:', error);
      throw error;
    }
  }

  /**
   * Load volume data for all pekerjaan
   * @returns {Promise<Map>} Volume map
   */
  async loadVolumes() {
    try {
      const url = `/detail_project/api/project/${this.projectId}/volume-pekerjaan/list/`;
      const data = await apiCall(url);

      this.state.volumeMap.clear();

      const volumes = data.items || data.volumes || data.data || [];
      if (Array.isArray(volumes)) {
        volumes.forEach(v => {
          const pkjId = v.pekerjaan_id || v.id;
          const qty = parseFloat(v.quantity || v.volume || v.qty) || 0;
          if (pkjId) {
            this.state.volumeMap.set(pkjId, qty);
          }
        });
      }

      console.log(`[DataLoader] ✅ Loaded ${this.state.volumeMap.size} volume entries`);
      return this.state.volumeMap;
    } catch (error) {
      console.error('[DataLoader] ❌ Failed to load volumes:', error);
      // Don't throw, volumes are optional
      return this.state.volumeMap;
    }
  }

  /**
   * Load assignments (progress data) for all pekerjaan
   * @returns {Promise<Map>} Assignment map
   */
  async loadAssignments() {
    try {
      // Phase 0.3: Clear StateManager data (both modes)
      this.stateManager.states.planned.assignmentMap.clear();
      this.stateManager.states.actual.assignmentMap.clear();
      console.log('[DataLoader] Phase 0.3: Loading assignments (attempting API v2)...');

      const pekerjaanNodes = this.state.flatPekerjaan.filter(node => node.type === 'pekerjaan');
      const totalNodes = pekerjaanNodes.length;

      if (totalNodes === 0) {
        console.info('[DataLoader] No pekerjaan nodes found for assignments');
        return this.state.assignmentMap;
      }

      await this._loadAssignmentsViaV2();
      return this.state.assignmentMap;
    } catch (error) {
      console.error('[DataLoader] ❌ Failed to load assignments:', error);
      return this.state.assignmentMap;
    }
  }

  /**
   * Reload specific data type
   * @param {string} type - Data type (tahapan|pekerjaan|volumes|assignments)
   * @returns {Promise<any>} Loaded data
   */
  async reload(type) {
    const loaders = {
      tahapan: () => this.loadTahapan(),
      pekerjaan: () => this.loadPekerjaan(),
      volumes: () => this.loadVolumes(),
      assignments: () => this.loadAssignments()
    };

    const loader = loaders[type];
    if (!loader) {
      throw new Error(`[DataLoader] Unknown reload type: ${type}`);
    }

    console.log(`[DataLoader] Reloading ${type}...`);
    return loader();
  }

  _buildWeekColumnIndex() {
    const weekColumnIndex = {};
    if (Array.isArray(this.state.timeColumns)) {
      this.state.timeColumns.forEach((col) => {
        const weekNumber = Number(col.weekNumber || col.week_number || col.urutan);
        if (Number.isFinite(weekNumber) && weekNumber >= 1 && col.id) {
          weekColumnIndex[weekNumber] = col;
        }
      });
    }
    return weekColumnIndex;
  }

  async _loadAssignmentsViaV2() {
    const url = `/detail_project/api/v2/project/${this.projectId}/assignments/`;
    const data = await apiCall(url);

    if (!data || !Array.isArray(data.assignments)) {
      console.info('[DataLoader] API v2 returned no assignments array (treating as empty dataset)');
      return;
    }

    if (data.assignments.length === 0) {
      console.info('[DataLoader] API v2 assignments empty (no progress recorded yet)');
      return;
    }

    const weekColumnIndex = this._buildWeekColumnIndex();
    let mapped = 0;

    data.assignments.forEach((item) => {
      const pekerjaanId = Number(item.pekerjaan_id || item.pekerjaanId || item.id);
      const weekNumber = Number(item.week_number || item.weekNumber);

      // Phase 0.3: Read both planned and actual proportions
      const plannedProportion = parseFloat(item.planned_proportion) || 0;
      const actualProportion = parseFloat(item.actual_proportion) || 0;
      const rawCost = item.actual_cost ?? item.actualCost ?? null;
      const actualCost = rawCost === null || typeof rawCost === 'undefined'
        ? null
        : Number.parseFloat(rawCost);

      if (!pekerjaanId || !weekNumber) {
        return;
      }

      const column = weekColumnIndex[weekNumber];
      if (!column) {
        return;
      }

      const columnKey = column.fieldId || column.id;
      if (!columnKey) {
        return;
      }

      // Phase 0.3: Use StateManager.setInitialValue to set both planned and actual
      const options = {};
      if (actualCost !== null && !Number.isNaN(actualCost) && Number.isFinite(actualCost)) {
        options.actualCost = actualCost;
      }

      this.stateManager.setInitialValue(
        pekerjaanId,
        columnKey,
        plannedProportion,
        actualProportion,
        options
      );
      mapped += 1;
    });

    // Phase 0.3: Log loaded data statistics
    const stats = this.stateManager.getStats();
    console.log(`[DataLoader] Phase 0.3: Loaded ${mapped} assignments via API v2`);
    console.log(`[DataLoader] Planned: ${stats.planned.assignmentCount} assignments`);
    console.log(`[DataLoader] Actual: ${stats.actual.assignmentCount} assignments`);
  }
}

// Export utilities for external use
export {
  apiCall,
  getCookie,
  deriveTimeScaleFromTahapan,
  buildPekerjaanTree,
  flattenTree,
  initialiseExpandedNodes
};
