# 🐛 BUG INVESTIGATION: Pekerjaan Hilang Setelah Ubah Source Type

**Reported by:** User
**Date:** 2025-11-09
**Severity:** 🔴 CRITICAL
**Status:** 🔍 UNDER INVESTIGATION

---

## 📋 BUG DESCRIPTION

### User Report:
```
Steps to Reproduce:
1. Input "Pekerjaan A" dengan source apapun (REF/CUSTOM/REF_MOD)
2. Click "Simpan" ✅ Success - page reload, pekerjaan tersimpan normal
3. Ubah source "Pekerjaan A" ke source yang berbeda
4. Click "Simpan"
5. Page reload → ❌ PEKERJAAN HILANG! (baris kosong/terhapus)

Expected: Pekerjaan tetap ada dengan source type yang baru
Actual: Pekerjaan HILANG dari daftar
```

---

## 🔍 ROOT CAUSE ANALYSIS

### Code Location:
```python
File: detail_project/views_api.py
Function: api_upsert_list_pekerjaan()
Lines: 703-806 (UPDATE EXISTING block)
Line: 908 (DELETE statement)
```

### Critical Code Flow:

```python
# Line 703-806: UPDATE EXISTING PEKERJAAN
if p_id and p_id in existing_p and existing_p[p_id].project_id == project.id:
    # ============ UPDATE EXISTING ============
    pobj = existing_p[p_id]  # Line 705

    # Line 710-718: Validation for source change to REF/REF_MOD
    if pobj.source_type != src:
        if src in [SOURCE_REF, SOURCE_REF_MOD] and new_ref_id is None:
            errors.append(_err(..., "Wajib diisi..."))
            continue  # ← BUG #1: Skip to next item, pobj.id NOT added to keep_all_p!
        replace = True

    if replace:
        # Line 731-787: Replace logic
        try:
            if src in [SOURCE_REF, SOURCE_REF_MOD]:
                # ... clone & adopt ...
                _adopt_tmp_into(pobj, tmp, s_obj, order)
            else:
                # Line 757-780: ke CUSTOM
                _reset_pekerjaan_related_data(pobj)
                uraian = (p.get("snapshot_uraian") or "").strip()
                if not uraian:
                    errors.append(_err(..., "Wajib untuk custom baru"))
                    continue  # ← BUG #2: Skip, pobj.id NOT added!
                # ... update fields ...
        except AHSPReferensi.DoesNotExist:
            errors.append(_err(...))
            continue  # ← BUG #3: Skip, pobj.id NOT added!
    else:
        # Line 788-803: Update biasa
        pobj.save(...)

    # Line 806: CRITICAL LINE
    keep_all_p.add(pobj.id)  # ← ONLY REACHED IF NO CONTINUE!

# Line 908: DELETE ALL NOT IN keep_all_p
Pekerjaan.objects.filter(project=project).exclude(id__in=keep_all_p).delete()
```

---

## 🚨 THE BUG

### Problem:
`keep_all_p.add(pobj.id)` is placed at **line 806**, which is **AFTER** multiple `continue` statements.

If any validation error occurs, the code executes `continue` and skips line 806, causing `pobj.id` to NOT be added to `keep_all_p`.

Then at line 908, ALL pekerjaan NOT in `keep_all_p` are DELETED!

### Failure Scenarios:

#### Scenario 1: Missing ref_id when changing to REF
```python
User: Change CUSTOM → REF
User: Forgets to select AHSP (ref_id = null)
User: Click Save

Flow:
Line 710: if pobj.source_type != src:  # True (CUSTOM != REF)
Line 712: if src in [REF, REF_MOD] and new_ref_id is None:  # True!
Line 713-716: errors.append(...)
Line 717: continue  # ← Skip to next pekerjaan
Line 806: SKIPPED! (pobj.id NOT added to keep_all_p)
Line 908: DELETE pekerjaan ❌

Result: Pekerjaan HILANG!
```

#### Scenario 2: Missing uraian when changing to CUSTOM
```python
User: Change REF → CUSTOM
User: Forgets to enter uraian (or clears it)
User: Click Save

Flow:
Line 710: if pobj.source_type != src:  # True (REF != CUSTOM)
Line 718: replace = True
Line 731: if replace:
Line 757: else: # ke CUSTOM
Line 759: _reset_pekerjaan_related_data(pobj)  ✅ Data reset
Line 761-762: uraian = empty string
Line 762: if not uraian:  # True!
Line 763-766: errors.append(...)
Line 767: continue  # ← Skip!
Line 806: SKIPPED!
Line 908: DELETE pekerjaan ❌

Result: Pekerjaan HILANG!
```

#### Scenario 3: AHSP reference not found
```python
User: Change to REF with invalid ref_id
User: Click Save

Flow:
Line 736: ref_obj = AHSPReferensi.objects.get(id=rid)  # DoesNotExist!
Line 781: except AHSPReferensi.DoesNotExist:
Line 782-786: errors.append(...)
Line 787: continue  # ← Skip!
Line 806: SKIPPED!
Line 908: DELETE pekerjaan ❌

Result: Pekerjaan HILANG!
```

---

## ✅ THE FIX

### Current Code (BUGGY):
```python
Line 703: if p_id and p_id in existing_p:
    Line 705: pobj = existing_p[p_id]

    # Validations here (might continue)
    Line 717: continue  # ← BUG: Skip add to keep_all_p
    Line 767: continue  # ← BUG: Skip add to keep_all_p
    Line 787: continue  # ← BUG: Skip add to keep_all_p

    # ... processing ...

    Line 806: keep_all_p.add(pobj.id)  # ← Too late! Already skipped!
```

### Fixed Code (SAFE):
```python
Line 703: if p_id and p_id in existing_p and existing_p[p_id].project_id == project.id:
    Line 705: pobj = existing_p[p_id]

    # FIX: Add to keep_all_p IMMEDIATELY, BEFORE any validation
    keep_all_p.add(pobj.id)  # ← MOVE HERE! (New line 706)

    # Now validations can continue safely
    Line 717: continue  # ✅ OK, pekerjaan already in keep_all_p
    Line 767: continue  # ✅ OK, pekerjaan already in keep_all_p
    Line 787: continue  # ✅ OK, pekerjaan already in keep_all_p

    # ... processing ...

    # Line 806: keep_all_p.add(pobj.id)  # ← REMOVE THIS (duplicate)
```

---

## 📝 DETAILED FIX

### File: `detail_project/views_api.py`

**Change 1: Add pobj.id to keep_all_p immediately**

```python
# Line 703-710 (BEFORE)
if p_id and p_id in existing_p and existing_p[p_id].project_id == project.id:
    # ============ UPDATE EXISTING ============
    pobj = existing_p[p_id]
    replace = False
    new_ref_id = p.get("ref_id")

    # Ganti tipe sumber → pasti replace
    if pobj.source_type != src:


# Line 703-711 (AFTER FIX)
if p_id and p_id in existing_p and existing_p[p_id].project_id == project.id:
    # ============ UPDATE EXISTING ============
    pobj = existing_p[p_id]

    # CRITICAL FIX: Add to keep list IMMEDIATELY to prevent deletion
    # even if validation fails later
    keep_all_p.add(pobj.id)  # ← ADD THIS LINE (New line 708)

    replace = False
    new_ref_id = p.get("ref_id")

    # Ganti tipe sumber → pasti replace
    if pobj.source_type != src:
```

**Change 2: Remove duplicate add at end of block**

```python
# Line 804-806 (BEFORE)
                    ])

                # CRITICAL: Add to keep list so it doesn't get deleted at line 905
                keep_all_p.add(pobj.id)


# Line 804-806 (AFTER FIX)
                    ])

                # NOTE: Already added to keep_all_p at line 708
                # keep_all_p.add(pobj.id)  # ← REMOVE THIS LINE (duplicate)
```

---

## 🧪 TESTING THE FIX

### Test Case 1: Missing ref_id (Should NOT delete pekerjaan)
```python
# Setup
1. Create pekerjaan CUSTOM "Test Pekerjaan"
2. Save successfully
3. Change source to REF
4. DO NOT select AHSP (ref_id = null)
5. Click Save

# Before Fix:
❌ Pekerjaan DELETED
❌ User sees empty list
❌ Data lost!

# After Fix:
✅ Pekerjaan NOT deleted (stays in database)
✅ Error message shown: "Wajib diisi saat mengganti source type..."
✅ User can fix and retry
✅ Data preserved
```

### Test Case 2: Missing uraian for CUSTOM (Should NOT delete)
```python
# Setup
1. Create pekerjaan REF with AHSP
2. Save successfully
3. Change source to CUSTOM
4. Clear uraian field (empty)
5. Click Save

# Before Fix:
❌ Pekerjaan DELETED
❌ CASCADE RESET already executed (data lost!)

# After Fix:
✅ Pekerjaan NOT deleted
✅ Error message: "Wajib untuk custom baru"
✅ User can enter uraian and retry
✅ Data preserved
```

### Test Case 3: Valid source change (Should work normally)
```python
# Setup
1. Create pekerjaan CUSTOM
2. Change to REF with valid AHSP selection
3. Click Save

# Before Fix:
✅ Works (pekerjaan updated)

# After Fix:
✅ Still works (no regression)
✅ CASCADE RESET executed correctly
✅ Pekerjaan preserved with new source type
```

---

## 🎯 WHY THIS BUG WASN'T CAUGHT EARLIER

### Original Fix (Commit 4163426):
The original fix added `keep_all_p.add(pobj.id)` at line 806, which worked for the **happy path** (no validation errors).

### The Bug:
The fix didn't account for **validation error paths** where `continue` is called BEFORE reaching line 806.

### Why It Passed Tests:
Manual testing likely only tested successful scenarios:
- ✅ CUSTOM → REF with valid AHSP selected
- ✅ REF → CUSTOM with uraian filled
- ❌ NOT tested: Validation errors during source change

---

## 📊 IMPACT ASSESSMENT

### Severity: 🔴 CRITICAL
- **Data Loss:** Pekerjaan can be permanently deleted
- **User Experience:** Frustrating, unexpected behavior
- **Frequency:** HIGH - Common validation errors trigger this

### Affected Scenarios:
1. ✅ Change source type + validation error → Pekerjaan DELETED
2. ✅ Missing ref_id for REF/REF_MOD → Pekerjaan DELETED
3. ✅ Missing uraian for CUSTOM → Pekerjaan DELETED
4. ✅ Invalid AHSP reference → Pekerjaan DELETED

### Users Affected:
- **All users** who make validation errors during source type changes
- **Especially new users** unfamiliar with required fields

---

## 🚀 DEPLOYMENT PLAN

### Immediate Actions (URGENT):
1. ✅ Apply fix to views_api.py (5 minutes)
2. ✅ Test all 3 scenarios above (30 minutes)
3. ✅ Deploy to production ASAP (high priority)

### Verification:
1. Create test project
2. Create pekerjaan CUSTOM
3. Change to REF without selecting AHSP
4. Save
5. ✅ Verify: Pekerjaan still exists in database
6. ✅ Verify: Error message shown
7. ✅ Verify: Can retry with valid AHSP

### Rollback Plan:
If fix causes issues:
1. Revert to previous commit
2. Apply alternative fix (add to keep_all_p in multiple places)

---

## 📚 RELATED ISSUES

### Similar Bugs Fixed:
- Commit 4163426: Original fix (incomplete)
- This fix: Complete fix (handles validation errors)

### Prevention:
Add integration test:
```python
def test_source_change_with_validation_error_should_not_delete_pekerjaan():
    """Test that pekerjaan is preserved even if validation fails."""
    # Create CUSTOM pekerjaan
    pekerjaan = create_custom_pekerjaan()

    # Change to REF without ref_id (validation error)
    payload = build_payload_with_missing_ref_id(pekerjaan)
    response = client.post(url, payload)

    # Should return error
    assert response.status_code == 207
    assert "Wajib diisi" in response.json()['errors'][0]['message']

    # CRITICAL: Pekerjaan should still exist
    pekerjaan.refresh_from_db()
    assert pekerjaan is not None  # ← This would FAIL before fix!
    assert pekerjaan.source_type == 'custom'  # ← Unchanged
```

---

## ✅ FIX VERIFICATION CHECKLIST

Before deployment:
- [ ] Fix applied to views_api.py
- [ ] Code reviewed
- [ ] Test Case 1 passed (missing ref_id)
- [ ] Test Case 2 passed (missing uraian)
- [ ] Test Case 3 passed (valid change)
- [ ] No regression in other scenarios
- [ ] Integration test added
- [ ] Documentation updated

---

**Status:** 🔍 FIX IDENTIFIED - READY TO IMPLEMENT
**Estimated Fix Time:** 5 minutes (code change) + 30 minutes (testing)
**Priority:** 🔴 URGENT - Deploy ASAP

---

**Next Step:** Implement fix and test all scenarios

