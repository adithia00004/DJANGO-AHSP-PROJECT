# 🔍 Load Test Coverage Analysis - Missing Endpoints

**Generated:** 2026-01-10
**Status:** CRITICAL gaps identified in load test coverage

---

## 📊 Coverage Summary

| Category | Total | Tested | Missing | Coverage % | Status |
|----------|-------|--------|---------|------------|--------|
| **All detail_project Endpoints** | 132 | 26 | 106 | 19.7% | ❌ **POOR** |
| **CRITICAL APIs** | 13 | 5 | 8 | 38% | ⚠️ **INSUFFICIENT** |
| **HIGH Priority APIs** | 35 | 7 | 28 | 20% | ⚠️ **POOR** |
| **Page Views** | 14 | 6 | 8 | 43% | 🟡 **MODERATE** |
| **Export Operations** | 30 | 4 | 26 | 13% | ❌ **VERY POOR** |
| **Write APIs** | 21 | 1* | 20 | 5% | ❌ **CRITICAL** |

*Only `volume-pekerjaan/save/` tested, but in DISABLED MutationUser class

---

## 🚨 CRITICAL Findings

### 1. **Search/Autocomplete NOT TESTED** ⚠️⚠️⚠️
**Endpoint:** `/api/project/<int:project_id>/search-ahsp/`

**Issue:** This is called on EVERY KEYSTROKE when users type in AHSP dropdown (Select2 autocomplete)

**Risk:**
- High frequency endpoint (10-50 calls per user interaction)
- Not tested under load
- Could become bottleneck with concurrent users
- Low latency required (<100ms expected)

**Impact if slow:**
- Dropdown lag
- Poor UX
- Database query storms

**Recommendation:** Add IMMEDIATELY with high task weight (task(10))

---

### 2. **Business Logic Not Load Tested** ⚠️⚠️
**Endpoints:**
- `/api/project/<int:project_id>/pricing/`
- `/api/project/<int:project_id>/pekerjaan/<int:pekerjaan_id>/pricing/`

**Issue:** Core profit/margin calculations not tested

**Risk:**
- Business-critical calculations
- Complex aggregations
- Potential performance issues undetected

**Recommendation:** Add to APIUser with medium-high weight

---

### 3. **Write Operations Undertested** ⚠️⚠️
**Issue:** Only 1 write operation tested (and it's DISABLED!)

**Missing CRITICAL writes:**
- `list-pekerjaan/save/` - Tree structure saves
- `assign-weekly/` - V2 canonical assignments
- `harga-items/save/` - Bulk item saves
- `detail-ahsp/save/` - Complex nested saves

**Risk:**
- Concurrency issues undetected
- Optimistic locking not tested
- Database deadlocks possible
- Data corruption risks

**Recommendation:**
- Enable MutationUser class
- Use dedicated test database
- Test with concurrent writes
- Validate optimistic locking behavior

---

### 4. **V2 Architecture Underrepresented** ⚠️
**Missing V2 APIs:**
- `weekly-progress/` - Canonical storage foundation
- `kurva-s-harga/` - Cost-based calculations
- `rekap-kebutuhan-weekly/` - Weekly breakdowns
- `assign-weekly/` - Write operations

**Risk:**
- New architecture not validated under load
- Migration risks
- Performance characteristics unknown

---

### 5. **Export Coverage Biased** ⚠️
**Issue:**
- Testing same data (Rekap RAB) in multiple formats
- Missing critical exports:
  - Full backup JSON (VERY HEAVY)
  - Professional reports (EXTREMELY HEAVY)
  - NEW rincian RAB exports

**Risk:**
- Heavy operations not tested
- Memory/timeout issues possible
- CPU spike risks

---

## 🎯 3-Phase Addition Plan

### **PHASE 1: CRITICAL Additions (Immediate - This Week)**
**Goal:** Cover high-frequency and business-critical endpoints

#### Add to `APIUser` class:

```python
@tag('api', 'critical', 'autocomplete')
@task(10)  # HIGH frequency
def api_search_ahsp(self):
    """Autocomplete search - Called on every keystroke"""
    project_id = random.choice(self.project_ids)
    search_term = random.choice(['beton', 'semen', 'pasir', 'besi', 'kayu'])
    self.client.get(
        _api_url(project_id, f"search-ahsp/?q={search_term}"),
        name="/api/project/[id]/search-ahsp/"
    )

@tag('api', 'critical', 'pricing')
@task(6)
def api_project_pricing(self):
    """Project pricing calculation - Business logic"""
    project_id = random.choice(self.project_ids)
    self.client.get(
        _api_url(project_id, "pricing/"),
        name="/api/project/[id]/pricing/"
    )

@tag('api', 'critical', 'pricing')
@task(5)
def api_pekerjaan_pricing(self):
    """Per-pekerjaan pricing"""
    project_id = random.choice(self.project_ids)
    pekerjaan_id = random.randint(1, 50)
    with self.client.get(
        _api_url(project_id, f"pekerjaan/{pekerjaan_id}/pricing/"),
        name="/api/project/[id]/pekerjaan/[pekerjaan_id]/pricing/",
        catch_response=True
    ) as response:
        if response.status_code in [200, 404]:
            response.success()
        else:
            response.failure(f"HTTP {response.status_code}")

@tag('api', 'critical', 'validation')
@task(5)
def api_validate_rekap_kebutuhan(self):
    """Data validation - Phase 5"""
    project_id = random.choice(self.project_ids)
    self.client.get(
        _api_url(project_id, "rekap-kebutuhan/validate/"),
        name="/api/project/[id]/rekap-kebutuhan/validate/"
    )

@tag('api', 'critical', 'new')
@task(5)
def api_rincian_rab(self):
    """NEW rincian RAB API"""
    project_id = random.choice(self.project_ids)
    self.client.get(
        _api_url(project_id, "rincian-rab/"),
        name="/api/project/[id]/rincian-rab/"
    )

@tag('api', 'critical', 'enhanced')
@task(5)
def api_rekap_kebutuhan_enhanced(self):
    """Enhanced rekap with filters"""
    project_id = random.choice(self.project_ids)
    self.client.get(
        _api_url(project_id, "rekap-kebutuhan-enhanced/"),
        name="/api/project/[id]/rekap-kebutuhan-enhanced/"
    )

@tag('api', 'v2', 'critical')
@task(4)
def api_kurva_s_harga(self):
    """V2 cost-based S-curve"""
    project_id = random.choice(self.project_ids)
    self.client.get(
        _api_v2_url(project_id, "kurva-s-harga/"),
        name="/api/v2/project/[id]/kurva-s-harga/"
    )

@tag('api', 'v2', 'critical')
@task(4)
def api_rekap_kebutuhan_weekly(self):
    """V2 weekly procurement breakdown"""
    project_id = random.choice(self.project_ids)
    self.client.get(
        _api_v2_url(project_id, "rekap-kebutuhan-weekly/"),
        name="/api/v2/project/[id]/rekap-kebutuhan-weekly/"
    )
```

#### Add to `BrowsingUser` class:

```python
@tag('page', 'rincian_ahsp')
@task(4)
def browse_rincian_ahsp(self):
    """View rincian AHSP gabungan"""
    project_id = random.choice(self.project_ids)
    self.client.get(
        _page_url(project_id, "rincian-ahsp/"),
        name="/detail_project/[id]/rincian-ahsp/"
    )

@tag('page', 'rekap_kebutuhan')
@task(3)
def browse_rekap_kebutuhan(self):
    """View rekap kebutuhan (material requirements)"""
    project_id = random.choice(self.project_ids)
    self.client.get(
        _page_url(project_id, "rekap-kebutuhan/"),
        name="/detail_project/[id]/rekap-kebutuhan/"
    )

@tag('page', 'rincian_rab')
@task(3)
def browse_rincian_rab(self):
    """View rincian RAB (NEW)"""
    project_id = random.choice(self.project_ids)
    self.client.get(
        _page_url(project_id, "rincian-rab/"),
        name="/detail_project/[id]/rincian-rab/"
    )

@tag('page', 'audit_trail')
@task(2)
def browse_audit_trail(self):
    """View audit trail"""
    project_id = random.choice(self.project_ids)
    self.client.get(
        _page_url(project_id, "audit-trail/"),
        name="/detail_project/[id]/audit-trail/"
    )
```

#### Enable `MutationUser` class (with caution):

```python
class MutationUser(AuthenticatedUser):
    """Test concurrent writes - USE DEDICATED TEST DATABASE"""
    weight = 1
    wait_time = between(5, 15)

    # ENABLE with caution!
    MUTATIONS_ENABLED = True  # ⚠️ Will write to database

    @tag('mutation', 'critical', 'tree')
    @task(4)
    def save_list_pekerjaan(self):
        """Test tree structure save + optimistic locking"""
        if not self.MUTATIONS_ENABLED:
            return

        project_id = random.choice(self.project_ids)
        # Simplified test data
        test_data = {
            "items": [
                {
                    "id": None,
                    "uraian": f"Test Pekerjaan {random.randint(1000, 9999)}",
                    "ordering_index": 1
                }
            ]
        }

        with self.client.post(
            _api_url(project_id, "list-pekerjaan/save/"),
            json=test_data,
            name="/api/project/[id]/list-pekerjaan/save/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 400]:  # 400 = validation error OK
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @tag('mutation', 'critical', 'v2', 'assignment')
    @task(3)
    def assign_weekly_v2(self):
        """Test V2 canonical weekly assignment"""
        if not self.MUTATIONS_ENABLED:
            return

        project_id = random.choice(self.project_ids)
        pekerjaan_id = random.randint(1, 50)
        week_number = random.randint(1, 20)

        test_data = {
            "pekerjaan_id": pekerjaan_id,
            "week_number": week_number,
            "percentage": random.randint(5, 20)
        }

        with self.client.post(
            _api_v2_url(project_id, "assign-weekly/"),
            json=test_data,
            name="/api/v2/project/[id]/assign-weekly/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 400, 404]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
```

**Expected Impact:**
- **+15 endpoints tested**
- Coverage: 19.7% → 31.1% (+11.4%)
- CRITICAL APIs: 38% → 100% coverage
- HIGH Priority APIs: 20% → 40% coverage

---

### **PHASE 2: HIGH Priority Additions (Next Sprint)**
**Goal:** Add frequently-used features and representative export samples

#### Additional API endpoints (10-15):
- Audit trail
- Template library (list, detail, import)
- Bundle expansion
- Conversion profiles
- V2 weekly progress
- Parameter detail

#### Representative exports (5-7):
- Full backup JSON (VERY HEAVY)
- Jadwal professional report (EXTREMELY HEAVY)
- Rincian RAB CSV export (NEW)
- 1 PDF + 1 Excel per data type (sample coverage)

#### Additional write operations (3-5):
- Harga items save
- Detail AHSP save
- Tahapan assignment
- Template create

**Expected Impact:**
- **+25 endpoints tested**
- Coverage: 31.1% → 50.8% (+19.7%)
- Write APIs: 5% → 30% coverage
- Export ops: 13% → 35% coverage

---

### **PHASE 3: MEDIUM Priority (Optional Enhancement)**
**Goal:** Comprehensive coverage for completeness

#### Complete remaining endpoints (30-40):
- All export format variations
- Full template library CRUD
- Complete tahapan API coverage
- Batch export system (if in production)
- Additional V2 APIs

**Expected Impact:**
- **+40 endpoints tested**
- Coverage: 50.8% → 81.1% (+30.3%)
- Near-complete coverage for user-facing features

---

## ⚠️ IMPORTANT: Write Operation Testing

### Prerequisites for MutationUser Testing:

1. **Dedicated Test Database:**
   ```python
   # settings_test.py
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'ahsp_loadtest',  # Separate DB
           'USER': 'test_user',
           'PASSWORD': 'test_password',
       }
   }
   ```

2. **Test Data Setup:**
   - Populate with realistic project data
   - Ensure sufficient test projects
   - Verify user permissions

3. **Post-Test Cleanup:**
   ```bash
   # After test, reset database
   python manage.py flush --database=ahsp_loadtest --no-input
   ```

4. **Monitoring:**
   - Watch for database locks
   - Monitor optimistic locking failures
   - Check for data corruption
   - Verify transaction rollbacks

### Testing Strategy for Writes:

```python
# Run separately from read-only tests
locust -f load_testing/locustfile.py \
    --headless \
    -u 10 \  # Start with low concurrency
    -r 1 \   # Slow spawn rate
    -t 120s \
    --host=http://localhost:8000 \
    --tags mutation \  # Only run mutation tests
    --csv=hasil_test_mutations
```

**Focus Areas:**
1. **Concurrency conflicts** - Multiple users editing same data
2. **Optimistic locking** - Version conflicts
3. **Database deadlocks** - Transaction ordering
4. **Data integrity** - Validation under load
5. **Response times** - Write performance

---

## 📈 Coverage Improvement Roadmap

### Current State:
```
████░░░░░░░░░░░░░░░░ 19.7% coverage
```

### After Phase 1 (Week 1):
```
██████░░░░░░░░░░░░░░ 31.1% coverage (+11.4%)
```

### After Phase 2 (Week 2-3):
```
██████████░░░░░░░░░░ 50.8% coverage (+19.7%)
```

### After Phase 3 (Week 4-6):
```
████████████████░░░░ 81.1% coverage (+30.3%)
```

---

## 🎯 Success Metrics

### Phase 1 Targets:
- ✅ Search/autocomplete tested (<100ms response)
- ✅ Pricing APIs validated (business logic)
- ✅ Critical page views covered
- ✅ V2 architecture validated
- ✅ Basic write operations tested

### Phase 2 Targets:
- ✅ Export operations representative sample tested
- ✅ Template library workflows validated
- ✅ Concurrency testing for writes initiated
- ✅ 50%+ coverage achieved

### Phase 3 Targets:
- ✅ 80%+ coverage of user-facing endpoints
- ✅ All critical paths validated
- ✅ Heavy operations stress tested
- ✅ Production-ready confidence

---

## 🚀 Implementation Priority

### This Week (CRITICAL):
1. Add search/autocomplete (task(10))
2. Add pricing APIs (task(6))
3. Add rincian-ahsp page (task(4))
4. Add rekap-kebutuhan page (task(3))

### Next Week (HIGH):
5. Add V2 APIs (kurva-s-harga, rekap-weekly)
6. Add validation endpoint
7. Add rincian-rab (NEW)
8. Enable basic mutation testing

### Following Weeks (MEDIUM):
9. Add export samples (heavy operations)
10. Add template library
11. Complete V2 coverage
12. Comprehensive write testing

---

## 📝 Notes

### Why Some Endpoints Skipped:

**Monitoring Endpoints:**
- Developer/admin tools
- Testing would pollute metrics
- Separate test suite recommended

**Deep/Batch Copy:**
- EXTREMELY heavy operations
- Create many database records
- Dedicated performance test only
- Not for regular load tests

**Legacy Aliases:**
- If main endpoints work, aliases likely fine
- Test one sample for validation

---

## ✅ Action Items

- [ ] **IMMEDIATE**: Add Phase 1 critical endpoints to locustfile.py
- [ ] **THIS WEEK**: Run baseline test with Phase 1 additions
- [ ] **THIS WEEK**: Set up dedicated test database for mutations
- [ ] **NEXT WEEK**: Implement Phase 2 endpoints
- [ ] **NEXT WEEK**: Enable and test MutationUser with concurrency
- [ ] **WEEK 3-4**: Add export operation samples
- [ ] **WEEK 4-6**: Complete Phase 3 comprehensive coverage

---

**Last Updated:** 2026-01-10
**Status:** Action required - Critical gaps identified
**Next Review:** After Phase 1 implementation
