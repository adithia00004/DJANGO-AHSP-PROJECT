# 🧪 Pytest Testing Recommendations - List Pekerjaan

**Date:** 2025-11-09
**Page:** List Pekerjaan
**Context:** Post Bug Fix #2 (Source Type Change Persistence)

---

## 📊 Executive Summary

After fixing the source type change persistence bug, run the following pytest tests to ensure:
1. ✅ Bug is actually fixed (regression prevention)
2. ✅ No new bugs introduced
3. ✅ All existing functionality still works

**Recommended Test Order:**
1. Source change tests (most relevant)
2. API tests (comprehensive coverage)
3. UI/Integration tests (end-to-end validation)

**Estimated Total Time:** 5-10 minutes

---

## 🎯 Priority Tests (Run These First)

### 1. Source Change Tests - HIGHEST PRIORITY ⭐⭐⭐

**Why:** These tests directly validate the bug fix we just implemented.

**File:** `detail_project/tests/test_list_pekerjaan_source_change.py` (723 lines)

**What it tests:**
- ✅ CUSTOM → REF transition with cascade reset
- ✅ CUSTOM → REF_MODIFIED transition
- ✅ REF → CUSTOM transition
- ✅ REF_MODIFIED → REF transition
- ✅ ref_id changes trigger cascade reset
- ✅ Cascade reset deletes volume, jadwal, detail AHSP
- ✅ Multiple pekerjaan isolation (one change doesn't affect others)

**Run command:**
```bash
# Run all source change tests
pytest detail_project/tests/test_list_pekerjaan_source_change.py -v

# Expected: ALL TESTS SHOULD PASS
# Total tests: ~15 tests
# Expected time: 30-60 seconds
```

**Individual test classes:**
```bash
# Test CUSTOM → REF specifically
pytest detail_project/tests/test_list_pekerjaan_source_change.py::TestSourceChangeCUSTOMtoREF -v

# Test REF → CUSTOM specifically
pytest detail_project/tests/test_list_pekerjaan_source_change.py::TestSourceChangeREFtoCUSTOM -v

# Test ref_id changes
pytest detail_project/tests/test_list_pekerjaan_source_change.py::TestSourceChangeRefIDChange -v

# Test integration workflows
pytest detail_project/tests/test_list_pekerjaan_source_change.py::TestSourceChangeIntegration -v
```

**Key tests to watch:**

| Test Name | What it validates | Expected Result |
|-----------|-------------------|-----------------|
| `test_change_custom_to_ref_resets_fields` | CUSTOM→REF persists | ✅ PASS |
| `test_change_custom_to_ref_triggers_cascade_reset` | CASCADE RESET works | ✅ PASS |
| `test_change_custom_to_ref_modified` | CUSTOM→REF_MODIFIED works | ✅ PASS |
| `test_change_ref_to_custom_resets_to_empty` | REF→CUSTOM works | ✅ PASS |
| `test_change_ref_id_resets_and_repopulates` | ref_id change works | ✅ PASS |
| `test_full_workflow_custom_to_ref_and_back` | Round-trip workflow | ✅ PASS |
| `test_multiple_pekerjaan_source_change_isolated` | Isolation verified | ✅ PASS |

---

### 2. Core API Tests - HIGH PRIORITY ⭐⭐

**Why:** Comprehensive API validation including edge cases.

**File:** `detail_project/tests/test_list_pekerjaan.py` (281 lines)

**What it tests:**
- Basic CRUD operations
- Validation logic
- Error handling
- Transaction atomicity

**Run command:**
```bash
pytest detail_project/tests/test_list_pekerjaan.py -v

# Expected: ALL TESTS SHOULD PASS
# Total tests: ~10-15 tests
# Expected time: 20-30 seconds
```

---

### 3. API Full Coverage Tests - HIGH PRIORITY ⭐⭐

**Files:**
- `test_list_pekerjaan_api_full.py` (90 lines)
- `test_list_pekerjaan_api_advanced.py` (226 lines)
- `test_list_pekerjaan_api_extra.py` (126 lines)
- `test_list_pekerjaan_api_gaps.py` (249 lines)

**What they test:**
- Full API endpoint coverage
- Advanced scenarios (nested structures, complex payloads)
- Edge cases and boundary conditions
- API gaps and missing functionality

**Run command:**
```bash
# Run all API tests together
pytest detail_project/tests/test_list_pekerjaan_api*.py -v

# Expected: Most tests should pass
# Total tests: ~30-40 tests
# Expected time: 60-90 seconds
```

**Or run individually:**
```bash
pytest detail_project/tests/test_list_pekerjaan_api_full.py -v
pytest detail_project/tests/test_list_pekerjaan_api_advanced.py -v
pytest detail_project/tests/test_list_pekerjaan_api_extra.py -v
pytest detail_project/tests/test_list_pekerjaan_api_gaps.py -v
```

---

### 4. UI/Page Tests - MEDIUM PRIORITY ⭐

**Why:** Validates page rendering and frontend integration.

**File:** `detail_project/tests/test_list_pekerjaan_page_ui.py` (19 lines)

**What it tests:**
- Page loads successfully
- Required elements present
- JavaScript loads correctly
- User interface components work

**Run command:**
```bash
pytest detail_project/tests/test_list_pekerjaan_page_ui.py -v

# Expected: ALL TESTS SHOULD PASS
# Total tests: ~2-5 tests
# Expected time: 10-15 seconds
```

---

## 📋 Complete Test Suite

### Run ALL List Pekerjaan Tests

**Command:**
```bash
# Run all tests with verbose output
pytest detail_project/tests/test_list_pekerjaan*.py -v

# Run with coverage report
pytest detail_project/tests/test_list_pekerjaan*.py -v --cov=detail_project --cov-report=term-missing

# Run with detailed output and stop on first failure
pytest detail_project/tests/test_list_pekerjaan*.py -v -x

# Run with parallel execution (faster)
pytest detail_project/tests/test_list_pekerjaan*.py -v -n auto
```

**Expected Results:**
- Total tests: ~60-80 tests
- Expected pass rate: 100% (all tests should pass after bug fix)
- Expected time: 2-5 minutes (depending on machine)

---

## 🎯 Specific Test Recommendations by Bug

### For Bug #1 (Pekerjaan Deletion) - Already Fixed

**Relevant tests:**
```bash
# Tests that validate keep_all_p logic
pytest detail_project/tests/test_list_pekerjaan.py -v -k "delete"
pytest detail_project/tests/test_list_pekerjaan_api_full.py -v -k "validation"
```

These tests verify that pekerjaan is NOT deleted when validation fails.

---

### For Bug #2 (Source Type Change) - Just Fixed

**Relevant tests:**
```bash
# PRIMARY: Source change specific tests
pytest detail_project/tests/test_list_pekerjaan_source_change.py -v

# SECONDARY: API tests that include source changes
pytest detail_project/tests/test_list_pekerjaan_api_advanced.py -v -k "source"
pytest detail_project/tests/test_list_pekerjaan_api_gaps.py -v -k "ref"
```

**Expected behavior after fix:**
- All CUSTOM→REF tests should PASS
- All CUSTOM→REF_MODIFIED tests should PASS
- All REF_MODIFIED→REF tests should PASS
- Cascade reset should trigger correctly
- Error messages should be clear

---

## 🔍 Interpreting Test Results

### ✅ Success Indicators

```
PASSED detail_project/tests/test_list_pekerjaan_source_change.py::TestSourceChangeCUSTOMtoREF::test_change_custom_to_ref_resets_fields
PASSED detail_project/tests/test_list_pekerjaan_source_change.py::TestSourceChangeCUSTOMtoREF::test_change_custom_to_ref_triggers_cascade_reset
PASSED detail_project/tests/test_list_pekerjaan_source_change.py::TestSourceChangeCUSTOMtoREF::test_change_custom_to_ref_modified
...
```

**What this means:**
- ✅ Bug fix is working
- ✅ Source type changes persist correctly
- ✅ Cascade reset triggers as expected
- ✅ No regressions introduced

---

### ❌ Failure Scenarios

If you see failures, categorize them:

#### **Failure Type 1: Test Setup Issues**
```
FAILED ... - fixture 'setup_source_change_test' not found
ERROR ... - django.db.utils.OperationalError
```

**Solution:** Database migration or fixture issue, not related to bug fix
```bash
python manage.py migrate
pytest --create-db
```

---

#### **Failure Type 2: Actual Bug Still Present**
```
FAILED test_change_custom_to_ref_resets_fields - AssertionError: assert 'custom' == 'ref'
```

**This means:** Bug fix didn't work correctly

**Debug steps:**
1. Check browser console for JavaScript errors
2. Verify list_pekerjaan.js changes were applied
3. Clear browser cache
4. Check if file was saved correctly

---

#### **Failure Type 3: New Regression Introduced**
```
FAILED test_change_ref_to_custom - AssertionError: ref_id should be None
```

**This means:** Fix introduced new bug

**Debug steps:**
1. Review the exact changes made
2. Check if logic handles all source type combinations
3. Review `list_pekerjaan.js` lines 1335-1353

---

#### **Failure Type 4: Environment/Dependency Issue**
```
ERROR test_list_pekerjaan.py - ModuleNotFoundError: No module named 'referensi'
```

**Solution:** Environment setup issue
```bash
pip install -r requirements.txt
```

---

## 📊 Test Coverage Analysis

### Current Coverage (Expected)

After running tests with coverage:
```bash
pytest detail_project/tests/test_list_pekerjaan*.py --cov=detail_project.views_api --cov-report=html
```

**Expected coverage:**

| File | Coverage | Notes |
|------|----------|-------|
| `views_api.py` | ~95% | High coverage, most paths tested |
| `list_pekerjaan.js` | N/A | JavaScript not covered by pytest |
| `models.py` | ~100% | Models well tested |
| `services.py` | ~90% | clone_ref_pekerjaan covered |

**View HTML report:**
```bash
# After running with --cov-report=html
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

---

## 🛠️ Troubleshooting Test Failures

### Common Issues & Solutions

#### Issue 1: Tests fail with "URL not found"
**Symptom:**
```
django.urls.exceptions.NoReverseMatch: Reverse for 'api_upsert_list_pekerjaan' not found
```

**Solution:**
```bash
# Check URL configuration
python manage.py show_urls | grep list_pekerjaan

# Ensure app is in INSTALLED_APPS
python manage.py check
```

---

#### Issue 2: Tests fail with "Permission denied"
**Symptom:**
```
AssertionError: 403 != 200
```

**Solution:**
```bash
# Check if client_logged fixture is working
# Check user permissions in test setup
```

---

#### Issue 3: Tests pass locally but fail in CI
**Common causes:**
- Database differences (SQLite vs PostgreSQL)
- Timezone issues
- Missing environment variables
- Different Python/Django versions

**Solution:**
```bash
# Run with same settings as CI
pytest --ds=config.settings.test
```

---

## 🎯 Recommended Test Workflow

### Quick Test (After Bug Fix) - 2 minutes
```bash
# 1. Run source change tests only
pytest detail_project/tests/test_list_pekerjaan_source_change.py -v

# 2. If all pass, done! ✅
```

---

### Standard Test (Before Deploy) - 5 minutes
```bash
# 1. Run all list_pekerjaan tests
pytest detail_project/tests/test_list_pekerjaan*.py -v

# 2. Check results, fix any failures
# 3. If all pass, safe to deploy ✅
```

---

### Comprehensive Test (Weekly/Monthly) - 10 minutes
```bash
# 1. Run with coverage
pytest detail_project/tests/test_list_pekerjaan*.py -v --cov=detail_project --cov-report=html

# 2. Review coverage report
open htmlcov/index.html

# 3. Run full detail_project test suite
pytest detail_project/tests/ -v

# 4. Document any new gaps or issues
```

---

## 📝 Test Result Documentation Template

After running tests, document results in `MANUAL_TEST_RESULTS.md`:

```markdown
## Automated Test Results - List Pekerjaan

**Date:** 2025-11-09
**Branch:** claude/check-main-branch-011CUwNSyACLmgQPQdM9HjzQ
**Commit:** 7592fac

### Source Change Tests
- **File:** test_list_pekerjaan_source_change.py
- **Tests Run:** 15
- **Passed:** 15 ✅
- **Failed:** 0
- **Skipped:** 0
- **Time:** 45 seconds

### API Tests
- **Files:** test_list_pekerjaan*.py (all)
- **Tests Run:** 65
- **Passed:** 65 ✅
- **Failed:** 0
- **Skipped:** 0
- **Time:** 3 minutes

### Coverage
- **views_api.py:** 95.2%
- **models.py:** 100%
- **services.py:** 91.5%

### Conclusion
✅ All tests passing. Bug fix validated. Safe to deploy.
```

---

## 🚀 CI/CD Integration

### GitHub Actions / GitLab CI

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml
- name: Run List Pekerjaan Tests
  run: |
    pytest detail_project/tests/test_list_pekerjaan*.py -v --cov=detail_project --cov-report=xml

- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

---

## 📚 Additional Test Files (Optional)

### Related Tests Worth Running

```bash
# Volume tests (List Pekerjaan creates volume data)
pytest detail_project/tests/test_volume*.py -v

# Rekap tests (depends on List Pekerjaan data)
pytest detail_project/tests/test_rekap*.py -v

# Integration tests (end-to-end workflows)
pytest detail_project/tests/test_phase5_integration.py -v
```

---

## ✅ Final Checklist

Before marking testing as complete:

- [ ] ✅ Ran `test_list_pekerjaan_source_change.py` - ALL PASSED
- [ ] ✅ Ran all `test_list_pekerjaan*.py` tests - ALL PASSED
- [ ] ✅ Reviewed any failures and documented solutions
- [ ] ✅ Coverage above 90% for modified files
- [ ] ✅ Manual testing completed (see `LIST_PEKERJAAN_CHANGELOG.md`)
- [ ] ✅ No console errors in browser during manual testing
- [ ] ✅ Documented results in `MANUAL_TEST_RESULTS.md`
- [ ] ✅ Code committed and pushed
- [ ] ✅ Ready for production deployment

---

## 🎯 Quick Commands Summary

```bash
# QUICKEST: Just source change tests (30s)
pytest detail_project/tests/test_list_pekerjaan_source_change.py -v

# RECOMMENDED: All List Pekerjaan tests (3-5 min)
pytest detail_project/tests/test_list_pekerjaan*.py -v

# COMPREHENSIVE: With coverage (5 min)
pytest detail_project/tests/test_list_pekerjaan*.py -v --cov=detail_project --cov-report=term-missing

# FULL SUITE: All detail_project tests (10 min)
pytest detail_project/tests/ -v
```

---

**Document Version:** 1.0
**Last Updated:** 2025-11-09
**Status:** Ready for execution
