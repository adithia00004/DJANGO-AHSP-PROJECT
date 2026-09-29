# Audit backend Jadwal Pekerjaan terhadap rencana v4

Tanggal: 29 September 2026. Objek: working tree saat audit, termasuk perubahan lokal yang belum di-commit.

## Kesimpulan

Opsi A sesuai dengan arsitektur database sekarang. Tidak perlu memisahkan planned dan actual ke tabel baru atau merombak penyimpanan mingguan. Namun, jaminan backup/duplikasi dalam W-1 belum bisa dipenuhi hanya dengan menambah field akhir kontrak. Audit menemukan tiga masalah transfer data yang sudah ada dan satu jalur perubahan batas kontrak yang belum terinventarisasi dalam rencana.

Temuan di bawah membedakan masalah kode yang direproduksi, celah cakupan rencana, dan catatan implementasi. Ini bukan hasil pengujian fitur baru: field akhir kontrak dan implementasi v4 belum tersedia saat audit.

## 1. Arsitektur yang terverifikasi

| Komponen | Peran sebenarnya | Implikasi untuk fitur |
|---|---|---|
| `dashboard.Project` | Tanggal mulai/selesai, konfigurasi hari minggu, revisi jadwal | Tambah akhir kontrak; akhir jadwal tetap menjadi rentang pencatatan |
| `PekerjaanProgressWeekly` | Sumber utama, satu baris unik per pekerjaan dan nomor minggu | Planned, actual, dan biaya aktual terpisah sebagai field dalam baris yang sama |
| `TahapPelaksanaan` | Struktur periode/kolom, dapat dibentuk ulang | Bukan sumber kebenaran nilai realisasi |
| `PekerjaanTahapan` | Proyeksi turunan untuk kompatibilitas; sinkronisasi mengambil planned | Menyalin tabel ini tidak sama dengan menyalin progres mingguan |
| `build_week_buckets` / `expected_week_count` | Batas dan jumlah minggu berdasarkan tanggal serta konfigurasi akhir minggu | Import dan seluruh pemeriksaan rentang harus mengikuti aturan yang sama |
| API simpan mingguan | Mengubah sisi planned atau actual sesuai mode; memeriksa total; sinkronisasi; rollback saat kesalahan | Aturan kontrak baru perlu masuk sesuai jenis operasi, tanpa menghalangi simpan actual |
| Layanan perubahan timeline | Transaksi, gerbang perlindungan actual/biaya, resolusi, pembentukan ulang, invalidasi cache | Perpanjangan biasa dapat memakai layanan ini; K-6 adalah operasi planned khusus |

Bukti: `detail_project/models.py:823-955,958-968`; `progress_utils.py:181-287`; `views_api_tahapan_v2.py:313-347,400-506`; `timeline_utils.py:642-783`.

Form Dashboard mewajibkan kedua tanggal. Aturan 31 Desember berada pada management command untuk melengkapi data lama, bukan default form saat ini. Tidak ada alasan membuka kembali isu tanggal kosong sebagai penghalang alur normal.

Model mingguan menjalankan `full_clean()` pada `save()`. Penulisan massal tidak melewati metode itu. Karena restore historis memang boleh mempertahankan planned di luar kontrak, jangan memasang larangan tanpa konteks pada seluruh penyimpanan model. Validasi harus membedakan penulisan planned baru, actual, restore, dan pemindahan yang dipilih user sebagaimana prinsip v4.

## 2. Temuan yang harus masuk sebelum implementasi selesai

### A. Duplikasi tidak menyalin sumber utama progres — terkonfirmasi

`DeepCopyService.copy()` memanggil `_copy_tahapan()` dan `_copy_jadwal_pekerjaan()`. Fungsi kedua menyalin `PekerjaanTahapan`, bukan `PekerjaanProgressWeekly`. `_copy_project()` juga tidak menyalin `tanggal_selesai` atau konfigurasi hari minggu. Rujukan `services.py:235` di E-8 menunjuk pembentukan signature cache tahapan, bukan fungsi duplikasi.

Probe dengan proyek sumber berisi satu baris planned=20%, actual=15%, biaya=5000 menghasilkan salinan dengan **0 baris mingguan** dan **tanggal selesai None** melalui service. Jalur form Dashboard kemudian dapat mengisi tanggal selesai, tetapi tidak memperbaiki ketiadaan data mingguan; API deep-copy langsung memakai service.

Tindakan dalam W-1:

- Salin tanggal kontrak, akhir jadwal, dan konfigurasi minggu sesuai kebijakan salinan.
- Saat `copy_jadwal=True`, salin canonical weekly melalui pemetaan ID pekerjaan, termasuk planned, actual, biaya aktual, dan catatan.
- Selaraskan proyeksi dari data canonical, bukan mengandalkan proyeksi sebagai sumber.
- Untuk duplikasi yang mengizinkan tanggal mulai baru, nyatakan kebijakan timeline secara eksplisit; jangan mengasumsikan semua tanggal bisa selalu disalin mentah.
- Uji service/API, form Dashboard, serta pilihan tanpa jadwal.

Bukti: `services.py:4348-4407,5090-5176`; `views_api.py:6859-6867`; `dashboard/views.py:774-811`.

### B. Restore dapat membuang minggu terakhir yang sah — terkonfirmasi

Import menghitung `ceil((tanggal_selesai - tanggal_mulai).days / 7)`. Ini berbeda dari minggu kalender canonical yang memperhitungkan hari akhir minggu dan minggu pertama yang pendek.

Probe: proyek Minggu 6 September sampai Minggu 13 September 2026 memiliki dua minggu canonical. Backup membawa realisasi 15% di M2. Import berhasil, tetapi **baris M2 tidak diimpor**, karena rumus import menghitung satu minggu saja.

Tindakan dalam W-1:

- Ganti perhitungan import dan statistik export dengan helper jumlah minggu canonical.
- Fallback tanggal minggu pada import harus memakai bucket canonical, bukan tanggal mulai + kelipatan tujuh hari.
- Uji minggu pertama pendek, minggu terakhir pendek, konfigurasi hari akhir minggu nondefault, dan realisasi pada minggu tambahan terakhir.
- Bandingkan seluruh baris sebelum/sesudah restore, bukan hanya kedua tanggal proyek.

Bukti: `views_api.py:9292-9301,9680-9719`; `timeline_utils.py:117-128`; `progress_utils.py:296-334`.

### C. Biaya aktual tidak ikut backup/restore — terkonfirmasi

Kedua pembentuk JSON progres membawa planned dan actual, tetapi tidak membawa `actual_cost` maupun `notes`. Import juga hanya mengisi kedua proporsi tersebut.

Probe pada minggu valid: actual 15% berhasil kembali, tetapi **biaya 5000 menjadi None**. Ini relevan terhadap fitur karena gerbang pemendekan melindungi biaya aktual juga; baris dengan actual 0 dan biaya terisi dapat kehilangan perlindungannya setelah restore.

Tindakan: perluas W-1 agar menyalin field progres yang diperlukan, paling sedikit biaya aktual dan catatan selain proporsi; tetap kompatibel dengan backup lama yang belum memiliki field tersebut. Bedakan biaya `0` dari `None`.

Bukti: `views_api.py:8917-8927,9267-9278,9721-9729`; `timeline_utils.py:70-71`.

### D. Perubahan hari batas minggu juga mengubah batas kontrak — jalur aktif terkonfirmasi

Rencana membahas perubahan tanggal kontrak, tetapi belum memetakan endpoint pengaturan hari minggu dan regenerasi yang dapat mengubah `week_start_day`/`week_end_day`.

Probe: tanggal mulai 1 Januari 2026, calon akhir kontrak 5 Januari. Dengan minggu berakhir Minggu, batas kontrak berada di M2. Setelah pengaturan diubah agar minggu berakhir Senin, batas kontrak menjadi M1. Endpoint menerima perubahan; planned M2=20% tetap ada. Setelah fitur ditambahkan, M2 akan diklasifikasikan sebagai minggu tambahan tanpa perubahan tanggal kontrak.

Ini bukan bukti bahwa planned saat ini melanggar field kontrak yang belum ada. Ini membuktikan perubahan konfigurasi minggu adalah pemicu lain yang harus diperiksa oleh aturan kontrak baru.

Tindakan: masukkan `api_update_week_boundaries` dan `api_regenerate_tahapan_v2` ke inventaris perubahan struktur. Gunakan aturan pratinjau/penanganan data terdampak yang konsisten; jangan otomatis memindahkan nilai. Uji perubahan batas minggu dengan planned dan actual yang sudah terisi.

Bukti: `views_api_tahapan_v2.py:525-570,1106-1155`; `timeline_utils.py:117-128`.

## 3. Catatan pelaksanaan, bukan fitur tambahan

- **K-6:** setelah planned dipindahkan, sinkronkan `PekerjaanTahapan`, revisi, dan cache seperti jalur simpan yang ada. Nilai actual/biaya pada sumber serta tujuan tetap. Jangan berhenti setelah mengubah baris canonical.
- **Restore historis:** validasi planned di luar kontrak tidak boleh menolak penyimpanan actual pada baris historis yang planned-nya dipertahankan. `save()` memanggil validasi seluruh model, sehingga tempat pemasangan guard perlu diperhatikan.
- **Perubahan tanggal:** terapkan invariant tanggal di layanan penulisan, bukan hanya form Dashboard; import, API timeline, dan duplikasi memiliki jalur sendiri.
- **Export tambahan:** selain endpoint professional yang dicatat E-1 sampai E-4, URL generik CSV/PDF/Word/XLSX masih terdaftar dan memanggil `export_jadwal_pekerjaan`. Inventarisasikan sebagai jalur backend tersendiri; tentukan penerapan metadata kontrak pada format dokumen. Audit ini tidak menyatakan semuanya tampil pada UI utama. Bukti: `urls.py:239-258`, `views_api.py:6451-6538`, `exports/export_manager.py:646`.
- **Minggu pendek dan fallback kosong:** keputusan v4 tidak perlu dibuka kembali. Jalankan uji minggu pendek yang sudah ditulis; field kontrak baru diisi pada alur normal sesuai rencana.
- **P-6:** fungsi migrasi historis masih menggunakan argumen legacy `proportion`; bukan jalur perpanjangan aktif. Jangan menganggapnya jalur yang siap dijalankan ulang tanpa penyesuaian. Bukti: `progress_utils.py:505-512`, migrasi `0025_remove_legacy_proportion_field.py`.

## 4. Verifikasi yang dilakukan

Database pengujian SQLite in-memory, terpisah dari data proyek pengguna. Tidak menjalankan management command pengisian tanggal pada database pengguna.

Empat suite existing dijalankan, **42 tes lulus**:

- `detail_project.tests_timeline_crud_hardening`
- `detail_project.tests_timeline_resolution_engine`
- `detail_project.tests_timeline_contract_freeze`
- `detail_project.tests_timeline_mass_edit_safety`

Empat probe tambahan dijalankan melalui Django di database in-memory:

| Probe | Hasil teramati |
|---|---|
| Service duplikasi, `copy_jadwal=True` | Sumber 1 baris, salinan 0; akhir jadwal None |
| Export/import minggu pertama pendek | Export 1 baris M2, restore 0 |
| Export/import biaya aktual pada minggu valid | Actual 15% tetap, biaya 5000 menjadi None |
| Endpoint perubahan hari minggu | HTTP 200; calon minggu batas kontrak 2 menjadi 1; planned M2 tetap |

Probe mengonfirmasi perilaku kode saat ini; bukan tes kelulusan perilaku yang diinginkan. Skrip probe bersifat sementara dan tidak ditambahkan ke suite repository.

Batas verifikasi: belum menguji PostgreSQL, migrasi field baru, UI browser, atau render dokumen export. SQLite tidak membuktikan perilaku locking/constraint PostgreSQL. Kode aplikasi dan rencana v4 tidak diubah oleh audit ini.

## 5. Rekomendasi terhadap rencana

Pertahankan Opsi A dan struktur database sekarang. Sebelum menyatakan seluruh cakupan v4 selesai, perluas W-1 dengan temuan A–C, tambahkan perubahan konfigurasi minggu pada aturan kontrak (D), dan masukkan jalur export generik ke inventaris. Temuan A–C adalah masalah lama yang menjadi prasyarat janji backup/duplikasi v4; tidak berarti tombol perpanjangan sendiri harus didesain ulang.
