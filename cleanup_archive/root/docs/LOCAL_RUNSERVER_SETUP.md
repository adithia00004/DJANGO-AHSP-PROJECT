# Local Runserver Preparation Guide

Use this checklist to make sure the AHSP Django project can be started with `python manage.py runserver` on any developer PC (Windows or Linux) and shared over the local network.

## 1. Prerequisites
- **Python**: 3.11 or newer (tested on 3.11.14 & 3.13.1).
- **Git** and **pip**.
- **PostgreSQL 15+** (preferred) or use SQLite for quick smoke tests.
- **Redis 7+** (optional, only needed if you want to exercise rate limiting / cache features locally).
- Windows Firewall (or ufw) must allow inbound traffic on the port you plan to expose (default 8000).

## 2. Clone + virtual environment
```powershell
git clone <repo-url>
cd "DJANGO AHSP PROJECT"
python -m venv .venv
.venv\Scripts\activate      # On Linux/Mac: source .venv/bin/activate
python -m pip install --upgrade pip
```

## 3. Install dependencies
For a full dev experience (pytest, debug toolbar, etc.):
```powershell
pip install -r requirements\development.txt
```
`requirements.txt` also works if you only need the minimal stack.

## 4. Configure environment variables
1. Copy the sample file:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Adjust the following keys (all live inside `.env`):
   - `DJANGO_ENV=development` (default). Leave it unless you intentionally want to test staging/production settings.
   - `DJANGO_SECRET_KEY`: any random string for local use.
   - `DJANGO_DEBUG=True`.
   - `DJANGO_ALLOWED_HOSTS`: include `localhost`, `127.0.0.1`, and the LAN IP of the host machine (e.g. `192.168.1.5`).
   - `DJANGO_CSRF_TRUSTED_ORIGINS`: add `http://<lan-ip>:8000` so forms work from another PC.
   - Database block (`POSTGRES_*`) or set `DJANGO_DB_ENGINE=sqlite` if you prefer SQLite.
   - Cache block: leave default (`locmem`) or set `CACHE_BACKEND=redis` + `REDIS_URL=redis://127.0.0.1:6379/1` if Redis is running.
   - Optional e-mail defaults (`EMAIL_*`) if you need real SMTP.

> `.env.production.example` and `.env.staging.example` are available if you need stricter presets for deployments.

## 5. Database setup
### Option A – PostgreSQL (recommended)
```sql
-- From psql
CREATE DATABASE ahsp_sni_db;
CREATE USER ahsp_user WITH PASSWORD 'change-me';
ALTER ROLE ahsp_user SET client_encoding TO 'UTF8';
GRANT ALL PRIVILEGES ON DATABASE ahsp_sni_db TO ahsp_user;
```
Update `.env` with the same credentials (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`).

### Option B – SQLite (quick smoke tests)
Set `DJANGO_DB_ENGINE=sqlite` in `.env` (or export before running commands). The database file `db.sqlite3` will be created automatically.

## 6. Optional services
- **Redis**: run `docker run -p 6379:6379 redis:7-alpine` or use the helper `scripts/setup-redis.sh` (Linux/macOS). Then set `CACHE_BACKEND=redis`.
- **Celery workers** (Phase 5 features): start Redis first, then use `scripts/start_celery_worker.sh` / `start_celery_beat.sh` / `start_flower.sh` as needed.

## 7. Prepare the Django database
```powershell
python manage.py migrate
python manage.py createcachetable   # Required because sessions use cached_db
python manage.py createsuperuser    # Needed to log in to admin/Referensi
```
Optional sample data (gives you AHSP rows to browse immediately):
```powershell
python manage.py loaddata backup_ahsp.json
```

## 8. Quick health checks
```powershell
python manage.py check
pytest --maxfail=1 --disable-warnings
```
Running the full pytest suite is optional but ensures the install matches CI.

## 9. Run the development server
### Local-only
```powershell
python manage.py runserver
```

### Share over LAN
1. Make sure `.env` includes your host LAN IP inside `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`.
2. Either:
   ```powershell
   python manage.py runserver 0.0.0.0:8000
   ```
   **or** run the helper script (auto-detects IP & can force SQLite):
   ```powershell
   scripts\run-dev-lan.ps1 -Port 8000 -UseSQLite
   ```
3. On the client PC, browse to `http://<host-ip>:8000/`. Allow the connection through Windows Firewall the first time.

## 10. Useful follow-up commands
- `python manage.py collectstatic --noinput` (only if you plan to package the app or test WhiteNoise locally).
- `python manage.py warm_cache` to pre-populate Referensi dropdown caches.
- `python manage.py refresh_stats` to update materialized stats.

## 11. Troubleshooting
- Use `python manage.py shell` to ensure environment variables are loaded.
- If migrations fail on PostgreSQL, confirm the user has CREATEDB or run them as the `postgres` superuser.
- Redis connection errors: keep `CACHE_BACKEND=locmem` during development.
- More detailed checklists live under `docs/TROUBLESHOOTING_GUIDE.md` and `docs/DEPLOYMENT_GUIDE.md`.
