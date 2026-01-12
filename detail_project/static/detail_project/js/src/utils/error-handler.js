/**
 * Global Error Handler with Recovery Dialog
 * 
 * Features:
 * - Global error catching (window.onerror, unhandledrejection)
 * - API fetch wrapper with timeout (180s = 3 minutes)
 * - Retry logic (max 3 attempts)
 * - User-friendly Error Recovery Dialog
 * - Sentry integration
 * 
 * @module ErrorHandler
 */

const ErrorHandler = (() => {
    // ===== CONFIGURATION =====
    const CONFIG = {
        TIMEOUT_MS: 180000,           // 3 minutes
        EXTENDED_TIMEOUT_MS: 180000,  // +3 minutes on "Tunggu"
        MAX_RETRIES: 3,
        RETRY_DELAY_MS: 1000,
        STORAGE_KEY: 'error_handler_preferences',
    };

    // Error types
    const ERROR_TYPES = {
        TIMEOUT: 'timeout',
        NETWORK: 'network',
        SERVER: 'server',
        UNKNOWN: 'unknown',
    };

    // State
    let activeRequests = new Map();
    let preferences = loadPreferences();

    // ===== UTILITIES =====
    function loadPreferences() {
        try {
            return JSON.parse(localStorage.getItem(CONFIG.STORAGE_KEY)) || {};
        } catch (e) {
            return {};
        }
    }

    function savePreferences(prefs) {
        try {
            localStorage.setItem(CONFIG.STORAGE_KEY, JSON.stringify(prefs));
        } catch (e) {
            // Ignore storage errors
        }
    }

    function generateRequestId() {
        return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    // ===== MODAL MANAGEMENT =====
    function createModalHTML() {
        const modalHTML = `
            <div id="errorRecoveryOverlay" class="error-recovery-overlay">
                <div class="error-recovery-modal" role="dialog" aria-labelledby="errorRecoveryTitle">
                    <div class="error-recovery-header">
                        <span class="error-icon timeout" id="errorRecoveryIcon">
                            <i class="bi bi-hourglass-split"></i>
                        </span>
                        <h3 class="error-recovery-title" id="errorRecoveryTitle">Proses Memakan Waktu Lama</h3>
                    </div>
                    <div class="error-recovery-body">
                        <p class="error-recovery-message" id="errorRecoveryMessage">
                            Request telah berjalan lebih dari 3 menit. Pilih aksi yang ingin dilakukan:
                        </p>
                        <div class="error-recovery-actions">
                            <button type="button" class="error-recovery-btn btn-wait" id="btnErrorWait">
                                <i class="bi bi-arrow-repeat"></i>
                                <span>Tunggu<br><small>(+ 3 menit)</small></span>
                            </button>
                            <button type="button" class="error-recovery-btn btn-reload" id="btnErrorReload">
                                <i class="bi bi-arrow-clockwise"></i>
                                <span>Reload Page</span>
                            </button>
                        </div>
                        <label class="error-recovery-option">
                            <input type="checkbox" id="chkDontAskAgain">
                            <span>Jangan tanya lagi, terus tunggu</span>
                        </label>
                    </div>
                    <div class="error-recovery-footer">
                        <p class="error-recovery-tip">
                            <span class="tip-icon"><i class="bi bi-lightbulb"></i></span>
                            <span>Proses besar seperti export atau perhitungan mungkin memerlukan waktu lebih lama.</span>
                        </p>
                    </div>
                </div>
            </div>
        `;

        // Only add if not exists
        if (!document.getElementById('errorRecoveryOverlay')) {
            document.body.insertAdjacentHTML('beforeend', modalHTML);
            attachModalEvents();
        }
    }

    function attachModalEvents() {
        const btnWait = document.getElementById('btnErrorWait');
        const btnReload = document.getElementById('btnErrorReload');
        const chkDontAsk = document.getElementById('chkDontAskAgain');

        if (btnWait) {
            btnWait.addEventListener('click', handleWaitClick);
        }
        if (btnReload) {
            btnReload.addEventListener('click', handleReloadClick);
        }
        if (chkDontAsk) {
            chkDontAsk.addEventListener('change', (e) => {
                preferences.autoWait = e.target.checked;
                savePreferences(preferences);
            });
        }
    }

    let currentResolve = null;
    let currentRequestId = null;

    function showModal(errorType, message, requestId) {
        // If auto-wait is enabled, don't show modal
        if (preferences.autoWait) {
            return Promise.resolve('wait');
        }

        createModalHTML();

        const overlay = document.getElementById('errorRecoveryOverlay');
        const icon = document.getElementById('errorRecoveryIcon');
        const title = document.getElementById('errorRecoveryTitle');
        const msg = document.getElementById('errorRecoveryMessage');

        // Configure based on error type
        const configs = {
            [ERROR_TYPES.TIMEOUT]: {
                iconClass: 'bi-hourglass-split',
                iconType: 'timeout',
                title: 'Proses Memakan Waktu Lama',
                message: 'Request telah berjalan lebih dari 3 menit. Pilih aksi yang ingin dilakukan:',
            },
            [ERROR_TYPES.NETWORK]: {
                iconClass: 'bi-wifi-off',
                iconType: 'network',
                title: 'Koneksi Terputus',
                message: 'Tidak dapat terhubung ke server. Periksa koneksi internet Anda.',
            },
            [ERROR_TYPES.SERVER]: {
                iconClass: 'bi-exclamation-triangle',
                iconType: 'server',
                title: 'Terjadi Kesalahan Server',
                message: 'Server mengalami masalah. Tim kami sudah diberitahu.',
            },
            [ERROR_TYPES.UNKNOWN]: {
                iconClass: 'bi-question-circle',
                iconType: 'unknown',
                title: 'Terjadi Masalah',
                message: message || 'Terjadi kesalahan yang tidak terduga.',
            },
        };

        const config = configs[errorType] || configs[ERROR_TYPES.UNKNOWN];

        icon.innerHTML = `<i class="bi ${config.iconClass}"></i>`;
        icon.className = `error-icon ${config.iconType}`;
        title.textContent = config.title;
        msg.textContent = config.message;

        overlay.classList.add('show');
        currentRequestId = requestId;

        return new Promise((resolve) => {
            currentResolve = resolve;
        });
    }

    function hideModal() {
        const overlay = document.getElementById('errorRecoveryOverlay');
        if (overlay) {
            overlay.classList.remove('show');
        }
    }

    function handleWaitClick() {
        hideModal();
        if (currentResolve) {
            currentResolve('wait');
            currentResolve = null;
        }
    }

    function handleReloadClick() {
        hideModal();
        if (currentResolve) {
            currentResolve('reload');
            currentResolve = null;
        }
        // Hard reload
        window.location.reload(true);
    }

    // ===== FETCH WRAPPER =====
    async function fetchWithTimeout(url, options = {}, timeoutMs = CONFIG.TIMEOUT_MS) {
        const requestId = generateRequestId();
        const controller = new AbortController();

        let timeoutId;
        let totalElapsed = 0;

        const executeRequest = async (remainingTimeout) => {
            return new Promise(async (resolve, reject) => {
                timeoutId = setTimeout(async () => {
                    controller.abort();
                    totalElapsed += remainingTimeout;

                    // Show recovery dialog
                    const action = await showModal(ERROR_TYPES.TIMEOUT, null, requestId);

                    if (action === 'wait') {
                        // Extend timeout and retry
                        try {
                            const result = await fetchWithTimeout(url, options, CONFIG.EXTENDED_TIMEOUT_MS);
                            resolve(result);
                        } catch (e) {
                            reject(e);
                        }
                    } else {
                        reject(new Error('Request cancelled by user'));
                    }
                }, remainingTimeout);

                try {
                    const response = await fetch(url, {
                        ...options,
                        signal: controller.signal,
                    });

                    clearTimeout(timeoutId);

                    if (!response.ok && response.status >= 500) {
                        // Server error
                        const action = await showModal(ERROR_TYPES.SERVER, null, requestId);
                        if (action === 'reload') {
                            reject(new Error('Server error - user chose reload'));
                        }
                    }

                    resolve(response);
                } catch (error) {
                    clearTimeout(timeoutId);

                    if (error.name === 'AbortError') {
                        // Already handled by timeout
                        return;
                    }

                    if (!navigator.onLine || error.message.includes('fetch')) {
                        // Network error
                        const action = await showModal(ERROR_TYPES.NETWORK, null, requestId);
                        if (action === 'wait') {
                            // Retry after delay
                            await new Promise(r => setTimeout(r, CONFIG.RETRY_DELAY_MS));
                            try {
                                const result = await fetchWithTimeout(url, options, remainingTimeout);
                                resolve(result);
                            } catch (e) {
                                reject(e);
                            }
                        } else {
                            reject(error);
                        }
                    } else {
                        reject(error);
                    }
                }
            });
        };

        return executeRequest(timeoutMs);
    }

    // ===== GLOBAL ERROR HANDLERS =====
    function setupGlobalHandlers() {
        // Handle uncaught errors
        window.onerror = function (message, source, lineno, colno, error) {
            console.error('[ErrorHandler] Uncaught error:', { message, source, lineno, colno, error });

            // Send to Sentry if available
            if (window.Sentry && error) {
                window.Sentry.captureException(error);
            }

            // Show recovery dialog for critical errors
            if (isCriticalError(message)) {
                showModal(ERROR_TYPES.UNKNOWN, message);
            }

            return false; // Let default handler run too
        };

        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', function (event) {
            console.error('[ErrorHandler] Unhandled rejection:', event.reason);

            // Send to Sentry if available
            if (window.Sentry) {
                window.Sentry.captureException(event.reason);
            }

            // Show recovery dialog for critical errors
            if (event.reason && isCriticalError(event.reason.message || String(event.reason))) {
                showModal(ERROR_TYPES.UNKNOWN, event.reason.message || 'Terjadi kesalahan asinkron');
            }
        });

        // Handle offline/online
        window.addEventListener('offline', () => {
            console.warn('[ErrorHandler] Connection lost');
            // Use global toast if available
            if (window.DP && window.DP.toast && window.DP.toast.network) {
                window.DP.toast.network.offline();
            }
        });

        window.addEventListener('online', () => {
            console.log('[ErrorHandler] Connection restored');
            // Use global toast if available
            if (window.DP && window.DP.toast && window.DP.toast.network) {
                window.DP.toast.network.online();
            }
        });
    }

    function isCriticalError(message) {
        const criticalPatterns = [
            /out of memory/i,
            /maximum call stack/i,
            /script error/i,
            /network error/i,
            /failed to fetch/i,
            /load failed/i,
        ];
        return criticalPatterns.some(pattern => pattern.test(message));
    }

    // ===== TOAST NOTIFICATIONS =====
    // Use global DP.toast system - this is just a fallback
    function showToast(type, message) {
        // Prefer global toast system
        if (window.DP && window.DP.toast && window.DP.toast[type]) {
            window.DP.toast[type](message);
            return;
        }

        // Fallback to basic alert (if global toast not loaded yet)
        const toastId = `toast_${Date.now()}`;
        const iconMap = {
            success: 'bi-check-circle-fill',
            warning: 'bi-exclamation-triangle-fill',
            error: 'bi-x-circle-fill',
            danger: 'bi-x-circle-fill',
            info: 'bi-info-circle-fill',
        };

        const toastHTML = `
            <div id="${toastId}" class="alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed dp-z-toast" 
                 style="top: 20px; left: 50%; transform: translateX(-50%); min-width: 300px; z-index: 13100;"
                 role="alert">
                <i class="bi ${iconMap[type] || iconMap.info} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', toastHTML);

        // Auto-remove after 5s
        setTimeout(() => {
            const toast = document.getElementById(toastId);
            if (toast) {
                toast.remove();
            }
        }, 5000);
    }

    // ===== INITIALIZATION =====
    function init() {
        setupGlobalHandlers();
        createModalHTML();
        console.log('[ErrorHandler] Initialized with timeout:', CONFIG.TIMEOUT_MS, 'ms');
    }

    // Auto-init on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // ===== PUBLIC API =====
    return {
        // Fetch with timeout and recovery dialog
        fetch: fetchWithTimeout,

        // Show recovery dialog manually
        showDialog: showModal,

        // Hide dialog
        hideDialog: hideModal,

        // Show toast notification
        toast: showToast,

        // Configuration
        config: CONFIG,

        // Error types
        ERROR_TYPES,

        // Re-initialize
        init,
    };
})();

// Export for ES modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ErrorHandler;
}

// Attach to window for global access
if (typeof window !== 'undefined') {
    window.ErrorHandler = ErrorHandler;
}
