# 🧪 Panduan Eksekusi Test Dual Storage

**Dibuat**: 2025-11-09
**Tujuan**: Panduan untuk menjalankan dan menginterpretasi pytest dual storage

---

## 📦 Persiapan

### 1. Pastikan Dependencies Terinstall
```bash
# Aktifkan virtual environment (jika ada)
source venv/bin/activate  # Linux/Mac
# atau
venv\Scripts\activate  # Windows

# Install pytest dan pytest-django jika belum
pip install pytest pytest-django
```

### 2. Verifikasi pytest.ini atau Django Settings
Pastikan pytest dikonfigurasi dengan benar untuk Django. File `pytest.ini` seharusnya sudah ada atau pytest akan otomatis mendeteksi Django settings.

---

## 🚀 Menjalankan Test

### **Opsi 1: Jalankan Semua Test Dual Storage**
```bash
pytest detail_project/tests/test_dual_storage.py -v
```

**Output yang Diharapkan** (jika semua PASS):
```
test_dual_storage.py::TestREFPekerjaanDualStorage::test_clone_ref_populates_both_storages PASSED
test_dual_storage.py::TestREFPekerjaanDualStorage::test_harga_items_api_returns_ref_items PASSED
test_dual_storage.py::TestREFMODIFIEDPekerjaanDualStorage::test_clone_ref_modified_populates_both_storages PASSED
test_dual_storage.py::TestREFMODIFIEDPekerjaanDualStorage::test_ref_modified_metadata PASSED
test_dual_storage.py::TestCUSTOMBundleDualStorage::test_custom_bundle_expansion_populates_expanded_storage PASSED
test_dual_storage.py::TestCUSTOMBundleDualStorage::test_harga_items_shows_expanded_not_bundle PASSED
test_dual_storage.py::TestOverrideBugFixed::test_multiple_bundles_same_kode_no_override PASSED
test_dual_storage.py::TestDualStorageErrorCases::test_lain_without_ref_pekerjaan_errors PASSED
test_dual_storage.py::TestDualStorageErrorCases::test_empty_bundle_handled_gracefully PASSED

==================== 9 passed in X.XXs ====================
```

### **Opsi 2: Jalankan Test Spesifik per Skenario**

**Test REF saja:**
```bash
pytest detail_project/tests/test_dual_storage.py::TestREFPekerjaanDualStorage -v
```

**Test REF_MODIFIED saja:**
```bash
pytest detail_project/tests/test_dual_storage.py::TestREFMODIFIEDPekerjaanDualStorage -v
```

**Test CUSTOM Bundle saja:**
```bash
pytest detail_project/tests/test_dual_storage.py::TestCUSTOMBundleDualStorage -v
```

**Test Override Bug Fix (CRITICAL):**
```bash
pytest detail_project/tests/test_dual_storage.py::TestOverrideBugFixed -v
```

### **Opsi 3: Jalankan dengan Output Logging (Debug Mode)**
```bash
pytest detail_project/tests/test_dual_storage.py -v -s
```

Flag `-s` akan menampilkan semua `print()` statements dan logging dari backend Django, berguna untuk debugging.

### **Opsi 4: Jalankan Test Tertentu**
```bash
# Jalankan hanya test bundle expansion
pytest detail_project/tests/test_dual_storage.py::TestCUSTOMBundleDualStorage::test_custom_bundle_expansion_populates_expanded_storage -v
```

---

## 📊 Menginterpretasi Hasil

### ✅ **Test PASSED - Semua OK**
```
test_dual_storage.py::TestREFPekerjaanDualStorage::test_clone_ref_populates_both_storages PASSED
```

**Artinya**: Scenario ini bekerja dengan benar. Dual storage terisi sesuai harapan.

---

### ❌ **Test FAILED - Ada Error**

**Contoh Output:**
```
test_dual_storage.py::TestCUSTOMBundleDualStorage::test_custom_bundle_expansion_populates_expanded_storage FAILED

=================================== FAILURES ===================================
_________________________________ test_custom_bundle_expansion_populates_expanded_storage _________________________________

    def test_custom_bundle_expansion_populates_expanded_storage(self, ...):
        ...
>       assert data['saved_expanded_rows'] == 3, "Should expand to 3 components"
E       AssertionError: Should expand to 3 components
E       assert 0 == 3
```

**Cara Membaca Error:**
- **Baris `assert`**: Assertion yang gagal
- **Expected vs Actual**: `0 == 3` artinya expected 3 tapi actual 0
- **Error Message**: "Should expand to 3 components"

**Langkah Debugging:**
1. Jalankan test dengan `-s` flag untuk melihat logging:
   ```bash
   pytest detail_project/tests/test_dual_storage.py::TestCUSTOMBundleDualStorage::test_custom_bundle_expansion_populates_expanded_storage -v -s
   ```

2. Periksa Django logs yang muncul (cari `[EXPAND_BUNDLE]`, `[POPULATE_EXPANDED]`, dll)

3. Cek output API response di terminal (test akan print response data jika ada error)

---

## 🔍 Test Coverage Matrix

| Test Class | Scenario | Storage 1 (Raw) | Storage 2 (Expanded) | Harga Items API | Override Fix |
|------------|----------|-----------------|----------------------|-----------------|--------------|
| **TestREFPekerjaanDualStorage** | REF | ✅ | ✅ | ✅ | N/A |
| **TestREFMODIFIEDPekerjaanDualStorage** | REF_MODIFIED | ✅ | ✅ | ✅ | N/A |
| **TestCUSTOMBundleDualStorage** | CUSTOM Bundle | ✅ | ✅ | ✅ | N/A |
| **TestOverrideBugFixed** | Override Bug | ✅ | ✅ | ✅ | ✅ |
| **TestDualStorageErrorCases** | Error Validation | N/A | N/A | N/A | N/A |

---

## 🎯 Apa yang Divalidasi Setiap Test?

### **1. TestREFPekerjaanDualStorage**
- ✅ `clone_ref_pekerjaan()` membuat rows di `DetailAHSPProject`
- ✅ `_populate_expanded_from_raw()` membuat rows di `DetailAHSPExpanded`
- ✅ Harga Items API returns 3 items (L.01, C.01, D.01)
- ✅ `HargaItemProject` created untuk setiap item

### **2. TestREFMODIFIEDPekerjaanDualStorage**
- ✅ Metadata pekerjaan: `source_type='ref_modified'`, `snapshot_kode` starts with `mod.`
- ✅ Dual storage populated sama seperti REF
- ✅ Override uraian/kode berfungsi

### **3. TestCUSTOMBundleDualStorage**
- ✅ LAIN bundle item disimpan di `DetailAHSPProject` (raw)
- ✅ Bundle di-expand ke components di `DetailAHSPExpanded`
- ✅ Koefisien multiplication benar (10 × 0.66 = 6.60)
- ✅ `source_bundle_kode` dan `expansion_depth` tracked
- ✅ Harga Items API shows ONLY components (L.01, M.01, N.01), NOT bundle

### **4. TestOverrideBugFixed** ⚠️ CRITICAL
- ✅ Multiple bundles dengan kode sama (TK.001) BOTH preserved
- ✅ `DetailAHSPExpanded` has 4 rows (2 TK.001, 1 BHN.001, 1 BHN.002)
- ✅ `source_bundle_kode` distinguishes duplicates
- ✅ Koefisien per bundle berbeda (5.0 vs 4.5)

### **5. TestDualStorageErrorCases**
- ✅ LAIN without `ref_pekerjaan_id` returns error message
- ✅ Empty bundle handled gracefully (no crash)

---

## 🐛 Troubleshooting

### **Test Gagal: Database Errors**
```
django.db.utils.OperationalError: no such table: detail_project_detailahspexpanded
```

**Solusi**: Jalankan migrations
```bash
python manage.py migrate
```

---

### **Test Gagal: Import Errors**
```
ImportError: cannot import name 'clone_ref_pekerjaan'
```

**Solusi**: Pastikan fungsi ada di `detail_project/utils/clone_pekerjaan.py` atau sesuaikan import di test file.

---

### **Test Gagal: Authentication Errors**
```
AssertionError: assert 403 == 200
```

**Solusi**: Test menggunakan fixture `client_logged` yang sudah authenticated. Periksa apakah fixture di `conftest.py` benar.

---

## 📝 Menambahkan Test Baru

Jika ingin menambahkan test case baru:

```python
@pytest.mark.django_db
class TestNewScenario:
    def test_my_new_case(self, project, sub_klas, client_logged):
        # Arrange
        pekerjaan = Pekerjaan.objects.create(...)

        # Act
        response = client_logged.post(...)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
```

---

## 🎯 Next Steps Setelah Test

1. **Jika semua test PASS** ✅
   - Dual storage implementation verified!
   - Lanjutkan testing manual di UI untuk validasi UX

2. **Jika ada test FAILED** ❌
   - Jalankan dengan `-s` flag untuk logging
   - Periksa assertion error message
   - Debug menggunakan logging backend (`[SAVE_DETAIL_AHSP]`, dll)
   - Fix bug, re-run test

3. **Jika test PASS tapi manual testing gagal** ⚠️
   - Kemungkinan data lama (created before fixes)
   - Delete old pekerjaan, create new one
   - Verify migrations up-to-date

---

## 📚 Referensi

- **Test Plan**: `DUAL_STORAGE_TEST_PLAN.md` - Detailed scenario documentation
- **Test Code**: `detail_project/tests/test_dual_storage.py` - pytest implementation
- **Fixtures**: `detail_project/tests/conftest.py` - Reusable test data setup

---

**Status**: Ready untuk eksekusi test! 🚀
