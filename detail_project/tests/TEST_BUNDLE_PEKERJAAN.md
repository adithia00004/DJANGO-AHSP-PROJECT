# Test Documentation: Pekerjaan Gabungan (Bundle) Feature

## Overview

File `test_template_ahsp_bundle.py` berisi comprehensive test suite untuk fitur "Pekerjaan Gabungan" (bundle pekerjaan) yang baru ditambahkan ke Template AHSP.

## Test Coverage

### 1. Circular Dependency Detection (`TestCircularDependencyDetection`)

**Purpose:** Memastikan sistem mendeteksi dan menolak circular reference dalam bundle pekerjaan.

**Test Cases:**
- `test_self_reference_detected`: Deteksi self-reference (A → A)
- `test_two_level_circular_detected`: Deteksi 2-level circular (A → B → A)
- `test_three_level_circular_detected`: Deteksi 3-level circular (A → B → C → A)
- `test_no_circular_in_valid_chain`: Valid chain (A → B → C) tidak di-flag sebagai circular

**What's Tested:**
- Function `check_circular_dependency_pekerjaan()` di services.py
- BFS algorithm untuk cycle detection
- Path tracking untuk error messages

---

### 2. Bundle Validation (`TestBundleValidation`)

**Purpose:** Test function `validate_bundle_reference()` yang validate sebelum save.

**Test Cases:**
- `test_validate_self_reference_error`: Reject self-reference
- `test_validate_circular_dependency_error`: Reject circular dependency
- `test_validate_nonexistent_pekerjaan_error`: Reject reference ke pekerjaan tidak ada
- `test_validate_valid_reference`: Accept valid reference

**What's Tested:**
- 4 validation checks: self-ref, circular, existence, same project
- Error message generation dengan pekerjaan codes

---

### 3. Recursive Bundle Expansion (`TestRecursiveBundleExpansion`)

**Purpose:** Test function `expand_bundle_recursive()` yang expand bundle ke unit terkecil.

**Test Cases:**
- `test_expand_single_level_bundle`: Expand bundle 1 level (A → TK/BHN)
- `test_expand_multi_level_bundle`: Expand nested bundle (A → B → TK/BHN/ALT)
- `test_expand_detects_circular_reference`: Raise error jika circular terdeteksi
- `test_expand_max_depth_limit`: Raise error jika max depth (10) terlampaui

**What's Tested:**
- Koefisien multiplication cascading
- Visited set tracking dengan try/finally cleanup
- Error handling untuk circular dan max depth
- Decimal precision

**Example Calculation:**
```python
# Job B punya: TK koef=2.5, BHN koef=10.0
# Bundle A → B dengan koef=2.0
# Volume A = 5.0
# Result:
#   TK: 2.5 * 2.0 * 5.0 = 25.0 OH
#   BHN: 10.0 * 2.0 * 5.0 = 100.0 Zak
```

---

### 4. API Endpoints (`TestBundleAPIEndpoints`)

**Purpose:** Test GET/SAVE API dengan ref_kind='job' support.

**Test Cases:**
- `test_get_detail_includes_ref_pekerjaan_id`: GET endpoint return ref_pekerjaan_id
- `test_save_detail_with_ref_kind_job`: SAVE dengan ref_kind='job' berhasil
- `test_save_detail_rejects_self_reference`: SAVE reject self-reference dengan 400
- `test_save_detail_rejects_circular_reference`: SAVE reject circular dengan 400

**API Endpoints Tested:**
- GET `/api/detail-project/<project_id>/pekerjaan/<pekerjaan_id>/detail-ahsp/`
- POST `/api/detail-project/<project_id>/pekerjaan/<pekerjaan_id>/detail-ahsp/save/`

**Payload Format:**
```json
{
  "rows": [
    {
      "kategori": "LAIN",
      "kode": "LAIN.001",
      "uraian": "Bundle Job B",
      "satuan": "LS",
      "koefisien": "1.500000",
      "ref_kind": "job",
      "ref_id": 123
    }
  ]
}
```

**Error Response Format:**
```json
{
  "ok": false,
  "errors": [
    {
      "field": "rows[0].ref_job",
      "message": "Circular dependency detected: A001 → B002 → A001"
    }
  ]
}
```

---

### 5. Rekap Computation (`TestRekapWithBundles`)

**Purpose:** Test function `compute_kebutuhan_items()` dengan bundle pekerjaan.

**Test Cases:**
- `test_rekap_expands_single_bundle`: Rekap expand single-level bundle
- `test_rekap_expands_nested_bundle`: Rekap expand multi-level nested bundle
- `test_rekap_skips_circular_bundle`: Rekap skip (log error) untuk circular bundle

**What's Tested:**
- Integration dengan compute_kebutuhan_items()
- Aggregasi items dari expanded bundles
- Volume multiplication
- Error handling (skip corrupted data)

**Example Multi-level Calculation:**
```
Setup:
  Job A -> Job B (koef 2.0) -> Job C (koef 3.0)
  Job B punya: TK koef=2.5, BHN koef=10.0
  Job C punya: ALT koef=1.5
  Volume A = 1.0

Expected Result:
  TK:  2.5 * 2.0 * 1.0 = 5.0 OH
  BHN: 10.0 * 2.0 * 1.0 = 20.0 Zak
  ALT: 1.5 * 3.0 * 2.0 * 1.0 = 9.0 Jam
```

---

### 6. Database Constraints (`TestDatabaseConstraints`)

**Purpose:** Test database-level constraints di migration 0017.

**Test Cases:**
- `test_cannot_set_both_ref_ahsp_and_ref_pekerjaan`: IntegrityError jika kedua ref di-set
- `test_non_lain_cannot_have_bundle_ref`: IntegrityError jika non-LAIN punya bundle ref

**Constraints Tested:**
- `bundle_ref_exclusive`: Hanya satu jenis ref (ahsp OR pekerjaan)
- `bundle_ref_only_for_lain`: Bundle ref hanya untuk kategori LAIN

---

## Running Tests

### Prerequisites

1. **Migration harus sudah dijalankan:**
   ```bash
   python manage.py migrate detail_project
   ```

2. **Pytest harus terinstall:**
   ```bash
   pip install pytest pytest-django
   ```

### Run Commands

**Run semua test bundle:**
```bash
pytest detail_project/tests/test_template_ahsp_bundle.py -v
```

**Run specific test class:**
```bash
pytest detail_project/tests/test_template_ahsp_bundle.py::TestCircularDependencyDetection -v
```

**Run specific test:**
```bash
pytest detail_project/tests/test_template_ahsp_bundle.py::TestCircularDependencyDetection::test_self_reference_detected -v
```

**Run dengan coverage:**
```bash
pytest detail_project/tests/test_template_ahsp_bundle.py --cov=detail_project.services --cov=detail_project.views_api --cov-report=term-missing
```

**Run dengan detailed output:**
```bash
pytest detail_project/tests/test_template_ahsp_bundle.py -vv --tb=long
```

---

## Test Data Setup

Setiap test menggunakan fixture `setup_bundle_test` yang create:

- **3 Pekerjaan (CUSTOM):**
  - Job A (kode: A001) - untuk parent bundle
  - Job B (kode: B002) - punya TK + BHN details
  - Job C (kode: C003) - punya ALT detail

- **3 HargaItemProject:**
  - TK.001: Pekerja (150,000/OH)
  - BHN.001: Semen (85,000/Zak)
  - ALT.001: Excavator (500,000/Jam)

- **DetailAHSPProject untuk Job B:**
  - TK.001 koef = 2.5
  - BHN.001 koef = 10.0

- **DetailAHSPProject untuk Job C:**
  - ALT.001 koef = 1.5

---

## Expected Test Results

**All 23 tests should PASS:**

```
TestCircularDependencyDetection
  ✓ test_self_reference_detected
  ✓ test_two_level_circular_detected
  ✓ test_three_level_circular_detected
  ✓ test_no_circular_in_valid_chain

TestBundleValidation
  ✓ test_validate_self_reference_error
  ✓ test_validate_circular_dependency_error
  ✓ test_validate_nonexistent_pekerjaan_error
  ✓ test_validate_valid_reference

TestRecursiveBundleExpansion
  ✓ test_expand_single_level_bundle
  ✓ test_expand_multi_level_bundle
  ✓ test_expand_detects_circular_reference
  ✓ test_expand_max_depth_limit

TestBundleAPIEndpoints
  ✓ test_get_detail_includes_ref_pekerjaan_id
  ✓ test_save_detail_with_ref_kind_job
  ✓ test_save_detail_rejects_self_reference
  ✓ test_save_detail_rejects_circular_reference

TestRekapWithBundles
  ✓ test_rekap_expands_single_bundle
  ✓ test_rekap_expands_nested_bundle
  ✓ test_rekap_skips_circular_bundle

TestDatabaseConstraints
  ✓ test_cannot_set_both_ref_ahsp_and_ref_pekerjaan
  ✓ test_non_lain_cannot_have_bundle_ref

======================== 23 passed in X.XXs ========================
```

---

## Impact on Existing Tests

**Existing tests yang checked:**
- ✅ `test_rekap_rab_with_buk_and_lain.py` - TIDAK terpengaruh (LAIN tanpa ref tetap valid)
- ✅ `test_api_numeric_endpoints.py` - TIDAK terpengaruh (numeric parsing independent)
- ✅ `test_rekap_consistency.py` - TIDAK terpengaruh (backward compatible)
- ✅ `test_deepcopy_service.py` - TIDAK terpengaruh (deep copy logic unchanged)

**Why existing tests still work:**
1. Field `ref_pekerjaan` adalah nullable (NULL by default)
2. Constraint hanya apply untuk new data dengan ref_pekerjaan
3. Backward compatibility dengan old ref_ahsp format
4. LAIN items tanpa bundle reference tetap valid

---

## Troubleshooting

### Test fails with IntegrityError

**Cause:** Migration 0017 belum dijalankan.

**Fix:**
```bash
python manage.py migrate detail_project
```

### Test fails: "Module not found: referensi.models"

**Cause:** AHSP Referensi app tidak tersedia.

**Fix:** Install atau enable referensi app di settings.py

### Test fails: "Circular dependency not detected"

**Cause:** Test data mungkin tidak ter-setup dengan benar.

**Fix:** Check bahwa DetailAHSPProject records ter-create dengan ref_pekerjaan yang benar.

### Test fails: "Expansion returns wrong koefisien"

**Cause:** Decimal rounding issue.

**Fix:** Pastikan semua koefisien menggunakan Decimal dengan 6 decimal places:
```python
Decimal('2.500000')  # Correct
Decimal(2.5)         # Might cause rounding issue
```

---

## Maintenance Notes

**When modifying bundle logic:**

1. Update tests if you change:
   - MAX_DEPTH limit (currently 10)
   - Koefisien decimal places
   - Error message formats
   - BFS algorithm logic

2. Add new test if you add:
   - New validation rules
   - New error scenarios
   - New bundle reference types
   - Performance optimizations

3. Run full test suite:
   ```bash
   pytest detail_project/tests/ -v
   ```

---

## References

**Related Files:**
- Implementation: `detail_project/services.py` (lines 68-391, 646-682)
- API: `detail_project/views_api.py` (lines 956-1196)
- Models: `detail_project/models.py` (lines 280-317)
- Migration: `detail_project/migrations/0017_add_ref_pekerjaan_bundle_support.py`

**Related Documentation:**
- Template AHSP Documentation: `docs/TEMPLATE_AHSP.md`
- Circular Dependency Algorithm: BFS (Breadth-First Search)
- Decimal Precision: HALF_UP rounding, 6 decimal places for koefisien
