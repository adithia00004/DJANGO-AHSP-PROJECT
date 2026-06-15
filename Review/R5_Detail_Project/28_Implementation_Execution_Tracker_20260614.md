# Implementation Execution Tracker R4/R5

**Mulai:** 14 Juni 2026  
**Master plan:** `27_Master_Implementation_Plan_20260614.md`  
**Status keseluruhan (≈ 33% implementasi):** **IN PROGRESS - WP-A1/WP-A2(report-only)/WP-B1/WP-B2/WP-B3/WP-B4/WP-B5 DONE / WP-B6 (weekly distribution) atau WP-B7 NEXT · defer: CSP enforcement, export perf (auto-async/client-render)**

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
| WP-A2 | CSP report-only/enforcement plan | DONE (report-only); enforcement DEFERRED (milestone terpisah) | 2026-06-15 | 2026-06-15 | WP-A1 | Middleware custom report-only + hardened sink `/csp-report/` + policy + 11 test. Inventory CDN/inline + roadmap enforcement + dep-governance tercatat. Enforcement (self-host + nonce inline) = milestone terpisah |
| WP-B1 | Canonical Rekap calculation | DONE | 2026-06-14 | 2026-06-14 | WP-00, Gate B1 | Service, rounding, nested, dan parity web/export terverifikasi |
| WP-B2 | Shared cache signature | DONE | 2026-06-14 | 2026-06-14 | WP-B1 | Rekap/Kurva/chart/Kebutuhan memakai helper domain bersama |
| WP-B3 | Atomic mutation convention | DONE | 2026-06-14 | 2026-06-14 | WP-00 | inc1 LP-02/JDW-01/03 · inc2 Volume VP-01/02/03/04 + quantity atomic · inc3 Harga HI-06/HI-01 · inc4 Template TA-01 · inc5 last-write-wins frontend/backend. 25 contract/failure tests; no concurrency 409 atau active-form 207 pada endpoint target. HI-16/HI-02→WP-P1; DB CheckConstraint koef→follow-up migrasi |
| WP-B4 | Canonical readiness | DONE | 2026-06-15 | 2026-06-15 | WP-B1 | Schema `b4.4` lengkap (null≠zero; expansion missing/stale/incomplete/excess via signature bypass-proof; 3 sinyal jadwal). 5/5 consumer wired + `/readiness/` + autoload. UF-011 fixed. Migrasi 0046–0048. Test 36 readiness backend + 265 frontend |
| WP-B5 | Server-authoritative export | DONE | 2026-06-15 | 2026-06-15 | B1/B2/B4 | B5a seluruh controller export memakai error-wrapper · B5b identity (fix lokasi/tahun) · B5c filename · B5d JSON keluar report+data-package atomic/versioned · B5e signature/empty/PDF-placement locked. 3 item scope (auto-async threshold, client-render migrasi, snapshot eksplisit) DEFER ke milestone perf. Full B5+CSP suite 56/56 |
| WP-B6 | Canonical weekly distribution | IN PROGRESS (backend calc-core DONE; B6d/e ke WP-P8, B6f part-2 cleanup/defer) | 2026-06-16 | - | WP-B4 | ✅B6a builder (7 test) ✅B6b+B6c `compute_kebutuhan_timeline` canonical (weekly+4-week+unscheduled+tahapan-deprecated, parity, filter periods canonical) ✅B6f part-1 snapshot scope canonical. Verifikasi B6 targeted 37/37. ⬜B6d jadwal JS no-recompute/no-auto-regen (Vite/WP-P8) ⬜B6e parity JS↔Python ⬜B6f part-2 `api_rekap_kebutuhan_weekly` tidak ada consumer aktif ditemukan; kandidat cleanup/defer |
| WP-B7 | CUSTOM live-reference | PENDING | - | - | B3/B4 | - |
| WP-B8 | Tipe LAIN | PENDING | - | - | B3 | - |
| WP-B9 | Bundle limits | PENDING | - | - | B7/B8 | - |
| WP-B10 | Actual-cost legacy mapping | PENDING | - | - | WP-00/B3/B6 | Eksekusi hanya jika data legacy ada |
| WP-P1..P9 | Integrasi per-page | PENDING | - | - | Shared WP | - |
| Fase 3 | Cleanup/deprecation | PENDING | - | - | Replacement gates | - |
| Fase 4 | Regression/UAT | PENDING | - | - | Semua WP target | - |

## 2.5 Progress Implementasi (estimasi terbobot)

**Headline: ≈ 33% dari eksekusi implementasi selesai** (per 2026-06-15).
Prasyarat audit + planning (docs 09, 16–28) = **100% selesai** dan TIDAK dihitung di angka implementasi ini.

Estimasi terbobot per fase (bobot = perkiraan effort relatif, bukan jumlah WP):

| Fase | Bobot | % Selesai | Kontribusi | Dasar |
|---|---|---|---|---|
| Fase 1 — Shared foundation (A1–A2, B1–B10) | 45% | ~69% | ~31% | A1·A2(report-only)·B1·B2·B3·B4·**B5 DONE**; B6·B7·B8·B9·B10 PENDING (CSP enforcement + export-perf = milestone terpisah) |
| Fase 2 — Integrasi per-page (P1–P9) | 30% | ~5% | ~1.5% | readiness display terpasang di 5 halaman (bagian B4); integrasi per-page penuh belum |
| Fase 3 — Cleanup/deprecation (CL-01..17) | 10% | 0% | 0% | belum mulai (gate: replacement selesai) |
| Fase 4 — Regression/UAT | 15% | ~2% | ~0.3% | contract/regression test berjalan tiap WP; UAT formal belum |
| **Total** | **100%** | | **≈ 33%** | |

Rincian bobot Fase 1 (sub-effort relatif, total 45): A1=3 ✅, A2=3 ✅ (report-only), B1=5 ✅, B2=3 ✅, B3=6 ✅, B4=6 ✅, **B5=5 ✅**, B6=4 ⬜, B7=4 ⬜, B8=2 ⬜, B9=2 ⬜, B10=2 ⬜ → selesai 31/45 ≈ 69%.

**WP-B4 SELESAI** (inc-1 survei · inc-2/2.1/2.2 kontrak `b4.3` · UF-011 fix + UAT PASS · inc-3 5/5 consumer wired · inc-4a 3 sinyal jadwal · inc-4b stale-signature `b4.4`).

> Catatan: angka ini estimasi terbobot untuk komunikasi progres, bukan metrik presisi. Diperbarui saat status WP berubah.

## 2.6 Agenda & Sequencing (per 2026-06-15, sesudah temuan UAT)

**Prinsip:** bersihkan blocker WP-B4 lebih dulu; temuan UX per-halaman (List Pekerjaan/Template) ditunda ke WP-P2 karena tidak memblok kebenaran readiness/perhitungan.

1. **UF-011 (HIGH, blocker WP-B4) — ✅ FIXED & verified.** Frontend Harga Items kini mempertahankan null (belum-diisi ≠ 0). Satu-satunya temuan yang menghalangi validitas UAT readiness sudah bersih.
2. **WP-B4 lanjut (jalur kritis) — ⏳:**
   - (a) ✅ Owner re-UAT banner Rekap RAB **PASS** (2026-06-15) — `missing_price` (pasca-fix UF-011) + `missing_volume` terverifikasi.
   - (b) Fan-out 1-per-1: ✅ **Rincian** · ✅ **Template** · ✅ **Jadwal** · ✅ **Rekap Kebutuhan** (semua 5 consumer wired) — **inc-3 SELESAI**.
   - (c) inc-4: sinyal jadwal (`incomplete_planned_allocation`/`allocation_without_volume`/`timeline_stale`) + stale-revision (limit `updated_at`).
3. **WP-P2 (List Pekerjaan / Template AHSP / Volume) — 🔜 TIDAK memblok WP-B4, dikerjakan setelah fan-out:** UF-007 (nama mod lama saat ref_modified→ref), UF-008 (placeholder "Pekerjaan N"), UF-009 (stabilitas kode/sumber ref = Bug B), UF-010 (banner reload Template eager), UF-012 (volume lama tertaut saat ganti ref/mode — reset sudah desain, gap = UF-009/stale display), ENH-01 (item picker).

**Alasan UF-007..010 + ENH-01 tidak diangkat sekarang:** semua isu UX/setup-data di halaman List Pekerjaan/Template; tidak memengaruhi kebenaran sinyal readiness maupun perhitungan. Mengangkatnya sekarang memecah fokus WP-B4; dikelompokkan per-halaman di WP-P2.

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
| KF-07 | Subscription expired-user renewal middleware | Dua test mendapat 302: payment flow mengharapkan JSON dan write-gate lain mengharapkan 403 | known-failing, reproducible terpisah | Owner subscriptions; tidak berkaitan WP-B4/UF-011. Triage kontrak middleware vs endpoint sebelum fase subscription |
| KF-08 | Full Django checkpoint 2026-06-15 | 437 total, 40 skipped; 8 failure KF-01/KF-02 + 2 failure KF-07 | baseline-known-only | Tidak ada failure WP-B4, Rekap RAB, Harga Items, atau last-write-wins guard |
| KF-09 | Full Django checkpoint A2+B5a-c 2026-06-15 | 483 total, 40 skipped; 9 failure + 1 error seluruhnya KF-01/KF-02/KF-07 | baseline-known-only | Tidak ada failure baru pada CSP, identity, naming, export error wrapper, calculation, atau exporter |

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

### UF-007 - (UAT B4, project 163) Nama "modified" lama tertinggal saat switch ref_modified→ref

**Ditemukan:** 2026-06-15 oleh owner saat UAT readiness (bukan disebabkan WP-B4).

Pekerjaan `ref_modified` dengan nama override → diganti ke `ref` (atau ganti sumber). Nama override lama masih tampil hingga **reload**.

**Verifikasi:** **TEMUAN BARU** (tidak tercatat di doc 16). **Backend BENAR** — path replace `api_upsert_list_pekerjaan` (`views_api.py:1466-1491`) clone dari ref dengan `override=None` utk `SOURCE_REF` → `snapshot_uraian` = `nama_ahsp` referensi; reload menampilkan nilai benar. **Root cause = FRONTEND** `list_pekerjaan.js:1535`: auto-reset uraian/satuan saat pindah ke ref-like HANYA dipicu bila `oldSourceType === 'custom'` — TIDAK menangani `ref_modified → ref`, sehingga field uraian (kini read-only) menyimpan nama mod lama hingga reload. Tema = source-change UX (LP), tapi bug spesifik baru.

**Disposition:** tambahkan `oldSourceType === 'ref_modified'` ke kondisi auto-reset (atau reset uraian saat target = `ref` murni apa pun asalnya). Owner WP-P2 (List Pekerjaan) atau fix frontend tertarget. Severity: Medium (data benar di server; risiko salah-paham user).

### UF-008 - (UAT B4) Placeholder "Pekerjaan N" untuk baris ref sebelum reload

**Ditemukan:** 2026-06-15 oleh owner saat UAT.

Baris mode `ref` ditandai "Pekerjaan 1/2/3" (di mini-TOC/sidebar) alih-alih nama referensi; benar setelah reload.

**Verifikasi:** **TEMUAN BARU** (cosmetic). **Root cause = FRONTEND** `list_pekerjaan.js:1645` `collectTree()`: nama baris diambil dari `.uraian` input → `.current-ref` → fallback `Pekerjaan ${pi+1}`. Untuk baris ref belum-tersimpan, uraian kosong & `.current-ref` dihapus saat `syncFields` (`:1566`), sehingga jatuh ke placeholder. Tidak membaca nama ref terpilih dari Select2. `loadTree` pasca-reload mengisi `uraian`=snapshot benar → self-heal.

**Disposition:** di `collectTree`, untuk baris ref baca teks ref terpilih (Select2 data / `ref_label`) sebelum fallback. Severity: Low (cosmetic, pre-save). Owner WP-P2.

### UF-009 - (UAT B4) Perubahan kode/sumber referensi AHSP tidak stabil (mempertahankan versi lama)

**Ditemukan:** 2026-06-15 oleh owner saat UAT.

Mengubah kode/sumber referensi AHSP tetap mempertahankan versi yang tersimpan sebelumnya.

**Verifikasi:** **BUKAN BARU — KNOWN (Bug B family).** Terdokumentasi di `docs/BUG_REPORT_IMPORT_DETAIL_PROJECT.md` + memory [[import-detail-project-bugs]]: resolusi referensi by `kode_ahsp` saja (tanpa sumber) → "auto-update/pertahankan versi"; uniqueness per `(sumber, kode_ahsp)`. Fix parsial sudah dilakukan (resolve by `(kode_ahsp, sumber)`, `.first()` ganti `.get()`). Konsisten dgn logika replace `views_api.py:1454-1464` (REF→REF replace HANYA bila `new_ref_id != pobj.ref_id`; bila frontend kirim ref_id stale/sama → tak replace → versi lama bertahan). **Follow-up tertinggal:** "do NOT auto-change bound ref_id" + surface sumber/versi di UI List Pekerjaan. Owner WP-P2/WP-B7 (CUSTOM live-ref) — sudah dalam scope.

### UF-010 - (UAT B4) Banner reload Template AHSP muncul walau detail dibiarkan

**Ditemukan:** 2026-06-15 oleh owner saat UAT.

Membuka Template AHSP tanpa mengubah apa pun tetap menampilkan banner/prompt reload.

**Verifikasi:** **KNOWN-class (bukan regresi WP-B4/B3).** Banner `#ta-sync-banner` (`template_ahsp.js:36-50`, "auto-reload stale jobs") = sistem **kesadaran source-change** (`register_source_change_flags`/`get_pending_source_change_flags`); `api_upsert_list_pekerjaan` menandai `reload_jobs` pada setiap edit pekerjaan (`views_api.py:1543`). BERBEDA dari prompt merge/override Volume yang dihapus WP-B3 inc-5 (itu false-positive last-write-wins). Banner ini niatnya sah (detail jadi stale saat sumber pekerjaan berubah di List Pekerjaan), TAPI **terlalu eager** (menandai reload walau perubahan tak relevan ke detail). **Disposition:** review eagerness di WP-P2 (Template) — flag reload hanya saat `source_type`/`ref_id` benar-benar berubah, bukan tiap upsert. Severity: Low-Medium (UX noise). Bukan blocker UAT readiness.

### UF-011 - (UAT B4, project 163) Frontend Harga Items mengubah NULL "belum diisi" → 0.00 (mematahkan null≠zero & missing_price)

**Ditemukan:** 2026-06-15 saat UAT readiness (probe DB project 163). **Severity: HIGH untuk WP-B4.**

**Gejala:** owner buat 3 pekerjaan custom (Clear=harga+vol, Non Harga=vol saja, Non Volume=harga saja). `compute_project_readiness` BENAR menandai `missing_volume`=[938 "Non Volume"], tetapi `missing_price`=[] meski "Non Harga" tak diisi harga. Probe: item "Non Harga" (B-3695) tersimpan `harga_satuan=0.00`, BUKAN NULL → karena 0=gratis eksplisit (kontrak b4.3), benar tidak diflag. **Akar: harga jadi 0.00, bukan NULL.**

**Root cause = FRONTEND `harga_items.js`:** (1) render `:399` `r.harga_canon === '' ? '0.00'` → harga NULL ditampilkan "0.00", `origCanon` `:425` jadi "0.00"; (2) save `:608-621` iterasi SEMUA baris, `:614` `if(!canon) canon='0.00'`, `:620` push tiap baris → baris belum-diisi terkirim `harga_satuan:"0.00"` → backend simpan 0.00. Backend HI-01 (`api_save_harga_items` simpan null utk null/empty) BENAR tapi **dikalahkan** frontend yang mengirim "0.00". `_upsert_harga_item` membuat item baru dengan `harga_satuan=NULL` (default), jadi sumber 0.00 murni dari save Harga Items.

**Dampak:** setiap save Harga Items meng-convert seluruh item belum-diisi → 0 → **`missing_price` praktis tak pernah muncul**; melanggar keputusan terkunci HI-01 (null≠zero). Mengurangi nilai sinyal WP-B4 yang baru dibangun.

**Fix (frontend):** render NULL sebagai kosong + placeholder "belum diisi" (bukan "0.00"), `origCanon=''`; saat save kirim `harga_satuan:null` (bukan "0.00") untuk baris kosong/belum-diisi (jangan koersi `''→'0.00'`, jangan push baris yang tetap kosong sebagai 0). Backend sudah mendukung null (HI-01). Tambah regression test (frontend: baris kosong → payload null; backend: sudah ada).

**Disposition:** **FIXED 2026-06-15** (frontend `harga_items.js`, 3 path koersi 0.00 dihapus):
- render `:399` → harga NULL tetap kosong + placeholder "belum diisi"; `origCanon=''`; hanya baris belum-diisi yang `hi-row-empty` (0 eksplisit tidak).
- save `:608+` → field kosong dikirim `harga_satuan: null` (bukan `"0.00"`); success-branch pertahankan status belum-diisi.
- blur handler `:564+` → kosong tidak lagi autofill `0.00` (tetap belum-diisi); CSV export tampilkan kosong utk belum-diisi.
- review lanjutan menutup edge case clear-existing-price: event `input` kini menganggap kosong sebagai perubahan valid, mengaktifkan dirty/save, menampilkan status "belum diisi", dan tidak memberi `ux-invalid`; sebelumnya blur memperbaiki visual tetapi tombol Simpan dapat tetap disabled.
- Guard: `atomic_save_contract_guard.test.js` +1 (UF-011: tak ada koersi `'0.00'`, kirim `harga_satuan: null`). **Verifikasi:** frontend 253 pass (+1) / 25 skip; backend `tests_wp_b3_atomic`+`tests_wp_b4_readiness` 51/51 (HI-01 null-preserve + readiness missing_price tetap hijau); `node --check` OK. Backend HI-01 tidak diubah (sudah benar). Severity HIGH → CLEARED sebelum lanjut WP-B4.

### UF-012 - (UAT B4) Volume lama tetap tertaut saat ganti referensi/mode pekerjaan

**Ditemukan:** 2026-06-15 oleh owner saat UAT. **Owner expectation:** perubahan referensi/mode pekerjaan di List Pekerjaan → volume dianggap **reset (belum diisi)**.

**Verifikasi:** **Perilaku yang diinginkan SUDAH menjadi desain backend** (bukan kontradiksi). `_reset_pekerjaan_related_data(pobj)` (`views_api.py:1256`) **menghapus `VolumePekerjaan`** + DetailAHSP + `PekerjaanTahapan` + formula state + `detail_ready=False`, lalu menandai `source_change_state["volume_reset_jobs"]` → `register_source_change_flags(... volume_reset_job_ids=...)` (`services.py:1026`, field `pending_volume_reset_job_ids`). Dipanggil via `_adopt_tmp_into` (`:1288`, ganti ke ref/ref_mod) dan jalur ganti ke custom (`:1495`). **Terpicu saat:** `source_type` berubah (ganti mode) ATAU `ref_id` berubah (REF→REF ref_id beda, `:1454-1464`).

**Gap (kenapa owner masih lihat volume lama):** reset TIDAK terpicu bila perubahan ref **tidak mengubah `ref_id`** (replace=False) — yaitu **UF-009** (resolusi ref by-kode tak stabil → ref_id sama → tak ada replace → volume tak di-reset). Alternatif: **display stale** halaman Volume belum refresh setelah perubahan (sekelas UF-007/008). Perlu repro singkat untuk memastikan jalur mana.

**Disposition:** **bukan keputusan desain baru** — reset-on-source-change sudah benar & diinginkan. Yang perlu: (a) pastikan trigger reset ikut menyala saat owner "ganti sumber" walau ref_id resolusinya bermasalah → **tergantung perbaikan UF-009**; (b) pastikan halaman Volume membaca `pending_volume_reset_job_ids` dan menampilkan job tsb sebagai "belum diisi" tanpa perlu reload manual. Owner **WP-P2** (List Pekerjaan/Volume), digabung dengan UF-009. Severity: Medium. Tidak memblok WP-B4.

### ENH-01 - Item Picker (typeahead) di Template AHSP untuk TK/BHN/ALT

**Diminta:** 2026-06-15 oleh owner saat UAT (input item custom merepotkan: harus ketik kode manual; item identik antar-pekerjaan tak mudah dipakai ulang). **Tipe: ENHANCEMENT (bukan bug).**

**Temuan kode:** 80% sudah ada di backend — (a) reuse antar-pekerjaan via kode: `_upsert_harga_item` upsert by `(project, kode_item)` (`services.py:1256`) → kode sama = `HargaItemProject` sama (harga konsisten); (b) auto-kode: `kode` kosong utk TK/BHN/ALT → `Unit-NNNN` (`_auto_unit_code`, `views_api.py:2206-2208`, `_UNIT_AUTO_KATEGORI` = TK/BHN/ALT); (c) daftar item: `api_list_harga_items` (id/kode_item/kategori/uraian/satuan/harga_satuan). **Gap = FRONTEND:** autocomplete hanya utk LAIN+custom (`template_ahsp.js:721 enhanceLAINAutocomplete`); item biasa tak punya picker.

**Keputusan owner (15 Jun):** sumber saran = **item proyek ini saja**; kode item baru = **manual dengan auto-fallback** (`Unit-NNNN`).

**Spec:**
- Frontend `template_ahsp.js`: generalisasi `enhanceLAINAutocomplete` utk baris TK/BHN/ALT. Field kode/uraian → typeahead **difilter kategori baris**, sumber `api_list_harga_items`; tampilkan `KODE — Uraian (satuan) · Rp harga`.
- Pilih item → isi `kode`+`uraian`+`satuan` (reuse `HargaItemProject` sama via kode); **kunci kategori** saat pick item lama (cegah konflik signal `_sync_guard_detail_kategori`).
- "Buat baru": kode **editable**; dikosongkan → auto `Unit-NNNN` (sudah didukung backend).
- Backend: cukup reuse `api_list_harga_items` (opsional: tambah `?q=&kategori=` server-filter bila daftar besar; v1 filter client-side).
- Test: frontend behavior (pick mengisi field + reuse kode, filter kategori, blank→auto). Backend auto-code+upsert sudah tercakup `tests_wp_b3`/import.

**Disposition:** owner **WP-P2 (Template AHSP)**. Severity: enhancement/UX (Medium value). Tidak memblokir UAT readiness.

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

---

### WP-B4 — Canonical Readiness & Missing-Value Schema (increment-1: SURVEI + KONTRAK)

**Status:** inc-1 SURVEI SELESAI (2026-06-15) — menunggu persetujuan kontrak owner sebelum inc-2 (implementasi service + contract test).
**Sumber:** A-8, A-9, B-4. **Dependency:** WP-B1 (DONE).

#### Survei keadaan saat ini (readiness/missing-value TERSEBAR + MAYORITAS SENYAP)

| Sinyal | Lokasi saat ini | Perilaku saat ini | Gap vs DoD |
|---|---|---|---|
| missing_volume | `compute_rekap_for_project` `services.py:2546` `vol_map.get(pkj_id) or 0` | volume tak ada **disamakan dengan 0** secara senyap | null≠zero tak dibedakan; tak ada penanda |
| missing_price | `services.py` agregasi `Coalesce(Sum(coef*price),0)` (harga `NULL`→0) | harga `NULL` (belum diisi) **berkontribusi 0** senyap | tak ada penanda item belum diisi |
| invalid_coefficient | divalidasi saat save (WP-B3 TA-01/gabungan, `koef<0`→400) | tak bisa tersimpan negatif lagi | runtime check defensif kosong (perlu sebagai jaring) |
| expanded_ready / expansion_not_ready | `_populate_expanded_from_raw` `services.py:1156-1191`; rekap baca `DetailAHSPExpanded` + fallback raw `:2496-2507` | fallback senyap ke raw; tak ada sinyal "ekspansi belum siap/stale" ke consumer | perlu sinyal eksplisit |
| incomplete_planned_allocation | jadwal `PekerjaanTahapan.proporsi_volume` (`models.py:950`); cek total `views_api_tahapan_v2.py:~601` | implisit di jadwal saja | perlu di schema lintas-page |
| missing_capacity / volume-exceeds-capacity | `views_api_tahapan_v2.py:345-364` (`type:'missing_capacity'`) | hanya validasi assign-time, bukan objek readiness terbaca | satu-satunya diagnostics terstruktur yg sudah ada |
| timeline_stale | JS `_estimateExpectedWeeklyColumns:116` (R2 audit Jadwal) | dihitung di client, memicu auto-regenerate | pindah deteksi ke server |

**Konsekuensi:** belum ada service diagnostics tunggal; `null` vs `0` tidak dibedakan (defek inti B-4); tiap consumer (rekap/rincian/RAB/jadwal/kebutuhan) menghitung hint sendiri; penyebab tak dapat ditelusuri lewat schema seragam.

**Fakta model yang mengunci desain null-vs-zero:**
- `VolumePekerjaan.quantity` **NOT NULL** (`models.py:305`, `MinValueValidator(0)`) → "missing volume" = **baris tidak ada** (pekerjaan tak ada di `vol_map`); zero eksplisit = baris dengan `quantity=0`. (Sesuai 2 contract test rekap yang ada: hapus baris = missing; set 0 = preserved.)
- `HargaItemProject.harga_satuan` **NULLABLE** (`models.py:329`) → null-vs-zero asli: `NULL`="belum diisi", `0.00`=gratis eksplisit (HI-01).
- `PekerjaanTahapan.proporsi_volume` (`models.py:950`) → basis `incomplete_planned_allocation` (Σ per-pekerjaan ≠ 100).

#### Kontrak yang DIUSULKAN (sketsa awal inc-1 — **DI-SUPERSEDE oleh inc-2.1 → `b4.2`**, lihat bagian inc-2.1 di bawah)

Service tunggal `compute_project_readiness(project)` (modul baru `detail_project/readiness.py`), di-cache dengan `build_project_cache_signature` (WP-B2). Output:

```text
{
  expanded_ready: bool,                       # semua pekerjaan ber-detail-raw punya baris expanded
  missing_volume:  [pekerjaan_id, ...],       # tak ada baris VolumePekerjaan (≠ quantity 0)
  missing_price:   [{harga_item_id, kode, affected_pekerjaan:[...]}, ...],  # harga_satuan IS NULL
  invalid_coefficient: [{pekerjaan_id, kode}, ...],  # defensif; harusnya kosong pasca WP-B3
  expansion_not_ready: [pekerjaan_id, ...],   # punya detail raw tapi expanded hilang/stale
  incomplete_planned_allocation: [{pekerjaan_id, total_proporsi}, ...],  # Σ proporsi ≠ 100
  timeline_stale: bool,                        # kolom mingguan ≠ rentang waktu project (deteksi server)
  affected_pekerjaan: [...],                   # union indeks utk UI
  affected_items: [...],
}
```

Prinsip (selaras DoD + B-1):
- consumer **hanya menyajikan** readiness, tidak menghitung ulang;
- warning **tidak memblokir** save/compute kecuali operasi memang tak bisa dihitung;
- `null` vs `0` dibedakan tegas (volume: baris-ada; harga: NULL);
- setiap warning menyebut pekerjaan/item penyebab agar dapat ditelusuri.

**Rencana increment:** inc-2 = implement `compute_project_readiness` + contract test (null-vs-zero volume & harga, incomplete allocation, expansion_not_ready); inc-3 = wiring 5 consumer (rekap/rincian/RAB/jadwal/kebutuhan) baca schema sama (display-only) + buang recompute client; inc-4 = pindahkan deteksi `timeline_stale` ke server (audit Jadwal R2) + tutup auto-regenerate page-open.

#### inc-2 — Service + contract test (DONE 2026-06-15)

Modul baru **`detail_project/readiness.py`** → `compute_project_readiness(project)` (cached via `build_project_cache_signature` + `CALCULATION_CACHE_DOMAINS`, schema_version `b4.1`). Sinyal calc-path LIVE: `missing_volume` (baris VolumePekerjaan absen ≠ qty 0), `missing_price` (harga_satuan `NULL`, sumber detail mirror rekap: expanded ∪ raw-fallback), `invalid_coefficient` (defensif `<0`), `expansion_not_ready`/`expanded_ready` (raw tanpa expanded; non-blocking krn rekap fallback ke raw), plus `affected_pekerjaan`/`affected_items`. **ISOLATED — belum diwire ke consumer manapun (zero perubahan perilaku endpoint).** Sinyal jadwal (`incomplete_planned_allocation`, `timeline_stale`) sengaja `[]`/`False` + dideklarasikan di `pending_signals` (consumer tak boleh anggap "all clear") → inc-4. Alasan defer: keduanya bergantung weekly-canonical `PekerjaanProgressWeekly` (`PekerjaanTahapan` = derived view) + logika kolom timeline jadwal.

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-15 | WP-B4 inc-2 | `tests_wp_b4_readiness` (`ReadinessContractTests`) | PASS | 10/10 (kontrak b4.1, di-supersede inc-2.1) |

#### inc-2.1 — Contract hardening (4 koreksi owner) — DONE 2026-06-15 → schema `b4.2`

Empat koreksi owner sebelum kontrak publik dikunci:
1. **HIGH expansion D-06:** analisis kini **per-`source_detail`** (bukan per-pekerjaan). Raw row tanpa expanded component → `missing_expansion`; raw lebih baru dari expansion-nya → `stale_expansion`; sertakan `expected`/`actual` count (direct=1, bundle=None). Menangkap kasus berbahaya: pekerjaan **expanded sebagian** masuk `expanded_job_ids` → rekap baca expanded saja & **diam-diam drop raw tak-terekspansi** (undercount).
2. **MEDIUM pending = `null`:** `incomplete_planned_allocation`/`allocation_without_volume`/`timeline_stale` → `None` (bukan `[]`/`false`) sampai inc-4 authoritative; `pending_signals` dipertahankan.
3. **MEDIUM traceability:** tiap entry diagnostic = `{pekerjaan_id, kode, uraian, source_table, source_page, issue, (actual/expected/affected_pekerjaan)}`. Count TIDAK disimpan (turunan array). `affected_pekerjaan` = index ringan; `affected_items` dihapus (redundan — detail penuh ada di entry `missing_price`).
4. **MEDIUM cache stale:** tambah `_readiness_digest` (Count+Sum+problem-count atas volume/harga/koef raw+expanded) di-fold ke signature → `QuerySet.update()`/`bulk_update()` value-only (tak bump `updated_at`) tetap meng-invalidasi cache. Contract test cache-invalidation ditambahkan.

**Schema addition:** `allocation_without_volume` (planned proportion > 0 saat volume absen/0) dipisah dari `incomplete_planned_allocation` (total rencana < 100%). Keduanya jadwal-derived → pending (inc-4).

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-15 | WP-B4 inc-2.1 | `tests_wp_b4_readiness` | PASS | 15/15: + partial-expansion (D-06), stale-expansion, expected/actual, traceable entry (kode/uraian/source_table/source_page), pending=None, 2× cache-invalidation (bulk_update koef negatif & harga terisi). `manage.py check` 0 issue |

**Kontrak FINAL `b4.2`** (live di `readiness.py`, lulus 15 test) — entry diagnostic uniform; `expanded_ready` kini sahih utk partial/stale; pending = `None` + `pending_signals`; cache tahan bulk-update.

**Gate inc-3 (perlu persetujuan owner):** wiring bertahap **satu-per-satu** sesuai urutan owner — pilot **Rekap RAB** (silent-zero paling mudah diverifikasi), lalu Rincian AHSP → Template AHSP → Jadwal → Rekap Kebutuhan. JANGAN wire kelima sekaligus. Mohon review `b4.2` sebelum mulai pilot Rekap RAB. → **DISETUJUI owner 2026-06-15.**

#### inc-3 PILOT — Rekap RAB (DONE 2026-06-15)

Wiring display-only pertama (pilot), pola untuk consumer berikutnya:
- **Backend** `api_get_rekap_rab` (`views_api.py:~4620`): tambah `"readiness": compute_project_readiness(project)` ke respons JSON (import `from .readiness import compute_project_readiness`). Tidak mengubah `rows`/`meta`/perhitungan — murni metadata tambahan.
- **Frontend** `rekap_rab.js`: `renderReadiness(rRes.data.readiness)` dipanggil di `loadData()` setelah `render('')`. Banner advisory non-blocking (`#rab-readiness`, `alert-warning`) di atas tabel: hitung+kode `missing_price`/`missing_volume`/`expansion_not_ready`/`invalid_coefficient` (semua via `escapeHtml`, selaras RR-01). **Page TIDAK menghitung ulang readiness** — hanya menampilkan apa yang server laporkan. Sinyal jadwal (pending) tidak ditampilkan (hindari noise; bukan "all clear").

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-15 | WP-B4 inc-3 pilot | `tests_wp_b4_readiness` (+`RekapRabReadinessWiringTests`) + `tests_rekap_calculation_contract` | PASS | 33/33: respons rekap memuat `readiness` b4.2; refleksi missing_price/missing_volume; timeline_stale tetap `None`. Rekap contract 15/15 tanpa regresi. `node --check` rekap_rab.js OK. `manage.py check` 0 issue |

**Gate consumer berikutnya (Rincian AHSP):** pola pilot di atas siap direplikasi. Mohon review tampilan banner Rekap RAB (visual UAT) sebelum lanjut Rincian → Template → Jadwal → Kebutuhan. → **Visual UAT PASS 2026-06-15** (owner: banner warning tampil di Rekap RAB; `missing_price` terverifikasi setelah fix UF-011, `missing_volume` terbukti project 163/pekerjaan 938).

#### inc-3 FAN-OUT #1 — Rincian AHSP (DONE 2026-06-15)

Consumer ke-2. **Murni frontend** — halaman Rincian AHSP sudah memuat `api_get_rekap_rab` via `data-ep-rekap` (`loadRekap()` `rincian_ahsp.js:485`), jadi `readiness` sudah ada di response; tak perlu perubahan backend.
- `rincian_ahsp.js`: tambah `renderReadiness(j.readiness)` di `loadRekap()`; banner `#ra-readiness` disisipkan setelah `#ra-toolbar`, dibangun modul `ReadinessBanner` bersama (display-only).
- Template `rincian_ahsp.html`: muat `shared/readiness_banner.js` (classic, sebelum `rincian_ahsp.js`).
- Guard wiring ditambah di `readiness_banner.test.js` (`readiness consumer wiring`): tiap consumer (rekap_rab.js, rincian_ahsp.js) wajib pakai `ReadinessBanner` + `renderReadiness(` + baca field readiness server.

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-15 | WP-B4 inc-3 fan-out#1 | `vitest run` | PASS | 255 pass (+2 wiring guard) / 25 skip; `node --check` rincian_ahsp.js OK |

**Berikutnya:** fan-out #2 **Template AHSP** (catatan: Template punya alur data berbeda — perlu cek endpoint/anchor sendiri), lalu Jadwal, Rekap Kebutuhan.

#### inc-3 FAN-OUT #2 — Template AHSP + endpoint readiness khusus (DONE 2026-06-15)

Template AHSP = editor per-pekerjaan, **tidak** memuat `/rekap/`. Solusi reusable: **endpoint readiness khusus** `GET api/project/<id>/readiness/` (`api_get_readiness`, `views_api.py`) → `{ok, readiness}` via `compute_project_readiness(project, request=request)`. Dipakai consumer yang tak load `/rekap/` (Template, dan nanti Jadwal/Kebutuhan); Rekap RAB & Rincian tetap baca inline dari `/rekap/`.
- `template_ahsp.js`: `endpoints.readiness` (`data-endpoint-readiness`); `renderReadiness()` (banner `#ta-readiness` setelah `#ta-toolbar`, modul `ReadinessBanner`); `refreshReadiness()` dipanggil saat boot + setelah save sukses (detail berubah → readiness berubah).
- Template `template_ahsp.html`: `data-endpoint-readiness` + muat `shared/readiness_banner.js` (defer, sebelum `template_ahsp.js`).
- Guard wiring `readiness_banner.test.js` diperluas → kini mengunci rekap_rab.js + rincian_ahsp.js + template_ahsp.js. Backend test `test_dedicated_readiness_endpoint` (200, `b4.3`, refleksi missing_price).

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-15 | WP-B4 inc-3 fan-out#2 | `tests_wp_b4_readiness` + `vitest run` + `manage.py check` | PASS | backend 24/24 (+endpoint khusus); frontend 256 pass (+1 guard) / 25 skip; `node --check` template_ahsp.js OK; check bersih |

**Berikutnya:** fan-out #3 **Jadwal** lalu #4 **Rekap Kebutuhan** (keduanya bisa pakai endpoint `/readiness/` khusus), lalu inc-4 (sinyal jadwal aktual).

#### inc-3 FAN-OUT #3 (Jadwal) + #4 (Rekap Kebutuhan) — DONE 2026-06-15

Jadwal = `kelola_tahapan_grid_modern.html` (bundle Vite — JANGAN sentuh build); Kebutuhan = `rekap_kebutuhan.html` (JS sendiri). Solusi **bundle-agnostic**: modul autoload baru **`shared/readiness_autoload.js`** — membaca `data-readiness-endpoint` pada elemen anchor, fetch endpoint `/readiness/` khusus, render banner via `ReadinessBanner` (self-init `DOMContentLoaded`; expose `window.ReadinessAutoload.render/init`). Tidak menyentuh bundle/JS halaman.
- Jadwal: anchor `#kt-readiness` (setelah toolbar) + muat `readiness_banner.js`+`readiness_autoload.js` (defer).
- Kebutuhan: anchor `#rk-readiness` (atas konten) + muat kedua script (defer, sebelum rekap_kebutuhan.js).
- Test: `readiness_autoload.test.js` (5, happy-dom + mocked fetch): isi banner saat ada masalah, kosong+hidden saat bersih, escaping XSS end-to-end, no-op tanpa endpoint, fetch-fail tak throw.
- Hardening review: endpoint khusus dikunci dengan test login + isolasi owner (non-owner = 404); guard template memastikan Jadwal/Kebutuhan benar-benar mendeklarasikan endpoint dan memuat builder sebelum autoload; Template AHSP refresh readiness setelah reset-to-reference selain boot/save.

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-15 | WP-B4 inc-3 fan-out#3+#4 | `tests_wp_b4_readiness` + `tests_rekap_calculation_contract` + `vitest run` | PASS | 26/26 readiness backend; 42/42 readiness+rekap; 264 frontend / 25 skip. Tambahan hardening: endpoint login+owner scope, wiring template Jadwal/Kebutuhan, dan refresh readiness setelah reset Template. `node --check` + Django check bersih |

**inc-3 SELESAI — kelima consumer wired:** Rekap RAB + Rincian (inline `/rekap/`), Template + Jadwal + Kebutuhan (endpoint `/readiness/` khusus; Jadwal/Kebutuhan via autoload). **Berikutnya: inc-4** — sinyal jadwal aktual (`incomplete_planned_allocation`/`allocation_without_volume`/`timeline_stale`) + stale-revision, lalu WP-B4 DONE.

#### inc-4 — DESAIN (sinyal jadwal + stale-expansion signature) — menunggu persetujuan owner

**Sumber data tervalidasi:** `PekerjaanProgressWeekly` (canonical; `planned_proportion` per `(pekerjaan, week_number)`, + `week_start_date/end_date`); validasi assign-time `views_api_tahapan_v2.py:332-366` sudah hitung `total_percent` + `missing_capacity`; `Project.tanggal_mulai/selesai`.

**Kontrak 3 sinyal jadwal (mengisi yang sebelumnya `null`/pending):**

1. `incomplete_planned_allocation` — pekerjaan **terjadwal sebagian**: `0 < Σ planned_proportion < 100` (toleransi 0.01). **Σ=0 (belum dijadwalkan) DIKECUALIKAN** agar proyek baru tak diflag massal. Entry: `{pekerjaan_id, kode, uraian, source_table:"PekerjaanProgressWeekly", source_page:"jadwal", issue:"incomplete_planned_allocation", actual: "<Σ%>"}`.
2. `allocation_without_volume` — `Σ planned_proportion > 0` TAPI volume absen ATAU 0 (= cek `missing_capacity` existing). Lebih berat dari `missing_volume` (kerja dijadwalkan tanpa kapasitas). Entry: `{pekerjaan_id, kode, uraian, source_table:"PekerjaanProgressWeekly"+"VolumePekerjaan", source_page:"jadwal", issue, actual:"<Σ%>"}`.
3. `timeline_stale` (bool project-level) — jadwal dibangun di atas rentang tanggal lama. **Definisi (diusulkan):** ada `PekerjaanProgressWeekly` dengan `week_start_date < project.tanggal_mulai` ATAU `week_end_date > project.tanggal_selesai`. (Sekunder opsional: `max(week_number) ≠ expected_weeks` dari tanggal.) Jika project tanpa tanggal atau tanpa weekly data → `false` (tak dapat dinilai). **Memindahkan deteksi dari client `_estimateExpectedWeeklyColumns` ke server (audit Jadwal R2).**

`pending_signals` dikosongkan setelah ketiganya live; nilai `null` → list aktual.

**Mekanisme stale-expansion (ganti heuristik `updated_at` yang bisa di-bypass `QuerySet.update`):**
- **Usulan = CONTENT SIGNATURE (bukan revision-counter).** Alasan: counter di-bump saat write punya kelemahan yang SAMA dengan `updated_at` (bulk_update melewatinya). Signature dihitung **dari nilai aktual saat read** → bypass-proof.
- Tambah field `source_signature` (CharField, nullable) di `DetailAHSPExpanded` = hash pendek dari source raw row saat ekspansi: `sha1(f"{kategori}|{kode}|{koefisien}|{ref_pekerjaan_id}|{ref_ahsp_id}")`. Ditulis di setiap create `DetailAHSPExpanded` dalam rutin ekspansi (`_populate_expanded_from_raw` + builder bundle).
- **Readiness:** untuk tiap raw row, hitung signature CURRENT, bandingkan dgn `source_signature` tersimpan di expanded rows-nya → beda = `stale_expansion`. Menggantikan perbandingan `updated_at`.
- **Migrasi:** add field nullable + data-migration backfill (hitung dari source saat ini; konsisten ketika deploy). Pasca-backfill tak ada NULL → readiness pakai signature murni. (NULL → fallback aman: tak diflag, tunggu re-ekspansi berikut.)

**Keputusan owner (DIPUTUSKAN 2026-06-15):** (a) `timeline_stale` = **hanya minggu di luar jendela** [tanggal_mulai, tanggal_selesai]; (b) stale-expansion = **content signature** (bukan revision-counter, karena counter punya kelemahan bypass yang sama dgn updated_at); (c) `incomplete_planned_allocation` **mengecualikan Σ=0**.

**Rencana increment inc-4:** inc-4a = 3 sinyal jadwal (read-only, tanpa migrasi) + contract test; inc-4b = field `source_signature` + migrasi/backfill + ganti deteksi stale + test bypass `QuerySet.update`.

#### inc-4a — Sinyal jadwal LIVE (DONE 2026-06-15) → schema `b4.4`

`readiness.py` kini menghitung 3 sinyal dari `PekerjaanProgressWeekly` (Σ `planned_proportion` per pekerjaan) + `VolumePekerjaan.quantity` + `Project.tanggal_*`:
- `incomplete_planned_allocation`: `0 < Σ < 100` (toleransi 0.01); Σ=0 dikecualikan.
- `allocation_without_volume`: `Σ > 0` & volume absen/0.
- `timeline_stale` (bool): ada weekly row dgn `week_start_date < mulai` ATAU `week_end_date > selesai`; project tanpa tanggal/weekly → `false`.
`PENDING_SIGNALS` kini `()` kosong; `pending_signals` di output = `[]`. Banner (`readiness_banner.js`) menampilkan ketiganya (3 baris baru). Entry jadwal masuk `affected_pekerjaan`.

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-15 | WP-B4 inc-4a | `tests_wp_b4_readiness` + lintas-consumer + `vitest run` | PASS | backend 76/76 (readiness 32; rekap 15; wp_b3 29); frontend 265 (+1 banner jadwal); `manage.py check` bersih. Review hardening: sumber `allocation_without_volume` mencatat weekly+volume; tolerance 99.99% dan minggu sebelum tanggal mulai dikunci contract test. |

**Berikutnya: inc-4b** — field `source_signature` (`DetailAHSPExpanded`) + migrasi/backfill + populate di semua write ekspansi + ganti deteksi `stale_expansion` (dari `updated_at` → signature, bypass-proof) + test bypass `QuerySet.update`. Perlu migrasi DB.

#### inc-4b — Stale-expansion content signature (DONE 2026-06-15) — WP-B4 SELESAI

- **Model:** field `source_signature` (`CharField(40)`, nullable) di `DetailAHSPExpanded`. Migrasi `0046` (add field) + `0047` (data-migration backfill dari source_detail, logic frozen inline).
- **Helper:** `readiness.source_signature(...)` = sha1; koefisien dikuantisasi 12dp agar konsisten write-vs-read. Signature mencakup identitas `harga_item` agar perubahan FK langsung juga terdeteksi.
- **Populate:** di-stamp pada SEMUA titik tulis ekspansi (loop sebelum `bulk_create` di `services.py` `_populate_expanded_from_raw` + `views_api.py` save-detail) via lazy import (tanpa circular).
- **Deteksi:** signature CURRENT dibandingkan dengan signature tersimpan → **bypass-proof** thd `QuerySet.update()`/`bulk_update()`. Kelompok signature campuran/parsial juga dianggap stale. Fallback `updated_at` hanya bila seluruh signature grup legacy NULL.
- **Review correction:** `0047` yang sudah sempat diterapkan Docker dapat menandai raw-lama/expanded-lama sebagai fresh saat backfill. Migrasi korektif `0048` mempertahankan grup yang terbukti stale dari timestamp sebagai NULL (agar fallback tetap bekerja), serta meng-upgrade grup fresh ke format signature dengan `harga_item_id`.
- **Batas ownership:** signature B4 mendeteksi perubahan pada raw `DetailAHSPProject` itu sendiri. Perubahan isi master AHSP atau pekerjaan yang direferensikan tanpa perubahan raw parent tetap menjadi ownership **WP-B7 CUSTOM live-reference/cascade**, bukan diklaim selesai oleh B4.
- **Test:** `test_stale_expansion_detected_via_signature_bypassing_updated_at` (update koef via QuerySet.update tanpa re-ekspansi → terdeteksi; metode `updated_at` lama miss) + `test_fresh_expansion_signature_matches_not_stale`; helper `_detail` stamp signature seperti produksi.

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-15 | WP-B4 inc-4b | `tests_wp_b4_readiness` + lintas-ekspansi + `makemigrations --check` | PASS | 85/85 (readiness 36; rekap 15; wp_b3 29; item_ssot 5); migrasi 0046–0048 bersih; `manage.py check` 0 issue; frontend 265 pass / 25 skip |
| 2026-06-15 | WP-B4 inc-4b Docker | backup + `migrate --plan` + container check + HTTP smoke | PASS | DB Docker sudah di `0048`; 752 expanded row, 0 signature NULL, 0 grup signature campuran; `/` HTTP 200. Backup: `backups/wp_b4_0048_20260615_165016.dump` |

**WP-B4 SELESAI.** Schema `b4.4` lengkap: missing_volume/price (null≠zero), expansion (missing/stale/incomplete/excess, signature bypass-proof), invalid_coefficient, 3 sinyal jadwal, affected index; 5/5 consumer wired (display-only); endpoint `/readiness/` + autoload.

**Konsistensi signature (2026-06-15):** owner memperkuat `source_signature` menambah `harga_item_id` (relation-move harga ikut terdeteksi stale). Dirapikan agar **6 field konsisten di SEMUA call-site**: helper, `_compute` recompute, kedua populate (services+views), test helper, **dan migrasi backfill `0047`** (semula 5 field → diperbaiki; kalau tidak, semua baris pre-deploy ter-flag stale palsu). `makemigrations --check` bersih, readiness suite hijau.

**Berikutnya WP: A2 (CSP) — dimulai.**

---

### WP-A2 — CSP Report-Only + Dependency Governance (report-only DONE 2026-06-15)

**Sumber:** A-4, VP-08, TA-11, RR-15. Master plan: report-only dulu, enforcement = milestone terpisah.

**Keputusan owner (didelegasikan, rekomendasi Claude diadopsi):** (1) mekanisme = **middleware custom** (tanpa dependency; django-csp dipertimbangkan saat enforcement utk nonce); (2) arah CDN jangka panjang = **self-host** (CSP paling bersih, cocok on-prem) — diterapkan di fase enforcement.

**Inventaris (survei):**
- CSP: TIDAK ADA sebelumnya (production hanya `SECURE_*`/HSTS).
- CDN tanpa SRI: `base.html` (Bootstrap), List Pekerjaan/Volume/Template/Rekap RAB/Jadwal (jQuery `code.jquery.com`, Select2/html2canvas/Bootstrap `cdn.jsdelivr.net`, SheetJS `cdn.sheetjs.com`).
- Inline `<script>`: ~6 template (harga_items, kelola_tahapan ×2, rekap_rab, rincian_rab, _alert) + `<script>` inline lain di base.html; inline `style=""` pervasif.

**Diimplementasikan (report-only, non-breaking):**
- `config/middleware/csp.py` → `ContentSecurityPolicyMiddleware` (header dari `settings.CSP_POLICY`; nama header `Content-Security-Policy-Report-Only` saat `CSP_REPORT_ONLY=True`, jadi `Content-Security-Policy` saat flag off) + `csp_report` (sink, csrf-exempt, log `csp` logger, 204; 405 utk GET).
- `settings/base.py`: `CSP_REPORT_ONLY` (env `DJANGO_CSP_REPORT_ONLY`, default True), `CSP_POLICY` (default-src 'self'; **script-src TANPA 'unsafe-inline'** agar inline script ke-report; style-src 'self' 'unsafe-inline' — pengecualian terdokumentasi; img/font/connect/object-src/base-uri/frame-ancestors), `CSP_REPORT_PATH=/csp-report/`. Middleware dipasang setelah `SecurityMiddleware` (production reslice tetap menjaganya).
- `config/urls.py`: route `/csp-report/`.
- Test `detail_project/tests_csp.py` (11): header report-only default, script-src tanpa unsafe-inline (style-src dgn), header enforcing saat flag off, tak menimpa header eksisting, sink 204/malformed/non-object/Reporting-API-array/oversized-drop/GET-405/route+csrf-exempt. Sink membatasi body 64 KiB dan menyaring nilai log.

**Dependency governance:** dependency frontend baru WAJIB self-host atau SRI; tak boleh menambah domain ke `script-src` tanpa persetujuan. (DoD: "tidak ada dependency baru tanpa integrity/self-host policy".)

**Roadmap enforcement (milestone terpisah — acceptance criteria tercatat, DoD):**
1. Kumpulkan laporan violation (report-only aktif di env target) → inventaris inline script aktual.
2. Pindahkan/nonce semua inline `<script>` (atau django-csp utk nonce).
3. Self-host jQuery/Select2/SheetJS/html2canvas/Bootstrap → `script-src 'self'` (atau SRI bila self-host tertunda).
4. Acceptance: workflow utama 0 violation (atau exception disetujui) → flip `DJANGO_CSP_REPORT_ONLY=False`.

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-15 | WP-A2 report-only | `tests_csp` + `manage.py check` | PASS | 11/11; header report-only + sink hardened; non-breaking |

**WP-A2 (report-only) SELESAI** — DoD report-only terpenuhi (report-only aktif, sink/laporan tersedia, dependency-governance + acceptance enforcement tercatat). **Enforcement = milestone terpisah (deferred).**

---

### WP-B5 — Server-Authoritative Export Framework (SURVEI 2026-06-15)

**Status:** IN PROGRESS (survei + rencana increment; mulai B5a). **Sumber:** A-3, B-2, B-5. **Dependency:** WP-B1/B2/B4 (semua DONE).

**Survei lanskap export (≈20 file `detail_project/exports/` + 2 sistem):**
- **Calc reuse (DoD#1):** adapter (`rekap_rab_adapter`, `rincian_ahsp_adapter`, `rekap_kebutuhan*`, `jadwal_pekerjaan_adapter`, `export_manager`) sudah mereferensikan `compute_rekap_for_project` (kanonik WP-B1). Perlu verifikasi tak ada calc duplikat tersisa (kelas RA-03).
- **`str(e)` leak (DoD#2):** banyak di `views_export.py` (180/300/404/413/482/544/622) + **`word_exporter.py:1211` membocorkan teks exception KE DALAM dokumen** (`[{title} - Error embedding image: {str(e)}]`). Belum ada wrapper error + correlation ID.
- **Project identity (B-5):** terpencar — `base.py` pakai `project.nama` langsung (`:145/170/205/249/428`); `excel_exporter` pakai dict `project_info` (`nama_client`/`sumber_dana` fallback, `:1314+/2296+/2680+`); `export_manager` punya konsep identity sendiri (`:48`). BELUM ada satu provider. (Terkait RR-04 identitas hardcoded di print JS — sisi berbeda.)
- **Filename:** `base.py:205` `{base}_{project.nama}_{timestamp}` — dekat tapi belum seragam `NamaProject_TanggalExport.ext`.
- **JSON (B-2):** JSON MASIH ditawarkan sbg format report (`export_manager` `format_type='json'` → `JSONExporter`, `:32/1067-1071`). B-2 mengunci JSON = paket data terpisah (project_backup/work_structure_template/diagnostic_snapshot), bukan format report.
- **Dua sistem export:** (a) server adapter + `ExportManager`; (b) client-render image upload (`views_export.py` `export_init`/`export_upload_pages`/`export_finalize`). B-5 "server-authoritative" mengarah menjauh dari client-render (perlu keputusan saat B5e).

**Rencana increment (disetujui untuk eksekusi bertahap):**
| Inc | Fokus | DoD |
|---|---|---|
| **B5a** | Wrapper error export + correlation ID; hapus semua `str(e)` leak (termasuk `word_exporter:1211` yg masuk dokumen) | #2 |
| **B5b** | Satu `get_project_identity(project)` provider (dari Dashboard) dipakai semua exporter | B-5 identity |
| **B5c** | Konvensi filename `NamaProject_TanggalExport.ext` seragam | filename |
| **B5d** | Pisahkan JSON dari menu report (B-2): JSON=paket data via endpoint terpisah + schema_version + import atomik | #5,#6 |
| **B5e** | Signature config per report + aturan PDF signature tak berdiri sendiri + dataset snapshot + threshold sync/bg + empty-export "." ; keputusan client-render vs server-authoritative | #3,#4 |

**Catatan:** B5d & B5e perlu keputusan desain (struktur endpoint JSON; aturan signature; nasib jalur client-render) — kontrak diajukan saat tiba di increment tsb. Mulai eksekusi: **B5a**.

#### inc-B5a — Error wrapper + correlation ID (DONE 2026-06-15)

- Modul baru `detail_project/exports/errors.py`: `new_correlation_id()` (12-hex), `log_export_error(exc, context, ...)` (log penuh + cid, return cid), `export_error_response(exc, ...)` (JsonResponse aman: `{ok:False, error: generik, correlation_id}`, TANPA `str(e)`).
- **Leak nyata diperbaiki:** (1) `word_exporter.py` tak lagi menaruh teks exception di DOKUMEN → placeholder dengan correlation ID; (2) `export_finalize` tak lagi membalas `str(e)`; (3) status Celery `FAILURE` tidak lagi mengirim `task.info` mentah; (4) endpoint init/upload/finalize/status/async memakai pesan generik + correlation ID.
- Handler generik lain (`export_init`/`export_upload_pages`/`export_finalize` outer) kini sertakan `correlation_id` (str(e) hanya di log, bukan respons).
- Test `detail_project/tests_export_errors.py` (6): cid hex-12, response tak bocor exception, status/message kustom, leak-guard word_exporter + finalize.

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-15 | WP-B5 inc-B5a | `tests_export_errors` + regresi export | PASS | 12/12 (export_errors 6 + export_csrf + harga_items_export); `manage.py check` bersih |

**Berikutnya: B5b** (satu `get_project_identity(project)` provider dari Dashboard, dipakai semua exporter).

#### inc-B5b — Satu provider project identity (DONE 2026-06-15)

- Modul baru `detail_project/exports/identity.py`: `get_project_identity(project)` membaca **field Dashboard yang BENAR** (name=`nama`, location=`lokasi_project`, year=`tahun_project`, owner/client=`nama_client`, `sumber_dana`, `anggaran_owner`, kontraktor/konsultan). Default `'-'` hanya jika atribut benar-benar absen.
- **Bug nyata diperbaiki:** `export_manager._get_project_identity` membaca nama field TAK ADA (`lokasi`, `tahun_anggaran`) → location & year SELALU `'-'` di export. Kini delegasi ke provider → nilai benar. (kelas RR-04 identitas salah.)
- `jadwal_pekerjaan_adapter._get_project_info` juga di-route ke provider untuk seluruh field identitas dan signature yang memang tersedia pada model Dashboard (`jabatan_client`, `instansi_*`, nama para pihak).
- Test `detail_project/tests_export_identity.py` (5): provider baca field riil, year dari `tahun_project`, fallback absen→'-', + guard delegasi (export_manager & jadwal adapter pakai provider, tak baca field salah).

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-15 | WP-B5 inc-B5b | `tests_export_identity` + regresi export/adapter | PASS | 33/33 (identity 5 + errors 6 + export_csrf + harga_items_export + rekap_contract 15); `manage.py check` bersih |

**Catatan:** model `Project` mengisi field wajib kosong dgn default saat save (jadi jarang `'-'` di praktik). Review lanjutan memastikan provider tidak menghilangkan `index_project`, `ket_project1/2`, `jabatan_client`, atau `instansi_*`. **Berikutnya: B5c** (konvensi filename `NamaProject_TanggalExport.ext`).

#### inc-B5c — Konvensi filename seragam (DONE 2026-06-15)

- Modul baru `detail_project/exports/naming.py`: `build_export_filename(project_name, doc_label, ext, when)` → keputusan terkunci **`NamaProject_YYYY-MM-DD.ext`**; `doc_label` dipertahankan hanya untuk kompatibilitas call-site dan sengaja tidak masuk filename. `sanitize_for_filename` mencegah karakter header/path berbahaya.
- Diterapkan ke seluruh download report aktif: generic CSV/XLSX/PDF/Word, Volume, Rincian AHSP, Jadwal weekly/monthly/rekap, Rekap RAB/Kebutuhan, serta endpoint download session/async. Filename UUID internal tetap internal; JSON dikecualikan karena ownership B5d.
- Test `detail_project/tests_export_naming.py` mengunci format name+date-only, label tidak memengaruhi filename, sanitasi, dan wiring semua keluarga exporter/download.

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-15 | WP-B5 inc-B5c | `tests_export_naming` + regresi export | PASS | Review gate gabungan A2+B5a-c 77/77; frontend 265 pass/25 skip; `manage.py check` dan migration check bersih |
| 2026-06-15 | WP-A2/B5 Docker smoke | restart web + HTTP/header/sink + container check | PASS | web/db healthy; login HTTP 200 memuat CSP Report-Only dan tanpa enforcing header; `/csp-report/` HTTP 204; `migrate --plan` kosong |

**Baseline:** `tests_export_button_visibility` tetap 3 failure HTTP 302 = **KF-02 known-failing**, identik dengan baseline WP-00 dan bukan regresi A2/B5.

#### inc-B5d — Pisah JSON dari report (B-2) — SURVEI 2026-06-15 (menunggu keputusan owner)

**Survei JSON landscape:**
- Frontend `export-coordinator.js:36` menampilkan **`JSON: 'json'` sebagai FORMAT report** (sejajar PDF/XLSX/Word/CSV) → B-2 minta dihapus dari menu report.
- `export_manager` punya cabang `format_type == 'json'` (`:1040`) → `JSONExporter.export_jadwal_pekerjaan` (data jadwal utk import/export).
- **Sudah ADA** (kerja opaque-ID, terpisah dari menu report): `project_backup` v3.0 (`views_api.py:8549` export + `:8624` import), template import/export (`api_import_template`/`api_import_template_from_file` `:9661/9724`) = 2 dari 3 tipe B-2.
- **`diagnostic_snapshot` TIDAK ADA** (hanya di doc planning).
- Entanglement: infra JSON package = bagian aktif **opaque-ID import/export** (export_version 1.0/1.1/3.0) — sentuhan hati-hati.

**Usulan kontrak B5d (perlu keputusan owner):**
1. Hapus JSON dari menu FORMAT report (frontend `export-coordinator.js` + cabang `format_type=='json'` `export_manager`) → report = PDF/XLSX/Word/CSV.
2. Data jadwal JSON (`JSONExporter.export_jadwal_pekerjaan`): jadikan aksi "paket data" terpisah / fold ke `project_backup` / pensiun — **keputusan owner**.
3. `project_backup`+`work_structure_template`: pastikan `schema_version`+import atomik (verifikasi).
4. `diagnostic_snapshot`: **bangun sekarang atau defer?** — keputusan owner.

**Keputusan owner (2026-06-15):** (1) hapus JSON dari menu FORMAT report — DISETUJUI; (2) data Jadwal menjadi bagian `project_backup` dengan `include_progress`, bukan report JSON tersendiri; dedicated schedule-only package belum diperlukan; (3) `diagnostic_snapshot` → **DEFER** ke milestone terpisah.

**Rencana eksekusi B5d (final, menunggu Docker up):**
1. Frontend: keluarkan JSON dari seluruh menu laporan Jadwal, Volume, Harga Items, Rekap RAB, dan Rekap Kebutuhan. JSON parameter Volume dan paket transfer List/Template tetap dipertahankan karena bukan laporan.
2. Backend: cabang `export_manager format_type=='json'` dihapus dari dispatcher report; data package tetap melalui endpoint data yang terpisah.
3. Verifikasi `project_backup`+`work_structure_template` punya `schema_version`+import atomik (cek `views_api.py:8549/8624`, `:9661/9724`).
4. Test: backend (export_manager dispatch tanpa json report; data-jadwal action) — **butuh DB up**; frontend (vitest) report-menu tanpa JSON.

**inc-B5d DONE 2026-06-15** (Docker up, semua hijau):
- **Temuan kunci:** radio JSON di modal export Jadwal ternyata **DEAD** — tak ada `json-generator` (generators hanya csv/excel/pdf/word), tak ada URL `export_jadwal_pekerjaan_json`, coordinator switch pakai reportType bukan format. Jadi "JSON sebagai format report" memang tak berfungsi. Menghapusnya tak menghilangkan fitur (data project penuh termasuk jadwal ada di `project_backup`).
- **Dihapus:** radio/binding/route JSON laporan dari Jadwal, Volume, Harga Items, Rekap RAB, dan Rekap Kebutuhan; `JSONExporter` dikeluarkan dari `ExportManager.EXPORTER_MAP` dan cabang dispatch report dihapus.
- **DoD #6 terverifikasi & dikunci:** `project_backup` + `work_structure_template` memiliki `export_type`/`export_version` (v3.0), dan seluruh import terkait memakai `@transaction.atomic`.
- **Keputusan owner diterapkan:** JSON keluar dari seluruh menu/endpoint report ✓; data Jadwal tersedia via `project_backup(include_progress)` ✓; `diagnostic_snapshot` defer ✓.
- Test `detail_project/tests_export_json_separation.py` (8): seluruh JSON report route/UI hilang, backend manager menolak JSON sebagai report, data-package versioned + atomic import.

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-15 | WP-B5 inc-B5d | `tests_export_json_separation` + regresi export + `vitest` | PASS | JSON separation 8/8; full B5+CSP 56/56; frontend 265/25skip; `node --check` + `manage.py check` bersih |

**Catatan defer:** dedicated schedule-only package dapat dibangun kelak bila ada workflow import parsial Jadwal yang sah; saat ini full data Jadwal round-trip melalui `project_backup`.

#### inc-B5e — Signature/snapshot/threshold/empty (SURVEI + LOCK 2026-06-15)

**Survei:** sebagian besar item B5e SUDAH ada:
- **Signature config per report:** `signature_config.SignaturePresets` (PERENCANAAN owner+perencana; PELAKSANAAN owner+kontraktor+pengawas; FULL) + `DOCUMENT_PRESETS` map per report type + `build_signatures` (field cocok model: nama_client/nama_konsultan_perencana/nama_kontraktor/nama_konsultan_pengawas). **DIKUNCI** `tests_export_signature.py` (5).
- **PDF signature tak berdiri sendiri:** `pdf_exporter` memakai `KeepTogether`, `SignatureLayoutRules` dengan minimum 3 baris, dan reservasi `signature_height` pada halaman terakhir. Contract test mengunci aturan minimum-row dan wiring layout.
- **Empty export:** PDF/Excel/Word memiliki placeholder data kosong dan dikunci contract test.
- **Calc dataset = layar:** WP-B1 kanonik (adapter pakai `compute_rekap_for_project`).
- **Threshold sync/bg:** ada jalur async Celery (`api_start_export_async`) + warning `>100 pages` (`export-coordinator warningThreshold:100`). Auto-switch threshold = opsional.

**DoD acceptance WP-B5 — TERPENUHI:** calc parity ✓ (B1) · no `str(e)` ✓ (B5a) · empty allowed ✓ · PDF pagination/signature ✓ (locked) · report tanpa JSON ✓ (B5d) · backup/template versioned+atomik ✓ (B5d).

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-15 | WP-B5 inc-B5e | `tests_export_signature` + full B5+CSP suite | PASS | 56/56: signature roles + anti-orphan minimum 3 baris + empty placeholder + safe error wrapper + JSON separation terkunci. |
| 2026-06-15 | WP-B5 final review | independent code review + Docker smoke | PASS | Menutup gap yang ditemukan saat review: 4 JSON-report route/UI tersisa dipensiunkan; seluruh controller export aktif memakai correlation-ID wrapper. Docker web/celery healthy, HTTP `/` 200 + CSP report-only, migration plan kosong. |

**Keputusan owner diperlukan untuk MENUTUP WP-B5 (item scope non-acceptance):**
1. **Threshold sync/background:** terima apa adanya (async ada + warning 100pp) ATAU tambah auto-switch ke async di > N pages (N=?).
2. **Nasib jalur client-render** (`views_export.py` image-upload): pertahankan (fungsional) ATAU migrasi penuh server-authoritative (effort terpisah).
3. **dataset snapshot per export:** terima (export pakai compute kanonik = identik layar) ATAU butuh snapshot tersimpan eksplisit.

**Rekomendasi:** terima ketiganya apa-adanya/defer (fungsional; bukan bagian acceptance) → **WP-B5 DONE**. Enhancement (auto-async threshold, full server-authoritative client-render) = milestone perf terpisah, seperti CSP enforcement.

**KEPUTUSAN OWNER 2026-06-15: terima as-is → WP-B5 SELESAI.** 3 item scope (auto-async threshold, migrasi penuh client-render→server-authoritative, dataset snapshot eksplisit) di-DEFER ke **milestone performa terpisah** (DEC-B5-DEFER). Tidak memblok; semua fungsional + DoD acceptance terpenuhi.

**WP-B5 SELESAI:** B5a error-wrapper+correlation-id · B5b identity provider (fix lokasi/tahun='-') · B5c filename `NamaProject_YYYY-MM-DD.ext` · B5d JSON keluar dari report + data-package atomic/versioned · B5e signature/empty/PDF-placement locked. Owner hardening: async-leak, CSP sink, full identity fields.

---

### WP-B6 — Canonical Weekly Distribution Service (SURVEI 2026-06-16)

**Status:** IN PROGRESS (survei + rencana increment). **Sumber:** JDW/RK, KS-01..05, RK-01, R1/R2. **Dependency:** WP-B4 (DONE). **Arah sudah di-pre-decide** doc 23 §10 (D-RK-*) + audit Jadwal R1/R2.

**Survei:**
- **JS recompute + auto-regenerate senyap:** `jadwal_kegiatan_app.js:116 _estimateExpectedWeeklyColumns()` → `:2128/2140` auto `_regenerateTimeline` saat page open (R2). **Vite-bundled** (KF-06 dist protected).
- **`compute_kebutuhan_timeline` (`services.py:3064`)** pakai `_calculate_overlap_days` (PekerjaanTahapan + overlap-hari) = **RK-01** — BUKAN weekly canonical. Kompleks (period buckets, cache).
- **Belum ada builder distribusi mingguan kanonik bersama** (SSOT yg dipakai Jadwal + Kebutuhan).
- `timeline_stale` server-side: ✅ sudah (B4 inc-4a).
- Canonical weekly source = `PekerjaanProgressWeekly.planned_proportion` (per pekerjaan×week_number) — sudah dipakai B4.

**Rencana increment (perlu persetujuan):**
| Inc | Fokus | Sifat | DoD |
|---|---|---|---|
| **B6a** | Builder kanonik `build_weekly_distribution(project,…)` dari `planned_proportion` → bucket mingguan + minggu parsial + unscheduled; SSOT | backend, baru, **testable** | total weekly+unscheduled=total |
| **B6b** | Rekap Kebutuhan weekly pakai builder (ganti overlap-day RK-01) | backend, **risky** (ubah angka kebutuhan; arah=D-RK §10) | kebutuhan weekly=jadwal builder; total parity |
| **B6c** | Agregasi Periode 4-Minggu (4 bucket) via builder | backend, testable | 4-week=Σ4 minggu |
| **B6d** | Jadwal: week_number/kolom dari server; hentikan JS recompute + auto-regenerate senyap (R1/R2) | **frontend Vite bundle** (KF-06 — perlu rebuild/strategi) | JS tak recompute week; no silent regenerate |
| **B6e** | Contract test parity week-numbering JS↔Python | test | lulus |

**Catatan:** B6a–B6c backend (bisa dites sekarang, DB up). B6d butuh strategi Vite bundle. B6b mengubah angka kebutuhan (RK-01) → perlu kehati-hatian + parity test. Mulai: **B6a** (builder kanonik, fondasi, tanpa keputusan baru).

#### inc-B6a — Builder kanonik `build_weekly_distribution` (DONE 2026-06-16)

`services.build_weekly_distribution(project)` — SSOT distribusi mingguan dari `PekerjaanProgressWeekly.planned_proportion`. Return: `weeks` (kolom kanonik {week_number,start,end} tersortir), `by_pekerjaan` ({pkj:{week:fraksi 0..1}}), `scheduled_fraction`, `unscheduled_fraction` (=max(0,1−Σ)). Pekerjaan tanpa baris weekly tetap muncul sebagai `scheduled=0` dan `unscheduled=1`, agar kebutuhan belum terjadwal tidak hilang. **Invariant: Σ fraksi mingguan + unscheduled = 1** (saat ≤100%) → distribusi qty apa pun atas minggu+unscheduled mereproduksi total persis. Read-only (PekerjaanProgressWeekly), tak ubah perilaku consumer lain.

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-16 | WP-B6 inc-B6a | `tests_weekly_distribution` | PASS | 7/7: empty, weeks kanonik tersortir+dates, fraksi=prop/100, full→unscheduled 0, partial→remainder, pekerjaan tanpa weekly→unscheduled 1, invariant Σ+unscheduled=1. `manage.py check` bersih |

**Berikutnya: B6b** — Rekap Kebutuhan weekly/4-week pakai builder (ganti overlap-day RK-01) + parity test (`Σ weekly + unscheduled = total kebutuhan`). RISKY (ubah angka) → kawal dengan parity.

#### inc-B6b — DEEP SURVEI + RENCANA (2026-06-16, MENUNGGU REVIEW OWNER)

**Temuan kunci (lebih besar dari "ganti distribusi"):**
- Bucket minggu Rekap Kebutuhan **TIDAK** dari `PekerjaanProgressWeekly`. Dibangun `get_project_period_options` (`services.py:328`) dari **`TahapPelaksanaan`** (ISO-week key `YYYY-Www`, week_num project-relative) → lalu `compute_kebutuhan_timeline` (`:3134`) distribusi via **overlap-hari** terhadap tanggal `PekerjaanTahapan` (`assignment_map`, `_calculate_overlap_days`, loop `:3399-3422`). Ini RK-01.
- Jadi B6b = **mengganti SUMBER bucket minggu** (TahapPelaksanaan ISO-week → `build_weekly_distribution` PekerjaanProgressWeekly) **DAN** mekanisme distribusi (overlap-hari → fraksi kanonik). Tujuan: minggu Kebutuhan == minggu Jadwal; "Tahapan bukan calculation source".
- `base_quantity` per (item×pekerjaan) = `koef_expanded × volume × proporsi_multiplier` (`:3370-3385`) — **dipertahankan**; hanya pembagian ke periode yang diganti.
- `compute_kebutuhan_timeline` ~400 baris: mode `week`/`month`, `mode='tahapan'` (filter 1 tahapan), filters (klas/sub/pekerjaan), time_scope, cache (`_kebutuhan_signature`). Rewrite penuh = RISIKO tinggi.

**Keterkaitan / sub-keputusan:**
1. **Week mode** — jelas: bucket dari `build_weekly_distribution(project).weeks`; distribusi `base_quantity × by_pekerjaan[pkj][week]`; sisa → bucket **unscheduled** (`unscheduled_fraction`). Inti DoD.
2. **Month mode** — agregasi minggu-kanonik → bulan (by tanggal mulai minggu), bukan ISO-month dari TahapPelaksanaan. Supaya satu sumber.
3. **Tahapan-mode** (`mode='tahapan'`) — bergantung `PekerjaanTahapan`; **D-RK-08 = tahapan DIPENSIUN**. Jalur ini kemungkinan usang → butuh keputusan owner: ikut pensiun (hapus mode) atau biarkan sementara.

**Rencana eksekusi (usulan, perlu persetujuan):**
- **B6b-1:** Week mode pakai builder kanonik + unscheduled bucket. Parity test: `Σ semua minggu + unscheduled == total kebutuhan` per item (invariant B6a). Regresi `tests_rekap_calculation_contract` + kebutuhan.
- **B6b-2:** Month mode = agregasi minggu-kanonik ke bulan (satu sumber).
- **B6b-3 (keputusan owner):** tahapan-mode → pensiun (ikut D-RK-08) ATAU pertahankan sementara.

**Dampak diketahui:** B6b mengubah **nilai per-periode** Rekap Kebutuhan (memperbaiki RK-01); **total tetap** (dijaga parity test). Cache signature dipertahankan; verifikasi tanpa regresi.

**STATUS: menunggu review/keputusan owner** atas (a) scope B6b-1+B6b-2 sekarang, (b) nasib tahapan-mode (B6b-3 / D-RK-08). Belum ada perubahan kode B6b (B6a tetap fondasi additive aman).

**KEPUTUSAN OWNER 2026-06-16:** B6b-1 disetujui (week + builder + unscheduled; DoD Σminggu+unscheduled=total per item). B6b-2 dikoreksi → **agregasi Periode 4-Minggu (week 1-4, 5-8, …), BUKAN kalender bulan**. B6b-3 → **tahapan-mode DIPENSIUN** (D-RK-08): backend abaikan `mode=tahapan` + metadata deprecation; UI/filter/chip/export param dibersihkan di WP-P8/CL-06; Tahapan TAK BOLEH lagi ubah quantity/total.

**TEMUAN TAMBAHAN (dua jalur kebutuhan):**
- `api_rekap_kebutuhan_weekly` (`views_api.py:6748`) SUDAH pakai weekly proportion (Item Qty × proporsi/100) — bukan jalur bug — TAPI logika sendiri (belum `build_weekly_distribution`). Konvergensikan ke SSOT B6a.
- `compute_kebutuhan_timeline` (`services.py:3134`, via `api_get_rekap_kebutuhan_timeline`) = jalur **overlap-day** (RK-01) yang dipakai TIMELINE halaman Rekap Kebutuhan → ini target utama B6b.

**Edit-map cohesive rewrite `compute_kebutuhan_timeline` (B6b-1+2+3 bersama, krn deprecate tahapan membuang overlap-day utk SEMUA mode):**
- bucket source: `_select_period_buckets`/`get_project_period_options` (TahapPelaksanaan ISO-week) → `build_weekly_distribution(project).weeks`; week mode = per-week, 4-week mode = grup 4 minggu (week_number 1-4/5-8/…).
- distribusi: hapus `assignment_map`+overlap-day; `base_quantity × by_pekerjaan[pkj][week]` → bucket; `base_quantity × unscheduled_fraction[pkj]` → bucket 'unscheduled'. `base_quantity = koef_expanded × volume` (buang `proporsi_multiplier` tahapan).
- `mode='tahapan'` → diabaikan (treat 'all') + `meta.deprecated_mode`. Tahapan tak ubah quantity.
- time_scope: filter bucket via **rentang tanggal** (scope start/end → tanggal) terhadap minggu kanonik (key lama ISO-week tak kompatibel → map by date); parity diuji TANPA scope (full).
- pertahankan: cache (`_kebutuhan_signature`), filters (klas/sub/pekerjaan), payload shape (periods[] + 'unscheduled' + meta), logging.
- caveat frontend: period selector (week/month) frontend-coupled (Vite/template) → label "month" akan menampilkan 4-week; penyelarasan UI = WP-P8/B6d.

**Tes:** parity (Σ minggu+unscheduled=total per item, tanpa scope) + regresi `tests_rekap_calculation_contract` + `tests_api_v2_access` (akses) + check/migrasi. Existing test hanya akses/kontrak field (tak mengunci overlap-day) → aman diubah.

**GO OWNER 2026-06-16 dengan koreksi scope:**
- B6b = rewrite **`compute_kebutuhan_timeline` SAJA**. `api_rekap_kebutuhan_weekly` DIKELUARKAN → **B6f follow-up** (belum SSOT: pakai detail_list raw, default volume 1.0, tanpa expanded/raw-fallback canonical, tanpa unscheduled, payload beda → blast radius besar bila dicampur).
- B6c (agregasi 4-minggu) **masuk bersama** B6b.
- `month_range` = **compat alias** utk four-week: request lama `month_range`→ diperlakukan `four_week_range`; meta `bucket_mode:"four_week"` + `compat_mode:"month_range"`. BUKAN kalender bulan.
- bucket values **stabil**: `week_1`, `period4_1`, dst. Request lama `YYYY-Wxx`/`YYYY-MM` → map best-effort via tanggal. Parity full (tanpa scope) + 1 test scope sederhana (range tak kosong).
- tahapan-mode: diabaikan utk kalkulasi (quantity == all+filter lain, TANPA PekerjaanTahapan); meta `deprecated_mode:"tahapan"` + `deprecated_tahapan_id`.

**B6f (follow-up, dicatat):** konvergensi `api_rekap_kebutuhan_weekly` ke SSOT (`build_weekly_distribution` + base_quantity canonical expanded/raw-fallback + unscheduled + payload selaras). Tidak dikerjakan di B6b.

#### inc-B6b + B6c — `compute_kebutuhan_timeline` canonical rewrite (DONE 2026-06-16)

Rewrite `services.compute_kebutuhan_timeline` (+ helper `_scope_date_window`):
- **Sumber bucket** = `build_weekly_distribution(project).weeks` (bukan TahapPelaksanaan ISO-week). Mode `week` (value `week_N`) atau **`four_week`** (value `period4_N`, grup 4 minggu) — `month_range` jadi **compat alias** (`meta.bucket_mode="four_week"`, `meta.compat_mode="month_range"`).
- **Filter metadata ikut canonical:** `get_project_period_options(project)` tidak lagi membaca `TahapPelaksanaan`; `periods.weeks` = `week_N`, `periods.months` = compat 4-minggu `period4_N`, sehingga period selector tidak kosong pada project yang hanya punya `PekerjaanProgressWeekly`.
- **Distribusi** = `base_quantity × planned_proportion_fraction[week]` → bucket; sisa `× unscheduled_fraction` → bucket `unscheduled`. `base_quantity = koef_expanded × volume` (proporsi tahapan DIBUANG).
- **Tahapan dipensiun (D-RK-08):** `assignment_map`/overlap-day DIHAPUS; `mode='tahapan'` diperlakukan = `all` (quantity sama), hanya `meta.deprecated_mode="tahapan"` + `meta.deprecated_tahapan_id`. Tahapan TAK lagi ubah quantity.
- **time_scope** difilter by-tanggal (`_scope_date_window` map key legacy → tanggal via period_options). Parity diuji penuh (tanpa scope).
- Dipertahankan: cache/signature, filters (klas/sub/pekerjaan), payload shape (periods[] + `unscheduled` + meta), no-scope return.
- `api_rekap_kebutuhan_weekly` TIDAK disentuh (B6f).

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-16 | WP-B6 inc-B6b+B6c | `tests_kebutuhan_timeline_b6b` + regresi | PASS | 34/34: 7 timeline/filter tests (weekly=proporsi, **parity Σperiode+unscheduled=total/item**, unscheduled remainder+job, four_week=compat month_range, filter periods canonical tanpa Tahapan, canonical week scope, tahapan-deprecated quantity=all) + weekly_distribution 7 + rekap_calc_contract 15 + api_v2_access 5. `manage.py check` bersih |

**Caveat frontend (B6d/WP-P8):** period selector Rekap Kebutuhan (Vite/template) masih label week/month → "month" kini menampilkan data 4-minggu (label "Minggu 1-4"). Penyelarasan UI + hentikan JS week-recompute/auto-regenerate Jadwal = **B6d** (Vite bundle).

**Gap-fix owner (2026-06-16, sebelum checkpoint):** `get_project_period_options()` masih berbasis `TahapPelaksanaan` → filter periode UI bisa kosong/desync utk project yang punya `PekerjaanProgressWeekly` tapi tanpa Tahapan. Diubah **canonical**: `periods.weeks` = `week_1,week_2,…`; `periods.months` = compat key 4-minggu `period4_1,period4_2,…`. `_normalize_time_scope()` kini menerima `week_N` & `period4_N` → range filter UI tetap bekerja dgn bucket baru. Konsisten dgn `_scope_date_window`/`compute_kebutuhan_timeline` (B6 suite 34/34, B4/B5 +76/76, check & migrasi bersih). Test owner: `test_period_options_are_canonical_without_tahapan`.

**RESIDUAL (valid, → B6f/WP-P8):** `compute_kebutuhan_items(... time_scope=...)` (SNAPSHOT path) masih pakai helper legacy `_build_time_scope_multiplier()` berbasis `PekerjaanTahapan`. B6b menutup **timeline** path saja. Jika snapshot+time_scope masih dipakai aktif di UI/export → harus dikonvergensi (jangan ada dua cara scope kebutuhan). Masuk **B6f / WP-P8**.

#### inc-B6f part-1 — Snapshot scope multiplier → canonical (DONE 2026-06-16)

`_build_time_scope_multiplier()` (`services.py:472`) **TIDAK lagi pakai `PekerjaanTahapan`/overlap-day** → kini fraksi in-scope dari `build_weekly_distribution` (Σ `planned_proportion` minggu dalam jendela tanggal). Mekanisme di-swap; **edge legacy dipertahankan** (pekerjaan tanpa jadwal → 1.0 fully-in-scope). Menutup "dua cara scope kebutuhan" — snapshot path kini = timeline path (satu SSOT). Test `tests_kebutuhan_timeline_b6b` +3 (fraksi window 0.60, both 1.00, unscheduled 1.0, all→{}); B6 targeted suite **37/37**; B4/B5 regression **76/76**; `manage.py check`, `makemigrations --check --dry-run`, dan `git diff --check` bersih.

**B6f part-2 (sisa):** `api_rekap_kebutuhan_weekly` (`views_api.py:6748`) konvergensi ke SSOT — pakai detail_list raw + default volume 1.0 + tanpa expanded/raw-fallback + tanpa unscheduled + payload beda. Perubahan PERILAKU endpoint (volume 1.0→real, +expanded, +unscheduled) → perlu survei consumer (kurva-s/V2) dulu. **Belum dikerjakan.**

**Survei consumer B6f part-2 (2026-06-16):** pencarian repo hanya menemukan route/view/test/dokumen untuk `api_rekap_kebutuhan_weekly` / `rekap-kebutuhan-weekly`; tidak ditemukan consumer frontend aktif di luar test. Rekomendasi: **jangan konvergensi sekarang** karena endpoint tampak orphan/eksperimental dan perubahan angka/payload berisiko tanpa manfaat UI langsung. Tandai sebagai kandidat **cleanup/defer**; bila nanti dipertahankan sebagai API eksternal/mobile, konvergensikan dalam WP terpisah dengan kontrak payload eksplisit.

**Berikutnya:** B6d (jadwal JS, Vite — no recompute/auto-regenerate) + B6e (parity JS↔Python) tetap dipindahkan ke **WP-P8**. Secara backend calc-core, WP-B6 dianggap cukup untuk checkpoint.

#### inc-2.2 — Verdict-review hardening (5 koreksi owner, sebelum lock/fan-out) → schema `b4.3`

Owner review menolak lock b4.2 + fan-out; 5 hal diperbaiki:
1. **HIGH cache collision:** owner mereproduksi digest count+sum bertabrakan (pertukaran nilai/relasi total-tetap → signature sama → readiness stale). **Cache cross-request DIHAPUS total** (digest row-exact biayanya = recompute, jadi tak berfaedah). Kini selalu hitung dari DB live + memoize **per-request** (arg `request`). Contract test: `test_relation_move_updates_affected_set_no_stale` (pindah FK harga_item, count tetap → affected set berubah benar) + `test_bulk_update_negative_coef_is_reflected`.
2. **Bundle expansion lengkap:** `expected/actual` per source_detail. ref_pekerjaan → expected = jumlah komponen expanded pekerjaan yg direferensikan (EXAK); ref_ahsp → `RincianReferensi` count (best-effort, tak menaikkan flag partial agar tak false-positive). Issue baru `incomplete_expansion` (actual<expected). Test `test_bundle_incomplete_expansion_flagged` (expected 2, actual 1).
3. **`affected_items` dipulihkan:** kontrak minimum Master Plan (line 330) — index item kanonik `[{harga_item_id, kode}]`. Test `test_affected_items_is_canonical_item_index`.
4. **Test frontend nyata (bukan source-grep):** logika banner diekstrak ke modul ESM mandiri `static/.../js/shared/readiness_banner.js` (`buildReadinessBannerHTML`, self-contained escapeHtml, expose `window.ReadinessBanner`); `rekap_rab.js` mendelegasi ke modul; template muat sebagai `<script type="module">`. Test happy-dom `tests/readiness_banner.test.js` (5): escaping XSS, null saat bersih (tak ada false "all clear"), per-signal lines, **pending diabaikan/tak dianggap selesai**, truncation.
5. **PERFORMA query-budget:** `test_query_budget_constant_no_n_plus_1` (query count konstan utk 2 vs 8 pekerjaan, ≤12) + `test_request_scoped_memoization` (panggilan ke-2 dlm satu request = 0 query tambahan).

**Stale-expansion KNOWN LIMITATION (didokumentasikan di `readiness.py`):** deteksi `stale_expansion` pakai `updated_at` yg bisa di-bypass `QuerySet.update()`. Reliable staleness butuh revision/timestamp eksplisit per mutasi = **inc-4**. Tanpa cache, semua sinyal LAIN selalu mencerminkan state terbaru.

**Review lanjutan 2026-06-15:** dua gap pilot ditutup sebelum lock:
- shared banner diubah dari module-deferred menjadi classic global yang dimuat sinkron sebelum `rekap_rab.js`; ini mencegah banner hilang pada initial load karena `loadData()` berjalan saat script klasik dieksekusi;
- validasi count expansion kini menolak dua arah mismatch untuk expected yang exact: `actual < expected` = `incomplete_expansion`, `actual > expected` = `excess_expansion`. Pesan banner diubah menjadi “total belum final” karena mismatch dapat menyebabkan undercount maupun overcount, dan arah perbaikan diselaraskan ke page Template AHSP.

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-15 | WP-B4 inc-2.2 | `tests_wp_b4_readiness` | PASS | 23/23 (incl relation-move collision, bundle incomplete/excess expansion, affected_items, query-budget, request-memo, dan urutan load banner sebelum script Rekap RAB) |
| 2026-06-15 | WP-B4 inc-2.2 | `tests_rekap_calculation_contract` | PASS | 15/15 tanpa regresi |
| 2026-06-15 | WP-B4 inc-2.2 | frontend `vitest run` | PASS | 252 passed / 25 skipped (incl `readiness_banner.test.js` 5); `node --check` rekap_rab.js OK |

**Owner-approved (review verdict):** null≠zero, pending=None, allocation_without_volume terpisah, diagnostic traceable, Rekap RAB display-only. **Sisa gate sebelum fan-out:** mohon review schema `b4.3` + visual UAT banner Rekap RAB → lalu Rincian AHSP satu per satu.

#### inc-2.3 — Owner lock + 2 fix tambahan (2026-06-15)

Owner **menyetujui & MENGUNCI schema `b4.3`** — tidak ada blocker kode tersisa sebelum fan-out. Owner menambahkan 2 perbaikan:
1. **Race condition initial-load:** `readiness_banner.js` kini dimuat sebagai classic `<script>` **sinkron sebelum** `rekap_rab.js` (`rekap_rab.html:263`) — `globalThis.ReadinessBanner` pasti tersedia saat first load (modul diubah: tanpa top-level `export`, attach ke `globalThis`; test impor utk side-effect).
2. **`excess_expansion`:** expanded berlebih (`actual > expected`) kini diflag (`readiness.py:236-238`) → cegah RAB terhitung ganda. Pesan banner diperjelas: **"total RAB belum dapat dianggap final"** (mismatch bisa terlalu rendah MAUPUN tinggi); baris ekspansi → "sumber AHSP belum sinkron dengan hasil ekspansi".

**Verifikasi owner:** WP-B4 readiness 23/23 · readiness+rekap 38/38 · frontend 252 pass / 25 skip · `manage.py check` + migration check bersih · `node --check` + `git diff --check` bersih. Keterbatasan `stale_expansion` berbasis `updated_at` tetap tercatat utk inc-4 (`readiness.py:56`).

**Status:** schema LOCKED. **Gate tersisa: visual UAT banner Rekap RAB** → setelah itu fan-out **Rincian AHSP** (1 consumer/tahap) memakai pola pilot.
