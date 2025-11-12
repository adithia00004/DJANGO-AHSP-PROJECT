# 📋 Comprehensive Page Interaction Integration Tests

## 🎯 Tujuan

Test suite ini dibuat untuk memverifikasi bahwa **interaksi antar page terjadi dengan harmonis dan tersinkronisasi sempurna** saat terjadi CRUD operations, khususnya untuk mencegah bug seperti:

- ✅ Data tampak kosong setelah save di page lain
- ✅ Cache tidak ter-invalidate dengan benar
- ✅ Bundle expansion gagal atau tidak muncul di Harga Items
- ✅ Perubahan volume tidak reflect di Rekap RAB
- ✅ Dual storage (DetailAHSPProject vs DetailAHSPExpanded) tidak sinkron

---

## 📁 Lokasi File

```
detail_project/tests/test_page_interactions_comprehensive.py
```

**Total Tests**: 20 integration tests
**Coverage**: 7 critical page interactions

---

## 🔍 Test Coverage Matrix

| # | From Page | To Page | Tests | Status | Priority |
|---|-----------|---------|-------|--------|----------|
| 1 | List Pekerjaan | Volume Pekerjaan | 3 | ✅ Complete | MEDIUM |
| 2 | List Pekerjaan | Template AHSP | 3 | ✅ Complete | HIGH |
| 3 | Volume Pekerjaan | Rekap RAB | 2 | ✅ Complete | HIGH |
| **4** | **Template AHSP** | **Harga Items** | **6** | ✅ **Complete** | **🔴 CRITICAL** |
| 5 | Template AHSP | Rincian AHSP | 2 | ✅ Complete | HIGH |
| 6 | Harga Items | Rincian AHSP | 2 | ✅ Complete | MEDIUM |
| 7 | Rincian AHSP | Rekap RAB | 2 | ✅ Complete | HIGH |

---

## 🧪 Cara Menjalankan Tests

### Option 1: Run All Page Interaction Tests

```bash
pytest detail_project/tests/test_page_interactions_comprehensive.py -v
```

### Option 2: Run Specific Test Class

```bash
# Test Template AHSP ↔ Harga Items (MOST CRITICAL)
pytest detail_project/tests/test_page_interactions_comprehensive.py::TestTemplateAHSPHargaItemsInteraction -v

# Test Volume ↔ Rekap RAB
pytest detail_project/tests/test_page_interactions_comprehensive.py::TestVolumePekerjaanRekapRABInteraction -v
```

### Option 3: Run Specific Test

```bash
# Test bundle expansion (frequent bug)
pytest detail_project/tests/test_page_interactions_comprehensive.py::TestTemplateAHSPHargaItemsInteraction::test_bundle_expansion_creates_expanded_harga_items -v
```

### Option 4: Run with Coverage Report

```bash
pytest detail_project/tests/test_page_interactions_comprehensive.py \
  --cov=detail_project.views_api \
  --cov=detail_project.services \
  --cov-report=html \
  -v
```

---

## 📊 Test Details

### Test #1: List Pekerjaan ↔ Volume Pekerjaan

**Purpose**: Memastikan volume tersimpan dengan benar saat pekerjaan dibuat/diubah.

#### Test Cases:
1. **test_create_pekerjaan_then_add_volume**
   - Scenario: User create pekerjaan → tambah volume
   - Expected: Volume tersimpan dan muncul di list volume API

2. **test_delete_pekerjaan_cascades_volume**
   - Scenario: User hapus pekerjaan yang punya volume
   - Expected: Volume ikut terhapus (CASCADE)

3. **test_volume_update_multiple_pekerjaan**
   - Scenario: User update volume untuk multiple pekerjaan sekaligus
   - Expected: Semua volume tersimpan dengan benar

---

### Test #2: List Pekerjaan ↔ Template AHSP

**Purpose**: Memastikan pekerjaan yang dibuat muncul di Template AHSP dengan status editable yang benar.

#### Test Cases:
1. **test_create_custom_pekerjaan_appears_in_template_ahsp**
   - Scenario: User create CUSTOM pekerjaan
   - Expected: Muncul di Template AHSP dan editable (read_only=false)

2. **test_create_ref_pekerjaan_readonly_in_template_ahsp**
   - Scenario: User create REF pekerjaan
   - Expected: Muncul tapi read-only (tidak bisa diedit di Template AHSP)

3. **test_change_pekerjaan_source_type_affects_editability**
   - Scenario: User ubah CUSTOM → REF via upsert
   - Expected: Status editable berubah menjadi read-only

---

### Test #3: Volume Pekerjaan ↔ Rekap RAB

**Purpose**: Memastikan perubahan volume langsung reflect di perhitungan Rekap RAB.

#### Test Cases:
1. **test_volume_change_updates_rekap_rab**
   - Scenario: User ubah volume dari 10 → 20
   - Expected: Subtotal di Rekap RAB naik 2x lipat
   - Formula: `subtotal = koef × volume × harga`

2. **test_zero_volume_excludes_from_rekap**
   - Scenario: User set volume = 0
   - Expected: Pekerjaan tidak muncul di Rekap (atau subtotal = 0)

---

### Test #4: Template AHSP ↔ Harga Items ⚠️ **CRITICAL**

**Purpose**: **INI TEST PALING PENTING!** Sering terjadi bug di interaksi ini, terutama dengan bundle dan dual storage.

#### Test Cases:

1. **test_add_tk_item_creates_harga_item**
   - Scenario: User tambah TK item di Template AHSP
   - Expected: HargaItemProject created, muncul di Harga Items page

2. **test_bundle_expansion_creates_expanded_harga_items** 🔥 **MOST CRITICAL**
   - Scenario: User tambah LAIN (bundle) item yang referensi pekerjaan lain
   - Expected:
     - Bundle di-expand menjadi komponen base (TK/BHN/ALT)
     - DetailAHSPProject created (raw input - keeps bundle)
     - DetailAHSPExpanded created (expanded components)
     - **Semua expanded components muncul di Harga Items page**
     - Koefisien dikalikan dengan benar
   - **INI BUG YANG PALING SERING MUNCUL!**

3. **test_empty_bundle_shows_error**
   - Scenario: User tambah bundle yang referensi pekerjaan KOSONG (no details)
   - Expected: Error message jelas, bundle tidak di-expand

4. **test_update_template_ahsp_syncs_to_harga_items**
   - Scenario: User edit uraian item di Template AHSP
   - Expected: HargaItemProject ter-update, terlihat di Harga Items

5. **test_delete_template_ahsp_item_keeps_harga_item_if_used_elsewhere**
   - Scenario: Item 'L.01' dipakai di 2 pekerjaan, dihapus dari 1 pekerjaan
   - Expected: HargaItemProject tetap ada (masih dipakai pekerjaan lain)

6. **test_dual_storage_consistency**
   - Scenario: Verify DetailAHSPProject (raw) vs DetailAHSPExpanded (computed) sinkron
   - Expected: Data konsisten di kedua storage

---

### Test #5: Template AHSP ↔ Rincian AHSP

**Purpose**: Memastikan data di Template AHSP muncul dengan benar di Rincian AHSP (Detail Gabungan).

#### Test Cases:
1. **test_save_template_ahsp_appears_in_rincian**
   - Scenario: User save TK + BHN di Template AHSP
   - Expected: Kedua item muncul di Rincian AHSP

2. **test_bundle_expanded_in_rincian_ahsp**
   - Scenario: User save bundle di Template AHSP
   - Expected: Rincian AHSP show expanded components (TK/BHN/ALT), bukan bundle LAIN

---

### Test #6: Harga Items ↔ Rincian AHSP

**Purpose**: Memastikan perubahan harga langsung reflect di subtotal Rincian AHSP.

#### Test Cases:
1. **test_update_harga_reflects_in_rincian_subtotal**
   - Scenario: User update harga dari 100,000 → 150,000
   - Expected: Subtotal di Rincian AHSP naik proporsional

2. **test_null_harga_shows_zero_subtotal_in_rincian**
   - Scenario: Item belum diisi harganya (NULL)
   - Expected: Subtotal = 0 di Rincian AHSP

---

### Test #7: Rincian AHSP ↔ Rekap RAB

**Purpose**: Memastikan Rekap RAB aggregate dari Rincian AHSP dengan benar.

#### Test Cases:
1. **test_rincian_changes_reflect_in_rekap_total**
   - Scenario: Perubahan koef/harga/volume di Rincian
   - Expected: Grand total di Rekap RAB ter-update

2. **test_rekap_aggregates_multiple_pekerjaan_correctly**
   - Scenario: Project punya 2+ pekerjaan dengan detail & harga
   - Expected: Rekap aggregate semua dengan benar (SUM)

---

## 🐛 Common Bugs These Tests Catch

### Bug #1: Bundle Components Missing in Harga Items ⚠️ **FREQUENT**
**Symptom**: User add bundle di Template AHSP, tapi komponen tidak muncul di Harga Items.

**Root Cause**:
- Bundle expansion gagal
- HargaItemProject tidak ter-create untuk expanded components
- Query di Harga Items hanya ambil dari DetailAHSPExpanded

**Test**: `test_bundle_expansion_creates_expanded_harga_items`

**How to Fix**:
1. Check `expand_bundle_to_components()` function
2. Verify HargaItemProject created for each expanded component
3. Check Harga Items query includes `expanded_refs__project=project`

---

### Bug #2: Stale Cache After Data Change
**Symptom**: User update data di page A, tapi page B masih show data lama.

**Root Cause**:
- Cache invalidated BEFORE transaction commit
- Frontend memory cache not cleared

**Test**: All tests implicitly check this by calling `clear_cache_for_project()`

**How to Fix**:
1. Wrap `invalidate_rekap_cache()` with `transaction.on_commit()`
2. Clear frontend cache after successful save

---

### Bug #3: Dual Storage Inconsistency
**Symptom**: DetailAHSPProject (raw) ada, tapi DetailAHSPExpanded (computed) kosong.

**Root Cause**:
- Bundle expansion failed silently
- Transaction rollback partial

**Test**: Bundle tests check both storages

**How to Fix**:
1. Add proper error handling in expansion
2. Use `@transaction.atomic` consistently

---

### Bug #4: Volume Change Not Reflected in Rekap
**Symptom**: User update volume, Rekap RAB masih show old calculation.

**Root Cause**:
- Cache not invalidated after volume save
- Race condition in cache timing

**Test**: `test_volume_change_updates_rekap_rab`

**How to Fix**:
1. Ensure `api_save_volume_pekerjaan` invalidates cache
2. Use `transaction.on_commit(lambda: invalidate_rekap_cache(project))`

---

## 🔧 Running Tests in CI/CD

### GitHub Actions Example

```yaml
name: Page Interaction Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-django pytest-cov

    - name: Run Page Interaction Tests
      run: |
        pytest detail_project/tests/test_page_interactions_comprehensive.py \
          -v \
          --cov=detail_project \
          --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        files: ./coverage.xml
```

---

## 📈 Success Metrics

### When All Tests Pass:
✅ **20/20 tests passing** = Page interactions working correctly!

### When Tests Fail:
1. **1-2 failures** = Isolated bug, fix specific interaction
2. **3-5 failures** = Systemic issue, check cache/transactions
3. **6+ failures** = Major regression, revert recent changes

---

## 🚨 Critical Test Priority

If time is limited, run tests in this order:

### **Priority 1: CRITICAL** (Must pass before deploy)
```bash
pytest detail_project/tests/test_page_interactions_comprehensive.py::TestTemplateAHSPHargaItemsInteraction -v
```
- Most frequent bugs
- Complex bundle logic
- Dual storage

### **Priority 2: HIGH** (Should pass before deploy)
```bash
pytest detail_project/tests/test_page_interactions_comprehensive.py::TestVolumePekerjaanRekapRABInteraction -v
pytest detail_project/tests/test_page_interactions_comprehensive.py::TestRincianAHSPRekapRABInteraction -v
```
- Financial calculations
- User-facing totals

### **Priority 3: MEDIUM** (Nice to have)
```bash
pytest detail_project/tests/test_page_interactions_comprehensive.py::TestListPekerjaanVolumeInteraction -v
```
- Basic CRUD
- Less critical

---

## 🔍 Debugging Failed Tests

### Step 1: Read the Error Message
```bash
pytest detail_project/tests/test_page_interactions_comprehensive.py::test_name -vv
```

### Step 2: Check Database State
Tests use `@pytest.mark.django_db` so each test has isolated DB state.

### Step 3: Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Step 4: Run Single Test with PDB
```bash
pytest detail_project/tests/test_page_interactions_comprehensive.py::test_name -vv --pdb
```

---

## 📝 Adding New Tests

### Template for New Page Interaction Test:

```python
@pytest.mark.django_db
class TestNewPageInteraction:
    """Test interaksi antara Page A dan Page B"""

    def test_action_in_page_a_reflects_in_page_b(
        self, client_logged, project, fixtures
    ):
        """
        Scenario: User does X in Page A

        Expected: Y appears in Page B
        """
        # Step 1: Setup data
        # ...

        # Step 2: Perform action in Page A
        response = client_logged.post(...)
        assert response.status_code == 200

        # Step 3: Verify result in Page B
        response = client_logged.get(...)
        data = response.json()

        # Step 4: Assert expectations
        assert data['expected_field'] == expected_value
```

---

## 🎯 Expected Outcomes

### After Running All Tests:

```
===================== test session starts ======================
platform linux -- Python 3.11.x, pytest-7.x.x, ...
collected 20 items

test_page_interactions_comprehensive.py::TestListPekerjaanVolumeInteraction::test_create_pekerjaan_then_add_volume PASSED [ 5%]
test_page_interactions_comprehensive.py::TestListPekerjaanVolumeInteraction::test_delete_pekerjaan_cascades_volume PASSED [10%]
test_page_interactions_comprehensive.py::TestListPekerjaanVolumeInteraction::test_volume_update_multiple_pekerjaan PASSED [15%]

test_page_interactions_comprehensive.py::TestListPekerjaanTemplateAHSPInteraction::test_create_custom_pekerjaan_appears_in_template_ahsp PASSED [20%]
test_page_interactions_comprehensive.py::TestListPekerjaanTemplateAHSPInteraction::test_create_ref_pekerjaan_readonly_in_template_ahsp PASSED [25%]
test_page_interactions_comprehensive.py::TestListPekerjaanTemplateAHSPInteraction::test_change_pekerjaan_source_type_affects_editability PASSED [30%]

test_page_interactions_comprehensive.py::TestVolumePekerjaanRekapRABInteraction::test_volume_change_updates_rekap_rab PASSED [35%]
test_page_interactions_comprehensive.py::TestVolumePekerjaanRekapRABInteraction::test_zero_volume_excludes_from_rekap PASSED [40%]

test_page_interactions_comprehensive.py::TestTemplateAHSPHargaItemsInteraction::test_add_tk_item_creates_harga_item PASSED [45%]
test_page_interactions_comprehensive.py::TestTemplateAHSPHargaItemsInteraction::test_bundle_expansion_creates_expanded_harga_items PASSED [50%] ⚠️
test_page_interactions_comprehensive.py::TestTemplateAHSPHargaItemsInteraction::test_empty_bundle_shows_error PASSED [55%]
test_page_interactions_comprehensive.py::TestTemplateAHSPHargaItemsInteraction::test_update_template_ahsp_syncs_to_harga_items PASSED [60%]
test_page_interactions_comprehensive.py::TestTemplateAHSPHargaItemsInteraction::test_delete_template_ahsp_item_keeps_harga_item_if_used_elsewhere PASSED [65%]

test_page_interactions_comprehensive.py::TestTemplateAHSPRincianAHSPInteraction::test_save_template_ahsp_appears_in_rincian PASSED [70%]
test_page_interactions_comprehensive.py::TestTemplateAHSPRincianAHSPInteraction::test_bundle_expanded_in_rincian_ahsp PASSED [75%]

test_page_interactions_comprehensive.py::TestHargaItemsRincianAHSPInteraction::test_update_harga_reflects_in_rincian_subtotal PASSED [80%]
test_page_interactions_comprehensive.py::TestHargaItemsRincianAHSPInteraction::test_null_harga_shows_zero_subtotal_in_rincian PASSED [85%]

test_page_interactions_comprehensive.py::TestRincianAHSPRekapRABInteraction::test_rincian_changes_reflect_in_rekap_total PASSED [90%]
test_page_interactions_comprehensive.py::TestRincianAHSPRekapRABInteraction::test_rekap_aggregates_multiple_pekerjaan_correctly PASSED [95%]

=================== 20 passed in 45.32s ====================
```

✅ **All 20 tests PASSED** = System fully synchronized!

---

## 📞 Support

**If tests fail after your changes**:
1. Read error message carefully
2. Check which page interaction is broken
3. Review recent changes to related views/services
4. Run test in isolation with `-vv` flag
5. Check cache invalidation timing
6. Verify dual storage consistency

**Common fixes**:
- Add `transaction.on_commit()` for cache invalidation
- Clear frontend cache after save
- Add proper error handling in bundle expansion
- Check foreign key relationships

---

## ✅ Checklist Before Deployment

- [ ] Run all page interaction tests
- [ ] **Critical**: Template AHSP ↔ Harga Items tests pass (6/6)
- [ ] Volume ↔ Rekap RAB tests pass (2/2)
- [ ] No regression in other test suites
- [ ] Manual smoke test on staging
- [ ] Cache invalidation verified
- [ ] Bundle expansion working correctly

---

**Created**: 2025-11-12
**Last Updated**: 2025-11-12
**Maintainer**: Development Team
**Priority**: 🔴 CRITICAL - Run before every deployment
