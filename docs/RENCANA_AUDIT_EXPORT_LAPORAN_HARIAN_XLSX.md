# Rencana dan Audit Export Laporan Harian

Tanggal dokumen: 2026-06-27

## Update Audit Exporter Menyeluruh

Tanggal audit: 2026-06-28

Status fitur laporan harian saat audit:

- Format final laporan harian adalah **DOCX template-based**, bukan XLSX.
- Template wajib deploy: `detail_project/export_templates/laporan_harian_template.docx`.
- Output laporan harian sudah divalidasi dari host dan dari Docker untuk mode harian, mingguan, dan bulanan.
- File hasil Docker untuk `project_id=109`, mode `daily_mode=week`, `period=9` berhasil dibuka Microsoft Word dan tidak memiliki duplikasi ID/relasi SmartArt.

### Cakupan Exporter yang Diaudit

Area yang diperiksa:

- Endpoint export legacy di `detail_project/views_api.py`.
- Endpoint professional jadwal di `export_jadwal_pekerjaan_professional`.
- Koordinator export di `detail_project/exports/export_manager.py`.
- Exporter utama:
  - `csv_exporter.py`
  - `pdf_exporter.py`
  - `word_exporter.py`
  - `excel_exporter.py`
- Adapter jadwal dan identitas project:
  - `jadwal_pekerjaan_adapter.py`
  - `identity.py`
  - `signature_config.py`
- Frontend modal export:
  - `kelola_tahapan_grid_modern.html`
  - `jadwal_kegiatan_app.js`
- Async export task:
  - `detail_project/tasks.py`

Smoke test yang dijalankan pada `project_id=109`:

| Export | Format | Hasil |
| --- | --- | --- |
| Rekap RAB | XLSX | OK, ZIP valid |
| Volume Pekerjaan | XLSX | OK, ZIP valid |
| Harga Items | XLSX | OK, ZIP valid |
| Rincian AHSP | XLSX | OK, ZIP valid |
| Jadwal laporan harian | DOCX | OK, ZIP valid |
| Jadwal mingguan professional | XLSX | OK, ZIP valid |
| Jadwal bulanan professional | XLSX | OK, ZIP valid |
| Rekap RAB | PDF | OK, `%PDF-` valid |
| Volume Pekerjaan | PDF | OK, `%PDF-` valid |
| Jadwal mingguan professional | PDF | OK, `%PDF-` valid |

Catatan: smoke test ini memvalidasi struktur file dan respons dasar, belum menggantikan regression test otomatis.

### Temuan Audit Terbaru

#### E-01 - Regression test export DOCX harian belum ada

Severity: High

Status 2026-06-28: **Fixed**.

Masalah:

- Error Word sebelumnya disebabkan oleh duplikasi DrawingML/SmartArt relationship dan ID saat halaman dokumentasi dicopy.
- Perbaikan sudah ada di `word_exporter.py`, tetapi belum dikunci dengan test otomatis.
- Risiko regresi tinggi karena template DOCX boleh diedit manual dan generator melakukan manipulasi package/XML DOCX.

Dampak:

- Perubahan kecil pada template atau helper copy dokumentasi bisa membuat file kembali tidak bisa dibuka Word.

Rekomendasi:

- Tambahkan test backend untuk `daily_mode=day/week/month`.
- Test minimal harus membuka DOCX sebagai ZIP dan memeriksa:
  - `word/document.xml` tersedia.
  - tidak ada duplikasi `wp:docPr/@id`.
  - tidak ada duplikasi `wp14:anchorId`.
  - tidak ada duplikasi `wp14:editId`.
  - tidak ada duplikasi `dgm:relIds` untuk SmartArt.
  - `[Content_Types].xml` memuat override diagram part yang dicopy.

Implementasi:

- Test regresi `JadwalDailyDocxExportTests` memvalidasi template deploy, output DOCX month mode, filename range, ZIP package, dan uniqueness DrawingML/SmartArt IDs.
- Boundary test memastikan laporan harian tidak bisa diexport sebagai XLSX.

#### E-02 - Jalur Word export belum punya kontrak produk yang konsisten

Severity: High

Status 2026-06-28: **Policy fixed**.

Masalah:

- Laporan harian memakai DOCX dan sudah aktif.
- Jalur professional jadwal menolak Word untuk report selain `daily` dengan pesan `Word export is currently disabled`.
- Namun endpoint legacy Word masih tersedia untuk beberapa tipe laporan, termasuk `export_jadwal_pekerjaan_word`, `export_rekap_rab_word`, `export_volume_pekerjaan_word`, dan lainnya.
- UI saat ini diarahkan agar Word aktif hanya untuk laporan harian, tetapi backend masih menyisakan beberapa endpoint Word legacy.

Dampak:

- User atau integrasi lama bisa memanggil endpoint Word yang tidak sejalan dengan keputusan produk.
- Dokumentasi produk bisa membingungkan: “Word tersedia” untuk sebagian route, tetapi “Word disabled” di jalur professional.

Rekomendasi:

- Tetapkan policy final:
  - Opsi A: Word hanya untuk laporan harian. Endpoint Word legacy diberi respons 400/410 yang eksplisit atau disembunyikan total dari route aktif.
  - Opsi B: Word tetap didukung untuk semua modul yang legacy-nya stabil, tetapi professional jadwal selain daily tetap ditolak.
- Setelah policy dipilih, update UI, endpoint, tests, dan dokumentasi agar konsisten.

Keputusan:

- Dipilih Opsi B.
- Word legacy tetap didukung untuk modul non-jadwal yang sudah memiliki exporter stabil: Rekap RAB, Rekap Kebutuhan, Volume Pekerjaan, Harga Items, dan Rincian AHSP.
- Jadwal professional Word tetap hanya aktif untuk `report_type='daily'`.
- Jadwal professional non-harian tetap memakai PDF/XLSX; Word non-harian professional ditolak eksplisit oleh `ExportManager`.

#### E-03 - Async export task belum sinkron dengan format export saat ini

Severity: Medium-High

Status 2026-06-28: **Fixed untuk async legacy; intentionally not expanded ke daily professional**.

Masalah:

- `detail_project/tasks.py` hanya menerima format `pdf` dan `word`.
- Task ini belum mengenal XLSX dan belum mengenal laporan harian DOCX professional.
- Nama file async juga masih dibentuk manual berdasarkan `export_type_normalized`, `project_id`, dan timestamp, bukan memakai naming convention terbaru.

Dampak:

- Jika async export dipakai kembali, perilakunya akan berbeda dari export UI modern.
- Laporan harian tidak punya jalur async yang setara.
- XLSX export modern tidak tercakup async.

Rekomendasi:

- Audit apakah async export masih digunakan.
- Jika tidak digunakan, tandai deprecated atau hapus dari UI/route.
- Jika masih digunakan, refactor agar memakai kontrak export modern:
  - `report_type`
  - `format`
  - `daily_mode`
  - `period/months/weeks/days`
  - naming response dari exporter.

Implementasi:

- Async export masih digunakan oleh beberapa halaman legacy untuk PDF/Word berat, sehingga tidak dihapus.
- `generate_export_async()` sekarang meneruskan `options` ke manager:
  - `volume-pekerjaan`: `parameters`
  - `rincian-ahsp`: `orientation`
  - `rekap-kebutuhan`: `mode`, `tahapan_id`, `filters`, `search`, `time_scope`, `unit_mode`
  - `jadwal-pekerjaan`: `attachments`, `parameters`
- Async download memakai `download_filename` dari `Content-Disposition` exporter jika tersedia.
- Laporan harian DOCX professional tetap memakai jalur direct export karena output multi-hari sudah berhasil dan tidak membutuhkan Celery pada kondisi saat ini.

#### E-04 - Logging exporter masih memakai `print()` debug dalam jumlah besar

Severity: Medium

Status 2026-06-28: **Fixed untuk jalur exporter utama**.

Masalah:

- `excel_exporter.py`, `export_manager.py`, `word_exporter.py`, dan `jadwal_pekerjaan_adapter.py` masih menulis banyak `print()`.
- Smoke test mingguan/bulanan XLSX menghasilkan banyak log debug detail, termasuk contoh row dan map progress.

Dampak:

- Log Docker/production menjadi berisik.
- Informasi data proyek bisa bocor ke stdout log.
- Debug output menyulitkan observability saat export gagal.

Rekomendasi:

- Ganti `print()` dengan `logger.debug()` atau `logger.info()` secukupnya.
- Hapus debug data detail seperti sample row, planned map keys, dan harga pekerjaan dari log default.
- Pertahankan timing ringkas hanya pada debug level.

Implementasi:

- `export_manager.py`, `excel_exporter.py`, `word_exporter.py`, dan `jadwal_pekerjaan_adapter.py` sudah memakai module logger.
- Timing/detail debug hanya muncul jika level logging mengaktifkan `DEBUG`.
- Ringkasan export selesai memakai `logger.info()`.

#### E-05 - Filename export belum konsisten antar tipe laporan

Severity: Medium

Masalah:

- Naming canonical di `naming.py` saat ini menghasilkan `NamaProject_YYYY-MM-DD.ext`.
- Laporan harian DOCX sengaja memakai nama berbasis rentang isi laporan, misalnya `Laporan Harian 02-03 - 08-03.docx`.
- JSON export dan beberapa endpoint lain masih membentuk filename sendiri.

Dampak:

- User mendapatkan pola nama file berbeda antar export.
- Sulit mencari file berdasarkan jenis laporan jika semua file non-harian hanya memakai nama project dan tanggal export.

Rekomendasi:

- Tetapkan policy filename baru:
  - Laporan periodik: sertakan jenis laporan dan periode isi.
  - Export data/backup JSON: sertakan jenis paket dan timestamp.
  - Export umum: minimal `NamaProject_JenisLaporan_YYYY-MM-DD.ext`.
- Update `naming.py` agar mendukung policy ini secara terpusat, bukan masing-masing exporter membentuk sendiri.

#### E-06 - `excel_exporter.py` terlalu besar dan memegang terlalu banyak tanggung jawab

Severity: Medium

Masalah:

- `excel_exporter.py` sudah sangat besar dan memuat banyak jalur:
  - export umum,
  - rekap professional,
  - monthly professional,
  - weekly professional,
  - daily XLSX legacy/WIP,
  - SSOT sheet,
  - chart sheet,
  - formula/control sheet.

Dampak:

- Risiko regresi tinggi saat memperbaiki satu tipe laporan.
- Sulit menambah test fokus per tipe laporan.
- Debug/performance tuning menjadi lebih sulit.

Rekomendasi:

- Pecah bertahap menjadi modul lebih kecil, misalnya:
  - `excel/jadwal_rekap.py`
  - `excel/jadwal_monthly.py`
  - `excel/jadwal_weekly.py`
  - `excel/common_ssot.py`
  - `excel/volume.py`
  - `excel/rincian_ahsp.py`
- Jangan refactor sekaligus; lakukan setelah regression test dasar tersedia.

#### E-07 - Daily XLSX WIP masih ada di `excel_exporter.py`

Severity: Medium

Status 2026-06-28: **Partially fixed**.

Masalah:

- Keputusan final laporan harian adalah DOCX.
- Namun `excel_exporter.py` masih memiliki `export_daily_professional` dan `_build_daily_rincian_sheet`.
- `ExportManager.export_jadwal_professional` juga masih memiliki branch `format_type == 'xlsx' and report_type == 'daily'`, meskipun endpoint menolak daily selain Word.

Dampak:

- Membingungkan maintainer.
- Berpotensi aktif kembali tanpa sengaja jika validasi endpoint berubah.

Rekomendasi:

- Hapus jalur daily XLSX yang tidak lagi dipakai, atau beri komentar/deprecation eksplisit dan test bahwa endpoint daily XLSX ditolak.
- Prioritas penghapusan setelah DOCX regression test tersedia.

Implementasi:

- Boundary `ExportManager.export_jadwal_professional()` sekarang menolak `report_type='daily'` jika format bukan `word`.
- Test regresi memastikan daily XLSX ditolak di boundary manager.
- Kode daily XLSX lama di `excel_exporter.py` belum dihapus total agar tidak memperbesar blast radius refactor Excel; statusnya tidak lagi reachable dari flow resmi.

#### E-08 - Validasi periode export masih tersebar

Severity: Medium

Masalah:

- Validasi `months`, `weeks`, `days`, `period`, dan `daily_mode` dilakukan di view dan sebagian lagi di manager/helper.
- Beberapa jalur menggunakan array (`months`, `weeks`), beberapa fallback ke `period`.

Dampak:

- Risiko mismatch antara UI dan backend.
- Edge case periode di luar durasi proyek lebih sulit diuji.

Rekomendasi:

- Buat helper kontrak periode terpusat untuk jadwal:
  - `resolve_report_period(report_type, daily_mode, period, weeks, months, days, project_start, project_end)`.
- Helper mengembalikan objek periode final dan pesan error validasi.
- Pakai helper yang sama untuk PDF/XLSX/DOCX.

#### E-09 - Dependensi template DOCX belum masuk checklist deployment/CI

Severity: Medium

Status 2026-06-28: **Fixed untuk guard otomatis; tetap perlu checklist deploy**.

Masalah:

- Laporan harian membutuhkan `detail_project/export_templates/laporan_harian_template.docx`.
- Jika file tidak ikut image/server, export fallback ke placeholder sederhana dan hasil tidak sesuai desain.

Dampak:

- Production bisa terlihat “berhasil export” tetapi layout dokumentasi salah.

Rekomendasi:

- Tambahkan test existence template.
- Tambahkan checklist deployment bahwa folder `detail_project/export_templates/` harus ikut build.
- Jika template tidak ada di production, pertimbangkan fail-fast dengan error jelas, bukan fallback diam-diam.

Implementasi:

- Template source berada di `detail_project/export_templates/laporan_harian_template.docx`.
- Test regresi memeriksa template ada, valid sebagai paket DOCX, dan memiliki `word/document.xml`.
- Catatan deploy: folder `detail_project/export_templates/` wajib ikut artifact/image production.

#### E-10 - Error response file export belum selalu aman untuk frontend download

Severity: Medium

Status 2026-06-28: **Fixed pada jalur frontend export utama dan report professional langsung**.

Masalah:

- Frontend melakukan download blob setelah response dianggap OK pada beberapa jalur.
- Jika backend mengembalikan error JSON/HTML tetapi status tidak ditangani konsisten, user bisa mendapat file yang extension-nya terlihat benar tetapi isinya error.

Dampak:

- Gejala user: file “berhasil didownload” tetapi tidak bisa dibuka.
- Ini mirip pola error lama meskipun penyebabnya bisa berbeda dari korupsi DOCX.

Rekomendasi:

- Frontend wajib cek:
  - `response.ok`
  - `Content-Type` sesuai format.
  - untuk DOCX/XLSX, byte awal `PK` opsional sebagai guard tambahan.
  - untuk PDF, byte awal `%PDF-` opsional.
- Jika bukan file valid, tampilkan error message dari JSON/text dan jangan auto-download.

Implementasi:

- `jadwal_kegiatan_app.js` memvalidasi MIME dan signature file untuk PDF/DOCX/XLSX sebelum download.
- `ExportManager.js` global memvalidasi jalur sync dan async sebelum download.
- `weekly-report.js`, `monthly-report.js`, dan `rekap-report.js` memvalidasi response backend yang langsung menghasilkan blob.
- Jika response adalah JSON/HTML error, UI melempar error dan tidak membuat file download palsu.

### Rencana Perbaikan Prioritas

| Prioritas | Item | Tujuan |
| --- | --- | --- |
| P0 | Tambah regression test DOCX harian SmartArt | Selesai, menutup regresi Word error |
| P0 | Pastikan template DOCX ikut CI/deploy | Selesai untuk test existence; deploy checklist tetap wajib |
| P1 | Frontend content-type/file-signature guard | Selesai pada jalur export utama |
| P1 | Bersihkan `print()` exporter menjadi logger | Selesai pada exporter utama |
| P1 | Putuskan policy Word legacy | Selesai, Word legacy non-jadwal tetap didukung |
| P2 | Refactor kontrak periode jadwal | Mengurangi mismatch day/week/month |
| P2 | Pecah `excel_exporter.py` bertahap | Mengurangi risiko regresi jangka panjang |
| P2 | Evaluasi async export lama | Selesai, async legacy disinkronkan untuk options utama |

### Status Kesiapan Launch Export

Kesiapan saat ini: **siap untuk QA akhir/pilot**, dengan sisa pekerjaan yang bersifat refactor jangka menengah.

Yang sudah stabil:

- Export harian DOCX dari Docker setelah restart.
- Template dokumentasi SmartArt dapat dipertahankan.
- Export PDF/XLSX utama lulus smoke test struktur file.
- Identitas project dan tanda tangan laporan harian sudah mengambil data dashboard.
- Word legacy non-jadwal tetap didukung dengan policy eksplisit.
- Async export legacy tetap aktif dan sudah meneruskan options utama ke exporter sync.

Yang belum ideal untuk launch penuh:

- `excel_exporter.py` masih besar dan sebaiknya dipecah bertahap setelah regression coverage makin lengkap.
- Helper validasi periode masih tersebar dan layak disatukan pada refactor berikutnya.

## Keputusan Final Implementasi

Setelah evaluasi placeholder foto Excel/SmartArt, format laporan harian dialihkan dari **XLSX-only** menjadi **DOCX template-based**.

Alasan perubahan:

- Kebutuhan utama adalah dokumen lapangan siap print A4 dengan placeholder foto yang stabil dan mudah diisi manual.
- SmartArt/diagram di XLSX rawan hilang saat file diproses ulang dengan `openpyxl`.
- DOCX template memberi peluang lebih baik untuk mempertahankan blok dokumentasi yang dibuat manual di Microsoft Word.
- Server tidak perlu menjalankan Word/Excel automation; generator cukup memakai `python-docx` dan menyalin blok dokumentasi dari template.

Output final:

| Mode | Input user | Output |
| --- | --- | --- |
| Harian | Pilih 1 hari | 1 file DOCX berisi halaman pekerjaan dan halaman dokumentasi |
| Mingguan | Pilih minggu tertentu | 1 file DOCX berisi rangkaian laporan harian dalam minggu tersebut |
| Bulanan | Pilih periode bulan ke-n | 1 file DOCX berisi rangkaian laporan harian untuk 4 minggu |

Aturan halaman:

- Setiap tanggal memakai heading native Word agar muncul di Navigation Pane.
- Halaman pekerjaan dapat dipaginasi menjadi `01 JAN - Pekerjaan 1`, `01 JAN - Pekerjaan 2`, dst.
- Halaman dokumentasi ditempatkan setelah seluruh halaman pekerjaan tanggal tersebut.
- Tabel tanda tangan hanya muncul pada halaman pekerjaan terakhir untuk tanggal tersebut.
- Blok dokumentasi dicopy dari template DOCX agar SmartArt/diagram/template visual tidak dibuat ulang dari kode.

Template implementasi saat ini:

```text
detail_project/export_templates/laporan_harian_template.docx
```

Catatan: bagian di bawah ini tetap menyimpan audit awal XLSX sebagai riwayat keputusan dan pembanding teknis.

## Tujuan

Menambahkan fitur export **Laporan Harian** pada halaman Jadwal Pekerjaan. Laporan ini bukan laporan progres detail, bukan rekap kebutuhan, dan bukan laporan biaya. Fokusnya adalah dokumen lapangan harian yang memuat identitas proyek, status progres minggu sebelumnya, daftar pekerjaan yang dijadwalkan pada tanggal laporan, area dokumentasi foto manual, dan keterangan manual.

Fitur ini harus memanfaatkan pola export jadwal yang sudah ada untuk laporan mingguan dan bulanan, tetapi menggunakan template harian yang lebih sederhana dan sesuai kebutuhan lapangan.

## Ruang Lingkup yang Disepakati

### Format

- Format output hanya `.xlsx`.
- PDF dan Word tidak disediakan untuk laporan harian.
- Sistem menghasilkan workbook Excel, lalu user mengisi bagian manual langsung di file tersebut.

### Mode Export

User dapat export laporan harian dalam tiga mode:

| Mode | Input user | Output |
| --- | --- | --- |
| Harian | Pilih 1 tanggal/hari | 1 file XLSX dengan 1 sheet laporan harian |
| Mingguan | Pilih minggu tertentu | 1 file XLSX berisi sheet harian untuk hari-hari dalam minggu tersebut |
| Bulanan | Pilih periode bulan ke-n | 1 file XLSX berisi sheet harian untuk 4 minggu pada periode tersebut |

Definisi bulanan mengikuti sistem saat ini:

- Bulan 1 = Minggu 1-4
- Bulan 2 = Minggu 5-8
- Bulan 3 = Minggu 9-12
- dst.

### Penamaan Sheet

Nama sheet mengikuti format:

```text
01 JAN
02 JAN
03 JAN
...
```

Aturan teknis:

- Format tanggal memakai `DD MMM` dengan bulan 3 huruf uppercase.
- Nama sheet harus aman untuk Excel dan maksimal 31 karakter.
- Jika ada tanggal duplikat lintas tahun atau konflik nama sheet, tambahkan suffix pendek, misalnya `01 JAN (2)`.

### Print Setup

Setiap sheet laporan harian harus siap print sebagai **A4 portrait**.

Aturan print:

- Paper size: A4.
- Orientation: portrait.
- Print area eksplisit untuk seluruh layout laporan harian.
- Horizontal centered.
- Fit to 1 page wide dan 1 page tall jika layout final ditargetkan satu lembar.
- Template harus diuji melalui print preview Excel/LibreOffice, bukan hanya validasi `openpyxl`.

## Isi Tiap Sheet Laporan Harian

### 1. Identitas Proyek

Field otomatis dari data proyek:

- Nama proyek
- Lokasi proyek
- Nomor kontrak / kode proyek
- Tanggal laporan
- Nama kontraktor
- Konsultan pengawas
- Owner / instansi

Field manual/editable:

- Cuaca pagi
- Cuaca siang
- Cuaca sore

### 2. Progress Minggu Sebelumnya

Tidak perlu ringkasan progress harian. Cukup tampilkan:

- Progress rencana minggu sebelumnya
- Progress realisasi minggu sebelumnya
- Deviasi minggu sebelumnya

Untuk hari pada Minggu 1, nilai minggu sebelumnya dapat diisi `0.00%` atau `-`, dengan keputusan final disarankan memakai `-` agar tidak terlihat sebagai data aktual.

### 3. Pekerjaan yang Dilaksanakan Hari Ini

Tabel sederhana:

| No | Uraian pekerjaan | Lokasi / area | Keterangan |
| --- | --- | --- | --- |

Catatan:

- Daftar pekerjaan diambil dari data Grid View / jadwal untuk minggu tempat tanggal laporan berada.
- Karena penyimpanan progress saat ini berbasis mingguan, daftar pekerjaan untuk 7 hari dalam minggu yang sama kemungkinan sama.
- Tidak memuat volume, bobot, progress, harga, tenaga kerja, material, atau peralatan.
- Kolom `Lokasi / area` dan `Keterangan` dapat dibuat manual/editable.

### 4. Dokumentasi

Bagian dokumentasi adalah elemen penting.

Template XLSX harus menyediakan placeholder foto manual, mengikuti inspirasi dari:

```text
AHSP Document/Sample Laporan Harian.xlsx
```

Hasil inspeksi file contoh:

- File berisi 1 sheet bernama `47`.
- Layout utama berupa dokumen dokumentasi pengawasan kegiatan.
- Terdapat beberapa blok berulang dengan label pekerjaan/kegiatan/kondisi/lokasi.
- Tidak ada image tertanam saat inspeksi, sehingga area foto kemungkinan berupa ruang layout/placeholder untuk input manual.
- File memiliki drawing part `xl/drawings/drawing1.xml`.
- File memiliki diagram/SmartArt parts di `xl/diagrams/`.
- Placeholder dokumentasi pada referensi bukan sekadar merged cell; ada drawing/SmartArt yang membantu area gambar tetap stabil pada printout.

Temuan teknis penting:

- Membuka dan menyimpan ulang file referensi dengan `openpyxl` menghapus drawing dan SmartArt parts.
- Karena itu, implementasi final tidak boleh mengisi template SmartArt dengan pola `openpyxl.load_workbook(...).save(...)` biasa jika ingin mempertahankan placeholder SmartArt.
- Jika placeholder SmartArt wajib dipertahankan, implementasi harus memakai strategi yang menjaga part XLSX asli, misalnya manipulasi package/XML XLSX secara hati-hati atau automation Excel di environment yang mendukung.

Rancangan baru sebaiknya menyediakan placeholder foto yang lebih sesuai laporan harian:

- Foto 1 + caption/keterangan
- Foto 2 + caption/keterangan
- Foto 3 + caption/keterangan
- Foto 4 + caption/keterangan

Foto tidak otomatis diambil dari sistem. User akan insert picture manual ke area yang disediakan.

### 5. Hambatan / Kendala / Keterangan

Field manual:

- Hambatan / kendala
- Catatan lapangan
- Tindak lanjut

### 6. Pengesahan

Area tanda tangan:

- Dibuat oleh
- Diperiksa oleh
- Disetujui oleh

Nama/jabatan dapat diisi otomatis jika sudah tersedia pada identitas proyek, tetapi tetap harus editable.

## Audit Kondisi Export Saat Ini

### Jalur Export Jadwal yang Ada

Export jadwal saat ini terdiri dari:

- UI modal export pada `detail_project/templates/detail_project/kelola_tahapan_grid_modern.html`.
- Handler frontend pada `detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js`.
- Endpoint backend `export_jadwal_pekerjaan_professional` pada `detail_project/views_api.py`.
- Koordinator export pada `detail_project/exports/export_manager.py`.
- Adapter data jadwal pada `detail_project/exports/jadwal_pekerjaan_adapter.py`.
- Generator Excel pada `detail_project/exports/excel_exporter.py`.

Endpoint professional saat ini sudah menangani laporan `rekap`, `monthly`, dan `weekly`. Export Excel bulanan dan mingguan memakai metode khusus:

- `ExcelExporter.export_monthly_professional`
- `ExcelExporter.export_weekly_professional`

Adapter jadwal sudah memiliki asumsi bulanan = 4 minggu, terlihat pada `get_monthly_comparison_data`.

### Kesiapan yang Mendukung Fitur

- Data jadwal/progress kanonik sudah tersedia dalam bentuk mingguan melalui `PekerjaanProgressWeekly`.
- Adapter sudah dapat menghasilkan:
  - daftar week columns,
  - base rows pekerjaan,
  - planned map,
  - actual map,
  - project identity.
- Export XLSX sudah memakai `openpyxl`, sehingga memungkinkan membuat workbook dengan banyak sheet dan placeholder layout.
- Export mingguan dan bulanan sudah punya pola multi-sheet dalam satu workbook.
- UI sudah punya konsep pemilihan minggu dan bulan, sehingga mode laporan harian dapat mengikuti pola yang sama.

### Kesenjangan untuk Laporan Harian

- Belum ada model/input harian murni. Data harian harus diturunkan dari minggu atau hanya digunakan untuk menentukan tanggal sheet.
- Belum ada storage untuk cuaca, kendala, caption foto, atau dokumentasi. Untuk fase awal, field tersebut harus manual/editable di Excel.
- Belum ada template XLSX khusus laporan harian yang formal dan sesuai spesifikasi final.
- Belum ada helper periode yang eksplisit menghasilkan daftar tanggal dari:
  - mode harian,
  - mode mingguan,
  - mode bulanan 4 minggu.
- Belum ada aturan final untuk pekerjaan aktif pada tanggal tertentu. Dengan data saat ini, aturan realistis adalah pekerjaan yang punya rencana/realisasi pada minggu terkait.

## Temuan Audit Relevan

### 1. Implementasi WIP `daily` yang ada saat ini belum sesuai desain final

Worktree saat audit menunjukkan perubahan WIP yang sudah menambahkan `report_type=daily` ke beberapa file. Implementasi itu dibuat sebelum spesifikasi ini disepakati dan belum sesuai kebutuhan final.

Masalah pada WIP tersebut:

- Masih membawa konsep progress harian detail.
- Menghitung progress harian dengan membagi nilai mingguan menjadi 7, padahal desain final hanya perlu progress minggu sebelumnya.
- Tabel pekerjaan masih membawa pola progress/bobot dari export mingguan, bukan tabel inti laporan harian.
- UI memilih banyak hari langsung, bukan mode `harian/mingguan/bulanan` yang sekarang disepakati.
- Belum memakai template yang dirancang dari `Sample Laporan Harian.xlsx`.
- Sheet name masih berbasis `D{nomor_hari}`, belum `01 JAN`.

Rekomendasi:

- Jangan lanjutkan WIP tersebut sebagai implementasi final.
- Rework atau revert bagian WIP daily, lalu implementasi ulang sesuai dokumen ini.

### 2. Endpoint professional terlalu generik untuk kebutuhan laporan harian

Endpoint `export_jadwal_pekerjaan_professional` saat ini menggabungkan kebutuhan rekap, bulanan, mingguan, attachment chart, dan format PDF/Word/XLSX. Menambahkan daily ke endpoint yang sama bisa dilakukan, tetapi perlu validasi ketat agar tidak ikut jalur chart/offscreen export.

Rekomendasi:

- Tetap boleh memakai endpoint yang sama untuk konsistensi, tetapi payload daily harus eksplisit:

```json
{
  "report_type": "daily",
  "format": "xlsx",
  "daily_mode": "day|week|month",
  "day": 12,
  "week": 3,
  "month": 2
}
```

- Backend yang menentukan tanggal/sheet yang valid, bukan frontend mengirim daftar tanggal bebas.

### 3. UI export saat ini mencampur mode report dan format

UI modal saat ini memilih jenis laporan (`full`, `monthly`, `weekly`) dan format (`pdf`, `xlsx`). Untuk laporan harian, yang dibutuhkan adalah sub-mode periode: harian, mingguan, bulanan.

Rekomendasi:

- Tambahkan report type `Laporan Harian`.
- Saat `Laporan Harian` dipilih:
  - format terkunci ke Excel,
  - tampilkan kontrol `Mode Periode`: Harian / Mingguan / Bulanan,
  - tampilkan input yang sesuai mode.

### 4. Bulanan di sistem adalah periode 4 minggu, bukan bulan kalender

Ini sudah konsisten dengan export bulanan saat ini. Namun nama `Bulanan` bisa disalahpahami sebagai bulan kalender.

Rekomendasi:

- Label UI: `Bulanan (4 Minggu)`.
- Preview: `Bulan 2: Minggu 5-8`.
- Dokumentasi tooltip menjelaskan bahwa ini periode sistem, bukan Januari/Februari kalender.

### 5. Kebutuhan performance perlu dibatasi

Mode bulanan dapat menghasilkan sampai 28 sheet. Dengan placeholder foto dan styling, workbook masih wajar, tetapi perlu batas.

Rekomendasi batas awal:

- Harian: 1 sheet.
- Mingguan: maksimal 7 sheet.
- Bulanan: maksimal 28 sheet.
- Tidak ada rentang bebas pada fase awal.

### 6. File lock Excel muncul di folder contoh

Terdapat file sementara:

```text
AHSP Document/~$Sample Laporan Harian.xlsx
```

Ini biasanya file lock dari Excel. File ini tidak boleh dipakai sebagai template dan sebaiknya tidak ikut commit.

## Rancangan Teknis

### Komponen Baru

Tambahkan modul khusus, misalnya:

```text
detail_project/exports/laporan_harian_adapter.py
detail_project/exports/laporan_harian_excel.py
```

Alasan:

- Menghindari `excel_exporter.py` makin besar.
- Memisahkan laporan harian yang berbasis template dari export jadwal profesional yang berbasis progress report.
- Memudahkan test khusus laporan harian.

### Adapter Laporan Harian

Tanggung jawab:

- Resolve identitas proyek.
- Resolve mode periode menjadi daftar tanggal.
- Resolve minggu untuk setiap tanggal.
- Ambil progress minggu sebelumnya.
- Ambil daftar pekerjaan aktif pada minggu terkait.
- Siapkan payload netral untuk exporter.

Contoh payload:

```python
{
    "project": {...},
    "sheets": [
        {
            "date": date(2026, 1, 1),
            "sheet_name": "01 JAN",
            "week_number": 1,
            "previous_week": None,
            "previous_progress": {
                "planned": None,
                "actual": None,
                "deviation": None,
            },
            "work_items": [
                {"no": 1, "uraian": "Pekerjaan A", "lokasi": "", "keterangan": ""},
            ],
        }
    ]
}
```

### Exporter Template XLSX

Tanggung jawab:

- Membuat workbook.
- Membuat satu sheet per tanggal.
- Menyalin struktur template untuk setiap sheet.
- Mengisi cell otomatis.
- Menyediakan placeholder manual untuk:
  - cuaca,
  - lokasi/area pekerjaan,
  - keterangan,
  - dokumentasi foto,
  - hambatan/kendala,
  - tanda tangan.

Untuk fase awal, template dapat dibuat secara programmatic dengan `openpyxl`. Setelah layout stabil, template file `.xlsx` bisa disimpan sebagai asset dan diisi via cell mapping.

### Resolusi Periode

Input backend yang disarankan:

```text
daily_mode = day | week | month
day_number = integer, jika daily_mode=day
week_number = integer, jika daily_mode=week
month_number = integer, jika daily_mode=month
```

Rules:

- `day`: tanggal = project_start + day_number - 1.
- `week`: tanggal = 7 hari pada week_number.
- `month`: week range = `((month_number - 1) * 4 + 1)` sampai `month_number * 4`, tanggal = semua hari dalam rentang minggu tersebut.
- Clamp tanggal ke durasi proyek agar tidak membuat sheet di luar proyek.

### Penentuan Pekerjaan Harian

Untuk tanggal tertentu:

1. Hitung `week_number`.
2. Ambil pekerjaan yang punya planned atau actual proportion pada minggu tersebut.
3. Jika kosong, fallback opsional:
   - tampilkan semua pekerjaan dengan kolom keterangan kosong, atau
   - tampilkan tabel kosong dengan pesan `Tidak ada pekerjaan terjadwal`.

Rekomendasi fase awal: tampilkan hanya pekerjaan yang punya nilai planned/actual pada minggu terkait. Ini menjaga laporan tetap relevan.

## Rencana Implementasi

### Fase 0 - Bersihkan WIP

- Rework/revert perubahan daily WIP yang belum sesuai desain.
- Pastikan bundle frontend kembali sinkron setelah perubahan final.
- Pastikan file lock `~$Sample Laporan Harian.xlsx` tidak ikut commit.

### Fase 1 - Kontrak Data dan Adapter

- Buat adapter laporan harian.
- Implement helper:
  - `resolve_daily_dates(project, mode, day/week/month)`.
  - `build_sheet_name(date, existing_names)`.
  - `get_previous_week_progress(project, week_number)`.
  - `get_work_items_for_week(project, week_number)`.

### Fase 2 - Template XLSX

- Buat exporter khusus laporan harian.
- Layout sheet:
  - identitas proyek,
  - cuaca,
  - progress minggu sebelumnya,
  - pekerjaan hari ini,
  - dokumentasi 4 placeholder,
  - hambatan/keterangan,
  - pengesahan.
- Gunakan sheet names `01 JAN`, dst.

### Fase 3 - Backend Endpoint

- Tambahkan route atau extend endpoint professional.
- Validasi:
  - format wajib `xlsx`,
  - mode wajib `day/week/month`,
  - nilai periode positif,
  - periode tidak melebihi durasi proyek.
- Return response XLSX dengan filename yang jelas:
  - `Laporan_Harian_01_JAN.xlsx`
  - `Laporan_Harian_Minggu_03.xlsx`
  - `Laporan_Harian_Bulan_02.xlsx`

### Fase 4 - UI

- Tambahkan pilihan `Laporan Harian`.
- Lock format ke Excel.
- Tampilkan mode periode:
  - Harian: pilih hari/tanggal.
  - Mingguan: pilih minggu ke.
  - Bulanan: pilih bulan/periode ke.
- Preview jumlah sheet yang akan dibuat.

### Fase 5 - Test

Test backend:

- Harian menghasilkan 1 sheet.
- Mingguan menghasilkan maksimal 7 sheet.
- Bulanan menghasilkan maksimal 28 sheet.
- Sheet names `DD MMM`.
- Minggu sebelumnya untuk minggu 1 menghasilkan nilai kosong/`-`.
- Pekerjaan yang muncul sesuai weekly progress.
- Format selain XLSX ditolak.

Test frontend:

- Format PDF/Word tidak bisa dipilih untuk laporan harian.
- Payload sesuai mode.
- Preview jumlah sheet benar.

Manual QA:

- Buka file XLSX di Excel/LibreOffice.
- Insert gambar manual pada placeholder.
- Cek print layout.
- Cek panjang nama pekerjaan tidak merusak layout.

## Keputusan yang Masih Perlu Dikonfirmasi

- Jumlah placeholder foto final: rekomendasi 4.
- Untuk minggu pertama, progress minggu sebelumnya ditampilkan `-` atau `0.00%`.
- Jika tidak ada pekerjaan pada minggu tertentu, tabel kosong atau fallback semua pekerjaan.
- Apakah template final dibuat programmatic dulu atau memakai file `.xlsx` template fisik sejak awal.

## Rekomendasi Akhir

Fitur siap secara fondasi karena export jadwal, adapter mingguan/bulanan, dan Excel generator sudah ada. Namun implementasi harian sebaiknya dibuat sebagai jalur khusus yang lebih sederhana, bukan menumpang penuh pada struktur laporan progress mingguan/bulanan.

Prioritas berikutnya adalah menyepakati layout template final, lalu membuat adapter dan exporter khusus laporan harian berdasarkan spesifikasi ini.
