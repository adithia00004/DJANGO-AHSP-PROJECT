# Implementation Execution Tracker R4/R5

**Mulai:** 14 Juni 2026  
**Master plan:** `27_Master_Implementation_Plan_20260614.md`  
**Status keseluruhan (≈ 26% implementasi):** **IN PROGRESS - WP-B1/WP-B2/WP-A1/WP-B3 DONE / WP-B4 `b4.4` · inc-3 (5/5 consumer) + inc-4a (3 sinyal jadwal LIVE) DONE · sisa inc-4b stale-signature (migrasi) / WP-A2 NEXT**

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
| WP-B4 | Canonical readiness | IN PROGRESS (~92%, schema `b4.4`) | 2026-06-15 | - | WP-B1 | b4.4: UF-011 FIXED + `/readiness/` + autoload + **inc-3 5/5 consumer** + **inc-4a 3 sinyal jadwal LIVE**. Sisa: **inc-4b** stale-expansion signature (perlu migrasi). Test 32 readiness backend + 265 frontend |
| WP-B5 | Server-authoritative export | PENDING | - | - | B1/B2/B4 | - |
| WP-B6 | Canonical weekly distribution | PENDING | - | - | WP-B4 | - |
| WP-B7 | CUSTOM live-reference | PENDING | - | - | B3/B4 | - |
| WP-B8 | Tipe LAIN | PENDING | - | - | B3 | - |
| WP-B9 | Bundle limits | PENDING | - | - | B7/B8 | - |
| WP-B10 | Actual-cost legacy mapping | PENDING | - | - | WP-00/B3/B6 | Eksekusi hanya jika data legacy ada |
| WP-P1..P9 | Integrasi per-page | PENDING | - | - | Shared WP | - |
| Fase 3 | Cleanup/deprecation | PENDING | - | - | Replacement gates | - |
| Fase 4 | Regression/UAT | PENDING | - | - | Semua WP target | - |

## 2.5 Progress Implementasi (estimasi terbobot)

**Headline: ≈ 25% dari eksekusi implementasi selesai** (per 2026-06-15).
Prasyarat audit + planning (docs 09, 16–28) = **100% selesai** dan TIDAK dihitung di angka implementasi ini.

Estimasi terbobot per fase (bobot = perkiraan effort relatif, bukan jumlah WP):

| Fase | Bobot | % Selesai | Kontribusi | Dasar |
|---|---|---|---|---|
| Fase 1 — Shared foundation (A1–A2, B1–B10) | 45% | ~49% | ~22.1% | A1·B1·B2·B3 DONE; B4 ~85% (service+kontrak+5 consumer wired, sisa inc-4); A2·B5·B6·B7·B8·B9·B10 PENDING |
| Fase 2 — Integrasi per-page (P1–P9) | 30% | ~5% | ~1.5% | readiness display terpasang di 5 halaman (bagian B4); integrasi per-page penuh belum |
| Fase 3 — Cleanup/deprecation (CL-01..17) | 10% | 0% | 0% | belum mulai (gate: replacement selesai) |
| Fase 4 — Regression/UAT | 15% | ~2% | ~0.3% | contract/regression test berjalan tiap WP; UAT formal belum |
| **Total** | **100%** | | **≈ 25%** | |

Rincian bobot Fase 1 (sub-effort relatif, total 45): A1=3 ✅, A2=3 ⬜, B1=5 ✅, B2=3 ✅, B3=6 ✅, **B4=6 (≈85% → 5.1)**, B5=5 ⬜, B6=4 ⬜, B7=4 ⬜, B8=2 ⬜, B9=2 ⬜, B10=2 ⬜ → selesai 22.1/45 ≈ 49%.

Rincian B4 (≈85%): inc-1 survei ✅ · inc-2/2.1/2.2 service+kontrak `b4.3` LOCKED ✅ · UF-011 fix + UAT PASS ✅ · **inc-3 SELESAI: 5/5 consumer wired** (Rekap RAB·Rincian·Template·Jadwal·Kebutuhan + endpoint `/readiness/` + autoload) ✅ · **sisa: inc-4 sinyal jadwal aktual & stale-revision** ⬜.

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
