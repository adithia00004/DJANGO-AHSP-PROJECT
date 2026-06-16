# Implementation Execution Tracker R4/R5

**Mulai:** 14 Juni 2026  
**Master plan:** `27_Master_Implementation_Plan_20260614.md`  
**Status keseluruhan (≈ 49% implementasi):** **FASE 1 SELESAI & 100% hijau (A1/A2/B1-B5/B7-B10; B6 DoD 3/5 — B6d/e→WP-P7). FASE 2 dimulai: WP-P1 (Harga Items) DONE.** Kebenaran perhitungan AMAN (SSOT canonical). NEXT: WP-P2 (Template AHSP) dst. Defer (tercatat, non-blocking): **B6d/e→WP-P7 (Jadwal)**, B6f-2 cleanup→WP-P8, B9b prospective UI→WP-P, A2 CSP enforcement, B5 export-perf, B3 DB-constraint-koef follow-up.

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
| WP-B6 | Canonical weekly distribution | IN PROGRESS (DoD 3/5 — backend SSOT DONE; B6d/e → WP-P7 Jadwal) | 2026-06-16 | - | WP-B4 | **DoD 5 butir: ✅#2 builder sama Jadwal/Kebutuhan, ✅#3 Σweekly+unscheduled=total, ⬜#1 JS tak recompute week (B6d), ⬜#4 contract test JS↔Python (B6e), ⬜#5 no auto-regenerate senyap (B6d).** ✅B6a builder ✅B6b/c `compute_kebutuhan_timeline` canonical ✅B6f-1 snapshot scope. Targeted 37/37. **⬜B6d+B6e = Vite (KF-06, butuh rebuild owner) → dikerjakan di WP-P7 (Jadwal; checklist "R1 week number server-authoritative")**. ⬜B6f-2 `api_rekap_kebutuhan_weekly` orphan → cleanup (Rekap Kebutuhan/WP-P8). **Kebenaran angka AMAN (SSOT backend canonical); sisa = hardening UI Jadwal + parity guard.** |
| WP-B7 | CUSTOM live-reference | DONE | 2026-06-16 | 2026-06-16 | B3/B4 | D-05 reference-sync + user-value protection LENGKAP (a–e). B7a signature+migrasi 0049/0050 · B7b sinyal readiness `b4.5` · B7c fix TA-03 (cascade reset atomik) · B7d endpoint sync manual (bundle_quantity utuh, audit, idempotent) · B7e badge+tombol Template AHSP. Skenario-1 only (Skenario-2 versi-baru sengaja tak memicu). Caveat: nested-master signature + "upgrade versi tahunan" = WP terpisah. AT-05 audit-writer RETAINED |
| WP-B8 | Tipe LAIN | DONE | 2026-06-16 | 2026-06-16 | B3 | D-08 LENGKAP (a–d): OTHER_DIRECT vs WORK_BUNDLE, item_type **derived** (tanpa kolom). B8a helper+expose API · B8b save terima LAIN-tanpa-ref sbg OTHER_DIRECT (2 jalur ekspansi konsisten) · B8c label humanis · B8d UI 3-aksi tambah. Perangkap save tertutup; angka data lama tak berubah |
| WP-B9 | Bundle limits | DONE (server guards; B9b UI→WP-P) | 2026-06-16 | 2026-06-16 | B7/B8 | D-10 inti: `MAX_BUNDLE_LEVELS=4` (depth 2→3, kedua jalur) + `MAX_EXPANDED_COMPONENTS=500` stop-segera + circular (existing). Test 4/4. B9b prospective-validation UI DEFER→WP-P |
| WP-B10 | Actual-cost legacy mapping | DONE | 2026-06-16 | 2026-06-16 | WP-00/B3/B6 | Inventory: actual_cost hanya di PekerjaanProgressWeekly kanonik → mapping legacy NO MIGRATION REQUIRED. JDW-05 fix: reset actual kini hapus actual_cost (no orphan); planned tak terdampak. Test 2/2 |
| WP-P1 | Harga Items | DONE | 2026-06-16 | 2026-06-16 | B1/B3/B4 | Model A (harga_satuan=SSOT, profil=kalkulator+provenance, LWW). P1a validasi(HI-05)·P1b atomic backend+frontend wiring(HI-02 e2e)·P1c bootstrap(HI-04)·P1d export=harga_satuan(HI-03/12)·P1e paste market÷factor+confirm(HI-07)·HI-08 localStorage dihapus·HI-16 dead code. Endpoint konversi orphan→Model-A-consistent+deprecated. Orphan-cleanup UI→Fase 3 |
| WP-P2..P9 | Integrasi per-page | PENDING | - | - | Shared WP | P2 Template AHSP (incl UF-007..012, ENH-01); **P7 Jadwal = serap B6d/e (JS week server-authoritative + stop auto-regenerate) + B6e parity test**; **P8 Rekap Kebutuhan = serap B6f-2 cleanup (`api_rekap_kebutuhan_weekly` orphan) + period selector 4-minggu**; P3 Volume; dst |
| Fase 3 | Cleanup/deprecation | PENDING | - | - | Replacement gates | - |
| Fase 4 | Regression/UAT | PENDING | - | - | Semua WP target | - |

## 2.1 Penjelasan Bahasa-Mudah: Apa & Kenapa Tiap WP

> Untuk pembaca non-teknis. Tiap WP = satu masalah nyata yang membuat angka/keamanan aplikasi bisa salah secara diam-diam. "Diam-diam" = aplikasi tetap terlihat normal dan melaporkan sukses, padahal hasilnya keliru — ini risiko terburuk untuk aplikasi RAB.

| WP | Apa ini (konteks) | Kenapa harus diperbaiki |
|---|---|---|
| **WP-A1** Hapus XSS | Mencegah teks yang diketik user (nama pekerjaan, uraian, dll.) dijalankan sebagai kode di browser saat ditampilkan kembali. | Tanpa ini, seseorang bisa menyisipkan skrip lewat nama/uraian yang lalu mencuri sesi login atau merusak tampilan saat halaman dibuka orang lain. |
| **WP-A2** CSP | Lapisan pertahanan kedua: browser menolak skrip dari sumber yang tak dikenal. | Membatasi kerusakan bila ada satu XSS yang lolos — pertahanan berlapis, bukan satu titik gagal. |
| **WP-B1** Satu mesin hitung RAB | Layar, cetak, dan export memakai SATU rumus perhitungan yang sama. | Dulu angka bisa berbeda antara yang dilihat di layar dan yang di-export (mis. markup 0% vs 10%) → laporan tidak konsisten dan tidak bisa dipercaya. |
| **WP-B2** Sidik jari cache | "Sidik jari" data: bila harga/markup berubah, hasil yang disimpan sementara (cache) otomatis dianggap kedaluwarsa. | Dulu sidik jari lupa menyertakan harga → cache bisa menampilkan total lama padahal harga sudah diubah. |
| **WP-B3** Simpan atomik | Saat menyimpan, SEMUA baris tersimpan atau SEMUA ditolak — tidak ada "sebagian berhasil". | Dulu sebagian data bisa tersimpan diam-diam sambil melaporkan "sukses" → data jadi rusak separuh tanpa disadari. |
| **WP-B4** Banner kesiapan | Mendeteksi & menampilkan kondisi "data belum siap" (volume belum diisi, harga kosong, komposisi AHSP belum sinkron) sebagai banner peringatan. | Dulu nilai kosong diam-diam dihitung sebagai 0 → total terlihat final padahal sebenarnya kurang. |
| **WP-B5** Export resmi server | Export (Excel/PDF/Word) memakai angka resmi dari server, bukan draf yang belum disimpan; pesan error tidak membocorkan detail teknis. | Laporan resmi harus sama persis dengan perhitungan resmi, dan tidak boleh membocorkan informasi internal sistem. |
| **WP-B6** Distribusi mingguan kanonik | Rekap Kebutuhan dan Jadwal memakai SATU sumber distribusi mingguan yang sama (proporsi per minggu). | Dulu kebutuhan per-minggu dihitung dari "Tahapan + tumpang-tindih hari" yang berbeda dari Jadwal → angka per-minggu bisa keliru. |
| **WP-B7** Sinkronisasi referensi CUSTOM | Bila master AHSP (versi yang dipilih project) dikoreksi, sistem memberi tahu dan memungkinkan sinkronisasi manual — sambil menjaga angka yang diinput user. | Dulu koreksi master tidak pernah sampai ke project → RAB diam-diam memakai komposisi/harga lama tanpa cara untuk tahu. |
| **WP-B8** Tipe LAIN | Rapikan perilaku item kategori "LAIN" (bundle) sesuai keputusan produk D-08. | Agar komponen bundle dihitung dan ditampilkan konsisten dengan kategori lain. |
| **WP-B9** Batas bundle | Batasi kedalaman/ukuran ekspansi bundle (D-10). | Mencegah bundle bersarang tak terbatas membuat perhitungan lambat atau gagal. |
| **WP-B10** Pemetaan biaya aktual lama | Petakan data actual_cost legacy bila ada. | Hanya dieksekusi jika data lama benar-benar ada; menjaga kompatibilitas histori. |
| **WP-P1..P9** Integrasi per-halaman | Terapkan semua fondasi di atas ke tiap halaman + tuntaskan temuan UF/ENH per-halaman. | Fondasi bersama harus benar-benar terpasang di setiap halaman, bukan hanya di halaman pilot. |
| **Fase 3** Pembersihan | Hapus kode/jalur usang setelah penggantinya aktif (CL-01..17). | Mengurangi kebingungan & risiko memakai jalur lama yang salah. |
| **Fase 4** Regresi/UAT | Uji menyeluruh + uji terima oleh owner. | Memastikan seluruh perbaikan benar dari sudut pandang pemakaian nyata. |

## 2.5 Progress Implementasi (estimasi terbobot)

**Headline: ≈ 49% dari eksekusi implementasi selesai** (per 2026-06-16).
Prasyarat audit + planning (docs 09, 16–28) = **100% selesai** dan TIDAK dihitung di angka implementasi ini.

Estimasi terbobot per fase (bobot = perkiraan effort relatif, bukan jumlah WP):

| Fase | Bobot | % Selesai | Kontribusi | Dasar |
|---|---|---|---|---|
| Fase 1 — Shared foundation (A1–A2, B1–B10) | 45% | ~98% | ~44% | **A1·A2(report-only)·B1·B2·B3·B4·B5·B7·B8·B9·B10 DONE; B6 backend SSOT DONE (DoD 3/5)**; sisa hanya **B6d/e (Vite → WP-P7 Jadwal)** + defer (CSP enforcement, export-perf, B9b prospective UI, B3 DB-constraint) |
| Fase 2 — Integrasi per-page (P1–P9) | 30% | ~16% | ~4.8% | **WP-P1 Harga Items DONE** (Model A, HI-01..16); readiness display di 5 halaman (B4); P2–P9 belum |
| Fase 3 — Cleanup/deprecation (CL-01..17) | 10% | 0% | 0% | belum mulai (gate: replacement selesai) |
| Fase 4 — Regression/UAT | 15% | ~2% | ~0.3% | contract/regression test berjalan tiap WP; UAT formal belum |
| **Total** | **100%** | | **≈ 49%** | |

Rincian bobot Fase 1 (sub-effort relatif, total 45): A1=3 ✅, A2=3 ✅ (report-only), B1=5 ✅, B2=3 ✅, B3=6 ✅, B4=6 ✅, B5=5 ✅, **B6=4 (backend SSOT ✅ ≈3.2 = DoD 3/5; sisa B6d/e frontend≈0.8 → WP-P7 Jadwal)**, **B7=4 ✅**, **B8=2 ✅**, **B9=2 ✅**, **B10=2 ✅** → selesai ≈44.2/45 ≈ 98% (sisa hanya B6d/e≈0.8 Vite → WP-P7 Jadwal).

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
| KF-01 | Audit Trail admin-only tests | Test client redirect login meski `force_login` | **RESOLVED 2026-06-16** | Akar = `TimeoutMiddleware` jalankan view di thread terpisah → drop sesi force_login → 302 `/accounts/login/`. BUKAN auth global (terkonfirmasi). Fix: `@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)` (buang TimeoutMiddleware) di `tests_admin_only_pages`. 4/4 PASS |
| KF-02 | Rincian/export-button visibility | 3 fixture mendapat HTTP 302, expected 200 | **RESOLVED 2026-06-16** | Akar sama (TimeoutMiddleware vs force_login). Fix: `@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)` di `tests_export_button_visibility`. 3/3 PASS. SubscriptionMiddleware hanya gate WRITE (GET selalu lolos) → bukan penyebab |
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

### UF-013 - AT-01 (Audit Trail stored-XSS) TERLEWAT dari scope WP-A1 — FIXED 2026-06-16

**Konteks penemuan:** owner mempertanyakan apakah perbaikan kita kerap di-scope terlalu sempit (per-app/per-halaman) sehingga ada isu lintas-cutting yang terlewat. Cross-cutting completeness check dijalankan terhadap tema sistemik doc 26. **Hasil:** B1 (calc service), B2 (cache signature — tak ada `_kebutuhan_signature`/`_chart` terpisah, semua via `build_project_cache_signature`), B3 (tak ada 207 live), B5 (`exports/` + `views_export` response bersih; sisa `str(e)` = `logger.error` server-side, benar) **terbukti sudah app-wide**. **Satu celah nyata:** `audit_trail.js` adalah satu-satunya file render **tanpa `escapeHtml`**, menyuntik konten user mentah ke `innerHTML` (`:103-112` pekerjaan.uraian/change_summary/triggered_by/username/action; `renderDiffContent :59` old/new data) = **stored XSS**.

**Kenapa lolos (akar masalah scoping):** WP-A1 mengambil daftar kerja dari audit per-halaman yang punya temuan XSS (F-01/LP-01/RR-01/RR-18). **AT-01 diaudit di dokumen TERPISAH (doc 24 Audit Trail)** dan masuk doc 26 grup A-4, tetapi A-4 **tidak dipakai sebagai checklist final** saat menyusun worklist WP-A1 → item lintas-dokumen jatuh di seam.

**Fix (2026-06-16):** tambah `function escapeHtml` di `audit_trail.js`; escape semua field user di baris tabel + `escapeHtml(oldText/newText)` di `renderDiffContent`. Guard `xss_render_guard.test.js` diperluas dengan blok **AT-01** (escapeHtml ada; tiap field user di-escape; diff di-escape; no raw `${entry.*}`). `node --check` OK; guard **13/13 PASS**. Severity: **P0 stored-XSS** (sekarang CLOSED).

> **⚠️ PENEKANAN PROSES — anti-celah scoping (WAJIB dipakai tiap WP lintas-cutting):** sebelum menutup WP shared/keamanan, **gunakan doc 26 (Cross-Page Reconciliation) grup A-* sebagai checklist final**, BUKAN hanya temuan per-halaman dari satu dokumen audit. Untuk WP keamanan/format/atomicity/cache: lakukan **sweep repo-wide** (mis. `git grep` pola di SEMUA app/file, bukan hanya halaman pilot) dan catat hasil "sudah tersebar / masih sempit". Tema sistemik doc 26 (#1 XSS+CSP, #2 atomicity, #3 LWW, #4 export-leak, #5 calc service, #6 owner-decision consumers, #7 cache signature) = daftar induk; tiap WP yang menyentuhnya HARUS memverifikasi seluruh instans, bukan satu. Pelajaran UF-013: audit per-dokumen ≠ scope per-WP; selalu rekonsiliasi ke A-* sebelum tutup.

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
- caveat frontend: period selector Rekap Kebutuhan (week/month) frontend-coupled (Vite/template) → label "month" akan menampilkan 4-week; penyelarasan UI = WP-P8 (Rekap Kebutuhan). Jadwal JS recompute/auto-regen = B6d → WP-P7.

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

**Caveat frontend (dua halaman berbeda):** (a) period selector **Rekap Kebutuhan** (Vite/template) masih label week/month → "month" kini menampilkan data 4-minggu (label "Minggu 1-4"); penyelarasan UI ini = **WP-P8 (Rekap Kebutuhan)**. (b) hentikan JS week-recompute/auto-regenerate **Jadwal** = **B6d → WP-P7 (Jadwal)**, Vite bundle.

**Gap-fix owner (2026-06-16, sebelum checkpoint):** `get_project_period_options()` masih berbasis `TahapPelaksanaan` → filter periode UI bisa kosong/desync utk project yang punya `PekerjaanProgressWeekly` tapi tanpa Tahapan. Diubah **canonical**: `periods.weeks` = `week_1,week_2,…`; `periods.months` = compat key 4-minggu `period4_1,period4_2,…`. `_normalize_time_scope()` kini menerima `week_N` & `period4_N` → range filter UI tetap bekerja dgn bucket baru. Konsisten dgn `_scope_date_window`/`compute_kebutuhan_timeline` (B6 suite 34/34, B4/B5 +76/76, check & migrasi bersih). Test owner: `test_period_options_are_canonical_without_tahapan`.

**RESIDUAL (valid, → B6f/WP-P8):** `compute_kebutuhan_items(... time_scope=...)` (SNAPSHOT path) masih pakai helper legacy `_build_time_scope_multiplier()` berbasis `PekerjaanTahapan`. B6b menutup **timeline** path saja. Jika snapshot+time_scope masih dipakai aktif di UI/export → harus dikonvergensi (jangan ada dua cara scope kebutuhan). Masuk **B6f / WP-P8**.

#### inc-B6f part-1 — Snapshot scope multiplier → canonical (DONE 2026-06-16)

`_build_time_scope_multiplier()` (`services.py:472`) **TIDAK lagi pakai `PekerjaanTahapan`/overlap-day** → kini fraksi in-scope dari `build_weekly_distribution` (Σ `planned_proportion` minggu dalam jendela tanggal). Mekanisme di-swap; **edge legacy dipertahankan** (pekerjaan tanpa jadwal → 1.0 fully-in-scope). Menutup "dua cara scope kebutuhan" — snapshot path kini = timeline path (satu SSOT). Test `tests_kebutuhan_timeline_b6b` +3 (fraksi window 0.60, both 1.00, unscheduled 1.0, all→{}); B6 targeted suite **37/37**; B4/B5 regression **76/76**; `manage.py check`, `makemigrations --check --dry-run`, dan `git diff --check` bersih.

**B6f part-2 — KEPUTUSAN OWNER 2026-06-16: DEFER → kandidat cleanup (CL).** `api_rekap_kebutuhan_weekly` (`views_api.py:6748`, route `api/v2/.../rekap-kebutuhan-weekly/`) hanya ada di route/view/test/dokumen — **tidak ada consumer frontend aktif**. Payload beda + konvergensi mengubah angka/perilaku (default volume 1.0→real, +expanded/raw-fallback, +unscheduled) → **JANGAN konvergensi sekarang**. Bila kelak terbukti dipakai (mobile/API eksternal) → konvergensikan sebagai WP kecil dengan kontrak payload eksplisit. Sementara: kandidat cleanup roadmap (CL).

**WP-B6 BACKEND CALC-CORE SELESAI — checkpoint commit `58d3c41e` (owner verifikasi 2026-06-16):** B6a builder · B6b/B6c timeline canonical (RK-01, parity) · B6f-1 snapshot scope canonical. **Tahapan tidak lagi sumber kalkulasi kebutuhan di mana pun.** Verifikasi owner: B6 targeted 37/37, B4/B5 regression 76/76, `manage.py check` + `makemigrations --check` + `git diff --check` bersih. **Sisa DoD frontend → WP-P7 (Jadwal):** B6d (Jadwal JS week_number server-authoritative + stop recompute/auto-regenerate, Vite bundle KF-06) + B6e (parity test JS↔Python). B6f-2 (orphan endpoint) = cleanup → WP-P8 (Rekap Kebutuhan).

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

---

### WP-B7 — CUSTOM Live-Reference Propagation (SURVEI 2026-06-16, MENUNGGU REVIEW OWNER)

**Status:** IN PROGRESS (survei + rencana, BELUM ada perubahan kode). **Sumber:** TA-03, TA-18, keputusan owner **D-05** (final), AT-05 (audit-writer RETAIN). **Dependency:** WP-B3 (atomic, DONE), WP-B4 (readiness/signature, DONE).

**Konteks keputusan owner D-05 (final, doc 18 §916-947):** bundle master = **reference synchronization dengan perlindungan nilai milik user** — BUKAN live-reference senyap, BUKAN snapshot beku. Aturan:
1. Komponen/koefisien yang masih *inherited* dari AHSP Referensi mengikuti koreksi sumber.
2. Nilai input user — terutama **`bundle_quantity` (koefisien bundle di `DetailAHSPProject`)** — TIDAK boleh berubah.
3. Expanded = derived storage, boleh dibangun ulang.
4. Perubahan master TIDAK boleh mengubah project secara diam-diam → wajib **status + audit**.
Implementasi minimum yang dipilih owner: simpan revision/hash + waktu sync master pada raw bundle; saat master berubah tandai `reference_update_available`; rebuild expanded via proses sinkronisasi (aksi, bukan otomatis); pertahankan koef/jumlah bundle user; catat old/new ke audit trail. Client: badge "update tersedia" + aksi sync + ringkasan perubahan + feedback. **Bukan restrukturisasi DB besar.**

**Survei kode (terverifikasi):**
- **Dua sumbu propagasi (B7 mencakup keduanya):**
  - **TA-03 (intra-project):** `cascade_bundle_re_expansion(project, modified_pekerjaan_id)` (`services.py:1962`) ADA & dipanggil pada **save** (`:2772`) tetapi **TIDAK pada reset-to-reference** (`:2899` hanya `_populate_expanded_from_raw` utk pekerjaan itu sendiri). Akibat: reset pekerjaan A yang dipakai bundle (`ref_pekerjaan`) oleh B → expanded B stale, "reset berhasil" senyap.
  - **TA-18/D-05 (master→project):** CUSTOM dengan `ref_ahsp` → komponen master disalin komputasional ke `DetailAHSPExpanded`. Signal app `referensi` hanya `rebuild_search_cache()` (`referensi/models.py:18-19`); **tidak ada** mekanisme cari `DetailAHSPProject.ref_ahsp` lalu rebuild expanded / tandai stale. Perubahan/import ulang master → FK tunjuk versi terbaru, expanded tetap versi lama.
- **Model master TIDAK punya `updated_at`** (`AHSPReferensi`/`RincianReferensi`, `referensi/models.py:23/78`) — punya `HistoricalRecords()`. → deteksi revisi master harus **content-hash** atas rincian master (kategori/kode_item/koefisien/satuan/uraian), sesuai pilihan D-05 ("revision/hash"). Pola identik `readiness.source_signature()` (B4 inc-4b, sha1 koef-quant) — **REUSE/sejajarkan**.
- **B4 sudah punya** `DetailAHSPExpanded.source_signature` (signature internal: expanded vs raw project sendiri). B7 butuh sumbu BERBEDA: signature **master** yang disnapshot pada raw bundle saat sync, dibandingkan hash master terkini → `reference_update_available`. Dua signature ini komplementer, jangan dicampur.

**Rencana increment (USULAN — perlu persetujuan owner):**
| Inc | Fokus | Sifat | DoD |
|---|---|---|---|
| **B7a** | Helper `master_reference_signature(ref_ahsp)` (sha1 atas RincianReferensi master, sejajar `source_signature`) + simpan snapshot signature+waktu pada raw bundle (`DetailAHSPProject`: field `ref_snapshot_signature` + `ref_synced_at`, nullable; migrasi add + backfill frozen) | backend + migrasi, additive | signature deterministik; stamped saat expand dari master |
| **B7b** | Deteksi `reference_update_available` di **readiness** (sinyal baru, schema bump `b4.5`): per CUSTOM `ref_ahsp` bandingkan snapshot vs master terkini → entry traceable | backend, additive (tak ubah angka) | sinyal muncul saat master beda; tak ada saat sinkron |
| **B7c** | **TA-03 fix:** panggil `cascade_bundle_re_expansion` setelah reset commit (+ rollback bila gagal, no silent success) | backend, **perbaikan reliabilitas** | reset A → expanded dependent B ikut fresh; test A↔B |
| **B7d** | Aksi sinkronisasi master (endpoint): rebuild expanded dari master terkini, **pertahankan `bundle_quantity` user**, stamp signature baru, **audit old/new** (AT-05 writer) | backend, **risky** (ubah angka expanded — by design, atas aksi user) | expanded = master baru; koef bundle user utuh; audit tercatat |
| **B7e** | Frontend badge "update referensi tersedia" + aksi sync + ringkasan + feedback | frontend (cek Vite vs classic per template) | badge tampil; sync berjalan; non-blocking |

**Catatan risiko & sekuens:** B7a/B7b/B7c backend additive/reliabilitas → **bisa mulai sekarang** (DB up). B7d mengubah nilai expanded (atas aksi user eksplisit, bukan senyap) → kawal audit + preservasi `bundle_quantity` + test. B7e cek bundling template (Template AHSP = classic? Jadwal = Vite). **Tahapan-mode tak relevan di sini.** AT-05 (audit-writer observability) = **RETAIN** (dipakai B7d).

**Pertanyaan keputusan owner sebelum GO:**
1. Setuju field baru di `DetailAHSPProject` (`ref_snapshot_signature`, `ref_synced_at`) untuk menyimpan revisi master per raw bundle? (alternatif: tabel terpisah — lebih berat, D-05 bilang "pada raw bundle").
2. Sinyal `reference_update_available` masuk ke **readiness** (`b4.5`) atau channel terpisah? (rekomendasi: readiness, konsisten 5 consumer).
3. Sync = **aksi manual user** (badge→tombol) sesuai D-05, konfirmasi? (BUKAN cascade otomatis saat master berubah — D-05 melarang perubahan senyap).
4. Mulai B7a–B7c (backend additive + TA-03) dulu, B7d/e setelah review? (pola WP berisiko = increment hijau bertahap).

#### inc-B7 — DESAIN PENUH (2026-06-16, MENUNGGU PERSETUJUAN OWNER)

**Keputusan owner terkonfirmasi:** Q3 = **sync = aksi manual user** (badge→tombol; tak ada perubahan senyap, sesuai D-05). Q4 = **rancang penuh B7a–e dulu** sebelum tulis kode. Q1 (storage) & Q2 (channel) → owner minta uraian trade-off + contoh kasus (di bawah; rekomendasi ditandai).

**Stamp site terverifikasi:** `_populate_expanded_from_raw` (`services.py:1758`) — loop raw `DetailAHSPProject`; baris `kategori='LAIN' & ref_ahsp_id` (`:1796`) di-expand via `expand_ahsp_bundle_to_components(ref_ahsp_id)` (`:1589`, baca `RincianReferensi`). Di titik inilah snapshot master di-stamp. Karena fungsi ini dipanggil tiap save/reset → snapshot SELALU = master saat build terakhir; stale terdeteksi bila master berubah SETELAH itu. Semantik benar.

---

##### Q1 (storage revisi master) — trade-off + contoh kasus

**Opsi A — field di `DetailAHSPProject`** (`ref_snapshot_signature` CharField(40,null), `ref_synced_at` DateTime(null)); hanya bermakna saat `ref_ahsp_id` set.
**Opsi B — tabel terpisah** (mis. `BundleReferenceSnapshot`: bundle_detail FK, signature, synced_at, [opsional history]).

| Dimensi | Opsi A (field di raw bundle) | Opsi B (tabel terpisah) |
|---|---|---|
| Kepatuhan D-05 | **Literal** ("simpan revision/hash pada raw bundle") | Menyimpang ("pada raw bundle") |
| Query readiness | Tanpa join — baris `DetailAHSPProject` SUDAH dibaca di loop expansion/readiness | Butuh join per baris bundle |
| Riwayat banyak-versi | Tidak (hanya snapshot terkini) | Bisa (tapi tak dibutuhkan — audit sudah di AT-05) |
| Biaya skema | 2 kolom nullable di tabel besar + backfill | Tabel+FK+lifecycle (cascade delete saat bundle dihapus) |
| Risiko | Minimal (additive) | Over-engineering utk kebutuhan "snapshot terkini == master?" |

**Contoh kasus:** Project punya 3 pekerjaan CUSTOM, tiap-tiap 1 baris bundle `ref_ahsp` → master `A.2.3.1.1`. Master diperbarui (koef berubah).
- *Opsi A:* readiness loop sudah membaca 3 baris `DetailAHSPProject`; bandingkan `ref_snapshot_signature` vs hash master live → 3 baris stale, **tanpa join**.
- *Opsi B:* hasil sama, tapi +1 join + tabel ekstra utk manfaat nol (kita tak butuh riwayat tiap sync — itu domain audit trail).
- *Kapan B menang:* bila kita butuh menyimpan BANYAK snapshot historis per bundle (mis. "tunjukkan 5 sync terakhir"). D-05 TIDAK memintanya; old/new sudah masuk audit trail di B7d.

**REKOMENDASI: Opsi A** (literal D-05, no-join, additive, sejajar pola `DetailAHSPExpanded.source_signature` B4).

---

##### Q2 (channel sinyal `reference_update_available`) — trade-off + contoh kasus

**Opsi A — Readiness (schema bump `b4.5`)**: tambah sebagai sinyal readiness → otomatis muncul di 5 consumer ter-wire (banner advisory non-blocking + autoload).
**Opsi B — channel/endpoint terpisah**: endpoint khusus B7, wiring UI baru per halaman.

| Dimensi | Opsi A (readiness) | Opsi B (terpisah) |
|---|---|---|
| Wiring UI | Nol baru — autoload+banner sudah jalan di 5 halaman | Baru per halaman (fetch+elemen) |
| Konsistensi | Satu tempat "project belum final / sumber belum sinkron" | Dua sistem awareness paralel |
| Biaya | Bump schema `b4.4`→`b4.5` (re-review owner) | Tanpa bump schema readiness |
| Semantik | Stale master = expanded berbasis sumber lama = isu correctness → cocok di readiness (advisory) | Terisolasi, tapi duplikasi mekanisme |
| Aksi sync | Awareness di mana-mana; **tombol sync tetap di Template AHSP** (tempat edit) | Idem (aksi tetap page-specific) |

**Contoh kasus:** User buka **Rekap RAB**. Master di balik 1 bundle CUSTOM mereka diperbarui minggu lalu.
- *Opsi A:* banner readiness yang SUDAH ada menambah 1 baris "1 bundle memakai versi master lama — sinkronkan di Template AHSP" berdampingan dgn missing_price dll. Nol wiring baru. User klik ke Template AHSP → badge+tombol sync (B7e).
- *Opsi B:* Rekap RAB perlu fetch+banner BARU khusus; ulangi tiap halaman → lebih banyak kode + risiko drift.
- *Kapan B menang:* bila update-referensi jadi UX fundamental berbeda (mis. "sync center" lintas-project). Itu lebih berat dari minimum D-05 (badge+aksi).

**Nuansa:** sinyal readiness saat ini bermakna "belum siap/belum final". `reference_update_available` = "pembaruan tersedia" — tetap correctness-relevant (expanded dari sumber lama) & tetap **advisory non-blocking**. Pesan dibedakan nadanya: "pembaruan referensi tersedia" (bukan "data salah").

**REKOMENDASI: Opsi A (readiness `b4.5`)**, aksi sync tetap di Template AHSP.

---

##### Desain increment penuh B7a–B7e (berbasis Opsi A+A+manual)

**B7a — signature + snapshot master (backend + migrasi, additive)**
- `readiness.master_reference_signature(ref_ahsp_id) -> str|None`: sha1 atas `RincianReferensi` master tersortir (`kategori, kode_item, koefisien` quantize 12dp, `satuan_item, uraian_item`), join newline. Deterministik; sejajar `source_signature`. Return None bila master tak ada.
- Field baru `DetailAHSPProject.ref_snapshot_signature` (CharField 40,null), `ref_synced_at` (DateTime,null). Migrasi 0049 add + 0050 backfill frozen: utk baris `ref_ahsp_id` set → stamp signature master terkini + `ref_synced_at=now` (asumsi sinkron saat deploy). Master hilang → null.
- Stamp di `_populate_expanded_from_raw` (`:1796` cabang ref_ahsp): setelah expand, set `detail_obj.ref_snapshot_signature/ref_synced_at` (lazy import, batch save). **Caveat nested master:** signature = master langsung; perubahan master ber-nested (`expand_ahsp_bundle_to_components` rekursi `:1685`) = keterbatasan diketahui → opsi recurse signature di iterasi lanjut (catat).
- DoD: signature deterministik (test) + ter-stamp saat expand + backfill tak error. Tak ubah angka/perilaku.

**B7b — sinyal readiness `reference_update_available` (backend, additive, schema `b4.5`)**
- Di `readiness._compute`: utk tiap `DetailAHSPProject` `ref_ahsp_id` set, bandingkan `ref_snapshot_signature` vs `master_reference_signature(ref_ahsp_id)` live. Beda (dan snapshot non-null) → entry `{pekerjaan_id,kode,uraian,source_table:"DetailAHSPProject",issue:"reference_update_available", ref_ahsp_id, ref_kode}`. snapshot null → diabaikan (legacy, jangan false-positive).
- SCHEMA_VERSION `b4.4`→`b4.5`; tambah ke payload + banner (1 baris advisory: "pembaruan referensi tersedia — sinkronkan di Template AHSP"). Query-budget tetap konstan (prefetch master sig per ref_ahsp unik).
- DoD: sinyal muncul saat master beda, hilang saat sinkron; backward-compat (snapshot null tak memicu); 5 consumer otomatis tampil; test + bump frontend banner test.

**B7c — TA-03 fix: cascade re-expansion saat reset (backend, reliabilitas)**
- Reset-to-reference (`:2899`) saat ini hanya `_populate_expanded_from_raw(target)`. Tambah `cascade_bundle_re_expansion(project, target.id)` setelah commit (pola sama dgn save `:2772`); bila gagal → rollback + pesan generik (no silent success, sejalan WP-B3 atomicity).
- DoD: pekerjaan A direset → expanded dependent B (yg `ref_pekerjaan=A`) ikut fresh; test A↔B reset; tak ada 207/partial.

**B7d — aksi sinkronisasi master (backend, RISKY by-design, atas aksi user)**
- Endpoint `POST api/project/<id>/sync-reference/` (body: pekerjaan_id atau bundle detail_id; atau "semua bundle stale di project"). Atomic (`@transaction.atomic`, atomic_error_response).
- Aksi: rebuild expanded dari master terkini utk bundle target (re-`_populate_expanded_from_raw` pekerjaan ybs → otomatis re-stamp B7a). **Pertahankan `bundle_quantity` user** = koef di `DetailAHSPProject` TIDAK disentuh (hanya expanded/derived dibangun ulang; raw bundle row koef tetap). Audit old/new via AT-05 writer (komponen+signature lama→baru).
- DoD: setelah sync, `reference_update_available` hilang utk bundle itu; `DetailAHSPProject.koefisien` (bundle_quantity) identik pre/post; audit entry tercatat; angka expanded = master baru; test preservasi koef + idempotensi.

**B7e — frontend badge + aksi (frontend; cek bundling per template)**
- Template AHSP (cek classic vs Vite): badge "pembaruan referensi tersedia" per bundle stale (baca readiness `reference_update_available`); tombol "Sinkronkan" → konfirmasi + ringkasan komponen berubah → POST B7d → feedback sukses/gagal → refresh readiness. Non-blocking; escapeHtml semua.
- DoD: badge tampil saat stale; sync jalan; ringkasan akurat; guard test.

**Risiko & sekuens:** B7a/B7b/B7c additive/reliabilitas (DB up → bisa). B7d ubah angka expanded TAPI atas aksi user eksplisit + audit + preservasi bundle_quantity (bukan senyap — patuh D-05). B7e per-template bundling. **Caveat known:** nested-master signature (B7a), dan `ref_pekerjaan` (job-bundle) vs `ref_ahsp` (master-bundle) = dua jenis bundle; B7b/B7d fokus `ref_ahsp` (master), TA-03/B7c menutup `ref_pekerjaan` (intra-project).

**MENUNGGU OWNER:** (1) konfirmasi Q1=Opsi A, (2) Q2=readiness `b4.5`, (3) approve desain B7a–e + caveat nested-master, (4) GO mulai B7a.

**KEPUTUSAN OWNER 2026-06-16: GO** — Q1=Opsi A, Q2=readiness `b4.5`, sync manual, desain disetujui. Mulai B7a.

#### inc-B7a — Master reference signature + snapshot stamping (DONE 2026-06-16)

- `readiness.master_reference_signature(ref_ahsp_id)` — sha1 atas `RincianReferensi` master (kategori, kode_item, koefisien quant-12dp, satuan_item, uraian_item) tersortir deterministik; return None bila master hilang/kosong. Sejajar `source_signature`.
- Field baru `DetailAHSPProject.ref_snapshot_signature` (CharField 40,null) + `ref_synced_at` (DateTime,null). Migrasi **0049** (add) + **0050** (backfill frozen: stamp signature master terkini + synced_at=now utk baris `ref_ahsp_id` set → asumsi sinkron saat deploy, cegah false-positive flood; depend referensi 0024 agar field name final).
- Stamp di `_populate_expanded_from_raw` (`services.py`): kumpulkan `ref_ahsp_rows` di loop, setelah bulk_create expanded → `bulk_update(["ref_snapshot_signature","ref_synced_at"])`. **Koefisien user (bundle_quantity) TIDAK disentuh.**

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-16 | WP-B7 inc-B7a | `tests_wp_b7_reference_sync` | PASS | 8/8: signature deterministik, sensitif koef/komponen-ditambah, None master kosong, independen urutan-insert; stamp saat expand, koef user utuh, non-master tak di-stamp |
| 2026-06-16 | WP-B7 inc-B7a | B4/B3/B6/rekap regresi | PASS | 90/90; `manage.py check` + `makemigrations --check` + `git diff --check` bersih |

**Caveat known (dicatat):** signature = master LANGSUNG; perubahan master ber-nested (`expand_ahsp_bundle_to_components` rekursi) belum tercakup → iterasi lanjut.

#### inc-B7b — Sinyal readiness `reference_update_available` (DONE 2026-06-16, schema `b4.5`)

- `readiness._compute`: utk tiap baris `DetailAHSPProject` `ref_ahsp_id` set, bandingkan `ref_snapshot_signature` (tersimpan) vs signature master live. Beda → entry `{pekerjaan_id, source_detail_id, kode, uraian, ref_ahsp_id, source_table:"DetailAHSPProject", source_page, issue:"reference_update_available"}`. **snapshot null (legacy) atau master hilang/kosong → diabaikan** (anti false-positive). Masuk `affected_pekerjaan`.
- **Query budget DIJAGA:** master signature dihitung dari SATU query `RincianReferensi` (filter `ahsp_id__in`), di-group Python, refactor helper `_master_sig_from_rows` dipakai bersama `master_reference_signature`. Query lama (count) DIGANTI (bukan ditambah) → budget tetap.
- `SCHEMA_VERSION` `b4.4`→`b4.5`. Banner `readiness_banner.js`: baris advisory "X bundle memakai versi master AHSP lama … (sinkronkan di Template AHSP)". 5 consumer otomatis tampil (tak perlu wiring baru).

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-16 | WP-B7 inc-B7b | `tests_wp_b7_reference_sync` + `tests_wp_b4_readiness` | PASS | 57/57: schema b4.5, no-signal-in-sync, **fire saat master dikoreksi in-place (Skenario 1)**, **versi tahunan baru TIDAK memicu (Skenario 2 owner)**, legacy null tak memicu, affected_pekerjaan |
| 2026-06-16 | WP-B7 inc-B7b | frontend `vitest run` | PASS | 270 pass / 25 skip (16 file); banner B7b line + 3 assert; `node --check` OK |
| 2026-06-16 | WP-B7 inc-B7b | check + makemigrations --check + diff --check | CLEAN | b4.4 sweep repo = nol sisa |

**Skenario 2 (versi tahunan baru) terbukti TIDAK memicu** lewat `test_new_yearly_version_does_not_fire` — proyek tetap ter-pin ke versi terpilih; "upgrade versi" = WP terpisah (di luar B7).

#### inc-B7c — Fix TA-03: cascade re-expansion saat reset-to-reference (DONE 2026-06-16)

- `api_reset_detail_ahsp_to_ref` (`views_api.py:2827`): setelah `_populate_expanded_from_raw(pkj)`, tambah `cascade_bundle_re_expansion(project, pkj.id)` **di dalam transaksi atomik yang sama**. Reset pekerjaan A yang dipakai bundle (LAIN `ref_pekerjaan`) oleh B kini ikut me-refresh expanded B (sebelumnya: stale senyap, "reset berhasil").
- **No silent success (konvensi WP-B3):** cascade gagal → `transaction.set_rollback(True)` + respons generik 500 (no `str(e)` leak) → seluruh reset dibatalkan, bukan setengah-jadi. (Lebih kuat dari jalur save yang cascade post-commit.)

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-16 | WP-B7 inc-B7c | `tests_wp_b7_reference_sync` + `tests_template_ahsp_formula_state` | PASS | 37/37: `test_reset_re_expands_dependent_bundle` (A ref_mod dari master, B bundle ref_pekerjaan=A; expanded B dihapus → reset A → cascade rebuild B; koef per-unit RA-19 = 5). check + makemigrations + diff bersih |

#### inc-B7d — Endpoint sync manual master→project (DONE 2026-06-16)

- `api_sync_reference` (`POST api/project/<id>/sync-reference/`, atomik, owner-scoped). Body opsional `pekerjaan_id` (sync 1 pekerjaan) atau kosong (semua bundle stale di project).
- Cari bundle stale (`ref_snapshot_signature` ≠ signature master live; sig master di-cache per ahsp unik). Untuk tiap pekerjaan stale: rebuild expanded via `_populate_expanded_from_raw` (auto re-stamp B7a). **`bundle_quantity` (DetailAHSPProject.koefisien) dipertahankan** — diverifikasi runtime (koef_before==koef_after, else RuntimeError→rollback). Audit old/new komposisi **expanded** (bukan raw — raw tak berubah) via `log_audit` ACTION_UPDATE summary "Sinkronisasi referensi AHSP master".
- No silent success: exception → `set_rollback(True)` + 500 generik. Sync gagal = nol perubahan. D-05: tak ada propagasi senyap (hanya atas aksi user).

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-16 | WP-B7 inc-B7d | `tests_wp_b7_reference_sync` | PASS | 36/36: sync clears `reference_update_available`, rebuild expanded (komponen baru masuk: 1→2), **bundle_quantity user utuh**, audit tertulis, **idempotent** (sync ke-2 count=0), sync-all tanpa pekerjaan_id |
| 2026-06-16 | WP-B7 inc-B7d | B4/B3/template/rekap regresi | PASS | 95/95; check + makemigrations + diff bersih |

#### inc-B7e — Frontend badge + tombol Sinkronkan (DONE 2026-06-16) → WP-B7 SELESAI

- `template_ahsp.html`: data attr `data-endpoint-sync-reference` (url `api_sync_reference`). `template_ahsp.js`: `renderSyncReferenceAction(box, readiness)` dipanggil dari `renderReadiness` — bila `readiness.reference_update_available` non-kosong, tambah tombol **"Sinkronkan referensi"** di bawah banner. Klik → konfirmasi (jumlah bundle + jaminan koef tak berubah) → `POST /sync-reference/` (CSRF) → status "Tersinkronkan N pekerjaan" → `refreshReadiness()` (baris hilang saat sinkron). Gagal → pesan + tombol aktif lagi. Advisory/non-blocking; editor RAW tak perlu reload (hanya expanded berubah).
- Banner awareness (B7b) tetap tampil di 5 halaman; **aksi** hanya di Template AHSP (tempat edit), sesuai D-05.

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-16 | WP-B7 inc-B7e | `readiness_banner.test.js` (+wiring B7e) | PASS | 12/12; guard: renderSyncReferenceAction + reference_update_available + endpoints.syncReference + POST + Tersinkronkan |
| 2026-06-16 | WP-B7 inc-B7e | frontend `vitest run` penuh + `manage.py check` (URL resolve) | PASS | 271 pass / 25 skip (16 file); `node --check` template_ahsp.js OK; diff bersih |

**WP-B7 SELESAI (a–e).** D-05 reference-sync + user-value protection terimplementasi penuh: deteksi (B7a/b) + reliabilitas reset (B7c) + aksi sync manual (B7d) + UI (B7e). Skenario-1 (perubahan in-place versi terpilih) ditangani; Skenario-2 (versi tahunan baru) sengaja tak memicu (proyek ter-pin). **Caveat known:** nested-master signature = iterasi lanjut; "upgrade versi tahunan" = WP terpisah bila diinginkan. **Sisa Fase 1: B8 (tipe LAIN D-08), B9 (bundle limits D-10), B10 (actual_cost legacy bila ada).**

---

### WP-B8 — Tipe LAIN: pisahkan OTHER_DIRECT vs WORK_BUNDLE (SURVEI 2026-06-16, MENUNGGU REVIEW OWNER)

**Status:** IN PROGRESS (survei + rencana, BELUM ada perubahan kode). **Sumber:** keputusan owner **D-08** (final, doc 18 §1044-1095). **Dependency:** WP-B3 (atomic save, DONE), WP-B7 (ref handling, DONE).

**Masalah (D-08):** kategori `LAIN` punya DUA makna bercampur — (a) **bundle** yang harus di-expand (punya `ref_ahsp`/`ref_pekerjaan`), dan (b) **biaya lain langsung** tanpa referensi. **Inkonsistensi terverifikasi:**
- Save (`api_save_detail_ahsp_for_pekerjaan`, `views_api.py:2666-2677`): LAIN tanpa ref → **DITOLAK** ("invalid bundle", tidak masuk expanded). → user TIDAK bisa menambah "Biaya Lain Langsung".
- `_populate_expanded_from_raw` (`services.py:1927-1941`): LAIN tanpa ref → **diteruskan** sebagai direct (pass-through). → dua jalur ekspansi beda perilaku untuk input yang sama.

**Keputusan owner D-08 (final):** pisahkan dua makna secara **aditif**:
- `OTHER_DIRECT` ("Biaya Lain Langsung"): tanpa ref, WAJIB punya Harga Item, diteruskan seperti direct.
- `WORK_BUNDLE` ("Pekerjaan Gabungan"): WAJIB tepat satu referensi (AHSP atau PROJECT_JOB), di-expand.
- Struktur: `kategori` (TK/BHN/ALT/LAIN tetap) + `item_type` (DIRECT/OTHER_DIRECT/WORK_BUNDLE) + `reference_type` (null/AHSP/PROJECT_JOB). UI: 3 aksi terpisah. Migrasi: LAIN+ref→WORK_BUNDLE, LAIN tanpa ref→OTHER_DIRECT.

**Fakta struktur (terverifikasi):** `DetailAHSPProject.harga_item` = FK NOT NULL → OTHER_DIRECT pasti punya Harga Item (aturan terpenuhi struktural). `ref_ahsp`/`ref_pekerjaan` nullable + CheckConstraint (`bundle_ref_only_for_lain`, `bundle_ref_exclusive`) sudah menjamin "≤1 ref & hanya LAIN".

**KEPUTUSAN DESAIN UNTUK OWNER:**
1. **`item_type` DISIMPAN (kolom) atau DITURUNKAN (derived)?** Aturan deterministik dari keberadaan ref (LAIN+ref=WORK_BUNDLE, LAIN tanpa ref=OTHER_DIRECT, non-LAIN=DIRECT).
   - **Derived (REKOMENDASI):** tanpa kolom/migrasi; satu sumber kebenaran = keberadaan ref; helper `item_type_of(row)` + expose di API/serializer. Paling aditif, nol risiko desync. UI 3-aksi tetap jalan (aksi menentukan apakah ref dilampirkan).
   - **Stored:** kolom `item_type`/`reference_type` eksplisit (sesuai teks D-08). Lebih eksplisit untuk intent TAPI butuh migrasi + jaga sinkron dgn ref (risiko desync).
2. **Scope B8 sekarang:** backend (terima OTHER_DIRECT di save + samakan dua jalur ekspansi + expose item_type) saja, atau termasuk UI 3-aksi (`template_ahsp.js`)? UI lebih besar; bisa B8d terpisah/menyusul.
3. **B9 (bundle limits D-10)** terpisah dari B8 (MAX_BUNDLE_LEVELS=4 + MAX_EXPANDED_COMPONENTS) — konfirmasi dikerjakan setelah B8.

**Rencana increment (USULAN, perlu persetujuan):**
| Inc | Fokus | Sifat | DoD |
|---|---|---|---|
| **B8a** | Helper kanonik `item_type_of(detail)` (+ `reference_type`) di backend; expose di API detail/serializer | backend, additive, derived | type benar utk DIRECT/OTHER_DIRECT/WORK_BUNDLE |
| **B8b** | Save: LAIN tanpa ref → **terima sebagai OTHER_DIRECT** (pass-through ke expanded, seperti `_populate`), bukan ditolak; WORK_BUNDLE tetap wajib tepat 1 ref (validasi+pesan). Samakan 2 jalur ekspansi | backend, **ubah perilaku** (enable input baru) | OTHER_DIRECT tersimpan+masuk expanded; WORK_BUNDLE tanpa ref ditolak jelas |
| **B8c** | Consumer/label: pastikan rekap/kebutuhan perlakukan OTHER_DIRECT expanded sbg biaya langsung (sudah, krn pass-through); label humanis "Biaya Lain Langsung"/"Pekerjaan Gabungan" di API/export | backend, additive | label benar; angka data lama tak berubah |
| **B8d** | UI Template AHSP: 3 aksi tambah terpisah + label tipe (`template_ahsp.js` classic) | frontend | 3 aksi berfungsi; OTHER_DIRECT bisa dibuat via UI |

**Dampak:** B8b **mengaktifkan input yang sebelumnya ditolak** (OTHER_DIRECT) — menambah kemampuan, tak mengubah angka data lama (LAIN+ref tetap WORK_BUNDLE/expanded). Data lama tetap valid (derived type).

**KEPUTUSAN OWNER 2026-06-16: GO** — #1 item_type **DERIVED** (tanpa kolom), #2 **backend dulu (B8a–c), UI B8d menyusul**, #3 B9 setelah B8.

#### inc-B8a/b/c — Backend tipe LAIN (DONE 2026-06-16)

- **B8a** `services.item_type_of(kategori, ref_ahsp_id, ref_pekerjaan_id)` + `reference_type_of(...)` + konstanta `ITEM_TYPE_*`/`REFERENCE_TYPE_*` + `ITEM_TYPE_LABELS` (derived, tanpa kolom). Di-expose di `build_detail_ahsp_payload`: tiap baris kini punya `item_type`, `item_type_label`, `reference_type`.
- **B8b** `api_save_detail_ahsp_for_pekerjaan` (`views_api.py:2676`): cabang LAIN-tanpa-ref **TIDAK lagi menolak** — diteruskan ke expanded sebagai **OTHER_DIRECT** (pass-through, source_bundle_kode=None, depth=0), sama seperti `_populate_expanded_from_raw` → **dua jalur ekspansi konsisten**. Raw row sudah dapat harga_item via `_upsert_harga_item` (NOT NULL terpenuhi). WORK_BUNDLE tetap di-expand; CheckConstraint jamin ≤1 ref.
- **B8c** label humanis ("Biaya Lain Langsung"/"Pekerjaan Gabungan"/"Komponen Langsung") di payload API. OTHER_DIRECT expanded otomatis dihitung rekap sbg biaya langsung (pass-through, kategori LAIN).

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-16 | WP-B8 inc-a/b/c | `tests_wp_b8_item_type` | PASS | 8/8: derivasi DIRECT/OTHER_DIRECT/WORK_BUNDLE + reference_type, payload expose item_type+label, **save terima LAIN-tanpa-ref sbg OTHER_DIRECT** (raw ref=None, masuk expanded), mixed direct+other tersimpan |
| 2026-06-16 | WP-B8 inc-a/b/c | B3/template/readiness/rekap/B7 regresi | PASS | 138/138 gabungan; check + makemigrations + diff bersih |

#### inc-B8d — UI Template AHSP 3 aksi tambah LAIN (DONE 2026-06-16) → WP-B8 SELESAI

- `template_ahsp.html`: header segmen LAIN — tombol "Baris" tunggal diganti **3 aksi**: **Biaya Lain** (`data-lain-mode="direct"`), **Gabungan AHSP** (`ahsp`), **Gabungan Project** (`job`).
- `template_ahsp.js`: `addLainRow(mode)` set `tr.dataset.refMode`; `enhanceLAINAutocomplete` (a) **skip baris `refMode==='direct'`** (OTHER_DIRECT = input teks biasa, tanpa picker referensi), (b) filter picker per mode (`ahsp`→hanya Master AHSP, `job`→hanya Pekerjaan Proyek, legacy/unset→keduanya). Aksi gabungan dikunci ke pekerjaan custom (toast bila bukan). Tombol baru masuk daftar lock read-only.

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-16 | WP-B8 inc-B8d | `template_ahsp_lain.test.js` (guard baru) | PASS | 4/4: addLainRow direct/ahsp/job, skip direct picker, filter per mode, 3 tombol wired, guard custom; template punya 3 `data-lain-mode` |
| 2026-06-16 | WP-B8 inc-B8d | frontend `vitest run` penuh + `node --check` + `manage.py check` | PASS | 275 pass / 25 skip (17 file); diff bersih |

**WP-B8 SELESAI (a–d).** D-08 terimplementasi: OTHER_DIRECT ("Biaya Lain Langsung") vs WORK_BUNDLE ("Pekerjaan Gabungan") eksplisit, item_type **derived** (tanpa kolom), dua jalur ekspansi konsisten, UI 3-aksi. Perangkap save LAIN-tanpa-ref tertutup; angka data lama tak berubah.

---

### WP-B9 — Batas kedalaman & ukuran bundle (D-10)

**Sumber:** keputusan owner **D-10** (final, doc 18 §1118-1153). **Dependency:** WP-B7/B8 (expansion paths).

**Survei:** kedua jalur ekspansi (`expand_bundle_to_components` ref_pekerjaan + `expand_ahsp_bundle_to_components` ref_ahsp) memakai `MAX_DEPTH = 2` ("≈3 level"). Circular sudah ditolak (`check_circular_dependency_pekerjaan` + visited-set per jalur). Belum ada cap jumlah komponen. `validate_bundle_reference` (save-time) cek circular+existence.

#### inc-B9a — Server guards (DONE 2026-06-16)

- Konstanta modul `services.MAX_BUNDLE_LEVELS = 4`, `MAX_BUNDLE_DEPTH = 3` (depth mulai 1 → 4 level pekerjaan: A→B→C→D valid, A→B→C→D→E ditolak), `MAX_EXPANDED_COMPONENTS = 500`.
- Kedua jalur ekspansi: guard depth pakai `MAX_BUNDLE_DEPTH` (pesan "maks 4 level pekerjaan") + cap **stop-segera** `len(result) > MAX_EXPANDED_COMPONENTS` → ValueError. Berlaku untuk SEMUA jalur (UI save, import/clone populate, maintenance rebuild) krn semuanya lewat 2 fungsi ini. Circular tetap ditolak (existing).

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-16 | WP-B9 inc-B9a | `tests_wp_b9_bundle_limits` | PASS | 4/4: 4 level OK, 5 level ditolak ("kedalaman"), component cap (patch=2) ditolak ("batas"), konstanta=4/3 |
| 2026-06-16 | WP-B9 inc-B9a | B7/B8/template/rekap regresi | PASS | 78/78; check + diff bersih; tak ada test lama yang mem-pin depth lama |

**Catatan nilai:** `MAX_EXPANDED_COMPONENTS = 500` = default aman (tunable; AHSP normal jauh di bawah ini). Owner boleh setel bila perlu.

**SISA B9b (opsional, UX):** endpoint prospective validation ringan (`valid/depth/estimated_component_count/reference_chain/reason`) saat user memilih referensi di UI + wiring client. **Must-have D-10 (guard server) SUDAH terpenuhi** — over-deep/over-besar ditolak saat save dengan pesan jelas; B9b hanya memajukan feedback ke saat-pilih (nice-to-have, sejajar pola "UI menyusul").

**KEPUTUSAN OWNER 2026-06-16:** WP-B9 = **DONE** (guard server = inti D-10). **B9b DEFER → WP-P (integrasi per-halaman)** bersama feedback referensi UI lain. Lanjut WP-B10.

---

### WP-B10 — Legacy Actual Cost Mapping (D-10 §B10; JDW-05)

**Sumber:** JDW-05, JDW-13A. **Status:** `IMPLEMENT/DEFER` berdasarkan inventory.

**INVENTORY (terverifikasi):** `actual_cost` HANYA ada di `PekerjaanProgressWeekly` (model kanonik, migrasi 0026) — **tidak ada field actual_cost legacy terpisah** (bukan di PekerjaanTahapan/TahapPelaksanaan/Project). → **bagian "legacy mapping migration" = `NO MIGRATION REQUIRED`.**

**Defek nyata (JDW-05):** `api_reset_progress` mode=`actual` (`views_api_tahapan_v2.py:1030`) men-nol-kan `actual_proportion` TAPI **membiarkan `actual_cost`** → biaya aktual yatim (realisasi 0 tapi biaya tetinggal). `reset_project_progress` (hapus-semua) AMAN (hapus baris weekly utuh).

#### inc-B10 — Fix reset actual + inventory (DONE 2026-06-16)

- `api_reset_progress` mode=`actual` kini juga set `actual_cost=None` (update_fields += actual_cost). Mode=`planned` TIDAK menyentuh actual_cost (planned cost tak berubah saat actual dibersihkan).
- Copy/import: JSON exporter lama (deprecated) tak membawa `actual_cost` → salinan mulai konsisten (actuals kosong); tak ada penyalinan actual_cost tanpa actual_proportion.

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-16 | WP-B10 inc-B10 | `tests_wp_b10_actual_cost` | PASS | 2/2: reset actual → actual_cost=None + planned utuh; reset planned → actual_cost & actual_proportion utuh |
| 2026-06-16 | WP-B10 inc-B10 | V2 reset/security/change-status regresi | PASS | 16/16; diff bersih |

**DoD terpenuhi:** tak ada actual cost yatim setelah reset; planned cost tak berubah saat actual dibersihkan; legacy mapping = NO MIGRATION REQUIRED (tak perlu migrasi/dry-run). **WP-B10 SELESAI.**

---

#### ⚑ STATUS FASE 1 (otoritatif, 2026-06-16) — baca ini untuk menghindari kebingungan

**Fondasi BACKEND shared SELESAI & 100% test hijau** (473 backend OK / 0 gagal, 275 frontend). **11 dari 12 WP DoD penuh: A1·A2(report-only)·B1·B2·B3·B4·B5·B7·B8·B9·B10.**

**WP-B6 = SATU-SATUNYA yang belum 100%** (DoD 3/5):
- ✅ Backend SSOT canonical (B6a builder, B6b/c timeline weekly+4-minggu+unscheduled, B6f-1 snapshot scope) → **Rekap Kebutuhan/RAB/Kurva-S server AKURAT**.
- ⬜ **B6d** (JS tak recompute week + stop auto-regenerate senyap) + **B6e** (contract test JS↔Python) = **frontend Jadwal, Vite bundle (KF-06)** → **dikerjakan di WP-P7 (Jadwal)**, bukan WP-P8. Bukan defek correctness (JS↔Python terverifikasi konsisten + regenerate no-data-loss); = hardening UI + parity guard.
- ⬜ **B6f-2** `api_rekap_kebutuhan_weekly` (orphan, tanpa consumer) → cleanup di WP-P8 (Rekap Kebutuhan).

**Defer lain (owner-sanctioned, non-blocking, tercatat):** A2 CSP enforcement (milestone-2), B5 export-perf (DEC-B5-DEFER), B9b prospective-validation UI (→WP-P), B3 DB CheckConstraint koef (follow-up migrasi; validasi app-level sudah jalan).

**Konsekuensi keberlanjutan:** TIDAK ada yang memblok Fase 2. WP-P1 (B1/B3/B4 ✓), WP-P2 (B3/B4/B7/B8/B9 ✓) tak butuh Jadwal JS. B6d/e tuntas otomatis saat WP-P7. Backend SSOT sudah benar → consumer hilir akurat tanpa menunggu B6d/e.

→ **Fase 1 dianggap cukup untuk MEMULAI Fase 2** (B6d/e diserap WP-P7).

---

## FASE 2 — Integrasi Per-Halaman

### WP-P1 — Harga Items (SURVEI 2026-06-16, MENUNGGU REVIEW OWNER)

**Dependency:** B1/B3/B4 (DONE). **Tindakan:** REPLACE + REMOVE. **Sumber:** HI-01..16 + B-2 (JSON paket data).

**Status finding (apa yang SUDAH ditutup Fase 1 vs SISA):**
| Finding | Status |
|---|---|
| HI-01 null→0 | ✅ DONE (UF-011 frontend + backend null-preserve) |
| HI-06 harga negatif | ✅ DONE (WP-B3 inc-3, validate ≥0) |
| HI-09 multi-tab LWW | ✅ reconciled (B-1 atomic LWW) |
| **HI-02** conversion+harga bukan 1 transaksi | ⬜ SISA — endpoint apply-conversion atomik |
| **HI-03** export ≠ calculation (adapter pakai market/factor) | ⬜ SISA — export satuan dasar = `harga_satuan` + rekonsiliasi/warning |
| **HI-04** profile tak dimuat ulang di editor | ⬜ SISA — bootstrap `conv` di payload / fetch saat load |
| **HI-05** validasi conversion API lemah | ⬜ SISA — strict schema (negatif, method whitelist, full_clean, generic 400) |
| **HI-07** bulk paste campur base/market | ⬜ SISA — pisah alur paste + preview |
| **HI-08** localStorage tak project-scoped | ⬜ SISA — **hapus fallback localStorage konversi** (server=SSOT) |
| **HI-12** scope page vs export beda | ⬜ SISA — verifikasi/selaraskan |
| **HI-16** dead/drifted code | ⬜ SISA — hapus (bukan perbaiki) |

**Survei kode (terverifikasi):**
- **Dua jalur konversi** = akar HI-02: (a) modal konversi simpan via `api_save_conversion_profile` (`views_api.py:3245`, profil SAJA, tak hitung/simpan harga_satuan); (b) main save `api_save_harga_items` kirim `conversions[]` (`harga_items.js:693`). Profil & harga dasar bisa divergen (HI-02).
- **localStorage** konversi: prefill `harga_items.js:360` + simpan `:1033` (`lsk(kode)` tanpa project → HI-08). WP-P1 = hapus.
- **HI-05**: `api_save_conversion_profile` parse longgar (negatif→default, tanpa full_clean, method bebas).
- **HI-03**: `HargaItemsAdapter` pilih `market_price/factor_to_base` bila profil ada; Rincian/Rekap baca `harga_satuan` → dokumen Harga bisa beda RAB.
- **HI-04**: `build_harga_items_payload` belum kirim `conv` → editor modal kosong di device baru.
- **JSON report** Harga (B-2): JSON Harga/RAB/Kebutuhan dipensiun jadi laporan; perlu cek menu format Harga Items.

**Rencana increment (USULAN, perlu persetujuan):**
| Inc | Fokus | Sifat | Finding |
|---|---|---|---|
| **P1a** | Strict validation `api_save_conversion_profile` (tolak negatif/overflow, whitelist method, full_clean, generic 400) | backend, additive-safety | HI-05 |
| **P1b** | Endpoint **apply-conversion atomik**: validasi profil → hitung `harga_satuan` server-side → simpan profil + harga 1 transaksi; **manual override harga → hapus profil** | backend, **ubah perilaku** | HI-02 |
| **P1c** | Bootstrap profil di `build_harga_items_payload` (`conv` per item via select_related) → editor isi ulang | backend, additive | HI-04 |
| **P1d** | Export Harga: satuan dasar = `harga_satuan` (SSOT), hasil profil = rekonsiliasi + warning bila beda; selaraskan scope page/export | backend, **ubah export** | HI-03, HI-12 |
| **P1e** | Bulk paste: pisah base-price vs market-conversion + preview/konfirmasi | frontend | HI-07 |
| **P1f** | Hapus fallback localStorage konversi; pensiunkan JSON report Harga; hapus dead code | frontend + cleanup | HI-08, HI-16, B-2 |

**KEPUTUSAN UNTUK OWNER:**
1. **HI-02 apply-conversion**: endpoint baru terpisah, atau fold ke main save (`conversions[]` sudah ada) jadi atomik di sana? (rekомendasi: **fold ke main save** — satu tombol Simpan, satu transaksi; modal hanya mengisi nilai, tak commit sendiri).
2. **HI-03 export**: konfirmasi "satuan dasar selalu `harga_satuan`, profil = rekonsiliasi + warning" (selaras B5 server-authoritative).
3. **Manual override → hapus profil**: konfirmasi (user isi harga dasar manual ⇒ profil konversi dibuang, biar tak ada dua sumber).
4. **Scope/urutan**: backend dulu (P1a–d), UI (P1e/f) menyusul? (pola Fase 1).

**Dampak:** P1b/P1d mengubah perilaku harga/export (financial) → kawal hati-hati + test parity. P1a/c additive.

**KEPUTUSAN OWNER 2026-06-16 (arsitektur presedensi harga — Model A LOCKED):** `harga_satuan` = **SSOT tunggal** (dipakai semua perhitungan). `ItemConversionProfile` = **kalkulator + provenance**, BUKAN SSOT kedua (B-5). Aturan presedensi = **last-write-wins** ditegakkan: apply konversi → server hitung `harga_satuan = market_price/factor` + simpan profil (provenance); **edit manual → tulis harga_satuan + HAPUS profil** (cegah recompute senyap menimpa edit terbaru). Apply konversi **fold ke main save** (1 tombol Simpan, 1 transaksi). Export satuan dasar = `harga_satuan` + rekonsiliasi/warning. Konfirmasi #2: profil disimpan sbg provenance (bukan dihapus saat apply).

**TEMUAN SEQUENCING (penting):** "manual override hapus profil" TIDAK boleh disimpulkan dari ketiadaan item di `conversions[]` (destruktif — `build_harga_items_payload` dulu tak kirim profil, jadi convStore frontend bisa tak tahu profil ada → page-save bisa hapus profil yang tak pernah dimuat). → **HI-04 (P1c bootstrap) WAJIB sebelum auto-clear**, dan clear harus via **sinyal eksplisit** `clear_conversion` dari frontend, bukan inferensi. Urutan dikoreksi: **P1a → P1c → P1b → P1d → P1e → P1f**.

#### inc-P1a — Strict validation conversion (DONE 2026-06-16, HI-05)

`api_save_conversion_profile` (`views_api.py:3245`): validasi ketat — `parse_strict` tolak (bukan default 0/1) angka invalid/negatif; `factor_to_base` wajib >0; `method` whitelist `METHOD_CHOICES`; `market_unit` wajib string non-kosong; `density/capacity` ≥0; **`full_clean` sebelum save** → overflow DecimalField jadi **400, bukan 500**. Tak persist bila ada error.

#### inc-P1c — Bootstrap profil di payload (DONE 2026-06-16, HI-04)

`build_harga_items_payload`: tiap item kini punya `conv` (profil konversi dari DB, 1 query) atau `null`. Editor bisa isi-ulang modal di device/browser baru. Decimal di-string-kan. **Prasyarat aman utk P1b auto-clear.**

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-16 | WP-P1 inc-a/c | `tests_wp_p1_harga_items` | PASS | 10/10: validasi (negatif/zero-factor/invalid/method/non-string-unit/density/overflow→400) + payload expose conv (none/terisi) |
| 2026-06-16 | WP-P1 inc-a/c | B3/B4 regresi | PASS | 74/74; check + diff bersih |

#### inc-P1b (BACKEND) — Atomic conversion apply di main save (DONE 2026-06-16, HI-02 + Model A + HI-07 server-math)

`api_save_harga_items` kini proses `conversions[]` (sebelumnya DIABAIKAN): validasi penuh (item allowed, market_unit teks, market_price≥0, factor>0, method whitelist, density/capacity≥0, `full_clean`→overflow 400) → **server hitung `harga_satuan = market_price/factor`** (server-authoritative; client price diabaikan utk item ber-konversi → tutup HI-07) → upsert profil + set harga_satuan, **1 transaksi atomik** dgn items[]/markup. Item dgn `clear_conversion:true` (sinyal eksplisit) → set harga manual + **hapus profil** (Model A last-write-wins). Manual TANPA flag → profil tak disentuh (non-destruktif).

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-16 | WP-P1 inc-b (backend) | `tests_wp_p1_harga_items` | PASS | 15/15: conversion→server price 24000(=240000/10), override client-price salah, manual+flag hapus profil, manual tanpa flag pertahankan profil, conversion invalid→atomic 400 |
| 2026-06-16 | WP-P1 inc-b (backend) | B3/B4/rekap regresi | PASS | 95/95; check + makemigrations + diff bersih |

**⚠️ SISA P1b (FRONTEND wiring) — HI-02 belum tertutup END-TO-END:** modal konversi `harga_items.js` MASIH commit ke endpoint terpisah `api_save_conversion_profile` (`:1039`) dan belum kirim `conversions[]`/`clear_conversion` via main save. Backend jalur atomik sudah SIAP & teruji, tapi UI belum memakainya. **Frontend P1b/P1f:** (a) modal stage ke convStore (jangan commit sendiri), (b) main save kirim `conversions[]`, (c) edit manual baris ber-profil kirim `clear_conversion`, (d) hapus localStorage (HI-08) + setop pakai endpoint modal lama (dipensiun). Sampai itu, jalur lama (non-atomik) masih aktif.

#### inc-P1d — Export Harga = harga_satuan + rekonsiliasi (DONE 2026-06-16, HI-03/12)

`harga_items_adapter.py`: tabel **Satuan Dasar** kini SELALU pakai `item.harga_satuan` (SSOT yang dibaca Rincian/RAB) — bukan lagi `market_price/factor`. Tabel **Satuan Konversi** jadi **rekonsiliasi**: tampilkan "Harga Beli ÷ faktor = Rp derived", dan **flag ⚠ "override manual"** bila `derived ≠ harga_satuan`. Dokumen Harga tak bisa lagi beda dari RAB. Docstring lama (yang menyuruh pakai market/factor) dikoreksi.
**Catatan (BUKAN HI-03):** `export_manager.py` market unit-mode (Rekap Kebutuhan) menampilkan qty dalam satuan beli (qty/faktor) + harga market — **total tetap** (base-derived) = fitur sah D-09 "satuan beli tak ubah total" → WP-P8, dibiarkan.

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-16 | WP-P1 inc-d | `tests_wp_p1_harga_items` (HargaExport) | PASS | 2/2: base table = 23.500 (harga_satuan) bukan 24.000 (derived); konversi flag "override manual" |
| 2026-06-16 | WP-P1 inc-d | export identity/naming/errors + rekap regresi | PASS | 57/57; check + diff bersih |

#### inc-P1b-wiring + P1f(localStorage) — Frontend Harga Items (DONE 2026-06-16)

`harga_items.js` di-rewire ke Model A, **convStore dinormalisasi ke backend-keys** (market_unit/market_price/factor_to_base/density/capacity_m3/capacity_ton/method):
- **HI-02 e2e:** modal konversi kini **STAGE** ke convStore + `setDirty` (TIDAK lagi commit ke `api_save_conversion_profile` terpisah). Main save kirim **semua** konversi di convStore via `payload.conversions` (backend hitung harga_satuan atomik). Panggilan endpoint terpisah DIHAPUS.
- **HI-04 lengkap:** modal-open prefill kini baca backend-keys → profil dari server (P1c) terisi benar di modal (sebelumnya baca `unit`/`price_market` → kosong).
- **Model A last-write-wins:** user ketik/paste harga di baris ber-profil → `convStore.delete` + `clear_conversion:true` di payload (modal set value programatik TIDAK fire 'input' → aman). Apply konversi → batalkan clear.
- **HI-08:** fallback localStorage konversi DIHAPUS total (prefill + set + helper `lsk`). Server = SSOT.
- **HI-07 (parsial):** paste ber-faktor → stage konversi (server hitung harga benar); paste polos di baris ber-profil → clear. **Preview/konfirmasi base-vs-market = P1e (sisa).**

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-16 | WP-P1 frontend | `tests/harga_items_conversion.test.js` (guard baru) | PASS | 6/6: no conversion-profile/save call, no localStorage/hiConv, conversions backend-keyed dari convStore, no price_market/rememberServer, clear_conversion wiring, stage+setDirty |
| 2026-06-16 | WP-P1 frontend | frontend `vitest run` penuh + `node --check` | PASS | 281 pass / 25 skip (18 file); backend P1 17/17; diff bersih |

**✅ HI-02 TERTUTUP END-TO-END** (modal stage → main save atomik → server hitung). HI-04/HI-05/HI-08 selesai. HI-03/12 selesai (P1d).

#### inc-P1e + cleanup — Paste UX + dead-code (DONE 2026-06-16) → WP-P1 SELESAI

- **P1e (HI-07):** bulk paste di-rewrite — baris **ber-faktor = market paste** → base price **dihitung (market÷factor)** SEBELUM masuk kolom harga (market tak bisa lagi nyangkut sbg base price); baris tanpa faktor = base paste. **Preview + konfirmasi** (`confirmModal`, `formatMessage` auto-escape → XSS-safe) sebelum apply; ringkasan N base / N market / N invalid + contoh 6 baris. Plan dibangun tanpa mutasi, baru diterapkan saat confirm.
- **HI-16 (dead code):** checkbox "Ingat pengaturan"/remember-server (tak lagi dibaca JS) DIHAPUS dari modal → diganti info "tersimpan saat Simpan".
- **B-2 (JSON report):** export Harga = Excel/PDF/Word saja — **tak ada JSON report** (sudah compliant); komentar stale diperbaiki.
- **Orphan endpoint:** `api_save_conversion_profile` (kini UI-orphan) dibuat **Model-A-consistent** (juga set `harga_satuan = market/factor`) + docstring DEPRECATED → kandidat hapus Fase 3.

| Tanggal | WP | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-06-16 | WP-P1 inc-e+cleanup | `tests_wp_p1_harga_items` + `harga_items_conversion.test.js` | PASS | backend 18/18 (incl endpoint sync harga_satuan) + frontend guard 8/8 (paste market÷factor, confirm-before-apply) |
| 2026-06-16 | WP-P1 final | frontend penuh + backend P1/B3/B4/rekap/export | PASS | 283 pass/25 skip; 103/103; check + makemigrations + diff bersih |

**✅ WP-P1 SELESAI.** Checklist HI tertutup: HI-01 (Fase1), HI-02 (e2e), HI-03/HI-12 (P1d), HI-04 (P1c+modal), HI-05 (P1a), HI-06 (Fase1), HI-07 (P1e), HI-08 (localStorage dihapus), HI-09 (Fase1 LWW), HI-16 (dead code). **Model A:** harga_satuan = SSOT tunggal, profil = kalkulator+provenance, last-write-wins, semua jalur (modal/paste/manual/endpoint) konsisten. Orphan-cleanup UI = Fase 3.
