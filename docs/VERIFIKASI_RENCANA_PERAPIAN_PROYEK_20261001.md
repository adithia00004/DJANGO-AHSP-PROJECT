# Verifikasi Rencana Perapian Proyek — 2026-10-01

Dokumen yang diperiksa: `docs/RENCANA_PERAPIAN_PROYEK_20261001.md`.
Snapshot: HEAD `5767608d`, branch `feat/tambahan-waktu-kerja`, dengan WIP owner masih belum di-commit.

**Kesimpulan: arah rencana masuk akal, tetapi belum tepat untuk dijalankan apa adanya.** Koreksi di bawah perlu dimasukkan sebelum pelaksanaan terkait. Pemeriksaan ini tidak merupakan persetujuan merge, deploy, atau keputusan launch.

## Lingkup dan batas verifikasi

- Membaca rencana, dokumen 41/43/44 dan checklist launch, riwayat/ancestry Git, migrasi terkait, konfigurasi tes, dan implementasi notifikasi terkait.
- Mereproduksi perilaku inti toast melalui Node + happy-dom, dengan timer ditangkap dan tanpa mengubah sumber aplikasi.
- Memeriksa keberadaan 12 sampel export: 5 PDF, 4 DOCX, 3 XLSX. Isi/penampilan sampel belum diperiksa.
- Tidak menjalankan ulang suite backend/frontend penuh, build, migrasi, atau UAT browser. Angka hasil tes lama adalah bukti yang tercatat, bukan hasil pengujian ulang pada sesi ini.
- Tidak mengubah WIP, dokumen rencana asli, branch, database, atau server. Hanya menambahkan laporan ini.

## Fakta yang terkonfirmasi

| Klaim | Hasil |
|---|---|
| `main` berada di `69059282` | Benar. |
| Rangkaian 14 branch pada tabel doc 44 saling bertumpuk | Benar; setiap pasangan berurutan lolos `git merge-base --is-ancestor`. |
| `main` dapat fast-forward ke `feat/tambahan-waktu-kerja` | Benar untuk snapshot ini; `main` adalah ancestor dan selisihnya 320 commit. Periksa ulang setelah WIP di-commit. |
| Ada 27 berkas migrasi dalam diff kedua ujung | Benar. Ini bukan bukti bahwa seluruh 27 migrasi belum diterapkan pada database deployment. |
| WIP masih ada | Benar; 9 berkas tracked berubah dan tes `tests_list_pekerjaan_grow_tree.py` untracked, sesuai kelompok topik doc 44. Status “siap” belum diverifikasi ulang melalui tes sesi ini. |
| 944 tes / 0 gagal dan Vitest 39 file | Tercatat pada doc 43 §7, entri lanjutan D-11. Belum diulang pada snapshot sekarang. |
| Checklist launch tertinggal | Benar; commit terakhir untuk berkas tersebut `452401ae`, 2026-06-10, dan masih NO-GO. |
| T-F1 durasi objek | Benar; tujuh pemanggilan ditemukan. Reproduksi menghasilkan nol timer penutupan untuk objek `{duration: 3000}`. |
| T-F2 pesan Django menjadi modal | Benar, melalui `messages_modal.js`. |
| T-F3 notifikasi simpan dari dua lapisan | Benar; SaveHandler dan aplikasi Jadwal sama-sama memunculkan pesan hasil simpan. |
| T-F4 toast proses validasi tidak dibersihkan | Benar; tidak ada dismiss sebelum hasil. Namun `info(..., 0)` saat ini menjadi 3000 ms, bukan permanen, pada jalur DP.toast. |
| T-F6 tidak ada deduplikasi inti | Benar. |
| T-F8 bahasa teknis/campuran | Benar pada sumber export/PNG dan preset. |
| T-F9 cleanup loading export tidak lengkap | Benar; `_showLoading` mengabaikan handle toast, `_hideLoading` hanya memulihkan tombol. Klaim bahwa pemakaiannya hanya halaman tes admin tidak disertifikasi oleh pemeriksaan ini. |

## Koreksi yang diperlukan

### V-01 — Tanggal main salah dan cakupan branch terlalu luas

Rencana §1 menyebut tanggal `main` 2026-06-08. `git show -s --format=fuller main` menunjukkan **AuthorDate dan CommitDate 2026-02-11**. Jika 8 Juni dimaksud sebagai tanggal pemeriksaan atau terakhir branch dipindahkan, harus diberi label dan bukti tersendiri.

Empat branch lokal belum merupakan ancestor dari ujung yang direncanakan:

- `claude/fix-transaction-management-error-011CUox8f9ABCiXmbvqMPmtS`
- `codex/review-workflow_3_pages-and-create-agenda`
- `fix/kurva-s-phase1-critical-fixes`
- `refactor/bundle-quantity-semantic`

Karena itu, kriteria 1.5 “hanya main tersisa” tidak dapat dicapai hanya dengan menghapus branch yang sudah tergabung. Ubah menjadi **hapus hanya branch yang terbukti tergabung dan tidak dipakai worktree; pertahankan empat branch tersebut sampai perbandingan commit/patch selesai**. Gunakan penghapusan aman `git branch -d`, bukan pemaksaan. Commit berbeda belum tentu berarti perubahan fungsional belum terintegrasi; perlu review patch.

### V-02 — Inventaris migrasi berisiko belum lengkap

Selain detail_project 0047/0050/0051, rencana perlu secara eksplisit memasukkan:

- `detail_project/migrations/0048_repair_expanded_source_signature.py`: `RunPython` memperbarui signature data existing.
- `referensi/migrations/0023_unique_registry_code_per_category.py`: unique constraint; data duplikat dapat menghalangi penerapan.
- `subscriptions/migrations/0006_remove_planfeatureentitlement_uniq_entitlement_feature_plan_status_and_more.py`: menghapus entitlement duplikat sebelum membuat constraint `nulls_distinct=False`; reverse fungsi datanya tidak memulihkan baris yang dihapus.

Pertahankan uji 1.6 pada salinan, tetapi awali dengan inventaris migrasi yang benar-benar pending, audit duplikat/koefisien negatif, lalu catat perubahan jumlah/data, hasil constraint, durasi, dan kemampuan restore. Tag Git hanya mengamankan referensi kode; tidak membalikkan perubahan database.

### V-03 — Gate tes belum mencakup semua aplikasi yang ikut merge

R1–R9 dan 1.3 menjadikan `detail_project` + `dashboard` gate utama, sementara perubahan juga menyentuh accounts, subscriptions, dan referensi. Tambahkan suite aplikasi terdampak tersebut, termasuk tes PostgreSQL yang relevan.

`config/settings/test_pg.py` mewarisi `config/settings/test.py`, yang menetapkan `MIGRATION_MODULES = DisableMigrations()`. Jadi tes PostgreSQL tersebut **tidak membuktikan rantai migrasi berjalan**. Untuk audit migration drift dan uji migrasi nyata, gunakan settings dengan migrasi aktif; jangan mengandalkan settings tes itu. Pemisahan uji 1.6 sudah benar dan wajib dipertahankan.

Tuliskan perintah, settings, SHA, status WIP, jumlah pass/skip/fail, dan database yang dipakai untuk bukti terbaru. Jangan menyajikan hasil historis sebagai jaminan snapshot sekarang.

### V-04 — Alias danger di dalam show saja belum memperbaiki semua jalur

Rencana T-3 menyebut seluruh `danger` sudah tertangani T-2. Ini belum cukup: wrapper di Dashboard dan Referensi mengakses `DP.toast[type]` terlebih dahulu. Misalnya `referensi/static/referensi/js/ahsp_database_api.js:51` memilih `(DP.toast[type] || DP.toast.info)`. Karena `DP.toast.danger` tidak ada, jenis sudah berubah menjadi info sebelum mencapai normalisasi inti.

Tambahkan alias metode publik `DP.toast.danger` / `DP.toast.warn`, atau ubah seluruh wrapper untuk menormalisasi jenis sebelum memilih metode. Uji kedua bentuk, yakni `show(message, 'danger')` dan pemanggilan dinamis `DP.toast[type](message)`.

Koreksi deskripsi T-F5: ikon bukan hilang; implementasi saat ini memakai **ikon info** dan kelas `dp-toast-danger`, yang tidak memperoleh gaya error.

### V-05 — Kontrak API dan durasi T-2 harus mencakup jalur lama

Pertahankan semua bentuk yang sudah digunakan:

- `DP.toast.show({message, type, duration, title, closable, icon})`.
- `DP.toast.show(message, type, durationOrOptions)`.
- `DP.toast.success/error/info/warning(message, durationOrOptions)`.
- `DP.core.toast.show(...)` dan `window.showToast(...)` selama migrasi.

Bentuk objek pertama dipakai antara lain oleh `referensi/static/referensi/js/import_progress.js:369`; jangan hilangkan ketika menambah normalisasi argumen.

Definisikan secara eksplisit makna `duration: 0`, angka negatif, NaN, dan nilai nonangka. Saat ini `duration || default` mengubah nol menjadi default. Wrapper `Toast` di `src/modules/shared/ux-enhancements.js:268–303` juga memaksakan default 1600/2000/3000 ms sehingga perubahan default inti saja tidak menyeragamkan durasi 3000/5000/6000 ms.

Untuk deduplikasi, batalkan timer lama sebelum memperpanjang, bersihkan peta saat dismiss/clear/eviction, dan jangan menambah penghitung melalui HTML dari pesan pengguna. Tetapkan penanganan loading dengan pesan sama dari dua operasi berbeda: deduplikasi tidak boleh membuat cleanup satu operasi menghilangkan indikator operasi lain.

### V-06 — Tambahkan bug batas jumlah toast ke T-2

`core/toast.js:177` memanggil `clampToasts()` **sebelum** menambahkan toast baru. Dengan maxVisible 3, toast keempat masih aktif: reproduksi memperoleh **4 toast tanpa kelas dp-toast-hide**.

Ubah urutan atau perhitungan kapasitas dan tambahkan regresi untuk empat notifikasi berturut-turut. Uji juga interaksi batas jumlah dengan deduplikasi dan loading.

### V-07 — T-6 perlu menguji tag gabungan dan pesan campuran

`messages_modal.js` mengambil level dari `tags.split(' ')[0]`. Ada pemanggilan nyata dengan `extra_tags='import-error'` di `referensi/views/preview.py:481,498`. Jangan mengasumsikan token pertama selalu level; cari token level yang dikenal atau kirim level sebagai atribut data tersendiri.

Urutan template saat ini juga terbalik: `messages_modal.js` di `templates/base.html:352`, kemudian `core/toast.js:354`. Penataan ulang yang diusulkan benar.

Selain tes urutan render, tambah tes perilaku: success/info menjadi toast, error/warning tetap modal, tag gabungan tetap dikenali, kumpulan pesan campuran tampil tepat sekali, serta fallback modal ketika DP.toast tidak tersedia. Pertahankan kebutuhan detail/link pesan import.

### V-08 — T-F7 mencampur wrapper, fallback, dan implementasi aktif

Dashboard dan beberapa berkas Referensi sudah mendelegasikan notifikasi ke DP.toast. Karena itu angka “±15 implementasi terpisah” belum layak menjadi fakta terverifikasi tanpa daftar dan klasifikasi tiap lokasi.

T-4 sebaiknya menginventarisasi **renderer DOM aktif, fallback renderer, wrapper delegasi, dan kode tidak terpakai**. Guard yang melarang semua definisi `showToast` akan menolak adapter yang sah, callback tes, atau hasil build. Batasi pada sumber produksi yang relevan; kecualikan dist, arsip, dependency, dan fixture. Larang renderer/penjadwal independen di luar inti, bukan semata nama fungsi. Pastikan `src/utils/error-handler.js`, `export/ExportManager.js`, dan `src/export/ui-integration.js` ikut ditangani bila masih aktif; urutan halaman T-4 belum secara eksplisit mencakupnya.

### V-09 — Urutan transisi dan isolasi sesi perlu dipertegas

K-7 menyebut branch `fix/toast-notifikasi`, sedangkan R1 mewajibkan branch dari main dan main masih tertinggal. Nyatakan dependensi: **commit WIP dan gerbang/merge Langkah 1 lebih dahulu, baru branch toast dari main yang sudah diperbarui**. Jika toast harus mendahului merge, catat pengecualian transisi secara eksplisit; jangan diam-diam membangun dari main lama.

R3 memakai `test_<agen>_<tanggal>`, yang bisa bertabrakan untuk dua sesi agen pada hari sama. Gunakan suffix unik sesi/task. Worktree terpisah juga belum menjamin perintah `docker exec ... ahsp_web` membaca worktree yang tepat: verifikasi mount/path sumber dan SHA yang diuji. R8 pada container bersama perlu koordinasi agar tidak memutus tes agen lain; restart hanya memuat kode terbaru bila sumber/build memang tersedia di container tersebut.

## Hasil probe inti toast

Probe membaca sumber asli dengan Node `vm` + happy-dom; setTimeout dicatat, bukan dijalankan. Ini memvalidasi cabang kode lokal, bukan penampilan browser.

| Probe | Hasil |
|---|---|
| `DP.core.toast.show('object duration', 'success', {duration:3000})` | Tidak membuat timer auto-dismiss. |
| `DP.toast.show('failure', 'danger', 3000)` | Kelas `dp-toast-danger`; ikon `bi-info-circle-fill`; metode `DP.toast.danger` undefined. |
| Empat `DP.toast.info(...)` pada area kosong | Empat toast aktif, walau config maxVisible = 3. |
| `DP.toast.info('zero duration', 0)` | Membuat timer 3000 ms; nol tidak dipertahankan. |

## Usulan urutan revisi

1. Betulkan fakta Git dan kriteria penghapusan branch (V-01).
2. Perluas inventaris/gate migrasi dan aplikasi terdampak (V-02/V-03).
3. Lengkapi spesifikasi dan regresi T-2/T-3/T-6 (V-04 sampai V-07).
4. Perbaiki inventaris serta guard T-4 dan dependensi transisi (V-08/V-09).
5. Jalankan gerbang baru pada snapshot yang jelas, lalu perbarui tracker dengan bukti aktual.

Keputusan owner K-6/K-7 yang tertulis dalam rencana tetap dicatat sebagaimana adanya. Laporan ini tidak mengubah keputusan tersebut maupun menyatakan keputusan K-1 sampai K-5 telah diberikan.
