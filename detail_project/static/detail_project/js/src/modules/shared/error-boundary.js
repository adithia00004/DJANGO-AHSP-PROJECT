/**
 * ErrorBoundary - Global error handling and user-friendly error messages
 *
 * Provides:
 * - Try-catch wrappers for async functions
 * - Fallback UI for critical errors
 * - Error logging and reporting
 * - User-friendly error messages
 *
 * @module ErrorBoundary
 */

import { Toast } from './ux-enhancements.js';

const LOG_PREFIX = '[ErrorBoundary]';

/**
 * Error severity levels
 * @enum {string}
 */
export const ErrorLevel = {
  INFO: 'info',
  WARNING: 'warning',
  ERROR: 'error',
  CRITICAL: 'critical'
};

/**
 * User-friendly error messages
 * @type {Object<string, string>}
 */
const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Koneksi ke server terputus. Periksa koneksi internet Anda.',
  TIMEOUT_ERROR: 'Permintaan memakan waktu terlalu lama. Coba lagi.',
  VALIDATION_ERROR: 'Data yang dimasukkan tidak valid. Periksa kembali.',
  PERMISSION_ERROR: 'Anda tidak memiliki izin untuk melakukan tindakan ini.',
  NOT_FOUND_ERROR: 'Data yang diminta tidak ditemukan.',
  SERVER_ERROR: 'Terjadi kesalahan pada server. Tim kami telah diberitahu.',
  UNKNOWN_ERROR: 'Terjadi kesalahan yang tidak terduga. Silakan coba lagi.',
  DATA_LOAD_ERROR: 'Gagal memuat data. Silakan refresh halaman.',
  SAVE_ERROR: 'Gagal menyimpan perubahan. Pastikan data valid dan coba lagi.',
  CHART_RENDER_ERROR: 'Gagal menampilkan grafik. Data mungkin tidak lengkap.'
};

/**
 * Map HTTP status codes to user-friendly messages
 * @param {number} statusCode - HTTP status code
 * @returns {string} User-friendly message
 */
function getMessageForStatusCode(statusCode) {
  if (statusCode >= 400 && statusCode < 500) {
    switch (statusCode) {
      case 401:
      case 403:
        return ERROR_MESSAGES.PERMISSION_ERROR;
      case 404:
        return ERROR_MESSAGES.NOT_FOUND_ERROR;
      case 408:
        return ERROR_MESSAGES.TIMEOUT_ERROR;
      case 422:
        return ERROR_MESSAGES.VALIDATION_ERROR;
      default:
        return ERROR_MESSAGES.UNKNOWN_ERROR;
    }
  }

  if (statusCode >= 500) {
    return ERROR_MESSAGES.SERVER_ERROR;
  }

  return ERROR_MESSAGES.UNKNOWN_ERROR;
}

/**
 * Extract user-friendly error message from error object
 * @param {Error} error - Error object
 * @param {string} context - Error context (e.g., 'data-load', 'save', 'chart-render')
 * @returns {string} User-friendly message
 */
export function getUserFriendlyMessage(error, context = 'unknown') {
  // Network errors
  if (error.name === 'NetworkError' || error.message.includes('network')) {
    return ERROR_MESSAGES.NETWORK_ERROR;
  }

  // Timeout errors
  if (error.name === 'TimeoutError' || error.message.includes('timeout')) {
    return ERROR_MESSAGES.TIMEOUT_ERROR;
  }

  // HTTP errors with status code
  if (error.response?.status) {
    return getMessageForStatusCode(error.response.status);
  }

  // Context-specific errors
  const contextMessages = {
    'data-load': ERROR_MESSAGES.DATA_LOAD_ERROR,
    'save': ERROR_MESSAGES.SAVE_ERROR,
    'chart-render': ERROR_MESSAGES.CHART_RENDER_ERROR,
    'validation': ERROR_MESSAGES.VALIDATION_ERROR
  };

  if (contextMessages[context]) {
    return contextMessages[context];
  }

  // Fallback to generic message
  return ERROR_MESSAGES.UNKNOWN_ERROR;
}

/**
 * Log error with context and severity
 * @param {Error} error - Error object
 * @param {string} context - Error context
 * @param {ErrorLevel} level - Error severity level
 * @param {Object} metadata - Additional metadata
 */
export function logError(error, context = 'unknown', level = ErrorLevel.ERROR, metadata = {}) {
  const errorData = {
    message: error.message,
    stack: error.stack,
    context,
    level,
    timestamp: new Date().toISOString(),
    ...metadata
  };

  // Log to console
  if (level === ErrorLevel.CRITICAL || level === ErrorLevel.ERROR) {
    console.error(LOG_PREFIX, 'Error occurred:', errorData);
  } else if (level === ErrorLevel.WARNING) {
    console.warn(LOG_PREFIX, 'Warning:', errorData);
  } else {
    console.info(LOG_PREFIX, 'Info:', errorData);
  }

  // TODO: Send to error tracking service (Sentry, etc.)
  // if (window.Sentry && level !== ErrorLevel.INFO) {
  //   window.Sentry.captureException(error, {
  //     level: level,
  //     tags: { context },
  //     extra: metadata
  //   });
  // }
}

/**
 * Wrap an async function with error handling
 *
 * @param {Function} fn - Async function to wrap
 * @param {Object} options - Error handling options
 * @param {string} options.context - Error context
 * @param {ErrorLevel} options.level - Error severity level
 * @param {boolean} options.showToast - Show toast notification
 * @param {Function} options.fallback - Fallback function on error
 * @param {boolean} options.rethrow - Rethrow error after handling
 * @returns {Function} Wrapped function
 *
 * @example
 * const safeLoadData = withErrorBoundary(
 *   async () => await fetchData(),
 *   { context: 'data-load', showToast: true }
 * );
 */
export function withErrorBoundary(fn, options = {}) {
  const {
    context = 'unknown',
    level = ErrorLevel.ERROR,
    showToast = true,
    fallback = null,
    rethrow = false
  } = options;

  return async (...args) => {
    try {
      return await fn(...args);
    } catch (error) {
      // Log error
      logError(error, context, level);

      // Show user-friendly message
      if (showToast) {
        const message = getUserFriendlyMessage(error, context);
        const toastType = level === ErrorLevel.CRITICAL ? 'danger' :
                         level === ErrorLevel.ERROR ? 'danger' :
                         level === ErrorLevel.WARNING ? 'warning' : 'info';
        Toast.show(message, toastType, 4000);
      }

      // Execute fallback if provided
      if (fallback && typeof fallback === 'function') {
        try {
          return await fallback(error);
        } catch (fallbackError) {
          console.error(LOG_PREFIX, 'Fallback failed:', fallbackError);
        }
      }

      // Rethrow if requested
      if (rethrow) {
        throw error;
      }

      return null;
    }
  };
}

/**
 * Create an error boundary for a component/module
 *
 * @param {string} componentName - Component name
 * @returns {Object} Error boundary methods
 *
 * @example
 * const boundary = createErrorBoundary('DataLoader');
 * boundary.wrap(async () => await loadData())();
 */
export function createErrorBoundary(componentName) {
  return {
    /**
     * Wrap function with component-specific error boundary
     * @param {Function} fn - Function to wrap
     * @param {Object} options - Error handling options
     * @returns {Function} Wrapped function
     */
    wrap: (fn, options = {}) => {
      return withErrorBoundary(fn, {
        context: componentName,
        ...options
      });
    },

    /**
     * Log error for this component
     * @param {Error} error - Error object
     * @param {ErrorLevel} level - Error severity
     * @param {Object} metadata - Additional metadata
     */
    logError: (error, level = ErrorLevel.ERROR, metadata = {}) => {
      logError(error, componentName, level, metadata);
    },

    /**
     * Show error toast for this component
     * @param {Error} error - Error object
     * @param {string} customMessage - Custom message (optional)
     */
    showError: (error, customMessage = null) => {
      const message = customMessage || getUserFriendlyMessage(error, componentName);
      Toast.show(message, 'danger', 4000);
      logError(error, componentName, ErrorLevel.ERROR);
    }
  };
}

/**
 * Global unhandled error handler
 */
export function setupGlobalErrorHandler() {
  // Handle unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    console.error(LOG_PREFIX, 'Unhandled promise rejection:', event.reason);
    logError(
      event.reason instanceof Error ? event.reason : new Error(String(event.reason)),
      'unhandled-rejection',
      ErrorLevel.CRITICAL
    );

    // Prevent default console error
    event.preventDefault();

    // Show user-friendly message
    Toast.show(
      'Terjadi kesalahan yang tidak terduga. Halaman akan di-refresh.',
      'danger',
      5000
    );
  });

  // Handle uncaught errors
  window.addEventListener('error', (event) => {
    console.error(LOG_PREFIX, 'Uncaught error:', event.error);
    logError(
      event.error || new Error(event.message),
      'uncaught-error',
      ErrorLevel.CRITICAL,
      {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno
      }
    );
  });

  console.log(LOG_PREFIX, 'Global error handlers installed');
}

export default {
  ErrorLevel,
  getUserFriendlyMessage,
  logError,
  withErrorBoundary,
  createErrorBoundary,
  setupGlobalErrorHandler
};
