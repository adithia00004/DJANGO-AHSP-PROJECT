# Checklist Progress Kesiapan Launch

> ✅ **DOKUMEN INI ADALAH SSOT TUNGGAL STATUS LAUNCH** (ditetapkan 2026-06-10).
> Dokumen launch lama (`Review/CHECKLIST_PROGRESS.md`, `PRE_PRODUCTION_LAUNCH_CHECKLIST.md`) = SUPERSEDED/arsip.
> `AGENDA_PROVIDER_PIHAK_KETIGA.md` tetap aktif khusus tracker provider (PVD-01..09).

**Tanggal mulai:** 2026-06-09
**Branch:** `checkpoint/save-sync-plan-20260608`
**Image RC:** `ahsp-launch:rc-20260609-final`
**Image digest:** `sha256:42a817f51b22c94198f03a4f4e416a7e4b47976b572a5725887935d70583d6bb`
**Status keseluruhan:** IN PROGRESS / NO-GO PUBLIC LAUNCH

## Legenda

- `[x]` selesai dan bukti tersedia
- `[~]` sebagian selesai
- `[ ]` belum dikerjakan
- `[!]` blocker launch

## L0 - Safety dan Baseline

- [x] Branch/HEAD awal direkam: `e05f0748`.
- [x] `manage.py check` dan migration drift check lulus.
- [x] Inventaris SSOT: 159 proyek, 5.104 AHSP, 30.101 rincian, 3 plan, 80 user.
- [x] Dump PostgreSQL custom-format dibuat dan diberi SHA-256.
- [x] `cleanup_archive/` disalin ke arsip eksternal, dilengkapi manifest dan SHA-256.
- [x] Backup Redis dibuat sebelum repair AOF.
- [x] Baseline backend, frontend, dan build direkam.

Lokasi backup eksternal:
`D:\PORTOFOLIO ADIT\DJANGO AHSP LAUNCH ARCHIVE\20260609`

## L1 - Production Image Correctness

- [x] `.dockerignore` tidak lagi membuang `referensi/` atau `package-lock.json`.
- [x] Dockerfile memakai multi-stage Python/frontend dan `npm ci`.
- [x] Node/npm/node_modules tidak masuk runtime image.
- [x] `referensi`, migration graph, dan static asset tersedia dalam image.
- [x] Container production start tanpa bind mount source.
- [x] Health check produksi lulus.
- [x] Smoke endpoint: `/health/` 200, `/` 200, `/pricing/` 200.
- [x] `/referensi/import/` memberi 302 autentikasi sesuai desain.
- [x] Image final sekitar 239 MB, turun dari baseline sekitar 513 MB.

## L2 - Archive dan Repo Hygiene

- [x] `node_modules/` tidak lagi tracked: 17.198 file.
- [x] `cleanup_archive/` tidak lagi tracked: 2.694 file.
- [x] `package-lock.json` tetap tracked.
- [x] Kedua direktori masuk `.gitignore`.
- [x] Folder kerja lokal dipertahankan; perubahan hanya pada index/HEAD.
- [x] Total staged deletion cleanup: 19.901 file, termasuk 9 dead/scratch file.

## L3 - Dead File Terverifikasi

- [x] Reference scan dilakukan.
- [x] Dua backup JS, backup CSS, backup view, dan lima scratch root dihapus dari HEAD.
- [x] Compatibility/deprecated code aktif tidak dihapus massal.
- [x] Backend, frontend, build, dan immutable smoke lulus setelah cleanup.

## L4 - Dependency Security

- [x] Python package audit: 0 vulnerability setelah patch upgrade.
- [x] Django dinaikkan ke `5.2.15`.
- [x] Paket Python terdampak lain dinaikkan ke versi perbaikan.
- [x] Frontend critical vulnerabilities turun dari 4 menjadi 0.
- [x] jsPDF, Vitest, coverage-v8, dan happy-dom dinaikkan dan lulus test/build.
- [x] `xlsx` dipatch ke `0.20.3` via tarball resmi SheetJS CDN (commit `4d1f4353`, 2026-06-10) — advisory high (Prototype Pollution + ReDoS) tertutup; `npm audit` → 0 critical, 0 high.
- [~] Lima advisory moderate tersisa (`uuid<11.1.1` via `exceljs` + tooling transitive). `npm audit fix --force` akan downgrade `exceljs` ke 3.4.0 (breaking) — jangan dijalankan; defer sadar-risiko.

## L5-L8 - Production dan Release

> **Plan eksekusi aktif:** `IMPLEMENTATION_PLAN_RC_20260610.md` (fase R0-R6, dibuat 2026-06-10 11:30 WITA) — L5→R2, L6→R3, L7→R4, L8→R5, plus R1 (penutupan temuan kode pra-UAT: F10/F11/F14, M7/M9/M12). R0 (baseline RC: semua fix audit committed+pushed+CI) sudah DONE.

- [ ] Jalankan stack nyata dengan domain, TLS, dan secret produksi.
- [ ] Hilangkan kredensial dev dan batasi port PostgreSQL/Flower.
- [ ] Jadwalkan backup SSOT dan lakukan restore drill.
- [ ] Pastikan hanya satu jalur database yang aktif.
- [ ] Jalankan CI remote dan browser UAT proyek nyata.
- [ ] Tutup QA Gate D Opaque ID dan monitoring.
- [ ] Review staged cleanup besar sebelum commit/push.
- [ ] Buat release candidate dan keputusan GO/NO-GO.

## Hasil Gate Terakhir

| Gate | Hasil |
|---|---|
| Backend dalam image final | `404 passed, 40 skipped, 35 subtests passed` |
| Frontend clean workspace | `233 passed, 25 skipped` |
| Frontend production build | PASS |
| Django system check | PASS |
| Migration drift | PASS |
| Immutable container | Healthy, mounts `[]` |
| Python dependency audit | 0 vulnerability |
| npm dependency audit (full) | 0 critical, 0 high, 5 moderate (re-audit 2026-06-10, pasca patch `xlsx@0.20.3`) |
| npm dependency audit (production-only, `--omit=dev`) | 0 critical, 0 high, **2 moderate** (verifikasi 2026-06-10 11:09) |

## Record Eksekusi

| Fase | Aktivitas | Hasil / bukti |
|---|---|---|
| L0 | Backup DB | `ahsp_sni_db_pre_launch_20260609_200434.dump`, 22.604.817 byte + SHA-256 |
| L0 | Arsip cleanup | `cleanup_archive_20260609.zip`, SHA-256 `6C37F37473A70AD73174A51B0691535C92F291D4987949ABD943F8C385C92BFF` |
| L0 | Backup Redis | `redis_data_pre_repair_20260609.tar.gz`, SHA-256 `B9703620FBB17C613DB66C3D98D08B552F8E86C56FF3333987F799F16E5D78DE` |
| Operasional | Repair Redis AOF | Backup dibuat; 44 byte tail korup dipangkas; service kembali healthy |
| L1 | Immutable image | Image final healthy tanpa source bind mount |
| L2/L3 | Cleanup | Vendor, arsip, dan 9 dead file keluar dari HEAD |
| Quality | Test baseline | Permission test dan XSS governance guard diperbaiki sesuai kontrak |
| Security | Dependency upgrade | Python audit bersih; npm critical menjadi nol |
| Security | Patch `xlsx` 0.20.3 (2026-06-10) | Commit `4d1f4353`; npm audit 0 critical, 0 high |
| Audit | Re-audit independen (2026-06-10 05:47 WITA) | HEAD `4d1f4353`; temuan baru F1-F8 dicatat di addendum `AUDIT_KESIAPAN_LAUNCH_20260609.md` |
| Audit | Audit per-app/per-page (2026-06-10 06:20 WITA) | 6 app, ±150 endpoint dipetakan; auth/owner-scope konsisten; temuan F9-F13; gate: pytest 404 passed / vitest 233 passed |
| Audit | Rincian per-halaman (2026-06-10 06:28 WITA) | 12 halaman detail_project + 6 referensi + 4 dashboard + pages/subscriptions/accounts dinilai satu-per-satu; temuan baru F14 (export-test ter-route); prioritas UAT browser ditetapkan |
| Audit | Catatan arsitektur & workflow (2026-06-10 06:45 WITA) | Tidak ada restrukturisasi pemblokir launch; 4 utang struktural pasca-launch dicatat di `AUDIT_KESIAPAN_LAUNCH_20260609.md` |
| Audit | Audit UI/UX + peta z-index (2026-06-10 06:50 WITA) | Dokumen baru `AUDIT_UI_UX_20260610.md`; 216 deklarasi z-index dipetakan, 5 skala bersaing, temuan U1-U10 (2 tinggi: toast tertutup modal); checklist visual UAT ditambahkan |
| UI/UX | Eksekusi pra-UAT M1/M2/M8 + Kontrak Feedback (2026-06-10 10:55 WITA) | U1 fixed (templateLibraryModal → token); U14 fixed (orphan/audit admin-only + 4 test baru); U2/U9 fixed (4 toast referensi → DP.toast, modal 99999 → token); guard test `feedback_governance_guard` (z literal + budget confirm/alert 18 file); vitest 235 passed |
| Review | Verifikasi review eksternal + tindak lanjut (2026-06-10 11:09-11:15 WITA) | 5 klaim BENAR & ditindaklanjuti: SSOT tunggal (banner SUPERSEDED dok Feb), F9 exclusion dipersempit `/subscriptions/payment/`, CI Py3.11 + job frontend + trigger checkpoint/**, wording feature-complete/RC, npm audit full 5 / prod-only 2 moderate. Commit `a115296d`, `51c4a0ff` |
| Fix | Import full-backup raw-only (2026-06-10 11:15 WITA) | `expand_bundle_to_components` salah signature + except-pass → imported project bernilai nol; fix `_populate_expanded_from_raw` + raw-fallback services; 3 regression test; verifikasi independen 26 passed; commit `38046135` |
| Release | Push ke origin + plan RC (2026-06-10 11:30 WITA) | Branch pushed `4d1f4353..51c4a0ff` (CI berjalan); `IMPLEMENTATION_PLAN_RC_20260610.md` dibuat (R0 DONE, R1-R5 jalur launch, R6 backlog) |
| R0 | Gate CI remote (2026-06-10 11:50 WITA) | CI `51c4a0ff` SUCCESS — run pertama dengan job backend Py3.11 + frontend (vitest+build). R0 CLOSED |
| R3 | Restore drill LULUS (2026-06-10 12:06 WITA, dieksekusi pemilik) | Dump in-container 21 MB SHA-256 `aed701c1...494bc` → scratch DB → `159\|80\|5104\|3` match baseline L0 → scratch dihapus, live aman. Blocker #2 (restore drill) CLOSED untuk lingkup lokal |
| R3 | Akar B2 ditemukan (2026-06-10 12:30 WITA) | PG16 native masih menang di host:5432 (host pytest selama ini ke PG16, bukti `test_ahsp_sni_db`); PG16 juga melayani project lain → keputusan pemilik: pindah port 5433. `postgresql.conf` diubah; menunggu restart service (Administrator) + verifikasi |
| R1 | Eksekusi penuh R1.1-R1.6 (2026-06-10 12:10 WITA) | **F10 keputusan pemilik: gate permission portal** — `ReferensiPortalRequiredMixin` 4 view + `export_task_status` (bonus: endpoint ini sebelumnya TANPA auth) + 5 test; F11 DEBUG+superuser; F14 staff-gate; U15 redirect permanen + 2 API `@api_deprecated` sunset 2026-09-01; **M7 tombol export Pro kini terlihat terkunci** (context processor + `_export_menu_item.html` di 4 halaman + 3 test); U8 noscript. Vitest 235 passed; pytest penuh menyusul |
| Security | Fix F9 expired-user payment (2026-06-10) | `accounts/middleware.py` exclude `/subscriptions/` + 2 regression test (subscriptions 23 passed) |
| Security | Hardening F1/F2 compose prod (2026-06-10) | Bind loopback default db/web/flower, Flower `--basic-auth`, guard `:?` SECRET_KEY; `docker compose config` valid |

## Blocker Aktif

*(diperbarui 2026-06-10 06:20 WITA — audit per-app/per-page selesai, lihat addendum di `AUDIT_KESIAPAN_LAUNCH_20260609.md`)*

1. Production domain/TLS/secret/network hardening belum diterapkan pada deployment nyata (scaffolding Caddy + runbook siap).
2. Backup terjadwal dan restore drill belum dilakukan (`scripts/restore_drill_db.sh` siap).
3. UAT browser proyek nyata (semua halaman pada tabel per-page addendum + E2E Midtrans sandbox) dan Opaque ID sign-off belum selesai.
4. F10: export database referensi hanya digate login — keputusan gating (Pro/permission) sebelum public launch.

Blocker selesai sejak versi sebelumnya: advisory high `xlsx` (dipatch 0.20.3, `4d1f4353`); CI remote hijau (`fc8fdcba`); cleanup 19.901 file di-commit (`8483685e`); **F9 user expired tidak bisa bayar (FIXED + regression test, 2026-06-10)**; **F1/F2 hardening compose prod (bind loopback default, Flower basic-auth, guard SECRET_KEY — 2026-06-10)**.
