# Implementation Execution Tracker R4/R5

**Mulai:** 14 Juni 2026  
**Master plan:** `27_Master_Implementation_Plan_20260614.md`  
**Status keseluruhan:** **IN PROGRESS - WP-00 / WP-B1**

## 1. Aturan Tracking

Dokumen ini diperbarui ketika:

- work package dimulai, selesai, diblokir, atau berubah scope;
- ditemukan kondisi yang belum dibahas dalam audit/planning;
- keputusan owner atau kontrak teknis berubah;
- baseline/test menghasilkan kegagalan baru;
- artefak dipindahkan dari `IMPLEMENT` menjadi `REMOVE`, `RETAIN`, atau `DEFER`.

Status:

| Status | Arti |
|---|---|
| `PENDING` | belum dimulai |
| `IN PROGRESS` | sedang dikerjakan |
| `BLOCKED` | tidak dapat lanjut tanpa keputusan/dependency |
| `DONE` | Definition of Done terpenuhi |
| `DEFERRED` | ditunda dengan alasan dan gate eksplisit |
| `REMOVED` | diselesaikan melalui cleanup |

## 2. Progress Work Package

| WP | Scope | Status | Mulai | Selesai | Gate/Dependency | Catatan |
|---|---|---|---|---|---|---|
| WP-00 | Inventory, ownership ledger, baseline | IN PROGRESS | 2026-06-14 | - | Gate 0 | Baseline dan consumer scan berjalan |
| WP-A1 | Stored XSS removal | PENDING | - | - | WP-00 | Boleh paralel setelah baseline |
| WP-A2 | CSP report-only/enforcement plan | PENDING | - | - | WP-A1 | - |
| WP-B1 | Canonical Rekap calculation | IN PROGRESS | 2026-06-14 | - | WP-00, Gate B1 | Kontrak service dan compatibility aliases diterapkan |
| WP-B2 | Shared cache signature | PENDING | - | - | WP-B1 | - |
| WP-B3 | Atomic mutation convention | PENDING | - | - | WP-00 | - |
| WP-B4 | Canonical readiness | PENDING | - | - | WP-B1 | - |
| WP-B5 | Server-authoritative export | PENDING | - | - | B1/B2/B4 | - |
| WP-B6 | Canonical weekly distribution | PENDING | - | - | WP-B4 | - |
| WP-B7 | CUSTOM live-reference | PENDING | - | - | B3/B4 | - |
| WP-B8 | Tipe LAIN | PENDING | - | - | B3 | - |
| WP-B9 | Bundle limits | PENDING | - | - | B7/B8 | - |
| WP-B10 | Actual-cost legacy mapping | PENDING | - | - | WP-00/B3/B6 | Eksekusi hanya jika data legacy ada |
| WP-P1..P9 | Integrasi per-page | PENDING | - | - | Shared WP | - |
| Fase 3 | Cleanup/deprecation | PENDING | - | - | Replacement gates | - |
| Fase 4 | Regression/UAT | PENDING | - | - | Semua WP target | - |

## 3. Gate Status

| Gate | Status | Evidence |
|---|---|---|
| Gate 0 - Section E/G diterapkan | PASS | Doc 26/27 mengunci no optimistic locking, no 409 concurrency, no 207-save |
| Gate 0 - VP-02 | PASS | HTTP 422 dikunci |
| Gate 0 - Audit Trail | PASS | Reader UI/API = cleanup CL-17; writer/history retain |
| Gate 0 - Baseline | PASS | Django check, 23 backend tests, dan 235 frontend tests lulus; build tidak dijalankan karena output `dist` sudah dirty sebelum WP |
| Gate B1 - Contract output | PASS | Field kanonik ditambah; alias lama dipertahankan |
| Gate B1 - Fixture parity | PASS | Fixture komponen-harga-markup-volume lulus |
| Gate B1 - Default markup test | PASS | Project tanpa `ProjectPricing` menghasilkan 10.00% |

## 4. Baseline dan Known Failures

| ID | Command/Area | Baseline | Klasifikasi | Owner/Disposition |
|---|---|---|---|---|
| KF-01 | Audit Trail admin-only tests | Test client redirect login meski `force_login` | known-failing | REMOVE bersama CL-17; pastikan penyebab bukan auth global |
| KF-02 | Rincian/export-button visibility | 3 fixture mendapat HTTP 302, expected 200 | known-failing | WP-00 triage; fix test/environment bila masih relevan |
| KF-03 | Rekap Kebutuhan suite teardown | Assertions lulus; exit 1 karena DB dipakai session lain | environment-only | Gunakan `--keepdb`; catat assertion terpisah dari teardown |
| KF-04 | Frontend Vitest | 235 passed, 25 skipped | passing | Baseline 2026-06-14 |
| KF-05 | Django targeted baseline | 20 passed sebelum WP-B1 | passing | `tests_item_ssot` + `tests_template_ahsp_formula_state` |
| KF-06 | Frontend production build | Tidak dijalankan | protected-dirty-output | `detail_project/static/detail_project/dist` sudah memiliki perubahan user; jangan overwrite pada WP-B1 |

`python manage.py check` juga lulus tanpa issue.

## 5. Finding Ownership Ledger

Ledger lengkap dikembangkan pada WP-00. Entri awal yang mengikat WP-B1:

| Finding | Severity | Owner WP | Action | Acceptance |
|---|---|---|---|---|
| RA-01 | Critical | WP-B1 | REPLACE | default markup tunggal 10.00 |
| RA-02 | Critical | WP-B1/WP-P5 | REPLACE | scope total konsisten |
| RA-03 | High | WP-B1/WP-B5 | REPLACE | web = export |
| RR-02 | Critical | WP-B1 | REPLACE | no 0%/10% divergence |
| KS-05 | High | WP-B1/WP-P7 | REPLACE | bobot = G×volume, pre-PPN |
| A-2/RR-11/KS-03/RK-04 | High/Medium | WP-B2 | IMPLEMENT | harga/markup invalidates consumers |

Medium/Low akan diberi salah satu disposisi:
`folded-into-WP`, `cleanup`, `defer-post-launch`, atau `no-action`.

## 6. Unexpected Findings

### UF-001 - Default Markup Service Bertentangan dengan Model

**Ditemukan:** 14 Juni 2026 saat WP-00.

- `ProjectPricing.markup_percent` default = `10.00`.
- API pricing juga memakai fallback `10.00`.
- `compute_rekap_for_project()` menginisialisasi `proj_markup = Decimal("0")`.

**Dampak:** Project tanpa row `ProjectPricing` dihitung 0% oleh calculation
service, sementara adapter/API lain dapat memakai 10%.

**Disposition:** masuk WP-B1; tambahkan contract test Project tanpa pricing row.

### UF-002 - Cache Rekap Tidak Memuat Nilai Markup Override

**Ditemukan:** 14 Juni 2026 melalui contract test WP-B1.

- Signature cache hanya bergantung pada timestamp pekerjaan dan metadata source.
- `save(update_fields=["markup_override_percent"])` tidak wajib memperbarui
  `updated_at`.
- Hasil setelah override dapat tetap memakai markup project dari cache lama.

**Disposition:** nilai `markup_override_percent` dimasukkan langsung ke signature.
Contract test membuktikan perubahan 12.50% menjadi override 5.00% terbaca.

### UF-003 - Contract Test Optimistic Concurrency Lama Masih Aktif

**Ditemukan:** 14 Juni 2026 pada baseline
`tests_template_ahsp_formula_state`.

Suite masih mengeksekusi dan mengharapkan respons `409` untuk stale write, padahal
Section G membatalkan optimistic locking app-wide.

**Disposition:** jangan dipertahankan sebagai kontrak baru. Rekonsiliasi endpoint
dan test dilakukan oleh WP-B3/WP-P2 menggunakan last-write-wins + transaksi
atomik.

### UF-004 - API Rekap Menganggap Markup 0% sebagai Missing

**Ditemukan:** 14 Juni 2026 saat migrasi contract WP-B1.

`api_get_rekap_rab()` sebelumnya memasukkan `0` ke kondisi nilai kosong, lalu
menyuntikkan default/project markup dan menghitung ulang F/G/total.

**Dampak:** markup eksplisit 0% dapat berubah menjadi 10% pada response API dan
controller menjadi calculation source kedua.

**Disposition:** rekalkulasi di controller dihapus. API hanya menambahkan alias
presentasi, sementara 0% tetap diperlakukan sebagai nilai valid.

## 7. Change and Decision Log

| ID | Tanggal | Jenis | Perubahan/Keputusan | Dampak |
|---|---|---|---|---|
| DEC-001 | 2026-06-14 | Contract | Default markup = 10.00% | WP-B1 dan seluruh consumer |
| DEC-002 | 2026-06-14 | Contract | Last-write-wins; no optimistic locking/409 | WP-B3/Px |
| DEC-003 | 2026-06-14 | Contract | Atomic save = 200/400-422/500; no 207 | WP-B3/Px |
| DEC-004 | 2026-06-14 | Contract | VP-02 dependency delete = 422 | WP-B3/P3 |
| DEC-005 | 2026-06-14 | Cleanup | Audit Trail reader dihapus; writer/history retain | CL-17 |
| DEC-006 | 2026-06-14 | Reliability | Audit writer retain dengan observability AT-05 | WP-B7/Fase 3 |
| DEC-007 | 2026-06-14 | Git safety | Snapshot worktree dibuat pada branch `checkpoint/r5-planning-wp-b1-start-20260614`, kemudian pekerjaan dilanjutkan di branch implementasi terpisah | Seluruh fase eksekusi |

Perubahan baru yang belum dibahas harus dicatat di sini sebelum mengubah master
plan atau implementasi.

## 8. WP-B1 Execution Notes

Target awal:

1. tetapkan konstanta/default markup canonical `Decimal("10.00")`;
2. perbaiki fallback `compute_rekap_for_project()` dan helper terkait;
3. pertahankan compatibility aliases sementara;
4. tambahkan nama output canonical tanpa memutus consumer lama;
5. tambahkan contract tests:
   - tanpa ProjectPricing row → 10%;
   - ProjectPricing eksplisit;
   - override pekerjaan;
   - `G × volume`;
   - PPN tidak masuk work total;
   - null/zero volume.

Selesai 14 Juni 2026:

- default kanonik `10.00%` diterapkan pada service dan helper;
- output kanonik ditambahkan tanpa menghapus alias lama;
- signature sementara memuat `markup_override_percent`;
- rekalkulasi F/G/total di controller Rekap RAB dihapus;
- total export Rincian AHSP membaca service kanonik;
- contract test mencakup default, project markup, override pekerjaan, 0%
  eksplisit, missing volume, PPN tidak masuk work total, parity export, dan
  expanded nested multiplier.

Belum dilakukan:

- migrasi consumer page;
- penghapusan compatibility alias;
- cache helper WP-B2;
- readiness WP-B4.
- kebijakan rounding lintas renderer masih perlu dikunci/dibuktikan sebelum
  WP-B1 berstatus `DONE`.

## 9. Verification Log

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-14 | WP-00 | `python manage.py check` | PASS | 0 issue |
| 2026-06-14 | WP-00 | `tests_item_ssot` + `tests_template_ahsp_formula_state` | PASS | 20 tests |
| 2026-06-14 | WP-00 | `npm run test:frontend -- --run` | PASS | 235 passed, 25 skipped |
| 2026-06-14 | WP-B1 | Rekap contract + SSOT/formula suites | PASS | 26 tests |
| 2026-06-14 | WP-B1 | Rekap contract suite | PASS | 7 tests termasuk nested/export/zero markup |
