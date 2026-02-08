# PRE-PRODUCTION LAUNCH CHECKLIST
## Django AHSP Project

Dokumen ini adalah checklist eksekusi launch (GO/NO-GO).
Dokumen audit temuan teknis tetap di `AUDIT_PRE_LAUNCH.md`.
Dokumen agenda provider/pihak ketiga ada di `AGENDA_PROVIDER_PIHAK_KETIGA.md`.

Tanggal update: 2026-02-08 (automation refresh)

---

## 1) GO / NO-GO GATE

Status launch hanya boleh `GO` jika semua item P0 di bawah sudah `PASS`.

| Gate | Status | Bukti/Command |
|---|---|---|
| P0 security fixes sudah diterapkan | [x] | `python manage.py check` |
| Secret default sudah diganti | [x] | review `SECRETS_LOCAL.md` + `.env.production` |
| DB koneksi production valid | [x] | `DJANGO_ENV=production python manage.py shell --settings=config.settings.production -c "from django.db import connection; connection.cursor().execute('SELECT 1'); print('DB OK')"` |
| Migration production sukses | [x] | `DJANGO_ENV=production python manage.py migrate --settings=config.settings.production --noinput` |
| CSRF/IDOR regression test lulus | [x] | `python manage.py test detail_project.tests_api_v2_access detail_project.tests_export_csrf detail_project.tests_page_security_audit --keepdb --noinput` |
| Export tier/subscription test lulus | [x] | `python manage.py test subscriptions.tests detail_project.tests_export_access referensi.tests.test_import_permissions --keepdb --noinput` |
| Functional smoke test otomatis lulus | [x] | `python manage.py test dashboard.tests_prelaunch_smoke --keepdb --noinput` |
| Pytest suite aktif lulus | [x] | `pytest -q` -> `79 passed` |

Jika ada satu saja gagal, status tetap `NO-GO`.

---

## 2) WAJIB SEBELUM SWITCH TRAFFIC

### A. Secret & Credential
- [x] `DJANGO_SECRET_KEY` bukan default (`insecure-dev-key`).
- [x] `POSTGRES_PASSWORD` bukan `password`.
- [x] `REDIS_PASSWORD` bukan `redis_password`.
- [ ] Jika payment aktif: `MIDTRANS_SERVER_KEY` + `MIDTRANS_CLIENT_KEY` terisi benar.
- [x] Simpan nilai aktual hanya di `SECRETS_LOCAL.md` (lokal, private).

### B. Environment Production
- [x] `DJANGO_ENV=production`.
- [x] `DJANGO_ALLOWED_HOSTS` sudah diisi domain kandidat launch (`rabdashboard.com`).
- [x] `DJANGO_CSRF_TRUSTED_ORIGINS` sudah diisi domain HTTPS kandidat launch (`rabdashboard.com`).
- [x] `DEBUG=False` terkonfirmasi di production settings.

### C. Database
- [ ] Backup DB terakhir tersedia (timestamp dicatat).
- [ ] Restore drill minimal 1x pernah diuji di staging.
- [ ] Akses DB hanya dari network internal/server yang diizinkan.

### D. Functional Smoke Test
- [x] Login/logout/signup baseline endpoint berjalan (otomatis).
- [ ] Verifikasi email end-to-end (butuh SMTP/provider aktif).
- [x] Dashboard buka normal.
- [x] Create/edit/delete project oleh owner berjalan.
- [x] Non-owner tidak bisa akses project owner lain.
- [x] Export flow inti berjalan sesuai policy subscription.

Command otomatis gabungan:
- `python scripts/prelaunch_autocheck.py`
  - Menjalankan check runtime production, DB connectivity, migration check, security regression, dan functional smoke.
  - Status saat ini PASS untuk domain kandidat `rabdashboard.com`.

---

## 3) OPSI ARSITEKTUR LAUNCH AWAL (SKALA KECIL)

Untuk launch awal, valid memakai 1 server (mis. VPS):
- Django app
- PostgreSQL
- Redis
- Reverse proxy + HTTPS

Catatan:
- DB tetap wajib dari awal.
- Saat traffic tumbuh, baru pertimbangkan pemisahan DB ke managed/dedicated.

---

## 4) POST-LAUNCH 24 JAM PERTAMA

- [ ] Pantau error rate (HTTP 5xx).
- [ ] Pantau login failure rate.
- [ ] Pantau query lambat DB.
- [ ] Pantau memory/CPU server.
- [ ] Pantau job Celery (jika aktif).
- [ ] Verifikasi backup harian benar-benar berjalan.

---

## 5) ROLLBACK MINIMUM

- [ ] Simpan backup DB sebelum deploy.
- [ ] Simpan image/tag release sebelumnya.
- [ ] Jika incident kritis: rollback app + restore DB sesuai timestamp.
- [ ] Catat RCA singkat dan update `AUDIT_PRE_LAUNCH.md`.

---

## 6) ROLLBACK MIGRASI IRREVERSIBLE (WAJIB SIAP)

Gunakan prosedur ini untuk migrasi data yang ditandai berisiko irreversible.

1. Sebelum deploy, buat backup penuh:
   - `pg_dump -h <DB_HOST> -U <DB_USER> -d <DB_NAME> -Fc -f pre_migration_<timestamp>.dump`
2. Jalankan migrasi di staging lebih dulu dan catat migration target rollback:
   - `python manage.py showmigrations referensi`
3. Jika deploy production gagal pasca-migrasi:
   - Stop traffic/write sementara.
   - Rollback code ke image/tag release sebelumnya.
   - Kembalikan database dari backup:
     - `dropdb -h <DB_HOST> -U <DB_USER> <DB_NAME>`
     - `createdb -h <DB_HOST> -U <DB_USER> <DB_NAME>`
     - `pg_restore -h <DB_HOST> -U <DB_USER> -d <DB_NAME> --clean --if-exists pre_migration_<timestamp>.dump`
4. Verifikasi pasca-restore:
   - `python manage.py migrate --plan --settings=config.settings.production`
   - Smoke test login + dashboard + export inti.
5. Dokumentasikan incident + keputusan lanjut/hold launch.

---

## 7) OPEN ITEMS DARI AUDIT (BELUM CLOSED)

Sebelum launch production, item berikut wajib diputuskan:
- [x] Rotasi secret/password core yang sempat tersimpan lama.
- [x] Hardening monitoring endpoint (API key + rate limit).
- [x] Triage risiko `CASCADE` pada model kritis (retensi inti diterapkan: `Project.owner=PROTECT`, `DetailAHSPAudit.pekerjaan=SET_NULL`, hard-delete Project via admin dinonaktifkan).
- [x] Sanitasi `log.metadata|safe` pada audit detail template.

---

## 8) KEPUTUSAN LAUNCH

- Tanggal:
- Environment:
- PIC:
- Status akhir: `GO / NO-GO`
- Catatan:
