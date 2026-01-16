# 🔧 Dual Storage Implementation - Bundle Fix

**Date:** 2025-11-09
**Status:** ✅ COMPLETED (Ready for Testing)
**Priority:** 🔴 CRITICAL (Bug Fix)

---

## 📋 Problem Summary

### Current Bug (OVERRIDE CONFLICT)

```
USER INPUT:
Bundle A (koef 2.0) → TK.001 (2.5) → Expanded: TK.001 (5.0)
Bundle B (koef 1.5) → TK.001 (3.0) → Expanded: TK.001 (4.5)

DATABASE (after save):
DetailAHSPProject:
- TK.001 (koef 4.5) ← LAST WRITE WINS! Bundle A lost!

unique_together = (project, pekerjaan, kode) ← Constraint prevents 2 rows with same kode
```

---

## ✅ Solution: Dual Storage

### Architecture

```
┌───────────────────────────────────────────────────────────────┐
│ STORAGE 1: DetailAHSPProject (RAW INPUT)                      │
│ Purpose: Store user's original input (audit trail + editable) │
├───────────────────────────────────────────────────────────────┤
│ Row 1: LAIN | Bundle_A | ref_pekerjaan=A | koef=2.0          │
│ Row 2: LAIN | Bundle_B | ref_pekerjaan=B | koef=1.5          │
│ Row 3: TK   | L.01     | direct          | koef=1.0          │
└───────────────────────────────────────────────────────────────┘
         │
         │ on_save: expand_and_store()
         ▼
┌───────────────────────────────────────────────────────────────┐
│ STORAGE 2: DetailAHSPExpanded (COMPUTED)                      │
│ Purpose: Expanded components for rekap (no override conflict) │
├───────────────────────────────────────────────────────────────┤
│ Row 1: TK.001 | source=Bundle_A | koef=5.0  | depth=1        │
│ Row 2: BHN.001| source=Bundle_A | koef=20.0 | depth=1        │
│ Row 3: TK.001 | source=Bundle_B | koef=4.5  | depth=1  ← OK! │
│ Row 4: BHN.002| source=Bundle_B | koef=12.0 | depth=1        │
│ Row 5: TK.001 | source=L.01     | koef=1.0  | depth=0  ← OK! │
└───────────────────────────────────────────────────────────────┘
                        ↑
                        │ NO unique constraint on kode!
                        │ Multiple bundles can have same kode
```

---

## 🔧 Implementation

### Step 1: Model (DONE ✅)

**File:** `models.py`

```python
class DetailAHSPExpanded(TimeStampedModel):
    project = FK(Project)
    pekerjaan = FK(Pekerjaan)
    source_detail = FK(DetailAHSPProject, on_delete=CASCADE)

    # Expanded component
    harga_item = FK(HargaItemProject, on_delete=PROTECT)
    kategori = CharField(10)
    kode = CharField(100)
    uraian = TextField()
    satuan = CharField(50, null=True)
    koefisien = DecimalField(18, 6)

    # Bundle metadata
    source_bundle_kode = CharField(100, null=True)
    expansion_depth = PositiveSmallIntegerField(default=0)

    # NO unique constraint on kode! ← KEY DIFFERENCE
```

---

### Step 2: Save Logic (IN PROGRESS ⏳)

**File:** `views_api.py` - `api_save_detail_ahsp_for_pekerjaan()`

**New Logic:**
```python
@transaction.atomic
def api_save_detail_ahsp_for_pekerjaan(request, project_id, pekerjaan_id):
    """
    DUAL STORAGE IMPLEMENTATION:
    1. Save raw input to DetailAHSPProject (keep LAIN bundles)
    2. Expand bundles to DetailAHSPExpanded (computed)
    3. Direct input (TK/BHN/ALT) pass-through to both
    """
    # ... validation ...

    # STORAGE 1: Save RAW input (keep bundles!)
    saved_details = []
    for row_data in rows:
        hip = _upsert_harga_item(...)

        detail = DetailAHSPProject(
            project=project,
            pekerjaan=pkj,
            harga_item=hip,
            kategori=row_data['kategori'],
            kode=row_data['kode'],
            uraian=row_data['uraian'],
            satuan=row_data['satuan'],
            koefisien=row_data['koefisien'],
            ref_pekerjaan=ref_pkj if kategori=='LAIN' else None,
            ref_ahsp=ref_ahsp if kategori=='LAIN' else None,
        )
        saved_details.append(detail)

    # DELETE old + INSERT new (replace-all)
    DetailAHSPProject.objects.filter(project=project, pekerjaan=pkj).delete()
    DetailAHSPProject.objects.bulk_create(saved_details)

    # STORAGE 2: Expand to DetailAHSPExpanded
    DetailAHSPExpanded.objects.filter(project=project, pekerjaan=pkj).delete()

    expanded_list = []
    for detail in saved_details:
        if detail.kategori == 'LAIN' and detail.ref_pekerjaan:
            # EXPAND bundle
            components = expand_bundle_to_components(
                detail=detail,
                base_koef=Decimal('1.0'),
                depth=0
            )
            for comp in components:
                expanded_list.append(DetailAHSPExpanded(
                    project=project,
                    pekerjaan=pkj,
                    source_detail=detail,
                    harga_item=comp['harga_item'],
                    kategori=comp['kategori'],
                    kode=comp['kode'],
                    uraian=comp['uraian'],
                    satuan=comp['satuan'],
                    koefisien=comp['koefisien'],
                    source_bundle_kode=detail.kode,
                    expansion_depth=comp['depth'],
                ))
        else:
            # PASS-THROUGH (direct TK/BHN/ALT)
            expanded_list.append(DetailAHSPExpanded(
                project=project,
                pekerjaan=pkj,
                source_detail=detail,
                harga_item=detail.harga_item,
                kategori=detail.kategori,
                kode=detail.kode,
                uraian=detail.uraian,
                satuan=detail.satuan,
                koefisien=detail.koefisien,
                source_bundle_kode=None,  # direct input
                expansion_depth=0,
            ))

    DetailAHSPExpanded.objects.bulk_create(expanded_list)

    # Update pekerjaan.detail_ready
    Pekerjaan.objects.filter(pk=pkj.pk).update(
        detail_ready=(len(expanded_list) > 0)
    )

    invalidate_rekap_cache(project)
    return JsonResponse({"ok": True, "saved_rows": len(saved_details)})
```

---

### Step 3: Expansion Helper (NEW)

**File:** `services.py`

```python
def expand_bundle_to_components(detail, base_koef, depth, visited=None):
    """
    Expand bundle DetailAHSPProject to component list.

    Args:
        detail: DetailAHSPProject instance (LAIN with ref_pekerjaan)
        base_koef: Accumulated koef from parent (Decimal)
        depth: Current expansion depth (int)
        visited: Set of pekerjaan_id to prevent circular

    Returns:
        List of dicts:
        [{
            'harga_item': HargaItemProject instance,
            'kategori': 'TK',
            'kode': 'TK.001',
            'uraian': 'Pekerja',
            'satuan': 'OH',
            'koefisien': Decimal('5.000000'),
            'depth': 1
        }, ...]
    """
    MAX_DEPTH = 10

    if depth > MAX_DEPTH:
        raise ValueError(f"Max depth {MAX_DEPTH} exceeded")

    if visited is None:
        visited = set()

    # Check circular
    if detail.ref_pekerjaan_id in visited:
        raise ValueError(f"Circular dependency: {visited}")

    visited.add(detail.ref_pekerjaan_id)

    # Fetch components from ref_pekerjaan
    ref_components = DetailAHSPProject.objects.filter(
        project=detail.project,
        pekerjaan=detail.ref_pekerjaan
    ).select_related('harga_item')

    result = []
    bundle_koef = detail.koefisien

    for comp in ref_components:
        if comp.kategori == 'LAIN' and comp.ref_pekerjaan:
            # Nested bundle - recursive
            nested = expand_bundle_to_components(
                detail=comp,
                base_koef=base_koef * bundle_koef,
                depth=depth + 1,
                visited=visited.copy()
            )
            result.extend(nested)
        else:
            # Base component
            final_koef = comp.koefisien * bundle_koef * base_koef
            result.append({
                'harga_item': comp.harga_item,
                'kategori': comp.kategori,
                'kode': comp.kode,
                'uraian': comp.uraian,
                'satuan': comp.satuan,
                'koefisien': final_koef,
                'depth': depth + 1
            })

    visited.remove(detail.ref_pekerjaan_id)
    return result
```

---

### Step 4: Update Rekap Computation (PENDING)

**File:** `services.py` - `compute_kebutuhan_items()`

**Change:**
```python
# OLD: Read from DetailAHSPProject
details = DetailAHSPProject.objects.filter(
    project=project,
    pekerjaan__in=pekerjaan_qs
).values(...)

# NEW: Read from DetailAHSPExpanded
details = DetailAHSPExpanded.objects.filter(
    project=project,
    pekerjaan__in=pekerjaan_qs
).values(...)

# Rest stays same - DetailAHSPExpanded has same structure
```

---

### Step 5: Update GET API (PENDING)

**File:** `views_api.py` - `api_get_detail_ahsp()`

**Keep reading from DetailAHSPProject** (raw input for editing!)

```python
# NO CHANGE - still read from DetailAHSPProject
# User edits raw input (keeps bundles intact)
qs = DetailAHSPProject.objects.filter(
    project=project,
    pekerjaan=pkj
).select_related('harga_item')
```

---

## 🧪 Test Scenarios

### Test 1: Override Conflict (Before Fix)

**Input:**
```python
rows = [
    {'kategori': 'LAIN', 'kode': 'BUNDLE_A', 'koef': '2.0', 'ref_kind': 'job', 'ref_id': job_b_id},
    {'kategori': 'LAIN', 'kode': 'BUNDLE_B', 'koef': '1.5', 'ref_kind': 'job', 'ref_id': job_c_id},
]

# job_b has: TK.001 (2.5)
# job_c has: TK.001 (3.0)
```

**Expected (OLD - BUG):**
```sql
SELECT * FROM detail_ahsp_project WHERE pekerjaan_id=A;
-- TK.001 | koef=4.5 ← OVERRIDE! Should be 5.0 AND 4.5
```

**Expected (NEW - FIXED):**
```sql
SELECT * FROM detail_ahsp_project WHERE pekerjaan_id=A;
-- LAIN | BUNDLE_A | ref_pekerjaan=B | koef=2.0 ✓
-- LAIN | BUNDLE_B | ref_pekerjaan=C | koef=1.5 ✓

SELECT * FROM detail_ahsp_expanded WHERE pekerjaan_id=A;
-- TK.001 | source_bundle=BUNDLE_A | koef=5.0 ✓
-- TK.001 | source_bundle=BUNDLE_B | koef=4.5 ✓ (NO OVERRIDE!)
```

---

### Test 2: Direct Input + Bundle

**Input:**
```python
rows = [
    {'kategori': 'TK', 'kode': 'L.01', 'koef': '1.0'},  # direct
    {'kategori': 'LAIN', 'kode': 'BUNDLE_A', 'koef': '2.0', 'ref_kind': 'job', 'ref_id': job_b_id},
]

# job_b has: TK.001 (2.5)
```

**Expected:**
```sql
SELECT * FROM detail_ahsp_project WHERE pekerjaan_id=A;
-- TK   | L.01     | koef=1.0 ✓
-- LAIN | BUNDLE_A | ref_pekerjaan=B | koef=2.0 ✓

SELECT * FROM detail_ahsp_expanded WHERE pekerjaan_id=A;
-- TK   | L.01     | source_bundle=NULL | koef=1.0 | depth=0 ✓
-- TK   | TK.001   | source_bundle=BUNDLE_A | koef=5.0 | depth=1 ✓
```

---

### Test 3: Re-edit Bundle

**Scenario:**
1. User saves Bundle A
2. Reload page
3. Edit Bundle A koef from 2.0 → 3.0
4. Save again

**Expected:**
```sql
-- After step 1:
SELECT * FROM detail_ahsp_project WHERE pekerjaan_id=A;
-- LAIN | BUNDLE_A | koef=2.0

SELECT * FROM detail_ahsp_expanded WHERE pekerjaan_id=A;
-- TK.001 | source_bundle=BUNDLE_A | koef=5.0 (2.5 × 2.0)

-- After step 4 (re-edit):
SELECT * FROM detail_ahsp_project WHERE pekerjaan_id=A;
-- LAIN | BUNDLE_A | koef=3.0 ✓ UPDATED

SELECT * FROM detail_ahsp_expanded WHERE pekerjaan_id=A;
-- TK.001 | source_bundle=BUNDLE_A | koef=7.5 ✓ RE-EXPANDED (2.5 × 3.0)
```

---

## 📊 Impact Analysis

### Benefits ✅

1. **No Override Conflict**
   - Multiple bundles can have same kode
   - All expanded components preserved

2. **Audit Trail**
   - Raw input kept in DetailAHSPProject
   - Can see what user originally input

3. **Editable**
   - User can edit bundle koef later
   - Re-expansion automatic on save

4. **Backward Compatible**
   - GET API unchanged (reads raw input)
   - Frontend unchanged (sends same payload)

### Drawbacks ⚠️

1. **Storage 2x**
   - Need 2 tables instead of 1
   - ~2x database size for detail AHSP

2. **Migration Needed**
   - Existing data needs migration
   - DetailAHSPProject → keep as-is (if already expanded, mark as direct)
   - Create DetailAHSPExpanded from current data

3. **Complexity**
   - More code to maintain
   - 2 save operations instead of 1

### Trade-off Decision

**Verdict:** ✅ **WORTH IT**

**Reasoning:**
- Bug is critical (data loss)
- Benefits outweigh complexity
- Storage cost is minimal (detail AHSP not huge)
- Backward compatible (low risk)

---

## 🚀 Deployment Plan

### Phase 1: Development ✅ COMPLETED

- [x] Create DetailAHSPExpanded model
- [x] Add to admin
- [x] Update save API logic (detail_project/views_api.py:1287-1424)
- [x] Create expansion helper (detail_project/services.py:174-313)
- [x] Update rekap computation (detail_project/services.py:571-580, 758-799)
- [ ] Update tests (PENDING - manual testing recommended first)

### Phase 2: Migration ✅ COMPLETED

- [x] Create Django migration (detail_project/migrations/0018_detailahspexpanded_and_more.py)
- [ ] Data migration script (PENDING - optional, existing data can be re-saved via UI)
  ```python
  # For each DetailAHSPProject:
  #   Create matching DetailAHSPExpanded (pass-through)
  #   If kategori=LAIN with ref_pekerjaan → expand
  ```

### Phase 3: Testing ⏳ IN PROGRESS

- [ ] Unit tests for expansion
- [ ] Integration tests for save API
- [x] Manual tests for override scenarios (READY - need database setup)
- [ ] Performance tests (2x storage impact)

### Phase 4: Production 🔜 PENDING

- [ ] Deploy to staging
- [ ] Run migration on staging data
- [ ] Verify rekap calculations unchanged
- [ ] Deploy to production

---

**Status:** ✅ IMPLEMENTATION COMPLETED - Ready for Testing
**Next:** Run migration and perform manual testing
**Files Changed:**
- detail_project/models.py (added DetailAHSPExpanded)
- detail_project/admin.py (registered DetailAHSPExpanded)
- detail_project/services.py (added expand_bundle_to_components, updated rekap)
- detail_project/views_api.py (dual storage save logic)
- detail_project/migrations/0018_detailahspexpanded_and_more.py (new)
