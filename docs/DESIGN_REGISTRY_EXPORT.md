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
| R-12 | **Laporan harian sengaja ringkas** (tanpa volume/bobot ~~/progress display~~; ~~total_harga hanya untuk bobot internal~~). *Direvisi 2026-09-27 (owner): progress kumulatif DITAMPILKAN — lihat R-31; bobot kini dari `adapter._get_bobot_maps`* | `export_manager.py:1110` | 2026-07-08 |
| R-13 | **Aturan anti-orphan tanda tangan** (min 3 baris konten sehalaman dengan ttd; ruang min 50mm) | `signature_config.py:160-263` | 2026-07-08 |
| R-14 | **Laporan mingguan tanpa sheet Kurva S** | `excel_exporter.py:3964` | 2026-07-08 |
| R-15 | **Kontrak presisi WP Export**: nilai kanonik Decimal dari backend; 2dp id-ID diformat di boundary exporter via `materialize_display_rows`; hanya tabel ber-`column_formats` | Doc 30; `exports/cell_format.py` | 2026-07-08 |
| R-16 | **NULL/kosong ≠ 0,00 pada Harga Items export** — harga belum diisi tampil kosong/`-`, BUKAN `0,00`; nol finansial sungguhan tetap `0,00` | Commit `4ce0870f` (WP Export slice Harga Items) | 2026-07-08 |
| R-17 | **Kebijakan nilai kosong 3 kelas** (doc 32 item 2.4): (a) `None`/tidak diisi → `-`; (b) 0% grid progress → suppressed (R-10); (c) nol finansial → tampil `0,00` (R-16) | Doc 32 v1.1 §5 Fase 2 | 2026-07-08 |
| R-18 | **Footer Rekap Kebutuhan: TANPA baris "Total Quantity" per kategori** (agregat kuantitas lintas satuan tidak relevan), dan **blok ringkasan footer hanya tampil SEKALI di lembar terakhir** (bersama tanda tangan), tidak diulang per lembar | Keputusan owner 2026-07-13 (temuan manual 1.1 & 1.2); `rekap_kebutuhan_adapter.py`, `pdf_exporter.py` build_page `skip_footer` | 2026-07-13 |
| R-19 | **Pembulatan grand total RAB SELALU ke bawah** (floor), bukan ke terdekat — nilai yang ditagihkan tidak boleh melebihi hasil hitungan. Berlaku di **6 lokasi** yang harus diubah bersama: footer `rekap_rab.js`, pembuat export teks di file sama, `ExcelExporter.js`, `RekapRABPrint.js`, `services.compute_rab_grand_total`, `exports/rekap_rab_adapter.py` | Keputusan owner 2026-08-18; commit `a5f3e5f5`, `1b92ba34` | 2026-08-18 |
| R-20 | **Lembar pengesahan: susunan baku** — kata penghubung (Mengetahui/Dibuat oleh/Diperiksa oleh), sebutan peran, ruang tanda tangan basah, NAMA (digarisbawahi), lalu baris keterangan tanpa slot kosong. Jumlah baris keterangan berbeda antar peran; tabel dipadatkan ke jumlah terbanyak agar kolom sejajar | Keputusan owner 2026-08-18; `pdf_exporter._build_signatures`, `word_exporter._build_signature_section`; commit `d2570b08` | 2026-08-18 |
| R-21 | **Nama penanda tangan digarisbawahi; TIDAK ada baris garis terpisah di atasnya.** PDF memakai `Paragraph` markup `<u>` (bukan `LINEBELOW`) supaya garis selebar teks, bukan selebar kolom | Keputusan owner 2026-08-18; commit `2126bd62` | 2026-08-18 |
| R-22 | **Tempat & tanggal DIHAPUS dari lembar pengesahan** — sempat ditambahkan pagi 2026-08-18 lalu dicabut owner sore harinya. Helper `format_place_and_date` beserta tabel nama bulan dihapus sampai ke sumbernya | Keputusan owner 2026-08-18; commit `9932d0a4` | 2026-08-18 |
| R-23 | **Spasi lembar pengesahan serapat mungkin** — semua padding sel dinolkan; ruang tanda tangan basah satu baris setinggi `SIGNATURE_SPACE_MM = 15`, konstanta bersama PDF & Word | Keputusan owner 2026-08-18; `signature_config.py`; commit `9932d0a4` | 2026-08-18 |
| R-24 | **Identitas pemilik pada pengesahan dapat disetel per-project**: `sebutan_client` menimpa label "Pemilik Proyek" (mis. "Pejabat Pembuat Komitmen Dinas X"); `jabatan_client` = Keterangan 1; `ket_client2` = Keterangan 2 (NIP/ID). `jabatan_client` DIPAKAI ULANG, bukan diganti field baru — 103 dari 178 project sudah mengisinya | Keputusan owner 2026-08-18; migrasi `dashboard/0016`; commit `d2570b08` | 2026-08-18 |
| R-25 | **Hierarki tabel dibedakan tipografi, bukan hanya warna** (warna sulit dibedakan saat cetak hitam-putih): Klasifikasi `Helvetica-Bold` 9pt, Sub-Klasifikasi `Helvetica-BoldOblique` 8,5pt, Pekerjaan `Helvetica` 7,5pt | Keputusan owner 2026-08-18; konstanta `HIER_FONT_*` di `pdf_exporter.py`; commit `9932d0a4` | 2026-08-18 |
| R-26 | **Indentasi hierarki DIGANTI jarak bawah** (`HIER_SPACE_AFTER_*` 4/3/1pt) — indentasi `LEFTPADDING 12pt` memakan lebar kolom uraian yang sudah sempit. Indentasi berbasis spasi di `_render_uraian_text` TIDAK ikut diubah: itu milik tabel Kurva-S | Keputusan owner 2026-08-18; commit `9932d0a4` | 2026-08-18 |
| R-27 | **Lebar tabel tanda tangan diturunkan dari lebar cetak sebenarnya**, bukan angka mati. Nilai lama 250mm melebihi area cetak A4 portrait 190mm sehingga kolom kanan terpotong. Dikunci tes | Commit `d2570b08`; `tests_export_signature.SignatureSheetRenderTests` | 2026-08-18 |
| R-28 | **Lembar pengesahan wajib di 5 dokumen perencanaan** (Rekap RAB, Rincian AHSP, Volume, Harga Items, Rekap Kebutuhan) memakai SATU blok bersama. Dikunci `SignatureCoverageTests` | Keputusan owner 2026-08-18; commit `982a96b1` | 2026-08-18 |
| R-30 | **Jumlah periode laporan Jadwal = periode NYATA proyek**, tanpa minimum buatan (dulu view memaksa ≥12 minggu/≥3 bulan: proyek 41 hari menawarkan Minggu 1-12/Bulan 1-3). SATU sumber `timeline_utils.project_report_period_counts` (batas minggu kanonik `expected_week_count`, "Bulan" = 4 minggu) dipakai modal export, validasi backend, dan kolom mingguan adapter. Periode di luar masa proyek DITOLAK (`ExportValidationError` → HTTP 400), bukan laporan kosong 0% | Keputusan owner 2026-09-27; `tests_jadwal_monthly_report.ReportPeriod*` | 2026-09-27 |
| R-31 | **Progress kumulatif = W1 s.d. akhir periode sebelumnya** di SEMUA laporan Jadwal (harian: s.d. minggu lalu; bulanan: "Kumulatif Bulan Lalu" = W1..akhir bulan lalu; mingguan: sudah begitu). Nilai TIDAK dibulatkan per baris sebelum dijumlah → TOTAL tabel = Akumulasi di Ringkasan. Laporan harian menambah kolom **s.d. minggu ini berisi target rencana saja** (realisasi/deviasi `-`) | Keputusan owner 2026-09-27; `tests_jadwal_monthly_report.MonthlyCumulativeProgressTests`, `tests_wp_export_parity.JadwalDailyDocxExportTests` | 2026-09-27 |
| R-32 | **Laporan harian: tabel identitas hanya Proyek/Lokasi/Cuaca/Pemilik** (No. Kontrak, Kontraktor, Konsultan, Tgl Laporan dibuang — sudah di subjudul/pengesahan); **pengesahan hanya Kontraktor Pelaksana + Konsultan Pengawas** (tanpa Pemilik), ruang TTD 2,2 cm; 24 baris pekerjaan/halaman | Keputusan owner 2026-09-27; commit `e2183b89` | 2026-09-27 |
| R-33 | **Jabatan penanda tangan TIDAK dikarang.** Pengesahan laporan progress (`_build_progress_signature_section`) dulu mencetak "Direktur" untuk Pelaksana & Pengawas; model tidak punya field jabatan keduanya → tampil `Jabatan: ....` untuk diisi tangan | Keputusan owner 2026-09-27 | 2026-09-27 |
| R-34 | **Label identitas laporan progress PDF sesuai isinya**: Pemilik, Sumber Dana, Lokasi; `Ket. Project 1/2` (field Dashboard `ket_project1/2`) hanya tampil bila diisi — dulu label "Ket. Project" menampilkan Sumber Dana/Pemilik | Keputusan owner 2026-09-27 | 2026-09-27 |
| R-35 | **Angka PDF tidak boleh dipotong karakter** (dulu `Rp6.894.896.91` = Rp 6,8 miliar terbaca juta; volume `3000.`): format id-ID via `format_cell_display`, font diperkecil (`_fit_font_size`) bila tak muat. Rupiah dibulatkan, bukan `int()`. PageBreak beruntun (halaman kosong) dipadatkan `_collapse_redundant_page_breaks` | Keputusan owner 2026-09-27; `tests_jadwal_monthly_report.MonthlyPdfRenderTests` | 2026-09-27 |
| R-29 | **Paket perencanaan = 4 dokumen dalam SATU berkas** (Rekap RAB, Rincian AHSP, Volume, Harga Items), tersedia PDF/Word/Excel, **lembar pengesahan tetap per dokumen** (bukan satu di akhir). Tombol "Unduh Paket" berdiri sendiri; dropdown export dokumen tunggal TETAP ada | Keputusan owner 2026-08-18; commit `354c66e8`; `tests_export_paket.py` | 2026-08-18 |

## Keputusan arsitektur terkait (bukan visual, jangan dilanggar)

| # | Keputusan | Bukti |
|---|---|---|
| A-1 | Nilai resmi sheet Excel = nilai backend (bukan formula recompute); formula recompute → sheet "Kontrol Kalkulasi"; mirror 1:1 `='Data Master'!cell` diperbolehkan | Doc 30 §7-8 |
| A-2 | Error export tidak pernah membocorkan `str(e)` ke user — pakai correlation ID (`export_error_response`, `log_export_error`) | WP-B5; `exports/errors.py` |
| A-3 | Penamaan file export via `build_export_filename` (naming.py); identitas proyek via `get_project_identity` (identity.py) | `exports/naming.py:24`, `exports/identity.py` |
| A-4 | **Lembar pengesahan HANYA lewat `_build_signatures()` (PDF) / `_build_signature_section()` (Word).** Dilarang membuat tabel tanda tangan inline baru | `SignatureCoverageTests`; commit `982a96b1` |
| A-5 | **`include_signatures` ≠ tata letak pengesahan.** `include_signatures` hanya memutuskan ADA/TIDAK blok tanda tangan; penggantian tabel halaman jadi tabel pengesahan 3 kolom dipilih terpisah lewat `pengesahan_layout`. Menggabungkan keduanya pernah menghilangkan kolom Nilai di halaman parameter Volume | Ditangkap `tests_wp_export_parity`; commit `982a96b1` |
| A-7 | **Paket TIDAK boleh punya jalur data sendiri.** Isinya wajib memakai adapter yang sama dengan unduhan tunggal; data Rekap RAB diekstrak ke `_build_rekap_rab_data()` agar perakitan halaman hanya hidup di satu tempat. Dikunci `test_package_reuses_single_download_data` | Commit `354c66e8` |
| A-8 | **Penggabungan dilakukan di tingkat exporter, bukan menggabungkan berkas jadi.** PDF `collect_only=True` → satu `SimpleDocTemplate`; Word `_package_mode`; Excel `_package_wb`. Menggabungkan berkas jadi butuh pustaka merge (tidak terpasang) dan nomor halaman tiap dokumen akan mulai dari 1 lagi | Commit `354c66e8` |
| A-6 | **Identitas pihak-pihak harus diteruskan `ExportManager._get_project_identity()` ke level ATAS `project_info`** (bukan hanya `extra`) — exporter membacanya di sana. Penyempitan dict pernah menjatuhkan seluruh field konsultan | `ExportManagerIdentityPassthroughTests`; commit `877edb55` |

---

## Catatan sejarah — enam implementasi tanda tangan (2026-08-18)

Ditemukan saat menelusuri laporan "lembar pengesahan kosong". Dicatat agar tidak
diulang, dan agar auditor berikutnya tahu ke mana harus melihat.

| # | Mekanisme | Dipakai | Nasib |
|---|---|---|---|
| 1 | `_build_signatures()` + `signature_config` | Rekap RAB, Rekap Kebutuhan | **Dijadikan SSOT** (A-4) |
| 2 | `_build_progress_signature_section()` | Laporan progress/pengawasan | Masih terpisah — format 3 kolom berbeda, belum disatukan |
| 3 | `_build_monthly_signature_page()` | — | **Kode mati**, tanpa pemanggil. Konsisten dengan R-4 (tanda tangan sengaja dihapus dari laporan bulanan). Layak dihapus |
| 4 | dict `signature_data` | Volume, Harga Items | **Hanya dibaca Excel**, nama masih hardcode titik-titik. Belum diperbaiki (cakupan owner: PDF & Word saja) |
| 5 | Tabel inline `pdf_exporter` | Rincian AHSP | **Dihapus**, diganti no. 1 |
| 6 | Tabel inline `word_exporter` | Rincian AHSP | **Dihapus**, diganti no. 1 |

Pelajaran yang berlaku umum: **tes yang hanya memeriksa penyedia data akan lolos
meski perendernya membuang data itu.** `IdentityDelegationGuardTests` memindai teks
sumber dan lolos sepenuhnya; `build_signatures` menghasilkan nama yang benar
sementara PDF mencetak 20 garis bawah. Uji pada lapisan yang benar-benar dirender.

## Referensi silang

- `Review/R5_Detail_Project/32_Export_PDF_Word_Visual_Refinement_Plan_20260708.md` — rencana perbaikan visual (asal dokumen ini)
- `Review/R5_Detail_Project/30_WP_Export_K2_K3_Decision_20260620.md` — keputusan presisi & formula
- `Review/R5_Detail_Project/12_Export_System.md` — review sistem export
