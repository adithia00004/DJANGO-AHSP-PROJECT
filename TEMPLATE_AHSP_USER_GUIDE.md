# 📘 Template AHSP - Panduan Lengkap Pengguna

**Versi:** 2.0
**Tanggal:** 2025-11-09
**Status:** ✅ SIAP PRODUKSI

---

## 📋 Daftar Isi

1. [Apa itu Template AHSP?](#apa-itu-template-ahsp)
2. [Cara Kerja Sistem](#cara-kerja-sistem)
3. [Panduan Penggunaan](#panduan-penggunaan)
4. [Fitur Pekerjaan Gabungan](#fitur-pekerjaan-gabungan)
5. [Tips & Trik](#tips--trik)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)

---

## 1. Apa itu Template AHSP?

**Template AHSP** adalah halaman untuk mengelola **rincian komponen AHSP** (Analisa Harga Satuan Pekerjaan) untuk setiap pekerjaan dalam proyek.

### Komponen AHSP terdiri dari 4 kategori:

| Kategori | Deskripsi | Contoh |
|----------|-----------|--------|
| **TK** (Tenaga Kerja) | Pekerja, mandor, tukang | Pekerja, Mandor, Tukang Batu |
| **BHN** (Bahan) | Material/bahan konstruksi | Semen, Pasir, Kerikil |
| **ALT** (Alat) | Peralatan/equipment | Excavator, Molen, Vibrator |
| **LAIN** (Pekerjaan Gabungan) | Referensi ke AHSP lain atau pekerjaan lain | Pekerjaan Galian Tanah |

---

## 2. Cara Kerja Sistem

### 2.1 Source Type (Sumber Data)

Setiap pekerjaan memiliki **source_type** yang menentukan cara kerja Template AHSP:

#### A. REF (Referensi) - READ ONLY
```
┌─────────────────────────────────────┐
│ Source: AHSP 2025 (REF)             │
│ Status: 🔒 READ-ONLY               │
├─────────────────────────────────────┤
│ Data diambil dari master AHSP       │
│ TIDAK BISA diedit                   │
│ Otomatis sync dengan referensi      │
└─────────────────────────────────────┘
```

**Ciri-ciri:**
- ✅ Badge: "AHSP 2025" atau "AHSP {tahun}"
- 🔒 Semua field disabled (tidak bisa edit)
- 📖 Hanya bisa lihat data
- 🔄 Otomatis update jika referensi berubah

**Kapan digunakan:**
- Pekerjaan menggunakan AHSP standar tanpa modifikasi

---

#### B. REF_MODIFIED (Ref Modified) - EDITABLE + RESET
```
┌─────────────────────────────────────┐
│ Source: AHSP 2025 (modified)        │
│ Status: ✏️ EDITABLE                │
├─────────────────────────────────────┤
│ Clone dari AHSP, bisa diubah        │
│ Bisa di-RESET ke referensi original │
│ Perubahan disimpan di database      │
└─────────────────────────────────────┘
```

**Ciri-ciri:**
- ✅ Badge: "AHSP 2025 (modified)"
- ✏️ Semua field bisa diedit
- 🔄 Ada tombol "Reset to Ref" untuk kembali ke original
- 💾 Perubahan disimpan permanen

**Kapan digunakan:**
- AHSP standar tapi perlu sedikit modifikasi
- Ingin keep option untuk reset ke original

**Tombol "Reset to Ref":**
- Menghapus semua perubahan
- Kembali ke data referensi original
- ⚠️ TIDAK BISA UNDO!

---

#### C. CUSTOM (Kustom) - FULLY EDITABLE
```
┌─────────────────────────────────────┐
│ Source: Kustom                      │
│ Status: ✏️ FULLY EDITABLE          │
├─────────────────────────────────────┤
│ Dibuat manual dari nol              │
│ TIDAK ada referensi                 │
│ Full kontrol atas semua komponen    │
└─────────────────────────────────────┘
```

**Ciri-ciri:**
- ✅ Badge: "Kustom"
- ✏️ Semua field bisa diedit
- ➕ Bisa tambah/hapus row sesuka hati
- 🔗 Bisa pakai fitur "Pekerjaan Gabungan" (LAIN)

**Kapan digunakan:**
- Pekerjaan spesifik yang tidak ada di AHSP standar
- Butuh kontrol penuh atas komponen

---

### 2.2 Alur Data

```
┌─────────────────────────────────────────────────────────┐
│ 1. USER INPUT (Template AHSP)                          │
│    - Pilih pekerjaan dari sidebar                      │
│    - Isi komponen (TK/BHN/ALT/LAIN)                    │
│    - Klik "Simpan"                                      │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 2. AUTO-UPSERT HARGA ITEMS                             │
│    - Sistem otomatis create/update HargaItemProject    │
│    - Satu kode_item = satu HargaItemProject            │
│    - Shared across all pekerjaan                       │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 3. SAVE DETAIL AHSP                                    │
│    - DELETE semua row lama untuk pekerjaan ini         │
│    - INSERT semua row baru                             │
│    - Atomik transaction (all-or-nothing)               │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 4. CACHE INVALIDATION                                  │
│    - Hapus cache rekap (force recalculation)           │
│    - Rekap akan dihitung ulang next time diakses       │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Panduan Penggunaan

### 3.1 Membuka Template AHSP

1. Login ke sistem
2. Pilih project
3. Klik menu **"Template AHSP"** di sidebar

**Screenshot:** *(Insert screenshot here)*

---

### 3.2 Pilih Pekerjaan

**Sidebar Pekerjaan:**
```
┌────────────────────────────────┐
│ Cari pekerjaan...    🔍 Cari   │
├────────────────────────────────┤
│ ▸ 1.1 Pekerjaan Tanah          │
│   ├─ 1.1.1 Galian Tanah [REF]  │ ← Klik untuk load
│   ├─ 1.1.2 Urugan [MOD]        │
│   └─ 1.1.3 Pemadatan [CUS]     │
│ ▸ 1.2 Pekerjaan Pondasi        │
└────────────────────────────────┘
```

**Cara mencari:**
- Ketik keyword di search box (contoh: "galian")
- Filter otomatis tampil

**Badge indikator:**
- **REF** = Referensi (read-only)
- **MOD** = Modified (editable + reset)
- **CUS** = Custom (fully editable)

---

### 3.3 Mengedit Komponen (CUSTOM/REF_MODIFIED)

#### Tambah Baris Baru

1. Pilih segment (TK/BHN/ALT/LAIN)
2. Klik tombol **"+ Baris"** di segment header
3. Row baru muncul dengan **koefisien default = 1,000000**
4. Isi field:
   - **Uraian**: Deskripsi item (wajib)
   - **Kode**: Kode item (wajib, harus unik)
   - **Satuan**: Satuan (opsional, contoh: OH, m³, Zak)
   - **Koefisien**: Angka koefisien (wajib, default 1,000000)

**Contoh:**
```
┌──────────────────────────────────────────────────────────┐
│ TENAGA KERJA                      [+ Baris] [🗑️ 0 baris] │
├──┬──────────────────┬─────────┬────────┬────────────────┤
│No│ Uraian           │ Kode    │ Satuan │ Koefisien      │
├──┼──────────────────┼─────────┼────────┼────────────────┤
│1 │ Pekerja          │ L.01    │ OH     │ 2,500000       │
│2 │ Mandor           │ L.04    │ OH     │ 0,100000       │
└──┴──────────────────┴─────────┴────────┴────────────────┘
```

#### Hapus Baris

1. **Centang** checkbox di kolom No untuk baris yang ingin dihapus
2. Counter di tombol **"🗑️ X baris"** akan update
3. Klik tombol **"🗑️ X baris"**
4. Row terpilih akan dihapus

**Multi-select:**
- Centang beberapa baris sekaligus
- Hapus batch dengan 1 klik

---

### 3.4 Menyimpan Perubahan

1. Setelah edit komponen, klik **"Simpan"** di toolbar
2. Sistem akan validasi:
   - ✅ Uraian tidak boleh kosong
   - ✅ Kode tidak boleh kosong
   - ✅ Kode harus unique (tidak boleh duplikat)
   - ✅ Koefisien harus angka ≥ 0
3. Jika validasi gagal, muncul error message:
   ```
   ⚠️ Periksa isian: rows[0].koefisien - Wajib
   ```
4. Jika sukses:
   ```
   ✅ Tersimpan
   ```

**Status Dirty:**
- Indikator **"● Belum disimpan"** muncul saat ada perubahan
- Hilang setelah save sukses

---

### 3.5 Keyboard Shortcuts

| Shortcut | Aksi |
|----------|------|
| `Ctrl/⌘ + S` | Simpan perubahan |
| `Enter` | Pindah ke sel berikutnya (horizontal) |
| `Shift + Enter` | Pindah ke sel sebelumnya |
| `Del` | Hapus baris (saat cell terfokus) |
| `Tab` | Pindah ke field berikutnya |

---

## 4. Fitur Pekerjaan Gabungan (LAIN)

### 4.1 Apa itu Pekerjaan Gabungan?

**Pekerjaan Gabungan** adalah fitur untuk **memasukkan seluruh komponen dari pekerjaan lain** ke dalam pekerjaan saat ini.

**Contoh Use Case:**
```
Pekerjaan: "1.3 Pekerjaan Galian + Urugan"
└─ Segment LAIN:
   ├─ [BUNDLE] 1.1.1 Galian Tanah (koef 2.0)
   │  └─ Akan expand jadi:
   │     ├─ TK: Pekerja (2.5 × 2.0 = 5.0)
   │     ├─ BHN: Pasir (10.0 × 2.0 = 20.0)
   │     └─ ALT: Excavator (1.5 × 2.0 = 3.0)
   │
   └─ [BUNDLE] 1.1.2 Urugan (koef 1.5)
      └─ Akan expand jadi:
         ├─ TK: Pekerja (3.0 × 1.5 = 4.5)
         └─ BHN: Tanah Urug (15.0 × 1.5 = 22.5)
```

### 4.2 Cara Menggunakan

**HANYA untuk pekerjaan CUSTOM!**

#### Step 1: Tambah Baris di Segment LAIN

1. Klik **"+ Baris"** di segment **LAIN**
2. Row baru muncul

#### Step 2: Pilih Pekerjaan Referensi

1. Klik di field **"Kode item"**
2. Dropdown **Select2** muncul dengan 2 grup:

```
┌─────────────────────────────────────────┐
│ Cari AHSP atau Pekerjaan...             │
├─────────────────────────────────────────┤
│ 📂 Pekerjaan Proyek                    │
│    [CUS] A001 — Bundle Job A           │
│    [MOD] B002 — Detail Job B           │
│                                         │
│ 📂 Master AHSP                         │
│    AHSP.001 — Galian Tanah Biasa       │
│    AHSP.002 — Urugan Tanah             │
└─────────────────────────────────────────┘
```

3. Pilih salah satu pekerjaan
4. Field akan **auto-fill**:
   - ✅ Kode
   - ✅ Uraian
   - ✅ Satuan
   - ✅ Koefisien = 1,000000 (default)

5. Tag **"Bundle"** muncul di kolom Kode

#### Step 3: Set Koefisien (Multiplier)

- **Koefisien** di bundle = **multiplier**
- Contoh: koefisien 2.0 = semua komponen dikali 2

**Rumus:**
```
Koefisien Final = Koefisien Komponen × Koefisien Bundle
```

#### Step 4: Simpan

1. Klik **"Simpan"**
2. Sistem akan:
   - ✅ Validasi circular dependency (A → B → A tidak boleh!)
   - ✅ Validasi self-reference (A → A tidak boleh!)
   - ✅ **EXPAND** bundle jadi komponen individual
   - ✅ Simpan komponen hasil expansion (TK/BHN/ALT)
   - ✅ **HAPUS** row LAIN bundle (sudah di-expand)

**Hasil setelah save:**
```
SEBELUM SAVE:
┌────────────────────────────────────┐
│ LAIN                               │
├──┬────────────────────────────────┤
│1 │ [Bundle] B002 - Job B (koef 2) │
└──┴────────────────────────────────┘

SETELAH SAVE (AUTO-EXPANDED):
┌────────────────────────────────────┐
│ TK                                 │
├──┬─────────────────────┬──────────┤
│1 │ Pekerja             │ 5.0      │ ← 2.5 × 2.0
└──┴─────────────────────┴──────────┘
│ BHN                                │
├──┬─────────────────────┬──────────┤
│1 │ Semen               │ 20.0     │ ← 10.0 × 2.0
└──┴─────────────────────┴──────────┘
│ LAIN                               │
├──┴────────────────────────────────┤
│ (kosong - bundle sudah di-expand) │
└────────────────────────────────────┘
```

---

### 4.3 Proteksi Circular Dependency

Sistem **otomatis mendeteksi** dan **mencegah** circular dependency:

#### Contoh Circular Dependency yang DITOLAK:

**Scenario 1: Self-Reference**
```
Pekerjaan A → referensi ke Pekerjaan A (diri sendiri)
❌ ERROR: "Pekerjaan tidak boleh mereferensi diri sendiri"
```

**Scenario 2: 2-Level Circular**
```
Pekerjaan A → referensi Pekerjaan B
Pekerjaan B → referensi Pekerjaan A
❌ ERROR: "Circular dependency detected: A → B → A"
```

**Scenario 3: 3-Level Circular**
```
Pekerjaan A → referensi Pekerjaan B
Pekerjaan B → referensi Pekerjaan C
Pekerjaan C → referensi Pekerjaan A
❌ ERROR: "Circular dependency detected: A → B → C → A"
```

**Proteksi:**
- ✅ BFS (Breadth-First Search) algorithm
- ✅ Max depth = 10 levels
- ✅ Deteksi real-time saat save

---

### 4.4 Multi-Level Bundle (Nested)

Bundle bisa **nested** (bertingkat) sampai **10 level**:

```
Pekerjaan A (LAIN)
└─ referensi ke Pekerjaan B (koef 2.0)
   └─ Pekerjaan B (LAIN)
      └─ referensi ke Pekerjaan C (koef 1.5)
         └─ Pekerjaan C (base components)
            ├─ TK: Pekerja (koef 3.0)
            └─ BHN: Semen (koef 10.0)

HASIL EXPANSION di Pekerjaan A:
- TK: Pekerja (3.0 × 1.5 × 2.0 = 9.0)
- BHN: Semen (10.0 × 1.5 × 2.0 = 30.0)
```

**Max Depth:**
- Batas: 10 levels
- Error jika exceeded: "Maksimum kedalaman bundle terlampaui"

---

## 5. Tips & Trik

### 5.1 Naming Convention untuk Kode Item

**Rekomendasi:**
```
TK:   L.01, L.02, L.03, L.04 (Tenaga Kerja)
BHN:  M.01, M.02, M.03 (Material)
ALT:  E.01, E.02, E.03 (Equipment)
LAIN: B.01, B.02 (Bundle)
```

**Keuntungan:**
- ✅ Mudah dibedakan by prefix
- ✅ Konsisten across pekerjaan
- ✅ Sorting otomatis by kategori

---

### 5.2 Copy Komponen Antar Pekerjaan

**Cara manual:**
1. Buka pekerjaan sumber
2. **Export CSV**
3. Copy row yang diinginkan
4. Buka pekerjaan tujuan
5. Paste manual (atau import CSV jika fitur ada)

**Cara otomatis (via Bundle):**
1. Gunakan fitur **Pekerjaan Gabungan (LAIN)**
2. Reference ke pekerjaan sumber
3. Save → auto-expand

---

### 5.3 Bulk Edit Koefisien

**Scenario:** Update koefisien semua Pekerja dari 2.5 → 3.0

**Cara:**
1. Export CSV
2. Find & Replace di Excel: "2,500000" → "3,000000"
3. Import CSV (jika fitur ada)

**Atau:**
- Edit manual satu per satu (lebih aman)

---

### 5.4 Validasi Before Save

**Checklist sebelum save:**
- [ ] Semua Uraian terisi
- [ ] Semua Kode terisi dan unique
- [ ] Semua Koefisien terisi dan valid (angka)
- [ ] Tidak ada kode duplikat
- [ ] Bundle tidak circular

---

## 6. Troubleshooting

### ❌ Error: "rows[0].koefisien - Wajib"

**Penyebab:** Field koefisien kosong

**Solusi:**
1. Cari row index 0 (row pertama)
2. Isi koefisien dengan angka (contoh: 1,000000)
3. Save lagi

---

### ❌ Error: "Kode duplikat"

**Penyebab:** Ada 2+ row dengan kode sama

**Solusi:**
1. Cari row dengan kode duplikat
2. Ganti salah satu kode
3. Save lagi

**Contoh:**
```
❌ WRONG:
Row 1: Kode = L.01
Row 2: Kode = L.01 ← Duplikat!

✅ CORRECT:
Row 1: Kode = L.01
Row 2: Kode = L.02 ← Unique
```

---

### ❌ Error: "Circular dependency detected"

**Penyebab:** Bundle reference membuat loop

**Solusi:**
1. Review struktur bundle
2. Hapus reference yang membuat circular
3. Save lagi

**Contoh:**
```
❌ WRONG:
Pekerjaan A → referensi B
Pekerjaan B → referensi A ← Circular!

✅ CORRECT:
Pekerjaan A → referensi C (base)
Pekerjaan B → referensi C (base)
```

---

### ❌ Error: "Pekerjaan tidak boleh mereferensi diri sendiri"

**Penyebab:** Self-reference di LAIN

**Solusi:**
1. Pilih pekerjaan LAIN yang berbeda
2. Bukan pekerjaan yang sedang diedit

---

### ❌ Tombol "Simpan" Disabled

**Penyebab:** Source type = REF (read-only)

**Solusi:**
1. Pekerjaan REF tidak bisa diedit
2. Ubah source_type di **List Pekerjaan** jadi CUSTOM atau REF_MODIFIED
3. Reload Template AHSP

---

### ❌ Data Hilang Setelah Reload

**Penyebab 1:** Lupa save

**Solusi:** Selalu klik "Simpan" sebelum pindah pekerjaan

**Penyebab 2:** Concurrent edit (multi-user)

**Solusi:**
- Koordinasi dengan tim
- Refresh page sebelum edit
- Save lebih sering

---

### ❌ Koefisien Format Salah

**Penyebab:** Input format tidak sesuai locale

**Solusi:**
- Gunakan koma (,) untuk desimal: `1,234567`
- JANGAN gunakan titik untuk ribuan: `1.000,00` ← WRONG
- Format otomatis saat blur dari field

**Contoh:**
```
✅ CORRECT: 1,234567
✅ CORRECT: 0,5
✅ CORRECT: 10
❌ WRONG: 1.234567 (titik, tapi akan auto-convert)
```

---

## 7. FAQ

### Q1: Perbedaan HargaItemProject vs DetailAHSPProject?

**A:**
```
HargaItemProject (MASTER):
- 1 row per unique kode_item per project
- Shared across all pekerjaan
- Berisi: kode, uraian, satuan, kategori, HARGA SATUAN
- Dikelola di page "Harga Items"

DetailAHSPProject (DETAIL):
- Many rows per pekerjaan
- Berisi: kode, uraian, satuan, kategori, KOEFISIEN
- Dikelola di page "Template AHSP"
- Reference ke HargaItemProject via FK
```

**Analogi:**
- **HargaItemProject** = Katalog produk (master)
- **DetailAHSPProject** = Item di shopping cart (detail per pekerjaan)

---

### Q2: Apa yang terjadi saat save Template AHSP?

**A:**
```
1. Validasi input (kode, uraian, koefisien)
2. Expand bundle (jika ada LAIN)
3. Upsert HargaItemProject (auto-create/update master)
4. DELETE semua DetailAHSPProject lama untuk pekerjaan ini
5. INSERT semua DetailAHSPProject baru
6. Update pekerjaan.detail_ready = True
7. Invalidate cache rekap
```

**Catatan:**
- Replace-all strategy (DELETE + INSERT)
- Atomik transaction (all-or-nothing)
- Jika gagal, rollback otomatis

---

### Q3: Kenapa koefisien default 1,000000?

**A:**
- Default sensible untuk kebanyakan kasus
- User bisa langsung save tanpa isi manual
- Mencegah validation error karena kosong

**Custom default:**
- TK: 1.0 (1 orang)
- BHN: 1.0 (1 unit)
- ALT: 1.0 (1 unit)
- LAIN: 1.0 (1× multiplier)

---

### Q4: Bisa import/export CSV?

**A:**
- ✅ Export CSV: Ada (tombol "Export" di toolbar)
- ❌ Import CSV: Belum ada (future feature)

**Export format:**
```csv
kategori;kode;uraian;satuan;koefisien
TK;L.01;Pekerja;OH;2.500000
BHN;M.01;Semen;Zak;10.000000
```

---

### Q5: Apa itu "Reset to Ref"?

**A:**
- Tombol khusus untuk REF_MODIFIED
- Menghapus semua custom changes
- Kembali ke data referensi original
- ⚠️ TIDAK BISA UNDO!

**Confirm dialog:**
```
⚠️ Reset rincian dari referensi?
Perubahan lokal akan hilang.

[Batal]  [OK, Reset]
```

---

### Q6: Bundle expansion terjadi kapan?

**A:**
- **Saat SAVE** (bukan saat load)
- Bundle di-expand jadi komponen base (TK/BHN/ALT)
- Row LAIN bundle dihapus setelah expansion
- User tidak lihat bundle di database, hanya komponen hasil expansion

**Timeline:**
```
User Input → Save → Expand Bundle → Store Components → User Reload
                     ^^^^^^^^^^^^
                     Terjadi di sini
```

---

### Q7: Max berapa row per pekerjaan?

**A:**
- **Tidak ada limit hard** di kode
- **Praktis:** 100-200 row per pekerjaan (performance)
- Jika > 200 row, consider breakdown jadi sub-pekerjaan

---

### Q8: Bisa edit multiple pekerjaan sekaligus?

**A:**
- ❌ Tidak bisa bulk edit
- Edit satu pekerjaan at a time
- Switch pekerjaan via sidebar (auto-save prompt jika ada changes)

---

### Q9: Apa yang terjadi jika delete pekerjaan?

**A:**
```
DELETE Pekerjaan
  └─ CASCADE → DELETE all DetailAHSPProject
                └─ HargaItemProject tetap ada (shared)
```

**Catatan:**
- ⚠️ Data detail AHSP hilang permanent
- HargaItemProject tidak ikut terhapus (shared)
- Belum ada soft delete (future feature)

---

### Q10: Concurrent edit aman?

**A:**
- ⚠️ **TIDAK** sepenuhnya aman (belum ada optimistic locking)
- Last write wins
- **Rekomendasi:**
  - Koordinasi tim (satu user edit satu pekerjaan)
  - Refresh page sebelum edit
  - Save lebih sering

**Future improvement:**
- Optimistic locking dengan detail_version field
- Conflict detection
- Merge UI

---

## 📞 Support

**Pertanyaan atau Issue?**
- 📧 Email: support@example.com
- 📝 GitHub Issues: [Link]
- 📚 Dokumentasi Teknis: TEMPLATE_AHSP_DOCUMENTATION.md

---

**Versi:** 2.0
**Terakhir Update:** 2025-11-09
**Status:** ✅ PRODUCTION READY
