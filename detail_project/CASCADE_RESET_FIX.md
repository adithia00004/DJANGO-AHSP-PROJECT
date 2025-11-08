# Cascade Reset Fix for List Pekerjaan Modification

> **⚠️ UPDATED DOCUMENTATION:** For complete details, see [SOURCE_CHANGE_CASCADE_RESET.md](./SOURCE_CHANGE_CASCADE_RESET.md)
>
> This document provides overview. For comprehensive documentation including:
> - Complete user flow diagrams
> - All bug fixes with root cause analysis
> - Frontend auto-reset implementation
> - Complete test suite documentation
> - API reference
>
> Please refer to the main documentation file.

---

## Problem Statement

**Bug Report:**
User melaporkan 2 masalah pada List Pekerjaan:
1. **Input tidak bisa dimodifikasi** pada kolom sumber (referensi/modified/custom)
2. **Data related tidak tereset** saat user modify/hapus pekerjaan

**Impact:**
Saat user mengubah pekerjaan (misalnya ganti dari "Referensi" ke "Custom", atau ganti ref_id), data-data terkait TIDAK ter-reset:
- ✅ DetailAHSPProject (Template AHSP) - **partially reset** (hanya move, ada conflict)
- ❌ VolumePekerjaan (Volume) - **TIDAK RESET** (volume lama tetap ada!)
- ❌ PekerjaanTahapan (Jadwal) - **TIDAK RESET** (jadwal lama tetap ada!)
- ❌ VolumeFormulaState (Formula State) - **TIDAK RESET**
- ❌ detail_ready flag - **TIDAK RESET**

**Expected Behavior:**
Saat user modify pekerjaan (ganti source_type atau ref_id), SEMUA data terkait harus di-reset/dihapus.

---

## Root Cause Analysis

### Code Location: `detail_project/views_api.py`

**Function:** `api_upsert_list_pekerjaan()` (line 392+)

**Problem Code (OLD `_adopt_tmp_into`):**

```python
def _adopt_tmp_into(pobj, tmp, s_obj, order: int):
    """Salin snapshot tmp → pobj, pindahkan seluruh detail tmp → pobj, lalu hapus tmp."""
    from .models import DetailAHSPProject

    # ... copy snapshot fields ...

    # PROBLEM: Hanya move DetailAHSPProject dengan dedup
    existing_kodes = set(
        DetailAHSPProject.objects
        .filter(project=project, pekerjaan=pobj)
        .values_list("kode", flat=True)
    )
    tmp_qs = DetailAHSPProject.objects.filter(project=project, pekerjaan=tmp)
    if existing_kodes:
        tmp_qs = tmp_qs.exclude(kode__in=existing_kodes)  # Skip conflict
    tmp_qs.update(pekerjaan=pobj)
    tmp.delete()
```

**Issues:**
1. DetailAHSPProject lama TIDAK DIHAPUS → conflict items skipped
2. VolumePekerjaan TIDAK DIRESET → volume lama tetap ada
3. PekerjaanTahapan TIDAK DIHAPUS → jadwal lama tetap ada
4. VolumeFormulaState TIDAK DIHAPUS → formula state lama tetap ada
5. detail_ready flag TIDAK DIRESET → flag salah

---

## Solution Implemented

### 1. Created `_reset_pekerjaan_related_data()` function

**Purpose:** Reset ALL related data when pekerjaan is modified

```python
def _reset_pekerjaan_related_data(pobj):
    """
    Reset semua data terkait pekerjaan saat pekerjaan dimodifikasi.

    Cascade reset:
    - DetailAHSPProject: hapus semua detail lama
    - VolumePekerjaan: reset volume jadi NULL/0
    - PekerjaanTahapan: hapus dari semua tahapan (jadwal)
    - VolumeFormulaState: hapus formula state
    - detail_ready flag: set ke False
    """
    from .models import DetailAHSPProject, VolumePekerjaan, PekerjaanTahapan, VolumeFormulaState

    # 1. Hapus semua DetailAHSPProject (template AHSP)
    DetailAHSPProject.objects.filter(project=project, pekerjaan=pobj).delete()

    # 2. Hapus VolumePekerjaan (quantity field is NOT NULL, must DELETE not UPDATE)
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

### 2. Updated `_adopt_tmp_into()` to call reset

**NEW Code:**

```python
def _adopt_tmp_into(pobj, tmp, s_obj, order: int):
    """
    Salin snapshot tmp → pobj, pindahkan seluruh detail tmp → pobj, lalu hapus tmp.

    IMPORTANT: Karena pekerjaan berubah, reset semua data terkait.
    """
    from .models import DetailAHSPProject

    # CRITICAL: Reset semua data terkait sebelum adopt new data
    _reset_pekerjaan_related_data(pobj)

    # ... copy snapshot fields ...

    # Move DetailAHSPProject from tmp to pobj
    # (No dedup needed since we already deleted all old details)
    DetailAHSPProject.objects.filter(project=project, pekerjaan=tmp).update(pekerjaan=pobj)

    tmp.delete()
```

**Changes:**
- ✅ Call `_reset_pekerjaan_related_data()` FIRST
- ✅ No dedup needed (old details already deleted)
- ✅ Clean transfer of new detail from tmp

### 3. Updated REF→CUSTOM conversion to reset

**Location:** Line 707-731

**OLD:**
```python
else:
    # ke CUSTOM: update in-place + bersihkan FK ref
    pobj.source_type = src
    pobj.ref = None
    # ... update fields ...
```

**NEW:**
```python
else:
    # ke CUSTOM: update in-place + bersihkan FK ref
    # CRITICAL: Reset related data karena source_type berubah
    _reset_pekerjaan_related_data(pobj)

    pobj.source_type = src
    pobj.ref = None
    # ... update fields ...
```

### 4. Updated REUSE case to reset when source changes

**Location:** Line 815-832

**NEW:**
```python
pobj = _get_or_reuse_pekerjaan_for_order(order)
if pobj:
    # Check if source_type is changing - if yes, reset related data
    if pobj.source_type != src:
        _reset_pekerjaan_related_data(pobj)

    # ... update fields ...
```

---

## Scenarios Covered

### Scenario 1: User Changes ref_id (REF/REF_MOD)

**Before:**
1. Pekerjaan A dengan ref_id=10 (AHSP "Galian Tanah")
2. Volume sudah diisi: 100 m3
3. Jadwal sudah diatur: Minggu 1-2
4. Template AHSP sudah ada detail items

**User Action:** Ganti ref_id jadi 20 (AHSP "Timbunan Tanah")

**OLD Behavior (BUG):**
- ❌ Detail AHSP dari ref_id=10 masih ada (conflict!)
- ❌ Volume 100 m3 tetap ada (WRONG untuk Timbunan!)
- ❌ Jadwal Minggu 1-2 tetap ada
- ❌ detail_ready = True (WRONG!)

**NEW Behavior (FIXED):**
- ✅ Detail AHSP dari ref_id=10 DIHAPUS
- ✅ Detail baru dari ref_id=20 di-load
- ✅ Volume di-reset jadi NULL (user harus isi ulang)
- ✅ Jadwal dihapus (user harus atur ulang)
- ✅ detail_ready = False

### Scenario 2: User Changes from REF to CUSTOM

**Before:**
1. Pekerjaan A (source=REF, ref_id=10)
2. Volume: 50 m2
3. Template AHSP: auto-loaded dari referensi

**User Action:** Ganti jadi CUSTOM dengan uraian manual

**OLD Behavior (BUG):**
- ❌ Detail AHSP dari ref tetap ada
- ❌ Volume 50 m2 tetap ada (mungkin tidak cocok untuk custom!)
- ❌ detail_ready = True (SALAH, detail belum diisi untuk custom!)

**NEW Behavior (FIXED):**
- ✅ Detail AHSP dihapus SEMUA
- ✅ Volume di-reset jadi NULL
- ✅ Jadwal dihapus
- ✅ detail_ready = False
- ✅ User harus isi manual template AHSP untuk custom

### Scenario 3: User Changes from CUSTOM to REF

**Before:**
1. Pekerjaan A (source=CUSTOM)
2. Volume: 75 unit
3. Template AHSP: manual input (TK, BHN, ALT)
4. Jadwal: Minggu 5-10

**User Action:** Ganti jadi REF dengan ref_id=30

**OLD Behavior (BUG):**
- ❌ Detail manual dari CUSTOM masih ada (conflict dengan auto-load!)
- ❌ Volume 75 unit tetap ada
- ❌ Jadwal Minggu 5-10 tetap ada

**NEW Behavior (FIXED):**
- ✅ Detail manual dihapus SEMUA
- ✅ Detail baru auto-load dari ref_id=30
- ✅ Volume di-reset jadi NULL
- ✅ Jadwal dihapus
- ✅ detail_ready = False → akan jadi True setelah auto-load

### Scenario 4: User Deletes Pekerjaan

**Handled by Django CASCADE DELETE** (line 852)

```python
# Hapus pekerjaan yang tidak ada di payload
Pekerjaan.objects.filter(project=project).exclude(id__in=keep_all_p).delete()
```

Django automatically cascades deletion to related models with ForeignKey.

---

## Impact on User Experience

### Positive Changes:

1. **Clean State After Modification**
   - User mendapatkan fresh start setelah ganti pekerjaan
   - Tidak ada data "ghost" dari pekerjaan lama
   - Konsistensi data terjaga

2. **Predictable Behavior**
   - User tahu bahwa ganti pekerjaan = reset all
   - No confusion dari mixing old/new data

3. **Data Integrity**
   - Volume yang di-reset memaksa user isi ulang (prevent wrong volume)
   - Jadwal di-reset karena duration mungkin berubah
   - Template AHSP sesuai dengan referensi baru

### Trade-offs:

1. **User Must Re-enter Data**
   - Volume harus diisi ulang
   - Jadwal harus diatur ulang
   - Template AHSP (untuk CUSTOM) harus diisi manual lagi

2. **Recommendation for UI:**
   - Tambahkan confirmation dialog:
     ```
     "Mengubah pekerjaan akan menghapus semua data terkait:
     - Volume
     - Jadwal
     - Template AHSP
     Apakah Anda yakin?"
     ```
   - Show warning indicator jika pekerjaan punya volume/jadwal

---

## Logging

Function logs reset action for debugging:

```python
logger.info(
    f"Reset all related data for pekerjaan {pobj.id} (kode: {pobj.snapshot_kode})",
    extra={'project_id': project.id, 'pekerjaan_id': pobj.id}
)
```

**Log Output Example:**
```
INFO: Reset all related data for pekerjaan 123 (kode: CUST-001)
  extra: {'project_id': 1, 'pekerjaan_id': 123}
```

---

## Testing Recommendations

### Manual Testing:

**Test 1: Change REF ref_id**
1. Create pekerjaan with source=REF, ref_id=10
2. Fill volume, jadwal, verify template AHSP auto-loaded
3. Change ref_id to 20
4. **Verify:** Volume=NULL, Jadwal empty, Detail AHSP from ref_id=20

**Test 2: Change REF to CUSTOM**
1. Create pekerjaan with source=REF
2. Fill volume, jadwal
3. Change to CUSTOM with manual uraian
4. **Verify:** Volume=NULL, Jadwal empty, Detail AHSP empty, detail_ready=False

**Test 3: Change CUSTOM to REF**
1. Create pekerjaan with source=CUSTOM
2. Manually fill template AHSP, volume, jadwal
3. Change to REF with ref_id
4. **Verify:** Old detail deleted, new detail auto-loaded, volume=NULL, jadwal empty

**Test 4: REUSE case with source change**
1. Create pekerjaan at order=1 (REF)
2. Delete it, create new at same order=1 (CUSTOM)
3. **Verify:** Reset triggered, clean state

### Automated Testing:

Recommended test cases:
- test_modify_pekerjaan_resets_volume
- test_modify_pekerjaan_resets_jadwal
- test_modify_pekerjaan_resets_detail_ahsp
- test_modify_pekerjaan_resets_formula_state
- test_modify_pekerjaan_resets_detail_ready_flag

---

## Files Modified

**File:** `detail_project/views_api.py`

**Changes:**
1. Added `_reset_pekerjaan_related_data()` function (line 519-554)
2. Updated `_adopt_tmp_into()` to call reset (line 556-589)
3. Updated REF→CUSTOM conversion to call reset (line 707-731)
4. Updated REUSE case to check source change and reset (line 815-832)

**Lines Changed:** ~70 lines modified/added

---

## Backward Compatibility

**Breaking Change:** YES

Users yang sudah terbiasa dengan behavior lama (data tidak direset) akan terkejut bahwa data sekarang di-reset.

**Mitigation:**
1. Add UI confirmation dialog
2. Add release notes explaining new behavior
3. Consider adding "preserve volume" checkbox (optional)

**Database Migration:** NO

No database schema changes needed.

---

## Related Issues

This fix also resolves potential issues:
- Circular bundle detection now works correctly (old bundle details deleted)
- No more detail conflict when changing ref
- No more wrong volume calculation from old data
- Rekap consistency improved (no mixing old/new data)

---

## References

- User report: "input tidak bisa dimodifikasi pada kolom sumber"
- User requirement: "saat user modify/hapus pekerjaan, semua page terkait harus tereset"
- Related pages affected:
  - List Pekerjaan (modification trigger)
  - Template AHSP (detail reset)
  - Volume Pekerjaan (volume reset)
  - Jadwal (tahapan reset)
  - Rekap (recomputed with clean data)
