# Runbook Deploy: L5 (Security/TLS) & L6 (Data Safety)

Scaffolding siap; langkah ini hanya butuh **input/keputusanmu** (domain, secrets) dan
masuk daftar "Perubahan yang Memerlukan Konfirmasi". Tidak ada yang dijalankan otomatis.

## Prasyarat
- Server publik dengan domain mengarah ke IP-nya (A record), port 80/443 terbuka.
- Docker + Docker Compose terpasang di server.

## L5 — Production Security & TLS

1. **Siapkan secrets** — salin `.env.production.example` → `.env.production`, isi:
   - `DJANGO_ENV=production`
   - `DJANGO_SECRET_KEY` = random ≥50 char (bukan placeholder)
   - `DJANGO_ALLOWED_HOSTS` = domain nyata (mis. `ahsp.domainmu.id`)
   - `DJANGO_CSRF_TRUSTED_ORIGINS` = `https://ahsp.domainmu.id`
   - `POSTGRES_PASSWORD` / `REDIS_PASSWORD` = kuat (bukan `password`/default)
   - (opsional) `SENTRY_DSN`
   `production.py` akan menolak nilai placeholder/host dev — ini disengaja.

2. **Kunci jaringan** (di `docker-compose.prod.yml`): hapus publish port host untuk
   `web` (8000), `db` (5432), `redis` (6379). Hanya **Caddy** (80/443) yang terekspos.

3. **Jangan buat dev-admin** — entrypoint hanya membuat `admin/admin` saat
   `DJANGO_ENV=development`. Dengan `production`, ini tidak terjadi. Buat superuser
   nyata: `docker exec -it ahsp_web python manage.py createsuperuser`.

4. **Jalankan stack + TLS** (Caddy auto Let's Encrypt):
   ```bash
   DOMAIN=ahsp.domainmu.id docker compose -p ahsp \
     -f docker-compose.prod.yml \
     -f deploy/docker-compose.prod.proxy.yml up -d
   ```

5. **Verifikasi keamanan**:
   ```bash
   docker exec ahsp_web python manage.py check --deploy   # harus 0 issue serius
   curl -I https://ahsp.domainmu.id/                      # 200/302 + HSTS header
   ```

## L6 — Data Safety

1. **Backup terjadwal** — `scripts/safe_backup_db.sh` membuat dump `-Fc` + verifikasi.
   Jadwalkan (Linux cron contoh harian 02:00):
   ```
   0 2 * * * cd /path/repo && bash scripts/safe_backup_db.sh >> backups/backup.log 2>&1
   ```
   Simpan backup ke lokasi terenkripsi/terpisah (mis. object storage + enkripsi).

2. **Restore drill** (wajib sebelum percaya backup) — restore ke DB scratch + cek baris,
   tanpa menyentuh DB live:
   ```bash
   bash scripts/restore_drill_db.sh ./backups/<file>.dump
   # [OK] Restore drill LULUS ... projects=NNN
   ```

3. **Matikan jalur DB lama** — setelah backup + restore drill terbukti dan Docker SSOT
   stabil, hentikan PostgreSQL native agar tak ada penulisan ganda:
   ```powershell
   Stop-Service postgresql-x64-16    # konfirmasi dulu; reversibel via Start-Service
   ```

## Acceptance (gate L5/L6)
- `check --deploy` bersih; HTTPS aktif; tidak ada port DB/Redis/web terekspos publik.
- Tidak ada kredensial default; superuser nyata dibuat.
- Backup terjadwal + **restore drill LULUS**.
- Hanya satu DB sumber (PG16 native dimatikan).
