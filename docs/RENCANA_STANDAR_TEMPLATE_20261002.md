# Rencana Penerapan Standar Template Dokumen Export

| | |
|---|---|
| Tanggal | 2026-10-02 |
| Pembaca | Owner, Codex, Claude |
| Dasar | `D:\PORTOFOLIO ADIT\usulan_standar_template\Usulan_Standar_Template_Dokumen_Export_v4.pdf` (disetujui owner 2026-10-02, termasuk Rincian 0,4 cm, palet, dan krem/tint minimal) |
| Branch | `feat/standar-template` dari `main` `091f9c73`, di worktree `../ahsp-standar-template` (folder utama dipakai Codex untuk `chore/satukan-toast`) |
| Status | **WIP** — T1–T3 selesai (menunggu cek visual owner); T4–T5 berikutnya |

## 1. Keputusan

| # | Keputusan | Status |
|---|---|---|
| S-1 | Cover hanya untuk Paket Perencanaan dan laporan berperiode; dokumen tunggal tanpa cover | Rekomendasi dipakai (owner: "terapkan") |
| S-2 | Huruf PDF DejaVu Sans (glyph lengkap, berkas font disertakan di repo); Word Arial | Rekomendasi dipakai |
| S-3 | Rekap Kebutuhan dikelompokkan Tenaga Kerja / Bahan / Alat + subtotal | Rekomendasi dipakai |
| S-4 | Kolom yang seluruhnya "-" disembunyikan otomatis | Rekomendasi dipakai |
| S-5 | Paket Perencanaan memuat Rekap Kebutuhan (5 dokumen) | Rekomendasi dipakai |
| S-6 | Palet #213448 / #547792 / #94B4C1 / #EAE0CF; krem & tint minimal | **Disetujui owner** |
| S-7 | Laporan Jadwal ikut "Halaman x dari y" + nama dokumen di header kanan | Rekomendasi dipakai (tahap T4) |
| S-8 | Word mengikuti spesifikasi PDF (uraian tetap utuh) | Rekomendasi dipakai |
| S-9 | Rincian AHSP: tinggi baris 0,4 cm, huruf 6,5 pt | **Disetujui owner** |

Owner dapat mengoreksi S-1..S-5, S-7, S-8 kapan saja; tahap yang terdampak diulang.

## 2. Arsitektur

- Modul baru `detail_project/exports/standard/`:
  - `tokens.py`: palet, ukuran huruf, spasi, margin (satu sumber untuk PDF & Word).
  - `fonts.py`: registrasi DejaVu Sans dari `exports/fonts/` (berkas + lisensi disertakan).
  - `pdf.py`: kanvas header/footer bernomor, kepala dokumen, tabel standar, blok total, pengesahan menempel, cover + daftar isi; satu fungsi render per dokumen dari payload adapter yang SAMA dengan export sekarang.
  - `word.py`: padanan Word dari spesifikasi yang sama.
- `export_manager` memilih renderer standar untuk dokumen perencanaan (PDF & Word). Excel/CSV dan laporan Jadwal tidak berubah sampai T4.
- Jalur lama tetap ada sampai semua dokumen pindah, lalu dibersihkan (T5).

## 3. Tahapan & tracker

Status: `TODO` / `WIP` / `REVIEW` / `DONE`.

| ID | Tugas | Status | Commit / bukti |
|---|---|---|---|
| T1 | Fondasi `exports/standard/` (token, font, kanvas, komponen) + tes komponen | DONE | `0a3105b7`; tes `tests_standard_template` |
| T2.1 | Rencana Anggaran Biaya + Rekapitulasi (PDF & Word) | REVIEW | PDF `0a3105b7`, Word (commit tahap Word) |
| T2.2 | Rekap & Rincian Analisa Harga Satuan (PDF & Word; baris 0,4 cm) | REVIEW | Baris terukur: PDF 4,01 mm, Word 4,17 mm (0,4 cm + garis) |
| T2.3 | Volume Pekerjaan + Daftar Parameter (PDF & Word) | REVIEW | |
| T2.4 | Harga Satuan Dasar + Satuan Konversi (PDF & Word) | REVIEW | |
| T2.5 | Rekap Kebutuhan Material, berkelompok (PDF & Word; semua mode filter/periode) | REVIEW | mode per periode: satu tabel per periode |
| T3 | Paket Perencanaan utuh: cover + daftar isi + nomor halaman, 5 dokumen | REVIEW | PDF & Word 217: 20 halaman (sama) |
| T4 | Laporan Jadwal: palet + "Halaman x dari y" + header kanan | TODO | |
| T5 | Registri desain (R-51 dst.), tes penjaga, hapus jalur lama yang tidak terpakai | WIP | R-51–R-55 dicatat di `docs/DESIGN_REGISTRY_EXPORT.md`; tes penjaga dan pembersihan jalur lama belum dilakukan. |
| V | Cek visual owner per tahap (sampel proyek 217) | TODO | |

## 4. Aturan kerja

- Satu tahap = satu commit (atau lebih kecil), pesan bahasa Indonesia.
- Tes di container sementara yang me-mount worktree (bukan `ahsp_web`); DB tes unik per run.
- Gerbang tiap tahap: tes export terkait + suite 5 app sebelum merge; sampel PDF & Word proyek 217 untuk owner.
- **Tanpa push.** Owner mengizinkan penggabungan lokal pada 2026-10-02.

## 5. Catatan teknis

- Isi dokumen = blok netral (`standard/documents.py`) yang diterjemahkan oleh `pdf.flowables` dan `word.WordBuilder.blocks`; PDF & Word tidak bisa berbeda isi.
- Tinggi baris minimum: PDF memakai mekanisme `pdf_exporter.Table._calc` (ambang per tabel); Word memakai `trHeight atLeast` dengan margin atas/bawah sel 0 karena di Word tinggi minimum TIDAK mencakup margin sel (eksperimen 2026-10-02: 0,4 cm + 2×0,63 mm = 5,3 mm).
- Template bawaan python-docx: urutan anak `tblPr` harus sesuai skema OOXML (`_tblpr_insert`), tanda paragraf sel ikut ukuran teks.
- Huruf PDF DejaVu Sans dari `exports/fonts` (fallback Helvetica bila berkas hilang); Word Arial (∅ dirender Word dengan font pengganti).
- Tes container worktree: entrypoint image dilewati (ia menjalankan migrate + collectstatic ke DB bersama).
