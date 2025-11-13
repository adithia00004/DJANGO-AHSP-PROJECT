# WORKFLOW DOKUMENTASI: TEMPLATE AHSP, HARGA ITEMS, DAN RINCIAN AHSP

## DAFTAR ISI

1. [Gambaran Umum](#gambaran-umum)
2. [Alur Kerja Standard](#alur-kerja-standard)
3. **[SEGMENT D (LAIN) - COMPLETE LIFECYCLE](#segment-d-lain---complete-lifecycle)** ← BARU!
4. [Arsitektur Data & Sinkronisasi](#arsitektur-data--sinkronisasi)
5. [Skenario User Action & Response](#skenario-user-action--response)
6. [Error Handling & Validasi](#error-handling--validasi)
7. [Edge Cases & Solusi](#edge-cases--solusi)
8. [Troubleshooting](#troubleshooting)

---

## GAMBARAN UMUM

### Ketiga Halaman dan Fungsinya

**TEMPLATE AHSP (INPUT)**
- Input komponen AHSP per pekerjaan (TK/BHN/ALT/LAIN)
- Support bundle reference (LAIN segment)
- TANPA kolom harga (fokus pada komponen & koefisien)
- Auto Save & Expand

↓

**HARGA ITEMS (PRICING)**
- Set harga satuan untuk setiap item
- Hanya tampilkan items yang digunakan (expanded)
- Filter: TK/BHN/ALT (bundle LAIN tidak ditampilkan)
- Join Harga

↓

**RINCIAN AHSP (REVIEW & RECAP)**
- Tampilkan komponen DENGAN harga
- Kalkulasi total per pekerjaan
- Support markup/profit override
- Visual distinction untuk bundle-expanded items

### Dual Storage Architecture

System menggunakan 2 storage untuk fleksibilitas:

| Storage | Table | Purpose | Content |
|---------|-------|---------|---------|
| **RAW INPUT** | `DetailAHSPProject` | Simpan input user asli | Semua items termasuk bundle (LAIN) |
| **EXPANDED** | `DetailAHSPExpanded` | Storage komputasi | Komponen hasil ekspansi (TK/BHN/ALT only) |
| **PRICING** | `HargaItemProject` | Master harga | Harga satuan per item |

**Contoh:**
```
USER INPUT (DetailAHSPProject):
  - TK, L.01, Pekerja, koef=5.0
  - BHN, B.02, Semen, koef=20.0
  - LAIN, Bundle_A, ref_pekerjaan=123, koef=3.0  ← Bundle!

EXPANDED (DetailAHSPExpanded):
  - TK, L.01, koef=5.0, source_bundle=NULL
  - BHN, B.02, koef=20.0, source_bundle=NULL
  - TK, L.99, koef=6.0, source_bundle='Bundle_A'  ← From expansion!
  - ALT, A.01, koef=12.0, source_bundle='Bundle_A'  ← From expansion!

PRICING (HargaItemProject):
  - L.01, harga_satuan=150000
  - B.02, harga_satuan=50000
  - L.99, harga_satuan=0  ← Auto-created, belum diisi
  - A.01, harga_satuan=0  ← Auto-created, belum diisi
```

---

## ALUR KERJA STANDARD

### FASE 1: INPUT KOMPONEN (Template AHSP)

**Tujuan:** Definisikan komponen AHSP untuk setiap pekerjaan

**Langkah:**
1. **Pilih Pekerjaan** dari sidebar
2. **Input Komponen Direct** (TK/BHN/ALT):
   - Masukkan kode, uraian, satuan, koefisien
   - Kode harus unique per pekerjaan
3. **Input Bundle** (LAIN - optional):
   - Pilih ref_pekerjaan yang sudah ada komponennya
   - System akan auto-expand bundle
4. **Save**
   - System validate input
   - Create/update HargaItemProject (harga=0 untuk item baru)
   - Expand bundle ke DetailAHSPExpanded
   - **CASCADE RE-EXPANSION**: Re-expand pekerjaan lain yang reference pekerjaan ini

**Hasil:**
```
✓ DetailAHSPProject: Raw input tersimpan
✓ DetailAHSPExpanded: Komponen expanded ready untuk pricing
✓ HargaItemProject: Auto-created untuk items baru (harga=0)
→ Lanjut ke Harga Items untuk set harga!
```

---

### FASE 2: SET HARGA (Harga Items)

**Tujuan:** Set harga satuan untuk setiap item yang digunakan

**Langkah:**
1. **Filter Items** (optional):
   - Filter by kategori (TK/BHN/ALT)
   - Filter by search (kode/uraian)
2. **Review Items**:
   - Items ditampilkan: yang ada di DetailAHSPExpanded
   - Items TIDAK ditampilkan: bundle LAIN (sudah di-expand)
3. **Set Harga Satuan**:
   - Input harga per item
   - Validation: non-negative, max 2 decimal places
4. **Set Project Profit/Margin** (optional):
   - Global profit % untuk seluruh project
5. **Save**
   - System validate harga format
   - Update HargaItemProject
   - Invalidate rekap cache

**Hasil:**
```
✓ HargaItemProject: Harga satuan updated
✓ Cache invalidated: Rincian AHSP will show updated prices
→ Lanjut ke Rincian AHSP untuk review total!
```

---

### FASE 3: REVIEW & RECAP (Rincian AHSP)

**Tujuan:** Review komponen dengan harga dan total per pekerjaan

**Langkah:**
1. **Pilih Pekerjaan** dari sidebar
2. **Review Komponen**:
   - Lihat kode, uraian, koefisien, harga satuan
   - Items dari bundle ditandai dengan icon/badge
   - Jumlah harga = koefisien × harga satuan
3. **Check Total**:
   - Subtotal = SUM(jumlah harga)
   - BUK (Profit/Margin) = Subtotal × markup%
   - Grand Total = Subtotal + BUK
4. **Override Markup** (optional):
   - Override profit% khusus untuk pekerjaan ini
5. **Export RAB** (optional)

**Hasil:**
```
✓ Total pekerjaan calculated dengan benar
✓ Ready untuk export RAB
```

---

## SEGMENT D (LAIN) - COMPLETE LIFECYCLE

### Apa itu Segment D (LAIN)?

**LAIN** adalah kategori khusus yang berfungsi sebagai **"Bundle" atau "Pekerjaan Gabungan"**:
- Mereferensi pekerjaan lain yang sudah memiliki komponen
- Otomatis meng-expand komponen dari pekerjaan target
- Mengalikan koefisien secara hierarkis
- Mencegah duplikasi input manual

**Use Cases:**
- Pekerjaan berulang (misal: kolom struktural yang sama dipakai berkali-kali)
- Pekerjaan komposit (misal: "Finishing Lengkap" terdiri dari beberapa sub-pekerjaan)
- Template work packages

---

### Bundle Workflow: Step-by-Step

#### STEP 1: Persiapkan Pekerjaan Target

**Di Template AHSP:**
```
Pilih: Pekerjaan B (Target)

Input komponen:
  - Kategori TK, Kode L.01, Uraian "Pekerja", Koef 5.0
  - Kategori BHN, Kode B.02, Uraian "Semen", Koef 10.0

Save → Pekerjaan B sekarang memiliki 2 komponen
```

**PENTING:** Pekerjaan target HARUS sudah memiliki komponen sebelum bisa dijadikan bundle!

---

#### STEP 2: Buat Bundle di Pekerjaan Sumber

**Di Template AHSP:**
```
Pilih: Pekerjaan A (Sumber)

Tab LAIN (Bundle):
  - Kode: Bundle_B
  - Uraian: "Pekerjaan Gabungan B"
  - Ref Pekerjaan: [Dropdown] Pilih "Pekerjaan B"
  - Koefisien: 3.0

Preview Expansion (optional):
  Sistem akan menampilkan:
  - L.01: 5.0 × 3.0 = 15.0
  - B.02: 10.0 × 3.0 = 30.0

Save
```

---

#### STEP 3: System Processing (Automatic)

**Backend melakukan (automatic):**

1. **Validation:**
   ```python
   # Check: Target pekerjaan exists?
   # Check: Target has components? (BARU!)
   # Check: Circular dependency? (A→B→A)
   # Check: Max depth not exceeded? (max 3 levels)
   ```

2. **Save Raw Input:**
   ```sql
   INSERT INTO DetailAHSPProject (
     project_id, pekerjaan_id, kategori, kode, koefisien, ref_pekerjaan_id
   ) VALUES (
     1, 'A', 'LAIN', 'Bundle_B', 3.0, 'B'
   );
   ```

3. **Bundle Expansion:**
   ```python
   # Fetch Pekerjaan B components
   components_B = [
     {'kode': 'L.01', 'koef': 5.0},
     {'kode': 'B.02', 'koef': 10.0}
   ]

   # Multiply with bundle koefisien (3.0)
   for comp in components_B:
     final_koef = comp.koef * 3.0

     # Create in DetailAHSPExpanded
     DetailAHSPExpanded.create(
       pekerjaan=A,
       kode=comp.kode,
       koefisien=final_koef,
       source_bundle_kode='Bundle_B'
     )
   ```

4. **HargaItemProject Creation:**
   ```python
   # Auto-create if not exists
   HargaItemProject.get_or_create(
     project=project,
     kode='L.01',
     defaults={'harga_satuan': 0}
   )

   HargaItemProject.get_or_create(
     project=project,
     kode='B.02',
     defaults={'harga_satuan': 0}
   )
   ```

5. **Cache Invalidation:**
   ```python
   invalidate_rekap_cache(project)
   ```

---

#### STEP 4: Impact on Harga Items Page

**User navigates to Harga Items:**

**Yang DITAMPILKAN:**
```
Table rows:
  - L.01, Pekerja, TK, Harga: Rp 0 (belum diisi)
  - B.02, Semen, BHN, Harga: Rp 0 (belum diisi)
```

**Yang TIDAK DITAMPILKAN:**
```
  - Bundle_B (LAIN item)

WHY? Karena bundle sudah di-expand menjadi L.01 dan B.02
      Harga Items hanya menampilkan komponen expanded (TK/BHN/ALT)
```

**User Action:**
```
Set harga:
  - L.01: Rp 150,000
  - B.02: Rp 50,000

Save
```

---

#### STEP 5: Impact on Rincian AHSP Page

**User navigates to Rincian AHSP, pilih Pekerjaan A:**

**Tampilan Table:**
```
Kode   | Uraian  | Koef  | Harga Satuan | Jumlah Harga | Source
-------|---------|-------|--------------|--------------|--------
L.01   | Pekerja | 15.0  | 150,000      | 2,250,000    | [Bundle_B]
B.02   | Semen   | 30.0  | 50,000       | 1,500,000    | [Bundle_B]
-------|---------|-------|--------------|--------------|--------
                           SUBTOTAL:      3,750,000
                           BUK (10%):       375,000
                           GRAND TOTAL:   4,125,000
```

**Visual Indicators:**
- Badge/icon menunjukkan item berasal dari bundle
- Grouping (optional) untuk items dari bundle yang sama

---

### Multi-Level Bundle (Nested)

**Scenario:**
```
Pekerjaan A: LAIN Bundle_B (koef 2.0)
Pekerjaan B: LAIN Bundle_C (koef 3.0)
Pekerjaan C: TK L.01 (koef 5.0)
```

**Expansion Result:**
```
Pekerjaan A Expanded:
  - L.01, koef = 5.0 × 3.0 × 2.0 = 30.0

Calculation:
  Level 0: Pekerjaan C has L.01 (koef 5.0)
  Level 1: Bundle_C expands → L.01 (5.0 × 3.0 = 15.0)
  Level 2: Bundle_B expands → L.01 (15.0 × 2.0 = 30.0)
```

**Max Depth: 3 levels**
- Lebih dari 3 levels akan di-reject dengan error

---

### Bundle Modification & Cascade Re-Expansion

**CRITICAL FEATURE:** Ketika pekerjaan target dimodifikasi, semua pekerjaan yang me-reference-nya otomatis di-update.

**Example:**

**Initial State:**
```
Pekerjaan A: LAIN Bundle_B (koef 3.0)
Pekerjaan B: TK L.01 (koef 5.0)

Pekerjaan A Expanded:
  - L.01, koef 15.0 (5.0 × 3.0)
```

**User modifies Pekerjaan B:**
```
Template AHSP → Pilih Pekerjaan B
Edit L.01: koef 5.0 → 8.0
Save
```

**System Response (AUTOMATIC CASCADE):**
```
1. Save Pekerjaan B:
   - DetailAHSPProject updated: L.01 koef=8.0
   - DetailAHSPExpanded updated for B

2. Detect References:
   - Find: Pekerjaan A references B (via Bundle_B)

3. Cascade Re-Expansion:
   - Re-expand Pekerjaan A automatically
   - New koef: 8.0 × 3.0 = 24.0

4. Update Expanded:
   - DetailAHSPExpanded (A): L.01 koef=24.0 ✓

5. Invalidate Cache:
   - Rincian AHSP will show updated total
```

**Implementation:**
```python
# services.py:676-799
def cascade_bundle_re_expansion(project, modified_pekerjaan_id):
    # Find all pekerjaan that reference modified_pekerjaan_id
    referencing = DetailAHSPProject.objects.filter(
        kategori='LAIN',
        ref_pekerjaan_id=modified_pekerjaan_id
    )

    # Re-expand each referencing pekerjaan
    for ref in referencing:
        populate_expanded_from_project(project, ref.pekerjaan)

        # Recursive: this pekerjaan might also be referenced
        cascade_bundle_re_expansion(project, ref.pekerjaan.id)
```

**Result:**
```
Rincian AHSP (Pekerjaan A):
  - L.01, koef 24.0 ✓ (updated automatically!)
  - Jumlah: 24.0 × 150,000 = 3,600,000 ✓
```

---

### Bundle Lifecycle Summary

**Lifecycle Stages:**

1. **CREATION**
   - User creates LAIN item with ref_pekerjaan
   - System validates target has components
   - Saved to DetailAHSPProject

2. **EXPANSION**
   - System fetches target components
   - Multiplies koefisien hierarchically
   - Creates DetailAHSPExpanded entries
   - Auto-creates HargaItemProject (harga=0)

3. **PRICING**
   - User sets harga_satuan in Harga Items
   - Expanded components shown (not bundle itself)
   - HargaItemProject updated

4. **CALCULATION**
   - Rincian AHSP joins expanded + harga
   - Calculates jumlah_harga per item
   - Sums to grand total with margin

5. **MODIFICATION**
   - User edits target pekerjaan
   - CASCADE RE-EXPANSION triggered
   - All referencing pekerjaan updated
   - Cache invalidated

6. **DELETION**
   - User deletes bundle (LAIN item)
   - System deletes expanded components
   - HargaItemProject may become orphaned
   - User can cleanup orphans manually

---

### Common Questions & Answers

**Q: Kenapa bundle saya tidak muncul di Harga Items?**
A: Ini NORMAL! Bundle (LAIN) di-expand menjadi komponen TK/BHN/ALT. Yang muncul di Harga Items adalah komponen hasil ekspansi, bukan bundle itu sendiri.

**Q: Saya pilih pekerjaan tapi error "tidak memiliki komponen"?**
A: Pekerjaan target harus sudah memiliki komponen sebelum dijadikan bundle. Isi komponen dulu di Template AHSP untuk pekerjaan tersebut.

**Q: Total di Rincian AHSP tiba-tiba berubah, kenapa?**
A: Kemungkinan pekerjaan target (yang di-reference sebagai bundle) telah dimodifikasi. System otomatis re-expand bundle dengan cascade mechanism.

**Q: Bisa bundle dalam bundle (nested)?**
A: Ya, bisa sampai max 3 levels (A→B→C). Lebih dari itu akan di-reject.

**Q: Apa yang terjadi jika saya hapus pekerjaan yang di-reference sebagai bundle?**
A: System akan block deletion jika pekerjaan masih di-reference. User harus hapus bundle reference dulu sebelum menghapus pekerjaan target.

---

### Validation Rules untuk Bundle

| Rule | Check | Error Message |
|------|-------|---------------|
| Target Exists | ref_pekerjaan_id valid? | "Pekerjaan #... tidak ditemukan" |
| **Target Not Empty** | Target has components? | **"Pekerjaan '...' tidak memiliki komponen"** (BARU!) |
| No Circular | A→B→A not allowed | "Circular dependency detected: ..." |
| Max Depth | depth <= 3 | "Maksimum kedalaman bundle terlampaui" |
| Only for LAIN | kategori == 'LAIN' | "Hanya boleh pada kategori 'Lain-lain'" |
| Only for CUSTOM | source_type == 'CUSTOM' | "Hanya boleh untuk pekerjaan custom" |

---

### Data Flow Diagram: Bundle Creation

```
USER ACTION: Create Bundle
  ↓
[1] VALIDATION
  - Target exists? ✓
  - Target has components? ✓ (NEW!)
  - Circular dependency? ✗
  - Max depth? ✓
  ↓
[2] SAVE RAW INPUT
  DetailAHSPProject
    kategori='LAIN'
    ref_pekerjaan_id=target
  ↓
[3] FETCH TARGET COMPONENTS
  SELECT * FROM DetailAHSPProject
  WHERE pekerjaan_id=target
  ↓
[4] MULTIPLY KOEFISIEN
  for each component:
    final_koef = comp.koef * bundle.koef
  ↓
[5] CREATE EXPANDED
  DetailAHSPExpanded
    koefisien=final_koef
    source_bundle_kode=bundle.kode
  ↓
[6] AUTO-CREATE HARGA
  HargaItemProject.get_or_create(
    kode=comp.kode,
    harga_satuan=0
  )
  ↓
[7] INVALIDATE CACHE
  invalidate_rekap_cache(project)
  ↓
RESULT:
  ✓ Bundle saved
  ✓ Components expanded
  ✓ Harga items ready for pricing
```

---

### Data Flow Diagram: Bundle Modification (Cascade)

```
USER ACTION: Modify Target Pekerjaan B
  (Pekerjaan A references B as bundle)
  ↓
[1] SAVE TARGET PEKERJAAN B
  DetailAHSPProject updated
  DetailAHSPExpanded updated for B
  ↓
[2] DETECT REFERENCES
  SELECT pekerjaan_id
  FROM DetailAHSPProject
  WHERE kategori='LAIN'
    AND ref_pekerjaan_id=B
  → Found: Pekerjaan A
  ↓
[3] CASCADE RE-EXPANSION
  for each referencing_pekerjaan (A):
    - Delete old expanded data
    - Re-fetch B components (NEW values)
    - Re-multiply koefisien
    - Create new expanded data
  ↓
[4] RECURSIVE CHECK
  Does A referenced by others?
  If yes → Repeat step 2-3
  ↓
[5] INVALIDATE CACHE
  invalidate_rekap_cache(project)
  ↓
RESULT:
  ✓ Pekerjaan B updated
  ✓ Pekerjaan A auto-updated
  ✓ Totals in Rincian AHSP correct
```

---

## ARSITEKTUR DATA & SINKRONISASI

### Complete Data Flow

```
[TEMPLATE AHSP]
  Save → DetailAHSPProject (raw input with bundle refs)
       → expand_bundle_to_components()
       → DetailAHSPExpanded (computed components)
       → HargaItemProject.get_or_create() (harga=0 for new)
       → cascade_bundle_re_expansion() (update referencing)
       → invalidate_rekap_cache()

[HARGA ITEMS]
  Query → DetailAHSPExpanded (to get used items)
       → Join HargaItemProject
  Save  → HargaItemProject.harga_satuan
       → invalidate_rekap_cache()

[RINCIAN AHSP]
  Query → DetailAHSPExpanded
       → Join HargaItemProject
       → Calculate jumlah_harga = koef × harga
       → Sum to grand_total with margin
```

### Critical: Cascade Re-Expansion

**Problem Solved:**
Ketika Pekerjaan B dimodifikasi, dan Pekerjaan A me-reference B sebagai bundle, expanded data di A menjadi stale.

**Solution:**
Cascade re-expansion automatically re-expands all referencing pekerjaans.

**Implementation:** `services.py:676-799`

---

## SKENARIO USER ACTION & RESPONSE

### SKENARIO 1: Add New Direct Item

**User Action:**
```javascript
// Template AHSP
{
  "kategori": "TK",
  "kode": "L.99",
  "uraian": "Mandor Baru",
  "koefisien": "0.5"
}
```

**System Response:**
```
1. Validate: ✓ kategori valid, kode unique, koef >= 0
2. Save to DetailAHSPProject
3. Upsert HargaItemProject(kode=L.99, harga_satuan=0)
4. Pass-through to DetailAHSPExpanded (no expansion needed)
5. Invalidate cache

Impact:
  → Harga Items: L.99 muncul dengan harga=0
  → Rincian AHSP: L.99 muncul dengan jumlah_harga=0
  ! User harus set harga di Harga Items
```

---

### SKENARIO 2: Edit Koefisien Direct Item

**Initial:** TK, L.01, koef=5.0, harga=150000

**User Action:**
```javascript
{"kode": "L.01", "koefisien": "8.0"}  // Changed!
```

**System Response:**
```
1. Replace-all: DELETE old, CREATE new with koef=8.0
2. DetailAHSPExpanded updated: koef=8.0
3. HargaItemProject UNCHANGED (harga tetap 150000)
4. Invalidate cache

Impact:
  → Harga Items: No change
  → Rincian AHSP: Jumlah = 8.0 × 150,000 = 1,200,000 (was 750,000)
  → Total pekerjaan updated
```

---

### SKENARIO 3: Add Bundle

**Initial:**
```
Pekerjaan A: (empty)
Pekerjaan B: TK L.01 (koef=5.0), BHN B.02 (koef=10.0)
```

**User Action:**
```javascript
{
  "kategori": "LAIN",
  "kode": "Bundle_B",
  "ref_pekerjaan_id": 456,  // ID of Pekerjaan B
  "koefisien": "3.0"
}
```

**System Response:**
```
1. Validate:
   ✓ ref_pekerjaan exists
   ✓ No circular dependency
   ✓ Target has components (NOT EMPTY)
2. Save to DetailAHSPProject: LAIN, Bundle_B, ref_pekerjaan_id=456
3. Expand bundle:
   - L.01: 5.0 × 3.0 = 15.0
   - B.02: 10.0 × 3.0 = 30.0
4. Save to DetailAHSPExpanded (2 rows)
5. Auto-create HargaItemProject for L.01, B.02 (harga=0)
6. Invalidate cache

Impact:
  → Harga Items: L.01, B.02 visible (Bundle_B NOT visible)
  → Rincian AHSP: L.01 (koef 15.0), B.02 (koef 30.0) shown with bundle indicator
  → Total includes expanded components
```

---

### SKENARIO 4: Edit Bundle TARGET (Indirect - CRITICAL!)

**Initial:**
```
Pekerjaan A: LAIN Bundle_B (ref=B, koef=3.0)
Pekerjaan B: TK L.01 (koef=5.0)

DetailAHSPExpanded (A): L.01, koef=15.0
```

**User Action:**
```javascript
// User EDIT Pekerjaan B (not A!)
// Change L.01: koef 5.0 → 8.0
```

**System Response:**
```
1. Save Pekerjaan B:
   - Update DetailAHSPProject for B
   - Update DetailAHSPExpanded for B

2. CASCADE RE-EXPANSION (AUTOMATIC!):
   - Detect Pekerjaan A references B
   - Re-expand Pekerjaan A automatically
   - Update DetailAHSPExpanded for A: L.01 koef=24.0 ✓

3. Invalidate cache

Impact:
  → Harga Items: No change
  ✓ Rincian AHSP (A): Automatically updated!
  ✓ Total recalculated with new values

BEFORE FIX: ✗ Pekerjaan A would show STALE data
AFTER FIX:  ✓ CASCADE ensures consistency
```

---

## ERROR HANDLING & VALIDASI

### Validation Rules

| Validation | Check | Error Response |
|------------|-------|----------------|
| Kategori Valid | Must be TK/BHN/ALT/LAIN | 400: "Kategori tidak valid" |
| Kode Unique | Unique per pekerjaan | 400: "Kode sudah digunakan" |
| Koefisien >= 0 | koef >= 0 | 400: "Koefisien harus >= 0" |
| Kategori Immutable | Cannot change kategori | 400: "Item '...' sudah ada dengan kategori '...'" |
| **Bundle Target Not Empty** | Target has components | **400: "Pekerjaan '...' tidak memiliki komponen"** |
| No Circular Dependency | A→B→C→A not allowed | 400: "Circular dependency detected: ..." |
| Max Expansion Depth | Max 3 levels | 400: "Maksimum kedalaman bundle terlampaui" |

### Error Message Examples

**Empty Bundle:**
```json
{
  "ok": false,
  "user_message": "Ditemukan kesalahan pada data yang Anda masukkan.",
  "errors": [{
    "field": "rows[0].ref_id",
    "message": "Pekerjaan 'PKJ.001' tidak memiliki komponen AHSP. Bundle harus mereferensi pekerjaan yang sudah memiliki komponen."
  }]
}
```

**Circular Dependency:**
```json
{
  "ok": false,
  "user_message": "Circular dependency detected",
  "errors": [{
    "field": "rows[0].ref_pekerjaan",
    "message": "Circular dependency detected: PKJ.A → PKJ.B → PKJ.A"
  }]
}
```

---

## EDGE CASES & SOLUSI

### EDGE CASE 1: Empty Bundle
**Problem:** User selects ref_pekerjaan yang tidak ada komponennya
**Status:** ✓ FIXED (validation added)
**Solution:** `views_api.py:1352-1366` - validates target has components

### EDGE CASE 2: Circular Dependency
**Problem:** A→B→A infinite recursion
**Status:** ✓ PROTECTED
**Solution:** `check_circular_dependency_pekerjaan()` detects cycles

### EDGE CASE 3: Orphaned HargaItemProject
**Problem:** Old items tetap ada setelah rename/delete
**Status:** ! TODO
**Proposed Solution:**
- UI filter untuk orphaned items
- Manual cleanup API
- Optional: Auto-cleanup (30-day safety period)

### EDGE CASE 4: Stale Expanded Data
**Problem:** Target modified, references not updated
**Status:** ✓ FIXED
**Solution:** `cascade_bundle_re_expansion()` auto-updates all references

---

## TROUBLESHOOTING

### Problem: Bundle tidak muncul di Harga Items

**Cause:** Bundle (LAIN) tidak ditampilkan karena sudah di-expand

**Solution:** Ini adalah behavior yang benar (by design)
- Bundle otomatis di-expand menjadi komponen TK/BHN/ALT
- Komponen expanded yang muncul di Harga Items

**Verification:**
```sql
SELECT * FROM detail_ahsp_expanded
WHERE pekerjaan_id = ? AND source_bundle_kode IS NOT NULL
```

---

### Problem: Total tidak update setelah edit harga

**Cause:** Cache not invalidated atau browser cache

**Solution:**
1. Hard refresh browser (Ctrl+Shift+R)
2. Check server logs untuk cache invalidation
3. Verify HargaItemProject updated

---

### Problem: Pekerjaan A masih show old values setelah edit Pekerjaan B

**Cause (OLD):** Stale data - cascade re-expansion not implemented
**Status:** ✓ FIXED

**Verification:**
```bash
grep "CASCADE_RE_EXPANSION" /var/log/django.log
# Expected: Found X pekerjaan referencing #B
```

---

## SUMMARY

### Complete Workflow Matrix

| User Action | Template AHSP | Harga Items | Rincian AHSP | Architecture Status |
|-------------|---------------|-------------|--------------|---------------------|
| Add direct item | ✓ Saved | ✓ Created (harga=0) | ✓ Shown | ✓ Ready |
| Edit koefisien | ✓ Updated | - No change | ✓ Recalculated | ✓ Ready |
| Add bundle | ✓ Saved | ✓ Components shown | ✓ Expanded shown | ✓ Ready |
| Edit bundle target | ✓ Modified | - No change | ✓ CASCADE UPDATED | ✓ FIXED |
| Delete item | ✓ Removed | ! May orphan | ✓ Removed | ! Orphan cleanup TODO |

---

## RELATED DOCUMENTATION

- Template AHSP Documentation: `TEMPLATE_AHSP_DOCUMENTATION.md`
- Rincian AHSP Documentation: `RINCIAN_AHSP_README.md`
- Bundle Expansion Fix: `BUNDLE_EXPANSION_FIX.md`
- API Reference: See `views_api.py` docstrings

---

## CHANGELOG

### v2.0.0 (2025-01-XX) - Cascade Re-Expansion & Segment D Docs
- ✓ CRITICAL FIX: Implemented cascade_bundle_re_expansion()
- ✓ VALIDATION: Added empty bundle target check
- ✓ DOCUMENTATION: Complete Segment D lifecycle section
- ! TODO: Implement orphaned items cleanup

### v1.0.0 - Initial Dual Storage
- Implemented dual storage architecture
- Added bundle expansion support
- Added circular dependency protection

---

**Last Updated:** 2025-01-XX
**Status:** Production Ready (with orphan cleanup TODO)
