# FASE 0.3: Monitoring & Logging Guide

**Status:** ✅ COMPLETED
**Version:** 1.0
**Last Updated:** 2025-11-13

---

## EXECUTIVE SUMMARY

Structured logging and metrics collection telah ditambahkan untuk monitoring critical operations:

1. ✅ **Bundle Expansion** - Track bundle usage, component count, duration
2. ✅ **Cascade Re-Expansion** - Monitor cascade operations, depth, affected pekerjaan
3. ✅ **Circular Dependency** - Log circular dependency detections
4. ✅ **Optimistic Locking** - Track concurrent edit conflicts
5. ✅ **Metrics Collection** - In-memory metrics collector for aggregation

**Files Modified:**
- `detail_project/monitoring_helpers.py` (NEW - 680 lines)
- `detail_project/services.py` (monitoring integrated)
- `detail_project/views_api.py` (monitoring integrated)

---

## STRUCTURED LOGGING FORMAT

### Log Format

All structured logs follow consistent format:

```
[OPERATION_NAME] key1=value1 key2=value2 key3=value3 ...
```

**Example:**
```
[CASCADE_REEXPANSION] project_id=1 modified_pekerjaan_id=5 referencing_count=2
                      referencing_ids=[3, 7] cascade_depth=1 re_expanded_count=2
                      duration_ms=125.5
```

### Operation Types

| Operation | Description | Log Level | Example |
|-----------|-------------|-----------|---------|
| `BUNDLE_EXPANSION` | Bundle expansion operation | INFO | Bundle from job/ahsp expanded |
| `CASCADE_REEXPANSION` | Cascade re-expansion | INFO | Modified pekerjaan triggers cascade |
| `CIRCULAR_DEPENDENCY_CHECK` | Cycle detection | WARNING (if circular), DEBUG (if not) | Circular dependency detected/prevented |
| `OPTIMISTIC_LOCK_CONFLICT` | Concurrent edit conflict | WARNING | User tried to save stale data |
| `POPULATE_EXPANDED_START` | Expansion started | INFO | Entering expansion process |
| `POPULATE_EXPANDED_COMPLETE` | Expansion finished | INFO | Expansion completed with timing |

---

## METRICS COLLECTION

### Available Metrics

| Metric Name | Type | Description | Tags |
|-------------|------|-------------|------|
| `bundle_expansions` | Counter | Bundle expansion count | project_id, pekerjaan_id, ref_kind, component_count |
| `cascade_operations` | Counter | Cascade re-expansion count | project_id, modified_pekerjaan_id, re_expanded_count |
| `cascade_depth` | Gauge | Cascade depth distribution | project_id, cascade_depth |
| `circular_dependencies` | Counter | Circular dependency detections | project_id, source_pekerjaan_id, target_pekerjaan_id |
| `lock_conflicts` | Counter | Optimistic lock conflicts | project_id, pekerjaan_id |
| `orphan_detections` | Counter | Orphan detection results | project_id, orphan_count |

### Accessing Metrics

```python
from detail_project.monitoring_helpers import get_metrics_summary

# Get summary of all metrics
summary = get_metrics_summary()

# Example output:
# {
#     'bundle_expansions': {
#         'count': 45,
#         'min': 1,
#         'max': 15,
#         'avg': 5.2,
#         'recent': [...]
#     },
#     'cascade_operations': {
#         'count': 12,
#         'min': 1,
#         'max': 3,
#         'avg': 1.5,
#         'recent': [...]
#     }
# }

print(f"Total bundle expansions: {summary['bundle_expansions']['count']}")
print(f"Average cascade depth: {summary['cascade_depth']['avg']:.1f}")
```

---

## USAGE EXAMPLES

### 1. Bundle Expansion Monitoring

**Code Location:** `services.py:~600-650`

**What's Logged:**
- Bundle kode
- Reference kind ('job' or 'ahsp')
- Component count
- Duration

**Log Example:**
```
[BUNDLE_EXPANSION] project_id=1 pekerjaan_id=5 bundle_kode=LAIN.A001 ref_kind=job
                   ref_id=3 component_count=15 duration_ms=125.5
```

**Metrics Collected:**
```python
# Counter: bundle_expansions
# Tags: project_id=1, ref_kind='job', component_count=15
```

---

### 2. Cascade Re-Expansion Monitoring

**Code Location:** `services.py:685-827`

**What's Logged:**
- Modified pekerjaan ID
- Referencing pekerjaan IDs list
- Cascade depth (recursion level)
- Total re-expanded count
- Duration

**Log Example:**
```
[CASCADE_REEXPANSION] project_id=1 modified_pekerjaan_id=5 referencing_count=2
                      referencing_ids=[3, 7] cascade_depth=1 re_expanded_count=3
                      duration_ms=250.3
```

**Metrics Collected:**
```python
# Counter: cascade_operations (value=3)
# Gauge: cascade_depth (value=1)
# Tags: project_id=1, modified_pekerjaan_id=5
```

**Interpretation:**
- `cascade_depth=0`: Direct references only (no nested cascades)
- `cascade_depth=1`: One level of recursion (A→B→C)
- `cascade_depth>2`: Deep cascades (may impact performance)

---

### 3. Circular Dependency Monitoring

**Code Location:** `services.py:111-182`

**What's Logged:**
- Source pekerjaan ID
- Target pekerjaan ID
- Whether circular detected

**Log Example (Circular Detected):**
```
[CIRCULAR_DEPENDENCY_CHECK] project_id=1 source_pekerjaan_id=5 target_pekerjaan_id=3
                           is_circular=True
```

**Log Example (No Circular):**
```
[CIRCULAR_DEPENDENCY_CHECK] project_id=1 source_pekerjaan_id=5 target_pekerjaan_id=8
                           is_circular=False
```

**Metrics Collected:**
```python
# Counter: circular_dependencies (only when is_circular=True)
# Tags: project_id=1, source_pekerjaan_id=5, target_pekerjaan_id=3
```

**Action Required:**
- If `is_circular=True`: User should see error message, prevent bundle creation
- Monitor frequency: High frequency may indicate UI bug or user confusion

---

### 4. Optimistic Locking Monitoring

**Code Location:** `views_api.py:~1260-1287`

**What's Logged:**
- Project ID
- Pekerjaan ID
- Client timestamp (what user had)
- Server timestamp (actual current time)

**Log Example:**
```
[OPTIMISTIC_LOCK_CONFLICT] project_id=1 pekerjaan_id=5
                          client_timestamp=2025-11-13T10:30:00Z
                          server_timestamp=2025-11-13T10:35:22Z
```

**Metrics Collected:**
```python
# Counter: lock_conflicts
# Tags: project_id=1, pekerjaan_id=5
```

**Interpretation:**
- Time gap = 5 minutes 22 seconds
- Indicates another user edited between 10:30 and 10:35
- User sees conflict dialog with "Muat Ulang" or "Timpa" options

**Action Required:**
- High conflict rate for specific pekerjaan: May indicate multiple users working on same item
- Consider adding real-time collaboration features or user presence indicators

---

## MONITORING DASHBOARD QUERIES

### Query 1: Bundle Usage Analysis

```python
from detail_project.monitoring_helpers import get_metrics_summary

summary = get_metrics_summary()
bundle_stats = summary.get('bundle_expansions', {})

print(f"Total bundle expansions: {bundle_stats.get('count', 0)}")
print(f"Average components per bundle: {bundle_stats.get('avg', 0):.1f}")
print(f"Max components in single bundle: {bundle_stats.get('max', 0)}")

# Recent expansions
for entry in bundle_stats.get('recent', []):
    print(f"Project {entry['project_id']}: {entry['value']} components")
```

---

### Query 2: Cascade Performance Analysis

```python
cascade_stats = summary.get('cascade_operations', {})
depth_stats = summary.get('cascade_depth', {})

print(f"Total cascade operations: {cascade_stats.get('count', 0)}")
print(f"Average re-expanded per cascade: {cascade_stats.get('avg', 0):.1f}")
print(f"Average cascade depth: {depth_stats.get('avg', 0):.1f}")
print(f"Max cascade depth: {depth_stats.get('max', 0)}")

# Alert if max depth > 2
if depth_stats.get('max', 0) > 2:
    print("⚠️ WARNING: Deep cascade detected (depth > 2)")
    print("   This may indicate complex bundle chains.")
```

---

### Query 3: Conflict Analysis

```python
conflict_stats = summary.get('lock_conflicts', {})

print(f"Total optimistic lock conflicts: {conflict_stats.get('count', 0)}")

# Recent conflicts
for entry in conflict_stats.get('recent', []):
    print(f"Project {entry['project_id']}, Pekerjaan {entry['pekerjaan_id']}")
```

---

## ALERTING RULES

### Rule 1: High Cascade Depth

**Trigger:** `cascade_depth > 2`

**Severity:** WARNING

**Action:**
- Investigate bundle chain: A→B→C→D...
- Consider flattening deep cascades
- May impact save performance

**Query:**
```python
depth_stats = summary['cascade_depth']
if depth_stats.get('max', 0) > 2:
    alert("High cascade depth detected")
```

---

### Rule 2: Frequent Conflicts

**Trigger:** `lock_conflicts > 5 per hour for same pekerjaan`

**Severity:** INFO

**Action:**
- Multiple users working on same item
- Consider adding user presence indicator
- May benefit from real-time collaboration

---

### Rule 3: Circular Dependency Attempts

**Trigger:** `circular_dependencies > 0`

**Severity:** ERROR

**Action:**
- Should be prevented by UI validation
- If occurring frequently: Check frontend validation
- May indicate user confusion or bug

---

## LOG ANALYSIS

### Grep Examples

**Find all cascade operations:**
```bash
grep "CASCADE_REEXPANSION" django.log
```

**Find conflicts for specific project:**
```bash
grep "OPTIMISTIC_LOCK_CONFLICT.*project_id=1" django.log
```

**Find circular dependency detections:**
```bash
grep "CIRCULAR_DEPENDENCY_CHECK.*is_circular=True" django.log
```

**Find slow operations (>500ms):**
```bash
grep "duration_ms=[5-9][0-9][0-9]\|duration_ms=[0-9]\{4,\}" django.log
```

---

### Python Log Analysis

```python
import re

# Parse log file
with open('django.log') as f:
    for line in f:
        if 'CASCADE_REEXPANSION' in line:
            # Extract duration
            match = re.search(r'duration_ms=(\d+\.?\d*)', line)
            if match:
                duration = float(match.group(1))
                if duration > 500:
                    print(f"Slow cascade: {duration}ms")
                    print(line)
```

---

## PRODUCTION INTEGRATION

### Django Settings

```python
# settings/production.py

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'structured': {
            'format': '[{levelname}] {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/ahsp.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'structured',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'structured',
        },
    },
    'loggers': {
        'detail_project': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

---

### External Monitoring Integration

#### Prometheus (Recommended for Production)

```python
# Replace in-memory metrics collector with Prometheus client

from prometheus_client import Counter, Histogram, Gauge

bundle_expansions = Counter(
    'ahsp_bundle_expansions_total',
    'Total bundle expansions',
    ['project_id', 'ref_kind']
)

cascade_duration = Histogram(
    'ahsp_cascade_duration_seconds',
    'Cascade operation duration',
    ['project_id']
)

cascade_depth = Gauge(
    'ahsp_cascade_depth',
    'Current cascade depth',
    ['project_id']
)

# In monitoring_helpers.py
def log_cascade_operation(...):
    # ...existing logging...
    cascade_duration.labels(project_id=project_id).observe(duration_ms / 1000)
    cascade_depth.labels(project_id=project_id).set(cascade_depth)
```

#### CloudWatch (AWS)

```python
import boto3

cloudwatch = boto3.client('cloudwatch')

def log_cascade_operation(...):
    # ...existing logging...

    cloudwatch.put_metric_data(
        Namespace='AHSP/Workflow',
        MetricData=[
            {
                'MetricName': 'CascadeOperations',
                'Value': re_expanded_count,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'ProjectId', 'Value': str(project_id)}
                ]
            },
            {
                'MetricName': 'CascadeDuration',
                'Value': duration_ms,
                'Unit': 'Milliseconds',
                'Dimensions': [
                    {'Name': 'ProjectId', 'Value': str(project_id)}
                ]
            }
        ]
    )
```

---

## TROUBLESHOOTING

### Issue: No logs appearing

**Cause:** Logger not configured or wrong level

**Fix:**
```python
# In settings.py
LOGGING = {
    'loggers': {
        'detail_project': {
            'level': 'DEBUG',  # <- Change from INFO to DEBUG
            ...
        }
    }
}
```

---

### Issue: Metrics show 0 count

**Cause:** Metrics not being collected

**Fix:**
```python
# Verify imports in services.py
from .monitoring_helpers import log_cascade_operation, collect_metric

# Verify function calls exist
log_cascade_operation(...)
collect_metric('cascade_operations', re_expanded_count, ...)
```

---

### Issue: Log file too large

**Cause:** Verbose logging

**Fix:**
- Use log rotation (RotatingFileHandler)
- Filter debug logs in production
- Archive old logs

```python
'handlers': {
    'file': {
        'class': 'logging.handlers.RotatingFileHandler',
        'maxBytes': 10485760,  # 10MB
        'backupCount': 5,  # Keep 5 old files
    }
}
```

---

## SUCCESS CRITERIA

### FASE 0.3 Completion Checklist

- [x] Structured logging helper module created
- [x] Metrics collection implemented
- [x] Bundle expansion monitoring integrated
- [x] Cascade re-expansion monitoring integrated
- [x] Circular dependency monitoring integrated
- [x] Optimistic locking monitoring integrated
- [x] Documentation created
- [x] Example queries provided
- [x] Production integration guide provided

### Key Achievements

1. ✅ **Consistent Log Format** - All logs follow structured format
2. ✅ **Performance Metrics** - Duration tracking for critical operations
3. ✅ **Metrics Aggregation** - In-memory collector with stats
4. ✅ **Production Ready** - Integration examples for Prometheus/CloudWatch
5. ✅ **Troubleshooting Guide** - Common issues and solutions

---

## NEXT STEPS

### Immediate (Before Production)

1. **Test Monitoring** - Verify all logs appear correctly
2. **Set Alert Thresholds** - Define acceptable limits for each metric
3. **Setup Log Rotation** - Prevent log files from filling disk
4. **Test Metrics API** - Verify `/api/metrics/` endpoint works (if implemented)

### Future Enhancements (FASE 1+)

1. **Orphan Detection Monitoring** - Track orphan accumulation rate
2. **API Response Time** - Track endpoint latency
3. **Database Query Performance** - Slow query detection
4. **User Activity Metrics** - Active users, most edited projects
5. **Error Rate Tracking** - 4xx/5xx response rate

---

**FASE 0.3 STATUS: ✅ COMPLETED**

**Next:** FASE 1 - Orphan Cleanup Mechanism
