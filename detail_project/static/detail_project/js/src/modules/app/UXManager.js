/**
 * UXManager - Manages UI/UX elements and user interactions
 *
 * This class is responsible for:
 * - Syncing toolbar radio buttons with application state
 * - Managing skeleton loaders (show/hide)
 * - Setting up week boundary controls
 * - Configuring cost view toggle
 * - Handling loading states and transitions
 *
 * @class UXManager
 * @example
 * const uxManager = new UXManager(app);
 * uxManager.syncToolbarRadios();
 * uxManager.showSkeleton('grid');
 */
export class UXManager {
  /**
   * Create a new UXManager instance
   * @param {Object} app - JadwalKegiatanApp instance
   */
  constructor(app) {
    this.app = app;
  }

  /**
   * Sync toolbar radio buttons with application state
   *
   * Updates checked state for:
   * - Display mode (percentage/volume/cost)
   * - Progress mode (planned/actual)
   * - Time scale (daily/weekly/monthly)
   *
   * Called during initialization and when state changes.
   *
   * @returns {void}
   */
  syncToolbarRadios() {
    const state = this.app?.state || {};
    const displayMode = state.inputMode || 'percentage';
    this._setRadioGroupChecked('displayMode', displayMode);

    const progressMode = state.progressMode || 'planned';
    this._setRadioGroupChecked('progressMode', progressMode, { ariaSelected: true });

    const timeScale = state.displayScale || state.timeScale || 'weekly';
    this._setRadioGroupChecked('timeScale', timeScale);

    if (typeof this.app?._updateCostToggleAvailability === 'function') {
      this.app._updateCostToggleAvailability();
    }
  }

  /**
   * Attach change handler to radio button group
   *
   * @param {string} groupName - Radio group name attribute
   * @param {Function} handler - Handler function called with selected value
   * @returns {void}
   *
   * @example
   * uxManager.attachRadioGroupHandler('displayMode', (value) => {
   *   console.log('Display mode changed to:', value);
   * });
   */
  attachRadioGroupHandler(groupName, handler) {
    const radios = document.querySelectorAll(`input[name="${groupName}"]`);
    if (!radios || radios.length === 0) return;
    radios.forEach((radio) => {
      radio.addEventListener('change', (event) => {
        if (!event.target.checked) return;
        handler(event.target.value);
      });
    });
  }

  /**
   * Set checked state for radio group (private)
   *
   * @private
   * @param {string} groupName - Radio group name
   * @param {string} value - Value to check
   * @param {Object} options - Additional options
   * @param {boolean} [options.ariaSelected] - Set aria-selected on labels
   * @returns {void}
   */
  _setRadioGroupChecked(groupName, value, options = {}) {
    const radios = document.querySelectorAll(`input[name="${groupName}"]`);
    radios.forEach((radio) => {
      const isChecked = radio.value === value;
      if (radio.checked !== isChecked) {
        radio.checked = isChecked;
      }
      if (options.ariaSelected) {
        const label = radio.nextElementSibling;
        if (label && label.matches('.btn')) {
          label.setAttribute('aria-selected', String(isChecked));
        }
      }
    });
  }

  /**
   * Setup week boundary (start/end day) controls
   *
   * Wires up event listeners for week start/end select dropdowns.
   * When changed, automatically regenerates timeline with new boundaries.
   *
   * @returns {void}
   */
  setupWeekBoundaryControls() {
    const { weekStartSelect, weekEndSelect } = this.app.state.domRefs || {};
    if (!weekStartSelect || !weekEndSelect) return;

    this.app._syncWeekBoundaryControls();

    weekStartSelect.addEventListener('change', (event) => {
      const nextStart = this.app._normalizePythonWeekday(event.target.value, this.app._getWeekStartDay());
      const derivedEnd = (nextStart + 6) % 7;
      this.app._handleWeekBoundaryChange({ weekStartDay: nextStart, weekEndDay: derivedEnd, source: 'start' });
    });

    weekEndSelect.addEventListener('change', (event) => {
      const nextEnd = this.app._normalizePythonWeekday(event.target.value, this.app._getWeekEndDay());
      const derivedStart = (nextEnd + 1) % 7;
      this.app._handleWeekBoundaryChange({ weekStartDay: derivedStart, weekEndDay: nextEnd, source: 'end' });
    });
  }

  /**
   * Setup cost view toggle button for S-Curve chart
   *
   * Configures the "Biaya" button that switches S-Curve between
   * progress view and cost view (EVM metrics).
   *
   * @returns {void}
   */
  setupCostViewToggle() {
    const toggleBtn = document.getElementById('toggleCostViewBtn');
    const toggleBtnText = document.getElementById('toggleCostViewBtnText');
    const toggleBtnSpinner = document.getElementById('toggleCostViewBtnSpinner');
    const toggleBtnIcon = toggleBtn?.querySelector('i');

    if (!toggleBtn) {
      this.app._log?.('[JadwalKegiatanApp] Cost view toggle button not found (chart tab may not be active)');
      return;
    }

    if (!this.app.kurvaSChart) {
      console.warn('[JadwalKegiatanApp] Kurva S chart not initialized, cannot setup toggle');
      return;
    }

    if (this.app.kurvaSChart?.options?.enableCostView === false) {
      toggleBtn.classList.add('d-none');
      return;
    }

    this.app._costToggleBtn = toggleBtn;
    this.app._costToggleBtnText = toggleBtnText;
    this.app._costToggleSpinner = toggleBtnSpinner;
    this.app._costToggleBtnIcon = toggleBtnIcon;

    const enable = () => {
      toggleBtn.disabled = false;
      toggleBtn.classList.remove('disabled');
      if (toggleBtnSpinner) toggleBtnSpinner.classList.add('d-none');
      if (toggleBtnIcon) toggleBtnIcon.classList.remove('d-none');
    };

    const disable = () => {
      toggleBtn.disabled = true;
      toggleBtn.classList.add('disabled');
      if (toggleBtnSpinner) toggleBtnSpinner.classList.remove('d-none');
      if (toggleBtnIcon) toggleBtnIcon.classList.add('d-none');
    };

    const updateLabel = (label) => {
      if (toggleBtnText) toggleBtnText.textContent = label;
    };

    const handleClick = async () => {
      disable();
      updateLabel('Memuat biaya...');
      try {
        if (typeof this.app._loadCostView === 'function') {
          await this.app._loadCostView();
        }
      } catch (error) {
        console.error('[JadwalKegiatanApp] Failed to toggle cost view', error);
        if (typeof this.app.showToast === 'function') {
          this.app.showToast('Gagal memuat view biaya', 'danger', 2600);
        }
      } finally {
        enable();
        updateLabel('Biaya');
      }
    };

    toggleBtn.addEventListener('click', handleClick);
  }

  /**
   * Show skeleton loader for a view type
   *
   * Displays animated skeleton loader while content is loading.
   * Hides actual content to prevent layout shift.
   *
   * @param {string} type - View type ('grid', 'gantt', 'scurve')
   * @returns {void}
   *
   * @example
   * uxManager.showSkeleton('grid');
   */
  showSkeleton(type) {
    const skeleton = document.getElementById(`skeleton-${type}`);
    const view = document.getElementById(`${type}-view`);
    if (skeleton) {
      skeleton.classList.add('showing');
      skeleton.classList.remove('fade-out');
    }
    if (view) {
      view.classList.add('content-hidden');
    }
  }

  /**
   * Hide skeleton loader and show actual content
   *
   * Fades out skeleton with 300ms transition, then reveals content.
   *
   * @param {string} type - View type ('grid', 'gantt', 'scurve')
   * @returns {void}
   *
   * @example
   * uxManager.hideSkeleton('grid');
   */
  hideSkeleton(type) {
    const skeleton = document.getElementById(`skeleton-${type}`);
    const view = document.getElementById(`${type}-view`);
    if (skeleton) {
      skeleton.classList.add('fade-out');
      setTimeout(() => {
        skeleton.classList.remove('showing');
        skeleton.classList.remove('fade-out');
      }, 300);
    }
    if (view) {
      view.classList.remove('content-hidden');
    }
  }
}
