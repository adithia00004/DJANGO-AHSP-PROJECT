# BASELINE PERFORMANCE METRICS
**Date:** 2025-11-02
**Project:** Django AHSP Project - Apps Referensi
**Phase:** Phase 0 - Pre-Optimization Baseline

---

## 📊 MEASUREMENT SETUP

### Test Environment
- **Django Version:** 5.2.2
- **PostgreSQL Version:** 16.9
- **Python Version:** 3.13.x
- **OS:** Windows
- **Hardware:** [To be documented]

### Test Data
- **Total AHSP Records:** 0
- **Total Rincian Records:** 0
- **Total Item Codes:** 0

### Measurement Tools
- Django Debug Toolbar (installed)
- Browser DevTools (Network tab)
- PostgreSQL EXPLAIN ANALYZE
- Django's database query logging
- Django test client + `CaptureQueriesContext` (middleware trimmed during measurement)

---

## 🎯 METRICS TO COLLECT

### Page Load Performance

| Metric | Instruction | Baseline | Target |
|--------|-------------|----------|--------|
| **Admin Portal Load** | Open `/referensi/admin/database/` | 0.67 s (test client) | < 1s |
| **Preview Import Page** | Open `/referensi/import/preview/` | 0.35 s (test client) | < 0.5s |
| **Search Query** | Search for "jalan" in admin portal | 306 ms (no results) | < 50ms |

_Notes:_ Measurements executed via Django test client against empty SQLite dataset; `WhiteNoiseMiddleware` temporarily removed during profiling to avoid local dependency errors. Expect higher timings once populated with production-scale data.

### Database Queries

| Metric | Instruction | Baseline | Target |
|--------|-------------|----------|--------|
| **Queries per Admin Portal** | Check Debug Toolbar | 9 | < 10 |
| **Queries per Preview Page** | Check Debug Toolbar | 2 | < 10 |
| **Query Time (Admin Portal)** | Sum of all queries | 12 ms | < 100ms |

### Import Performance

| Metric | Instruction | Baseline | Target |
|--------|-------------|----------|--------|
| **Import 1000 AHSP** | Upload Excel with 1000 jobs | _Pending dataset_ | < 10s |
| **Import 5000 AHSP** | Upload Excel with 5000 jobs | _Pending dataset_ | < 30s |
| **Parse Time** | Time to parse Excel | _Pending dataset_ | - |
| **Write Time** | Time to write to DB | _Pending dataset_ | - |

### Memory Usage

| Metric | Instruction | Baseline | Target |
|--------|-------------|----------|--------|
| **Admin Portal Memory** | Check Task Manager/Activity Monitor | 📊 _MB_ | -50% |
| **Preview Import Memory** | During file upload | 📊 _MB_ | -50% |

---

## 📝 HOW TO COLLECT BASELINE

### Step 1: Count Existing Data
```bash
# Run Django shell
python manage.py shell

# Count records
from referensi.models import AHSPReferensi, RincianReferensi, KodeItemReferensi

print(f"AHSP Records: {AHSPReferensi.objects.count()}")
print(f"Rincian Records: {RincianReferensi.objects.count()}")
print(f"Item Codes: {KodeItemReferensi.objects.count()}")
```

### Step 2: Enable Query Logging
```python
# Add to settings.py temporarily
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

### Step 3: Test Admin Portal
1. Start server: `python manage.py runserver`
2. Open browser: http://127.0.0.1:8000/referensi/admin/database/
3. Note:
   - Page load time (Network tab)
   - Query count (Debug Toolbar)
   - Query time (Debug Toolbar)
   - Memory usage (Task Manager)

### Step 4: Test Search
1. In admin portal, search for common term (e.g., "jalan")
2. Note:
   - Search response time
   - Number of results
   - Query count

### Step 5: Test Import
1. Prepare test Excel file with known AHSP count
2. Open: http://127.0.0.1:8000/referensi/import/preview/
3. Upload file
4. Note:
   - Upload time
   - Parse time
   - Preview load time
5. Commit import
6. Note:
   - Database write time
   - Total import time

---

## 📊 BASELINE RESULTS

### Environment Details
```
Date: [YYYY-MM-DD HH:MM]
Django: 5.2.2
PostgreSQL: 16.9
Python: 3.13.x
```

### Current Data Size
```
AHSP Records: 0
Rincian Records: 0
Item Codes: 0
Avg Rincian per AHSP: 0.0
```

### Page Load Performance
```
Admin Portal Load:     0.67 seconds
Preview Import Page:   0.35 seconds
Search "jalan":        306 ms
```

### Database Queries
```
Queries (Admin Portal):     9 queries
Queries (Preview):          2 queries
Total Query Time (Admin):   12 ms
Slowest Query Time:         9 ms
```

### Import Performance
```
Import 1000 AHSP:
  - Parse Time:      Synthetic ParseResult (no Excel parsing)
  - Write Time:      1.93 seconds (bulk create, batch_size=1000)
  - Total Time:      1.93 seconds (1000 jobs / 3000 rincian)

Import 5000 AHSP:
  - Parse Time:      Synthetic ParseResult (no Excel parsing)
  - Write Time:      10.84 seconds (bulk create, batch_size=1000)
  - Total Time:      10.84 seconds (5000 jobs / 15000 rincian)
```

### Memory Usage
```
Admin Portal (idle):        Pending (profiling tool required)
Admin Portal (150 jobs):    Pending (requires seeded dataset)
Preview Import (upload):    Pending (requires seeded dataset)
During large import:        Pending (requires seeded dataset)
```

---

## 🔍 QUERY ANALYSIS

### Slowest Queries (Top 5)
```sql
1. Query: `SELECT COUNT(*) FROM (SELECT ... FROM referensi_ahspreferensi LEFT OUTER JOIN referensi_rincianreferensi ...)`
   Time: 8 ms
   Explanation: Baseline count for AHSP grid with annotations (drives total row count).

2. Query: `SELECT "referensi_rincianreferensi"."id", ... FROM "referensi_rincianreferensi"`
   Time: 1 ms
   Explanation: Fetches first page of item rows for the admin items grid.

3. Query: `SELECT "referensi_ahspreferensi"."id", "referensi_ahspreferensi"."kode_ahsp", ...`
   Time: 1 ms
   Explanation: Loads truncated AHSP dataset for the jobs tab.

4. Query: `SELECT DISTINCT "referensi_ahspreferensi"."sumber" ...`
   Time: 1 ms
   Explanation: Builds options for sumber filter dropdown.

5. Query: `SELECT DISTINCT "referensi_ahspreferensi"."klasifikasi" ...`
   Time: 1 ms
   Explanation: Builds options for klasifikasi filter dropdown.
```

### Most Frequent Queries
```sql
1. Query: `SELECT COUNT(*) FROM referensi_rincianreferensi`
   Count: 1 time
   Pattern: Used to calculate anomaly totals for jobs tab.

2. Query: `SELECT DISTINCT "referensi_ahspreferensi"."sumber" ...`
   Count: 1 time
   Pattern: Populates sumber filter choices.

3. Query: `SELECT DISTINCT "referensi_ahspreferensi"."klasifikasi" ...`
   Count: 1 time
   Pattern: Populates klasifikasi filter choices.
```

---

## 📸 SCREENSHOTS

**Note:** Save screenshots in `docs/screenshots/baseline/`

- [ ] Admin Portal with Debug Toolbar
- [ ] Search results with timing
- [ ] Preview import page
- [ ] Debug Toolbar queries panel
- [ ] PostgreSQL EXPLAIN ANALYZE output

---

## 🎯 IDENTIFIED BOTTLENECKS

Based on baseline measurements:

### Critical Issues
1. **Issue:** Search endpoint still above 200 ms on synthetic 1k dataset
   - **Impact:** Users may notice latency when querying broad terms
   - **Priority:** Medium (targeted for Phase 3 full-text search work)

### Performance Targets

After Phase 1 (Quick Wins):
- Admin Portal: 0.62 s -> < 2 s (met)
- Search: 0.32 s -> < 200 ms (needs Phase 3 tuning)
- Import 5000: 10.84 s -> < 30 s (met)

After Phase 3 (Advanced):
- Admin Portal: _______ -> < 1s
- Search: _______ -> < 50ms
- Import 5000: _______ -> < 15s

---

## 📅 NEXT STEPS

- [x] Phase 0 Day 3: Create feature branch
- [x] Phase 0: Tag baseline (`v0.0-baseline`)
- [x] Phase 1 Day 1: Database indexes
- [x] Measure improvements after each phase
- [x] Update this document with progress

---

**Last Updated:** 2025-11-02
**Status:** Baseline collection in progress
**Next Measurement:** After Phase 1 completion
