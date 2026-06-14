# Audit Komprehensif Page Template AHSP

**Tanggal audit:** 13 Juni 2026  
**Target:** `/detail_project/<project_id>/template-ahsp/`  
**Objek:** current working tree pada saat audit  
**Status:** **LULUS BERSYARAT - terdapat temuan High pada validasi, concurrency, bundle reset, dan propagasi master AHSP**

## 1. Ringkasan Eksekutif

Page Template AHSP merupakan editor komponen dan koefisien per pekerjaan. Page ini menangani:

- pemilihan pekerjaan REF, MOD, dan CUS;
- mode read-only dan editable;
- komponen Tenaga Kerja, Bahan, Peralatan, dan Pekerjaan Gabungan;
- formula koefisien berbasis parameter;
- bundle dari master AHSP atau pekerjaan lain;
- parameter dasar dan computed parameter;
- reset pekerjaan MOD ke referensi;
- save replace-all dan dual storage raw/expanded;
- sinkronisasi ke Harga Items, Rekap RAB, dan Rekap Kebutuhan;
- export CSV per pekerjaan dan JSON seluruh project.

Fondasi backend cukup kuat:

- page/API owner-scoped dan project aktif;
- initial detail pekerjaan pertama menggunakan SSR bootstrap;
- pekerjaan REF dijaga read-only di frontend dan backend;
- save memakai transaction atomic dan row lock;
- seluruh row divalidasi sebelum replace-all;
- bundle divalidasi dan diperluas ke storage terpisah;
- kegagalan expansion melakukan rollback eksplisit;
- formula sidecar disimpan dalam transaksi yang sama;
- orphan Harga Items dibersihkan setelah commit;
- save normal mencatat audit dan menjalankan cascade re-expansion;
- test backend dan frontend yang tersedia lulus.

Namun, production sign-off belum direkomendasikan karena:

1. Backend dapat menyimpan koefisien manual negatif.
2. UI sengaja tidak mengirim version token sehingga save full-state memakai last-save-wins.
3. Reset-to-reference tidak menjalankan cascade re-expansion untuk pekerjaan bundle yang bergantung padanya.
4. Perubahan master AHSP tidak memperbarui CUSTOM bundle yang sudah di-expand.

## 2. Ruang Lingkup

Audit mencakup:

- route, page view, API, model, service, dan export;
- template, JavaScript utama, shared formula/parameter modules, dan CSS;
- initial load, cache, loading, error, empty, read-only, dirty, dan stale state;
- filter dan pencarian pekerjaan;
- mode REF, REF_MODIFIED/MOD, dan CUSTOM/CUS;
- empat segmen item;
- add, edit, select, bulk delete, save, reload, dan reset;
- Select2 pencarian master AHSP dan pekerjaan bundle;
- formula koefisien inline dan modal;
- parameter sidebar dan computed parameter;
- CSV/JSON export;
- authorization, formula security, transaction, concurrency, rate limiting, dan SSOT;
- accessibility, keyboard, responsive behavior, dark mode, modal, toast, dan feedback user.

Audit visual browser belum dijalankan. Validasi langsung terhadap viewport, focus order, screen reader, Select2 positioning, touch, dan modal stacking masih diperlukan.

## 3. Komponen Utama

| Area | Implementasi |
|---|---|
| Route | `detail_project/urls.py` |
| Page view | `detail_project.views.template_ahsp_view` |
| API detail | `api_get_detail_ahsp` |
| API save | `api_save_detail_ahsp_for_pekerjaan` |
| API reset | `api_reset_detail_ahsp_to_ref` |
| Formula preload | `api_template_ahsp_formula_state` |
| Export | `export_template_ahsp_json` + CSV frontend |
| Template | `detail_project/templates/detail_project/template_ahsp.html` |
| JavaScript | `detail_project/static/detail_project/js/template_ahsp.js` |
| Shared parameter | `shared/param_store.js`, `shared/param_sidebar_editor.js` |
| Shared formula modal | `shared/formula_editor_modal.js`, `shared/formula_adapter.js` |
| CSS | `template_ahsp.css`, `template_ahsp_enhanced.css`, `param_sidebar_shared.css` |
| Raw storage | `DetailAHSPProject` |
| Expanded storage | `DetailAHSPExpanded` |
| Formula sidecar | `TemplateAhspKoefFormulaState` |

Ukuran implementasi utama:

- `template_ahsp.js`: sekitar 2.442 baris;
- `template_ahsp.html`: sekitar 742 baris;
- CSS page utama/enhanced: sekitar 1.151 baris;
- parameter sidebar dan formula editor juga memakai modul shared berukuran besar.

## 4. Audit Per Mode

### 4.1 Initial Load

**Status:** Bersyarat.

- Semua pekerjaan project dimuat di sidebar tanpa memfilter source type.
- Detail pekerjaan pertama di-bootstrap ke HTML.
- Pekerjaan lain lazy-loaded ketika dipilih.
- HTML page memakai kebijakan `no-store`.
- Loading placeholder dan retry tersedia saat fetch gagal.

Risiko tersisa:

- page menjadwalkan auto-reload seluruh pekerjaan berstatus pending `900 ms` setelah dibuka;
- auto-reload memakai jalur selection/render yang sama dengan interaksi user, sehingga tabel aktif dapat berkedip atau berganti sementara;
- cache frontend per pekerjaan mempunyai TTL/state sendiri;
- parameter dimuat terpisah;
- kebijakan last-save-wins membuat freshness token yang sudah tersedia tidak digunakan saat save normal.

### 4.2 Mode REF

**Status:** Baik secara enforcement.

- Detail referensi ditampilkan read-only.
- Input, add, delete, save, dan reset dikunci.
- Backend menolak save untuk pekerjaan REF.
- Jika detail project belum ada, backend fallback ke rincian referensi.

Catatan UX:

- user guide menyatakan REF dapat menjadi MOD melalui edit Template AHSP, sedangkan implementasi page mengunci REF;
- alur membuat REF menjadi MOD perlu dijelaskan secara konsisten melalui List Pekerjaan atau aksi khusus.

### 4.3 Mode REF_MODIFIED / MOD

**Status:** Fungsional.

- Komponen dan koefisien dapat diedit.
- Bundle tidak diizinkan.
- Reset-to-reference tersedia.
- Formula koefisien dapat disimpan.
- Source badge dan metadata aktif ditampilkan.

Masalah utama berada pada reset: pekerjaan lain yang memakai MOD tersebut sebagai bundle tidak otomatis dibangun ulang.

### 4.4 Mode CUSTOM / CUS

**Status:** Fungsional bersyarat.

- User dapat membuat item TK, BHN, ALT, dan LAIN.
- Item LAIN dapat mereferensikan master AHSP atau pekerjaan project.
- Bundle target kosong dicegah pada UI dan backend.
- Circular reference divalidasi backend.
- Save membentuk raw storage dan expanded storage.
- Item TK/BHN/ALT direct dan hasil expansion memakai `HargaItemProject` yang sama sebagai SSOT harga.
- Rekap Kebutuhan membaca komponen expanded, lalu mengalikan koefisien, kuantitas bundle, dan Volume Pekerjaan.
- Rekap RAB membaca komponen expanded untuk HSP, menerapkan markup, lalu mengalikan Volume Pekerjaan.

Kelemahan:

- validasi manual koefisien frontend dan backend tidak konsisten;
- API langsung masih dapat menyimpan koefisien negatif.
- perubahan pekerjaan yang direferensikan hanya aman jika cascade re-expansion berhasil;
- perubahan master AHSP referensi tidak mempunyai cascade ke CUSTOM yang sudah menyimpan hasil expansion;
- kontrak semantik koefisien `DetailAHSPExpanded` bertentangan antara dokumentasi model dan implementasi quantity-per-unit.

#### 4.4.1 Kontrak Lintas Page Mode CUSTOM

| Tahap | Sumber/Consumer | Kontrak yang Diharapkan | Status |
|---|---|---|---|
| Input direct | Template AHSP → `DetailAHSPProject` | TK/BHN/ALT menyimpan item dan koefisien user | Baik bersyarat |
| Bundle AHSP | `ref_ahsp` → `DetailAHSPExpanded` | Rincian master di-expand menjadi komponen dasar | Baik saat save |
| Bundle pekerjaan | `ref_pekerjaan` → `DetailAHSPExpanded` | Detail pekerjaan target di-expand rekursif | Baik saat save |
| Harga Item | `HargaItemProject` | Satu harga per kode item per project dipakai seluruh consumer | Baik, metadata dapat ditimpa oleh upsert terakhir |
| Volume | `VolumePekerjaan` | Satu volume per pekerjaan, independen dari mode REF/MOD/CUS | Baik |
| Rekap Kebutuhan | expanded × bundle quantity × volume | Menghasilkan total kebutuhan TK/BHN/ALT/LAIN | Baik jika expanded fresh |
| Rekap RAB | expanded × harga → HSP; HSP × markup × volume | Menghasilkan nilai pekerjaan dan total project | Baik jika expanded fresh |
| Cascade pekerjaan | perubahan target → dependent CUSTOM | Semua dependent dibangun ulang | Ada, tetapi failure tidak surfaced |
| Cascade master AHSP | perubahan `RincianReferensi` → CUSTOM | Dependent CUSTOM dibangun ulang atau ditandai stale | Belum ada |

**Catatan produk:** mode satu akun/satu role tidak menghapus kebutuhan konsistensi lintas page. Risiko utama bukan konflik role, melainkan apakah `DetailAHSPExpanded` masih merepresentasikan raw CUSTOM, master AHSP, Harga Item, dan Volume yang terbaru.

### 4.5 Formula Koefisien

**Status:** Baik bersyarat.

- Formula dapat memakai base/computed parameter.
- Formula raw disimpan di sidecar berdasarkan kode row.
- Evaluasi, preview, warning missing parameter, resolver, palette, dan modal tersedia.
- Backend memakai formula validator yang membatasi token, function, panjang, dan karakter.
- Hasil formula dibatasi ke range koefisien.
- Formula metadata ikut export/import dan project copy.

Catatan SSOT:

- sidecar memakai `row_key = kode`;
- perubahan kode item akan memindahkan identitas formula pada save replace-all;
- kode duplikat ditolak, tetapi row identity tetap bergantung pada business key yang dapat diedit.

### 4.6 Parameter Sidebar

**Status:** Fungsional, mewarisi temuan Volume Pekerjaan.

Template AHSP menggunakan endpoint parameter dan modul shared yang sama dengan Volume Pekerjaan:

- create/edit/delete base parameter;
- create/edit/delete computed parameter;
- import/export JSON/CSV/XLSX;
- optimistic timestamp sync;
- usage warning dan formula editor.

Karena itu, risiko berikut ikut berlaku:

- delete dependency hanya dijaga frontend;
- replace sync dapat sukses dengan warning setelah menghapus snapshot lama;
- computed expression belum divalidasi penuh oleh backend;
- conflict detection berbasis max row timestamp mempunyai blind spot setelah delete-all.

### 4.7 Add/Edit/Delete Row

**Status:** Baik bersyarat.

- Add row tersedia per segmen.
- Bulk delete per segmen menampilkan jumlah dan preview maksimal lima item.
- Delete belum langsung committed sampai save.
- Dirty state, before-unload, dan save-before-switch tersedia.
- Error save mencegah perpindahan pekerjaan.

Kelemahan UI:

- konfirmasi memakai dialog native;
- tidak ada undo row setelah delete;
- checkbox dinamis tidak mempunyai accessible name.

### 4.8 Bundle Search

**Status:** Fungsional.

- Select2 menggabungkan pekerjaan lokal dan master AHSP.
- Pencarian remote memakai delay dan minimum satu karakter.
- Sumber referensi ditampilkan.
- Pekerjaan bundle kosong dicegah.
- Timeout validasi frontend tidak memblokir save karena backend tetap memvalidasi.
- Bundle expansion failure melakukan rollback.

Browser UAT masih diperlukan untuk dropdown dekat topbar/bottom viewport, scrolling, keyboard, focus return, dan mobile.

### 4.9 Save dan Auto-Save Sebelum Pindah Pekerjaan

**Status:** Fungsional, concurrency tidak aman.

- Jika dirty, perpindahan pekerjaan meminta user menyimpan dulu.
- Save Promise harus selesai sebelum selection berpindah.
- Save gagal mempertahankan editor aktif dan dirty state.
- Save normal atomic.
- Server dapat mendeteksi conflict jika `client_updated_at` dikirim.

Tetapi frontend sengaja tidak mengirim token tersebut. Dua tab yang mengedit pekerjaan sama dapat saling menimpa full-state.

### 4.10 Reload dan Sync

**Status:** Bersyarat.

- Source-change jobs diberi badge “Perlu reload”.
- Auto reload hanya dilakukan ketika tidak dirty.
- Manual reload meminta konfirmasi jika edit belum disimpan.
- Template memantau scope `pekerjaan,harga`.
- Sync LED dapat di-acknowledge setelah seluruh pending job selesai.

Kelemahan:

- auto-reload dijadwalkan `900 ms` setelah page open;
- seluruh pending job di-fetch berurutan melalui `selectJobInternal()`;
- opsi `silent` tetap mengubah `activeJobId`, highlight sidebar, header aktif, loading placeholder, dan isi empat tabel sebelum selection awal dipulihkan;
- durasi delay bertambah linear terhadap jumlah pending job dan latency endpoint;
- banyak alur konfirmasi masih memakai native `confirm`;
- notification dan reload behavior perlu UAT dua sesi browser.

### 4.11 Reset to Reference

**Status:** Bersyarat.

- Hanya MOD yang dapat di-reset.
- Project dikunci selama reset.
- Detail raw, expanded, dan formula sidecar dibangun ulang.
- Cache di-invalidasi dan orphan dibersihkan.

Kelemahan:

- tidak menjalankan cascade terhadap pekerjaan lain yang mereferensikan target sebagai bundle;
- tidak membuat audit entry;
- tidak memakai version token untuk mencegah reset terhadap data yang baru diubah tab lain.

### 4.12 Export

**Status:** Baik bersyarat.

- CSV pekerjaan aktif mempunyai escaping.
- JSON mengekspor semua pekerjaan, item, formula, dan metadata bundle.
- JSON memakai prefetch untuk menghindari N+1.
- Export dibatasi 1.000 pekerjaan dan memasukkan warning dalam file.
- JSON export memiliki entitlement guard.

Kelemahan:

- response error 500 mengekspos `str(exception)`;
- limit 1.000 hanya diinformasikan di file, bukan sebelum download;
- dependency SheetJS dan Select2 berasal dari CDN tanpa SRI.

## 5. Implementasi UI/UX yang Sudah Baik

1. Layout mempunyai `<main>` dan sidebar pekerjaan yang jelas.
2. Pekerjaan dapat dipilih menggunakan Enter atau Space.
3. Filter REF/MOD/CUS memiliki count dan reset.
4. Active job menampilkan kode, uraian, satuan, dan source badge.
5. Empat segmen mempunyai heading dan action group.
6. Dirty indicator dan save spinner tersedia.
7. Save-before-switch mencegah perpindahan saat save gagal.
8. Delete terpilih menampilkan count dan preview.
9. Formula menyediakan inline state, modal, palette, preview, resolver, dan warning.
10. Sidebar parameter mempunyai search, tabs, import/export, dan sync indicator.
11. Focus-visible tersedia pada job item, add button, contenteditable, suggestion, dan palette.
12. Toolbar label mengecil pada viewport kecil.
13. Table wrapper mendukung data lebar.
14. Help modal menjelaskan source mode dan formula.
15. Error, loading, stale, dirty, read-only, dan empty state tersedia.

## 6. Temuan Audit

### TA-01 - HIGH - Backend Dapat Menyimpan Koefisien Manual Negatif

**Area:** Data integrity

Frontend menolak koefisien di bawah `0.000000000001`. Model mempunyai `MinValueValidator(0)`, tetapi endpoint save:

- hanya memastikan nilai dapat diparse;
- hanya menerapkan min/max pada row formula;
- tidak menolak koefisien manual negatif;
- menyimpan dengan `bulk_create`, yang tidak menjalankan `full_clean`.

**Dampak:**

- API langsung dapat menyimpan koefisien negatif;
- harga satuan pekerjaan dapat menjadi negatif;
- Rekap RAB dan Rekap Kebutuhan dapat terdistorsi;
- frontend dan backend mempunyai aturan domain berbeda.

**Rekomendasi:**

1. Terapkan `if koef < 0` atau, jika kebijakan harus positif, `if koef <= 0`.
2. Definisikan aturan nol secara eksplisit dan samakan frontend/backend.
3. Tambahkan database `CheckConstraint(koefisien__gte=0)`.
4. Tambahkan test koefisien negatif manual dan formula.

### TA-02 - HIGH - Full-State Save Menggunakan Last-Save-Wins

**Area:** Concurrency dan data loss

Backend sudah mempunyai detail-scoped version token dan response `409`. Frontend menyimpan token dalam cache tetapi sengaja tidak mengirim `client_updated_at`. Regression test juga mengunci kebijakan tersebut.

Row lock hanya menserialisasi proses save; lock tidak membuktikan bahwa payload berasal dari versi terbaru.

**Dampak:**

- tab kedua dapat menghapus/menimpa seluruh perubahan tab pertama;
- save replace-all memperbesar blast radius;
- user tidak diberi conflict warning;
- formula sidecar dan expanded storage ikut ditimpa.

**Rekomendasi:**

1. Aktifkan kembali pengiriman `client_updated_at`.
2. Pertahankan dialog Reload/Timpa yang sudah tersedia.
3. Force overwrite harus membutuhkan konfirmasi kedua.
4. Tambahkan browser UAT dua tab dan regression test frontend aktif.

### TA-03 - HIGH - Reset Tidak Melakukan Cascade Re-Expansion Bundle Dependents

**Area:** Cross-page SSOT

Save normal menjalankan `cascade_bundle_re_expansion(project, pkj.id)` setelah commit. Reset-to-reference hanya membangun ulang raw/expanded target, lalu invalidasi cache dan orphan cleanup.

Jika pekerjaan A dipakai sebagai bundle oleh pekerjaan B, reset A dapat meninggalkan expanded components B berdasarkan versi lama.

**Dampak:**

- Rekap RAB dan kebutuhan dapat menggunakan komponen stale;
- UI menyampaikan reset berhasil;
- inconsistency bertahan sampai pekerjaan dependent disimpan ulang.

**Rekomendasi:**

1. Jalankan cascade re-expansion setelah reset commit.
2. Jika cascade gagal, simpan status pending/error yang terlihat user.
3. Tambahkan test A direferensikan B, reset A, lalu verifikasi expanded B.

### TA-04 - MEDIUM - Reset Destruktif Tidak Tercatat di Audit Trail

Save normal mengambil old/new snapshot dan memanggil `log_audit`. Reset tidak melakukan hal yang sama.

**Dampak:** perubahan besar pada detail dan formula tidak dapat ditelusuri secara lengkap.

**Rekomendasi:** log old/new snapshot dengan action reset, user, timestamp, dan referensi sumber.

### TA-05 - MEDIUM - Reset Tidak Mempunyai Conflict Token

Reset mengambil project lock tetapi tidak menerima detail revision dari client. Tab lama dapat mereset pekerjaan setelah tab lain menyimpan perubahan baru.

**Rekomendasi:** kirim detail version pada reset dan tolak stale reset dengan `409`.

### TA-06 - MEDIUM - Parameter Sidebar Mewarisi Risiko Destructive Sync

Shared parameter editor memakai mode `replace` dan endpoint yang sama dengan Volume:

- delete dependency tidak dijaga backend;
- invalid entries dapat di-skip sebagai warning;
- frontend tetap menganggap sync berhasil;
- computed expression belum mempunyai validator backend setara formula koefisien.

**Rekomendasi:** remediasi parameter dibuat pada shared backend/service, bukan patch khusus per page.

### TA-07 - MEDIUM - Save/Reset Belum Mempunyai Rate Limit dan Payload Limit Spesifik

Endpoint write Template AHSP tidak memakai `@rate_limit(category='write')`. Global body limit 50 MB terlalu besar.

**Rekomendasi minimum:**

- rate limit per user/project;
- maximum row count per pekerjaan;
- body size limit;
- maximum formula/description length;
- maximum bundle depth dan expansion output;
- timeout/circuit breaker untuk cascade besar.

### TA-08 - MEDIUM - Export JSON Mengekspos Detail Exception

Pada error, endpoint mengembalikan:

```text
Export JSON gagal: <detail exception>
```

**Dampak:** nama class, database error, atau detail internal dapat bocor.

**Rekomendasi:** log detail server-side dan kirim pesan generik beserta correlation ID.

### TA-09 - MEDIUM - Konfirmasi Native Mendominasi Workflow Penting

Terdapat sembilan callsite `confirm()`/`window.confirm()` untuk:

- pindah pekerjaan;
- retry load;
- sync dirty;
- conflict;
- delete;
- reset;
- reload.

**Dampak:**

- tidak mengikuti dark mode/design system;
- copy panjang sulit dibaca;
- keyboard/focus behavior berbeda antar-browser;
- dialog memblokir thread;
- pilihan OK/Cancel kadang mewakili dua tindakan nonstandar.

**Rekomendasi:** gunakan satu modal service dengan tombol bernama sesuai tindakan.

### TA-10 - MEDIUM - Accessibility Tabel, Tabs, Checkbox, dan Feedback Belum Lengkap

Temuan:

- header tabel tidak memakai `scope="col"`;
- tab Parameter/Formula tidak mempunyai `aria-controls`;
- pane tidak mempunyai `role="tabpanel"` dan `aria-labelledby`;
- checkbox row dibuat dinamis tanpa `aria-label`;
- input invalid lebih banyak diberi visual class daripada `aria-invalid`;
- textarea formula tidak terhubung ke preview/error melalui `aria-describedby`;
- toast dinamis tidak mempunyai live-region semantics.

**Rekomendasi:** lengkapi semantics dan lakukan UAT screen reader.

### TA-11 - MEDIUM - Dependency Frontend CDN Tanpa SRI

Select2 CSS/JS dan SheetJS dimuat dari CDN tanpa Subresource Integrity.

**Risiko:** supply chain, availability, privacy, dan kesulitan menerapkan CSP.

**Rekomendasi:** self-host melalui package/build pipeline atau pin dengan SRI dan local fallback.

### TA-12 - MEDIUM - Formula Identity Bergantung pada Kode Item yang Dapat Diedit

Formula sidecar memakai `row_key = kode`. User dapat mengubah kode item. Pada replace-all, formula kemudian terasosiasi dengan kode baru dan sidecar kode lama dihapus.

**Risiko:**

- rename dan delete/recreate tidak dapat dibedakan;
- audit identity kurang stabil;
- duplicate/race pada kode memengaruhi formula mapping.

**Rekomendasi:** gunakan immutable row UUID untuk identity, sementara kode tetap business field.

### TA-17 - MEDIUM - Auto-Reload Saat Page Open Tidak Benar-Benar Berjalan di Background

**Area:** UI/UX, initial-load performance, dan state management

Detail pekerjaan pertama memang tersedia melalui SSR bootstrap. Namun, setelah page dibuka:

1. `scheduleAutoReloadPendingJobs('page-open')` menjadwalkan proses setelah `900 ms`.
2. Seluruh ID pada `pendingReloadJobs` diproses berurutan.
3. Setiap ID dipanggil melalui `selectJobInternal(..., forceRefresh=true)`.
4. Fungsi tersebut mengubah pekerjaan aktif, sidebar highlight, header, loading placeholder, dan melakukan `paint()` ke empat tabel.
5. Setelah semua target selesai, selection awal baru dipulihkan.

Opsi `silent: true` hanya menekan toast dan button state; prosesnya tetap memutasi UI aktif. Ini menjelaskan delay dan kesan bahwa semua tabel AHSP dimuat ulang sesaat setelah page tampil.

Perilaku tersebut masih aktif dan dikunci oleh regression test `test_template_auto_reloads_pending_jobs_on_open`. Jumlah request bukan selalu seluruh pekerjaan project, tetapi seluruh pekerjaan yang tercatat pending pada source-change state. Jika hampir semua pekerjaan pending, dampaknya setara reload massal.

**Dampak:**

- first paint SSR terasa tidak stabil karena diikuti second-phase reload;
- selection dan tabel dapat berkedip atau berubah tanpa aksi user;
- page dapat terasa lambat pada project besar atau koneksi lambat;
- request detail dilakukan serial sehingga waktu tunggu bertambah per pending job;
- user dapat mulai membaca atau berinteraksi dengan data yang kemudian diganti otomatis.

**Rekomendasi:**

1. Hapus `scheduleAutoReloadPendingJobs('page-open')` dan reload massal seluruh pending job.
2. Pertahankan stale/pending flag sebagai metadata, bukan pemicu mutasi UI massal.
3. Detail pekerjaan pertama memakai SSR bootstrap tanpa second reload.
4. Pekerjaan stale lain di-fetch hanya ketika dipilih user.
5. Jika pekerjaan aktif terbukti stale, refresh satu pekerjaan itu secara terkontrol dan pertahankan scroll/focus.
6. Pisahkan fungsi `fetchJobIntoCache(jobId)` dari `selectJobInternal()`.
7. Tambahkan browser/performance test yang memastikan page open tidak menghasilkan request waterfall dan lazy refresh tidak mengubah selection lain.

**Keputusan audit:** auto-reload massal saat page open tidak diperlukan pada arsitektur saat ini. Stale detection tetap diperlukan untuk perubahan lintas page/tab, tetapi resolusinya harus lazy per pekerjaan.

### TA-18 - HIGH - Perubahan Master AHSP Tidak Memperbarui CUSTOM Bundle yang Sudah Di-expand

**Area:** Cross-page SSOT dan data integrity

CUSTOM dapat menyimpan `ref_ahsp` langsung ke `AHSPReferensi`, lalu rincian master disalin secara komputasional ke `DetailAHSPExpanded`. Signal pada app Referensi hanya meng-invalidasi cache Referensi. Tidak ditemukan mekanisme yang:

- mencari `DetailAHSPProject` yang mereferensikan master tersebut;
- membangun ulang expanded storage pekerjaan CUSTOM;
- menandai pekerjaan/project sebagai stale;
- memberi tahu user bahwa Rincian AHSP, Rekap Kebutuhan, dan Rekap RAB masih memakai snapshot lama.

Akibatnya, perubahan atau import ulang `RincianReferensi` dapat membuat FK bundle menunjuk master terbaru sementara expanded components tetap berasal dari versi lama.

**Dampak:**

- Harga Item baru dari master tidak muncul;
- koefisien kebutuhan dapat memakai komposisi lama;
- HSP dan Rekap RAB dapat stale;
- UI tidak menunjukkan bahwa re-save/rebuild diperlukan.

**Rekomendasi:**

1. Tetapkan product rule: bundle master bersifat live-reference atau immutable snapshot.
2. Jika live-reference, buat dependency index `ref_ahsp → pekerjaan CUSTOM` dan cascade re-expansion setelah perubahan master commit.
3. Jika snapshot, simpan source revision/hash/timestamp dan tampilkan versi snapshot pada UI.
4. Import master massal sebaiknya membuat rebuild queue, bukan cascade sinkron tanpa batas.
5. Tambahkan UAT perubahan komponen/koefisien master lalu verifikasi Harga Item, Rincian AHSP, Kebutuhan, dan Rekap RAB.

### TA-19 - MEDIUM - Kontrak Koefisien Expanded Bertentangan dengan Implementasi

**Area:** SSOT semantics dan maintainability

Model dan API expansion mendeskripsikan `DetailAHSPExpanded.koefisien` sebagai koefisien final yang sudah dikali multiplier bundle. Implementasi aktual memakai quantity semantic:

- expanded menyimpan koefisien komponen per satu unit bundle;
- koefisien bundle tetap berada pada `DetailAHSPProject`;
- Rekap RAB dan Rekap Kebutuhan mengalikan `expanded.koefisien × source_detail.koefisien`;
- Rincian AHSP menampilkan harga satuan bundle per unit, lalu menghitung jumlah dengan koefisien bundle.

Jalur utama saat ini konsisten, tetapi nama field, help text, contoh model, dan docstring API menyatakan hal sebaliknya.

**Risiko:** consumer baru dapat lupa multiplier atau mengalikannya dua kali. API detail expansion juga mengembalikan total per-unit dengan dokumentasi “already multiplied”, sehingga makna angka bagi frontend/integrator tidak eksplisit.

**Rekomendasi:** tetapkan quantity semantic sebagai kontrak resmi, ubah dokumentasi/help text, dan expose field eksplisit seperti `component_koef_per_bundle_unit`, `bundle_quantity`, dan `effective_koef`.

### TA-20 - MEDIUM - Kegagalan Cascade Dependent Tidak Terlihat User

**Area:** Reliability dan observability

Save pekerjaan target dijalankan lebih dahulu. Cascade dependent berjalan `on_commit`. Pada cascade:

- `_populate_expanded_from_raw()` menangkap sebagian error expansion dan hanya menulis log;
- loop cascade menangkap exception lain lalu melanjutkan;
- save induk tetap merespons sukses;
- seluruh ID dependent tetap diperbarui `detail_last_modified`, termasuk yang mungkin gagal dibangun ulang.

**Dampak:** user melihat save berhasil, tetapi CUSTOM dependent dapat mempunyai expanded storage kosong/parsial dan laporan downstream stale.

**Rekomendasi:**

1. Kembalikan structured result per dependent: success, failed, reason, component count.
2. Jangan menandai `detail_last_modified` sukses untuk dependent gagal.
3. Simpan status `rebuild_pending/rebuild_failed`.
4. Tampilkan warning pada Template AHSP dan page laporan sampai rebuild berhasil.
5. Sediakan retry job yang idempotent dan test rantai A → B → C.

### TA-21 - MEDIUM - Coverage Belum Mengunci Kontrak CUSTOM Sampai Laporan Akhir

Test yang ada mencakup rollback expansion save, export metadata bundle, source resolution, MOD menolak bundle, dan sebagian SSOT Harga Item. Belum ditemukan test otomatis end-to-end yang mengunci:

1. CUSTOM direct TK/BHN/ALT → Harga Item → Kebutuhan → Rekap RAB.
2. CUSTOM bundle AHSP dengan koefisien lebih dari satu.
3. CUSTOM bundle pekerjaan dan nested bundle.
4. Perubahan harga sesudah expansion.
5. Perubahan volume sesudah expansion.
6. Perubahan target pekerjaan dan cascade dependent.
7. Perubahan master AHSP setelah CUSTOM tersimpan.
8. Kesamaan nilai UI Rincian AHSP, API Kebutuhan, dan API Rekap RAB.

**Rekomendasi:** buat contract-test fixture kecil dengan angka deterministik dan assert hasil setiap tahap, bukan hanya jumlah row atau status HTTP.

### TA-13 - LOW - Export 1.000 Pekerjaan Tidak Diperingatkan Sebelum Download

File berisi `warning`, tetapi user baru mengetahui limit setelah membuka JSON.

**Rekomendasi:** tampilkan warning/toast sebelum download atau gunakan streaming/export async tanpa truncation.

### TA-14 - LOW - Empty State Belum Mengarahkan User

Sidebar hanya menampilkan “Belum ada pekerjaan yang bisa ditampilkan.”

**Rekomendasi:** sediakan CTA ke List Pekerjaan. Untuk filter kosong, tampilkan CTA Reset Filter yang berbeda dari project benar-benar kosong.

### TA-15 - LOW - Alur REF ke MOD Tidak Konsisten dengan Dokumentasi

Implementasi mengunci REF dan backend menyuruh user menggunakan page lain, sedangkan user guide menyatakan edit Template AHSP mengubah REF menjadi MOD.

**Rekomendasi:** tetapkan satu product rule, perbarui help text, API message, dan dokumentasi.

### TA-16 - LOW - Responsive Tetap Bergantung pada Tabel Lebar

Breakpoint dan sidebar responsive tersedia, tetapi empat tabel editable, Select2, formula input, dan dua sidebars tetap berat pada layar kecil.

**Rekomendasi:** sediakan card/row editor mobile atau nyatakan page desktop-optimized dengan minimum supported viewport yang jelas.

## 7. Penilaian SSOT

### Kondisi yang Sudah Baik

- `DetailAHSPProject` menyimpan raw user input.
- `DetailAHSPExpanded` menyimpan hasil ekspansi untuk perhitungan.
- Formula sidecar disimpan bersama detail secara atomic.
- Harga item memakai project-level SSOT.
- Save normal membangun ulang expanded storage.
- Kegagalan expansion rollback.
- Orphan cleanup menjaga Harga Items.
- Source type dan read-only ditentukan backend.
- Formula validator server digunakan untuk koefisien.

### Kelemahan SSOT

- concurrency guard backend tidak digunakan frontend;
- reset tidak menjalankan cascade dependent;
- perubahan master AHSP tidak menandai atau membangun ulang CUSTOM dependent;
- kontrak koefisien expanded berbeda antara dokumentasi dan implementasi;
- kegagalan cascade pekerjaan dependent tidak menjadi state yang terlihat user;
- parameter dependency policy masih frontend-only;
- formula row identity memakai mutable code;
- frontend/backend berbeda dalam aturan minimum koefisien;
- reset tidak masuk audit trail.

### Target SSOT

1. Immutable detail row identity.
2. Canonical coefficient validation service.
3. Version token wajib pada save dan reset.
4. Semua mutasi detail memicu dependency cascade yang sama.
5. Semua mutasi mencatat audit.
6. Parameter dependency graph dijaga backend.

## 8. Rekomendasi Restrukturisasi

### Tahap 1 - Integrity

1. Tolak koefisien negatif backend dan tambah DB constraint.
2. Aktifkan optimistic locking UI.
3. Tambahkan cascade reset.
4. Catat reset pada audit trail.
5. Tambahkan reset revision token.

### Tahap 2 - Shared Domain Services

Pisahkan:

- `validate_detail_rows`;
- `build_detail_change_plan`;
- `apply_detail_change_plan`;
- `rebuild_expanded_detail`;
- `cascade_detail_dependents`;
- `audit_detail_change`.

Save, reset, import, dan source transition harus memakai service yang sama.

### Tahap 3 - Frontend

1. Migrasikan native confirm ke modal service.
2. Gunakan immutable row key.
3. Pisahkan job navigation, editor state, bundle picker, formula controller, dan save controller.
4. Satukan toast dan error mapping.
5. Tambahkan explicit loading/conflict/reset states.

### Tahap 4 - UI/UX dan Accessibility

1. Lengkapi semantics tabel/tab/form.
2. Tambahkan accessible checkbox labels.
3. Tambahkan live-region toast.
4. Perjelas REF/MOD transition.
5. Buat mobile editing strategy.
6. Jalankan browser UAT lintas mode dan viewport.

## 9. Pengujian yang Dijalankan

### Django

Suite utama:

```text
detail_project.tests_template_ahsp_formula_state
detail_project.tests_template_ahsp_ui_regressions
detail_project.tests_formula_server_validation
detail_project.tests_formula_ui_regressions
detail_project.tests_orphan_autocleanup
detail_project.tests_item_ssot
detail_project.tests_change_status_sync
detail_project.tests_harga_items_export
detail_project.tests_page_security_audit
detail_project.tests_page_cache_headers
```

**Hasil:** 150 test ditemukan, seluruh test aktif lulus, 40 guard WIP di-skip.

### Frontend

```text
vol_formula_engine.test.js
formula_adapter.test.js
shared_param_store.test.js
xss_governance_guard.test.js
feedback_governance_guard.test.js
```

**Hasil:** 5 file, 61 test, seluruhnya lulus.

### JavaScript Syntax

```text
node --check template_ahsp.js
node --check shared/param_sidebar_editor.js
node --check shared/formula_editor_modal.js
```

**Hasil:** seluruh file valid.

### Test Tambahan yang Wajib

1. Koefisien manual negatif ditolak.
2. Koefisien nol sesuai aturan domain.
3. Dua tab edit pekerjaan sama menghasilkan 409.
4. Reset stale ditolak.
5. Reset pekerjaan bundle target membangun ulang dependent.
6. Reset mencatat audit old/new snapshot.
7. Parameter delete yang masih dipakai ditolak backend.
8. Formula identity bertahan saat kode display diubah.
9. Rate/payload limits.
10. Browser UAT Select2, modal, keyboard, screen reader, dark mode, dan mobile.
11. CUSTOM direct item → Harga Item → Volume → Kebutuhan → Rekap RAB.
12. CUSTOM bundle AHSP quantity lebih dari satu dan nested reference.
13. CUSTOM bundle pekerjaan A → B → C serta cascade setelah B/C berubah.
14. Perubahan master AHSP menandai/rebuild seluruh CUSTOM dependent.
15. Kegagalan rebuild dependent menghasilkan visible failed state.
16. Page open tidak melakukan reload massal pending job.

## 10. Prioritas Remediasi

| Urutan | Item | Gate |
|---|---|---|
| P0 | TA-01 validasi koefisien backend | Wajib sebelum production |
| P0 | TA-02 optimistic locking aktif | Wajib untuk multi-tab safety |
| P0 | TA-03 cascade reset bundle | Wajib untuk konsistensi laporan |
| P0 | TA-18 kebijakan dan propagasi perubahan master AHSP | Wajib untuk CUSTOM live-reference |
| P1 | TA-04 dan TA-05 reset audit/version | Data governance |
| P1 | TA-06 shared parameter integrity | SSOT lintas page |
| P1 | TA-07 rate/payload limit | Availability |
| P1 | TA-08 generic export error | Security hardening |
| P1 | TA-09 modal governance | UI sign-off |
| P1 | TA-10 accessibility semantics | Accessibility sign-off |
| P1 | TA-11 dependency self-hosting | Supply-chain hardening |
| P2 | TA-12 immutable row identity | Maintainability/integrity |
| P1 | TA-17 background reload tanpa mutasi UI aktif | Initial-load UX/performance |
| P1 | TA-19 kontrak quantity semantic expanded | SSOT contract |
| P1 | TA-20 visible cascade failure state | Reliability |
| P1 | TA-21 cross-page contract tests | Regression safety |
| P2 | TA-13 sampai TA-16 | UX refinement |

## 11. Browser UAT Matrix

| Area | Skenario |
|---|---|
| Initial | SSR first job, lazy job, loading, failed load, retry, request waterfall |
| Filter | REF/MOD/CUS combinations, search, zero result, reset |
| REF | seluruh editor benar-benar read-only |
| MOD | edit, formula, delete, save, reset |
| CUS | direct TK/BHN/ALT, bundle AHSP, bundle pekerjaan, nested bundle, quantity > 1 |
| Formula | inline, modal, palette, missing parameter, invalid formula |
| Save | Ctrl+S, save-before-switch, failure, rollback |
| Conflict | dua tab save dan reset |
| Sync | List Pekerjaan berubah, Harga berubah, dirty refresh, pending reload tidak mengubah selection/tabel aktif |
| CUSTOM chain | Template → Harga Item → Volume → Rincian AHSP → Kebutuhan → Rekap RAB |
| Reference change | target pekerjaan berubah, master AHSP berubah, cascade sukses/gagal |
| Export | CSV escaping, JSON limit, entitlement, failure |
| Accessibility | keyboard-only, focus order, announcement, screen reader |
| Responsive | 320, 360, 576, 768, 1024, desktop, zoom 200% |
| Theme | light, dark, reduced motion, forced colors |
| Select2 | viewport atas/bawah, scroll, keyboard, mobile |

## 12. Keputusan Produk dan Alur yang Perlu Didiskusikan

Bagian ini memuat perilaku yang belum tentu salah secara teknis, tetapi kontrak bisnisnya ambigu atau berpotensi menghasilkan workflow yang tidak diharapkan.

### D-01 - Definisi HSP Tidak Tunggal

Saat ini terdapat tiga istilah/nilai:

- `E_base`: biaya komponen sebelum markup;
- `G`: harga satuan setelah markup;
- `HSP` pada backend diisi `E_base`, tetapi sidebar Rincian AHSP menampilkan `G` dengan label “HSP”.

Rekap RAB memakai `G`, tetapi mempunyai fallback ke `harga_satuan`, `HSP`, atau `unit_price`. Jika field `G` hilang pada payload lama/parsial, fallback dapat memakai nilai sebelum markup.

**Keputusan disepakati:**

- `component_cost_before_markup` menjadi nama kanonik biaya komponen sebelum markup (`E_base`);
- `markup_amount` menjadi nama kanonik nilai profit/markup (`F`);
- `unit_price_after_markup` menjadi nama kanonik harga satuan final (`G`);
- total RAB pekerjaan dihitung dengan `unit_price_after_markup × volume`;
- field lama `HSP`, `E_base`, `F`, `G`, dan `unit_price` dipertahankan sementara sebagai compatibility alias;
- Rekap RAB, Rincian AHSP, export, dan consumer lain dipindahkan bertahap ke field kanonik;
- alias lama baru boleh dihapus setelah seluruh consumer dan regression test lintas-page telah dimigrasikan.

Label UI yang direkomendasikan:

1. Biaya Komponen Sebelum Markup.
2. Profit/Markup.
3. Harga Satuan Setelah Markup.

**Status keputusan:** final, tidak memerlukan diskusi produk lanjutan. Implementasi harus bersifat aditif agar tidak mengubah hasil perhitungan saat ini.

### D-02 - Apakah Rincian AHSP Page Laporan atau Page Editor Pricing?

Rincian AHSP terlihat sebagai page inspeksi/perhitungan, tetapi user dapat mengubah override Profit/Margin per pekerjaan dari page tersebut. Perubahan itu langsung memengaruhi Rekap RAB.

**Risiko workflow:** user membuka laporan untuk memeriksa angka, tetapi sebenarnya dapat mengubah pricing source tanpa berpindah ke page konfigurasi.

**Keputusan disepakati:** Rincian AHSP memang merupakan tempat yang sah untuk melihat dan mengubah override Profit/Markup per pekerjaan. Fitur ini dipertahankan.

Persyaratan UX dan governance:

- tampilkan markup default project dan effective markup pekerjaan;
- bedakan status `Menggunakan Default` dan `Override`;
- jelaskan bahwa perubahan memengaruhi Harga Satuan Setelah Markup dan Rekap RAB;
- sediakan aksi `Kembalikan ke Default`;
- catat nilai lama, nilai baru, pekerjaan, user, dan timestamp pada audit trail;
- setelah save, refresh nilai Rincian AHSP dan Rekap RAB;
- perubahan markup tidak boleh mengubah koefisien, Volume Pekerjaan, atau Rekap Kebutuhan;
- tampilkan feedback save sukses/gagal dan effective markup terbaru.

**Status keputusan:** final. Fitur edit markup pada Rincian AHSP valid; kebutuhan tersisa adalah kejelasan status, dampak, dan auditability.

### D-03 - Perubahan Source Pekerjaan Menghapus Volume dan Jadwal

Ketika source type atau referensi pekerjaan berubah dari List Pekerjaan, backend menghapus:

- detail Template AHSP;
- `VolumePekerjaan`;
- seluruh assignment `PekerjaanTahapan`;
- formula volume;
- formula koefisien Template AHSP.

Menghapus detail/formula dapat dipahami karena basis AHSP berubah. Namun, volume pekerjaan dan penempatan jadwal sering merupakan identitas kuantitas/waktu pekerjaan, bukan bagian dari sumber AHSP.

**Keputusan disepakati:** pergantian source REF/MOD/CUS memang harus menghapus detail AHSP, volume, assignment tahapan/jadwal, formula volume, dan formula koefisien terkait. Data lama tidak boleh dipertahankan karena dapat tidak lagi sesuai dengan sumber, satuan, atau komposisi pekerjaan yang baru.

Tambahkan konfirmasi eksplisit sebelum perubahan dijalankan. Konfirmasi harus menyebut dampak secara rinci, bukan hanya “data akan di-reset”:

> Perubahan sumber pekerjaan akan menghapus Detail AHSP, Volume Pekerjaan, formula volume, formula koefisien, dan assignment jadwal/tahapan untuk pekerjaan ini. Tindakan ini tidak dapat dibatalkan.

Rekomendasi UX:

- tampilkan identitas pekerjaan dan perubahan source lama → baru;
- gunakan tombol aksi bernama `Ubah Sumber dan Hapus Data Terkait`;
- sediakan tombol `Batal`;
- setelah berhasil, tampilkan ringkasan data yang dihapus dan page yang perlu diisi kembali;
- catat perubahan source dan reset turunannya pada audit trail.

**Status keputusan:** final. Logika penghapusan dipertahankan; yang perlu ditambahkan adalah informed confirmation dan feedback setelah aksi.

### D-04 - Missing Volume dan Volume Nol Diproses Sama

API Volume membedakan `has_quantity`, tetapi perhitungan Rekap Kebutuhan dan Rekap RAB mengubah missing volume menjadi `0`. Akibatnya pekerjaan yang belum diisi dan pekerjaan yang memang volumenya nol sama-sama menghasilkan total nol.

**Risiko:** laporan tampak valid dan seimbang, padahal input belum lengkap.

**Keputusan disepakati:** nilai volume yang belum diisi tetap dinormalisasi menjadi `0` pada jalur perhitungan agar Rekap RAB dan Rekap Kebutuhan tidak gagal karena `null` atau nilai kosong. Namun, status “belum diisi” harus tetap dapat dibedakan dari volume eksplisit `0`.

Kontrak yang digunakan:

- `quantity_for_calculation = quantity ?? 0`;
- `has_quantity = false` berarti volume belum pernah diisi;
- `has_quantity = true` dan `quantity = 0` berarti user secara eksplisit menetapkan nol;
- Rekap RAB dan Rekap Kebutuhan tetap dapat dibuka dan dihitung;
- tampilkan warning non-blocking `N pekerjaan belum memiliki volume`;
- export tetap diizinkan, tetapi membawa metadata/catatan kelengkapan volume;
- tidak diperlukan pemblokiran workflow selama belum ada proses finalisasi atau sign-off resmi.

**Status keputusan:** final. Normalisasi nol dipertahankan untuk keamanan perhitungan; completeness tracking ditambahkan sebagai informasi terpisah.

### D-05 - CUSTOM Bundle Master: Live Reference atau Snapshot

FK `ref_ahsp` terlihat seperti live reference, tetapi expanded components berperilaku seperti snapshot saat save. Perubahan master tidak otomatis mengubah project.

**Keputusan disepakati:** gunakan reference synchronization dengan perlindungan nilai milik user.

Aturannya:

- komponen/koefisien yang masih inherited dari AHSP Referensi mengikuti koreksi sumber utama;
- nilai yang memang menjadi input user, terutama `bundle_quantity`, tidak boleh berubah;
- komponen hasil expansion tetap merupakan derived storage dan dapat dibangun ulang;
- perubahan master tidak boleh mengubah project secara diam-diam tanpa status dan audit.

Implementasi minimum yang dipilih:

1. Pertahankan `DetailAHSPProject` dan `DetailAHSPExpanded`.
2. Simpan revision/hash dan waktu sinkronisasi master pada raw bundle.
3. Ketika revision master berubah, tandai `reference_update_available`.
4. Rebuild expanded storage dari master terbaru melalui proses sinkronisasi.
5. Pertahankan koefisien/jumlah bundle yang dimasukkan user.
6. Catat nilai/revision lama dan baru pada audit trail.

Dampak client-side dibatasi pada:

- badge/status bahwa pembaruan referensi tersedia;
- aksi sinkronisasi;
- konfirmasi dan ringkasan komponen yang berubah;
- feedback sukses atau gagal.

Editor tabel, struktur utama page, dan workflow normal tidak perlu direstrukturisasi. Override per komponen internal bundle belum diperlukan karena komponen expanded bukan area edit langsung.

**Status keputusan:** final dengan implementasi skala kecil sampai menengah, bukan restrukturisasi database besar.

### D-06 - Partial Expanded Storage Tidak Mempunyai Readiness Contract

Consumer memakai raw fallback hanya jika suatu pekerjaan sama sekali tidak mempunyai expanded row. Jika cascade helper menghasilkan sebagian expanded row dan melewatkan bundle yang gagal, consumer menganggap expanded storage valid dan komponen gagal hilang dari laporan.

**Keputusan disepakati:** `detail_ready` tidak cukup hanya berarti expanded row lebih dari nol. Tambahkan readiness dan diagnostic state yang dapat menjelaskan sumber masalah.

Status minimum:

- `expanded_ready`;
- `expanded_source_revision`;
- `expanded_error`;
- `rebuild_pending`;
- `rebuild_failed`;
- expected versus actual bundle/component count.

Warning dipicu:

1. Setelah save Template AHSP menghasilkan expansion gagal atau parsial.
2. Setelah sinkronisasi master referensi gagal.
3. Setelah cascade dependent gagal.
4. Ketika revision raw/master lebih baru daripada expanded.
5. Saat membuka Rincian AHSP, Rekap Kebutuhan, atau Rekap RAB dengan expanded state tidak valid.
6. Saat export dilakukan dari data yang mempunyai warning.

Setiap diagnostic wajib membawa:

- pekerjaan ID, kode, dan uraian;
- bundle/raw row ID dan kode;
- source type: direct, `ref_ahsp`, atau `ref_pekerjaan`;
- tabel sumber masalah, misalnya `DetailAHSPProject`, `DetailAHSPExpanded`, `RincianReferensi`, atau `HargaItemProject`;
- field dan nilai bermasalah;
- expected value/count/revision;
- actual value/count/revision;
- dampak ke Rincian AHSP, Rekap Kebutuhan, dan Rekap RAB;
- tindakan pemulihan yang direkomendasikan.

Contoh informasi:

```text
Pekerjaan : CUS-001 - Pemasangan Bata
Bundle    : BUNDLE-BATA (raw row #128)
Sumber    : DetailAHSPProject.ref_ahsp_id = 45
Masalah   : RincianReferensi tidak menghasilkan komponen
Expected  : minimal 1 komponen expanded
Actual    : 0 DetailAHSPExpanded
Dampak    : HSP dan kebutuhan pekerjaan belum lengkap
Tindakan  : periksa AHSP Referensi #45 lalu jalankan sinkronisasi ulang
```

Severity:

- `Info`: pembaruan referensi tersedia;
- `Warning`: stale atau rebuild pending;
- `Error`: expansion gagal/parsial dan laporan belum lengkap;
- `Critical`: circular dependency atau integrity mismatch lintas banyak pekerjaan.

Consumer laporan tetap dapat menampilkan hasil untuk diagnosis, tetapi wajib memberi label `Data belum lengkap`. Export tetap dapat dilakukan dengan catatan status sampai tersedia proses finalisasi/sign-off resmi.

**Status keputusan:** final. Warning harus actionable dan menunjuk tabel, baris, field, serta nilai yang menjadi sumber masalah.

### D-07 - Harga Item Menjadi SSOT Harga Sekaligus Metadata Item

`HargaItemProject` bukan hanya menyimpan harga, tetapi juga menjadi sumber canonical untuk kode, uraian, kategori, dan satuan. Upsert dari Template/AHSP dapat memperbarui metadata tersebut dan memproyeksikannya ke seluruh raw/expanded rows yang memakai item sama.

**Keputusan disepakati:** arsitektur konversi Harga Item saat ini sudah sesuai dengan kebutuhan lapangan.

Kontrak yang dipertahankan:

- Template AHSP menyimpan koefisien dan satuan dasar AHSP;
- `HargaItemProject.harga_satuan` menyimpan harga ekuivalen per satuan dasar;
- `ItemConversionProfile` menyimpan satuan pembelian, harga pasar, dan faktor konversi;
- helper menghitung `harga satuan dasar = harga pasar ÷ factor_to_base`;
- Rincian AHSP menghitung biaya menggunakan koefisien AHSP × harga satuan dasar;
- Rekap Kebutuhan dapat menampilkan kebutuhan dalam base unit atau market unit;
- conversion profile tidak boleh mengubah koefisien atau satuan dasar Template AHSP.

Contoh:

```text
Template AHSP : 120 kg semen
Harga pasar   : Rp60.000 per zak
Konversi      : 1 zak = 40 kg
Harga dasar   : Rp1.500 per kg
Biaya AHSP    : 120 × Rp1.500
```

Guard yang tetap diperlukan:

- perubahan `market_unit` tidak menulis ke `HargaItemProject.satuan`;
- perubahan conversion profile hanya memperbarui harga ekuivalen per base unit;
- `_upsert_harga_item()` tidak boleh mengganti satuan dasar canonical secara tidak sengaja karena metadata dari sumber lain;
- perubahan metadata canonical harus melalui validasi atau aksi khusus dengan preview dampak.

**Status keputusan:** final. Tidak diperlukan restrukturisasi fitur konversi; hanya penguatan guard pada metadata dan satuan dasar.

### D-08 - LAIN Mempunyai Dua Makna

Kategori `LAIN` dipakai sebagai:

- bundle yang harus di-expand; dan
- pada beberapa jalur legacy/master, komponen dasar LAIN yang tidak cocok dengan AHSP lain.

Save CUSTOM justru menolak LAIN tanpa referensi. Artinya makna kategori berbeda tergantung sumber/jalur data.

**Keputusan disepakati:** pisahkan dua makna `LAIN` dengan terminology yang eksplisit untuk sistem dan user.

Label UI:

- `Biaya Lain Langsung`;
- `Pekerjaan Gabungan`.

System type:

- `OTHER_DIRECT`;
- `WORK_BUNDLE`.

Struktur compatibility yang direkomendasikan:

```text
kategori       = TK | BHN | ALT | LAIN
item_type      = DIRECT | OTHER_DIRECT | WORK_BUNDLE
reference_type = null | AHSP | PROJECT_JOB
```

Aturan:

- `OTHER_DIRECT` tidak mempunyai `ref_ahsp` atau `ref_pekerjaan`, serta wajib mempunyai Harga Item;
- `WORK_BUNDLE` wajib mempunyai tepat satu referensi;
- `reference_type = AHSP` menggunakan `ref_ahsp`;
- `reference_type = PROJECT_JOB` menggunakan `ref_pekerjaan`;
- `WORK_BUNDLE` di-expand ke komponen dasar;
- `OTHER_DIRECT` diteruskan ke expanded storage seperti item direct;
- placeholder harga bundle tidak digunakan sebagai sumber biaya.

UI Template AHSP menyediakan aksi terpisah:

1. `Tambah Biaya Lain Langsung`.
2. `Tambah Pekerjaan Gabungan dari AHSP`.
3. `Tambah Pekerjaan Gabungan dari Project`.

Migrasi data lama:

- `LAIN` dengan referensi → `WORK_BUNDLE`;
- `LAIN` tanpa referensi → `OTHER_DIRECT`;
- kategori `LAIN` lama dipertahankan sementara agar consumer lama tidak rusak.

**Status keputusan:** final. Pemisahan tipe dilakukan secara aditif untuk menghilangkan ambiguitas tanpa migrasi kategori besar secara langsung.

### D-09 - Scope Rekap Kebutuhan dan Rekap RAB Berbeda

Rekap Kebutuhan mendukung filter tahapan, proporsi volume, serta periode waktu. Rekap RAB menghitung total pekerjaan dari volume penuh. Kedua angka benar untuk scope masing-masing, tetapi user dapat membandingkannya seolah berasal dari scope yang sama.

**Keputusan disepakati:** perbedaan scope Rekap Kebutuhan dan Rekap RAB memang disengaja dan sesuai konteks bisnis.

- Rekap RAB menggunakan volume total pekerjaan untuk nilai biaya seluruh project.
- Rekap Kebutuhan dapat menggunakan seluruh project, tahapan, proporsi volume, atau periode waktu.
- Tidak diperlukan penyamaan logika perhitungan kedua page.

Persyaratan UI dan export:

- tampilkan badge scope aktif, misalnya `Seluruh Project`, `Tahapan: Struktur`, atau `Periode: Juni 2026`;
- tampilkan volume efektif/proporsi yang dipakai;
- hasil scoped tidak boleh diberi label total project;
- export menyertakan mode, filter, tahapan, periode, proporsi, dan generated timestamp;
- tampilkan informasi ketika scope aktif berbeda dari scope Rekap RAB;
- pertahankan opsi `Seluruh Project` pada Rekap Kebutuhan sebagai basis pembanding.

**Status keputusan:** final. Logika tetap berbeda; yang diperkuat adalah context visibility dan metadata scope.

### D-10 - Batas Kedalaman Bundle adalah Aturan Teknis, Belum Aturan Produk

Expansion membatasi nested bundle sekitar tiga level. Batas ini mencegah recursion berlebihan, tetapi belum terlihat sebagai aturan saat user memilih referensi.

**Keputusan disepakati:** nested bundle dibatasi maksimal empat level pekerjaan dengan definisi yang eksplisit.

```text
Level 1: pekerjaan utama
Level 2: bundle yang direferensikan
Level 3: bundle di dalam bundle
Level 4: bundle terdalam yang masih diperbolehkan
```

Rantai `A → B → C → D` valid, sedangkan `A → B → C → D → E` ditolak.

Guard backend:

- gunakan konstanta `MAX_BUNDLE_LEVELS = 4`;
- circular reference selalu ditolak;
- tetapkan `MAX_EXPANDED_COMPONENTS` agar branching besar tidak menghasilkan ledakan row;
- hentikan validasi/expansion segera ketika limit terlampaui;
- gunakan transaction dan bulk operation;
- cascade besar dapat dialihkan ke rebuild queue berdasarkan threshold;
- aturan yang sama berlaku untuk input UI, API, import, dan maintenance rebuild.

Client-side hanya melakukan prospective validation ringan ketika referensi dipilih. Response cukup memuat:

- valid/tidak valid;
- depth;
- estimated component count;
- reference chain;
- alasan penolakan.

Expansion penuh tetap server-side dan expanded tree tidak perlu dikirim ke browser.

Contoh error:

> Referensi menghasilkan kedalaman 5 level: A → B → C → D → E. Maksimum yang diperbolehkan adalah 4 level.

**Status keputusan:** final. Batas empat level diterapkan bersama batas total expanded component agar dampak performa tetap terkendali.

## 13. Keputusan Audit

Page Template AHSP mempunyai arsitektur dual-storage dan formula yang cukup matang. Atomic replace-all, rollback expansion, SSR bootstrap, owner isolation, formula validation, orphan cleanup, dan cascade pada save normal adalah implementasi yang baik.

Page **belum direkomendasikan sebagai final production-ready** sebelum TA-01, TA-02, TA-03, dan TA-18 ditutup atau TA-18 diputuskan secara eksplisit sebagai immutable snapshot. Temuan tersebut dapat menghasilkan nilai perhitungan salah, kehilangan perubahan antar-tab, atau laporan stale yang terlihat sukses.

Audit ini menilai editor Template AHSP, bukan fitur Template Library. Review lama `03_Template_AHSP.md` lebih banyak membahas Template Library dan tidak menggantikan laporan ini.

---

## 14. Verifikasi Independen (Claude, 13 Juni 2026)

Temuan diperiksa ulang terhadap kode kerja. Yang diverifikasi langsung: **TA-01, TA-02, TA-03, TA-04, TA-05, TA-08, TA-11, TA-17, TA-18 — semuanya valid, tidak ada false positive.** Sisanya (TA-06/07/09/10/12/13/14/15/16/19/20/21) konsisten dengan kode/struktur; TA-06 mewarisi temuan Volume yang sudah saya verifikasi terpisah (VP-02/03/05/06). Keputusan produk D-01..D-10 adalah keputusan owner yang sudah final — tidak saya nilai ulang.

### 14.1 Verdict per temuan (yang diverifikasi langsung)

| Temuan | Verdict | Bukti verifikasi |
|---|---|---|
| TA-01 Koefisien manual negatif | **DIKONFIRMASI** | `views_api.py:2250-2251` hanya menolak `koef is None`; range check (`:2256`) **hanya** untuk formula rows; `bulk_create(..., ignore_conflicts=True)` (`:2483`) tidak memanggil `full_clean`, jadi `MinValueValidator(0)` model tidak berlaku. Lihat penajaman 14.2. |
| TA-02 Full-state save last-save-wins | **DIKONFIRMASI** | Backend punya token + 409 (`:2165-2196`), tetapi frontend `template_ahsp.js:1735-1739` **sengaja** tidak mengirim `client_updated_at` (baris pengiriman di-comment, ada komentar "POLICY single-user / last-save-wins"); path `force_overwrite:true` ada (`:1806`). |
| TA-03 Reset tanpa cascade re-expansion | **DIKONFIRMASI** | Reset (`:2846-2918`) hanya `_populate_expanded_from_raw(project, pkj)` untuk pekerjaan itu sendiri (`:2899`); tidak ada `cascade_bundle_re_expansion` (satu-satunya panggilan ada di save `:2772`). |
| TA-04 Reset tak masuk audit trail | **DIKONFIRMASI** | Tidak ada `log_audit` di fungsi reset (`:2846-2918`); `log_audit` hanya di jalur save (`:1348`, `:2814`). |
| TA-05 Reset tanpa conflict token | **DIKONFIRMASI** | Reset mengambil `select_for_update` (`:2855`) tetapi tidak menerima/memeriksa `client_updated_at` → tidak ada 409. |
| TA-08 Export JSON bocorkan exception | **DIKONFIRMASI (lebih luas)** | Pola `f'Export ... gagal: {str(e)}'` ada di **puluhan** endpoint export (`:4786, 4824, 4857, 4892, 5292, 5390, 5463, 5612, ...`), bukan hanya Template AHSP JSON. Lihat 14.2. |
| TA-11 CDN tanpa SRI | **DIKONFIRMASI** | `template_ahsp.html:15` (Select2 CSS), `:24` (Select2 JS), `:735` (SheetJS) semua tanpa `integrity`. |
| TA-17 Auto-reload massal saat page open | **DIKONFIRMASI** | `scheduleAutoReloadPendingJobs` (`template_ahsp.js:1271`) memproses `pendingReloadJobs`; dijadwalkan saat page open, melalui jalur selection yang sama. |
| TA-18 Master AHSP tak propagasi ke CUSTOM expanded | **DIKONFIRMASI** | Signal app `referensi` hanya memanggil `rebuild_search_cache()` (`referensi/models.py:18-19`); tidak ada mekanisme yang mencari `DetailAHSPProject.ref_ahsp` lalu rebuild `DetailAHSPExpanded`. Satu-satunya sentuhan lintas-app ke `DetailAHSPProject` adalah command `purge_ahsp_referensi` yang men-`detach ref_ahsp=None`. |

### 14.2 Penajaman bukti

- **TA-01 — pesan error menyesatkan + `ignore_conflicts` menyembunyikan row gagal.** String error di `:2251` berbunyi "Harus ≥ 0…" padahal kode hanya menolak `None` — jadi nilai manual negatif lolos meski pesannya menjanjikan sebaliknya. Selain `full_clean` yang dilewati `bulk_create`, flag `ignore_conflicts=True` (`:2483`) juga **diam-diam membuang** row yang melanggar unique constraint; kode duplikat memang sudah dipra-validasi (`:2261`), tapi flag ini menutup kasus yang lolos. Fix paling kokoh: validasi `koef < 0` (atau `<= 0` sesuai kebijakan) di loop + `CheckConstraint(koefisien__gte=0)` di DB (sesuai rekomendasi TA-01 butir 1 & 3).

- **TA-08 — ini pola sistemik, bukan satu endpoint.** Karena `{str(e)}` muncul di hampir semua exporter (Excel/PDF/Word/CSV/JSON di banyak page), perbaikannya sebaiknya **satu wrapper error export bersama** (log detail + correlation ID, balas pesan generik), bukan tambalan di `export_template_ahsp_json` saja. Ini sejalan dengan tema lintas-page di 14.3.

### 14.3 Catatan konsistensi lintas-page (page ke-4)

Template AHSP mengonfirmasi ulang pola sistemik yang sama di Dashboard, List Pekerjaan, dan Volume:
- **Tanpa CSP** di `config/` — diperparah TA-11 (Select2 + SheetJS CDN tanpa SRI).
- **Concurrency last-write-wins / `Max(updated_at)`** — di sini bahkan **sengaja dimatikan di frontend** (TA-02) walau backend sudah menyediakan 409; reset tidak punya token sama sekali (TA-05). Ini varian paling tajam dari tema VP-06/LP-03.
- **Bocoran `str(e)`** pada error path (TA-08) — sistemik di seluruh exporter.
- **Cascade/propagasi parsial yang sukses secara diam-diam** (TA-03 reset, TA-18 master, TA-20 cascade dependent) — sejalan dengan tema "sukses parsial `ok:true`" di LP/VP.

Rekomendasi tetap: putuskan empat hal ini di tingkat aplikasi (CSP bertahap; konvensi concurrency revisi monotonik; wrapper error export; kontrak readiness/`expanded_ready` lintas consumer — yang sebagian sudah diputuskan owner di D-06).

### 14.4 Kalibrasi prioritas

Urutan P0 (TA-01, TA-02, TA-03, TA-18) sudah tepat. Catatan effort:
- **TA-01 adalah quick win** (tambah satu guard `koef < 0` + DB constraint) dengan dampak integritas tinggi — dahulukan.
- **TA-02 sebagian besar adalah keputusan kebijakan**, bukan kerja teknis besar: backend + dialog Reload/Timpa sudah ada; tinggal meng-uncomment pengiriman `client_updated_at` (`:1739`) dan menyesuaikan regression test yang saat ini mengunci last-save-wins. Murah, tapi perlu keputusan owner karena saat ini "single-user policy" tampaknya disengaja.
- **TA-03 dan TA-18** lebih berat (cascade + dependency index + kontrak snapshot/live-reference) dan terkait keputusan D-05/D-06 — jadwalkan sebagai unit kerja tersendiri di fase perbaikan.
