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
| R-1 | **Lebar tabel FIXED 100% + kolom pengisi kosong (blank filler)** — lebar kolom minggu identik di semua halaman grid; halaman terakhir dengan sedikit minggu tetap tampil seragam. *Pengecualian 2026-09-30: Kurva S Rekap yang semua minggunya muat satu halaman melebar mengisi halaman (R-45)* | `detail_project/exports/table_styles.py:349`, `pdf_exporter.py:2145-2185` | 2026-07-08 |
| R-2 | **Maks 18 minggu per halaman** grid Jadwal | `table_styles.py:216`, `export_config.py:193` | 2026-07-08 |
| R-3 | **Arial 7pt untuk baris data grid Word** | `word_exporter.py:1138` — "per user request" | 2026-07-08 |
| R-4 | **Tanda tangan DIHAPUS dari laporan bulanan PDF** | `pdf_exporter.py:1826, 5210, 5671` — "per user request" | 2026-07-08 |
| R-5 | **Page indicator DIHAPUS di segmen Kurva S portrait** | `pdf_exporter.py:5202` — "per user request" | 2026-07-08 |
| R-6 | **Rekap Kebutuhan orientasi portrait** | `export_manager.py:241-244` — "User specified" | 2026-07-08 |
| R-7 | **Label seksi tertentu** (~~"Input Progress Planned", "Input Progress Actual"~~, dst.). *Direvisi 2026-09-30 (owner, doc 42 K-14/L-2): label berbahasa Indonesia — "Input Progres Rencana", "Input Progres Realisasi"; label kolom "Minggu N"/"Bulan N", "Realisasi" menggantikan "Actual". Singkatan kolom rapat "W7" dan nama sheet Excel (mis. "Input Progress-Gantt", dirujuk formula) tetap* | `table_styles.py:732` | 2026-07-08 |
| R-8 | **Header Excel tertentu** | `excel_exporter.py:2496` — "per user request" | 2026-07-08 |
| R-9 | **Gantt/Kurva S tidak dirender di Word** (bukan format native Word; user download image terpisah dari UI). *Tetap berlaku untuk Word bulanan/mingguan yang diaktifkan 2026-09-30 (R-44)* | `word_exporter.py:650-652` | 2026-07-08 |
| R-10 | **Suppress nilai 0% di grid progress** (kurangi clutter & ukuran file; berlaku format titik & koma) | `word_exporter.py:1089-1101`, `pdf_exporter.py:2080-2083` | 2026-07-08 |
| R-11 | **Rincian AHSP tanpa page break antar pekerjaan** (compact) | `pdf_exporter.py:886`, `word_exporter.py:532` | 2026-07-08 |
| R-12 | **Laporan harian sengaja ringkas** (tanpa volume/bobot ~~/progress display~~; ~~total_harga hanya untuk bobot internal~~). *Direvisi 2026-09-27 (owner): progress kumulatif DITAMPILKAN — lihat R-31; bobot kini dari `adapter._get_bobot_maps`* | `export_manager.py:1110` | 2026-07-08 |
| R-13 | **Aturan anti-orphan tanda tangan** (min 3 baris konten sehalaman dengan ttd; ruang min 50mm) | `signature_config.py:160-263` | 2026-07-08 |
| R-14 | **Laporan mingguan tanpa sheet Kurva S.** *Revisi 2026-09-30 (owner, doc 42 K-12): Rincian mingguan Excel menampilkan realisasi berbobot pada blok terpisah untuk **semua proyek** (bukan hanya proyek bertambahan); nilai rencana H-J tetap. Keputusan tanpa sheet Kurva S tetap berlaku.* | `excel_exporter._build_weekly_rincian_sheet`, doc 30 §8.3; `JadwalMonthlyValueOnlyTests`, `ExtensionExcelMarkerTests` | 2026-07-08 |
| R-15 | **Kontrak presisi WP Export**: nilai kanonik Decimal dari backend; 2dp id-ID diformat di boundary exporter via `materialize_display_rows`; hanya tabel ber-`column_formats` | Doc 30; `exports/cell_format.py` | 2026-07-08 |
| R-16 | **NULL/kosong ≠ 0,00 pada Harga Items export** — harga belum diisi tampil kosong/`-`, BUKAN `0,00`; nol finansial sungguhan tetap `0,00` | Commit `4ce0870f` (WP Export slice Harga Items) | 2026-07-08 |
| R-17 | **Kebijakan nilai kosong 3 kelas** (doc 32 item 2.4): (a) `None`/tidak diisi → `-`; (b) 0% grid progress → suppressed (R-10); (c) nol finansial → tampil `0,00` (R-16) | Doc 32 v1.1 §5 Fase 2 | 2026-07-08 |
| R-18 | **Footer Rekap Kebutuhan: TANPA baris "Total Quantity" per kategori** (agregat kuantitas lintas satuan tidak relevan), dan **blok ringkasan footer hanya tampil SEKALI di lembar terakhir** (bersama tanda tangan), tidak diulang per lembar | Keputusan owner 2026-07-13 (temuan manual 1.1 & 1.2); `rekap_kebutuhan_adapter.py`, `pdf_exporter.py` build_page `skip_footer` | 2026-07-13 |
| R-19 | **Pembulatan grand total RAB SELALU ke bawah** (floor), bukan ke terdekat — nilai yang ditagihkan tidak boleh melebihi hasil hitungan. Berlaku di **6 lokasi** yang harus diubah bersama: footer `rekap_rab.js`, pembuat export teks di file sama, `ExcelExporter.js`, `RekapRABPrint.js`, `services.compute_rab_grand_total`, `exports/rekap_rab_adapter.py` | Keputusan owner 2026-08-18; commit `a5f3e5f5`, `1b92ba34` | 2026-08-18 |
| R-20 | **Lembar pengesahan: susunan baku** — ~~kata penghubung (Mengetahui/Dibuat oleh/Diperiksa oleh), sebutan peran,~~ ruang tanda tangan basah, NAMA (digarisbawahi), lalu baris keterangan tanpa slot kosong. *Direvisi 2026-09-27 (owner): susunan diganti R-37 — kata penghubung & sebutan peran dihapus, INSTANSI di baris teratas.* Jumlah baris keterangan berbeda antar peran; tabel dipadatkan ke jumlah terbanyak agar kolom sejajar | Keputusan owner 2026-08-18; `pdf_exporter._build_signatures`, `word_exporter._build_signature_section`; commit `d2570b08` | 2026-08-18 |
| R-21 | **Nama penanda tangan digarisbawahi; TIDAK ada baris garis terpisah di atasnya.** PDF memakai `Paragraph` markup `<u>` (bukan `LINEBELOW`) supaya garis selebar teks, bukan selebar kolom | Keputusan owner 2026-08-18; commit `2126bd62` | 2026-08-18 |
| R-22 | **Tempat & tanggal DIHAPUS dari lembar pengesahan** — sempat ditambahkan pagi 2026-08-18 lalu dicabut owner sore harinya. Helper `format_place_and_date` beserta tabel nama bulan dihapus sampai ke sumbernya | Keputusan owner 2026-08-18; commit `9932d0a4` | 2026-08-18 |
| R-23 | **Spasi lembar pengesahan serapat mungkin** — semua padding sel dinolkan; ruang tanda tangan basah satu baris setinggi ~~`SIGNATURE_SPACE_MM = 15`~~ **20 mm** (direvisi owner 2026-09-30: satu baris lebih tinggi, semua dokumen export; harian Word 2,2 → 2,7 cm), konstanta bersama PDF, Word & Excel | Keputusan owner 2026-08-18; `signature_config.py`; commit `9932d0a4` | 2026-08-18 |
| R-24 | **Identitas pemilik pada pengesahan dapat disetel per-project**: ~~`sebutan_client` menimpa label "Pemilik Proyek" (mis. "Pejabat Pembuat Komitmen Dinas X");~~ `jabatan_client` = Keterangan 1; `ket_client2` = Keterangan 2 (NIP/ID). *Direvisi 2026-09-27 (owner, R-37): sebutan peran tidak dicetak lagi, jadi `sebutan_client` tidak tampil; urutan kini ket_client2 lalu jabatan_client.* `jabatan_client` DIPAKAI ULANG, bukan diganti field baru — 103 dari 178 project sudah mengisinya | Keputusan owner 2026-08-18; migrasi `dashboard/0016`; commit `d2570b08` | 2026-08-18 |
| R-25 | **Hierarki tabel dibedakan tipografi, bukan hanya warna** (warna sulit dibedakan saat cetak hitam-putih): Klasifikasi `Helvetica-Bold` 9pt, Sub-Klasifikasi `Helvetica-BoldOblique` 8,5pt, Pekerjaan `Helvetica` 7,5pt | Keputusan owner 2026-08-18; konstanta `HIER_FONT_*` di `pdf_exporter.py`; commit `9932d0a4` | 2026-08-18 |
| R-26 | **Indentasi hierarki DIGANTI jarak bawah** (`HIER_SPACE_AFTER_*` 4/3/1pt) — indentasi `LEFTPADDING 12pt` memakan lebar kolom uraian yang sudah sempit. Indentasi berbasis spasi di `_render_uraian_text` TIDAK ikut diubah: itu milik tabel Kurva-S | Keputusan owner 2026-08-18; commit `9932d0a4` | 2026-08-18 |
| R-27 | **Lebar tabel tanda tangan diturunkan dari lebar cetak sebenarnya**, bukan angka mati. Nilai lama 250mm melebihi area cetak A4 portrait 190mm sehingga kolom kanan terpotong. Dikunci tes | Commit `d2570b08`; `tests_export_signature.SignatureSheetRenderTests` | 2026-08-18 |
| R-28 | **Lembar pengesahan wajib di 5 dokumen perencanaan** (Rekap RAB, Rincian AHSP, Volume, Harga Items, Rekap Kebutuhan) memakai SATU blok bersama. Dikunci `SignatureCoverageTests` | Keputusan owner 2026-08-18; commit `982a96b1` | 2026-08-18 |
| R-30 | **Jumlah periode laporan Jadwal = periode NYATA proyek**, tanpa minimum buatan (dulu view memaksa ≥12 minggu/≥3 bulan: proyek 41 hari menawarkan Minggu 1-12/Bulan 1-3). SATU sumber `timeline_utils.project_report_period_counts` (batas minggu kanonik `expected_week_count`, "Bulan" = 4 minggu) dipakai modal export, validasi backend, dan kolom mingguan adapter. Periode di luar masa proyek DITOLAK (`ExportValidationError` → HTTP 400), bukan laporan kosong 0% | Keputusan owner 2026-09-27; `tests_jadwal_monthly_report.ReportPeriod*` | 2026-09-27 |
| R-31 | **Progress kumulatif = W1 s.d. akhir periode sebelumnya** di SEMUA laporan Jadwal (harian: s.d. minggu lalu; bulanan: "Kumulatif Bulan Lalu" = W1..akhir bulan lalu; mingguan: sudah begitu). Nilai TIDAK dibulatkan per baris sebelum dijumlah → TOTAL tabel = Akumulasi di Ringkasan. Laporan harian menambah kolom **s.d. minggu ini berisi target rencana saja** (realisasi/deviasi `-`) | Keputusan owner 2026-09-27; `tests_jadwal_monthly_report.MonthlyCumulativeProgressTests`, `tests_wp_export_parity.JadwalDailyDocxExportTests` | 2026-09-27 |
| R-32 | **Laporan harian: tabel identitas hanya Proyek/Lokasi/Cuaca/Pemilik** (No. Kontrak, Kontraktor, Konsultan, Tgl Laporan dibuang — sudah di subjudul/pengesahan); **pengesahan hanya Kontraktor Pelaksana + Konsultan Pengawas** (tanpa Pemilik), ruang TTD 2,2 cm; 24 baris pekerjaan/halaman | Keputusan owner 2026-09-27; commit `e2183b89` | 2026-09-27 |
| R-33 | **Jabatan penanda tangan TIDAK dikarang.** Pengesahan laporan progress dulu mencetak "Direktur" untuk Pelaksana & Pengawas. ~~→ tampil `Jabatan: ....` untuk diisi tangan~~ *Direvisi 2026-09-27 (R-37): placeholder melanggar R-20 (tanpa slot kosong); pihak tanpa field jabatan tidak mendapat baris jabatan.* | Keputusan owner 2026-09-27 | 2026-09-27 |
| R-34 | **Label identitas laporan progress PDF sesuai isinya**: Pemilik, Sumber Dana, Lokasi; `Ket. Project 1/2` (field Dashboard `ket_project1/2`) hanya tampil bila diisi — dulu label "Ket. Project" menampilkan Sumber Dana/Pemilik | Keputusan owner 2026-09-27 | 2026-09-27 |
| R-35 | **Angka PDF tidak boleh dipotong karakter** (dulu `Rp6.894.896.91` = Rp 6,8 miliar terbaca juta; volume `3000.`): format id-ID via `format_cell_display`, font diperkecil (`_fit_font_size`) bila tak muat. Rupiah dibulatkan, bukan `int()`. PageBreak beruntun (halaman kosong) dipadatkan `_collapse_redundant_page_breaks` | Keputusan owner 2026-09-27; `tests_jadwal_monthly_report.MonthlyPdfRenderTests` | 2026-09-27 |
| R-36 | **Cover PDF laporan Jadwal (bulanan/mingguan/rekap) disederhanakan**: kotak placeholder logo (40×25mm, opacity 40%) DIHAPUS — tidak lagi dipakai di PDF; pemisah `'─' * 35` (glyph tak ada di Helvetica → tercetak deret kotak) diganti satu `HRFlowable` tipis; bingkai halaman, judul, nama proyek (di-escape), periode, dan detail dipertahankan. Nilai identitas (cover & halaman progress) dibungkus `Paragraph` agar teks panjang turun baris | Keputusan owner 2026-09-27; `tests_jadwal_monthly_report.MonthlyPdfRenderTests` | 2026-09-27 |
| R-37 | **Susunan lembar pengesahan untuk SEMUA pihak (pemilik, perencana, kontraktor, pengawas): INSTANSI / ruang TTD / NAMA (digarisbawahi) / keterangan.** Keterangan pemilik: `ket_client2` langsung setelah nama, lalu `jabatan_client`; pihak lain belum punya field jabatan → tanpa baris keterangan. Tanpa kata penghubung, sebutan peran, tempat & tanggal. Berlaku **PDF + Word + Excel**: satu sumber data `SignaturePresets.build_signatures` (`instansi`/`name`/`details`), satu renderer per format (`_build_signatures` PDF, `_build_signature_section` Word, `_write_signature_block` Excel). Laporan progress PDF & Excel Jadwal (yang dulu hardcode "Manajer Proyek"/"(Nama Pemilik)"/"PEMILIK PEKERJAAN") kini memakai blok ini; laporan harian Word tetap 2 pihak (R-32) dengan susunan yang sama. Template pengesahan di sheet "Data Master" dihapus | Keputusan owner 2026-09-27; `tests_export_signature`, `tests_jadwal_monthly_report.ProgressSignatureLayoutTests` | 2026-09-27 |
| R-29 | **Paket perencanaan = 4 dokumen dalam SATU berkas** (Rekap RAB, Rincian AHSP, Volume, Harga Items), tersedia PDF/Word/Excel, **lembar pengesahan tetap per dokumen** (bukan satu di akhir). Tombol "Unduh Paket" berdiri sendiri; dropdown export dokumen tunggal TETAP ada | Keputusan owner 2026-08-18; commit `354c66e8`; `tests_export_paket.py` | 2026-08-18 |
| R-38 | **Rangkuman Progress Akhir Waktu Kerja hanya di PDF mingguan/bulanan dan Word harian saat ada tambahan.** Halaman sendiri sesudah periode batas (atau di depan bila hanya masa tambahan dipilih), dengan pengesahan PDF **menempel di halaman yang sama** (owner 2026-09-30; tanpa pemutus halaman); Word harian tanpa pengesahan pada rangkuman. Angka berbobot s.d. minggu batas, dengan catatan bahwa progres dicatat per minggu; tabel hanya pekerjaan yang belum 100% | Doc 42 K-1..K-8; doc 43 E3; `ExtensionSummaryDataTests`, `ExtensionSummaryWordTests`, `ExtensionSummaryPdfTests` | 2026-09-30 |
| R-39 | **Tabel mingguan PDF menandai tambahan seperti web:** garis tebal merah di tepi kanan kolom minggu batas dan teks "Penambahan" pada header minggu tambahan. Berlaku pada grid rekap Rencana/Realisasi, Kurva S, Gantt; laporan mingguan/bulanan pada periode tambahan juga memiliki subjudul "Penambahan Waktu Kerja" di halaman progres, tanpa mengubah cover | Doc 42 K-9..K-11/K-15; doc 43 E4; `ExtensionPdfMarkerTests`; QA render PDF tipe 2 | 2026-09-30 |
| R-40 | **Excel Jadwal memberi garis tebal di tepi kanan minggu batas dan label "Penambahan" pada header minggu tambahan** di sheet berkolom minggu (Data Master, Kurva S, Input Progress-Gantt). Rincian periode tambahan memakai subjudul "Penambahan Waktu Kerja". Blok realisasi Rincian mingguan berlaku untuk semua proyek (R-14) | Doc 42 K-11/K-12/K-15; doc 43 E5; `ExtensionExcelMarkerTests`, gate doc 30 §8.3 | 2026-09-30 |
| R-41 | **Laporan harian Word pada tanggal sesudah akhir kontrak memakai subjudul "Penambahan Waktu Kerja"** di halaman laporan dan dokumentasi hari tersebut. Tanggal dalam masa kontrak tidak diberi penanda; isi dan pengesahan harian tetap mengikuti R-32/R-37 | Doc 42 K-9/K-15; doc 43 E2; `ExtensionDailyWordTests` | 2026-09-30 |
| R-42 | **Bagian masa Penambahan Waktu Kerja berwarna merah tua hampir hitam `#4a0e0e`** (`UTS.EXTENSION_PRIMARY`, Excel `COLORS['EXTENSION']`); masa kontrak tetap navy. Berlaku: judul/subjudul & header tabel halaman progres periode tambahan (PDF), judul cover laporan periode tambahan, lembar Rangkuman (judul + header tabel), header kolom minggu tambahan di semua tabel berkolom minggu (grid Rekap, Gantt, Kurva S, Data Master/Kurva S/Input Progress-Gantt Excel), judul & header Rincian Excel periode tambahan, judul & header tabel halaman harian Word hari tambahan. Kata "terlambat" tetap tidak dipakai (K-15) | Owner 2026-09-30; `ExtensionOwnerFeedbackTests` | 2026-09-30 |
| R-43 | **Kurva S Rekap PDF yang terbagi karena baris panjang adalah SATU kurva**, seperti web: skala 0-100% memakai tinggi gabungan semua baris (100% = baris pertama halaman pertama, 0% = baris terakhir halaman terakhir); tiap halaman menggambar potongan kurva di rentang barisnya (dipotong di batas halaman). Baris per halaman mengikuti tinggi halaman yang tersedia, bukan batas tetap 25 baris | Owner 2026-09-30; `RekapKurvaSingleCurveTests` | 2026-09-30 |
| R-44 | **Word untuk laporan bulanan & mingguan Jadwal diaktifkan** (owner 2026-09-30). Susunan per periode sama dengan PDF: cover (judul, nama proyek, periode, identitas), halaman Progres Pelaksanaan (identitas + ringkasan: rencana/realisasi periode, akumulasi, deviasi; rincian per pekerjaan: volume, harga satuan, total harga, bobot, kumulatif lalu, progres ini, kumulatif ini, TOTAL), lalu pengesahan (R-37). Rangkuman Progress Akhir Waktu Kerja ditempatkan seperti PDF (R-38); warna masa tambahan R-42. **Tanpa grafik** (R-9). Rekap Word tetap dimatikan. Status Ahead/Behind tidak dicetak (K-13) | `word_exporter._export_progress_report`; `WordProgressReportTests` | 2026-09-30 |
| R-45 | **Kurva S Rekap PDF selebar halaman bila semua minggu muat satu halaman**: kolom minggu melebar mengisi sisa lebar (dulu separuh halaman kosong). Bila minggu terbagi ke beberapa halaman, lebar kolom tetap (R-1) agar halaman sejajar | Owner 2026-09-30; `RekapKurvaSingleCurveTests.test_single_week_chunk_fills_the_page_width` | 2026-09-30 |
| R-46 | **Daftar isi Rekap PDF memakai nomor halaman nyata** dari render akhir (ReportLab `TableOfContents` + `multiBuild`; penanda di awal tiap bagian). Hanya bagian yang benar-benar ada yang tercantum (mis. "Gantt Chart" tidak muncul bila bagiannya tidak dirender). Tampilan disederhanakan: titik-titik penghubung + nomor di kanan; ikon/emoji dan latar baris selang-seling dihapus (dulu nomor halaman berupa "...") | Temuan cek visual 2026-10-01 (`docs/CEK_VISUAL_SAMPEL_EXPORT_20261001.md`); commit `230f975b`; `RekapPdfLayoutTests.test_rekap_toc_uses_real_section_page_numbers` | 2026-10-01 |
| R-47 | **Judul "GRAFIK KURVA S" selalu sehalaman dengan grafik pertamanya**: judul + grafik halaman pertama dijaga `KeepTogether`, dan potongan baris pertama dikurangi setinggi judul (`first_chunk_reserve`); halaman Kurva S berikutnya tetap memuat baris penuh (R-43) | Temuan cek visual 2026-10-01; commit `230f975b` + perbaikan lanjutan; `RekapPdfLayoutTests.test_kurva_s_title_stays_with_full_height_chart`, `RekapKurvaSingleCurveTests.test_first_page_reserves_room_for_section_title` | 2026-10-01 |
| R-48 | **Word laporan bulanan & mingguan Jadwal mengikuti tampilan PDF** (memperbarui R-44): huruf Arial; cover berbingkai navy selebar area cetak, judul di tengah + garis tipis, nama proyek, periode, identitas Lokasi/Pemilik/Sumber Dana/Anggaran (label rata kanan), tanpa header/footer; halaman progres: panel IDENTITAS PROJECT \| RINGKASAN PROGRESS berdampingan berlatar abu muda (deviasi hijau/merah/kuning), RINCIAN PROGRESS dengan header kapital, baris klasifikasi/sub diarsir penuh, garis abu tebal mengapit kolom progres, baris TOTAL; judul "LEMBAR PENGESAHAN" kecil rata kiri; header berjalan (nama proyek \| segmen) + footer "Dashboard-RAB.com". **Perbedaan sengaja: uraian pekerjaan di Word tidak dipotong** (PDF memotong "..."). Warna masa tambahan tetap R-42 | Owner 2026-10-01; `WordProgressReportTests.test_word_progress_follows_pdf_design` | 2026-10-01 |
| R-49 | **Persen di laporan Jadwal PDF memakai format Indonesia** (koma desimal, mis. "8,64%", "+16,33%"): ringkasan progres bulanan/mingguan, tabel rincian, ringkasan Kurva S Rekap, ringkasan eksekutif; juga **Word harian** (tabel progres kumulatif, mis. "30,00% (+10,00%)"). Menyelaraskan PDF dengan keputusan doc 30 (2dp id-ID semua format); dulu PDF memakai titik | Owner 2026-10-01; `pdf_exporter._pct_id`; `WordProgressReportTests.test_weekly_pdf_progress_percent_uses_id_locale` | 2026-10-01 |
| R-50 | **Semua cover PDF tanpa header/footer**, termasuk cover periode ke-2 dst. di laporan bulanan/mingguan (dulu hanya halaman 1 yang bersih). Cover menandai halamannya lewat `SegmentMarker(COVER_SEGMENT)`; kanvas melewati header/footer halaman itu (R-36) | Temuan cek visual 2026-10-01; `WordProgressReportTests.test_every_pdf_cover_has_no_header_footer` | 2026-10-01 |

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
| 2 | `_build_progress_signature_section()` | Laporan progress/pengawasan | **Disatukan 2026-09-27** — kini pembungkus tipis `_build_signatures(width_mm=A4)` (R-37) |
| 3 | `_build_monthly_signature_page()` | — | **Dihapus 2026-09-27** (kode mati) |
| 4 | dict `signature_data` | Volume, Harga Items | **Dihapus 2026-09-27** — Excel memakai `_write_signature_block` dari data proyek (R-37) |
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
