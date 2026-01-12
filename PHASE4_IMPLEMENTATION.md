# ✅ PHASE 4 IMPLEMENTATION PLAN

**Date**: 2026-01-10
**Status**: READY FOR IMPLEMENTATION

---

## 📊 Summary

Phase 4 focuses on **completing critical gaps** - tahapan management, remaining exports, monitoring APIs, and orphaned items cleanup.

### Coverage Target:

| Metric | Phase 3 | Phase 4 Target | Improvement |
|--------|---------|----------------|-------------|
| **Total Endpoints Tested** | 63 | 88 | **+25 (+40%)** ✅ |
| **Coverage %** | 47.7% | 66.7% | **+19%** ✅ |
| **Tahapan APIs** | 1/10 (10%) | 7/10 (70%) | **+60%** ✅ |
| **Export Operations** | 20/30 (67%) | 28/30 (93%) | **+26%** ✅ |
| **Monitoring APIs** | 0/5 (0%) | 3/5 (60%) | **+60%** ✅ |
| **Orphaned Items** | 0/2 (0%) | 2/2 (100%) | **+100%** ✅ |

---

## 🎯 Phase 4 Additions (25 New Endpoints)

### **Category 1: Tahapan Management APIs (6 new)** - CRITICAL GAP

Currently only 1/10 tahapan endpoints tested! This is a critical project feature.

```python
@tag('api', 'high', 'tahapan', 'phase4')
@task(3)
def api_tahapan_detail(self):
    """Get tahapan detail"""
    /api/project/[id]/tahapan/[tahapan_id]/
```

**Why Important:**
- Tahapan is core project management feature
- Used for scheduling and progress tracking
- Currently only 10% coverage!

**Endpoints:**
1. **GET** `/api/project/[id]/tahapan/[tahapan_id]/` - Get tahapan detail
2. **POST** `/api/project/[id]/tahapan/[tahapan_id]/assign/` - Assign pekerjaan to tahapan
3. **POST** `/api/project/[id]/tahapan/[tahapan_id]/unassign/` - Unassign pekerjaan
4. **POST** `/api/project/[id]/tahapan/reorder/` - Reorder tahapan
5. **GET** `/api/project/[id]/tahapan/unassigned/` - Get unassigned pekerjaan
6. **POST** `/api/project/[id]/tahapan/validate/` - Validate all assignments

---

### **Category 2: V2 Tahapan APIs (4 new)** - CRITICAL

V2 architecture for weekly progress tracking.

```python
@tag('api', 'v2', 'high', 'tahapan', 'phase4')
@task(3)
def api_v2_assign_weekly(self):
    """V2: Assign pekerjaan to weekly schedule"""
    /api/v2/project/[id]/assign-weekly/
```

**Why Important:**
- V2 canonical storage for weekly progress
- New architecture needs testing
- Used in Gantt chart UI

**Endpoints:**
1. **POST** `/api/v2/project/[id]/assign-weekly/` - Assign to weekly schedule
2. **POST** `/api/v2/project/[id]/regenerate-tahapan/` - Regenerate tahapan
3. **POST** `/api/v2/project/[id]/reset-progress/` - Reset progress data
4. **POST** `/api/v2/project/[id]/week-boundary/` - Update week boundaries

---

### **Category 3: Remaining Export Operations (8 new)**

Complete export coverage to 93%!

```python
@tag('export', 'pdf', 'rekap-rab', 'phase4')
@task(1)
def export_rekap_rab_pdf(self):
    """Export Rekap RAB as PDF"""
    /api/project/[id]/export/rekap-rab/pdf/
```

**Why Important:**
- Complete all export format variations
- Users need all formats for different purposes
- PDF exports critical for official documentation

**Endpoints:**
1. **GET** `/api/project/[id]/export/rekap-rab/pdf/` - Rekap RAB PDF
2. **GET** `/api/project/[id]/export/rincian-ahsp/word/` - Rincian AHSP Word
3. **GET** `/api/project/[id]/export/rekap-kebutuhan/json/` - Rekap Kebutuhan JSON
4. **GET** `/api/project/[id]/export/rekap-kebutuhan/word/` - Rekap Kebutuhan Word
5. **GET** `/api/project/[id]/export/jadwal-pekerjaan/pdf/` - Jadwal PDF
6. **GET** `/api/project/[id]/export/volume-pekerjaan/pdf/` - Volume PDF
7. **GET** `/api/project/[id]/export/volume-pekerjaan/word/` - Volume Word
8. **GET** `/api/project/[id]/export/volume-pekerjaan/xlsx/` - Volume Excel

---

### **Category 4: Rekap Kebutuhan Variants (2 new)**

Missing rekap kebutuhan filtering and timeline.

```python
@tag('api', 'high', 'rekap', 'phase4')
@task(3)
def api_rekap_kebutuhan_timeline(self):
    """Get rekap kebutuhan timeline"""
    /api/project/[id]/rekap-kebutuhan-timeline/
```

**Why Important:**
- Timeline view critical for procurement planning
- Filters allow users to customize views
- Used in material requirement reports

**Endpoints:**
1. **GET** `/api/project/[id]/rekap-kebutuhan-timeline/` - Timeline view
2. **GET** `/api/project/[id]/rekap-kebutuhan/filters/` - Get available filters

---

### **Category 5: Orphaned Items Management (2 new)**

Cleanup unused harga items from project.

```python
@tag('api', 'medium', 'cleanup', 'phase4')
@task(2)
def api_list_orphaned_items(self):
    """List orphaned harga items"""
    /api/project/[id]/orphaned-items/
```

**Why Important:**
- Cleanup feature for data hygiene
- Identify unused items taking up space
- Important for large projects

**Endpoints:**
1. **GET** `/api/project/[id]/orphaned-items/` - List orphaned items
2. **POST** `/api/project/[id]/orphaned-items/cleanup/` - Cleanup orphaned items

---

### **Category 6: Monitoring & Performance APIs (3 new)**

Track performance and deprecation metrics.

```python
@tag('api', 'monitoring', 'phase4')
@task(1)
def api_performance_metrics(self):
    """Get performance metrics"""
    /api/monitoring/performance-metrics/
```

**Why Important:**
- Monitor API performance in production
- Track deprecated endpoint usage
- Identify slow operations

**Endpoints:**
1. **GET** `/api/monitoring/performance-metrics/` - Get performance metrics
2. **GET** `/api/monitoring/deprecation-metrics/` - Get deprecation metrics
3. **POST** `/api/monitoring/report-client-metric/` - Report client-side metrics

---

## 🚀 How to Run Phase 4 Test

### **Quick Start:**

```bash
# Terminal 1: Start Django server
python manage.py runserver

# Terminal 2: Run Phase 4 test
run_test_phase4.bat
```

### **Manual Command:**

```bash
locust -f load_testing/locustfile.py --headless -u 10 -r 2 -t 150s --host=http://localhost:8000 --csv=hasil_test_v10_phase4 --html=hasil_test_v10_phase4.html
```

**Note:** Duration increased to **150s** (2.5 minutes) to ensure all 88 endpoints get called.

---

## 📈 Expected Results

### **Performance Targets:**

| Endpoint Type | Target Response Time | Notes |
|--------------|---------------------|-------|
| **Tahapan APIs** | < 300ms (P95) | Moderate complexity |
| **V2 APIs** | < 500ms (P95) | Weekly operations |
| **Export PDFs** | < 3000ms (P95) | HEAVY |
| **Export Word** | < 2000ms (P95) | Moderate |
| **Export Excel** | < 1000ms (P95) | Fast |
| **Monitoring APIs** | < 200ms (P95) | Lightweight |
| **Cleanup Operations** | < 1000ms (P95) | Database operations |

### **Success Criteria:**

- ✅ **Success rate > 95%** (some heavy exports may timeout)
- ✅ **Tahapan APIs functional** (critical gap filled!)
- ✅ **V2 APIs working** (new architecture validated)
- ✅ **Export coverage > 90%** (almost complete!)
- ✅ **No unexpected 500 errors**
- ⚠️ **PDF exports may timeout** (acceptable - very heavy)

---

## 📊 Comparison: Phase 3 vs Phase 4 (Expected)

| Metric | Phase 3 | Phase 4 (Expected) | Change |
|--------|---------|-------------------|--------|
| **Endpoints** | 63 | 88 (+25) | +40% ✅ |
| **Success Rate** | 99.7% | > 95% | May decrease (more operations) |
| **Total Requests** | 333 | ~500 (+167) | +50% |
| **Coverage** | 47.7% | 66.7% | +19% ✅ |
| **Tahapan Coverage** | 10% | 70% | +60% ✅ |
| **Export Coverage** | 67% | 93% | +26% ✅ |

**Note:** More write operations (tahapan, cleanup) = potential for more failures

---

## ⚠️ Important Notes

### **Write Operations Require Ownership**

Many Phase 4 endpoints are **write operations** that require project ownership:
- Tahapan assign/unassign
- V2 weekly assignments
- Orphaned items cleanup
- Tahapan regenerate

**Expected Behavior:**
- Test user may get **403 Forbidden** (not project owner)
- This is **acceptable** - mark as success in Locust tests
- We're testing endpoint availability, not full authorization flow

### **Heavy Operations**

**PDF Exports** are expected to be SLOW:
- Rekap RAB PDF: 2-5 seconds
- Jadwal PDF: 1-3 seconds
- Volume PDF: 1-3 seconds
- Rincian AHSP Word: 2-4 seconds

**Acceptable Timeouts:**
- ⚠️ PDF exports may timeout under load (acceptable)
- ⚠️ V2 regenerate tahapan may timeout (heavy operation)
- ⚠️ Cleanup operations may be slow (database intensive)

### **Success Rate Targets**

- **Read APIs**: 98%+
- **Write APIs**: 80%+ (many will return 403 - acceptable)
- **Export PDFs**: 70%+ (timeouts acceptable)
- **Overall**: 95%+

---

## 🔍 What to Check After Test

### **1. Tahapan APIs Coverage**
```bash
# Check hasil_test_v10_phase4_stats.csv
# Verify tahapan endpoints were called:
# - GET tahapan detail
# - POST assign/unassign
# - GET unassigned
# - POST validate
```

### **2. V2 APIs Functional**
```bash
# Verify V2 tahapan endpoints:
# - POST assign-weekly
# - POST regenerate-tahapan
# - POST reset-progress
# - POST week-boundary
```

### **3. Export Coverage Complete**
```bash
# Verify NEW exports were called:
# - Rekap RAB PDF
# - Rincian AHSP Word
# - Rekap Kebutuhan JSON/Word
# - Jadwal PDF
# - Volume PDF/Word/Excel
```

### **4. 403 Errors Acceptable**
```bash
# Check failures.csv
# 403 errors on write operations are EXPECTED and ACCEPTABLE:
# - Tahapan assign/unassign
# - V2 assignments
# - Orphaned items cleanup
```

---

## 🎯 Success Metrics

### **Must Achieve:**
- ✅ Overall success rate > 95%
- ✅ Tahapan APIs callable (even if 403)
- ✅ V2 APIs working
- ✅ Export coverage > 90%
- ✅ No unexpected 500 errors

### **Good to Have:**
- ✅ PDF exports > 70% success
- ✅ Write operations functional (if test user is owner)
- ✅ Monitoring APIs working
- ✅ All Phase 4 endpoints called at least once

### **Acceptable:**
- ⚠️ 403 errors on write operations (expected for non-owners)
- ⚠️ PDF export timeouts (heavy operation)
- ⚠️ V2 regenerate timeout (very heavy)
- ⚠️ Slightly lower success rate than Phase 3 (more complex operations)

---

## 📁 Files to be Modified

### **1. load_testing/locustfile.py**
**Changes:**
- Add 6 tahapan management tasks to `APIUser` class
- Add 4 V2 tahapan tasks to `APIUser` class
- Add 8 export tasks to `HeavyUser` class
- Add 2 rekap kebutuhan tasks to `APIUser` class
- Add 2 orphaned items tasks to `APIUser` class
- Add 3 monitoring tasks to `APIUser` class

**Total Lines to Add:** ~300 lines

### **2. run_test_phase4.bat** (NEW)
**Purpose:** Quick runner script for Phase 4 test with 150s duration

### **3. PHASE4_IMPLEMENTATION.md** (THIS FILE)
**Purpose:** Complete documentation of Phase 4 additions

---

## 🔄 Next Steps After Phase 4 Test

### **If Test Passes (Success Rate > 95%):**

1. **✅ Celebrate!** - Coverage improved from 19.7% to 66.7% (3.4x increase!)

2. **Review Performance:**
   - Check if V2 Rekap Kebutuhan Weekly was called
   - Still need optimization (3-7 seconds is critical!)
   - Review new endpoints for performance issues

3. **Decide Next Step:**
   - **Option A**: Implement performance optimizations (RECOMMENDED before scaling)
   - **Option B**: Start scaling tests (30→50→100 users)
   - **Option C**: Add remaining endpoints to reach 80%+ coverage

### **If Test Has Issues:**

1. **Check failures.csv** - Which endpoints failed?

2. **Common Expected Issues:**
   - **403 on write operations**: Expected for non-owners (ACCEPTABLE)
   - **PDF export timeouts**: Expected for heavy documents (ACCEPTABLE)
   - **V2 regenerate timeout**: Expected for large projects (ACCEPTABLE)
   - **500 errors**: Investigate and fix

3. **Fix and Re-test:**
   ```bash
   run_test_phase4.bat
   ```

---

## ✅ Summary

**Phase 4 Achievement Target:**
- ✅ 25 new endpoints added
- ✅ Tahapan coverage: 10% → 70% (+60%)
- ✅ Export coverage: 67% → 93% (+26%)
- ✅ Overall coverage: 47.7% → 66.7% (+19%)
- ✅ Monitoring APIs included
- ✅ Critical gaps filled

**What's New:**
- Tahapan management (assign, unassign, reorder)
- V2 weekly assignments
- Remaining export formats (PDF, Word, Excel variants)
- Orphaned items cleanup
- Monitoring & performance tracking

**What's Next:**
- Run Phase 4 test
- Review results
- Implement performance optimizations
- Start scaling tests OR add more endpoints

---

**Phase 4 Implementation Status:** ✅ PLANNED - READY FOR IMPLEMENTATION
**Ready for Coding:** ✅ YES
**Next Phase:** Scaling tests (30-200 users) OR Performance optimization
