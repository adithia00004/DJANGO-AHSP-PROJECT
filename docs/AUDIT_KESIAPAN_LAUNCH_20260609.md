# Audit Kesiapan Launch & Dead Code — Basis Implementation Plan

**Tanggal:** 2026-06-09

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
**Branch:** `checkpoint/save-sync-plan-20260608` (verifikasi ulang dari HEAD `e05f0748`)
**Metode:** pemeriksaan source + runtime Docker (`manage.py check`, suite test, baca `production.py`/compose), inventaris file & penanda dead-code.
**Tujuan:** menjadi dasar penyusunan implementation plan menuju launch.
**Pelengkap:** `SISA_PEKERJAAN_DAN_KESIAPAN_PRODUKSI_20260609.md`, `IMPLEMENTATION_PLAN_SAVE_SYNC_20260608.md`, `OPAQUE_ID_CHECKLIST.md`.

---

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
