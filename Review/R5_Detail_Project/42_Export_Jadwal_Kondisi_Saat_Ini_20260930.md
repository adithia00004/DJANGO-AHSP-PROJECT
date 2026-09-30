# 42 — Export Jadwal Pekerjaan: Kondisi Saat Ini

| | |
|---|---|
| Tanggal | 2026-09-30 |
| Tujuan | Peta kondisi export Jadwal **sebelum** laporan pengawasan disesuaikan dengan Tambahan Waktu Kerja |
| Sifat | Read-only. Tidak ada kode yang diubah untuk dokumen ini |
| Bukti | Pembacaan kode + export sungguhan proyek 217 (di dalam transaksi yang di-rollback) |
| Terkait | Rancangan `docs/RENCANA_JADWAL_MELEWATI_AKHIR_KONTRAK.md` §9; registri `docs/DESIGN_REGISTRY_EXPORT.md`; doc 30, 32, 40, 41 |

---

## 1. Ringkasan

1. **Semua laporan resmi dibuat di server** lewat satu endpoint:
   `POST /detail_project/api/project/<id>/export/jadwal-pekerjaan/professional/`.
   Browser hanya mengirim pilihan periode dan, untuk PDF Rekap/Bulanan, gambar grafik.
2. **Jumlah minggu dan bulan sudah ikut masa tambahan.** Proyek 217 menawarkan 7 minggu dan 2 bulan.
   Minggu ke-7 (hari tambahan) bisa diekspor di laporan mingguan, bulanan, dan rekap.
3. **Laporan harian belum mengenal masa tambahan.** Hari tambahan tidak bisa diekspor sama sekali.
   Ini satu-satunya hal yang benar-benar gagal.
4. **Tidak ada laporan yang menandai batas kontrak.**
   - Minggu tambahan tampil seperti minggu biasa.
   - Cover tidak pernah menyebut akhir waktu kerja maupun Penambahan Waktu Kerja.
5. **Laporan mingguan Excel hanya berisi rencana.** Di minggu tambahan (rencana = 0) realisasinya
   tidak terlihat. Versi PDF menampilkan rencana dan realisasi, jadi kedua format berbeda isi.
6. **Belum ada satu pun tes export yang memakai proyek bertambahan.**

---

## 2. Alur: dari tombol sampai file

### 2.1 Pilihan di modal export

| Laporan (label UI) | `report_type` | Format yang bisa dipilih | Pilihan periode |
|---|---|---|---|
| Laporan Rekap | `rekap` (UI: `full`) | PDF, Excel | — |
| Laporan Bulanan | `monthly` | PDF, Excel | Centang bulan (bisa lebih dari satu) |
| Laporan Mingguan | `weekly` | PDF, Excel | Centang minggu (bisa lebih dari satu) |
| Laporan Harian | `daily` | Word saja | Per hari, per minggu, atau per bulan |

Word untuk Rekap/Bulanan/Mingguan dimatikan di UI dan ditolak server
(`export_manager.py`, "Word export is currently disabled").

### 2.2 Jalur per format

| Format | Jalur di browser | Yang dikirim |
|---|---|---|
| PDF (Rekap, Bulanan) | `jadwal_kegiatan_app.handleExport` → langsung POST ke endpoint professional | Periode, **gambar Kurva S dan Gantt yang digambar di browser**, `gantt_data` (baris + progres dari state browser) |
| PDF (Mingguan) | Sama, tanpa gambar | Periode |
| Word (Harian) | Sama, tanpa gambar | `daily_mode`, `period` |
| Excel (semua) | `handleExport` → `export/export-coordinator.js` → `reports/{rekap,monthly,weekly}-report.js` → POST endpoint professional (`format: 'xlsx'`) | Periode |
| PNG Kurva S/Gantt | Tombol di toolbar grafik, digambar penuh di browser | — (tidak ke server) |

Catatan: `generators/excel-generator.js` (ExcelJS, dibuat di browser) hanya dipakai jalur
`autoDownload = false` yang tidak dipanggil UI. Excel yang diterima pengguna berasal dari server.

### 2.3 Di server

`ExportManager.export_jadwal_professional` (`export_manager.py:800`):

1. Validasi periode (`_validate_report_periods` → `project_report_period_counts`, R-30).
2. Ambil data dari `JadwalPekerjaanExportAdapter`:
   - `get_rekap_report_data`
   - `get_monthly_comparison_data(m)`
   - `get_weekly_comparison_data(w)`
   - harian: `_build_laporan_harian_sheets`
3. Kirim ke exporter:

| Laporan | PDF | Excel | Word |
|---|---|---|---|
| Rekap | `PDFExporter.export_professional` | `ExcelExporter.export_professional` | ditolak |
| Bulanan | `PDFExporter.export_professional` | `export_monthly_professional` | ditolak |
| Mingguan | `PDFExporter.export_professional` | `export_weekly_professional` | ditolak |
| Harian | ditolak | ditolak | `WordExporter.export_daily_professional` (template DOCX) |

---

## 3. Sumber data (adapter)

| Hal | Cara dihitung | Mengikuti tambahan? |
|---|---|---|
| Jumlah minggu/bulan untuk pilihan dan validasi | `project_report_period_counts` → `work_period_end` | **Ya** |
| Tanggal akhir laporan (`adapter.project_end`) | Terbesar dari `tanggal_selesai`, tanggal akhir baris mingguan, dan tahapan mingguan (`_resolve_project_dates`) | **Ya**, tidak langsung (lewat tahapan yang sudah dibentuk ulang) |
| Kolom minggu | Dari `TahapPelaksanaan` mingguan; label bahasa Inggris "Week N" | **Ya** (W7 = 21/09–21/09) |
| Bulan | Kelompok 4 minggu; label "Month N", rentang "W5-W8" | **Ya**, tapi label bisa melebihi jumlah minggu nyata (M2 = "W5-W8" padahal hanya 7 minggu) |
| Bobot | Harga pekerjaan / total harga (`_get_bobot_maps`, `_get_pekerjaan_harga`) | Tidak relevan |
| Kurva S | Kumulatif berbobot per minggu (`_calculate_kurva_s_data`) | Ya; rencana datar 100% setelah minggu batas |
| `project_info.tanggal_selesai` | Diisi `adapter.project_end` (= akhir **tambahan**), sementara `durasi_hari` = durasi **kontrak** | Pasangan ini tidak konsisten. Laten: tidak ditemukan dicetak di cover saat ini |
| Batas kontrak | **Tidak dikirim ke exporter sama sekali** | Tidak |

---

## 4. Hasil export sungguhan — proyek 217

Data proyek:
- mulai 10/08/2026;
- akhir waktu kerja **Sabtu 19/09/2026** (41 hari);
- tambahan sampai **Senin 21/09/2026**;
- minggu berakhir Minggu.

Susunan minggunya:
- W6 = 14–20/09, minggu batas yang berisi hari tambahan Minggu 20/09;
- W7 = 21/09 saja, minggu tambahan.

Semua export dijalankan di container dalam `transaction.atomic()` lalu di-rollback.

| Export | Hasil | Temuan |
|---|---|---|
| Rekap PDF | OK, 8 halaman | Kolom W1–W7 lengkap. **Cover tanpa baris periode**. Tidak ada penanda batas kontrak |
| Rekap Excel | OK (Cover, Input Progress-Gantt, Kurva S) | Kolom W1–W7. **Anggaran di cover Rp 114,872,700 (jumlah harga, format en-US), sedangkan PDF Rp 127.500.000 (anggaran pemilik)** |
| Bulanan PDF (M1+M2) | OK, 12 halaman | Cover M2: "Periode: 07/09/2026 - 21/09/2026", jadi masa tambahan tercampur tanpa keterangan |
| Bulanan Excel (M2) | OK (Data Master, Rincian Progress M2, Kurva S M2) | Deviasi tertulis `2e-28` (sisa pembulatan float). Tidak ada penanda tambahan |
| Mingguan PDF (W6+W7) | OK, 6 halaman | Lihat catatan W7 di bawah tabel |
| Mingguan Excel (W7) | OK (Data Master, Rincian Progress W7) | **"Progress Minggu Ini: 0"**. Excel mingguan hanya memuat rencana, jadi realisasi 9,45% di minggu tambahan hilang |
| Harian Word, hari ke-1 | OK | Normal |
| Harian Word, minggu 6 | OK | **Hanya 14–19/09. Minggu 20/09 (hari tambahan di minggu batas) tidak ada** |
| Harian Word, minggu 7 | **GAGAL**: "Periode yang dipilih berada di luar masa proyek (10/08/2026 - 19/09/2026)" | Hari tambahan tidak bisa diekspor |

Catatan untuk Mingguan PDF W7:
- Cover: "Periode: 21/09/2026 - 21/09/2026". Ringkasan: Rencana 0,00%, Actual 9,45%, Akumulasi 100/100, Deviasi +0,00%.
- Tidak ada keterangan bahwa W7 minggu tambahan.
- Footer halaman cover W7 tertulis "Rincian Progress Minggu ke-6", yaitu judul halaman sebelumnya.

Batasan uji ini:
- Tanpa gambar dari browser, sehingga Kurva S dan Gantt versi gambar di PDF tidak ikut diuji.
- Tanpa klik lewat UI.

---

## 5. Temuan

### 5.1 Terkait Tambahan Waktu Kerja

| # | Temuan | Dampak | Bukti |
|---|---|---|---|
| X-1 | Laporan harian memakai `tanggal_selesai` sebagai batas akhir | Hari tambahan (tipe 1 dan tipe 2) tidak bisa dilaporkan; pilihan minggu 7 gagal | `export_manager.py:1284`, `:1376`; hasil §4 |
| X-2 | Batas kontrak tidak diteruskan ke exporter mana pun | Tidak ada garis, label, atau warna pembeda minggu tambahan di PDF/Excel | §3 |
| X-3 | Cover dan identitas tidak menyebut akhir waktu kerja maupun tambahan | Pembaca tidak tahu proyek sedang dalam masa tambahan | Cover Rekap tanpa periode; cover Bulanan/Mingguan hanya "Periode: a - b" |
| X-4 | Excel mingguan hanya rencana (kontrak doc 30 §8.3, "planned-only") | Di minggu tambahan isinya 0 walau ada realisasi; beda dengan PDF mingguan | Hasil §4 |
| X-5 | Rencana datar 100% dan deviasi di masa tambahan tanpa keterangan | Angkanya benar, tapi mudah disalahbaca | Kurva S W6–W7 = 100/100 |
| X-6 | `project_info.tanggal_selesai` = akhir tambahan, `durasi_hari` = durasi kontrak | Saat ini laten (tidak dicetak); akan salah begitu cover menampilkan tanggal | `jadwal_pekerjaan_adapter.py:1550-1552` |
| X-7 | Status "Ahead/On Track/Behind/Critical" dihitung dari deviasi periode. W7 = **"Ahead"** padahal proyek terlambat | Laten: bagian PDF yang mencetak status (`_build_executive_summary_section`) tidak dipanggil, Word bulanan/mingguan dimatikan | `jadwal_pekerjaan_adapter.py:1084-1088`; `pdf_exporter.py:3990` tanpa pemanggil |
| X-8 | Gantt di PDF Rekap digambar server dari `gantt_data` (state browser); Kurva S dari data server. Gambar Kurva S dari browser ikut dilampirkan | Perlu diperiksa apakah Kurva S muncul dua kali dan apakah kedua sumber sama. **Belum diverifikasi** | `pdf_exporter.py:1903`, `:2024`, `:2119-2130`; `jadwal_kegiatan_app.js:1466-1570` |

### 5.2 Inkonsistensi lain (bukan karena tambahan, ditemukan saat pemetaan)

| # | Temuan | Bukti |
|---|---|---|
| L-1 | Anggaran di cover Excel Rekap (jumlah harga, format en-US) ≠ PDF (anggaran pemilik, id-ID) | §4 |
| L-2 | Label bahasa Inggris di tabel dan Excel: "Week N", "Month N", "Actual", "On Track" | Adapter dan exporter |
| L-3 | Label bulan bisa melebihi jumlah minggu nyata ("W5-W8" untuk proyek 7 minggu) | `get_monthly_comparison_data` |
| L-4 | Footer halaman cover laporan mingguan kedua memakai judul halaman sebelumnya | §4, PDF mingguan hlm. 4 |
| L-5 | Sisa float `2e-28` pada Deviasi Excel bulanan | §4 |
| L-6 | `review 12_Export_System.md` masih berstatus "BELUM DIREVIEW" dan menyebut file yang sudah tidak menjadi jalur utama | Doc 12 |

---

## 6. Tes yang ada

| Area | Berkas | Jumlah tes |
|---|---|---|
| Laporan bulanan, periode, render PDF, pengesahan | `tests_jadwal_monthly_report.py` | 23 |
| Paritas nilai export (termasuk DOCX harian) | `tests_wp_export_parity.py` | 25 |
| Pengesahan | `tests_export_signature.py` | 13 |
| Akses, error, penamaan, identitas, paket, dll. | `tests_export_*.py` | ±90 |
| PNG Kurva S (skala, kualitas, paritas pratinjau) | `js/tests/kurva-s-png-*.test.js`, `canvas-export-scale.test.js` | — |

**Celah:** tidak ada tes export yang memakai proyek dengan `tanggal_akhir_tambahan`.

---

## 7. Status dokumen terkait

| Dokumen | Status | Catatan |
|---|---|---|
| Doc 30 (WP Export presisi & formula) | **Selesai 6/6** (2026-06-21), termasuk Jadwal 2C/2D | Catatan memori lama yang menyebut 2C belum selesai sudah usang |
| Doc 32 + registri desain R-1..R-37 | Berlaku | **Wajib dicek sebelum mengubah tampilan export**. Relevan: R-2, R-9, R-12, R-14, R-30, R-31, R-32, R-36, R-37 |
| `RENCANA_AUDIT_EXPORT_LAPORAN_HARIAN_XLSX.md` | Harian final = DOCX berbasis template | Template `export_templates/laporan_harian_template.docx` |
| Rancangan Tambahan §9 | Bahan awal fase export | Dokumen ini memperbarui dan membuktikan bahan tersebut |

---

## 8. Yang belum diperiksa

1. Tampilan PDF secara visual (dokumen ini memeriksa teks, bukan tata letak).
2. Gambar Kurva S dan Gantt yang dikirim browser ke PDF (X-8).
3. Alur lengkap lewat klik di UI (uji ini memanggil server langsung).
4. Mode harian "per bulan" di masa tambahan.
5. Proyek tambahan **tipe 1**, yaitu tambahan yang masih di dalam minggu batas. Proyek 217 adalah tipe 2, walau W6 juga memuat satu hari tambahan (20/09).

---

## 9. Keputusan owner (2026-09-30)

### 9.1 Lembar "Rangkuman Progress Akhir Waktu Kerja"

| # | Keputusan |
|---|---|
| K-1 | Nama baku: **Rangkuman Progress Akhir Waktu Kerja**. Lembar pemisah antara laporan progres masa kontrak dan laporan masa Penambahan Waktu Kerja |
| K-2 | Hanya **PDF dan Word**. Excel tidak memuat lembar ini |
| K-3 | Berlaku untuk laporan **bulanan, mingguan, dan harian**. Proyek tanpa tambahan tidak berubah |
| K-4 | Akumulasi yang ditampilkan = posisi **saat masa kontrak berakhir** (rencana, realisasi, deviasi). Data progres per minggu, jadi angkanya s.d. akhir minggu batas, dengan catatan kecil "progres dicatat per minggu; minggu batas dd/mm–dd/mm" |
| K-5 | Tabel pekerjaan yang **belum 100%** saat kontrak berakhir: No, Uraian, Bobot, Realisasi Kumulatif, Sisa, Sisa Bobot, **Keterangan** (kosong, diisi tangan) |
| K-6 | Halaman tersendiri, sebelum pengesahan. Di laporan harian, lembar ini tanpa pengesahan (pengesahan tetap per halaman harian, R-32) |
| K-7 | Muncul bila periode yang diekspor mencakup minggu/bulan batas atau periode sesudahnya |

### 9.2 Susunan dokumen menurut tipe tambahan

**Tipe 1 — tambahan tidak menambah minggu** (hanya memperpanjang minggu batas):

| Laporan | Susunan |
|---|---|
| Harian | [hari masa kontrak] **[Rangkuman]** [hari tambahan — laporan Penambahan Waktu Kerja] |
| Mingguan | [… minggu batas] **[Rangkuman]**. Tanpa laporan Penambahan Waktu Kerja terpisah |
| Bulanan | [… bulan yang memuat minggu batas] **[Rangkuman]**. Tanpa laporan Penambahan Waktu Kerja terpisah |

**Tipe 2 — tambahan menambah minggu baru:**

| Laporan | Susunan |
|---|---|
| Harian | [… hari akhir kontrak] **[Rangkuman]** [hari tambahan — Penambahan Waktu Kerja] |
| Mingguan | [… minggu batas] **[Rangkuman]** [minggu tambahan — Penambahan Waktu Kerja] |
| Bulanan | [… bulan batas] **[Rangkuman]** [bulan berikutnya — Penambahan Waktu Kerja], bila tambahan mencapai bulan baru |

**Laporan harian, semua tipe:** setiap hari **setelah akhir kontrak** masuk laporan Penambahan Waktu Kerja, termasuk hari tambahan yang masih berada di minggu batas (contoh 217: Minggu 20/09).

### 9.3 Keputusan lanjutan (2026-09-30)

| # | Hal | Keputusan owner |
|---|---|---|
| K-8 | Ekspor yang hanya berisi periode tambahan | Rangkuman diletakkan **di depan**, sebelum laporan Penambahan Waktu Kerja pertama |
| K-9 | Isi laporan masa Penambahan Waktu Kerja (harian, mingguan, bulanan) | **Sama dengan laporan normal**, tetap bersumber dari input progres. Yang berbeda **hanya teks** (penanda "Penambahan Waktu Kerja"). Tidak ada aturan daftar pekerjaan khusus, tidak ada kotak rencana khusus |
| K-10 | Cover/identitas (X-3) | **Tidak diubah.** Tidak ada baris Waktu Pelaksanaan/Penambahan di cover. X-6 tetap laten, dicatat saja |
| K-11 | Penanda minggu tambahan di tabel PDF/Excel (X-2) | **Samakan dengan web**: satu garis tebal di tepi kanan kolom minggu batas, label "Penambahan" di header kolom tambahan |
| K-12 | Excel mingguan (X-4) | **Tambahkan realisasi** |
| K-13 | Keterangan rencana 100%/deviasi/status (X-5, X-7) | **Tidak ada tambahan info.** Angka apa adanya |
| K-14 | Temuan L-1..L-6 | **Dikerjakan di fase ini** |

| K-15 | Teks penanda | **Hindari kata "terlambat/keterlambatan"** di semua hasil export. Penanda cukup **"Penambahan Waktu Kerja"** |
| K-16 | Pelaksana | **Codex eksekutor, Claude pengawas** (pola sama dengan doc 40/41) |

### 9.4 Masih terbuka

- Posisi teks penanda K-15: subjudul di bawah judul laporan (usulan, judul tetap) atau bagian dari judul. Diputuskan saat review rencana kerja.

---

## 10. Bahan diskusi awal (sebelum keputusan §9)

Keputusan owner yang dibutuhkan sebelum perubahan (belum diputuskan):

1. Bagaimana cover dan identitas menulis masa waktu kerja dan Penambahan Waktu Kerja (X-3, X-6).
2. Penanda minggu/bulan tambahan di tabel PDF dan Excel. Samakan dengan web: satu garis di tepi kolom minggu batas, label "Penambahan" (X-2).
3. Laporan harian di masa tambahan: batas akhir, dan daftar pekerjaan yang ditampilkan (X-1).
4. Excel mingguan: tetap hanya rencana, atau ditambah realisasi seperti PDF (X-4).
5. Keterangan rencana 100% dan deviasi di masa tambahan (X-5), serta status (X-7).
6. Apakah L-1..L-6 ikut dikerjakan di fase ini atau dicatat terpisah.
