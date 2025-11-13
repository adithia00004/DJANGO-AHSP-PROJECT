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
- Support bundle reference: dari Pekerjaan lain (ref_kind='job') ATAU AHSP Master (ref_kind='ahsp')
- TANPA kolom harga (fokus pada komponen & koefisien)
- **Manual Save** dengan tombol "Simpan"
- **Optimistic Locking**: Deteksi konflik jika pengguna lain edit bersamaan
- Auto-expand bundle setelah save berhasil

↓

**HARGA ITEMS (PRICING)**
- Set harga satuan untuk setiap item
- Hanya tampilkan items yang digunakan (dari DetailAHSPExpanded)
- Filter: TK/BHN/ALT (bundle LAIN tidak ditampilkan karena sudah di-expand)
- **Manual Save** dengan tombol "Simpan"
- **Optimistic Locking**: Deteksi konflik
- **Harga Default**: NULL (ditampilkan sebagai 0.00 di UI)

↓

**RINCIAN AHSP (REVIEW & RECAP)**
- Tampilkan komponen DENGAN harga (join DetailAHSPExpanded + HargaItemProject)
- Kalkulasi total per pekerjaan dengan formula: Subtotal + BUK + PPN
- **Override Markup/BUK**: Per-pekerjaan override untuk profit/margin
- Visual distinction untuk bundle-expanded items
- Export RAB

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
  - L.99, harga_satuan=NULL  ← Auto-created, belum diisi (UI menampilkan "0.00")
  - A.01, harga_satuan=NULL  ← Auto-created, belum diisi (UI menampilkan "0.00")
```

**PENTING:** Harga baru disimpan sebagai NULL di database, bukan 0. UI hanya menampilkan "0.00" sebagai placeholder visual. Ini penting untuk audit data (NULL = belum diisi, 0 = sengaja diisi nol).

---

## ALUR KERJA STANDARD

### FASE 1: INPUT KOMPONEN (Template AHSP)

**Data Dependency:**
```
Read:  Pekerjaan list, existing DetailAHSPProject
Write: DetailAHSPProject (raw), DetailAHSPExpanded (computed), HargaItemProject (NULL harga)
```

**Tujuan:** Definisikan komponen AHSP untuk setiap pekerjaan

**Langkah:**
1. **Pilih Pekerjaan** dari sidebar (hanya SOURCE_CUSTOM dapat diedit di page ini)

2. **Input Komponen Direct** (TK/BHN/ALT):
   - Masukkan kode, uraian, satuan, koefisien
   - Kode harus unique per pekerjaan

3. **Input Bundle** (LAIN - optional):
   - **Pilih dari 2 sumber:**
     - **Pekerjaan Proyek** (ref_kind='job'): Bundle dari pekerjaan lain di project ini
     - **Master AHSP** (ref_kind='ahsp'): Bundle dari AHSP Referensi standard
   - Gunakan Select2 autocomplete: ketik untuk search
   - System validasi: target harus memiliki komponen (tidak boleh empty)

4. **Klik Tombol "Simpan"** (Manual Save - BUKAN auto-save!)
   - System validate input (client-side + server-side)
   - **Optimistic Locking**: System cek apakah ada user lain yang edit bersamaan

   **Jika ADA KONFLIK (data diubah user lain):**
   ```
   Dialog muncul dengan 2 pilihan:

   [OK] = Muat Ulang
        → Refresh page, lihat perubahan terbaru
        → Data yang Anda ketik AKAN HILANG

   [Cancel] = Timpa
        → Simpan data Anda, perubahan user lain AKAN HILANG
        → Gunakan hanya jika yakin perubahan Anda lebih penting
   ```

   **Jika TIDAK ADA KONFLIK:**
   - Create/update HargaItemProject (harga_satuan=NULL untuk item baru)
   - Expand bundle ke DetailAHSPExpanded
   - **CASCADE RE-EXPANSION**: Re-expand pekerjaan lain yang reference pekerjaan ini
   - Toast sukses: "✅ Data berhasil disimpan!"
   - Jika ada bundle: "📦 N bundle di-expand menjadi M komponen tambahan"

**Hasil:**
```
✓ DetailAHSPProject: Raw input tersimpan
✓ DetailAHSPExpanded: Komponen expanded ready untuk pricing
✓ HargaItemProject: Auto-created untuk items baru (harga_satuan=NULL, UI: "0.00")
✓ Cascade: Pekerjaan referencing ini auto-updated
→ Lanjut ke Harga Items untuk set harga!
```

---

### FASE 2: SET HARGA (Harga Items)

**Data Dependency:**
```
Read:  DetailAHSPExpanded (untuk list items yang digunakan), HargaItemProject (existing harga)
Write: HargaItemProject.harga_satuan, ProjectPricing.markup_percent (global BUK)
Note:  Fase ini HANYA memuat komponen dari DetailAHSPExpanded, sehingga bundle LAIN tidak muncul
```

**Tujuan:** Set harga satuan untuk setiap item yang digunakan

**Langkah:**
1. **Filter Items** (optional):
   - Filter by kategori (TK/BHN/ALT)
   - Filter by search (kode/uraian)

2. **Review Items**:
   - Items ditampilkan: yang ada di DetailAHSPExpanded (TK/BHN/ALT only)
   - Items TIDAK ditampilkan: bundle LAIN (sudah di-expand ke komponennya)
   - **Harga NULL ditampilkan sebagai "0.00"** dengan visual indicator (border merah/class 'vp-empty')

3. **Set Harga Satuan**:
   - Input harga per item (format: ribuan dengan titik atau koma)
   - Validation: non-negative, max 2 decimal places, max value ~999 triliun
   - Empty input akan diisi otomatis dengan 0
   - Tombol "Konversi" untuk bantu hitung konversi satuan (optional)

4. **Set Project Profit/Margin** (optional):
   - Global BUK % untuk seluruh project (default 10%)
   - Input di bagian atas form

5. **Klik Tombol "Simpan"** (Manual Save - BUKAN auto-save!)
   - System validate semua input
   - **Optimistic Locking**: System cek apakah ada user lain yang edit bersamaan

   **Jika ADA KONFLIK (data diubah user lain):**
   ```
   Dialog muncul dengan 2 pilihan:

   [OK] = Muat Ulang
        → Refresh page, lihat harga terbaru
        → Perubahan harga Anda AKAN HILANG

   [Cancel] = Timpa
        → Simpan harga Anda, perubahan user lain AKAN HILANG
        → Gunakan hanya jika yakin data Anda lebih akurat
   ```

   **Jika TIDAK ADA KONFLIK:**
   - Update HargaItemProject.harga_satuan (NULL → nilai yang diinput)
   - Save konversi satuan (jika ada yang di-flag "ingat ke server")
   - Update ProjectPricing.markup_percent (jika diubah)
   - Invalidate rekap cache
   - Toast sukses: "✅ Data harga berhasil disimpan!"

**Hasil:**
```
✓ HargaItemProject: Harga satuan updated (NULL → nilai input)
✓ Cache invalidated: Rincian AHSP akan show updated prices
✓ Rekap akan recalculate dengan harga baru
→ Lanjut ke Rincian AHSP untuk review total!
```

---

### FASE 3: REVIEW & RECAP (Rincian AHSP)

**Data Dependency:**
```
Read:  DetailAHSPExpanded (komponen), HargaItemProject (harga),
       ProjectPricing (global BUK/PPN), Pekerjaan.markup_override_percent
Write: Pekerjaan.markup_override_percent (per-pekerjaan override)
Join:  DetailAHSPExpanded + HargaItemProject ON kode
```

**Tujuan:** Review komponen dengan harga dan total per pekerjaan

**Langkah:**
1. **Pilih Pekerjaan** dari sidebar kiri
   - Pekerjaan dengan override BUK ditandai dengan chip warning (warna berbeda)
   - HSP (Harga Satuan Pekerjaan) ditampilkan di sebelah kode

2. **Review Komponen** (panel kanan):
   - Lihat kode, uraian, koefisien, harga satuan
   - Items dari bundle ditandai dengan badge `[Bundle_X]`
   - Jumlah harga = koefisien × harga satuan

3. **Check Total** (panel kanan bawah):
   ```
   Formula Kalkulasi:
   ─────────────────────────────────────────────────
   A. TK (Tenaga Kerja)    = Σ(koef × harga)  [TK items]
   B. BHN (Bahan)          = Σ(koef × harga)  [BHN items]
   C. ALT (Alat)           = Σ(koef × harga)  [ALT items]
   L. LAIN                 = 0 (bundle tidak counted, sudah expanded)

   E. Subtotal             = A + B + C + L
   F. BUK (Profit/Margin)  = E × (BUK% / 100)
   G. HSP per Satuan       = E + F

   (Di level project):
   D. Total Pekerjaan      = G × Volume
   PPN                     = D × (PPN% / 100)
   Grand Total             = D + PPN
   ```

4. **Override Markup/BUK** (OPTIONAL - Fitur Khusus):

   **Kapan Menggunakan Override:**
   - Pekerjaan tertentu memerlukan profit margin berbeda dari project default
   - Contoh: pekerjaan high-risk perlu BUK lebih tinggi, pekerjaan simple perlu BUK lebih rendah
   - **Effective BUK** yang dipakai sistem: override (jika ada) ATAU project default

   **Cara Menggunakan:**
   ```
   a. Klik tombol "⚙️ Override BUK" (di panel detail pekerjaan)

   b. Dialog muncul:
      - Project Default BUK: 10.00% (read-only)
      - Override BUK: [input field]
      - Validation: 0-100%, max 2 decimal

   c. Input nilai override (misal: 15.5%)

   d. Klik "Simpan"
      - System validate (0-100%)
      - POST ke /api/projects/{id}/pekerjaan/{id}/pricing/
      - Update Pekerjaan.markup_override_percent
      - Invalidate rekap cache
      - Sidebar auto-refresh: chip warning muncul
      - Total pekerjaan auto-recalculate

   e. Untuk CLEAR override (kembali ke project default):
      - Kosongkan input field ATAU
      - Klik "Reset ke Default"
      - System save NULL ke markup_override_percent
   ```

   **Visual Indicators:**
   - Pekerjaan dengan override: chip warning di sidebar (misal: "15.50%")
   - Pekerjaan normal: tidak ada chip (menggunakan default)
   - Tooltip hover: "Override BUK: 15.50% (default: 10.00%)"

5. **Export RAB** (optional):
   - Tombol export untuk generate RAB dengan semua kalkulasi

**Hasil:**
```
✓ Total pekerjaan calculated dengan benar (respecting override BUK)
✓ Grand total project updated dengan effective BUK per-pekerjaan
✓ Override tersimpan dan persistent
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
- Pekerjaan berulang (misal: kolom struktural CUSTOM yang user buat untuk dipakai berkali-kali)
- Pekerjaan komposit (misal: "Finishing Lengkap" terdiri dari beberapa sub-pekerjaan)
- Template work packages

**CATATAN PENTING:** Bundle hanya bisa ditambahkan ke **pekerjaan CUSTOM** (pekerjaan yang dibuat user), TIDAK bisa ke pekerjaan dari AHSP Referensi. Lihat penjelasan source_type di bawah.

---

### PENTING: Jenis Pekerjaan (source_type)

Sebelum menggunakan bundle, pahami dulu 3 jenis pekerjaan dalam sistem:

| source_type | Nama | Asal | Editable di Template AHSP? | Bisa Pakai Bundle? |
|-------------|------|------|----------------------------|-------------------|
| **REF** | Referensi | Import dari AHSP Referensi | ❌ READ-ONLY | ❌ Tidak bisa |
| **CUSTOM** | Custom | Dibuat user dari nol | ✓ Full edit | ✓ Bisa |
| **REF_MODIFIED** | Ref Modified | Clone dari REF + modifikasi | ⚠️ Edit di page lain | ❌ Di page ini tidak |

**Penjelasan Detail:**

1. **SOURCE_REF (Referensi)**
   - Pekerjaan yang di-import dari AHSP Referensi standard
   - Status: **READ-ONLY** di halaman Template AHSP
   - Tidak bisa edit komponen, tidak bisa tambah bundle
   - Untuk modifikasi: gunakan halaman "Rincian AHSP Gabungan"

2. **SOURCE_CUSTOM (Custom)**
   - Pekerjaan yang dibuat user dari nol
   - Status: **FULLY EDITABLE** di halaman Template AHSP
   - Bisa edit komponen, bisa tambah bundle
   - **INI SATU-SATUNYA jenis pekerjaan yang bisa pakai bundle di page ini**

3. **SOURCE_REF_MOD (Ref Modified)**
   - Clone dari pekerjaan REF yang sudah dimodifikasi
   - Status: Editable di halaman "Rincian AHSP Gabungan", TIDAK di Template AHSP
   - Workflow berbeda (tidak dibahas di dokumen ini)

**Mengapa Bundle Hanya untuk CUSTOM?**

Rule "Only for CUSTOM" bukan arbitrary restriction, tapi konsistensi dengan read-only policy:
- Pekerjaan REF = read-only di page ini → tidak bisa edit apapun (termasuk tambah bundle)
- Pekerjaan REF_MODIFIED = edit di workflow lain → tidak ditampilkan untuk edit di page ini
- Pekerjaan CUSTOM = fully editable → bisa tambah bundle

**Contoh Workflow yang Benar:**
```
Scenario: User ingin pakai bundle untuk "Kolom Standard" yang dipakai 10x

✓ BENAR:
1. User buat Pekerjaan CUSTOM baru: "Kolom Standard A"
   → source_type = 'custom'
2. Isi komponen: TK, BHN, ALT
3. Di 10 pekerjaan lain (yang juga CUSTOM), tambahkan bundle:
   → LAIN, Bundle_Kolom_A, ref_pekerjaan = "Kolom Standard A"
4. System auto-expand ke 10 pekerjaan tersebut

✗ SALAH:
1. User import pekerjaan dari AHSP Referensi
   → source_type = 'ref' (READ-ONLY)
2. User coba tambah bundle
   → ERROR: "Hanya boleh untuk pekerjaan custom"
```

**Summary:**
- "Pekerjaan berulang" dalam dokumentasi = **CUSTOM pekerjaan yang user CREATE untuk reuse**
- BUKAN pekerjaan dari AHSP Referensi standard
- Bundle adalah fitur untuk pekerjaan yang **user kontrol penuh (CUSTOM)**

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
Pilih: Pekerjaan A (Sumber) - harus SOURCE_CUSTOM

Tab LAIN (Bundle):
  - Kode: [Autocomplete dengan Select2]
    - Ketik untuk search (min. 1 karakter)
    - Hasil ditampilkan dalam 2 grup:
      ┌─────────────────────────────────────────┐
      │ 📋 Pekerjaan Proyek                     │
      │   [CUSTOM] PKJ.001 — Kolom Standard A   │
      │   [CUSTOM] PKJ.005 — Balok Standard B   │
      ├─────────────────────────────────────────┤
      │ 📚 Master AHSP                          │
      │   A.1.1.1 — Galian Tanah Biasa         │
      │   A.1.2.3 — Timbunan Tanah Kembali     │
      └─────────────────────────────────────────┘

    - Pilih salah satu (job atau ahsp)

  - System Auto-fill:
    - Uraian: otomatis dari pilihan
    - Satuan: otomatis dari pilihan
    - ref_kind: 'job' atau 'ahsp' (hidden field)
    - ref_id: ID dari pilihan (hidden field)

  - Koefisien: Input manual (misal: 3.0)
    - Default: 1.0 jika kosong

**Client-Side Validation (Immediate):**
- Jika pilih Pekerjaan Proyek (ref_kind='job'):
  - System fetch detail pekerjaan via API
  - Jika EMPTY (0 komponen): Toast warning
    ⚠️ "Bundle Kosong: [nama] belum memiliki komponen AHSP.
        Silakan isi detail AHSP terlebih dahulu..."
  - Selection dibatalkan otomatis
  - User harus pilih pekerjaan lain atau isi target dulu

- Jika pilih Master AHSP (ref_kind='ahsp'):
  - No client validation (AHSP master selalu valid)

**Klik "Simpan":**
- Server-side validation (double-check)
- Bundle expansion (lihat STEP 3)
```

**PERBEDAAN Bundle dari Pekerjaan vs AHSP Master:**

| Aspek | Bundle dari Pekerjaan (job) | Bundle dari AHSP Master (ahsp) |
|-------|----------------------------|--------------------------------|
| **ref_kind** | 'job' | 'ahsp' |
| **Source** | Pekerjaan lain di project ini | AHSP Referensi standard |
| **Dynamic** | ✓ Bisa berubah jika target diubah | ✗ Static dari master |
| **Cascade** | ✓ Cascade re-expansion jika target diubah | ✗ Tidak ada cascade |
| **Validation** | Harus punya komponen (empty check) | Selalu valid (dari master) |
| **Use Case** | Pekerjaan berulang dalam project | Template standard nasional |

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
   - Auto-creates HargaItemProject (harga_satuan=NULL, UI: "0.00")

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

**Q: Kenapa error "Hanya boleh untuk pekerjaan custom" saat saya coba tambah bundle?**
A: Bundle hanya bisa ditambahkan ke pekerjaan dengan source_type='CUSTOM' (pekerjaan yang dibuat user dari nol). Pekerjaan dari AHSP Referensi (source_type='REF') adalah read-only di page ini dan tidak bisa ditambahkan bundle. Jika Anda ingin pakai bundle, buat pekerjaan CUSTOM baru dulu, lalu tambahkan bundle di situ.

**Q: Dokumentasi bilang "pekerjaan berulang" bisa pakai bundle, tapi pekerjaan saya dari referensi ditolak?**
A: "Pekerjaan berulang" yang dimaksud adalah **CUSTOM pekerjaan yang user buat untuk dipakai berulang kali**, BUKAN pekerjaan dari AHSP Referensi standard. Workflow yang benar: Buat pekerjaan CUSTOM → isi komponen → pakai sebagai bundle di pekerjaan lain.

---

### Validation Rules untuk Bundle

| Rule | Check | Error Message | Penjelasan |
|------|-------|---------------|------------|
| Target Exists | ref_pekerjaan_id valid? | "Pekerjaan #... tidak ditemukan" | Target bundle harus ada di database |
| **Target Not Empty** | Target has components? | **"Pekerjaan '...' tidak memiliki komponen"** (BARU!) | Target harus sudah punya komponen AHSP sebelum bisa dijadikan bundle |
| No Circular | A→B→A not allowed | "Circular dependency detected: ..." | Prevent infinite loop (A reference B, B reference A) |
| Max Depth | depth <= 3 | "Maksimum kedalaman bundle terlampaui" | Maksimum nesting: A→B→C (3 levels) |
| Only for LAIN | kategori == 'LAIN' | "Hanya boleh pada kategori 'Lain-lain'" | Bundle reference hanya di kategori LAIN |
| **Only for CUSTOM** | source_type == 'CUSTOM' | "Hanya boleh untuk pekerjaan custom" | **Context:** Pekerjaan REF adalah read-only di page ini. REF_MOD diedit di page lain. Hanya CUSTOM pekerjaan yang fully editable di Template AHSP. **Reason:** Konsistensi dengan read-only policy untuk non-CUSTOM pekerjaan. |

**Catatan untuk "Only for CUSTOM" Rule:**
- Ini BUKAN batasan arbitrary
- Ini konsekuensi dari: Pekerjaan REF = read-only → tidak bisa edit apapun (termasuk bundle)
- Untuk detail source_type, lihat section [PENTING: Jenis Pekerjaan (source_type)](#penting-jenis-pekerjaan-source_type) di atas

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
    harga_satuan=NULL  # Belum diisi, UI: "0.00"
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
       → HargaItemProject.get_or_create() (harga_satuan=NULL for new)
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
3. Upsert HargaItemProject(kode=L.99, harga_satuan=NULL)
4. Pass-through to DetailAHSPExpanded (no expansion needed)
5. Invalidate cache

Impact:
  → Harga Items: L.99 muncul dengan harga "0.00" (NULL di DB, placeholder di UI)
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
5. Auto-create HargaItemProject for L.01, B.02 (harga_satuan=NULL, UI: "0.00")
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
| Add direct item | ✓ Saved | ✓ Created (NULL → "0.00" UI) | ✓ Shown | ✓ Ready |
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
