# Performance Optimization Roadmap - Jadwal Pekerjaan

## 📊 Executive Summary

**Goal**: Improve page performance by 60-80% untuk large datasets (1000+ pekerjaan, 50+ tahapan)

**Target Metrics**:
- Initial Load Time: < 2s (currently ~5-8s for large datasets)
- Time to Interactive: < 3s (currently ~8-12s)
- Memory Usage: < 100MB (currently ~200-300MB)
- Frame Rate: 60 FPS during scroll (currently drops to 20-30 FPS)
- API Response Time: Batch saves < 5s for 100+ pekerjaan

---

## 🎯 Optimization Strategy

We'll tackle 6 major areas in 6 phases:

```
Phase 1: Performance Audit (Week 1)
   ↓
Phase 2: Virtual Scrolling (Week 1-2)
   ↓
Phase 3: Memory Optimization (Week 2-3)
   ↓
Phase 4: Event Optimization (Week 3)
   ↓
Phase 5: Web Workers (Week 4)
   ↓
Phase 6: Network Optimization (Week 4-5)
```

---

## 📅 PHASE 1: Performance Audit & Profiling (Week 1, Day 1-2)

### Objectives
- Identify current bottlenecks
- Establish baseline metrics
- Prioritize optimization targets

### Tasks

#### 1.1 Create Performance Measurement Script
```javascript
// performance_profiler.js
class PerformanceProfiler {
  static measureLoadTime() {
    // Measure page load, data fetch, render time
  }

  static measureMemoryUsage() {
    // Track memory consumption over time
  }

  static measureFrameRate() {
    // Monitor FPS during scroll/interactions
  }

  static generateReport() {
    // Output comprehensive performance report
  }
}
```

**Deliverable**: `performance_profiler.js` script

#### 1.2 Run Lighthouse & Chrome DevTools Audit
- Run Lighthouse audit
- Use Performance tab to record trace
- Use Memory profiler to check for leaks
- Document findings

**Deliverable**: `PERFORMANCE_AUDIT_REPORT.md`

#### 1.3 Create Synthetic Test Data Generator
```python
# management/commands/generate_test_data.py
# Generate projects with varying sizes:
# - Small: 50 pekerjaan, 10 tahapan
# - Medium: 500 pekerjaan, 30 tahapan
# - Large: 2000 pekerjaan, 52 tahapan
# - XLarge: 5000 pekerjaan, 100 tahapan
```

**Deliverable**: Django management command

#### 1.4 Establish Baseline Metrics

Test scenarios:
- Load time for 50/500/2000/5000 pekerjaan
- Render time for grid with different tahapan counts
- Memory usage after 10 minutes of interaction
- API response time for batch operations

**Deliverable**: Baseline metrics table

### Success Criteria
- ✅ Documented performance bottlenecks
- ✅ Clear metrics for improvement
- ✅ Test data ready for benchmarking

**Estimated Time**: 2 days

---

## 📅 PHASE 2: Virtual Scrolling Implementation (Week 1-2, Day 3-7)

### Problem Statement
Current implementation renders ALL rows in DOM, causing:
- Slow initial render for 1000+ rows
- High memory usage
- Laggy scrolling

### Solution: Virtual Scrolling
Only render visible rows + buffer, recycle DOM nodes as user scrolls.

### Architecture

```
┌─────────────────────────────────┐
│   Viewport (visible area)       │
│                                 │
│   ┌───────────────────┐        │
│   │ Buffer (above)    │        │
│   ├───────────────────┤        │
│   │ Visible Row 1     │ ◄──── Rendered in DOM
│   │ Visible Row 2     │ ◄──── Rendered in DOM
│   │ Visible Row 3     │ ◄──── Rendered in DOM
│   │ ...               │        │
│   │ Visible Row N     │ ◄──── Rendered in DOM
│   ├───────────────────┤        │
│   │ Buffer (below)    │        │
│   └───────────────────┘        │
│                                 │
└─────────────────────────────────┘
         ↑
    Total: 5000 rows
    Rendered: ~30 rows (visible + buffer)
    Recycled: DOM nodes reused as user scrolls
```

### Implementation Tasks

#### 2.1 Create VirtualScroller Class
```javascript
// virtual_scroller.js
class VirtualScroller {
  constructor(config) {
    this.containerHeight = config.height;
    this.rowHeight = config.rowHeight;
    this.totalRows = config.totalRows;
    this.renderRow = config.renderRow;
    this.bufferSize = config.bufferSize || 5;

    this.visibleRowCount = Math.ceil(this.containerHeight / this.rowHeight);
    this.init();
  }

  init() {
    this.setupScrollContainer();
    this.attachScrollListener();
    this.renderVisibleRows(0);
  }

  setupScrollContainer() {
    // Create scrollable container with proper height
    const totalHeight = this.totalRows * this.rowHeight;
    this.spacer.style.height = totalHeight + 'px';
  }

  attachScrollListener() {
    // Throttled scroll handler
    this.container.addEventListener('scroll',
      this.throttle(this.handleScroll.bind(this), 16)); // 60fps
  }

  handleScroll() {
    const scrollTop = this.container.scrollTop;
    const startIndex = Math.floor(scrollTop / this.rowHeight);
    this.renderVisibleRows(startIndex);
  }

  renderVisibleRows(startIndex) {
    const endIndex = Math.min(
      startIndex + this.visibleRowCount + this.bufferSize,
      this.totalRows
    );

    // Clear existing rows
    this.rowContainer.innerHTML = '';

    // Render visible + buffer rows
    for (let i = startIndex; i < endIndex; i++) {
      const row = this.renderRow(i, this.data[i]);
      this.rowContainer.appendChild(row);
    }

    // Adjust top offset
    this.rowContainer.style.transform =
      `translateY(${startIndex * this.rowHeight}px)`;
  }

  throttle(func, wait) {
    let lastTime = 0;
    return function(...args) {
      const now = Date.now();
      if (now - lastTime >= wait) {
        lastTime = now;
        return func.apply(this, args);
      }
    };
  }

  updateData(newData) {
    this.data = newData;
    this.totalRows = newData.length;
    this.setupScrollContainer();
    this.renderVisibleRows(0);
  }

  scrollToRow(index) {
    const scrollTop = index * this.rowHeight;
    this.container.scrollTop = scrollTop;
  }

  destroy() {
    // Cleanup event listeners
    this.container.removeEventListener('scroll', this.handleScroll);
  }
}
```

**Deliverable**: `virtual_scroller.js` module

#### 2.2 Integrate VirtualScroller with Grid

Modify `grid_module.js`:
```javascript
// In renderTables()
if (state.flatPekerjaan.length > 100) { // Use virtual scrolling for large datasets
  const scroller = new VirtualScroller({
    container: domRefs.leftPanelScroll,
    height: domRefs.leftPanelScroll.clientHeight,
    rowHeight: 40, // Average row height
    totalRows: state.flatPekerjaan.length,
    data: state.flatPekerjaan,
    renderRow: (index, pekerjaan) => {
      return renderPekerjaanRow(pekerjaan, state, utils);
    }
  });

  state.virtualScroller = scroller;
} else {
  // Use traditional rendering for small datasets
  renderTraditionalGrid();
}
```

**Deliverable**: Integrated virtual scrolling

#### 2.3 Handle Edge Cases
- Tree expand/collapse with virtual scrolling
- Cell editing in virtualized rows
- Row selection/highlighting
- Scroll position preservation on data update

**Deliverable**: Edge case handling code

#### 2.4 Benchmark & Compare
- Measure render time improvement
- Measure memory reduction
- Test with 5000+ rows

**Deliverable**: Performance comparison report

### Success Criteria
- ✅ Smooth 60fps scrolling with 5000+ rows
- ✅ Memory usage reduced by 60-70%
- ✅ Initial render time < 500ms for any dataset size

**Estimated Time**: 5 days

---

## 📅 PHASE 3: Memory Optimization & Cleanup (Week 2-3, Day 8-12)

### Problem Statement
- Large Maps/Sets grow unbounded
- No garbage collection for unused data
- Event listeners not properly cleaned up
- DOM references leak after rerenders

### Solution Strategy

#### 3.1 Implement State Pruning
```javascript
// state_manager.js
class StateManager {
  constructor() {
    this.maxModifiedCells = 1000; // Limit modified cells cache
    this.maxAssignmentCache = 500;
  }

  pruneModifiedCells(state) {
    // Keep only most recent N modified cells
    if (state.modifiedCells.size > this.maxModifiedCells) {
      const entries = Array.from(state.modifiedCells.entries());
      const toKeep = entries.slice(-this.maxModifiedCells);
      state.modifiedCells = new Map(toKeep);
    }
  }

  clearUnusedAssignments(state) {
    // Remove assignments for pekerjaan not in current view
    const visiblePekerjaanIds = new Set(
      state.flatPekerjaan.map(p => p.id)
    );

    for (const [id] of state.assignmentMap) {
      if (!visiblePekerjaanIds.has(id)) {
        state.assignmentMap.delete(id);
      }
    }
  }

  cleanupOldData(state) {
    this.pruneModifiedCells(state);
    this.clearUnusedAssignments(state);
    // Force GC hint (not guaranteed)
    if (window.gc) window.gc();
  }
}
```

**Deliverable**: `state_manager.js` module

#### 3.2 Implement Proper Cleanup on Unmount
```javascript
// In kelola_tahapan_grid.js
function cleanup() {
  // Remove event listeners
  state.domRefs.rightPanelScroll?.removeEventListener('scroll', scrollHandler);
  state.domRefs.leftPanelScroll?.removeEventListener('scroll', scrollHandler);

  // Destroy chart instances
  if (state.ganttInstance) {
    state.ganttInstance.destroy();
    state.ganttInstance = null;
  }

  if (state.scurveChart) {
    state.scurveChart.dispose();
    state.scurveChart = null;
  }

  // Clear large data structures
  state.assignmentMap.clear();
  state.modifiedCells.clear();
  state.volumeMap.clear();

  // Clear DOM references
  Object.keys(state.domRefs).forEach(key => {
    state.domRefs[key] = null;
  });

  logger.info('Cleanup completed');
}

// Listen for page unload
window.addEventListener('beforeunload', cleanup);

// For SPA navigation (if applicable)
if (window.navigation) {
  window.navigation.addEventListener('navigate', cleanup);
}
```

**Deliverable**: Cleanup implementation

#### 3.3 Implement WeakMap for DOM References
```javascript
// Instead of storing DOM references in state
// Use WeakMap to allow GC when elements are removed

const domNodeCache = new WeakMap();

function cacheNodeData(element, data) {
  domNodeCache.set(element, data);
}

function getNodeData(element) {
  return domNodeCache.get(element);
}
```

**Deliverable**: WeakMap implementation

#### 3.4 Memory Leak Detection Script
```javascript
// memory_leak_detector.js
class MemoryLeakDetector {
  constructor() {
    this.snapshots = [];
    this.interval = null;
  }

  start(intervalMs = 5000) {
    this.interval = setInterval(() => {
      if (performance.memory) {
        this.snapshots.push({
          timestamp: Date.now(),
          usedJSHeapSize: performance.memory.usedJSHeapSize,
          totalJSHeapSize: performance.memory.totalJSHeapSize
        });
      }
    }, intervalMs);
  }

  stop() {
    clearInterval(this.interval);
  }

  analyze() {
    // Check if memory consistently grows without dropping
    // Flag potential leaks
    const trend = this.calculateTrend();
    if (trend > 0.1) { // Growing > 10% per minute
      console.warn('Potential memory leak detected!');
      return this.snapshots;
    }
  }

  calculateTrend() {
    if (this.snapshots.length < 2) return 0;
    const first = this.snapshots[0];
    const last = this.snapshots[this.snapshots.length - 1];
    const timeDiff = (last.timestamp - first.timestamp) / 60000; // minutes
    const memDiff = last.usedJSHeapSize - first.usedJSHeapSize;
    return (memDiff / first.usedJSHeapSize) / timeDiff;
  }
}
```

**Deliverable**: Memory leak detector

### Success Criteria
- ✅ Memory usage stays < 100MB after 30 min session
- ✅ No memory leaks detected in 1-hour test
- ✅ Proper cleanup on page navigation

**Estimated Time**: 5 days

---

## 📅 PHASE 4: Event Optimization - Debouncing & Throttling (Week 3, Day 13-15)

### Problem Statement
- Scroll events fire too frequently (60+ times/sec)
- Resize events trigger expensive reflows
- Input events cause unnecessary rerenders

### Solution Strategy

#### 4.1 Create Utility Functions
```javascript
// event_utils.js

/**
 * Debounce - Execute after quiet period
 * Use for: search input, resize, window events
 */
function debounce(func, wait, options = {}) {
  let timeout;
  let lastArgs;
  let lastThis;

  const leading = options.leading || false;
  const trailing = options.trailing !== false;
  const maxWait = options.maxWait;

  let lastCallTime;
  let lastInvokeTime = 0;

  function invokeFunc(time) {
    const args = lastArgs;
    const thisArg = lastThis;

    lastArgs = lastThis = undefined;
    lastInvokeTime = time;
    return func.apply(thisArg, args);
  }

  function shouldInvoke(time) {
    const timeSinceLastCall = time - lastCallTime;
    const timeSinceLastInvoke = time - lastInvokeTime;

    return (lastCallTime === undefined ||
            timeSinceLastCall >= wait ||
            timeSinceLastCall < 0 ||
            (maxWait !== undefined && timeSinceLastInvoke >= maxWait));
  }

  function debounced(...args) {
    const time = Date.now();
    const isInvoking = shouldInvoke(time);

    lastArgs = args;
    lastThis = this;
    lastCallTime = time;

    if (isInvoking) {
      if (timeout === undefined && leading) {
        return invokeFunc(lastCallTime);
      }

      if (maxWait !== undefined) {
        clearTimeout(timeout);
        timeout = setTimeout(() => invokeFunc(Date.now()), wait);
        return leading ? invokeFunc(lastCallTime) : undefined;
      }
    }

    if (timeout === undefined) {
      timeout = setTimeout(() => invokeFunc(Date.now()), wait);
    }

    return undefined;
  }

  debounced.cancel = function() {
    if (timeout !== undefined) {
      clearTimeout(timeout);
    }
    lastInvokeTime = 0;
    lastArgs = lastCallTime = lastThis = timeout = undefined;
  };

  return debounced;
}

/**
 * Throttle - Execute at most once per interval
 * Use for: scroll, mousemove, frequent events
 */
function throttle(func, wait, options = {}) {
  let timeout;
  let previous = 0;

  const leading = options.leading !== false;
  const trailing = options.trailing !== false;

  function throttled(...args) {
    const now = Date.now();

    if (!previous && !leading) {
      previous = now;
    }

    const remaining = wait - (now - previous);

    if (remaining <= 0 || remaining > wait) {
      if (timeout) {
        clearTimeout(timeout);
        timeout = null;
      }

      previous = now;
      return func.apply(this, args);
    } else if (!timeout && trailing) {
      timeout = setTimeout(() => {
        previous = leading ? Date.now() : 0;
        timeout = null;
        func.apply(this, args);
      }, remaining);
    }
  }

  throttled.cancel = function() {
    clearTimeout(timeout);
    previous = 0;
    timeout = null;
  };

  return throttled;
}

/**
 * RequestAnimationFrame-based throttle
 * Use for: visual updates, animations
 */
function rafThrottle(func) {
  let rafId = null;
  let lastArgs = null;

  function throttled(...args) {
    lastArgs = args;

    if (rafId === null) {
      rafId = requestAnimationFrame(() => {
        func.apply(this, lastArgs);
        rafId = null;
        lastArgs = null;
      });
    }
  }

  throttled.cancel = function() {
    if (rafId !== null) {
      cancelAnimationFrame(rafId);
      rafId = null;
      lastArgs = null;
    }
  };

  return throttled;
}

export { debounce, throttle, rafThrottle };
```

**Deliverable**: `event_utils.js` module

#### 4.2 Apply to Grid Events
```javascript
// In grid_module.js

import { debounce, throttle, rafThrottle } from './event_utils.js';

// Scroll synchronization
const syncScroll = throttle((scrollTop) => {
  leftPanel.scrollTop = scrollTop;
}, 16); // ~60fps

rightPanel.addEventListener('scroll', () => {
  syncScroll(rightPanel.scrollTop);
});

// Window resize
const handleResize = debounce(() => {
  syncHeaderHeights();
  syncRowHeights();
  if (state.scurveChart) {
    state.scurveChart.resize();
  }
}, 250, { maxWait: 1000 });

window.addEventListener('resize', handleResize);

// Cell input (for search/filter)
const handleSearchInput = debounce((value) => {
  filterPekerjaan(value);
  renderGrid();
}, 300);

searchInput.addEventListener('input', (e) => {
  handleSearchInput(e.target.value);
});

// Visual updates during scroll
const updateScrollShadow = rafThrottle(() => {
  const scrolled = rightPanel.scrollTop > 0;
  rightThead.classList.toggle('scrolled', scrolled);
});

rightPanel.addEventListener('scroll', updateScrollShadow);
```

**Deliverable**: Optimized event handlers

#### 4.3 Optimize Render Batching
```javascript
// batch_renderer.js
class BatchRenderer {
  constructor() {
    this.pendingUpdates = new Set();
    this.rafId = null;
  }

  scheduleUpdate(updateFn) {
    this.pendingUpdates.add(updateFn);

    if (this.rafId === null) {
      this.rafId = requestAnimationFrame(() => {
        this.flush();
      });
    }
  }

  flush() {
    const updates = Array.from(this.pendingUpdates);
    this.pendingUpdates.clear();
    this.rafId = null;

    // Execute all updates in single frame
    updates.forEach(fn => fn());
  }

  cancel() {
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    this.pendingUpdates.clear();
  }
}

const batchRenderer = new BatchRenderer();

// Usage
batchRenderer.scheduleUpdate(() => updateCell(cellId, value));
batchRenderer.scheduleUpdate(() => updateStatusBar());
// Both execute in same frame
```

**Deliverable**: Batch renderer

### Success Criteria
- ✅ Scroll events handled at 60fps
- ✅ No janky UI during rapid interactions
- ✅ Reduced CPU usage by 40-50%

**Estimated Time**: 3 days

---

## 📅 PHASE 5: Web Workers for Heavy Calculations (Week 4, Day 16-19)

### Problem Statement
- Gantt chart calculations block UI thread
- S-curve data processing causes freezes
- Large data transformations lock the browser

### Solution: Offload to Web Workers

#### 5.1 Create Calculation Worker
```javascript
// workers/calculation_worker.js

self.addEventListener('message', (e) => {
  const { type, data } = e.data;

  switch (type) {
    case 'CALCULATE_GANTT_TASKS':
      const ganttTasks = calculateGanttTasks(data);
      self.postMessage({ type: 'GANTT_TASKS_READY', data: ganttTasks });
      break;

    case 'CALCULATE_SCURVE_DATA':
      const scurveData = calculateScurveData(data);
      self.postMessage({ type: 'SCURVE_DATA_READY', data: scurveData });
      break;

    case 'TRANSFORM_ASSIGNMENTS':
      const transformed = transformAssignments(data);
      self.postMessage({ type: 'ASSIGNMENTS_TRANSFORMED', data: transformed });
      break;
  }
});

function calculateGanttTasks(state) {
  // Heavy calculation logic here
  // This runs in separate thread, doesn't block UI
  const tasks = [];

  state.flatPekerjaan.forEach(pekerjaan => {
    // Complex date calculations
    // Progress calculations
    // Dependency resolution
    tasks.push({
      id: pekerjaan.id,
      name: pekerjaan.uraian,
      start: calculateStartDate(pekerjaan),
      end: calculateEndDate(pekerjaan),
      progress: calculateProgress(pekerjaan)
    });
  });

  return tasks;
}

function calculateScurveData(state) {
  // Cumulative progress calculations
  const dataPoints = [];

  state.timeColumns.forEach((col, index) => {
    const cumulativeProgress = calculateCumulativeProgress(
      state.flatPekerjaan,
      state.assignmentMap,
      col.tahapanId
    );

    dataPoints.push({
      date: col.date,
      planned: cumulativeProgress.planned,
      actual: cumulativeProgress.actual
    });
  });

  return dataPoints;
}
```

**Deliverable**: `calculation_worker.js`

#### 5.2 Create Worker Manager
```javascript
// worker_manager.js
class WorkerManager {
  constructor() {
    this.worker = null;
    this.callbacks = new Map();
    this.requestId = 0;
  }

  init() {
    this.worker = new Worker('/static/detail_project/js/workers/calculation_worker.js');

    this.worker.addEventListener('message', (e) => {
      const { type, data, requestId } = e.data;

      const callback = this.callbacks.get(requestId);
      if (callback) {
        callback(data);
        this.callbacks.delete(requestId);
      }
    });

    this.worker.addEventListener('error', (error) => {
      console.error('Worker error:', error);
    });
  }

  calculate(type, data) {
    return new Promise((resolve) => {
      const requestId = ++this.requestId;

      this.callbacks.set(requestId, resolve);

      this.worker.postMessage({
        type,
        data,
        requestId
      });
    });
  }

  async calculateGanttTasks(state) {
    return await this.calculate('CALCULATE_GANTT_TASKS', state);
  }

  async calculateScurveData(state) {
    return await this.calculate('CALCULATE_SCURVE_DATA', state);
  }

  terminate() {
    if (this.worker) {
      this.worker.terminate();
      this.worker = null;
    }
  }
}

const workerManager = new WorkerManager();
workerManager.init();

export default workerManager;
```

**Deliverable**: `worker_manager.js`

#### 5.3 Integrate with Existing Code
```javascript
// In gantt_module.js
import workerManager from './worker_manager.js';

async function buildGanttTasks(options = {}) {
  try {
    showLoading('Building Gantt chart...', 'Processing tasks in background');

    // Offload heavy calculation to worker
    const tasks = await workerManager.calculateGanttTasks({
      flatPekerjaan: state.flatPekerjaan,
      assignmentMap: Array.from(state.assignmentMap.entries()),
      tahapanProgressMap: Array.from(state.tahapanProgressMap.entries())
    });

    state.ganttTasks = tasks;
    showLoading(false);

    return tasks;
  } catch (error) {
    logger.error('Failed to build Gantt tasks:', error);
    showLoading(false);
    return [];
  }
}
```

**Deliverable**: Worker integration

### Success Criteria
- ✅ UI stays responsive during heavy calculations
- ✅ No freezing on large datasets (5000+ rows)
- ✅ Gantt/S-curve generation < 2s for any size

**Estimated Time**: 4 days

---

## 📅 PHASE 6: Network Optimization (Week 4-5, Day 20-23)

### Problem Statement
- Sequential API calls for each pekerjaan during save
- No request batching
- No caching strategy
- No optimistic updates

### Solution Strategy

#### 6.1 Implement Batch Save Endpoint (Backend)
```python
# views_api_tahapan.py

@login_required
def api_batch_save_assignments(request, project_id):
    """
    Batch save assignments for multiple pekerjaan in single request

    Request body:
    {
      "pekerjaan_assignments": [
        {
          "pekerjaan_id": 123,
          "assignments": {
            "841": 50.0,
            "842": 30.0
          }
        },
        ...
      ]
    }
    """
    project = _owner_or_404(request, project_id)

    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
        pekerjaan_assignments = data.get('pekerjaan_assignments', [])

        saved_count = 0
        errors = []

        with transaction.atomic():
            for item in pekerjaan_assignments:
                pekerjaan_id = item['pekerjaan_id']
                assignments = item['assignments']

                try:
                    # Save assignments for this pekerjaan
                    save_pekerjaan_assignments(
                        project,
                        pekerjaan_id,
                        assignments
                    )
                    saved_count += 1
                except Exception as e:
                    errors.append({
                        'pekerjaan_id': pekerjaan_id,
                        'error': str(e)
                    })

        return JsonResponse({
            'ok': len(errors) == 0,
            'saved_count': saved_count,
            'errors': errors
        })

    except Exception as e:
        return JsonResponse({
            'ok': False,
            'error': str(e)
        }, status=400)
```

**Deliverable**: Batch save endpoint

#### 6.2 Implement Frontend Batch Saving
```javascript
// In save_handler_module.js

async function saveAllChanges({ state, helpers }) {
  const { showLoading, showToast, updateStatusBar } = helpers;

  if (state.modifiedCells.size === 0) {
    showToast('No changes to save', 'info');
    return;
  }

  try {
    showLoading('Preparing batch save...');

    // Group changes by pekerjaan
    const changesByPekerjaan = groupChangesByPekerjaan(state.modifiedCells, state);

    // Build batch payload
    const batchPayload = {
      pekerjaan_assignments: Array.from(changesByPekerjaan.entries()).map(
        ([pekerjaanId, assignments]) => ({
          pekerjaan_id: parseInt(pekerjaanId),
          assignments: Object.fromEntries(
            Object.entries(assignments).map(([tahapanId, value]) => [
              tahapanId,
              parseFloat(value)
            ])
          )
        })
      )
    };

    showLoading(`Saving ${batchPayload.pekerjaan_assignments.length} pekerjaan...`);

    // Single API call for all changes!
    const response = await fetch(
      `/detail_project/api/project/${state.projectId}/batch-save-assignments/`,
      {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(batchPayload)
      }
    );

    const result = await response.json();

    if (result.ok) {
      // Clear modified cells
      state.modifiedCells.clear();
      updateStatusBar();

      showToast(
        `Successfully saved ${result.saved_count} pekerjaan`,
        'success'
      );
    } else {
      throw new Error(result.error || 'Batch save failed');
    }

  } catch (error) {
    showToast(`Save failed: ${error.message}`, 'danger');
  } finally {
    showLoading(false);
  }
}
```

**Deliverable**: Batch save implementation

#### 6.3 Implement Response Caching
```javascript
// cache_manager.js
class CacheManager {
  constructor() {
    this.cache = new Map();
    this.ttl = 5 * 60 * 1000; // 5 minutes
  }

  set(key, value, ttl = this.ttl) {
    this.cache.set(key, {
      value,
      expires: Date.now() + ttl
    });
  }

  get(key) {
    const item = this.cache.get(key);

    if (!item) return null;

    if (Date.now() > item.expires) {
      this.cache.delete(key);
      return null;
    }

    return item.value;
  }

  invalidate(pattern) {
    // Invalidate cache entries matching pattern
    for (const key of this.cache.keys()) {
      if (key.includes(pattern)) {
        this.cache.delete(key);
      }
    }
  }

  clear() {
    this.cache.clear();
  }
}

const cacheManager = new CacheManager();

// Usage
async function loadTahapan() {
  const cacheKey = `tahapan_${projectId}`;
  const cached = cacheManager.get(cacheKey);

  if (cached) {
    logger.info('Using cached tahapan data');
    return cached;
  }

  const data = await fetch(/* ... */);
  cacheManager.set(cacheKey, data);
  return data;
}

// Invalidate on save
function onSaveSuccess() {
  cacheManager.invalidate('assignments');
  cacheManager.invalidate('tahapan');
}
```

**Deliverable**: Cache manager

#### 6.4 Implement Optimistic Updates
```javascript
// optimistic_update_manager.js
class OptimisticUpdateManager {
  constructor() {
    this.pendingUpdates = new Map();
  }

  apply(updateId, applyFn, revertFn) {
    // Apply update immediately (optimistic)
    applyFn();

    this.pendingUpdates.set(updateId, {
      applyFn,
      revertFn,
      timestamp: Date.now()
    });
  }

  commit(updateId) {
    // Server confirmed, remove from pending
    this.pendingUpdates.delete(updateId);
  }

  revert(updateId) {
    // Server rejected, revert change
    const update = this.pendingUpdates.get(updateId);
    if (update) {
      update.revertFn();
      this.pendingUpdates.delete(updateId);
    }
  }

  revertAll() {
    // Revert all pending updates (on error)
    for (const [id, update] of this.pendingUpdates) {
      update.revertFn();
    }
    this.pendingUpdates.clear();
  }
}

// Usage
const optimisticManager = new OptimisticUpdateManager();

function saveCell(cellId, oldValue, newValue) {
  const updateId = `cell_${cellId}_${Date.now()}`;

  optimisticManager.apply(
    updateId,
    () => {
      // Optimistic update
      updateCellDOM(cellId, newValue);
      state.modifiedCells.set(cellId, newValue);
    },
    () => {
      // Revert on failure
      updateCellDOM(cellId, oldValue);
      state.modifiedCells.delete(cellId);
    }
  );

  // Send to server
  apiCall('/save/', { cellId, value: newValue })
    .then(() => optimisticManager.commit(updateId))
    .catch(() => optimisticManager.revert(updateId));
}
```

**Deliverable**: Optimistic update manager

### Success Criteria
- ✅ Batch save 100 pekerjaan in < 5 seconds
- ✅ Reduced API calls by 90%
- ✅ Instant UI feedback with optimistic updates
- ✅ Cache hit rate > 70% for repeated loads

**Estimated Time**: 4 days

---

## 📊 Success Metrics Summary

| Metric | Before | Target | Measurement Method |
|--------|--------|--------|-------------------|
| Initial Load (1000 rows) | ~8s | < 2s | Lighthouse Performance |
| Time to Interactive | ~12s | < 3s | Lighthouse TTI |
| Memory Usage (30min) | 300MB | < 100MB | Chrome Memory Profiler |
| Scroll FPS (5000 rows) | 20-30 | 60 | Chrome FPS Meter |
| Batch Save (100 items) | 30s | < 5s | Network tab timing |
| Gantt Generation (2000 rows) | 5s | < 2s | Performance.now() |

---

## 🚀 Quick Start Guide

1. **Clone & Setup**
   ```bash
   cd "D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT"
   # Follow roadmap phase by phase
   ```

2. **Generate Test Data**
   ```bash
   python manage.py generate_test_data --size large
   ```

3. **Run Performance Audit**
   - Open Jadwal Pekerjaan page
   - F12 → Performance tab → Record
   - Interact with page for 30s
   - Stop recording → Analyze

4. **Implement Phase by Phase**
   - Complete each phase before moving to next
   - Benchmark after each phase
   - Document improvements

---

## 📚 Resources & References

- [Virtual Scrolling Best Practices](https://web.dev/virtualize-long-lists-react-window/)
- [Web Workers Guide](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API)
- [Debouncing & Throttling](https://css-tricks.com/debouncing-throttling-explained-examples/)
- [Memory Leak Detection](https://developer.chrome.com/docs/devtools/memory-problems/)
- [Request Batching Patterns](https://kentcdodds.com/blog/optimize-your-react-app-by-batching-requests)

---

**Version**: 1.0
**Status**: Planning Complete - Ready for Implementation
**Estimated Total Time**: 4-5 weeks
**Priority**: High - Performance critical for user experience
