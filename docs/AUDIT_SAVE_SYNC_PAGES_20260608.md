# Audit Penyimpanan Input dan Sinkronisasi Antar Page

Tanggal audit: 2026-06-08
Scope: page input user pada `detail_project` dan alur edit import validasi pada `referensi`.

## Catatan Scope

Audit ini dilakukan sesuai instruksi terakhir: hanya pemeriksaan dan laporan, bukan perbaikan kode. File kode tidak dipatch dalam audit ini; satu-satunya perubahan yang dibuat adalah dokumen laporan ini.

Workspace saat audit tidak berada pada kondisi clean. `git status --short` menunjukkan banyak file modified/untracked lintas app (`detail_project`, `referensi`, `dashboard`, `subscriptions`, `templates`, dan lain-lain). Artinya laporan ini membaca kondisi working tree saat ini, bukan baseline branch yang bersih.

## Ringkasan Eksekutif

Secara umum, jalur penyimpanan utama yang sebelumnya dicurigai bermasalah sudah memiliki pola safety yang cukup baik: dirty state, guard sebelum reload, endpoint backend transactional, dan beberapa test regresi targeted sudah lolos.

Namun masih ada beberapa hal yang perlu disampaikan karena bisa mengganggu aktivitas user:

1. Page Jadwal Pekerjaan belum ikut mekanisme Sync LED antar page.
2. Template Jadwal production memiliki typo JavaScript `le.log(...)`.
3. Alur Edit Mode import validasi menandai perubahan sebagai tersimpan tanpa menunggu response server.
4. Alur Edit Mode import validasi belum memiliki `beforeunload` guard.
5. Legacy jadwal save handler masih punya kontrak payload yang tidak sinkron dengan backend v2, walaupun template aktif saat ini memakai stack modern.

## Adendum Keputusan Arsitektur Save/Load (menunggu konfirmasi)

Adendum ini ditambahkan setelah diskusi produk tentang asumsi **single account, single operator, single role**.

Kesimpulan audit sebelumnya masih valid untuk masalah stale UI dan false success. Namun rekomendasi optimistic-lock/dialog konflik perlu ditinjau ulang bila produk memilih workflow yang lebih tegas:

- **DB adalah SSOT.**
- HTML dinamis tidak boleh dicache browser (`no-store`) karena membawa bootstrap data.
- Redis/cache tetap relevan untuk read model/perhitungan berat, tetapi bukan sumber kebenaran edit.
- UI default sebaiknya **last-save-wins** bila asumsi single-user dikonfirmasi.
- UI tidak perlu menampilkan warning konflik hanya karena dua tab/page terbuka.
- Save gagal tetap harus jujur: tidak boleh menandai sukses, dan input lokal tetap dirty.

Implikasi terhadap rekomendasi audit:

| Area | Rekomendasi audit awal | Revisi bila policy single-user disetujui |
|---|---|---|
| Harga Items | Optimistic lock menurunkan risiko overwrite diam-diam | UI tidak mengirim token konflik; save terakhir menang; backend boleh tetap menerima token untuk API/internal guard |
| Template AHSP | Pertimbangkan optimistic lock seperti Harga | UI save normal last-save-wins; konflik multi-tab tidak ditampilkan |
| Rincian/Detail AHSP Gabungan | Gap optimistic lock dianggap risiko residual | Risiko diterima sebagai trade-off single-user; fokus ke read-after-write dan dirty state |
| Sync LED | Warning/sinkronisasi antar page | Jadikan indikator pasif/silent atau aksi manual; jangan menjadi dialog konflik multi-tab |
| Import Validate | Await server + beforeunload | Tetap wajib, karena ini bukan konflik multi-tab melainkan false success/local unsaved edit |

Fitur yang akan hilang bila revisi policy dieksekusi:

- Dialog konflik "Muat Ulang / Timpa" pada save normal.
- Konfirmasi kedua "Ya, Timpa" untuk stale tab.
- Proteksi eksplisit terhadap dua tab yang menyimpan objek sama secara bergantian.
- Test UI yang mengharuskan stale client token menghasilkan blocking `409`.

Trade-off yang diterima:

- Positif: workflow user lebih sederhana, tidak banyak warning, dan sesuai asumsi satu operator.
- Positif: implementasi frontend save lebih konsisten: load terbaru, save terakhir, update baseline dari server.
- Negatif: user yang sengaja mengedit objek sama di dua tab bisa menimpa perubahan sebelumnya tanpa dialog.
- Mitigasi wajib: `no-store`, read-after-write, dirty-state jujur, dan E2E reload-after-save.

Status: **belum dieksekusi sebagai perubahan kode dalam audit ini**. Perlu konfirmasi eksplisit sebelum mengubah Harga Items, Template AHSP, dan test yang saat ini mengunci perilaku optimistic-lock.

## Adendum Verifikasi Implementasi Terbaru (2026-06-08)

Adendum ini memasukkan hasil verifikasi independen atas implementasi save/sync sebelumnya. Temuan ini **masih relevan** dengan arah perbaikan single-user/single-role karena sebagian adalah gate produksi, bukan pilihan policy save.

### Terkonfirmasi benar

- Middleware `no-store` untuk halaman HTML `/detail_project/` sudah sesuai cakupan: HTML diberi `Cache-Control: no-store`, API/attachment tidak ikut terdampak.
- Sync LED sudah masuk ke 4 halaman output utama: Rekap RAB, Rincian RAB, Rekap Kebutuhan, dan Jadwal.
- Ketepatan `watch` sudah selaras: Template memantau pekerjaan + harga; Volume memantau pekerjaan.
- Import Validate sudah memakai `await persistCurrentEdits()` dan `beforeunload` guard.
- `sync_indicator.js` dan partial legacy sudah dihapus dari jalur JS/HTML.

### Launch-blocker yang harus masuk rencana implementasi

1. **Build/manifest Jadwal masih berisiko.**
   - Ada direktori build bersarang yang ter-commit: `detail_project/static/detail_project/detail_project/static/detail_project/dist/...`.
   - Ada beberapa hash Jadwal berbeda antara active source build, nested build lama, dan `staticfiles` lokal.
   - Walaupun `vite_entry` membaca manifest aktif yang benar, produksi memakai `ManifestStaticFilesStorage`; bila path hashed hasil Vite tidak ada setelah `collectstatic`, halaman Jadwal bisa 500.
   - Wajib ditutup dengan clean source tree: hapus artefak nested ter-commit, clean build, clean collectstatic, dan verifikasi satu hash end-to-end di staging.

2. **Migration drift `referensi/0024` masih relevan.**
   - `makemigrations referensi --check --dry-run` melaporkan pending migration untuk perubahan `segment_type`.
   - Ini harus digenerate, dikomit, dan diaplikasikan sebelum deploy agar skema DB sesuai model.

3. **Verifikasi staging/browser Fase 4 belum boleh dianggap selesai.**
   - Test unit/source tidak cukup untuk menutup risiko cache, manifest, dan apa yang benar-benar dimuat browser.
   - Gate final tetap harus membuka halaman target di staging, terutama Jadwal, dan memastikan aset hashed yang dimuat sama dengan manifest aktif.

### Temuan yang berubah status karena keputusan single-user

- Optimistic lock untuk Template AHSP/Harga Items tidak lagi menjadi target UI utama bila policy last-save-wins disetujui. Statusnya berubah menjadi **backend dormant guard**: endpoint boleh tetap mampu `409` bila token eksplisit dikirim, tetapi UI normal tidak mengirim token dan tidak menampilkan dialog konflik.
- Gap optimistic lock di Rincian/Gabungan bukan lagi blocker arsitektur bila single-user disetujui. Risiko overwrite multi-tab diterima sebagai trade-off produk.
- Sync LED bukan warning konflik. Perannya menjadi indikator pasif bahwa data hulu berubah dan halaman bisa disegarkan.

### Temuan minor yang perlu hati-hati

- `base_detail.html` masih memuat `sync_indicator.css`, dan CSS ini terkonfirmasi masih memuat style `.dp-sync-led`. File ini tidak boleh dihapus mentah-mentah. Perbaikan yang benar adalah memindahkan style LED aktif ke `sync_led.css` atau CSS utama, lalu menghapus legacy CSS.
- Lima test merah baseline/domain sebaiknya tidak dibiarkan diam-diam. Ekspektasi test perlu diselaraskan dengan perilaku produk yang dipilih atau diberi `xfail` dengan alasan eksplisit.

## Validasi Yang Dijalankan

Berikut validasi yang dijalankan tanpa mengubah kode:

```powershell
python manage.py test detail_project.tests_volume_pekerjaan_save_api detail_project.tests_template_ahsp_ui_regressions detail_project.tests_detail_ahsp_gabungan_ui detail_project.tests_change_status_sync --keepdb
```

Hasil: 23 tests OK.

```powershell
python manage.py check
```

Hasil: System check no issues.

```powershell
node --check detail_project/static/detail_project/js/list_pekerjaan.js
node --check detail_project/static/detail_project/js/volume_pekerjaan.js
node --check detail_project/static/detail_project/js/template_ahsp.js
node --check detail_project/static/detail_project/js/harga_items.js
node --check detail_project/static/detail_project/js/detail_ahsp_gabungan.js
node --check detail_project/static/detail_project/js/sync_led.js
node --check detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js
node --check detail_project/static/detail_project/js/src/modules/core/save-handler.js
node --check detail_project/static/detail_project/js/src/modules/app/EventBinder.js
```

Hasil: semua syntax check OK.

## Audit Per Page

### 1. List Pekerjaan

Status: relatif aman.

Evidence:

- Frontend punya dirty state dan guard sebelum unload: `detail_project/static/detail_project/js/list_pekerjaan.js:108`, `:182`.
- Save dikirim ke endpoint upsert: `detail_project/static/detail_project/js/list_pekerjaan.js:2056`.
- Backend save/upsert memakai `@transaction.atomic`: `detail_project/views_api.py:634`, `:951`.
- Response save dapat push source-change flags: `detail_project/static/detail_project/js/list_pekerjaan.js:2062`.

Catatan:

- Page ini adalah sumber perubahan untuk pekerjaan. Halaman downstream seperti Template AHSP, Volume, Harga, dan Rincian perlu bereaksi terhadap perubahan dari page ini.
- Tidak ditemukan indikasi kuat bahwa rename/import list pekerjaan masih gagal simpan pada kondisi working tree saat ini.

Risiko residual:

- Karena worktree sangat dirty, perlu E2E browser test untuk skenario "import template library -> save -> reload -> rename klasifikasi -> reload".

### 2. Volume Pekerjaan

Status: area yang sebelumnya rawan sudah tertutup secara targeted.

Evidence:

- Pending input volume di-flush sebelum save dan unload: `detail_project/static/detail_project/js/volume_pekerjaan.js:4895`, `:6432`, `:6712`.
- Backend payload membedakan volume kosong vs explicit zero melalui `has_quantity`: `detail_project/views_api.py:1827`.
- Frontend membaca `has_quantity`: `detail_project/static/detail_project/js/volume_pekerjaan.js:6285`.
- Endpoint save transactional: `detail_project/views_api.py:1700`.

Kesimpulan:

- Penyebab user merasa volume hilang saat reload kemungkinan besar berasal dari input yang belum masuk dirty set sebelum save/reload, terutama bila ada debounce/input event tertunda. Current code sudah punya guard untuk flush nilai input langsung dari DOM.

Risiko residual:

- Butuh E2E browser test untuk membuktikan skenario cepat: ketik volume -> langsung klik save -> reload.

### 3. Template AHSP

Status: relatif aman untuk save dan switching pekerjaan.

Evidence:

- Dirty state dan beforeunload ada: `detail_project/static/detail_project/js/template_ahsp.js:31`, `:2281`.
- Handler sync refresh ada dan memperhatikan dirty state: `detail_project/static/detail_project/js/template_ahsp.js:1488`.
- Save failure sekarang dilempar ulang sehingga auto-switch tidak dianggap sukses palsu: `detail_project/static/detail_project/js/template_ahsp.js:1049`, `:1863`.
- Backend detail AHSP save transactional: `detail_project/views_api.py:2111`.

Kesimpulan:

- Workflow "edit template AHSP -> pindah pekerjaan -> save/reload" lebih aman karena error save tidak lagi disamarkan sebagai sukses.

Risiko residual:

- Masih perlu E2E browser test untuk kombinasi formula, bundle expansion, dan sync reload.

### 4. Harga Items

Status: relatif aman.

Evidence:

- Dirty state dan beforeunload ada: `detail_project/static/detail_project/js/harga_items.js:98`, `:311`.
- Handler sync refresh ada: `detail_project/static/detail_project/js/harga_items.js:186`.
- Optimistic lock memakai `client_updated_at`: frontend `detail_project/static/detail_project/js/harga_items.js:650`, backend `detail_project/views_api.py:2913`.
- Endpoint save transactional: `detail_project/views_api.py:2887`.

Kesimpulan:

- Risiko overwrite diam-diam lebih rendah karena ada timestamp conflict handling.

Risiko residual:

- Konflik multi-tab tetap perlu diuji E2E, terutama skenario user memilih force overwrite.

### 5. Rincian AHSP / Detail AHSP Gabungan

Status: lebih aman daripada sebelumnya.

Evidence:

- Dirty guard dan beforeunload ada: `detail_project/static/detail_project/js/detail_ahsp_gabungan.js:10`, `:30`.
- Jika user membatalkan pindah selection saat dirty, selection lama dipulihkan: `detail_project/static/detail_project/js/detail_ahsp_gabungan.js:19`, `:99`.
- Backend save gabungan transactional: `detail_project/views_api.py:3808`.

Risiko residual:

- Belum terlihat optimistic lock seperti Harga Items. Jika dua tab mengedit rincian AHSP bersamaan, last write masih berpotensi menang.

### 6. Jadwal Pekerjaan

Status: penyimpanan progress modern terlihat aman, tetapi sync antar page belum lengkap.

Evidence penyimpanan:

- Template aktif memakai modern Vite module, bukan legacy script: `detail_project/templates/detail_project/kelola_tahapan_grid_modern.html:1047`.
- Modern save handler mengirim `mode: progressMode` (`planned` atau `actual`): `detail_project/static/detail_project/js/src/modules/core/save-handler.js:260`.
- Backend v2 menyimpan ke canonical weekly storage dan transactional: `detail_project/views_api_tahapan_v2.py:45`.
- Backend memvalidasi total progress existing + baru agar tidak lewat 100%: `detail_project/views_api_tahapan_v2.py:317`.

Temuan 6.1 - Jadwal belum ikut Sync LED:

- Page lain include `_sync_led.html`: Volume `volume_pekerjaan.html:17`, Template `template_ahsp.html:4`, Harga `harga_items.html:4`, Rincian `rincian_ahsp.html:4`.
- `kelola_tahapan_grid_modern.html` tidak include `_sync_led.html`.
- View jadwal hanya mengirim `side_active` dan data total week/month, belum mengirim `change_status` dan initial sync timestamps seperti page lain: `detail_project/views.py:311`.

Dampak:

- User bisa membuka Jadwal, lalu List Pekerjaan/Volume/Harga/AHSP berubah di page lain, tetapi Jadwal tidak memberi indikator bahwa konteksnya stale.
- Save progress tetap bisa berjalan, tetapi user bisa mengambil keputusan berdasarkan volume/struktur pekerjaan lama.

Rekomendasi:

- Tambahkan `_sync_led.html` pada page Jadwal dengan watch minimal `pekerjaan,volume,ahsp,harga,jadwal` atau `all`.
- Tambahkan `change_status` dan `_get_sync_initial_timestamps(project)` ke context `jadwal_pekerjaan_view`.
- Tambahkan handler `dp:sync-refresh-request` di app modern yang menolak refresh bila ada unsaved changes.

Temuan 6.2 - Typo JavaScript pada production branch:

- `detail_project/templates/detail_project/kelola_tahapan_grid_modern.html:1060` berisi `le.log(...)`, bukan `console.log(...)`.

Dampak:

- Saat branch production assets dipakai, browser akan melempar `ReferenceError: le is not defined`.
- Kemungkinan besar tidak menghentikan module utama, tetapi error ini mengganggu debugging, error monitoring, dan persepsi user bila console dibuka.

Rekomendasi:

- Ganti `le.log(...)` menjadi `console.log(...)`.

Temuan 6.3 - Legacy jadwal save handler stale:

- Legacy handler mengirim `mode: state.timeScale` (`weekly/daily/monthly`): `detail_project/static/detail_project/js/jadwal_pekerjaan/kelola_tahapan/save_handler_module.js:685`.
- Backend v2 menafsirkan `mode` sebagai progress mode (`planned/actual`).
- Modern handler sudah benar, tetapi legacy path tetap ada di repository.

Dampak:

- Jika rollback ke legacy dilakukan, input actual/realisasi berisiko jatuh ke default planned.

Rekomendasi:

- Update legacy handler agar mengirim progress mode eksplisit, atau hapus legacy rollback path bila sudah tidak dipakai.

### 7. Import Validate Report Referensi

Status: server-side SSOT edit sudah ada, tetapi UX save masih punya risiko.

Evidence positif:

- Edit per halaman disimpan ke JSON sidecar berdasarkan parent AHSP: `referensi/views/import_views.py:1298`.
- Endpoint save edit ada dan protected dengan `@require_POST`: `referensi/views/import_views.py:1411`.
- Export dari frontend menggabungkan DOM page saat ini, persisted edits page lain, dan server validated file sehingga export tetap lengkap walau report paginated: `referensi/views/import_views.py:3419`.

Temuan 7.1 - Save UI tidak menunggu response server:

- Button save memanggil `persistCurrentEdits();`, lalu langsung mengubah UI menjadi "Perubahan tersimpan untuk export": `referensi/templates/referensi/import_validate_report.html:812` sampai `:825`.
- `persistCurrentEdits()` baru melakukan `fetch(...)`: `referensi/templates/referensi/import_validate_report.html:845`.

Dampak:

- Bila endpoint save gagal atau jaringan putus, user tetap melihat status tersimpan.
- Export/pagination berikutnya bisa tidak membawa edit yang user kira sudah aman.

Rekomendasi:

- `await persistCurrentEdits()` sebelum UI menyatakan sukses.
- Bila gagal, tetap tampilkan tombol save dan counter dirty.

Temuan 7.2 - Tidak ada guard keluar halaman untuk edit yang belum disimpan:

- File ini punya tracking `changes`, tetapi tidak ditemukan `beforeunload` guard pada `import_validate_report.html`.

Dampak:

- Jika user edit lalu menutup tab/reload langsung tanpa klik Simpan atau pagination, perubahan bisa hilang.

Rekomendasi:

- Tambahkan `beforeunload` guard saat `changes.modified.length + changes.deleted.length > 0`.

## Audit Backend Penyimpanan

Pola backend untuk jalur utama sudah cukup baik:

- List Pekerjaan: `@transaction.atomic`.
- Volume Pekerjaan: `@transaction.atomic`.
- Template AHSP per pekerjaan: `@transaction.atomic`.
- Harga Items: `@transaction.atomic`.
- Rincian AHSP gabungan: `@transaction.atomic`.
- Jadwal v2 assign/reset/regenerate: `@transaction.atomic`.
- Source-change ack: `@transaction.atomic`.
- Parameter APIs: transactional untuk mutasi.

Catatan backend yang mencurigakan tetapi bukan bug fungsional langsung:

- `api_get_change_status` masih memiliki assignment awal `jadwal_changed_at = None` sebelum dihitung ulang dari model jadwal: `detail_project/views_api.py:4256`, `:4271`.
- Ini tidak terlihat merusak response karena nilai akhirnya dikirim pada `detail_project/views_api.py:4301`, tetapi placeholder seperti ini rawan membingungkan reviewer berikutnya.

## Sinkronisasi Antar Page

Mekanisme yang ada:

- `sync_led.js` polling `/change-status/` setiap 30 detik.
- `_sync_led.html` menyimpan baseline timestamp AHSP, Harga, Pekerjaan, Volume, dan Jadwal.
- `source_change_state.js` menyimpan pending reload job IDs dan pending volume reset IDs.
- Volume, Template AHSP, dan Harga Items sudah punya listener `dp:sync-refresh-request`.

Kondisi saat audit:

- Volume ikut watch `all`.
- Template AHSP watch `pekerjaan`.
- Harga Items watch `ahsp`.
- Rincian AHSP watch `ahsp,harga`.
- Jadwal belum ikut watch.
- List Pekerjaan belum memakai Sync LED, tetapi sebagai page sumber perubahan ini masih bisa diterima selama downstream page menerima sinyal.

Kesimpulan sync:

- Masalah terbesar bukan endpoint change-status, melainkan coverage page: Jadwal belum masuk siklus indikator/refresh.

## Tradeoff Rekomendasi

1. Menambah Sync LED pada Jadwal

Keuntungan:

- User tahu kapan jadwal stale karena perubahan list pekerjaan, volume, AHSP, atau harga.
- Lebih konsisten dengan page detail project lain.

Tradeoff:

- Ada polling tambahan setiap 30 detik pada page Jadwal.
- Perlu desain refresh yang hati-hati agar tidak membuang unsaved progress.

2. Membuat Import Validate Save benar-benar await server

Keuntungan:

- User tidak mendapat false success.
- Export lebih dapat dipercaya.

Tradeoff:

- Klik save terasa sedikit lebih lambat karena menunggu response.
- Perlu loading/error state tambahan.

3. Menambah beforeunload guard pada Import Validate Report

Keuntungan:

- Mengurangi risiko edit hilang karena reload/close tab.

Tradeoff:

- Browser prompt bisa terasa mengganggu jika user sering melakukan navigasi.

4. Membersihkan legacy jadwal handler

Keuntungan:

- Mengurangi risiko rollback ke path yang kontraknya sudah usang.

Tradeoff:

- Jika legacy masih dibutuhkan sebagai fallback, perlu effort menjaga dua jalur save tetap sinkron.

5. Menambahkan E2E browser test

Keuntungan:

- Bug yang bergantung pada debounce, reload, dirty state, dan modal lebih mudah tertangkap.

Tradeoff:

- Test suite lebih lama.
- Perlu fixture project yang stabil.

## Rekomendasi Prioritas

P1:

- Tambahkan Sync LED dan guarded refresh pada Jadwal Pekerjaan.
- Perbaiki save UX di `import_validate_report.html` agar menunggu response server.
- Tambahkan `beforeunload` guard pada `import_validate_report.html`.

P2:

- Perbaiki typo `le.log(...)` pada `kelola_tahapan_grid_modern.html`.
- Update atau hapus legacy `save_handler_module.js` agar tidak menyimpan actual progress sebagai planned saat rollback.

P3:

- Tambahkan E2E save-reload test untuk:
  - import template library list pekerjaan -> save -> reload,
  - rename klasifikasi -> save -> reload,
  - volume input cepat -> save -> reload,
  - template AHSP edit -> pindah pekerjaan -> reload,
  - harga item conflict multi-tab,
  - jadwal planned/actual save -> reload,
  - import validate edit -> save -> pagination/export.

## Kesimpulan

Tidak ada bukti kuat dari audit targeted bahwa bug penyimpanan utama masih terbuka pada List Pekerjaan, Volume, Template AHSP, Harga Items, dan Rincian AHSP dalam working tree saat ini. Validasi targeted juga lolos.

Yang masih perlu perhatian adalah coverage sinkronisasi Jadwal dan UX save pada Import Validate Report. Dua area ini bukan sekadar kosmetik: keduanya bisa membuat user percaya data sudah sinkron/tersimpan padahal belum tentu demikian.

---

## Adendum — Temuan Sistemik / Lintas-Halaman (ditambahkan 2026-06-08, pasca audit per-halaman)

Catatan: bagian ini melengkapi laporan di atas. Audit awal memverifikasi **source code per-halaman**. Adendum ini menambahkan temuan **lintas-halaman**, **runtime/serving**, dan **sisi baca-ulang (reload/cache)** yang menjadi akar sebagian besar gejala "save berhasil tetapi reload memuat data lama". Temuan ini teridentifikasi setelah audit awal disusun, dan menjelaskan mengapa kesimpulan audit awal ("tidak ada bukti kuat bug save masih terbuka") tidak cocok dengan pengalaman user di lapangan.

### Keterbatasan cakupan audit awal (meta)

Audit awal memverifikasi **kode sumber** (mis. `node --check` pada file di `detail_project/static/.../*.js`) dan menyimpulkan aman. Namun audit awal **tidak** memverifikasi: (a) **apa yang benar-benar disajikan/dijalankan browser**, dan (b) **sisi baca-ulang/caching** halaman. Dua titik buta inilah yang paling menjelaskan gejala kehilangan data.

### S1 — [KRITIS — SUDAH DIPERBAIKI] Pipeline aset basi: WhiteNoise menyajikan static lama

- Bukti: file source `detail_project/static/detail_project/js/volume_pekerjaan.js` berisi perbaikan terbaru (mis. `pendingInputIds`, `saved_job_ids`), tetapi salinan ter-collect `staticfiles/detail_project/js/volume_pekerjaan.js` (tertanggal Jan) berisi **0** penanda tersebut. `whitenoise.middleware.WhiteNoiseMiddleware` aktif dan menyajikan dari `STATIC_ROOT`.
- Dampak: browser menjalankan **JavaScript lama** melawan backend yang sudah berubah (endpoint, kontrak save, bootstrap baru) → perilaku save/reload kacau di **semua** halaman. Inilah alasan utama "perbaikan tidak berpengaruh".
- Status: **DIPERBAIKI**. Dijalankan `python manage.py collectstatic` (menyegarkan aset tersaji) + ditambahkan `WHITENOISE_AUTOREFRESH = True` pada `config/settings/development.py` agar dev server selalu menyajikan source terbaru tanpa collectstatic.
- Tindak lanjut: pastikan CI/deploy selalu menjalankan `collectstatic`; pertimbangkan asset hashing (ManifestStaticFilesStorage) untuk cache-busting produksi.

### S2 — [KRITIS — BELUM] Halaman dinamis tanpa `Cache-Control` / `never_cache`

- Bukti: tidak ada cache-middleware (selain WhiteNoise untuk static) dan tidak ada `never_cache`/`cache_control` pada view di `detail_project/views.py`. Respons HTML halaman edit tidak memasang header anti-cache.
- Dampak: browser boleh menyajikan halaman dari **bfcache/heuristic cache** saat reload/back → menampilkan snapshot **sebelum save**. Digabung dengan bootstrap SSR (S3), ini = gejala "save sukses, reload memuat data lama" walau DB sudah benar.
- Rekomendasi: pasang `Cache-Control: no-store` (`@never_cache` atau middleware terbatas) pada **semua** halaman edit detail_project. Satu titik, menutup risiko di semua halaman.

### S3 — [TINGGI — BELUM] Bootstrap SSR = read-after-load tanpa validasi kesegaran

- Bukti: Template/Volume/Harga kini menanam payload data ke HTML (`json_script`: `ta-bootstrap-detail`, `vp-bootstrap`, `hi-bootstrap`) dan JS men-seed dari situ lalu **melewati fetch AJAX awal**.
- Dampak: tampilan saat reload kini bergantung pada **kesegaran HTML**. Sebelum bootstrap, fetch AJAX selalu mengambil data segar sehingga lubang ini tertutup secara kebetulan; optimasi bootstrap membukanya bila HTML basi (lihat S2).
- Rekomendasi: jamin HTML selalu segar (S2), DAN/ATAU bootstrap defensif — setelah seed, validasi ringan ke server lalu rekonsiliasi bila berbeda.

### S4 — [TINGGI — BELUM] Halaman OUTPUT hilir tanpa Sync LED

- Bukti: `_sync_led.html` di-include oleh Volume/Template/Harga/Rincian AHSP saja. **Rekap RAB** (`rekap_rab.html`), **Rincian RAB** (`rincian_rab.html`), dan **Rekap Kebutuhan** (`rekap_kebutuhan.html`) tidak punya LED; view-nya pun belum mengirim `change_status` + initial timestamps.
- Dampak: halaman output tersebut menampilkan total/angka turunan dari pekerjaan+ahsp+koef+harga+volume. Setelah perubahan di halaman lain, user bisa melihat **angka basi tanpa peringatan**.
- Rekomendasi: tambahkan LED `watch="all"` (read-only → tombol sinkron cukup `location.reload()`), beserta context `change_status` + `_get_sync_initial_timestamps`.
- Catatan: temuan Jadwal (6.1) di laporan utama adalah instans dari kelas masalah yang sama; S4 memperluasnya ke seluruh halaman output.

### S5 — [SEDANG — BELUM] Ketepatan `watch` Sync LED

- **Template AHSP `watch="pekerjaan"`** tidak memantau `harga`, padahal Template menampilkan `harga_satuan` + menghitung jumlah per baris → bisa menampilkan harga basi tanpa flag. Saran: `watch="pekerjaan,harga"`.
- **Volume `watch="all"`** terlalu luas; Volume hanya bergantung pada list pekerjaan (+parameter). `all` memicu false-alert saat harga/ahsp/jadwal berubah. Saran: `watch="pekerjaan"`.

### S6 — [RENDAH — BELUM] Dead code indikator legacy

- Bukti: `sync_indicator.js` dimuat di `base_detail.html:88`, tetapi partial `_sync_indicator.html` tidak di-include halaman mana pun → skrip inert.
- Rekomendasi: hapus skrip + partial legacy agar tidak rancu dengan sistem `_sync_led` yang aktif.

### S7 — [TINGGI — SEBAGIAN] Belum ada asas read-after-write seragam

- Observasi: tiap halaman meng-commit *baseline* secara optimistik di klien, bukan dari respons server. Bila partial-save/konflik, baris yang **tidak** dikonfirmasi server bisa ter-commit sebagai "tersimpan" → hilang saat reload.
- Status: **SEBAGIAN** — Volume & Harga sudah memakai kontrak `saved_job_ids`/HTTP 207 sehingga hanya baris terkonfirmasi yang di-commit; baris gagal tetap dirty. Template sudah me-reject save gagal (tidak auto-switch). **Belum** diseragamkan sebagai satu util save untuk semua halaman (mis. Rincian AHSP belum punya optimistic-lock).
- Rekomendasi: standarkan satu pola "save → perbarui baseline dari respons server; jangan commit baris yang tak dikonfirmasi".

### Status ringkas temuan sistemik

| Kode | Temuan | Severitas | Status |
|---|---|---|---|
| S1 | Pipeline aset basi (WhiteNoise serve static lama) | Kritis | Diperbaiki |
| S2 | Halaman dinamis tanpa `never_cache` | Kritis | Belum |
| S3 | Bootstrap SSR tanpa validasi kesegaran | Tinggi | Belum |
| S4 | Rekap RAB, Rincian RAB, dan Rekap Kebutuhan tanpa Sync LED | Tinggi | Belum |
| S5 | Ketepatan `watch` (Template tanpa harga; Volume terlalu luas) | Sedang | Belum |
| S6 | Dead code `sync_indicator.js` | Rendah | Belum |
| S7 | Asas read-after-write belum seragam | Tinggi | Sebagian |

Rencana implementasi perbaikan untuk S2–S7 (dan tindak lanjut S1) disusun terpisah setelah adendum ini.

---

## Analisis Regresi — Akar Inti & Mengapa Dulu Tidak Terjadi

Pertanyaan kunci: "kenapa beberapa bulan lalu tidak mengalami masalah save/reload ini?" Menjawabnya memindahkan diagnosis dari *gejala per-halaman* ke **akar inti tunggal**.

### Bukti timeline (git)

- WhiteNoise **belum ada** sebelum Okt 2025. Pengenalan: `8a6200b7` (2025-10-21, "Export Done, Persiapan Runserver LAN"), dimatangkan di `025087e8` (2025-11-03) dan `87a85d50` (2025-11-07, "Phase 4 infrastructure for production deployment"). Cek `8a6200b7~1:config/settings/base.py` tidak memuat WhiteNoise/`STATIC_ROOT serving`.
- Commit terakhir repo: `69059282` (2026-02-11). Seluruh perubahan sejak itu (SSOT, repair command, perbaikan save) berada di **working tree yang belum di-commit**.
- `staticfiles/` ada di `.gitignore` → hasil `collectstatic` adalah artefak **lokal**. Sebelum intervensi audit ini, `staticfiles/detail_project/js/volume_pekerjaan.js` berisi **0** penanda perbaikan terbaru (versi lama ± Jan 2026).

### Akar inti

**Transisi "dev → siap-produksi" (Okt–Nov 2025) mengubah model penyajian aset, tetapi loop pengembangan lokal tidak ikut menyesuaikan.**

- **Sebelum WhiteNoise (≤ Okt 2025):** `runserver` (DEBUG) menyajikan static **langsung dari source via finders → selalu segar**. Edit JS langsung terlihat browser. Itulah sebabnya dulu tidak ada masalah ini.
- **Sesudah WhiteNoise (Okt 2025 →):** middleware menyajikan dari **`STATIC_ROOT` (hasil collect)**, bukan source. Sejak titik ini, perubahan JS/CSS **hanya** terlihat browser bila `collectstatic` dijalankan ulang.
- **Jan → Jun 2026:** `collectstatic` lokal terakhir ± Jan; sesudah itu source berevolusi besar (di working tree, belum di-commit) sementara `STATIC_ROOT` tetap versi Jan. **Selisih "yang disajikan" vs "yang diedit" makin lebar** → kerusakan save/reload makin parah seiring waktu.

### Inti yang sebenarnya (lebih dalam dari "static basi")

Bukan satu bug, melainkan **divergensi tiga lapis antara "yang berjalan" dan "yang diedit":**

1. **Aset:** `STATIC_ROOT` (JS Jan) vs source JS (Jun).
2. **Backend:** commit terakhir (Feb) vs working tree (Jun) yang belum di-commit.
3. **Konsekuensi:** browser menjalankan **JS Jan** melawan **backend yang terus berubah** (endpoint, kontrak save, bootstrap baru) → save ditolak/disalah-artikan, reload menampilkan logika lama. Setiap perbaikan menyasar **"yang diedit"**, padahal yang menyakiti user adalah **"yang berjalan"**.

Inilah inti yang menyatukan semua gejala, dan sebabnya tambalan per-halaman terasa tidak berpengaruh. Gejala berkorelasi **dengan waktu transisi produksi** — bukan dengan perubahan logika halaman tertentu.

### Implikasi terhadap temuan lain

- **S1** naik status: dari "bug" menjadi **akar inti / regresi proses** pada transisi siap-produksi.
- **S2/S3** (cache HTML + bootstrap SSR) adalah pembuka lubang sisi-baca yang relatif **baru** (bootstrap ditambahkan belakangan) — memperparah, tetapi **bukan** penyebab "beberapa bulan lalu" (saat itu belum ada bootstrap; fetch AJAX selalu segar).
- Bug kode asli (debounce volume, partial-save, conflict-dismiss) **nyata**, tetapi sebagian **tertutup/tercampur** oleh S1; sebagian memang sudah lama ada namun jarang terpicu.

### Pencegahan agar tidak terulang (akar, bukan gejala)

1. **Paritas dev↔prod untuk aset:** sudah dimitigasi dgn `WHITENOISE_AUTOREFRESH = True` (dev menyajikan source langsung). Wajibkan `collectstatic` di pipeline build/deploy; pertimbangkan `ManifestStaticFilesStorage` (hashed filename) untuk cache-busting otomatis di produksi.
2. **Kurangi divergensi working tree:** commit pekerjaan secara berkala — selisih besar antara HEAD (Feb) dan working tree (Jun) menyembunyikan apa yang sebenarnya berjalan dan menyulitkan diagnosis.
3. **Verifikasi "yang berjalan", bukan hanya "yang diedit":** audit/QA berikutnya harus memeriksa aset yang **benar-benar disajikan** server (mis. `curl /static/.../file.js` lalu cek penanda versi), bukan hanya `node --check` pada source.

---

## Matriks Re-Verifikasi Runtime (per halaman)

Tujuan: memilah gejala yang sudah hilang karena perbaikan aset (S1) versus bug nyata yang masih tersisa. Dijalankan **di browser dengan aset terbaru** (dev: `Ctrl+Shift+R`; staging: aset terkompilasi produksi), bukan dengan membaca ulang source.

| Halaman | Skenario uji (Simpan → reload) | Yang dibuktikan | Status |
|---|---|---|---|
| List Pekerjaan | tambah / rename / import → Simpan → reload | persist + sinyal ke halaman hilir | [ ] |
| Volume | ketik cepat → **langsung** Simpan → reload; isi `0` → reload | edit cepat tidak hilang; `0` ≠ kosong | [ ] |
| Template AHSP | edit koef → pindah pekerjaan → reload; simulasikan save gagal | tidak pindah saat gagal; koef persist | [ ] |
| Harga Items | edit → Simpan → reload; konflik 2 tab (Timpa / Batal / tutup X) | partial-save aman; dismiss ≠ timpa | [ ] |
| Rincian AHSP | edit → Simpan → reload | persist (+ uji 2 tab) | [ ] |
| Jadwal | planned/actual → Simpan → reload | progress persist | [ ] |
| Rekap RAB / Rincian RAB | ubah data hulu di halaman lain → buka halaman ini | angka tidak basi / ada peringatan | [ ] |

Cara cek "yang benar-benar berjalan": DevTools → Network → klik Simpan → pastikan request save sukses; dan pastikan berkas JS yang dimuat adalah versi terbaru (mengandung penanda perbaikan, mis. `saved_job_ids`).

---

## Kesiapan Produksi & Launching

Karena akar inti (S1) adalah masalah **penyajian aset**, kesiapan launching diukur dari pipeline aset produksi, bukan ulang-audit logika tiap halaman. Hasil pemeriksaan:

Catatan status terbaru: bagian "Kabar baik" di bawah benar untuk prinsip pipeline produksi, tetapi **belum cukup untuk verdict launch saat ini** karena verifikasi berikutnya menemukan artefak Vite Jadwal bersarang yang ter-commit dan migration drift `referensi/0024`. Dengan demikian, kesiapan launch harus mengikuti adendum verifikasi terbaru: bersihkan manifest/build Jadwal, generate migration pending, lalu jalankan staging/browser gate.

### Kabar baik — pipeline aset produksi sudah benar (S1 TIDAK akan menimpa user produksi)

- `config/settings/production.py`: `STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"` → **nama file di-hash** ⇒ cache-busting otomatis. Setelah deploy, browser user mengambil JS baru tanpa hard-refresh.
- `collectstatic` dijalankan di **build** (`Dockerfile`) dan **startup** (`docker-entrypoint.sh`).
- **Uji nyata:** `collectstatic` dengan `CompressedManifestStaticFilesStorage` **berhasil** — tidak ada referensi `{% static %}` rusak (bukan launch-blocker).
- `WHITENOISE_AUTOREFRESH = True` **hanya** di `development.py` → tidak bocor ke produksi.

Kesimpulan: gejala "JS basi" yang Anda alami adalah **artefak dev** (runserver + `STATIC_ROOT` lokal yang lama). Di produksi, manifest hashing mencegahnya. **Bukan blocker launch.**

### Risiko produksi yang masih perlu ditutup

| Kode | Item | Severitas launch | Tindakan |
|---|---|---|---|
| P-1 | **HTML dinamis tanpa `never_cache` (S2)** — pasca-deploy, browser yang meng-cache HTML lama bisa mereferensikan nama JS hashed lama (404) + bootstrap basi | **Tinggi** | Pasang `Cache-Control: no-store` pada semua halaman edit detail_project (seragam → menutup "masalah sama di page lain") |
| P-2 | **Working tree belum di-commit** (sejak 11 Feb) — semua perbaikan ada di working tree | **Tinggi (proses)** | Commit & tag sebelum build image produksi, agar rilis reproducible & bisa rollback |
| P-3 | Dockerfile `collectstatic ... 2>/dev/null \|\| true` menelan kegagalan build | Sedang | Hapus `\|\| true` agar build fail-fast (entrypoint sudah fail-fast, ini pengaman ganda) |
| P-4 | S4 (Rekap/Rincian/Jadwal tanpa Sync LED), S5 (watch), S7 (read-after-write) | Sedang (UX/akurasi) | Tutup sebelum launch untuk pengalaman konsisten; bukan blocker teknis |
| P-5 | S6 dead code `sync_indicator.js` | Rendah | Hapus |

### "Jangan buat masalah yang sama di page lain"

Cara menjamin keseragaman lintas-halaman (bukan tambal per-halaman):
1. **`never_cache` diterapkan satu kali ke SEMUA view edit detail_project** (List, Volume, Template, Harga, Rincian, Jadwal, Rekap, Rincian RAB) — bukan per halaman.
2. **Pola save read-after-write diseragamkan** (S7) sebagai satu util, sehingga halaman baru otomatis ikut pola aman.
3. **Sync LED diterapkan ke semua halaman output** (S4) dengan `_get_sync_initial_timestamps` + `change_status` di context.

### Checklist launch (ringkas)

- [ ] P-1: `never_cache` pada halaman edit/output detail_project.
- [ ] P-2: commit + tag working tree; build image dari commit.
- [ ] P-3: Dockerfile collectstatic fail-fast.
- [ ] Verifikasi staging: deploy → buka tiap halaman → `Ctrl+Shift+R` tidak diperlukan (manifest bekerja) → save→reload persist.
- [ ] Matriks re-verifikasi runtime per halaman (lihat bagian "re-verifikasi runtime") dijalankan di staging.
- [ ] S4/S5/S7 ditutup (disarankan), S6 dibersihkan.

### Verdict
Verdict awal "siap di-launch setelah P-1 dan P-2" sudah **superseded** oleh adendum verifikasi terbaru. Verdict saat ini: belum siap launch sampai build/manifest Jadwal bersih, migration drift `referensi/0024` ditutup, dan verifikasi runtime staging lulus. Tidak diperlukan re-audit arsitektur menyeluruh; yang menentukan adalah **verifikasi runtime di staging** dengan aset terkompilasi produksi yang bersih.

---

## Lampiran — Penjelasan untuk Owner (Non-Teknis)

### Analogi
Aplikasi seperti **restoran**. "Dapur" (server & database) sudah di-upgrade berkali-kali dengan resep baru. Tetapi pelayan masih memakai **buku menu lama** saat melayani tamu, sehingga sebagian pesanan tidak nyambung dengan dapur dan tampak "hilang". Bukan dapurnya rusak, bukan datanya hilang — **buku menu yang dipegang ketinggalan versi.**

### Sumber masalah
- Bagian aplikasi yang berjalan di browser pengguna terus kami perbaiki.
- Beberapa bulan lalu, saat aplikasi disiapkan untuk mode produksi, cara pengiriman "panduan tampilan" berubah dari "selalu versi terbaru" menjadi "dari salinan tersimpan yang harus disegarkan dulu".
- Langkah menyegarkan itu tidak rutin dijalankan di komputer pengembangan, sehingga browser menerima **versi lama** sementara dapurnya sudah baru → muncul gejala "sudah simpan tetapi setelah refresh kembali kosong".
- Intinya satu akar, bukan banyak bug terpisah: **yang dipakai pengguna bukan versi terbaru.**

### Apakah data hilang?
**Tidak.** Data yang benar-benar tersimpan aman dan utuh. Hanya segelintir input yang sejak awal tidak pernah berhasil terkirim yang perlu diisi ulang (pada satu proyek contoh: 7 baris volume).

### Solusi
1. Sudah dikerjakan: lingkungan pengembangan kini selalu memakai versi terbaru otomatis.
2. Kabar baik: setelan versi-produksi **sudah benar sejak awal** — saat live, sistem otomatis memberi pengguna versi terbaru tiap ada pembaruan, sehingga **masalah ini tidak menimpa pengguna asli.**
3. Beberapa pengaman kecil sebelum launch agar semua halaman konsisten dan tidak ada tampilan basi pasca-update.

### Status kesiapan
Secara teknis siap diluncurkan setelah 2 langkah penutup singkat (pengaman tampilan + menyimpan resmi semua perbaikan ke arsip versi), lalu uji akhir di lingkungan mirip-produksi.

### Ringkasan satu kalimat
Pengguna sempat memakai "versi lama" aplikasi karena cara distribusi versi berubah saat persiapan produksi; data aman, akarnya sudah ditemukan dan ditutup, setup produksi memang sudah mencegahnya — tinggal beberapa pengaman kecil sebelum siap diluncurkan.
