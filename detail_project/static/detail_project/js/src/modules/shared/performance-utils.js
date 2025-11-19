/**
 * Performance Utilities Module
 * Provides debounce, throttle, and requestAnimationFrame helpers
 * License: MIT
 */

/**
 * Debounces a function - delays execution until after wait time has elapsed
 * since the last call. Useful for input events, window resize.
 *
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @param {boolean} immediate - Execute on leading edge instead of trailing
 * @returns {Function} Debounced function
 *
 * @example
 * const debouncedSearch = debounce((query) => {
 *   console.log('Searching for:', query);
 * }, 300);
 *
 * input.addEventListener('input', (e) => debouncedSearch(e.target.value));
 */
export function debounce(func, wait, immediate = false) {
  let timeout;

  const debounced = function (...args) {
    const context = this;

    const later = () => {
      timeout = null;
      if (!immediate) {
        func.apply(context, args);
      }
    };

    const callNow = immediate && !timeout;

    clearTimeout(timeout);
    timeout = setTimeout(later, wait);

    if (callNow) {
      func.apply(context, args);
    }
  };

  // Cancel method to clear pending execution
  debounced.cancel = () => {
    clearTimeout(timeout);
    timeout = null;
  };

  return debounced;
}

/**
 * Throttles a function - ensures it's called at most once per specified time period.
 * Useful for scroll events, mousemove.
 *
 * @param {Function} func - Function to throttle
 * @param {number} limit - Minimum time between calls in milliseconds
 * @param {Object} options - Configuration options
 * @param {boolean} options.leading - Execute on leading edge (default: true)
 * @param {boolean} options.trailing - Execute on trailing edge (default: true)
 * @returns {Function} Throttled function
 *
 * @example
 * const throttledScroll = throttle(() => {
 *   console.log('Scroll position:', window.scrollY);
 * }, 16); // ~60fps
 *
 * window.addEventListener('scroll', throttledScroll);
 */
export function throttle(func, limit, options = {}) {
  const { leading = true, trailing = true } = options;

  let inThrottle;
  let lastFunc;
  let lastRan;

  const throttled = function (...args) {
    const context = this;

    if (!inThrottle) {
      if (leading) {
        func.apply(context, args);
        lastRan = Date.now();
      }
      inThrottle = true;
    } else {
      clearTimeout(lastFunc);
      lastFunc = setTimeout(() => {
        if (Date.now() - lastRan >= limit) {
          if (trailing) {
            func.apply(context, args);
          }
          lastRan = Date.now();
        }
      }, Math.max(limit - (Date.now() - lastRan), 0));
    }

    setTimeout(() => {
      inThrottle = false;
    }, limit);
  };

  // Cancel method to clear pending execution
  throttled.cancel = () => {
    clearTimeout(lastFunc);
    inThrottle = false;
  };

  return throttled;
}

/**
 * requestAnimationFrame-based throttle for smooth animations
 * Ensures function is called at most once per animation frame (~60fps)
 *
 * @param {Function} func - Function to throttle
 * @returns {Function} RAF-throttled function
 *
 * @example
 * const rafScroll = rafThrottle(() => {
 *   // Sync scroll positions
 *   rightContainer.scrollLeft = leftContainer.scrollLeft;
 * });
 *
 * leftContainer.addEventListener('scroll', rafScroll);
 */
export function rafThrottle(func) {
  let rafId = null;
  let lastArgs = null;

  const throttled = function (...args) {
    lastArgs = args;

    if (rafId === null) {
      rafId = requestAnimationFrame(() => {
        func.apply(this, lastArgs);
        rafId = null;
        lastArgs = null;
      });
    }
  };

  // Cancel method to clear pending execution
  throttled.cancel = () => {
    if (rafId !== null) {
      cancelAnimationFrame(rafId);
      rafId = null;
      lastArgs = null;
    }
  };

  return throttled;
}

/**
 * Batches multiple synchronous DOM reads/writes to prevent layout thrashing
 *
 * @param {Function} readFunc - Function that reads from DOM
 * @param {Function} writeFunc - Function that writes to DOM
 *
 * @example
 * batchDOMOperations(
 *   () => {
 *     // Read phase
 *     const width = element.offsetWidth;
 *     return { width };
 *   },
 *   (readResults) => {
 *     // Write phase
 *     element.style.height = readResults.width + 'px';
 *   }
 * );
 */
export function batchDOMOperations(readFunc, writeFunc) {
  requestAnimationFrame(() => {
    const readResults = readFunc();

    requestAnimationFrame(() => {
      writeFunc(readResults);
    });
  });
}

/**
 * Creates a performance monitor for measuring execution time
 *
 * @param {string} label - Label for the measurement
 * @returns {Object} Monitor object with start/end methods
 *
 * @example
 * const monitor = createPerformanceMonitor('Grid Render');
 * monitor.start();
 * // ... expensive operation
 * const duration = monitor.end(); // Returns duration in ms
 */
export function createPerformanceMonitor(label) {
  let startTime = null;

  return {
    start() {
      startTime = performance.now();
      if (typeof performance.mark === 'function') {
        performance.mark(`${label}-start`);
      }
    },

    end() {
      if (startTime === null) {
        console.warn(`Performance monitor "${label}" was not started`);
        return 0;
      }

      const endTime = performance.now();
      const duration = endTime - startTime;

      if (typeof performance.mark === 'function') {
        performance.mark(`${label}-end`);
        performance.measure(label, `${label}-start`, `${label}-end`);
      }

      console.log(`⏱️ ${label}: ${duration.toFixed(2)}ms`);
      startTime = null;

      return duration;
    },

    cancel() {
      startTime = null;
    },
  };
}

/**
 * Idle callback wrapper with fallback for browsers that don't support it
 *
 * @param {Function} callback - Function to execute when idle
 * @param {Object} options - Configuration options
 * @param {number} options.timeout - Maximum wait time in ms
 *
 * @example
 * requestIdleCallback(() => {
 *   // Perform non-critical work during idle time
 *   preloadNextPageData();
 * }, { timeout: 2000 });
 */
export function requestIdleCallback(callback, options = {}) {
  if (typeof window.requestIdleCallback === 'function') {
    return window.requestIdleCallback(callback, options);
  }

  // Fallback for browsers without requestIdleCallback
  const timeout = options.timeout || 1;
  const start = Date.now();

  return setTimeout(() => {
    callback({
      didTimeout: false,
      timeRemaining: () => Math.max(0, 50 - (Date.now() - start)),
    });
  }, timeout);
}

/**
 * Cancels an idle callback
 *
 * @param {number} id - ID returned from requestIdleCallback
 */
export function cancelIdleCallback(id) {
  if (typeof window.cancelIdleCallback === 'function') {
    window.cancelIdleCallback(id);
  } else {
    clearTimeout(id);
  }
}
