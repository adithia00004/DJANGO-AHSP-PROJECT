import { DataLoader } from '@modules/core/data-loader.js';
import { TimeColumnGenerator } from '@modules/core/time-column-generator.js';
import { SaveHandler } from '@modules/core/save-handler.js';

/**
 * DataOrchestrator - Manages data loading, timeline regeneration, and save operations
 *
 * This class is responsible for:
 * - Loading initial data (tahapan, pekerjaan, volumes, assignments)
 * - Coordinating DataLoader, TimeColumnGenerator, and SaveHandler
 * - Regenerating timeline when scale changes (weekly/monthly)
 * - Handling refresh and reload operations
 * - Managing loading states and error handling
 *
 * @class DataOrchestrator
 * @example
 * const orchestrator = new DataOrchestrator(app);
 * await orchestrator.loadInitialData();
 * await orchestrator.regenerateTimeline({ mode: 'weekly' });
 */
export class DataOrchestrator {
  /**
   * Create a new DataOrchestrator instance
   * @param {Object} app - JadwalKegiatanApp instance
   */
  constructor(app) {
    this.app = app;
  }

  /**
   * Load initial data (tahapan, pekerjaan, volumes, assignments) and initialize charts
   *
   * Loading sequence:
   * 1. Check if data already preloaded from template
   * 2. Initialize DataLoader, TimeColumnGenerator, SaveHandler
   * 3. Load base data (tahapan list, pekerjaan tree, volumes)
   * 4. Generate time columns (enforce weekly if needed)
   * 5. Load assignments and calculate progress totals
   * 6. Load S-Curve cost data
   * 7. Initialize and update charts
   *
   * @param {Object} options - Loading options
   * @param {boolean} [options.forceReload=false] - Force reload even if data exists
   * @returns {Promise<void>}
   *
   * @example
   * await orchestrator.loadInitialData({ forceReload: true });
   */
  async loadInitialData(options = {}) {
    const app = this.app;
    const { forceReload = false } = options;

    if (!forceReload && app.state.pekerjaanTree?.length > 0) {
      console.log('[JadwalKegiatanApp] Using template dataset');
      console.log('Preloaded pekerjaanTree items:', app.state.pekerjaanTree.length);
      console.log('Preloaded tahapanList items:', app.state.tahapanList?.length || 0);
      console.log('Preloaded timeColumns items:', app.state.timeColumns?.length || 0);
      app._recalculateAllProgressTotals();
      app._syncGridViews();
      return;
    }

    app._showSkeleton('grid');

    // Init modern modules
    app.state.apiBase = app.state.apiEndpoints?.tahapan || `/detail_project/api/project/${app.state.projectId}/tahapan/`;
    app.dataLoader = new DataLoader(app.state);
    app.timeColumnGenerator = new TimeColumnGenerator(app.state);
    app.saveHandler = new SaveHandler(app.state, {
      apiUrl:
        app.state.apiEndpoints?.save ||
        `/detail_project/api/project/${app.state.projectId}/pekerjaan/assign_weekly/`,
      onSuccess: (result) => app._onSaveSuccess(result),
      onError: (error) => app._onSaveError(error),
      showToast: (msg, type) => app.showToast(msg, type),
      dataLoader: app.dataLoader
    });

    app.state.isLoading = true;

    try {
      console.log('[JadwalKegiatanApp] Loading data using modern DataLoader...');

      // 1) Base data
      await app.dataLoader.loadAllData({ skipIfLoaded: false, force: forceReload });

      // 2) Generate time columns (enforce weekly jika perlu)
      app.timeColumnGenerator.generate();
      const normalizedDisplayScale = (app.state.displayScale || app.state.timeScale || 'weekly').toLowerCase();
      if (!app._isEnforcingWeekly && normalizedDisplayScale === 'weekly') {
        const weeklyCount = app._countWeeklyColumns();
        const expectedWeeks = app._estimateExpectedWeeklyColumns();
        const firstColumnMode =
          (app.state.timeColumns?.[0]?.generationMode || app.state.timeColumns?.[0]?.type || '').toLowerCase();

        const shouldForceWeekly =
          weeklyCount === 0 ||
          firstColumnMode === 'monthly' ||
          (expectedWeeks > 0 && weeklyCount > 0 && weeklyCount < expectedWeeks);

        if (shouldForceWeekly) {
          console.warn('[JadwalKegiatanApp] Weekly columns incomplete; regenerating weekly structure based on project timeline...');
          app._isEnforcingWeekly = true;
          await this.regenerateTimeline({
            mode: 'weekly',
            weekStartDay: app._getWeekStartDay(),
            weekEndDay: app._getWeekEndDay(),
          });
          app._isEnforcingWeekly = false;
          return;
        }
      }

      // 3) Assignments + totals
      await app.dataLoader.loadAssignments();
      app._recalculateAllProgressTotals();

      // 3.5) Kurva S harga
      await app._loadKurvaSData();

      // 3.6) Dependencies array untuk unified overlay
      app.state.dependencies = app.state.dependencies || [];
      app.state.timeColumnIndex = app._createTimeColumnIndex(app.state.timeColumns);

      console.log(
        '[JadwalKegiatanApp] ƒo. Data loaded successfully:',
        `${app.state.flatPekerjaan?.length || 0} pekerjaan,`,
        `${app.state.tahapanList?.length || 0} tahapan,`,
        `${app.state.timeColumns?.length || 0} columns`
      );

      // 4) Charts
      app._initializeCharts();
      app._updateCharts();
    } catch (error) {
      console.error('[JadwalKegiatanApp] ƒ?O Failed to load data:', error);
      app.state.error = error;
      app.showToast('Gagal memuat data: ' + error.message, 'danger');
    } finally {
      app.state.isLoading = false;
      app._syncGridViews();
      app._hideSkeleton('grid');
    }
  }

  /**
   * Regenerate timeline columns (weekly/monthly) and reload dataset
   *
   * This triggers a backend API call to regenerate tahapan with new time scale.
   * Unsaved changes will be lost (user is prompted for confirmation).
   *
   * @param {Object} options - Regeneration options
   * @param {string} [options.mode='weekly'] - Time scale mode ('weekly' or 'monthly')
   * @param {number} [options.weekStartDay] - Week start day (0=Sunday, 1=Monday, etc.)
   * @param {number} [options.weekEndDay] - Week end day (0=Sunday, 6=Saturday, etc.)
   * @returns {Promise<void>}
   *
   * @example
   * await orchestrator.regenerateTimeline({
   *   mode: 'weekly',
   *   weekStartDay: 1, // Monday
   *   weekEndDay: 6    // Saturday
   * });
   */
  async regenerateTimeline(options = {}) {
    const app = this.app;
    const { mode = 'weekly', weekStartDay, weekEndDay } = options;
    const endpoint = app.state.apiEndpoints?.regenerateTahapan;
    if (!endpoint) return;

    if (app._isRegeneratingTimeline) {
      app._queuedRegeneratePayload = { mode, weekStartDay, weekEndDay };
      return;
    }

    if (app.state.isDirty && app.state.modifiedCells instanceof Map && app.state.modifiedCells.size > 0) {
      const confirmed = window.confirm(
        'Mengubah batas minggu akan me-refresh data dan membatalkan perubahan yang belum disimpan. Lanjutkan?'
      );
      if (!confirmed) return;
      app._resetEditedCellsState();
      app.state.isDirty = false;
    }

    app._isRegeneratingTimeline = true;
    app.state.isLoading = true;
    const statusLabel = mode === 'monthly' ? 'Mengatur ulang struktur bulanan...' : 'Mengatur ulang struktur minggu...';
    app._updateStatusBar(statusLabel);
    const toastLabel =
      mode === 'monthly'
        ? 'Mengatur ulang kolom monthly...'
        : 'Mengatur ulang kolom weekly sesuai preferensi Anda...';
    app.showToast(toastLabel, 'info', 2400);

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': app._getCsrfToken(),
        },
        body: JSON.stringify({
          mode,
          ...(mode === 'weekly'
            ? {
                week_start_day:
                  typeof weekStartDay === 'number' ? weekStartDay : app._getWeekStartDay(),
                week_end_day:
                  typeof weekEndDay === 'number' ? weekEndDay : app._getWeekEndDay(),
              }
            : {}),
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      app._invalidateCachedDataset();
      await this.loadInitialData({ forceReload: true });
      const successMessage =
        mode === 'monthly' ? 'Struktur monthly diperbarui (read-only)' : 'Periode minggu diperbarui';
      app.showToast(successMessage, 'success', 2200);
    } catch (error) {
      console.error('[JadwalKegiatanApp] Failed to regenerate weekly structure', error);
      app.showToast('Gagal memperbarui struktur waktu', 'danger', 3200);
    } finally {
      app.state.isLoading = false;
      app._updateStatusBar();
      app._isRegeneratingTimeline = false;
      if (app._queuedRegeneratePayload) {
        const next = app._queuedRegeneratePayload;
        app._queuedRegeneratePayload = null;
        this.regenerateTimeline(next);
      }
    }
  }
}
