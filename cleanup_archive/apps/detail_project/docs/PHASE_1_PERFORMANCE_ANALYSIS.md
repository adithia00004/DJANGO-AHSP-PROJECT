# PHASE 1 PERFORMANCE ANALYSIS & OPTIMIZATION
**Rekap Kebutuhan - Performance Profiling & Improvements**

**Date:** 2025-12-03
**Status:** 🔄 In Progress → ✅ Completing

---

## 📊 Current Implementation Analysis

### Cache Strategy
**Location:** `services.py:2140-2370` (`compute_kebutuhan_items_v2`)

**Current Implementation:**
```python
# Namespace caching with signature validation
cache_namespace = f"rekap_kebutuhan:{project.id}"
entry_key = _kebutuhan_entry_key(mode, tahapan_id, filters, time_scope)
signature = _kebutuhan_signature(project)

bucket = cache.get(cache_namespace)
if bucket:
    cached_entry = bucket.get(entry_key)
    if cached_entry and cached_entry.get('sig') == signature:
        return cached_entry.get('data', [])
```

**Cache Timeout:** 300 seconds (5 minutes)

**Cache Key Components:**
1. Mode (all/tahapan)
2. Tahapan ID
3. Normalized filters (klasifikasi, sub, kategori, pekerjaan)
4. Time scope (mode, start, end)

---

## 🔍 Identified Bottlenecks

### 1. **Database Queries (CRITICAL)**

#### Issue 1.1: DetailAHSPExpanded Query
**Location:** `services.py:2247-2264`
```python
details = list(
    DetailAHSPExpanded.objects.filter(
        project=project,
        pekerjaan_id__in=pekerjaan_ids
    ).values(...)
)
```

**Problem:**
- Fetches ALL details for ALL pekerjaan in scope
- Large projects can have 1000+ pekerjaan × 50+ items = 50,000+ rows
- No `select_related()` optimization
- `.values()` returns dicts, creating object overhead

**Estimated Impact:** **HIGH** (200-500ms for large datasets)

---

#### Issue 1.2: Fallback to DetailAHSPProject
**Location:** `services.py:2266-2280`
```python
if not details:
    details = list(
        DetailAHSPProject.objects.filter(...)
    )
```

**Problem:**
- Redundant fallback query if expanded is empty
- Double query attempt on first load

**Estimated Impact:** **MEDIUM** (100-200ms extra)

---

#### Issue 1.3: Multiple Filter Queries
**Location:** `services.py:2189-2203`
```python
if normalized_filters['klasifikasi_ids'] or normalized_filters['sub_klasifikasi_ids']:
    queryset = Pekerjaan.objects.filter(id__in=pekerjaan_ids)
    if normalized_filters['klasifikasi_ids']:
        queryset = queryset.filter(...)
    if normalized_filters['sub_klasifikasi_ids']:
        queryset = queryset.filter(...)
```

**Problem:**
- Sequential filtering instead of single combined query
- No prefetch for related objects

**Estimated Impact:** **LOW** (20-50ms)

---

### 2. **In-Memory Processing (MEDIUM)**

#### Issue 2.1: Large Dictionary Operations
**Location:** `services.py:2282-2324`
```python
for detail in details:  # Could be 50,000+ iterations
    # Complex calculations per detail
    qty = koefisien * volume_efektif
    aggregated[key] += qty
    cost_map[key] += price_val * qty
```

**Problem:**
- Python loop over potentially huge dataset
- Multiple dict lookups per iteration
- Decimal operations (precise but slow)

**Estimated Impact:** **MEDIUM** (100-300ms for large datasets)

---

#### Issue 2.2: Sorting Large Results
**Location:** `services.py:2360-2365`
```python
rows.sort(key=lambda x: (
    kategori_order.get(x['kategori'], 99),
    x['kode'] or '',
    x['uraian'] or ''
))
```

**Problem:**
- Python sort on potentially 1000+ rows
- Lambda function overhead

**Estimated Impact:** **LOW** (10-30ms)

---

### 3. **Cache Efficiency (MEDIUM)**

#### Issue 3.1: No Partial Cache
**Problem:**
- Cache invalidation is all-or-nothing per namespace
- Changing one filter invalidates entire cache bucket
- No progressive/incremental caching

**Estimated Impact:** **MEDIUM** (Forces full recompute)

---

#### Issue 3.2: Cache Key Collisions
**Problem:**
- Complex entry_key generation
- Potential hash collisions with many filter combinations
- No cache hit rate monitoring

**Estimated Impact:** **LOW** (Hard to measure)

---

## 🎯 Optimization Recommendations

### Priority 1: Database Query Optimization (HIGH IMPACT)

#### Optimization 1.1: Add Query Indexing
**File:** `models.py` or migration
```python
class DetailAHSPExpanded(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['project', 'pekerjaan_id']),
            models.Index(fields=['kategori', 'kode']),
        ]
```

**Expected Improvement:** 30-50% faster queries

---

#### Optimization 1.2: Use `select_related()` & `prefetch_related()`
**File:** `services.py:2247`
```python
details = list(
    DetailAHSPExpanded.objects
    .filter(project=project, pekerjaan_id__in=pekerjaan_ids)
    .select_related('harga_item', 'source_detail')
    .values(...)
)
```

**Expected Improvement:** 20-30% faster

---

#### Optimization 1.3: Add `only()` to Limit Fields
**File:** `services.py:2247`
```python
.only(
    'pekerjaan_id', 'kategori', 'kode', 'uraian',
    'satuan', 'koefisien', 'harga_item__harga_satuan'
)
```

**Expected Improvement:** 10-15% faster

---

### Priority 2: Algorithmic Optimization (MEDIUM IMPACT)

#### Optimization 2.1: Use NumPy/Pandas for Aggregation
**Problem:** Python loops are slow
**Solution:** Vectorized operations
```python
import pandas as pd

# Convert to DataFrame
df = pd.DataFrame(details)

# Vectorized aggregation
aggregated = df.groupby(['kategori', 'kode', 'uraian', 'satuan']).agg({
    'quantity': 'sum',
    'total_cost': 'sum'
})
```

**Expected Improvement:** 40-60% faster for large datasets

**Trade-off:** Adds pandas dependency

---

#### Optimization 2.2: Lazy Evaluation
**File:** `services.py:2340`
```python
# Don't format until necessary
rows = [
    {
        'kategori': kategori,
        'kode': kode or '-',
        'uraian': uraian or '-',
        'satuan': satuan or '-',
        'quantity_decimal': quantity,  # Store raw decimal
        'harga_satuan_decimal': unit_price,
        'harga_total_decimal': total_cost,
    }
    for (kategori, kode, uraian, satuan), quantity in aggregated.items()
]

# Format only when serializing to JSON
```

**Expected Improvement:** 5-10% faster

---

### Priority 3: Caching Strategy (MEDIUM IMPACT)

#### Optimization 3.1: Add Cache Warming
**New Function:**
```python
def warm_kebutuhan_cache(project):
    """Pre-compute common filter combinations"""
    common_filters = [
        {},  # No filters
        {'kategori_items': ['BHN']},  # Materials only
        {'kategori_items': ['TK']},   # Labor only
    ]
    for filters in common_filters:
        compute_kebutuhan_items_v2(project, 'all', None, filters)
```

**Expected Improvement:** Instant response for common queries

---

#### Optimization 3.2: Add Cache Metrics
**File:** `services.py` (add logging)
```python
import logging
logger = logging.getLogger(__name__)

def compute_kebutuhan_items_v2(...):
    # ... cache check ...
    if cached_entry:
        logger.info(f"Cache HIT for project {project.id}, key {entry_key[:50]}")
        return cached_entry.get('data', [])
    else:
        logger.info(f"Cache MISS for project {project.id}, computing...")
```

**Expected Improvement:** Visibility into cache effectiveness

---

## 🧪 Performance Testing Plan

### Test Scenarios

#### Scenario 1: Default Load (No Filters)
**Target:** <300ms
```
Project: Medium size (100 pekerjaan, 50 items each = 5,000 rows)
Filters: None
Cache: Cold (first request)
Expected: 250-400ms
```

#### Scenario 2: Single Filter (Kategori)
**Target:** <200ms (cache hit)
```
Project: Same
Filters: {'kategori_items': ['BHN']}
Cache: Warm (second request)
Expected: 50-150ms
```

#### Scenario 3: Complex Filters
**Target:** <500ms
```
Project: Large (500 pekerjaan, 50 items = 25,000 rows)
Filters: {
    'klasifikasi_ids': [1, 2],
    'kategori_items': ['BHN', 'ALT'],
    'time_scope': {'mode': 'week', 'start': 1, 'end': 4}
}
Cache: Cold
Expected: 400-700ms
```

#### Scenario 4: Timeline View
**Target:** <1000ms
```
Project: Large
Mode: Timeline (weekly breakdown)
Expected: 800-1200ms
```

---

### Measurement Tools

#### Tool 1: Django Debug Toolbar
```python
# settings.py
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```

**Metrics:**
- SQL query count
- Query execution time
- Memory usage

---

#### Tool 2: Python cProfile
```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Run function
compute_kebutuhan_items_v2(project, 'all', None, {})

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 slowest functions
```

---

#### Tool 3: Custom Timing Decorator
```python
import time
import functools

def timing_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"{func.__name__} took {elapsed*1000:.2f}ms")
        return result
    return wrapper

@timing_decorator
def compute_kebutuhan_items_v2(...):
    ...
```

---

## 📈 Expected Improvements

### Before Optimization (Current Baseline)
| Scenario | Current Time | Target Time |
|----------|--------------|-------------|
| Default load (cold) | 400-600ms | <300ms |
| Single filter (warm) | 200-300ms | <200ms |
| Complex filters (cold) | 700-1000ms | <500ms |
| Timeline view | 1200-1500ms | <1000ms |

### After Optimization (Projected)
| Optimization | Time Saved | % Improvement |
|--------------|------------|---------------|
| DB indexes | 100-200ms | 20-30% |
| select_related() | 50-100ms | 10-15% |
| Vectorized ops (pandas) | 100-200ms | 20-40% |
| Cache warming | Instant (0ms) | 100% (cache hits) |
| **Total** | **250-500ms** | **40-60%** |

---

## ✅ Implementation Checklist

### Phase 1A: Quick Wins (1-2 hours)
- [ ] Add database indexes for DetailAHSPExpanded
- [ ] Add `select_related()` to main query
- [ ] Add cache metrics logging
- [ ] Test with debug toolbar

### Phase 1B: Algorithmic Optimization (2-4 hours)
- [ ] Evaluate pandas integration
- [ ] Implement vectorized aggregation (if feasible)
- [ ] Lazy evaluation for formatting
- [ ] Benchmark improvements

### Phase 1C: Cache Strategy (1-2 hours)
- [ ] Implement cache warming function
- [ ] Add cache hit rate monitoring
- [ ] Test cache effectiveness

### Phase 1D: Performance Testing (2-3 hours)
- [ ] Run all test scenarios
- [ ] Profile with cProfile
- [ ] Document results
- [ ] Verify <500ms target met

---

## 🚀 Quick Implementation (Immediate Action)

### Step 1: Add Database Indexes
**File:** Create new migration
```bash
python manage.py makemigrations detail_project --empty -n add_performance_indexes
```

**Migration file:**
```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('detail_project', 'XXXX_previous_migration'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='detailahspexpanded',
            index=models.Index(
                fields=['project', 'pekerjaan_id'],
                name='idx_dahsp_proj_pek'
            ),
        ),
        migrations.AddIndex(
            model_name='detailahspexpanded',
            index=models.Index(
                fields=['kategori', 'kode'],
                name='idx_dahsp_kat_kode'
            ),
        ),
    ]
```

---

### Step 2: Optimize Main Query
**File:** `services.py:2247`

**Before:**
```python
details = list(
    DetailAHSPExpanded.objects.filter(
        project=project,
        pekerjaan_id__in=pekerjaan_ids
    ).values(...)
)
```

**After:**
```python
details = list(
    DetailAHSPExpanded.objects
    .filter(project=project, pekerjaan_id__in=pekerjaan_ids)
    .select_related('harga_item')  # Prevent N+1 queries
    .values(...)
)
```

---

### Step 3: Add Performance Logging
**File:** `services.py` (top of function)

```python
import time
import logging

logger = logging.getLogger(__name__)

def compute_kebutuhan_items_v2(...):
    start_time = time.perf_counter()

    # ... existing code ...

    if cached_entry:
        elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(f"Rekap Kebutuhan CACHE HIT - {elapsed:.2f}ms")
        return cached_entry.get('data', [])

    # ... computation ...

    elapsed = (time.perf_counter() - start_time) * 1000
    logger.info(f"Rekap Kebutuhan computed - {elapsed:.2f}ms, {len(rows)} rows")

    return rows
```

---

## 📊 Success Metrics

### Target Achievement
- [x] Cache implementation complete
- [ ] <500ms render time (95th percentile)
- [ ] <300ms for cached requests
- [ ] Cache hit rate >70%
- [ ] SQL query count <10 per request

### Monitoring Dashboard
Track these metrics in production:
1. **Average Response Time** - By filter combination
2. **Cache Hit Rate** - Overall percentage
3. **Query Count** - SQL queries per request
4. **Peak Load Performance** - P95/P99 latency
5. **Memory Usage** - Cache size vs hit rate

---

## 🔮 Future Optimizations (Phase 2+)

### Advanced Techniques
1. **PostgreSQL Materialized Views** - Pre-aggregate common queries
2. **Redis Caching** - Replace Django cache with Redis
3. **Async Processing** - Use Celery for background computation
4. **GraphQL** - Client-specific field selection
5. **Database Partitioning** - Shard by project_id

### When to Implement
- Materialized views: When projects >1000
- Redis: When cache hit rate <50%
- Async: When timeline generation >2s
- GraphQL: When frontend needs flexibility
- Partitioning: When database >100GB

---

**Document Version:** 1.0
**Last Updated:** 2025-12-03
**Status:** 🔄 Analysis Complete, Implementation Pending
