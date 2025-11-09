# 🐛 BUG: Source Type Changes Not Persisting

**Date:** 2025-11-09
**Status:** 🔴 CRITICAL - Root cause identified
**Affects:** CUSTOM→REF, CUSTOM→REF_MODIFIED, REF_MODIFIED→REF transitions

---

## 📋 Bug Summary

When user changes source type from CUSTOM to REF/REF_MODIFIED (or REF_MODIFIED to REF), the changes appear to succeed but are reverted after page reload. The system shows "✅ Perubahan tersimpan" (Changes saved) but values return to their previous state.

### Failing Transitions
- ❌ CUSTOM → REF
- ❌ CUSTOM → REF_MODIFIED
- ❌ REF_MODIFIED → REF

### Working Transitions
- ✅ REF → REF_MODIFIED
- ✅ REF → CUSTOM
- ✅ CUSTOM → CUSTOM (edit)
- ✅ REF → REF (different ref_id)

---

## 🔍 Root Cause Analysis

### The Bug Has TWO Parts

#### **Part 1: Frontend Logic Error - `data-ref-id` Update Timing** 🔴 CRITICAL

**File:** `detail_project/static/detail_project/js/list_pekerjaan.js`

**The Problem:**

When user selects a reference, the `select2:select` event **immediately** updates `row.dataset.refId` to the new value. Later, when building the save payload, the code checks if ref_id "changed" by comparing the current dataset value with the current select value - but they're now the SAME because dataset was already updated!

**Code Flow:**

1. **User changes CUSTOM → REF** (line 795-837: `syncFields()`)
   - Source dropdown changes to 'ref'
   - Ref dropdown is enabled
   - `data-ref-id` not yet set (pekerjaan was CUSTOM before, no ref)

2. **User selects ref from dropdown** (e.g., ref_id = 123)
   - `select2:select` event fires (line 741-756)
   - **Line 743:** `row.dataset.refId = String(v)` ← Sets `data-ref-id="123"`

3. **User clicks Save** (line 1233-1375: `handleSave()`)
   - **Line 1283-1288:** Reads select value: `refRaw = 123`
   - **Line 1301:** Converts to number: `refIdNum = 123`
   - **Line 1317:** Reads from dataset: `originalRefId = "123"` ← Already updated!
   - **Line 1318:** Calculates: `isRefChanged = (123 != null) && ('123' !== '123')` = **false** ❌
   - **Line 1335:** Check condition: `if (!existingId || isRefChanged)`
     - `existingId = true` (pekerjaan exists in DB)
     - `isRefChanged = false`
     - Result: `if (!true || false)` = **false**
   - **Line 1335:** `p.ref_id = refIdNum` is **SKIPPED** ❌

4. **Payload sent to backend:**
   ```json
   {
     "id": 456,
     "source_type": "ref",
     // ref_id is MISSING! ❌
     "ordering_index": 1
   }
   ```

**Relevant Code:**

```javascript
// list_pekerjaan.js:741-743 - Sets dataset immediately
$sel.on('select2:select', function () {
    const v = $sel.val();
    if (v) row.dataset.refId = String(v);  // ← BUG: Sets immediately!
    // ...
});

// list_pekerjaan.js:1317-1318 - Compares same values
const originalRefId = (tr.dataset.refId ?? null);  // ← Already updated!
const isRefChanged  = (refIdNum != null) && (String(refIdNum) !== String(originalRefId ?? ''));

// list_pekerjaan.js:1334-1336 - Conditional send
} else { // 'ref'
    if (!existingId || isRefChanged) p.ref_id = refIdNum;  // ← SKIPPED!
}
```

---

#### **Part 2: Frontend Error Handling Missing** 🟡 MAJOR

**File:** `detail_project/static/detail_project/js/list_pekerjaan.js`

**The Problem:**

When backend validation fails, it returns status 207 (partial success) with an errors array. The frontend incorrectly treats this as success and shows "✅ Perubahan tersimpan" without checking for errors.

**Code Flow:**

5. **Backend receives payload** (`views_api.py:437-922`)
   - **Line 715:** Detects source_type change: `if pobj.source_type != src:` → `replace = True`
   - **Line 717-722:** Validation checks ref_id:
     ```python
     if src in [Pekerjaan.SOURCE_REF, Pekerjaan.SOURCE_REF_MOD] and new_ref_id is None:
         errors.append(_err(
             f"klasifikasi[{ki}].sub[{si}].pekerjaan[{pi}].ref_id",
             "Wajib diisi saat mengganti source type ke ref/ref_modified"
         ))
         continue  # ← Skip processing, don't modify pekerjaan
     ```
   - Pekerjaan is preserved (line 709: `keep_all_p.add(pobj.id)`) but NOT modified
   - **Line 915-922:** Returns status 207 with errors array:
     ```python
     status = 200 if not errors else 207
     return JsonResponse({"ok": status == 200, "errors": errors, ...}, status=status)
     ```

6. **Frontend receives response** (`list_pekerjaan.js:1358-1374`)
   - **Line 1359-1366:** No error checking! Treats 207 as success:
     ```javascript
     await jfetch(`/.../${projectId}/list-pekerjaan/upsert/`, {...});
     alert('✅ Perubahan tersimpan.');  // ← Shows success even with errors!
     await reloadAfterSave();
     ```
   - **Line 1377:** Reloads page from database
   - Database still has old values (save was rejected)
   - User sees reverted changes and thinks "changes didn't persist"

**Relevant Code:**

```javascript
// list_pekerjaan.js:1358-1366 - No error checking
try {
    await jfetch(`/detail_project/api/project/${projectId}/list-pekerjaan/upsert/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    alert('✅ Perubahan tersimpan.');  // ← BUG: No response validation!
    tbAnnounce && (tbAnnounce.textContent = 'Perubahan tersimpan');
    await reloadAfterSave();
} catch (e) {
    // Only catches network/parse errors, not validation errors
    alert(`❌ Gagal simpan...`);
}
```

---

## 🎯 Why Some Transitions Work

### ✅ REF → CUSTOM (Works)
- Backend takes different code path (line 761-785: in-place update)
- Doesn't require ref_id in payload (sets `pobj.ref = None`)
- No validation that would fail

### ✅ REF → REF_MODIFIED (Works - User likely changing ref)
**Hypothesis:** User is selecting a DIFFERENT ref when testing this transition:
- Old ref: ref_id = 100
- New ref: ref_id = 123
- `originalRefId` gets updated to "123" on select2:select
- But `isRefChanged` still false: ('123' !== '123') = false
- **Same bug should occur!**

**Alternative explanation:** User might not be saving immediately, or testing with new pekerjaan (no existingId).

---

## 💡 Proposed Fixes

### Fix 1: Store Original State on Page Load 🎯 RECOMMENDED

**File:** `list_pekerjaan.js`

**Change 1a:** Store original values on page load (line ~643)

```javascript
// BEFORE
if (ref_id) row.dataset.refId = String(ref_id);

// AFTER
if (ref_id) {
    row.dataset.refId = String(ref_id);
    row.dataset.originalRefId = String(ref_id);  // ← NEW: Store original
}
row.dataset.originalSourceType = mode || 'ref';  // ← NEW: Store original source
```

**Change 1b:** Update comparison logic (line 1317-1318)

```javascript
// BEFORE
const originalRefId = (tr.dataset.refId ?? null);
const isRefChanged  = (refIdNum != null) && (String(refIdNum) !== String(originalRefId ?? ''));

// AFTER
const originalRefId = (tr.dataset.originalRefId ?? null);  // ← Use originalRefId, not current
const originalSourceType = (tr.dataset.originalSourceType ?? 'custom');
const isRefChanged  = (refIdNum != null) && (String(refIdNum) !== String(originalRefId ?? ''));
```

**Change 1c:** Handle source type changes (line 1334-1336)

```javascript
// BEFORE
} else { // 'ref'
    if (!existingId || isRefChanged) p.ref_id = refIdNum;
}

// AFTER
} else { // 'ref'
    // Always send ref_id if:
    // 1. New pekerjaan (!existingId)
    // 2. ref_id changed (isRefChanged)
    // 3. Source type changed (originalSourceType !== src)
    if (!existingId || isRefChanged || originalSourceType !== src) {
        p.ref_id = refIdNum;
    }
}
```

**Change 1d:** Same for ref_modified (line 1330-1333)

```javascript
// BEFORE
} else if (src === 'ref_modified') {
    if (!existingId || isRefChanged) p.ref_id = refIdNum;
    if (uraian) p.snapshot_uraian = uraian;
    if (satuan) p.snapshot_satuan = satuan;

// AFTER
} else if (src === 'ref_modified') {
    if (!existingId || isRefChanged || originalSourceType !== src) {
        p.ref_id = refIdNum;
    }
    if (uraian) p.snapshot_uraian = uraian;
    if (satuan) p.snapshot_satuan = satuan;
```

**Change 1e:** Reset original values after successful save (line 1377)

```javascript
// AFTER reloadAfterSave(), original values are reset naturally
// because loadTree() will set new dataset.original* values
```

---

### Fix 2: Add Error Response Handling 🎯 CRITICAL

**File:** `list_pekerjaan.js`

**Change 2:** Check response for errors (line 1358-1374)

```javascript
// BEFORE
try {
    await jfetch(`/detail_project/api/project/${projectId}/list-pekerjaan/upsert/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    alert('✅ Perubahan tersimpan.');
    tbAnnounce && (tbAnnounce.textContent = 'Perubahan tersimpan');
    await reloadAfterSave();

// AFTER
try {
    const response = await jfetch(`/detail_project/api/project/${projectId}/list-pekerjaan/upsert/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    // Check for errors in response
    if (response.errors && response.errors.length > 0) {
        console.error('[LP] Save validation errors:', response.errors);
        const errorMsg = response.errors.map(e => `• ${e.field}: ${e.message}`).join('\n');
        alert(`⚠️ Sebagian perubahan tidak tersimpan:\n\n${errorMsg}\n\nSilakan periksa dan coba lagi.`);

        // Highlight problematic rows if possible
        // (Can parse error.field to find which pekerjaan failed)

        await reloadAfterSave();  // Reload to show actual state
        return;
    }

    alert('✅ Perubahan tersimpan.');
    tbAnnounce && (tbAnnounce.textContent = 'Perubahan tersimpan');
    await reloadAfterSave();
```

---

### Fix 3: Alternative - Always Send ref_id for REF types 🔧 SIMPLER

**Simpler but less optimal (sends more data than needed)**

```javascript
// line 1330-1336 - Just always send ref_id for ref-like types
if (src === 'custom') {
    p.snapshot_uraian = uraian;
    if (satuan) p.snapshot_satuan = satuan;
} else if (src === 'ref_modified') {
    p.ref_id = refIdNum;  // ← ALWAYS send, remove condition
    if (uraian) p.snapshot_uraian = uraian;
    if (satuan) p.snapshot_satuan = satuan;
} else { // 'ref'
    p.ref_id = refIdNum;  // ← ALWAYS send, remove condition
}
```

**Pros:** Very simple, guaranteed to work
**Cons:** Sends ref_id even when unchanged (minor inefficiency)

---

## 🧪 Test Plan

### Manual Test Cases

#### Test 1: CUSTOM → REF (Should now work)
1. Create CUSTOM pekerjaan "Test A"
2. Save successfully
3. Change source to REF
4. Select AHSP reference "TEST.001"
5. Click Save
6. **Expected:** ✅ Success message, page reloads with REF source and selected ref shown
7. **Verify:** Check database: source_type='ref', ref_id populated
8. **Verify:** Navigate to Volume page: old data cleared (cascade reset worked)

#### Test 2: CUSTOM → REF_MODIFIED (Should now work)
1. Create CUSTOM pekerjaan "Test B"
2. Save successfully
3. Change source to REF_MODIFIED
4. Select AHSP reference
5. Modify uraian
6. Click Save
7. **Expected:** ✅ Success message, changes persist
8. **Verify:** Database has source_type='ref_modified', ref_id populated, custom uraian

#### Test 3: REF_MODIFIED → REF (Should now work)
1. Create REF_MODIFIED pekerjaan
2. Save successfully
3. Change source to REF
4. Keep same ref selected
5. Click Save
6. **Expected:** ✅ Success, uraian reverts to ref's uraian (custom override removed)

#### Test 4: Error Validation Display (Should show error)
1. Create CUSTOM pekerjaan
2. Change source to REF
3. **Don't select any ref** (leave dropdown empty)
4. Click Save
5. **Expected:** ⚠️ Error message: "Ref AHSP wajib dipilih" or similar
6. **Verify:** Page does NOT reload, user can fix and retry

#### Test 5: Regression - REF → CUSTOM (Should still work)
1. Create REF pekerjaan
2. Change to CUSTOM
3. Enter uraian
4. Save
5. **Expected:** ✅ Works as before

### Automated Test Cases

```python
# test_list_pekerjaan_source_changes.py

def test_custom_to_ref_persists(project, user):
    """Test that CUSTOM→REF transition now persists correctly."""
    # Create CUSTOM pekerjaan
    klas = Klasifikasi.objects.create(project=project, name="K1", ordering_index=1)
    sub = SubKlasifikasi.objects.create(project=project, klasifikasi=klas, name="S1", ordering_index=1)
    pekerjaan = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="CUST-001",
        snapshot_uraian="Custom Work",
        snapshot_satuan="unit",
        ordering_index=1
    )

    ref = AHSPReferensi.objects.create(
        kode="TEST.001",
        uraian="Test AHSP",
        satuan="m2"
    )

    # Simulate frontend sending source change with ref_id
    payload = {
        "klasifikasi": [{
            "id": klas.id,
            "name": "K1",
            "ordering_index": 1,
            "sub": [{
                "id": sub.id,
                "name": "S1",
                "ordering_index": 1,
                "pekerjaan": [{
                    "id": pekerjaan.id,
                    "source_type": "ref",  # Changed from custom
                    "ref_id": ref.id,       # NOW INCLUDED IN PAYLOAD ✅
                    "ordering_index": 1
                }]
            }]
        }]
    }

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f'/detail_project/api/project/{project.id}/list-pekerjaan/upsert/',
        data=json.dumps(payload),
        content_type='application/json'
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    assert response.json()['ok'] is True
    assert len(response.json()['errors']) == 0

    # Verify database
    pekerjaan.refresh_from_db()
    assert pekerjaan.source_type == Pekerjaan.SOURCE_REF
    assert pekerjaan.ref_id == ref.id
    assert pekerjaan.snapshot_kode == ref.kode
    assert pekerjaan.snapshot_uraian == ref.uraian


def test_custom_to_ref_without_ref_id_shows_error(project, user):
    """Test that CUSTOM→REF without ref_id shows proper error."""
    klas = Klasifikasi.objects.create(project=project, name="K1", ordering_index=1)
    sub = SubKlasifikasi.objects.create(project=project, klasifikasi=klas, name="S1", ordering_index=1)
    pekerjaan = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="CUST-001",
        snapshot_uraian="Custom Work",
        ordering_index=1
    )

    # Frontend sends source change WITHOUT ref_id (user didn't select)
    payload = {
        "klasifikasi": [{
            "id": klas.id,
            "name": "K1",
            "ordering_index": 1,
            "sub": [{
                "id": sub.id,
                "name": "S1",
                "ordering_index": 1,
                "pekerjaan": [{
                    "id": pekerjaan.id,
                    "source_type": "ref",
                    # ref_id missing! ❌
                    "ordering_index": 1
                }]
            }]
        }]
    }

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f'/detail_project/api/project/{project.id}/list-pekerjaan/upsert/',
        data=json.dumps(payload),
        content_type='application/json'
    )

    # Should return 207 with error
    assert response.status_code == 207
    assert response.json()['ok'] is False
    assert len(response.json()['errors']) > 0

    # Pekerjaan should NOT be modified (remains CUSTOM)
    pekerjaan.refresh_from_db()
    assert pekerjaan.source_type == Pekerjaan.SOURCE_CUSTOM
    assert pekerjaan.ref_id is None
```

---

## 📊 Impact Assessment

### Severity: 🔴 CRITICAL

**User Impact:**
- High frustration: Users think they saved but changes are lost
- Data confusion: System shows success but reverts changes
- Productivity loss: Users retry multiple times, give up, or enter incorrect workarounds

**Frequency:**
- Every time user changes from CUSTOM to REF/REF_MODIFIED
- Common workflow for users building project from scratch then switching to references

**Workaround:**
None discovered. Users cannot successfully perform these transitions.

---

## 🎯 Recommended Implementation Order

1. **Fix 2 (Error Handling)** - 30 minutes
   - Shows user what's actually wrong
   - Prevents confusion
   - Can deploy immediately for better UX

2. **Fix 1 or Fix 3 (ref_id Logic)** - 1-2 hours
   - Fix 3 is simpler (15 lines changed)
   - Fix 1 is more robust (handles all edge cases)
   - Recommend Fix 1 for long-term maintainability

3. **Testing** - 2 hours
   - Manual test all transitions
   - Add automated tests
   - Verify cascade reset still works

4. **Documentation Update** - 30 minutes
   - Update TESTING_AGENDA.md
   - Mark as resolved in MANUAL_TEST_RESULTS.md

**Total time: ~4 hours**

---

## 📝 Related Files

- `detail_project/static/detail_project/js/list_pekerjaan.js` - Primary fix location
- `detail_project/views_api.py` - Backend validation (working correctly)
- `BUG_INVESTIGATION_PEKERJAAN_DELETION.md` - Previous related bug
- `CODE_REVIEW_LIST_PEKERJAAN.md` - Code review with recommendations
- `MANUAL_TEST_RESULTS.md` - Testing documentation

---

## ✅ Next Steps

1. User confirms this analysis matches observed behavior
2. Choose Fix 1 (robust) or Fix 3 (simple)
3. Implement fixes in list_pekerjaan.js
4. Test manually with all transitions
5. Add automated tests
6. Commit and deploy
7. Update documentation

---

**Created:** 2025-11-09
**Author:** Claude (Bug Investigation)
**Status:** Ready for implementation
