# Spesifikasi Validasi Data Import AHSP

**Tanggal:** 2026-06-02
**Tujuan:** Mendefinisikan jenis & struktur data AHSP yang masuk ke validator, mana yang acceptable, mana yang bisa diperbaiki otomatis, dan mana yang dilompati karena kerusakan terlalu besar. Ditulis lebih dulu agar perbaikan validator berbasis **pemahaman struktur**, bukan detektor yang menerka.
**Grounding:** dibedah dari file nyata `media/exports/Import 2026/3.1 AHSP_Part_1.xlsx` (hasil konversi PDF mode `VALIDATION_HYBRID`, 1722 baris, 109 tabel terdeteksi).
**Catatan:** ASCII-only (hindari mojibake).

> **STATUS (2026-06-02): FIX UTAMA DITERAPKAN.** `_get_validation_results` kini membaca baris format kolom-tetap **by-posisi** (gate `is_fixed_format` -> compact re-pack hanya untuk workbook ringkas), dan baris legenda di-skip. Hasil pada fixture nyata `3.1 AHSP_Part_1.xlsx`: tabel ter-block keliru **86 -> 0**, tabel `Unknown` **1 -> 0**, item Bahan tanpa Kode terbaca benar (S1). Regression test: `test_wide_fixed_format_empty_kode_is_not_a_shift`. Acceptance A1/A2/A3/A7 terpenuhi; A4/A5/A6 dijaga oleh perilaku existing (warning pasif, wrapped, shift asli via compute_block_status).

---

## 0. Prinsip

1. **Baca berdasarkan struktur yang diketahui, jangan menebak.** Format konversi punya kolom tetap; baca by-posisi. Re-packing "sel tak kosong" hanya boleh untuk input yang benar-benar compact.
2. **Sel kosong bukan kerusakan.** Kode item kosong (umum untuk Bahan/Peralatan) adalah data VALID, bukan kolom bergeser.
3. **Pisahkan 3 keputusan:** (a) baris ini apa, (b) tabel ini valid/repairable/skip, (c) apakah boleh masuk Data Valid.
4. **Skip itu sah.** Tabel yang rusak parah dilewati dengan alasan jelas; jangan paksa diperbaiki dengan tebakan.

---

## 1. Sumber & Format Input yang Diterima

| Format | Asal | Dipakai di | Cara baca |
|---|---|---|---|
| **Konversi PDF (fixed-column)** | Opsi 1 mode `import`/`validation`/`validation_hybrid`/`source` | Opsi 2 (validation report) | **by-posisi kolom tetap** (lihat Bagian 2) |
| **AHSP Interchange v1** | Output Opsi 2 (`export_from_frontend`) | Opsi 3 (clean import) | by-nama kolom (`import_schema.load_workbook_rows`) |
| **Legacy flat / "Daftar Isi"+"Data Valid"** | Ekspor lama | Opsi 3 (fallback) | adapter khusus |

Dokumen ini fokus pada **format konversi fixed-column** karena di situ bug validasi terjadi.

---

## 2. Layout Kolom Format Konversi (FIXED)

Sheet `Data`, 11 kolom tetap (indeks 0-based):

| Idx | Kolom | Isi | Catatan |
|---|---|---|---|
| 0 | Parent / Judul | kode parent, atau teks judul, atau legenda | |
| 1 | Segmen | `HEADER` / `TK` / `BHN` / `PR` / kosong | penanda blok |
| 2 | No | nomor item; atau `A`/`B`/`C` (segment title); atau `JUMLAH HARGA ...` | |
| 3 | Uraian | nama item | |
| 4 | **Kode** | kode referensi item (mis. `L.01`) | **SERING KOSONG** untuk Bahan/Peralatan -- ini VALID |
| 5 | Satuan | mis. `OH`, `buah`, `m2` | |
| 6 | Koefisien | desimal (boleh koma: `0,1500`) | |
| 7 | (ghost) | kosong | artefak konversi |
| 8 | Harga Satuan (Rp) | kosong di mode validasi | diabaikan |
| 9 | Jumlah Harga (Rp) | kosong di mode validasi | diabaikan |
| 10 | Status | catatan konversi (`OK`/`REDUNDANT...`/`WARNING...`) | advisory; **bukan** sumber kebenaran |

**Aturan baca (KRITIS):** ambil `No=col_2, Uraian=col_3, Kode=col_4, Satuan=col_5, Koef=col_6` **langsung dari posisi tetap**. JANGAN membuang sel kosong lalu mengemas ulang -- itu menggeser data bila `Kode` (col_4) kosong.

---

## 3. Taksonomi Baris (row types)

| Tipe baris | Cara dikenali | Contoh (dari file nyata) | Penanganan |
|---|---|---|---|
| **Legenda/metadata** | di atas data; col_0 `[ LEGENDA ...]`/`[MERAH]` dst | `['[ LEGENDA WARNA ]']` | **IGNORE** (jangan jadi tabel/anomali) |
| **Klasifikasi** | col_0 token = 2 segmen angka | `1.1 ...` | hierarki (bukan data AHSP) |
| **Sub-klasifikasi** | col_0 token = 3 segmen angka | `3.1.1 ATAP GENTENG ...` | hierarki |
| **Parent (judul AHSP)** | col_0 token = 4-5 segmen (+suffix opsional), baris sel-tunggal/sparse | `3.1.1.1 Pemasangan 1 m2 Atap ...` | header AHSP -> `nama_ahsp` |
| **Header kolom tabel** | col_1 = `HEADER`; berisi "No/Uraian/Kode/..." | `[3.1.1.1, HEADER, No, Uraian, ...]` | REDUNDANT -> skip |
| **Judul segmen** | col_2 = `A`/`B`/`C`; col_3 = `TENAGA KERJA`/`BAHAN`/`PERALATAN` | `[3.1.1.1, TK, A, TENAGA KERJA]` | penanda segmen -> skip tapi DICATAT |
| **Item data** | col_1 = `TK`/`BHN`/`PR`; col_2 numerik; col_3 uraian | `[3.1.1.1, TK, 1, Pekerja, L.01, OH, 0,1500]` | **DATA** |
| **Item data (Kode kosong)** | sama, tapi col_4 kosong | `[3.1.1.1, BHN, 1, Genteng Palentong, (kosong), buah, 25,00]` | **DATA VALID** (kode_item = `-`) |
| **Subtotal/total** | col_2/col_3 mengandung `JUMLAH HARGA ...` atau `(A+B+C)` | `[3.1.1.1, TK, JUMLAH HARGA TENAGA KERJA]` | REDUNDANT -> skip |
| **Anomali/segmen tak dikenal** | col_1 tidak terpetakan ke TK/BHN/PR | `UK`/`LL`/teks asing | tandai ANOMALI |

---

## 4. Klasifikasi Tabel & Keputusan (matriks)

Per tabel AHSP (parent + baris-barisnya):

| Status tabel | Kriteria | Boleh masuk Data Valid? |
|---|---|---|
| **VALID** | punya >=1 item data well-formed di segmen standar; tidak ada baris bergeser/wrapped yang belum diperbaiki | YA |
| **WARNING (pasif)** | VALID, tetapi ada segmen standar yang tidak ada (mis. tanpa BHN/PR) -- sah untuk pekerjaan tertentu | YA (dengan catatan) |
| **REPAIRABLE** | ada baris wrapped (Uraian kosong tapi ada data) **atau** kolom benar-benar bergeser, yang punya kandidat perbaikan jelas | TIDAK sampai diperbaiki; tampilkan kandidat |
| **BLOCKED / SKIP** | kerusakan terlalu besar: segmen tak dikenal yang tak bisa dipetakan, parent code invalid, atau tak ada baris data yang bisa dikenali | TIDAK; dilewati dengan alasan |

**Catatan penting:** `Kode item kosong` BUKAN alasan REPAIRABLE/BLOCKED. Itu VALID.

---

## 5. Skenario Penanganan yang Sudah Diidentifikasi

| # | Skenario | Deteksi | Aksi sistem | Status implementasi |
|---|---|---|---|---|
| S1 | **Kode item kosong** (Bahan/PR tanpa kode ref) | col_4 kosong, sisanya wajar | Terima sebagai VALID, `kode_item='-'` | **PERLU FIX** (kini salah dianggap bergeser) |
| S2 | **Wrapped row** (Uraian kosong, tapi Satuan/Koef/Kode ada) | col_3 kosong & ada data lain di segmen TK/BHN/PR | REPAIRABLE: kandidat isi Uraian; blokir tabel sampai diperbaiki | Ada (`detect_wrapped_row`) |
| S3 | **Kolom benar-benar bergeser** | No kosong **DAN** Uraian numerik **DAN** Kode = teks panjang **DAN** Koef numerik **DAN col_4 sumber memang terisi** | REPAIRABLE: kandidat geser balik | Ada (`detect_shifted_numbered_row`) -- **terlalu agresif, perlu dipersempit** (lihat Bagian 6) |
| S4 | **Segmen standar tidak lengkap** (tanpa BHN/PR) | segmen hilang | WARNING pasif; tetap exportable | Ada (`compute_block_status`) |
| S5 | **Baris redundant** (HEADER kolom, JUMLAH HARGA, judul segmen, legenda) | pola di Bagian 3 | Skip otomatis, tidak dihitung sebagai data/anomali | Sebagian (legenda masih bocor -> "Unknown" table) |
| S6 | **Segmen tak dikenal / ANOMALI** | col_1 tak terpetakan | Tandai ANOMALI; bila >0 -> tabel BLOCKED | Ada |
| S7 | **Tabel zombie/kosong** (header tanpa item data) | tak ada item data di segmen mana pun | Skip dari Data Valid | Sebagian (terdeteksi di Summary; perlu konsisten di report) |
| S8 | **Desimal koma** (`0,1500`) | format angka lokal | Normalisasi `,`->`.` | Ada |
| S9 | **Kode suffix** (`2.2.1.1.5.a`) | huruf di segmen terakhir | Didukung penuh | Ada |
| S10 | **Kode 3-segmen ambigu** (`3.2.1` AHSP vs `3.1.1` folder) | kode 3-segmen yang PUNYA baris TK/BHN/PR vs hanya header | **Berbasis data**: 3-5 segmen + data = AHSP parent; header telanjang tanpa data = folder sub-klasifikasi. JANGAN putuskan dari jumlah segmen saja. | **FIX DITERAPKAN** (lihat S10 di bawah) |

> **Aturan S10 (penting):** AHSP 2026 memakai kode 3-segmen untuk DUA hal -- folder (`3.1.1 ATAP GENTENG`, hanya header) DAN item kerja nyata (`3.2.1 Pemasangan Insulasi`, punya TK/BHN/PR). Karena itu **jumlah segmen saja tidak menentukan** folder vs AHSP. Validator kini: kode 3-5 segmen yang membawa baris segmen = AHSP parent (data disimpan); kode yang ternyata tanpa tabel data dikembalikan jadi folder sub-klasifikasi. Hasil pada file nyata: 13 AHSP 3-segmen (`3.2.x/3.3.x/3.4.x`) kini tersimpan dengan data; `3.1.x/3.5.x/3.6.x` tetap folder; tidak ada lagi entri duplikat. Test: `test_three_segment_code_is_parent_when_it_has_data`.

---

## 6. Akar Masalah Saat Ini & Arah Perbaikan

### Bug yang terbukti (pada file nyata: 86/87 tabel ter-block keliru)
`_get_validation_results` punya blok **normalisasi compact-row**: bila segmen in {TK/BHN/PR/...} dan sel terakhir adalah status, ia membuang sel kosong (`nonempty_cells`) lalu mengemas ulang `nonempty_cells[2:-1]` **secara posisional**. Untuk item Bahan dengan **Kode kosong**, sel itu hilang -> payload 4 elemen -> dipetakan salah:
```
sumber:  No=1  Uraian="Genteng Palentong"  Kode=(kosong)
jadi:    No=-  Uraian="1"  Kode="Genteng Palentong"
```
Lalu `detect_shifted_numbered_row` (S3) menandainya bergeser -> tabel ter-BLOCKED. Karena hampir semua AHSP punya item Bahan tanpa kode, 86/87 tabel terblokir.

### Perbaikan (berbasis Bagian 2)
1. **Baca by-posisi tetap** untuk format konversi: pakai `col_0..col_6` langsung dari baris (sudah benar, termasuk sel kosong). **Batasi** blok compact-repack agar **tidak aktif** untuk baris format kolom-tetap (mis. ketika jumlah kolom baris > 7 / ada kolom Harga/ghost). Compact-repack hanya untuk input yang benar-benar ringkas.
2. **Pertajam S3 (`detect_shifted_numbered_row`)** agar hanya menyala bila ada bukti kuat geser **pada data sumber** -- bukan artefak normalisasi. Setelah #1, S3 tidak lagi melihat baris Kode-kosong sebagai geser.
3. **Tutup kebocoran legenda** (S5): baris sebelum parent pertama / baris legenda tidak boleh membentuk tabel "Unknown" ber-ANOMALI.

### Yang TIDAK diubah
- Cara user membuat file (sudah benar).
- Kebijakan: missing BHN/PR = warning pasif (S4); wrapped = repairable (S2); suffix didukung (S9).

---

## 7. Acceptance / Skenario Uji (pakai data nyata)

Fixture kanonik: `media/exports/Import 2026/3.1 AHSP_Part_1.xlsx` (atau turunannya yang dipangkas untuk test).

- **A1:** Tabel `3.1.1.1` (punya item Bahan tanpa kode) -> **VALID/warning**, BUKAN blocked "Kolom Bergeser". `BHN` ter-baca `No=1, Uraian="Genteng Palentong", Kode="-"`.
- **A2:** Item TK ber-kode (`L.01`) tetap terbaca benar (regresi).
- **A3:** Baris `JUMLAH HARGA ...` & judul segmen & HEADER & legenda -> skip, tidak jadi anomali; tidak ada tabel `Unknown`.
- **A4:** Tabel tanpa segmen BHN/PR -> warning pasif, tetap exportable (S4).
- **A5:** Wrapped row asli (Uraian kosong + data) -> tetap REPAIRABLE/blocked (S2) -- jangan ikut "diperbaiki" oleh fix ini.
- **A6:** Kolom benar-benar bergeser (No kosong + Uraian numerik + Kode teks panjang **dengan col_4 sumber terisi**) -> tetap terdeteksi S3.
- **A7:** Jumlah tabel ter-block keliru pada file nyata = **0** (turun dari 86).

---

## 8. Definisi "Acceptable" (ringkas)

Sebuah tabel AHSP **acceptable untuk Data Valid** bila:
- parent code valid (2-5 segmen angka, suffix huruf opsional), DAN
- punya >=1 item data di segmen standar (TK/BHN/PR), DAN
- item datanya well-formed by-posisi (Uraian terisi; Kode boleh kosong; Koef terbaca), DAN
- tidak ada baris wrapped/bergeser **asli** yang belum diperbaiki, DAN
- tidak ada segmen ANOMALI yang tak terpetakan.

Segmen standar yang tidak lengkap (mis. tanpa BHN/PR) **tidak** menggugurkan acceptability -- hanya warning pasif.
