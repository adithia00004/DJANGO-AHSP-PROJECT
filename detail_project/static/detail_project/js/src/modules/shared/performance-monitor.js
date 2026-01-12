/**
 * PerformanceMonitor - Client-side performance tracking and metrics
 *
 * Provides:
 * - Page load timing
 * - API request duration tracking
 * - Component render time measurement
 * - Memory usage monitoring
 * - FPS (frames per second) tracking
 * - Performance marks and measures
 *
 * @module PerformanceMonitor
 */

import { createLogger } from './logger.js';

const logger = createLogger('PerformanceMonitor');

/**
 * Performance threshold configuration
 * @type {Object}
 */
export const THRESHOLDS = {
  // Page load metrics (milliseconds)
  PAGE_LOAD_WARN: 3000,
  PAGE_LOAD_ERROR: 5000,

  // API request metrics (milliseconds)
  API_REQUEST_WARN: 1000,
  API_REQUEST_ERROR: 3000,

  // Component render metrics (milliseconds)
  RENDER_WARN: 100,
  RENDER_ERROR: 300,

  // FPS thresholds
  FPS_WARN: 30,
  FPS_ERROR: 20,

  // Memory thresholds (MB)
  MEMORY_WARN: 100,
  MEMORY_ERROR: 200
};

/**
 * Performance metrics storage
 * @type {Object}
 */
const metrics = {
  pageLoads: [],
  apiRequests: [],
  renders: [],
  fps: [],
  memory: []
};

/**
 * PerformanceMonitor class for tracking performance metrics
 *
 * @class PerformanceMonitor
 * @example
 * const monitor = new PerformanceMonitor();
 * monitor.trackPageLoad();
 * monitor.trackAPIRequest('/api/data', 1234);
 */
export class PerformanceMonitor {
  /**
   * Create a new PerformanceMonitor instance
   * @param {Object} options - Configuration options
   * @param {boolean} [options.autoTrack=true] - Auto-track page load metrics
   * @param {boolean} [options.trackFPS=false] - Enable FPS tracking
   * @param {boolean} [options.trackMemory=false] - Enable memory tracking
   */
  constructor(options = {}) {
    this.options = {
      autoTrack: options.autoTrack !== false,
      trackFPS: options.trackFPS || false,
      trackMemory: options.trackMemory || false,
      reportingEndpoint: options.reportingEndpoint || null
    };

    this.timers = new Map();
    this.marks = new Map();

    if (this.options.autoTrack) {
      this._setupAutoTracking();
    }

    logger.info('Initialized', this.options);
  }

  /**
   * Setup automatic performance tracking
   * @private
   */
  _setupAutoTracking() {
    // Track page load on DOMContentLoaded
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => {
        this.trackPageLoad();
      });
    } else {
      this.trackPageLoad();
    }

    // Track FPS if enabled
    if (this.options.trackFPS) {
      this.startFPSTracking();
    }

    // Track memory if enabled
    if (this.options.trackMemory) {
      this.startMemoryTracking();
    }
  }

  /**
   * Track page load performance
   * @returns {Object} Page load metrics
   */
  trackPageLoad() {
    if (!window.performance || !window.performance.timing) {
      logger.warn('Performance API not available');
      return null;
    }

    const timing = window.performance.timing;
    const navigation = window.performance.navigation;

    const metric = {
      timestamp: Date.now(),
      // Navigation timing
      navigationStart: timing.navigationStart,
      redirectTime: timing.redirectEnd - timing.redirectStart,
      dnsTime: timing.domainLookupEnd - timing.domainLookupStart,
      tcpTime: timing.connectEnd - timing.connectStart,
      requestTime: timing.responseStart - timing.requestStart,
      responseTime: timing.responseEnd - timing.responseStart,
      domProcessingTime: timing.domComplete - timing.domLoading,
      domContentLoadedTime: timing.domContentLoadedEventEnd - timing.domContentLoadedEventStart,
      loadEventTime: timing.loadEventEnd - timing.loadEventStart,
      // Total times
      totalLoadTime: timing.loadEventEnd - timing.navigationStart,
      domReadyTime: timing.domContentLoadedEventEnd - timing.navigationStart,
      // Navigation type
      navigationType: this._getNavigationType(navigation.type)
    };

    metrics.pageLoads.push(metric);

    // Check thresholds
    if (metric.totalLoadTime > THRESHOLDS.PAGE_LOAD_ERROR) {
      logger.error('Page load exceeded error threshold', { time: metric.totalLoadTime });
    } else if (metric.totalLoadTime > THRESHOLDS.PAGE_LOAD_WARN) {
      logger.warn('Page load exceeded warning threshold', { time: metric.totalLoadTime });
    } else {
      logger.info('Page loaded', { time: metric.totalLoadTime });
    }

    this._reportMetric('pageLoad', metric);

    return metric;
  }

  /**
   * Get navigation type string
   * @private
   * @param {number} type - Navigation type code
   * @returns {string} Navigation type
   */
  _getNavigationType(type) {
    const types = {
      0: 'navigate',
      1: 'reload',
      2: 'back_forward',
      255: 'reserved'
    };
    return types[type] || 'unknown';
  }

  /**
   * Track API request performance
   * @param {string} url - API endpoint URL
   * @param {number} duration - Request duration in milliseconds
   * @param {number} statusCode - HTTP status code
   * @param {Object} metadata - Additional metadata
   * @returns {Object} API request metric
   */
  trackAPIRequest(url, duration, statusCode = 200, metadata = {}) {
    const metric = {
      timestamp: Date.now(),
      url,
      duration,
      statusCode,
      success: statusCode >= 200 && statusCode < 300,
      ...metadata
    };

    metrics.apiRequests.push(metric);

    // Check thresholds
    if (duration > THRESHOLDS.API_REQUEST_ERROR) {
      logger.error('API request exceeded error threshold', { url, duration });
    } else if (duration > THRESHOLDS.API_REQUEST_WARN) {
      logger.warn('API request exceeded warning threshold', { url, duration });
    } else {
      logger.debug('API request completed', { url, duration });
    }

    this._reportMetric('apiRequest', metric);

    return metric;
  }

  /**
   * Start tracking component render time
   * @param {string} componentName - Component name
   */
  startRenderTracking(componentName) {
    const markName = `render-start-${componentName}`;
    this.timers.set(componentName, performance.now());
    this.marks.set(componentName, markName);

    if (window.performance && window.performance.mark) {
      performance.mark(markName);
    }
  }

  /**
   * End tracking component render time
   * @param {string} componentName - Component name
   * @returns {Object} Render metric
   */
  endRenderTracking(componentName) {
    if (!this.timers.has(componentName)) {
      logger.warn(`No render timer found for ${componentName}`);
      return null;
    }

    const startTime = this.timers.get(componentName);
    const duration = performance.now() - startTime;

    const metric = {
      timestamp: Date.now(),
      component: componentName,
      duration
    };

    metrics.renders.push(metric);

    // Performance measure API
    if (window.performance && window.performance.measure) {
      const startMark = this.marks.get(componentName);
      const endMark = `render-end-${componentName}`;
      performance.mark(endMark);
      try {
        performance.measure(`render-${componentName}`, startMark, endMark);
      } catch (error) {
        logger.debug('Performance measure failed', error);
      }
    }

    // Check thresholds
    if (duration > THRESHOLDS.RENDER_ERROR) {
      logger.error('Render exceeded error threshold', { component: componentName, duration });
    } else if (duration > THRESHOLDS.RENDER_WARN) {
      logger.warn('Render exceeded warning threshold', { component: componentName, duration });
    } else {
      logger.debug('Render completed', { component: componentName, duration });
    }

    this.timers.delete(componentName);
    this.marks.delete(componentName);

    this._reportMetric('render', metric);

    return metric;
  }

  /**
   * Start FPS (frames per second) tracking
   */
  startFPSTracking() {
    let lastTime = performance.now();
    let frames = 0;

    const trackFrame = () => {
      const currentTime = performance.now();
      frames++;

      // Calculate FPS every second
      if (currentTime >= lastTime + 1000) {
        const fps = Math.round((frames * 1000) / (currentTime - lastTime));

        const metric = {
          timestamp: Date.now(),
          fps
        };

        metrics.fps.push(metric);

        if (fps < THRESHOLDS.FPS_ERROR) {
          logger.error('FPS below error threshold', { fps });
        } else if (fps < THRESHOLDS.FPS_WARN) {
          logger.warn('FPS below warning threshold', { fps });
        }

        this._reportMetric('fps', metric);

        frames = 0;
        lastTime = currentTime;
      }

      requestAnimationFrame(trackFrame);
    };

    requestAnimationFrame(trackFrame);
  }

  /**
   * Start memory usage tracking
   */
  startMemoryTracking() {
    if (!performance.memory) {
      logger.warn('Memory API not available');
      return;
    }

    setInterval(() => {
      const memoryMB = performance.memory.usedJSHeapSize / (1024 * 1024);

      const metric = {
        timestamp: Date.now(),
        usedJSHeapSize: memoryMB,
        totalJSHeapSize: performance.memory.totalJSHeapSize / (1024 * 1024),
        jsHeapSizeLimit: performance.memory.jsHeapSizeLimit / (1024 * 1024)
      };

      metrics.memory.push(metric);

      if (memoryMB > THRESHOLDS.MEMORY_ERROR) {
        logger.error('Memory usage exceeded error threshold', { memory: memoryMB.toFixed(2) });
      } else if (memoryMB > THRESHOLDS.MEMORY_WARN) {
        logger.warn('Memory usage exceeded warning threshold', { memory: memoryMB.toFixed(2) });
      }

      this._reportMetric('memory', metric);
    }, 5000); // Track every 5 seconds
  }

  /**
   * Get all collected metrics
   * @returns {Object} All metrics
   */
  getMetrics() {
    return {
      pageLoads: metrics.pageLoads,
      apiRequests: metrics.apiRequests,
      renders: metrics.renders,
      fps: metrics.fps,
      memory: metrics.memory
    };
  }

  /**
   * Get summary statistics for all metrics
   * @returns {Object} Summary statistics
   */
  getSummary() {
    return {
      pageLoads: this._calculateStats(metrics.pageLoads, 'totalLoadTime'),
      apiRequests: this._calculateStats(metrics.apiRequests, 'duration'),
      renders: this._calculateStats(metrics.renders, 'duration'),
      fps: this._calculateStats(metrics.fps, 'fps'),
      memory: this._calculateStats(metrics.memory, 'usedJSHeapSize')
    };
  }

  /**
   * Calculate statistics for a metric array
   * @private
   * @param {Array} data - Metric data array
   * @param {string} key - Metric key to analyze
   * @returns {Object} Statistics
   */
  _calculateStats(data, key) {
    if (data.length === 0) {
      return { count: 0, min: 0, max: 0, avg: 0, p50: 0, p95: 0, p99: 0 };
    }

    const values = data.map(d => d[key]).filter(v => v !== undefined);
    values.sort((a, b) => a - b);

    const sum = values.reduce((acc, val) => acc + val, 0);
    const avg = sum / values.length;

    return {
      count: values.length,
      min: values[0],
      max: values[values.length - 1],
      avg: avg,
      p50: this._percentile(values, 50),
      p95: this._percentile(values, 95),
      p99: this._percentile(values, 99)
    };
  }

  /**
   * Calculate percentile value
   * @private
   * @param {Array} sortedValues - Sorted values array
   * @param {number} percentile - Percentile (0-100)
   * @returns {number} Percentile value
   */
  _percentile(sortedValues, percentile) {
    const index = Math.ceil((percentile / 100) * sortedValues.length) - 1;
    return sortedValues[Math.max(0, index)];
  }

  /**
   * Report metric to backend (if endpoint configured)
   * @private
   * @param {string} type - Metric type
   * @param {Object} metric - Metric data
   */
  _reportMetric(type, metric) {
    if (!this.options.reportingEndpoint) {
      return;
    }

    // Send metric to backend (non-blocking)
    fetch(this.options.reportingEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type, metric }),
      keepalive: true
    }).catch(error => {
      logger.debug('Failed to report metric', error);
    });
  }

  /**
   * Clear all metrics
   */
  clearMetrics() {
    metrics.pageLoads = [];
    metrics.apiRequests = [];
    metrics.renders = [];
    metrics.fps = [];
    metrics.memory = [];
    logger.info('Metrics cleared');
  }

  /**
   * Export metrics as JSON
   * @returns {string} JSON string of all metrics
   */
  exportMetrics() {
    return JSON.stringify({
      metrics: this.getMetrics(),
      summary: this.getSummary(),
      timestamp: Date.now(),
      userAgent: navigator.userAgent
    }, null, 2);
  }
}

/**
 * Global performance monitor instance
 * @type {PerformanceMonitor}
 */
let globalMonitor = null;

/**
 * Initialize global performance monitor
 * @param {Object} options - Configuration options
 * @returns {PerformanceMonitor} Monitor instance
 */
export function initPerformanceMonitor(options = {}) {
  if (!globalMonitor) {
    globalMonitor = new PerformanceMonitor(options);
  }
  return globalMonitor;
}

/**
 * Get global performance monitor instance
 * @returns {PerformanceMonitor|null} Monitor instance
 */
export function getPerformanceMonitor() {
  return globalMonitor;
}

export default {
  PerformanceMonitor,
  initPerformanceMonitor,
  getPerformanceMonitor,
  THRESHOLDS
};
