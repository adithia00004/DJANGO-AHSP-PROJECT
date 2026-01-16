# 🗓️ TESTING & BUG FIX AGENDA - DETAIL PROJECT APP

**Created:** 2025-11-09
**Target Completion:** Week of 2025-11-16
**Status:** 🟡 IN PROGRESS

---

## 📊 CURRENT STATUS

```
Automated Tests: 259/308 PASSING (84.4%)
Manual Tests:    0/10 PAGES TESTED
Bugs Found:      TBD
Critical Fixes:  3 PENDING
```

---

## 🎯 OBJECTIVES

1. ✅ Fix all critical automated test failures (target: >95% pass rate)
2. ✅ Manually test all 10 pages in detail_project app
3. ✅ Document bugs/features discovered during manual testing
4. ✅ Implement user warning for cascade reset (UX improvement)
5. ✅ Update documentation with findings

---

## 📅 TIMELINE OVERVIEW

| Phase | Duration | Focus | Status |
|-------|----------|-------|--------|
| **Phase 1** | Day 1-2 | Fix Critical Automated Tests | 🔴 PENDING |
| **Phase 2** | Day 3-4 | Manual Testing (Pages 1-5) | ⏳ WAITING |
| **Phase 3** | Day 5-6 | Manual Testing (Pages 6-10) | ⏳ WAITING |
| **Phase 4** | Day 7 | Bug Fixes & UX Improvements | ⏳ WAITING |
| **Phase 5** | Day 8 | Documentation & Review | ⏳ WAITING |

---

# PHASE 1: FIX CRITICAL AUTOMATED TESTS (Day 1-2)

## 🔴 Priority 1: Fix Test Infrastructure Errors

### Task 1.1: Fix Klasifikasi Field Name (nama → name)
**Impact:** 3 tests failing
**Severity:** 🔴 HIGH
**Files to fix:**
- `detail_project/tests/test_phase5_integration.py`

**Changes needed:**
```python
# Line 139, 141, 175
# OLD:
payload = {
    'klasifikasi': [{
        'nama': 'Test Klasifikasi',
        'subs': [{'nama': 'Sub1', ...}]
    }]
}

# NEW:
payload = {
    'klasifikasi': [{
        'name': 'Test Klasifikasi',  # ← Changed
        'subs': [{'name': 'Sub1', ...}]  # ← Changed
    }]
}
```

**Estimated time:** 30 minutes
**Status:** ⏳ PENDING

---

### Task 1.2: Fix tanggal_mulai Constraint Violations
**Impact:** 24 tests failing
**Severity:** 🔴 HIGH
**Root cause:** Tests creating Project directly without tanggal_mulai

**Strategy:**
1. Grep all direct Project.objects.create() calls
2. Replace with fixture usage or add tanggal_mulai
3. Verify conftest.py fixture is complete

**Command to find issues:**
```bash
grep -r "Project.objects.create" detail_project/tests/ | grep -v conftest
```

**Fix pattern:**
```python
# ❌ BAD - Will fail with NULL constraint
def test_something(user):
    project = Project.objects.create(
        nama="Test",
        owner=user,
        sumber_dana="APBD",
        lokasi_project="Jakarta",
        nama_client="Client Test",
        anggaran_owner=1000000
        # Missing: tanggal_mulai ❌
    )

# ✅ GOOD - Use fixture
def test_something(project):  # Use existing fixture
    # project already has tanggal_mulai

# ✅ ACCEPTABLE - Add tanggal_mulai manually
from datetime import date
def test_something(user):
    project = Project.objects.create(
        ...,
        tanggal_mulai=date.today()  # ✅ Add this
    )
```

**Files likely affected:**
- `test_api_numeric_endpoints.py` (5 tests)
- `test_weekly_canonical_validation.py` (13 tests)
- `test_rekap_consistency.py` (2 tests)
- `test_rekap_rab_with_buk_and_lain.py` (1 test)
- `test_tahapan_generation_conversion.py` (1 test)
- `test_phase5_security.py` (1 test)

**Estimated time:** 2-3 hours
**Status:** ⏳ PENDING

---

### Task 1.3: Run Full Test Suite
**Command:**
```bash
pytest detail_project/tests/ -v --tb=short > test_results_fixed.txt 2>&1
```

**Success criteria:**
- ✅ Pass rate > 95% (293+ tests passing)
- ✅ No critical errors
- ✅ All infrastructure tests passing

**Estimated time:** 30 minutes
**Status:** ⏳ PENDING

---

## 🟡 Priority 2: Document Test Failures (Not Blocking)

### Task 1.4: Categorize Remaining Failures
Create `TEST_FAILURES_ANALYSIS.md` with:
- Security test failures (expected in dev mode)
- Rate limiting failures (infrastructure)
- Performance test failures (index missing)

**Estimated time:** 1 hour
**Status:** ⏳ PENDING

---

# PHASE 2: MANUAL TESTING - PAGES 1-5 (Day 3-4)

## 📋 MANUAL TEST CHECKLIST

For each page, test:
1. ✅ Page loads without errors
2. ✅ Data displays correctly
3. ✅ CRUD operations work
4. ✅ Validation works
5. ✅ Error messages are clear
6. ✅ Export functions work (if applicable)
7. ✅ Search/filter works (if applicable)
8. ✅ UI/UX is smooth
9. ✅ Mobile responsive (bonus)
10. ✅ Cascade effects work correctly

---

## Page 1: List Pekerjaan 📝

**URL:** `/detail_project/<project_id>/list-pekerjaan/`
**Purpose:** Manage work items (Klasifikasi → Sub → Pekerjaan hierarchy)

### Test Scenarios:

#### Scenario 1.1: Basic CRUD Operations
- [ ] Create new Klasifikasi
- [ ] Create new Sub-Klasifikasi
- [ ] Create new Pekerjaan (CUSTOM)
- [ ] Edit existing Pekerjaan
- [ ] Delete Pekerjaan
- [ ] Verify cascade delete (delete Klasifikasi → all children deleted)

#### Scenario 1.2: Source Type Changes (CASCADE RESET TESTING)
**CRITICAL: This is the main feature from documentation!**

- [ ] Create CUSTOM pekerjaan with:
  - [ ] Volume: 100.00
  - [ ] Template AHSP: 2-3 items
  - [ ] Jadwal: assigned to tahapan
  - [ ] Uraian: "Test Custom Pekerjaan"
  - [ ] Satuan: "unit"

- [ ] Change CUSTOM → REFERENSI:
  - [ ] ✅ Frontend auto-clears uraian/satuan
  - [ ] ✅ Ref dropdown enabled
  - [ ] Select AHSP reference
  - [ ] Click Save
  - [ ] **VERIFY CASCADE RESET:**
    - [ ] Volume reset to NULL ✅
    - [ ] Template AHSP replaced with ref data ✅
    - [ ] Jadwal cleared ✅
    - [ ] Formula state cleared ✅
    - [ ] detail_ready = False ✅
  - [ ] **CHECK:** Pekerjaan still exists (not deleted) ✅

- [ ] Change REF → CUSTOM:
  - [ ] Enter custom uraian/satuan
  - [ ] Click Save
  - [ ] **VERIFY CASCADE RESET:**
    - [ ] All related data cleared ✅
    - [ ] ref_id = NULL ✅

- [ ] Change REF → REF (different ref_id):
  - [ ] Select different AHSP
  - [ ] Click Save
  - [ ] **VERIFY CASCADE RESET:**
    - [ ] Old template replaced with new ✅
    - [ ] Volume reset ✅

#### Scenario 1.3: Validation & Error Handling
- [ ] Try to change CUSTOM → REF without selecting reference
  - [ ] **EXPECT:** Clear error message (not Error 500)
  - [ ] Message: "Wajib diisi saat mengganti source type ke ref/ref_modified"

- [ ] Try to save CUSTOM without uraian
  - [ ] **EXPECT:** Validation error

- [ ] Try to create duplicate kode
  - [ ] **EXPECT:** Validation error

#### Scenario 1.4: Search Functionality
- [ ] Search by kode pekerjaan
- [ ] Search by uraian
- [ ] Search by AHSP reference kode
- [ ] Search by AHSP reference nama
- [ ] Verify tree filtering (only matching branches shown)

#### Scenario 1.5: UI/UX Elements
- [ ] Dropdown Select2 not clipped by containers
- [ ] Textarea auto-resize works
- [ ] Preview sync works
- [ ] Reordering (drag-drop if implemented)

**🐛 BUGS FOUND:**
```
Bug ID: LP-001
Description:
Severity:
Steps to reproduce:
Expected:
Actual:
Screenshot: (if applicable)
```

**💡 FEATURE REQUESTS:**
```
FR ID: LP-FR-001
Description:
Priority:
Justification:
```

**⏱️ Time spent:** _____ minutes
**Status:** ⏳ PENDING

---

## Page 2: Volume Pekerjaan 📊

**URL:** `/detail_project/<project_id>/volume-pekerjaan/`
**Purpose:** Set quantities for each pekerjaan

### Test Scenarios:

#### Scenario 2.1: Basic Volume Input
- [ ] Page loads and shows all pekerjaan
- [ ] Input decimal volume (e.g., 123.456)
- [ ] Input integer volume (e.g., 100)
- [ ] Save successfully
- [ ] Verify data persists after refresh

#### Scenario 2.2: Formula Mode
- [ ] Switch to formula mode
- [ ] Enter formula: `=10 * 5`
- [ ] Verify calculation: result = 50.000
- [ ] Save formula
- [ ] Refresh and verify formula persists
- [ ] Edit formula
- [ ] Clear formula (back to manual)

#### Scenario 2.3: Validation
- [ ] Try negative volume
  - [ ] **EXPECT:** Validation error or prevented
- [ ] Try non-numeric input
  - [ ] **EXPECT:** Validation error
- [ ] Try extremely large number (> max_digits)
  - [ ] **EXPECT:** Handled gracefully

#### Scenario 2.4: Cascade Effect Check
- [ ] Set volume for pekerjaan
- [ ] Go to List Pekerjaan
- [ ] Change source type
- [ ] Return to Volume Pekerjaan
- [ ] **VERIFY:** Volume reset to NULL/empty

#### Scenario 2.5: Export
- [ ] Export to CSV
- [ ] Export to PDF
- [ ] Export to Word
- [ ] Verify data accuracy in exports

**🐛 BUGS FOUND:**
```
Bug ID: VP-001
Description:
```

**⏱️ Time spent:** _____ minutes
**Status:** ⏳ PENDING

---

## Page 3: Template AHSP (Detail AHSP) 🔧

**URL:** `/detail_project/<project_id>/template-ahsp/`
**Purpose:** Define AHSP breakdown for each pekerjaan (TK, BHN, ALT, LAIN)

### Test Scenarios:

#### Scenario 3.1: View Template
- [ ] Select pekerjaan from dropdown
- [ ] Verify template loads
- [ ] Check categories: TK, BHN, ALT, LAIN

#### Scenario 3.2: Edit Template (CUSTOM Pekerjaan)
- [ ] Add new item (TK)
  - [ ] Input: kode, uraian, satuan, koefisien
  - [ ] Save
  - [ ] Verify item appears
- [ ] Edit existing item
  - [ ] Change koefisien
  - [ ] Save
  - [ ] Verify update
- [ ] Delete item
  - [ ] Confirm deletion
  - [ ] Verify removed

#### Scenario 3.3: REF Pekerjaan (Read-Only)
- [ ] Select REF pekerjaan
- [ ] **VERIFY:** Items shown but not editable
- [ ] Try to add item
  - [ ] **EXPECT:** Blocked or disabled

#### Scenario 3.4: REF_MODIFIED Pekerjaan
- [ ] Select REF_MODIFIED pekerjaan
- [ ] **VERIFY:** Can override koefisien only
- [ ] Change koefisien
- [ ] Save
- [ ] Verify override persists

#### Scenario 3.5: Bundle Support (Pekerjaan as Item)
- [ ] Add pekerjaan as bundle item
- [ ] Verify circular dependency detection
  - [ ] Try to add pekerjaan A to itself
  - [ ] **EXPECT:** Error prevented
- [ ] Verify bundle expansion works

#### Scenario 3.6: Reset to Reference
- [ ] For REF_MODIFIED pekerjaan
- [ ] Click "Reset to Reference"
- [ ] **VERIFY:** All overrides cleared
- [ ] Template back to original ref data

#### Scenario 3.7: Validation
- [ ] Try duplicate kode
  - [ ] **EXPECT:** Error (HTTP 207 multi-status)
- [ ] Try empty koefisien
  - [ ] **EXPECT:** Validation error
- [ ] Try invalid decimal format
  - [ ] **EXPECT:** Parsed correctly or error

**🐛 BUGS FOUND:**
```
Bug ID: TA-001
Description:
```

**⏱️ Time spent:** _____ minutes
**Status:** ⏳ PENDING

---

## Page 4: Harga Items 💰

**URL:** `/detail_project/<project_id>/harga-items/`
**Purpose:** Set unit prices for all items (TK, BHN, ALT, LAIN)

### Test Scenarios:

#### Scenario 4.1: View Harga Items
- [ ] Page loads all categories
- [ ] Filter by kategori (TK/BHN/ALT/LAIN)
- [ ] Search by kode
- [ ] Search by uraian

#### Scenario 4.2: Edit Prices
- [ ] Edit harga_satuan
- [ ] Input: 123456.78
- [ ] Save
- [ ] Verify decimal places (2 digits after comma)
- [ ] Verify thousands separator display

#### Scenario 4.3: Bulk Edit
- [ ] Select multiple items
- [ ] Apply price increase (e.g., +10%)
- [ ] Verify all updated correctly

#### Scenario 4.4: Import Harga
- [ ] Import from CSV/Excel
- [ ] Verify parsing
- [ ] Check error handling for invalid rows

#### Scenario 4.5: Export
- [ ] Export to CSV
- [ ] Export to PDF
- [ ] Export to Word

**🐛 BUGS FOUND:**
```
Bug ID: HI-001
Description:
```

**⏱️ Time spent:** _____ minutes
**Status:** ⏳ PENDING

---

## Page 5: Rincian AHSP 📋

**URL:** `/detail_project/<project_id>/rincian-ahsp/`
**Purpose:** Consolidated view of all AHSP details across all pekerjaan

### Test Scenarios:

#### Scenario 5.1: View Rincian
- [ ] Page loads with all pekerjaan
- [ ] Expand/collapse pekerjaan
- [ ] View all items under each pekerjaan
- [ ] Verify calculations (koefisien × volume × harga)

#### Scenario 5.2: Filter & Search
- [ ] Filter by kategori
- [ ] Search by item kode
- [ ] Search by item uraian
- [ ] Search by pekerjaan name

#### Scenario 5.3: Edit (if allowed)
- [ ] Try to edit koefisien
- [ ] Save changes
- [ ] Verify cascade to rekap

#### Scenario 5.4: Export
- [ ] Export to CSV
- [ ] Export to PDF
- [ ] Export to Word
- [ ] Verify all pekerjaan included

**🐛 BUGS FOUND:**
```
Bug ID: RA-001
Description:
```

**⏱️ Time spent:** _____ minutes
**Status:** ⏳ PENDING

---

# PHASE 3: MANUAL TESTING - PAGES 6-10 (Day 5-6)

## Page 6: Rekap RAB 💵

**URL:** `/detail_project/<project_id>/rekap-rab/`
**Purpose:** Summary of total costs per pekerjaan

### Test Scenarios:

#### Scenario 6.1: View Rekap
- [ ] Page loads summary
- [ ] Shows all pekerjaan with totals
- [ ] Breakdown by kategori (TK, BHN, ALT, LAIN)
- [ ] Grand total calculation

#### Scenario 6.2: Calculations Accuracy
- [ ] Pick one pekerjaan
- [ ] Manually calculate: Σ(koefisien × volume × harga)
- [ ] Compare with displayed total
- [ ] **EXPECT:** Match exactly

#### Scenario 6.3: BUK & LAIN Handling
- [ ] Verify BUK (Biaya Umum Kontraktor) included
- [ ] Verify LAIN category included
- [ ] Check percentage calculations if applicable

#### Scenario 6.4: Profit/Margin
- [ ] Input profit percentage (e.g., 10%)
- [ ] Verify calculation
- [ ] Save
- [ ] Verify persists

#### Scenario 6.5: Export
- [ ] Export to CSV
- [ ] Export to PDF (formatted nicely)
- [ ] Export to Word

**🐛 BUGS FOUND:**
```
Bug ID: RR-001
Description:
```

**⏱️ Time spent:** _____ minutes
**Status:** ⏳ PENDING

---

## Page 7: Rekap Kebutuhan 📦

**URL:** `/detail_project/<project_id>/rekap-kebutuhan/`
**Purpose:** Aggregate material/resource requirements across all pekerjaan

### Test Scenarios:

#### Scenario 7.1: View Kebutuhan
- [ ] Page loads aggregated items
- [ ] Groups same kode across pekerjaan
- [ ] Shows total quantity needed

#### Scenario 7.2: Verify Aggregation
- [ ] Find item used in multiple pekerjaan
- [ ] Manually sum: (koef1 × vol1) + (koef2 × vol2)
- [ ] Compare with displayed quantity
- [ ] **EXPECT:** Match

#### Scenario 7.3: Bundle Expansion
- [ ] Verify bundles are expanded (not shown as bundle)
- [ ] Check circular dependency handled

#### Scenario 7.4: Filter by Category
- [ ] Filter TK only
- [ ] Filter BHN only
- [ ] Filter ALT only

#### Scenario 7.5: Export
- [ ] Export to CSV
- [ ] Export to PDF
- [ ] Export to Word

**🐛 BUGS FOUND:**
```
Bug ID: RK-001
Description:
```

**⏱️ Time spent:** _____ minutes
**Status:** ⏳ PENDING

---

## Page 8: Jadwal Pekerjaan (Kelola Tahapan) 📅

**URL:** `/detail_project/<project_id>/jadwal-pekerjaan/`
**Purpose:** Schedule pekerjaan across time periods (tahapan)

### Test Scenarios:

#### Scenario 8.1: View Schedule
- [ ] Page loads with timeline
- [ ] Shows all tahapan (weeks/months)
- [ ] Shows pekerjaan assignments

#### Scenario 8.2: Create Tahapan
- [ ] Add new tahapan (e.g., "Minggu 1")
- [ ] Set date range
- [ ] Save
- [ ] Verify created

#### Scenario 8.3: Assign Pekerjaan to Tahapan
- [ ] Drag pekerjaan to tahapan (if drag-drop)
- [ ] Or: Select and assign
- [ ] Input proporsi_volume (e.g., 50%)
- [ ] Save
- [ ] Verify assignment

#### Scenario 8.4: Multiple Tahapan Assignment
- [ ] Assign same pekerjaan to 2 tahapan
  - [ ] Tahapan 1: 30%
  - [ ] Tahapan 2: 70%
- [ ] **VERIFY:** Total = 100%
- [ ] Try to save with total ≠ 100%
  - [ ] **EXPECT:** Validation error

#### Scenario 8.5: Unassign Pekerjaan
- [ ] Remove pekerjaan from tahapan
- [ ] Verify removed
- [ ] Check unassigned list updated

#### Scenario 8.6: Regenerate Tahapan
- [ ] Use time scale mode (weekly/monthly)
- [ ] Regenerate based on project duration
- [ ] **VERIFY:** Old manual assignments cleared
- [ ] **VERIFY:** New tahapan created correctly

#### Scenario 8.7: V2 API (Weekly Canonical)
- [ ] Assign using weekly canonical storage
- [ ] Switch view mode (daily/weekly/monthly)
- [ ] Verify data persists correctly
- [ ] Check no data loss on mode switch

**🐛 BUGS FOUND:**
```
Bug ID: JP-001
Description:
```

**⏱️ Time spent:** _____ minutes
**Status:** ⏳ PENDING

---

## Page 9: Rincian RAB (NEW) 📊

**URL:** `/detail_project/<project_id>/rincian-rab/`
**Purpose:** Detailed cost breakdown

### Test Scenarios:

#### Scenario 9.1: View Rincian RAB
- [ ] Page loads
- [ ] Shows detailed breakdown
- [ ] Check columns: Kode, Uraian, Satuan, Koef, Volume, Harga, Total

#### Scenario 9.2: Calculations
- [ ] Verify row totals
- [ ] Verify subtotals by pekerjaan
- [ ] Verify grand total

#### Scenario 9.3: Export
- [ ] Export CSV
- [ ] Verify format correct

**🐛 BUGS FOUND:**
```
Bug ID: RRB-001
Description:
```

**⏱️ Time spent:** _____ minutes
**Status:** ⏳ PENDING

---

## Page 10: Kelola Tahapan Grid 🎯

**URL:** `/detail_project/<project_id>/kelola-tahapan/` (if different from jadwal-pekerjaan)
**Purpose:** Grid-based schedule management

### Test Scenarios:

#### Scenario 10.1: Grid View
- [ ] Page loads grid
- [ ] Rows: Pekerjaan
- [ ] Columns: Tahapan
- [ ] Cells: Proporsi volume

#### Scenario 10.2: Edit in Grid
- [ ] Click cell
- [ ] Input percentage
- [ ] Save
- [ ] Verify saved

#### Scenario 10.3: Row Validation
- [ ] Fill row (one pekerjaan across multiple tahapan)
- [ ] Ensure total = 100%
- [ ] Try to exceed 100%
  - [ ] **EXPECT:** Validation error

**🐛 BUGS FOUND:**
```
Bug ID: KTG-001
Description:
```

**⏱️ Time spent:** _____ minutes
**Status:** ⏳ PENDING

---

# PHASE 4: BUG FIXES & UX IMPROVEMENTS (Day 7)

## Task 4.1: Implement User Warning Dialog

**Priority:** 🔴 CRITICAL
**File:** `detail_project/static/detail_project/js/list_pekerjaan.js`

**Implementation:**

```javascript
// Add before form submission
function confirmSourceChange(row) {
    const oldSourceType = row.dataset.originalSourceType || row.dataset.sourceType;
    const newSourceType = row.querySelector('[name*="source_type"]')?.value;

    // Check if pekerjaan has volume/jadwal/template
    const pekerjaanId = row.dataset.pekerjaanId;
    const hasVolume = checkIfPekerjaanHasVolume(pekerjaanId);  // Implement this
    const hasJadwal = checkIfPekerjaanHasJadwal(pekerjaanId);  // Implement this

    // Only show warning if source type changed AND has data
    if (oldSourceType !== newSourceType && (hasVolume || hasJadwal)) {
        const confirmed = confirm(
            "⚠️ PERHATIAN!\n\n" +
            "Mengubah tipe sumber akan menghapus data berikut:\n" +
            (hasVolume ? "• Volume Pekerjaan\n" : "") +
            (hasJadwal ? "• Jadwal (Tahapan)\n" : "") +
            "• Template AHSP\n" +
            "• Formula State\n\n" +
            "Data yang dihapus TIDAK DAPAT dikembalikan.\n\n" +
            "Apakah Anda yakin ingin melanjutkan?"
        );

        if (!confirmed) {
            // Revert source type dropdown to original
            row.querySelector('[name*="source_type"]').value = oldSourceType;
            return false;
        }
    }

    return true;
}

// Hook into form submit
const form = document.getElementById('list-pekerjaan-form');
form.addEventListener('submit', function(e) {
    const rows = document.querySelectorAll('.pekerjaan-row');
    for (let row of rows) {
        if (!confirmSourceChange(row)) {
            e.preventDefault();
            return false;
        }
    }
});
```

**Testing:**
- [ ] Change source type with volume → shows warning
- [ ] Change source type without volume → no warning
- [ ] Click Cancel → reverts dropdown
- [ ] Click OK → proceeds with save

**Status:** ⏳ PENDING

---

## Task 4.2: Fix Bugs Found During Manual Testing

**Process:**
1. Review all bugs logged in Phases 2-3
2. Prioritize by severity
3. Fix critical bugs first
4. Test fixes
5. Document in git commits

**Status:** ⏳ PENDING

---

## Task 4.3: Implement Feature Requests (if time permits)

**Process:**
1. Review all FRs logged
2. Assess effort vs value
3. Implement quick wins
4. Defer complex ones to backlog

**Status:** ⏳ PENDING

---

# PHASE 5: DOCUMENTATION & REVIEW (Day 8)

## Task 5.1: Update Documentation

**Files to update:**
- [ ] `SOURCE_CHANGE_CASCADE_RESET.md`
  - [ ] Add user warning dialog section
  - [ ] Update frontend implementation details
  - [ ] Add screenshots (if applicable)

- [ ] `CASCADE_RESET_FIX.md`
  - [ ] Add UX improvements section
  - [ ] Document confirmation dialog

- [ ] Create `MANUAL_TEST_RESULTS.md`
  - [ ] Summary of all pages tested
  - [ ] Bugs found and fixed
  - [ ] Feature requests logged
  - [ ] Test coverage achieved

- [ ] Create `BUGS_BACKLOG.md`
  - [ ] List of non-critical bugs to fix later
  - [ ] Feature requests for future sprints

**Status:** ⏳ PENDING

---

## Task 5.2: Update Test Results

**Commands:**
```bash
# Run full test suite after all fixes
pytest detail_project/tests/ -v --tb=short --html=test_report.html --self-contained-html

# Count results
pytest detail_project/tests/ -v --tb=no | grep -E "(passed|failed|error)"
```

**Document:**
- [ ] Before: 259/308 passing (84.4%)
- [ ] After: ___ /308 passing (___%)
- [ ] Improvement: +___ tests

**Status:** ⏳ PENDING

---

## Task 5.3: Create Deployment Checklist

**File:** `DEPLOYMENT_CHECKLIST.md`

```markdown
# Pre-Production Deployment Checklist

## Code Quality
- [ ] All critical tests passing (>95%)
- [ ] No known critical bugs
- [ ] Code reviewed
- [ ] Documentation updated

## Security
- [ ] ALLOWED_HOSTS configured (not '*')
- [ ] SECRET_KEY different from dev
- [ ] DEBUG = False
- [ ] HTTPS enabled
- [ ] SESSION_COOKIE_SECURE = True
- [ ] CSRF_COOKIE_SECURE = True
- [ ] Session timeout configured (7 days)

## Database
- [ ] Migrations applied
- [ ] Indexes created
- [ ] Backup configured

## Features
- [ ] User warning dialog implemented
- [ ] Cascade reset working correctly
- [ ] All exports working
- [ ] All pages manually tested

## Performance
- [ ] Slow queries optimized
- [ ] Static files collected
- [ ] Cache configured

## Monitoring
- [ ] Error logging configured
- [ ] Performance monitoring setup
- [ ] Audit trail working
```

**Status:** ⏳ PENDING

---

# 📝 TRACKING TEMPLATES

## Bug Report Template

```markdown
### Bug ID: [PAGE-###]
**Reported by:** [Your Name]
**Date:** 2025-11-__
**Page:** [Page Name]
**Severity:** 🔴 Critical / 🟡 Major / 🟢 Minor

**Description:**
Clear description of the bug

**Steps to Reproduce:**
1. Step 1
2. Step 2
3. Step 3

**Expected Behavior:**
What should happen

**Actual Behavior:**
What actually happens

**Screenshots:**
[Attach if applicable]

**Environment:**
- Browser:
- OS:
- Django Version:

**Status:**
- [ ] Confirmed
- [ ] Fixed
- [ ] Tested
- [ ] Deployed

**Fix Details:**
- Commit:
- Files changed:
- Test added:
```

---

## Feature Request Template

```markdown
### FR ID: [PAGE-FR-###]
**Requested by:** [Your Name]
**Date:** 2025-11-__
**Page:** [Page Name]
**Priority:** 🔴 High / 🟡 Medium / 🟢 Low

**Description:**
Clear description of desired feature

**Justification:**
Why is this needed? What problem does it solve?

**User Story:**
As a [user type], I want [feature] so that [benefit]

**Acceptance Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2

**Effort Estimate:**
- [ ] Small (< 4 hours)
- [ ] Medium (4-16 hours)
- [ ] Large (> 16 hours)

**Status:**
- [ ] Backlog
- [ ] Approved
- [ ] In Progress
- [ ] Done
```

---

# 🎯 SUCCESS CRITERIA

## Automated Tests
- [x] Pass rate > 95% (293+ of 308 tests)
- [x] No critical test errors
- [x] All infrastructure tests passing

## Manual Tests
- [x] All 10 pages tested
- [x] Each page has detailed test report
- [x] Critical bugs identified and fixed
- [x] Feature requests documented

## Code Quality
- [x] User warning dialog implemented
- [x] Cascade reset verified working
- [x] No known data loss issues

## Documentation
- [x] All docs updated
- [x] Bug reports filed
- [x] Test results documented
- [x] Deployment checklist created

---

# 📊 PROGRESS TRACKER

| Task | Status | Assigned | Started | Completed |
|------|--------|----------|---------|-----------|
| Fix Klasifikasi tests | ⏳ PENDING | - | - | - |
| Fix tanggal_mulai tests | ⏳ PENDING | - | - | - |
| Run test suite | ⏳ PENDING | - | - | - |
| Manual test: List Pekerjaan | ⏳ PENDING | - | - | - |
| Manual test: Volume Pekerjaan | ⏳ PENDING | - | - | - |
| Manual test: Template AHSP | ⏳ PENDING | - | - | - |
| Manual test: Harga Items | ⏳ PENDING | - | - | - |
| Manual test: Rincian AHSP | ⏳ PENDING | - | - | - |
| Manual test: Rekap RAB | ⏳ PENDING | - | - | - |
| Manual test: Rekap Kebutuhan | ⏳ PENDING | - | - | - |
| Manual test: Jadwal Pekerjaan | ⏳ PENDING | - | - | - |
| Manual test: Rincian RAB | ⏳ PENDING | - | - | - |
| Manual test: Kelola Tahapan | ⏳ PENDING | - | - | - |
| Implement warning dialog | ⏳ PENDING | - | - | - |
| Fix bugs found | ⏳ PENDING | - | - | - |
| Update documentation | ⏳ PENDING | - | - | - |
| Create deployment checklist | ⏳ PENDING | - | - | - |

---

# 📞 SUPPORT & RESOURCES

## Useful Commands

```bash
# Run specific test file
pytest detail_project/tests/test_file.py -v

# Run tests with coverage
pytest detail_project/tests/ --cov=detail_project --cov-report=html

# Find TODOs in code
grep -r "TODO" detail_project/ --exclude-dir=__pycache__

# Check for hardcoded URLs
grep -r "http://" detail_project/ --exclude-dir=node_modules

# Find large files
find detail_project/ -type f -size +1M

# Database query logging
python manage.py shell
>>> from django.db import connection
>>> connection.queries
```

## Reference Documentation
- SOURCE_CHANGE_CASCADE_RESET.md - Complete cascade reset documentation
- CASCADE_RESET_FIX.md - Overview and fix summary
- Django testing docs: https://docs.djangoproject.com/en/4.2/topics/testing/

---

**Last Updated:** 2025-11-09
**Next Review:** After Phase 1 completion
**Owner:** [Your Name]
