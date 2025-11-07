/**
 * Toast Wrapper - Convenience Methods for DP.core.toast
 *
 * Provides ES6 module exports with convenience methods for the existing
 * DP.core.toast system, making it easier to use from modern JS modules.
 *
 * Usage:
 *   import toast from '/static/detail_project/js/core/toast-wrapper.js';
 *
 *   toast.success('Data berhasil disimpan');
 *   toast.error('Terjadi kesalahan');
 *   toast.warning('Peringatan: data tidak lengkap');
 *   toast.info('Informasi: proses sedang berjalan');
 *
 * This wrapper ensures compatibility between:
 * - Old code: DP.core.toast.show(msg, 'success')
 * - New code: toast.success(msg)
 */

/**
 * Wait for DP.core.toast to be available
 * @returns {Promise} Resolves when toast system is ready
 */
function waitForToast() {
    return new Promise((resolve) => {
        if (window.DP?.core?.toast) {
            resolve(window.DP.core.toast);
            return;
        }

        // Poll for toast availability (max 5 seconds)
        let attempts = 0;
        const maxAttempts = 50;
        const interval = setInterval(() => {
            attempts++;
            if (window.DP?.core?.toast) {
                clearInterval(interval);
                resolve(window.DP.core.toast);
            } else if (attempts >= maxAttempts) {
                clearInterval(interval);
                console.error('DP.core.toast not available after 5 seconds');
                // Provide fallback
                resolve({
                    show: (msg) => console.log('[Toast Fallback]', msg),
                    clear: () => {},
                    setMax: () => {}
                });
            }
        }, 100);
    });
}

/**
 * Get toast system (synchronous)
 * Falls back to console if not available
 */
function getToast() {
    if (window.DP?.core?.toast) {
        return window.DP.core.toast;
    }

    // Fallback for when toast.js hasn't loaded yet
    console.warn('DP.core.toast not available, using fallback');
    return {
        show: (msg, variant) => {
            console.log(`[Toast ${variant}]`, msg);
        },
        clear: () => {},
        setMax: () => {}
    };
}

/**
 * Toast wrapper object with convenience methods
 */
const toast = {
    /**
     * Show success message
     * @param {string} message - Message to display
     * @param {number} duration - Duration in ms (default: 1600)
     * @returns {HTMLElement} Toast element
     */
    success(message, duration = 1600) {
        const t = getToast();
        return t.show(message, 'success', duration);
    },

    /**
     * Show error message
     * @param {string} message - Error message to display
     * @param {number} duration - Duration in ms (default: 3000)
     * @returns {HTMLElement} Toast element
     */
    error(message, duration = 3000) {
        const t = getToast();
        return t.show(message, 'danger', duration);
    },

    /**
     * Show warning message
     * @param {string} message - Warning message to display
     * @param {number} duration - Duration in ms (default: 2000)
     * @returns {HTMLElement} Toast element
     */
    warning(message, duration = 2000) {
        const t = getToast();
        return t.show(message, 'warning', duration);
    },

    /**
     * Show info message
     * @param {string} message - Info message to display
     * @param {number} duration - Duration in ms (default: 1600)
     * @returns {HTMLElement} Toast element
     */
    info(message, duration = 1600) {
        const t = getToast();
        return t.show(message, 'info', duration);
    },

    /**
     * Show message with custom options
     * @param {Object} options - Toast options
     * @param {string} options.message - Message to display
     * @param {string} options.title - Optional title
     * @param {string} options.variant - Toast variant (success/danger/warning/info)
     * @param {boolean} options.autohide - Auto hide toast (default: true)
     * @param {number} options.delay - Delay in ms (default: 1600)
     * @returns {HTMLElement} Toast element
     */
    show(options) {
        const t = getToast();
        return t.show(options);
    },

    /**
     * Clear all toasts
     */
    clear() {
        const t = getToast();
        t.clear();
    },

    /**
     * Set maximum number of toasts to show at once
     * @param {number} max - Maximum toasts (1-10)
     */
    setMax(max) {
        const t = getToast();
        t.setMax(max);
    },

    /**
     * Wait for toast system to be ready
     * Useful for code that runs very early in page lifecycle
     * @returns {Promise} Resolves when toast is ready
     */
    async ready() {
        await waitForToast();
        return this;
    }
};

// Also expose waitForToast for advanced usage
export { waitForToast };

// Default export
export default toast;

// For backwards compatibility with older bundlers
if (typeof module !== 'undefined' && module.exports) {
    module.exports = toast;
    module.exports.default = toast;
    module.exports.waitForToast = waitForToast;
}
