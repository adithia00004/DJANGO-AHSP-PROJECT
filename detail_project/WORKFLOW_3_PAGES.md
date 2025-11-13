# 🔄 WORKFLOW DOKUMENTASI: TEMPLATE AHSP, HARGA ITEMS, DAN RINCIAN AHSP

## 📋 DAFTAR ISI

1. [Gambaran Umum](#gambaran-umum)
2. [Alur Kerja Standard](#alur-kerja-standard)
3. [Arsitektur Data & Sinkronisasi](#arsitektur-data--sinkronisasi)
4. [Skenario User Action & Response](#skenario-user-action--response)
5. [Error Handling & Validasi](#error-handling--validasi)
6. [Edge Cases & Solusi](#edge-cases--solusi)
7. [Troubleshooting](#troubleshooting)

---

## 📊 GAMBARAN UMUM

### **Ketiga Halaman dan Fungsinya**

```
┌─────────────────────────────────────────────────────────────────┐
│                    TEMPLATE AHSP (INPUT)                        │
│  • Input komponen AHSP per pekerjaan (TK/BHN/ALT/LAIN)        │
│  • Support bundle reference (LAIN segment)                     │
│  • TANPA kolom harga (fokus pada komponen & koefisien)        │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Auto Save & Expand
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  HARGA ITEMS (PRICING)                          │
│  • Set harga satuan untuk setiap item                          │
│  • Hanya tampilkan items yang digunakan (expanded)            │
│  • Filter: TK/BHN/ALT (bundle LAIN tidak ditampilkan)         │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Join Harga
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                RINCIAN AHSP (REVIEW & RECAP)                    │
│  • Tampilkan komponen DENGAN harga                             │
│  • Kalkulasi total per pekerjaan                               │
│  • Support markup/profit override                              │
│  • Visual distinction untuk bundle-expanded items              │
└─────────────────────────────────────────────────────────────────┘
```

### **Dual Storage Architecture**

System menggunakan 2 storage untuk fleksibilitas:

| Storage | Table | Purpose | Content |
|---------|-------|---------|---------|
| **RAW INPUT** | `DetailAHSPProject` | Simpan input user asli | Semua items termasuk bundle (LAIN) |
| **EXPANDED** | `DetailAHSPExpanded` | Storage komputasi | Komponen hasil ekspansi (TK/BHN/ALT only) |
| **PRICING** | `HargaItemProject` | Master harga | Harga satuan per item |

**Contoh:**
```
USER INPUT (DetailAHSPProject):
├─ TK, L.01, Pekerja, koef=5.0
├─ BHN, B.02, Semen, koef=20.0
└─ LAIN, Bundle_A, ref_pekerjaan=123, koef=3.0  ← Bundle!

EXPANDED (DetailAHSPExpanded):
├─ TK, L.01, koef=5.0, source_bundle=NULL
├─ BHN, B.02, koef=20.0, source_bundle=NULL
├─ TK, L.99, koef=6.0, source_bundle='Bundle_A'  ← From expansion!
└─ ALT, A.01, koef=12.0, source_bundle='Bundle_A'  ← From expansion!

PRICING (HargaItemProject):
├─ L.01, harga_satuan=150000
├─ B.02, harga_satuan=50000
├─ L.99, harga_satuan=0  ← Auto-created, belum diisi
└─ A.01, harga_satuan=0  ← Auto-created, belum diisi
```

---

## 🔄 ALUR KERJA STANDARD

### **FASE 1: INPUT KOMPONEN (Template AHSP)**

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
✅ DetailAHSPProject: Raw input tersimpan
✅ DetailAHSPExpanded: Komponen expanded ready untuk pricing
✅ HargaItemProject: Auto-created untuk items baru (harga=0)
⚠️ Lanjut ke Harga Items untuk set harga!
```

---

### **FASE 2: SET HARGA (Harga Items)**

**Tujuan:** Set harga satuan untuk setiap item yang digunakan

**Langkah:**
1. **Filter Items** (optional):
   - Filter by kategori (TK/BHN/ALT)
   - Filter by search (kode/uraian)
2. **Review Items**:
   - ✓ Items ditampilkan: yang ada di DetailAHSPExpanded
   - ✗ Items TIDAK ditampilkan: bundle LAIN (sudah di-expand)
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
✅ HargaItemProject: Harga satuan updated
✅ Cache invalidated: Rincian AHSP will show updated prices
⚠️ Lanjut ke Rincian AHSP untuk review total!
```

---

### **FASE 3: REVIEW & RECAP (Rincian AHSP)**

**Tujuan:** Review komponen dengan harga dan total per pekerjaan

**Langkah:**
1. **Pilih Pekerjaan** dari sidebar
2. **Review Komponen**:
   - Lihat kode, uraian, koefisien, harga satuan
   - Items dari bundle ditandai dengan 📦 icon
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
✅ Total pekerjaan calculated dengan benar
✅ Ready untuk export RAB
```

---

## 🔄 ARSITEKTUR DATA & SINKRONISASI

### **Data Flow Diagram**

```
┌─────────────────────────────────────────────────────────────────┐
│  USER ACTION: Save di Template AHSP                            │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. VALIDATE INPUT                                              │
│     • Kategori valid?                                           │
│     • Kode unique per pekerjaan?                                │
│     • Koefisien ≥ 0?                                            │
│     • Bundle target kosong? ❌ REJECT                           │
│     • Circular dependency? ❌ REJECT                            │
└────────────┬────────────────────────────────────────────────────┘
             │ ✓ Valid
             ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. SAVE RAW INPUT (DetailAHSPProject)                          │
│     • Replace-all strategy (delete old, insert new)             │
│     • Keep bundle references (LAIN with ref_pekerjaan)          │
│     • Auto-upsert HargaItemProject (harga=0 untuk baru)         │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. EXPAND BUNDLES (DetailAHSPExpanded)                         │
│     • Delete old expanded data                                  │
│     • For each item:                                            │
│       - Direct item (TK/BHN/ALT) → pass-through                 │
│       - Bundle (LAIN) → expand recursively                      │
│     • Multiply koefisien hierarchically                         │
│     • Bulk create expanded components                           │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. CASCADE RE-EXPANSION (CRITICAL!)                            │
│     • Find pekerjaan that reference this modified pekerjaan     │
│     • Re-expand each referencing pekerjaan                      │
│     • Recursive: A→B→C chain                                    │
│     • Prevent infinite loop with visited set                    │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. INVALIDATE CACHE                                            │
│     • Clear rekap cache                                         │
│     • Rincian AHSP will recalculate on next load               │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│  RESULT: All 3 pages synchronized!                              │
│    ✓ Template AHSP: Raw input updated                           │
│    ✓ Harga Items: New items created (harga=0)                   │
│    ✓ Rincian AHSP: Expanded components ready for review         │
└─────────────────────────────────────────────────────────────────┘
```

### **Critical: Cascade Re-Expansion**

**Problem:** Ketika Pekerjaan B dimodifikasi, dan Pekerjaan A me-reference B sebagai bundle, expanded data di A menjadi stale.

**Solution:** Cascade re-expansion automatically re-expands all referencing pekerjaans.

**Example:**
```
BEFORE MODIFICATION:
  Pekerjaan A: LAIN Bundle_B (ref=B, koef=3.0)
  Pekerjaan B: TK L.01 (koef=5.0)

  DetailAHSPExpanded (A):
    └─ TK L.01, koef=15.0 (5.0 × 3.0)

USER MODIFIES PEKERJAAN B:
  Pekerjaan B: TK L.01 (koef=8.0)  ← Changed!

WITHOUT CASCADE:
  DetailAHSPExpanded (A):
    └─ TK L.01, koef=15.0  ❌ STALE!

WITH CASCADE RE-EXPANSION:
  1. Detect A references B
  2. Re-expand A automatically
  DetailAHSPExpanded (A):
    └─ TK L.01, koef=24.0  ✅ CORRECT! (8.0 × 3.0)
```

**Implementation:**
```python
# services.py:676-799
def cascade_bundle_re_expansion(project, modified_pekerjaan_id, visited=None):
    # Find all pekerjaan that reference modified_pekerjaan_id
    referencing = DetailAHSPProject.objects.filter(
        project=project,
        kategori='LAIN',
        ref_pekerjaan_id=modified_pekerjaan_id
    )

    # Re-expand each
    for pkj_id in referencing.values_list('pekerjaan_id', flat=True).distinct():
        pkj = Pekerjaan.objects.get(id=pkj_id)
        populate_expanded_from_project(project, pkj)

        # RECURSIVE: This pekerjaan might also be referenced!
        cascade_bundle_re_expansion(project, pkj.id, visited)
```

---

## 📝 SKENARIO USER ACTION & RESPONSE

### **SKENARIO 1: Add New Direct Item**

**User Action:**
```javascript
// User add new item di Template AHSP
{
  "kategori": "TK",
  "kode": "L.99",
  "uraian": "Mandor Baru",
  "koefisien": "0.5"
}
```

**System Response:**
```
1. Validate: ✓ kategori valid, kode unique, koef ≥ 0
2. Save to DetailAHSPProject
3. Upsert HargaItemProject(kode=L.99, harga_satuan=0)
4. Pass-through to DetailAHSPExpanded (no expansion needed)
5. Invalidate cache

Impact:
  ✓ Harga Items: L.99 muncul dengan harga=0
  ✓ Rincian AHSP: L.99 muncul dengan jumlah_harga=0
  ⚠️ User harus set harga di Harga Items!
```

---

### **SKENARIO 2: Edit Koefisien Direct Item**

**Initial State:**
```
DetailAHSPProject: TK, L.01, koef=5.0
HargaItemProject: L.01, harga_satuan=150000
```

**User Action:**
```javascript
// User change koefisien 5.0 → 8.0
{"kode": "L.01", "koefisien": "8.0"}
```

**System Response:**
```
1. Validate: ✓
2. Replace-all: DELETE old, CREATE new with koef=8.0
3. DetailAHSPExpanded updated: koef=8.0
4. HargaItemProject UNCHANGED (harga tetap 150000)
5. Invalidate cache

Impact:
  ✓ Harga Items: No change
  ✓ Rincian AHSP: Jumlah harga = 8.0 × 150000 = 1,200,000
  ✓ Total pekerjaan updated automatically
```

---

### **SKENARIO 3: Change Item Kode (Identifier)**

**Initial State:**
```
DetailAHSPProject: TK, L.01, koef=5.0
HargaItemProject: L.01, harga_satuan=150000
```

**User Action:**
```javascript
// User change kode L.01 → L.01A
{"kode": "L.01A", "uraian": "Pekerja", "koefisien": "5.0"}
```

**System Response:**
```
1. Validate: ✓ L.01A is unique
2. Upsert HargaItemProject:
   - Check L.01A exists? NO
   - CREATE new HargaItemProject(L.01A, harga=0)
   - OLD L.01 remains (not deleted)
3. Replace-all DetailAHSPProject: kode=L.01A
4. Populate DetailAHSPExpanded: kode=L.01A

Impact:
  ⚠️ Harga Items:
     • L.01 still exists (harga=150000)
     • L.01A created (harga=0)
     • L.01 becomes ORPHANED if not used elsewhere
  ⚠️ Rincian AHSP: L.01A muncul dengan jumlah=0
  ⚠️ User harus set harga L.01A!

Recommendation:
  • Avoid changing kode unless absolutely necessary
  • If must change, verify no other pekerjaan uses old kode
  • Set harga for new kode immediately
```

---

### **SKENARIO 4: Change Item Kategori (REJECTED)**

**User Action:**
```javascript
// User try change kategori TK → BHN
{"kategori": "BHN", "kode": "L.01"}
```

**System Response:**
```
1. Validate: ❌ REJECT
   - HargaItemProject L.01 already exists with kategori=TK
   - Kategori is IMMUTABLE
2. Return 400 Bad Request

Error Message:
  "❌ Item 'L.01' sudah ada dengan kategori 'TK'.
   Tidak dapat mengubah kategori menjadi 'BHN'."

Impact:
  ✗ Transaction rolled back
  ✗ No changes to any table

Workaround:
  1. Change kode (L.01 → L.01-BHN)
  2. Then change kategori to BHN
```

---

### **SKENARIO 5: Delete Item**

**Initial State:**
```
DetailAHSPProject:
  ├─ TK, L.01, koef=5.0
  └─ BHN, B.02, koef=20.0

HargaItemProject:
  ├─ L.01, harga_satuan=150000
  └─ B.02, harga_satuan=50000
```

**User Action:**
```javascript
// User delete L.01 (only save B.02)
{"rows": [{"kode": "B.02", ...}]}
```

**System Response:**
```
1. Validate: ✓
2. Replace-all:
   - DELETE all DetailAHSPProject
   - DELETE all DetailAHSPExpanded
   - CREATE new with only B.02
3. HargaItemProject L.01 REMAINS (not deleted)
4. Invalidate cache

Impact:
  ⚠️ Harga Items:
     • L.01 still visible IF used by other pekerjaan
     • L.01 ORPHANED IF this was only usage
  ✓ Rincian AHSP: L.01 tidak muncul lagi
  ✓ Total pekerjaan reduced

Orphan Detection Query:
  SELECT * FROM harga_item_project h
  WHERE NOT EXISTS (
    SELECT 1 FROM detail_ahsp_expanded e
    WHERE e.harga_item_id = h.id
  )
```

---

### **SKENARIO 6: Add Bundle**

**Initial State:**
```
Pekerjaan A: (empty)
Pekerjaan B:
  ├─ TK, L.01, koef=5.0
  └─ BHN, B.02, koef=10.0
```

**User Action:**
```javascript
// User add bundle di Pekerjaan A
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
   ✓ Target has components (NOT EMPTY) ← NEW VALIDATION!
2. Save to DetailAHSPProject:
   └─ LAIN, Bundle_B, ref_pekerjaan_id=456, koef=3.0
3. Expand bundle:
   • Fetch Pekerjaan B components
   • Multiply koefisien:
     - L.01: 5.0 × 3.0 = 15.0
     - B.02: 10.0 × 3.0 = 30.0
4. Save to DetailAHSPExpanded:
   ├─ TK, L.01, koef=15.0, source_bundle='Bundle_B'
   └─ BHN, B.02, koef=30.0, source_bundle='Bundle_B'
5. Invalidate cache

Impact:
  ✓ Harga Items:
     • L.01 visible
     • B.02 visible
     • Bundle_B NOT visible (bundles tidak ditampilkan)
  ✓ Rincian AHSP:
     • L.01 muncul dengan 📦 indicator
     • B.02 muncul dengan 📦 indicator
     • Total includes expanded components
```

**Validation: Empty Bundle Check**
```python
# views_api.py:1352-1366
target_component_count = DetailAHSPProject.objects.filter(
    project=project,
    pekerjaan=ref_pekerjaan_obj
).count()

if target_component_count == 0:
    return ERROR: "❌ Pekerjaan '...' tidak memiliki komponen AHSP.
                   Bundle harus mereferensi pekerjaan yang sudah memiliki komponen."
```

---

### **SKENARIO 7: Edit Bundle Reference (Change Target)**

**Initial State:**
```
Pekerjaan A: LAIN Bundle_B (ref=B, koef=3.0)
Pekerjaan B: TK L.01 (koef=5.0), BHN B.02 (koef=10.0)
Pekerjaan C: TK L.99 (koef=2.0), ALT A.01 (koef=8.0)

DetailAHSPExpanded (A):
  ├─ L.01, koef=15.0
  └─ B.02, koef=30.0
```

**User Action:**
```javascript
// Change bundle reference B → C
{
  "kode": "Bundle_B",
  "ref_pekerjaan_id": 789,  // Change to Pekerjaan C
  "koefisien": "3.0"
}
```

**System Response:**
```
1. Validate: ✓ Pekerjaan C exists and has components
2. Replace-all:
   - DELETE all DetailAHSPProject & DetailAHSPExpanded for A
   - CREATE new: LAIN Bundle_B, ref_pekerjaan_id=789
3. Expand NEW bundle (Pekerjaan C):
   - L.99: 2.0 × 3.0 = 6.0
   - A.01: 8.0 × 3.0 = 24.0
4. CREATE new DetailAHSPExpanded:
   ├─ L.99, koef=6.0
   └─ A.01, koef=24.0
5. Invalidate cache

Impact:
  ⚠️ Harga Items:
     • L.01, B.02 might become ORPHANED
     • L.99, A.01 created (harga=0)
  ⚠️ Rincian AHSP:
     • OLD components (L.01, B.02) disappear
     • NEW components (L.99, A.01) appear
     • Total completely different
  ⚠️ Risk: User loses price data for L.01/B.02 if orphaned

Recommendation:
  • Consider carefully before changing bundle reference
  • Check if old components are used elsewhere
  • Set prices for new components immediately
```

---

### **SKENARIO 8: Edit Bundle Koefisien**

**Initial State:**
```
Pekerjaan A: LAIN Bundle_B (ref=B, koef=3.0)
Pekerjaan B: TK L.01 (koef=5.0)

DetailAHSPExpanded (A):
  └─ L.01, koef=15.0
```

**User Action:**
```javascript
// Change koefisien 3.0 → 5.0
{"kode": "Bundle_B", "koefisien": "5.0"}
```

**System Response:**
```
1. Validate: ✓
2. Replace-all DetailAHSPProject: koef=5.0
3. Re-expand bundle:
   - L.01: 5.0 × 5.0 = 25.0
4. Update DetailAHSPExpanded: koef=25.0
5. Invalidate cache

Impact:
  ✓ Harga Items: No change
  ✓ Rincian AHSP: Jumlah harga recalculated
  ✓ Total updated automatically
```

---

### **SKENARIO 9: Delete Bundle**

**Initial State:**
```
Pekerjaan A:
  ├─ TK, L.99, koef=1.0
  └─ LAIN, Bundle_B, ref_pekerjaan_id=456, koef=3.0

DetailAHSPExpanded (A):
  ├─ L.99, koef=1.0
  ├─ L.01, koef=15.0 (from Bundle_B)
  └─ B.02, koef=30.0 (from Bundle_B)
```

**User Action:**
```javascript
// Delete bundle (only save L.99)
{"rows": [{"kode": "L.99", ...}]}
```

**System Response:**
```
1. Validate: ✓
2. Replace-all:
   - DELETE all DetailAHSPProject & DetailAHSPExpanded
   - CREATE new with only L.99
3. Invalidate cache

Impact:
  ⚠️ Harga Items: L.01, B.02 might become ORPHANED
  ✓ Rincian AHSP: Only L.99 remains
  ✓ Total drastically reduced
```

---

### **SKENARIO 10: Edit Bundle TARGET (Indirect Modification - CRITICAL!)**

**Initial State:**
```
Pekerjaan A: LAIN Bundle_B (ref=B, koef=3.0)
Pekerjaan B: TK L.01 (koef=5.0)

DetailAHSPExpanded (A):
  └─ L.01, koef=15.0
```

**User Action:**
```javascript
// User EDIT Pekerjaan B (not A!)
// Change L.01 koef: 5.0 → 8.0
```

**System Response:**
```
1. Save Pekerjaan B:
   - Update DetailAHSPProject for B
   - Update DetailAHSPExpanded for B

2. CASCADE RE-EXPANSION (AUTOMATIC!):
   - Detect Pekerjaan A references B
   - Re-expand Pekerjaan A automatically
   - Update DetailAHSPExpanded for A:
     └─ L.01, koef=24.0  ✅ (8.0 × 3.0)

3. Invalidate cache

Impact:
  ✓ Harga Items: No change
  ✅ Rincian AHSP (A): Automatically updated!
  ✅ Total recalculated with new values

BEFORE FIX (OLD BEHAVIOR):
  ❌ Pekerjaan A would show STALE data (koef=15.0)
  ❌ User would see WRONG totals

AFTER FIX (NEW BEHAVIOR):
  ✅ CASCADE RE-EXPANSION ensures data consistency
  ✅ All referencing pekerjaan automatically updated
```

**Multi-Level Cascade:**
```
Pekerjaan A: LAIN Bundle_B (ref=B)
Pekerjaan B: LAIN Bundle_C (ref=C)
Pekerjaan C: TK L.01 (koef=5.0)

User edits Pekerjaan C: koef 5.0 → 10.0

CASCADE SEQUENCE:
  1. Save C: koef=10.0
  2. Detect B references C → Re-expand B
  3. Detect A references B → Re-expand A
  4. All pekerjaan now have correct values ✅
```

---

## ⚠️ ERROR HANDLING & VALIDASI

### **Validation Rules**

| Validation | Check | Error Response |
|------------|-------|----------------|
| **Kategori Valid** | Must be TK/BHN/ALT/LAIN | 400: "Kategori tidak valid" |
| **Kode Unique** | Unique per pekerjaan | 400: "Kode sudah digunakan" |
| **Koefisien Non-Negative** | koef ≥ 0 | 400: "Koefisien harus ≥ 0" |
| **Kategori Immutable** | Cannot change kategori of existing item | 400: "Item '...' sudah ada dengan kategori '...'" |
| **Bundle Target Exists** | ref_pekerjaan_id exists | 400: "Pekerjaan #... tidak ditemukan" |
| **Bundle Target Not Empty** | Target has components | 400: "Pekerjaan '...' tidak memiliki komponen" |
| **No Circular Dependency** | A→B→C→A not allowed | 400: "Circular dependency detected: ..." |
| **Bundle Only for CUSTOM** | Only source_type=CUSTOM can have bundles | 400: "Hanya boleh untuk pekerjaan custom" |
| **Bundle Only for LAIN** | Only kategori=LAIN can have ref_pekerjaan | 400: "Hanya boleh pada kategori 'Lain-lain'" |
| **Max Expansion Depth** | Max 3 levels | 400: "Maksimum kedalaman bundle terlampaui" |

### **Error Message Format**

```json
{
  "ok": false,
  "user_message": "Human-readable summary",
  "errors": [
    {
      "field": "rows[0].kode",
      "message": "Kode 'L.01' sudah digunakan di pekerjaan ini"
    }
  ]
}
```

### **Concurrent Edit Protection**

**Row-Level Locking:**
```python
# views_api.py:1209-1211
pkj = (Pekerjaan.objects
       .select_for_update()  # Acquire row-level lock
       .get(id=pekerjaan_id, project=project))
```

**Optimistic Locking:**
```python
# Client sends client_updated_at timestamp
# Server checks against project.updated_at
if client_dt < server_dt:
    return 409 Conflict: "⚠️ KONFLIK DATA TERDETEKSI!
                          Data telah diubah oleh pengguna lain."
```

---

## 🚨 EDGE CASES & SOLUSI

### **EDGE CASE 1: Empty Bundle**

**Problem:**
```
User selects ref_pekerjaan yang tidak ada komponennya
→ Bundle expansion returns []
→ Rincian AHSP shows nothing
→ User sangat bingung!
```

**Solution: VALIDATION (IMPLEMENTED)**
```python
# views_api.py:1352-1366
if target_component_count == 0:
    return ERROR: "❌ Pekerjaan '...' tidak memiliki komponen AHSP."
```

**Status:** ✅ FIXED

---

### **EDGE CASE 2: Circular Dependency**

**Problem:**
```
Pekerjaan A: LAIN Bundle_B (ref=B)
Pekerjaan B: LAIN Bundle_A (ref=A)
→ Infinite recursion!
```

**Solution: VALIDATION (ALREADY EXISTS)**
```python
# services.py:101-149
def check_circular_dependency_pekerjaan(...):
    # Traverse bundle chain
    # Detect A→B→C→A cycle
    return (True, cycle_path) if cycle else (False, None)
```

**Status:** ✅ PROTECTED

---

### **EDGE CASE 3: Orphaned HargaItemProject**

**Problem:**
```
User renames kode or deletes items
→ Old HargaItemProject remains
→ Cluttered Harga Items page
```

**Solution: FILTER + CLEANUP (TODO)**

**Option A: UI Filter**
```javascript
// Add filter in Harga Items
<select id="filter-usage">
  <option value="used">Hanya yang Digunakan</option>
  <option value="orphaned">Tidak Digunakan</option>
</select>
```

**Option B: Cleanup API**
```python
@require_POST
def api_cleanup_orphaned_items(request, project_id):
    """Delete items with no expanded_refs"""
    orphaned = HargaItemProject.objects.filter(
        project_id=project_id
    ).annotate(
        ref_count=Count('expanded_refs')
    ).filter(ref_count=0)

    count = orphaned.count()
    orphaned.delete()

    return JsonResponse({
        "ok": True,
        "deleted_count": count
    })
```

**Status:** ⚠️ TODO

---

### **EDGE CASE 4: Concurrent Bundle Modification**

**Problem:**
```
User A: Edit Pekerjaan B (bundle target)
User B: Edit Pekerjaan A (references B)
→ Potential race condition
```

**Solution: TRANSACTION + LOCKING**
```python
@transaction.atomic
def api_save_detail_ahsp_for_pekerjaan(...):
    # Row-level lock prevents concurrent edits
    pkj = Pekerjaan.objects.select_for_update().get(...)

    # All operations in single transaction
    # Cascade re-expansion happens AFTER commit
    transaction.on_commit(cascade_operations)
```

**Status:** ✅ PROTECTED

---

## 🔧 TROUBLESHOOTING

### **Problem: Bundle tidak muncul di Harga Items**

**Penyebab:** Bundle (LAIN) tidak ditampilkan di Harga Items karena sudah di-expand.

**Solusi:**
- Bundle otomatis di-expand menjadi komponen TK/BHN/ALT
- Komponen expanded yang muncul di Harga Items
- Ini adalah behavior yang diinginkan (by design)

**Verifikasi:**
```sql
-- Check expanded components
SELECT * FROM detail_ahsp_expanded
WHERE pekerjaan_id = ? AND source_bundle_kode IS NOT NULL
```

---

### **Problem: Rincian AHSP total tidak update setelah edit harga**

**Penyebab:** Cache not invalidated atau browser cache

**Solusi:**
1. Hard refresh browser (Ctrl+Shift+R)
2. Check server logs untuk cache invalidation
3. Verify HargaItemProject updated:
```sql
SELECT * FROM harga_item_project WHERE kode = 'L.01'
```

---

### **Problem: Bundle expansion gagal (silent error)**

**Penyebab:**
- Target pekerjaan kosong
- Circular dependency
- Max depth exceeded

**Debug:**
```bash
# Check logs
grep "EXPAND_BUNDLE" /var/log/django.log

# Common errors:
# - "No components found in ref_pekerjaan"
# - "Circular dependency detected"
# - "Maksimum kedalaman bundle terlampaui"
```

**Solusi:**
- Validate target has components
- Break circular reference
- Reduce bundle nesting depth (max 3 levels)

---

### **Problem: Pekerjaan A masih show old values setelah edit Pekerjaan B**

**Penyebab (OLD BEHAVIOR):** Stale data - cascade re-expansion not implemented

**Status:** ✅ FIXED (cascade_bundle_re_expansion implemented)

**Verifikasi Fix:**
```bash
# Check logs after saving Pekerjaan B
grep "CASCADE_RE_EXPANSION" /var/log/django.log

# Expected output:
# [CASCADE_RE_EXPANSION] Found X pekerjaan referencing #B
# [CASCADE_RE_EXPANSION] Re-expanding pekerjaan ...
# [CASCADE_RE_EXPANSION] COMPLETE - Re-expanded X pekerjaan
```

---

## 📊 SUMMARY: COMPLETE WORKFLOW MATRIX

| User Action | Template AHSP | Harga Items | Rincian AHSP | Error Risk | Status |
|-------------|---------------|-------------|--------------|------------|--------|
| Add direct item | ✓ Saved | ✓ Created (harga=0) | ✓ Shown (total=0) | ✅ None | ✅ Ready |
| Edit koefisien | ✓ Updated | — No change | ✓ Recalculated | ✅ None | ✅ Ready |
| Edit kode | ✓ New kode | ⚠️ Orphan old | ✓ New kode shown | ⚠️ Orphan | ⚠️ OK |
| Change kategori | ❌ BLOCKED | — No change | — No change | ✅ Protected | ✅ Safe |
| Delete item | ✓ Removed | ⚠️ May orphan | ✓ Removed | ⚠️ Orphan | ⚠️ OK |
| Add bundle | ✓ Saved | ✓ Components shown | ✓ Expanded shown | ✅ Validated | ✅ Ready |
| Edit bundle ref | ✓ New ref | ⚠️ Old orphan, new added | ✓ New components | ⚠️ Data loss | ⚠️ OK |
| Edit bundle koef | ✓ Updated | — No change | ✓ Recalculated | ✅ None | ✅ Ready |
| Delete bundle | ✓ Removed | ⚠️ May orphan | ✓ Removed | ⚠️ Orphan | ⚠️ OK |
| Edit bundle target | ✓ (B modified) | — No change | ✅ CASCADE UPDATED | ✅ None | ✅ FIXED |

---

## 🎓 BEST PRACTICES

### **For Users:**

1. **Follow the 3-Phase Workflow:**
   - Phase 1: Complete Template AHSP (all components)
   - Phase 2: Set all prices in Harga Items
   - Phase 3: Review in Rincian AHSP

2. **Bundle Usage:**
   - Ensure target pekerjaan has components before referencing
   - Avoid circular references (A→B→A)
   - Limit bundle nesting to 2-3 levels maximum

3. **Price Management:**
   - Set prices immediately after adding new items
   - Use filter to find items with harga=0
   - Review Rincian AHSP to verify totals

4. **Kode Management:**
   - Avoid changing kode unless necessary
   - Use consistent naming convention
   - Check for shared usage before deleting

### **For Developers:**

1. **Always Use Transactions:**
   ```python
   @transaction.atomic
   def modify_detail_ahsp(...):
       # All DB operations here
       transaction.on_commit(cascade_operations)
   ```

2. **Always Invalidate Cache:**
   ```python
   transaction.on_commit(lambda: invalidate_rekap_cache(project))
   ```

3. **Always Validate Before Save:**
   - Check empty bundle
   - Check circular dependency
   - Check kategori immutability

4. **Always Log Critical Operations:**
   ```python
   logger.info(f"[OPERATION] Details: {details}")
   logger.error(f"[ERROR] Failure: {error}", exc_info=True)
   ```

---

## 📚 RELATED DOCUMENTATION

- [Template AHSP Documentation](./TEMPLATE_AHSP_DOCUMENTATION.md)
- [Rincian AHSP Documentation](./RINCIAN_AHSP_README.md)
- [Bundle Expansion Fix](./BUNDLE_EXPANSION_FIX.md)
- [Usage Examples](./USAGE_EXAMPLES.md)
- [API Reference](./API_REFERENCE.md)

---

## 🔄 CHANGELOG

### v2.0.0 (2025-XX-XX) - Cascade Re-Expansion
- ✅ **CRITICAL FIX:** Implemented cascade_bundle_re_expansion()
- ✅ **VALIDATION:** Added empty bundle target check
- ✅ **DOCUMENTATION:** Created comprehensive workflow guide
- ⚠️ **TODO:** Implement orphaned items cleanup API

### v1.0.0 - Initial Dual Storage
- Implemented dual storage architecture
- Added bundle expansion support
- Added circular dependency protection

---

**Last Updated:** 2025-01-XX
**Maintainer:** Development Team
**Status:** Active Development
