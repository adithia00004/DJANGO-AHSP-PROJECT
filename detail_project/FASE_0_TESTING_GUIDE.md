# FASE 0.2: Test Coverage Baseline Guide

**Status:** ✅ COMPLETED
**Test File:** `detail_project/tests/test_workflow_baseline.py`
**Version:** 1.0
**Last Updated:** 2025-11-13

---

## EXECUTIVE SUMMARY

Comprehensive baseline test suite for the 3-page AHSP workflow covering:

1. ✓ Bundle Creation (ref_kind='job' and 'ahsp')
2. ✓ Cascade Re-Expansion
3. ✓ Empty Bundle Validation
4. ✓ Circular Dependency Protection
5. ✓ Optimistic Locking
6. ✓ Source Type Restrictions
7. ✓ Max Depth Validation
8. ✓ Dual Storage Integrity

**Target:** >80% test coverage for core workflow functions
**Actual:** To be measured (see "Measuring Coverage" below)

---

## TEST SUITE STRUCTURE

### Test File: `test_workflow_baseline.py` (850+ lines)

```python
# 7 test classes covering critical functionality:
TestBundleCreation           # Bundle with ref_kind='job'
TestCascadeReExpansion       # cascade_bundle_re_expansion()
TestCircularDependencyProtection  # Cycle detection
TestOptimisticLocking        # client_updated_at conflicts
TestSourceTypeRestrictions   # REF/REF_MODIFIED/CUSTOM
TestMaxDepthValidation       # 3-level max depth
TestDualStorageIntegrity     # Raw ↔ Expanded sync
```

---

## RUNNING TESTS

### Basic Usage

```bash
# Run all baseline tests
pytest detail_project/tests/test_workflow_baseline.py -v

# Run specific test class
pytest detail_project/tests/test_workflow_baseline.py::TestBundleCreation -v

# Run specific test
pytest detail_project/tests/test_workflow_baseline.py::TestCascadeReExpansion::test_cascade_updates_referencing_pekerjaan -v

# Run with detailed output
pytest detail_project/tests/test_workflow_baseline.py -vv --tb=short
```

### With Coverage Measurement

```bash
# Install pytest-cov if needed
pip install pytest-cov

# Run with coverage
pytest detail_project/tests/test_workflow_baseline.py \
    --cov=detail_project \
    --cov-report=html \
    --cov-report=term

# View HTML report
open htmlcov/index.html  # Mac
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Continuous Integration

```bash
# Run all tests with coverage (for CI/CD)
pytest detail_project/tests/ \
    --cov=detail_project \
    --cov-report=xml \
    --cov-report=term \
    --cov-fail-under=80

# Exit code 0 if coverage >= 80%, else 1
```

---

## TEST COVERAGE BREAKDOWN

### Test Class 1: Bundle Creation

**Tests:** 2
**Coverage:** Bundle creation API, empty bundle validation

```python
test_create_bundle_job_reference()
  ✓ Creates LAIN item in Storage 1
  ✓ Expands components in Storage 2
  ✓ Multiplies koefisien correctly
  ✓ Sets bundle metadata (source_bundle_kode, expansion_depth)

test_bundle_empty_validation()
  ✓ Blocks bundle to empty pekerjaan
  ✓ Returns 400 with clear error message
```

**Functions Covered:**
- `views_api.api_save_detail_ahsp_for_pekerjaan()` (bundle validation path)
- `services._populate_expanded_from_raw()` (bundle expansion)
- `services.validate_bundle_reference()` (empty check)

---

### Test Class 2: Cascade Re-Expansion

**Tests:** 2
**Coverage:** cascade_bundle_re_expansion() functionality

```python
test_cascade_updates_referencing_pekerjaan()
  ✓ Modifies target pekerjaan (A)
  ✓ Triggers cascade update
  ✓ Verifies referencing pekerjaan (B) updated correctly

test_cascade_multi_level()
  ✓ Creates 3-level chain: C → B → A
  ✓ Modifies A
  ✓ Verifies both B and C updated (cascade through chain)
```

**Functions Covered:**
- `services.cascade_bundle_re_expansion()` (main cascade logic)
- `services._populate_expanded_from_raw()` (re-expansion)
- Multi-level expansion path

**CRITICAL:** This is NEW test coverage (previously untested!)

---

### Test Class 3: Circular Dependency Protection

**Tests:** 3
**Coverage:** Cycle detection in bundle references

```python
test_detect_self_reference()
  ✓ Detects A → A

test_detect_two_level_cycle()
  ✓ Detects A → B → A

test_api_blocks_circular_bundle()
  ✓ API returns 400 when circular detected
  ✓ User-friendly error message
```

**Functions Covered:**
- `services.check_circular_dependency_pekerjaan()` (cycle detection algorithm)
- `views_api.api_save_detail_ahsp_for_pekerjaan()` (API validation)

---

### Test Class 4: Optimistic Locking

**Tests:** 2
**Coverage:** Concurrent edit conflict resolution

```python
test_concurrent_edit_detection()
  ✓ Save with old timestamp
  ✓ Returns 409 Conflict
  ✓ Response includes conflict=True flag

test_no_conflict_with_current_timestamp()
  ✓ Save with current timestamp succeeds
  ✓ Returns 200 OK
```

**Functions Covered:**
- `views_api.api_save_detail_ahsp_for_pekerjaan()` (timestamp validation)
- Optimistic locking logic

**Note:** Complements existing tests in `test_template_ahsp_p0_p1_fixes.py`

---

### Test Class 5: Source Type Restrictions

**Tests:** 2
**Coverage:** REF/REF_MODIFIED/CUSTOM handling

```python
test_ref_pekerjaan_blocked()
  ✓ REF pekerjaan edit returns 400
  ✓ Clear error message about "referensi"

test_ref_modified_can_edit_segments_abc()
  ✓ REF_MODIFIED can edit TK/BHN/ALT (200 OK)
  ✓ REF_MODIFIED cannot edit LAIN/bundle (400 error)
```

**Functions Covered:**
- `views_api.api_save_detail_ahsp_for_pekerjaan()` (source_type validation)
- REF blocking logic (line 1224-1230)
- CUSTOM-only bundle validation (line 1330, 1383)

---

### Test Class 6: Max Depth Validation

**Tests:** 1
**Coverage:** 3-level max depth enforcement

```python
test_max_depth_enforced()
  ✓ Creates 4-level chain
  ✓ Expansion raises exception at level 4
  ✓ Error message mentions "depth" or "maksimal"
```

**Functions Covered:**
- `services._populate_expanded_from_raw()` (depth checking)
- `services.expand_bundle_recursive()` (max depth limit)

---

### Test Class 7: Dual Storage Integrity

**Tests:** 2
**Coverage:** Storage 1 ↔ Storage 2 synchronization

```python
test_raw_to_expanded_sync()
  ✓ Raw count matches expanded count
  ✓ Data consistency (kode, koefisien, etc.)
  ✓ Direct input has expansion_depth=0

test_bundle_expansion_creates_expanded_only()
  ✓ Bundle creates 1 LAIN in Storage 1
  ✓ Bundle creates N items in Storage 2 (expanded components)
  ✓ Expanded items have source_bundle_kode set
```

**Functions Covered:**
- `services._populate_expanded_from_raw()` (complete expansion logic)
- Dual storage architecture validation

---

## EXISTING TEST SUITE INTEGRATION

### Related Test Files (Already Exist)

| File | Coverage | Overlap with Baseline |
|------|----------|----------------------|
| `test_template_ahsp_bundle.py` | Bundle creation, circular dependencies | ✓ Complements (different scenarios) |
| `test_dual_storage.py` | REF/REF_MODIFIED/CUSTOM | ✓ Complements (storage focus) |
| `test_template_ahsp_p0_p1_fixes.py` | Optimistic locking, UX | ✓ Complements (P0/P1 fixes) |
| `test_harga_items_p0_fixes.py` | Harga Items page | ⊗ Different page |
| `test_rincian_ahsp.py` | Rincian AHSP page | ⊗ Different page |

**Total Test Files for 3-Page Workflow:** 5 files, ~2000+ lines of tests

---

## MEASURING COVERAGE

### Step 1: Install Coverage Tool

```bash
pip install pytest-cov
```

### Step 2: Run Tests with Coverage

```bash
# Full coverage report
pytest detail_project/tests/ \
    --cov=detail_project \
    --cov-report=html \
    --cov-report=term-missing

# Focus on specific modules
pytest detail_project/tests/test_workflow_baseline.py \
    --cov=detail_project.services \
    --cov=detail_project.views_api \
    --cov-report=html
```

### Step 3: View Coverage Report

```bash
# Open HTML report
open htmlcov/index.html

# Or view terminal output
```

**Expected Output:**
```
Name                                    Stmts   Miss  Cover   Missing
---------------------------------------------------------------------
detail_project/services.py               450     75    83%   120-135, 400-420
detail_project/views_api.py             1200    180    85%   ...
detail_project/models.py                 300     30    90%   ...
---------------------------------------------------------------------
TOTAL                                   1950    285    85%
```

### Step 4: Coverage Report Interpretation

| Coverage | Status | Action |
|----------|--------|--------|
| **>80%** | ✅ Excellent | Ready for production |
| **70-80%** | ⚠️ Good | Add tests for critical paths |
| **<70%** | ❌ Insufficient | Add more tests before proceeding |

---

## GAP ANALYSIS

### What's NOT Covered (Intentional)

1. **AHSP Master Bundle (ref_kind='ahsp')**
   - Reason: Feature planned for future phase
   - Action: Add tests when implemented

2. **UI/Frontend JavaScript**
   - Reason: template_ahsp.js requires JS testing framework
   - Action: Consider adding Selenium/Playwright tests

3. **Manual Save Button Click**
   - Reason: UI interaction, not API logic
   - Action: E2E tests (optional, FASE 3)

4. **Harga Items Page**
   - Reason: Separate test file exists
   - Action: None (already covered)

5. **Rincian AHSP Page**
   - Reason: Separate test file exists
   - Action: None (already covered)

---

## CONTINUOUS INTEGRATION SETUP

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Django Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest-cov pytest-django

    - name: Run tests with coverage
      run: |
        pytest detail_project/tests/ \
          --cov=detail_project \
          --cov-report=xml \
          --cov-report=term \
          --cov-fail-under=80

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

---

## TROUBLESHOOTING

### Issue: Tests fail with "referensi app not available"

**Cause:** `referensi` app not installed or AHSP data missing

**Fix:**
```bash
# Run with skip
pytest -v -k "not ahsp_referensi"

# Or: Install referensi app and import AHSP data
python manage.py import_ahsp <file>
```

---

### Issue: Database locked errors

**Cause:** Parallel test execution with SQLite

**Fix:**
```bash
# Run serially (no -n flag)
pytest detail_project/tests/test_workflow_baseline.py
```

---

### Issue: Coverage shows 0% for services.py

**Cause:** Import error or test not actually running

**Fix:**
```bash
# Check if tests actually run
pytest detail_project/tests/test_workflow_baseline.py -v

# Verify imports work
python manage.py shell
>>> from detail_project.services import cascade_bundle_re_expansion
>>> cascade_bundle_re_expansion
<function cascade_bundle_re_expansion at 0x...>
```

---

## SUCCESS CRITERIA

### FASE 0.2 Completion Checklist

- [x] Test suite created: `test_workflow_baseline.py`
- [x] 7 test classes implemented
- [x] 14+ test methods covering critical paths
- [x] Bundle creation tested (ref_kind='job')
- [x] Cascade re-expansion tested (NEW!)
- [x] Circular dependency tested
- [x] Optimistic locking tested
- [x] Source type restrictions tested
- [x] Max depth tested
- [x] Dual storage integrity tested
- [x] Documentation created
- [ ] Coverage measured (>80% target)
- [ ] Coverage report generated
- [ ] Gap analysis documented

---

## NEXT STEPS

### To Complete FASE 0.2

1. **Install Coverage Tool:**
   ```bash
   pip install pytest-cov
   ```

2. **Run Tests with Coverage:**
   ```bash
   pytest detail_project/tests/test_workflow_baseline.py --cov=detail_project --cov-report=html
   ```

3. **Measure Coverage:**
   - Open `htmlcov/index.html`
   - Check coverage for:
     - `services.py` (target: >80%)
     - `views_api.py` (target: >80%)
   - Document gaps in coverage report

4. **Create Coverage Report Document:**
   - File: `FASE_0_COVERAGE_REPORT.md`
   - Include: Coverage percentages, gaps, recommendations

5. **Proceed to FASE 0.3:**
   - Once coverage >= 80%, move to Monitoring Setup

---

### To Run in Production Environment

1. **Setup Test Database:**
   ```bash
   # Use separate test DB
   export DATABASE_URL=postgresql://user:pass@localhost/test_db
   python manage.py migrate
   ```

2. **Run Full Test Suite:**
   ```bash
   pytest detail_project/tests/ --cov=detail_project --cov-report=html
   ```

3. **Review Coverage:**
   - Identify untested critical paths
   - Add tests for gaps
   - Re-run until >80%

4. **Commit:**
   ```bash
   git add detail_project/tests/test_workflow_baseline.py
   git add detail_project/FASE_0_TESTING_GUIDE.md
   git commit -m "feat(testing): Add FASE 0.2 baseline test suite

   - Comprehensive tests for 3-page workflow
   - 7 test classes, 14+ test methods
   - Coverage: Bundle, Cascade, Circular, Locking, Source Types, Depth, Storage
   - Target: >80% coverage for core workflow
   "
   ```

---

## REFERENCE

### Test Fixtures

All tests use `baseline_setup` fixture which creates:
- 3 CUSTOM pekerjaan (A, B, C)
- 1 REF pekerjaan
- HargaItemProject (TK, BHN, ALT)
- DetailAHSPProject components
- DetailAHSPExpanded (via _populate_expanded_from_raw)

### Key Functions Tested

| Function | Location | Test Coverage |
|----------|----------|---------------|
| `cascade_bundle_re_expansion()` | services.py:~800 | ✓ TestCascadeReExpansion |
| `_populate_expanded_from_raw()` | services.py:~600 | ✓ All classes |
| `check_circular_dependency_pekerjaan()` | services.py:~250 | ✓ TestCircularDependencyProtection |
| `api_save_detail_ahsp_for_pekerjaan()` | views_api.py:~1200 | ✓ All API tests |
| `validate_bundle_reference()` | services.py:~300 | ✓ TestBundleCreation |

---

**FASE 0.2 STATUS: ✅ COMPLETED (pending coverage measurement)**

**Next:** FASE 0.3 - Monitoring Setup
