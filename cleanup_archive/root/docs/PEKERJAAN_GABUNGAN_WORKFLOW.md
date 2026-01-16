# 🔗 Alur Kerja Pekerjaan Gabungan (Bundle) - Analisis Lengkap

**Date:** 2025-11-09
**Status:** ⚠️ PERLU REVIEW DAN TESTING
**Priority:** 🔴 HIGH

---

## 📋 Daftar Isi

1. [Overview](#overview)
2. [Current Implementation](#current-implementation)
3. [Identified Issues](#identified-issues)
4. [Test Cases](#test-cases)
5. [Recommendations](#recommendations)

---

## 1. Overview

### 1.1 Apa itu Pekerjaan Gabungan?

**Pekerjaan Gabungan** (Bundle) adalah fitur yang memungkinkan user untuk:
- **Memasukkan komponen dari pekerjaan lain** ke dalam pekerjaan saat ini
- **Automatic expansion** saat save (bundle → komponen individual)
- **Koefisien multiplier** untuk scale up/down komponen

### 1.2 Use Cases

#### Use Case 1: Pekerjaan Kombinasi
```
Pekerjaan: "Galian + Urugan Komplet"
└─ LAIN:
   ├─ [Bundle] Galian Tanah (koef 2.0)
   └─ [Bundle] Urugan Tanah (koef 1.5)

HASIL:
- Semua komponen Galian × 2.0
- Semua komponen Urugan × 1.5
- Digabung jadi satu pekerjaan
```

#### Use Case 2: Pekerjaan Template Reusable
```
Template: "Pekerjaan Pondasi Standar"
└─ TK: Pekerja, Tukang, Mandor
└─ BHN: Semen, Pasir, Batu
└─ ALT: Molen, Vibrator

Multiple Pekerjaan bisa reference template ini:
- Pondasi Tipe A → reference template (koef 1.0)
- Pondasi Tipe B → reference template (koef 1.5)
- Pondasi Tipe C → reference template (koef 2.0)
```

#### Use Case 3: Nested Bundle (Multi-Level)
```
Level 1: "Pekerjaan Struktur Lengkap"
└─ LAIN: [Bundle] Pekerjaan Pondasi (koef 1.0)

Level 2: "Pekerjaan Pondasi"
└─ LAIN: [Bundle] Galian + Urugan (koef 2.0)

Level 3: "Galian + Urugan"
├─ TK: Pekerja (koef 3.0)
└─ BHN: Material (koef 10.0)

EXPANSION:
Level 1 → Level 2 → Level 3 → Base Components
Final: TK Pekerja (3.0 × 2.0 × 1.0 = 6.0)
```

---

## 2. Current Implementation

### 2.1 Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ USER INPUT (Frontend)                                           │
│                                                                 │
│ Segment LAIN:                                                   │
│ ┌────────────────────────────────────────────┐                 │
│ │ Kode: [Select2 Dropdown ▼]                │                 │
│ │  ├─ Pekerjaan Proyek                      │                 │
│ │  │   ├─ Job A001                          │                 │
│ │  │   └─ Job B002                          │                 │
│ │  └─ Master AHSP                            │                 │
│ │      ├─ AHSP.001                           │                 │
│ │      └─ AHSP.002                           │                 │
│ └────────────────────────────────────────────┘                 │
│                                                                 │
│ User selects "Job B002"                                         │
│ Auto-fill:                                                      │
│   - Kode: B002                                                  │
│   - Uraian: Detail Job B                                        │
│   - Satuan: LS                                                  │
│   - Koefisien: 1,000000                                        │
│   - ref_kind: 'job'                                            │
│   - ref_id: [B002.id]                                          │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ FRONTEND SAVE (template_ahsp.js)                                │
│                                                                 │
│ gatherRows() collects:                                          │
│ {                                                               │
│   "kategori": "LAIN",                                          │
│   "kode": "B002",                                              │
│   "uraian": "Detail Job B",                                    │
│   "satuan": "LS",                                              │
│   "koefisien": "2.000000",                                     │
│   "ref_kind": "job",        ← Bundle indicator                │
│   "ref_id": 123              ← Reference ID                    │
│ }                                                               │
│                                                                 │
│ POST to /api/.../detail-ahsp/{pid}/save/                       │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ BACKEND VALIDATION (views_api.py)                               │
│                                                                 │
│ 1. Check if ref_kind == 'job':                                 │
│    ✅ YES → Bundle expansion flow                              │
│    ❌ NO → Normal save flow                                    │
│                                                                 │
│ 2. Validate bundle reference:                                   │
│    validate_bundle_reference(pekerjaan_id, 'job', ref_id)      │
│    ├─ Check self-reference (A → A)                            │
│    ├─ Check circular dependency (A → B → A)                   │
│    └─ Check ref_pekerjaan exists                              │
│                                                                 │
│ 3. If validation passes:                                        │
│    ✅ Continue to expansion                                     │
│    ❌ Return error 400                                         │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ BUNDLE EXPANSION (services.py)                                  │
│                                                                 │
│ expand_bundle_recursive(detail_dict, base_koef, project):      │
│                                                                 │
│ 1. Check depth (max 10 levels)                                 │
│ 2. Check circular via visited set                              │
│ 3. Fetch components from ref_pekerjaan                          │
│ 4. For each component:                                          │
│    - If TK/BHN/ALT: Add to result with multiplied koef        │
│    - If LAIN (nested bundle): Recursive call                   │
│ 5. Return expanded components                                   │
│                                                                 │
│ Example:                                                        │
│ Input: LAIN B002 (koef 2.0)                                    │
│ B002 has:                                                       │
│   - TK.001 (koef 2.5)                                          │
│   - BHN.001 (koef 10.0)                                        │
│                                                                 │
│ Output:                                                         │
│   - TK.001 (koef 2.5 × 2.0 = 5.0)                            │
│   - BHN.001 (koef 10.0 × 2.0 = 20.0)                          │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ SAVE TO DATABASE (views_api.py)                                 │
│                                                                 │
│ @transaction.atomic                                             │
│                                                                 │
│ 1. Upsert HargaItemProject for each expanded component         │
│ 2. Create DetailAHSPProject instances                           │
│    ├─ kategori: TK/BHN/ALT (NOT LAIN!)                        │
│    ├─ kode, uraian, satuan: from expansion                     │
│    ├─ koefisien: multiplied koef                               │
│    └─ ref_pekerjaan: NULL (expanded items don't keep ref)     │
│                                                                 │
│ 3. DELETE all old DetailAHSPProject for this pekerjaan         │
│ 4. BULK_CREATE new DetailAHSPProject (expanded components)     │
│ 5. Update pekerjaan.detail_ready = True                        │
│ 6. Invalidate cache                                             │
│                                                                 │
│ RESULT:                                                         │
│ - LAIN bundle row: DELETED (not saved)                         │
│ - Expanded components: SAVED (TK/BHN/ALT)                      │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2.2 Key Functions

#### A. Frontend: enhanceLAINAutocomplete()

**Location:** `template_ahsp.js:235-345`

**Purpose:** Setup Select2 dropdown untuk LAIN segment

**Features:**
1. **Dual source:**
   - Local: Pekerjaan dalam project (via DOM parsing)
   - Remote: Master AHSP (via AJAX search)

2. **Auto-fill on select:**
   - kode, uraian, satuan
   - ref_kind ('job' or 'ahsp')
   - ref_id (pekerjaan_id or ahsp_id)
   - koefisien (default 1.0 if empty)

3. **Tag "Bundle":**
   - Visual indicator di UI
   - Dihapus saat user manual edit kode

**Code:**
```javascript
$input.on('select2:select', (e) => {
    const d = e.params.data || {};
    let kind = 'ahsp';
    let refId = '';

    if (d.id.startsWith('job:')) {
        kind = 'job';  // ← Bundle indicator
        refId = d.id.split(':')[1];
    } else {
        kind = 'ahsp';
        refId = d.id.split(':')[1];
    }

    // Auto-fill fields
    input.value = kode;
    $('.cell-wrap', tr).textContent = nama;
    $('input[data-field="satuan"]', tr).value = sat;
    $('input[data-field="ref_kind"]', tr).value = kind;
    $('input[data-field="ref_id"]', tr).value = refId;

    // Default koefisien
    if (!koefInput.value.trim()) {
        koefInput.value = __koefToUI('1.000000');
    }

    // Add bundle tag
    kodeTd.insertAdjacentHTML('beforeend', ' <span class="tag-bundle">Bundle</span>');
});
```

---

#### B. Backend: validate_bundle_reference()

**Location:** `services.py` (needs implementation check)

**Purpose:** Validate bundle reference sebelum save

**Validations:**
1. ✅ Self-reference check (A → A)
2. ✅ Circular dependency check (A → B → A)
3. ✅ Reference exists check
4. ✅ Project ownership check

**Code:**
```python
def validate_bundle_reference(pekerjaan_id, ref_kind, ref_id, project):
    """
    Validate bundle reference.

    Returns:
        (is_valid: bool, error_msg: str)
    """
    # Check self-reference
    if ref_kind == 'job' and pekerjaan_id == ref_id:
        return False, "Pekerjaan tidak boleh mereferensi diri sendiri"

    # Check circular dependency
    if ref_kind == 'job':
        is_circular, path = check_circular_dependency_pekerjaan(
            pekerjaan_id, ref_id, project
        )
        if is_circular:
            return False, f"Circular dependency detected: {path}"

    # Check reference exists
    if ref_kind == 'job':
        try:
            Pekerjaan.objects.get(id=ref_id, project=project)
        except Pekerjaan.DoesNotExist:
            return False, f"Pekerjaan ref_id={ref_id} tidak ditemukan"

    return True, ""
```

---

#### C. Backend: expand_bundle_recursive()

**Location:** `services.py`

**Purpose:** Recursively expand bundle to base components

**Algorithm:**
```python
def expand_bundle_recursive(detail_dict, base_koefisien, project, depth=0, visited=None):
    """
    Recursively expand bundle to base components.

    Args:
        detail_dict: Dict with kategori, kode, koefisien, ref_pekerjaan_id, etc.
        base_koefisien: Accumulated koefisien from parent levels
        project: Project instance
        depth: Current recursion depth (max 10)
        visited: Set of visited pekerjaan_id (circular detection)

    Returns:
        List of (kategori, kode, uraian, satuan, koefisien_final, harga_item)
    """
    MAX_DEPTH = 10

    # Check max depth
    if depth > MAX_DEPTH:
        raise ValueError(f"Maksimum kedalaman bundle terlampaui (max {MAX_DEPTH})")

    # Initialize visited set
    if visited is None:
        visited = set()

    # Get bundle reference
    ref_pekerjaan_id = detail_dict.get('ref_pekerjaan_id')
    if not ref_pekerjaan_id:
        # Not a bundle, return as-is
        return [(
            detail_dict['kategori'],
            detail_dict['kode'],
            detail_dict['uraian'],
            detail_dict['satuan'],
            Decimal(detail_dict['koefisien']),
            None  # harga_item will be upserted later
        )]

    # Check circular
    if ref_pekerjaan_id in visited:
        raise ValueError(f"Circular dependency detected in bundle expansion: {visited}")

    visited.add(ref_pekerjaan_id)

    # Fetch components from ref_pekerjaan
    ref_pekerjaan = Pekerjaan.objects.get(id=ref_pekerjaan_id, project=project)
    components = DetailAHSPProject.objects.filter(
        project=project,
        pekerjaan=ref_pekerjaan
    ).values('kategori', 'kode', 'uraian', 'satuan', 'koefisien', 'ref_pekerjaan_id')

    # Expand each component
    result = []
    bundle_koef = Decimal(detail_dict['koefisien'])

    for comp in components:
        if comp['kategori'] == 'LAIN' and comp.get('ref_pekerjaan_id'):
            # Nested bundle - recursive call
            nested_result = expand_bundle_recursive(
                detail_dict=comp,
                base_koefisien=base_koefisien * bundle_koef,
                project=project,
                depth=depth + 1,
                visited=visited.copy()  # Copy to avoid mutation
            )
            result.extend(nested_result)
        else:
            # Base component - add with multiplied koef
            final_koef = Decimal(comp['koefisien']) * bundle_koef * base_koefisien
            result.append((
                comp['kategori'],
                comp['kode'],
                comp['uraian'],
                comp['satuan'],
                final_koef,
                None  # harga_item will be upserted later
            ))

    visited.remove(ref_pekerjaan_id)
    return result
```

---

### 2.3 Database Schema

#### DetailAHSPProject with Bundle Support

```python
class DetailAHSPProject(TimeStampedModel):
    project = FK(Project)
    pekerjaan = FK(Pekerjaan)
    harga_item = FK(HargaItemProject, on_delete=PROTECT)

    kategori = CharField(10)  # TK/BHN/ALT/LAIN
    kode = CharField(100)
    uraian = TextField()
    satuan = CharField(50, null=True)
    koefisien = DecimalField(18, 6)

    # Bundle support (LAIN only)
    ref_ahsp = FK(AHSPReferensi, null=True, on_delete=PROTECT)
    ref_pekerjaan = FK(Pekerjaan, null=True, on_delete=PROTECT)

    class Meta:
        unique_together = ("project", "pekerjaan", "kode")
        constraints = [
            # Only LAIN can have bundle ref
            CheckConstraint(
                condition=(
                    Q(ref_ahsp__isnull=True, ref_pekerjaan__isnull=True) |
                    Q(kategori='LAIN')
                ),
                name="bundle_ref_only_for_lain"
            ),
            # Cannot have both ref_ahsp AND ref_pekerjaan
            CheckConstraint(
                condition=~Q(ref_ahsp__isnull=False, ref_pekerjaan__isnull=False),
                name="exclusive_ref_ahsp_or_pekerjaan"
            )
        ]
```

---

## 3. Identified Issues

### 🔴 Issue #1: OLD Data with LAIN Bundle (Not Expanded)

**Problem:**
- Old data di database mungkin masih punya row LAIN dengan ref_pekerjaan
- Data ini **TIDAK** di-expand (sebelum fix implementation)
- Rekap computation harus handle old bundle format

**Example:**
```sql
-- OLD DATA (before expansion fix)
SELECT * FROM detail_ahsp_project WHERE pekerjaan_id = 1;

id | kategori | kode   | ref_pekerjaan_id
1  | LAIN     | B002   | 2                ← Bundle (NOT expanded!)

-- NEW DATA (after expansion fix)
SELECT * FROM detail_ahsp_project WHERE pekerjaan_id = 1;

id | kategori | kode   | ref_pekerjaan_id
1  | TK       | TK.001 | NULL             ← Expanded
2  | BHN      | BHN.001| NULL             ← Expanded
```

**Impact:**
- Rekap computation must handle BOTH formats
- Backward compatibility required
- Data migration might be needed

**Recommendation:**
```python
# In compute_kebutuhan_items()
for detail in details:
    if detail['kategori'] == 'LAIN' and detail.get('ref_pekerjaan_id'):
        # OLD format - expand on-the-fly during rekap
        logger.warning(f"Old bundle format detected for pekerjaan {detail['pekerjaan_id']}")
        expanded = expand_bundle_for_old_data(detail, project)
        # ... use expanded items
    else:
        # NEW format - already expanded
        # ... use detail as-is
```

---

### 🟡 Issue #2: Bundle Expansion Timing

**Current:** Expansion happens during **SAVE**

**Pros:**
- ✅ Faster rekap computation (no expansion needed)
- ✅ Data stored in expanded form (clear structure)
- ✅ Easier to debug (can see expanded components in DB)

**Cons:**
- ❌ Changes in source pekerjaan NOT reflected automatically
- ❌ User must manually re-save to update
- ❌ No automatic propagation

**Example:**
```
1. Pekerjaan A has LAIN → Pekerjaan B (saved, expanded)
   Result: A has TK.001 (koef 5.0), BHN.001 (koef 20.0)

2. User edits Pekerjaan B:
   TK.001: 2.5 → 3.0
   BHN.001: 10.0 → 15.0

3. Pekerjaan A still has OLD values:
   TK.001 (koef 5.0)  ← Should be 6.0 (3.0 × 2.0)
   BHN.001 (koef 20.0) ← Should be 30.0 (15.0 × 2.0)

4. User must manually re-save Pekerjaan A to update
```

**Alternative:** Expansion during **REKAP** computation

**Pros:**
- ✅ Always up-to-date (auto-sync)
- ✅ Changes in source propagate automatically

**Cons:**
- ❌ Slower rekap computation
- ❌ Circular dependency check every time
- ❌ More complex logic

**Recommendation:**
- **Keep current approach** (expansion during save)
- **Add warning in UI**: "Bundle will be expanded. Changes in source pekerjaan won't auto-update."
- **Future:** Add "Refresh Bundle" button

---

### 🟡 Issue #3: Koefisien Precision Loss in Nested Bundles

**Problem:**
```
Level 1: koef 1.5
Level 2: koef 2.0
Level 3: koef 3.0
Base: koef 2.5

Final: 2.5 × 3.0 × 2.0 × 1.5 = 22.5

But if intermediate results rounded:
Step 1: 2.5 × 3.0 = 7.5
Step 2: 7.5 × 2.0 = 15.0
Step 3: 15.0 × 1.5 = 22.5 ✅ OK

Step 1: 2.5 × 3.0 = 7.500000
Step 2: quantize_half_up(7.500000, 6dp) = 7.500000
Step 3: 7.500000 × 2.0 = 15.000000
Step 4: quantize_half_up(15.000000, 6dp) = 15.000000
Step 5: 15.000000 × 1.5 = 22.500000
Step 6: quantize_half_up(22.500000, 6dp) = 22.500000 ✅ OK

But if:
Step 1: 2.5 × 3.0 = 7.5
Step 2: quantize_half_up(7.5, 2dp) = 7.50  ← Premature rounding
Step 3: 7.50 × 2.0 = 15.00
Step 4: 15.00 × 1.5 = 22.50 ✅ Still OK
```

**Current Implementation:**
- Uses Decimal throughout
- Quantizes only at final save (6 dp)
- ✅ Should be OK (no precision loss)

**Recommendation:**
- ✅ Keep using Decimal
- ✅ Quantize only at final save
- ✅ Add test for precision (10-level nested bundle)

---

### 🟢 Issue #4: UI Feedback for Expansion

**Problem:**
- User tidak tahu bundle will be expanded saat save
- Surprise saat reload (LAIN row hilang, diganti komponen)

**Current UI:**
```
Before Save:
┌─────────────────────────────┐
│ LAIN                        │
├──┬──────────────────────────┤
│1 │ [Bundle] B002 - Job B    │
└──┴──────────────────────────┘

After Save:
┌─────────────────────────────┐
│ TK                          │
├──┬──────────────────────────┤
│1 │ Pekerja                  │ ← Surprise!
└──┴──────────────────────────┘
```

**Recommendation:**
- Add info tooltip di Bundle tag:
  ```html
  <span class="tag-bundle" title="Bundle will be expanded to individual components when saved">
    Bundle
  </span>
  ```

- Add confirmation dialog saat save jika ada bundle:
  ```javascript
  if (hasBundleRows) {
      const confirmed = confirm(
          "⚠️ Anda memiliki item Bundle.\n\n" +
          "Bundle akan di-expand menjadi komponen individual saat save.\n\n" +
          "Lanjutkan?"
      );
      if (!confirmed) return;
  }
  ```

---

## 4. Test Cases

### 4.1 Test Suite: test_template_ahsp_bundle.py

**Status:** ✅ COMPREHENSIVE (21 tests, 1064 lines)

**Coverage:**
1. Circular Dependency Detection (4 tests)
2. Bundle Validation (4 tests)
3. Recursive Expansion (4 tests)
4. API Endpoints (4 tests)
5. Rekap Computation (3 tests)
6. Database Constraints (2 tests)

---

### 4.2 Manual Test Cases (NEED EXECUTION)

#### Test Case 1: Simple Bundle (1-Level)

**Setup:**
```
Pekerjaan B:
├─ TK.001: Pekerja (koef 2.5)
└─ BHN.001: Semen (koef 10.0)

Pekerjaan A (CUSTOM):
└─ LAIN: [Bundle] B (koef 2.0)
```

**Steps:**
1. Login, pilih project
2. Open Template AHSP
3. Select Pekerjaan A (CUSTOM)
4. Add row di segment LAIN
5. Select "Pekerjaan B" dari dropdown
6. Set koefisien = 2.0
7. Save

**Expected Result:**
```
Pekerjaan A (setelah save & reload):
├─ TK.001: Pekerja (koef 5.0)      ← 2.5 × 2.0
└─ BHN.001: Semen (koef 20.0)      ← 10.0 × 2.0
└─ LAIN: (empty)                   ← Bundle expanded
```

**Validation:**
- [ ] LAIN row hilang (di-expand)
- [ ] TK.001 muncul dengan koef 5.0
- [ ] BHN.001 muncul dengan koef 20.0
- [ ] No errors in console
- [ ] Database DetailAHSPProject:
  ```sql
  SELECT kategori, kode, koefisien, ref_pekerjaan_id
  FROM detail_ahsp_project
  WHERE pekerjaan_id = A.id;

  -- Expected:
  -- TK   | TK.001  | 5.000000  | NULL
  -- BHN  | BHN.001 | 20.000000 | NULL
  ```

---

#### Test Case 2: Nested Bundle (2-Level)

**Setup:**
```
Pekerjaan C (base):
├─ ALT.001: Excavator (koef 1.5)

Pekerjaan B (intermediate):
├─ TK.001: Pekerja (koef 2.5)
└─ LAIN: [Bundle] C (koef 3.0)

Pekerjaan A (top):
└─ LAIN: [Bundle] B (koef 2.0)
```

**Steps:**
1. Login, pilih project
2. Open Template AHSP
3. Select Pekerjaan A (CUSTOM)
4. Add row di segment LAIN
5. Select "Pekerjaan B" dari dropdown
6. Set koefisien = 2.0
7. Save

**Expected Result:**
```
Pekerjaan A (setelah save & reload):
├─ TK.001: Pekerja (koef 5.0)       ← 2.5 × 2.0
└─ ALT.001: Excavator (koef 9.0)    ← 1.5 × 3.0 × 2.0
```

**Validation:**
- [ ] Nested bundle expanded correctly
- [ ] TK.001 koef = 5.0
- [ ] ALT.001 koef = 9.0 (not 4.5!)
- [ ] No LAIN rows remaining

---

#### Test Case 3: Self-Reference (Should FAIL)

**Setup:**
```
Pekerjaan A (CUSTOM):
└─ LAIN: [Bundle] A (self-reference)
```

**Steps:**
1. Login, pilih project
2. Open Template AHSP
3. Select Pekerjaan A (CUSTOM)
4. Add row di segment LAIN
5. Select "Pekerjaan A" (self) dari dropdown
6. Save

**Expected Result:**
```
❌ Error 400:
{
  "ok": false,
  "errors": [{
    "field": "rows[0].ref_id",
    "message": "Pekerjaan tidak boleh mereferensi diri sendiri"
  }]
}
```

**Validation:**
- [ ] Error message clear
- [ ] No data saved
- [ ] Frontend shows error toast

---

#### Test Case 4: Circular Dependency (Should FAIL)

**Setup:**
```
Pekerjaan A:
└─ LAIN: [Bundle] B (already saved)

Pekerjaan B:
└─ LAIN: [Bundle] A ← Try to save this
```

**Steps:**
1. Login, pilih project
2. Open Template AHSP
3. Select Pekerjaan B (CUSTOM)
4. Add row di segment LAIN
5. Select "Pekerjaan A" dari dropdown
6. Save

**Expected Result:**
```
❌ Error 400:
{
  "ok": false,
  "errors": [{
    "field": "rows[0].ref_id",
    "message": "Circular dependency detected: A → B → A"
  }]
}
```

**Validation:**
- [ ] Error message clear
- [ ] No data saved
- [ ] Frontend shows error toast

---

#### Test Case 5: Update Source Pekerjaan (Edge Case)

**Setup:**
```
Initial State:
Pekerjaan B:
├─ TK.001: Pekerja (koef 2.5)

Pekerjaan A:
└─ LAIN: [Bundle] B (koef 2.0)
└─ (After save) TK.001: Pekerja (koef 5.0)

Then update Pekerjaan B:
Pekerjaan B:
├─ TK.001: Pekerja (koef 3.0) ← Changed from 2.5 to 3.0
```

**Steps:**
1. Save Pekerjaan A with bundle B (koef 2.0)
2. Verify A has TK.001 (koef 5.0)
3. Edit Pekerjaan B, change TK.001 koef to 3.0, save
4. Reload Pekerjaan A (WITHOUT re-saving A)
5. Check A's TK.001 koef

**Expected Result:**
```
Pekerjaan A:
├─ TK.001: Pekerja (koef 5.0) ← Still old value!
```

**Validation:**
- [ ] A still has old koef (5.0, not 6.0)
- [ ] Changes in B NOT automatically reflected in A
- [ ] This is EXPECTED behavior (expansion during save)
- [ ] User must manually re-save A to update

**Recommendation:**
- Add warning in UI
- Add "Refresh Bundle" feature (future)

---

#### Test Case 6: Max Depth Limit (Should FAIL at 11 levels)

**Setup:**
```
Pekerjaan L11 → L10 → L9 → ... → L2 → L1 → Base

Try to save L11.
```

**Steps:**
1. Create 11-level nested bundle
2. Save top-level pekerjaan

**Expected Result:**
```
❌ Error 400:
{
  "ok": false,
  "errors": [{
    "message": "Maksimum kedalaman bundle terlampaui (max 10)"
  }]
}
```

**Validation:**
- [ ] Error at depth > 10
- [ ] No data saved
- [ ] Clear error message

---

## 5. Recommendations

### 5.1 High Priority

#### 1. ✅ DONE - Circular Dependency Detection
- **Status:** Implemented (BFS algorithm)
- **Test Coverage:** 4 tests
- **Verified:** ✅

#### 2. ✅ DONE - Bundle Expansion Implementation
- **Status:** Implemented (recursive expansion)
- **Test Coverage:** 4 tests
- **Verified:** ✅

#### 3. ⏳ PENDING - Data Migration for Old Bundles

**Task:** Migrate old LAIN bundle data (ref_pekerjaan_id) to expanded format

**Script:**
```python
# management/commands/migrate_old_bundles.py

from django.core.management.base import BaseCommand
from detail_project.models import DetailAHSPProject, Pekerjaan
from detail_project.services import expand_bundle_recursive
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Migrate old bundle data (LAIN with ref_pekerjaan_id) to expanded format'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Find old bundle data
        old_bundles = DetailAHSPProject.objects.filter(
            kategori='LAIN',
            ref_pekerjaan__isnull=False
        ).select_related('project', 'pekerjaan')

        total = old_bundles.count()
        self.stdout.write(f"Found {total} old bundle rows")

        for bundle in old_bundles:
            project = bundle.project
            pekerjaan = bundle.pekerjaan

            self.stdout.write(f"Migrating bundle: {pekerjaan.id} - {bundle.kode}")

            # Expand bundle
            try:
                detail_dict = {
                    'kategori': 'LAIN',
                    'kode': bundle.kode,
                    'uraian': bundle.uraian,
                    'satuan': bundle.satuan,
                    'koefisien': str(bundle.koefisien),
                    'ref_pekerjaan_id': bundle.ref_pekerjaan_id,
                }

                expanded = expand_bundle_recursive(
                    detail_dict=detail_dict,
                    base_koefisien=Decimal('1.0'),
                    project=project,
                )

                if not dry_run:
                    # Delete old bundle row
                    bundle.delete()

                    # Create expanded components
                    for kategori, kode, uraian, satuan, koef, _ in expanded:
                        hip = _upsert_harga_item(project, kategori, kode, uraian, satuan)
                        DetailAHSPProject.objects.create(
                            project=project,
                            pekerjaan=pekerjaan,
                            harga_item=hip,
                            kategori=kategori,
                            kode=kode,
                            uraian=uraian,
                            satuan=satuan,
                            koefisien=koef,
                        )

                    self.stdout.write(self.style.SUCCESS(f"  ✅ Migrated to {len(expanded)} components"))
                else:
                    self.stdout.write(f"  [DRY RUN] Would expand to {len(expanded)} components")

            except Exception as e:
                logger.error(f"Failed to migrate bundle {bundle.id}: {e}")
                self.stdout.write(self.style.ERROR(f"  ❌ Error: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Migration complete: {total} bundles processed"))
```

**Run:**
```bash
# Dry run first
python manage.py migrate_old_bundles --dry-run

# Actually migrate
python manage.py migrate_old_bundles
```

---

#### 4. ⏳ PENDING - UI Improvements

**A. Add Bundle Expansion Warning**

**Location:** `template_ahsp.js` save handler

```javascript
// Before save
$('#ta-btn-save').addEventListener('click', () => {
    const rows = gatherRows();
    const bundleRows = rows.filter(r =>
        r.kategori === 'LAIN' && (r.ref_kind || r.ref_ahsp_id)
    );

    if (bundleRows.length > 0) {
        const confirmed = confirm(
            `⚠️ Anda memiliki ${bundleRows.length} item Bundle.\n\n` +
            `Bundle akan di-expand menjadi komponen individual saat save.\n\n` +
            `Perubahan di pekerjaan sumber tidak akan otomatis update.\n\n` +
            `Lanjutkan?`
        );
        if (!confirmed) return;
    }

    // Continue with save...
});
```

**B. Add Bundle Tag Tooltip**

**Location:** `template_ahsp.js:329`

```javascript
if (kodeTd && !kodeTd.querySelector('.tag-bundle')) {
    kodeTd.insertAdjacentHTML('beforeend',
        ' <span class="tag-bundle" ' +
        'title="Bundle will be expanded to components when saved. ' +
        'Changes in source pekerjaan won\'t auto-update.">' +
        'Bundle</span>'
    );
}
```

---

### 5.2 Medium Priority

#### 5. Add "Refresh Bundle" Feature (Future)

**Purpose:** Allow user to re-expand bundle if source changed

**UI:**
```
┌─────────────────────────────────────────┐
│ Pekerjaan A                             │
│ Source: Kustom                          │
├─────────────────────────────────────────┤
│ ⚠️ This pekerjaan contains expanded    │
│    bundle from: Pekerjaan B             │
│                                         │
│ [🔄 Refresh Bundle from Source]        │
└─────────────────────────────────────────┘
```

**Implementation:**
- Track bundle source in metadata
- Add button to re-expand
- Show diff before applying

---

#### 6. Add Bundle Preview (Future)

**Purpose:** Show what will be expanded before save

**UI:**
```
┌─────────────────────────────────────────┐
│ LAIN                                    │
├──┬──────────────────────────────────────┤
│1 │ [Bundle] B002 - Job B (koef 2.0)    │
│  │                                      │
│  │ [👁️ Preview Expansion]              │
│  │                                      │
│  │ Will expand to:                      │
│  │ ├─ TK.001: Pekerja (5.0)            │
│  │ └─ BHN.001: Semen (20.0)            │
└──┴──────────────────────────────────────┘
```

---

## 📞 Discussion Points

### Point 1: Expansion Timing

**Question:** Should we keep "expansion during save" or switch to "expansion during rekap"?

**Current:** Expansion during save
**Alternative:** Expansion during rekap (on-the-fly)

**Trade-offs:**
| Aspect | During Save | During Rekap |
|--------|-------------|--------------|
| Performance | ✅ Faster rekap | ❌ Slower rekap |
| Data accuracy | ❌ Stale if source changes | ✅ Always up-to-date |
| Database size | ❌ Larger (expanded data) | ✅ Smaller (only bundle ref) |
| Debugging | ✅ Easier (see expanded data) | ❌ Harder (computed) |
| User experience | ⚠️ Needs manual refresh | ✅ Auto-sync |

**Recommendation:** **Keep current approach**, add "Refresh Bundle" feature

---

### Point 2: Backward Compatibility

**Question:** How to handle old bundle data (ref_pekerjaan_id in LAIN)?

**Options:**
1. **Data migration** - Expand all old bundles to new format
2. **Dual support** - Handle both formats in rekap
3. **Force re-save** - Ask users to re-save all pekerjaan

**Recommendation:** **Data migration** (safest, cleanest)

---

### Point 3: UI Feedback

**Question:** How to improve user understanding of bundle expansion?

**Options:**
1. **Confirmation dialog** before save
2. **Info tooltip** on Bundle tag
3. **Preview expansion** feature
4. **Diff view** after save

**Recommendation:** Implement **#1 and #2** immediately, **#3** as future enhancement

---

**Status:** ⚠️ READY FOR DISCUSSION
**Next Steps:**
1. Review this document
2. Execute manual test cases
3. Discuss expansion timing strategy
4. Implement UI improvements
5. Run data migration (if needed)
