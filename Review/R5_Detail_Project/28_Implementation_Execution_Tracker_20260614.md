# Implementation Execution Tracker R4/R5

**Mulai:** 14 Juni 2026  
**Master plan:** `27_Master_Implementation_Plan_20260614.md`  
**Status keseluruhan:** **IN PROGRESS - WP-B1/WP-B2/WP-A1/WP-B3 DONE / WP-B4 + WP-A2 NEXT**

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
| WP-A1 | Stored XSS removal | DONE | 2026-06-14 | 2026-06-14 | WP-00 | F-01+LP-01+RR-01+RR-18 fixed & regression-locked (Django 2 + vitest 9). Browser visual UAT → Fase 4. CSP/SRI = WP-A2 |
| WP-A2 | CSP report-only/enforcement plan | PENDING | - | - | WP-A1 | - |
| WP-B1 | Canonical Rekap calculation | DONE | 2026-06-14 | 2026-06-14 | WP-00, Gate B1 | Service, rounding, nested, dan parity web/export terverifikasi |
| WP-B2 | Shared cache signature | DONE | 2026-06-14 | 2026-06-14 | WP-B1 | Rekap/Kurva/chart/Kebutuhan memakai helper domain bersama |
| WP-B3 | Atomic mutation convention | DONE | 2026-06-14 | 2026-06-14 | WP-00 | inc1 LP-02/JDW-01/03 · inc2 Volume VP-01/02/03/04 + quantity atomic · inc3 Harga HI-06/HI-01 · inc4 Template TA-01 · inc5 last-write-wins frontend/backend. 25 contract/failure tests; no concurrency 409 atau active-form 207 pada endpoint target. HI-16/HI-02→WP-P1; DB CheckConstraint koef→follow-up migrasi |
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
| KF-04 | Frontend Vitest | 247 passed, 25 skipped | passing | Checkpoint WP-B3 2026-06-14 |
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

### UF-005 - Kurva S Membaca Cache tetapi Tidak Menulis Cache

**Ditemukan:** 14 Juni 2026 pada WP-B2.

`api_kurva_s_data()` melakukan cache lookup dengan signature manual, tetapi
response sukses tidak pernah disimpan. Cache praktis selalu miss.

**Disposition:** response disimpan dengan shared signature; contract test
membuktikan perubahan harga bulk menghasilkan nilai Kurva S baru.

### UF-006 - Rekap Kebutuhan Weekly Menulis Cache Dua Kali

**Ditemukan:** 14 Juni 2026 pada WP-B2.

Entry identik ditulis melalui blok conditional lalu langsung ditulis ulang.

**Disposition:** hapus write kedua; hanya simpan saat signature berhasil dibuat.

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
| DEC-008 | 2026-06-14 | Calculation | Komponen, E/F/G, dan total pekerjaan memakai Decimal HALF_UP 2 desimal; volume 3 desimal; rounding base hanya untuk grand total RAB | WP-B1 dan seluruh consumer |
| DEC-009 | 2026-06-14 | Cache | Signature dibagi domain calculation/requirements/schedule; tabel besar memakai count+timestamp, nilai finansial kritis ikut digest | WP-B2 dan consumer |

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
- kalkulasi uang memakai `Decimal` + `ROUND_HALF_UP`: komponen/E/F/G dan total
  pekerjaan dua desimal; volume tiga desimal;
- parity service, API Rekap RAB, dan adapter export Rekap RAB dikunci test.

Belum dilakukan:

- migrasi consumer page;
- penghapusan compatibility alias;
- cache helper WP-B2;
- readiness WP-B4.
- migrasi seluruh consumer hilir tetap berada pada WP-Px/WP-B5, bukan scope
  service WP-B1.

## 9. Verification Log

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-14 | WP-00 | `python manage.py check` | PASS | 0 issue |
| 2026-06-14 | WP-00 | `tests_item_ssot` + `tests_template_ahsp_formula_state` | PASS | 20 tests |
| 2026-06-14 | WP-00 | `npm run test:frontend -- --run` | PASS | 235 passed, 25 skipped |
| 2026-06-14 | WP-B1 | Rekap contract + SSOT/formula suites | PASS | 26 tests |
| 2026-06-14 | WP-B1 | Rekap contract suite | PASS | 7 tests termasuk nested/export/zero markup |
| 2026-06-14 | WP-B1 | Rounding + service/API/export parity | PASS | 9 tests sebelum explicit-zero-volume ditambah |
| 2026-06-14 | WP-B1 | Final targeted regression | PASS | 30 tests; Django system check 0 issue |
| 2026-06-14 | WP-B2 | Shared signature contract | PASS | Harga bulk, override, volume, progress, endpoint consumers, dan query budget |
| 2026-06-14 | WP-B2 | Final targeted regression | PASS | 40 tests; Django system check 0 issue |
| 2026-06-14 | WP-B1/B2 | **Verifikasi independen (Claude) — contract** | PASS | `tests_rekap_calculation_contract` 16/16; konfirmasi `DEFAULT_PROJECT_MARKUP_PERCENT=10.00` (`services.py:37`), controller Rekap RAB tak rekalkulasi (`views_api.py:4577`), chart-data via `build_project_cache_signature` (`:7234`) |
| 2026-06-14 | WP-B1/B2 | **Gate B1 closure — regresi consumer hilir** | PASS | 70/70: `tests_volume_export_adapter, harga_items_export, harga_items_save_api, list_pekerjaan_export, export_access, export_csrf, item_ssot, change_status_sync, page_cache_headers, api_v2_access, orphan_autocleanup, phase4_negative_param` (+contract). Tak ada regresi dari refactor `compute_rekap_for_project`/signature |
| 2026-06-14 | WP-B1/B2 | **Regresi dashboard + security + data-safety** | PASS | 48/48: `dashboard` (mass_edit/data_retention/prelaunch_smoke), `tests_page_security_audit`, `tests_phase0_data_safety` |

| 2026-06-14 | WP-A1 | F-01 dashboard chart XSS | PASS | `dashboard.tests_chart_xss` 2/2: payload `</script><script>alert(1)` ter-escape jadi `<...`; nilai numerik (`1000000.0`) tetap angka. Helper `_safe_inline_json` (`dashboard/views.py`) mirror escaping `json_script` + DecimalEncoder float |

**Catatan WP-A1 (decision):** F-01 memakai pendekatan **escape-translate** (`<`/`>`/`&`→`\uXXXX`, U+2028/2029 sudah ditangani `json.dumps ensure_ascii`) — bukan `json_script` — untuk mempertahankan nilai float chart & zero perubahan template/JS (regresi minimal). Migrasi `json_script` + hapus inline = scope **WP-A2 (CSP)**. **WP-A1 SELESAI 2026-06-14:** F-01 (dashboard), LP-01 (preview Template Library), RR-01 (hierarki + highlight Rekap RAB), RR-18 (print reinjection) — semua user-data → `innerHTML` kini di-escape; dikunci `xss_render_guard.test.js` (9) + `xss_governance_guard.test.js` (3) + `dashboard.tests_chart_xss` (2). Sisa di luar WP-A1: WP-A2 (CSP report-only + SRI/self-host) dan browser visual UAT (Fase 4).

**Penutupan Gate B1 (verifikasi independen):** total **134 test OK** lintas 16+ modul consumer terdampak; tidak ada regresi pada Rekap RAB, Rincian AHSP (export parity), Rekap Kebutuhan signature, Kurva S/chart-data cache, Harga Items, SSOT item, change-status sync, dan dashboard/security. Catatan: traceback `Project.DoesNotExist`/`Http404` yang muncul saat run adalah exception yang **memang di-assert** oleh test owner-isolation (bukan kegagalan); hasil akhir runner `OK`. Doc 28 terverifikasi konsisten dengan kondisi kode aktual.

### WP-B3 — Atomic Mutation Convention (increment-1)

Helper bersama **`atomic_error_response`** (`detail_project/api_helpers.py`): `transaction.set_rollback(True)` + envelope konsisten (`ok/success/error/message/errors`), status 400/422/500 — **tak pernah 207 untuk satu save**. Diterapkan ke:
- **LP-02** (`views_api.py` upsert): error pemrosesan → batalkan SELURUH transaksi SEBELUM delete omitted; `207`→`400` (validate-before-delete).
- **JDW-01** (`views_api_tahapan_v2.py` assign_weekly): cabang `if errors` kini `set_rollback` (no partial), bukan 400 dgn klaim `saved`.
- **JDW-03** (sync gagal): rollback seluruh transaksi (weekly + sync) + pesan generik (tak bocor `str(sync_error)`, A-3).

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-14 | WP-B3 | `tests_wp_b3_atomic` (failure-injection) | PASS | 5/5: happy-path 200; JDW-01 bad-item→400 + 0 weekly rows (rollback); JDW-03 mocked-sync-fail→500 + 0 rows + no leak; LP-02 mocked-create-fail→4xx + 0 klas/pek (rollback); valid upsert 200 |
| 2026-06-14 | WP-B3 | Regresi endpoint terdampak | PASS | 22/22: `tests_wp_b3_atomic` + `tests_list_pekerjaan_upsert_validation` + `tests_list_pekerjaan_upsert_drag_drop` + `tests_change_status_sync`; `manage.py check` 0 issue. (Log "Exception: boom" = mock LP-02, bukan kegagalan) |

#### WP-B3 increment-2 — Volume cluster (VP-01/02/03/04)

- **VP-01** (`api_volume_formula_state`): restruktur **validate-all-first → reject atomik**; tak ada lagi "200 dengan errors" parsial. **VP-04** type-guard item non-dict → 400 (bukan 500).
- **VP-02** (`api_project_parameter_detail` DELETE): dependency guard `_parameter_dependents` (tokenizer match identifier utuh — `bp_3` ≠ `bp_30`) memindai computed expr + volume formula + koef formula; param dipakai → **422** + `usage`, tidak dihapus.
- **VP-03** (`api_project_parameters_sync` + `api_project_computed_parameters_sync`): **validate-before-delete** pada mode replace — payload sebagian invalid → **422**, tidak menghapus data lama.

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-14 | WP-B3 inc-2 | `tests_wp_b3_atomic.VolumeAtomicSyncTests` | PASS | Formula/parameter dan quantity memakai validate-all-first; mixed payload→400/422 tanpa write; VP-02 dependency→422; stale marker diabaikan sesuai LWW |
| 2026-06-14 | WP-B3 inc-2 | Regresi parameter/formula/volume | PASS | 45/45: + `tests_phase1_opaque_api` + `tests_volume_formula_owner_guard` + `tests_volume_pekerjaan_save_api` + `tests_formula_integration` + `tests_phase0_data_safety` |

**UF-007 (UF-003 terealisasi):** 2 test lama `tests_phase1_opaque_api` (`test_sync_*_partial_success_with_warnings`) mengunci perilaku partial-success-with-warnings (200) yang **dibatalkan VP-03/B-1**. Diperbarui ke kontrak baru: invalid item → **422** atomik, tidak ada partial. Bukan regresi — kontrak lama memang yang salah.

#### WP-B3 increment-3 — Harga Items save (`api_save_harga_items`)

Restruktur **validate-all-first → reject atomik** (no 207):
- **HI-06**: harga negatif ditolak (`dec < 0` → 400), bukan tersimpan;
- **HI-01 (backend)**: `harga_satuan` null/empty = **belum diisi → stored NULL** (tidak dikoersi ke 0, tidak error). Catatan: fix penuh HI-01 (FE kirim hanya baris dirty) = WP-P1;
- atomic: payload sebagian invalid → 400, tidak ada partial (rollback);
- markup divalidasi sebelum apply.

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-14 | WP-B3 inc-3 | `tests_wp_b3_atomic.HargaAtomicSaveTests` | PASS | 5/5: happy→250; HI-06 negatif→400 (harga utuh); HI-01 null & "" → NULL; partial(id invalid)→400 no-207 (rollback, harga tetap 100) |
| 2026-06-14 | WP-B3 inc-3 | Regresi Harga | PASS | Save atomik, null tetap missing, harga negatif ditolak, stale token diabaikan; frontend tidak membersihkan dirty state setelah rollback |

**Direklasifikasi keluar WP-B3:** HI-16 + HI-02 (conversion "Terapkan dan Simpan" atomik = fitur, D-HI-02) → **WP-P1**. DB `CheckConstraint(koefisien__gte=0)` tetap follow-up hardening migrasi.

#### WP-B3 increment-4 — Template AHSP save (`api_save_detail_ahsp_for_pekerjaan`) — WP-B3 SELESAI

- Atomicity **sudah ada** (kode: "Replace-all saves are atomic… `if errors: return`" — validate-before-mutate, no partial). Tidak diubah.
- **TA-01**: tambah penolakan koefisien **negatif** (`koef < 0` → 400) untuk koef manual maupun formula; **0 tetap sah**. `bulk_create` tak jalankan `full_clean`, jadi aturan ditegakkan di kode. DB `CheckConstraint(koefisien__gte=0)` = follow-up migrasi (hardening).

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-14 | WP-B3 inc-4 | `tests_wp_b3_atomic.TemplateSaveAtomicTests` | PASS | 3/3: happy→200 (1 detail); TA-01 negatif sibling→400 + 0 detail (atomic); koef 0→200 |
| 2026-06-14 | WP-B3 final | Regresi penuh | PASS | 96/96: `tests_wp_b3_atomic` (20) + `tests_template_ahsp_ui_regressions` + `tests_template_ahsp_formula_state` + `tests_formula_server_validation` + `tests_formula_integration` |

**UF-008 (UF-003 lanjutan):** `test_valid_items_saved_despite_invalid_sibling` (`tests_formula_server_validation`, endpoint `volume-formula-state`) mengunci partial-success (200) yang dibatalkan VP-01/A-5 → diperbarui jadi `test_invalid_sibling_rejects_whole_batch_atomically` (400, valid sibling tak tersimpan).

#### WP-B3 increment-5 — Penutupan verifikasi checkpoint

- Save quantity Volume diubah dari partial `207` menjadi validate-all-first `400` tanpa write.
- Stale token pada Template AHSP, Harga Items, parameter, computed parameter, dan formula state diabaikan sesuai last-write-wins.
- Prompt merge/reload dan polling konflik Volume dihapus.
- Frontend Harga Items mempertahankan seluruh dirty state ketika batch ditolak atomik.
- Save Volume tidak melanjutkan sync formula bila bagian volume ditolak.
- Guard frontend `atomic_save_contract_guard.test.js` mengunci kontrak tersebut.

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-14 | WP-B3 inc-5 | Contract backend target | PASS | 69/69: WP-B3 + Volume + parameter/formula + Harga + Template |
| 2026-06-14 | WP-B3 inc-5 | Frontend Vitest | PASS | 247 passed, 25 skipped; atomic/LWW guard 3/3 |
| 2026-06-14 | WP-B1/B2/A1/B3 checkpoint | Regresi gabungan | PASS | 174/174 backend + 247 frontend; `manage.py check` dan `makemigrations --check --dry-run` bersih |
| 2026-06-15 | WP-B3 verifikasi | Verifikasi fix checkpoint owner (commit `c1e46bd7`) | PASS | 409 nol di `views_api.py`; quantity-save 400-atomic (1772-1806); `harga_items.js` cabang gagal pertahankan dirty (658-699); test LWW 164/210 ada |
| 2026-06-15 | WP-B3 follow-up | `api_save_detail_ahsp_gabungan` 207→atomic 400 | PASS | 92/92: `tests_wp_b3_atomic` (+`DetailGabunganAtomicSaveTests` 3) + `tests_phase1_opaque_api` + `tests_formula_server_validation` |

**WP-B3 SELESAI.** Endpoint target kini all-or-nothing (`200/400-422/500`), tidak memiliki concurrency `409`, tidak mengembalikan `207` untuk form save, dan frontend tidak mengakui data yang di-rollback sebagai tersimpan.

**Verifikasi 2026-06-15 (fix checkpoint owner):** ketiga temuan HIGH owner terverifikasi benar terhadap kode aktual — (1) seluruh `status=409`/`is_stale_sync` dihapus dari `views_api.py`; (2) `api_save_volume_pekerjaan` validate-all-first → `atomic_error_response(400)` tanpa partial-write/207; (3) `harga_items.js` cabang gagal hanya menandai `ux-invalid`, baseline `origCanon`/clean hanya pada sukses. Test 409 lama sudah diubah ke last-write-wins (200).

**Follow-up 2026-06-15:** ditemukan satu jalur `207` aktif yang belum tercakup — `api_save_detail_ahsp_gabungan` (URL `/detail-ahsp/save/`, masih reachable). Diperbaiki ke kontrak atomik (`atomic_error_response(400)`, set_rollback membatalkan delete+create per-item; tak ada 207). Catatan: JS pemanggilnya (`detail_ahsp_gabungan.js`) **orphan** (tak dimuat template manapun) — endpoint reachable-by-URL tapi tanpa halaman UI aktif; tetap dihardening agar selaras DEC-003 dan tak meninggalkan partial-write live hingga cleanup.

**Residual cleanup yang sengaja tidak diperbaiki:** satu jalur `207` tersisa pada API full-save List Pekerjaan lama (`api_save_list_pekerjaan`, line 779) — tidak dipanggil frontend (kanonikal = `/upsert/`), dimiliki cleanup Section E (`CL-05`). Endpoint gabungan + JS orphan-nya tetap milik `CL-10` (hapus route/JS/test legacy); kontrak atomiknya sekarang hanya jaring pengaman sampai dihapus — jangan jadikan fitur baru.
