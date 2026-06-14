# Audit Komprehensif Page Jadwal Pekerjaan

**Tanggal audit:** 13 Juni 2026  
**Target:** `/detail_project/<project_id>/jadwal-pekerjaan/`  
**Objek:** current working tree pada saat audit  
**Status:** **BELUM PRODUCTION-READY - fondasi SSOT sudah benar, tetapi masih ada risiko partial save, pergeseran periode minggu, error loading yang tersamarkan, dan export dengan sumber data campuran**

## 1. Ringkasan Eksekutif

Page Jadwal Pekerjaan adalah sumber distribusi waktu untuk:

- progres rencana;
- progres realisasi;
- volume per minggu;
- biaya aktual per minggu;
- Grid, Gantt, dan Kurva S;
- laporan mingguan/bulanan;
- Rekap Kebutuhan per periode.

Fondasi arsitekturnya sudah baik:

- `PekerjaanProgressWeekly` ditetapkan sebagai storage mingguan kanonik;
- rencana dan realisasi disimpan terpisah;
- pergantian Grid/Gantt/Kurva S memakai state yang sama;
- mode bulanan diturunkan dari data mingguan, bukan menjadi storage baru;
- pergantian mode tidak menghapus data mingguan;
- total progres divalidasi maksimum 100%;
- endpoint utama owner-scoped dan memakai transaksi;
- tersedia guard ketika meninggalkan halaman, konfirmasi refresh/reset, skeleton, empty state, status `aria-live`, responsive toolbar, dan reduced-motion support;
- export profesional telah mendukung rekap, multi-minggu, dan multi-periode.

Masalah terpenting:

1. Payload yang berisi sebagian baris valid dan sebagian invalid dapat menyimpan baris valid, lalu mengembalikan HTTP 400 tanpa sinkronisasi view layer dan cache invalidation.
2. Fallback tanggal pada save selalu memakai Minggu sebagai batas akhir, walaupun project memilih batas minggu lain.
3. Perubahan batas minggu diterapkan dan disimpan sebelum konfirmasi pembuangan perubahan yang belum disimpan.
4. Kegagalan load assignment disamarkan sebagai jadwal kosong.
5. Export dapat menggabungkan chart dari state browser yang belum disimpan dengan tabel dari database.
6. Reset realisasi mengosongkan persentase, tetapi membiarkan `actual_cost`.
7. Definisi “Bulanan” saat ini adalah setiap empat minggu, bukan bulan kalender.
8. Tidak ada proteksi konflik edit antartab/perangkat.

## 2. Scope Audit

Audit mencakup:

- route, view, template, dan ownership;
- model dan SSOT progres;
- load, edit, validasi, save, refresh, reset;
- mode Rencana dan Realisasi;
- mode Persentase, Volume, dan Biaya;
- skala Mingguan dan Bulanan;
- Grid, Gantt, dan Kurva S;
- perubahan hari awal/akhir minggu;
- export PDF, XLSX, JSON, rekap, mingguan, dan bulanan;
- loading, empty state, error state, keyboard/accessibility, dan responsive behavior;
- hubungan ke Volume Pekerjaan, Harga Items, Rekap RAB, dan Rekap Kebutuhan;
- test coverage dan maintainability.

Tidak dilakukan perubahan source aplikasi pada audit ini.

## 3. Kontrak Produk dan SSOT

### 3.1 Storage kanonik

Kontrak yang direkomendasikan:

```text
PekerjaanProgressWeekly
  = SSOT distribusi waktu per pekerjaan

planned_proportion
  = progres rencana pekerjaan pada minggu tersebut

actual_proportion
  = progres realisasi pekerjaan pada minggu tersebut

actual_cost
  = biaya aktual pekerjaan pada minggu tersebut

PekerjaanTahapan
  = projection/view compatibility, bukan sumber utama
```

**Keputusan diskusi 14 Juni 2026: DISETUJUI.**

- `PekerjaanProgressWeekly` ditetapkan sebagai SSOT tunggal progres jadwal.
- `PekerjaanTahapan` dianggap sebagai projection legacy dari implementasi sebelumnya.
- Fitur baru dan perhitungan lintas-page tidak boleh menjadikan `PekerjaanTahapan`
  sebagai sumber progres.
- Penghapusan `PekerjaanTahapan` tidak dilakukan langsung. Ketergantungan lama
  dipetakan dan dimigrasikan bertahap terlebih dahulu.
- Selama masa transisi, sinkronisasi ke `PekerjaanTahapan` hanya berfungsi sebagai
  compatibility layer dan harus dapat dibangun ulang dari weekly SSOT.

Total tiap mode untuk satu pekerjaan:

```text
0 <= SUM(proportion_week) <= 100
```

Konversi tampilan:

```text
weekly_volume = volume_pekerjaan x weekly_proportion / 100
```

Kurva S berbobot:

```text
weekly_project_weight =
  SUM(nilai_pekerjaan x weekly_proportion / 100)
  / SUM(nilai_seluruh_pekerjaan)
```

### 3.2 Hubungan dengan page lain

- **Volume Pekerjaan:** kapasitas fisik yang didistribusikan.
- **Harga Items/Rincian AHSP/Rekap RAB:** menyediakan nilai/bobot pekerjaan.
- **Rekap Kebutuhan:** wajib membaca `planned_proportion` mingguan untuk kebutuhan rencana per periode.
- **Biaya Rencana:** bentuk input/tampilan dari `planned_proportion` berdasarkan
  nilai pekerjaan.
- **Volume Realisasi:** bentuk input/tampilan dari `actual_proportion` berdasarkan
  volume pekerjaan.

## 4. Matriks Mode

| Dimensi | Mode | Hasil audit |
|---|---|---|
| Progress | Rencana | Didukung dan state terpisah |
| Progress | Realisasi | Didukung, termasuk biaya aktual |
| Nilai | Persentase Rencana | Input langsung ke `planned_proportion` |
| Nilai | Biaya Rencana | Input alternatif Rencana, dikonversi menjadi persentase |
| Nilai | Persentase Realisasi | Input langsung ke `actual_proportion` |
| Nilai | Volume Realisasi | Input alternatif Realisasi, dikonversi menjadi persentase |
| Waktu | Mingguan | Storage dan skala kanonik |
| Waktu | Bulanan | Read-only, agregasi empat minggu |
| Visual | Grid | Mode input utama |
| Visual | Gantt | Projection dari state yang sama |
| Visual | Kurva S | Projection progres berbobot |
| Export | Rekap | Planned, actual, Gantt, Kurva S |
| Export | Mingguan | Single dan multi-week |
| Export | Bulanan | Single dan multi-period empat mingguan |

## 5. Temuan Backend, Data, dan SSOT

### JDW-01 - TINGGI - Partial save dapat terjadi walaupun response menyatakan gagal

Lokasi:

- `detail_project/views_api_tahapan_v2.py:46`
- `detail_project/views_api_tahapan_v2.py:373`

Endpoint menyimpan setiap item valid sambil mengumpulkan error item invalid. Jika ada `errors`, endpoint mengembalikan HTTP 400, tetapi tidak melakukan rollback.

Dampak:

- user melihat “gagal menyimpan”;
- sebagian nilai sebenarnya sudah berubah di database;
- sinkronisasi `PekerjaanTahapan` tidak dijalankan;
- cache tidak dihapus;
- browser tetap menganggap nilai belum tersimpan;
- save ulang dapat menghasilkan keadaan yang sulit dipahami.

Rekomendasi:

- jadikan operasi all-or-nothing;
- validasi seluruh payload sebelum write;
- jika ada satu error, rollback seluruh payload;
- response harus menunjukkan pekerjaan, minggu, field, dan penyebab error.

**Keputusan diskusi 14 Juni 2026: DISETUJUI.**

Penyimpanan satu aksi user harus atomik:

```text
Semua perubahan valid   -> seluruh perubahan disimpan
Ada perubahan invalid   -> seluruh perubahan dibatalkan
```

Informasi kegagalan wajib menampilkan:

- kode dan uraian pekerjaan;
- mode yang sedang disimpan: Rencana atau Realisasi;
- minggu/periode dan rentang tanggal;
- nilai yang dimasukkan;
- total sebelum dan sesudah input;
- alasan kegagalan;
- nilai maksimum atau kapasitas yang masih dapat dimasukkan;
- penegasan bahwa tidak ada perubahan dalam batch tersebut yang disimpan.

Contoh feedback:

```text
Pekerjaan : Pemasangan Beton
Mode      : Rencana
Periode   : Minggu 5 (1-7 Juli 2026)
Input     : 35%
Masalah   : Total progres menjadi 115%
Tersedia  : Maksimum 20%
Status    : Seluruh perubahan pada penyimpanan ini dibatalkan
```

UI harus menandai sel/baris sumber masalah dan mempertahankan input user agar
dapat diperbaiki tanpa mengetik ulang seluruh batch.

### JDW-02 - TINGGI - Save fallback mengabaikan batas minggu project

Lokasi:

- `detail_project/views_api_tahapan_v2.py:217`
- `detail_project/views_api_tahapan_v2.py:224`

Payload sudah mengirim `week_end_day`, tetapi fallback `get_week_date_range()` selalu memakai `week_end_day=6`.

Dampak:

- project dengan batas minggu selain Minggu dapat menyimpan tanggal minggu yang berbeda dari header UI;
- Rekap Kebutuhan per periode dapat memasukkan data ke periode yang salah;
- export dan API dapat menampilkan rentang berbeda.

Rekomendasi:

- gunakan nilai project yang telah dinormalisasi;
- jangan percaya payload sebagai sumber utama jika preferensi sudah tersimpan di project;
- tambahkan test untuk Sen-Min, Sab-Jum, dan boundary lintas bulan/tahun.

### JDW-03 - TINGGI - Gagal sinkronisasi dapat tetap commit dan meninggalkan cache lama

Lokasi:

- `detail_project/views_api_tahapan_v2.py:385`

Jika weekly storage berhasil disimpan tetapi `sync_weekly_to_tahapan()` gagal, exception ditangkap dan endpoint mengembalikan HTTP 500 tanpa menandai transaksi rollback.

Dampak:

- canonical storage berubah;
- projection legacy belum berubah;
- cache invalidation tidak dijalankan;
- user menerima pesan gagal walaupun sebagian operasi sudah commit.

Rekomendasi:

- rollback seluruh transaksi jika sync masih dianggap bagian kontrak save;
- atau commit canonical storage, jadikan sync idempotent async projection, lalu response menyatakan canonical save berhasil dengan status sync terpisah;
- jangan memakai response 500 ambigu untuk dua hasil tersebut.

### JDW-04 - TINGGI - Kegagalan load assignment ditampilkan seperti data kosong

Lokasi:

- `detail_project/static/detail_project/js/src/modules/core/data-loader.js`

`loadAssignments()` menangkap error dan mengembalikan map kosong. Akibatnya parent orchestrator dapat melanjutkan render tanpa error page.

Dampak:

- network/server error terlihat seperti seluruh progres 0%;
- user dapat mengisi ulang dan menimpa data yang sebenarnya ada;
- Grid, Gantt, dan Kurva S memberi informasi salah tanpa warning persisten.

Rekomendasi:

- bedakan state `empty`, `loading`, dan `error`;
- assignment load error harus memblokir editing;
- tampilkan retry dan detail endpoint yang gagal;
- volume load error juga tidak boleh diam-diam menjadi volume 0 pada mode Volume.

**Keputusan pengamanan loading 14 Juni 2026: DISETUJUI.**

Sistem menerapkan fail-closed berdasarkan tingkat dependensi:

- `empty` hanya ditampilkan jika request berhasil dan server memastikan belum
  ada data;
- `loading` menampilkan skeleton dan menonaktifkan input;
- `error` tidak boleh diubah menjadi nilai nol.

Jika progres/assignment gagal dimuat:

- seluruh editing Grid dikunci;
- Gantt dan Kurva S tidak dirender seolah progres nol;
- tampilkan error persisten dan tombol `Coba Lagi`;
- tegaskan bahwa data tersimpan tidak diubah;
- setelah retry berhasil, fitur aktif kembali tanpa wajib reload penuh.

Jika data pendukung gagal:

- kegagalan Volume Pekerjaan menonaktifkan input Volume Realisasi;
- kegagalan nilai pekerjaan menonaktifkan input Biaya Rencana dan Kurva S
  berbobot;
- input Persentase tetap boleh digunakan jika weekly progress berhasil dimuat;
- UI menyebutkan sumber data yang gagal dan fitur yang dinonaktifkan.

Error state tidak boleh hanya berupa toast yang hilang otomatis.

### JDW-05 - TINGGI - Reset Realisasi tidak menghapus biaya aktual

Lokasi:

- `detail_project/views_api_tahapan_v2.py:1028`

Reset mode Realisasi hanya mengubah `actual_proportion=0`, tetapi `actual_cost` tetap tersimpan.

Dampak:

- progres realisasi 0% dapat tetap mempunyai biaya aktual;
- Kurva S biaya dan laporan aktual dapat tetap menampilkan pengeluaran;
- pesan UI “semua progres Realisasi dikembalikan ke 0%” tidak menjelaskan biaya yang dipertahankan.

Keputusan yang diperlukan:

- Setelah kontrak mode input disepakati, `actual_cost` bukan lagi bagian dari
  input utama Jadwal Pekerjaan.
- Seluruh pemakaian `actual_cost` pada Grid, Kurva S, dan export harus dipetakan
  sebagai kontrak legacy sebelum diputuskan migrasi atau penghapusannya.
- Perilaku reset final dibahas pada poin reset progres.

**Keputusan reset progres 14 Juni 2026: DISETUJUI.**

- Reset hanya mengubah SSOT persentase pada mode yang sedang aktif.
- Reset Rencana mengubah seluruh `planned_proportion` dalam cakupan menjadi nol.
- Reset Realisasi mengubah seluruh `actual_proportion` dalam cakupan menjadi nol.
- Mode lain tidak boleh terpengaruh.
- Biaya Rencana dan Volume Realisasi otomatis menjadi nol karena keduanya hanya
  tampilan turunan dari persentase.
- Reset harus atomik dan dicatat pada audit trail.
- Sebelum konfirmasi, UI menampilkan mode, jumlah pekerjaan, jumlah sel/periode,
  serta penegasan bahwa tindakan tidak dapat dibatalkan.
- Jika terdapat perubahan belum tersimpan pada salah satu mode, user harus
  memilih simpan atau batalkan perubahan sebelum reset dilanjutkan.
- Selain reset seluruh mode, disediakan tindakan terpisah untuk mengosongkan
  baris atau sel terpilih agar koreksi kecil tidak memerlukan reset project.
- `actual_cost` legacy tidak menjadi bagian kontrak reset baru dan ditangani
  melalui migrasi terpisah setelah seluruh consumer dipetakan.

### JDW-06 - SEDANG - Notes shared dan dapat terhapus oleh save grid

Lokasi:

- `detail_project/views_api_tahapan_v2.py:249`

Frontend tidak mengirim notes, sedangkan backend memakai default string kosong dan menulis `wp.notes = notes` pada setiap update.

Dampak:

- notes yang ditulis melalui admin/API lama dapat hilang ketika user mengubah persentase;
- notes Rencana dan Realisasi tidak dapat dibedakan.

Rekomendasi:

- jika `notes` tidak ada di payload, jangan update field;
- putuskan apakah notes bersifat umum, planned, atau actual;
- jika UI tidak lagi mendukung notes, hapus kontrak notes secara eksplisit melalui migrasi terencana.

**Keputusan diskusi 14 Juni 2026: HAPUS FITUR CATATAN.**

- `notes` tidak menjadi bagian kontrak input Jadwal Pekerjaan.
- Frontend tidak perlu menampilkan atau mengirim catatan.
- Backend tidak boleh lagi menulis string kosong ke `notes` saat menyimpan
  progres.
- Field/kontrak legacy dihapus melalui migrasi dan pembersihan API terencana
  setelah dipastikan tidak mempunyai consumer aktif.

### JDW-07 - SEDANG - Timestamp realisasi berubah ketika hanya rencana yang diedit

Lokasi:

- `detail_project/models.py:850`

`actual_updated_at` menggunakan `auto_now=True`, sehingga setiap save record, termasuk edit planned, memperbarui timestamp realisasi.

Dampak:

- audit “kapan realisasi terakhir diperbarui” tidak akurat;
- cache/signature atau indikator freshness dapat memberi informasi palsu.

Rekomendasi:

- update timestamp aktual hanya ketika `actual_proportion` atau `actual_cost` berubah;
- pertimbangkan `planned_updated_at` dan `actual_updated_at` terpisah.

**Keputusan diskusi 14 Juni 2026: TIMESTAMP TIDAK DIPERLUKAN SEBAGAI FITUR.**

- Jangan menambah timestamp Rencana/Realisasi baru pada UI atau kontrak bisnis.
- Workflow tidak bergantung pada informasi kapan masing-masing nilai diedit.
- Timestamp teknis yang masih dibutuhkan ORM, cache, atau logging boleh tetap
  internal, tetapi tidak ditampilkan sebagai metadata progres dan tidak menjadi
  dasar keputusan user.

### JDW-08 - SEDANG - Tidak ada optimistic concurrency

Endpoint save tidak menerima version/`updated_at` expected.

Dampak:

- dua tab atau dua perangkat dapat saling menimpa;
- last-write-wins terjadi tanpa warning;
- status “Tersimpan” tidak berarti data berasal dari versi terbaru.

Rekomendasi:

- kirim revision project atau timestamp record;
- response `409 Conflict` jika sumber telah berubah;
- sediakan pilihan reload atau overwrite secara eksplisit.

**Keputusan diskusi 14 Juni 2026: GUNAKAN LAST SAVE WINS.**

- Optimistic locking dan dialog konflik tidak ditambahkan.
- Save terakhir yang berhasil menjadi nilai resmi.
- Save tetap harus atomik, owner-scoped, tervalidasi, dan tidak boleh
  menghasilkan partial write.
- UI tidak boleh memberi kesan bahwa sistem melindungi konflik lintas tab atau
  perangkat.

### JDW-09 - SEDANG - Save melakukan query dan `full_clean()` per sel

Untuk setiap sel, endpoint mengambil pekerjaan, mencari tahapan, `get_or_create`, dan save model.

Dampak:

- payload perubahan besar menghasilkan banyak query;
- save dapat lambat pada project dengan ratusan pekerjaan;
- timeout memperbesar risiko user menekan simpan berulang.

Rekomendasi:

- validasi pekerjaan dengan satu owner-scoped query;
- prefetch tahapan dan existing weekly rows;
- gunakan `bulk_create(..., update_conflicts=True)` setelah validasi;
- tetap pertahankan transaksi all-or-nothing.

**Keputusan diskusi 14 Juni 2026: DISETUJUI.**

- Save dioptimalkan melalui batch validation, prefetch, dan bulk upsert.
- Kontrak payload, tombol Simpan mode aktif, validasi, feedback, dan alur kerja
  client tidak berubah.
- Optimasi wajib mempertahankan transaksi all-or-nothing dan last save wins.

### JDW-10 - RENDAH - Invalid progress mode diam-diam menjadi planned

Mode selain `planned`/`actual` diubah menjadi `planned`.

Dampak:

- typo atau client lama dapat menulis ke Rencana tanpa diketahui.

Rekomendasi:

- return HTTP 400 untuk mode invalid;
- backward compatibility hanya diberikan pada payload tanpa field mode.

## 6. Temuan Frontend dan Alur Interaksi

### JDW-11 - TINGGI - Batas minggu disimpan sebelum konfirmasi discard

Lokasi:

- `detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js:1640`
- `detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js:1724`
- `detail_project/static/detail_project/js/src/modules/app/DataOrchestrator.js:166`

Alur saat ini:

1. state batas minggu langsung berubah;
2. kolom lokal langsung disusun ulang;
3. preferensi project disimpan;
4. baru proses regenerate memeriksa unsaved changes dan meminta konfirmasi.

Jika user membatalkan, preferensi dapat sudah berubah.

Risiko tambahan: pemeriksaan modified cells berfokus pada mode aktif. Perubahan belum tersimpan pada mode yang sedang tidak aktif dapat luput.

Rekomendasi:

- periksa seluruh dirty state planned + actual sebelum mengubah state atau server;
- konfirmasi terlebih dahulu;
- setelah konfirmasi, simpan preference dan regenerate sebagai satu operasi;
- jika gagal, restore selector dan state lama.

**Keputusan penyederhanaan batas minggu 14 Juni 2026: DISETUJUI.**

Kontrak final:

1. Batas minggu merupakan konfigurasi level project dan dipakai bersama oleh
   Grid, Gantt, Kurva S, export, serta Rekap Kebutuhan.
2. Batas minggu dapat dipilih selama project belum mempunyai progres Rencana
   maupun Realisasi yang bernilai lebih dari nol.
3. Setelah progres pertama tersimpan, batas minggu dikunci dan selector pada UI
   menjadi read-only.
4. Perubahan boundary setelah terkunci bukan fitur edit harian. Perubahan hanya
   tersedia sebagai migrasi administratif khusus dengan backup, preview dampak,
   konfirmasi, validasi, dan audit trail.
5. Sistem tidak mencoba memindahkan progres otomatis berdasarkan overlap
   tanggal karena storage kanonik tidak menyimpan distribusi harian.
6. Jika belum ada progres, perubahan boundary boleh menyusun ulang seluruh
   kolom waktu tanpa migrasi data.
7. Penyimpanan konfigurasi dan regenerate struktur harus menjadi satu operasi
   atomik. Jika gagal, boundary lama tetap berlaku.
8. Backend wajib menolak perubahan boundary yang sudah terkunci, sehingga
   pembatasan tidak hanya bergantung pada UI.

Kondisi penguncian:

```text
locked =
  exists(planned_proportion > 0)
  OR exists(actual_proportion > 0)
```

Record kosong atau bernilai nol tidak mengunci boundary.

UI saat terkunci:

```text
Batas minggu: Senin-Minggu
Status: Dikunci karena jadwal telah berisi progres
```

Dengan batasan ini, nomor minggu dan rentang tanggal tetap stabil sepanjang
siklus project dan tidak diperlukan algoritma redistribusi progres yang bersifat
perkiraan.

### JDW-12 - TINGGI - Export dapat mencampur data saved dan unsaved

Lokasi:

- `detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js:975`
- `detail_project/exports/export_manager.py`
- `detail_project/exports/jadwal_pekerjaan_adapter.py`

Chart/Gantt attachment dibangun dari state browser, sedangkan tabel profesional dibangun ulang dari database. Tidak ada guard dirty sebelum export.

Dampak:

- chart dapat memuat perubahan terbaru;
- tabel pada file yang sama masih memuat nilai lama;
- dokumen terlihat resmi tetapi kontradiktif.

Rekomendasi:

- blokir export ketika ada perubahan belum disimpan;
- tawarkan “Simpan lalu ekspor” atau “Ekspor data tersimpan”;
- backend tidak seharusnya menerima structured Gantt client sebagai otoritas data.

**Keputusan export 14 Juni 2026: DISETUJUI - server-authoritative.**

Kontrak export resmi:

```text
Frontend:
  format + jenis laporan + cakupan periode + opsi tampilan

Backend weekly SSOT:
  tabel + Gantt + Kurva S + ringkasan + metadata
```

- Backend membaca `PekerjaanProgressWeekly` dan seluruh data pendukung dari satu
  snapshot/revision yang konsisten.
- Frontend tidak mengirim planned/actual progress, `gantt_data`, atau attachment
  chart sebagai sumber resmi laporan.
- Jika ada draft, user memilih `Ekspor Data Tersimpan`, `Simpan Mode Aktif lalu
  Ekspor`, atau `Batal`.
- Jika mode lain masih mempunyai draft, UI menegaskan bahwa draft tersebut tidak
  ikut tersimpan maupun diekspor.
- Preview/chart browser tetap boleh diunduh terpisah dengan label `Draft`, tetapi
  bukan laporan resmi.
- Metadata laporan mencantumkan waktu pembuatan, revision data, batas minggu,
  cakupan minggu/Periode 4 Minggu, dan mode yang disertakan.
- PDF, XLSX, dan JSON harus berasal dari dataset snapshot yang sama.

Pengamanan tambahan export:

- validasi nomor minggu/periode terhadap timeline project;
- tolak pilihan periode kosong, duplikat, atau di luar rentang;
- hasil export kosong harus menjelaskan penyebab, bukan menghasilkan dokumen
  formal tanpa data;
- gunakan identitas project terpusat agar nama, kode, lokasi, owner, dan sumber
  dana konsisten;
- proses export besar harus mempunyai progress status, timeout yang jelas, dan
  pesan kegagalan yang dapat ditindaklanjuti;
- nama file memakai nama project, jenis laporan, cakupan periode, revision, dan
  tanggal export yang aman untuk filesystem;
- audit trail mencatat user, waktu, format, cakupan, dan revision yang diekspor;
- pembentukan dataset dan renderer dipisahkan agar parity antarformat dapat
  diuji dari input data yang sama.

#### Keputusan Klasifikasi Export 1 - Struktur dan Cakupan

**Hasil diskusi dan verifikasi 14 Juni 2026:**

1. Untuk laporan Mingguan dan Periode 4 Minggu, tombol export dinonaktifkan
   sampai minimal satu pilihan valid dipilih. Fallback tersembunyi ke periode
   pertama dihapus.
2. Pilihan tidak berurutan ditampilkan sebagai daftar eksplisit, bukan rentang
   penuh. Contoh: `Minggu 1, 3, 7`, bukan `Minggu 1-7`.
3. Kesesuaian preview dan output difinalkan setelah kontrak sumber data export
   ditetapkan. Preview wajib membaca capability matrix yang sama dengan
   dispatcher/renderer.
4. Seluruh label publik memakai `Periode 4 Minggu`; key internal `monthly`
   boleh dipertahankan sementara untuk kompatibilitas.
5. Daftar pilihan minggu tidak boleh dihitung dari estimasi `ceil(days/7)` atau
   minimum buatan. Daftar harus berasal dari weekly columns kanonik yang membawa
   `week_number`, `start_date`, dan `end_date`.
6. Minggu pertama dan terakhir boleh mempunyai jumlah hari kurang dari tujuh:

```text
Minggu pertama = tanggal mulai project sampai boundary pertama
Minggu tengah  = tujuh hari penuh
Minggu terakhir = boundary terakhir sampai tanggal selesai project
```

   Keduanya tetap merupakan minggu valid dan harus dapat dipilih/export.
7. Backend memvalidasi pilihan terhadap daftar minggu/periode kanonik, termasuk
   minggu parsial pertama dan terakhir. Nilai positif saja belum cukup.
8. Modal saat ini sudah memberi informasi umum tentang Cover, Progress,
   Gantt/Kurva S, dan cakupan pilihan, tetapi belum menjamin informasi tersebut
   sesuai untuk setiap kombinasi jenis-format. Tambahkan ringkasan dinamis:
   jenis laporan, format, pilihan eksplisit, tabel, Gantt, Kurva S, dan bentuk
   perbandingan yang benar-benar akan dihasilkan.

Catatan implementasi saat ini:

- view membentuk `total_weeks` dengan estimasi tanggal dan memaksakan minimum
  12 minggu;
- JavaScript modal kembali memaksakan minimum 4 minggu;
- pendekatan tersebut dapat membuat pilihan minggu yang tidak ada atau tidak
  cocok dengan timeline yang mempunyai minggu awal/akhir parsial;
- sumber pilihan harus diganti dengan weekly column kanonik, bukan diperbaiki
  hanya dengan rumus estimasi lain.

#### Catatan Tradeoff Hybrid Export

Belum ada bukti benchmark bahwa hybrid frontend-backend lebih ringan. Jalur
sekarang melakukan sebagian pekerjaan dua kali:

- frontend membangun state export, merender chart, dan mengirim base64;
- backend tetap membangun tabel dan Kurva S, serta mempunyai renderer Gantt.

Konsekuensinya adalah beban CPU browser, payload request besar, parsing base64,
dan potensi sumber data berbeda. Karena itu keputusan server-authoritative tetap
menjadi rekomendasi integritas. Jika beban server menjadi masalah, solusinya
adalah cache dataset/render, background job, atau pembatasan ukuran export,
bukan menjadikan draft frontend sebagai sumber laporan resmi.

#### Keputusan Klasifikasi Export 2 - Identitas Kegiatan/Project

**Hasil diskusi 14 Juni 2026: DISETUJUI.**

Identitas Project yang dikelola melalui Dashboard menjadi SSOT metadata laporan.
Tidak dibuat field `nama_kegiatan` baru karena maknanya sama dengan
`Project.nama`; pada dokumen export field tersebut cukup ditampilkan dengan
label publik `Nama Kegiatan`.

Pemetaan identitas laporan:

| Label laporan | Sumber resmi |
|---|---|
| Nama Kegiatan | `Project.nama` |
| Kode Project/Paket | `Project.index_project` |
| Lokasi | `Project.lokasi_project` |
| Tahun Anggaran | `Project.tahun_project` |
| Sumber Dana | `Project.sumber_dana` |
| Pemilik/Client | `Project.nama_client` |
| Nilai Anggaran | `Project.anggaran_owner` |
| Periode Pelaksanaan | tanggal mulai dan selesai Project |

Kontrak implementasi:

- seluruh format PDF, XLSX, dan JSON membaca satu adapter identitas backend;
- renderer tidak boleh memakai alias tidak resmi seperti `project.lokasi` atau
  `tahun_anggaran`;
- frontend hanya memilih jenis, format, dan cakupan laporan, bukan mengirim
  ulang identitas project sebagai sumber resmi;
- perubahan identitas pada Dashboard otomatis berlaku pada export berikutnya;
- validasi kelengkapan dilakukan sebelum export dan menyebut field Dashboard
  yang perlu dilengkapi;
- keputusan ini tidak memerlukan migrasi atau restrukturisasi database besar.

#### Keputusan Klasifikasi Export 3 - Struktur Penandatangan

**Hasil diskusi 14 Juni 2026: DISETUJUI.**

Semua laporan Jadwal Pekerjaan menggunakan tiga pihak penandatangan:

1. Konsultan Pengawas.
2. Kontraktor Pelaksana.
3. Pemilik/Client.

Ketentuan implementasi:

- struktur tiga pihak berlaku konsisten pada PDF dan XLSX;
- urutan visual harus sama pada seluruh jenis laporan Jadwal;
- setiap blok memuat peran, ruang tanda tangan, nama penandatangan, jabatan,
  serta nama perusahaan/instansi;
- renderer tidak boleh membuat struktur, urutan, atau placeholder sendiri;
- seluruh format membaca satu konfigurasi/profil tanda tangan dari backend;
- jabatan tidak boleh otomatis dipaksakan menjadi `Direktur`;
- makna dan pemetaan field nama, jabatan, serta instansi dibahas pada keputusan
  berikutnya.

#### Keputusan Klasifikasi Export 4 - Makna Nama dan Instansi Penandatangan

**Hasil diskusi 14 Juni 2026: DISETUJUI.**

Untuk Konsultan Pengawas dan Kontraktor Pelaksana, field nama diperlakukan
sebagai nama penanggung jawab. Sistem tidak perlu menambahkan atau meminta
jabatan khusus untuk kedua pihak tersebut.

Pemetaan data:

| Pihak | Nama penandatangan | Instansi |
|---|---|---|
| Konsultan Pengawas | `Project.nama_konsultan_pengawas` | `Project.instansi_konsultan_pengawas` |
| Kontraktor Pelaksana | `Project.nama_kontraktor` | `Project.instansi_kontraktor` |
| Pemilik/Client | `Project.nama_client` | `Project.instansi_client` |

Ketentuan tampilan:

- Konsultan Pengawas dan Kontraktor Pelaksana memakai keterangan
  `Penanggung Jawab`, bukan jabatan yang ditebak seperti `Direktur`;
- Pemilik/Client tetap dapat memakai `Project.jabatan_client` karena field
  tersebut memang tersedia;
- tidak ditambahkan field `jabatan_kontraktor` maupun
  `jabatan_konsultan_pengawas`;
- perubahan ini tidak memerlukan migrasi database.

#### Keputusan Klasifikasi Export 5 - SSOT Profil Pengesahan dan Pagination PDF

**Hasil diskusi 14 Juni 2026: DISETUJUI.**

Seluruh PDF dan XLSX harus membaca satu profil pengesahan backend yang sama.
Profil tersebut menetapkan tiga pihak, urutan, nama penanggung jawab, instansi,
dan jabatan Pemilik/Client jika tersedia. Renderer hanya mengatur presentasi
sesuai format dan tidak boleh membentuk data penandatangan sendiri.

Aturan khusus PDF:

- blok tanda tangan tidak boleh berdiri sendiri pada halaman baru;
- blok tanda tangan harus terikat dengan bagian akhir tabel;
- bundel penutup PDF memuat minimal tiga baris terakhir tabel, baris total jika
  tersedia, dan blok tanda tangan;
- apabila tabel hanya mempunyai satu atau dua baris, seluruh baris tersebut
  ikut dalam bundel;
- bila ruang halaman tidak mencukupi, seluruh bundel dipindahkan bersama ke
  halaman berikutnya;
- pagination harus mereservasi tinggi blok tanda tangan sebelum membagi tabel,
  bukan menambahkan tanda tangan setelah pembagian halaman selesai;
- aturan ini berlaku untuk laporan Rekap, Mingguan, dan Periode 4 Minggu;
- tambahkan regression test PDF untuk batas halaman, tabel pendek, tabel
  panjang, dan perubahan tinggi nama/instansi.

Implementasi saat ini telah memakai `KeepTogether` dan reservasi tinggi pada
sebagian jalur PDF, tetapi logikanya masih tersebar. Logika tersebut perlu
disatukan sebagai helper pagination agar kontraknya berlaku pada semua jenis
laporan dan tidak bergantung pada renderer tertentu.

#### Keputusan Klasifikasi Export 6 - Data Identitas/Pengesahan Belum Lengkap

**Hasil diskusi 14 Juni 2026: DISETUJUI.**

Data identitas project atau penandatangan yang belum lengkap tidak memblokir
proses export.

Ketentuan:

- nilai yang belum diisi ditampilkan kosong;
- jika komponen atau renderer mengharuskan karakter pengganti, gunakan `.`;
- jangan memakai placeholder seperti `-`, `(Nama Pemilik)`, `(Nama Pelaksana)`,
  `(Nama Pengawas)`, `N/A`, atau nilai tebakan;
- ketentuan ini berlaku untuk identitas kegiatan, nama penanggung jawab,
  instansi, jabatan Pemilik/Client, lokasi, sumber dana, dan metadata opsional
  lainnya;
- modal export boleh memberi informasi bahwa beberapa metadata belum diisi,
  tetapi tombol export tetap aktif;
- builder identitas dan profil pengesahan harus menormalisasi nilai kosong agar
  perilaku PDF, XLSX, dan JSON konsisten.

#### Keputusan Klasifikasi Export 7 - Lokasi dan Tanggal Pengesahan

**Hasil diskusi 14 Juni 2026: DISETUJUI.**

- Lokasi yang ditampilkan pada laporan hanya memakai
  `Project.lokasi_project` dari identitas Project.
- Sistem tidak perlu membuat lokasi pengesahan terpisah.
- Sistem tidak perlu menampilkan tanggal pengesahan yang otomatis diambil dari
  waktu user melakukan export.
- Tidak diperlukan input override lokasi atau tanggal pengesahan pada modal
  export.
- Tanggal mulai/selesai Project serta rentang Minggu atau Periode 4 Minggu tetap
  ditampilkan karena merupakan identitas dan cakupan isi laporan, bukan
  timestamp pengesahan.
- Timestamp internal proses export boleh tetap digunakan untuk nama file,
  logging, atau kebutuhan teknis, tetapi tidak menjadi bagian wajib dari lembar
  pengesahan.

#### Keputusan Klasifikasi Export 8 - Konsistensi Layout Antarformat

**Hasil diskusi 14 Juni 2026: DISETUJUI.**

PDF dan XLSX harus konsisten pada:

- tiga pihak dan urutannya;
- label peran;
- nama penanggung jawab;
- instansi;
- jabatan Pemilik/Client jika tersedia;
- perlakuan nilai kosong.

Konsistensi tidak berarti kedua format harus mempunyai ukuran, jarak, atau
orientasi visual yang identik. Renderer boleh menyesuaikan layout terhadap
media masing-masing selama tidak mengubah makna dan struktur data.

Khusus PDF:

- aturan pagination mempunyai prioritas atas penyamaan tampilan dengan XLSX;
- blok tanda tangan tetap wajib terikat dengan bagian akhir tabel;
- penyesuaian ukuran font, spacing, dan lebar kolom diperbolehkan untuk menjaga
  bundel baris akhir, total, dan tanda tangan tetap utuh;
- renderer tidak boleh memindahkan tanda tangan menjadi halaman mandiri hanya
  demi menyeragamkan layout dengan XLSX.

#### Keputusan Klasifikasi Export 9 - Fungsi JSON dan Nama File

**Hasil diskusi 14 Juni 2026: DISETUJUI.**

JSON bukan laporan presentasi seperti PDF/XLSX. JSON berfungsi sebagai paket
copy/duplikasi Project ketika user ingin membuat Project identik beserta seluruh
nilai input yang relevan.

Kontrak JSON:

- dipisahkan secara konseptual dari menu/jenis laporan formal;
- memuat schema version agar kompatibilitas import dapat divalidasi;
- dibangun dari data tersimpan backend, bukan draft frontend;
- mencakup seluruh data input Project yang memang menjadi bagian fitur copy;
- tidak memuat ID database sumber sebagai identitas record tujuan;
- proses import memvalidasi ownership, referensi, mode, rentang minggu, dan
  struktur data sebelum melakukan write;
- import harus atomik: seluruh Project berhasil diduplikasi atau tidak ada
  perubahan;
- exporter JSON legacy perlu diaudit terhadap model dan SSOT terbaru sebelum
  dipakai sebagai mekanisme copy resmi.

Nama file export PDF/XLSX cukup menggunakan:

```text
NamaProject_TanggalExport.ext
```

- nama Project dinormalisasi agar aman untuk filesystem;
- tanggal export digunakan pada nama file saja dan tidak menjadi timestamp
  wajib di isi laporan atau lembar pengesahan;
- jika file dengan nama yang sama dibuat pada tanggal yang sama, mekanisme
  download client/OS menangani duplikasi nama tanpa mengubah kontrak dasar.

#### Keputusan Klasifikasi Export 10 - Pesan Error

**Hasil diskusi 14 Juni 2026: DISETUJUI.**

- User menerima pesan singkat yang menjelaskan apa yang gagal, dampaknya, dan
  tindakan yang dapat dilakukan.
- Detail exception, stack trace, query, dan path internal hanya dicatat pada
  log server.
- Response memakai kode error stabil agar frontend dapat memilih pesan dan
  tindakan yang sesuai.
- Kegagalan export tidak boleh menghasilkan file kosong yang terlihat berhasil.
- Kegagalan save harus menegaskan bahwa tidak ada perubahan yang disimpan.

#### Keputusan Klasifikasi Export 11 - Beban, Timeout, dan Background Job

**Hasil diskusi 14 Juni 2026: DISETUJUI.**

Export menggunakan strategi adaptif berdasarkan estimasi beban:

```text
beban dasar = jumlah pekerjaan terpilih x jumlah minggu terpilih
```

Estimasi juga mempertimbangkan format dan konten karena PDF dengan pagination,
grafik, dan tanda tangan lebih berat daripada dataset sederhana.

Kontrak:

- tidak menggunakan batas kaku 52 minggu; cakupan valid mengikuti timeline
  Project;
- backend menghitung estimasi beban sebelum export;
- export ringan diproses langsung;
- export berat otomatis dipindahkan ke Celery background job tanpa mengubah isi
  laporan atau pilihan user;
- ambang sinkron/background ditentukan melalui performance test dan dapat
  dikonfigurasi, bukan ditanam sebagai asumsi permanen pada frontend;
- modal menjelaskan jumlah pekerjaan, jumlah minggu, dan bahwa proses berjalan
  di latar belakang;
- user dapat meninggalkan halaman dan mengambil file setelah job selesai.

Rekomendasi timeout awal:

- soft timeout background: 8 menit;
- hard timeout background: 10 menit;
- tidak melakukan retry untuk data invalid, error renderer deterministik, atau
  pelanggaran validasi;
- maksimal satu retry untuk gangguan sementara pada broker, storage, atau
  layanan pendukung.

Pengamanan proses:

- ownership Project diverifikasi kembali di worker;
- job export identik yang masih berjalan tidak dibuat ulang;
- dataset server-authoritative dibentuk sekali per snapshot dan dipakai seluruh
  renderer;
- kegagalan tidak boleh menghasilkan file kosong;
- status membedakan validasi data, worker tidak tersedia, timeout, kehabisan
  resource, kegagalan storage, dan kegagalan renderer;
- file sementara dibersihkan otomatis setelah 24 jam;
- import/copy Project besar tetap atomik dan setelah selesai menampilkan jumlah
  pekerjaan serta informasi bahwa operasi berat dapat memakai background job.

Nilai timeout dan ambang beban di atas merupakan baseline implementasi. Angka
final wajib dikalibrasi dari benchmark project kecil, menengah, besar, serta
kasus ekstrem sebelum release.

### JDW-13 - SEDANG - Pergantian Rencana/Realisasi menyimpan dirty state, tetapi statusnya kurang eksplisit

StateManager memisahkan perubahan kedua mode, yang merupakan desain baik. Namun user dapat berpindah mode dengan perubahan belum tersimpan dan tombol Simpan hanya menyimpan mode aktif.

Dampak:

- user dapat mengira tombol Simpan menyimpan semua mode;
- perubahan pada mode lain tetap tertunda.

Rekomendasi:

- tampilkan badge `Rencana: n perubahan` dan `Realisasi: n perubahan`;
- ubah label menjadi “Simpan mode aktif” atau simpan kedua mode secara atomik;
- konfirmasi sebelum reset jika mode lain masih dirty.

**Keputusan diskusi 14 Juni 2026: DISETUJUI.**

- Tombol Simpan hanya berlaku untuk mode yang sedang aktif.
- Label tombol harus mengikuti mode: `Simpan Rencana` atau `Simpan Realisasi`.
- Tab/selector harus menampilkan jumlah perubahan belum tersimpan per mode.
- Perpindahan mode mempertahankan perubahan yang belum disimpan.
- Status sukses harus menyebut mode yang baru disimpan dan tidak boleh memberi
  kesan bahwa mode lain ikut tersimpan.
- Refresh, keluar halaman, perubahan struktur waktu, dan tindakan destruktif
  harus memeriksa dirty state Rencana dan Realisasi sekaligus.
- Reset mode aktif tidak boleh menghapus progres mode lainnya.

**Keputusan perlindungan draft 14 Juni 2026: DISETUJUI.**

- Perpindahan Rencana/Realisasi tidak meminta konfirmasi karena draft masing-masing
  mode dipertahankan.
- Perpindahan Grid/Gantt/Kurva S tidak membuang draft.
- Gantt dan Kurva S boleh menampilkan draft sebagai preview dengan label yang
  jelas dan berbeda dari data tersimpan.
- Refresh, keluar halaman, reset, dan tindakan struktural memeriksa dirty state
  Rencana dan Realisasi sekaligus.
- Tindakan struktural tidak boleh dilanjutkan selama masih ada draft yang belum
  disimpan atau belum dibuang secara eksplisit.
- Karena tombol Simpan hanya menyimpan mode aktif, UI harus menjelaskan jika mode
  lain masih mempunyai draft.

Draft pemulihan:

- draft lokal disimpan sementara pada `sessionStorage`;
- key minimal mencakup user, project, mode, dan revision data sumber;
- draft mempunyai masa kedaluwarsa;
- draft tidak pernah dianggap sebagai data resmi atau SSOT;
- setelah reload/crash, UI menawarkan preview untuk pulihkan atau buang;
- draft tidak langsung dikirim ke database tanpa review dan aksi Simpan user;
- draft yang revision-nya tidak lagi cocok harus ditandai konflik dan tidak
  dipulihkan otomatis.

### JDW-13A - KEPUTUSAN MODE INPUT - Persentase menjadi SSOT, biaya dan volume hanya metode input

**Keputusan diskusi 14 Juni 2026: DISETUJUI.**

Matriks input final:

| Mode progres | Input langsung | Input alternatif | Nilai yang disimpan |
|---|---|---|---|
| Rencana | Persentase | Biaya Rencana | `planned_proportion` |
| Realisasi | Persentase | Volume Realisasi | `actual_proportion` |

Konversi Rencana:

```text
planned_proportion =
  biaya_rencana_mingguan / nilai_pekerjaan x 100

biaya_rencana_mingguan =
  planned_proportion / 100 x nilai_pekerjaan
```

Konversi Realisasi:

```text
actual_proportion =
  volume_realisasi_mingguan / volume_pekerjaan x 100

volume_realisasi_mingguan =
  actual_proportion / 100 x volume_pekerjaan
```

Ketentuan:

- biaya pada mode Rencana adalah nilai pekerjaan yang direncanakan untuk periode
  tersebut, bukan pengeluaran aktual;
- volume pada mode Realisasi adalah volume fisik yang telah diselesaikan;
- pergantian metode input tidak membuat storage baru;
- nilai pekerjaan harus tersedia dan lebih besar dari nol sebelum input biaya;
- volume pekerjaan harus tersedia dan lebih besar dari nol sebelum input volume;
- perubahan nilai pekerjaan atau volume master mengubah hasil tampilan turunan,
  tetapi tidak mengubah persentase yang telah tersimpan;
- UI harus menampilkan hasil konversi persentase agar user memahami nilai yang
  akan disimpan;
- total hasil konversi tetap tunduk pada batas maksimal 100%.

`actual_cost` yang saat ini ada tidak digunakan sebagai SSOT mode input Jadwal.
Field tersebut dipertahankan sementara sebagai legacy sampai seluruh pemakaiannya
pada frontend, Kurva S, API, dan export dipetakan dan dimigrasikan.

### JDW-13B - KEPUTUSAN EDITOR UTAMA - Grid menjadi satu-satunya jalur edit

**Keputusan diskusi 14 Juni 2026: DISETUJUI.**

- Grid menjadi satu-satunya tempat input dan koreksi progres.
- Gantt dan Kurva S bersifat read-only.
- Hanya baris pekerjaan yang dapat diedit.
- Baris klasifikasi dan subklasifikasi hanya menampilkan agregasi.
- Input Rencana tersedia sebagai Persentase atau Biaya Rencana.
- Input Realisasi tersedia sebagai Persentase atau Volume Realisasi.
- Paste massal diperbolehkan, tetapi divalidasi dan disimpan sebagai satu batch
  atomik.
- Total per pekerjaan tidak boleh melampaui 100%.
- Gantt tidak menyediakan drag/drop untuk mengubah jadwal karena hal tersebut
  akan menciptakan jalur edit kedua di luar Grid.
- Seluruh projection mengikuti alur:

```text
Grid -> validasi -> PekerjaanProgressWeekly -> Gantt/Kurva S/export/consumer
```

Peningkatan UI Grid yang direkomendasikan:

- sticky kolom identitas pekerjaan dan sticky header periode;
- indikator total teralokasi dan sisa alokasi pada setiap pekerjaan;
- warna status yang tidak hanya mengandalkan warna, disertai ikon/teks;
- preview hasil konversi Persentase-Biaya atau Persentase-Volume;
- penandaan sel modified, invalid, saving, dan failed;
- undo/redo lokal sebelum save;
- paste dari spreadsheet dengan preview dan validasi batch;
- shortcut keyboard dan navigasi sel;
- filter `Belum dijadwalkan`, `Belum 100%`, `Sudah 100%`, dan `Bermasalah`;
- panel ringkasan error yang dapat membawa fokus ke sel terkait;
- tampilan compact/comfortable untuk project kecil dan besar.

**Keputusan fitur UI Grid 14 Juni 2026: DISETUJUI.**

Prioritas implementasi:

1. indikator total teralokasi dan sisa alokasi per pekerjaan;
2. preview konversi Persentase-Biaya Rencana atau
   Persentase-Volume Realisasi;
3. panel masalah persisten yang dapat memfokuskan sel terkait;
4. filter status pekerjaan;
5. state sel tersimpan/diubah/invalid/saving/gagal;
6. sticky identitas pekerjaan dan header periode;
7. undo/redo lokal dan paste spreadsheet dengan preview;
8. distribusi nilai ke rentang minggu sebagai bantuan pengisian Grid;
9. pilihan tampilan ringkas dan nyaman.

Distribusi otomatis hanya membentuk draft pada Grid. Nilai tetap harus ditinjau,
divalidasi, dan disimpan oleh user melalui jalur save mode aktif.

### JDW-13C - KEPUTUSAN TAMPILAN GANTT - Bar kontinu dan read-only

**Keputusan diskusi 14 Juni 2026: DISETUJUI.**

- Gantt adalah projection read-only dari weekly SSOT.
- Bar menggunakan tampilan kontinu, bukan segmentasi visual per minggu.
- Rencana dan Realisasi dapat ditampilkan sendiri-sendiri atau berdampingan
  dalam mode Perbandingan.
- Awal dan akhir bar mengikuti minggu pertama dan terakhir yang mempunyai nilai
  progres lebih dari nol.
- Minggu kosong di tengah tidak memutus bar karena Gantt dipakai untuk membaca
  rentang secara cepat, bukan distribusi detail.
- Detail minggu tetap tersedia melalui tooltip berdasarkan posisi kolom waktu:
  nilai minggu tersebut, kumulatif, rentang tanggal, dan deviasi.
- Distribusi mingguan presisi tetap diperiksa pada Grid.
- Klik bar boleh memfokuskan pekerjaan yang sama pada Grid.
- Marker tanggal evaluasi/hari ini dan highlight keterlambatan dapat ditampilkan.
- Gantt tidak menyediakan drag, resize, atau penyimpanan tersendiri.
- Export Gantt hanya memakai data yang telah tersimpan.

Definisi keterlambatan:

```text
akhir periode evaluasi telah terlewati
AND actual cumulative < planned cumulative
```

Rekomendasi segmentasi bar per minggu dibatalkan karena menurunkan keterbacaan
visual pada project dengan timeline panjang.

### JDW-13D - KEPUTUSAN KURVA S - Pertahankan logika, fokus polishing

**Keputusan diskusi 14 Juni 2026: DISETUJUI.**

- Kurva S tetap merupakan projection read-only dari weekly SSOT.
- Kurva Rencana memakai `planned_proportion`.
- Kurva Realisasi memakai `actual_proportion`.
- Bobot pekerjaan berasal dari nilai pekerjaan terhadap total nilai project.
- Tidak ada perubahan logika bisnis besar; implementasi difokuskan pada
  polishing visual dan kejelasan informasi.
- Gunakan dua garis kontinu untuk Rencana dan Realisasi.
- Marker titik hanya tampil saat hover agar grafik tidak ramai.
- Tooltip menampilkan periode, progres periode, progres kumulatif, dan deviasi.
- Marker tanggal evaluasi/hari ini dan area deviasi dapat digunakan secara halus.
- Jika nilai pekerjaan belum lengkap atau total nilai project nol, Kurva S tidak
  boleh diam-diam memakai bobot rata. UI harus menjelaskan pekerjaan/sumber nilai
  yang belum tersedia.
- Perubahan Grid yang belum disimpan boleh terlihat sebagai `Preview Draft`,
  tetapi harus dibedakan dari data tersimpan.
- Export hanya memakai Kurva S dari data yang telah tersimpan.
- Istilah dan perhitungan biaya aktual legacy tidak diperluas sebelum
  `actual_cost` selesai dipetakan dan dimigrasikan.

### JDW-14 - SEDANG - Definisi “Bulanan” adalah blok empat minggu

Lokasi:

- `detail_project/exports/jadwal_pekerjaan_adapter.py:288`
- `detail_project/exports/jadwal_pekerjaan_adapter.py:751`

UI telah memberi toast “akumulasi 4 minggu”, tetapi label utama tetap “Bulanan/Month”.

Contoh:

```text
Periode 1 = Week 1-4
Periode 2 = Week 5-8
```

Ini tidak sama dengan Januari, Februari, dan seterusnya.

Rekomendasi:

- bila memang empat mingguan, gunakan label **Periode 4 Minggu**;
- bila laporan harus mengikuti bulan kalender, agregasikan berdasarkan overlap tanggal kalender;
- keputusan ini harus sama pada Jadwal, export, dan Rekap Kebutuhan.

**Keputusan diskusi 14 Juni 2026: DISETUJUI - gunakan Periode 4 Minggu.**

Kontrak final:

```text
Periode 1 = Minggu 1-4
Periode 2 = Minggu 5-8
Periode 3 = Minggu 9-12
dan seterusnya
```

Ketentuan:

- istilah `Bulanan`, `Monthly`, `Bulan 1`, dan label sejenis pada fitur agregasi
  ini diganti menjadi `Periode 4 Minggu`;
- nomor periode dihitung relatif dari awal timeline project;
- satu minggu hanya boleh masuk ke satu periode;
- tidak ada prorata berdasarkan bulan kalender;
- variasi 28/29/30/31 hari dan tahun kabisat tidak mengubah perhitungan;
- setiap periode menampilkan nomor minggu dan rentang tanggal aktual sebagai
  informasi, misalnya `Periode 3 · Minggu 9-12 · 15 Maret-11 April 2026`;
- periode terakhir boleh berisi kurang dari empat minggu jika timeline project
  berakhir sebelum blok lengkap;
- Grid, Gantt, Kurva S, export, dan Rekap Kebutuhan wajib memakai pembagian
  periode yang identik;
- route/API/internal key boleh dipertahankan sementara untuk kompatibilitas,
  tetapi kontrak dan label publik harus menggunakan istilah baru.

### JDW-15 - SEDANG - Lokasi project pada metadata client salah field

Lokasi:

- `detail_project/templates/detail_project/kelola_tahapan_grid_modern.html:207`
- model memakai `dashboard.Project.lokasi_project`.

Template membaca `project.lokasi`, sehingga metadata export client dapat menjadi `-`.

Rekomendasi:

- gunakan `project.lokasi_project`;
- pusatkan identitas project melalui helper/context yang sama dengan `_project_identity.html`.

### JDW-16 - RENDAH - Reset progres tidak mempunyai accessible name yang kuat pada layar kecil

Teks tombol memakai `d-none d-lg-inline`, ikon `aria-hidden`, dan tombol hanya mengandalkan `title`.

Rekomendasi:

- tambahkan `aria-label="Reset progres mode aktif"`;
- pada modal konfirmasi, sebutkan mode, jumlah record, dan apakah biaya ikut dihapus.

### JDW-17 - RENDAH - Istilah UI bercampur Indonesia dan Inggris

Contoh:

- Weekly, Monthly, Planned, Actual;
- Full Report, Month Boundaries;
- “Time scale diatur ke Weekly”.

Rekomendasi:

- UI user memakai Indonesia konsisten;
- istilah teknis Inggris tetap boleh pada kode/log internal.

## 7. Penilaian UI/UX

### Yang sudah baik

- Toolbar memprioritaskan Simpan, Refresh, Export, Bantuan, dan Reset.
- Rencana dan Realisasi terlihat jelas melalui badge dan warna.
- Mode Biaya dinonaktifkan ketika bukan Realisasi.
- Skala bulanan dinyatakan read-only.
- Grid/Gantt/Kurva S berada dalam satu navigasi tab.
- Empty state memberi CTA ke Daftar Pekerjaan.
- Initialization error menyediakan tindakan muat ulang.
- Status bar memakai `role="status"` dan `aria-live="polite"`.
- Ada guard `beforeunload`, konfirmasi refresh, dan konfirmasi reset.
- Skeleton, responsive toolbar, sticky area, fullscreen, dan export progress tersedia.

### Kekurangan UX terbesar

1. Error loading dapat terlihat sebagai data 0.
2. Export tidak menjelaskan apakah memakai data tersimpan atau perubahan layar.
3. Batas minggu berubah sebelum user menyetujui discard.
4. Status unsaved per mode belum cukup terlihat.
5. “Bulanan” masih ambigu terhadap bulan kalender.
6. Reset Realisasi tidak menjelaskan nasib biaya aktual.

**Keputusan polishing UI/UX 14 Juni 2026: DISETUJUI.**

Perbaikan UI/UX dapat dilaksanakan tanpa mengubah kontrak bisnis:

- gunakan istilah Indonesia secara konsisten;
- pertahankan Grid sebagai editor tunggal dan Gantt/Kurva S sebagai read-only;
- tampilkan dirty count dan status save per mode;
- bedakan loading, empty, warning, dan error secara visual serta semantik;
- tingkatkan navigasi keyboard, focus management modal, accessible name, dan
  `aria-live` untuk feedback dinamis;
- pertahankan input cepat melalui paste, fill, clear selection, undo/redo lokal,
  sticky context, dan validasi inline;
- modal export menjelaskan data tersimpan, jenis, format, cakupan, dan konten
  yang benar-benar akan dibuat;
- polishing tidak boleh memperkenalkan segmentasi bar Gantt atau mengubah
  workflow input yang sudah disepakati.

## 8. Security dan Reliability

Yang sudah baik:

- page dan endpoint memakai login;
- project diverifikasi berdasarkan owner;
- CSRF digunakan pada write;
- persentase dan biaya divalidasi;
- transaksi digunakan pada save/reset/regenerate.

Yang perlu diperbaiki:

- exception internal dikirim kembali melalui `str(e)` pada beberapa endpoint;
- payload export menerima chart/structured data dari client tanpa kontrak bahwa data itu hanya presentasi;
- tidak ada request size limit khusus untuk attachment base64;
- tidak ada concurrency token;
- partial-write semantics harus dihilangkan.

## 9. Test Coverage

Verifikasi yang dijalankan:

```text
python -m pytest detail_project/tests_page_security_audit.py
                 detail_project/exports/tests/test_progress_calculation.py -q

Hasil: 11 passed
```

Masalah test infrastructure:

```text
npm test

Gagal: detail_project/tests/test_jadwal_pekerjaan_page_ui.py tidak ditemukan.
```

Coverage yang belum memadai:

- save campuran valid/invalid;
- rollback saat sync gagal;
- custom week boundary;
- dirty state pada mode tidak aktif;
- assignment API failure state;
- reset actual beserta actual cost;
- export saat dirty;
- concurrent edit;
- agregasi lintas bulan/tahun;
- parity Grid/Gantt/Kurva S/export/Rekap Kebutuhan;
- performance save untuk project besar.

**Keputusan pengujian akhir 14 Juni 2026: DISETUJUI.**

Seluruh regression, integration, UI, export pagination, import/export JSON,
security, dan performance test dijalankan setelah implementasi perbaikan
selesai. Hasil akhir harus mencatat test yang lulus, gagal, dilewati, serta
risiko yang belum dapat diverifikasi.

## 10. Prioritas Perbaikan

### P0 - Integritas dan data trust

1. Jadikan save all-or-nothing.
2. Gunakan batas minggu project pada seluruh fallback.
3. Jangan samarkan assignment load failure sebagai jadwal kosong.
4. Putuskan dan perbaiki reset actual cost.
5. Blokir export campuran saved/unsaved.

### P1 - Konsistensi workflow

1. Konfirmasi sebelum perubahan batas minggu dipersist.
2. Periksa dirty state kedua mode.
3. Tambahkan optimistic concurrency.
4. Perbaiki notes dan timestamp mode.
5. Definisikan “Bulanan” sebagai bulan kalender atau periode empat minggu.

### P2 - UX, performance, maintainability

1. Tampilkan dirty count per mode.
2. Optimalkan save menjadi batch.
3. Perbaiki metadata lokasi.
4. Rapikan istilah Indonesia.
5. Pulihkan test command Jadwal dan tambah integration coverage.

## 11. Keputusan yang Perlu Didiskusikan

### D-01 - Reset Realisasi

**Keputusan:** reset berfokus pada `planned_proportion` atau
`actual_proportion` sesuai mode aktif. `actual_cost` bukan bagian kontrak input
utama dan ditangani dalam migrasi legacy terpisah.

### D-02 - Definisi Bulanan

**Keputusan:** gunakan periode tetap empat minggu, bukan bulan kalender. Seluruh
label publik diubah menjadi `Periode 4 Minggu`, sedangkan key legacy dapat
dipertahankan sementara untuk kompatibilitas.

### D-03 - Save lintas mode

Apakah tombol Simpan:

- hanya menyimpan mode aktif; atau
- menyimpan seluruh perubahan Rencana dan Realisasi?

**Keputusan:** tetap menyimpan mode aktif, dengan label dan dirty count kedua
mode yang eksplisit.

### D-04 - Export ketika dirty

**Keputusan:** tampilkan pilihan:

1. Simpan lalu ekspor.
2. Ekspor versi tersimpan.
3. Batal.

Laporan resmi sepenuhnya dibangun backend dari satu snapshot weekly SSOT. Jangan
membuat dokumen dari dua versi data.

## 12. Dampak terhadap Rekap Kebutuhan

Rekap Kebutuhan harus mengikuti kontrak berikut:

```text
planned_weekly_requirement =
  total_item_requirement
  x PekerjaanProgressWeekly.planned_proportion / 100
```

Rekap Kebutuhan tidak boleh:

- memakai `PekerjaanTahapan` sebagai SSOT;
- membagi volume rata berdasarkan jumlah hari overlap;
- memakai actual progress untuk kebutuhan rencana;
- menafsirkan “bulan” berbeda dari Jadwal;
- memproses rentang minggu dengan boundary berbeda.

Karena itu, temuan Rekap Kebutuhan harus direkonsiliasi terhadap laporan ini.

## 13. Kesimpulan

Page Jadwal Pekerjaan mempunyai fondasi paling penting yang benar: weekly canonical storage, pemisahan Rencana/Realisasi, dan projection terpadu untuk Grid/Gantt/Kurva S. Restrukturisasi database besar tidak diperlukan.

Fokus perbaikan seharusnya pada kontrak transaksi dan UX data trust:

- satu save harus sepenuhnya berhasil atau sepenuhnya gagal;
- periode minggu harus identik di UI, database, export, dan consumer;
- error tidak boleh terlihat sebagai nilai nol;
- export tidak boleh mencampur saved dan unsaved state;
- keputusan reset biaya dan definisi bulanan harus dibuat eksplisit.

---

## 14. Verifikasi Independen (Claude, 13 Juni 2026)

Temuan diperiksa ulang terhadap kode kerja. Yang diverifikasi langsung: **JDW-01, JDW-02, JDW-03, JDW-04, JDW-05, JDW-06, JDW-07, JDW-10, JDW-15 — semuanya valid, tidak ada false positive.** Sisanya (JDW-08/09/11/12/13/14/16/17) konsisten dengan kode/struktur. Dokumen ini sudah memuat banyak keputusan owner ("DISETUJUI 14 Juni 2026") — verifikasi ini hanya memastikan temuan teknisnya nyata, tidak menilai ulang keputusan.

### 14.1 Verdict per temuan (yang diverifikasi langsung)

| Temuan | Verdict | Bukti verifikasi |
|---|---|---|
| JDW-01 Partial save tanpa rollback | **DIKONFIRMASI** | `views_api_tahapan_v2.py:373` `if errors:` mengembalikan 400 **tanpa** `transaction.set_rollback(True)`, padahal cabang validasi `>100%` di `:365` justru memanggilnya. Item valid sudah ter-`save()` di loop (`:259`) → commit parsial. Lihat 14.2. |
| JDW-02 Fallback abaikan batas minggu | **DIKONFIRMASI** | `:217` dan `:224` hardcode `week_end_day=6` (Sunday) di kedua fallback, mengabaikan preferensi project. |
| JDW-03 Sync gagal tetap commit | **DIKONFIRMASI** | `:386-396` `except sync_error` → return 500 **tanpa** rollback; weekly storage sudah ter-commit di loop. |
| JDW-04 Load error tampak data kosong | **DIKONFIRMASI** | `data-loader.js:517-519` `catch { return this.state.assignmentMap }` (map sudah di-`clear()` `:490-491`) → map kosong. Kontras: `loadTahapan:379` & `loadPekerjaan:429` justru `throw error`. Lihat 14.2. |
| JDW-05 Reset tak hapus actual_cost | **DIKONFIRMASI** | Reset `:1028/1031` hanya set `actual_proportion`/`planned_proportion = 0`; `actual_cost` tidak disentuh. (Owner: actual_cost = legacy, migrasi terpisah.) |
| JDW-06 Notes ditimpa save grid | **DIKONFIRMASI** | `:240` defaults `'notes': notes`, `:249` `wp.notes = notes` tanpa syarat pada setiap update. (Owner: HAPUS fitur catatan.) |
| JDW-07 actual_updated_at auto_now | **DIKONFIRMASI** | `models.py:850-852` `actual_updated_at = DateTimeField(auto_now=True)` → ter-update pada setiap save termasuk edit planned. (Owner: timestamp bukan fitur.) |
| JDW-10 Mode invalid → planned senyap | **DIKONFIRMASI** | `:1019-1020` `if progress_mode not in {'planned','actual'}: progress_mode = 'planned'`. |
| JDW-15 Lokasi salah field | **DIKONFIRMASI** | `kelola_tahapan_grid_modern.html:207` `{{ project.lokasi|default:'-' }}` — model memakai `lokasi_project`, jadi selalu `-`. Sama kelas dengan RR-04. |

### 14.2 Penajaman bukti

- **JDW-01 — kode sudah tahu cara rollback, cabang `errors` saja yang lupa.** Di fungsi yang sama, cabang validasi `>100%` (`:365`) memanggil `transaction.set_rollback(True)` sebelum return 400, tetapi cabang `if errors:` (`:373`) tidak. Jadi fix minimal hanya menambahkan `transaction.set_rollback(True)` sebelum `:374` — bukan refactor besar. Ini menutup partial-save yang juga jadi akar JDW-03 (sync path).

- **JDW-04 — penanganan error tidak konsisten antar-loader.** `loadAssignments` menelan error dan mengembalikan map kosong, sedangkan `loadTahapan`/`loadPekerjaan` melempar. Ironisnya assignment adalah **data progres inti** — justru yang paling berbahaya bila disamarkan jadi "0%". Selaraskan: assignment failure harus `throw` (atau set error-state), bukan return map kosong.

### 14.3 Catatan konsistensi lintas-page + rekonsiliasi penting

Halaman ini mengubah pemahaman saya tentang satu tema sistemik:

- **Concurrency: last-write-wins ternyata keputusan owner yang DISENGAJA, bukan oversight.** JDW-08 secara eksplisit memutuskan "GUNAKAN LAST SAVE WINS" (tanpa optimistic locking/dialog konflik). Ini **konsisten** dengan "single-user policy" di Template AHSP (TA-02) dan Harga Items (HI-09). Artinya: rekomendasi "aktifkan optimistic locking" yang saya catat di TA-02/HI-09/RA-11/RR-20 **harus dibaca ulang** — owner punya stance app-wide last-write-wins. **Yang tetap wajib** dari JDW-08 adalah: save harus atomik, owner-scoped, tervalidasi, dan **tanpa partial write**. Jadi isu nyata lintas-page bukan "last-write-wins"-nya, melainkan **partial-write/atomicity** (JDW-01 = LP-02/VP-01/VP-03/HI-01). Catatan ini saya simpan juga ke memory agar fase perbaikan tidak salah arah.

- Tema lain yang tetap berlaku: **`str(e)` bocor** (§8 dokumen = TA-08/HI/RA/RR); **missing-vs-zero / error-as-zero** (JDW-04 = D-04 Volume/Rekap); **wrong project field metadata** (JDW-15 = RR-04 `project.lokasi`); **export mencampur sumber data** (JDW-12 = pola adapter/sumber-ganda di HI-03/RA-03/RR).

### 14.4 Kalibrasi prioritas

P0 (JDW-01..05) tepat. Catatan:
- **JDW-01 quick win** (satu baris `set_rollback` di cabang `errors`).
- **JDW-02 quick win** (gunakan boundary project, bukan literal `6`).
- **JDW-04 quick win** (assignment loader `throw`/error-state, bukan map kosong).
- JDW-03, JDW-12, dan keputusan export server-authoritative adalah unit kerja lebih besar (kontrak transaksi sync + dataset export tunggal) — jadwalkan terpisah.

Catatan proses: audit ini paling matang dari sisi keputusan produk (JDW-01..17 hampir semua sudah "DISETUJUI" dengan kontrak rinci). Verifikasi mengonfirmasi temuan-temuannya nyata, sehingga keputusan-keputusan itu berpijak pada bukti yang benar.

### 14.5 Hardening Penomoran Minggu dan Timeline Basi

**Hasil verifikasi dan diskusi 14 Juni 2026: DISETUJUI.**

Kondisi saat ini tidak membuktikan bahwa rumus penomoran minggu JavaScript dan
Python sedang menghasilkan nilai berbeda. Masalahnya adalah adanya dua
implementasi dan deteksi struktur waktu basi pada client, sehingga terdapat
risiko drift serta mutasi otomatis saat page dibuka.

Prioritas:

1. **P0 - reliabilitas save dan load**
   - cabang `if errors` wajib menandai transaksi rollback;
   - kegagalan `sync_weekly_to_tahapan()` wajib rollback selama projection
     legacy masih mempunyai consumer;
   - `loadAssignments()` wajib masuk error state dan memblokir editing, bukan
     mengembalikan map kosong.
2. **P1 - deteksi timeline basi di server**
   - backend membandingkan timeline Project, boundary, dan weekly columns
     kanonik;
   - response membawa `timeline_stale` dan rincian penyebab;
   - client tidak melakukan regenerate otomatis saat load;
   - user menjalankan tindakan `Perbarui Struktur Waktu` secara terkontrol
     setelah pemeriksaan draft.
3. **P2 - week number server-authoritative**
   - API kolom minggu mengirim `week_number`, `start_date`, dan `end_date`;
   - frontend menggunakan nilai tersebut tanpa menghitung ulang;
   - tidak perlu menambah field `week_number` pada `TahapPelaksanaan` selama
     adapter server menghasilkan metadata kanonik secara eksplisit.
4. **Regression protection**
   - selama transisi, contract test JS-Python mencakup seluruh konfigurasi
     boundary dan minggu parsial;
   - setelah client berhenti menghitung minggu, test permanen berfokus pada
     builder backend dan memastikan frontend tidak mentransformasi metadata
     kanonik.

Temuan ini diklasifikasikan sebagai hardening untuk penomoran minggu, bukan
temuan critical baru. Ancaman integritas yang nyata tetap partial write,
kegagalan sinkronisasi, dan error assignment yang disamarkan sebagai nilai nol.

### 14.5 Telaah reliabilitas arsitektur (Claude, 13 Juni 2026) — sesudah membaca implementasi page penuh

Bagian ini ditambahkan setelah menelusuri arsitektur frontend page secara menyeluruh (`StateManager`/`ModeState`, `TimeColumnGenerator`, `SaveHandler`, `DataOrchestrator`) dan jalur regenerate/sync backend, bukan dari ekstrapolasi temuan.

**Temuan yang MENENANGKAN (terverifikasi):**

- **Regenerate timeline tidak merusak progres.** Endpoint yang ter-wire adalah `api_v2_regenerate_tahapan` (template `kelola_tahapan_grid_modern.html:212`), yang eksplisit *"NO DATA LOSS — weekly canonical never touched"* (`views_api_tahapan_v2.py:835,848`): hapus tahapan auto → regenerate → `sync_weekly_to_tahapan` dari canonical. Fungsi hapus-semua `reset_project_progress` (`progress_utils.py:362`) ada di jalur berbeda (reset eksplisit / ganti tanggal di Dashboard). Jadi membuka/menyusun-ulang page **tidak** menghapus `PekerjaanProgressWeekly`.

- **Penomoran minggu JS dan Python KONSISTEN (bukan temuan).** Sempat diduga ada risiko divergensi penomoran minggu antara `getWeekNumberForDate` (JS, `time-column-generator.js:60`) dan `_generate_weekly_tahapan` (Python, `views_api_tahapan.py:1148`). Setelah ditelusuri: `firstWeekEnd` dihitung identik, konversi `week_end_day` Python→JS `(p+1)%7` benar, dan fallback kolom `urutan+1` justru = `week_num` Python (`urutan = week_num-1`). Pada dataset konsisten + WIB, keduanya menghasilkan angka yang sama termasuk minggu parsial. **Ini di-downgrade dari "risiko" menjadi catatan hardening**, bukan Critical.

**Rekomendasi reliabilitas (akar masalah = struktur tahapan bisa basi terhadap timeline project, deteksinya bersandar heuristik klien):**

- **R1 (hardening) — `week_number` otoritatif dari server.** Kolom membawa `week_number` tersimpan dari backend dan `SaveHandler` mengirimnya apa adanya; hentikan perhitungan ulang di JS (`_createColumn` `computedWeekNumber`). Saat ini keduanya kebetulan setuju — menghapus implementasi kedua menghilangkan kelas drift masa depan tanpa mengubah perilaku. Effort kecil.

- **R2 (sedang) — deteksi "timeline basi" di server, bukan `ceil(days/7)`.** Ganti `_estimateExpectedWeeklyColumns` (`jadwal_kegiatan_app.js:116`) yang memicu **auto-regenerate saat page open** (`DataOrchestrator.js:97-113`). Backend kirim flag `timeline_stale` (membandingkan tahapan vs `tanggal_mulai/selesai/boundary`); klien tidak auto-mutasi diam-diam, melainkan menampilkan ajakan regenerate terkontrol. Menghapus mutasi backend otomatis yang digerakkan estimasi rapuh (estimasi mengabaikan minggu parsial). Selaras prinsip owner di Keputusan Export 1 ("daftar minggu dari weekly columns kanonik").

- **R3 (P0, = JDW-01/03/04) — tutup partial-write & sync.** Ini perbaikan reliabilitas yang sesungguhnya:
  - JDW-01: tambah `transaction.set_rollback(True)` di cabang `if errors:` (`views_api_tahapan_v2.py:373`); pola sudah ada di `:365`.
  - JDW-03: bila `sync_weekly_to_tahapan` gagal → rollback transaksi, atau jadikan sync idempotent async + response yang membedakan "canonical tersimpan" vs "sync tertunda" (jangan 500 ambigu).
  - JDW-04: `loadAssignments` (`data-loader.js:517`) `throw`/error-state, bukan map kosong (samakan dengan `loadTahapan`/`loadPekerjaan`).

- **R4 (hardening) — contract-test JS↔Python week numbering.** Test yang menegaskan kedua penomoran identik untuk `(tanggal_mulai, week_end_day)` lintas konfigurasi termasuk minggu parsial awal/akhir — mengunci kesepakatan yang sekarang berlaku sehingga R1 aman dan regresi tertangkap.

Catatan tambahan: `sync_weekly_to_tahapan` adalah **titik gandeng tunggal** (linchpin) antara weekly canonical dan struktur kolom — dipakai save maupun regenerate. Memperkuat penanganan kegagalannya (R3/JDW-03) berdampak ganda.

**Prioritas:** R3 (nyata, integritas) > R2 (hapus auto-mutasi rapuh) > R1+R4 (pencegahan). "Divergensi penomoran" TIDAK dinaikkan sebagai temuan Critical karena verifikasi menunjukkan saat ini konsisten.

### 14.6 Temuan Kurva S — sumber data (KS-01..KS-05) — TERVERIFIKASI (Claude + owner, 13–14 Juni 2026)

Telaah khusus sumber data Kurva S, diverifikasi bersama owner. Status: **temuan terverifikasi, bukan sekadar hardening.**

**Arsitektur sebenarnya — jalur data tumpang tindih (bukan dua renderer terpisah).**
Koreksi owner: overlay canvas **tidak sepenuhnya server-side**. `UnifiedTableManager` dapat menyuplai overlay memakai **dataset client**, sementara `KurvaSCanvasOverlay` dapat menarik dari `chart-data` API server; `uplot-chart.js` juga memakai `buildProgressDataset` client. Jadi terdapat **jalur data yang saling tumpang tindih**, bukan dua jalur terpisah yang rapi:

| Jalur | Sumber | Data | Bobot |
|---|---|---|---|
| Server (`chart-data` API + export adapter) | `compute_rekap_for_project` via `JadwalPekerjaanExportAdapter` | `PekerjaanProgressWeekly` (tersimpan) | `G × volume` (post-markup efektif) |
| Client (`buildProgressDataset`: uPlot, UnifiedTableManager, dan dapat memasok overlay) | `stateManager.getAllCellsForMode` | assignment **+ modifiedCells (draft)** | harga→volume→**bobot rata** (fallback) |

**Temuan terverifikasi:**

- **KS-01 (CONFIRMED) — Layar vs export dapat berbeda sumber.** Renderer layar dapat memakai draft client, sedangkan export memakai data tersimpan server. Tidak ada satu SSOT untuk kurva di layar.
- **KS-02 (CONFIRMED — melanggar JDW-13D) — Fallback bobot rata senyap.** `dataset-builder.js:16` (`buildProgressDataset`) fallback harga → volume → bobot rata (`:60-66`). JDW-13D eksplisit melarang pemakaian bobot rata diam-diam.
- **KS-03 (CONFIRMED — = RR-11) — Cache signature kurang harga.** `views_api.py:7286` (signature `chart-data`) belum memasukkan perubahan `HargaItemProject` (dan perubahan markup pekerjaan) → bobot server bisa basi.
- **KS-04 (CONFIRMED — positif) — API chart & export memakai adapter server yang sama.** Fondasi yang benar; jadikan SSOT.
- **KS-05 (TERJAWAB) — Basis bobot resmi.** Adapter memakai **nilai RAB pekerjaan setelah markup efektif, sebelum PPN, sebelum pembulatan = `G × volume`**. Terlihat di `jadwal_pekerjaan_adapter.py:1581` `_build_rekap_harga_cache` yang mengambil `row["total"]` (`:1599`) dari `compute_rekap_for_project`. Secara konsep tepat dan konsisten dengan nilai pekerjaan Rekap RAB. **Catatan:** konsistensinya bergantung pada penyelesaian calculation service Rekap RAB — khususnya konflik markup default/override (RA-01/RR-02). Tambahan: `_build_rekap_harga_cache` menelan error menjadi cache kosong (`:1601-1602 except: pass`) → seluruh bobot bisa jadi 0 secara senyap; perlu di-surface.

**Rekomendasi final (disepakati owner):**

1. **Adapter server = SSOT kurva tersimpan dan export.**
2. **Client tidak boleh menghitung ulang bobot** dari harga, volume, atau bobot rata.
3. **Preview draft boleh, tetapi harus:** berlabel `Preview Draft`; memakai **bobot kanonik yang dikirim server**; hanya mengganti nilai progress draft; **tidak** dianggap data export.
4. **Jika nilai pekerjaan tidak lengkap:** tampilkan pekerjaan penyebab; **jangan** pakai fallback bobot rata/volume.
5. **Cache** memakai revision calculation Rekap RAB, atau minimal mencakup `HargaItemProject` dan perubahan markup pekerjaan.
6. **Contract test:** kurva tersimpan di layar harus identik dengan kurva export.

**Severity:** KS-01 & KS-02 berdampak pada kepercayaan data yang ditampilkan (layar bisa menyesatkan vs export); KS-03 menyebabkan basi senyap; KS-04 fondasi yang dipertahankan; KS-05 menetapkan kontrak basis bobot. Dikategorikan sebagai **temuan terverifikasi** untuk fase perbaikan, terkait erat dengan penyelesaian calculation service Rekap RAB (RA-01/RR-02). 
