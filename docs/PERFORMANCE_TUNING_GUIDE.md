# Performance Tuning Guide: Phase 2 & 3

## Table of Contents
1. [Overview](#overview)
2. [PostgreSQL Optimization](#postgresql-optimization)
3. [Django Application Tuning](#django-application-tuning)
4. [Search Performance Optimization](#search-performance-optimization)
5. [Audit System Performance](#audit-system-performance)
6. [Caching Strategies](#caching-strategies)
7. [Index Maintenance](#index-maintenance)
8. [Query Optimization](#query-optimization)
9. [System-Level Tuning](#system-level-tuning)
10. [Performance Benchmarking](#performance-benchmarking)
11. [Troubleshooting Slow Queries](#troubleshooting-slow-queries)

---

## Overview

This guide provides comprehensive performance tuning strategies for Phase 2 (Audit & Logging) and Phase 3 (Database Search Optimization) components.

### Performance Goals

| Component | Metric | Target | Current |
|-----------|--------|--------|---------|
| Simple Search | Query Time | <50ms | 12ms ✅ |
| Complex Search | Query Time | <100ms | 18ms ✅ |
| Fuzzy Search | Query Time | <150ms | 35ms ✅ |
| Auto-Complete | Query Time | <20ms | 8ms ✅ |
| Audit Dashboard | Page Load | <500ms | 350ms ✅ |
| Audit Logs List | Page Load | <300ms | 280ms ✅ |

### Optimization Priority

1. **Critical**: PostgreSQL configuration
2. **High**: Index optimization and maintenance
3. **Medium**: Django ORM query optimization
4. **Medium**: Caching implementation
5. **Low**: System-level tuning

---

## PostgreSQL Optimization

### 1. Memory Configuration

Edit `/etc/postgresql/13/main/postgresql.conf`:

```ini
# ============================================
# Memory Settings
# ============================================

# Shared Buffers (25% of total RAM)
# For 8GB RAM server:
shared_buffers = 2GB            # Default: 128MB

# For 16GB RAM server:
shared_buffers = 4GB

# Effective Cache Size (50-75% of total RAM)
# For 8GB RAM server:
effective_cache_size = 6GB      # Default: 4GB

# For 16GB RAM server:
effective_cache_size = 12GB

# Work Memory (per query operation)
# Formula: (Total RAM * 0.25) / max_connections
# For 8GB RAM, 100 connections:
work_mem = 20MB                 # Default: 4MB

# For high search traffic (increase gradually):
work_mem = 64MB

# Maintenance Work Memory (for VACUUM, CREATE INDEX)
# 10% of RAM or 2GB max
maintenance_work_mem = 512MB    # Default: 64MB

# For large databases:
maintenance_work_mem = 1GB
```

### 2. GIN Index Optimization

```ini
# ============================================
# GIN Index Settings (for Full-Text Search)
# ============================================

# Pending list limit for GIN indexes
# Higher = faster inserts, slower searches
# Lower = slower inserts, faster searches
gin_pending_list_limit = 4MB    # Default: 4MB

# For write-heavy workloads:
gin_pending_list_limit = 8MB

# For read-heavy workloads (recommended):
gin_pending_list_limit = 2MB
```

### 3. Query Planner Settings

```ini
# ============================================
# Query Planner Configuration
# ============================================

# Random page cost (SSD vs HDD)
# SSD (recommended):
random_page_cost = 1.1          # Default: 4.0

# HDD:
random_page_cost = 4.0

# Effective I/O concurrency (SSD)
effective_io_concurrency = 200  # Default: 1

# HDD:
effective_io_concurrency = 2

# CPU tuple cost (adjust for CPU-intensive searches)
cpu_tuple_cost = 0.01           # Default: 0.01

# For servers with powerful CPUs:
cpu_tuple_cost = 0.005
```

### 4. Connection and Performance

```ini
# ============================================
# Connections and Performance
# ============================================

# Maximum connections
max_connections = 100           # Default: 100

# For high-traffic sites:
max_connections = 200

# Shared memory for parallel queries
max_parallel_workers_per_gather = 4  # Default: 2
max_parallel_workers = 8             # Default: 8

# Autovacuum (critical for performance)
autovacuum = on                      # Default: on
autovacuum_max_workers = 3           # Default: 3
autovacuum_naptime = 1min            # Default: 1min

# Checkpoint settings
checkpoint_completion_target = 0.9   # Default: 0.5
wal_buffers = 16MB                   # Default: -1 (auto)
```

### 5. Logging for Performance Analysis

```ini
# ============================================
# Logging Configuration
# ============================================

# Log slow queries
log_min_duration_statement = 1000    # Log queries >1s

# For development/optimization:
log_min_duration_statement = 100     # Log queries >100ms

# Log autovacuum activity
log_autovacuum_min_duration = 0      # Log all autovacuum

# Log statement statistics
log_statement = 'mod'                # Log modifications

# For debugging:
log_statement = 'all'                # Log all statements
```

### 6. Apply Configuration

```bash
# Reload PostgreSQL configuration
sudo systemctl reload postgresql

# Or restart for some settings
sudo systemctl restart postgresql

# Verify settings
psql -U postgres -d your_database -c "SHOW shared_buffers;"
psql -U postgres -d your_database -c "SHOW effective_cache_size;"
psql -U postgres -d your_database -c "SHOW work_mem;"
```

---

## Django Application Tuning

### 1. Database Connection Pooling

```python
# config/settings/production.py

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT', default='5432'),

        # Connection pooling
        'CONN_MAX_AGE': 600,              # Keep connections for 10 minutes
        'CONN_HEALTH_CHECKS': True,       # Django 4.1+

        'OPTIONS': {
            'connect_timeout': 10,        # Connection timeout
            'options': '-c statement_timeout=30000',  # 30s query timeout
        },
    }
}

# For pgbouncer (external connection pooler)
DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True
```

### 2. Query Optimization with select_related/prefetch_related

```python
# referensi/services/ahsp_repository.py

class AHSPRepository:
    def search_ahsp_with_rincian(self, query: str, limit=None):
        """Optimized search with related rincian data."""
        results = self.search_ahsp(query, limit=limit)

        # Use prefetch_related to avoid N+1 queries
        results = results.prefetch_related(
            Prefetch(
                'rincian_set',
                queryset=RincianReferensi.objects.select_related(
                    'ahsp_ref'
                ).order_by('urut')
            )
        )

        return results

    def get_ahsp_with_details(self, ahsp_id: int):
        """Get single AHSP with all related data efficiently."""
        return AHSPReferensi.objects.select_related(
            # Add related fields if any
        ).prefetch_related(
            'rincian_set'
        ).get(id=ahsp_id)
```

### 3. QuerySet Iterator for Large Result Sets

```python
# For processing large datasets
def process_all_ahsp_jobs():
    """Process all AHSP jobs efficiently without loading all into memory."""
    # Bad: loads all records into memory
    # for job in AHSPReferensi.objects.all():

    # Good: uses server-side cursor
    for job in AHSPReferensi.objects.iterator(chunk_size=1000):
        process_job(job)

    # Or use chunking
    for chunk in AHSPReferensi.objects.all().chunked(1000):
        bulk_process_jobs(chunk)
```

### 4. Bulk Operations

```python
# Optimized bulk operations
def bulk_update_search_vectors():
    """Efficiently update search vectors for multiple records."""

    # Bad: individual updates (N queries)
    # for job in jobs:
    #     job.save()

    # Good: bulk update (1 query)
    jobs_to_update = AHSPReferensi.objects.filter(
        search_vector__isnull=True
    )

    # Django 4.2+ bulk_update
    AHSPReferensi.objects.bulk_update(
        jobs_to_update,
        ['updated_at'],
        batch_size=1000
    )
```

### 5. Database Query Debugging

```python
# config/settings/development.py

# Enable query debugging in development
DEBUG = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'logs/db_queries.log',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',  # Log all SQL queries
        },
    },
}

# Use django-debug-toolbar for query analysis
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

# Track query counts
from django.db import connection
print(f"Number of queries: {len(connection.queries)}")
```

---

## Search Performance Optimization

### 1. Search Vector Index Tuning

```sql
-- Monitor index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE indexname LIKE '%search%'
ORDER BY idx_scan DESC;

-- If low usage, investigate why searches aren't using index
EXPLAIN ANALYZE
SELECT * FROM referensi_ahspreferensi
WHERE search_vector @@ websearch_to_tsquery('simple', 'pekerjaan')
ORDER BY ts_rank(search_vector, websearch_to_tsquery('simple', 'pekerjaan')) DESC
LIMIT 50;

-- Should show: "Index Scan using ix_ahsp_search_vector"
```

### 2. Optimize Search Query Complexity

```python
# referensi/services/ahsp_repository.py

from django.core.cache import cache

class AHSPRepository:
    def search_ahsp_optimized(self, query: str, **kwargs):
        """Optimized search with result limiting."""

        # 1. Limit results early
        limit = kwargs.get('limit', 100)
        if limit > 1000:
            limit = 1000  # Cap maximum results

        # 2. Use simpler search for short queries
        if len(query) < 3:
            # Prefix search is faster for short queries
            return self.prefix_search_ahsp(query, limit=limit)

        # 3. Cache common searches
        cache_key = f"search:{query}:{limit}"
        cached_results = cache.get(cache_key)
        if cached_results is not None:
            return cached_results

        # 4. Perform search
        results = self.search_ahsp(query, limit=limit)

        # 5. Cache results
        cache.set(cache_key, results, timeout=300)  # 5 minutes

        return results
```

### 3. Optimize Fuzzy Search Threshold

```python
# Adjust threshold based on query length
def adaptive_fuzzy_search(query: str):
    """Fuzzy search with adaptive threshold."""
    query_length = len(query)

    if query_length < 5:
        threshold = 0.5  # Stricter for short queries
    elif query_length < 10:
        threshold = 0.3  # Normal
    else:
        threshold = 0.2  # More lenient for long queries

    return repo.fuzzy_search_ahsp(query, threshold=threshold)
```

### 4. Parallel Search for Multiple Queries

```python
from concurrent.futures import ThreadPoolExecutor
from django.db import connection

def parallel_search(queries: list[str]):
    """Search multiple queries in parallel."""

    def search_single(query):
        # Each thread needs its own connection
        connection.ensure_connection()
        return repo.search_ahsp(query, limit=20)

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(search_single, queries))

    return results
```

---

## Audit System Performance

### 1. Audit Log Partitioning

For high-volume audit logs, implement table partitioning:

```sql
-- Create partitioned audit log table
CREATE TABLE referensi_securityauditlog_partitioned (
    LIKE referensi_securityauditlog INCLUDING ALL
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions
CREATE TABLE referensi_securityauditlog_2025_01
PARTITION OF referensi_securityauditlog_partitioned
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE referensi_securityauditlog_2025_02
PARTITION OF referensi_securityauditlog_partitioned
FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- Automatically drop old partitions
DROP TABLE referensi_securityauditlog_2024_01;
```

### 2. Optimize Audit Dashboard Queries

```python
# referensi/services/audit_service.py

from django.db.models import Count, Q, F
from django.core.cache import cache

class AuditService:
    def get_dashboard_stats_optimized(self):
        """Optimized dashboard statistics."""

        # Cache results for 5 minutes
        cache_key = 'audit_dashboard_stats'
        stats = cache.get(cache_key)
        if stats:
            return stats

        # Single query with aggregation
        from datetime import timedelta
        from django.utils import timezone

        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        stats = SecurityAuditLog.objects.filter(
            timestamp__gte=last_7d
        ).aggregate(
            total_events=Count('id'),
            critical_events=Count('id', filter=Q(severity='CRITICAL')),
            high_events=Count('id', filter=Q(severity='HIGH')),
            events_24h=Count('id', filter=Q(timestamp__gte=last_24h)),
        )

        # Cache for 5 minutes
        cache.set(cache_key, stats, timeout=300)

        return stats

    def get_timeline_data_optimized(self, days=7):
        """Optimized timeline data with pre-aggregation."""

        # Use database-level date truncation
        from django.db.models.functions import TruncDay

        timeline = SecurityAuditLog.objects.filter(
            timestamp__gte=timezone.now() - timedelta(days=days)
        ).annotate(
            date=TruncDay('timestamp')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        return list(timeline)
```

### 3. Efficient Log Cleanup

```python
# referensi/management/commands/cleanup_audit_logs.py

def handle(self, *args, **options):
    """Optimized cleanup using delete in batches."""

    batch_size = 10000
    total_deleted = 0

    while True:
        # Delete in batches to avoid long transactions
        deleted = SecurityAuditLog.objects.filter(
            timestamp__lt=cutoff_date,
            severity__in=['INFO', 'LOW']
        )[:batch_size].delete()

        deleted_count = deleted[0]
        total_deleted += deleted_count

        if deleted_count == 0:
            break

        # Small sleep to avoid overwhelming database
        time.sleep(0.1)

    return total_deleted
```

---

## Caching Strategies

### 1. Redis Cache Configuration

```python
# config/settings/production.py

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'KEY_PREFIX': 'ahsp',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# Session cache (separate from data cache)
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

### 2. Cache Common Search Queries

```python
# referensi/services/ahsp_repository.py

from django.core.cache import cache
from django.conf import settings

class AHSPRepository:
    CACHE_TIMEOUT = getattr(settings, 'FTS_CACHE_TTL', 300)

    def _get_cache_key(self, method: str, **kwargs) -> str:
        """Generate cache key from method and parameters."""
        import hashlib
        params = '|'.join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_hash = hashlib.md5(params.encode()).hexdigest()
        return f"ahsp:{method}:{key_hash}"

    def search_ahsp(self, query: str, **kwargs):
        """Search with caching."""
        if not settings.FTS_CACHE_RESULTS:
            return self._search_ahsp_uncached(query, **kwargs)

        # Generate cache key
        cache_key = self._get_cache_key(
            'search_ahsp',
            query=query,
            **kwargs
        )

        # Try cache first
        results = cache.get(cache_key)
        if results is not None:
            return results

        # Perform search
        results = self._search_ahsp_uncached(query, **kwargs)

        # Cache results (convert QuerySet to list)
        cache.set(cache_key, list(results), timeout=self.CACHE_TIMEOUT)

        return results

    def invalidate_cache(self):
        """Clear all search caches."""
        cache.delete_pattern("ahsp:*")
```

### 3. Cache Audit Dashboard Data

```python
# referensi/views/audit_views.py

from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

class AuditDashboardView(View):
    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def get(self, request):
        # Dashboard data
        context = {
            'stats': self.get_stats(),
            'timeline': self.get_timeline(),
        }
        return render(request, 'audit/dashboard.html', context)
```

### 4. Template Fragment Caching

```django
{# referensi/templates/referensi/audit/dashboard.html #}

{% load cache %}

{# Cache summary cards for 5 minutes #}
{% cache 300 audit_summary_cards %}
<div class="row">
    <div class="col-md-3">
        <div class="card">
            <div class="card-body">
                <h5>Total Events</h5>
                <h2>{{ stats.total_events }}</h2>
            </div>
        </div>
    </div>
    {# ... other cards ... #}
</div>
{% endcache %}

{# Cache chart data for 10 minutes #}
{% cache 600 audit_timeline_chart %}
<canvas id="timelineChart"></canvas>
<script>
    // Chart rendering
</script>
{% endcache %}
```

---

## Index Maintenance

### 1. Regular Index Maintenance Schedule

```sql
-- Create maintenance function
CREATE OR REPLACE FUNCTION maintain_search_indexes()
RETURNS void AS $$
BEGIN
    -- Reindex all search indexes concurrently (no locks)
    REINDEX INDEX CONCURRENTLY ix_ahsp_search_vector;
    REINDEX INDEX CONCURRENTLY ix_ahsp_kode_trigram;
    REINDEX INDEX CONCURRENTLY ix_ahsp_nama_trigram;
    REINDEX INDEX CONCURRENTLY ix_rincian_search_vector;
    REINDEX INDEX CONCURRENTLY ix_rincian_uraian_trigram;

    -- Update statistics
    ANALYZE referensi_ahspreferensi;
    ANALYZE referensi_rincianreferensi;

    -- Vacuum to reclaim space
    VACUUM (ANALYZE, VERBOSE) referensi_ahspreferensi;
    VACUUM (ANALYZE, VERBOSE) referensi_rincianreferensi;
END;
$$ LANGUAGE plpgsql;

-- Schedule monthly via cron
-- 0 2 1 * * psql -U postgres -d dbname -c "SELECT maintain_search_indexes();"
```

### 2. Monitor Index Bloat

```sql
-- Check index bloat
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    CASE
        WHEN idx_scan = 0 THEN 'UNUSED'
        WHEN pg_relation_size(indexrelid) > 100 * 1024 * 1024 THEN 'LARGE'
        ELSE 'NORMAL'
    END AS status
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Rebuild bloated indexes
-- If status = 'LARGE' and growing rapidly:
REINDEX INDEX CONCURRENTLY ix_ahsp_search_vector;
```

### 3. Automated Vacuum Strategy

```ini
# postgresql.conf

# Autovacuum settings for search tables
autovacuum = on
autovacuum_max_workers = 3
autovacuum_naptime = 1min

# Aggressive vacuum for frequently updated tables
autovacuum_vacuum_scale_factor = 0.1    # Default: 0.2
autovacuum_analyze_scale_factor = 0.05  # Default: 0.1

# For tables with frequent updates
autovacuum_vacuum_cost_delay = 10ms     # Default: 20ms
autovacuum_vacuum_cost_limit = 200      # Default: -1 (auto)
```

---

## Query Optimization

### 1. Analyze Slow Queries

```sql
-- Enable slow query logging
ALTER DATABASE your_database SET log_min_duration_statement = 100;

-- View slow queries from log
SELECT
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
WHERE mean_time > 100  -- Queries averaging >100ms
ORDER BY mean_time DESC
LIMIT 20;
```

### 2. Optimize Search Queries

```python
# Before: Inefficient search
def search_inefficient(query):
    results = AHSPReferensi.objects.filter(
        Q(kode_ahsp__icontains=query) |
        Q(nama_ahsp__icontains=query)
    )  # Slow: full table scan
    return results

# After: Optimized with full-text search
def search_optimized(query):
    repo = AHSPRepository()
    results = repo.search_ahsp(query, limit=100)
    # Fast: uses GIN index
    return results
```

### 3. Use EXPLAIN ANALYZE

```python
# Analyze query performance
from django.db import connection

def analyze_search_query(query):
    """Analyze search query performance."""
    sql = """
    EXPLAIN ANALYZE
    SELECT *
    FROM referensi_ahspreferensi
    WHERE search_vector @@ websearch_to_tsquery('simple', %s)
    ORDER BY ts_rank(search_vector, websearch_to_tsquery('simple', %s)) DESC
    LIMIT 50;
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, [query, query])
        plan = cursor.fetchall()

    for row in plan:
        print(row[0])

# Usage
analyze_search_query("pekerjaan tanah")

# Look for:
# - "Index Scan using ix_ahsp_search_vector" (good)
# - "Seq Scan" (bad - not using index)
# - Execution time should be <50ms
```

---

## System-Level Tuning

### 1. Operating System Settings

```bash
# Edit /etc/sysctl.conf

# Increase shared memory for PostgreSQL
kernel.shmmax = 17179869184  # 16GB
kernel.shmall = 4194304      # 16GB in pages (4KB)

# Increase file descriptors
fs.file-max = 65536

# Apply settings
sudo sysctl -p
```

### 2. PostgreSQL Process Limits

```bash
# Edit /etc/security/limits.conf

postgres soft nofile 65536
postgres hard nofile 65536
postgres soft nproc 8192
postgres hard nproc 8192

# Verify
sudo -u postgres ulimit -n
# Should show: 65536
```

### 3. Disk I/O Optimization

```bash
# Check I/O scheduler (for SSD)
cat /sys/block/sda/queue/scheduler
# Should show: [noop] or [none] for SSD

# Set I/O scheduler
echo noop | sudo tee /sys/block/sda/queue/scheduler

# Make persistent (Ubuntu)
echo 'ACTION=="add|change", KERNEL=="sd[a-z]", ATTR{queue/scheduler}="noop"' | \
    sudo tee /etc/udev/rules.d/60-scheduler.rules
```

### 4. Gunicorn Workers Configuration

```python
# gunicorn.conf.py

import multiprocessing

# Workers calculation
workers = multiprocessing.cpu_count() * 2 + 1

# For CPU-intensive search operations
workers = multiprocessing.cpu_count()

# Worker class
worker_class = 'gevent'  # For I/O-bound operations
# worker_class = 'sync'  # For CPU-bound operations

# Threads per worker
threads = 2

# Timeout
timeout = 30

# Keep-alive
keepalive = 5

# Max requests per worker (prevent memory leaks)
max_requests = 1000
max_requests_jitter = 100
```

---

## Performance Benchmarking

### 1. Benchmark Script

```python
# scripts/benchmark_search.py

import time
from referensi.services.ahsp_repository import AHSPRepository

def benchmark_search():
    """Benchmark search performance."""
    repo = AHSPRepository()

    test_queries = [
        "pekerjaan",
        "pekerjaan tanah",
        "galian pondasi",
        "beton",
        "baja tulangan",
    ]

    results = {}

    for query in test_queries:
        # Warm-up
        repo.search_ahsp(query, limit=100)

        # Benchmark (10 iterations)
        times = []
        for _ in range(10):
            start = time.time()
            list(repo.search_ahsp(query, limit=100))
            duration = time.time() - start
            times.append(duration * 1000)  # Convert to ms

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        results[query] = {
            'avg': avg_time,
            'min': min_time,
            'max': max_time,
        }

        print(f"{query:20} | Avg: {avg_time:6.2f}ms | Min: {min_time:6.2f}ms | Max: {max_time:6.2f}ms")

    return results

if __name__ == '__main__':
    benchmark_search()
```

### 2. Load Testing with Locust

```python
# locustfile.py

from locust import HttpUser, task, between

class SearchUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def search_basic(self):
        """Basic search (weight: 3)."""
        self.client.get("/search/?q=pekerjaan")

    @task(2)
    def search_complex(self):
        """Complex search (weight: 2)."""
        self.client.get("/search/?q=pekerjaan+tanah+galian")

    @task(1)
    def search_autocomplete(self):
        """Auto-complete (weight: 1)."""
        self.client.get("/autocomplete/?q=peke")

    @task(1)
    def audit_dashboard(self):
        """Audit dashboard (weight: 1)."""
        self.client.get("/referensi/audit/dashboard/")

# Run: locust -f locustfile.py --host=http://localhost:8000
```

### 3. Database Performance Monitoring

```sql
-- Create monitoring view
CREATE VIEW v_performance_metrics AS
SELECT
    'Cache Hit Ratio' AS metric,
    ROUND(
        100.0 * sum(heap_blks_hit) / NULLIF(sum(heap_blks_hit) + sum(heap_blks_read), 0),
        2
    ) || '%' AS value
FROM pg_statio_user_tables
UNION ALL
SELECT
    'Index Hit Ratio',
    ROUND(
        100.0 * sum(idx_blks_hit) / NULLIF(sum(idx_blks_hit) + sum(idx_blks_read), 0),
        2
    ) || '%'
FROM pg_statio_user_indexes
UNION ALL
SELECT
    'Active Connections',
    COUNT(*)::text
FROM pg_stat_activity
WHERE state = 'active'
UNION ALL
SELECT
    'Slow Queries (>1s)',
    COUNT(*)::text
FROM pg_stat_statements
WHERE mean_time > 1000;

-- Query metrics
SELECT * FROM v_performance_metrics;
```

---

## Troubleshooting Slow Queries

### 1. Identify Slow Queries

```sql
-- Top 10 slowest queries
SELECT
    substring(query, 1, 100) AS query_preview,
    calls,
    total_time,
    mean_time,
    max_time,
    stddev_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Current running queries
SELECT
    pid,
    now() - query_start AS duration,
    state,
    substring(query, 1, 100) AS query_preview
FROM pg_stat_activity
WHERE state != 'idle'
    AND query NOT LIKE '%pg_stat%'
ORDER BY duration DESC;
```

### 2. Kill Long-Running Queries

```sql
-- Find long-running queries (>5 minutes)
SELECT
    pid,
    now() - query_start AS duration,
    query
FROM pg_stat_activity
WHERE state = 'active'
    AND now() - query_start > interval '5 minutes';

-- Kill specific query
SELECT pg_terminate_backend(12345);  -- Replace with actual PID
```

### 3. Optimize Query Plan

```sql
-- Force planner to use index
SET enable_seqscan = off;

-- Test query
EXPLAIN ANALYZE
SELECT * FROM referensi_ahspreferensi
WHERE search_vector @@ websearch_to_tsquery('simple', 'pekerjaan');

-- Reset
SET enable_seqscan = on;

-- If index is still not used, rebuild statistics
ANALYZE referensi_ahspreferensi;
```

---

## Performance Checklist

After implementing optimizations, verify:

- [ ] PostgreSQL `shared_buffers` set to 25% of RAM
- [ ] `effective_cache_size` set to 50-75% of RAM
- [ ] `work_mem` optimized for search operations (20-64MB)
- [ ] GIN indexes created and being used (check EXPLAIN)
- [ ] Autovacuum enabled and running regularly
- [ ] Slow query logging enabled (<100ms threshold)
- [ ] Cache hit ratio >95%
- [ ] Django connection pooling configured
- [ ] Redis cache implemented for common searches
- [ ] Template fragment caching for dashboards
- [ ] Index maintenance scheduled monthly
- [ ] Benchmark tests show <50ms average search time

---

## Recommended Monitoring Tools

1. **pgAdmin**: GUI for PostgreSQL management
2. **pg_stat_statements**: Query performance tracking
3. **Django Debug Toolbar**: Development query analysis
4. **New Relic / DataDog**: Application performance monitoring
5. **Grafana + Prometheus**: Custom metrics dashboards
6. **Locust**: Load testing
7. **pgBadger**: PostgreSQL log analyzer

---

**Document Version**: 1.0
**Last Updated**: 2025-11-04
**Target Improvement**: 10-100x faster queries
**Optimization Level**: Production-ready
