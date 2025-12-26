import { Toast } from '@modules/shared/ux-enhancements.js';

/**
 * ChartCoordinator - Handles chart initialization, updates, and lazy loading
 *
 * This class is responsible for:
 * - Lazy loading chart modules (Kurva-S, Gantt) when tabs are clicked
 * - Throttled chart updates to prevent performance issues
 * - Coordinating updates between multiple chart views
 * - Managing chart lifecycle (init, update, destroy)
 *
 * @class ChartCoordinator
 * @example
 * const coordinator = new ChartCoordinator(app);
 * coordinator.initializeCharts();
 * coordinator.updateChartsThrottled();
 */
export class ChartCoordinator {
  /**
   * Create a new ChartCoordinator instance
   * @param {Object} app - JadwalKegiatanApp instance
   */
  constructor(app) {
    this.app = app;
  }

  /**
   * Initialize charts and setup lazy loading
   *
   * Sets up event listeners for tab switches to lazy load chart modules.
   * Charts are not loaded until their respective tabs are clicked.
   *
   * @returns {void}
   */
  initializeCharts() {
    this._setupLazyChartLoading();
    this.app._bindUnifiedTabSync();
  }

  /**
   * Setup lazy loading for chart modules (private)
   *
   * NOTE: As of unified container refactor, lazy loading is now handled
   * directly in jadwal_kegiatan_app._bindUnifiedTabSync() to ensure
   * single source of truth for tab interactions.
   *
   * This function is kept for backwards compatibility but does nothing.
   *
   * @private
   * @returns {void}
   */
  _setupLazyChartLoading() {
    // NOOP - Lazy loading is now handled by _bindUnifiedTabSync()
    // See jadwal_kegiatan_app.js for the consolidated handler
  }

  /**
   * Update all charts with throttling (max 1 update per 200ms)
   *
   * Uses requestAnimationFrame + setTimeout to throttle chart updates.
   * Prevents multiple rapid updates when user edits cells quickly.
   *
   * @returns {void}
   *
   * @example
   * // Called on cell edit
   * coordinator.updateChartsThrottled();
   */
  updateChartsThrottled() {
    const app = this.app;
    if (app._chartUpdatePending) {
      return;
    }
    app._chartUpdatePending = true;
    requestAnimationFrame(() => {
      setTimeout(() => {
        this.updateCharts();
        app._chartUpdatePending = false;
      }, app._chartUpdateDelay);
    });
  }

  /**
   * Update all charts immediately (no throttling)
   *
   * Calls update() on all active chart instances:
   * - Kurva-S Chart (if initialized)
   * - Gantt V2 Chart (if initialized)
   *
   * @returns {void}
   *
   * @example
   * // Called on mode switch or data reload
   * coordinator.updateCharts();
   */
  updateCharts() {
    const app = this.app;
    console.log('[JadwalKegiatanApp] Updating charts...');

    // Update Kurva-S Chart
    if (app.kurvaSChart) {
      try {
        app.kurvaSChart.update();
        console.log('[JadwalKegiatanApp] ƒo. Kurva-S chart updated');
      } catch (error) {
        console.warn('[JadwalKegiatanApp] Failed to update Kurva-S chart:', error);
      }
    }

    // Update Gantt V2 with latest data
    if (app.ganttFrozenGrid && typeof app.ganttFrozenGrid.update === 'function') {
      try {
        app.ganttFrozenGrid.update();
        console.log('[JadwalKegiatanApp] ƒo. Gantt V2 chart updated');
      } catch (error) {
        console.warn('[JadwalKegiatanApp] Failed to update Gantt V2 chart:', error);
      }
    }
  }

  /**
   * Initialize charts after data is loaded (legacy method)
   *
   * Called after initial data load completes. Handles:
   * - Legacy Kurva-S chart initialization (if not using unified table)
   * - Cost view toggle setup
   * - Auto-activation of default cost view
   *
   * Note: New Redesigned Gantt Chart is initialized lazily on tab click.
   *
   * @returns {void}
   */
  initializeChartsAfterLoad() {
    const app = this.app;
    console.log('[JadwalKegiatanApp] Initializing charts after load...');

    // Skip legacy Kurva-S chart if using unified table overlay
    if (app.state.useUnifiedTable) {
      console.log('[JadwalKegiatanApp] Skipping legacy Kurva-S chart (using unified overlay)');
      return;
    }

    // Initialize Kurva-S Chart (LEGACY - only when NOT using unified table)
    if (app.state.domRefs?.scurveChart && app.KurvaSChartClass) {
      try {
        app.kurvaSChart = new app.KurvaSChartClass(app.state, {
          useIdealCurve: true,
          steepnessFactor: 0.8,
          smoothCurves: true,
          showArea: true,
          enableCostView: true,
        });
        const success = app.kurvaSChart.initialize(app.state.domRefs.scurveChart);
        if (success) {
          console.log('[JadwalKegiatanApp] Kurva-S chart initialized');
          app._setupCostViewToggle();
          const activatePromise = app._activateDefaultCostView();
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

    console.log('[JadwalKegiatanApp] ƒsÿ‹,? OLD Gantt Chart initialization SKIPPED (replaced by new design)');
    // NOTE: NEW Redesigned Gantt Chart will be initialized lazily when tab is clicked
  }

  async _initializeRedesignedGantt(retryCount = 0) {
    const app = this.app;
    const MAX_RETRIES = 3;
    const RETRY_DELAY = 200; // ms

    console.log('[JadwalKegiatanApp] Rendering Gantt via unified table overlay');

    // Wait a bit for DOM to be ready (Bootstrap tab transition)
    if (retryCount === 0) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    const ganttContainer = document.getElementById('gantt-redesign-container');

    if (!ganttContainer) {
      console.warn(`[JadwalKegiatanApp] Г?3 Gantt container not found (attempt ${retryCount + 1}/${MAX_RETRIES})`);

      // Retry if not max retries
      if (retryCount < MAX_RETRIES) {
        console.log(`[JadwalKegiatanApp] Retrying in ${RETRY_DELAY}ms...`);
        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
        return this._initializeRedesignedGantt(retryCount + 1);
      }

      console.error('[JadwalKegiatanApp] ❌ Gantt container not found after retries');
      console.error('[JadwalKegiatanApp] DOM state:', {
        unifiedView: document.getElementById('unified-view'),
        ganttTab: document.getElementById('gantt-tab')
      });
      Toast.error('Failed to find Gantt container');
      return;
    }

    try {
      await this._initializeUnifiedGanttOverlay(ganttContainer);
    } catch (error) {
      console.error('[JadwalKegiatanApp] Г?O Failed to initialize Gantt:', error);
      console.error('[JadwalKegiatanApp] Error stack:', error.stack);
      Toast.error('Failed to load Gantt Chart');
      throw error;
    }
  }

  async _initializeUnifiedGanttOverlay(ganttContainer) {
    const app = this.app;
    if (!app.unifiedManager) {
      app._initTanStackGridIfNeeded();
    }
    if (!app.unifiedManager) {
      console.warn('[JadwalKegiatanApp] Unified manager not available for Gantt overlay');
      return;
    }

    const host = this._ensureGanttHost(ganttContainer);
    if (!host) {
      console.warn('[JadwalKegiatanApp] Unable to prepare Gantt host for unified overlay');
      return;
    }

    const gridPayload = {
      tree: app.state.pekerjaanTree || [],
      timeColumns: app._getDisplayTimeColumns(),
      inputMode: app.state.inputMode || 'percentage',
      timeScale: app.state.displayScale || app.state.timeScale || 'weekly',
      dependencies: app.state.dependencies || [],
    };
    if (app.state.debugUnifiedTable) {
      console.log('[UnifiedGanttOverlay] Apply payload', {
        rows: gridPayload.tree.length,
        columns: gridPayload.timeColumns.length,
        deps: gridPayload.dependencies.length,
      });
    }
    app.unifiedManager.updateData(gridPayload);
    // NOTE: switchMode('gantt') removed - now handled centrally by _bindUnifiedTabSync
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
    const app = this.app;
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
    const app = this.app;
    const container = app.state?.domRefs?.tanstackGridContainer;
    if (!container || !target || container.parentNode === target) {
      return;
    }
    target.appendChild(container);
  }

  _restoreGridContainerPosition() {
    const app = this.app;
    const container = app.state?.domRefs?.tanstackGridContainer;
    const parent = app._gridContainerParent;
    if (!container || !parent) {
      return;
    }
    if (container.parentNode === parent) {
      return;
    }
    if (app._gridContainerNextSibling && app._gridContainerNextSibling.parentNode === parent) {
      parent.insertBefore(container, app._gridContainerNextSibling);
    } else {
      parent.appendChild(container);
    }
  }

  _prepareGanttData() {
    const app = this.app;
    const data = [];

    if (app.state?.flatPekerjaan && Array.isArray(app.state.flatPekerjaan)) {
      const pekerjaanNodes = app.state.flatPekerjaan.filter(n => n.type === 'pekerjaan');

      console.log(`[JadwalKegiatanApp] Transforming ${pekerjaanNodes.length} pekerjaan nodes for Gantt (filtered from ${app.state.flatPekerjaan.length} total nodes)`);

      if (pekerjaanNodes.length > 0) {
        console.log('[JadwalKegiatanApp] Sample pekerjaan node:', pekerjaanNodes[0]);
      }

      pekerjaanNodes.forEach(node => {
        data.push({
          id: node.id,
          name: node.nama || node.name || 'Pekerjaan',
          start: node.tanggal_mulai || node.start_date || this._fallbackDate(node),
          end: node.tanggal_selesai || node.end_date || this._fallbackDate(node, 7),
          progress_rencana: node.progress_plan || 0,
          progress_realisasi: node.progress_actual || 0,
          volume: node.volume || 0,
          satuan: node.satuan || ''
        });
      });
    } else {
      console.warn('[JadwalKegiatanApp] No flatPekerjaan data available for Gantt');
    }

    const projectMeta = {
      project_id: app.state.projectId,
      project_name: app.state.projectName || 'Project',
      start_date: app.state.projectStart,
      end_date: app.state.projectEnd
    };

    console.log(`[JadwalKegiatanApp] Prepared ${data.length} nodes for Gantt Chart`);

    return {
      data,
      project: projectMeta,
      milestones: []
    };
  }

  _fallbackDate(node, offset = 0) {
    const today = new Date();
    if (!node?.created_at) {
      const d = new Date(today);
      d.setDate(d.getDate() + offset);
      return d.toISOString().slice(0, 10);
    }
    const parsed = new Date(node.created_at);
    if (Number.isNaN(parsed.getTime())) {
      const d = new Date(today);
      d.setDate(d.getDate() + offset);
      return d.toISOString().slice(0, 10);
    }
    parsed.setDate(parsed.getDate() + offset);
    return parsed.toISOString().slice(0, 10);
  }
}
