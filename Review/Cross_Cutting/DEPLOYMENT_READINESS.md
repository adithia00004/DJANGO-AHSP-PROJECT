# Cross-Cutting: Deployment Readiness Review

**Status:** `[~]` BASELINE TERIMPORT, REVALIDASI SSOT BERJALAN
**Terakhir diperbarui:** 2026-02-16

---

## Scope

Review kesiapan deployment ke production: Docker, environment, CI/CD,
monitoring, backup, dan disaster recovery.

---

## Baseline Terimport (Referensi 2026-02-08)

Baseline berikut diambil dari audit/checklist sebelumnya dan akan divalidasi ulang di SSOT ini:

- Runtime check production, koneksi DB, dan migrate production pernah PASS.
- Prelaunch smoke test otomatis pernah PASS.
- Guard production (`DEBUG=False`, host/origin validation, startup safeguard) sudah ada.

Sumber referensi:
- `PRE_PRODUCTION_LAUNCH_CHECKLIST.md`
- `AUDIT_PRE_LAUNCH.md`

---

## 1. Docker & Container

| # | Check Item | File | Status | Temuan |
|---|-----------|------|--------|--------|
| D-1 | Dockerfile optimized (multi-stage) | `Dockerfile` | `[ ]` | - |
| D-2 | Docker image size reasonable | Build output | `[ ]` | - |
| D-3 | Non-root user in container | `Dockerfile` | `[ ]` | - |
| D-4 | Health check in Dockerfile | `Dockerfile` | `[ ]` | - |
| D-5 | docker-compose.prod.yml complete | `docker-compose.prod.yml` | `[ ]` | - |
| D-6 | Volume mounts for media/static | `docker-compose.prod.yml` | `[ ]` | - |
| D-7 | Restart policy configured | `docker-compose.prod.yml` | `[ ]` | - |
| D-8 | Resource limits (memory, CPU) | `docker-compose.prod.yml` | `[ ]` | - |

## 2. Environment & Secrets

| # | Check Item | Status | Temuan |
|---|-----------|--------|--------|
| D-9 | `.env.production` template exists | `[ ]` | - |
| D-10 | SECRET_KEY strong & unique | `[ ]` | - |
| D-11 | DEBUG = False | `[ ]` | - |
| D-12 | ALLOWED_HOSTS correct | `[ ]` | - |
| D-13 | Database credentials via env vars | `[ ]` | - |
| D-14 | Midtrans production keys configured | `[ ]` | - |
| D-15 | SendGrid API key configured | `[ ]` | - |
| D-16 | No secrets in git history | `[ ]` | - |
| D-17 | `.env` files in .gitignore | `[ ]` | - |

## 3. Web Server & WSGI

| # | Check Item | File | Status | Temuan |
|---|-----------|------|--------|--------|
| D-18 | Gunicorn workers configured | `gunicorn.conf.py` | `[ ]` | - |
| D-19 | Gunicorn timeout adequate | `gunicorn.conf.py` | `[ ]` | - |
| D-20 | Static files served by Nginx/CDN | Nginx config | `[ ]` | - |
| D-21 | Media files served correctly | Nginx config | `[ ]` | - |
| D-22 | SSL/TLS certificate | Server config | `[ ]` | - |
| D-23 | Gzip compression enabled | Nginx config | `[ ]` | - |
| D-24 | Request size limits | Nginx config | `[ ]` | - |

## 4. Database

| # | Check Item | Status | Temuan |
|---|-----------|--------|--------|
| D-25 | PostgreSQL (not SQLite) in production | `[ ]` | - |
| D-26 | PgBouncer connection pooling | `[ ]` | - |
| D-27 | All migrations applied | `[ ]` | - |
| D-28 | Database backup strategy | `[ ]` | - |
| D-29 | Backup restoration tested | `[ ]` | - |
| D-30 | Database monitoring | `[ ]` | - |

## 5. CI/CD Pipeline

| # | Check Item | File | Status | Temuan |
|---|-----------|------|--------|--------|
| D-31 | CI pipeline runs tests | `.github/workflows/ci.yml` | `[ ]` | - |
| D-32 | CI pipeline runs linting | `.github/workflows/ci.yml` | `[ ]` | - |
| D-33 | CI pipeline builds Docker image | `.github/workflows/ci.yml` | `[ ]` | - |
| D-34 | Deployment automation | CD pipeline | `[ ]` | - |
| D-35 | Rollback procedure documented | Runbook | `[ ]` | - |

## 6. Monitoring & Alerting

| # | Check Item | Status | Temuan |
|---|-----------|--------|--------|
| D-36 | Health check endpoint (`/health/`) | `[ ]` | - |
| D-37 | Readiness probe (`/health/ready/`) | `[ ]` | - |
| D-38 | Liveness probe (`/health/live/`) | `[ ]` | - |
| D-39 | Error tracking (Sentry / similar) | `[ ]` | - |
| D-40 | Application logging (structured) | `[ ]` | - |
| D-41 | Log rotation configured | `[ ]` | - |
| D-42 | Uptime monitoring | `[ ]` | - |
| D-43 | Performance monitoring | `[ ]` | - |

## 7. Backup & Disaster Recovery

| # | Check Item | Status | Temuan |
|---|-----------|--------|--------|
| D-44 | Database backup schedule | `[ ]` | - |
| D-45 | Media files backup | `[ ]` | - |
| D-46 | Backup stored off-site | `[ ]` | - |
| D-47 | Recovery Time Objective (RTO) defined | `[ ]` | - |
| D-48 | Recovery Point Objective (RPO) defined | `[ ]` | - |
| D-49 | Disaster recovery plan documented | `[ ]` | - |
| D-50 | DR drill performed | `[ ]` | - |

## 8. Pre-Launch Checklist

| # | Check Item | Status |
|---|-----------|--------|
| D-51 | Domain & DNS configured | `[ ]` |
| D-52 | Email delivery verified (SendGrid) | `[ ]` |
| D-53 | Midtrans production mode verified | `[ ]` |
| D-54 | collectstatic run | `[ ]` |
| D-55 | Django check --deploy passes | `[ ]` |
| D-56 | Seed data loaded (SubscriptionPlan, etc) | `[ ]` |
| D-57 | Superuser created | `[ ]` |
| D-58 | AHSP reference data loaded | `[ ]` |
| D-59 | Legal pages (Terms, Privacy Policy) | `[ ]` |
| D-60 | Contact / support info available | `[ ]` |

---

## Ringkasan Temuan

| Severity | Jumlah |
|----------|--------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 0 |
| LOW | 0 |

---

## Rekomendasi & Perbaikan

| # | Rekomendasi | Status |
|---|-------------|--------|
| - | Belum ada | - |

---

## Checklist Sign-off

- [ ] Docker config reviewed
- [ ] Environment secrets secure
- [ ] Web server configured
- [ ] Database production-ready
- [ ] CI/CD pipeline working
- [ ] Monitoring in place
- [ ] Backup strategy tested
- [ ] Pre-launch items complete
- [ ] Reviewer sign-off
