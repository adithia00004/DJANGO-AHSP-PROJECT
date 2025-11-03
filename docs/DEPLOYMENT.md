# Deployment Guide

## Prerequisites

- Python 3.12+
- PostgreSQL 16 (or compatible)
- Environment variables configured for production (see `.env.production.example`)
- Static file hosting (S3, CDN, or server-side via WhiteNoise)

## Steps

1. **Clone & set environment**
   ```bash
   git clone <repo>
   cd DJANGO AHSP PROJECT
   python -m venv .venv
   source .venv/bin/activate  # or .\.venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```
2. **Configure settings**
   - Export `DJANGO_ENV=production`
   - Copy `.env.production.example` → `.env.production` and update secrets
   - Set `DJANGO_SETTINGS_MODULE=config.settings`
   - Ensure `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, and Postgres variables are filled
3. **Database migrations**
   ```bash
   python manage.py migrate
   python manage.py createcachetable
   ```
4. **Collect static assets**
   ```bash
   DJANGO_ENV=production python manage.py collectstatic --noinput
   ```
5. **Create superuser and assign groups**
   ```bash
   python manage.py createsuperuser
   # Inside admin, group the new user into Referensi Admin for full access
   ```
6. **Warm caches and materialized views (optional)**
   ```bash
   DJANGO_ENV=production python manage.py warm_cache
   DJANGO_ENV=production python manage.py refresh_stats
   ```
7. **Start application**
   - Gunicorn example:
     ```bash
     DJANGO_ENV=production gunicorn config.wsgi:application --bind 0.0.0.0:8000
     ```
   - Or use the provided `run-waitress.sh/ps1` scripts for Windows-friendly deployments.

## Scheduled Maintenance

- Refresh Referensi statistics nightly (`python manage.py refresh_stats`)
- Rotate audit logs or archive `django_simple_history` tables if necessary
- Monitor CI status (GitHub Actions) to ensure tests remain green before deploys
