// detail_project/static/detail_project/js/core/loading.js
/**
 * Loading Manager - Centralized loading state management
 *
 * Provides:
 * - Global loading overlay
 * - Inline loading indicators
 * - Progress tracking for long operations
 * - Automatic cleanup
 *
 * Usage:
 *   import LoadingManager from './core/loading.js';
 *
 *   // Simple loading
 *   LoadingManager.show('Menyimpan data...');
 *   await saveData();
 *   LoadingManager.hide();
 *
 *   // With auto-cleanup
 *   await LoadingManager.wrap(saveData(), 'Menyimpan data...');
 *
 *   // Progress tracking
 *   LoadingManager.showProgress('Mengupload file...', 0, 100);
 *   // ... update progress
 *   LoadingManager.updateProgress(50);
 *   LoadingManager.hide();
 */

class LoadingManager {
    constructor() {
        this.overlayId = 'dp-loading-overlay';
        this.currentOverlay = null;
        this.progressCallback = null;
        this.isShowing = false;
    }

    /**
     * Show global loading overlay
     * @param {string} message - Message to display
     * @param {Object} options - Optional configuration
     * @param {boolean} options.spinner - Show spinner (default: true)
     * @param {boolean} options.backdrop - Show backdrop (default: true)
     * @param {string} options.size - Spinner size: 'sm', 'md', 'lg' (default: 'md')
     */
    show(message = 'Loading...', options = {}) {
        // Don't show if already showing
        if (this.isShowing) {
            this.updateMessage(message);
            return;
        }

        const {
            spinner = true,
            backdrop = true,
            size = 'md'
        } = options;

        // Create overlay
        const overlay = document.createElement('div');
        overlay.id = this.overlayId;
        overlay.className = 'dp-loading-overlay';
        if (backdrop) {
            overlay.classList.add('with-backdrop');
        }

        // Spinner size class
        let spinnerClass = 'spinner-border';
        if (size === 'sm') spinnerClass += ' spinner-border-sm';
        if (size === 'lg') spinnerClass += ' spinner-border-lg';

        // Build HTML
        overlay.innerHTML = `
            <div class="dp-loading-content">
                ${spinner ? `
                    <div class="${spinnerClass} text-primary mb-3" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                ` : ''}
                <div class="dp-loading-message">${this._escapeHtml(message)}</div>
                <div class="dp-loading-progress" style="display: none;">
                    <div class="progress mt-3" style="width: 300px; max-width: 100%;">
                        <div class="progress-bar" role="progressbar"
                             style="width: 0%"
                             aria-valuenow="0"
                             aria-valuemin="0"
                             aria-valuemax="100">0%</div>
                    </div>
                </div>
            </div>
        `;

        // Add to DOM
        document.body.appendChild(overlay);
        this.currentOverlay = overlay;
        this.isShowing = true;

        // Prevent body scroll
        document.body.style.overflow = 'hidden';

        // Fade in animation
        requestAnimationFrame(() => {
            overlay.classList.add('show');
        });
    }

    /**
     * Show loading with progress bar
     * @param {string} message - Message to display
     * @param {number} current - Current progress value
     * @param {number} total - Total progress value
     */
    showProgress(message = 'Loading...', current = 0, total = 100) {
        this.show(message, { spinner: false });

        if (this.currentOverlay) {
            const progressContainer = this.currentOverlay.querySelector('.dp-loading-progress');
            if (progressContainer) {
                progressContainer.style.display = 'block';
                this.updateProgress(current, total);
            }
        }
    }

    /**
     * Update progress bar
     * @param {number} current - Current progress value
     * @param {number} total - Total progress value (optional, uses previous if not provided)
     */
    updateProgress(current, total = 100) {
        if (!this.currentOverlay) return;

        const progressBar = this.currentOverlay.querySelector('.progress-bar');
        if (progressBar) {
            const percentage = Math.round((current / total) * 100);
            progressBar.style.width = `${percentage}%`;
            progressBar.setAttribute('aria-valuenow', percentage);
            progressBar.textContent = `${percentage}%`;
        }
    }

    /**
     * Update loading message
     * @param {string} message - New message
     */
    updateMessage(message) {
        if (!this.currentOverlay) return;

        const messageEl = this.currentOverlay.querySelector('.dp-loading-message');
        if (messageEl) {
            messageEl.textContent = message;
        }
    }

    /**
     * Hide loading overlay
     */
    hide() {
        if (!this.currentOverlay) return;

        // Fade out animation
        this.currentOverlay.classList.remove('show');

        // Remove after animation
        setTimeout(() => {
            if (this.currentOverlay && this.currentOverlay.parentNode) {
                this.currentOverlay.parentNode.removeChild(this.currentOverlay);
            }
            this.currentOverlay = null;
            this.isShowing = false;

            // Restore body scroll
            document.body.style.overflow = '';
        }, 300);
    }

    /**
     * Show loading for a promise
     * @param {Promise} promise - Promise to wait for
     * @param {string} message - Loading message
     * @returns {Promise} - Original promise result
     *
     * Usage:
     *   const result = await LoadingManager.wrap(
     *     fetch('/api/save/').then(r => r.json()),
     *     'Menyimpan data...'
     *   );
     */
    async wrap(promise, message = 'Loading...') {
        this.show(message);
        try {
            const result = await promise;
            return result;
        } finally {
            this.hide();
        }
    }

    /**
     * Show inline loading indicator for a specific element
     * @param {HTMLElement} element - Target element
     * @param {string} message - Optional message
     * @returns {Function} - Cleanup function
     *
     * Usage:
     *   const hide = LoadingManager.showInline(button, 'Saving...');
     *   await saveData();
     *   hide();
     */
    showInline(element, message = '') {
        if (!element) return () => {};

        // Save original content
        const originalContent = element.innerHTML;
        const originalDisabled = element.disabled;

        // Disable element
        element.disabled = true;

        // Show spinner
        element.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
            ${message || 'Loading...'}
        `;

        // Return cleanup function
        return () => {
            element.innerHTML = originalContent;
            element.disabled = originalDisabled;
        };
    }

    /**
     * Create a button with built-in loading state
     * @param {HTMLElement} button - Button element
     * @param {Function} asyncFn - Async function to execute
     * @param {string} loadingText - Text to show while loading
     *
     * Usage:
     *   const button = document.getElementById('save-btn');
     *   LoadingManager.withButton(button, async () => {
     *     await saveData();
     *   }, 'Menyimpan...');
     */
    withButton(button, asyncFn, loadingText = 'Loading...') {
        if (!button) return;

        button.addEventListener('click', async (e) => {
            e.preventDefault();

            // Save original state
            const originalText = button.textContent;
            const originalDisabled = button.disabled;

            // Set loading state
            button.disabled = true;
            button.innerHTML = `
                <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                ${loadingText}
            `;

            try {
                await asyncFn();
            } catch (error) {
                console.error('Button action failed:', error);
                // Error handling is done by the async function itself
            } finally {
                // Restore original state
                button.textContent = originalText;
                button.disabled = originalDisabled;
            }
        });
    }

    /**
     * Show error overlay with retry option
     * @param {Object} options - Error options
     * @param {string} options.title - Error title
     * @param {string} options.message - Error message
     * @param {Array} options.actions - Array of action buttons
     * @param {Function} options.onClose - Callback when closed
     */
    showError(options = {}) {
        const {
            title = 'Terjadi Kesalahan',
            message = 'Silakan coba lagi',
            actions = [],
            onClose = null
        } = options;

        // Hide any existing overlay
        this.hide();

        // Create error overlay
        const overlay = document.createElement('div');
        overlay.id = this.overlayId;
        overlay.className = 'dp-loading-overlay with-backdrop show';

        // Build action buttons HTML
        let actionsHtml = '';
        if (actions.length > 0) {
            actionsHtml = '<div class="mt-4 d-flex gap-2 justify-content-center">';
            actions.forEach((action, index) => {
                const btnClass = action.primary ? 'btn-primary' : 'btn-outline-secondary';
                actionsHtml += `
                    <button type="button"
                            class="btn ${btnClass}"
                            data-action-index="${index}">
                        ${this._escapeHtml(action.label)}
                    </button>
                `;
            });
            actionsHtml += '</div>';
        } else {
            // Default close button
            actionsHtml = `
                <div class="mt-4">
                    <button type="button" class="btn btn-primary" data-action="close">
                        Tutup
                    </button>
                </div>
            `;
        }

        overlay.innerHTML = `
            <div class="dp-loading-content">
                <div class="text-danger mb-3">
                    <i class="bi bi-exclamation-triangle-fill" style="font-size: 3rem;"></i>
                </div>
                <h5 class="mb-3">${this._escapeHtml(title)}</h5>
                <div class="dp-loading-message">${this._escapeHtml(message)}</div>
                ${actionsHtml}
            </div>
        `;

        // Add to DOM
        document.body.appendChild(overlay);
        this.currentOverlay = overlay;
        this.isShowing = true;

        // Prevent body scroll
        document.body.style.overflow = 'hidden';

        // Attach action handlers
        if (actions.length > 0) {
            overlay.querySelectorAll('[data-action-index]').forEach((btn) => {
                const index = parseInt(btn.dataset.actionIndex);
                const action = actions[index];
                btn.addEventListener('click', () => {
                    if (action.onClick) {
                        action.onClick();
                    }
                    if (action.closeAfter !== false) {
                        this.hide();
                        if (onClose) onClose();
                    }
                });
            });
        } else {
            overlay.querySelector('[data-action="close"]')?.addEventListener('click', () => {
                this.hide();
                if (onClose) onClose();
            });
        }
    }

    /**
     * Escape HTML to prevent XSS
     * @private
     */
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Create singleton instance
const loadingManager = new LoadingManager();

// Export as default
export default loadingManager;

// Also export class for custom instances
export { LoadingManager };
