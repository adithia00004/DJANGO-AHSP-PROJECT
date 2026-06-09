# Checklist Progress Kesiapan Launch

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
- [!] `xlsx@0.18.5` masih memiliki 1 advisory high dan tidak menyediakan fix di registry npm.
- [~] Lima advisory moderate tersisa pada tooling/transitive dependency.

Mitigasi sementara `xlsx`: hanya proses workbook internal/terpercaya. Penggantian library atau build resmi SheetJS yang telah diperbaiki perlu diputuskan sebelum public launch.

## L5-L8 - Production dan Release

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
| npm dependency audit | 0 critical, 1 high, 5 moderate |

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

## Blocker Aktif

1. Production domain/TLS/secret/network hardening belum diterapkan pada deployment nyata.
2. Backup terjadwal dan restore drill belum dilakukan.
3. Advisory high `xlsx` belum memiliki fix dan perlu keputusan mitigasi/penggantian.
4. CI remote, UAT browser proyek nyata, dan Opaque ID sign-off belum selesai.
5. Cleanup 19.901 file masih staged lokal dan belum menjadi checkpoint Git.
