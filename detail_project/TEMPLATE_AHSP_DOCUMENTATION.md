# Template AHSP - Complete Documentation & Analysis

**Created:** 2025-11-08
**Status:** COMPREHENSIVE ANALYSIS
**Purpose:** Document Template AHSP data flow, database interactions, and potential bugs

---

## 📋 TABLE OF CONTENTS

1. [Overview](#overview)
2. [Input & Data Flow](#input--data-flow)
3. [Database Schema](#database-schema)
4. [API Endpoints](#api-endpoints)
5. [Frontend Logic](#frontend-logic)
6. [Database Interactions](#database-interactions)
7. [Potential Bugs & Issues](#potential-bugs--issues)
8. [Race Conditions](#race-conditions)
9. [Recommendations](#recommendations)

---

## 1. OVERVIEW

Template AHSP adalah halaman untuk mengelola rincian/detail AHSP (Analisa Harga Satuan Pekerjaan) per pekerjaan. Setiap pekerjaan memiliki komponen yang terdiri dari:
- **TK** (Tenaga Kerja)
- **BHN** (Bahan)
- **ALT** (Alat)
- **LAIN** (Lain-lain / Pekerjaan Gabungan)

### Key Features:
1. **Read-only mode** untuk pekerjaan source_type = 'ref'
2. **Editable mode** untuk source_type = 'custom' atau 'ref_modified'
3. **Bundle support** - kategori LAIN dapat mereferensi AHSP lain atau Pekerjaan lain
4. **Auto-upsert HargaItemProject** - sinkronisasi otomatis master harga

---

## 2. INPUT & DATA FLOW

### 2.1 User Input (Frontend)

**Entry Point:** `template_ahsp.html`

**User Actions:**
1. Select pekerjaan dari sidebar kiri
2. Add row baru (per segment: TK/BHN/ALT/LAIN)
3. Edit data di row:
   - Uraian (contenteditable div)
   - Kode (input text)
   - Satuan (input text)
   - Koefisien (input numeric with auto-format)
4. Select dari dropdown Select2 (khusus segment LAIN)
5. Click "Simpan" button

**Input Format:**
```javascript
// Frontend sends this payload to backend:
{
  "rows": [
    {
      "kategori": "TK",        // Required: TK|BHN|ALT|LAIN
      "kode": "L.01",          // Required
      "uraian": "Pekerja",     // Required
      "satuan": "OH",          // Optional
      "koefisien": "1.000000", // Required, formatted locale id-ID
      "ref_ahsp_id": null      // Optional, only for LAIN + custom
    },
    ...
  ]
}
```

---

### 2.2 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INPUT                               │
│  (sidebar select + row editing + save button)                   │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (template_ahsp.js)                   │
│                                                                  │
│  1. gatherRows() - collect data from DOM                        │
│  2. validateClient() - check required fields & duplicates       │
│  3. Canonicalize koefisien: "1,234567" → "1.234567"            │
│  4. POST to /api/.../detail-ahsp/{pekerjaan_id}/save/          │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              BACKEND (views_api.py)                              │
│           api_save_detail_ahsp_for_pekerjaan()                  │
│                                                                  │
│  1. Parse JSON payload                                          │
│  2. Validate:                                                   │
│     - kategori in ['TK','BHN','ALT','LAIN']                    │
│     - kode, uraian not empty                                   │
│     - koefisien >= 0                                           │
│     - kode unique per pekerjaan                                │
│     - ref_ahsp_id only for custom.LAIN                         │
│  3. For each row:                                               │
│     a. Call _upsert_harga_item() → get/create HargaItemProject │
│     b. Create DetailAHSPProject with FK to HargaItemProject    │
│  4. Replace-all strategy: DELETE old + INSERT new              │
│  5. Set pekerjaan.detail_ready = True if rows > 0              │
│  6. Invalidate rekap cache                                     │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATABASE OPERATIONS                           │
│                                                                  │
│  1. services._upsert_harga_item():                              │
│     - get_or_create HargaItemProject by (project, kode_item)   │
│     - Update kategori, uraian, satuan if changed               │
│                                                                  │
│  2. DetailAHSPProject.objects.filter().delete()                 │
│     - Delete all existing rows for this pekerjaan              │
│                                                                  │
│  3. DetailAHSPProject.objects.bulk_create()                     │
│     - Insert all new rows                                       │
│                                                                  │
│  4. Pekerjaan.objects.update(detail_ready=True)                 │
│                                                                  │
│  5. cache.delete(f"rekap:{project_id}:v2")                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. DATABASE SCHEMA

### 3.1 Core Models

#### **Pekerjaan**
```python
class Pekerjaan(TimeStampedModel):
    SOURCE_REF = 'ref'           # Read-only dari referensi
    SOURCE_CUSTOM = 'custom'     # User-created
    SOURCE_REF_MOD = 'ref_modified'  # Modified dari referensi

    project = FK(Project)
    sub_klasifikasi = FK(SubKlasifikasi)
    source_type = CharField(choices=SOURCE_CHOICES)
    ref = FK(AHSPReferensi, null=True)  # Pointer ke referensi

    snapshot_kode = CharField(100)
    snapshot_uraian = TextField()
    snapshot_satuan = CharField(50)

    auto_load_rincian = BooleanField(default=True)
    detail_ready = BooleanField(default=False)  # True jika ada ≥1 detail valid

    markup_override_percent = DecimalField(null=True)  # Override profit/margin
```

**Key Points:**
- `source_type` menentukan mode edit:
  - `ref` → READ-ONLY (data dari RincianReferensi)
  - `custom` → EDITABLE (data di DetailAHSPProject)
  - `ref_modified` → EDITABLE (clone dari ref, bisa di-reset)
- `detail_ready` = True jika minimal 1 row DetailAHSPProject valid

---

#### **HargaItemProject** (Master Harga)
```python
class HargaItemProject(TimeStampedModel):
    KATEGORI_CHOICES = [
        ('TK', 'Tenaga Kerja'),
        ('BHN', 'Bahan'),
        ('ALT', 'Alat'),
        ('LAIN', 'Lain-lain'),
    ]

    project = FK(Project)
    kode_item = CharField(100)        # UNIQUE per project
    satuan = CharField(50, null=True)
    uraian = TextField()
    kategori = CharField(10, choices=KATEGORI_CHOICES)
    harga_satuan = DecimalField(18, 2, null=True)  # Bisa kosong awal

    class Meta:
        constraints = [
            UniqueConstraint(fields=["project", "kode_item"],
                           name="uniq_harga_kode_per_project")
        ]
```

**Key Points:**
- **MASTER TABLE** - 1 row per unique kode_item per project
- **Auto-upsert** via `_upsert_harga_item()` saat save detail AHSP
- `harga_satuan` diisi di halaman "Harga Items" (terpisah)
- Tidak boleh duplikat `kode_item` dalam 1 project

---

#### **DetailAHSPProject** (Rincian AHSP)
```python
class DetailAHSPProject(TimeStampedModel):
    project = FK(Project)
    pekerjaan = FK(Pekerjaan, related_name='detail_list')

    harga_item = FK(HargaItemProject, on_delete=PROTECT)  # FK ke master
    kategori = CharField(10, choices=KATEGORI_CHOICES)
    kode = CharField(100)
    uraian = TextField()
    satuan = CharField(50, null=True)
    koefisien = DecimalField(18, 6)  # 6 decimal places

    # Bundle support (kategori LAIN only)
    ref_ahsp = FK(AHSPReferensi, null=True, on_delete=PROTECT)

    class Meta:
        unique_together = ("project", "pekerjaan", "kode")
        constraints = [
            CheckConstraint(
                name="ref_ahsp_only_for_lain",
                condition=Q(ref_ahsp__isnull=True) | Q(kategori='LAIN')
            )
        ]
```

**Key Points:**
- **DETAIL TABLE** - many rows per pekerjaan
- `harga_item` adalah FK ke `HargaItemProject` (auto-upserted)
- `ref_ahsp` hanya boleh diisi jika `kategori='LAIN'` (enforced by constraint)
- `kode` harus unique per pekerjaan (bisa sama antar pekerjaan berbeda)
- `koefisien` disimpan dengan 6 decimal places, rounded HALF_UP

---

### 3.2 Database Relationships

```
Project (1) ─┬─ (many) Pekerjaan
             │         │
             │         ├─ (many) DetailAHSPProject ─┬─ (1) HargaItemProject
             │         │                            │
             │         │                            └─ (1) AHSPReferensi (optional, LAIN only)
             │         │
             │         └─ (1) VolumePekerjaan
             │
             └─ (many) HargaItemProject (master harga)
```

**Important Notes:**
1. **HargaItemProject is shared** - Multiple DetailAHSPProject dapat reference 1 HargaItemProject
2. **Auto-upsert pattern** - `_upsert_harga_item()` ensures HargaItemProject exists
3. **ON DELETE PROTECT** - Cannot delete HargaItemProject if referenced by DetailAHSPProject

---

## 4. API ENDPOINTS

### 4.1 GET Detail AHSP

**Endpoint:** `GET /api/project/{project_id}/detail-ahsp/{pekerjaan_id}/`

**Handler:** `api_get_detail_ahsp()`

**Logic:**
```python
1. Check pekerjaan exists & belongs to project
2. Determine source_type and read_only flag
3. If has DetailAHSPProject records:
   - Return from DetailAHSPProject (with harga_satuan from HargaItemProject)
4. Else if source_type == 'ref' (fallback):
   - Return from RincianReferensi (read-only)
5. Return JSON with items, meta, read_only flag
```

**Response Format:**
```json
{
  "ok": true,
  "pekerjaan": {
    "id": 123,
    "kode": "1.1.1",
    "uraian": "Galian Tanah",
    "satuan": "m3",
    "source_type": "custom",
    "detail_ready": true
  },
  "items": [
    {
      "id": 456,
      "kategori": "TK",
      "kode": "L.01",
      "uraian": "Pekerja",
      "satuan": "OH",
      "koefisien": "1.000000",
      "ref_ahsp_id": null,
      "harga_satuan": "150000.00"
    }
  ],
  "meta": {
    "kategori_opts": [...],
    "read_only": false
  }
}
```

---

### 4.2 SAVE Detail AHSP

**Endpoint:** `POST /api/project/{project_id}/detail-ahsp/{pekerjaan_id}/save/`

**Handler:** `api_save_detail_ahsp_for_pekerjaan()`

**Validations:**
1. **Source type check:** Reject if source_type == 'ref'
2. **Kategori valid:** Must be in ['TK', 'BHN', 'ALT', 'LAIN']
3. **Required fields:** kode, uraian not empty
4. **Koefisien valid:** Must be >= 0 and numeric
5. **Kode unique:** No duplicate kode within same pekerjaan
6. **Bundle restriction:** ref_ahsp_id only for custom + LAIN
7. **ref_ahsp exists:** If ref_ahsp_id provided, must exist in AHSPReferensi

**Logic:**
```python
@transaction.atomic
def api_save_detail_ahsp_for_pekerjaan():
    1. Parse & validate all rows
    2. For each valid row:
       a. _upsert_harga_item(project, kat, kode, uraian, satuan)
       b. Build DetailAHSPProject instance
    3. DELETE all old DetailAHSPProject for this pekerjaan
    4. BULK_CREATE all new DetailAHSPProject
    5. UPDATE pekerjaan.detail_ready = (len(rows) > 0)
    6. invalidate_rekap_cache(project)
    7. Return success/partial success
```

**Response:**
```json
{
  "ok": true,
  "saved_rows": 15,
  "errors": []
}
```

Or with errors:
```json
{
  "ok": false,
  "saved_rows": 10,
  "errors": [
    {"path": "rows[3].koefisien", "message": "Wajib"},
    {"path": "rows[5].kode", "message": "Kode duplikat"}
  ]
}
```

---

### 4.3 RESET Detail AHSP (ref_modified only)

**Endpoint:** `POST /api/project/{project_id}/detail-ahsp/{pekerjaan_id}/reset-to-ref/`

**Handler:** `api_reset_detail_ahsp_to_ref()`

**Logic:**
```python
@transaction.atomic
def api_reset_detail_ahsp_to_ref():
    1. Check source_type == 'ref_modified' (only this can reset)
    2. Check ref pointer exists
    3. DELETE all DetailAHSPProject for this pekerjaan
    4. Clone ref via clone_ref_pekerjaan() to TEMP pekerjaan
    5. Move DetailAHSPProject from TEMP to original pekerjaan
    6. DELETE TEMP pekerjaan
    7. invalidate_rekap_cache(project)
```

**Use Case:** User modified AHSP dari referensi, tapi ingin revert ke original.

---

## 5. FRONTEND LOGIC

### 5.1 Key Functions (template_ahsp.js)

#### **gatherRows()**
```javascript
function gatherRows() {
  const segs = ['TK','BHN','ALT','LAIN'];
  const out = [];
  segs.forEach(seg => {
    $('#seg-${seg}-body').querySelectorAll('tr.ta-row').forEach(tr => {
      const base = {
        kategori: seg,
        uraian: $('.cell-wrap', tr).textContent.trim(),
        kode: $('input[data-field="kode"]', tr).value.trim(),
        satuan: $('input[data-field="satuan"]', tr).value.trim(),
        koefisien: normKoefStrToSend($('input[data-field="koefisien"]', tr).value),
      };

      // Bundle support (LAIN + custom only)
      if (seg === 'LAIN' && activeSource === 'custom') {
        const rk = $('input[data-field="ref_kind"]', tr).value.trim();
        const rid = $('input[data-field="ref_id"]', tr).value.trim();
        if (rk && rid) {
          base.ref_kind = rk;
          base.ref_id = rid;
        } else {
          const refId = $('input[data-field="ref_ahsp_id"]', tr).value.trim();
          if (refId) base.ref_ahsp_id = refId;
        }
      }
      out.push(base);
    });
  });
  return out;
}
```

**Key Points:**
- Iterates TK → BHN → ALT → LAIN in order
- Collects all fields from DOM
- Bundle fields (ref_kind, ref_id, ref_ahsp_id) only for LAIN segment

---

#### **validateClient()**
```javascript
function validateClient(rows) {
  const errors = [];
  const seen = new Set();
  rows.forEach((r, i) => {
    if (!r.uraian) errors.push({path:`rows[${i}].uraian`, message:'Wajib'});
    if (!r.kode) errors.push({path:`rows[${i}].kode`, message:'Wajib'});

    const key = r.kode;
    if (key) {
      if (seen.has(key)) errors.push({path:`rows[${i}].kode`, message:'Kode duplikat'});
      seen.add(key);
    }

    if (r.koefisien === '' || r.koefisien == null) {
      errors.push({path:`rows[${i}].koefisien`, message:'Wajib'});
    }
  });
  return errors;
}
```

**Validations:**
1. ✅ Uraian wajib
2. ✅ Kode wajib
3. ✅ Koefisien wajib
4. ✅ Kode unique (no duplicates)

**Missing Validations:**
- ❌ Kategori valid (assumed from segment)
- ❌ Koefisien numeric & >= 0 (done in backend)

---

#### **enhanceLAINAutocomplete()**
```javascript
function enhanceLAINAutocomplete(scopeEl) {
  // Setup Select2 for kode input in LAIN segment
  $input.select2({
    ajax: {
      url: endpoints.searchAhsp,
      delay: 250,
      data: params => ({ q: params.term }),
      processResults: (data, params) => {
        const remote = data.results.map(x => ({
          id: `ahsp:${x.id}`,
          text: `${x.kode_ahsp} — ${x.nama_ahsp}`,
          kode_ahsp: x.kode_ahsp,
          nama_ahsp: x.nama_ahsp,
          satuan: x.satuan
        }));
        const local = localProjectOptions(params.term);
        return { results: [...local, ...remote] };
      }
    }
  });

  $input.on('select2:select', (e) => {
    const d = e.params.data;
    let kind = 'ahsp';
    let refId = '';

    if (d.id.startsWith('job:')) {
      kind = 'job';
      refId = d.id.split(':')[1];
    } else {
      kind = 'ahsp';
      refId = d.id.split(':')[1];
    }

    input.value = d.kode_ahsp || d.kode_job;
    $('.cell-wrap', tr).textContent = d.nama_ahsp || d.nama_job;
    $('input[data-field="satuan"]', tr).value = d.satuan;
    $('input[data-field="ref_kind"]', tr).value = kind;
    $('input[data-field="ref_id"]', tr).value = refId;

    // FIX: Set default koefisien
    const koefInput = $('input[data-field="koefisien"]', tr);
    if (!koefInput.value.trim()) {
      koefInput.value = __koefToUI('1.000000');
    }
  });
}
```

**Key Points:**
- Select2 provides autocomplete untuk segment LAIN
- Sources: AHSPReferensi (remote) + Pekerjaan proyek (local)
- Auto-fill: kode, uraian, satuan, ref_kind, ref_id
- **FIX Applied:** Auto-fill koefisien = 1 if empty

---

### 5.2 Row Template

```html
<template id="ta-row-template">
  <tr class="ta-row">
    <td class="col-no"><span class="row-index">1</span></td>

    <td class="col-uraian">
      <div class="cell-wrap" contenteditable="true" data-field="uraian"></div>
    </td>

    <td class="col-kode">
      <input type="text" class="cell-input mono" data-field="kode">
      <input type="hidden" data-field="ref_ahsp_id">
      <input type="hidden" data-field="ref_kind">
      <input type="hidden" data-field="ref_id">
    </td>

    <td class="col-satuan">
      <input type="text" class="cell-input" data-field="satuan">
    </td>

    <td class="col-koef">
      <input type="text" class="cell-input num" data-field="koefisien" inputmode="decimal">
    </td>
  </tr>
</template>
```

**Key Points:**
- Uraian uses `contenteditable` div (allows multi-line, rich text)
- Hidden fields for bundle reference (ref_ahsp_id, ref_kind, ref_id)
- Koefisien has `inputmode="decimal"` for mobile numeric keyboard
- **No default value** for koefisien → **FIXED** via JS

---

## 6. DATABASE INTERACTIONS

### 6.1 _upsert_harga_item() Function

**Location:** `services.py:48-65`

```python
def _upsert_harga_item(project, kategori: str, kode_item: str, uraian: str, satuan: str | None):
    """
    Upsert master harga unik per proyek (tanpa mengubah harga_satuan).
    """
    obj, _created = HargaItemProject.objects.get_or_create(
        project=project,
        kode_item=kode_item,
        defaults=dict(kategori=kategori, uraian=uraian, satuan=satuan)
    )
    changed = False
    if obj.kategori != kategori:
        obj.kategori = kategori; changed = True
    if uraian and obj.uraian != uraian:
        obj.uraian = uraian; changed = True
    if (satuan or None) != obj.satuan:
        obj.satuan = satuan or None; changed = True
    if changed:
        obj.save(update_fields=["kategori", "uraian", "satuan", "updated_at"])
    return obj
```

**Logic:**
1. **get_or_create** by (project, kode_item)
2. If created → set defaults (kategori, uraian, satuan)
3. If exists → update kategori, uraian, satuan if different
4. **NEVER touches harga_satuan** (managed separately in Harga Items page)

**Why Upsert?**
- Same kode_item might be used across multiple pekerjaan
- Ensures HargaItemProject exists before creating DetailAHSPProject
- Keeps metadata (uraian, satuan) in sync with latest usage

---

### 6.2 Save Transaction Flow

```python
@transaction.atomic
def api_save_detail_ahsp_for_pekerjaan():
    # 1. Validate all rows first
    for i, r in enumerate(rows):
        hip = _upsert_harga_item(project, kat, kode, uraian, satuan)
        # Store FK reference

    # 2. DELETE all old rows
    DetailAHSPProject.objects.filter(project=project, pekerjaan=pkj).delete()

    # 3. BULK CREATE all new rows
    to_create = [DetailAHSPProject(...) for each validated row]
    DetailAHSPProject.objects.bulk_create(to_create, ignore_conflicts=True)

    # 4. UPDATE pekerjaan metadata
    Pekerjaan.objects.filter(pk=pkj.pk).update(detail_ready=(len(to_create) > 0))

    # 5. Invalidate cache
    invalidate_rekap_cache(project)
```

**Key Points:**
- **@transaction.atomic** - All-or-nothing operation
- **Replace-all strategy** - DELETE old + INSERT new (not UPDATE)
- **bulk_create** - Efficient for multiple rows
- **ignore_conflicts=True** - Skip if unique constraint violated (shouldn't happen)

---

### 6.3 Query Patterns

#### **Load Detail (GET)**
```python
qs = (DetailAHSPProject.objects
      .filter(project=project, pekerjaan=pkj)
      .select_related('harga_item')  # Join HargaItemProject
      .order_by('kategori', 'id')
      .values('id', 'kategori', 'kode', 'uraian', 'satuan', 'koefisien',
              'ref_ahsp_id', 'harga_item__harga_satuan'))
```

**Performance:**
- ✅ `select_related('harga_item')` - Avoids N+1 queries
- ✅ `values()` - Returns dict instead of model instances (faster)
- ✅ Indexed by (project, pekerjaan) - Fast filter

---

#### **Upsert Harga Item**
```python
obj, _created = HargaItemProject.objects.get_or_create(
    project=project,
    kode_item=kode_item,
    defaults=dict(kategori=kategori, uraian=uraian, satuan=satuan)
)
```

**Performance:**
- ✅ Uses UNIQUE constraint (project, kode_item) - Fast lookup
- ⚠️ **Called N times** for N rows - Could be optimized with bulk lookup

---

#### **Delete Old Rows**
```python
DetailAHSPProject.objects.filter(project=project, pekerjaan=pkj).delete()
```

**Performance:**
- ✅ Single DELETE query
- ✅ Indexed by (project, pekerjaan)

---

#### **Bulk Create New Rows**
```python
DetailAHSPProject.objects.bulk_create(to_create, ignore_conflicts=True)
```

**Performance:**
- ✅ Single INSERT query (or batched if > 1000 rows)
- ✅ Much faster than N individual saves

---

## 7. POTENTIAL BUGS & ISSUES

### 7.1 🐛 BUG: Missing Koefisien Default (FIXED)

**Status:** ✅ FIXED (commit fcff3f1)

**Description:**
- Row template had no default koefisien value
- User could add row without filling koefisien
- Validation would fail with generic error message

**Impact:**
- User confusion - unclear what field is missing
- Poor UX - multiple failed save attempts

**Fix Applied:**
```javascript
// template_ahsp.js:428-430
const koefInput = $('input[data-field="koefisien"]', tr);
if (koefInput) koefInput.value = __koefToUI('1.000000');
```

---

### 7.2 🐛 ISSUE: kategori Can Mismatch Between Tables

**Status:** ⚠️ POTENTIAL BUG

**Scenario:**
```
1. User creates detail with kategori='TK', kode='L.01'
2. HargaItemProject created with kategori='TK'
3. User later changes same kode to kategori='BHN' in different pekerjaan
4. _upsert_harga_item() UPDATES kategori to 'BHN'
5. Now HargaItemProject.kategori != DetailAHSPProject.kategori for old rows!
```

**Example:**
```sql
-- DetailAHSPProject
pekerjaan_id | kategori | kode  | harga_item_id
1            | TK       | L.01  | 100

-- HargaItemProject (after update)
id  | kategori | kode_item
100 | BHN      | L.01      ← MISMATCH!
```

**Impact:**
- Data inconsistency between tables
- Rekap calculation might use wrong kategori
- Filter by kategori could return wrong items

**Root Cause:**
- HargaItemProject is SHARED across pekerjaan
- kategori is MUTABLE via _upsert_harga_item()
- No validation that all DetailAHSPProject referencing same HargaItemProject have same kategori

**Recommendation:**
```python
# Option 1: Make kategori immutable in HargaItemProject
def _upsert_harga_item():
    obj, created = HargaItemProject.objects.get_or_create(...)
    if created:
        obj.kategori = kategori
    elif obj.kategori != kategori:
        # Raise error instead of updating
        raise ValidationError(f"Kode {kode_item} already exists with kategori {obj.kategori}")
    # ... rest of logic

# Option 2: Include kategori in unique constraint
class HargaItemProject:
    class Meta:
        constraints = [
            UniqueConstraint(fields=["project", "kategori", "kode_item"])
        ]
```

---

### 7.3 🐛 ISSUE: Koefisien Rounding Precision Loss

**Status:** ⚠️ MINOR ISSUE

**Scenario:**
```
1. Backend uses Decimal(18, 6) for koefisien
2. Frontend formats with id-ID locale: "1,234567"
3. User enters: "0,333333" (1/3 repeating)
4. Backend quantizes to 6 dp: 0.333333
5. Calculation: 0.333333 × 3 = 0.999999 (not 1.000000)
```

**Impact:**
- Minor calculation errors accumulate
- Might affect final total by small amounts (< 0.01%)

**Recommendation:**
- Document expected precision (6 dp is industry standard)
- Consider using HALF_UP rounding for final totals
- Current implementation already uses `quantize_half_up()` ✅

---

### 7.4 🐛 ISSUE: Bundle Recursion Not Checked

**Status:** ⚠️ POTENTIAL INFINITE LOOP

**Scenario:**
```
Pekerjaan A (LAIN) references Pekerjaan B
Pekerjaan B (LAIN) references Pekerjaan A
→ Infinite recursion when computing rekap!
```

**Impact:**
- Stack overflow in rekap calculation
- Server crash or timeout

**Current Protection:**
- ❌ No recursion depth check
- ❌ No circular dependency detection

**Recommendation:**
```python
def compute_kebutuhan_items(project, visited=None):
    if visited is None:
        visited = set()

    for detail in details:
        if detail['ref_ahsp_id']:
            if detail['ref_ahsp_id'] in visited:
                logger.error(f"Circular bundle detected: {detail['ref_ahsp_id']}")
                continue  # Skip circular reference
            visited.add(detail['ref_ahsp_id'])
            # ... process bundle
            visited.remove(detail['ref_ahsp_id'])
```

---

### 7.5 🐛 ISSUE: Delete CASCADE Not Protected

**Status:** ⚠️ DATA LOSS RISK

**Scenario:**
```
1. User deletes Pekerjaan
2. ON DELETE CASCADE → all DetailAHSPProject deleted
3. But HargaItemProject still exists (orphaned if no other references)
4. User loses all detail data permanently
```

**Current Protection:**
- ✅ HargaItemProject uses `on_delete=PROTECT` in DetailAHSPProject
- ❌ Pekerjaan uses default `CASCADE` for DetailAHSPProject
- ❌ No soft delete / archival

**Recommendation:**
```python
# Option 1: Add soft delete
class Pekerjaan:
    deleted_at = models.DateTimeField(null=True, blank=True)

    def delete(self):
        self.deleted_at = timezone.now()
        self.save()

# Option 2: Add confirmation with data preview
def delete_pekerjaan_with_confirmation(pekerjaan):
    detail_count = DetailAHSPProject.objects.filter(pekerjaan=pekerjaan).count()
    if detail_count > 0:
        # Show warning: "This will delete {count} detail rows. Continue?"
        pass
```

---

### 7.6 🐛 ISSUE: Race Condition on Concurrent Edits

**Status:** ⚠️ RACE CONDITION

**Scenario:**
```
Time  User A                        User B
T0    GET detail for Pekerjaan 1
T1                                  GET detail for Pekerjaan 1
T2    Edit row 1: koef = 2.0
T3                                  Edit row 1: koef = 3.0
T4    POST save (DELETE + INSERT)
T5                                  POST save (DELETE + INSERT)
→ User A's changes LOST!
```

**Impact:**
- Last write wins (no merge)
- Silent data loss
- No conflict detection

**Recommendation:**
```python
# Option 1: Optimistic locking
class DetailAHSPProject:
    version = models.IntegerField(default=1)

def api_save_detail_ahsp_for_pekerjaan():
    expected_version = payload.get('version')
    current_version = DetailAHSPProject.objects.filter(...).aggregate(Max('version'))
    if expected_version != current_version:
        return JsonResponse({"ok": False, "error": "Data changed by another user"}, status=409)

# Option 2: Row-level timestamps
class DetailAHSPProject:
    updated_at = models.DateTimeField(auto_now=True)

# Frontend checks updated_at before save, warns if stale
```

---

### 7.7 🐛 ISSUE: Missing Transaction Rollback on Partial Failure

**Status:** ✅ HANDLED

**Current Implementation:**
```python
@transaction.atomic
def api_save_detail_ahsp_for_pekerjaan():
    # All DB operations inside transaction
    # If any fails → automatic rollback
```

**Good:**
- ✅ Uses `@transaction.atomic`
- ✅ All-or-nothing behavior
- ✅ If bulk_create fails → DELETE is rolled back

---

## 8. RACE CONDITIONS

### 8.1 🔒 Concurrent Save to Same Pekerjaan

**Scenario:**
```
Thread A: DELETE rows for Pekerjaan 1 → INSERT new rows
Thread B: DELETE rows for Pekerjaan 1 → INSERT new rows
```

**Timeline:**
```
T1: Thread A starts transaction
T2: Thread A deletes rows (holds lock)
T3: Thread B starts transaction
T4: Thread B tries to delete rows (WAITS for Thread A lock)
T5: Thread A inserts rows & commits (releases lock)
T6: Thread B deletes rows (including Thread A's new rows!)
T7: Thread B inserts rows & commits
→ Thread A's data LOST
```

**Django Behavior:**
- Default isolation level: **READ COMMITTED** (PostgreSQL)
- DELETE acquires **ROW EXCLUSIVE LOCK**
- Thread B will WAIT for Thread A to commit
- After commit, Thread B sees Thread A's new rows and deletes them

**Impact:**
- **HIGH** - Silent data loss
- No error raised
- Last transaction wins

**Recommendation:**
```python
# Option 1: SELECT FOR UPDATE
@transaction.atomic
def api_save_detail_ahsp_for_pekerjaan():
    # Acquire exclusive lock on pekerjaan row
    pkj = Pekerjaan.objects.select_for_update().get(id=pekerjaan_id)
    # Now only this transaction can modify detail rows
    DetailAHSPProject.objects.filter(pekerjaan=pkj).delete()
    DetailAHSPProject.objects.bulk_create(...)

# Option 2: Add version field to Pekerjaan
class Pekerjaan:
    detail_version = models.IntegerField(default=1)

def api_save_detail_ahsp_for_pekerjaan():
    expected_version = payload.get('detail_version')
    rows_updated = Pekerjaan.objects.filter(
        id=pekerjaan_id,
        detail_version=expected_version
    ).update(detail_version=F('detail_version') + 1)

    if rows_updated == 0:
        return JsonResponse({"ok": False, "error": "Conflict detected"}, status=409)
```

---

### 8.2 🔒 Concurrent Upsert of HargaItemProject

**Scenario:**
```
Thread A: Upsert kode="L.01" with kategori="TK"
Thread B: Upsert kode="L.01" with kategori="BHN"
```

**Timeline:**
```
T1: Thread A: get_or_create(kode="L.01") → creates with kategori="TK"
T2: Thread B: get_or_create(kode="L.01") → gets existing, updates to kategori="BHN"
T3: Thread A: continues with kategori="TK" in memory
T4: Thread B: commits
T5: Thread A: commits
→ Race condition on kategori value
```

**Django Behavior:**
- `get_or_create()` is **NOT atomic** without explicit locking
- Between SELECT and INSERT, another thread can insert
- Raises `IntegrityError` if both try to INSERT

**Impact:**
- **MEDIUM** - Kategori can flip-flop
- IntegrityError possible (caught by try/except in practice)

**Recommendation:**
```python
# Option 1: SELECT FOR UPDATE
def _upsert_harga_item(project, kategori, kode_item, uraian, satuan):
    with transaction.atomic():
        try:
            obj = HargaItemProject.objects.select_for_update().get(
                project=project, kode_item=kode_item
            )
            # Update if needed
        except HargaItemProject.DoesNotExist:
            obj = HargaItemProject.objects.create(...)
        return obj

# Option 2: Use update_or_create (atomic since Django 1.7)
def _upsert_harga_item(project, kategori, kode_item, uraian, satuan):
    obj, created = HargaItemProject.objects.update_or_create(
        project=project,
        kode_item=kode_item,
        defaults={
            'kategori': kategori,
            'uraian': uraian,
            'satuan': satuan
        }
    )
    return obj
```

---

### 8.3 🔒 Cache Invalidation Race

**Scenario:**
```
Thread A: Save detail → invalidate cache
Thread B: Compute rekap → read stale cache → write cache
Thread A: Finish commit
→ Stale cache written AFTER invalidation
```

**Timeline:**
```
T1: Thread A: saves detail
T2: Thread A: cache.delete("rekap:123:v2")
T3: Thread B: compute_rekap_for_project() checks cache (MISS)
T4: Thread A: commits transaction
T5: Thread B: computes rekap (using OLD data from before T4 commit!)
T6: Thread B: cache.set("rekap:123:v2", stale_data)
→ Cache now contains stale data until next invalidation
```

**Impact:**
- **MEDIUM** - Users see outdated totals
- Cache expires after TTL (5 minutes) so self-healing
- Manual refresh needed for immediate update

**Recommendation:**
```python
# Option 1: Invalidate AFTER commit
@transaction.atomic
def api_save_detail_ahsp_for_pekerjaan():
    # ... save operations ...
    transaction.on_commit(lambda: invalidate_rekap_cache(project))

# Option 2: Include version in cache key
def compute_rekap_for_project(project):
    version = Pekerjaan.objects.filter(project=project).aggregate(
        Max('updated_at')
    )['updated_at__max']
    key = f"rekap:{project.id}:v2:{version.timestamp()}"
    # Cache automatically invalidated when any pekerjaan updated
```

---

## 9. RECOMMENDATIONS

### 9.1 High Priority

1. **Add SELECT FOR UPDATE for concurrent saves**
   - Prevents race condition on same pekerjaan
   - Implementation: 5 lines
   - Impact: Critical data integrity fix

2. **Validate kategori consistency**
   - Prevent kategori mismatch between tables
   - Implementation: Add validation in _upsert_harga_item
   - Impact: Data integrity

3. **Add optimistic locking**
   - Detect concurrent edits
   - Implementation: Add version field to Pekerjaan
   - Impact: Better UX, no silent data loss

---

### 9.2 Medium Priority

4. **Check bundle recursion**
   - Prevent infinite loops
   - Implementation: Add visited set in compute_kebutuhan_items
   - Impact: Prevent server crashes

5. **Improve error messages**
   - Show field name in validation errors (✅ DONE)
   - Implementation: Already fixed in fcff3f1
   - Impact: Better UX

6. **Add soft delete for Pekerjaan**
   - Prevent accidental data loss
   - Implementation: Add deleted_at field
   - Impact: Data recovery option

---

### 9.3 Low Priority

7. **Optimize _upsert_harga_item for bulk**
   - Current: N queries for N rows
   - Potential: 1 query with bulk lookup
   - Impact: Performance (marginal for < 100 rows)

8. **Add audit log**
   - Track who changed what when
   - Implementation: Django Simple History
   - Impact: Debugging, compliance

9. **Add data migration for kategori fix**
   - Find and fix existing kategori mismatches
   - Implementation: Custom management command
   - Impact: Clean existing data

---

## 10. SUMMARY

### ✅ Strengths

1. **Clean separation** - HargaItemProject as master, DetailAHSPProject as detail
2. **Auto-upsert pattern** - Ensures master exists before detail
3. **Transaction safety** - Uses @transaction.atomic
4. **Bulk operations** - Efficient bulk_create
5. **Bundle support** - Flexible LAIN kategori

### ⚠️ Weaknesses

1. **Race conditions** - Concurrent edits can cause data loss
2. **Kategori mismatch** - Shared HargaItemProject can have inconsistent kategori
3. **No recursion check** - Bundle can create infinite loops
4. **Last write wins** - No conflict detection
5. **Cache race** - Invalidation can race with computation

### 🎯 Overall Assessment

**Grade:** B+ (Very Good, with room for improvement)

**Production Readiness:** ✅ Ready with caveats
- Works well for single-user or low-concurrency scenarios
- Needs optimistic locking for multi-user concurrent editing
- Needs recursion check for complex bundle hierarchies

**Recommended Next Steps:**
1. Implement SELECT FOR UPDATE (1 day)
2. Add optimistic locking (2 days)
3. Add bundle recursion check (1 day)
4. Write integration tests for race conditions (2 days)

---

**Documentation Created:** 2025-11-08
**Version:** 1.0
**Status:** ✅ COMPLETE
