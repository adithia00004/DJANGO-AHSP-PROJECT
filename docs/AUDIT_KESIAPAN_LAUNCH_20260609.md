# Audit Kesiapan Launch & Dead Code — Basis Implementation Plan

**Tanggal:** 2026-06-09
**Branch:** `checkpoint/save-sync-plan-20260608` (verifikasi ulang dari HEAD `e05f0748`)
**Metode:** pemeriksaan source + runtime Docker (`manage.py check`, suite test, baca `production.py`/compose), inventaris file & penanda dead-code.
**Tujuan:** menjadi dasar penyusunan implementation plan menuju launch.
**Pelengkap:** `SISA_PEKERJAAN_DAN_KESIAPAN_PRODUKSI_20260609.md`, `IMPLEMENTATION_PLAN_SAVE_SYNC_20260608.md`, `OPAQUE_ID_CHECKLIST.md`, `AUDIT_UI_UX_20260610.md` (audit lapisan presentasi, temuan U1-U15).

> **Struktur dokumen:** bagian atas = addendum kronologis (2026-06-09 → 2026-06-10); bagian bawah (mulai "1. Ringkasan Eksekutif") = dokumen audit asli 2026-06-09 yang dipertahankan utuh sebagai baseline. Status temuan asli (A/B/C/D/E) yang sudah berubah dikoreksi di addendum, bukan diedit di tempat.

## Addendum Eksekusi 2026-06-09

Temuan A6-A8, C1, D1-D3, dan E1 telah diverifikasi ulang dan ditindaklanjuti:

- Test permission kini membuat subscription aktif agar benar-benar menguji permission decorator.
- Image menggunakan build multi-stage, `npm ci`, app `referensi`, dan lockfile.
- 17.198 file `node_modules/` dan 2.694 file `cleanup_archive/` tidak lagi tracked.
- Sembilan file backup/scratch yang lolos reference scan dihapus dari HEAD.
- Audit Python: 0 vulnerability. Audit npm: 0 critical, 1 high, 5 moderate.
- Residual high adalah `xlsx@0.18.5` tanpa fix registry dan tetap perlu mitigasi/penggantian.
- Image `sha256:42a817f51b22c94198f03a4f4e416a7e4b47976b572a5725887935d70583d6bb` lulus immutable smoke tanpa mount.
- Test final: backend 404 passed; frontend 233 passed.

Redis AOF sempat korup. Setelah backup volume, `redis-check-aof` memangkas 44 byte tail yang rusak; Redis, web, dan worker kembali healthy.

Verdict terbaru tetap **NO-GO public launch**. Blocker tersisa: TLS/domain/secrets/network, restore drill, advisory `xlsx`, CI/UAT, dan Opaque ID sign-off.

## Addendum Verifikasi Ulang 2026-06-10 05:47 WITA (HEAD `4d1f4353`)

Audit ulang independen terhadap HEAD terbaru. Status dokumen di atas sebagian sudah usang:

### Temuan dokumen yang sudah TERTUTUP sejak addendum 2026-06-09

- **Advisory high `xlsx` SELESAI** — dipatch ke `xlsx@0.20.3` via tarball resmi SheetJS CDN (commit `4d1f4353`). Verifikasi: `npm ls xlsx` → 0.20.3; `npm audit` → **0 critical, 0 high, 5 moderate**. Kalimat "Residual high xlsx@0.18.5" di addendum 2026-06-09 tidak berlaku lagi.
- **Cleanup 19.901 file sudah di-commit** (`8483685e`); working tree clean. Bukan lagi staged-only.
- **CI remote HIJAU** di `fc8fdcba` (root cause: `ci.yml` meng-override `DJANGO_SETTINGS_MODULE` → diperbaiki ke `config.settings.test`).
- **L4 lanjutan:** 10 file JS pra-vite 0-referensi dihapus (`f462f20d`); legacy bertanda yang masih diroute/diuji dipertahankan (lihat `docs/L4_DEAD_CODE_REVIEW_20260610.md`).

### Temuan BARU (belum tercatat di audit/checklist sebelumnya)

| ID | Severity | Temuan | Bukti | Rekomendasi |
|---|---|---|---|---|
| F1 | 🟠 Tinggi | **`docker-compose.prod.yml` publish port berbahaya secara default**: `db` → `"${DB_PORT:-5432}:5432"` (semua interface), `flower` → `:5555` tanpa basic-auth | `docker-compose.prod.yml:21,210,218`; overlay Caddy hanya memberi **komentar** "REMOVE host port publishing" (`deploy/docker-compose.prod.proxy.yml:9-15`) — langkah manual rawan terlewat saat deploy L5 | Default-kan bind `127.0.0.1:` atau hapus mapping db/web; tambah `--basic-auth` pada command Flower. Buat default-nya aman, bukan instruksi |
| F2 | 🟡 Sedang | **`DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY}` tanpa guard `:?`** di compose prod (web/celery/beat/flower), tidak konsisten dengan `POSTGRES_PASSWORD`/`REDIS_PASSWORD` yang fail-fast | `docker-compose.prod.yml:83,145,179,213` | Pakai `${DJANGO_SECRET_KEY:?...}` agar gagal saat `compose up`, bukan saat startup guard |
| F3 | 🟡 Sedang | **Mismatch versi Python: CI 3.12 vs image produksi 3.11** — CI hijau tidak sepenuhnya membuktikan perilaku image | `.github/workflows/ci.yml:47` (`3.12`) vs `Dockerfile:2,33` (`python:3.11-slim`) | Samakan versi, atau jalankan job test di dalam image |
| F4 | 🟡 Sedang | **CI belum menjalankan frontend suite & build** (temuan C3 masih open); trigger hanya `push: main/develop` + PR — branch checkpoint tidak otomatis ter-CI | `.github/workflows/ci.yml` hanya `pytest` | Tambah job vitest + `npm run build`; pertimbangkan trigger branch release |
| F5 | 🟢 Rendah | **Bug kecil entrypoint**: `pg_isready ... -U postgres` hardcoded, bukan `$POSTGRES_USER` | `docker-entrypoint.sh:21` | Ganti ke `-U "$POSTGRES_USER"` sebelum kredensial produksi memakai user lain |
| F6 | 🟢 Rendah | **Runtime image meng-install `git`** (kemungkinan tidak diperlukan; bloat + attack surface kecil) | `Dockerfile:48` | Hapus dari stage runtime bila tidak dipakai |
| F7 | 🟢 Rendah | **`.env.pgbouncer` ter-track** — isi diverifikasi hanya template placeholder (aman), tapi namanya memicu alarm scanner | `git ls-files` | Rename ke `.env.pgbouncer.example` |
| F8 | 🟢 Info | **5 advisory moderate npm tersisa** = `uuid<11.1.1` via `exceljs` + tooling transitive; `npm audit fix --force` akan downgrade `exceljs` ke 3.4.0 (**breaking — jangan dijalankan**) | `npm audit` 2026-06-10 | Defer sadar-risiko; tunggu rilis exceljs yang menaikkan uuid |

### Yang diverifikasi ulang dan terkonfirmasi masih benar

- `.dockerignore` bersih (A7/A8 tertutup); Dockerfile multi-stage + `npm ci` + dist-only sesuai klaim L1.
- `node_modules/` & `cleanup_archive/` untracked (0 file); tidak ada `.bak/.backup/.old` ter-track; tidak ada secret nyata ter-track (hanya file example/template).
- **A2/A3 masih berlaku**: stack berjalan saat audit = mode dev; `docker ps` → web `0.0.0.0:8000`, PostgreSQL `0.0.0.0:5432`, Flower `0.0.0.0:5555` terpublish. (Verifikasi internal container tidak dilakukan pada sesi ini; bukti = port publishing + dokumen sebelumnya.)

**Verdict 2026-06-10: tetap NO-GO public launch.** Blocker tersisa: L5 (TLS/domain/secrets — scaffolding siap), L6 (backup terjadwal + restore drill — script siap), L7 (browser UAT + Opaque ID sign-off; CI sudah hijau), L8 GO/NO-GO. `xlsx` **bukan lagi blocker**. Tindakan murah berikutnya: F1+F2 (hardening default compose prod) sebelum eksekusi L5.

---

## Addendum Audit Per-App & Per-Page 2026-06-10 06:20 WITA (HEAD `4d1f4353` + working tree)

Audit mendalam backend + frontend per app dan per halaman. Metode: pemetaan seluruh URL (6 app lokal), inspeksi decorator auth/permission/ownership pada semua views, pemeriksaan middleware & entitlements, inventaris JS per halaman + disiplin XSS, lalu gate verifikasi penuh.

**Gate verifikasi sesi ini (host, `config.settings.test` + Postgres Docker):**
- Backend `pytest`: **404 passed, 40 skipped** (158 detik) — HIJAU.
- Frontend `vitest`: **233 passed, 25 skipped** (11 file test) — HIJAU.

### Temuan baru sesi ini (F9-F13) — F9 KRITIS, LANGSUNG DIPERBAIKI

| ID | Severity | Temuan | Bukti | Status |
|---|---|---|---|---|
| F9 | 🔴 Kritis | **User EXPIRED tidak bisa membayar/renew.** `SubscriptionMiddleware` memblokir semua POST untuk user tanpa write-entitlement, dan `/subscriptions/` TIDAK ada di `EXCLUDED_PATH_PATTERNS` — POST `/subscriptions/payment/create/` (Snap.js) terblokir 403 `SUBSCRIPTION_EXPIRED`. User yang langganannya habis (persis yang harus membayar) tidak bisa checkout. Tidak tertangkap test karena test payment memakai `RequestFactory` yang **melewati middleware** | `accounts/middleware.py:30-38` + `subscriptions/entitlements.py:128-134` (EXPIRED → WRITE_ACCESS=DENY); test lama `subscriptions/tests.py` (RequestFactory) | **FIXED sesi ini**: `^/subscriptions/` ditambahkan ke exclude list + 2 regression test berbasis test client (middleware aktif): expired user bisa create payment; write di luar `/subscriptions/` tetap terblokir. `subscriptions/tests.py` → 23 passed |
| F10 | 🟡 Sedang | **Export database referensi hanya digate login** — `ExportSingleJobView`/`ExportMultipleJobsView`/`ExportSearchResultsView`/`ExportAsyncView` memakai `LoginRequiredMixin` saja; user trial/expired apa pun bisa mengunduh seluruh AHSP referensi (aset produk), padahal export di `detail_project` digate entitlement Pro | `referensi/views/export_views.py:33,90,168,256` | OPEN — keputusan bisnis: gate dengan entitlement Pro / permission portal sebelum launch |
| F11 | 🟢 Rendah | **`debug_clear_data` ter-route permanen** — menghapus SELURUH data referensi; sudah digate `@permission_required("referensi.import_ahsp_data")` tapi tetap berbahaya operasional di production | `referensi/urls.py:63`, `referensi/views/preview.py:568-606` | OPEN — sarankan gate tambahan `settings.DEBUG` atau superuser-only |
| F12 | 🟢 Rendah | **XSS governance guard hanya meng-cover `volume_pekerjaan.js`** — file lain ber-`innerHTML` banyak (`rekap_kebutuhan.js` 31×, `list_pekerjaan.js` 29×, `rincian_ahsp.js` 18×). Spot-check: semuanya PUNYA helper `esc()` lokal dan dipakai pada interpolasi (bukan vulnerability), tapi tanpa guard allowlist regresi bisa lolos | `detail_project/static/.../tests/xss_governance_guard.test.js` (single-file scope) | OPEN — perluas allowlist test ke JS klasik lain |
| F13 | 🟢 Info | **Unit test frontend terpusat di modul jadwal/volume** — 11 file vitest semuanya untuk gantt/grid/kurva-s/formula/XSS; JS halaman klasik (list_pekerjaan, harga_items, rekap_*, rincian_*, dashboard, referensi import UI) tanpa unit test, dimitigasi test backend + rencana browser UAT (L7) | inventaris `*.test.js` | OPEN — terima sebagai risiko sadar; browser UAT L7 wajib menyentuh halaman ini |

Perbaikan lain yang diterapkan sesi ini (dari temuan 2026-06-10 pagi): **F1** (db/web/flower kini default bind `127.0.0.1` via `DB_BIND`/`WEB_BIND`/`FLOWER_BIND`; Flower wajib `--basic-auth`) dan **F2** (`DJANGO_SECRET_KEY` kini guard `:?` di keempat service) di `docker-compose.prod.yml` — tervalidasi `docker compose config`. `.env.production.example` diperbarui.

### Penilaian per app

| App | Halaman/Endpoint | Backend | Frontend | Test | Nilai |
|---|---|---|---|---|---|
| **pages** | `/` landing, `/pricing/` | Publik by design (TemplateView, tanpa data sensitif) | Statis | 7 test | ✅ Siap |
| **accounts** | (tanpa URL sendiri; auth via `/accounts/` allauth) | `CustomUser` TRIAL/PRO/EXPIRED + properti aktif ter-normalisasi; `SubscriptionMiddleware` write-gating (bug F9 fixed) | — | 25 test | ✅ Siap (pasca F9) |
| **dashboard** | dashboard, project detail/edit/delete/duplicate, upload Excel, mass-edit, bulk delete/archive/unarchive, export xlsx/csv/pdf | 100% `@login_required`; SEMUA query project di-scope `owner=request.user` (`get_object_or_404(..., owner=...)`); bulk ops `@require_POST` | 5 JS klasik (dashboard, formset, mass-edit, resizable, ux) | 29 test | ✅ Siap |
| **detail_project** | 12 halaman web + ±100 API (list/volume/template/harga/rekap/rincian/jadwal/tahapan v1-v2/export/monitoring) | Web views: `@login_required` + `_project_or_404(owner)` semua. API: 77 def / 78 `@login_required` / 75 `_owner_or_404` (2 sisanya memang non-project: list template global & import-create). Tahapan v1 12/12, v2 7/7. Monitoring staff-only; client-metric fail-closed API-key; export async login+rate-limit. Ada guard test khusus `tests_page_security_audit.py` | Jadwal = Vite app modular (satu-satunya entry). Halaman lain JS klasik dengan `esc()` lokal terverifikasi. XSS guard baru cover volume (F12) | 271 test backend + 233 vitest | ✅ Siap (catatan F12/F13) |
| **referensi** | admin portal, database v2, import 3-tier (PDF→Excel→staging→commit), audit dashboard, export, CRUD API | Portal & import digate permission terpusat (`referensi/permissions.py`: portal perms + `import_ahsp_data`); `ImportRateLimitMiddleware`; CRUD/lookup API login+permission | 7 JS klasik (import UI besar di template) | 68 test | ⚠️ Siap bersyarat (F10 export gating, F11 debug endpoint) |
| **subscriptions** | checkout, payment create/finish, webhook Midtrans, pricing redirect | Webhook: signature verified + `select_for_update` idempotent + snapshot durasi immutable; create-payment server-side pricing (amount client diabaikan); staff diblokir checkout. Bug F9 fixed | Snap.js (Midtrans) | 21→23 test | ✅ Siap (pasca F9) |

### Penilaian per halaman utama (jalur pengguna)

| Halaman | Auth/Owner | API pendukung | Frontend | Catatan |
|---|---|---|---|---|
| Landing & Pricing | publik | — | statis | OK |
| Login/Signup (allauth) | rate-limited allauth | — | — | Insiden Redis 2026-06-10 = masalah runtime host, bukan kode (rincian di "Koreksi Silang 08:05" butir 3) |
| Dashboard list/CRUD/upload | login+owner | bulk/export | dashboard.js dkk | OK |
| List Pekerjaan | login+owner | save/tree/upsert + template library | list_pekerjaan.js (esc ✓) | Multi-sumber bug (BUG_REPORT 2026-06-02) sudah FIXED + regression test |
| Volume Pekerjaan | login+owner | volume save/list, parameters/computed+sync (opaque) | volume_pekerjaan.js 7.641 baris + formula engine (tested) + XSS guard | Opaque ID Phase 1-4 done; sisa sign-off Gate D |
| Template/Detail AHSP | login+owner | detail-ahsp get/save/reset, bundle expansion | template_ahsp.js, detail_ahsp_gabungan.js (esc ✓) | Orphan harga auto-cleanup aktif |
| Harga Items | login+owner | harga save/list, orphan list/cleanup | harga_items.js (esc ✓) | SSR-bootstrap anti-flash |
| Rekap RAB / Kebutuhan / Rincian | login+owner | rekap/rincian + export 4-5 format per jenis | rekap_*.js, rincian_*.js (esc ✓) | Export PDF/Excel/Word digate entitlement Pro (`_api_pro_export_required`) |
| Jadwal Pekerjaan (grid/gantt/kurva-S) | login+owner | tahapan v1 (deprecation header) + v2 weekly canonical + chart-data SSoT | Vite bundle (core/grid/chart modules), 11 file test | Jalur paling teruji di frontend |
| Audit Trail & Orphan Cleanup | login+owner | audit-trail, orphaned-items | audit_trail.js, orphan_cleanup.js | OK |
| Referensi: import 3-tier | permission import | staging/commit/repair/export | template-embedded JS | Suffix & shift bugs FIXED (2026-06-02), suite import hijau |
| Referensi: database & portal | permission portal | jobs/items CRUD API | ahsp_database_v2.js | OK |
| Checkout & pembayaran | login (+F9 fix) | create payment (server pricing), webhook signature | Snap.js | Perlu E2E sandbox Midtrans saat UAT (L7) |

### Kesimpulan addendum

Lapisan auth/ownership/permission **konsisten dan rapi di seluruh app** — pola `login_required + owner-scope` hampir 100% dengan guard test otomatis. Temuan berarti satu-satunya yang kritis (F9, monetisasi) **sudah diperbaiki + regression test** di sesi ini. Sisa pekerjaan menuju launch tidak berubah: **L5** (deploy TLS/secrets nyata), **L6** (backup terjadwal + restore drill), **L7** (browser UAT semua halaman di tabel atas + E2E Midtrans sandbox + Opaque Gate D sign-off), plus keputusan F10 (gating export referensi). Verdict: **NO-GO publik sampai L5-L7 selesai; kode aplikasi sendiri dinilai launch-ready** dengan catatan F10-F13. *(Revisi wording 11:09, hasil review eksternal: istilah yang tepat = **feature-complete; layak release candidate setelah gate tersisa ditutup** — F10/F11/F14 + UAT masih open, CI saat itu belum meng-cover frontend.)*

---

## Addendum Rincian Per-Halaman 2026-06-10 06:28 WITA

Detail audit setiap halaman: akses, API pendukung, frontend (file + ukuran + disiplin XSS), cakupan test, dan status. Melengkapi tabel per-app di addendum 06:20.

### A. detail_project — 12 halaman

Semua halaman: `@login_required` + `_project_or_404(owner=user, is_active=True)`; cache `no-store` via `DetailProjectNoStoreMiddleware` (teruji `tests_page_cache_headers.py`); guard keamanan lintas-halaman `tests_page_security_audit.py`; CSRF export teruji `tests_export_csrf.py`.

#### 1. List Pekerjaan — `/detail_project/<id>/list-pekerjaan/`
- **API:** save/tree/upsert + Template Library (7 endpoint: list/detail/create/import/delete/export/import-file) + export JSON.
- **Frontend:** `list_pekerjaan.js` (3.078 baris) + modul core (`http/format/toast/keys`), `esc()` ✓.
- **Test:** `tests_list_pekerjaan_upsert_drag_drop`, `tests_list_pekerjaan_upsert_validation`, `tests_list_pekerjaan_export`, `tests_template_library_api`, `tests_import_multi_source_regressions`.
- **Catatan:** bug multi-sumber (BUG B, 2026-06-02) FIXED + regression. Follow-up minor: tampilkan `sumber` AHSP di UI. **Status: ✅ siap.**

#### 2. Volume Pekerjaan — `/detail_project/<id>/volume-pekerjaan/`
- **API:** volume save/list, parameters CRUD+sync, computed-parameters+sync (opaque `bp_N`/`cp_N`, 409 conflict), formula state, export 4 format.
- **Frontend:** `volume_pekerjaan.js` (7.641 baris — terbesar) + `vol_formula_engine` + `volume_runtime` + `numeric` patch; SSR-bootstrap anti-flash; XSS governance allowlist khusus file ini.
- **Test:** backend `tests_volume_pekerjaan_save_api`, `tests_volume_formula_owner_guard`, `tests_formula_server_validation`, `tests_formula_integration`, `tests_phase1_opaque_api`, `tests_volume_export_adapter`; vitest `vol_formula_engine`, `shared_param_store`, `formula_adapter`, `xss_governance_guard`.
- **Catatan:** Opaque ID Phase 1-4 done; sisa Gate D sign-off + test M5 (perf 100+ param). **Status: ✅ siap (pending sign-off).**

#### 3. Template AHSP — `/detail_project/<id>/template-ahsp/` (+ alias legacy `detail-ahsp`)
- **API:** detail-ahsp get/save/reset-to-ref per pekerjaan, formula state; orphan harga auto-cleanup saat save.
- **Frontend:** `template_ahsp.js` (2.442) + shared param modules (`param_store`, `formula_adapter`, `param_sidebar_editor`, `formula_editor_modal`), `esc()` ✓; SSR-bootstrap.
- **Test:** `tests_template_ahsp_formula_state`, `tests_template_ahsp_ui_regressions`, `tests_orphan_autocleanup`.
- **Status: ✅ siap.**

#### 4. Harga Items — `/detail_project/<id>/harga-items/`
- **API:** harga save/list + export 5 format (csv/pdf/word/xlsx/json); export non-CSV digate entitlement Pro.
- **Frontend:** `harga_items.js` (1.241) + numeric, `escapeHtml` ✓; SSR-bootstrap.
- **Test:** `tests_harga_items_save_api`, `tests_harga_items_export`, `tests_item_ssot`.
- **Status: ✅ siap.**

#### 5. Orphan Cleanup — `/detail_project/<id>/orphan-cleanup/`
- **API:** orphaned-items list + cleanup. **Frontend:** `orphan_cleanup.js` (209). **Test:** `tests_orphan_autocleanup`.
- **Catatan:** kini safety-net manual (auto-cleanup sudah berjalan saat save Detail AHSP). **Status: ✅ siap.** *(Revisi 08:05: ⚠️ catatan U14 — dimaksudkan admin-only tapi belum digate role; lihat Koreksi Silang)*

#### 6. Audit Trail — `/detail_project/<id>/audit-trail/`
- **API:** audit-trail (read-only), change-status, source-change ack. **Frontend:** `audit_trail.js` (220). **Test:** `tests_change_status_sync`, `tests_data_retention`.
- **Status: ✅ siap.** *(Revisi 08:05: ⚠️ catatan U14 — dimaksudkan admin-only tapi belum digate role; lihat Koreksi Silang)*

#### 7. Rincian AHSP — `/detail_project/<id>/rincian-ahsp/` (+ alias legacy `detail-ahsp-gabungan`)
- **API:** save gabungan, bundle expansion, export 4 format.
- **Frontend:** `rincian_ahsp.js` (1.602) + `detail_ahsp_gabungan.js`, `esc()` ✓ (spot-check baris 864-942).
- **Test:** `tests_detail_ahsp_gabungan_ui`.
- **Status: ✅ siap.**

#### 8. Rekap RAB — `/detail_project/<id>/rekap-rab/`
- **API:** rekap + pricing project/per-pekerjaan + export 5 format (gate Pro untuk PDF/Excel/Word).
- **Frontend:** `rekap_rab.js` (922) + `ExcelExporter`.
- **Test:** `tests_export_access` (entitlement), `tests_export_csrf`.
- **Status: ✅ siap.**

#### 9. Rekap Kebutuhan — `/detail_project/<id>/rekap-kebutuhan/`
- **API:** rekap-kebutuhan + validate + filters + enhanced + timeline + weekly (procurement) + export 4 format.
- **Frontend:** `rekap_kebutuhan.js` (2.882) + toolbar + vendor `echarts`; `esc()` ✓ (spot-check).
- **Test:** tercakup via suite tahapan/export; tanpa unit test JS sendiri (F13).
- **Status: ✅ siap (cek visual chart saat UAT).**

#### 10. Rincian RAB — `/detail_project/<id>/rincian-rab/`
- **API:** rincian-rab GET + export CSV.
- **Frontend:** **JS inline di template** (±120 baris, satu-satunya halaman tanpa file JS terpisah) — konsistensi minor, bukan risiko.
- **Status: ✅ siap.** *(Revisi 08:05: 🟡 LEGACY — digantikan Rincian AHSP + Rekap RAB, tanpa link masuk; kandidat redirect/deprecation, lihat U15 di `AUDIT_UI_UX_20260610.md`)*

#### 11. Jadwal Pekerjaan — `/detail_project/<id>/jadwal-pekerjaan/` (grid + Gantt + Kurva-S)
- **API:** tahapan v1 (12 endpoint, deprecation header + telemetry) + **v2 weekly canonical** (7 endpoint, `PekerjaanProgressWeekly` SSoT) + chart-data SSoT + kurva-s-harga + regenerate; export 4 format + professional report.
- **Frontend:** **satu-satunya Vite app** — `jadwal_kegiatan_app.js` (4.927) + chunks `core/grid/chart` + `ExportManager`; vendor xlsx/jspdf/html2canvas di chunk terpisah.
- **Test:** vitest 8 file (tanstack-grid, gantt-canvas-overlay, unified-gantt/table, state-manager, week-zero, validation-utils); backend `tests_api_v2_access`, `tests_monitoring_security`.
- **Catatan:** jalur frontend paling teruji; deprecation v1 dimonitor dashboard staff-only. **Status: ✅ siap.**

#### 12. Export Test — `/detail_project/<id>/export-test/`
- **Temuan baru F14 (🟢 Rendah):** halaman uji developer (Phase 4 export) ter-route di production dan dapat diakses semua pemilik proyek (login+owner). Tidak bocor data lintas-user, tapi bukan untuk end-user.
- **Saran:** gate `settings.DEBUG`/staff-only, atau keluarkan dari urls production. **Status: ⚠️ gate sebelum launch (rendah).**

### B. referensi — 6 kelompok halaman

Semua halaman admin dicek `has_referensi_portal_access()` **di dalam body** (redirect `/` + warning) di atas `@login_required`; import digate `@permission_required("referensi.import_ahsp_data")` + `ImportRateLimitMiddleware`.

| Halaman | Akses | Frontend | Test | Status |
|---|---|---|---|---|
| Admin Portal `/referensi/admin-portal/` | login + portal access (in-body) | `admin_portal.js` | — (smoke via suite) | ✅ |
| AHSP Database v2 `/referensi/admin/database-v2/` (+ redirect legacy) | login + portal access; CRUD API jobs/items/stats login-gated | `ahsp_database_api.js`/`v2.js` | `test_ahsp_code`, `test_item_code_registry_runtime` | ✅ |
| Pricing Management `/referensi/admin/pricing/` | login + portal access; kelola SubscriptionPlan tier 1-3 + promo | template form | `test_pricing_management` | ✅ |
| Import 3-Tier `/referensi/import/...` (options → pdf-convert → validate/report → staging → commit) | permission import + rate-limit | JS embedded besar di `import_validate_report.html` (WYSIWYG editor) | 10 file test (repair, schema, staging_validation, multifile, permissions, suffix, pdf, batch_commit_policy, validate_report_ui, export_completeness) — bug A-D FIXED | ✅ |
| Audit Dashboard `/referensi/audit/...` (logs/detail/resolve/statistics/export) | login + portal guard | template | `test_audit_template_security` | ✅ |
| Export `/referensi/export/...` (single/multiple/search/async) | **login saja** | — | `test_export_completeness` | ⚠️ **F10** — gate Pro/permission belum diputuskan |

Plus **F11**: `debug/clear-data/` (hapus seluruh data referensi) — permission-gated tapi sebaiknya DEBUG/superuser-only.

### C. dashboard — 4 kelompok halaman

| Halaman | Akses | Frontend | Test | Status |
|---|---|---|---|---|
| Dashboard utama `/dashboard/` (list + filter + statistik + mass-edit) | login; queryset `owner=request.user` | 5 JS (dashboard/formset/mass-edit/resizable/ux) | 29 test (2 file) | ✅ |
| Project detail/edit/delete/duplicate | login + `get_object_or_404(pk, owner, is_active)`; duplicate via `DeepCopyService` (termasuk VolumeFormulaState Step 9 + opaque remap Opsi B) | modal templates | tercakup suite dashboard + `tests_phase45_rollback`/copy | ✅ |
| Upload Excel `/dashboard/upload/` | login; project dibuat `owner=request.user` | `formset.js` | suite dashboard | ✅ |
| Export & bulk (xlsx/csv/pdf, delete/archive/unarchive) | login + `@require_POST` (bulk); owner-filtered | — | suite dashboard | ✅ |

### D. pages, subscriptions, accounts

| Halaman | Akses | Catatan | Status |
|---|---|---|---|
| Landing `/` | publik | redirect dashboard/portal jika login | ✅ |
| Pricing `/pricing/` | publik | render plan dari DB; target redirect middleware subscription | ✅ |
| Checkout `/subscriptions/checkout/<plan>/` | login; staf/superuser diblokir (ADMIN_CHECKOUT_BLOCKED) | server-side pricing — `amount` client diabaikan (teruji) | ✅ |
| Payment create (AJAX Snap.js) | login (+ exclude middleware pasca-F9) | regression test expired-user PASS | ✅ |
| Payment finish | login | status polling transaksi | ✅ |
| Webhook Midtrans | publik by design | signature verified + `select_for_update` idempotent + snapshot durasi | ✅ |
| Login/Signup/Reset (allauth `/accounts/...`) | publik + rate-limit allauth (cache-backed) | insiden 500 (2026-06-10) = Redis runtime host, bukan kode | ✅ |
| Django Admin `/admin/` | superuser; login dialihkan ke allauth | — | ✅ |

### Rekap temuan baru dari rincian per-halaman

| ID | Severity | Temuan | Status |
|---|---|---|---|
| F14 | 🟢 Rendah | Halaman dev `export-test` ter-route di production untuk semua owner | OPEN — gate DEBUG/staff sebelum launch |

Prioritas UAT browser (L7) berdasarkan bobot risiko frontend: (1) Volume Pekerjaan — file JS terbesar + formula opaque; (2) Jadwal Pekerjaan — grid/Gantt/Kurva-S interaktif; (3) Import 3-tier referensi — WYSIWYG embedded; (4) Checkout E2E Midtrans sandbox (pasca-fix F9); (5) Rekap Kebutuhan — chart echarts tanpa unit test.

---

## Catatan Arsitektur & Workflow 2026-06-10 06:45 WITA (hasil review arsitektural)

**Kesimpulan: tidak ada yang fundamental rusak; arsitektur = "modular monolith + progressive enhancement" yang sehat dan proporsional. Tidak ada restrukturisasi yang memblokir launch.**

### Yang dinilai benar (JANGAN diubah)
- Django SSR + JS per halaman (bukan SPA) — tepat untuk solo-maintainer dengan ±150 endpoint.
- Batas 6 app memetakan domain dengan bersih; multi-tenancy owner-scope konsisten + guard test.
- Keputusan sulit sudah benar: opaque ID via counter table, jadwal v2 weekly canonical SSoT, deprecation v1 ber-telemetry, entitlements engine terpusat.
- Infra compose single-host + Caddy + Celery proporsional; jangan ke k8s/microservices. Evolusi 6-12 bulan yang layak: managed Postgres (operasional, bukan kode).

### 4 utang struktural — roadmap PASCA-launch (berurutan)
1. **`views_api.py` god-file (~8.000 baris, ±77 endpoint).** Pecah jadi package `views_api/` per domain (volume/harga/detail_ahsp/rekap/parameters/export) dengan re-export di `__init__.py` agar `urls.py` tak berubah; per-batch dengan suite hijau. Pola sudah ada (`views_api_tahapan.py`, `views_export.py`).
2. **Tiga subsistem export paralel** (±30 endpoint sinkron per-format, jalur async Celery, pipeline batch client `export/init→upload-pages→finalize`). Konsolidasi: satu export service + format-adapter (pola adapter sudah ada di `exports/volume_pekerjaan_adapter.py`) + satu dispatcher + satu jalur async; endpoint lama jadi thin alias selama deprecation.
3. **Middleware subscription berbasis regex path rapuh — kelas bug F9.** Pindahkan enforcement utama ke decorator per-view (`@requires_write_entitlement`, padanan `_api_pro_export_required` sudah ada); middleware tetap sebagai defense-in-depth, bukan satu-satunya lapisan.
4. **Frontend: 3 file monolit + util terduplikasi** (`volume_pekerjaan.js` 7.6k, `list_pekerjaan.js` 3.1k, `rekap_kebutuhan.js` 2.9k; `esc()`/http/format diduplikasi per file). Bukan rewrite — angkat bertahap: satukan util ke `js/core/`+`js/shared/`, jadikan volume entry Vite kedua (multi-entry sudah terbukti di Jadwal), perluas XSS guard (F12); side-effect: unit test per halaman jadi murah (menutup F13).

### Catatan workflow client-side
Pola SSR-bootstrap → edit → dirty-guard → save eksplisit → sync LED → change-status adalah state model yang tepat untuk aplikasi data-entry (lebih prediktabel daripada auto-save). Rapikan saat disentuh lagi: (a) arahkan semua save ke `upsert/`, jadikan `save/` full-create reset-only (docstring-nya sendiri memperingatkan risiko duplikasi); (b) beri deprecation header + telemetry pada alias URL legacy (`detail-ahsp`, `detail-ahsp-gabungan`, `volume-formula-state` alias) seperti pola tahapan v1 agar pemangkasan kelak berbasis data.

### Urutan eksekusi yang disarankan
Launch dulu (L5-L8) → #3 (kecil, cegah kelas bug F9 terulang) → #1 (mekanis) → #4 bertahap per halaman → #2 saat ada permintaan fitur export berikutnya. Semua evolusioner, tanpa big-bang rewrite.

---

## Koreksi Silang & Review Konsistensi 2026-06-10 08:05 WITA

Hasil review menyeluruh kedua dokumen audit (dokumen ini + `AUDIT_UI_UX_20260610.md`):

1. **Revisi status per-halaman** (addendum 06:28) berdasarkan klarifikasi pemilik produk + temuan U14/U15 di `AUDIT_UI_UX_20260610.md` §9:
   - Halaman **#5 Orphan Cleanup** & **#6 Audit Trail**: status "✅ siap" direvisi menjadi **"⚠️ siap dengan catatan U14"** — keduanya dimaksudkan admin-only tetapi sidebar & view belum punya gating role (terlihat/terbuka untuk semua pemilik proyek).
   - Halaman **#10 Rincian RAB**: status "✅ siap" direvisi menjadi **"🟡 LEGACY (U15)"** — fungsinya sudah digantikan Rincian AHSP + Rekap RAB, tidak punya satu pun link masuk; kandidat redirect/deprecation, bukan halaman aktif.
2. **Koreksi angka:** baris "volume_pekerjaan.js ~3500 baris" pada tabel per-halaman 06:20 adalah angka usang; ukuran terverifikasi = **7.641 baris** (sudah benar di addendum 06:28).
3. **Insiden Redis 2026-06-10** yang dirujuk tabel 06:20: akar masalah = `manage.py runserver` native host (4 proses) membajak `localhost:8000` dari Docker + `ahsp_redis` ter-recreate dari compose prod sehingga port 6379 tidak terpublish ke host → allauth rate-limit gagal konek cache → 500 di halaman login. Solusi disepakati: matikan runserver native, operasikan hanya via stack Docker (`docker compose up -d`), perubahan kode via `docker compose restart web`.
4. **Penomoran temuan lintas dokumen:** F1-F14 (dokumen ini) + U1-U15 (`AUDIT_UI_UX_20260610.md`) — tidak ada nomor ganda/celah. Status terkini: F9 FIXED (+2 regression test); F1/F2 FIXED (compose hardening); F3-F8, F10-F14, U1-U15 OPEN dengan prioritas di masing-masing dokumen.
5. **Tindak lanjut prioritas gabungan sebelum UAT L7:** M1+M2+M8 (UI/UX §9.3, ~1 jam) + keputusan F10 (gating export referensi) + F14 (gate export-test).

---

## Verifikasi Review Eksternal 2026-06-10 11:09 WITA

Review independen pihak kedua atas kedua dokumen audit diverifikasi klaim-per-klaim terhadap source/git:

| Klaim reviewer | Hasil verifikasi | Tindakan |
|---|---|---|
| **Tinggi: SSOT launch tidak sinkron** — `Review/CHECKLIST_PROGRESS.md` (2026-02-17, klaim SSOT, 29/54) & `PRE_PRODUCTION_LAUNCH_CHECKLIST.md` (gate `[x]` semua, "pytest 79 passed") bertentangan dengan audit Juni | **BENAR** — keduanya snapshot Februari berbasis lingkungan dev; risiko GO dari dokumen salah nyata | **FIXED**: banner SUPERSEDED di kedua dokumen; `docs/CHECKLIST_PROGRESS_KESIAPAN_LAUNCH_20260609.md` ditetapkan SSOT tunggal; `AGENDA_PROVIDER` ditandai tetap aktif khusus tracker provider (isinya TODO PVD-01..09 = masih akurat & konsisten NO-GO) |
| **Tinggi: FIXED tapi belum masuk Git** (middleware, compose, tests, audit UI/UX untracked; HEAD remote `4d1f4353`) | **BENAR saat review ditulis; sudah berubah** — kini ter-commit lokal: `c5442a07` (F9+F1/F2), `bf04ae9a` (docs), `a842cb14` (UI fixes). Status tepat: **fixed locally, committed, PENDING PUSH + CI** (branch 3+ commit di depan origin) | Push + CI run = langkah berikutnya sebelum status "release-closed" |
| **Sedang: klaim "kode launch-ready" terlalu kuat** (F10/F11/F14 open, UAT belum, CI belum cover frontend, Python mismatch) | **BENAR** — istilah direvisi | **FIXED**: wording resmi kini "**feature-complete; layak release candidate setelah gate tersisa ditutup**". Catatan: U14 sudah CLOSED (commit `a842cb14`); F10/F11/F14 + UAT tetap open |
| **Sedang: pengecualian F9 terlalu luas** (`^/subscriptions/` memutihkan endpoint write masa depan) | **BENAR** — kritik desain valid | **FIXED**: dipersempit ke `^/subscriptions/payment/` (satu-satunya POST ter-autentikasi; webhook anonim sudah di-skip middleware; checkout/pricing GET-only). Test subscriptions+accounts: 48 passed |
| **Rendah: scope npm audit perlu diperjelas** | **BENAR** — diverifikasi ulang: full dependency = **5 moderate**; production-only (`--omit=dev`) = **2 moderate** | **FIXED**: dicatat dengan dua angka terpisah (lihat juga tabel gate di checklist) |
| Penilaian UI/UX reviewer (U1/U2/U7/U8/U11/U14/U15 terkonfirmasi; U1/U2 = static-analysis sampai M1/M2 direproduksi browser) | Sesuai — dan M1/M2 **fix-nya sudah diterapkan** (`a842cb14`); reproduksi browser tetap wajib saat UAT L7 | — |

Tindak lanjut tambahan yang dieksekusi bersamaan: **F3** (CI Python 3.12 → **3.11**, match image) dan **F4** (job `frontend` baru di CI: `npm ci` → vitest → production build) pada `.github/workflows/ci.yml` — efektif setelah push.

Verifikasi sampingan: `SECRETS_LOCAL.md` di root **tidak ter-track** (`.gitignore:89`) dan ter-exclude dari image (`.dockerignore` `*.md`) — aman; berisi SECRET_KEY dev, pastikan SECRET_KEY production berbeda saat L5.

---

# DOKUMEN AUDIT ASLI (2026-06-09) — baseline, dipertahankan utuh

## 1. Ringkasan Eksekutif

- **Kabar baik:** konfigurasi **produksi sudah sangat matang**. `config/settings/production.py` menutup hampir semua security checklist Django (lihat A1). Masalahnya **bukan** kode keamanan yang hilang.
- **Akar gap launch:** sistem saat ini **berjalan dalam mode `development`** (bukan production), masih memakai akun dev `admin/admin`, belum ada reverse-proxy/TLS, backup belum terjadwal, dan image production belum reproducible.
- Secret runtime aktif **bukan placeholder/default** dan panjangnya memadai. Gap keamanan aktual adalah mode development, `ALLOWED_HOSTS='*'`, port host terbuka, serta kredensial dev.
- **Blocker build production baru:** `.dockerignore` mengecualikan seluruh app `referensi/`, sementara `INSTALLED_APPS`, URL, dan middleware membutuhkannya. Image tanpa bind mount berisiko gagal build/start.
- Repo HEAD memuat **20.668 file tracked**. `node_modules/` (17.198 file, ~149 MiB) dan `cleanup_archive/` (2.694 file, ~293 MiB) membentuk sekitar **89% ukuran file HEAD**.
- **1 test merah** = ekspektasi usang (redirect pricing vs login), **bukan** lubang keamanan.
- **Skor kesiapan keseluruhan: ~65%** — *feature-ready & security-code-ready, tapi belum deploy-ready*.

Severity yang dipakai: **Kritis** (blokir launch) · **Tinggi** (harus sebelum launch) · **Sedang** (sebaiknya) · **Rendah/Info**.

---

## 2. Temuan

### A. Keamanan & Konfigurasi

| ID | Severity | Temuan | Bukti | Dampak |
|---|---|---|---|---|
| A1 | ✅ Positif | **`production.py` ter-hardening penuh** | DEBUG=False; guard `DJANGO_ENV`, `SECRET_KEY` (≥32 & non-placeholder), `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` tolak placeholder; `SECURE_SSL_REDIRECT`, cookie `Secure`, **HSTS 1th+preload**, `SECURE_PROXY_SSL_HEADER`, referrer-policy; JSON logging; **Sentry** opsional; sesi `cached_db` (durable) | Fondasi keamanan produksi kuat |
| A2 | 🔴 Kritis | **Runtime berjalan mode `development`** | Stack aktif pakai `docker-compose.yml` (DJANGO_ENV=development); ada `admin/admin`, port `:8000` & `:5432` bind `0.0.0.0` | Data klien bisa diakses bila terjangkau jaringan |
| A3 | 🟠 Tinggi | **Kredensial dev dan host policy longgar** | Secret runtime bukan placeholder, tetapi akun `admin/admin` aktif, `DEBUG=True`, `ALLOWED_HOSTS` memuat `*`, dan port web/DB/Redis/Flower dipublish ke semua interface | Akses lokal/LAN terlalu luas untuk data nyata |
| A4 | 🟠 Tinggi | **Belum ada reverse-proxy/TLS** | `docker-compose.prod.yml` punya db/redis/pgbouncer/web/celery, **tanpa** nginx/caddy/certbot | `SECURE_SSL_REDIRECT`/HSTS mengasumsikan TLS-terminating proxy yang belum ada |
| A5 | 🟡 Sedang | **Entrypoint membuat `admin/admin`** saat `DJANGO_ENV=development` | `docker-entrypoint.sh:64` | Kredensial lemah di lingkungan berdata nyata |
| A6 | 🟢 Rendah | **1 test permission merah = ekspektasi usang, bukan lubang** | `test_import_endpoints_block_user_without_permissions`: endpoint tetap blokir (302) tapi redirect **pricing** (subscription middleware duluan) bukan **login** | Test maintenance; CI tertahan |
| A7 | 🔴 Kritis | **Build context production membuang app `referensi/`** | `.dockerignore` memuat `referensi/`, sedangkan Dockerfile menjalankan `COPY . .` dan `collectstatic`; app tetap aktif di settings/URL/middleware | Image production bersih dapat gagal import/build/start; dev bind mount menutupi masalah |
| A8 | 🟠 Tinggi | **Build frontend tidak deterministik** | `.dockerignore` mengecualikan `package-lock.json`; Dockerfile memakai `npm install`, bukan `npm ci` | Versi dependency image dapat berubah antar-build |

### B. Data & Operasional

| ID | Severity | Temuan | Dampak |
|---|---|---|---|
| B1 | 🟠 Tinggi | **Backup SSOT belum terjadwal** (hanya dump satu-kali migrasi) | Volume Docker rusak → kehilangan kerja sejak migrasi |
| B2 | 🟠 Tinggi | **Risiko divergensi dua-DB** (PG16 native masih jalan & menjawab `localhost:5432`) | `runserver` host tak sengaja menulis ke DB lama |
| B3 | 🟡 Sedang | **`docker-compose.prod.yml` belum pernah diuji** dengan secrets/host nyata | Deploy pertama berisiko gagal (guard production aktif) |
| B4 | 🟡 Sedang | **Migration opaque sudah dijalankan**, tetapi **monitoring window & QA Gate D belum** | Regresi parameter/formula bisa tak terdeteksi |

### C. Kualitas & CI

| ID | Severity | Temuan | Dampak |
|---|---|---|---|
| C1 | 🟡 Sedang | **CI merah** + **1 test merah** (A6) | Tak bisa merge bersih; perlu revalidasi gate (cakupan branch membesar C0–C7) |
| C2 | 🟢 Rendah | **40 test skipped** (guard fitur WIP) | Cakupan verifikasi belum penuh |
| C3 | 🟢 Rendah | **Frontend (vitest) belum di CI** | Regresi JS tak terjaring otomatis |
| C4 | ✅ Positif | **Suite Django HIJAU di Docker** (`350 OK, 40 skipped`) | Runtime SSOT sehat |

### D. Dead Files & Dead Code

| ID | Severity | Temuan | Aksi disarankan |
|---|---|---|---|
| D1 | 🟠 Tinggi | **`cleanup_archive/` = 2.694 file, ~293 MiB ter-track** | Buat arsip eksternal + checksum/manifest, lalu hapus dari HEAD dan tambahkan ignore root |
| D2 | 🟠 Tinggi | **`node_modules/` = 17.198 file, ~149 MiB ter-track** walaupun sudah di-ignore | Hapus dari index/HEAD; pertahankan `package-lock.json`; jangan hapus instalasi lokal sebelum build/test selesai |
| D3 | 🟢 Rendah | **Backup/scratch aktif ter-track**: `rekap_kebutuhan.js.bak`, `rekap_kebutuhan.js.backup_bom`, `ahsp_database_backup.css`, `preview_old.py.backup`, serta script root `analyze_*`, `debug_*`, `fix_template.py`, `temp.html` | Hapus setelah reference scan + smoke test; sejarah tetap tersedia di Git |
| D4 | 🟢 Info | **Guard `ProgrammingError/OperationalError`** kompatibilitas opaque (sementara) | Hapus setelah semua env confirmed migrated |
| D5 | 🟡 Sedang | **Penanda `legacy/deprecated/backward compatibility` bukan bukti dead code** | Beberapa jalur masih diroute, dipanggil, dan diuji (`_stage_rincian_legacy_flat`, API tahapan v1, export legacy, parameter fallback). Jangan mass-delete berdasarkan grep |
| D6 | 🟢 Info | **Artefak lokal** (`.tmp_*`, `_wcag_*`, `generate_pass.py`) sudah di-gitignore sesi ini | — |

### E. Dependensi (belum diaudit — rekomendasi)

| ID | Severity | Temuan | Aksi |
|---|---|---|---|
| E1 | 🟡 Sedang (TBD) | **Audit dependensi belum dilakukan** | Jalankan `pip list --outdated` + `pip-audit`/`safety`; `npm audit`; catat CVE & versi tertinggal |

---

## 3. Tingkat Kesiapan Produksi (refined)

| Area | Kesiapan | Catatan |
|---|---|---|
| Konfigurasi keamanan (kode) | **~90%** ✅ | `production.py` solid (A1) |
| Penerapan/deployment (jalan sbg produksi) | **~45%** 🔴 | Masih dev mode (A2), secrets default (A3), TLS/proxy belum (A4), prod compose belum diuji (B3) |
| Keandalan data & backup | **~55%** 🟠 | SSOT live; backup terjadwal & matikan DB lama belum (B1, B2) |
| Gate kualitas (test/CI) | **~80%** 🟠 | Docker hijau (C4); 1 test + CI merah (C1) |
| Kebersihan repo / dead code | **~30%** 🔴 | 89% ukuran file HEAD berasal dari `node_modules` + arsip; backup/scratch masih tracked |
| Verifikasi / UAT | **~30%** 🔴 | UAT proyek nyata & browser gate ulang belum |

### Skor keseluruhan: **~65%**

**Verdict:**
- ✅ **Layak pemakaian internal terkontrol** setelah A2/A3 (mode+secret) + B1/B2 ditutup.
- ❌ **Belum layak launch publik** sampai A2–A4, B1–B3, C1 selesai (+ UAT).
- 💡 Inti: aplikasi **sudah punya** semua "rem keselamatan" produksi; tinggal **menyalakannya** (mode prod + secrets + TLS) dan **operasional** (backup, gate, bersih-bersih).

---

## 4. Rekomendasi Workstream → Basis Implementation Plan

Disusun sebagai kandidat fase/workstream untuk plan berikutnya (dengan ketergantungan):

- **WS0 — Production Image Correctness (Kritis)**
  A7,A8 → keluarkan `referensi/` dari `.dockerignore`, masukkan `package-lock.json` ke build context, pakai `npm ci`, dan uji image tanpa bind mount. *Acceptance:* clean build sukses; `referensi` import/migration/URL tersedia; `collectstatic` sukses.
- **WS1 — Security & Deployment Hardening (Kritis)**
  A2,A3,A4,A5 → jalankan via `docker-compose.prod.yml` (DJANGO_ENV=production), isi secrets nyata (SECRET_KEY ≥32, DB password, ALLOWED_HOSTS, CSRF), pasang reverse-proxy + TLS (nginx/caddy + certbot), nonaktifkan dev-admin di non-dev. *Acceptance:* `check --deploy` bersih, HTTPS aktif, tak ada kredensial default.
- **WS2 — Data Safety (Tinggi)**
  B1,B2 → jadwalkan `safe_backup_db.sh` + uji restore; hentikan service PG16 native setelah verifikasi. *Acceptance:* backup terbukti restore-able; hanya satu DB sumber.
- **WS3 — Quality Gate Closeout (Sedang)**
  A6,C1,C2 → perbaiki ekspektasi test permission (atau urutan middleware), hijaukan CI, revalidasi gate save/sync + Opaque setelah C0–C7, lalu UAT proyek nyata. *Acceptance:* CI hijau, gate lulus, UAT sign-off.
- **WS4 — Repo Archive & Cleanup (Tinggi–Rendah)**
  D1-D6 → arsipkan `cleanup_archive/` di luar repo dengan checksum; untrack `node_modules/`; hapus backup/scratch terverifikasi; pertahankan compatibility code yang masih diroute/diuji; guard opaque hanya dihapus setelah semua environment termigrasi. *Acceptance:* HEAD tidak memuat dependency vendor/arsip/file backup, clean install/build/test tetap hijau.
- **WS5 — Opaque ID Closeout (Sedang)**
  B4 → QA Gate D/Phase 2 + monitoring window 1 minggu (`opaque_daily_monitor.sh`). *Acceptance:* sign-off + nol regresi parameter/formula.
- **WS6 — Dependency Audit (Sedang)**
  E1 → audit & update dependensi rentan (Python + npm). *Acceptance:* tidak ada CVE kritis terbuka.

### Urutan disarankan
WS0 → WS4 batch aman → WS1 → WS2 → WS3 (gate+UAT) → WS5 → WS6. WS0, WS1, dan WS2 adalah prasyarat launch terbatas; WS3+UAT prasyarat launch publik.

---

## 5. Lampiran — perintah audit yang dipakai
- `docker exec ahsp_web python manage.py test` → `350 OK, 40 skipped` (Docker/Postgres).
- `python -m pytest` → `1 failed, 403 passed, 40 skipped` (failing: `test_import_permissions::test_import_endpoints_block_user_without_permissions`).
- `manage.py check --deploy` (production) → terhalang guard `production.py` (ALLOWED_HOSTS/CSRF placeholder) — guard berfungsi sesuai desain.
- `git ls-files cleanup_archive/` → 2694; scan `.bak/.backup/.old`; Grep penanda `deprecated/legacy/unused`.
- `git ls-files node_modules/` → 17198.
- `git ls-tree -r -l HEAD` → sekitar 497 MiB file HEAD; `node_modules` + `cleanup_archive` sekitar 89%.
- Runtime Docker: `DEBUG=True`, `DJANGO_ENV=development`, secret non-placeholder, akun `admin/admin` aktif.
- `check --deploy --settings=config.settings.production` berhenti sesuai desain karena host lokal/dev masih tercantum.
