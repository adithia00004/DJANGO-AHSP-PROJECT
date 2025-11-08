# Source Change & Cascade Reset Documentation

**Version:** 1.0
**Last Updated:** 2025-11-08
**Feature:** List Pekerjaan - Source Type Change with Auto-Reset

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [User Requirements](#user-requirements)
3. [Technical Implementation](#technical-implementation)
4. [User Flow](#user-flow)
5. [Bug Fixes](#bug-fixes)
6. [Testing](#testing)
7. [Model Reference](#model-reference)
8. [API Reference](#api-reference)

---

## 🎯 Overview

Implementasi fitur **Source Change dengan Cascade Reset** pada halaman List Pekerjaan yang memungkinkan user mengganti jenis sumber pekerjaan (CUSTOM ↔ REF ↔ REF_MODIFIED) dengan auto-reset semua data terkait untuk menjaga konsistensi data.

### Key Features

- ✅ **Frontend Auto-Reset**: Kolom uraian dan satuan otomatis dikosongkan saat user mengganti source type
- ✅ **Backend Validation**: Validasi ref_id wajib diisi saat mengganti ke REF/REF_MODIFIED
- ✅ **Cascade Reset**: Semua data terkait (volume, jadwal, template AHSP) direset otomatis
- ✅ **Data Integrity**: Pekerjaan tidak terhapus saat update, hanya data terkait yang direset
- ✅ **Comprehensive Testing**: 7 test scenarios untuk memastikan behavior yang konsisten

---

## 👤 User Requirements

### Requirement 1: Auto-Reset Kolom saat Source Change

**User Story:**
> "Ketika saya mengganti kolom 'Sumber' dari CUSTOM ke REFERENSI, saya ingin kolom Uraian Pekerjaan dan Satuan langsung dikosongkan agar jelas bahwa saya harus memilih AHSP dari dropdown."

**Implementation:**
- Frontend JavaScript auto-clear fields saat source_type berubah
- Preview ter-update otomatis
- Textarea resize setelah clear

### Requirement 2: Cascade Delete pada Source/Ref Change

**User Story:**
> "Ketika saya mengganti source type atau ref_id pekerjaan, semua data terkait (volume, jadwal, template AHSP) harus direset karena referensi berubah."

**Implementation:**
- Backend cascade reset semua related data
- Volume: DELETE record (bukan update ke NULL)
- Jadwal: DELETE semua PekerjaanTahapan
- Template AHSP: DELETE dan replace dengan data baru
- Formula State: DELETE

### Requirement 3: Extended Search Scope

**User Story:**
> "Saya ingin bisa mencari pekerjaan berdasarkan kode AHSP, nama AHSP referensi, atau uraian pekerjaan."

**Implementation:**
- Search across 4 fields menggunakan Django Q objects
- Tree filtering untuk menampilkan hanya branch yang relevan

---

## 🔧 Technical Implementation

### 1. Frontend Auto-Reset (list_pekerjaan.js)

**Location:** `detail_project/static/detail_project/js/list_pekerjaan.js:795-813`

```javascript
function syncFields() {
    const v = srcSel?.value;
    const oldSourceType = row.dataset.sourceType;  // Save old value
    row.dataset.sourceType = v || '';
    const isCustom  = (v === 'custom');
    const isRefLike = (v === 'ref' || v === 'ref_modified');

    // AUTO-RESET: Reset uraian/satuan when changing FROM custom TO ref/ref_modified
    if (oldSourceType === 'custom' && isRefLike) {
        if (uraianInput) {
            uraianInput.value = '';
            autoResize(uraianInput);  // Resize textarea after clear
        }
        if (satuanInput) satuanInput.value = '';
        // Trigger preview update
        const td = row.querySelector('td.col-urai, #lp-table tbody td:nth-child(4)');
        if (td) syncPreview(td);
    }

    // Set readonly based on source type
    if (uraianInput) uraianInput.readOnly = !(isCustom || v === 'ref_modified');
    if (satuanInput) satuanInput.readOnly = !isCustom;

    // ... rest of code
}
```

**Triggers:**
- User changes dropdown "Sumber"
- Event listener: `srcSel?.addEventListener('change', syncFields)`

**Behavior:**
| Source Change | Uraian | Satuan | Ref Dropdown |
|---------------|--------|--------|--------------|
| CUSTOM → REF | ✅ Clear | ✅ Clear | ✅ Enable |
| CUSTOM → REF_MOD | ✅ Clear | ✅ Clear | ✅ Enable |
| REF → CUSTOM | ❌ Keep | ❌ Keep | ✅ Disable |
| REF → REF_MOD | ❌ Keep | ❌ Keep | ✅ Keep |

---

### 2. Backend Validation (views_api.py)

**Location:** `detail_project/views_api.py:710-718`

```python
# Ganti tipe sumber → pasti replace
if pobj.source_type != src:
    # Special case: ganti ke REF/REF_MOD tapi tidak ada ref_id
    if src in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_REF_MOD] and new_ref_id is None:
        errors.append(_err(
            f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].ref_id",
            "Wajib diisi saat mengganti source type ke ref/ref_modified"
        ))
        continue
    replace = True
```

**Error Handling:**
- ✅ Prevents `int(None)` error
- ✅ Returns clear error message to user
- ✅ Prevents data corruption

---

### 3. Cascade Reset Function (_reset_pekerjaan_related_data)

**Location:** `detail_project/views_api.py:564-598`

```python
def _reset_pekerjaan_related_data(pobj):
    """
    Reset semua data terkait pekerjaan saat pekerjaan dimodifikasi (source_type atau ref_id berubah).

    Cascade reset:
    - DetailAHSPProject: hapus semua detail lama
    - VolumePekerjaan: hapus record (quantity field NOT NULL)
    - PekerjaanTahapan: hapus dari semua tahapan (jadwal)
    - VolumeFormulaState: hapus formula state
    - detail_ready flag: set ke False
    """
    from .models import DetailAHSPProject, VolumePekerjaan, PekerjaanTahapan, VolumeFormulaState

    # 1. Hapus semua DetailAHSPProject (template AHSP)
    DetailAHSPProject.objects.filter(project=project, pekerjaan=pobj).delete()

    # 2. Hapus VolumePekerjaan (quantity field is NOT NULL, so delete instead of update)
    VolumePekerjaan.objects.filter(project=project, pekerjaan=pobj).delete()

    # 3. Hapus dari semua tahapan (jadwal)
    PekerjaanTahapan.objects.filter(pekerjaan=pobj).delete()

    # 4. Hapus volume formula state
    VolumeFormulaState.objects.filter(project=project, pekerjaan=pobj).delete()

    # 5. Set detail_ready flag ke False
    pobj.detail_ready = False
    pobj.save(update_fields=['detail_ready'])

    logger.info(
        f"Reset all related data for pekerjaan {pobj.id} (kode: {pobj.snapshot_kode})",
        extra={'project_id': project.id, 'pekerjaan_id': pobj.id}
    )
```

**Called By:**
1. `_adopt_tmp_into()` - Before adopting new reference data
2. REF→CUSTOM conversion - Before updating to custom

**Why DELETE instead of UPDATE to NULL?**

```python
# Model definition (models.py:230)
class VolumePekerjaan(TimeStampedModel):
    quantity = models.DecimalField(max_digits=18, decimal_places=3, validators=[MinValueValidator(0)])
    # ❌ No null=True → NOT NULL constraint in database
```

- Field `quantity` tidak punya `null=True`
- Database constraint: NOT NULL
- UPDATE ke NULL akan error: `IntegrityError: null value in column "quantity"`
- Solution: DELETE record

---

### 4. Extended Search Implementation

**Location:** `detail_project/views_api.py:359-376`

```python
search_query = request.GET.get('search') or request.GET.get('q') or ''

if search_query:
    from django.db.models import Q
    # Search in 4 fields
    p_qs = p_qs.filter(
        Q(snapshot_kode__icontains=search_query) |        # Kode AHSP
        Q(snapshot_uraian__icontains=search_query) |      # Uraian
        Q(ref__kode_ahsp__icontains=search_query) |       # Ref kode
        Q(ref__nama_ahsp__icontains=search_query)         # Ref nama
    )

    # Filter tree to only show matching branches
    filtered_sub_ids = set(p_qs.values_list('sub_klasifikasi_id', flat=True))
    s_qs = s_qs.filter(id__in=filtered_sub_ids)

    filtered_klas_ids = set(s_qs.values_list('klasifikasi_id', flat=True))
    k_qs = k_qs.filter(id__in=filtered_klas_ids)
```

**Search Scope:**
1. `snapshot_kode` - Kode pekerjaan
2. `snapshot_uraian` - Uraian pekerjaan
3. `ref__kode_ahsp` - Kode AHSP referensi
4. `ref__nama_ahsp` - Nama AHSP referensi

---

## 🔄 User Flow

### Flow 1: CUSTOM → REF (Success Path)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User State: CUSTOM Pekerjaan                             │
│    - Uraian: "Pembuatan kolom praktis 12x12"                │
│    - Satuan: "unit"                                          │
│    - Volume: 50.000                                          │
│    - Jadwal: Minggu 1 (100%)                                 │
│    - Detail AHSP: 2 items (TK.CUSTOM, BHN.CUSTOM)            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. User Action: Change "Sumber" from CUSTOM to REFERENSI    │
│    Frontend: syncFields() triggered                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Frontend Auto-Reset                                       │
│    ✅ Uraian: "" (cleared)                                   │
│    ✅ Satuan: "" (cleared)                                   │
│    ✅ Ref dropdown: enabled                                  │
│    ✅ Preview: updated                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. User Action: Select AHSP from dropdown                   │
│    - Pilih: "TEST.001 - Test AHSP Pekerjaan Balok"          │
│    - ref_id: 42                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. User Action: Click "Simpan"                              │
│    POST /api/project/99/list-pekerjaan/upsert/              │
│    Payload: {                                                │
│      source_type: "ref",                                     │
│      ref_id: 42,                                             │
│      id: 123                                                 │
│    }                                                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Backend Processing (views_api.py)                        │
│    a. Validation: ✅ ref_id present                          │
│    b. Detect source change: CUSTOM ≠ REF                     │
│    c. replace = True                                         │
│    d. clone_ref_pekerjaan() → create tmp                     │
│    e. _adopt_tmp_into(pobj, tmp, ...)                        │
│       └─ Calls _reset_pekerjaan_related_data(pobj)           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. Cascade Reset (_reset_pekerjaan_related_data)            │
│    ✅ DELETE DetailAHSPProject (TK.CUSTOM, BHN.CUSTOM)       │
│    ✅ DELETE VolumePekerjaan (volume 50.000)                 │
│    ✅ DELETE PekerjaanTahapan (Minggu 1)                     │
│    ✅ DELETE VolumeFormulaState                              │
│    ✅ UPDATE detail_ready = False                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. Adopt New Data (_adopt_tmp_into)                         │
│    ✅ Copy snapshot: kode, uraian, satuan from tmp           │
│    ✅ Move DetailAHSPProject from tmp to pobj                │
│    ✅ Set ref_id = 42                                        │
│    ✅ DELETE tmp                                             │
│    ✅ ADD pobj.id to keep_all_p (prevent deletion!)          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 9. Final State: REF Pekerjaan                               │
│    - Source: REF                                             │
│    - Kode: "TEST.001"                                        │
│    - Uraian: "Test AHSP Pekerjaan Balok" (from AHSP)        │
│    - Satuan: "m3" (from AHSP)                                │
│    - ref_id: 42                                              │
│    - Volume: NULL (reset)                                    │
│    - Jadwal: [] (reset)                                      │
│    - Detail AHSP: [TK.REF, BHN.REF] (from AHSP)              │
│    - detail_ready: False                                     │
└─────────────────────────────────────────────────────────────┘
```

### Flow 2: CUSTOM → REF (Error Path - Missing ref_id)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User State: CUSTOM Pekerjaan                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. User Action: Change "Sumber" to REFERENSI                │
│    Frontend: Fields auto-cleared                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. User Action: Click "Simpan" WITHOUT selecting AHSP       │
│    ❌ ref_id: null                                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Backend Validation (views_api.py:712-717)                │
│    if src in REF/REF_MOD and new_ref_id is None:            │
│        ❌ ERROR                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Response to User                                          │
│    HTTP 207 Multi-Status                                     │
│    {                                                         │
│      "ok": false,                                            │
│      "errors": [{                                            │
│        "path": "klasifikasi[0].sub[0].pekerjaan[0].ref_id", │
│        "message": "Wajib diisi saat mengganti source type    │
│                    ke ref/ref_modified"                      │
│      }]                                                      │
│    }                                                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. User sees clear error message                            │
│    ✅ No error 500                                           │
│    ✅ Data not corrupted                                     │
│    ✅ Can fix and retry                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🐛 Bug Fixes

### Bug Fix 1: Error 500 - int(None)

**Date:** 2025-11-08
**Commit:** f2ec17c
**Severity:** 🔴 Critical

**Issue:**
```
TypeError: int() argument must be a string, a bytes-like object or a real number, not 'NoneType'
Location: views_api.py:728
```

**Root Cause:**
```python
# Line 710: Sets replace=True without checking ref_id
if pobj.source_type != src:
    replace = True

# Line 728: Assumes new_ref_id is not None
if replace:
    rid = int(new_ref_id)  # ❌ ERROR if new_ref_id is None
```

**Scenario:**
1. User changes CUSTOM → REF
2. User forgets to select AHSP (ref_id = None)
3. User clicks Save
4. Code tries `int(None)` → Error 500

**Fix:**
```python
if pobj.source_type != src:
    if src in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_REF_MOD] and new_ref_id is None:
        errors.append(_err(..., "Wajib diisi saat mengganti source type ke ref/ref_modified"))
        continue
    replace = True
```

---

### Bug Fix 2: Frontend Not Auto-Resetting Fields

**Date:** 2025-11-08
**Commit:** f2ec17c
**Severity:** 🟡 Major

**Issue:**
When user changes source from CUSTOM to REF, uraian field still shows old CUSTOM value.

**Root Cause:**
```javascript
// OLD CODE: No reset logic
function syncFields() {
    const v = srcSel?.value;
    row.dataset.sourceType = v || '';
    // ❌ No auto-reset when source changes
}
```

**Fix:**
```javascript
function syncFields() {
    const oldSourceType = row.dataset.sourceType;  // ✅ Track old value
    row.dataset.sourceType = v || '';

    // ✅ Auto-reset on CUSTOM → REF transition
    if (oldSourceType === 'custom' && isRefLike) {
        if (uraianInput) {
            uraianInput.value = '';
            autoResize(uraianInput);
        }
        if (satuanInput) satuanInput.value = '';
        const td = row.querySelector('td.col-urai, #lp-table tbody td:nth-child(4)');
        if (td) syncPreview(td);
    }
}
```

---

### Bug Fix 3: Pekerjaan Deleted After Save

**Date:** 2025-11-08
**Commit:** 4163426
**Severity:** 🔴 Critical

**Issue:**
Pekerjaan disappears after changing source type and saving.

**Root Cause:**
```python
# Line 703-803: UPDATE EXISTING block
if p_id and p_id in existing_p:
    pobj = existing_p[p_id]
    # ... update logic ...
    _adopt_tmp_into(pobj, tmp, s_obj, order)
    # ❌ MISSING: keep_all_p.add(pobj.id)

# Line 896: CREATE block HAS it
else:
    # ... create logic ...
    keep_all_p.add(pobj.id)  # ✅ Present here

# Line 905: DELETE all not in keep_all_p
Pekerjaan.objects.filter(project=project).exclude(id__in=keep_all_p).delete()
```

**Scenario:**
1. User updates existing pekerjaan (enters UPDATE block)
2. `pobj.id` NOT added to `keep_all_p`
3. Line 905: Pekerjaan deleted (not in keep_all_p)
4. User sees pekerjaan disappear

**Fix:**
```python
# Line 805-806
# CRITICAL: Add to keep list so it doesn't get deleted at line 905
keep_all_p.add(pobj.id)
```

---

### Bug Fix 4: VolumePekerjaan IntegrityError

**Date:** 2025-11-08
**Commit:** 80fd0fc
**Severity:** 🔴 Critical

**Issue:**
```
IntegrityError: null value in column "quantity" of relation "detail_project_volumepekerjaan" violates not-null constraint
```

**Root Cause:**
```python
# OLD CODE: Tried to UPDATE to NULL
VolumePekerjaan.objects.filter(...).update(quantity=None)  # ❌ ERROR

# Model has NOT NULL constraint
class VolumePekerjaan(TimeStampedModel):
    quantity = models.DecimalField(...)  # No null=True
```

**Fix:**
```python
# DELETE instead of UPDATE
VolumePekerjaan.objects.filter(project=project, pekerjaan=pobj).delete()
```

---

### Bug Fix 5: Test Failures - Wrong Field Access

**Date:** 2025-11-08
**Commit:** 4163426
**Severity:** 🟡 Major

**Issue:**
```
FAILED test_rekap_expands_single_bundle - AssertionError: assert '25' == Decimal('25.000')
```

**Root Cause:**
```python
# compute_kebutuhan_items() returns:
{
    'quantity': '25',              # String for display
    'quantity_decimal': Decimal('25.000')  # Decimal for calculation
}

# Test used wrong field
result[key] = row['quantity']  # ❌ String
assert result[key] == Decimal('25.000')  # ❌ Fails: '25' != Decimal('25.000')
```

**Fix:**
```python
result[key] = row['quantity_decimal']  # ✅ Decimal
assert result[key] == Decimal('25.000')  # ✅ Pass
```

---

## ✅ Testing

### Test Suite: test_list_pekerjaan_source_change.py

**Location:** `detail_project/tests/test_list_pekerjaan_source_change.py`
**Total Tests:** 7
**Status:** ✅ All Passing

#### Test Coverage

**1. TestSourceChangeCUSTOMtoREF**
- ✅ `test_change_custom_to_ref_resets_fields`
  - Verifies uraian/satuan reset to AHSP values
  - Checks snapshot_kode from reference
  - Validates ref_id set correctly

- ✅ `test_change_custom_to_ref_triggers_cascade_reset`
  - Verifies DetailAHSPProject replaced
  - Checks VolumePekerjaan deleted
  - Validates PekerjaanTahapan deleted
  - Confirms VolumeFormulaState deleted

- ✅ `test_change_custom_to_ref_modified`
  - Tests REF_MODIFIED with custom overrides
  - Validates snapshot_kode format: "mod.X-{kode_ref}"
  - Checks custom uraian/satuan preserved

**2. TestSourceChangeREFtoCUSTOM**
- ✅ `test_change_ref_to_custom_resets_to_empty`
  - Verifies ref_id cleared
  - Checks snapshot_kode preserved (not regenerated)
  - Validates cascade reset triggered

**3. TestSourceChangeRefIDChange**
- ✅ `test_change_ref_id_resets_and_repopulates`
  - Tests changing from AHSP #1 to AHSP #2
  - Verifies cascade reset on ref_id change
  - Validates repopulation from new reference

**4. TestSourceChangeIntegration**
- ✅ `test_full_workflow_custom_to_ref_and_back`
  - Complete workflow: CUSTOM → REF → CUSTOM
  - Cascade reset at each step
  - Data integrity throughout

- ✅ `test_multiple_pekerjaan_source_change_isolated`
  - Changes to pekerjaan #1 don't affect pekerjaan #2
  - Isolation verification

#### Running Tests

```bash
# Run source change tests
pytest detail_project/tests/test_list_pekerjaan_source_change.py -v

# Expected output:
# test_change_custom_to_ref_resets_fields PASSED
# test_change_custom_to_ref_triggers_cascade_reset PASSED
# test_change_custom_to_ref_modified PASSED
# test_change_ref_to_custom_resets_to_empty PASSED
# test_change_ref_id_resets_and_repopulates PASSED
# test_full_workflow_custom_to_ref_and_back PASSED
# test_multiple_pekerjaan_source_change_isolated PASSED
#
# 7 passed
```

---

## 📚 Model Reference

### Field Constraints

| Model | Field | Type | NULL? | Notes |
|-------|-------|------|-------|-------|
| **Pekerjaan** | | | | |
| | source_type | CharField | ❌ NO | CUSTOM/REF/REF_MOD |
| | ref | FK | ✅ YES | To AHSPReferensi |
| | snapshot_kode | CharField | ❌ NO | |
| | snapshot_uraian | TextField | ❌ NO | |
| | snapshot_satuan | CharField | ✅ YES | |
| | detail_ready | BooleanField | ❌ NO | Default False |
| **VolumePekerjaan** | | | | |
| | quantity | DecimalField | ❌ NO | **Must DELETE** |
| **DetailAHSPProject** | | | | |
| | koefisien | DecimalField | ❌ NO | 6 decimal places |
| | ref_ahsp | FK | ✅ YES | For bundles |
| | ref_pekerjaan | FK | ✅ YES | For bundles |
| **VolumeFormulaState** | | | | |
| | raw | TextField | ✅ YES | Formula text |
| | is_fx | BooleanField | ❌ NO | Default True |
| **PekerjaanTahapan** | | | | |
| | proporsi_volume | DecimalField | ❌ NO | 0-100 |
| **TahapPelaksanaan** | | | | |
| | urutan | IntegerField | ❌ NO | Not ordering_index |
| **RincianReferensi** | | | | |
| | kode_item | CharField | ❌ NO | Not kode |
| | uraian_item | TextField | ❌ NO | Not uraian |
| | satuan_item | CharField | ❌ NO | Not satuan |

### Source Type Values

```python
# Pekerjaan.SOURCE_*
CUSTOM = 'custom'        # User-defined
REF = 'ref'             # Reference to AHSP (read-only uraian/satuan)
REF_MOD = 'ref_modified' # Reference with custom overrides

# Kode Format
# REF:      "TEST.001"
# REF_MOD:  "mod.1-TEST.001"
# CUSTOM:   "CUST-{sequential}"
```

### Cascade Delete Configuration

```python
# Django CASCADE configured in models.py
class Klasifikasi(TimeStampedModel):
    project = models.ForeignKey('dashboard.Project', on_delete=models.CASCADE)

class SubKlasifikasi(TimeStampedModel):
    klasifikasi = models.ForeignKey(Klasifikasi, on_delete=models.CASCADE)

class Pekerjaan(TimeStampedModel):
    sub_klasifikasi = models.ForeignKey(SubKlasifikasi, on_delete=models.CASCADE)

# Delete Klasifikasi → Deletes SubKlasifikasi → Deletes Pekerjaan → Deletes all related
```

---

## 🔌 API Reference

### POST /api/project/{project_id}/list-pekerjaan/upsert/

**Purpose:** Create or update pekerjaan with source type change support

#### Request Body

```json
{
  "klasifikasi": [
    {
      "id": 1,                    // Optional: existing klasifikasi
      "name": "Klasifikasi 1",
      "ordering_index": 1,
      "subs": [
        {
          "id": 10,               // Optional: existing sub
          "name": "Sub 1",
          "ordering_index": 1,
          "jobs": [
            {
              "id": 123,          // Required for UPDATE
              "source_type": "ref", // CUSTOM/REF/REF_MODIFIED
              "ref_id": 42,       // Required for REF/REF_MOD
              "snapshot_uraian": "Custom Override", // Optional for REF_MOD
              "snapshot_satuan": "meter",           // Optional for REF_MOD
              "ordering_index": 1
            }
          ]
        }
      ]
    }
  ]
}
```

#### Response (Success)

```json
{
  "ok": true,
  "id_map": {
    "klasifikasi": {"temp_k1": 1},
    "sub": {"temp_s1": 10},
    "pekerjaan": {"temp_p1": 123}
  },
  "summary": {
    "klasifikasi": 1,
    "sub": 1,
    "pekerjaan": 1
  }
}
```

#### Response (Validation Error)

```json
{
  "ok": false,
  "errors": [
    {
      "path": "klasifikasi[0].sub[0].pekerjaan[0].ref_id",
      "message": "Wajib diisi saat mengganti source type ke ref/ref_modified"
    }
  ]
}
```

#### Response (Partial Success)

```json
{
  "ok": false,
  "errors": [
    {
      "path": "klasifikasi[0].sub[0].pekerjaan[1].ref_id",
      "message": "Referensi #999 tidak ditemukan"
    }
  ],
  "id_map": {
    "pekerjaan": {"temp_p1": 123}  // First one succeeded
  }
}
```

**HTTP Status Codes:**
- `200` - Full success
- `207` - Partial success (some items failed)
- `400` - Validation failed (all items)
- `500` - Server error

---

### GET /api/project/{project_id}/list-pekerjaan/tree/

**Purpose:** Get hierarchical list of pekerjaan with search support

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| search | string | No | Search query |
| q | string | No | Alias for search |

#### Search Scope

Searches across 4 fields:
1. `snapshot_kode` - Pekerjaan code
2. `snapshot_uraian` - Pekerjaan description
3. `ref__kode_ahsp` - AHSP reference code
4. `ref__nama_ahsp` - AHSP reference name

#### Response

```json
{
  "ok": true,
  "tree": [
    {
      "id": 1,
      "name": "Klasifikasi 1",
      "ordering_index": 1,
      "subs": [
        {
          "id": 10,
          "name": "Sub 1",
          "ordering_index": 1,
          "pekerjaan": [
            {
              "id": 123,
              "source_type": "ref",
              "ref_id": 42,
              "snapshot_kode": "TEST.001",
              "snapshot_uraian": "Test AHSP",
              "snapshot_satuan": "m3",
              "detail_ready": false,
              "ordering_index": 1
            }
          ]
        }
      ]
    }
  ]
}
```

---

## 📋 Commit History

| # | Commit | Date | Description |
|---|--------|------|-------------|
| 1 | 9962184 | 2025-11-08 | Initial comprehensive test suite (727 lines) |
| 2 | d492fba | 2025-11-08 | Fix RincianReferensi field names |
| 3 | 45b4201 | 2025-11-08 | Fix TahapPelaksanaan model name |
| 4 | af70269 | 2025-11-08 | Fix VolumeFormulaState field names |
| 5 | a0af711 | 2025-11-08 | Remove non-existent formula field |
| 6 | 80fd0fc | 2025-11-08 | Delete VolumePekerjaan instead of NULL update |
| 7 | 36dcb5d | 2025-11-08 | Fix test expectations for REF_MODIFIED |
| 8 | f2ec17c | 2025-11-08 | Fix error 500 and auto-reset fields |
| 9 | 4163426 | 2025-11-08 | Prevent pekerjaan deletion on source change |

---

## 🎓 Lessons Learned

### 1. Database Constraints Matter

**Issue:** Tried to UPDATE VolumePekerjaan.quantity to NULL
**Lesson:** Always check model field definitions for `null=True`
**Solution:** DELETE record instead of UPDATE when field is NOT NULL

### 2. Frontend State Management

**Issue:** Fields retained old values after source change
**Lesson:** Track old state before updating to detect transitions
**Solution:** Save `oldSourceType` before setting new value

### 3. Keep Lists for Deletion Prevention

**Issue:** Updated pekerjaan got deleted by cleanup logic
**Lesson:** All code paths must add to keep_all_p set
**Solution:** Add `keep_all_p.add(pobj.id)` after UPDATE block

### 4. Test Field Types

**Issue:** Tests compared string '25' with Decimal('25.000')
**Lesson:** Check return value types in service functions
**Solution:** Use correct field: `quantity_decimal` not `quantity`

### 5. Validation Before Processing

**Issue:** Code tried `int(None)` causing error 500
**Lesson:** Validate required fields BEFORE processing
**Solution:** Check ref_id exists before setting replace=True

---

## 🚀 Future Enhancements

### Potential Improvements

1. **Undo/Redo Support**
   - Track change history
   - Allow users to revert source changes

2. **Batch Source Change**
   - Change multiple pekerjaan at once
   - Bulk cascade reset

3. **Change Preview**
   - Show what will be reset before save
   - Confirmation dialog for destructive changes

4. **Audit Trail**
   - Log all source type changes
   - Track who changed what and when

5. **Smart Suggestions**
   - Suggest AHSP based on uraian similarity
   - Auto-complete for AHSP selection

---

## 📞 Support

For issues or questions related to source change and cascade reset:

1. Check this documentation first
2. Review test cases in `test_list_pekerjaan_source_change.py`
3. Check commit history for bug fix patterns
4. Review code comments in `views_api.py` and `list_pekerjaan.js`

---

**Document Version:** 1.0
**Last Updated:** 2025-11-08
**Maintained By:** Development Team
