# Audit Komprehensif Page Volume Pekerjaan

**Tanggal audit:** 13 Juni 2026  
**Target:** `/detail_project/<project_id>/volume-pekerjaan/`  
**Objek:** current working tree pada saat audit  
**Status:** **LULUS BERSYARAT - temuan integritas formula dan parameter perlu ditutup**

## 1. Ringkasan Eksekutif

Page Volume Pekerjaan merupakan salah satu page paling kompleks di aplikasi. Page ini tidak hanya mengelola quantity, tetapi juga:

- formula quantity per pekerjaan;
- parameter dasar dan computed parameter;
- opaque parameter ID;
- autocomplete dan formula palette;
- formula editor modal;
- import/export parameter;
- export page ke Excel, PDF, Word, dan JSON;
- dirty tracking, autosave, conflict handling, dan sinkronisasi lintas page.

Fondasi implementasinya relatif matang:

- page dan API dibatasi berdasarkan owner;
- initial volume dan formula state telah di-bootstrap dari server;
- quantity memakai presisi canonical 3 desimal dan `ROUND_HALF_UP`;
- formula divalidasi client-side dan server-side;
- formula tidak dieksekusi melalui JavaScript `eval`;
- parameter memakai server-generated opaque ID;
- optimistic conflict handling sudah tersedia untuk parameter dan formula;
- dirty row yang gagal pada save volume dipertahankan;
- UI mempunyai search, filter summary, keyboard shortcut, responsive rules, dark mode, reduced motion, dan live feedback;
- 139 test Django dan 55 test frontend terarah berhasil.

Namun, terdapat masalah integritas yang membuat page belum dapat diberi final production sign-off:

1. Formula-state API dapat menerima sebagian item, mengembalikan `ok: true`, lalu frontend menghapus dirty marker untuk semua item termasuk formula yang gagal.
2. Delete parameter tidak mempunyai dependency enforcement di backend.
3. Replace sync parameter menghapus data lama sebelum melewati seluruh validasi, tetapi tetap mengembalikan sukses dengan warnings.
4. Computed parameter belum memakai validasi formula server yang sama dengan formula volume.

## 2. Ruang Lingkup

Audit mencakup:

- route, page view, authorization, dan cache policy;
- SSR/bootstrap initial state;
- template, JavaScript, CSS, dan responsive behavior;
- input quantity manual;
- formula quantity inline dan modal;
- parameter dasar;
- computed parameter;
- sidebar, tab, search, palette, dan autocomplete;
- summary filter dan collapse/expand;
- import/export parameter;
- export page;
- save, autosave, undo, dirty tracking, dan before-unload;
- conflict detection dan multi-tab behavior;
- integration dengan List Pekerjaan, Rekap RAB, Rincian AHSP, dan sync status;
- keamanan, transaction behavior, rate limiting, dan payload limits;
- accessibility dan UI/UX seluruh kontrol yang dapat ditelusuri dari kode.

Audit visual langsung melalui browser belum dilakukan. Karena itu, contrast, focus order, screen-reader announcement, touch behavior, dan modal stacking masih perlu browser UAT.

## 3. Komponen Utama

| Area | Implementasi |
|---|---|
| Route | `detail_project/urls.py` |
| Page view | `detail_project.views.volume_pekerjaan_view` |
| API | `detail_project/views_api.py` |
| Template | `detail_project/templates/detail_project/volume_pekerjaan.html` |
| JavaScript utama | `detail_project/static/detail_project/js/volume_pekerjaan.js` |
| Runtime sidebar | `detail_project/static/detail_project/js/volume_runtime.js` |
| Numeric patch | `detail_project/static/detail_project/js/volume_numeric_patch.js` |
| Formula engine | `detail_project/static/detail_project/js/vol_formula_engine.js` |
| CSS | `detail_project/static/detail_project/css/volume_pekerjaan.css` |
| Export adapter | `detail_project/exports/volume_pekerjaan_adapter.py` |
| Model quantity | `VolumePekerjaan` |
| Model formula | `VolumeFormulaState` |
| Model parameter | `ProjectParameter`, `ProjectComputedParameter`, `ParameterSequence` |

Ukuran implementasi saat audit:

- `volume_pekerjaan.js`: sekitar 7.642 baris;
- `volume_pekerjaan.html`: sekitar 662 baris;
- `volume_pekerjaan.css`: sekitar 2.372 baris.

## 4. Audit Per Mode

### 4.1 Initial Load dan SSR Bootstrap

**Status:** Baik.

Page view mengambil pekerjaan berdasarkan project owner dan project aktif. Volume serta formula state disertakan sebagai bootstrap JSON sehingga kolom tidak perlu menunggu fetch kedua untuk prefill awal.

Kondisi ini menutup masalah flash kosong yang pernah ditemukan pada implementasi lama. HTML page juga memakai kebijakan `no-store`.

Catatan:

- parameter dasar dan computed parameter tetap dimuat asynchronous;
- localStorage dapat ditampilkan lebih dahulu sebelum snapshot server diterapkan;
- pada koneksi lambat masih mungkin terjadi perubahan tampilan parameter setelah initial render.

### 4.2 Input Quantity Manual

**Status:** Baik bersyarat.

- Input menerima format angka lokal.
- Backend melakukan parse, menolak negatif, dan menyimpan 3 desimal.
- Nilai nol diterima dan dibedakan dari record yang belum pernah diisi.
- Dirty state dipertahankan sampai row benar-benar tersimpan.
- Save partial mengembalikan `saved_job_ids`, dan frontend hanya mengakui row tersebut.
- Terdapat shortcut Enter, Shift+Enter, dan Ctrl/Cmd+D.

Catatan:

- save quantity tidak mempunyai revision token per row;
- dua tab yang mengubah pekerjaan sama masih memakai last-write-wins;
- partial save perlu ditampilkan sebagai hasil campuran yang sangat eksplisit.

### 4.3 Formula Quantity Inline

**Status:** Bersyarat.

- Formula dapat dimulai dengan `=`.
- Autocomplete parameter, computed parameter, dan operation tersedia.
- Preview label dan nilai ditampilkan.
- Invalid formula memblokir sync pada frontend.
- Server membatasi panjang, token, identifier, function, dan karakter berbahaya.
- Formula sidecar dipisahkan dari quantity canonical.

Masalah utama berada pada partial server acceptance: formula invalid dapat ditolak backend tetapi dianggap tersinkron oleh frontend apabila sibling formula berhasil.

### 4.4 Formula Editor Modal

**Status:** Fungsional, kompleksitas modal tinggi.

Editor menyediakan:

- textarea formula;
- highlight invalid token;
- undo;
- raw/label view;
- preview label dan nilai;
- parameter palette;
- resolver unknown token;
- close confirmation ketika dirty;
- keyboard shortcut.

Terdapat banyak workaround modal:

- backdrop dimatikan;
- z-index dinaikkan manual;
- MutationObserver menghapus backdrop;
- watchdog berjalan periodik;
- native confirm/alert menjadi fallback.

Workaround ini menunjukkan modal stack belum mempunyai satu orchestration layer yang stabil. Browser UAT untuk skenario editor, palette, confirm, Escape, dan focus return tetap wajib.

### 4.5 Parameter Dasar

**Status:** Fungsional, backend dependency safety belum cukup.

- Kode `bp_N` dibuat server.
- Label dapat diubah tanpa mengubah opaque ID.
- Nilai mendukung presisi tinggi dan nilai negatif.
- Usage badge menghitung penggunaan pada computed formula dan formula pekerjaan.
- Delete menampilkan warning penggunaan di UI.
- Search dan import/export tersedia.

Warning penggunaan hanya dihitung di browser. Endpoint DELETE tetap dapat menghapus parameter tanpa memeriksa formula yang mereferensikannya.

### 4.6 Computed Parameter

**Status:** Fungsional, validasi server belum setara formula volume.

- Kode `cp_N` dibuat server.
- Expression dapat menggunakan base/computed parameter.
- Dependency resolution dan cyclic/unresolved state ditampilkan di client.
- Nilai computed digunakan dalam formula quantity.
- Rename label tidak mengubah ID.

Backend hanya memastikan expression tidak kosong. Syntax, allowed functions, unknown token, dependency existence, dan cycle belum divalidasi saat create/sync.

### 4.7 Import Parameter

**Status:** Baik bersyarat.

- Mendukung JSON, CSV, dan XLSX.
- Batas file browser 5 MB tersedia.
- Parser memvalidasi code dan numeric value.
- Import menampilkan ringkasan Merge/Replace.
- Undo tersedia melalui action toast.
- Computed parameter dapat ikut diimpor.

Kelemahan:

- tidak ada batas jumlah row/formula;
- computed expression tidak divalidasi sebelum state diterapkan;
- pilihan Merge/Replace memakai confirm dengan cancel button bermakna Replace, pola yang berisiko disalahartikan;
- perubahan awalnya diterapkan ke state lokal dan sinkronisasi backend berlangsung terpisah.

### 4.8 Export Parameter

**Status:** Baik.

Parameter dapat diekspor ke JSON, CSV, dan XLSX, serta disalin ke clipboard. CSV escaping telah menangani delimiter, quote, dan newline.

Catatan: file spreadsheet yang berisi label/formula dari user perlu tetap memperhatikan spreadsheet formula injection jika data tersebut dibuka di aplikasi spreadsheet. Exporter perlu memastikan cell text yang tidak dimaksudkan sebagai formula tidak dimulai sebagai formula aktif.

### 4.9 Export Page

**Status:** Baik bersyarat.

- Excel, PDF, Word, dan JSON tersedia sesuai entitlement.
- Async export mempunyai timeout dan fallback sync.
- Parameter formula dikirim ke ExportManager.
- Export permission telah memiliki test.

Risiko UX:

- bila ExportManager gagal dimuat, tombol baru dinonaktifkan secara logis setelah retry tetapi user hanya memperoleh console warning;
- button state/loading dan pesan kegagalan perlu diverifikasi langsung melalui browser.

### 4.10 Search, Filter, dan Navigation

**Status:** Cukup baik.

- Search mengindeks klasifikasi, subklasifikasi, dan pekerjaan.
- Keyboard navigation untuk hasil tersedia.
- Summary bar memfilter Semua, Terisi, Kosong, dan Formula.
- Expand/collapse state disimpan.
- Sidebar mempunyai search terpisah untuk parameter/formula.

Kelemahan:

- input search memiliki `aria-expanded="false"` tetapi JavaScript hanya memperbarui attribute pada results container;
- dua search mempunyai scope berbeda dan perlu label/feedback hasil yang tegas;
- search result hanya mengambil maksimum 15 item.

### 4.11 Responsive dan Mobile

**Status:** Bersyarat.

CSS menyediakan breakpoint 768 px dan 576 px, modal editor menjadi satu kolom, sidebar mendekati full width, dan quantity cell ditumpuk vertikal.

Namun:

- searchbar mempunyai `min-width: 320px`;
- sidebar memakai minimum 360 px;
- uraian memakai `min-width: 400px !important`;
- quantity minimum 28ch;
- tabel nested memang dapat horizontal scroll, tetapi penggunaan formula panjang di mobile tetap berat;
- touch target dan virtual keyboard mode perlu diuji pada perangkat nyata.

## 5. Implementasi UI/UX yang Sudah Baik

1. Initial quantity/formula tidak lagi mengalami flash kosong.
2. Summary bar sekaligus berfungsi sebagai status dan filter.
3. Empty state parameter menjelaskan CTA Tambah.
4. Dirty count ditampilkan pada FAB Simpan.
5. Save status, sync banner, summary, dan toast mempunyai live-region.
6. Dark mode mencakup page, toolbar, sidebar, table state, dan modal.
7. `prefers-reduced-motion` dan `forced-colors` ditangani.
8. Input formula menyediakan shortcut serta help modal.
9. Parameter palette mengurangi kebutuhan menghafal opaque code.
10. Label-only formula mode aktif secara default.
11. Server-generated opaque ID mencegah rename label merusak referensi.
12. Formula preview membedakan label dan nilai.
13. Row error, edited, saved, empty, dan pending-reset memiliki visual state.
14. Before-unload dan close confirmation mengurangi kehilangan edit lokal.
15. Import menyediakan preview ringkas dan undo.

## 6. Temuan Audit

### VP-01 - HIGH - Partial Formula Sync Menghapus Dirty State Formula yang Gagal

**Area:** Data integrity, frontend/backend contract

`api_volume_formula_state` menyimpan item valid dan mengumpulkan error item invalid. Jika minimal satu item berhasil, endpoint mengembalikan HTTP 200 dan `ok: true` walaupun `errors` tidak kosong.

Frontend `syncFormulaStateToServer()` hanya memeriksa `res.ok && res.data.ok`, kemudian menghapus `formulaDirtySet` untuk seluruh item yang dikirim.

**Dampak:**

- formula invalid yang ditolak server dianggap sudah sinkron;
- tombol save dapat kembali bersih;
- local dirty flag dapat dihapus;
- reload berikutnya menghilangkan formula yang gagal;
- user tidak memperoleh mapping row mana yang benar-benar tersimpan.

Perilaku partial success ini saat ini dikunci oleh test `test_valid_items_saved_despite_invalid_sibling`, tetapi test belum memeriksa kontrak acknowledgement frontend.

**Rekomendasi:**

1. Kembalikan `saved_job_ids` dan `failed_job_ids`, seperti save quantity.
2. Gunakan HTTP `207` atau `422` untuk mixed result.
3. Set `ok: false` ketika ada error, atau definisikan `partial: true`.
4. Frontend hanya menghapus dirty marker pada formula yang ada di `saved_job_ids`.
5. Mark input formula gagal dengan pesan server.
6. Tambahkan end-to-end regression test untuk satu formula valid dan satu invalid.

### VP-02 - HIGH - Delete Parameter Tidak Dijaga Dependency di Backend

**Area:** SSOT dan referential integrity

UI menghitung usage parameter dan menampilkan warning sebelum delete. Namun endpoint DELETE parameter langsung menghapus record tanpa memeriksa:

- computed parameter yang mereferensikan code tersebut;
- formula volume yang mereferensikan code tersebut;
- formula lain yang bergantung secara transitif.

**Dampak:**

- API caller atau race condition dapat meninggalkan formula yatim;
- reload menghasilkan unknown token/unresolved dependency;
- nilai quantity formula dapat tidak lagi dapat direproduksi;
- kebijakan data safety hanya berada di browser, bukan pada source of truth.

**Rekomendasi:**

1. Pindahkan dependency scanner ke service backend.
2. DELETE default harus mengembalikan `409 Conflict` beserta usage summary.
3. Sediakan explicit force-delete hanya jika memang menjadi kebijakan produk.
4. Force-delete harus memilih antara cascade formula, replace token, atau menjadikan formula invalid secara eksplisit.
5. Tambahkan audit event dan regression test.

### VP-03 - HIGH - Replace Sync Dapat Menghapus Snapshot Lama dan Tetap Berhasil Parsial

**Area:** Transaction semantics dan destructive synchronization

Pada mode `replace`, endpoint parameter dan computed parameter menghapus seluruh record terlebih dahulu. Item invalid kemudian di-skip dan hanya dikembalikan sebagai `warnings`, sementara response tetap `ok: true`.

Frontend menganggap sync berhasil, memperbarui timestamp, dan menghapus dirty flag.

**Dampak:**

- parameter lama sudah hilang sebelum seluruh payload dinyatakan valid;
- item invalid hanya tinggal di local state;
- reload menyebabkan perbedaan dengan apa yang terakhir dilihat user;
- formula yang bergantung pada item yang di-skip menjadi rusak.

**Rekomendasi:**

1. Validasi seluruh payload sebelum delete.
2. Gunakan change plan: `create`, `update`, `delete`, `reject`.
3. Terapkan all-or-nothing untuk mode replace.
4. Jika partial mode diperlukan, jangan menghapus item lama yang corresponding payload-nya invalid.
5. Jangan clear dirty state ketika warnings memengaruhi data authoritative.

### VP-04 - MEDIUM - Formula-State API Tidak Memvalidasi Tipe Setiap Item

**Area:** Backend robustness

`api_volume_formula_state` memanggil `it.get(...)` tanpa memastikan setiap item merupakan object/dictionary. Payload seperti `{"items":[null]}` atau `{"items":["x"]}` dapat menghasilkan server error.

Save quantity sudah mempunyai guard serupa, tetapi formula endpoint belum.

**Rekomendasi:** tambahkan type guard, error path `items[i]`, HTTP 400, dan regression test malformed payload.

### VP-05 - MEDIUM - Computed Expression Tidak Divalidasi Server-Side

**Area:** Data integrity dan security hardening

Create/sync computed parameter hanya menolak expression kosong. Validator formula server yang digunakan oleh formula quantity tidak diterapkan.

**Dampak:**

- syntax invalid dapat disimpan;
- unknown function dan unknown token dapat tersimpan;
- dependency cycle tidak dicegah;
- import dapat memasukkan expression rusak;
- backend dan frontend mempunyai definisi validitas berbeda.

Tidak ditemukan penggunaan `eval` backend, sehingga ini bukan remote code execution aktif. Namun stored invalid expression merusak reproducibility dan SSOT.

**Rekomendasi:**

1. Gunakan tokenizer/parser canonical yang sama.
2. Validasi allowed function dan identifier.
3. Validasi referenced parameter exists.
4. Bangun dependency graph dan tolak cycle.
5. Terapkan validator pada create, update, sync, import, dan export preparation.

### VP-06 - MEDIUM - Conflict Detection Memiliki Blind Spot Setelah Delete

**Area:** Concurrency

Stale detection memakai `Max(updated_at)` dari record yang masih ada. Jika client lain menghapus seluruh parameter/formula, queryset tidak mempunyai timestamp terbaru. Client lama kemudian dapat menyinkronkan snapshot localStorage dan menghidupkan kembali data yang telah dihapus.

Save quantity sendiri juga belum memakai revision token per pekerjaan.

**Rekomendasi:**

- simpan monotonic revision pada project atau scope state;
- increment revision pada create/update/delete;
- client mengirim revision, bukan hanya max row timestamp;
- reject stale revision dengan `409`;
- jangan gunakan localStorage timestamp sebagai concurrency authority.

### VP-07 - MEDIUM - Endpoint Write Belum Mempunyai Rate Limit dan Domain Payload Limit

**Area:** Availability dan abuse protection

Endpoint save volume, parameter CRUD/sync, computed sync, dan formula state tidak menggunakan rate limit write yang terlihat pada endpoint List Pekerjaan legacy.

Global request body limit 50 MB terlalu besar untuk payload parameter/formula. Batas browser import 5 MB tidak melindungi API langsung.

**Rekomendasi minimum:**

- rate limit per user/project;
- body size limit khusus endpoint;
- maximum item count;
- maximum label/unit/description length sebelum model validation;
- maximum expression length untuk computed parameter;
- maximum dependency depth;
- batching untuk payload besar.

### VP-08 - MEDIUM - SheetJS Dimuat dari CDN Tanpa SRI atau Self-Hosting

**Area:** Supply chain, availability, dan privacy

Template memuat SheetJS dari `cdn.sheetjs.com` tanpa `integrity` dan tanpa local fallback.

**Dampak:**

- import/export XLSX bergantung pada layanan pihak ketiga;
- CSP ketat menjadi lebih sulit;
- perubahan atau compromise upstream berdampak langsung pada page;
- browser user melakukan request ke domain eksternal.

**Rekomendasi:** pin dependency melalui package/build pipeline atau self-host asset terverifikasi. Jika CDN tetap dipakai, gunakan integrity metadata yang tersedia, CSP allowlist sempit, dan local fallback.

### VP-09 - MEDIUM - Semantik Accessibility Struktur Page Belum Lengkap

**Area:** Accessibility

Temuan terverifikasi:

- tidak ada `<main>` landmark pada konten page;
- table header belum memakai `scope="col"`;
- tab Parameter/Formula belum mempunyai `aria-controls`;
- panel belum mempunyai `role="tabpanel"` dan `aria-labelledby`;
- quantity input tidak terhubung programatis dengan preview/error;
- invalid state lebih banyak memakai class visual daripada `aria-invalid`;
- collapse button klasifikasi hanya memakai label generik.

**Rekomendasi:** lengkapi semantics tersebut dan lakukan UAT keyboard serta screen reader.

### VP-10 - MEDIUM - Mobile Layout Masih Bergantung pada Horizontal Scroll

**Area:** Responsive UI/UX

Responsive rules tersedia, tetapi kombinasi minimum width search, sidebar, uraian, dan quantity membuat mobile tetap padat. Horizontal scroll dibutuhkan di nested table.

**Rekomendasi:**

1. Ubah row menjadi card/stacked layout pada layar kecil.
2. Tampilkan kode, uraian, satuan, dan quantity secara vertikal.
3. Jadikan formula editor sebagai primary mobile editing surface.
4. Pastikan sidebar memakai `inset` dan width yang aman pada viewport di bawah 360 px.
5. Uji zoom 200% dan virtual keyboard.

### VP-11 - LOW - State ARIA Search Tidak Sinkron

Input `#vp-search` mempunyai `aria-expanded`, tetapi JavaScript memperbarui `aria-expanded` pada results container. Assistive technology tidak memperoleh state combobox dari control yang mengendalikannya.

**Rekomendasi:** gunakan pattern ARIA combobox yang lengkap: `role="combobox"`, `aria-expanded`, `aria-controls`, `aria-activedescendant`, dan state update pada input.

### VP-12 - LOW - Modal Stack Memerlukan Terlalu Banyak Workaround

**Area:** Maintainability dan UX reliability

Page menggunakan no-backdrop mode, z-index boost, backdrop pruning, MutationObserver, interval watchdog, dan native dialog fallback.

**Risiko:** focus trap, body scroll, Escape behavior, dan screen-reader modal context mudah mengalami regresi.

**Rekomendasi:** gunakan satu modal manager yang mendukung nested workflow tanpa membuka dua Bootstrap modal bersamaan. Palette dapat menjadi panel di dalam formula editor, bukan modal kedua.

### VP-13 - LOW - Loading Order Formula Engine Berpotensi Menimbulkan Transient Error

`vol_formula_engine.js` dimuat dengan `defer`, sedangkan `volume_pekerjaan.js` dimuat synchronously setelahnya. Script utama melakukan initial render dan async load sebelum deferred engine dieksekusi.

Interaksi user normal kemungkinan terjadi setelah engine tersedia, tetapi initial computed render dapat memakai fallback/error state sesaat.

**Rekomendasi:** konsistenkan seluruh script ke `defer` dengan urutan dependency yang jelas atau gunakan module bundler/import.

### VP-14 - LOW - Empty State Pekerjaan Tidak Memberi CTA

Ketika belum ada pekerjaan, page hanya menampilkan “Belum ada pekerjaan.” User tidak diarahkan kembali ke List Pekerjaan.

**Rekomendasi:** tampilkan CTA **Tambah Pekerjaan** yang menuju page List Pekerjaan, serta jelaskan bahwa volume baru dapat diisi setelah pekerjaan tersedia.

### VP-15 - LOW - Monolith Frontend dan Tiga Lapisan State Meningkatkan Risiko Regresi

JavaScript utama berukuran lebih dari 7.600 baris dan mengelola:

- rendering;
- formula engine adapter;
- modal;
- parameter state;
- localStorage;
- HTTP;
- import/export;
- search;
- filtering;
- autosave;
- conflict resolution.

State yang sama berada pada database, localStorage, dan DOM/in-memory. Source of truth berubah menurut kondisi network dan dirty flag.

**Rekomendasi restrukturisasi:**

- `volume-store.js`;
- `volume-api.js`;
- `formula-controller.js`;
- `parameter-controller.js`;
- `parameter-import-export.js`;
- `volume-view.js`;
- `volume-conflict-manager.js`;
- satu schema dan state transition contract yang diuji.

## 7. Penilaian SSOT

### Kondisi yang Sudah Baik

- `VolumePekerjaan.quantity` menjadi nilai canonical quantity.
- `VolumeFormulaState` hanya menjadi sidecar raw formula.
- Project parameter disimpan di database.
- Opaque ID dibuat server dan monotonic.
- Initial volume/formula dibangun melalui helper payload yang sama dengan GET API.
- Owner scope diterapkan pada page dan endpoint.
- Formula mempunyai validator server.
- Export adapter menggunakan parameter/formula terstruktur.

### Kelemahan SSOT

- localStorage masih dapat menjadi fallback state.
- dirty state lokal dapat bertentangan dengan database.
- computed formula tidak memakai validator canonical.
- dependency policy hanya berada di frontend.
- replace sync dapat committed dengan warning.
- formula partial success tidak mempunyai acknowledgement per item.
- conflict version berasal dari row timestamp, bukan monotonic scope revision.

### Target SSOT

1. Database selalu authoritative.
2. localStorage hanya draft dengan revision asal yang eksplisit.
3. Semua mutation memakai per-scope revision.
4. Semua formula memakai parser/validator canonical.
5. Dependency graph disimpan atau dihitung backend.
6. Partial success selalu mengembalikan acknowledgement per item.
7. Replace operation selalu validate-before-delete.

## 8. Rekomendasi Restrukturisasi

### Tahap 1 - Integrity Gate

1. Perbaiki formula partial acknowledgement.
2. Tambahkan dependency guard backend.
3. Ubah replace sync menjadi validate-first dan atomic.
4. Terapkan computed formula validation.
5. Tambahkan malformed item guard.

### Tahap 2 - Concurrency dan SSOT

1. Tambahkan `parameter_revision`, `computed_revision`, `formula_revision`, dan volume row version.
2. Sertakan revision pada bootstrap/GET.
3. Tolak stale write dengan `409`.
4. Simpan draft localStorage bersama revision asal.
5. Tampilkan compare/merge workflow yang jelas.

### Tahap 3 - Frontend Modularization

1. Pisahkan store, API, rendering, modal, dan import/export.
2. Gunakan typed schema atau runtime schema validation.
3. Kurangi direct `innerHTML`.
4. Hilangkan native dialog fallback dari normal production flow.
5. Integrasikan seluruh feedback melalui satu toast/modal service.

### Tahap 4 - UI/UX dan Accessibility

1. Lengkapi landmark, table semantics, tabs, combobox, dan error relation.
2. Buat mobile card layout.
3. Ubah import Merge/Replace menjadi modal dengan dua tombol eksplisit.
4. Tambahkan CTA empty state.
5. Jalankan browser UAT pada desktop, tablet, mobile, keyboard-only, dan screen reader.

## 9. Pengujian yang Dijalankan

### Django

Suite:

```text
detail_project.tests_volume_pekerjaan_save_api
detail_project.tests_volume_formula_owner_guard
detail_project.tests_formula_server_validation
detail_project.tests_formula_integration
detail_project.tests_phase1_opaque_api
detail_project.tests_volume_export_adapter
detail_project.tests_formula_ui_regressions
detail_project.tests_page_security_audit
detail_project.tests_page_cache_headers
```

**Hasil:** 139 test ditemukan, seluruh test aktif lulus, 40 guard WIP di-skip.

### Frontend

```text
vol_formula_engine.test.js
xss_governance_guard.test.js
feedback_governance_guard.test.js
```

**Hasil:** 3 file, 55 test, seluruhnya lulus.

### Test Tambahan yang Wajib

1. Partial formula sync tidak menghapus dirty formula gagal.
2. Malformed formula item menghasilkan 400, bukan 500.
3. Delete parameter yang dipakai formula menghasilkan 409.
4. Replace sync invalid tidak menghapus snapshot server lama.
5. Computed parameter invalid, unknown function, dan cycle ditolak.
6. Stale client tidak dapat resurrect parameter setelah delete-all.
7. Same-row concurrent volume edit menghasilkan conflict.
8. Payload size dan item count limit.
9. Spreadsheet formula injection pada CSV/XLSX.
10. Browser UAT modal stack, focus return, keyboard, touch, dan responsive.

## 10. Prioritas Remediasi

| Urutan | Item | Gate |
|---|---|---|
| P0 | VP-01 formula partial acknowledgement | Wajib sebelum production sign-off |
| P0 | VP-02 backend dependency guard | Wajib untuk integritas formula |
| P0 | VP-03 atomic replace sync | Wajib sebelum import/replace dianggap aman |
| P1 | VP-05 computed formula validation | Wajib sebelum computed formula dianggap SSOT |
| P1 | VP-04 malformed item guard | API hardening |
| P1 | VP-06 monotonic revision | Multi-tab consistency |
| P1 | VP-07 rate/payload limits | Availability protection |
| P1 | VP-08 self-host SheetJS | Supply-chain hardening |
| P1 | VP-09 accessibility semantics | UI sign-off |
| P2 | VP-10 mobile layout | Mobile sign-off |
| P2 | VP-11 sampai VP-14 | UX dan reliability |
| P3 | VP-15 modularization | Maintainability |

## 11. Browser UAT Matrix yang Masih Diperlukan

| Area | Skenario |
|---|---|
| Initial load | no flash, no console error, bootstrap benar |
| Quantity | angka, nol, negatif, paste, rapid save, partial error |
| Formula inline | autocomplete, keyboard, invalid, long formula |
| Formula modal | apply, cancel, dirty close, nested palette, Escape |
| Parameter | create, edit, delete used/unused, search |
| Computed | create, chain, cycle, invalid dependency |
| Import | JSON/CSV/XLSX, merge, replace, undo, large file |
| Export | entitlement, loading, timeout, fallback, failed export |
| Conflict | dua tab base/computed/formula/quantity |
| Accessibility | tab order, screen reader, live messages, focus return |
| Responsive | 320, 360, 576, 768, desktop, 200% zoom |
| Theme | light, dark, forced-colors, reduced-motion |
| Touch | sidebar, table scroll, editor, palette, save FAB |

## 12. Keputusan Audit

Page Volume Pekerjaan memiliki implementasi formula dan parameter yang lebih matang daripada audit lama Februari 2026. Initial bootstrap, opaque ID, server formula validation, conflict response, dirty-row preservation, dan feedback UI merupakan peningkatan nyata.

Namun, page **belum direkomendasikan sebagai final production-ready** sebelum VP-01, VP-02, dan VP-03 ditutup. Ketiga temuan tersebut dapat membuat UI dan database berbeda mengenai formula/parameter mana yang benar-benar tersimpan.

Setelah P0 selesai, computed validation, monotonic revision, API limits, accessibility semantics, dan browser UAT menjadi syarat berikutnya untuk menyatakan page stabil secara menyeluruh.

---

## 13. Verifikasi Independen (Claude, 13 Juni 2026)

Temuan diperiksa ulang terhadap kode kerja. Yang diverifikasi langsung di kode: **VP-01 s/d VP-08 dan VP-13 — semuanya valid, tidak ada false positive.** VP-09 s/d VP-12, VP-14, VP-15 bersifat struktural/UX dan konsisten dengan kode (perlu UAT browser untuk konfirmasi penuh).

### 13.1 Verdict per temuan

| Temuan | Verdict | Bukti verifikasi |
|---|---|---|
| VP-01 Partial formula sync hapus dirty | **DIKONFIRMASI (backend + frontend)** | Backend `views_api.py:5185` `status_code = 400 if errors and (created+updated+deleted == 0) else 200` → `ok:true` saat parsial; tidak ada `saved/failed_job_ids`. Frontend `volume_pekerjaan.js:2995` hanya cek `res.ok && res.data?.ok`, lalu `:3003` `formulaDirtySet.delete(...)` untuk **semua** item terkirim, termasuk yang ditolak server. |
| VP-02 Delete parameter tanpa dependency guard | **DIKONFIRMASI** | `views_api.py:3456-3459`: DELETE langsung `param.delete()` lalu `ok:True`, tanpa scan computed/formula yang mereferensikan kode. |
| VP-03 Replace sync hapus dulu, sukses parsial | **DIKONFIRMASI (dengan penajaman)** | Base: `:3556` `ProjectParameter...delete()` sebelum loop create; item invalid → `warnings` (`:3562`); response `ok:True` (`:3638`). Computed: `:3773` pola sama. Lihat penajaman 13.2 — ini **atomic** (silent data-loss + false success), bukan torn write. |
| VP-04 Formula-state tidak guard tipe item | **DIKONFIRMASI** | `:5149` `it.get("pekerjaan_id")` tanpa cek `isinstance(it, dict)`. `{"items":[null]}`/`["x"]` → `AttributeError` → 500. List sudah di-guard (`:5140`), item belum. |
| VP-05 Computed expression tak divalidasi server | **DIKONFIRMASI** | `:3799` hanya tolak expression kosong; `_validate_formula_raw` (dipakai volume `:5170`) **tidak** dipanggil. Tidak ada cek syntax/function/unknown token/cycle. |
| VP-06 Conflict blind spot setelah delete | **DIKONFIRMASI (lebih luas)** | `_is_stale_sync:461-468`: `latest_ts = Max(updated_at)`; saat semua record dihapus `latest_ts=None` → `if latest_ts and ...` gagal → `(False, None)` = tak ada konflik. Lihat 13.2 untuk dua perluasan. |
| VP-07 Tanpa rate limit & payload limit | **DIKONFIRMASI** | `api_save_volume_pekerjaan` (`:1700-1703`), `api_project_parameters` (`:3341-3344`), `api_volume_formula_state` (`:5108-5111`), sync base/computed — semua tanpa `@rate_limit`. |
| VP-08 SheetJS CDN tanpa SRI | **DIKONFIRMASI** | `volume_pekerjaan.html:652` `<script defer src="https://cdn.sheetjs.com/xlsx-0.20.3/...">` tanpa `integrity`/fallback. |
| VP-13 Loading order formula engine | **DIKONFIRMASI** | `vol_formula_engine.js` `defer` (`:650`); `volume_pekerjaan.js` (`:661`) + runtime/patch (`:655-657`) **tanpa** `defer`. Script non-defer eksekusi sebelum deferred → engine belum siap saat render awal. |
| VP-09/10/11/12/14/15 | **PLAUSIBEL** | Struktural/UX/a11y; konsisten dengan kode. Perlu UAT browser (a11y, mobile, modal stack) untuk konfirmasi tuntas. |

### 13.2 Penajaman bukti

- **VP-03 — ini operasi atomic, jadi masalahnya "silent data-loss + sukses palsu", bukan torn write.** Kedua endpoint sync ber-`@transaction.atomic` (`:3507`, `:3651`), sehingga delete-all + create-valid commit bersama; tidak ada kondisi DB setengah jadi. Tetapi item invalid **hilang permanen** (hanya jadi `warnings`) sementara response `ok:True` dan frontend membersihkan dirty → state lokal user (yang masih punya item invalid) berbeda dari server saat reload. Perbaikannya tetap seperti rekomendasi (validate-before-delete / change plan), namun framing yang lebih tepat: **validasi seluruh payload dulu; jika ada yang invalid, tolak (`400/422`) tanpa menghapus apa pun** — bukan sekadar "jangan torn".

- **VP-06 — dua perluasan yang memperparah.**
  1. **Guard bersifat opt-in dari client.** `_is_stale_sync:462-464`: bila payload tidak menyertakan `last_sync_at`, fungsi langsung `return False, None` → **deteksi konflik dilewati total**. Client yang lupa/sengaja tidak mengirim timestamp tidak mendapat proteksi apa pun. Ini, bukan hanya kasus delete-all, adalah lubang terbesar.
  2. **Partial delete juga bisa menurunkan `Max(updated_at)`.** Karena `Max` hanya melihat row tersisa, menghapus row yang paling baru di-update bisa menurunkan `latest_ts` di bawah `client_ts` → konflik nyata terlewat. Ini memperkuat rekomendasi monotonic revision per-scope (yang tidak turun saat delete).

- **Interaksi VP-02 × VP-03 × VP-05 (orphan lintas-endpoint).** Karena base-sync `replace` (`:3556`) menghapus semua base param dan computed-sync tidak memvalidasi referensi (VP-05), sebuah `replace` base yang men-skip satu kode (invalid) akan meninggalkan computed param/formula volume yang masih mereferensikan kode itu sebagai **token yatim** — tanpa peringatan. Dependency guard (VP-02) sebaiknya didefinisikan satu kali di service dan dipakai oleh DELETE **dan** kedua jalur sync.

### 13.3 Catatan konsistensi lintas-page

Pola yang sama berulang di tiga page yang sudah diaudit (Dashboard, List Pekerjaan, Volume):
- **Tidak ada CSP** di `config/` — VP-08 (CDN tanpa SRI) memperburuk ini; tanpa CSP, kompromi upstream SheetJS langsung berdampak.
- **Sukses parsial dengan `ok:true`** dipakai berulang (LP-02/LP-07, VP-01/VP-03) — layak dijadikan satu konvensi kontrak API: hasil campuran selalu memakai `207/422` + daftar id sukses/gagal eksplisit.
- **Concurrency berbasis `Max(updated_at)`** (bukan revisi monotonik) muncul di banyak endpoint (`:832-834`, `:6527-6530`, dll) — blind spot VP-06 kemungkinan berlaku untuk page lain juga, bukan hanya Volume.

Ketiga hal ini sebaiknya diputuskan sebagai kebijakan tingkat-aplikasi, bukan tambalan per-page.

### 13.4 Kalibrasi prioritas

Urutan P0 (VP-01, VP-02, VP-03) sudah tepat. Tambahan: **VP-04 (one-line dict guard) dan bypass `last_sync_at` pada VP-06 adalah quick win** — effort sangat rendah, dan VP-06 opt-in-bypass sebaiknya dinaikkan ke P1 atas (saat ini tertanam di VP-06 yang P1) karena membuat seluruh proteksi konflik tidak efektif untuk client tertentu.

### 13.5 Gejala lapangan terkait VP-06 (dilaporkan owner, 13 Juni 2026)

Owner melaporkan **sering melihat prompt konflik sinkronisasi "merge / override (Reload)"** di page Volume Pekerjaan dan menanyakan apakah itu wajar. Hasil penelusuran kode mengonfirmasi gejala ini adalah **manifestasi langsung dari VP-06**, terdiri dari dua lapisan:

- **Banner pasif** — `volume_pekerjaan.js:688-703`: "*X pekerjaan perlu diperbarui setelah perubahan sumber*" / "*Perubahan data terbaru terdeteksi dari halaman lain*".
- **Confirm aktif (memblokir)** — konflik parameter/computed `:6984` ("data di server lebih baru. Reload? [Reload]/[Tetap Lokal]") dan konflik formula `:2980` ("Merge = edit lokal + server, Reload = versi server").

Deteksi memakai `Max(updated_at)` (`api_get_change_status` `views_api.py:4285-4288`) dibanding timestamp client + `localStorage` sebagai fallback (last-write-wins, tanpa revisi monotonik).

**Penilaian:** wajar/by-design **hanya** saat pekerjaan benar-benar ditambah/diubah source-nya di List Pekerjaan. Bila muncul berulang **tanpa** perubahan (mis. buka ulang Volume atau tab kedua), itu false-positive — yaitu kelemahan yang sudah didokumentasikan di VP-06 dan bagian "Kelemahan SSOT", **bukan regresi baru**.

**Keputusan:** owner meminta perbaikan ini **dimasukkan ke fase perbaikan** (setelah seluruh audit/review page selesai), tergabung dengan remediasi VP-06:
1. Revisi monotonik per-scope (`parameter_revision`/`computed_revision`/`formula_revision` + volume row version) supaya prompt hanya muncul saat ada perubahan nyata.
2. Hilangkan bypass opt-in `last_sync_at` di `_is_stale_sync` (`views_api.py:461-468`).

Dicatat juga di memory proyek `audit-fix-phase-backlog`.

### 13.6 Cakupan parameter & computed (formula) parameter — konfirmasi + satu catatan

Permintaan owner (13 Juni 2026): pastikan isu **parameter dasar** dan **formula/computed parameter** sudah masuk audit. Hasil pemeriksaan: **keduanya sudah tercakup.** Pemetaan:

- **Parameter dasar (`bp_N`):** §4.5; VP-02 (delete tanpa dependency guard, `views_api.py:3456-3459`); VP-03 (replace sync, `:3556`); VP-06 (konflik/stale); VP-07 (rate/payload + batas panjang label/unit); §4.7 import; §4.8 export.
- **Computed/formula parameter (`cp_N`):** §4.6; **VP-05** — dikonfirmasi berlaku di **dua jalur**: create (`:3683-3684`, hanya tolak expression kosong) dan sync (`:3799`); VP-03 (replace computed, `:3773`); VP-06; VP-02 (dependency transitif base→computed→formula).

**Verifikasi tambahan (hasil: aman, bukan temuan).** Perubahan **nilai** parameter di page Volume mempropagasi benar dalam-sesi: `reevaluateAllFormulas()` (`volume_pekerjaan.js:4979`) → `handleInputChange` → `updateDirty()` (`:4841`) menandai baris formula dirty bila nilai berubah, sehingga user diminta menyimpan. Residu satu-satunya — quantity tersimpan di DB tidak ter-update lintas-page sampai Volume dibuka & disimpan ulang — adalah konsekuensi desain sidecar (quantity canonical, formula sidecar) yang sudah tercermin di bagian SSOT, bukan bug baru.

**Catatan yang belum eksplisit di temuan:** Computed parameter **tidak memiliki endpoint detail tersendiri** (tidak ada `api_project_computed_parameter_detail` GET/PUT/DELETE; bandingkan base param di `:3432`). Akibatnya seluruh update dan **penghapusan** computed parameter hanya mengalir lewat `api_project_computed_parameters_sync` yang **tidak memvalidasi expression** (VP-05) dan **tidak memeriksa dependency** (VP-02), dengan pola replace-destruktif (VP-03). Implikasi remediasi: dependency guard (VP-02) dan validator canonical (VP-05) harus diterapkan **eksplisit pada jalur sync computed**, bukan hanya pada endpoint DELETE base param — karena untuk computed, sync adalah satu-satunya jalur mutasi/hapus.
