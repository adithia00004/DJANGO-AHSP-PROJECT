# Design Registry — Export PDF/Word/Excel

**Status:** LIVING DOCUMENT — wajib dicek sebelum mengubah elemen visual/perilaku export
**Dibuat:** 2026-07-08 (keputusan O-8, Review/R5_Detail_Project/32 §7)
**Sumber:** audit sesi 2026-07-08 (doc 32 §3) + komentar intent di kode + sejarah commit

---

## Tujuan

Keputusan desain export selama ini hanya hidup di komentar kode yang tersebar
(mis. `"per user request"`) — audit 2026-07-08 hampir menghapus fitur yang disengaja
(kolom pengisi kosong) karena dikira pemborosan. Dokumen ini menjadi tempat resmi
mencatat keputusan tersebut agar tidak menabraknya lagi.

## Aturan pemakaian

1. **Sebelum mengubah elemen visual/perilaku export apa pun:** cek tabel di bawah,
   cek marker intent di komentar kode (`per user request`, `NOTE:`, `FIXED:`,
   `intentionally`, `by design`), dan `git log`/blame baris terkait.
2. **Klasifikasikan setiap perubahan:** *behavior-preserving* (implementasi saja,
   output identik) vs *behavior-changing* (butuh persetujuan owner eksplisit).
3. **Keputusan baru dicatat di sini** dengan ID baru (R-N), bukti (file:baris /
   commit / doc), dan tanggal. Keputusan yang dicabut TIDAK dihapus — beri strikethrough
   + catatan tanggal & alasan pencabutan.

---

## Registri Keputusan

| # | Keputusan | Bukti | Dicatat |
|---|---|---|---|
| R-1 | **Lebar tabel FIXED 100% + kolom pengisi kosong (blank filler)** — lebar kolom minggu identik di semua halaman grid; halaman terakhir dengan sedikit minggu tetap tampil seragam | `detail_project/exports/table_styles.py:349`, `pdf_exporter.py:2145-2185` | 2026-07-08 |
| R-2 | **Maks 18 minggu per halaman** grid Jadwal | `table_styles.py:216`, `export_config.py:193` | 2026-07-08 |
| R-3 | **Arial 7pt untuk baris data grid Word** | `word_exporter.py:1138` — "per user request" | 2026-07-08 |
| R-4 | **Tanda tangan DIHAPUS dari laporan bulanan PDF** | `pdf_exporter.py:1826, 5210, 5671` — "per user request" | 2026-07-08 |
| R-5 | **Page indicator DIHAPUS di segmen Kurva S portrait** | `pdf_exporter.py:5202` — "per user request" | 2026-07-08 |
| R-6 | **Rekap Kebutuhan orientasi portrait** | `export_manager.py:241-244` — "User specified" | 2026-07-08 |
| R-7 | **Label seksi tertentu** ("Input Progress Planned", "Input Progress Actual", dst.) | `table_styles.py:723` — "as requested by user" | 2026-07-08 |
| R-8 | **Header Excel tertentu** | `excel_exporter.py:2496` — "per user request" | 2026-07-08 |
| R-9 | **Gantt/Kurva S tidak dirender di Word** (bukan format native Word; user download image terpisah dari UI) | `word_exporter.py:650-652` | 2026-07-08 |
| R-10 | **Suppress nilai 0% di grid progress** (kurangi clutter & ukuran file; berlaku format titik & koma) | `word_exporter.py:1089-1101`, `pdf_exporter.py:2080-2083` | 2026-07-08 |
| R-11 | **Rincian AHSP tanpa page break antar pekerjaan** (compact) | `pdf_exporter.py:886`, `word_exporter.py:532` | 2026-07-08 |
| R-12 | **Laporan harian sengaja ringkas** (tanpa volume/bobot/progress display; total_harga hanya untuk bobot internal) | `export_manager.py:1110` | 2026-07-08 |
| R-13 | **Aturan anti-orphan tanda tangan** (min 3 baris konten sehalaman dengan ttd; ruang min 50mm) | `signature_config.py:160-263` | 2026-07-08 |
| R-14 | **Laporan mingguan tanpa sheet Kurva S** | `excel_exporter.py:3964` | 2026-07-08 |
| R-15 | **Kontrak presisi WP Export**: nilai kanonik Decimal dari backend; 2dp id-ID diformat di boundary exporter via `materialize_display_rows`; hanya tabel ber-`column_formats` | Doc 30; `exports/cell_format.py` | 2026-07-08 |
| R-16 | **NULL/kosong ≠ 0,00 pada Harga Items export** — harga belum diisi tampil kosong/`-`, BUKAN `0,00`; nol finansial sungguhan tetap `0,00` | Commit `4ce0870f` (WP Export slice Harga Items) | 2026-07-08 |
| R-17 | **Kebijakan nilai kosong 3 kelas** (doc 32 item 2.4): (a) `None`/tidak diisi → `-`; (b) 0% grid progress → suppressed (R-10); (c) nol finansial → tampil `0,00` (R-16) | Doc 32 v1.1 §5 Fase 2 | 2026-07-08 |

## Keputusan arsitektur terkait (bukan visual, jangan dilanggar)

| # | Keputusan | Bukti |
|---|---|---|
| A-1 | Nilai resmi sheet Excel = nilai backend (bukan formula recompute); formula recompute → sheet "Kontrol Kalkulasi"; mirror 1:1 `='Data Master'!cell` diperbolehkan | Doc 30 §7-8 |
| A-2 | Error export tidak pernah membocorkan `str(e)` ke user — pakai correlation ID (`export_error_response`, `log_export_error`) | WP-B5; `exports/errors.py` |
| A-3 | Penamaan file export via `build_export_filename` (naming.py); identitas proyek via `get_project_identity` (identity.py) | `exports/naming.py:24`, `exports/identity.py` |

---

## Referensi silang

- `Review/R5_Detail_Project/32_Export_PDF_Word_Visual_Refinement_Plan_20260708.md` — rencana perbaikan visual (asal dokumen ini)
- `Review/R5_Detail_Project/30_WP_Export_K2_K3_Decision_20260620.md` — keputusan presisi & formula
- `Review/R5_Detail_Project/12_Export_System.md` — review sistem export
