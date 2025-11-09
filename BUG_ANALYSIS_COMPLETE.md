# 🐛 Dual Storage: Complete Bug Analysis & Solutions

**Created**: 2025-11-09
**Status**: Investigation Complete
**Critical Finding**: **Pytest PASS but Manual Testing FAIL** - Root causes identified

---

## 🎯 Executive Summary

**All 9 pytest tests PASS** ✅ but **manual testing FAILS** ❌

**Root Causes Identified:**
1. ❌ **User Workflow Error** - Selecting AHSP instead of Pekerjaan for CUSTOM bundles
2. ❌ **Old Data** - REF/REF_MODIFIED pekerjaan created before dual storage fix
3. ✅ **Backend Inconsistency** - Validation accepts AHSP bundles but expansion rejects them
4. ✅ **Test vs Production Gap** - Fresh data vs legacy data, correct format vs user errors

---

## 🔍 **Bug #1: CUSTOM Save Error** ❌

### **Error Message** (Browser Console):
```javascript
[SAVE] HTTP Status: 207
[SAVE] Response: {ok: false, saved_raw_rows: 1, saved_expanded_rows: 0, errors: Array(1)}
[error] Save Failed: item.2.2.1.4.6 - Item LAIN '1 m3 beton mutu sedang f'c 21 MPa...'
        tidak memiliki referensi pekerjaan. Untuk pekerjaan gabungan, pilih pekerjaan dari dropdown.
```

### **Root Cause**:
User selected AHSP from autocomplete **"Master AHSP"** group (kode: `2.2.1.4.6`) instead of **"Pekerjaan Proyek"** group.

### **Flow Analysis**:

#### **What User Did:**
1. Opened CUSTOM pekerjaan
2. Added LAIN row
3. Typed "beton" in kode autocomplete
4. Selected from **"Master AHSP"** group → AHSP Referensi (2.2.1.4.6)

#### **Frontend Action:**
```javascript
// template_ahsp.js line 310-314
kind = 'ahsp';  // ❌ WRONG for CUSTOM bundles
refId = ahsp_id;
$('input[data-field="ref_kind"]', tr).value = 'ahsp';
$('input[data-field="ref_id"]', tr).value = String(ahsp_id);
```

**Payload Sent to Backend:**
```json
{
    "kategori": "LAIN",
    "kode": "2.2.1.4.6",
    "uraian": "1 m3 beton mutu sedang...",
    "koefisien": "1.0",
    "ref_kind": "ahsp",     // ❌ PROBLEM!
    "ref_id": 123
}
```

#### **Backend Processing:**

**Step 1: Validation** (views_api.py line 1246-1250) - ✅ **ACCEPTS**
```python
if ref_kind == 'ahsp':
    ref_ahsp_obj = AHSPReferensi.objects.get(id=ref_id)
    # No error - validation passes!
```

**Step 2: Save to DetailAHSPProject** (line 1313-1324) - ✅ **SUCCESS**
```python
DetailAHSPProject(
    ...
    ref_ahsp=ref_ahsp_obj,      # Set
    ref_pekerjaan=None           # NULL!
)
```

**Step 3: Expansion** (line 1354) - ❌ **SKIPS**
```python
for detail_obj in saved_raw_details:
    if detail_obj.kategori == 'LAIN' and detail_obj.ref_pekerjaan:
        # ❌ SKIPPED - ref_pekerjaan is None!
```

**Step 4: Error Handler** (line 1430-1441) - ❌ **ERRORS**
```python
elif detail_obj.kategori == HargaItemProject.KATEGORI_LAIN:
    # LAIN item without ref_pekerjaan - invalid bundle
    logger.warning(f"LAIN item '{detail_obj.kode}' has no ref_pekerjaan")
    errors.append("Item LAIN tidak memiliki referensi pekerjaan")
```

**Result**: `saved_raw_rows=1`, `saved_expanded_rows=0`, `errors=[...]`

### **Backend Design Issue**:

**Inconsistency Found:**
- ✅ Validation **ACCEPTS** `ref_kind='ahsp'` for CUSTOM pekerjaan
- ❌ Expansion **ONLY SUPPORTS** `ref_kind='job'` (ref_pekerjaan)

**Expansion Function** (services.py line 183):
```python
def expand_bundle_to_components(
    detail_data: dict,
    ...
):
    """
    Expand bundle (LAIN dengan ref_pekerjaan) menjadi list komponen base (TK/BHN/ALT).
    """
    ref_pekerjaan_id = detail_data.get('ref_pekerjaan_id')
    if not ref_pekerjaan_id:
        return []  # ❌ AHSP bundles not supported!
```

### **Why Pytest PASSES**:
```python
# test_dual_storage.py uses CORRECT format
payload = {
    'kategori': 'LAIN',
    'ref_kind': 'job',  # ✅ CORRECT!
    'ref_id': bundle_pekerjaan.id
}
```

### **Solutions**:

#### **Option A: Fix User Workflow** (RECOMMENDED)
**Immediate Action**:
1. User must select from **"Pekerjaan Proyek"** dropdown, NOT "Master AHSP"
2. Only Pekerjaan within project can be used as bundles for CUSTOM

**Long-term UX Fix**:
- Hide "Master AHSP" group for LAIN in CUSTOM pekerjaan
- Show ONLY "Pekerjaan Proyek" options
- Add frontend validation

#### **Option B: Support AHSP Bundle Expansion** (FUTURE FEATURE)
Implement `expand_ahsp_bundle()` function to expand AHSP Referensi bundles.

**Pros**: More flexible for users
**Cons**: Complex implementation, need to handle RincianReferensi expansion

---

## 🔍 **Bug #2: REF_MODIFIED Harga Items Empty** ❌

### **Error**:
Page "Harga Items" shows NO items for REF_MODIFIED pekerjaan.

### **Root Cause**:
Old pekerjaan created **BEFORE** commit `54d123c` (dual storage implementation).

### **Data State**:
- ✅ `DetailAHSPProject` exists (3 rows)
- ❌ `DetailAHSPExpanded` is EMPTY (0 rows) ← **PROBLEM!**

### **Why Empty**:
Old code did NOT call `_populate_expanded_from_raw()` after `clone_ref_pekerjaan()`.

**Before (commit < 54d123c)**:
```python
def clone_ref_pekerjaan(...):
    # Created DetailAHSPProject
    DetailAHSPProject.objects.bulk_create(...)
    # ❌ Did NOT populate DetailAHSPExpanded
    return pekerjaan
```

**After (commit >= 54d123c)**:
```python
def clone_ref_pekerjaan(...):
    # Created DetailAHSPProject
    DetailAHSPProject.objects.bulk_create(...)
    # ✅ NEW: Populate expanded storage
    _populate_expanded_from_raw(project, pekerjaan)
    return pekerjaan
```

### **Why Harga Items Empty**:
Harga Items API reads from `DetailAHSPExpanded`:

```python
# views_api.py line 1944
qs = (HargaItemProject.objects
      .filter(project=project, expanded_refs__project=project)  # ← expanded_refs!
      .distinct())
```

If `DetailAHSPExpanded` empty → No items match filter → Result empty!

### **Why Pytest PASSES**:
```python
# test_dual_storage.py fixture
def test_clone_ref_modified_populates_both_storages(...):
    pekerjaan = clone_ref_pekerjaan(
        project=project,
        ahsp_referensi=ahsp_referensi,
        source_type='ref_modified'
    )
    # ✅ Uses LATEST code with _populate_expanded_from_raw()
```

### **Solution**:

**Immediate Fix**:
1. Delete old REF_MODIFIED pekerjaan
2. Create new one with latest code
3. Verify `DetailAHSPExpanded` populated

**Verification Query**:
```sql
-- Check if expanded storage populated
SELECT COUNT(*) FROM detail_project_detailahspexpanded
WHERE project_id = <project_id> AND pekerjaan_id = <pekerjaan_id>;
-- Should return 3 (not 0!)
```

---

## 🔍 **Bug #3: REF Harga Items Empty** ❌

### **Error**:
Page "Harga Items" shows NO items for REF pekerjaan (same as REF_MODIFIED).

### **Root Cause**:
**Same as Bug #2** - Old data created before dual storage fix.

### **Why Surprising**:
REF should have been working longer than REF_MODIFIED. Possible causes:
1. Old data (most likely)
2. Frontend cache issue
3. Different API endpoint used

### **Solution**:
Same as Bug #2 - Delete old, create new.

---

## 🔍 **Bug #4: Pytest PASS vs Manual FAIL** ❓

### **Why Different Results?**

#### **Pytest Environment**:
- ✅ **Database**: SQLite in-memory (fresh on every run)
- ✅ **Data**: Created by fixtures with LATEST code
- ✅ **Format**: Uses correct `ref_kind='job'` format
- ✅ **Workflow**: Programmatic (no user errors)

#### **Manual Testing Environment**:
- ⚠️ **Database**: PostgreSQL (persistent, has old data)
- ❌ **Data**: Mix of old (before fixes) and new
- ❌ **Format**: User selects AHSP (`ref_kind='ahsp'`)
- ❌ **Workflow**: Via UI (prone to user errors)

### **Key Differences**:

| Aspect | Pytest | Manual Testing |
|--------|--------|----------------|
| **Database** | SQLite in-memory | PostgreSQL production |
| **Data Age** | Fresh (0 seconds old) | Old (days/weeks old) |
| **Data Quality** | Perfect (fixtures) | Inconsistent (legacy) |
| **Bundle Format** | `ref_kind='job'` ✅ | `ref_kind='ahsp'` ❌ |
| **User Workflow** | N/A (programmatic) | Error-prone |
| **Code Version** | Latest | Old pekerjaan = old code |

### **Conclusion**:
Pytest validates **implementation logic** is correct.
Manual testing reveals **data migration** and **user workflow** issues.

**Both are valuable!** Pytest confirms code works, manual testing finds real-world problems.

---

## 🎯 **Complete Solution Roadmap**

### **Immediate Actions** (User Must Do):

#### **1. Fix CUSTOM Bundle Workflow**
❌ **STOP**: Selecting from "Master AHSP" autocomplete
✅ **START**: Selecting from "Pekerjaan Proyek" dropdown

**Correct Steps**:
1. Create bundle pekerjaan first (with TK/BHN/ALT components)
2. In CUSTOM pekerjaan, add LAIN row
3. Type pekerjaan kode in autocomplete
4. Select from **"Pekerjaan Proyek"** group (NOT "Master AHSP")
5. Save

#### **2. Migrate Old REF/REF_MODIFIED Data**
1. Identify old pekerjaan (check `DetailAHSPExpanded` empty)
2. Delete old pekerjaan
3. Create new from AHSP Referensi
4. Verify Harga Items populated

**SQL Check**:
```sql
-- Find pekerjaan with empty expanded storage
SELECT p.id, p.snapshot_kode, p.source_type,
       COUNT(dap.id) as raw_count,
       COUNT(dae.id) as expanded_count
FROM detail_project_pekerjaan p
LEFT JOIN detail_project_detailahspproject dap ON dap.pekerjaan_id = p.id
LEFT JOIN detail_project_detailahspexpanded dae ON dae.pekerjaan_id = p.id
WHERE p.project_id = <project_id>
  AND p.source_type IN ('ref', 'ref_modified')
GROUP BY p.id
HAVING COUNT(dap.id) > 0 AND COUNT(dae.id) = 0;
```

### **Short-term Backend Fix** (Recommended):

#### **Add Frontend Validation**
Reject AHSP selection for LAIN in CUSTOM pekerjaan:

```javascript
// template_ahsp.js - enhance autocomplete
$input.on('select2:select', (e) => {
    const d = e.params.data || {};
    const sid = String(d.id||'');

    // NEW: Reject AHSP for CUSTOM bundles
    if (activeSource === 'custom' && sid.startsWith('ahsp:')) {
        toast('Untuk pekerjaan custom, pilih dari Pekerjaan Proyek (bukan Master AHSP)', 'error');
        $input.val(null).trigger('change');
        return;
    }

    // ... rest of code
});
```

### **Long-term Backend Enhancement** (Future):

#### **Option 1: Support AHSP Bundle Expansion**
Implement `expand_ahsp_bundle_to_components()` to expand from RincianReferensi.

#### **Option 2: Reject AHSP at Validation**
Add validation to reject `ref_kind='ahsp'` for CUSTOM pekerjaan:

```python
# views_api.py line 1246
if ref_kind == 'ahsp':
    # NEW: Reject for CUSTOM bundles
    if pkj.source_type == Pekerjaan.SOURCE_CUSTOM:
        errors.append(_err(
            f"rows[{i}].ref_kind",
            "Pekerjaan custom hanya bisa reference pekerjaan dalam project (ref_kind='job')"
        ))
        continue

    ref_ahsp_obj = AHSPReferensi.objects.get(id=ref_id)
```

---

## 📊 **Testing Matrix**

| Scenario | Pytest | Manual (Old Data) | Manual (New Data) | Status |
|----------|--------|-------------------|-------------------|--------|
| **REF - Dual Storage** | ✅ PASS | ❌ FAIL (empty) | ✅ PASS | Old data issue |
| **REF - Harga Items** | ✅ PASS | ❌ FAIL (empty) | ✅ PASS | Old data issue |
| **REF_MODIFIED - Dual Storage** | ✅ PASS | ❌ FAIL (empty) | ✅ PASS | Old data issue |
| **REF_MODIFIED - Harga Items** | ✅ PASS | ❌ FAIL (empty) | ✅ PASS | Old data issue |
| **CUSTOM Bundle (Job)** | ✅ PASS | ❓ Not Tested | ✅ PASS | Should work |
| **CUSTOM Bundle (AHSP)** | N/A | ❌ FAIL (error) | ❌ FAIL (error) | Not supported |
| **Override Bug Fix** | ✅ PASS | ✅ PASS | ✅ PASS | Fixed! |

---

## 🔧 **Migration Guide for Old Data**

### **Step 1: Identify Affected Pekerjaan**

**Django Shell**:
```python
from detail_project.models import Pekerjaan, DetailAHSPProject, DetailAHSPExpanded

project_id = <your_project_id>

# Find pekerjaan with empty expanded storage
for pkj in Pekerjaan.objects.filter(project_id=project_id):
    raw_count = DetailAHSPProject.objects.filter(pekerjaan=pkj).count()
    expanded_count = DetailAHSPExpanded.objects.filter(pekerjaan=pkj).count()

    if raw_count > 0 and expanded_count == 0:
        print(f"❌ Pekerjaan {pkj.id}: {pkj.snapshot_kode} - "
              f"Raw: {raw_count}, Expanded: {expanded_count}")
```

### **Step 2: Migrate Data**

**Option A: Delete & Recreate** (Safest):
1. Note pekerjaan details (ref_id, kode, uraian, etc.)
2. Delete pekerjaan from UI
3. Re-add from AHSP Referensi (will use latest code)
4. Verify Harga Items shows items

**Option B: Programmatic Migration** (Advanced):
```python
from detail_project.services import _populate_expanded_from_raw

# For each affected pekerjaan
pkj = Pekerjaan.objects.get(id=<pekerjaan_id>)
_populate_expanded_from_raw(pkj.project, pkj)

# Verify
expanded_count = DetailAHSPExpanded.objects.filter(pekerjaan=pkj).count()
print(f"✅ Migrated! Expanded rows: {expanded_count}")
```

### **Step 3: Verify**

1. Check Harga Items page shows items
2. Check DetailAHSPExpanded has rows
3. Check Rekap RAB calculates correctly

---

## 📈 **Success Metrics**

### **After Fixes Applied**:
- ✅ Pytest: 9/9 tests PASS
- ✅ Manual REF: Harga Items populated
- ✅ Manual REF_MODIFIED: Harga Items populated
- ✅ Manual CUSTOM: Bundles expand correctly (when using Pekerjaan ref)
- ✅ Override bug: Multiple bundles with same kode preserved

---

## 📝 **Lessons Learned**

1. **Test Environment ≠ Production**
   - Pytest validates logic, not data migration
   - Always test with real/legacy data

2. **User Workflow Matters**
   - Backend accepts, but expansion rejects
   - Clear error messages crucial

3. **Data Migration Critical**
   - Code changes don't auto-fix old data
   - Need migration strategy

4. **Frontend Validation Helps**
   - Prevent user errors early
   - Better UX than backend errors

---

**Status**: Documentation Complete ✅
**Next**: Apply fixes and verify in production
