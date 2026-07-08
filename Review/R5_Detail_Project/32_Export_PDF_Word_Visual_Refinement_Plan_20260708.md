# 32 — Rencana Perbaikan Visual & Keterbacaan Export PDF/Word

**Tanggal:** 2026-07-08
**Status:** v1.2 — AKTIF; O-8 + Fase 0 SELESAI (log §12); Fase 1 siap jalan
**Penyusun:** Claude (audit sesi 2026-07-08, tanpa perubahan kode)
**Reviewer:** Codex (review independen atas v1.0 — koreksi diadopsi, lihat §11)
**Referensi terkait:** Doc 30 (keputusan presisi 2dp WP Export), Doc 12 (Export System review)

---

## 1. Ringkasan Eksekutif

**Tujuan:** hasil export PDF & Word terasa seperti dokumen profesional yang konsisten
(tipografi, perataan, spasi, warna seragam) — **tanpa menambah beban server**, dan
**tanpa mengubah keputusan desain yang sudah disengaja**.

**Prinsip kunci hasil audit:** sumber "tampilan amatir" dan sumber "boros CPU" di kode
export adalah **pola yang sama** (styling diputuskan lokal per-fungsi/per-sel, bukan dari
satu aturan). Memperbaiki konsistensi dengan cara yang benar justru **menurunkan** beban
server, bukan menaikkannya.

**Struktur rencana:**
- **Fase 0** — Baseline (ukur dulu, tanpa perubahan).
- **Fase 1** — Konsolidasi fondasi (behavior-preserving: tampilan TIDAK berubah, kode lebih ringan).
- **Fase 2** — PDF jalur data (behavior-changing terkendali: perubahan visual yang disetujui).
- **Fase 3** — Word jalur data (paritas dengan PDF).
- **Bagian 7** — Item OPEN yang menunggu keputusan owner per-item (TIDAK dieksekusi tanpa jawaban).

---

## 2. Peta Arsitektur Saat Ini

Ada 3 jalur penghasil PDF/Word dengan tingkat kematangan berbeda:

| Jalur | Dipakai oleh | Bentuk output | File kunci |
|---|---|---|---|
| **A. Native tabel** (`ExportManager` → `PDFExporter.export` / `WordExporter.export`) | Rekap RAB, Rekap Kebutuhan, Volume Pekerjaan, Harga Items, Rincian AHSP | Tabel asli, teks dapat diseleksi | `detail_project/exports/pdf_exporter.py`, `word_exporter.py`, `export_manager.py` |
| **B. Native "professional"** (`export_professional`) | Jadwal Pekerjaan (PDF rekap/bulanan/mingguan), Laporan Harian (Word template) | Laporan bersampul + grafik Kurva S digambar manual | `pdf_exporter.py:957+`, `word_exporter.py:98+` (daily) |
| **C. Screenshot** (`generate_pdf_from_pages` / `generate_word_from_pages`) | Kurva-S/Gantt visual dari frontend | PNG base64 ditempel ke halaman | `detail_project/views_export.py:431-572` |

**Scope rencana ini: Jalur A (utama) + fondasi bersama.** Jalur B dan C hanya disentuh
pada item yang disetujui eksplisit (lihat §7).

### Konfigurasi styling saat ini (akar masalah)

Ada **dua modul yang sama-sama mengaku SSOT** dan nilainya saling bertentangan:

| Aspek | `detail_project/export_config.py` | `detail_project/exports/table_styles.py` |
|---|---|---|
| Header tabel | `ExportColors.HEADER_BG = 'e8e8e8'` (abu-abu) | `UTS.HEADER_BG = '#1e3a5f'` (navy) |
| Judul dokumen | `ExportFonts.TITLE = 18` | `ED.FONT_SIZE_TITLE = 16` |
| Body tabel | `ExportFonts.LEVEL3 = 9` | `ED.FONT_SIZE_NORMAL = 8`; grid `UTS.DATA_FONT_SIZE = 6` |
| Margin | `ExportLayout: 20/20/15/15 mm` | `ED: 10/10/10/10 mm` |

Halaman berbeda mengambil nilai dari sumber berbeda → inkonsistensi struktural yang
akan selalu kambuh selama dua sumber ini hidup berdampingan.

---

## 3. Registri Keputusan Desain yang DISENGAJA (DO-NOT-TOUCH)

Hasil audit ulang (grep marker intent + pembacaan komentar kode). **Semua item di bawah
DIPERTAHANKAN.** Perubahan apa pun terhadapnya butuh persetujuan owner eksplisit,
terpisah dari dokumen ini.

| # | Keputusan | Bukti |
|---|---|---|
| R-1 | **Lebar tabel FIXED 100% + kolom pengisi kosong (blank filler)** — lebar kolom minggu identik di semua halaman grid | `table_styles.py:349` ("FIXED: Usable width same for all tables"), `pdf_exporter.py:2145-2185` |
| R-2 | **Maks 18 minggu per halaman** grid Jadwal | `table_styles.py:216`, `export_config.py:193` |
| R-3 | **Arial 7pt untuk baris data grid Word** | `word_exporter.py:1138` — "per user request" |
| R-4 | **Tanda tangan DIHAPUS dari laporan bulanan PDF** | `pdf_exporter.py:1826, 5210, 5671` — "per user request" |
| R-5 | **Page indicator DIHAPUS di segmen Kurva S portrait** | `pdf_exporter.py:5202` — "per user request" |
| R-6 | **Rekap Kebutuhan orientasi portrait** | `export_manager.py:241-244` — "User specified" |
| R-7 | **Label seksi berbahasa tertentu** ("Input Progress Planned", dst.) | `table_styles.py:723` — "as requested by user" |
| R-8 | **Header Excel tertentu** | `excel_exporter.py:2496` — "per user request" |
| R-9 | **Gantt/Kurva S tidak dirender di Word** (bukan format native Word) | `word_exporter.py:650-652` |
| R-10 | **Suppress nilai 0% di grid** (kurangi clutter & ukuran file) | `word_exporter.py:1089-1101`, `pdf_exporter.py:2080-2083` |
| R-11 | **Rincian AHSP tanpa page break antar pekerjaan** (compact) | `pdf_exporter.py:886`, `word_exporter.py:532` |
| R-12 | **Laporan harian sengaja ringkas** (tanpa volume/bobot/progress) | `export_manager.py:1110` |
| R-13 | **Aturan anti-orphan tanda tangan** (min 3 baris konten sehalaman dengan ttd) | `signature_config.py:160-263` |
| R-14 | **Laporan mingguan tanpa sheet Kurva S** | `excel_exporter.py:3964` |
| R-15 | **Kontrak presisi WP Export**: nilai kanonik Decimal, 2dp id-ID di boundary exporter via `materialize_display_rows` | Doc 30; `exports/cell_format.py` |
| R-16 | **NULL/kosong ≠ 0,00 pada Harga Items export** — harga yang belum diisi tampil kosong/`-`, BUKAN `0,00` (nol finansial sungguhan tetap tampil `0,00`) | Commit `4ce0870f` (WP Export slice Harga Items) |

---

## 4. Temuan Kondisi Saat Ini (drift — tidak ada jejak kesengajaan)

### 4.1 Konsistensi visual

| # | Temuan | Lokasi | Dampak ke user |
|---|---|---|---|
| T-1 | **3 warna biru header dalam satu dokumen**: `#1a365d` (tabel utama), `#2c5282` (PRIMARY_LIGHT, judul/rincian), `#1976D2` (tabel pengesahan) | `pdf_exporter.py:2194`, `table_styles.py:103`, `pdf_exporter.py:2017` | Halaman 1 vs halaman 2 Rekap RAB tampak seperti dua template berbeda |
| T-2 | **Dua SSOT konfigurasi bertentangan** (lihat §2) | `export_config.py` vs `table_styles.py` | Ukuran judul/margin/warna berubah tergantung jalur kode |
| T-3 | **Word body jatuh ke Calibri 11pt default** — font dokumen tidak pernah di-set di jalur generik; sel grid di-hardcode Arial | `word_exporter.py:210` (`Document()` tanpa set style), vs `:1125,1167` | Satu dokumen bercampur Calibri + Arial; terasa "tempelan" |
| T-4 | **Perataan angka tidak konsisten antar builder**: `_build_simple_table` kolom tengah CENTER; `_build_table` "3 kolom terakhir kanan"; base style tanpa ALIGN (kiri) | `pdf_exporter.py:1975, 2088, 527-534` | Kolom Qty/Harga kadang center, kadang kanan, kadang kiri — sinyal "amatir" terkuat di dokumen finansial |
| T-5 | **Judul dokumen PDF rata kiri vs Word rata tengah** untuk konten yang sama (Rincian AHSP) | `pdf_exporter.py:233` vs `word_exporter.py:346` | PDF dan Word tidak terasa satu produk |
| T-6 | **Blok identitas proyek**: PDF = tabel 3 kolom rapi; Word = paragraf "Label: value" berulang | `pdf_exporter.py:1862` vs `word_exporter.py:225-230` | Sama seperti T-5 |
| T-7 | **Spasi Word memakai paragraf kosong** (`doc.add_paragraph()` sebagai "enter-enter") | `word_exporter.py:231, 310, 819, dll.` | Layout rusak bila user mengedit dokumen; bukan pola native Word |
| T-8 | **Bold/style di Word via loop per-run manual**, bukan named styles | `word_exporter.py` (pola berulang `for para → for run`) | Word menganggap teks polos; Navigation Pane & TOC otomatis tidak berfungsi |
| T-9 | **Kebijakan nilai kosong campur**: `-`, string kosong, `0,00` | `pdf_exporter.py:2080` vs `word_exporter.py:1089` vs adapter | Tidak seragam antar halaman/format |

### 4.2 Beban server (pola boros yang juga menghambat konsistensi)

| # | Temuan | Lokasi | Biaya |
|---|---|---|---|
| T-10 | **`getSampleStyleSheet()` + `ParagraphStyle` baru dibuat PER SEL** | `pdf_exporter.py:2050-2059`; pola sama di `:2303, 3014, 3418, 3855, 4015` | Tabel 500×10 = 5.000 alokasi stylesheet dibuang; CPU+RAM |
| T-11 | **`_build_table` membungkus SEMUA sel jadi `Paragraph`** (flowable terberat ReportLab), termasuk sel angka pendek; pola serupa di builder professional (`:2303, 3014, 3418, 3855, 4015`). **Catatan v1.1:** `_build_simple_table` SUDAH selektif (hanya kolom wrap + multiline) — optimisasi dipetakan per-builder (Lampiran A), bukan pukul rata | `pdf_exporter.py:2074-2089` | Ribuan flowable tak perlu per export, di builder yang terdampak saja |
| T-12 | **Blank filler diisi objek `Paragraph('')`** padahal string `''` polos render identik | `pdf_exporter.py:2181-2185` | Objek tambahan per baris × kolom kosong. **Catatan: fiturnya (R-1) DIPERTAHANKAN — hanya implementasi diringankan** |
| T-13 | **Word: set lebar sel per-baris×per-kolom + shading OxmlElement per sel** | `word_exporter.py:1209-1219, 1112-1126` | XML besar, build lambat, file .docx besar |
| T-14 | `NumberedCanvas.save()` = wrapper no-op (hanya memanggil `super().save()`), tetapi komentarnya menjanjikan "second pass" total halaman (format 1/X) yang tidak pernah diimplementasikan — **penanda fitur setengah jadi, bukan sekadar kode mati** (koreksi v1.1) | `pdf_exporter.py:107-111` | Nol saat runtime; nasibnya digabung ke investigasi O-2, tidak dihapus terpisah |

---

## 5. Rencana Perubahan

### Fase 0 — Baseline (tanpa perubahan kode produk)

| Langkah | Detail |
|---|---|
| 0.1 | Jalankan seluruh suite export (~136+ test: `tests_wp_export_parity.py`, `tests_export_*.py`) → catat status hijau |
| 0.2 | Generate file contoh nyata dari 1 proyek uji: PDF+Word untuk Rekap RAB, Rekap Kebutuhan, Volume, Harga Items, Rincian AHSP → simpan sebagai pembanding "SEBELUM", **termasuk render PNG per halaman** (basis image-diff Fase 1) |
| 0.3 | **Script baseline kecil (dev-only)** yang mencatat durasi build + ukuran file per export ke CSV — bukan hanya mengandalkan logger manual (v1.1) |
| 0.4 | **Lengkapi matriks report → builder → sumber style** (Lampiran A) — sel berstatus TBD diverifikasi empiris di langkah ini (v1.1) |
| 0.5 | Siapkan tooling **visual-diff otomatis** dev-only: PDF→PNG (pymupdf/poppler) + image diff; DOCX→PDF via LibreOffice bila tersedia (opsional) (v1.1) |

**Risiko: nol** (tanpa perubahan kode produk; tooling diff adalah dependensi dev-only,
bukan runtime). Output fase ini = artefak pembanding untuk review Anda di fase berikutnya.

---

### Fase 1 — Konsolidasi fondasi (BEHAVIOR-PRESERVING: tampilan tidak berubah)

> Gate fase: file "SESUDAH" identik secara visual dengan "SEBELUM" — diverifikasi
> **image-diff otomatis** (tooling Fase 0.5), bukan hanya mata; semua test hijau;
> timing sama atau lebih cepat. **Fase 1 TIDAK mengubah nilai visual apa pun** —
> warna/font/margin tetap nilai lama; migrasi ke nilai baru terjadi di Fase 2,
> per-report (revisi v1.1 atas rencana alias v1.0).

| # | Perubahan | Kondisi saat ini | Menjadi | Alasan |
|---|---|---|---|---|
| 1.1 | **Style registry semantik + adapter per format** | Dua modul bertentangan (T-2); styling diputuskan lokal per-builder | Registry token semantik baru (`doc_title`, `section_heading`, `table_header`, `money_cell`, `text_cell`, `total_row`, dst.) + adapter PDF (ParagraphStyle/TableStyle) dan adapter Word (named styles). **`ExportColors`/`ExportFonts`/`ExportLayout` legacy TIDAK diubah nilainya** — konsumen lama tetap menerima nilai lama; migrasi ke registry dilakukan per-jalur eksplisit di Fase 2/3 | Menghentikan drift struktural TANPA risiko diam-diam mengubah output konsumen legacy (Excel dkk.) — koreksi review Codex |
| 1.2 | **Hoist stylesheet** | Style dibuat per sel (T-10) — terpetakan di `_build_table` + builder professional | `ParagraphStyle` didefinisikan sekali (registry 1.1 / `_create_styles()`), builder me-reuse; scope per-builder mengikuti matriks Lampiran A | Hemat CPU/RAM; satu definisi = satu tampilan |
| 1.3 | **Blank filler ringan** | `Paragraph('')` per sel kosong (T-12) | String `''` polos — render identik, diverifikasi image-diff | Hemat objek; **fitur R-1 tetap utuh 100%** |
| 1.4 | **Helper alignment tunggal dari `column_formats`** | Perataan hardcode berbeda-beda per builder (T-4) | Helper bersama: `'@'`=kiri, numerik=kanan, kolom No/Kode/Satuan=center. **Dibangun + unit test di Fase 1, DIAKTIFKAN per-report baru di Fase 2** — agar Fase 1 tetap bebas perubahan visual | Aturan objektif satu pintu; tidak dihardcode ulang di tiap builder (usulan review Codex) |
| 1.5 | **`NumberedCanvas.save()`** | T-14: wrapper no-op + komentar fitur "second pass" yang tak pernah diimplementasikan | **TIDAK dihapus di Fase 1** — dicatat, nasibnya mengikuti keputusan O-2 (page-numbering) | Hindari menghapus penanda fitur setengah jadi sebelum keputusannya jelas (koreksi review Codex) |

**Positif:** kode lebih ringan & terpusat; fondasi Fase 2-3; build export lebih cepat.
**Negatif:** tidak ada perubahan visual yang bisa "dirasakan" user di fase ini.
**Risiko & mitigasi:**

| Risiko | Level | Mitigasi |
|---|---|---|
| Konsumen legacy (Excel exporter dkk.) masih mengimpor `ExportColors/ExportFonts/ExportLayout` | Sedang | **v1.1: nilai legacy TIDAK diubah sama sekali di Fase 1** (tidak ada aliasing nilai); audit semua import tetap dilakukan; migrasi per-jalur eksplisit di Fase 2/3 dengan image-diff |
| Reuse style object ReportLab ternyata di-mutate di satu builder → menular ke builder lain | Rendah | Style di-hoist sebagai frozen/copy-on-write (buat varian bernama, bukan mutasi) |
| Test parity membandingkan struktur internal yang berubah | Rendah | Jalankan suite penuh per commit; commit kecil per item agar mudah `git revert` |

---

### Fase 2 — PDF jalur data (BEHAVIOR-CHANGING terkendali — inilah perubahan visual yang Anda review)

> Berlaku untuk 5 halaman jalur A: Rekap RAB, Rekap Kebutuhan, Volume, Harga Items,
> Rincian AHSP. **Grid Jadwal (jalur B) TIDAK disentuh** (menunggu O-1).
>
> **Pola pilot (v1.1):** mulai dari 1 report paling sederhana — **Harga Items** —
> hingga di-approve owner, baru replikasi polanya: Rekap Kebutuhan → Rekap RAB →
> Volume → Rincian AHSP. Perubahan warna/font dari registry 1.1 diaktifkan
> **per-report** di fase ini, bukan global sekaligus.

| # | Perubahan | Kondisi saat ini | Menjadi | Alasan |
|---|---|---|---|---|
| 2.1 | **Satu warna header tabel** | 3 biru berbeda (T-1) | Semua header tabel = `UTS.HEADER_BG` (#1e3a5f navy) + teks putih; aksen total memakai turunan navy/netral (mengganti hijau `#e8f5e9`/`#c8e6c9` di total E/F/G Rincian) | Dokumen terlihat satu sistem |
| 2.2 | **Skala tipografi 6 peran** | ~12 ukuran ad-hoc | Judul 16 bold navy · Judul seksi 11 bold · Header tabel 8 bold putih · Body 8 · Total/subtotal 8 bold · Caption/identitas 7 | Konsistensi + keterbacaan cetak (≥7pt) |
| 2.3 | **Perataan berbasis TIPE data** | Ditentukan posisi kolom per-builder (T-4) | Teks=kiri · Angka/mata uang/%=**kanan selalu** · No/Kode/Satuan=center · Header=center-middle. Diturunkan otomatis dari `column_formats` (`'@'`=teks, numerik=kanan) yang sudah ada di payload | Aturan objektif; angka rata kanan = standar dokumen finansial |
| 2.4 | **Kebijakan nilai kosong dipertajam (v1.1)** | Campur `-`/kosong/`0,00` (T-9) | **Tiga kelas dibedakan:** (a) `None`/tidak diisi → `-`; (b) 0% pada grid progress → tetap disuppress (R-10); (c) **angka finansial bernilai nol → tetap tampil `0,00`** — nol bermakna di dokumen biaya, konsisten R-16 | Seragam tanpa menghilangkan makna nol finansial (koreksi review Codex) |
| 2.5 | **Sel angka = string polos + ALIGN kolom** | Semua sel `Paragraph` (T-11) | Hanya kolom teks panjang (Uraian/Keterangan) yang wrap dengan `Paragraph` | Prasyarat 2.3 + hemat beban (lebih cepat) |
| 2.6 | **Spasi skala tetap** | Spacer acak 3/5/8/10/15mm | Skala 2/4/8/12mm dengan aturan pemakaian (judul→tabel: 4; antar tabel: 8; sebelum pengesahan: 12) | Ritme visual konsisten |
| 2.7 | **Judul + identitas seragam** | T-5, T-6 | Judul dokumen rata kiri + blok identitas tabel (pola PDF saat ini menjadi acuan kedua format) | Paritas PDF↔Word |

**Positif:**
- Perubahan yang paling langsung dirasakan user: angka rapi rata kanan, satu bahasa
  visual, terbaca saat dicetak.
- Lebih cepat dari kondisi sekarang (2.5 menghapus ribuan objek per export).

**Negatif / trade-off yang jujur:**
- Tampilan berubah — user lama yang hafal layout akan melihat pergeseran satu kali.
- Body 8pt (dari campuran 8/9) + spasi terstandar dapat menggeser titik potong halaman;
  jumlah halaman bisa berubah ±1 pada dokumen panjang.
- Banyak test export meng-assert struktur/isi sel → sebagian test perlu diperbarui
  (perubahan test = bagian dari pekerjaan, bukan efek samping tak terduga).

**Risiko & mitigasi:**

| Risiko | Level | Mitigasi |
|---|---|---|
| Aturan align dari `column_formats` salah tebak pada tabel yang belum punya `column_formats` | Sedang | Fallback ke perilaku lama per-tabel; migrasi tabel per tabel, bukan big-bang |
| Aksen warna total baru dianggap kurang kontras oleh owner | Rendah | Sampel visual dulu (gate review owner) sebelum diterapkan ke semua halaman |
| Pergeseran paginasi memecah baris total dari tabelnya | Sedang | `KeepTogether` untuk blok total+pengesahan (pola sudah ada); uji dokumen terpanjang di data uji |
| Kontrak 2dp (R-15) tersentuh tak sengaja | Rendah | `materialize_display_rows` tidak diubah; hanya presentasi (align/font), bukan nilai |

---

### Fase 3 — Word jalur data (paritas dengan PDF)

| # | Perubahan | Kondisi saat ini | Menjadi | Alasan |
|---|---|---|---|---|
| 3.1 | **Font default dokumen** | Body Calibri 11 default (T-3) | `styles['Normal']` = Arial + ukuran skala §2.2, di-set sekali per dokumen (pola yang sudah dipakai jalur daily: `word_exporter.py:1428-1434`) | Satu keluarga font; paritas dengan Helvetica di PDF |
| 3.2 | **Named styles** | Loop per-run manual (T-8) | Style bernama: `DocTitle`, `SectionHeading`, `TableHeader`, `TotalRow` — paragraf memakai style, bukan formatting run | Dokumen "native Word": Navigation Pane hidup, edit user tidak merusak format, XML lebih kecil (T-13 ikut turun) |
| 3.3 | **Spasi via style** | Paragraf kosong (T-7) | `space_before`/`space_after` pada style, skala sama dengan §2.6 | Native + tahan edit |
| 3.4 | **Identitas = tabel** | Paragraf "Label: value" (T-6) | Tabel 3 kolom identik strukturnya dengan PDF | Paritas |
| 3.5 | **Perataan & warna** | Per-sel manual | Aturan §2.3 + warna §2.1 diterapkan via helper terpusat | Paritas |

**Positif:** Word berubah dari "hasil generator" menjadi dokumen yang bisa diedit
instansi/konsultan tanpa berantakan; file .docx lebih kecil; build lebih cepat.
**Negatif:** sama seperti Fase 2 — tampilan bergeser satu kali; test Word perlu update.
**Risiko & mitigasi:**

| Risiko | Level | Mitigasi |
|---|---|---|
| Grid Word Jadwal ikut tersentuh (R-3: Arial 7pt per user request) | — | Grid Jadwal dikecualikan eksplisit dari 3.1-3.5; hanya jalur data |
| Named style bentrok dengan template daily DOCX (`laporan_harian_template.docx`) | Rendah | Jalur daily tidak diubah sama sekali di fase ini |
| LibreOffice/Word versi lama merender named style berbeda | Rendah | Uji buka di Word + LibreOffice sebagai bagian gate |

---

## 6. Dampak Beban Server (ringkasan)

| Perubahan | Dampak beban |
|---|---|
| Hoist stylesheet (1.2) | ⬇️ Turun signifikan (ribuan alokasi → puluhan) |
| String polos utk sel angka (2.5) | ⬇️ Turun (flowable Paragraph = objek terberat ReportLab) |
| Blank filler `''` (1.3) | ⬇️ Turun kecil; fitur tetap |
| Named styles Word (3.2) | ⬇️ Turun (XML lebih kecil, loop per-run hilang) |
| Warna/align/spasi terstandar | ➖ Nol (nilai konstan) |
| Format & kebijakan `-` | ➖ Nol (string formatting) |
| **Yang sengaja TIDAK dilakukan demi server:** naikkan DPI screenshot (jalur C); embed font custom | — |

**Ekspektasi jujur:** total waktu build export **lebih cepat** dari kondisi sekarang
meski ada dokumen yang bertambah halaman. Diverifikasi dengan angka baseline Fase 0 —
bila ternyata lebih lambat, itu temuan yang akan dilaporkan apa adanya.

---

## 7. Item OPEN — menunggu keputusan owner (TIDAK dieksekusi di Fase 1-3)

| ID | Pertanyaan | Konteks | Rekomendasi saya | Keputusan owner |
|---|---|---|---|---|
| O-1 | Naikkan font grid Jadwal 6→7pt dengan konsekuensi kapasitas minggu/halaman turun (≈18→15)? | 7pt Arial data rows adalah permintaan Anda sendiri (R-3); 6pt PDF grid & 4-5pt header minggu di bawah ambang nyaman cetak | Naikkan minimum ke 6.5-7pt, header minggu 5pt tetap; terima pengurangan kapasitas | ☐ |
| O-2 | **Investigasi fitur page-numbering menyeluruh**, lalu (bila layak) aktifkan nomor halaman + kop berjalan di 5 halaman data? | Dinonaktifkan dengan alasan "ReportLab compatibility" (`pdf_exporter.py:945`); `save()` menjanjikan "second pass" total halaman (1/X) yang tak pernah diimplementasikan (T-14); preseden page indicator dihapus di segmen Kurva S (R-5) | Perlakukan sebagai **investigasi fitur** (bukan sekadar enable/hapus method): riset bug kompatibilitas lama + putuskan format `Halaman X` (single-pass) vs `X/Y` (butuh two-pass) → aktifkan hanya di jalur data; biaya server praktis nol | ☐ |
| O-3 | Halaman "DAFTAR ISI" pada laporan profesional: pertahankan, perbaiki (tambah nomor halaman), atau hapus? | Saat ini daftar teks manual tanpa nomor halaman (`pdf_exporter.py:3905`) | Sederhanakan/hapus (nilai informasi rendah untuk 1 halaman) | ☐ |
| O-4 | Hapus ±800 baris jalur Word professional yang terblokir permanen? | `export_rekap/monthly/weekly` + helper hanya tercapai via jalur yang selalu raise error (`export_manager.py:1076-1077`); berisi placeholder "will be added here"; grep: tak ada pemanggil lain | Hapus (git menyimpan sejarah; bila Word Jadwal dihidupkan lagi, tulis ulang dengan sistem style baru) | ☐ |
| O-5 | Perkaya blok pengesahan (kota+tanggal, jabatan, garis rapi) di dokumen yang MEMANG bertanda tangan? | Sekarang hanya `(_______)` statis; laporan bulanan tetap TANPA ttd sesuai R-4 | Ya, di dokumen perencanaan (Rekap RAB dkk.) | ☐ |
| O-6 | Jalur screenshot (C): rapikan framing/orientasi/kop TANPA menaikkan DPI? | PNG base64 = beban memori terbesar jalur itu | Ya, kosmetik saja; DPI tetap | ☐ |
| O-7 | Samakan `_format_rupiah` (pembulatan integer, jalur B professional) dengan kontrak 2dp (R-15)? | Satu dokumen bisa menampilkan `Rp 1.234.567` dan `1.234.567,89` bersamaan | Samakan ke 2dp id-ID, konsisten doc 30 | ☐ |
| O-8 | Registri §3 dipindah/disalin ke doc permanen (mis. `docs/DESIGN_REGISTRY_EXPORT.md`) agar keputusan desain tidak hanya hidup di komentar kode? | Pelajaran audit ini: usulan hampir menabrak fitur yang disengaja | **Ya — direkomendasikan diputuskan PERTAMA, sebelum fase mana pun** (juga rekomendasi #1 reviewer Codex) | ✅ 2026-07-08 — `docs/DESIGN_REGISTRY_EXPORT.md` dibuat (R-1..R-17 + A-1..A-3) |

---

## 8. Strategi Verifikasi & Gate per Fase

1. **Test suite**: seluruh `tests_export_*`, `tests_wp_export_parity.py`, `tests_harga_items_export.py`, dll. hijau sebelum & sesudah tiap fase.
2. **Review visual owner**: file contoh "SEBELUM vs SESUDAH" (PDF + DOCX per halaman) diserahkan tiap akhir fase; fase berikutnya tidak mulai sebelum Anda approve.
3. **Visual-diff otomatis (v1.1)**: PDF dirender ke PNG (pymupdf/poppler — dependensi dev-only) lalu di-diff terhadap baseline Fase 0; DOCX dikonversi ke PDF via LibreOffice bila tersedia (opsional). Gate Fase 1 = **diff nol**; gate Fase 2/3 = diff hanya pada elemen yang memang diubah.
4. **Gate khusus Fase 1**: tampilan harus identik (behavior-preserving) — bila image-diff menunjukkan perbedaan sekecil apa pun, itu bug Fase 1.
5. **Timing & ukuran file**: dibandingkan dengan baseline Fase 0 (script 0.3), dilaporkan apa adanya.
6. **Kompatibilitas Word**: file .docx diuji buka di MS Word + LibreOffice.
7. **Commit hygiene**: satu commit per item bernomor (mis. `1.2`, `2.3`) agar `git revert` bedah-presisi; tidak dicampur dengan pekerjaan lain.

---

## 9. Risiko Keseluruhan & Rencana Rollback

| Risiko global | Penilaian | Mitigasi |
|---|---|---|
| Perubahan menyentuh keputusan disengaja yang belum terdokumentasi (di luar §3) | Sedang — komentar kode terbukti tidak lengkap | Sebelum mengubah elemen visual apa pun: cek marker intent + `git log`/blame baris terkait; bila ragu → masuk §7 sebagai pertanyaan, bukan dieksekusi |
| Kegagalan test massal karena assert struktur sel | Sedang | Fase 2-3 memperbarui test seiring perubahan; parity test nilai (angka) TIDAK boleh berubah — hanya presentasi |
| Regresi paginasi dokumen panjang | Sedang | Uji dengan proyek data terbesar; `KeepTogether` di blok kritis |
| Rollback | — | Semua fase = commit terpisah di branch fitur; revert per item; tidak ada migrasi DB/state — murni kode render |

**Yang secara eksplisit TIDAK dilakukan dalam rencana ini:**
- Tidak mengubah nilai/angka apa pun (kontrak R-15 utuh).
- Tidak menyentuh Excel exporter (di luar scope).
- Tidak menyentuh grid Jadwal, laporan bulanan/mingguan professional, jalur daily DOCX, jalur screenshot — kecuali item O yang Anda setujui.
- Tidak menambah dependensi baru, font embed, atau proses background baru.

---

## 10. Definisi Selesai

- [x] Fase 0 (✅ 2026-07-08): baseline test/timing/ukuran file/render PNG tersimpan; matriks Lampiran A terkonfirmasi penuh via trace; tooling visual-diff siap & tervalidasi (lihat §12)
- [x] Fase 1 (✅ 2026-07-08): style registry + hoist + helper alignment; **image-diff = nol (24/24)**; 118 test PASS; timing ≤ baseline (lihat §12)
- [ ] Fase 2: 5 halaman PDF memakai skala tipografi, perataan, warna, spasi terstandar (pilot Harga Items dulu); approved owner per-report
- [ ] Fase 3: Word paritas dengan PDF; approved owner; teruji Word+LibreOffice
- [ ] Item O-1..O-8: masing-masing berstatus diputuskan (ya/tidak/ditunda)
- [ ] Registri keputusan desain terdokumentasi permanen (bila O-8 disetujui)

---

## Lampiran A — Matriks Report → Builder → Sumber Style (v1.1)

Granularitas yang diminta review Codex: setiap report jalur A dipetakan ke builder yang
benar-benar dilewatinya. Status ✅ = terverifikasi dari pembacaan kode; **TBD =
dikonfirmasi empiris di Fase 0.4** sebelum builder tersebut disentuh.

| Report | PDF builder | Word builder | Sumber style saat ini | Status |
|---|---|---|---|---|
| Rekap RAB — hal. 1 (RAB detail) | `export()` → `build_page` → `_build_simple_table` (branch `row_types`) | `export()` generic table loop | `_get_base_table_style` + hardcode lokal | ✅ |
| Rekap RAB — hal. 2 (pengesahan) | `_build_pengesahan_table` | `_build_pengesahan_word_table` | Hardcode lokal (`#1976D2`) | ✅ |
| Rekap Kebutuhan — per-periode (time range) | `_build_simple_table` (branch `col_widths`) | `export()` generic | `_get_base_table_style` | ✅ |
| Rekap Kebutuhan — full | `_build_simple_table` ×1 + `_build_footer_table` ×2 + `_build_signatures` ×1 | `export()` generic | `_get_base_table_style` | ✅ **trace 0.4** |
| Volume Pekerjaan (2 halaman: Parameter + Volume&Formula) | **`_build_simple_table` ×2** + `_build_footer_table` ×1 — dugaan v1.1 (`_build_table`) TERBANTAH oleh trace | `export()` generic | `_get_base_table_style` | ✅ **trace 0.4 (koreksi)** |
| Harga Items | `_build_simple_table` ×1 + `_build_footer_table` ×1 | `export()` generic (single `table_data`) | `_get_base_table_style` | ✅ **trace 0.4** |
| Rincian AHSP | Branch root `sections`+`pekerjaan` di `export()` (builder inline `pdf_exporter.py:677-887`) — trace 0.4: **tidak ada builder method terpanggil** → jalur inline terkonfirmasi; `_build_pekerjaan_section` (jalur duplikat via `build_page`) TIDAK terpakai untuk flow ini — konsolidasi dievaluasi saat pilot Fase 2 | `_export_rincian_ahsp` | Hardcode lokal (hijau total E/F/G, wrap style lokal) | ✅ **trace 0.4** |
| Footer totals (lintas report) | `_build_footer_table` | Paragraf manual | Hardcode lokal | ✅ |

**Temuan penting trace 0.4:** `_build_table` — builder terboros (T-10/T-11, Paragraph
per sel + stylesheet per sel) — **TIDAK dipakai oleh satu pun report jalur A** pada
fixture baseline. Hot path-nya = jalur B (Jadwal professional/timeline). Implikasi:
(a) perbaikan visual jalur A berfokus ke `_build_simple_table`, `_build_pengesahan_table`,
`_build_footer_table`, `_build_signatures`, dan builder inline Rincian AHSP;
(b) optimisasi T-10/T-11 tetap dikerjakan di Fase 1 tapi manfaat runtime-nya baru
terasa di export Jadwal (jalur B); (c) `_build_simple_table` membuat wrap-style
per-panggilan (bukan per-sel) — jauh lebih ringan dari dugaan awal.

---

## 11. Riwayat Revisi

| Versi | Tanggal | Perubahan |
|---|---|---|
| v1.0 | 2026-07-08 | Draft awal (audit Claude) |
| v1.2 | 2026-07-08 | Eksekusi O-8 + Fase 0 selesai (log di §12); Lampiran A terkonfirmasi penuh via trace empiris — koreksi: Volume Pekerjaan lewat `_build_simple_table` ×2 (bukan `_build_table`); `_build_table` tidak dipakai jalur A sama sekali |
| v1.1 | 2026-07-08 | Revisi pasca-review independen Codex: (1) **Fase 1 tidak mengubah nilai visual apa pun** — style registry semantik + adapter per format; legacy constants `ExportColors`/`ExportFonts` TIDAK dialias ke nilai UTS/ED (mencegah perubahan diam-diam pada konsumen legacy spt. Excel); (2) T-11 di-scope ke `_build_table` + builder professional — `_build_simple_table` sudah selektif; (3) T-14 direframe: `save()` = penanda fitur two-pass belum selesai → digabung ke O-2; (4) kebijakan nol dipertajam 3 kelas: `None`→`-`, 0% grid suppressed (R-10), nol finansial tetap `0,00` — ditambah R-16 (NULL≠0.00, commit `4ce0870f`); (5) Fase 0 diperkaya: script baseline CSV, render PNG, tooling visual-diff otomatis, matriks builder (Lampiran A); (6) Fase 2 pola pilot mulai Harga Items, aktivasi registry per-report; (7) helper alignment jadi item eksplisit 1.4 (dibangun Fase 1, diaktifkan Fase 2); (8) O-8 direkomendasikan diputuskan pertama |

---

## 12. Log Eksekusi (2026-07-08)

### O-8 — SELESAI
`docs/DESIGN_REGISTRY_EXPORT.md` dibuat: R-1..R-17 + keputusan arsitektur A-1..A-3
+ aturan pemakaian (cek intent → klasifikasi BP/BC → catat keputusan baru).

### Fase 0 — SELESAI

**0.1 Test suite:** 92 test export PASS (101,6 dtk) — 12 modul `tests_export_*`/
`tests_wp_export_parity`/`tests_harga_items_export`/`tests_volume_export_adapter`/
`tests_list_pekerjaan_export`, settings `config.settings.test` (SQLite; PG15 Docker
tidak menyala saat run — konsisten dengan pola run "SQLite 90" sebelumnya).
Catatan: working tree memuat 2 modifikasi uncommitted dari pekerjaan lain
(`_export_menu_item.html`, `tests_export_button_visibility.py`) — baseline
mencakup keduanya.

**0.2 + 0.3 Artefak & metrik SEBELUM:** `export_baseline/SEBELUM_20260708/`
(gitignored) — 5 report × 4 format + 10 PNG (150 dpi) + `baseline_metrics.csv`.
Script: `scripts/export_baseline.py` (fixture: 2 klasifikasi, 3 sub, 4 pekerjaan,
4 item TK/BHN/ALT, uraian panjang utk uji wrap, volume desimal).

| Report | PDF | Word | Hal. PDF |
|---|---|---|---|
| Rekap RAB | 0,029s / 5,2 KB | 0,151s / 37,9 KB | 2 |
| Rekap Kebutuhan | 0,018s / 4,3 KB | 0,050s / 37,6 KB | 2 |
| Volume Pekerjaan | 0,017s / 4,4 KB | 0,121s / 37,5 KB | 2 |
| Harga Items | 0,009s / 3,1 KB | 0,076s / 37,4 KB | 1 |
| Rincian AHSP | 0,035s / 7,9 KB | 0,290s / 38,7 KB | 3 |

(xlsx & csv ikut terekam di CSV — di luar scope visual. Durasi = fixture kecil;
angka relatif antar-fase yang bermakna, bukan absolutnya.)

**0.4 Trace builder:** `scripts/export_baseline.py --trace` → Lampiran A
terkonfirmasi penuh; koreksi terhadap dugaan v1.1 dicatat di Lampiran A
(Volume → `_build_simple_table`; `_build_table` tak dipakai jalur A).

**0.5 Tooling visual-diff:** `scripts/export_visual_diff.py` (Pillow ImageChops;
PNG via pymupdf 1.28.0 — dipasang dev-only ke venv). **Validasi determinisme:**
baseline dijalankan 2× (tag SEBELUM vs VALIDASI) → **10/10 halaman IDENTIK** —
gate image-diff Fase 1 terbukti feasible. LibreOffice tidak terpasang → DOCX
tidak di-diff visual (fallback: review manual + test suite, sesuai rencana).
`.gitignore` ditambah `export_baseline/`.

### Fase 1 — SELESAI (2026-07-08, branch `feat/export-visual-refinement`)

Baseline diperluas dulu ke jalur B (`00949d93`): temuan trace — hot path 1.2/1.3
(`_build_table`) hanya dipanggil `jadwal_prof_rekap`; tanpa perluasan ini gate
image-diff tidak meng-cover perubahan. Gate final = 24 halaman PNG (jalur A+B).

| Item | Commit | Isi | Gate |
|---|---|---|---|
| 1.1+1.4 | `65099344` | `exports/styles/tokens.py` (registry semantik + adapter PDF cached + Word named-styles, PASIF) + `exports/styles/alignment.py` (helper perataan dari `column_formats`, PASIF) + 16 unit test termasuk guard nilai legacy | 16 test PASS |
| 1.2 | `cb7eee40` | 9 situs `getSampleStyleSheet()+ParagraphStyle` per SEL → cache modul `_CELL_STYLE_CACHE` (2 keluarga: parent-Normal leading 12; plain leading=size+2; + varian Gantt/PHeader) | **24/24 halaman IDENTIK**; 60 test PASS |
| 1.3 | `5189deef` | Blank filler `Paragraph('')` → `''` — fitur lebar-tetap R-1 utuh | **24/24 halaman IDENTIK** |
| 1.5 | — | `NumberedCanvas.save()` TIDAK dihapus (menunggu O-2), sesuai rencana | — |

**Gate akhir:** 118 test PASS (92 export + 16 tokens + 10 jadwal WP-P7); image-diff
nol; timing sama-atau-lebih-cepat (fixture kecil — perbaikan nyata terlihat di
`jadwal_prof_rekap`: 0,109s → 0,066s; tidak ada yang melambat).

### Berikutnya
**Fase 2 (behavior-changing, butuh persetujuan owner per-report):** pilot **Harga
Items** — aktifkan registry (warna header tunggal, skala tipografi, helper
alignment, kebijakan nilai kosong 3 kelas) lalu serahkan PDF SEBELUM vs SESUDAH
untuk review owner sebelum replikasi ke report lain. Keputusan O-1..O-7 masih
terbuka (§7).
