# 43 — Export Jadwal: Penambahan Waktu Kerja — Rencana & Tracker

| | |
|---|---|
| Tanggal | 2026-09-30 |
| Dasar | Doc 42 (kondisi saat ini, temuan X-1..X-8, L-1..L-6, keputusan K-1..K-16) |
| Pelaksana | **Codex** (eksekutor). **Claude** mengawasi: review diff, menjalankan tes di DB terpisah, memeriksa hasil export sungguhan |
| Branch | `feat/tambahan-waktu-kerja` (lanjutan). WIP owner di working tree **tidak disentuh**; commit hanya memuat hunk milik langkahnya |
| Aturan tampilan | Wajib cek `docs/DESIGN_REGISTRY_EXPORT.md` sebelum mengubah visual; keputusan baru dicatat sebagai R-38 dst. |

Dokumen ini adalah **satu-satunya sumber status** pekerjaan export Penambahan Waktu Kerja.

---

## 1. Ringkasan keputusan yang dieksekusi (dari doc 42 §9)

| # | Isi |
|---|---|
| K-1..K-7 | Lembar **"Rangkuman Progress Akhir Waktu Kerja"**, PDF & Word saja, akumulasi saat kontrak berakhir (s.d. minggu batas + catatan "progres dicatat per minggu"), tabel pekerjaan belum 100% (No, Uraian, Bobot, Realisasi Kumulatif, Sisa, Sisa Bobot, Keterangan kosong), halaman sendiri sebelum pengesahan, tanpa pengesahan di harian |
| §9.2 | Susunan per tipe (tabel §3 di bawah) |
| K-8 | Ekspor yang hanya berisi periode tambahan → Rangkuman di depan |
| K-9 | Laporan masa tambahan **isinya sama** dengan laporan normal; beda hanya teks penanda |
| K-10 | Cover tidak diubah |
| K-11 | Penanda tabel PDF/Excel **sama dengan web**: satu garis tebal di tepi kanan kolom minggu batas + label "Penambahan" di header kolom tambahan |
| K-12 | Excel mingguan **ditambah realisasi** |
| K-13 | Tidak ada keterangan tambahan untuk rencana 100%/deviasi/status |
| K-14 | L-1..L-6 dikerjakan di fase ini |
| K-15 | **Tidak ada kata "terlambat/keterlambatan"** di hasil export; penanda = **"Penambahan Waktu Kerja"** |

---

## 2. Aturan teknis bersama

1. **Satu sumber batas.**
   - Akhir kontrak, minggu batas, minggu/hari tambahan, dan akhir rentang **hanya** dihitung lewat helper `timeline_utils`: `work_period_end`, `contract_boundary_week`, `is_extension_week`, `is_extension_day`.
   - Ini invariant I-5 doc 41. Exporter tidak menghitung sendiri.
2. **Adapter meneruskan metadata.**
   - Kolom minggu membawa `is_boundary_week` dan `is_extension_week`.
   - Data laporan membawa `contract_end`, `additional_end`, `boundary_week`.
   - Proyek tanpa tambahan: semua penanda `False`/`None`, keluaran **identik** dengan sebelum fase ini (I-1).
3. **Angka tidak berubah.** Bobot, kumulatif, deviasi, dan nilai resmi Excel (A-1 doc 30) tetap. Fase ini hanya menambah penanda, lembar Rangkuman, realisasi Excel mingguan, dan perbaikan L-1..L-6.
4. **Tes di lapisan render.** Tes harus membuka file hasil (teks PDF via `pdf_page_texts`, DOCX via python-docx, XLSX via openpyxl), bukan hanya data adapter. Ini pelajaran registri: tes penyedia data lolos meski perender membuang data.
5. **Fixture wajib dua tipe.**
   - **Tipe 1:** akhir kontrak Rabu, tambahan Sabtu di minggu yang sama, tidak ada minggu baru.
   - **Tipe 2:** seperti proyek 217. Akhir kontrak Sabtu; minggu batas memuat satu hari tambahan (Minggu); lalu satu minggu baru.

---

## 3. Susunan dokumen yang harus dihasilkan

"Masa tambahan" = periode sesudah akhir kontrak. **"Periode batas"** = minggu/bulan yang memuat akhir kontrak.

| Laporan | Tipe 1 | Tipe 2 |
|---|---|---|
| Harian (Word) | [hari ≤ akhir kontrak] **[Rangkuman]** [hari tambahan, bertanda PWK] | sama |
| Mingguan (PDF) | [… minggu batas] **[Rangkuman]** | [… minggu batas] **[Rangkuman]** [minggu tambahan, bertanda PWK] |
| Bulanan (PDF) | [… bulan batas] **[Rangkuman]** | [… bulan batas] **[Rangkuman]** [bulan sesudahnya, bertanda PWK, bila ada] |

PWK = "Penambahan Waktu Kerja".

Aturan penempatan:
- **Harian:** setiap hari **sesudah** akhir kontrak bertanda PWK, termasuk hari tambahan di minggu batas.
- Rangkuman muncul bila periode yang dipilih mencakup periode batas atau periode sesudahnya (K-7).
- Ekspor yang hanya berisi masa tambahan: Rangkuman di depan (K-8).
- Ekspor yang hanya berisi periode sebelum periode batas: tidak ada Rangkuman.
- Periode batas sendiri memakai teks normal. Kolom tambahan di dalamnya ditandai lewat K-11.

---

## 4. Langkah

### E0 — Fixture & baseline

- **Isi:** fixture tes tipe 1 dan tipe 2 (bisa di modul tes baru `tests_export_penambahan_waktu_kerja.py`).
- **Baseline:** rekam suite penuh `detail_project` + `dashboard` di DB terisolasi, serta Vitest.
- **Selesai bila:** baseline tercatat di §6. Kegagalan yang diketahui hanya 3 tes lama (lihat doc 41 §3).

### E1 — Metadata batas di adapter

- **Isi:** aturan §2 butir 1–2 di `jadwal_pekerjaan_adapter.py` (kolom minggu, data rekap/bulanan/mingguan, data harian).
- **Tes:**
  - tipe 1: minggu batas benar, tidak ada minggu tambahan;
  - tipe 2: W6 batas, W7 tambahan;
  - proyek tanpa tambahan: semua `False`.
- **Selesai bila:** metadata dipakai dari helper; tidak ada perhitungan tanggal baru di exporter.

### E2 — Laporan harian di masa tambahan (X-1)

- **Isi:**
  - batas akhir `_build_laporan_harian_sheets`/`_resolve_laporan_harian_dates` = `work_period_end` (`export_manager.py:1284`);
  - halaman hari sesudah akhir kontrak diberi penanda PWK (K-15);
  - isi halaman sama dengan hari normal (K-9).
- **Tes (render DOCX):**
  - tipe 2 minggu 7 kini berhasil;
  - minggu 6 memuat hari tambahan 20/09 dengan penanda;
  - hari masa kontrak tanpa penanda;
  - tidak ada kata "terlambat".
- **Selesai bila:** periode di luar `work_period_end` tetap ditolak (`ExportValidationError`, R-30).

### E3 — Rangkuman Progress Akhir Waktu Kerja

- **Data:** satu metode adapter (misalnya `get_contract_end_summary`), dipakai PDF dan Word.
  - Akumulasi rencana/realisasi/deviasi s.d. minggu batas, berbobot, **memakai fungsi bobot yang sama** dengan laporan lain.
  - Daftar pekerjaan dengan realisasi < 100% s.d. minggu batas.
  - Kolom per pekerjaan: bobot, realisasi kumulatif, sisa, sisa bobot.
  - Catatan "progres dicatat per minggu; minggu batas dd/mm–dd/mm".
- **Render:** PDF (mingguan, bulanan) dan Word (harian), sebagai halaman sendiri, dengan penempatan sesuai §3.
- **Tes (render):**
  - urutan halaman untuk semua kasus §3: tipe 1 dan tipe 2, campuran, hanya-tambahan, hanya-sebelum-batas;
  - angka Rangkuman = kumulatif laporan mingguan minggu batas;
  - Excel **tidak** memuat Rangkuman (K-2).
- **Selesai bila:** registri R-38 (Rangkuman) tercatat.

### E4 — Penanda masa tambahan di PDF (K-11, K-9)

- **Isi:**
  - garis tebal di tepi kanan kolom minggu batas dan label "Penambahan" di header kolom tambahan, pada semua tabel mingguan PDF: grid Rencana/Realisasi Rekap, tabel Kurva S, Gantt;
  - subjudul PWK pada laporan mingguan/bulanan untuk periode tambahan (tipe 2).
- **Periksa juga X-8:** apakah Kurva S muncul dua kali di PDF Rekap (gambar browser + gambar server). Laporkan temuannya; putuskan bersama owner sebelum mengubah.
- **Tes (render):** penanda ada hanya pada proyek bertambahan; posisinya di kolom minggu batas yang benar.
- **Selesai bila:** registri R-39 tercatat.

### E5 — Excel (K-11, K-12)

- **Isi:**
  - penanda K-11 di sheet Excel yang memiliki kolom minggu: Data Master, Rincian, Kurva S, Input Progress-Gantt;
  - Excel mingguan ditambah realisasi (K-12).
- **Perhatian:** doc 30 §8.3 mengunci Excel mingguan sebagai "planned-only" beserta gate-nya. Perbarui gate dan doc 30. Nilai tetap nilai backend (A-1), tanpa formula recompute di sheet resmi.
- **Tes (render XLSX):**
  - minggu tambahan tipe 2 menampilkan realisasi (proyek 217 W7 = 9,45%);
  - gate paritas doc 30 tetap hijau.
- **Selesai bila:** registri R-40 (penanda Excel) dan revisi R-14/doc 30 tercatat.

### E6 — Perbaikan L-1..L-6

| # | Isi |
|---|---|
| L-1 | Anggaran cover Excel Rekap = anggaran pemilik, format id-ID, sama dengan PDF |
| L-2 | Label Indonesia di tabel/Excel ("Minggu", "Bulan", "Realisasi"); status Ahead/Behind tidak dicetak (K-13), jadi cukup dibiarkan |
| L-3 | Label bulan tidak melebihi minggu nyata (M2 = "W5–W7") |
| L-4 | Footer halaman cover laporan kedua memakai judul yang benar |
| L-5 | Sisa float (`2e-28`) dibulatkan di boundary exporter |
| L-6 | Doc 12 diperbarui ke jalur export saat ini |

- **Tes:** satu tes render per butir L-1, L-3, L-4, L-5.
- **Selesai bila:** registri diperbarui bila menyangkut tampilan.

### E7 — Verifikasi akhir

1. Suite penuh `detail_project` + `dashboard` di DB terisolasi: tidak ada kegagalan di luar baseline.
2. Vitest penuh dan `npm run build` (bila JS berubah).
3. Probe export proyek 217 (semua laporan × format, di transaksi rollback) dan fixture tipe 1: urutan halaman, penanda, Rangkuman, tanpa kata "terlambat".
4. UAT owner (§5).

---

## 5. Checklist UAT (owner)

| # | Skenario | Diharapkan | Hasil |
|---|---|---|---|
| U-1 | Harian minggu 7 proyek 217 | Berhasil; halaman 21/09 bertanda PWK; Rangkuman di depan | |
| U-2 | Harian minggu 6 proyek 217 | 14–19/09 normal, Rangkuman, lalu 20/09 bertanda PWK | |
| U-3 | Mingguan W6+W7 PDF | [W6] [Rangkuman] [W7 bertanda PWK] | |
| U-4 | Bulanan M1+M2 PDF | [M1] [M2] [Rangkuman]; kolom W7 berlabel "Penambahan", garis di tepi W6 | |
| U-5 | Rekap PDF & Excel | Garis batas di W6, label "Penambahan" di W7, tanpa Rangkuman di Excel | |
| U-6 | Mingguan Excel W7 | Realisasi 9,45% tampil | |
| U-7 | Proyek tanpa tambahan | Tidak ada perbedaan dari sebelum fase ini | |
| U-8 | Proyek tipe 1 | Mingguan/bulanan hanya menambah Rangkuman; harian menandai hari tambahan | |
| U-9 | Semua file | Tidak ada kata "terlambat/keterlambatan" | |

---

## 6. Progres

| Langkah | Status | Commit | Tanggal | Catatan |
|---|---|---|---|---|
| E0 | DONE | `63ef286c` | 2026-09-30 | Fixture tipe 1, tipe 2, tanpa tambahan lulus; baseline backend 894 tes/3 gagal lama/40 skipped, frontend 431 lulus/25 skipped |
| E1 | DONE | `af99f8ff` | 2026-09-30 | Adapter meneruskan akhir kontrak/tambahan dan minggu batas; kolom bertanda, harian membawa flag hari tambahan; 21 tes terkait lulus |
| E2 | DONE | `4d9907a7` | 2026-09-30 | Word harian menerima tanggal tambahan dan menandainya di subjudul; 14 tes render harian lulus |
| E3 | DONE | `f77ed38c` | 2026-09-30 | Rangkuman berbobot PDF/Word sesudah periode batas, sebelum pengesahan PDF; uji data dan file jadi lulus |
| E4 | DONE | `a577f2a8` | 2026-09-30 | Garis W6/label W7 di grid, Kurva S, Gantt PDF; subjudul laporan tambahan; 32 tes lulus dan PDF tipe 2 diperiksa visual |
| E5 | DONE | `98f9fddc` + `0851b429` | 2026-09-30 | Excel: penanda minggu pada sheet berkolom waktu, subjudul Rincian tambahan. Realisasi mingguan semula hanya proyek bertambahan; owner memutuskan **semua proyek** (§8) dan diperbaiki di commit E6 |
| E6 | DONE | `0851b429` | 2026-09-30 | Dimulai Codex (L-1, L-2, token habis), diselesaikan Claude: L-1..L-6 + perbaikan review (halaman kosong, realisasi semua proyek, `planned_map` mati) |
| E7 | REVIEW | — | 2026-09-30 | Suite penuh + probe 217 lulus (§7). Menunggu UAT owner §5 |

Status: `TODO` / `WIP` / `REVIEW` (menunggu pemeriksaan Claude) / `DONE` / `BLOCKED`.
Setiap langkah = satu commit kode + catatan bukti uji di bawah.

## 7. Log bukti uji

| Tanggal | Langkah | Perintah | Hasil |
|---|---|---|---|
| 2026-09-30 | E0 baseline backend | `docker exec -e POSTGRES_TEST_DB=test_twk_export_43_20260930 ahsp_web python manage.py test detail_project dashboard --settings=config.settings.test_pg --noinput --verbosity=1` | 894 tes; 3 gagal baseline yang sama dengan doc 41 §3; 40 skipped. DB terisolasi dibuat dan dihancurkan. |
| 2026-09-30 | E0 baseline frontend | `npm run test:frontend -- --reporter=dot --silent` | 39 file; 431 lulus, 25 skipped. |
| 2026-09-30 | E0 fixture | `docker exec -e POSTGRES_TEST_DB=test_twk_export_43_e0 ahsp_web python manage.py test detail_project.tests_export_penambahan_waktu_kerja --settings=config.settings.test_pg --noinput --verbosity=1` | 3 lulus: tambahan satu minggu yang sama, tambahan sampai W7, tanpa tambahan. |
| 2026-09-30 | E1 | `docker exec -e POSTGRES_TEST_DB=test_twk_export_43_e1 ahsp_web python manage.py test detail_project.tests_export_penambahan_waktu_kerja detail_project.tests_jadwal_monthly_report.ReportPeriodCountTests detail_project.tests_wp_export_parity.JadwalDailyDocxExportTests --settings=config.settings.test_pg --noinput --verbosity=1` | 21 lulus; metadata tipe 1/2 dan tanpa tambahan, hitung periode kanonik, serta jalur DOCX harian lama. |
| 2026-09-30 | E2 | `docker exec -e POSTGRES_TEST_DB=test_twk_export_43_e2 ahsp_web python manage.py test detail_project.tests_export_penambahan_waktu_kerja.ExtensionDailyWordTests detail_project.tests_wp_export_parity.JadwalDailyDocxExportTests --settings=config.settings.test_pg --noinput --verbosity=1` | 14 lulus; DOCX W7 dapat dibuat, W6 hanya 20/09 bertanda, tipe 1 bertanda sesudah Rabu, hari di luar akhir tambahan ditolak. |
| 2026-09-30 | E3 | `docker exec -e POSTGRES_TEST_DB=test_twk_export_43_e3 ahsp_web python manage.py test detail_project.tests_export_penambahan_waktu_kerja detail_project.tests_jadwal_monthly_report.ProgressSignatureLayoutTests detail_project.tests_wp_export_parity.JadwalDailyDocxExportTests --settings=config.settings.test_pg --noinput --verbosity=1` | 33 lulus: bobot 25:75 menghasilkan realisasi 62,50% dan sisa bobot 37,50%; PDF mingguan/bulanan dan DOCX harian dibuka dan urutan halaman diperiksa. |
| 2026-09-30 | E3 single period | `docker exec -e POSTGRES_TEST_DB=test_twk_export_43_e3_single ahsp_web python manage.py test detail_project.tests_export_penambahan_waktu_kerja.ExtensionSummaryPdfTests.test_single_period_pdf_paths_place_summary_once --settings=config.settings.test_pg --noinput --verbosity=1` | 1 lulus; PDF minggu/bulan tunggal masing-masing memiliki satu Rangkuman sebelum pengesahan. |
| 2026-09-30 | E4 | `docker exec -e POSTGRES_TEST_DB=test_twk_export_43_e4 ahsp_web python manage.py test detail_project.tests_export_penambahan_waktu_kerja detail_project.tests_jadwal_monthly_report.ProgressSignatureLayoutTests --settings=config.settings.test_pg --noinput --verbosity=1` | 32 lulus; PDF hasil dibuka untuk grid Rencana/Realisasi, Kurva S rekap/bulanan, Gantt, laporan minggu tambahan dan pengesahan. Garis W6 dan label W7 tampak pada render tipe 2. |
| 2026-09-30 | E5 | `docker exec -e POSTGRES_TEST_DB=test_twk_export_43_e5 ahsp_web python manage.py test detail_project.tests_export_penambahan_waktu_kerja.ExtensionExcelMarkerTests detail_project.tests_wp_export_parity.JadwalMonthlyValueOnlyTests --settings=config.settings.test_pg --noinput --verbosity=1` | 10 lulus; XLSX hasil dibuka untuk Data Master, Kurva S, Input Progress-Gantt, Rincian W6/W7; realisasi W7 37,50% pada fixture dan rencana lama tetap; gate no-formula-recompute hijau. |
| 2026-09-30 | Review E0-E5 (Claude) | Snapshot `git archive HEAD` (tanpa WIP) di container, `POSTGRES_TEST_DB=test_claude_review_head`, suite penuh `detail_project` + `dashboard` | 920 tes; hanya 3 gagal baseline; 40 skipped |
| 2026-09-30 | Review E0-E5 (Claude) | Probe export nyata proyek 217 (semua laporan × format, transaksi di-rollback) | Urutan halaman, Rangkuman, penanda, realisasi Excel sesuai §3. Temuan: halaman 1 kosong pada PDF mingguan yang hanya berisi masa tambahan (lihat §8) |
| 2026-09-30 | E6 (Claude) | `tests_export_penambahan_waktu_kerja`, `tests_jadwal_monthly_report`, `tests_wp_export_parity` | 84 lulus. Tes baru halaman-kosong dan footer L-4 terbukti gagal saat perbaikannya dicabut |
| 2026-09-30 | E7 (Claude) | Suite penuh working tree, `POSTGRES_TEST_DB=test_claude_final` | **931 tes; hanya 3 gagal baseline**; 40 skipped |
| 2026-09-30 | E7 (Claude) | Probe export proyek 217 ulang | W7 saja: Rangkuman di halaman 1; header Excel "Minggu 7 / Penambahan"; realisasi W7 tampil; tanpa kata "terlambat". Frontend tidak diubah pada E6, Vitest tidak perlu diulang |

## 8. Log temuan & keputusan tambahan

| Tanggal | Langkah | Temuan / keputusan | Oleh |
|---|---|---|---|
| 2026-09-30 | E2 | Penanda harian K-15 ditempatkan di subjudul tanggal/minggu. Halaman dokumentasi hari yang sama memakai subjudul itu juga; isi pekerjaan dan pengesahan tetap. | Codex |
| 2026-09-30 | E4 / X-8 | Kurva S browser tidak digandakan pada PDF Rekap: exporter sengaja melewati lampiran dengan judul Kurva S dan tetap menggambar Kurva S server. PDF dengan/tanpa lampiran browser berjumlah halaman dan segmen Kurva S sama. Tidak ada perubahan X-8. | Codex |
| 2026-09-30 | E4 / L-3 | QA visual PDF Bulan 2 proyek 7 minggu masih menulis "Minggu 5 - 8" dan menampilkan W8 kosong. Ini temuan L-3 yang sudah direncanakan untuk E6, bukan akibat penanda E4. | Codex |
| 2026-09-30 | E5 / I-1 | K-12 ditafsirkan untuk proyek dengan masa tambahan saja. Bila diterapkan pada semua proyek, Excel mingguan proyek tanpa tambahan berubah dan melanggar invariant I-1 §2. Gate doc 30 untuk proyek biasa tetap planned-only; proyek bertambahan mendapat blok realisasi. | Codex |
| 2026-09-30 | Review E3 | PDF mingguan/bulanan yang **hanya** berisi masa tambahan (K-8) diawali halaman kosong: `_append_contract_end_summary` selalu memberi `PageBreak` walau belum ada isi. Diperbaiki: tanpa pemutus halaman bila Rangkuman membuka dokumen; tes `test_extension_only_starts_with_summary_before_weekly_cover` diperketat | Claude |
| 2026-09-30 | Review E5 | Owner memutuskan realisasi Excel mingguan untuk **semua proyek** (membatalkan tafsiran E5 "hanya proyek bertambahan"). Gate doc 30 §8.3, R-14, R-40 diperbarui | Owner / Claude |
| 2026-09-30 | E6 / L-2 | Owner menyetujui revisi R-7: label Indonesia ("Input Progres Rencana/Realisasi", "Minggu N", "Bulan N", "Realisasi"). Singkatan kolom rapat "W7" dan nama sheet Excel yang dirujuk formula tetap | Owner / Claude |
| 2026-09-30 | E6 / L-3 | Label bulan dibatasi minggu nyata di PDF (judul Kurva S bulanan, "Grafik: Minggu 1 - Minggu N", header kolom) dan label periode adapter. Padding kolom Excel bulanan (gate doc 30) sengaja tidak diubah | Claude |
| 2026-09-30 | E6 / L-4 | Footer cover laporan mingguan kedua membawa judul "Rincian Progress Minggu ke-(n-1)": segmen tidak ditutup. Kini ditutup sebelum cover, sama seperti loop bulanan | Claude |
| 2026-09-30 | E6 / L-5 | Deviasi Excel bulanan dibulatkan 1e-12 (sisa Decimal 2e-28 tampil "+0,00%" alih-alih "-") | Claude |
