# Master Implementation Plan R4/R5

**Tanggal:** 14 Juni 2026  
**Sumber otoritatif:** audit 09 dan 16-24, cleanup roadmap 25, rekonsiliasi 26  
**Status:** **READY FOR EXECUTION - contract dan urutan kerja telah dikunci**

## 1. Tujuan

Dokumen ini mengubah hasil audit menjadi work package terurut tanpa:

- memperbaiki akar masalah yang sama berkali-kali;
- mengimplementasikan rekomendasi lama yang dibatalkan Section G;
- memperbaiki artefak yang akan dihapus berdasarkan Section E;
- mengubah workflow user tanpa keputusan owner;
- membuat migrasi database besar yang tidak diperlukan.

Urutan utama:

```text
Fase 0: contract freeze
  ├─ Track A: security quick-wins
  └─ Track B: shared service/foundation
       ↓
Fase 2: integrasi per-page
       ↓
Fase 3: cleanup/deprecation
       ↓
Fase 4: full regression + UAT
```

## 2. Aturan Otoritatif

### 2.1 Concurrency dan Atomicity

- Kebijakan aplikasi adalah **last-write-wins**.
- Tidak ada optimistic locking, revision token, stale-write `409`, atau dialog
  konflik.
- Satu aksi save bersifat atomik:

```text
200      seluruh aksi berhasil
400/422  seluruh aksi ditolak tanpa perubahan
500      transaksi rollback tanpa perubahan
```

- `207` hanya untuk batch yang itemnya independen, bukan satu form/save.
- Delete parameter yang masih dipakai mengembalikan **422** beserta dependency,
  bukan `409`.

### 2.2 JSON

- JSON bukan format laporan.
- Tipe paket yang diperbolehkan:
  - `project_backup`;
  - `work_structure_template`;
  - `diagnostic_snapshot` internal.
- Laporan user memakai PDF/XLSX/Word/CSV sesuai kebutuhan.

### 2.3 Export

- Export laporan resmi server-authoritative.
- Layar dan export memakai calculation service/dataset canonical yang sama.
- Draft belum disimpan tidak masuk export.
- Background export hanya digunakan setelah threshold beban tercapai.
- Identitas laporan berasal dari Project pada Dashboard.
- Signature/pagination hanya diterapkan pada laporan yang memerlukannya.

### 2.4 Nilai dan Readiness

- `null` berarti belum diisi.
- `0` berarti nilai eksplisit dan sah.
- Nama nilai biaya mengikuti kontrak:
  - `component_cost_before_markup`;
  - `markup_amount`;
  - `unit_price_after_markup`;
  - `work_total_after_markup = unit_price_after_markup × volume`.
- Rekap Kebutuhan memakai `Total Harga Dasar Kebutuhan`, sebelum markup dan PPN.
- Readiness memakai schema D-RK-07 sebagai superset lintas-page.

### 2.5 Cleanup Filter

Jangan memperbaiki artefak yang akan dihapus:

- Dashboard mass edit lama;
- Audit Trail UI/API pembacaan;
- Orphan Cleanup UI;
- Rincian RAB template lama;
- mode Tahapan Rekap Kebutuhan;
- client Kurva S sebagai calculation SSOT;
- dead controls dan duplicate export dependency.

## 3. Kategori Tindakan

Setiap task wajib diberi salah satu status:

| Status | Arti |
|---|---|
| `IMPLEMENT` | kapabilitas baru/shared contract |
| `REPLACE` | ganti implementasi lama dengan canonical implementation |
| `REMOVE` | hapus artefak berdasarkan Section E/roadmap 25 |
| `RETAIN` | pertahankan compatibility/data sementara |
| `DEFER` | tidak dikerjakan sampai gate tertentu terpenuhi |

## 4. Fase 0 - Contract Freeze dan Baseline

### WP-00 - Surface and Consumer Inventory

**Status:** `IMPLEMENT`  
**Tujuan:** memastikan implementation plan tidak melewatkan mode atau consumer.

Scope:

- cocokkan toolbar, modal, mode, route, API, export, dan mobile state terhadap
  audit per-page;
- daftar semua consumer shared calculation, cache, readiness, export, dan JSON;
- buat `finding ownership ledger` untuk seluruh P0/High dengan kolom:
  `finding_id`, `work_package`, `action`, `dependency`, `test`, dan `status`;
- masukkan seluruh finding Medium/Low ke ledger yang sama dengan disposisi ringan:
  `folded-into-WP`, `cleanup`, `defer-post-launch`, atau `no-action`;
  Medium/Low tidak otomatis menjadi work package terpisah;
- tandai artefak Section E sebagai `REMOVE`;
- tandai compatibility Section E sebagai `RETAIN`;
- ambil baseline test dan build sebelum edit.

Definition of Done:

- matriks route-template-JS-API-export tersedia;
- tidak ada item audit tanpa owner work package;
- seluruh P0/High mempunyai finding ID dan acceptance test eksplisit;
- seluruh Medium/Low mempunyai disposisi sehingga tidak hilang dari backlog;
- baseline `manage.py check`, Python tests relevan, JS tests, dan build tercatat;
- baseline memisahkan `known-failing` dari regresi baru, minimal:
  - Audit Trail admin-only test diarahkan ke login meski memakai `force_login`;
  - Rincian/export-button fixture mendapat HTTP 302 ketika mengharapkan 200;
  - Rekap Kebutuhan assertion lulus tetapi teardown database berakhir exit 1
    karena session PostgreSQL lain;
- setiap known failure mempunyai owner, reproduksi command, dan keputusan
  `fix`, `remove bersama cleanup`, atau `environment-only`;
- perubahan existing user yang tidak terkait tidak disentuh.

### Gate 0

Fase berikutnya hanya dimulai setelah:

- Section G dibaca sebagai override audit lama;
- VP-02=`422` tercatat;
- Audit Trail dipetakan sebagai cleanup, bukan security repair;
- tidak ada optimistic locking/409/207-save pada task list.

## 5. Track A - Security Quick-Wins

Track A dapat berjalan paralel dengan Track B karena tidak mengubah calculation
contract.

### WP-A1 - Stored XSS Removal

**Status:** `REPLACE`  
**Sumber:** F-01, LP-01, RR-01, RR-18, A-4.

Scope:

- Dashboard chart/bootstrap payload memakai `json_script` atau serializer aman;
- List Pekerjaan preview dibangun dengan DOM API/`textContent`;
- Rekap RAB hierarchy dan print tidak melakukan reinjection HTML user;
- tambah regression payload `</script>`, closing tag, event handler, dan quote.

Tidak termasuk:

- Audit Trail; UI/API-nya dihapus pada cleanup CL-17.

Definition of Done:

- tidak ada user data masuk `innerHTML` tanpa sanitizer/escaping terkontrol;
- XSS regression tests lulus;
- output visual tidak berubah;
- browser console bebas CSP/XSS error baru.

### WP-A2 - CSP Report-Only dan Dependency Governance

**Status:** `IMPLEMENT`  
**Sumber:** A-4, VP-08, TA-11, RR-15.

Scope:

- tambahkan CSP `Report-Only` lebih dahulu;
- inventaris inline script/style dan CDN;
- self-host dependency atau gunakan SRI bila self-host belum dilakukan;
- kumpulkan violation sebelum enforcement.
- buat milestone enforcement setelah inline script/style aktif selesai
  dipindahkan atau diberi nonce/hash.

Definition of Done:

- CSP report-only aktif pada environment target;
- tidak ada dependency baru tanpa integrity/self-host policy;
- laporan violation tersedia;
- target dan acceptance criteria CSP enforcement tercatat;
- enforcement diaktifkan pada milestone terpisah setelah violation workflow
  utama menjadi nol atau mempunyai exception yang disetujui.

### Gate A

- regression XSS lulus;
- CSP report-only tidak memblokir workflow;
- Audit Trail tidak ikut dipoles.

## 6. Track B - Fondasi Shared

### WP-B1 - Canonical Rekap Calculation Service

**Status:** `REPLACE`  
**Prioritas:** pertama  
**Sumber:** A-1, B-3, RA-01/03, RR-02, KS-05.

Tujuan:

- satu service menghitung komponen biaya sebelum markup, markup, harga satuan
  setelah markup, volume, dan total pekerjaan;
- satu default markup resmi sebesar **10,00%** ketika Project belum mempunyai
  konfigurasi markup;
- tidak ada adapter/controller menghitung ulang dengan default berbeda.

Contract output minimum:

```text
pekerjaan_id
component_cost_before_markup
markup_percent_effective
markup_amount
unit_price_after_markup
volume
work_total_after_markup
```

WP-B1 hanya menghasilkan nilai kalkulasi dan diagnostics mentah yang diperlukan
untuk perhitungan. Object `readiness` lintas-page dikomposisi oleh WP-B4 agar
dependency tidak berputar.

Consumer:

- Rincian AHSP;
- Rekap RAB;
- bobot Kurva S Jadwal;
- adapter export terkait;
- diagnostics Rekap Kebutuhan, tanpa mengubah basis harga dasarnya.

Definition of Done:

- satu source default markup `10.00`;
- web dan export menghasilkan nilai identik;
- override pekerjaan bekerja;
- total pekerjaan = `G × volume`;
- PPN tidak masuk bobot pekerjaan;
- test default, override, null volume, zero volume, nested AHSP, dan rounding lulus.

### WP-B2 - Shared Cache Signature and Revision

**Status:** `IMPLEMENT`  
**Dependency:** WP-B1  
**Sumber:** A-2, RR-11, KS-03, RK-04.

Scope:

- helper signature bersama untuk source calculation;
- sertakan perubahan HargaItemProject;
- sertakan ProjectPricing dan markup override pekerjaan;
- sertakan volume, expanded detail, weekly progress sesuai consumer;
- hindari daftar timestamp manual yang berbeda per endpoint.

Definition of Done:

- perubahan harga langsung mengubah RAB, Kurva S, dan Rekap Kebutuhan;
- perubahan markup mengubah seluruh consumer relevan;
- contract test invalidasi cache lulus;
- tidak ada cache key lama yang tetap menjadi source aktif.

### WP-B3 - Atomic Mutation Convention

**Status:** `IMPLEMENT` + `REPLACE`  
**Sumber:** A-5, B-1, G-1, G-2.

Scope:

- helper/pola validasi sebelum mutasi;
- rollback eksplisit saat errors dikumpulkan;
- response envelope konsisten;
- daftar error field/item yang mudah dipahami;
- `422` untuk dependency/domain validation;
- last-write-wins tanpa stale token.

Target awal:

- List Pekerjaan upsert;
- Volume formula/parameter sync;
- Template AHSP save/reset;
- Harga Items save/conversion;
- Jadwal weekly save/sync.

**Batas kepemilikan:** WP-B3 memiliki konvensi dan implementasi atomicity pada
endpoint inti di atas. Work package per-page hanya mengintegrasikan UX, pesan,
dan perilaku domain di atas endpoint tersebut. WP-Px tidak boleh membuat helper
transaksi atau response convention kedua.

Definition of Done:

- injected failure tidak meninggalkan partial write;
- tidak ada `ok:true` ketika sebagian save gagal;
- tidak ada save form yang mengembalikan `207`;
- tidak ada concurrency `409`;
- dua tab mengikuti last-write-wins dan masing-masing transaksi tetap atomik;
- VP-02 mengembalikan `422` + usage list.

### WP-B4 - Canonical Readiness and Missing-Value Schema

**Status:** `IMPLEMENT`  
**Dependency:** WP-B1  
**Sumber:** A-8, A-9, B-4.

Schema minimum:

```text
expanded_ready
missing_volume
missing_price
invalid_coefficient
expansion_not_ready
incomplete_planned_allocation
timeline_stale
affected_pekerjaan
affected_items
```

Scope:

- satu service diagnostics;
- `null` dan zero dibedakan;
- consumer hanya menyajikan diagnostics, tidak menghitung ulang readiness;
- warning berisi sumber page/item yang perlu diperbaiki.

Definition of Done:

- Template, Rincian, RAB, Jadwal, dan Kebutuhan membaca schema yang sama;
- warning tidak memblokir kecuali operasi memang tidak dapat dihitung;
- item penyebab dapat ditelusuri;
- contract tests null-vs-zero dan incomplete allocation lulus.

### WP-B5 - Server-Authoritative Export Framework

**Status:** `REPLACE`  
**Dependency:** WP-B1, WP-B2, WP-B4  
**Sumber:** A-3, B-2, B-5.

Scope:

- satu wrapper error dengan correlation ID;
- satu project identity provider;
- snapshot dataset per export;
- threshold sync/background;
- filename `NamaProject_TanggalExport.ext`;
- signature configuration per report;
- aturan PDF signature tidak berdiri sendiri;
- package JSON dipisahkan dari report export.

Definition of Done:

- layar saved dan export memakai calculation dataset sama;
- error tidak membocorkan `str(e)`;
- export kosong tetap diizinkan sesuai keputusan dengan `.` bila renderer perlu;
- PDF pagination/signature lulus;
- report formats tidak menawarkan JSON;
- `project_backup` dan `work_structure_template` memiliki schema version dan
  import atomik.

### WP-B6 - Canonical Weekly Distribution Service

**Status:** `IMPLEMENT` + `REPLACE`  
**Dependency:** WP-B4  
**Sumber:** JDW/RK, KS-01..05.

Scope:

- week columns dan `week_number` berasal dari backend canonical;
- planned distribution memakai `PekerjaanProgressWeekly.planned_proportion`;
- Periode 4 Minggu mengagregasi empat bucket minggu;
- minggu parsial awal/akhir dipertahankan;
- timeline stale dihitung server-side;
- Tahapan bukan calculation source.

Definition of Done:

- JS tidak menghitung ulang week number;
- Rekap Kebutuhan weekly + 4-week memakai builder yang sama dengan Jadwal;
- total weekly + unscheduled = total kebutuhan;
- contract test JS/Python week numbering lulus;
- tidak ada auto-regenerate diam-diam saat page open.

### WP-B7 - CUSTOM Live-Reference Propagation

**Status:** `IMPLEMENT` + `REPLACE`  
**Dependency:** WP-B3, WP-B4  
**Sumber:** TA-03, TA-18, D-05.

Scope:

- perubahan master AHSP menandai dependent CUSTOM sebagai
  `reference_update_available`;
- rebuild expanded dependent dilakukan melalui aksi terkontrol;
- reset pekerjaan memicu cascade re-expansion seluruh dependent;
- kegagalan cascade terlihat pada diagnostics dan tidak dinyatakan sukses;
- audit write tetap menggunakan writer `DetailAHSPAudit` yang di-`RETAIN`.
- writer audit yang dipertahankan mempunyai observability kegagalan minimal:
  structured error log + metric/counter/alert hook ketika insert audit gagal
  (AT-05); kegagalan tidak boleh benar-benar senyap.

Definition of Done:

- perubahan master terbukti mengalir sampai Rincian, RAB, Jadwal, dan Kebutuhan;
- tidak ada dependent expanded stale yang ditampilkan sebagai ready;
- cycle dan missing reference ditolak dengan pesan terarah;
- integration test master → CUSTOM → nested bundle → laporan lulus.

### WP-B8 - Pemisahan Tipe LAIN

**Status:** `IMPLEMENT`  
**Dependency:** WP-B3  
**Sumber:** D-08.

Scope:

- tipe kanonik `OTHER_DIRECT` dan `WORK_BUNDLE`;
- migrasi aditif:
  - LAIN dengan referensi → `WORK_BUNDLE`;
  - LAIN tanpa referensi → `OTHER_DIRECT`;
- compatibility reader dipertahankan selama transisi;
- label UI manusiawi dan kode internal tidak ambigu.

Definition of Done:

- `OTHER_DIRECT` wajib mempunyai Harga Item dan tidak mempunyai referensi;
- `WORK_BUNDLE` mempunyai tepat satu referensi;
- expansion, export package, copy Project, dan import memahami kedua tipe;
- migration dry-run dan rollback plan tersedia.

### WP-B9 - Bundle Expansion Limits

**Status:** `IMPLEMENT`  
**Dependency:** WP-B7, WP-B8  
**Sumber:** D-10.

Scope:

- batas nested bundle resmi **maksimal 4 level**;
- tetapkan `MAX_EXPANDED_COMPONENTS`;
- validasi cycle, depth, dan branching sebelum menyimpan/rebuild;
- error menyebut rantai bundle dan pekerjaan sumber.

Definition of Done:

- depth 1-4 berhasil;
- depth 5 ditolak tanpa partial-write;
- komponen melebihi limit ditolak sebelum ledakan row;
- test cycle, wide branching, dan nested duplicate lulus.

### WP-B10 - Legacy Actual Cost Mapping

**Status:** `IMPLEMENT` atau `DEFER` berdasarkan inventory WP-00  
**Dependency:** WP-B3, WP-B6  
**Sumber:** JDW-05, JDW-13A.

Scope:

- petakan field biaya aktual legacy terhadap persentase realisasi canonical;
- reset realisasi menghapus seluruh projection aktual terkait;
- biaya tetap metode input/projection, bukan SSOT kedua;
- bila field/data legacy tidak ditemukan, tandai `NO MIGRATION REQUIRED`.

Definition of Done:

- tidak ada actual cost yatim setelah reset;
- import/copy Project lama menghasilkan realisasi yang konsisten;
- migration idempotent dan mempunyai dry-run report;
- planned cost tidak berubah ketika actual dibersihkan.

## 7. Fase 2 - Integrasi Per-Page

Setiap work package page membaca kontrak shared, bukan menyalin rumus.

### WP-P1 - Harga Items

**Dependency:** B1, B3, B4  
**Tindakan:** `REPLACE` + `REMOVE`.

- atomicity diwarisi dari WP-B3; page tidak membuat transaction convention baru;
- harga dasar menjadi SSOT;
- apply conversion + price disimpan atomik;
- manual override menghapus conversion profile;
- null tidak diubah massal menjadi zero;
- hapus localStorage conversion fallback;
- pensiunkan JSON report;
- Orphan Cleanup UI masuk Fase 3.

**Finding checklist:** HI-01, HI-02, HI-03, HI-04, HI-05, HI-06, HI-07,
HI-12. HI-09 direkonsiliasi oleh G-1 menjadi atomic last-write-wins. HI-16 dead
path dihapus, bukan diperbaiki.

### WP-P2 - Template AHSP

**Dependency:** B3, B4, B7, B8, B9  
**Tindakan:** `REPLACE` + `REMOVE`.

- atomicity diwarisi dari WP-B3;
- save/reset atomik last-write-wins;
- tidak ada revision token/409;
- backend menolak koefisien manual negatif dan menambahkan constraint/validator
  storage yang sesuai;
- reset memicu cascade re-expansion dependent melalui WP-B7;
- perubahan master AHSP menampilkan `reference_update_available` dan rebuild
  CUSTOM terkontrol;
- lazy stale resolution per pekerjaan;
- hapus auto reload massal page-open;
- pertahankan REF/MOD/CUSTOM, nested bundle, formula, dan transfer JSON template;
- warning menyebut tabel/item sumber masalah.
- audit write untuk source change, reset, dan cascade tetap diteruskan ke writer
  `DetailAHSPAudit` yang di-`RETAIN`; hanya reader page/API Audit Trail yang
  dihapus.

**Finding checklist:** TA-01, TA-02 (reframe atomicity), TA-03, TA-18, TA-20,
TA-21. TA-05 dibatalkan G-1. TA-17 dihapus melalui CL-08. Keputusan D-05,
D-08, dan D-10 dimiliki WP-B7/B8/B9.

### WP-P3 - Volume Pekerjaan

**Dependency:** B3, B4  
**Tindakan:** `REPLACE`.

- atomicity diwarisi dari WP-B3;
- formula sync atomik;
- validate-before-replace;
- dirty marker hanya dibersihkan setelah seluruh save berhasil;
- delete parameter terpakai = `422` + usage;
- hilangkan prompt merge/override false-positive;
- null dan zero tetap berbeda;
- pensiunkan JSON report bila tidak ada import sah.

**Finding checklist:** VP-01, VP-02, VP-03, VP-04, VP-05, VP-06, VP-07.
VP-02 memakai 422; seluruh revision-token/409 dibatalkan G-1.

### WP-P4 - List Pekerjaan

**Dependency:** B3  
**Tindakan:** `REPLACE` + `REMOVE`.

- atomicity diwarisi dari WP-B3;
- upsert menjadi satu-satunya mutation contract;
- save atomik tanpa `207/409/revision`;
- destructive impact confirmation;
- package JSON tetap sebagai `work_structure_template`;
- legacy full-save dihapus pada Fase 3 setelah telemetry.

**Finding checklist:** LP-01 dimiliki WP-A1; LP-02 dan LP-04 wajib selesai;
LP-03 dibatalkan G-1; LP-05 dihapus melalui CL-05; LP-06 dan LP-07 tetap masuk
hardening endpoint/import.

### WP-P5 - Rincian AHSP

**Dependency:** B1, B4, B5  
**Tindakan:** `REPLACE` + `REMOVE`.

- memakai output canonical calculation;
- markup override tetap fitur resmi;
- parser override menerima format desimal secara konsisten dan tidak menghapus
  titik desimal yang sah;
- hapus calculation/adaptor paralel;
- hapus dead save/reset controls dan Grand Total toolbar;
- export memakai dataset server yang sama.
- audit write perubahan markup/override tetap diteruskan ke writer
  `DetailAHSPAudit` yang di-`RETAIN`.

**Finding checklist:** RA-01, RA-02, RA-03, RA-04, RA-06, RA-07, RA-08.
RA-05 diselesaikan dengan removal CL-12; RA-11 dibatalkan G-1.

### WP-P6 - Rekap RAB

**Dependency:** B1, B2, B4, B5  
**Tindakan:** `REPLACE` + `REMOVE`.

- read-only consumer canonical calculation;
- label biaya mengikuti B-3;
- metadata Project nyata;
- print tidak reinject unsafe HTML;
- JSON report dipensiunkan;
- SheetJS/client Excel dihapus setelah parity server XLSX.

**Finding checklist:** RR-01 dimiliki WP-A1; RR-02, RR-03, RR-04, RR-05,
RR-06, RR-07, RR-08, RR-09, RR-10 wajib terpetakan. RR-20 dibatalkan G-1;
RR-24 masuk cleanup.

### WP-P7 - Jadwal Pekerjaan

**Dependency:** B1, B2, B3, B5, B6, B10  
**Tindakan:** `REPLACE` + `REMOVE` + `RETAIN`.

- atomicity diwarisi dari WP-B3;
- weekly planned/actual tetap SSOT;
- save hanya mode aktif;
- biaya rencana dan volume realisasi mengikuti keputusan;
- Kurva S saved memakai adapter server;
- Preview Draft diberi label dan memakai bobot canonical;
- hapus fallback volume/equal weight;
- hapus client calculation sebagai SSOT;
- pertahankan Tahapan sebagai projection sementara;
- export report tidak memakai JSON.
- audit write source/reset/cascade yang relevan tetap diteruskan ke writer
  `DetailAHSPAudit` yang di-`RETAIN`.

**Finding checklist:** JDW-01, JDW-02, JDW-03, JDW-04, JDW-05, JDW-11,
JDW-12, KS-01 sampai KS-05, serta R1 week number server-authoritative.
JDW-08 dibatalkan sebagai rekomendasi locking oleh G-1; keputusan
last-write-wins tetap berlaku.

### WP-P8 - Rekap Kebutuhan

**Dependency:** B1, B2, B4, B5, B6, B7, B8, B9  
**Tindakan:** `REPLACE` + `REMOVE`.

- page hanya menyajikan hasil canonical builder;
- planned proportion menjadi sumber distribusi;
- pekerjaan tanpa jadwal memakai multiplier periode `0`, bukan `1`;
- weekly builder memakai `DetailAHSPExpanded`, bukan komponen raw;
- mode: Total, Mingguan, Periode 4 Minggu;
- tampilkan Total, Teralokasi, dan Belum Terjadwal;
- filter rentang minggu tetap tersedia;
- satuan beli tidak mengubah total;
- hapus mode/filter Tahapan;
- hapus dead column visibility/hidden controls;
- export server-authoritative tanpa JSON report.

WP-P8 tidak bergantung pada penyelesaian UI page lain. Ia bergantung pada shared
contract dan data canonical; integration test dapat memakai fixture/service
langsung.

**Finding checklist:** RK-01, RK-03, RK-04, RK-05, RK-06, RK-07, RK-08,
RK-09, RK-10, RK-11, RK-12, RK-13, RK-14. RK-02 diselesaikan dengan menghapus
mode Tahapan melalui CL-06.

### WP-P9 - Dashboard

**Dependency:** Track A; B1 untuk angka biaya bila digunakan  
**Tindakan:** `REPLACE` + `REMOVE`.

- perbaiki XSS payload;
- status domain tunggal;
- quick search dan interaction state diperbaiki;
- mass edit aktif atomik;
- fungsi mass edit lama dihapus;
- JSON tetap `project_backup`, bukan report.

**Finding checklist:** F-01 dimiliki WP-A1; F-02, F-03, F-04/UX-01 wajib
selesai. F-10 dihapus melalui CL-04.

## 8. Fase 3 - Cleanup dan Deprecation

Eksekusi mengikuti roadmap 25 setelah replacement melewati gate:

1. Dashboard mass edit function lama;
2. template Rincian RAB mati dan duplicate ExportManager;
3. Orphan Cleanup UI;
4. Audit Trail UI/API pembacaan;
5. Export Test page setelah test dipindahkan;
6. legacy List Pekerjaan full-save;
7. mode Tahapan Rekap Kebutuhan;
8. client Kurva S calculation path;
9. SheetJS/Excel exporter client;
10. CSS/dead controls/management command hygiene.

`RETAIN` pada fase ini:

- `DetailAHSPAudit`, histori, dan writer backend dengan observability kegagalan
  minimal sesuai AT-05; reader UI/API tetap dihapus;
- auto orphan cleanup service;
- Tahapan projection dan API v1 sampai decoupling/telemetry selesai;
- raw fallback dan calculation aliases selama consumer lama masih ada;
- parameter migration guards;
- migration Django historis.

## 9. Fase 4 - Test dan UAT

### Contract Tests Wajib

- canonical calculation web = export;
- default markup `10.00` dan override;
- cache invalidation harga/markup;
- atomic rollback pada injected failure;
- null != zero;
- readiness schema lintas-page;
- conversion base/market menjaga total;
- week numbering JS/Python;
- saved Kurva S screen = export;
- draft Kurva S berlabel dan tidak masuk export;
- weekly + unscheduled = total kebutuhan;
- package JSON round-trip dan schema version;
- PDF signature/pagination.
- master AHSP → CUSTOM dependent → expanded → laporan;
- LAIN legacy → OTHER_DIRECT/WORK_BUNDLE;
- bundle depth 4 berhasil, depth 5/row-limit ditolak;
- actual cost legacy mapping/reset bila WP-B10 diperlukan.

### UAT Wajib

- seluruh mode desktop/mobile;
- light/dark/reduced motion/zoom 200%;
- empty/error/loading/filtered-empty;
- project kecil, menengah, besar;
- minggu parsial awal/akhir;
- nested bundle depth limit;
- copy/import Project;
- export full/range dan background threshold;
- tidak ada request asset 404 atau console error.

## 10. Gate Antar-Fase

### Gate B1

Calculation service tidak boleh diintegrasikan ke seluruh page sebelum:

- contract output disetujui;
- existing fixture parity diketahui;
- default markup tests lulus.

### Gate B3

Mutation endpoint tidak boleh diklaim selesai sebelum failure injection
membuktikan rollback.

### Gate B5

Client export lama tidak dihapus sebelum output server mencapai parity fungsi
dan format minimum.

### Gate Fase 2

Consumer hilir tidak dimigrasikan sebelum service hulunya stabil.

### Gate Cleanup

Artefak hanya dihapus jika:

- replacement live;
- telemetry/reference scan menunjukkan tidak ada consumer;
- test dipindahkan atau dihapus dengan alasan;
- smoke UAT lulus.

## 11. Urutan Eksekusi Konkret

```text
WP-00
├─ WP-A1 → WP-A2
└─ WP-B1 → WP-B2
          → WP-B3
          → WP-B4
          → WP-B5
          → WP-B6
          ├─ WP-B7 ─┐
          ├─ WP-B8 ─┴→ WP-B9
          └─ WP-B10

WP-P1 Harga
→ WP-P2 Template
→ WP-P3 Volume
→ WP-P4 List
→ WP-P5 Rincian
→ WP-P6 RAB
→ WP-P7 Jadwal
→ WP-P8 Kebutuhan

WP-P9 Dashboard berjalan paralel setelah WP-A1.
Fase 3 cleanup dimulai per-artefak setelah gate masing-masing.
```

## 12. Definition of Done Global

Sebuah work package selesai hanya jika:

- implementation dan migration yang diperlukan selesai;
- seluruh finding ID miliknya pada ownership ledger berstatus selesai,
  dipindahkan ke cleanup, atau mempunyai alasan `DEFER` yang eksplisit;
- regression + contract tests lulus;
- error state dan user message dapat dipahami;
- security/ownership diperiksa;
- tidak ada formula/SSOT kedua;
- tidak ada partial-write;
- tidak ada optimistic locking/409 concurrency;
- tidak ada JSON report yang melanggar B-2;
- docs 25/26/27 dan audit page terkait diperbarui;
- browser smoke test lulus;
- existing unrelated user changes tidak diubah.

## 13. Starting Point

Work package implementasi pertama adalah:

**WP-B1 - Canonical Rekap Calculation Service.**

Track security **WP-A1** dapat berjalan paralel karena tidak mengubah contract
calculation. Coding per-page tidak dimulai sebelum interface WP-B1 dan baseline
WP-00 tersedia.

WP-B7/B8/B9 dapat dipersiapkan setelah atomicity/readiness stabil dan harus
selesai sebelum Template AHSP serta Rekap Kebutuhan dinyatakan final. WP-B10
hanya dieksekusi bila WP-00 membuktikan data legacy actual cost memang ada.
