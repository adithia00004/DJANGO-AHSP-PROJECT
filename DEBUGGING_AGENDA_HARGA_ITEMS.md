# 🔍 Debugging Agenda: Harga Items Kosong - Root Cause Analysis

**Created**: 2025-11-09
**Purpose**: Systematic investigation untuk mengidentifikasi kenapa harga_items page kosong
**Scope**: 3 kondisi (CUSTOM, REF, REF_MODIFIED)

---

## 🎯 OBJECTIVE

**Problem Statement**:
Harga Items page shows EMPTY (no items displayed) untuk semua 3 source_type:
1. ❌ CUSTOM: Setelah save dengan bundle
2. ❌ REF: Setelah add dari AHSP Referensi
3. ❌ REF_MODIFIED: Setelah clone dari REF

**Expected Behavior**:
Harga Items page should show all base components (TK/BHN/ALT) dari DetailAHSPExpanded.

---

## 📋 DEBUGGING AGENDA

### **STEP 1: Verify Data State** (5 minutes)

#### **1.1 Check DetailAHSPProject (Storage 1)**

**Django Shell**:
```python
from detail_project.models import Pekerjaan, DetailAHSPProject, DetailAHSPExpanded

# Replace with actual pekerjaan_id
pekerjaan_id = <YOUR_PEKERJAAN_ID>

pkj = Pekerjaan.objects.get(id=pekerjaan_id)
print(f"Pekerjaan: {pkj.snapshot_kode} - {pkj.source_type}")

# Check Storage 1
raw_items = DetailAHSPProject.objects.filter(pekerjaan=pkj)
print(f"\n=== STORAGE 1 (DetailAHSPProject) ===")
print(f"Total rows: {raw_items.count()}")
for item in raw_items:
    print(f"  - {item.kategori} | {item.kode} | {item.uraian[:40]} | koef={item.koefisien}")
    if item.kategori == 'LAIN':
        print(f"    ref_ahsp_id: {item.ref_ahsp_id}")
        print(f"    ref_pekerjaan_id: {item.ref_pekerjaan_id}")
```

**Expected Output**:
```
Pekerjaan: 1.1.4.1 - ref
=== STORAGE 1 (DetailAHSPProject) ===
Total rows: 3
  - TK | L.01 | Pekerja | koef=0.66
  - BHN | C.01 | Semen | koef=326.00
  - BHN | D.01 | Pasir | koef=0.52
```

**Decision Point**:
- ✅ If count > 0: Storage 1 OK → Continue to Step 1.2
- ❌ If count = 0: **CRITICAL** → Storage 1 empty! Jump to Section 2.1

---

#### **1.2 Check DetailAHSPExpanded (Storage 2)**

**Django Shell**:
```python
# Check Storage 2
expanded_items = DetailAHSPExpanded.objects.filter(pekerjaan=pkj)
print(f"\n=== STORAGE 2 (DetailAHSPExpanded) ===")
print(f"Total rows: {expanded_items.count()}")
for item in expanded_items:
    print(f"  - {item.kategori} | {item.kode} | {item.uraian[:40]} | koef={item.koefisien}")
    print(f"    source_bundle_kode: {item.source_bundle_kode}")
    print(f"    expansion_depth: {item.expansion_depth}")
```

**Expected Output**:
```
=== STORAGE 2 (DetailAHSPExpanded) ===
Total rows: 3
  - TK | L.01 | Pekerja | koef=0.66
    source_bundle_kode: None
    expansion_depth: 0
  - BHN | C.01 | Semen | koef=326.00
    source_bundle_kode: None
    expansion_depth: 0
  - BHN | D.01 | Pasir | koef=0.52
    source_bundle_kode: None
    expansion_depth: 0
```

**Decision Point**:
- ✅ If count > 0: Storage 2 OK → Continue to Step 1.3
- ❌ If count = 0: **ROOT CAUSE IDENTIFIED** → Jump to Section 2.2

---

#### **1.3 Check HargaItemProject Link**

**Django Shell**:
```python
# Check if HargaItemProject exists and is linked
from detail_project.models import HargaItemProject

project = pkj.project

# Check HargaItemProject
hip_items = HargaItemProject.objects.filter(project=project)
print(f"\n=== HargaItemProject (Master Harga) ===")
print(f"Total items in project: {hip_items.count()}")

# Check which ones are referenced by DetailAHSPExpanded
hip_used = HargaItemProject.objects.filter(
    project=project,
    expanded_refs__project=project  # ← KEY CHECK!
).distinct()
print(f"Items used in DetailAHSPExpanded: {hip_used.count()}")

for item in hip_used:
    print(f"  - {item.kode_item} | {item.uraian[:40]}")
```

**Expected Output**:
```
=== HargaItemProject (Master Harga) ===
Total items in project: 10
Items used in DetailAHSPExpanded: 3
  - L.01 | Pekerja
  - C.01 | Semen
  - D.01 | Pasir
```

**Decision Point**:
- ✅ If hip_used.count() > 0: Data linked OK → Continue to Step 2
- ❌ If hip_used.count() = 0 but hip_items.count() > 0: **LINK BROKEN** → Jump to Section 2.3

---

### **STEP 2: Trace Harga Items API Call** (10 minutes)

#### **2.1 Check API Response**

**Browser DevTools**:
```javascript
// Open browser console on Harga Items page
// Network tab → Find request: /api/project/{id}/harga-items/list/

// Check response
{
  "ok": true,
  "items": [],  // ← EMPTY ARRAY = PROBLEM!
  "meta": {"markup_percent": "10.00"}
}
```

**If items = []**:
→ API returns empty, continue to Step 2.2

---

#### **2.2 Debug Backend API**

**File**: `detail_project/views_api.py`
**Function**: `api_list_harga_items()`
**Line**: 1933-1958

**Add Debug Logging**:
```python
def api_list_harga_items(request: HttpRequest, project_id: int):
    """
    List all Harga Items used in this project.
    """
    project = _owner_or_404(project_id, request.user)

    # ===== DEBUG: CHECK QUERY =====
    import logging
    logger = logging.getLogger(__name__)

    # Check total HargaItemProject
    total_hip = HargaItemProject.objects.filter(project=project).count()
    logger.warning(f"[HARGA_ITEMS] Total HargaItemProject in project: {total_hip}")

    # Check DetailAHSPExpanded count
    total_expanded = DetailAHSPExpanded.objects.filter(project=project).count()
    logger.warning(f"[HARGA_ITEMS] Total DetailAHSPExpanded in project: {total_expanded}")

    # Original query
    qs = (HargaItemProject.objects
          .filter(project=project, expanded_refs__project=project)  # ← LINE 1944
          .distinct()
          .order_by('kode_item'))

    logger.warning(f"[HARGA_ITEMS] Query result count: {qs.count()}")  # ← KEY!

    items = list(qs.values('id','kode_item','kategori','uraian','satuan','harga_satuan'))
    logger.warning(f"[HARGA_ITEMS] Final items count: {len(items)}")

    # ... rest of code
```

**Run Test**:
1. Refresh Harga Items page
2. Check Django server logs

**Expected Output**:
```
[HARGA_ITEMS] Total HargaItemProject in project: 10
[HARGA_ITEMS] Total DetailAHSPExpanded in project: 0  ← PROBLEM!
[HARGA_ITEMS] Query result count: 0
[HARGA_ITEMS] Final items count: 0
```

**Decision Point**:
- If `total_expanded = 0`: **ROOT CAUSE = DetailAHSPExpanded empty!**
  → Jump to Section 3 (diagnose why Storage 2 empty)

---

### **STEP 3: Diagnose Why Storage 2 Empty** (15 minutes)

#### **3.1 Check Pekerjaan Creation Method**

**Django Shell**:
```python
pkj = Pekerjaan.objects.get(id=<pekerjaan_id>)

# Check metadata
print(f"Source type: {pkj.source_type}")
print(f"Created at: {pkj.created_at}")
print(f"Updated at: {pkj.updated_at}")
print(f"Ref AHSP: {pkj.ref_id}")
```

**Compare with commit date**:
```bash
# Check when dual storage fix was added
git log --oneline | grep "populate_expanded"
# Output: 54d123c - fix: add _populate_expanded_from_raw call
git show 54d123c --stat
```

**Decision Point**:
- If `pkj.created_at < commit_date(54d123c)`: **OLD DATA!**
  → Jump to Section 4.1 (Old Data Migration)
- If `pkj.created_at >= commit_date(54d123c)`: **NEW DATA BUG!**
  → Jump to Section 4.2 (Code Bug Investigation)

---

#### **3.2 For CUSTOM: Check Bundle Reference**

**Django Shell**:
```python
# For CUSTOM pekerjaan only
if pkj.source_type == 'custom':
    lain_items = DetailAHSPProject.objects.filter(
        pekerjaan=pkj,
        kategori='LAIN'
    )

    print(f"\n=== LAIN Bundle Items ===")
    print(f"Total LAIN items: {lain_items.count()}")

    for item in lain_items:
        print(f"\nItem: {item.kode}")
        print(f"  ref_ahsp_id: {item.ref_ahsp_id}")  # ← Should be NULL
        print(f"  ref_pekerjaan_id: {item.ref_pekerjaan_id}")  # ← Should have value

        if item.ref_ahsp_id:
            print(f"  ⚠️ WARNING: AHSP reference (not supported for expansion!)")
        if not item.ref_pekerjaan_id:
            print(f"  ❌ ERROR: No pekerjaan reference (expansion skipped!)")
```

**Expected Output (PROBLEM)**:
```
=== LAIN Bundle Items ===
Total LAIN items: 1

Item: 2.2.1.4.6
  ref_ahsp_id: 123  ← PROBLEM! AHSP reference
  ref_pekerjaan_id: None  ← MISSING!
  ⚠️ WARNING: AHSP reference (not supported for expansion!)
```

**Decision Point**:
- If `ref_ahsp_id` is set: **USER ERROR!** Selected AHSP instead of Pekerjaan
  → Jump to Section 4.3 (User Workflow Fix)

---

### **STEP 4: Root Cause Specific Diagnosis**

#### **4.1 Scenario: Old Data (Before commit 54d123c)**

**Problem**: Pekerjaan created before `_populate_expanded_from_raw()` was added.

**Exact Location of Missing Code**:
```python
# File: detail_project/services.py
# Function: clone_ref_pekerjaan()
# Line: 400-480

# OLD CODE (before 54d123c):
def clone_ref_pekerjaan(...):
    # ... create DetailAHSPProject ...
    DetailAHSPProject.objects.bulk_create(raw_details)

    # ❌ MISSING: _populate_expanded_from_raw() call!

    return pekerjaan

# NEW CODE (after 54d123c):
def clone_ref_pekerjaan(...):
    # ... create DetailAHSPProject ...
    DetailAHSPProject.objects.bulk_create(raw_details)

    # ✅ ADDED: Populate expanded storage
    _populate_expanded_from_raw(project, pekerjaan)  # ← LINE 476

    return pekerjaan
```

**Verification**:
```bash
# Check commit diff
git show 54d123c -- detail_project/services.py | grep -A 5 "_populate_expanded"
```

**Root Cause**:
- Function: `clone_ref_pekerjaan()` (services.py:400)
- Missing call: `_populate_expanded_from_raw()` (should be at line 476)
- Impact: Storage 2 never populated for old REF/REF_MODIFIED

**Solution**: Jump to Section 5.1

---

#### **4.2 Scenario: New Data Code Bug**

**Problem**: New pekerjaan but Storage 2 still empty (code not working).

**Debug Points**:

**A. Check if _populate_expanded_from_raw() was called**

Add logging to `services.py`:
```python
# File: detail_project/services.py
# Line: 343

def _populate_expanded_from_raw(project, pekerjaan):
    logger.warning(f"[POPULATE_EXPANDED] ===== CALLED FOR PEKERJAAN {pekerjaan.id} =====")

    # ... rest of function

    if expanded_to_create:
        DetailAHSPExpanded.objects.bulk_create(expanded_to_create)
        logger.warning(f"[POPULATE_EXPANDED] ===== SUCCESS: Created {len(expanded_to_create)} rows =====")
```

**Test**: Re-create pekerjaan, check logs for:
```
[POPULATE_EXPANDED] ===== CALLED FOR PEKERJAAN 123 =====
[POPULATE_EXPANDED] ===== SUCCESS: Created 3 rows =====
```

**If NOT CALLED**:
→ **BUG**: `clone_ref_pekerjaan()` not calling helper
→ Check line 476 in services.py

**If CALLED but SUCCESS = 0**:
→ **BUG**: `expanded_to_create` list is empty
→ Check why loop doesn't create items

---

**B. Check if save API calls populate**

For CUSTOM pekerjaan (via API save):

**File**: `detail_project/views_api.py`
**Function**: `api_save_detail_ahsp_for_pekerjaan()`
**Lines**: 1339-1464

**Debug Points**:
```python
# Line 1347: Check if raw details saved
logger.warning(f"[SAVE_DETAIL_AHSP] Fetched {saved_raw_details.count()} raw details")

# Line 1354: Check if bundle expansion triggered
if detail_obj.kategori == 'LAIN' and detail_obj.ref_pekerjaan:
    logger.warning(f"[SAVE_DETAIL_AHSP] BUNDLE: {detail_obj.kode}, ref_pekerjaan={detail_obj.ref_pekerjaan_id}")
else:
    logger.warning(f"[SAVE_DETAIL_AHSP] DIRECT or INVALID LAIN: {detail_obj.kategori} - {detail_obj.kode}")

# Line 1460: Check expanded count
logger.warning(f"[SAVE_DETAIL_AHSP] About to create {len(expanded_to_create)} expanded rows")
```

**Expected for CUSTOM with valid bundle**:
```
[SAVE_DETAIL_AHSP] Fetched 1 raw details
[SAVE_DETAIL_AHSP] BUNDLE: Bundle Bekisting, ref_pekerjaan=123
[EXPAND_BUNDLE] Expanding bundle...
[SAVE_DETAIL_AHSP] About to create 3 expanded rows
```

**Problem Patterns**:

**Pattern 1: LAIN skipped**
```
[SAVE_DETAIL_AHSP] DIRECT or INVALID LAIN: LAIN - Bundle Bekisting
[SAVE_DETAIL_AHSP] About to create 0 expanded rows  ← PROBLEM!
```
**Root Cause**: Line 1354 condition failed
- `detail_obj.ref_pekerjaan` is NULL
- Check why: Line 1324 sets ref_pekerjaan

**Pattern 2: Expansion fails**
```
[SAVE_DETAIL_AHSP] BUNDLE: Bundle Bekisting, ref_pekerjaan=123
[EXPAND_BUNDLE] ERROR: ...
[SAVE_DETAIL_AHSP] About to create 0 expanded rows
```
**Root Cause**: `expand_bundle_to_components()` threw error
- Check error message in logs

---

#### **4.3 Scenario: User Selected AHSP Bundle (CUSTOM)**

**Problem**: User selected from "Master AHSP" instead of "Pekerjaan Proyek".

**Exact Flow**:

**Frontend** (template_ahsp.js):
```javascript
// Line 310-314: User selects AHSP
if (sid.startsWith('ahsp:')) {
    kind = 'ahsp';
    refId = sid.split(':')[1];
}

// Payload sent:
{
    kategori: 'LAIN',
    kode: '2.2.1.4.6',
    ref_kind: 'ahsp',  // ← PROBLEM!
    ref_id: 123
}
```

**Backend Validation** (views_api.py):
```python
# Line 1246-1250: ACCEPTS AHSP
if ref_kind == 'ahsp':
    ref_ahsp_obj = AHSPReferensi.objects.get(id=ref_id)  # ✅ OK
```

**Backend Save** (views_api.py):
```python
# Line 1323: Sets ref_ahsp, NOT ref_pekerjaan
DetailAHSPProject(
    ...
    ref_ahsp=ref_ahsp_obj,      # ✅ Set
    ref_pekerjaan=None           # ❌ NULL!
)
```

**Backend Expansion** (views_api.py):
```python
# Line 1354: SKIPPED!
if detail_obj.kategori == 'LAIN' and detail_obj.ref_pekerjaan:
    # ❌ SKIPPED - ref_pekerjaan is NULL
```

**Line 1430-1441: ERROR LOGGED**
```python
elif detail_obj.kategori == HargaItemProject.KATEGORI_LAIN:
    logger.warning(f"LAIN item has no ref_pekerjaan")
    errors.append("tidak memiliki referensi pekerjaan")
```

**Root Cause Summary**:
- **File**: views_api.py
- **Line 1354**: Condition only checks `ref_pekerjaan`, ignores `ref_ahsp`
- **Line 1430**: Error handler catches but doesn't expand
- **Impact**: LAIN item saved to Storage 1 but NOT expanded to Storage 2

**Solution**: Jump to Section 5.3

---

## 🔧 SECTION 5: SOLUTIONS

### **5.1 Solution: Old Data Migration**

**Quick Fix (Manual)**:
1. Delete old pekerjaan from UI
2. Re-add from AHSP Referensi
3. Verify Harga Items populated

**Proper Fix (Automated)**:
```python
# File: detail_project/management/commands/migrate_dual_storage.py

from django.core.management.base import BaseCommand
from detail_project.models import Pekerjaan, DetailAHSPProject, DetailAHSPExpanded
from detail_project.services import _populate_expanded_from_raw

class Command(BaseCommand):
    help = 'Migrate old pekerjaan to populate DetailAHSPExpanded'

    def add_arguments(self, parser):
        parser.add_argument('--project-id', type=int, help='Project ID')
        parser.add_argument('--fix', action='store_true', help='Actually fix (dry-run by default)')

    def handle(self, *args, **options):
        project_id = options['project_id']
        fix = options['fix']

        # Find inconsistent pekerjaan
        for pkj in Pekerjaan.objects.filter(project_id=project_id):
            raw_count = DetailAHSPProject.objects.filter(pekerjaan=pkj).count()
            expanded_count = DetailAHSPExpanded.objects.filter(pekerjaan=pkj).count()

            if raw_count > 0 and expanded_count == 0:
                self.stdout.write(f"❌ Pekerjaan {pkj.id} ({pkj.snapshot_kode}): {raw_count} raw, 0 expanded")

                if fix:
                    _populate_expanded_from_raw(pkj.project, pkj)
                    new_count = DetailAHSPExpanded.objects.filter(pekerjaan=pkj).count()
                    self.stdout.write(self.style.SUCCESS(f"✅ Fixed! Now has {new_count} expanded rows"))
                else:
                    self.stdout.write("  (use --fix to migrate)")
```

**Usage**:
```bash
# Dry run (check only)
python manage.py migrate_dual_storage --project-id=1

# Actually fix
python manage.py migrate_dual_storage --project-id=1 --fix
```

---

### **5.2 Solution: Code Bug (If Found)**

**If _populate_expanded_from_raw() not called**:
```python
# File: detail_project/services.py
# Line: 476 (after bulk_create)

# Add this line if missing:
_populate_expanded_from_raw(project, pekerjaan)
```

**If expand_bundle_to_components() fails**:
- Check error logs
- Debug specific error (circular dependency, missing ref, etc.)

---

### **5.3 Solution: AHSP Bundle Not Supported**

**Frontend Fix** (template_ahsp.js):
```javascript
// Line 296-314: Add validation

$input.on('select2:select', (e) => {
    const d = e.params.data || {};
    const sid = String(d.id||'');

    // NEW: Reject AHSP for CUSTOM bundles
    if (activeSource === 'custom' && sid.startsWith('ahsp:')) {
        toast('Untuk pekerjaan custom, pilih dari Pekerjaan Proyek (bukan Master AHSP)', 'error');
        $input.val(null).trigger('change');
        return;  // ← Prevent selection
    }

    // ... existing code
});
```

**Backend Fix** (views_api.py):
```python
# Line 1246-1257: Add validation

if ref_kind == 'ahsp':
    # NEW: Reject for CUSTOM pekerjaan
    if pkj.source_type == Pekerjaan.SOURCE_CUSTOM:
        errors.append(_err(
            f"rows[{i}].ref_kind",
            "Pekerjaan custom hanya bisa reference pekerjaan dalam project (ref_kind='job')"
        ))
        continue

    # Existing code for ref_ahsp_obj...
```

---

## 📊 DECISION TREE

```
START: Harga Items Empty
    ↓
[1] Check Storage 1 (DetailAHSPProject)
    ├─ Empty? → CRITICAL: Pekerjaan has no details! (User never added)
    └─ Has data? → Continue
    ↓
[2] Check Storage 2 (DetailAHSPExpanded)
    ├─ Empty? → ROOT CAUSE FOUND!
    │   ↓
    │   [3] Check pekerjaan.created_at
    │       ├─ Before 54d123c? → OLD DATA (Solution 5.1)
    │       └─ After 54d123c? → CODE BUG (Solution 5.2)
    │   ↓
    │   [4] For CUSTOM: Check LAIN items
    │       ├─ ref_ahsp_id set? → USER ERROR (Solution 5.3)
    │       └─ ref_pekerjaan_id NULL? → CODE BUG (Solution 5.2)
    │
    └─ Has data? → Continue
    ↓
[5] Check HargaItemProject link
    ├─ expanded_refs empty? → LINK BROKEN (rare, check FK)
    └─ Has data? → API ISSUE (check views_api.py:1944)
```

---

## 🎯 EXECUTION CHECKLIST

Use this checklist untuk systematically debug:

### **Phase 1: Data Verification** (5 min)
- [ ] Run Step 1.1: Check DetailAHSPProject count
- [ ] Run Step 1.2: Check DetailAHSPExpanded count
- [ ] Run Step 1.3: Check HargaItemProject links
- [ ] Record findings in table below

### **Phase 2: API Trace** (10 min)
- [ ] Run Step 2.1: Check browser Network tab
- [ ] Run Step 2.2: Add debug logging to API
- [ ] Refresh Harga Items page
- [ ] Check Django logs
- [ ] Record API response + log output

### **Phase 3: Root Cause** (15 min)
- [ ] Run Step 3.1: Check pekerjaan metadata
- [ ] Compare created_at with commit 54d123c date
- [ ] For CUSTOM: Run Step 3.2
- [ ] Identify specific scenario (4.1, 4.2, or 4.3)
- [ ] Note exact file + line number causing issue

### **Phase 4: Apply Solution** (varies)
- [ ] Choose solution from Section 5
- [ ] Implement fix
- [ ] Test with fresh pekerjaan
- [ ] Verify Harga Items populated

---

## 📝 FINDINGS TEMPLATE

Fill this as you debug:

### **Pekerjaan Details**
```
ID: _______
Kode: _______
Source Type: _______
Created At: _______
Project ID: _______
```

### **Storage State**
```
DetailAHSPProject (Storage 1):
  Count: _______
  Sample row: _______

DetailAHSPExpanded (Storage 2):
  Count: _______  ← KEY!
  Sample row: _______

HargaItemProject linked:
  Count: _______
```

### **API Response**
```
GET /api/project/{id}/harga-items/list/
Response items count: _______
Response: _______
```

### **Root Cause**
```
Scenario: [ ] Old Data  [ ] Code Bug  [ ] AHSP Bundle
File: _______
Function: _______
Line: _______
Exact Issue: _______
```

### **Solution Applied**
```
Solution: _______
Code changes: _______
Test result: _______
```

---

## 🚀 QUICK START COMMAND

Run this in Django shell to get instant diagnosis:

```python
# Quick Diagnostic Script
from detail_project.models import Pekerjaan, DetailAHSPProject, DetailAHSPExpanded, HargaItemProject

def diagnose_harga_items_empty(pekerjaan_id):
    pkj = Pekerjaan.objects.get(id=pekerjaan_id)
    project = pkj.project

    print(f"{'='*60}")
    print(f"DIAGNOSIS: Pekerjaan {pkj.id} - {pkj.snapshot_kode}")
    print(f"{'='*60}")
    print(f"Source: {pkj.source_type}")
    print(f"Created: {pkj.created_at}")
    print()

    # Storage 1
    raw = DetailAHSPProject.objects.filter(pekerjaan=pkj)
    print(f"[1] Storage 1 (DetailAHSPProject): {raw.count()} rows")
    if raw.exists():
        for r in raw[:3]:
            print(f"    - {r.kategori} | {r.kode} | koef={r.koefisien}")
            if r.kategori == 'LAIN':
                print(f"      ref_ahsp_id: {r.ref_ahsp_id}")
                print(f"      ref_pekerjaan_id: {r.ref_pekerjaan_id}")

    # Storage 2
    expanded = DetailAHSPExpanded.objects.filter(pekerjaan=pkj)
    print(f"\n[2] Storage 2 (DetailAHSPExpanded): {expanded.count()} rows")
    if expanded.exists():
        for e in expanded[:3]:
            print(f"    - {e.kategori} | {e.kode} | koef={e.koefisien}")
    else:
        print(f"    ❌ EMPTY! This is why Harga Items is empty!")

    # HargaItemProject
    hip = HargaItemProject.objects.filter(project=project, expanded_refs__project=project).distinct()
    print(f"\n[3] HargaItemProject linked: {hip.count()} items")

    # Diagnosis
    print(f"\n{'='*60}")
    print("DIAGNOSIS:")
    if raw.count() == 0:
        print("❌ CRITICAL: No raw data! Pekerjaan has no details.")
    elif expanded.count() == 0:
        print("❌ ROOT CAUSE: Storage 2 empty!")
        print("   Possible reasons:")
        print("   - Old data (created before dual storage fix)")
        print("   - LAIN bundle with AHSP reference (not supported)")
        print("   - Code bug (expansion not triggered)")

        # Check for LAIN
        lain = raw.filter(kategori='LAIN')
        if lain.exists():
            for l in lain:
                if l.ref_ahsp_id:
                    print(f"   ⚠️  LAIN '{l.kode}' has ref_ahsp (not supported!)")
                if not l.ref_pekerjaan_id:
                    print(f"   ⚠️  LAIN '{l.kode}' missing ref_pekerjaan")
    else:
        print("✅ Storage 2 has data!")
        if hip.count() == 0:
            print("❌ But HargaItemProject link broken!")

    print(f"{'='*60}")

# RUN IT:
diagnose_harga_items_empty(<YOUR_PEKERJAAN_ID>)
```

---

## 📋 SUMMARY

**Key Files to Check**:
1. `detail_project/views_api.py` - Line 1944 (Harga Items query)
2. `detail_project/views_api.py` - Line 1354 (Bundle expansion condition)
3. `detail_project/services.py` - Line 476 (populate call)
4. `detail_project/services.py` - Line 343 (_populate_expanded_from_raw)

**Most Likely Causes** (in order):
1. 🔴 **Old data** (before commit 54d123c) - 70% probability
2. 🔴 **AHSP bundle** (user selected wrong source) - 20% probability
3. 🔴 **Code bug** (expansion not triggered) - 10% probability

**Expected Time**:
- Diagnosis: 30 minutes
- Solution: 30-120 minutes (depending on cause)

---

**Ready to debug!** Start with the Quick Start Command above untuk instant diagnosis.
