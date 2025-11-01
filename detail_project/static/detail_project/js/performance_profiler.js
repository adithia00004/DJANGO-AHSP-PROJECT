/**
 * Performance Profiler for Jadwal Pekerjaan
 *
 * Comprehensive performance monitoring tool to identify bottlenecks
 * and measure optimization improvements.
 *
 * Usage:
 *   const profiler = new PerformanceProfiler();
 *   profiler.start();
 *   // ... interact with page ...
 *   const report = profiler.generateReport();
 *   console.log(report);
 */

class PerformanceProfiler {
  constructor(options = {}) {
    this.options = {
      sampleInterval: options.sampleInterval || 1000, // 1s
      trackMemory: options.trackMemory !== false,
      trackFPS: options.trackFPS !== false,
      trackNetwork: options.trackNetwork !== false,
      ...options
    };

    this.metrics = {
      loadTimes: {},
      renderTimes: [],
      memorySnapshots: [],
      fpsData: [],
      networkRequests: [],
      interactionLatency: [],
      customMarks: []
    };

    this.intervals = [];
    this.observers = [];
    this.startTime = null;
    this.isRunning = false;
  }

  // =========================================================================
  // START/STOP
  // =========================================================================

  start() {
    if (this.isRunning) {
      console.warn('[Profiler] Already running');
      return;
    }

    console.log('[Profiler] Starting performance profiling...');
    this.startTime = performance.now();
    this.isRunning = true;

    // Measure initial load times
    this.measureLoadTimes();

    // Start continuous monitoring
    if (this.options.trackMemory) {
      this.startMemoryMonitoring();
    }

    if (this.options.trackFPS) {
      this.startFPSMonitoring();
    }

    if (this.options.trackNetwork) {
      this.startNetworkMonitoring();
    }

    // Track user interactions
    this.startInteractionTracking();

    console.log('[Profiler] Profiling started. Use profiler.stop() to end.');
  }

  stop() {
    if (!this.isRunning) {
      console.warn('[Profiler] Not running');
      return;
    }

    console.log('[Profiler] Stopping profiling...');
    this.isRunning = false;

    // Clear all intervals
    this.intervals.forEach(id => clearInterval(id));
    this.intervals = [];

    // Disconnect observers
    this.observers.forEach(obs => obs.disconnect());
    this.observers = [];

    console.log('[Profiler] Profiling stopped.');
  }

  // =========================================================================
  // LOAD TIME MEASUREMENT
  // =========================================================================

  measureLoadTimes() {
    const navigation = performance.getEntriesByType('navigation')[0];

    if (navigation) {
      this.metrics.loadTimes = {
        // DNS & Connection
        dns: navigation.domainLookupEnd - navigation.domainLookupStart,
        tcp: navigation.connectEnd - navigation.connectStart,

        // Request/Response
        request: navigation.responseStart - navigation.requestStart,
        response: navigation.responseEnd - navigation.responseStart,

        // DOM Processing
        domProcessing: navigation.domComplete - navigation.domLoading,
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,

        // Load Event
        loadEvent: navigation.loadEventEnd - navigation.loadEventStart,

        // Total Times
        domInteractive: navigation.domInteractive - navigation.fetchStart,
        domComplete: navigation.domComplete - navigation.fetchStart,
        totalLoadTime: navigation.loadEventEnd - navigation.fetchStart
      };
    }

    // Measure resource loading
    const resources = performance.getEntriesByType('resource');
    this.metrics.loadTimes.resources = {
      scripts: resources.filter(r => r.initiatorType === 'script').length,
      stylesheets: resources.filter(r => r.initiatorType === 'css' || r.initiatorType === 'link').length,
      images: resources.filter(r => r.initiatorType === 'img').length,
      fetch: resources.filter(r => r.initiatorType === 'fetch' || r.initiatorType === 'xmlhttprequest').length,
      total: resources.length
    };
  }

  // =========================================================================
  // MEMORY MONITORING
  // =========================================================================

  startMemoryMonitoring() {
    if (!performance.memory) {
      console.warn('[Profiler] Memory API not available (Chrome only)');
      return;
    }

    const sampleMemory = () => {
      this.metrics.memorySnapshots.push({
        timestamp: performance.now() - this.startTime,
        usedJSHeapSize: performance.memory.usedJSHeapSize,
        totalJSHeapSize: performance.memory.totalJSHeapSize,
        jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
      });
    };

    // Initial sample
    sampleMemory();

    // Periodic samples
    const intervalId = setInterval(sampleMemory, this.options.sampleInterval);
    this.intervals.push(intervalId);
  }

  getMemoryStats() {
    if (this.metrics.memorySnapshots.length === 0) {
      return null;
    }

    const snapshots = this.metrics.memorySnapshots;
    const usedHeaps = snapshots.map(s => s.usedJSHeapSize);

    return {
      current: usedHeaps[usedHeaps.length - 1],
      min: Math.min(...usedHeaps),
      max: Math.max(...usedHeaps),
      avg: usedHeaps.reduce((a, b) => a + b, 0) / usedHeaps.length,
      growth: usedHeaps[usedHeaps.length - 1] - usedHeaps[0],
      snapshots: snapshots.length
    };
  }

  detectMemoryLeak() {
    const stats = this.getMemoryStats();
    if (!stats) return { hasLeak: false, confidence: 0 };

    // Simple heuristic: if memory grows > 20% and doesn't drop
    const growthPercent = (stats.growth / stats.min) * 100;
    const hasLeak = growthPercent > 20 && stats.current > stats.avg * 1.1;

    return {
      hasLeak,
      confidence: hasLeak ? Math.min(growthPercent / 50, 1) : 0,
      growthPercent,
      growthMB: stats.growth / (1024 * 1024)
    };
  }

  // =========================================================================
  // FPS MONITORING
  // =========================================================================

  startFPSMonitoring() {
    let lastTime = performance.now();
    let frames = 0;

    const measureFPS = () => {
      const now = performance.now();
      frames++;

      if (now >= lastTime + 1000) {
        const fps = Math.round((frames * 1000) / (now - lastTime));

        this.metrics.fpsData.push({
          timestamp: now - this.startTime,
          fps
        });

        frames = 0;
        lastTime = now;
      }

      if (this.isRunning) {
        requestAnimationFrame(measureFPS);
      }
    };

    requestAnimationFrame(measureFPS);
  }

  getFPSStats() {
    if (this.metrics.fpsData.length === 0) {
      return null;
    }

    const fpsValues = this.metrics.fpsData.map(d => d.fps);

    return {
      current: fpsValues[fpsValues.length - 1],
      min: Math.min(...fpsValues),
      max: Math.max(...fpsValues),
      avg: fpsValues.reduce((a, b) => a + b, 0) / fpsValues.length,
      samples: fpsValues.length,
      below30: fpsValues.filter(fps => fps < 30).length,
      below60: fpsValues.filter(fps => fps < 60).length
    };
  }

  // =========================================================================
  // NETWORK MONITORING
  // =========================================================================

  startNetworkMonitoring() {
    // Use PerformanceObserver to track network requests
    try {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.initiatorType === 'fetch' || entry.initiatorType === 'xmlhttprequest') {
            this.metrics.networkRequests.push({
              name: entry.name,
              duration: entry.duration,
              transferSize: entry.transferSize || 0,
              timestamp: entry.startTime,
              type: entry.initiatorType
            });
          }
        }
      });

      observer.observe({ entryTypes: ['resource'] });
      this.observers.push(observer);
    } catch (e) {
      console.warn('[Profiler] PerformanceObserver not supported');
    }
  }

  getNetworkStats() {
    if (this.metrics.networkRequests.length === 0) {
      return null;
    }

    const requests = this.metrics.networkRequests;
    const durations = requests.map(r => r.duration);
    const sizes = requests.map(r => r.transferSize);

    return {
      count: requests.length,
      totalDuration: durations.reduce((a, b) => a + b, 0),
      avgDuration: durations.reduce((a, b) => a + b, 0) / durations.length,
      minDuration: Math.min(...durations),
      maxDuration: Math.max(...durations),
      totalSize: sizes.reduce((a, b) => a + b, 0),
      avgSize: sizes.reduce((a, b) => a + b, 0) / sizes.length
    };
  }

  // =========================================================================
  // INTERACTION TRACKING
  // =========================================================================

  startInteractionTracking() {
    const measureInteraction = (eventType) => (event) => {
      const startTime = performance.now();

      // Use rAF to measure when browser actually responds
      requestAnimationFrame(() => {
        const endTime = performance.now();
        const latency = endTime - startTime;

        this.metrics.interactionLatency.push({
          type: eventType,
          latency,
          timestamp: startTime - this.startTime
        });
      });
    };

    // Track click latency
    document.addEventListener('click', measureInteraction('click'), { passive: true });

    // Track scroll latency
    document.addEventListener('scroll', measureInteraction('scroll'), { passive: true, capture: true });

    // Track input latency
    document.addEventListener('input', measureInteraction('input'), { passive: true });
  }

  getInteractionStats() {
    if (this.metrics.interactionLatency.length === 0) {
      return null;
    }

    const latencies = this.metrics.interactionLatency.map(i => i.latency);

    return {
      count: latencies.length,
      avg: latencies.reduce((a, b) => a + b, 0) / latencies.length,
      min: Math.min(...latencies),
      max: Math.max(...latencies),
      p95: this.percentile(latencies, 0.95),
      p99: this.percentile(latencies, 0.99)
    };
  }

  // =========================================================================
  // CUSTOM MARKS
  // =========================================================================

  mark(name, metadata = {}) {
    this.metrics.customMarks.push({
      name,
      timestamp: performance.now() - this.startTime,
      metadata
    });

    // Also use native Performance API
    performance.mark(name);
  }

  measure(name, startMark, endMark) {
    try {
      performance.measure(name, startMark, endMark);

      const measures = performance.getEntriesByName(name, 'measure');
      if (measures.length > 0) {
        const duration = measures[measures.length - 1].duration;
        this.metrics.renderTimes.push({
          name,
          duration,
          timestamp: performance.now() - this.startTime
        });
        return duration;
      }
    } catch (e) {
      console.warn('[Profiler] Measure failed:', e);
    }
    return null;
  }

  // =========================================================================
  // REPORT GENERATION
  // =========================================================================

  generateReport() {
    const report = {
      metadata: {
        duration: performance.now() - this.startTime,
        url: window.location.href,
        userAgent: navigator.userAgent,
        timestamp: new Date().toISOString()
      },
      loadTimes: this.metrics.loadTimes,
      memory: this.getMemoryStats(),
      memoryLeak: this.detectMemoryLeak(),
      fps: this.getFPSStats(),
      network: this.getNetworkStats(),
      interactions: this.getInteractionStats(),
      customMarks: this.metrics.customMarks,
      renderTimes: this.metrics.renderTimes
    };

    // Pretty print to console
    this.printReport(report);

    return report;
  }

  printReport(report) {
    console.log('\n' + '='.repeat(80));
    console.log('%c PERFORMANCE PROFILING REPORT ', 'background: #0066cc; color: white; font-weight: bold; font-size: 16px; padding: 4px;');
    console.log('='.repeat(80) + '\n');

    // Metadata
    console.log('%c📊 Metadata', 'font-weight: bold; font-size: 14px; color: #0066cc');
    console.log(`   Duration: ${(report.metadata.duration / 1000).toFixed(2)}s`);
    console.log(`   URL: ${report.metadata.url}`);
    console.log(`   Timestamp: ${report.metadata.timestamp}\n`);

    // Load Times
    if (report.loadTimes && report.loadTimes.totalLoadTime) {
      console.log('%c⏱️  Load Times', 'font-weight: bold; font-size: 14px; color: #0066cc');
      console.log(`   Total Load Time: ${report.loadTimes.totalLoadTime.toFixed(2)}ms`);
      console.log(`   DOM Interactive: ${report.loadTimes.domInteractive.toFixed(2)}ms`);
      console.log(`   DOM Complete: ${report.loadTimes.domComplete.toFixed(2)}ms`);
      console.log(`   Resources: ${report.loadTimes.resources?.total || 0} files\n`);
    }

    // Memory
    if (report.memory) {
      const mem = report.memory;
      console.log('%c💾 Memory Usage', 'font-weight: bold; font-size: 14px; color: #0066cc');
      console.log(`   Current: ${(mem.current / 1024 / 1024).toFixed(2)} MB`);
      console.log(`   Min: ${(mem.min / 1024 / 1024).toFixed(2)} MB`);
      console.log(`   Max: ${(mem.max / 1024 / 1024).toFixed(2)} MB`);
      console.log(`   Avg: ${(mem.avg / 1024 / 1024).toFixed(2)} MB`);
      console.log(`   Growth: ${(mem.growth / 1024 / 1024).toFixed(2)} MB`);

      if (report.memoryLeak.hasLeak) {
        console.log(`   %c⚠️  POTENTIAL MEMORY LEAK DETECTED`, 'color: red; font-weight: bold');
        console.log(`   Growth: ${report.memoryLeak.growthPercent.toFixed(1)}%`);
        console.log(`   Confidence: ${(report.memoryLeak.confidence * 100).toFixed(0)}%`);
      }
      console.log('');
    }

    // FPS
    if (report.fps) {
      const fps = report.fps;
      console.log('%c🎮 Frame Rate', 'font-weight: bold; font-size: 14px; color: #0066cc');
      console.log(`   Current: ${fps.current} FPS`);
      console.log(`   Average: ${fps.avg.toFixed(1)} FPS`);
      console.log(`   Min: ${fps.min} FPS`);
      console.log(`   Max: ${fps.max} FPS`);
      console.log(`   Samples < 30 FPS: ${fps.below30} (${((fps.below30 / fps.samples) * 100).toFixed(1)}%)`);
      console.log(`   Samples < 60 FPS: ${fps.below60} (${((fps.below60 / fps.samples) * 100).toFixed(1)}%)\n`);
    }

    // Network
    if (report.network) {
      const net = report.network;
      console.log('%c🌐 Network', 'font-weight: bold; font-size: 14px; color: #0066cc');
      console.log(`   Requests: ${net.count}`);
      console.log(`   Total Duration: ${net.totalDuration.toFixed(2)}ms`);
      console.log(`   Avg Duration: ${net.avgDuration.toFixed(2)}ms`);
      console.log(`   Total Transfer: ${(net.totalSize / 1024).toFixed(2)} KB\n`);
    }

    // Interactions
    if (report.interactions) {
      const int = report.interactions;
      console.log('%c🖱️  Interaction Latency', 'font-weight: bold; font-size: 14px; color: #0066cc');
      console.log(`   Count: ${int.count}`);
      console.log(`   Average: ${int.avg.toFixed(2)}ms`);
      console.log(`   P95: ${int.p95.toFixed(2)}ms`);
      console.log(`   P99: ${int.p99.toFixed(2)}ms`);
      console.log(`   Max: ${int.max.toFixed(2)}ms\n`);
    }

    // Custom Marks
    if (report.customMarks && report.customMarks.length > 0) {
      console.log('%c📍 Custom Marks', 'font-weight: bold; font-size: 14px; color: #0066cc');
      report.customMarks.forEach(mark => {
        console.log(`   ${mark.name}: ${mark.timestamp.toFixed(2)}ms`, mark.metadata);
      });
      console.log('');
    }

    // Render Times
    if (report.renderTimes && report.renderTimes.length > 0) {
      console.log('%c🎨 Render Times', 'font-weight: bold; font-size: 14px; color: #0066cc');
      const grouped = {};
      report.renderTimes.forEach(rt => {
        if (!grouped[rt.name]) grouped[rt.name] = [];
        grouped[rt.name].push(rt.duration);
      });

      Object.entries(grouped).forEach(([name, durations]) => {
        const avg = durations.reduce((a, b) => a + b, 0) / durations.length;
        console.log(`   ${name}: ${avg.toFixed(2)}ms (${durations.length} samples)`);
      });
      console.log('');
    }

    console.log('='.repeat(80) + '\n');
  }

  // =========================================================================
  // UTILITIES
  // =========================================================================

  percentile(arr, p) {
    const sorted = arr.slice().sort((a, b) => a - b);
    const index = Math.ceil(sorted.length * p) - 1;
    return sorted[index];
  }

  exportJSON() {
    const report = this.generateReport();
    const json = JSON.stringify(report, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `performance-report-${Date.now()}.json`;
    a.click();

    URL.revokeObjectURL(url);
    console.log('[Profiler] Report exported as JSON');
  }
}

// Auto-start profiler if on Jadwal Pekerjaan page
if (document.getElementById('tahapan-grid-app')) {
  window.performanceProfiler = new PerformanceProfiler();

  // Add helper to console
  console.log('%c[PerformanceProfiler] Available', 'color: green; font-weight: bold');
  console.log('Start profiling: performanceProfiler.start()');
  console.log('Stop profiling:  performanceProfiler.stop()');
  console.log('Get report:      performanceProfiler.generateReport()');
  console.log('Export JSON:     performanceProfiler.exportJSON()');
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = PerformanceProfiler;
}
