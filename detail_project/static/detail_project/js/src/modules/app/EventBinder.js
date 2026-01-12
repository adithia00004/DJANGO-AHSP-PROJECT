import {
  KeyboardShortcuts,
  Toast,
  initializeUXEnhancements
} from '@modules/shared/ux-enhancements.js';

/**
 * EventBinder - Handles UI event wiring and UX helpers for Jadwal Kegiatan
 *
 * This class is responsible for:
 * - Attaching event listeners to toolbar buttons (save, refresh, reset)
 * - Setting up keyboard shortcuts (Ctrl+S, Ctrl+R, etc.)
 * - Wiring radio button groups (display mode, progress mode, time scale)
 * - Initializing UX enhancements (tooltips, loading states, etc.)
 *
 * @class EventBinder
 * @example
 * const binder = new EventBinder(app);
 * binder.attachAll(); // Wire all events
 */
export class EventBinder {
  /**
   * Create a new EventBinder instance
   * @param {Object} app - JadwalKegiatanApp instance (acts as controller)
   */
  constructor(app) {
    this.app = app;
  }

  /**
   * Attach all event listeners (toolbar, shortcuts, UX enhancements)
   *
   * This is the main entry point called during app initialization.
   * Delegates to specialized setup methods for different event categories.
   *
   * @returns {void}
   */
  attachAll() {
    this._attachToolbarEvents();
    this.app._initTanStackGridIfNeeded();
  }

  /**
   * Attach toolbar button events and radio group handlers (private)
   *
   * Wires up:
   * - Save/Refresh/Reset buttons
   * - Display mode radios (percentage/volume/cost)
   * - Progress mode radios (planned/actual)
   * - Time scale radios (daily/weekly/monthly)
   * - Week boundary controls
   * - Export buttons
   * - Cost view toggle
   * - Keyboard shortcuts
   * - UX enhancements
   *
   * @private
   * @returns {void}
   */
  _attachToolbarEvents() {
    const dom = this.app.state?.domRefs || {};
    const saveButton = dom.saveButton;
    const refreshButton = dom.refreshButton;
    const resetButton = dom.resetButton;

    if (saveButton) {
      saveButton.addEventListener('click', () => this.app.saveChanges());
    }

    if (refreshButton) {
      refreshButton.addEventListener('click', () => this.app.refresh());
    }

    if (resetButton) {
      resetButton.addEventListener('click', () => this.app._handleResetProgress());
    }

    this.app._syncToolbarRadios();
    this.app._attachRadioGroupHandler('displayMode', (value) => this.app._handleDisplayModeChange(value));
    this.app._attachRadioGroupHandler('progressMode', (value) => this.app._handleProgressModeChange(value));
    this.app._attachRadioGroupHandler('timeScale', (value) => this.app._handleTimeScaleChange(value));
    this.app._setupWeekBoundaryControls();
    this.app._setupExportButtons();
    this.app._setupCostViewToggle();
    this._setupKeyboardShortcuts();
    this._setupUXEnhancements();
  }

  /**
   * Setup keyboard shortcuts for common actions (private)
   *
   * Registered shortcuts:
   * - Ctrl+S: Save changes
   * - Ctrl+R: Refresh data
   * - Ctrl+Alt+P: Switch to Perencanaan mode
   * - Ctrl+Alt+A: Switch to Realisasi mode
   * - Ctrl+Alt+1: Switch to Percentage display
   * - Ctrl+Alt+2: Switch to Volume display
   * - Ctrl+Alt+3: Switch to Cost display
   * - Escape: Close open menus
   * - Ctrl+Shift+/: Show shortcuts help
   *
   * @private
   * @returns {void}
   */
  _setupKeyboardShortcuts() {
    this.app.keyboardShortcuts = new KeyboardShortcuts();

    this.app.keyboardShortcuts.register('ctrl+s', () => {
      this.app.saveChanges();
      Toast.info('Saving changes... (Ctrl+S)');
    }, { description: 'Save all changes' });

    this.app.keyboardShortcuts.register('ctrl+r', () => {
      this.app.refresh();
      Toast.info('Refreshing data... (Ctrl+R)');
    }, { description: 'Refresh data from server' });

    this.app.keyboardShortcuts.register('ctrl+alt+p', () => {
      const plannedRadio = document.getElementById('mode-planned');
      if (plannedRadio) {
        plannedRadio.checked = true;
        plannedRadio.dispatchEvent(new Event('change', { bubbles: true }));
        Toast.info('Switched to Perencanaan mode (Ctrl+Alt+P)');
      }
    }, { description: 'Switch to Perencanaan mode' });

    this.app.keyboardShortcuts.register('ctrl+alt+a', () => {
      const actualRadio = document.getElementById('mode-actual');
      if (actualRadio) {
        actualRadio.checked = true;
        actualRadio.dispatchEvent(new Event('change', { bubbles: true }));
        Toast.info('Switched to Realisasi mode (Ctrl+Alt+A)');
      }
    }, { description: 'Switch to Realisasi mode' });

    this.app.keyboardShortcuts.register('ctrl+alt+1', () => {
      const percentageRadio = document.getElementById('mode-percentage');
      if (percentageRadio && !percentageRadio.disabled) {
        percentageRadio.checked = true;
        percentageRadio.dispatchEvent(new Event('change', { bubbles: true }));
        Toast.info('Display: Percentage (Ctrl+Alt+1)');
      }
    }, { description: 'Switch to Percentage display' });

    this.app.keyboardShortcuts.register('ctrl+alt+2', () => {
      const volumeRadio = document.getElementById('mode-volume');
      if (volumeRadio && !volumeRadio.disabled) {
        volumeRadio.checked = true;
        volumeRadio.dispatchEvent(new Event('change', { bubbles: true }));
        Toast.info('Display: Volume (Ctrl+Alt+2)');
      }
    }, { description: 'Switch to Volume display' });

    this.app.keyboardShortcuts.register('ctrl+alt+3', () => {
      const costRadio = document.getElementById('mode-cost');
      if (costRadio && !costRadio.disabled) {
        costRadio.checked = true;
        costRadio.dispatchEvent(new Event('change', { bubbles: true }));
        Toast.info('Display: Cost (Ctrl+Alt+3)');
      } else {
        Toast.warning('Cost view only available in Realisasi mode');
      }
    }, { description: 'Switch to Cost display' });

    this.app.keyboardShortcuts.register('escape', () => {
      const openDropdowns = document.querySelectorAll('.dropdown-menu.show');
      openDropdowns.forEach(dropdown => {
        const toggle = dropdown.previousElementSibling;
        if (toggle) {
          const bsDropdown = bootstrap.Dropdown.getInstance(toggle);
          if (bsDropdown) bsDropdown.hide();
        }
      });
    }, { description: 'Close open menus', preventDefault: false });

    this.app.keyboardShortcuts.register('ctrl+shift+/', () => {
      this._showKeyboardShortcutsHelp();
    }, { description: 'Show keyboard shortcuts help' });

    if (this.app?.state?.debugUnifiedTable || window.DEBUG_UNIFIED_TABLE) {
      console.log('[EventBinder] Keyboard shortcuts registered', this.app.keyboardShortcuts.getShortcuts?.());
    }
  }

  /**
   * Initialize UX enhancements (tooltips, keyboard hints, etc.) (private)
   *
   * Applies:
   * - Bootstrap tooltips initialization
   * - Keyboard hint badges on buttons
   * - Loading state utilities
   * - Focus management
   *
   * @private
   * @returns {void}
   */
  _setupUXEnhancements() {
    initializeUXEnhancements();
    const saveButton = this.app.state?.domRefs?.saveButton;
    if (saveButton) {
      saveButton.setAttribute('data-keyboard-hint', 'Ctrl+S');
    }
    if (this.app?.state?.debugUnifiedTable || window.DEBUG_UNIFIED_TABLE) {
      console.log('[EventBinder] UX enhancements applied');
    }
  }

  /**
   * Display keyboard shortcuts help modal (private)
   *
   * Shows a Bootstrap modal with all registered keyboard shortcuts
   * and their descriptions in a formatted table.
   *
   * @private
   * @returns {void}
   */
  _showKeyboardShortcutsHelp() {
    const shortcuts = this.app.keyboardShortcuts?.getShortcuts?.() || [];
    const shortcutList = shortcuts.map(s => `
      <tr>
        <td><kbd>${s.key.replace(/\\+/g, '</kbd> + <kbd>')}</kbd></td>
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
                    <th>Shortcut</th>
                    <th>Deskripsi</th>
                  </tr>
                </thead>
                <tbody>
                  ${shortcutList}
                </tbody>
              </table>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
            </div>
          </div>
        </div>
      </div>
    `;

    const existingModal = document.getElementById('keyboardShortcutsModal');
    if (existingModal) {
      existingModal.remove();
    }
    const container = document.createElement('div');
    container.innerHTML = modalHtml;
    document.body.appendChild(container.firstElementChild);

    const modal = new bootstrap.Modal(document.getElementById('keyboardShortcutsModal'));
    document.getElementById('keyboardShortcutsModal').addEventListener('hidden.bs.modal', function() {
      const el = document.getElementById('keyboardShortcutsModal');
      if (el && el.parentNode) el.parentNode.removeChild(el);
    });
    modal.show();
  }
}
