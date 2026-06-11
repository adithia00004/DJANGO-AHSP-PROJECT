# Implementation Plan Kesiapan Launch Produk

**Tanggal:** 2026-06-09
**Branch acuan:** `checkpoint/save-sync-plan-20260608`
**Sumber:** `AUDIT_KESIAPAN_LAUNCH_20260609.md` dan `SISA_PEKERJAAN_DAN_KESIAPAN_PRODUKSI_20260609.md`
**Status:** EKSEKUSI BERTAHAP. L0-L3 dan dependency hardening telah dijalankan; L5-L8 belum melewati gate produksi.

---

## 1. Sasaran

Menyiapkan release yang:

1. dapat dibangun ulang dari checkout bersih;
2. tidak membawa arsip, dependency lokal, backup, atau scratch file ke HEAD/image;
3. berjalan dengan production settings, TLS, secret kuat, dan satu SSOT database;
4. memiliki backup teruji, CI hijau, runtime gate, dan UAT proyek nyata;
5. mempunyai rollback code dan database yang dapat dieksekusi.

## 2. Keputusan Arsitektur Cleanup

- **Git adalah arsip historis kode.** File yang dihapus dari HEAD masih tersedia pada commit lama.
- `cleanup_archive/` tetap dibuatkan **salinan eksternal** sebelum dihapus karena berisi campuran dokumen, dump, eksperimen, dan source historis.
- `node_modules/` tidak diarsipkan karena dapat dibentuk ulang dari `package-lock.json`.
- Penanda `legacy`, `deprecated`, atau `compatibility` **tidak otomatis berarti dead code**. Penghapusan hanya boleh dilakukan bila tidak diroute, tidak di-import, tidak dipanggil, tidak dipakai template/static, dan test penggantinya tersedia.
- Cleanup dilakukan per batch kecil dan setiap batch harus melewati test sebelum commit berikutnya.

## 3. Progress Tracker

| Fase | Scope | Status | Gate |
|---|---|---|---|
| L0 | Freeze, backup, baseline, dan manifest cleanup | DONE | Backup + checksum + baseline tercatat |
| L1 | Perbaikan clean production image | DONE | Image final healthy tanpa bind mount |
| L2 | Archive/untrack dependency dan arsip | DONE (commit `8483685e`) | Clean install/build/test hijau; node_modules + cleanup_archive untracked (tetap di disk) |
| L3 | Hapus backup/scratch file terverifikasi | DONE (commit `8483685e`) | Reference scan + smoke test hijau; 9 file backup/scratch dihapus |
| L4 | Review compatibility/deprecated code | PARTIAL (review selesai) | Reference-scan: legacy Python/JS bertanda = USED/sengaja (KEEP). Ditemukan **11 file JS top-level 0-ref** (monolith pra-vite) + dok refactoring di folder static — kandidat hapus, menunggu konfirmasi + smoke. Detail: `docs/L4_DEAD_CODE_REVIEW_20260610.md` |
| L5 | Security/TLS/production compose | TODO (scaffolding siap) | Caddy auto-TLS (`deploy/Caddyfile` + `deploy/docker-compose.prod.proxy.yml`) + runbook `RUNBOOK_DEPLOY_TLS_L5_L6.md`. Eksekusi menunggu domain/secrets. Gate: `check --deploy`, HTTPS, port policy |
| L6 | Backup SSOT dan single-DB enforcement | TODO (scaffolding siap) | `scripts/restore_drill_db.sh` (restore ke DB scratch + verifikasi, tak sentuh live). Gate: restore drill LULUS + PG16 native dimatikan |
| L7 | CI, browser gate, UAT, dan Opaque sign-off | PARTIAL (CI hijau) | CI HEAD HIJAU di `fc8fdcba` (root cause: ci.yml override `DJANGO_SETTINGS_MODULE` → diperbaiki ke `config.settings.test`). Sisa: browser gate ulang, UAT proyek nyata, Opaque sign-off |
| L8 | Release candidate dan GO/NO-GO | TODO | Semua P0/P1 wajib PASS |

## 4. Fase L0 — Safety dan Baseline

1. Bekukan penambahan fitur pada branch release.
2. Catat HEAD, status PR, migration graph, jumlah project, dan checksum database.
3. Buat dump PostgreSQL format custom sebelum cleanup/deploy.
4. Buat arsip eksternal:
   - sumber: `cleanup_archive/`;
   - target disarankan: direktori di luar repository;
   - hasil: ZIP/7z + SHA-256 + daftar file.
5. Rekam baseline:
   - `python manage.py check`;
   - `python manage.py makemigrations --check --dry-run`;
   - `pytest -q`;
   - `npm run test:frontend`;
   - `npm run build`.

**Rollback:** checkout commit sebelum batch cleanup dan restore dump bila ada operasi data.

## 5. Fase L1 — Production Image Correctness

### Blocker yang wajib diperbaiki

1. Hapus aturan `referensi/` dari `.dockerignore`.
2. Jangan mengecualikan `package-lock.json` dari build context.
3. Ganti `npm install` pada Dockerfile menjadi `npm ci`.
4. Tambahkan `cleanup_archive/`, test artifact, dan local tooling ke `.dockerignore`.
5. Build image dari checkout bersih tanpa bind mount.

### Acceptance

- `referensi` tersedia di image dan dapat di-import.
- `manage.py check`, migration graph, dan `collectstatic` sukses di image.
- Web dapat start menggunakan image immutable.
- Import AHSP, pricing management, dan halaman referensi dapat dibuka.
- Build kedua dengan lockfile yang sama tidak mengubah dependency tree.

## 6. Fase L2 — Archive dan Repo Hygiene

### Batch L2-A: `node_modules/`

- Untrack 17.198 file `node_modules/`.
- Pertahankan `.gitignore` dan `package-lock.json`.
- Hapus folder lokal hanya setelah `npm ci` terbukti dapat memulihkannya.

### Batch L2-B: `cleanup_archive/`

- Verifikasi arsip eksternal dan checksum.
- Tambahkan `/cleanup_archive/` ke `.gitignore`.
- Hapus 2.694 file arsip dari HEAD.
- Jangan rewrite history pada fase launch. History rewrite menjadi pekerjaan maintenance terpisah karena berdampak pada semua clone/branch.

### Acceptance

- `git ls-files node_modules cleanup_archive` kosong.
- `npm ci`, frontend test, build, Django check, dan suite backend tetap hijau.
- Ukuran checkout/PR berkurang tanpa perubahan perilaku aplikasi.

## 7. Fase L3 — Dead File yang Terverifikasi

### Kandidat aman setelah reference scan

- `detail_project/static/detail_project/js/rekap_kebutuhan.js.bak`
- `detail_project/static/detail_project/js/rekap_kebutuhan.js.backup_bom`
- `referensi/static/referensi/css/ahsp_database_backup.css`
- `referensi/views/preview_old.py.backup`
- `analyze_pdf_structure.py`
- `debug_excel_structure.py`
- `debug_pdf_structure.py`
- `fix_template.py`
- `temp.html`

File management command bernama `debug_*`, `fix_*`, atau `generate_*` **tidak termasuk batch otomatis** karena dapat merupakan alat operasional. Audit penggunaannya terlebih dahulu.

### Acceptance

- Tidak ada referensi aktif dari URL, import, template, static include, command, CI, atau dokumentasi operasional.
- `collectstatic`, targeted page test, import test, dan browser smoke test lulus.

## 8. Fase L4 — Dead Code Review

### Jangan dihapus sekarang

- parser `_stage_rincian_legacy_flat`;
- endpoint tahapan v1 yang masih diroute dan diberi deprecation header;
- export legacy yang masih diuji;
- fallback parameter legacy/opaque;
- alias URL/template yang masih melayani data/export lama.

### Metode penghapusan

Untuk setiap simbol:

1. cari route/import/call/template/static usage;
2. ukur deprecation telemetry bila endpoint;
3. tambahkan regression test yang membuktikan jalur pengganti;
4. hapus satu kelompok kecil;
5. jalankan suite dan UAT data lama.

Compatibility code baru boleh dihapus setelah masa deprecation dan bukti nol penggunaan.

## 9. Fase L5 — Production Security dan Network

- Jalankan `DJANGO_ENV=production`, `DEBUG=False`.
- Nonaktifkan/hapus password `admin/admin`.
- Gunakan host/domain nyata dan CSRF origin HTTPS.
- Pasang reverse proxy dan TLS.
- Jangan publish PostgreSQL/Redis ke internet; gunakan internal network atau bind localhost + SSH tunnel.
- Lindungi Flower dengan auth/network policy atau jangan expose.
- Jalankan `manage.py check --deploy`.

## 10. Fase L6 — Data Safety

- Jadwalkan backup SSOT.
- Enkripsi/isolasi lokasi backup.
- Uji restore ke database staging kosong.
- Verifikasi jumlah project, owner, AHSP referensi, pricing, dan migration state.
- Hentikan PostgreSQL native lama setelah bukti Docker SSOT dan restore tersedia.

## 11. Fase L7 — Quality Gate dan UAT

1. Perbaiki test permission import sehingga entitlement aktif dan test benar-benar menguji permission layer.
2. Pastikan CI HEAD hijau.
3. Jalankan backend suite, frontend suite, clean build, dan dependency audit.
4. Ulang browser/runtime gate pada image production.
5. UAT akun pemilik proyek nyata:
   - dashboard dan kepemilikan project;
   - List Pekerjaan;
   - Volume dan formula;
   - Template AHSP dan Harga Item;
   - Rekap/Rincian/Jadwal;
   - import AHSP 2026;
   - export/import project;
   - pricing/subscription.
6. Tutup QA Gate D Opaque ID dan mulai monitoring tujuh hari.

## 12. Fase L8 — Release dan GO/NO-GO

### GO hanya bila

- production image clean dan reproducible;
- tidak ada P0/P1 terbuka;
- backup dan restore drill lulus;
- CI dan browser gate hijau;
- UAT disetujui;
- rollback image/database tersedia;
- monitoring dan PIC incident ditetapkan.

### NO-GO otomatis bila

- app `referensi` tidak tersedia di image;
- secret/host/TLS production belum valid;
- CI merah;
- DB backup belum dapat direstore;
- project owner/data tidak tervalidasi;
- ada migration drift atau static manifest error.

## 13. Urutan Eksekusi Minimum

`L0 → L1 → L2 → L3 → L5 → L6 → L7 → L8`

L4 berjalan bertahap dan tidak memblokir launch selama compatibility code aman. Dependency audit dapat berjalan paralel setelah L1.

## 14. Perubahan yang Memerlukan Konfirmasi

- menghapus `cleanup_archive/` dari HEAD setelah arsip eksternal dibuat;
- menonaktifkan service PostgreSQL native;
- mengubah password/nonaktifkan akun admin dev;
- mengganti port/network exposure;
- menjalankan production compose atau migrasi terhadap SSOT;
- mengubah PR besar menjadi release candidate/merge.
