# 🚀 Performance Optimization Recommendations

**Generated:** 2026-01-10
**Based on:** Phase 2 Load Test Results

---

## 📊 Executive Summary

Dari hasil load test Phase 2, teridentifikasi **3 endpoint lambat** yang membutuhkan optimasi:

| Endpoint | Current Performance | Target | Priority |
|----------|-------------------|--------|----------|
| **V2 Rekap Kebutuhan Weekly** | 3100-6400ms | <1000ms | 🔥 CRITICAL |
| **V2 Chart Data** | 960-2086ms | <500ms | ⚠️ HIGH |
| **V2 Kurva S Harga** | 360ms | <300ms | 🟡 MEDIUM |

**Impact:**
- **6.4 detik** response time akan membuat user timeout
- Concurrent requests dapat memicu database overload
- User experience sangat buruk

---

## 🔥 CRITICAL: V2 Rekap Kebutuhan Weekly

### **Current Performance:**
```
Median: 3100ms (3.1 seconds)
P95: 5000ms (5.0 seconds)
P99: 6400ms (6.4 seconds!)
Max: 6400ms
Requests: 5
```

### **File:** [detail_project/views_api.py:5692](detail_project/views_api.py#L5692)

### **Root Cause Analysis:**

#### 1. **Complex N+1 Query Pattern**
```python
for progress in weekly_progress:
    # Get components for this pekerjaan (DetailAHSPProject)
    components = DetailAHSPProject.objects.filter(
        pekerjaan_id=pkj_id
    ).select_related('harga_item')  # ← Query per pekerjaan!

    for comp in components:
        # Get volume for this pekerjaan
        vol_pek = VolumePekerjaan.objects.get(pekerjaan_id=pkj_id)  # ← Another query!
```

**Problem:**
- If 20 weeks × 50 pekerjaan = **1000+ database queries**
- Each query has ~5-10ms latency
- Total: 1000 × 5ms = **5000ms+**

#### 2. **Heavy Aggregation in Python**
```python
# Building nested dictionaries in Python
for week_num in sorted(weekly_data.keys()):
    for kategori in ['TK', 'BHN', 'ALT', 'LAIN']:
        items_list = []
        for item_data in week['items_by_kategori'][kategori].values():
            items_list.append({...})  # ← Nested loops
```

**Problem:**
- Heavy CPU processing in Python
- Multiple nested loops
- Large data structures in memory

---

### **💡 SOLUTION 1: Query Optimization (Quick Win)**

**Estimated Improvement:** 3100ms → 800-1200ms (60-70% faster)

```python
def api_rekap_kebutuhan_weekly(request: HttpRequest, project_id: int) -> JsonResponse:
    try:
        from dashboard.models import Project
        project = get_object_or_404(Project, id=project_id)
    except Exception as e:
        return JsonResponse({'error': 'Project not found'}, status=404)

    # OPTIMIZATION 1: Prefetch related data to avoid N+1 queries
    from .models import PekerjaanProgressWeekly, DetailAHSPProject, VolumePekerjaan

    # Get all weekly progress with prefetched pekerjaan data
    weekly_progress = PekerjaanProgressWeekly.objects.filter(
        project=project
    ).select_related(
        'pekerjaan'
    ).prefetch_related(
        'pekerjaan__detailahspproject_set__harga_item',  # Prefetch components
        'pekerjaan__volumepekerjaan'                      # Prefetch volumes
    ).order_by('week_number')

    # OPTIMIZATION 2: Build lookup dict for volumes (avoid repeated queries)
    volume_lookup = {}
    for vol in VolumePekerjaan.objects.filter(
        pekerjaan__project=project
    ).select_related('pekerjaan'):
        volume_lookup[vol.pekerjaan_id] = vol.quantity

    # Step 3: Build week-by-week requirements (now using prefetched data)
    weekly_data = {}

    for progress in weekly_progress:
        week_num = progress.week_number
        pkj = progress.pekerjaan  # Already loaded via select_related
        proportion = progress.planned_proportion

        if week_num not in weekly_data:
            weekly_data[week_num] = {
                'week_number': week_num,
                'week_start': progress.week_start_date.isoformat(),
                'week_end': progress.week_end_date.isoformat(),
                'items_by_kategori': {
                    'TK': {},
                    'BHN': {},
                    'ALT': {},
                    'LAIN': {}
                }
            }

        # Use prefetched components (NO additional query!)
        components = pkj.detailahspproject_set.all()  # ← Already loaded

        # Get volume from lookup dict (NO query!)
        volume = Decimal(str(volume_lookup.get(pkj.id, 1.0)))

        for comp in components:
            harga_item = comp.harga_item  # Already loaded via prefetch
            kategori = harga_item.kategori
            kode = harga_item.kode_item or harga_item.uraian
            koefisien = Decimal(str(comp.koefisien))

            # Calculate weekly requirement
            weekly_qty = volume * koefisien * Decimal(str(proportion)) / Decimal('100')

            # Aggregate by item
            items_dict = weekly_data[week_num]['items_by_kategori'][kategori]
            key = kode

            if key not in items_dict:
                items_dict[key] = {
                    'kode': kode,
                    'uraian': harga_item.uraian,
                    'satuan': harga_item.satuan,
                    'quantity': Decimal('0'),
                    'pekerjaan_breakdown': {}
                }

            items_dict[key]['quantity'] += weekly_qty
            items_dict[key]['pekerjaan_breakdown'][str(pkj.id)] = float(weekly_qty)

    # ... rest of the code stays the same
```

**Key Changes:**
1. ✅ `prefetch_related()` to load all components in 2-3 queries instead of 1000+
2. ✅ Pre-build `volume_lookup` dict to avoid repeated queries
3. ✅ Use already-loaded relations (no additional queries in loop)

**Expected Result:**
- Queries: 1000+ → 5-10 queries
- Response time: 3100ms → 800-1200ms

---

### **💡 SOLUTION 2: Database-Level Aggregation (Best Performance)**

**Estimated Improvement:** 3100ms → 200-500ms (85-95% faster)

```python
def api_rekap_kebutuhan_weekly(request: HttpRequest, project_id: int) -> JsonResponse:
    """
    Optimized version using database aggregation instead of Python loops.
    """
    try:
        from dashboard.models import Project
        project = get_object_or_404(Project, id=project_id)
    except Exception as e:
        return JsonResponse({'error': 'Project not found'}, status=404)

    from django.db.models import F, Sum, DecimalField
    from django.db.models.functions import Coalesce
    from .models import PekerjaanProgressWeekly, DetailAHSPProject, VolumePekerjaan

    # OPTIMIZATION: Single query with database aggregation
    weekly_items = DetailAHSPProject.objects.filter(
        pekerjaan__project=project,
        pekerjaan__pekerjaanprogressweekly__project=project
    ).annotate(
        week_number=F('pekerjaan__pekerjaanprogressweekly__week_number'),
        week_start=F('pekerjaan__pekerjaanprogressweekly__week_start_date'),
        week_end=F('pekerjaan__pekerjaanprogressweekly__week_end_date'),
        proportion=F('pekerjaan__pekerjaanprogressweekly__planned_proportion'),
        volume=Coalesce(F('pekerjaan__volumepekerjaan__quantity'), 1.0),
        kategori_item=F('harga_item__kategori'),
        kode_item=F('harga_item__kode_item'),
        uraian_item=F('harga_item__uraian'),
        satuan_item=F('harga_item__satuan'),
        weekly_qty=(
            F('volume') * F('koefisien') * F('proportion') / 100.0
        )
    ).values(
        'week_number', 'week_start', 'week_end',
        'kategori_item', 'kode_item', 'uraian_item', 'satuan_item'
    ).annotate(
        total_quantity=Sum('weekly_qty', output_field=DecimalField())
    ).order_by('week_number', 'kategori_item', 'kode_item')

    # Build response from aggregated results
    weekly_data = {}
    for item in weekly_items:
        week_num = item['week_number']
        if week_num not in weekly_data:
            weekly_data[week_num] = {
                'week_number': week_num,
                'week_start': item['week_start'].isoformat(),
                'week_end': item['week_end'].isoformat(),
                'items_by_kategori': {
                    'TK': {},
                    'BHN': {},
                    'ALT': {},
                    'LAIN': {}
                }
            }

        kategori = item['kategori_item']
        kode = item['kode_item'] or item['uraian_item']

        weekly_data[week_num]['items_by_kategori'][kategori][kode] = {
            'kode': kode,
            'uraian': item['uraian_item'],
            'satuan': item['satuan_item'],
            'quantity': float(item['total_quantity'])
        }

    # ... rest remains similar but much simpler
```

**Key Changes:**
1. ✅ Single query with database aggregation (SUM, GROUP BY)
2. ✅ Database does the heavy lifting (much faster than Python)
3. ✅ Minimal Python processing
4. ✅ Only 1-2 queries total

**Expected Result:**
- Queries: 1000+ → 1-2 queries
- Response time: 3100ms → 200-500ms
- CPU usage: Significantly reduced

---

### **💡 SOLUTION 3: Redis Caching (Production-Ready)**

**Estimated Improvement:** 3100ms → 10-50ms (99% faster for cached)

```python
from django.core.cache import cache
from hashlib import md5
import json

def api_rekap_kebutuhan_weekly(request: HttpRequest, project_id: int) -> JsonResponse:
    """
    Cached version with Redis - BEST for production.
    """
    # Generate cache key based on project data version
    cache_key = f'rekap_weekly_v2:{project_id}:{_get_project_version(project_id)}'

    # Try to get from cache
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.info(f"[Rekap Weekly] Cache HIT for project {project_id}")
        return JsonResponse(cached_data)

    logger.info(f"[Rekap Weekly] Cache MISS for project {project_id}, generating...")

    # Generate data (using optimized query from Solution 1 or 2)
    response_data = _generate_rekap_weekly_data(project_id)

    # Cache for 15 minutes (or until project data changes)
    cache.set(cache_key, response_data, timeout=900)

    return JsonResponse(response_data)

def _get_project_version(project_id):
    """
    Get version hash based on last update timestamp.
    Invalidates cache when project data changes.
    """
    from dashboard.models import Project
    from .models import DetailAHSPProject, PekerjaanProgressWeekly

    # Get latest update times
    project_updated = Project.objects.filter(id=project_id).values_list('updated_at', flat=True).first()
    detail_updated = DetailAHSPProject.objects.filter(
        pekerjaan__project_id=project_id
    ).values_list('updated_at', flat=True).order_by('-updated_at').first()

    # Create version hash
    version_str = f"{project_updated}:{detail_updated}"
    return md5(version_str.encode()).hexdigest()[:8]
```

**Key Changes:**
1. ✅ Cache results in Redis (in-memory)
2. ✅ Auto-invalidate when project data changes
3. ✅ 99% of requests served from cache (<50ms)
4. ✅ Only recalculate when data actually changes

**Expected Result:**
- First request: 800ms (optimized query)
- Subsequent requests: 10-50ms (from cache)
- Cache hit rate: 95%+

**Redis Setup:**
```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

---

## ⚠️ HIGH PRIORITY: V2 Chart Data

### **Current Performance:**
```
Median: 960ms
P95: 1900ms
P99: 2086ms
Max: 2086ms
Requests: 5
```

### **File:** [detail_project/views_api.py](detail_project/views_api.py) (line number varies)

### **Recommended Optimizations:**

#### **1. Selective Data Loading**
```python
# Instead of loading ALL data
chart_data = get_all_chart_data(project)

# Load only required date range
from_date = request.GET.get('from_date')
to_date = request.GET.get('to_date')
chart_data = get_chart_data_filtered(project, from_date, to_date)
```

#### **2. Pre-calculate Static Data**
```python
# Pre-calculate during project save, not on every request
class Project(models.Model):
    chart_data_cache = models.JSONField(null=True, blank=True)
    chart_data_updated = models.DateTimeField(null=True, blank=True)

    def update_chart_cache(self):
        """Update cached chart data."""
        self.chart_data_cache = calculate_chart_data(self)
        self.chart_data_updated = timezone.now()
        self.save(update_fields=['chart_data_cache', 'chart_data_updated'])
```

#### **3. Pagination for Large Datasets**
```python
# Return only visible data points
def api_chart_data(request, project_id):
    limit = int(request.GET.get('limit', 100))
    offset = int(request.GET.get('offset', 0))

    data_points = ChartDataPoint.objects.filter(
        project_id=project_id
    )[offset:offset+limit]

    return JsonResponse({
        'data': list(data_points.values()),
        'total': ChartDataPoint.objects.filter(project_id=project_id).count()
    })
```

**Expected Improvement:** 960ms → 200-400ms

---

## 🟡 MEDIUM PRIORITY: V2 Kurva S Harga

### **Current Performance:**
```
Single request: 360ms
```

### **Recommended Optimizations:**

#### **1. Use Database Aggregation**
```python
from django.db.models import Sum, F, DecimalField

# Instead of Python loops
kurva_data = []
for week in weeks:
    total = sum(item.harga for item in get_items_for_week(week))
    kurva_data.append({'week': week, 'total': total})

# Use database aggregation
kurva_data = WeeklyData.objects.filter(
    project=project
).values('week_number').annotate(
    total_harga=Sum(F('quantity') * F('harga_satuan'), output_field=DecimalField())
).order_by('week_number')
```

#### **2. Cache with Short TTL**
```python
@cached(timeout=300)  # 5 minutes
def get_kurva_s_harga(project_id):
    # ... calculation
    return kurva_data
```

**Expected Improvement:** 360ms → 100-150ms

---

## 📊 Implementation Priority

### **Phase 1: Quick Wins (This Week)**
1. ✅ Fix template export (DONE)
2. 🔥 Optimize V2 Rekap Weekly with Solution 1 (prefetch_related)
3. ⚠️ Add pagination to Chart Data endpoint

**Expected Impact:**
- V2 Rekap Weekly: 3100ms → 800ms (74% faster)
- Chart Data: 960ms → 400ms (58% faster)

### **Phase 2: Database Optimization (Next Week)**
1. 🔥 Implement Solution 2 for V2 Rekap Weekly (database aggregation)
2. 🟡 Optimize Kurva S Harga with database queries

**Expected Impact:**
- V2 Rekap Weekly: 800ms → 200-500ms (additional 60-75% faster)
- Kurva S Harga: 360ms → 100ms (72% faster)

### **Phase 3: Production Caching (Week 3)**
1. 🔥 Setup Redis caching
2. 🔥 Implement Solution 3 for V2 Rekap Weekly
3. ⚠️ Cache Chart Data with smart invalidation

**Expected Impact:**
- V2 Rekap Weekly: 200ms → 10-50ms (95% cache hit rate)
- Chart Data: 400ms → 20-100ms (80% cache hit rate)
- Overall load: 80% reduction

---

## 🎯 Success Metrics

### **After Quick Wins (Phase 1):**
- [ ] V2 Rekap Weekly < 1000ms (P95)
- [ ] Chart Data < 500ms (P95)
- [ ] Overall P95 < 1500ms (excluding auth)
- [ ] Success rate maintained at 99%+

### **After Database Optimization (Phase 2):**
- [ ] V2 Rekap Weekly < 500ms (P95)
- [ ] Chart Data < 300ms (P95)
- [ ] Kurva S Harga < 200ms (P95)
- [ ] Database query count reduced by 80%+

### **After Caching (Phase 3):**
- [ ] Cache hit rate > 90%
- [ ] Cached responses < 100ms
- [ ] Database load reduced by 70%+
- [ ] Can handle 100+ concurrent users

---

## 🔧 Monitoring & Validation

### **Add Performance Logging:**
```python
import time
import logging

logger = logging.getLogger(__name__)

def api_rekap_kebutuhan_weekly(request, project_id):
    start_time = time.time()

    # ... processing

    elapsed = (time.time() - start_time) * 1000
    logger.info(
        f"[Perf] Rekap Weekly project={project_id} "
        f"time={elapsed:.0f}ms queries={len(connection.queries)}"
    )

    # Alert if too slow
    if elapsed > 2000:
        logger.warning(f"[Perf] SLOW ENDPOINT: Rekap Weekly took {elapsed:.0f}ms")

    return response
```

### **Database Query Analysis:**
```python
from django.db import connection
from django.test.utils import override_settings

@override_settings(DEBUG=True)
def analyze_queries():
    # Clear existing queries
    connection.queries_log.clear()

    # Call your endpoint
    response = api_rekap_kebutuhan_weekly(request, 160)

    # Analyze
    print(f"Total queries: {len(connection.queries)}")
    for i, query in enumerate(connection.queries, 1):
        print(f"{i}. {query['time']}s - {query['sql'][:100]}")
```

---

## 📝 Testing After Optimization

```bash
# Run load test again
locust -f load_testing/locustfile.py --headless \
  -u 10 -r 2 -t 90s \
  --host=http://localhost:8000 \
  --csv=hasil_test_v8_phase2_optimized \
  --html=hasil_test_v8_phase2_optimized.html

# Expected improvements:
# - V2 Rekap Weekly: 3100ms → 800ms (Phase 1)
# - Chart Data: 960ms → 400ms
# - Template Export: WORKING
# - Success Rate: 100%
```

---

## ✅ Summary

| Optimization | Complexity | Time to Implement | Impact | Priority |
|-------------|------------|-------------------|---------|----------|
| **Prefetch Related** | Low | 1-2 hours | High (74% faster) | 🔥 DO NOW |
| **Database Aggregation** | Medium | 4-6 hours | Very High (85% faster) | ⚠️ THIS WEEK |
| **Redis Caching** | Medium | 4-8 hours | Extreme (99% faster) | 🟡 NEXT WEEK |
| **Chart Pagination** | Low | 2-3 hours | Medium (58% faster) | ⚠️ THIS WEEK |
| **Pre-calculate Data** | High | 1-2 days | High (90% faster) | 🟡 FUTURE |

**Recommended Path:**
1. **Today**: Implement prefetch_related for V2 Rekap Weekly
2. **This Week**: Add database aggregation + Chart pagination
3. **Next Week**: Setup Redis caching
4. **Re-test**: Run load test to measure improvements

---

**Last Updated:** 2026-01-10
**Status:** Recommendations ready for implementation
