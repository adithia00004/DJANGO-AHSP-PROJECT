// static/detail_project/js/jadwal_pekerjaan/kelola_tahapan/save_handler_module.js
// Save Handler Module for Kelola Tahapan Page

(function() {
  'use strict';

  const bootstrap = window.KelolaTahapanPageApp || window.JadwalPekerjaanApp;
  const manifest = window.KelolaTahapanModuleManifest;

  if (!bootstrap || !manifest) {
    console.error('[SaveHandler] Bootstrap or manifest not found');
    return;
  }

  const meta = {
    id: 'kelolaTahapanSaveHandler',
    namespace: 'kelola_tahapan.save_handler',
    label: 'Kelola Tahapan - Save Handler',
    description: 'Handles save operations with canonical storage conversion'
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
  const moduleStore = globalModules.saveHandler = Object.assign({}, globalModules.saveHandler || {});

  const ONE_DAY_MS = 24 * 60 * 60 * 1000;

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

  /**
   * Show success modal with custom message
   * @param {string} title - Modal title
   * @param {string} message - Main message
   * @param {string} detail - Detail message (optional)
   */
  function showSuccessModal(title, message, detail = '') {
    bootstrap.log.info('[SaveHandler] showSuccessModal called:', { title, message, detail });

    const modalEl = document.getElementById('successModal');
    if (!modalEl) {
      bootstrap.log.warn('[SaveHandler] Success modal element not found in DOM');
      return;
    }

    bootstrap.log.info('[SaveHandler] Modal element found, updating content');

    // Update modal content
    const titleEl = document.getElementById('successModalTitle');
    const messageEl = document.getElementById('successModalMessage');
    const detailEl = document.getElementById('successModalDetail');

    if (titleEl) titleEl.textContent = title;
    if (messageEl) messageEl.textContent = message;
    if (detailEl) {
      detailEl.textContent = detail;
      detailEl.style.display = detail ? 'block' : 'none';
    }

    // Try multiple methods to show modal
    bootstrap.log.info('[SaveHandler] Checking Bootstrap availability...');
    bootstrap.log.info('[SaveHandler] window.bootstrap:', !!window.bootstrap);
    bootstrap.log.info('[SaveHandler] window.bootstrap.Modal:', !!(window.bootstrap && window.bootstrap.Modal));

    try {
      // Method 1: Bootstrap 5 JS API
      if (window.bootstrap && window.bootstrap.Modal) {
        bootstrap.log.info('[SaveHandler] Using Bootstrap 5 Modal API');
        const modal = new window.bootstrap.Modal(modalEl);
        modal.show();
        bootstrap.log.info('[SaveHandler] Modal shown successfully via Bootstrap 5');
        return;
      }

      // Method 2: jQuery Bootstrap
      if (window.$ && typeof window.$.fn.modal === 'function') {
        bootstrap.log.info('[SaveHandler] Using jQuery Bootstrap modal');
        window.$(modalEl).modal('show');
        bootstrap.log.info('[SaveHandler] Modal shown via jQuery');
        return;
      }

      // Method 3: Manual DOM manipulation
      bootstrap.log.warn('[SaveHandler] Bootstrap Modal API not available, using manual DOM');
      modalEl.classList.add('show');
      modalEl.classList.add('fade');
      modalEl.style.display = 'block';
      modalEl.setAttribute('aria-modal', 'true');
      modalEl.removeAttribute('aria-hidden');

      // Add backdrop
      const backdrop = document.createElement('div');
      backdrop.className = 'modal-backdrop fade show';
      backdrop.id = 'successModalBackdrop';
      document.body.appendChild(backdrop);
      document.body.classList.add('modal-open');

      bootstrap.log.info('[SaveHandler] Modal shown manually');

      // Close handler
      const okBtn = modalEl.querySelector('[data-bs-dismiss="modal"]');
      if (okBtn) {
        okBtn.onclick = () => {
          modalEl.classList.remove('show');
          modalEl.style.display = 'none';
          modalEl.setAttribute('aria-hidden', 'true');
          modalEl.removeAttribute('aria-modal');
          const bd = document.getElementById('successModalBackdrop');
          if (bd) bd.remove();
          document.body.classList.remove('modal-open');
        };
      }

    } catch (error) {
      bootstrap.log.error('[SaveHandler] Error showing success modal:', error);
    }
  }

  /**
   * Show confirmation modal and return promise that resolves with user's choice
   * @returns {Promise<boolean>} True if user confirms, false if cancels
   */
  function showResetConfirmationModal() {
    bootstrap.log.info('[SaveHandler] showResetConfirmationModal called');

    return new Promise((resolve) => {
      const modalEl = document.getElementById('resetProgressModal');
      if (!modalEl) {
        bootstrap.log.warn('[SaveHandler] Reset modal not found, using confirm()');
        const result = confirm(
          'Apakah Anda yakin ingin mereset semua progress pekerjaan ke 0?\n\n' +
          'Tindakan ini akan menghapus semua data progress yang telah disimpan.\n\n' +
          'Data tidak dapat dikembalikan setelah direset!'
        );
        resolve(result);
        return;
      }

      const confirmBtn = document.getElementById('confirmResetBtn');
      if (!confirmBtn) {
        bootstrap.log.error('[SaveHandler] Confirm button not found');
        resolve(false);
        return;
      }

      bootstrap.log.info('[SaveHandler] Modal and button found');
      bootstrap.log.info('[SaveHandler] Checking Bootstrap availability...');
      bootstrap.log.info('[SaveHandler] window.bootstrap:', !!window.bootstrap);
      bootstrap.log.info('[SaveHandler] window.bootstrap.Modal:', !!(window.bootstrap && window.bootstrap.Modal));

      let modal = null;
      let isResolved = false;

      const handleConfirm = () => {
        if (isResolved) return;
        bootstrap.log.info('[SaveHandler] User confirmed reset');
        isResolved = true;
        hideModal();
        cleanup();
        resolve(true);
      };

      const handleCancel = () => {
        if (isResolved) return;
        bootstrap.log.info('[SaveHandler] User cancelled reset');
        isResolved = true;
        cleanup();
        resolve(false);
      };

      const hideModal = () => {
        if (modal && typeof modal.hide === 'function') {
          modal.hide();
        } else if (window.$ && typeof window.$.fn.modal === 'function') {
          window.$(modalEl).modal('hide');
        } else {
          modalEl.classList.remove('show');
          modalEl.style.display = 'none';
          modalEl.setAttribute('aria-hidden', 'true');
          modalEl.removeAttribute('aria-modal');
          const backdrop = document.querySelector('.modal-backdrop');
          if (backdrop) backdrop.remove();
          document.body.classList.remove('modal-open');
        }
      };

      const cleanup = () => {
        confirmBtn.removeEventListener('click', handleConfirm);
        modalEl.removeEventListener('hidden.bs.modal', handleCancel);
        const cancelBtns = modalEl.querySelectorAll('[data-bs-dismiss="modal"]');
        cancelBtns.forEach(btn => btn.removeEventListener('click', handleCancel));
      };

      // Attach listeners
      confirmBtn.addEventListener('click', handleConfirm);
      modalEl.addEventListener('hidden.bs.modal', handleCancel, { once: true });

      const cancelBtns = modalEl.querySelectorAll('[data-bs-dismiss="modal"]');
      cancelBtns.forEach(btn => btn.addEventListener('click', handleCancel));

      // Show modal - try multiple methods
      try {
        // Method 1: Bootstrap 5 JS API
        if (window.bootstrap && window.bootstrap.Modal) {
          bootstrap.log.info('[SaveHandler] Showing reset modal via Bootstrap 5');
          modal = new window.bootstrap.Modal(modalEl);
          modal.show();
          bootstrap.log.info('[SaveHandler] Reset modal shown via Bootstrap 5');
          return;
        }

        // Method 2: jQuery Bootstrap
        if (window.$ && typeof window.$.fn.modal === 'function') {
          bootstrap.log.info('[SaveHandler] Showing reset modal via jQuery');
          window.$(modalEl).modal('show');
          bootstrap.log.info('[SaveHandler] Reset modal shown via jQuery');
          return;
        }

        // Method 3: Manual DOM
        bootstrap.log.warn('[SaveHandler] Showing reset modal manually');
        modalEl.classList.add('show');
        modalEl.classList.add('fade');
        modalEl.style.display = 'block';
        modalEl.setAttribute('aria-modal', 'true');
        modalEl.removeAttribute('aria-hidden');

        const backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop fade show';
        document.body.appendChild(backdrop);
        document.body.classList.add('modal-open');

        bootstrap.log.info('[SaveHandler] Reset modal shown manually');

      } catch (error) {
        bootstrap.log.error('[SaveHandler] Error showing reset modal:', error);
        cleanup();
        resolve(false);
      }
    });
  }

  function getWeekNumberForDate(targetDate, projectStart, weekEndDay = 6) {
    if (!(targetDate instanceof Date) || Number.isNaN(targetDate.getTime())) {
      return 1;
    }

    if (!(projectStart instanceof Date) || Number.isNaN(projectStart.getTime())) {
      return 1;
    }

    if (targetDate <= projectStart) {
      return 1;
    }

    const firstWeekEnd = new Date(projectStart);
    const offsetToEnd = (weekEndDay - projectStart.getDay() + 7) % 7;
    firstWeekEnd.setDate(firstWeekEnd.getDate() + offsetToEnd);

    if (targetDate <= firstWeekEnd) {
      return 1;
    }

    const daysAfterFirst = Math.floor((targetDate - firstWeekEnd) / ONE_DAY_MS);
    return 1 + Math.floor((daysAfterFirst + 6) / 7);
  }

  function getProjectStartDate(state) {
    if (state.tahapanList && state.tahapanList.length > 0 && state.tahapanList[0].tanggal_mulai) {
      return new Date(state.tahapanList[0].tanggal_mulai);
    }

    if (state.projectStart) {
      const date = new Date(state.projectStart);
      if (!Number.isNaN(date.getTime())) {
        return date;
      }
    }

    return new Date();
  }

  // =========================================================================
  // SAVE FUNCTIONS
  // =========================================================================

  /**
   * Save all changes to server
   * @param {Object} context - Context with state, helpers
   * @returns {Object} Save result
   */
  async function saveAllChanges(context = {}) {
    const state = resolveState(context.state);
    if (!state) {
      throw new Error('[SaveHandler] State is required');
    }

    const showLoading = context.helpers?.showLoading || (() => {});
    const showToast = context.helpers?.showToast || (() => {});
    const updateStatusBar = context.helpers?.updateStatusBar || (() => {});

    bootstrap.log.info(`SaveHandler: Save All clicked. Modified cells: ${state.modifiedCells.size}`);

    if (state.modifiedCells.size === 0) {
      showToast('No changes to save', 'warning');
      return null;
    }

    try {
      // Step 1: Group changes by pekerjaan
      showLoading('Preparing changes...', `Processing ${state.modifiedCells.size} modified cell(s)`);
      const changesByPekerjaan = new Map();

      state.modifiedCells.forEach((value, key) => {
        // Parse cellKey: format is "pekerjaanId-colId" where colId may contain dashes
        // Split only on FIRST dash to separate pekerjaanId from colId
        const firstDashIndex = key.indexOf('-');
        if (firstDashIndex === -1) {
          bootstrap.log.warn(`SaveHandler: Invalid cellKey format: ${key}`);
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
          bootstrap.log.warn(`SaveHandler: Column not found for colId: ${colId}, or missing tahapanId`);
        }
      });

      bootstrap.log.info('SaveHandler: Changes grouped by pekerjaan:', Array.from(changesByPekerjaan.entries()));

      // Step 2: Validate total progress ≤ 100%
      showLoading('Validating...', 'Checking progress totals');

      const validationModule = globalModules.validation;
      if (!validationModule) {
        throw new Error('[SaveHandler] Validation module not available');
      }

      const validation = validationModule.validateBeforeSave({
        state,
        changesByPekerjaan,
      });

      // Show warnings (don't block save)
      if (validation.warnings && validation.warnings.length > 0) {
        bootstrap.log.warn('SaveHandler: Progress warnings:', validation.warnings);
        showToast(
          `⚠️ ${validation.warnings.length} pekerjaan memiliki progress < 100%`,
          'warning'
        );
      }

      // Block save if errors
      if (!validation.isValid) {
        showLoading(false);
        const errorMessages = validation.errors.map(e => e.message).join('\n');
        showToast(
          `❌ Tidak bisa menyimpan!\n\n${errorMessages}\n\nTotal progress tidak boleh melebihi 100%`,
          'danger'
        );
        bootstrap.log.error('SaveHandler: Validation errors:', validation.errors);
        return null;
      }

      // Step 3: Save each pekerjaan with progress updates
      const totalPekerjaan = changesByPekerjaan.size;
      let successCount = 0;

      for (const [pekerjaanId, assignments] of changesByPekerjaan.entries()) {
        showLoading(
          `Saving changes...`,
          `Pekerjaan ${successCount + 1} of ${totalPekerjaan}`
        );
        bootstrap.log.info(`SaveHandler: Saving pekerjaan ${pekerjaanId}:`, assignments);
        await savePekerjaanAssignments(pekerjaanId, assignments, { state, helpers: context.helpers });
        successCount++;
      }

      bootstrap.log.info(`SaveHandler: Successfully saved ${successCount} pekerjaan assignments`);

      // Step 4: Update UI
      showLoading('Updating UI...', 'Applying saved changes to grid');

      // SUCCESS: Move modified values to assignmentMap
      state.modifiedCells.forEach((value, key) => {
        state.assignmentMap.set(key, value);

        // Update cell data-saved-value attribute
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

      // Show success modal instead of toast for better visibility
      showSuccessModal(
        'Progress Berhasil Disimpan!',
        `Semua perubahan telah disimpan dengan sukses.`,
        `${successCount} pekerjaan telah diperbarui progress-nya.`
      );

      // Also show toast for quick notification (optional)
      showToast(`✓ ${successCount} pekerjaan berhasil disimpan`, 'success');
      updateStatusBar();

      return {
        success: true,
        savedCount: successCount,
        totalPekerjaan,
      };

    } catch (error) {
      bootstrap.log.error('SaveHandler: Save failed', error);
      showToast('Failed to save: ' + error.message, 'danger');
      throw error;
    } finally {
      showLoading(false);
    }
  }

  /**
   * Save assignments for a single pekerjaan
   * Converts to weekly canonical storage
   * @param {string|number} pekerjaanId - Pekerjaan ID
   * @param {Object} assignments - Assignments by tahapan ID
   * @param {Object} context - Context with state, helpers
   */
  async function savePekerjaanAssignments(pekerjaanId, assignments, context = {}) {
    const state = resolveState(context.state);
    if (!state) {
      throw new Error('[SaveHandler] State is required');
    }

    // IMPORTANT: Save to CANONICAL STORAGE (weekly) for lossless data preservation!
    // Strategy:
    // 1. Convert tahapan assignments to weekly format (different logic for each mode)
    // 2. Save to PekerjaanProgressWeekly (canonical)
    // 3. Backend will automatically sync to PekerjaanTahapan (view layer)

    const weeklyAssignments = [];
    const projectStart = getProjectStartDate(state);

    bootstrap.log.info(`SaveHandler: Converting ${state.timeScale} mode assignments to weekly canonical format...`);

    if (state.timeScale === 'weekly') {
      // WEEKLY MODE: Direct 1:1 mapping
      for (const [tahapanId, proporsi] of Object.entries(assignments)) {
        if (parseFloat(proporsi) < 0) continue;  // Allow 0 to clear assignments

        const tahapan = state.tahapanList.find(t => t.tahapan_id == tahapanId);
        if (!tahapan || !tahapan.tanggal_mulai) {
          bootstrap.log.warn(`SaveHandler: Tahapan ${tahapanId} not found, skipping`);
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
          weekNumber = getWeekNumberForDate(tahapStart, projectStart, state.weekEndDay || 6);
        }

        bootstrap.log.info(`SaveHandler: - Week ${weekNumber}: ${proporsi}%`);

        weeklyAssignments.push({
          pekerjaan_id: parseInt(pekerjaanId),
          week_number: weekNumber,
          proportion: parseFloat(proporsi),
          notes: `Saved from ${state.timeScale} mode`
        });
      }

    } else if (state.timeScale === 'daily') {
      // DAILY MODE: Aggregate days into weeks
      bootstrap.log.info(`SaveHandler: Aggregating ${Object.keys(assignments).length} daily values into weeks...`);

      const weeklyProportions = new Map();

      for (const [tahapanId, proporsi] of Object.entries(assignments)) {
        if (parseFloat(proporsi) < 0) continue;

        const tahapan = state.tahapanList.find(t => t.tahapan_id == tahapanId);
        if (!tahapan || !tahapan.tanggal_mulai) continue;

        // Calculate which week this day belongs to
        const dayDate = new Date(tahapan.tanggal_mulai);
        const weekNumber = getWeekNumberForDate(dayDate, projectStart, state.weekEndDay || 6);

        // Accumulate proportions for this week
        const current = weeklyProportions.get(weekNumber) || 0;
        weeklyProportions.set(weekNumber, current + parseFloat(proporsi));

        bootstrap.log.info(`SaveHandler: - Day ${tahapan.nama} → Week ${weekNumber}: +${proporsi}%`);
      }

      // Convert accumulated weekly proportions to assignments
      weeklyProportions.forEach((proportion, weekNumber) => {
        bootstrap.log.info(`SaveHandler: → Week ${weekNumber}: ${proportion.toFixed(2)}% (aggregated from daily)`);
        weeklyAssignments.push({
          pekerjaan_id: parseInt(pekerjaanId),
          week_number: weekNumber,
          proportion: Math.round(proportion * 100) / 100,
          notes: `Saved from ${state.timeScale} mode (aggregated from daily)`
        });
      });

    } else if (state.timeScale === 'monthly') {
      // MONTHLY MODE: Split monthly to daily, then aggregate to weekly
      bootstrap.log.info(`SaveHandler: Splitting ${Object.keys(assignments).length} monthly values to daily, then aggregating to weekly...`);

      const weeklyProportions = new Map();

      for (const [tahapanId, proporsi] of Object.entries(assignments)) {
        if (parseFloat(proporsi) < 0) continue;

        const tahapan = state.tahapanList.find(t => t.tahapan_id == tahapanId);
        if (!tahapan || !tahapan.tanggal_mulai || !tahapan.tanggal_selesai) continue;

        const monthStart = new Date(tahapan.tanggal_mulai);
        const monthEnd = new Date(tahapan.tanggal_selesai);

        // Calculate days in this month
        const daysInMonth = Math.floor((monthEnd - monthStart) / ONE_DAY_MS) + 1;
        const dailyProportion = parseFloat(proporsi) / daysInMonth;

        bootstrap.log.info(`SaveHandler: - Month ${tahapan.nama}: ${proporsi}% / ${daysInMonth} days = ${dailyProportion.toFixed(4)}% per day`);

        // Distribute to each day, then aggregate to weeks
        let currentDate = new Date(monthStart);
        while (currentDate <= monthEnd) {
          const weekNumber = getWeekNumberForDate(currentDate, projectStart, state.weekEndDay || 6);

          const current = weeklyProportions.get(weekNumber) || 0;
          weeklyProportions.set(weekNumber, current + dailyProportion);

          currentDate.setDate(currentDate.getDate() + 1);
        }
      }

      // Convert accumulated weekly proportions to assignments
      weeklyProportions.forEach((proportion, weekNumber) => {
        bootstrap.log.info(`SaveHandler: → Week ${weekNumber}: ${proportion.toFixed(2)}% (aggregated from monthly→daily)`);
        weeklyAssignments.push({
          pekerjaan_id: parseInt(pekerjaanId),
          week_number: weekNumber,
          proportion: Math.round(proportion * 100) / 100,
          notes: `Saved from ${state.timeScale} mode (split from monthly)`
        });
      });

    } else {
      // CUSTOM MODE: Use week-based calculation as fallback
      bootstrap.log.warn('SaveHandler: Custom mode: Using week-based calculation');
      for (const [tahapanId, proporsi] of Object.entries(assignments)) {
        if (parseFloat(proporsi) < 0) continue;

        const tahapan = state.tahapanList.find(t => t.tahapan_id == tahapanId);
        if (!tahapan || !tahapan.tanggal_mulai) continue;

        const tahapStart = new Date(tahapan.tanggal_mulai);
        const weekNumber = getWeekNumberForDate(tahapStart, projectStart, state.weekEndDay || 6);

        weeklyAssignments.push({
          pekerjaan_id: parseInt(pekerjaanId),
          week_number: weekNumber,
          proportion: parseFloat(proporsi),
          notes: `Saved from ${state.timeScale} mode`
        });
      }
    }

    bootstrap.log.info(`SaveHandler: - Saving ${weeklyAssignments.length} weekly assignments to canonical storage`);

    if (weeklyAssignments.length === 0) {
      bootstrap.log.warn(`SaveHandler: - No assignments to save for pekerjaan ${pekerjaanId}`);
      return;
    }

    // Save to canonical storage (API V2)
    const url = `/detail_project/api/v2/project/${state.projectId}/assign-weekly/`;
    const payload = {
      assignments: weeklyAssignments,
      mode: state.timeScale,        // tell backend which grid view is active so it can sync PekerjaanTahapan
      week_end_day: state.weekEndDay || 6
    };
    bootstrap.log.info(`SaveHandler: - POST ${url}`, payload);

    const response = await apiCall(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify(payload)
    });

    bootstrap.log.info(`SaveHandler: - Weekly canonical save response:`, response);

    if (!response.ok) {
      throw new Error(response.error || 'Failed to save to canonical storage');
    }

    bootstrap.log.info(`SaveHandler: ✓ Successfully saved to canonical storage: ${response.created_count} created, ${response.updated_count} updated`);
    bootstrap.log.info(`SaveHandler: ✓ View layer will be synced on next mode operation`);
  }

  /**
   * Reset all progress to 0
   * @param {Object} context - Context with state, helpers
   */
  async function resetAllProgress(context = {}) {
    const state = resolveState(context.state);
    if (!state) {
      throw new Error('[SaveHandler] State is required');
    }

    const showLoading = context.helpers?.showLoading || (() => {});
    const showToast = context.helpers?.showToast || (() => {});
    const updateStatusBar = context.helpers?.updateStatusBar || (() => {});
    const renderGrid = context.helpers?.renderGrid || (() => {});

    // Show confirmation modal and wait for user response
    const userConfirmed = await showResetConfirmationModal();

    if (!userConfirmed) {
      bootstrap.log.info('[SaveHandler] Reset cancelled by user');
      return null;
    }

    try {
      showLoading('Resetting all progress...', 'Please wait while we reset all pekerjaan progress');

      // Call API to reset progress
      const response = await apiCall(`/detail_project/api/v2/project/${state.projectId}/reset-progress/`, {
        method: 'POST',
        body: JSON.stringify({})
      });

      if (response.ok) {
        bootstrap.log.info('SaveHandler: Progress reset successful:', response);

        // Clear all assignments and modified cells
        state.assignmentMap.clear();
        state.modifiedCells.clear();

        // Re-render grid to show empty progress
        renderGrid();

        // Show success modal
        showSuccessModal(
          'Progress Berhasil Direset!',
          'Semua progress pekerjaan telah direset ke 0.',
          `${response.deleted_count || 0} record progress telah dihapus dari database.`
        );

        // Also show toast
        showToast(
          `✓ Progress berhasil direset (${response.deleted_count || 0} record dihapus)`,
          'success'
        );
        updateStatusBar();

        return {
          success: true,
          deletedCount: response.deleted_count || 0,
        };
      } else {
        throw new Error(response.error || 'Failed to reset progress');
      }

    } catch (error) {
      bootstrap.log.error('SaveHandler: Reset progress error:', error);
      showToast(`Error resetting progress: ${error.message}`, 'error');
      throw error;
    } finally {
      showLoading(false);
    }
  }

  // =========================================================================
  // MODULE EXPORTS
  // =========================================================================

  Object.assign(moduleStore, {
    resolveState,
    saveAllChanges,
    savePekerjaanAssignments,
    resetAllProgress,
    // UI Helpers
    showSuccessModal,
    showResetConfirmationModal,
    // Utilities
    getWeekNumberForDate,
    getProjectStartDate,
    apiCall,
    getCookie,
  });

  // Register module with bootstrap
  bootstrap.registerModule(meta.id, {
    namespace: meta.namespace,
    pageId: manifest.pageId,
    description: meta.description,
    onRegister(context) {
      bootstrap.log.info('SaveHandler module registered successfully');
      if (context && context.emit) {
        context.emit('kelola_tahapan.save_handler:registered', { meta });
      }
    },
    // Public API
    saveAllChanges: (context) => moduleStore.saveAllChanges(context),
    savePekerjaanAssignments: (pekerjaanId, assignments, context) =>
      moduleStore.savePekerjaanAssignments(pekerjaanId, assignments, context),
    resetAllProgress: (context) => moduleStore.resetAllProgress(context),
    apiCall: (url, options) => moduleStore.apiCall(url, options),
  });

  bootstrap.log.info('[SaveHandler] Module initialized');
})();
