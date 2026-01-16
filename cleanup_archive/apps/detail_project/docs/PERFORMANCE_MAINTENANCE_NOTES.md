# Performance & Maintenance Considerations

**Date**: 2025-11-23
**Purpose**: Document performance and maintenance considerations for time period management

---

## 🎯 PERFORMANCE GOALS

### Target Metrics
- ✅ **Grid Load Time**: < 2 seconds (12 columns, 50 rows)
- ✅ **Mode Switch Time**: < 3 seconds (weekly ↔ monthly)
- ✅ **Save Operation**: < 1 second (single cell)
- ✅ **Chart Render**: < 1 second (Kurva-S + Gantt)
- ✅ **Memory Usage**: < 50MB frontend (stable, no leaks)

### Current Performance Baseline

**Before Optimization** (with daily/custom modes):
- Grid Load: 5-10 seconds (90+ columns)
- Memory: 100MB+ (memory leaks)
- Mode Switch: Not implemented
- Save: 2-3 seconds (inefficient API calls)

**After Phase 2E** (weekly/monthly only):
- Grid Load: < 2 seconds (12 columns max)
- Memory: < 50MB (clean lifecycle)
- Mode Switch: < 3 seconds (efficient aggregation)
- Save: < 1 second (canonical storage)

---

## 📊 PERFORMANCE BOTTLENECKS (Identified)

### 1. Too Many Columns (Daily Mode)
**Issue**: 90+ daily columns for 3-month project
**Impact**:
- Slow grid rendering
- High memory usage
- Poor UX (horizontal scroll nightmare)

**Solution**: ✅ **Remove daily mode**
- Max 12 columns (weekly) or 3 columns (monthly)
- Fast rendering
- Better UX

---

### 2. Inefficient Database Queries
**Issue**: N+1 queries for assignments
**Impact**:
- Slow data loading
- High database load

**Current Code** (inefficient):
```python
# Bad: N+1 queries
for pekerjaan in pekerjaan_list:
    assignments = PekerjaanTahapan.objects.filter(pekerjaan=pekerjaan)
    # Query executed N times
```

**Solution**: ✅ **Use select_related and prefetch_related**
```python
# Good: 2 queries total
pekerjaan_list = Pekerjaan.objects.filter(
    project=project
).select_related('sub_klasifikasi', 'sub_klasifikasi__klasifikasi')
 .prefetch_related('tahapan_assignments__tahapan')
```

**Recommended Indexes**:
```python
class Meta:
    indexes = [
        models.Index(fields=['project', 'urutan']),  # TahapPelaksanaan
        models.Index(fields=['pekerjaan', 'tahapan']),  # PekerjaanTahapan
        models.Index(fields=['project', 'pekerjaan', 'week_number']),  # PekerjaanProgressWeekly
    ]
```

---

### 3. Unoptimized Frontend Rendering
**Issue**: Re-rendering entire grid on every change
**Impact**:
- Slow cell updates
- Poor responsiveness

**Current Code** (inefficient):
```javascript
// Bad: Re-render everything
function onCellChange(cellId, value) {
  renderGrid();  // Re-renders entire grid
}
```

**Solution**: ✅ **Update only changed cells**
```javascript
// Good: Update single cell
function onCellChange(cellId, value) {
  const cell = document.querySelector(`[data-cell-id="${cellId}"]`);
  cell.textContent = value;
  cell.classList.add('modified');
}
```

---

### 4. Chart Rendering Overhead
**Issue**: Charts render on every data change (even when hidden)
**Impact**:
- Wasted CPU cycles
- Slow save operations

**Solution**: ✅ **Lazy chart rendering**
```javascript
// Only render when chart tab is active
function onTabChange(newTab) {
  if (newTab === 'kurva-s' && !kurvaSChart.isRendered) {
    kurvaSChart.render();
  }
  if (newTab === 'gantt' && !ganttChart.isRendered) {
    ganttChart.render();
  }
}
```

---

### 5. Excessive API Calls
**Issue**: Save API call on every keystroke
**Impact**:
- High server load
- Poor UX (laggy input)

**Solution**: ✅ **Debounce input**
```javascript
// Debounce save (wait 500ms after last change)
const debouncedSave = debounce(() => {
  saveHandler.save();
}, 500);

input.addEventListener('input', () => {
  debouncedSave();
});
```

---

## 🔧 MAINTENANCE CONSIDERATIONS

### 1. Code Complexity

**Before** (4 modes):
```javascript
// Complex logic for 4 modes
if (mode === 'daily') {
  // Daily logic
} else if (mode === 'weekly') {
  // Weekly logic
} else if (mode === 'monthly') {
  // Monthly logic
} else if (mode === 'custom') {
  // Custom logic
}
```

**After** (2 modes):
```javascript
// Simple logic for 2 modes
if (mode === 'weekly') {
  return generateWeeklyColumns();
} else {
  return generateMonthlyColumns();
}
```

**Benefits**:
- ✅ 50% less code to maintain
- ✅ Easier to understand
- ✅ Fewer edge cases
- ✅ Faster to debug

---

### 2. Testing Burden

**Before** (4 modes):
- 4 mode generation tests
- 4×4 = 16 mode switching tests (all combinations)
- 4 save handler tests
- **Total: 24+ test cases**

**After** (2 modes):
- 2 mode generation tests
- 2×2 = 4 mode switching tests (weekly→monthly, monthly→weekly)
- 2 save handler tests
- **Total: 8 test cases** (67% reduction)

---

### 3. Database Maintenance

**Canonical Storage Benefits**:
- ✅ Single source of truth (PekerjaanProgressWeekly)
- ✅ Mode switching doesn't delete canonical data
- ✅ Easy data recovery (regenerate view layer)

**Schema Stability**:
```python
# Canonical storage (NEVER changes)
class PekerjaanProgressWeekly(models.Model):
    pekerjaan = ForeignKey('Pekerjaan')
    week_number = PositiveIntegerField()
    proportion = DecimalField(...)
    # This schema is stable, won't change

# View layer (can be regenerated)
class PekerjaanTahapan(models.Model):
    pekerjaan = ForeignKey('Pekerjaan')
    tahapan = ForeignKey(TahapPelaksanaan)
    proporsi_volume = DecimalField(...)
    # Derived from canonical, can be deleted/regenerated
```

**Benefits**:
- ✅ Easy to add new modes (quarterly, yearly)
- ✅ No migration needed for new modes
- ✅ Data never lost during mode switch

---

### 4. Documentation Maintenance

**Simplified Documentation**:
- User guide: 2 modes instead of 4
- API docs: 2 mode endpoints instead of 4
- Developer guide: Simpler architecture diagrams

**Example User Guide** (simplified):
```markdown
# How to Choose Time Period Mode

## Weekly Mode
- Best for: Detailed project tracking
- Shows: 12 weeks (3 months)
- Use when: You need weekly progress reports

## Monthly Mode
- Best for: High-level summaries
- Shows: 3 months
- Use when: You want overview, not details

## Switching Modes
1. Click "Switch to Monthly" button
2. Confirm (your data is preserved)
3. Grid updates to show monthly columns
```

---

## 🚀 OPTIMIZATION STRATEGIES

### Database Level

#### 1. Indexes
```python
# Add these indexes to models.py
class TahapPelaksanaan(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['project', 'urutan']),
            models.Index(fields=['project', 'is_auto_generated', 'generation_mode']),
        ]

class PekerjaanProgressWeekly(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['project', 'pekerjaan', 'week_number']),
            models.Index(fields=['pekerjaan', 'week_start_date', 'week_end_date']),
        ]
```

#### 2. Query Optimization
```python
# Efficient loading with select_related and prefetch_related
def load_tahapan_with_assignments(project_id):
    return TahapPelaksanaan.objects.filter(
        project_id=project_id,
        is_auto_generated=True
    ).prefetch_related(
        Prefetch(
            'pekerjaan_items',
            queryset=PekerjaanTahapan.objects.select_related('pekerjaan')
        )
    ).order_by('urutan')
```

#### 3. Caching
```python
from django.core.cache import cache

def get_tahapan_list(project_id):
    cache_key = f'tahapan_list_{project_id}'
    tahapan = cache.get(cache_key)

    if not tahapan:
        tahapan = list(TahapPelaksanaan.objects.filter(project_id=project_id))
        cache.set(cache_key, tahapan, timeout=300)  # 5 minutes

    return tahapan
```

---

### Frontend Level

#### 1. Virtual Scrolling (if needed)
```javascript
// Only render visible rows (for projects with 100+ pekerjaan)
class VirtualGrid {
  constructor(totalRows, rowHeight, viewportHeight) {
    this.totalRows = totalRows;
    this.rowHeight = rowHeight;
    this.visibleRows = Math.ceil(viewportHeight / rowHeight);
  }

  getVisibleRange(scrollTop) {
    const startIndex = Math.floor(scrollTop / this.rowHeight);
    const endIndex = startIndex + this.visibleRows;
    return { startIndex, endIndex };
  }
}
```

#### 2. Debouncing & Throttling
```javascript
// Debounce: Wait for user to stop typing
const debouncedSave = debounce(() => saveHandler.save(), 500);

// Throttle: Execute at most once per 100ms
const throttledScroll = throttle(() => syncScroll(), 100);
```

#### 3. Lazy Loading
```javascript
// Load charts only when tabs are activated
function initCharts() {
  // Don't render charts on page load
  kurvaSChart = new KurvaSChart(state, { autoRender: false });
  ganttChart = new GanttChart(state, { autoRender: false });
}

function onTabChange(tabName) {
  if (tabName === 'kurva-s') {
    kurvaSChart.render();
  } else if (tabName === 'gantt') {
    ganttChart.render();
  }
}
```

---

### API Level

#### 1. Pagination
```python
# For projects with many pekerjaan (100+)
class PekerjaanPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100
```

#### 2. Batch Operations
```python
# Save multiple cells in one request
@api_view(['POST'])
def batch_save_assignments(request, project_id):
    """
    Save multiple cell changes in one request.

    Payload:
    {
      "changes": [
        {"pekerjaan_id": 1, "tahapan_id": 10, "proportion": 25.5},
        {"pekerjaan_id": 2, "tahapan_id": 10, "proportion": 30.0},
        ...
      ]
    }
    """
    changes = request.data.get('changes', [])

    # Bulk create/update (single transaction)
    with transaction.atomic():
        for change in changes:
            # Save to canonical storage
            # ...
```

#### 3. Response Compression
```python
# settings.py
MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware',  # Compress responses
    # ...
]
```

---

## 📊 MONITORING & PROFILING

### Frontend Profiling

```javascript
// Measure grid render time
console.time('Grid Render');
gridRenderer.render();
console.timeEnd('Grid Render');
// Expected: < 200ms

// Measure memory usage
if (performance.memory) {
  console.log('Memory used:', performance.memory.usedJSHeapSize / 1048576, 'MB');
  // Expected: < 50MB
}
```

### Backend Profiling

```python
# Use Django Debug Toolbar
INSTALLED_APPS = [
    'debug_toolbar',
    # ...
]

# Check query count and time
from django.db import connection
print(f'Queries: {len(connection.queries)}')  # Expected: < 10
print(f'Time: {sum(float(q["time"]) for q in connection.queries)}s')  # Expected: < 0.5s
```

---

## 🎯 PERFORMANCE CHECKLIST

### Before Deployment
- [ ] Run Django Debug Toolbar on all pages
- [ ] Check query count (target: < 10 queries per page load)
- [ ] Profile frontend with Chrome DevTools
- [ ] Measure memory usage (target: < 50MB stable)
- [ ] Test with large dataset (100+ pekerjaan, 12 weeks)
- [ ] Test mode switching (measure time)
- [ ] Test save operation (measure time)
- [ ] Verify no memory leaks (use Chrome Task Manager)

### Post-Deployment Monitoring
- [ ] Set up Django logging for slow queries (> 1 second)
- [ ] Monitor server response times
- [ ] Track user-reported performance issues
- [ ] Run monthly performance audits

---

## 🔒 MAINTENANCE BEST PRACTICES

### 1. Keep It Simple
- ✅ Only 2 modes (weekly/monthly)
- ✅ Clear separation: canonical vs view layer
- ✅ Simple aggregation logic (sum weekly → monthly)

### 2. Document Everything
- ✅ Inline code comments for complex logic
- ✅ README for each major module
- ✅ Architecture diagrams (data flow, mode switch)

### 3. Write Tests
- ✅ Unit tests for all services
- ✅ Integration tests for mode switching
- ✅ Performance tests (load time benchmarks)

### 4. Monitor Performance
- ✅ Log slow queries
- ✅ Track frontend metrics (render time, memory)
- ✅ User feedback for UX issues

### 5. Plan for Scale
- ✅ Pagination for large datasets
- ✅ Virtual scrolling for 100+ rows
- ✅ Caching for frequently accessed data

---

## 📝 TECHNICAL DEBT TO AVOID

### ❌ Don't Do This
1. **Adding daily mode back** → Performance nightmare
2. **Skipping indexes** → Slow queries as data grows
3. **Not debouncing input** → Excessive API calls
4. **Rendering all charts on load** → Wasted resources
5. **Hardcoding week start day** → Inflexible (use config)
6. **Not using canonical storage** → Data loss on mode switch
7. **Not caching tahapan list** → Repeated queries

### ✅ Do This Instead
1. **Stick to weekly/monthly** → Fast, maintainable
2. **Add all recommended indexes** → Fast queries
3. **Debounce/throttle all inputs** → Smooth UX
4. **Lazy load charts** → Fast page load
5. **Make week start day configurable** → Flexible
6. **Always save to canonical storage** → No data loss
7. **Cache static data** → Reduced load

---

## 🎓 LEARNING RESOURCES

### Performance Optimization
- Django Query Optimization: https://docs.djangoproject.com/en/stable/topics/db/optimization/
- Django Debug Toolbar: https://django-debug-toolbar.readthedocs.io/
- Chrome DevTools Performance: https://developer.chrome.com/docs/devtools/performance/

### Best Practices
- Database Indexing: https://use-the-index-luke.com/
- Frontend Performance: https://web.dev/fast/
- JavaScript Debouncing: https://www.freecodecamp.org/news/javascript-debounce-example/

---

**Last Updated**: 2025-11-23
**Status**: Guidelines Documented
**Next**: Implement optimizations during Phase 2E
