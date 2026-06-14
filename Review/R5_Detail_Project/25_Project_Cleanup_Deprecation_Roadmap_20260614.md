# Roadmap Cleanup dan Deprecation Project

**Tanggal:** 14 Juni 2026  
**Target:** seluruh project, dengan fokus awal `detail_project` dan Dashboard  
**Status:** **INVENTARIS SELESAI - EKSEKUSI HARUS PER BATCH DENGAN TEST DAN SMOKE UAT**

## 1. Tujuan

Cleanup dilakukan untuk:

- menghapus page dan workflow yang telah diputuskan tidak relevan;
- menghapus endpoint dormant yang bukan lagi bagian kontrak produk;
- mengurangi implementasi paralel yang dapat menghasilkan data berbeda;
- menghapus file, listener, kontrol, dan dependency yang tidak mempunyai consumer;
- mempertahankan compatibility layer yang masih melindungi data lama, bookmark,
  import, copy Project, atau deployment yang belum selesai dimigrasikan.

Cleanup bukan refactor massal. Setiap penghapusan harus mempunyai:

1. bukti tidak ada consumer aktif;
2. keputusan pengganti/SSOT;
3. migration atau fallback yang jelas bila data lama terlibat;
4. regression test;
5. smoke test page terdampak;
6. rollback melalui Git, bukan duplicate code yang dibiarkan hidup.

## 2. Prinsip Klasifikasi

### A. Hapus Sekarang

Artefak tidak diroute, tidak di-load template, tidak di-import runtime, dan tidak
menjadi compatibility contract.

### B. Pensiunkan Bertahap

Fitur telah ditolak oleh keputusan produk, tetapi route/API/data masih mempunyai
consumer, bookmark, deprecation window, atau test transisi.

### C. Pertahankan Sementara

Nama atau implementasi terlihat legacy, tetapi masih diperlukan untuk:

- copy/import/backup;
- data Project lama;
- projection dari SSOT baru;
- alias route selama deprecation window;
- migration lintas-environment;
- operational repair.

### D. Jangan Dihapus

Migration Django, data canonical, audit history, dan source untuk generated
bundle tidak boleh dihapus hanya karena tidak dirujuk langsung oleh template.

## 3. Ringkasan Kandidat

| ID | Kandidat | Klasifikasi | Keputusan |
|---|---|---|---|
| CL-01 | Page Orphan Cleanup | B | Pensiunkan UI; pertahankan housekeeping backend |
| CL-02 | Page/template Rincian RAB legacy | A/B | Template mati dapat dihapus; redirect/API tunggu sunset |
| CL-03 | Page Export Test | B | Pindahkan fungsi ke automated test; hapus route production |
| CL-04 | Dashboard `mass_edit_bulk_update` lama | A | Hapus fungsi dead di `dashboard/views.py` |
| CL-05 | Legacy full-save List Pekerjaan | B | Hapus setelah telemetry dan consumer test |
| CL-06 | Mode Tahapan Rekap Kebutuhan | B | Hapus menyeluruh sesuai keputusan D-RK-08 |
| CL-07 | Jalur Kurva S client sebagai SSOT | B | Pensiunkan setelah server adapter menjadi canonical |
| CL-08 | Auto reload Template AHSP saat page open | A/B | Hapus trigger massal, pertahankan stale diagnostics |
| CL-09 | Duplicate ExportManager/SheetJS/Excel exporter | A/B | Hapus per-page duplication setelah parity server export |
| CL-10 | `detail_ahsp_gabungan.js` lama | A | Hapus bersama test yang hanya menjaga file lama |
| CL-11 | Template tanpa route/consumer | A | Verifikasi final lalu hapus |
| CL-12 | Dead controls/CSS per page | A/B | Hapus setelah selector-contract scan |
| CL-13 | Tahapan API v1 dan projection models | C | Belum boleh dihapus |
| CL-14 | Alias HSP/export/raw fallback | C | Pertahankan sampai seluruh consumer dimigrasikan |
| CL-15 | Parameter legacy dan migration guards | C | Pertahankan sampai seluruh environment selesai |
| CL-16 | One-off management commands | C | Audit deployment dahulu; archive/delete belakangan |
| CL-17 | Page Audit Trail | B | Hapus UI/API pembacaan; pertahankan histori dan writer backend |

## 4. Batch 1 - Artefak Mati dan Duplikasi Tanpa Perubahan Produk

### CL-04 - Fungsi Mass Edit Dashboard Lama

`dashboard/urls.py` memakai implementasi dari `dashboard/views_mass_edit.py`.
Fungsi bernama sama di `dashboard/views.py` tidak diroute dan mencatat raw request
body bila kembali terpakai secara tidak sengaja.

**Aksi:**

- hapus `mass_edit_bulk_update` lama dari `dashboard/views.py`;
- pastikan tidak ada import;
- pertahankan implementasi `views_mass_edit.py`;
- jalankan test mass edit Dashboard.

**Risiko:** rendah.

### CL-10 - JavaScript `detail_ahsp_gabungan.js`

Page Rincian AHSP aktif memakai `rincian_ahsp.js`. File
`detail_ahsp_gabungan.js` tidak di-load template dan hanya dirujuk test lama.

**Aksi:**

- verifikasi ulang melalui browser/network bahwa file tidak dimuat;
- pindahkan assertion yang masih relevan ke test `rincian_ahsp.js`;
- hapus file dan test khusus implementasi lama;
- jangan hapus endpoint detail AHSP yang masih dipakai Template/Rincian AHSP.

**Risiko:** rendah setelah test dipindahkan.

### CL-11 - Template Tanpa Consumer

Kandidat awal:

- `detail_project/templates/detail_project/rekap_ahsp.html`;
- `detail_project/templates/detail_project/tambah_dari_referensi.html`;
- `detail_project/templates/detail_project/rincian_rab.html`.

`rincian_rab.html` tidak pernah dirender karena view langsung melakukan permanent
redirect. Dua template lain tidak ditemukan pada route/render/include aktif.

**Aksi:**

- lakukan exact reference scan pada nama template;
- hapus hanya template yang tetap 0-reference;
- hapus CSS/JS eksklusifnya bila juga 0-reference;
- update test inventory page.

**Risiko:** rendah.

### CL-09A - Duplicate ExportManager

`base_detail.html` sudah memuat `ExportManager.js`, tetapi Jadwal Pekerjaan
memuat file yang sama lagi.

**Aksi:**

- pertahankan satu load global;
- hapus load kedua dari template Jadwal;
- pastikan initializer idempotent dan modal tetap satu;
- browser smoke export semua page.

**Risiko:** rendah.

### CL-12A - Dead UI Controls yang Telah Diputuskan

Kandidat yang telah disepakati:

- Grand Total toolbar Rincian AHSP;
- column visibility Rekap Kebutuhan yang tidak bekerja;
- hidden compatibility controls Rekap Kebutuhan;
- listener/debug shortcut production;
- kontrol override Rincian AHSP yang tidak terhubung;
- toolbar target yang tidak mempunyai element.

**Aksi:** hapus markup, handler, selector, CSS, dan test lama dalam commit yang
sama per page.

**Risiko:** rendah-menengah karena selector JavaScript dapat tersembunyi.

## 5. Batch 2 - Pensiun Page Orphan Cleanup

Keputusan produk: page Orphan Cleanup tidak lagi relevan. Harga Items hanya
menampilkan item yang benar-benar dipakai dan orphan dibersihkan otomatis setelah
transaction yang dapat menciptakannya berhasil commit.

### Yang Dihapus

- route `orphan-cleanup/`;
- `orphan_cleanup_view`;
- link dan label sidebar;
- `orphan_cleanup.html`;
- `orphan_cleanup.js`;
- `orphan_cleanup.css`;
- test page/sidebar khusus Orphan Cleanup;
- entry page-cache/UAT lama.

### Yang Dipertahankan

- `detect_orphaned_items()`;
- `cleanup_orphaned_items()`;
- `_auto_cleanup_orphans()` dan `transaction.on_commit`;
- management command cleanup untuk operasi darurat;
- regression test auto cleanup;
- guard agar item tidak dihapus ketika expansion pending, stale, partial, atau
  gagal.

### Endpoint Manual

Endpoint list/cleanup orphan dapat dihapus setelah:

1. tidak ada admin/ops consumer;
2. telemetry menunjukkan tidak dipanggil;
3. auto cleanup mencakup seluruh mutation path;
4. management command cukup untuk recovery.

Jangan menghapus service bersamaan dengan UI.

## 5A. Batch 2 - Pensiun Page Audit Trail

**Keputusan owner 14 Juni 2026:** page Audit Trail tidak lagi relevan terhadap
workflow utama dan dipensiunkan.

### Yang Dihapus

- link, label, dan active state Audit Trail dari sidebar;
- route `audit-trail/`;
- `audit_trail_view`;
- `audit_trail.html`;
- `audit_trail.js`;
- `audit_trail.css`;
- endpoint `api_get_audit_trail`;
- route API pembacaan audit;
- test admin-only/page-cache/sidebar yang hanya menjaga page Audit Trail.

### Yang Dipertahankan

- model dan tabel `DetailAHSPAudit`;
- `log_audit()` dan callsite pencatatan perubahan AHSP/cascade;
- data histori yang telah tersimpan;
- test retensi ketika pekerjaan dihapus;
- diagnosis internal melalui Django admin, shell, atau management tooling.

Dengan menghapus web/API surface, stored XSS dan mismatch permission pada page
ditutup tanpa menginvestasikan waktu pada UI yang tidak lagi digunakan. Model
dan writer baru dievaluasi untuk penghapusan setelah sistem utama stabil dan
terbukti tidak dibutuhkan untuk troubleshooting.

## 6. Batch 3 - Pensiun Rincian RAB Legacy

Page Rincian RAB telah digantikan oleh:

- Rincian AHSP untuk detail harga satuan;
- Rekap RAB untuk ringkasan nilai Project.

### Dapat Dihapus Sekarang

- template `rincian_rab.html`, karena view tidak merendernya;
- sync scope/listener khusus `rincian_rab` yang tidak mempunyai page aktif;
- CSS/JS eksklusif jika terbukti 0-reference.

### Dipertahankan Sampai Sunset

- redirect permanent `/rincian-rab/`;
- `api_get_rincian_rab`;
- `api_export_rincian_rab_csv`;
- decorator dan telemetry deprecation.

Tanggal sunset yang tercatat adalah **1 September 2026**. Jangan menghapus route
dan API pada 14 Juni 2026 tanpa mengganti keputusan sunset atau membuktikan zero
usage.

### Saat Sunset

- periksa telemetry minimal 30 hari;
- hapus dua API dan `_compute_rincian_rab`;
- hapus test access/deprecation lama;
- pertahankan redirect bookmark lebih lama bila biayanya kecil.

## 7. Batch 4 - Hapus Legacy Full-Save List Pekerjaan

UI aktif memakai endpoint `upsert/`. Endpoint `list-pekerjaan/save/` masih
callable dan membawa semantics full-state/destructive yang berbeda.

**Aksi:**

1. beri/pertahankan deprecation telemetry;
2. scan frontend, integration, external caller, dan account tests;
3. migrasikan caller yang masih hardcoded;
4. hapus route dan `api_save_list_pekerjaan`;
5. pertahankan satu contract upsert transactional;
6. perbarui security/rate-limit test.

**Jangan dilakukan** sebelum upsert mempunyai rollback, conflict protection, rate
limit, dan impact confirmation yang disepakati pada audit List Pekerjaan.

## 8. Batch 5 - Hapus Mode Tahapan Rekap Kebutuhan

Keputusan final: Rekap Kebutuhan memakai:

- Total Kebutuhan;
- Mingguan;
- Periode 4 Minggu.

Tahapan tidak menjadi formula distribusi kebutuhan.

### Scope Penghapusan

- parameter publik `mode=tahapan`;
- `tahapan_id` dan `tahapan_ids` untuk Rekap Kebutuhan;
- filter/dropdown/chip/URL state Tahapan;
- service branch proporsi Tahapan;
- endpoint enhanced/filter yang hanya mendukung mode lama;
- export title/adapter branch Tahapan;
- validation dan cache key Tahapan;
- test fixture mode Tahapan.

### Yang Tidak Ikut Dihapus

- `TahapPelaksanaan`;
- `PekerjaanTahapan`;
- API tahapan yang masih menjadi projection Jadwal;
- copy/import mapping tahapan;
- regenerate/sync dari weekly canonical.

Model tersebut masih dipakai Jadwal dan compatibility projection. Penghapusan
mode Rekap Kebutuhan bukan izin menghapus storage projection Jadwal.

## 9. Batch 6 - Konsolidasi Jadwal dan Kurva S

### Jalur Kurva S

Hapus status `buildProgressDataset()` sebagai sumber bobot independen setelah:

- server adapter menjadi SSOT saved curve;
- preview draft memakai bobot canonical dari server;
- fallback volume/equal weight dihapus;
- layar saved dan export mempunyai contract test parity.

Renderer client/uPlot boleh dipertahankan sebagai renderer, bukan calculator
SSOT.

### Auto-Regenerate dan API Tahapan v1

Hapus auto-regenerate saat page open yang dipicu heuristik client. Ganti dengan
flag `timeline_stale` server dan aksi user terkontrol.

API v1 belum boleh dihapus karena:

- v2 masih mengimpor helper/fungsi dari v1;
- projection Tahapan masih dipakai;
- beberapa modul dan test masih bergantung padanya.

Sebelum API v1 dihapus:

1. pindahkan shared helper ke service/module netral;
2. pastikan frontend hanya memakai v2/canonical;
3. pertahankan projection builder internal;
4. verifikasi telemetry endpoint v1;
5. jalankan migration/repair seluruh Project.

## 10. Batch 7 - Export dan Asset Cleanup

### Export Test Page

`export-test/` adalah page pengembangan yang masih diroute untuk staff.

**Target:**

- pindahkan skenario valid ke automated browser/unit test;
- hapus route, view, template, dan page-cache/UAT entry;
- jangan menghapus module export yang masih dipakai Jadwal.

### Rekap RAB SheetJS/ExcelExporter

Audit menetapkan export server-authoritative. Rekap RAB masih memuat SheetJS CDN
dan `ExcelExporter.js`.

**Aksi setelah parity server export teruji:**

- hapus dependency SheetJS dari page;
- hapus `ExcelExporter.js` jika tidak dipakai page lain;
- hapus duplicate client export initialization;
- pertahankan server XLSX export;
- update CSP/SRI concern menjadi selesai.

### Generated `dist`

Jangan menghapus file individual di `dist` secara manual. Bersihkan source/import
lebih dahulu, jalankan clean build, lalu commit output sesuai kebijakan repository.

## 11. Batch 8 - CSS, Debug, dan Operational Tools

### CSS

Jangan menghapus stylesheet hanya karena namanya lama. Gunakan:

1. template reference scan;
2. selector scan terhadap template/JS;
3. browser coverage pada seluruh mode;
4. visual regression/screenshot;
5. delete per page.

Prioritas:

- duplicate Rekap Kebutuhan generations;
- dead print rule;
- unused Jadwal redesign rule;
- global `detail_ahsp.css` yang dimuat semua page melalui base template.

### Management Commands

Command bernama `debug_*`, `fix_*`, `migrate_*`, atau `verify_*` bukan otomatis
dead. Klasifikasikan:

- operational recovery: pertahankan;
- migration masih berjalan: pertahankan;
- one-off selesai dan tidak dibutuhkan rollback: pindah ke archive docs atau hapus;
- sample/test data: pastikan tidak tersedia di production workflow.

Sebelum menghapus command migration, konfirmasi seluruh deployment/environment
telah mencapai schema dan data version yang sama.

## 12. Compatibility yang Belum Boleh Dihapus

Daftar berikut tetap dipertahankan pada tahap cleanup awal:

- migration Django historis;
- `PekerjaanProgressWeekly` sebagai SSOT Jadwal;
- `PekerjaanTahapan`/`TahapPelaksanaan` sebagai projection sementara;
- route alias `detail-ahsp` dan `detail-ahsp-gabungan` selama deprecation;
- HSP/E/F/G/unit-price compatibility aliases sampai consumer dimigrasikan;
- raw Detail AHSP fallback untuk fixture/import/data lama;
- `LEGACY_PARAM_NAME_RE`, migration log, dan rollback opaque parameter sampai
  seluruh environment selesai;
- import parser schema JSON/Excel lama yang masih didukung;
- copy Project mapping Tahapan dan formula;
- auto orphan cleanup service;
- audit history;
- export server adapters;
- repair commands yang masih diperlukan untuk recovery.

## 13. Urutan Eksekusi

1. **Batch 1:** dead function, dead template, duplicate script, dead controls.
2. **Batch 2:** Orphan Cleanup UI dan Audit Trail UI/API pembacaan.
3. **Batch 3:** Rincian RAB template/dead scope; API mengikuti sunset.
4. **Batch 4:** legacy List Pekerjaan save.
5. **Batch 5:** mode Tahapan Rekap Kebutuhan.
6. **Batch 6:** Kurva S/client calculation dan Tahapan v1 setelah decoupling.
7. **Batch 7:** export-test dan client export dependencies.
8. **Batch 8:** CSS dan management command hygiene.

Setiap batch harus menjadi perubahan mandiri. Jangan mencampur penghapusan
storage, page, dan calculation service dalam satu commit besar.

## 14. Acceptance Criteria per Batch

- `rg` tidak menemukan route/import/include lama selain dokumentasi arsip;
- `python manage.py check` lulus;
- migration check tidak menghasilkan migration tak disengaja;
- Python tests domain terkait lulus;
- JavaScript tests terkait lulus;
- `npm run build` lulus bila source Vite berubah;
- tidak ada 404 asset pada browser network;
- seluruh page utama dapat dibuka;
- save/edit/export workflow terkait tetap bekerja;
- copy/import/backup round-trip tetap bekerja;
- data Project lama dapat dibuka;
- no console error;
- dokumentasi audit dan UAT diperbarui.

## 15. Keputusan Cleanup

Cleanup dimulai dari kode mati yang tidak memengaruhi data. Page atau mode yang
telah dipensiunkan dihapus setelah backend penggantinya benar-benar menjadi SSOT.

Prioritas paling aman dan bernilai:

1. hapus fungsi mass edit Dashboard lama;
2. hapus template Rincian RAB yang tidak pernah dirender;
3. hapus duplicate ExportManager;
4. pensiunkan UI Orphan Cleanup sambil mempertahankan auto cleanup;
5. pensiunkan Audit Trail UI/API pembacaan sambil mempertahankan histori;
6. pindahkan export-test ke automated tests;
7. hapus mode Tahapan dari Rekap Kebutuhan secara menyeluruh;
8. konsolidasikan Kurva S ke server adapter;
9. baru setelah itu evaluasi penghapusan API v1, projection model, alias, dan
   compatibility layer.
