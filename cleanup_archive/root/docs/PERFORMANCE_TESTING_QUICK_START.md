# Performance Testing - Quick Start Guide

## 🚀 Quick Start (5 minutes)

### Step 1: Generate Test Data (2 min)

```bash
cd "D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT"

# Activate virtual environment (if using)
# venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Generate test projects
python manage.py generate_test_data --size small --user admin
python manage.py generate_test_data --size medium --user admin
python manage.py generate_test_data --size large --user admin

# Optional: Generate custom size
python manage.py generate_test_data --custom 1000 24 --user admin
```

**Output:**
```
=== Generating SMALL Test Project ===
Pekerjaan: 50
Tahapan: 10
Owner: admin

✓ Project created
✓ 10 Tahapan created
✓ 50 Pekerjaan created
✓ 120 Assignments created

✓ Successfully created test project: [TEST] Performance Test - SMALL (50P x 10T)
Project ID: 42
URL: /detail-project/42/kelola-tahapan/
```

### Step 2: Run Performance Profiler (3 min)

1. **Open Test Project**
   - Navigate to: `/detail-project/{PROJECT_ID}/kelola-tahapan/`
   - Wait for page to fully load

2. **Open Browser DevTools**
   - Press `F12`
   - Go to `Console` tab

3. **Start Profiler**
   ```javascript
   performanceProfiler.start()
   ```

4. **Interact with Page** (do these for ~2 minutes):
   - Scroll up and down rapidly
   - Expand/collapse tree nodes
   - Edit some cells (double-click, enter values)
   - Switch between tabs (Grid, Gantt, S-Curve)
   - Change time scale (Daily → Weekly → Monthly)
   - Click Save All (if you edited cells)

5. **Stop & Get Report**
   ```javascript
   performanceProfiler.stop()
   const report = performanceProfiler.generateReport()
   ```

6. **Export Report (optional)**
   ```javascript
   performanceProfiler.exportJSON()  // Downloads JSON file
   ```

### Step 3: Analyze Results

Check the console output for:

**🔴 Red Flags:**
- Load Time > 5s
- Memory Growth > 50 MB
- FPS Average < 30
- Potential Memory Leak Warning

**🟡 Yellow Flags:**
- Load Time 3-5s
- Memory Growth 20-50 MB
- FPS Average 30-45
- Interaction Latency P95 > 100ms

**🟢 Good:**
- Load Time < 3s
- Memory Growth < 20 MB
- FPS Average > 45
- Interaction Latency P95 < 100ms

---

## 📊 Detailed Testing Scenarios

### Scenario 1: Initial Load Performance

**Test:** Measure how fast page loads with different data sizes

```bash
# Generate different sizes
python manage.py generate_test_data --size small
python manage.py generate_test_data --size medium
python manage.py generate_test_data --size large

# For each project:
# 1. Open in browser (fresh incognito tab)
# 2. F12 → Network tab → Disable cache ✓
# 3. Hard refresh (Ctrl+F5)
# 4. Check:
#    - DOMContentLoaded time
#    - Load event time
#    - Total blocking time
```

**Record:**
| Size | Pekerjaan | Tahapan | Load Time | DOM Interactive | Notes |
|------|-----------|---------|-----------|-----------------|-------|
| Small | 50 | 10 | ___ s | ___ s | |
| Medium | 500 | 30 | ___ s | ___ s | |
| Large | 2000 | 52 | ___ s | ___ s | |

### Scenario 2: Scroll Performance

**Test:** Measure FPS during rapid scrolling

```javascript
performanceProfiler.start()

// Scroll rapidly for 30 seconds
// (Use scroll wheel or drag scrollbar)

performanceProfiler.stop()
const fps = performanceProfiler.getFPSStats()

console.log('Average FPS:', fps.avg)
console.log('Min FPS:', fps.min)
console.log('Frames < 30 FPS:', fps.below30)
```

**Record:**
| Size | Avg FPS | Min FPS | Frames < 30 | Acceptable? |
|------|---------|---------|-------------|-------------|
| Small | ___ | ___ | ___ | ✓/✗ |
| Medium | ___ | ___ | ___ | ✓/✗ |
| Large | ___ | ___ | ___ | ✓/✗ |

### Scenario 3: Memory Usage Over Time

**Test:** Check for memory leaks during extended session

```javascript
performanceProfiler.start()

// Interact with page for 10 minutes:
// - Scroll
// - Edit cells
// - Expand/collapse
// - Switch tabs
// - Repeat

performanceProfiler.stop()
const leak = performanceProfiler.detectMemoryLeak()

if (leak.hasLeak) {
  console.error('MEMORY LEAK DETECTED!')
  console.error('Growth:', leak.growthMB, 'MB')
  console.error('Confidence:', leak.confidence * 100, '%')
}
```

**Record:**
| Size | Initial MB | Final MB | Growth MB | Leak? |
|------|------------|----------|-----------|-------|
| Small | ___ | ___ | ___ | ✓/✗ |
| Medium | ___ | ___ | ___ | ✓/✗ |
| Large | ___ | ___ | ___ | ✓/✗ |

### Scenario 4: Save Operation Performance

**Test:** Measure time to save changes

```javascript
// 1. Edit 10 cells with different values
// 2. Use console:

performance.mark('save-start')
// Click "Save All" button
// Wait for success toast
performance.mark('save-end')
performance.measure('save-duration', 'save-start', 'save-end')

const measures = performance.getEntriesByName('save-duration')
console.log('Save took:', measures[0].duration, 'ms')
```

**Record:**
| Modified Cells | Save Time (ms) | Acceptable? |
|----------------|----------------|-------------|
| 10 | ___ | ✓/✗ |
| 50 | ___ | ✓/✗ |
| 100 | ___ | ✓/✗ |

### Scenario 5: Chart Generation Performance

**Test:** Measure Gantt & S-Curve render time

```javascript
// Switch to Gantt tab
performance.mark('gantt-start')
// Click "Gantt Chart" tab
// Wait for chart to fully render
performance.mark('gantt-end')
performance.measure('gantt-render', 'gantt-start', 'gantt-end')

const ganttTime = performance.getEntriesByName('gantt-render')[0].duration
console.log('Gantt render:', ganttTime, 'ms')

// Repeat for S-Curve
```

**Record:**
| Size | Gantt Time (ms) | S-Curve Time (ms) | Acceptable? |
|------|-----------------|-------------------|-------------|
| Small | ___ | ___ | ✓/✗ |
| Medium | ___ | ___ | ✓/✗ |
| Large | ___ | ___ | ✓/✗ |

---

## 🔬 Advanced Profiling

### Chrome DevTools Performance Tab

1. **Open** `/detail-project/{PROJECT_ID}/kelola-tahapan/`
2. **F12** → **Performance** tab
3. **Click Record** ⏺️
4. **Interact** with page (scroll, edit, etc.)
5. **Stop Recording** ⏹️
6. **Analyze**:
   - Yellow: JavaScript execution
   - Purple: Layout/Reflow
   - Green: Paint
   - Red: Long tasks (> 50ms)

**Look for:**
- 🔴 Long tasks blocking main thread
- 🔴 Excessive layout thrashing
- 🔴 Paint storms during scroll

### Chrome DevTools Memory Tab

1. **F12** → **Memory** tab
2. **Take Heap Snapshot** (before interaction)
3. **Interact** with page for 5 minutes
4. **Take another Heap Snapshot**
5. **Compare** snapshots
6. **Look for**:
   - Growing arrays/objects
   - Detached DOM nodes
   - Event listener leaks

### Lighthouse Audit

1. **F12** → **Lighthouse** tab
2. **Select**:
   - ✓ Performance
   - ✓ Best Practices
   - Device: Desktop
3. **Generate Report**
4. **Check**:
   - Performance Score (target: > 90)
   - First Contentful Paint (target: < 1.8s)
   - Largest Contentful Paint (target: < 2.5s)
   - Total Blocking Time (target: < 200ms)
   - Cumulative Layout Shift (target: < 0.1)

---

## 📈 Benchmarking Script

Save this as `benchmark.js` and run in console:

```javascript
async function runBenchmark() {
  console.log('Starting benchmark...\n');

  const results = {
    timestamp: new Date().toISOString(),
    tests: {}
  };

  // Test 1: Grid Render Time
  console.log('Test 1: Grid Render...');
  performance.mark('grid-render-start');
  window.KelolaTahapanPage.grid.renderGrid();
  performance.mark('grid-render-end');
  performance.measure('grid-render', 'grid-render-start', 'grid-render-end');
  results.tests.gridRender = performance.getEntriesByName('grid-render')[0].duration;
  console.log('  ✓ Grid render:', results.tests.gridRender.toFixed(2), 'ms\n');

  // Test 2: Expand All
  console.log('Test 2: Expand All...');
  performance.mark('expand-start');
  document.getElementById('btn-expand-all').click();
  await new Promise(r => setTimeout(r, 100));
  performance.mark('expand-end');
  performance.measure('expand-all', 'expand-start', 'expand-end');
  results.tests.expandAll = performance.getEntriesByName('expand-all')[0].duration;
  console.log('  ✓ Expand all:', results.tests.expandAll.toFixed(2), 'ms\n');

  // Test 3: Collapse All
  console.log('Test 3: Collapse All...');
  performance.mark('collapse-start');
  document.getElementById('btn-collapse-all').click();
  await new Promise(r => setTimeout(r, 100));
  performance.mark('collapse-end');
  performance.measure('collapse-all', 'collapse-start', 'collapse-end');
  results.tests.collapseAll = performance.getEntriesByName('collapse-all')[0].duration;
  console.log('  ✓ Collapse all:', results.tests.collapseAll.toFixed(2), 'ms\n');

  // Test 4: Memory Usage
  if (performance.memory) {
    results.tests.memory = {
      used: (performance.memory.usedJSHeapSize / 1024 / 1024).toFixed(2) + ' MB',
      total: (performance.memory.totalJSHeapSize / 1024 / 1024).toFixed(2) + ' MB'
    };
    console.log('Test 4: Memory Usage');
    console.log('  ✓ Used:', results.tests.memory.used);
    console.log('  ✓ Total:', results.tests.memory.total, '\n');
  }

  console.log('='.repeat(60));
  console.log('BENCHMARK COMPLETE');
  console.log('='.repeat(60));
  console.table(results.tests);

  return results;
}

// Run it
runBenchmark();
```

---

## 📝 Performance Test Report Template

Use this template to document your findings:

```markdown
# Performance Test Report

**Date:** YYYY-MM-DD
**Tester:** Your Name
**Browser:** Chrome 120.x.x
**OS:** Windows 11

## Test Environment
- CPU:
- RAM:
- Network:

## Test Results

### Load Performance
| Size | Pekerjaan | Load Time | Score |
|------|-----------|-----------|-------|
| Small | 50 | X.Xs | ✓/✗ |
| Medium | 500 | X.Xs | ✓/✗ |
| Large | 2000 | X.Xs | ✓/✗ |

### Scroll Performance
| Size | Avg FPS | Min FPS | Score |
|------|---------|---------|-------|
| Small | XX | XX | ✓/✗ |
| Medium | XX | XX | ✓/✗ |
| Large | XX | XX | ✓/✗ |

### Memory Usage
| Size | Initial | After 10min | Growth | Leak? |
|------|---------|-------------|--------|-------|
| Small | XX MB | XX MB | XX MB | ✗ |
| Medium | XX MB | XX MB | XX MB | ✗ |
| Large | XX MB | XX MB | XX MB | ✗ |

## Identified Bottlenecks

1. **[Issue Name]**
   - Severity: High/Medium/Low
   - Location: file.js:line
   - Description: ...
   - Impact: ...

2. ...

## Recommendations

1. **Priority 1:** ...
2. **Priority 2:** ...
3. **Priority 3:** ...

## Next Steps

- [ ] Implement virtual scrolling
- [ ] Add debouncing to scroll events
- [ ] Optimize memory management
- [ ] ...
```

---

## 🎯 Success Criteria

Before moving to implementation phases, ensure:

- ✅ Test data generated for all sizes (S/M/L/XL)
- ✅ Baseline metrics documented
- ✅ Bottlenecks identified and prioritized
- ✅ Performance goals defined
- ✅ Test report completed

## 🚦 Ready to Optimize?

Once Phase 1 (Audit) is complete, proceed to:
- **Phase 2:** Virtual Scrolling
- **Phase 3:** Memory Optimization
- **Phase 4:** Event Optimization
- **Phase 5:** Web Workers
- **Phase 6:** Network Optimization

See [PERFORMANCE_OPTIMIZATION_ROADMAP.md](./PERFORMANCE_OPTIMIZATION_ROADMAP.md) for details.

---

**Happy Testing!** 🚀
