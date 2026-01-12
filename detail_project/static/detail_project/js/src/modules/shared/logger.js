/**
 * Logger - Centralized logging system with level control
 *
 * Provides:
 * - Log level filtering (DEBUG, INFO, WARN, ERROR)
 * - Context-aware logging
 * - Colored console output
 * - Performance timing utilities
 * - Production vs development mode handling
 *
 * @module Logger
 */

/**
 * Log levels (in order of severity)
 * @enum {number}
 */
export const LogLevel = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
  NONE: 4
};

/**
 * Log level names for display
 * @type {Object<number, string>}
 */
const LEVEL_NAMES = {
  [LogLevel.DEBUG]: 'DEBUG',
  [LogLevel.INFO]: 'INFO',
  [LogLevel.WARN]: 'WARN',
  [LogLevel.ERROR]: 'ERROR'
};

/**
 * Console colors for different log levels
 * @type {Object<number, string>}
 */
const LEVEL_COLORS = {
  [LogLevel.DEBUG]: 'color: #6c757d',      // gray
  [LogLevel.INFO]: 'color: #0d6efd',       // blue
  [LogLevel.WARN]: 'color: #ffc107',       // yellow
  [LogLevel.ERROR]: 'color: #dc3545'       // red
};

/**
 * Default minimum log level based on environment
 */
const DEFAULT_MIN_LEVEL = (typeof window !== 'undefined' && window.DEBUG) ||
                          (typeof process !== 'undefined' && process.env.NODE_ENV === 'development')
  ? LogLevel.DEBUG
  : LogLevel.WARN;

/**
 * Logger class for context-aware logging
 *
 * @class Logger
 * @example
 * const logger = new Logger('DataLoader');
 * logger.debug('Loading data...', { count: 10 });
 * logger.info('Data loaded successfully');
 * logger.warn('Cache expired');
 * logger.error('Failed to load', error);
 */
export class Logger {
  /**
   * Global minimum log level
   * @type {number}
   * @static
   */
  static minLevel = DEFAULT_MIN_LEVEL;

  /**
   * Performance timers storage
   * @type {Map<string, number>}
   * @static
   * @private
   */
  static _timers = new Map();

  /**
   * Set global minimum log level
   * @param {number} level - Minimum log level
   * @static
   */
  static setMinLevel(level) {
    Logger.minLevel = level;
    console.log(`[Logger] Min level set to: ${LEVEL_NAMES[level] || level}`);
  }

  /**
   * Create a new Logger instance
   * @param {string} context - Logger context (e.g., 'DataLoader', 'ChartCoordinator')
   * @param {Object} options - Logger options
   * @param {number} [options.minLevel] - Instance-specific minimum level (overrides global)
   */
  constructor(context, options = {}) {
    this.context = context;
    this.minLevel = options.minLevel !== undefined ? options.minLevel : Logger.minLevel;
    this._prefix = `[${context}]`;
  }

  /**
   * Log a debug message
   * @param {string} message - Log message
   * @param {...any} args - Additional arguments
   */
  debug(message, ...args) {
    this._log(LogLevel.DEBUG, message, ...args);
  }

  /**
   * Log an info message
   * @param {string} message - Log message
   * @param {...any} args - Additional arguments
   */
  info(message, ...args) {
    this._log(LogLevel.INFO, message, ...args);
  }

  /**
   * Log a warning message
   * @param {string} message - Log message
   * @param {...any} args - Additional arguments
   */
  warn(message, ...args) {
    this._log(LogLevel.WARN, message, ...args);
  }

  /**
   * Log an error message
   * @param {string} message - Log message
   * @param {Error} [error] - Error object
   * @param {...any} args - Additional arguments
   */
  error(message, error = null, ...args) {
    if (error instanceof Error) {
      this._log(LogLevel.ERROR, message, error, ...args);
    } else {
      this._log(LogLevel.ERROR, message, error, ...args);
    }
  }

  /**
   * Start a performance timer
   * @param {string} label - Timer label
   */
  time(label) {
    const key = `${this.context}:${label}`;
    Logger._timers.set(key, performance.now());
    this.debug(`⏱️ Timer started: ${label}`);
  }

  /**
   * End a performance timer and log duration
   * @param {string} label - Timer label
   * @returns {number} Duration in milliseconds
   */
  timeEnd(label) {
    const key = `${this.context}:${label}`;
    const start = Logger._timers.get(key);

    if (start === undefined) {
      this.warn(`Timer "${label}" was not started`);
      return 0;
    }

    const duration = performance.now() - start;
    Logger._timers.delete(key);

    this.debug(`⏱️ Timer ended: ${label} - ${duration.toFixed(2)}ms`);
    return duration;
  }

  /**
   * Log a group (collapsible in console)
   * @param {string} label - Group label
   * @param {Function} fn - Function to execute within group
   */
  group(label, fn) {
    if (this.minLevel > LogLevel.DEBUG) {
      // Skip grouping if debug not enabled
      fn();
      return;
    }

    console.group(`${this._prefix} ${label}`);
    try {
      fn();
    } finally {
      console.groupEnd();
    }
  }

  /**
   * Log a collapsed group
   * @param {string} label - Group label
   * @param {Function} fn - Function to execute within group
   */
  groupCollapsed(label, fn) {
    if (this.minLevel > LogLevel.DEBUG) {
      fn();
      return;
    }

    console.groupCollapsed(`${this._prefix} ${label}`);
    try {
      fn();
    } finally {
      console.groupEnd();
    }
  }

  /**
   * Log a table (for arrays/objects)
   * @param {any} data - Data to display as table
   * @param {string} [label] - Optional label
   */
  table(data, label = null) {
    if (this.minLevel > LogLevel.DEBUG) {
      return;
    }

    if (label) {
      console.log(`${this._prefix} ${label}`);
    }
    console.table(data);
  }

  /**
   * Internal log method
   * @private
   * @param {number} level - Log level
   * @param {string} message - Log message
   * @param {...any} args - Additional arguments
   */
  _log(level, message, ...args) {
    // Check if this log level should be displayed
    if (level < this.minLevel) {
      return;
    }

    const levelName = LEVEL_NAMES[level];
    const color = LEVEL_COLORS[level];
    const timestamp = new Date().toISOString().substr(11, 12);

    // Format: [HH:MM:SS.mmm] [CONTEXT] LEVEL: message
    const prefix = `%c[${timestamp}] ${this._prefix} ${levelName}:`;

    // Use appropriate console method
    switch (level) {
      case LogLevel.DEBUG:
        console.log(prefix, color, message, ...args);
        break;
      case LogLevel.INFO:
        console.info(prefix, color, message, ...args);
        break;
      case LogLevel.WARN:
        console.warn(prefix, color, message, ...args);
        break;
      case LogLevel.ERROR:
        console.error(prefix, color, message, ...args);
        break;
      default:
        console.log(prefix, color, message, ...args);
    }
  }
}

/**
 * Create a logger instance
 * @param {string} context - Logger context
 * @param {Object} options - Logger options
 * @returns {Logger} Logger instance
 *
 * @example
 * const logger = createLogger('MyComponent');
 * logger.info('Component initialized');
 */
export function createLogger(context, options = {}) {
  return new Logger(context, options);
}

/**
 * Quick logging functions for global use
 */
export const log = {
  /**
   * Log debug message
   * @param {string} context - Context
   * @param {string} message - Message
   * @param {...any} args - Arguments
   */
  debug: (context, message, ...args) => {
    const logger = new Logger(context);
    logger.debug(message, ...args);
  },

  /**
   * Log info message
   * @param {string} context - Context
   * @param {string} message - Message
   * @param {...any} args - Arguments
   */
  info: (context, message, ...args) => {
    const logger = new Logger(context);
    logger.info(message, ...args);
  },

  /**
   * Log warning message
   * @param {string} context - Context
   * @param {string} message - Message
   * @param {...any} args - Arguments
   */
  warn: (context, message, ...args) => {
    const logger = new Logger(context);
    logger.warn(message, ...args);
  },

  /**
   * Log error message
   * @param {string} context - Context
   * @param {string} message - Message
   * @param {Error} [error] - Error object
   * @param {...any} args - Arguments
   */
  error: (context, message, error = null, ...args) => {
    const logger = new Logger(context);
    logger.error(message, error, ...args);
  }
};

/**
 * Initialize logger with environment settings
 */
export function setupLogger() {
  // Set min level based on environment
  const isDevelopment = (typeof window !== 'undefined' && window.DEBUG) ||
                       (typeof process !== 'undefined' && process.env.NODE_ENV === 'development');

  Logger.setMinLevel(isDevelopment ? LogLevel.DEBUG : LogLevel.WARN);

  // Expose logger to window for debugging
  if (typeof window !== 'undefined') {
    window.Logger = Logger;
    window.LogLevel = LogLevel;
  }

  console.log(
    '%c[Logger] Initialized',
    'color: #0d6efd; font-weight: bold',
    `(min level: ${LEVEL_NAMES[Logger.minLevel]})`
  );
}

export default {
  Logger,
  LogLevel,
  createLogger,
  log,
  setupLogger
};
