# Jadwal Pekerjaan - Deployment Guide

## Overview

This guide covers deploying the Jadwal Pekerjaan feature to production environments, including database migrations, static files, configuration, and post-deployment verification.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Database Migration](#database-migration)
4. [Static Files](#static-files)
5. [Environment Configuration](#environment-configuration)
6. [Deployment Steps](#deployment-steps)
7. [Post-Deployment Verification](#post-deployment-verification)
8. [Rollback Procedures](#rollback-procedures)
9. [Monitoring & Maintenance](#monitoring--maintenance)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **Python**: 3.8+ (tested on 3.10)
- **Django**: 4.0+ (tested on 4.2)
- **Database**: PostgreSQL 12+ (or MySQL 8.0+)
- **Web Server**: Nginx or Apache
- **WSGI Server**: Gunicorn or uWSGI
- **OS**: Linux (Ubuntu 20.04+ recommended)

### Python Dependencies

Ensure these packages are in `requirements.txt`:

```txt
Django>=4.2
psycopg2-binary>=2.9  # For PostgreSQL
python-dateutil>=2.8
```

### Database Setup

The following models must exist:

- `TahapPelaksanaan` (detail_project/models.py)
- `PekerjaanTahapan` (detail_project/models.py)
- `Pekerjaan` (detail_project/models.py)

---

## Pre-Deployment Checklist

### 1. Code Review

- [ ] All tests passing (`pytest detail_project/tests/test_tahapan*.py`)
- [ ] Code reviewed and approved
- [ ] No debug statements or console.logs in production code
- [ ] All TODOs resolved or documented

### 2. Database Backup

**CRITICAL**: Always backup database before deployment!

```bash
# PostgreSQL backup
pg_dump -U postgres -d your_database > backup_$(date +%Y%m%d_%H%M%S).sql

# MySQL backup
mysqldump -u root -p your_database > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 3. Environment Variables

Verify production settings:

```bash
# .env or environment variables
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
SECRET_KEY=your-production-secret-key
DATABASE_URL=postgresql://user:pass@localhost/dbname
```

### 4. Static Files Check

```bash
# Ensure static files are configured
python manage.py collectstatic --noinput --dry-run
```

---

## Database Migration

### Step 1: Review Migration Files

Check all migration files in `detail_project/migrations/`:

```bash
# List pending migrations
python manage.py showmigrations detail_project
```

Expected migrations for Jadwal Pekerjaan:
- `0XXX_add_tahapan_models.py` - Creates TahapPelaksanaan and PekerjaanTahapan models
- `0XXX_add_tahapan_flags.py` - Adds is_auto_generated and generation_mode fields

### Step 2: Run Migrations in Production

```bash
# 1. Activate virtual environment
source /path/to/venv/bin/activate

# 2. Navigate to project directory
cd /path/to/DJANGO-AHSP-PROJECT

# 3. Run migrations
python manage.py migrate detail_project --database=default

# 4. Verify migrations applied
python manage.py showmigrations detail_project
```

### Step 3: Verify Database Schema

```sql
-- PostgreSQL verification
\d detail_project_tahappelaksanaan
\d detail_project_pekerjaan_tahapan

-- Expected columns in TahapPelaksanaan:
-- id, project_id, nama, urutan, deskripsi,
-- tanggal_mulai, tanggal_selesai, created_at, updated_at,
-- is_auto_generated, generation_mode

-- Expected columns in PekerjaanTahapan:
-- id, pekerjaan_id, tahapan_id, proporsi_volume, created_at, updated_at
```

---

## Static Files

### Step 1: Collect Static Files

```bash
# Collect all static files to STATIC_ROOT
python manage.py collectstatic --noinput

# Expected output:
# - detail_project/static/detail_project/js/kelola_tahapan_grid.js
# - detail_project/static/detail_project/css/kelola_tahapan_grid.css
# - Bootstrap, jQuery, and other dependencies
```

### Step 2: Configure Web Server

#### Nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Static files
    location /static/ {
        alias /path/to/DJANGO-AHSP-PROJECT/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /path/to/DJANGO-AHSP-PROJECT/media/;
    }

    # Django application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Apache Configuration

```apache
<VirtualHost *:80>
    ServerName yourdomain.com

    # Static files
    Alias /static /path/to/DJANGO-AHSP-PROJECT/staticfiles
    <Directory /path/to/DJANGO-AHSP-PROJECT/staticfiles>
        Require all granted
    </Directory>

    # Django application
    ProxyPass /static !
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/
</VirtualHost>
```

### Step 3: Verify Static Files Accessible

```bash
# Test static file access
curl -I https://yourdomain.com/static/detail_project/js/kelola_tahapan_grid.js

# Expected: HTTP 200 OK
```

---

## Environment Configuration

### settings.py Configuration

```python
# settings.py or settings/production.py

# Security
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']
SECRET_KEY = os.environ.get('SECRET_KEY')

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Session & CSRF
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/error.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}
```

---

## Deployment Steps

### Option A: Manual Deployment

```bash
# 1. Pull latest code
cd /path/to/DJANGO-AHSP-PROJECT
git pull origin main

# 2. Activate virtual environment
source venv/bin/activate

# 3. Install/update dependencies
pip install -r requirements.txt

# 4. Run migrations
python manage.py migrate

# 5. Collect static files
python manage.py collectstatic --noinput

# 6. Restart application server
sudo systemctl restart gunicorn
# or
sudo systemctl restart uwsgi

# 7. Restart web server
sudo systemctl restart nginx
```

### Option B: Automated Deployment (Using Fabric)

Create `fabfile.py`:

```python
from fabric import task

@task
def deploy(c):
    """Deploy to production"""
    code_dir = '/path/to/DJANGO-AHSP-PROJECT'

    # Pull latest code
    with c.cd(code_dir):
        c.run('git pull origin main')

        # Activate venv and update
        c.run('source venv/bin/activate && pip install -r requirements.txt')

        # Run migrations
        c.run('source venv/bin/activate && python manage.py migrate')

        # Collect static
        c.run('source venv/bin/activate && python manage.py collectstatic --noinput')

    # Restart services
    c.sudo('systemctl restart gunicorn')
    c.sudo('systemctl restart nginx')

    print("✅ Deployment completed!")
```

Run deployment:

```bash
fab -H user@production-server deploy
```

### Option C: Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Run migrations
RUN python manage.py migrate

# Expose port
EXPOSE 8000

# Start Gunicorn
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - .:/app
      - static_volume:/app/staticfiles
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db

  db:
    image: postgres:13
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=ahsp_db
      - POSTGRES_USER=ahsp_user
      - POSTGRES_PASSWORD=securepassword

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - static_volume:/app/staticfiles
    ports:
      - "80:80"
    depends_on:
      - web

volumes:
  postgres_data:
  static_volume:
```

Deploy with Docker:

```bash
docker-compose up -d --build
```

---

## Post-Deployment Verification

### 1. Health Check

```bash
# Check application is running
curl -I https://yourdomain.com/

# Check API endpoint
curl -H "Cookie: sessionid=YOUR_SESSION" \
     https://yourdomain.com/detail_project/api/project/1/tahapan/
```

### 2. Functional Testing

Test these critical features:

#### A. Load Jadwal Pekerjaan Page

1. Login to application
2. Navigate to a project
3. Click "Jadwal Pekerjaan" tab
4. **Expected**: Grid loads with pekerjaan list and time columns
5. **Check console**: No JavaScript errors

#### B. Switch Time Scale Mode

1. Select "Weekly" mode
2. Click confirm in dialog
3. **Expected**:
   - Loading indicator appears with progress messages
   - Grid regenerates with weekly columns
   - No errors in console
   - Toast notification: "Mode switched to weekly"

#### C. Edit and Save

1. Double-click a cell in grid
2. Enter value (e.g., 33.33)
3. Press Enter
4. Click "Save All Changes"
5. **Expected**:
   - Loading overlay with "Saving changes..." message
   - Toast notification: "All changes saved successfully"
   - Cell turns blue (saved state)
   - Status bar shows "0 changes"

#### D. Page Refresh Persistence

1. After saving, refresh the page (F5)
2. **Expected**:
   - Saved values remain in grid
   - Blue cells persist

### 3. Database Verification

```sql
-- Check tahapan were created
SELECT COUNT(*), generation_mode
FROM detail_project_tahappelaksanaan
WHERE project_id = 1 AND is_auto_generated = TRUE
GROUP BY generation_mode;

-- Check assignments were saved
SELECT COUNT(*)
FROM detail_project_pekerjaan_tahapan pt
JOIN detail_project_tahappelaksanaan t ON pt.tahapan_id = t.id
WHERE t.project_id = 1;

-- Verify proporsi values
SELECT
  p.kode_pekerjaan,
  t.nama AS tahapan,
  pt.proporsi_volume
FROM detail_project_pekerjaan_tahapan pt
JOIN detail_project_pekerjaan p ON pt.pekerjaan_id = p.id
JOIN detail_project_tahappelaksanaan t ON pt.tahapan_id = t.id
WHERE p.project_id = 1
ORDER BY p.kode_pekerjaan, t.urutan;
```

### 4. Performance Check

```bash
# Check page load time
time curl https://yourdomain.com/detail_project/project/1/jadwal-pekerjaan/

# Check API response time
time curl -H "Cookie: sessionid=YOUR_SESSION" \
          https://yourdomain.com/detail_project/api/project/1/tahapan/
```

**Target Performance**:
- Page load: < 2 seconds
- API response: < 500ms
- Grid render: < 1 second for 100 pekerjaan

---

## Rollback Procedures

### Emergency Rollback

If deployment fails or critical bugs discovered:

```bash
# 1. Restore database backup
psql -U postgres -d your_database < backup_20251026_120000.sql

# 2. Revert code to previous version
git revert HEAD
# or
git reset --hard <previous-commit-hash>

# 3. Restart services
sudo systemctl restart gunicorn
sudo systemctl restart nginx

# 4. Clear cache if using Redis/Memcached
redis-cli FLUSHALL
```

### Partial Rollback

If only JavaScript needs rollback:

```bash
# 1. Git checkout previous version of JS file
git checkout <previous-commit> detail_project/static/detail_project/js/kelola_tahapan_grid.js

# 2. Collect static
python manage.py collectstatic --noinput

# 3. Clear browser cache or use versioned static URL
```

---

## Monitoring & Maintenance

### 1. Application Monitoring

#### Monitor Error Logs

```bash
# Django error log
tail -f /var/log/django/error.log

# Nginx error log
tail -f /var/log/nginx/error.log

# Gunicorn log
sudo journalctl -u gunicorn -f
```

#### Set Up Alerts

Use tools like:
- **Sentry**: For error tracking and alerting
- **New Relic**: For APM and performance monitoring
- **Datadog**: For infrastructure and application monitoring

Example Sentry setup:

```python
# settings.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,
    send_default_pii=True
)
```

### 2. Database Maintenance

```bash
# Weekly database backup
0 2 * * 0 /usr/bin/pg_dump -U postgres your_database > /backups/weekly_backup.sql

# Monthly vacuum (PostgreSQL)
0 3 1 * * psql -U postgres -d your_database -c "VACUUM ANALYZE;"
```

### 3. Cleanup Old Data

Create management command `cleanup_old_tahapan.py`:

```python
# detail_project/management/commands/cleanup_old_data.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from detail_project.models import TahapPelaksanaan

class Command(BaseCommand):
    help = 'Clean up auto-generated tahapan older than 6 months with no assignments'

    def handle(self, *args, **options):
        cutoff_date = timezone.now() - timedelta(days=180)

        old_tahapan = TahapPelaksanaan.objects.filter(
            is_auto_generated=True,
            created_at__lt=cutoff_date,
            pekerjaan_items__isnull=True  # No assignments
        )

        count = old_tahapan.count()
        old_tahapan.delete()

        self.stdout.write(
            self.style.SUCCESS(f'Deleted {count} old unused tahapan')
        )
```

Run monthly:

```bash
# Cron job
0 1 1 * * cd /path/to/project && python manage.py cleanup_old_data
```

---

## Troubleshooting

### Issue 1: Static Files Not Loading (404)

**Symptoms**: JavaScript/CSS files return 404

**Solutions**:
```bash
# 1. Verify STATIC_ROOT and STATIC_URL
python manage.py diffsettings | grep STATIC

# 2. Re-collect static files
python manage.py collectstatic --clear --noinput

# 3. Check Nginx/Apache config
nginx -t
sudo systemctl reload nginx

# 4. Verify file permissions
ls -la /path/to/staticfiles/
chmod -R 755 /path/to/staticfiles/
```

### Issue 2: Database Migration Errors

**Symptoms**: "relation does not exist" or migration conflicts

**Solutions**:
```bash
# 1. Check migration status
python manage.py showmigrations

# 2. Fake previous migrations if schema already exists
python manage.py migrate detail_project 0XXX --fake

# 3. Create fresh migration
python manage.py makemigrations detail_project
python manage.py migrate detail_project

# 4. If all else fails, dump data and recreate
python manage.py dumpdata detail_project > backup.json
python manage.py migrate detail_project zero
python manage.py migrate detail_project
python manage.py loaddata backup.json
```

### Issue 3: CSRF Token Errors

**Symptoms**: "CSRF verification failed" on POST requests

**Solutions**:
```python
# 1. Verify CSRF middleware enabled
# settings.py
MIDDLEWARE = [
    'django.middleware.csrf.CsrfViewMiddleware',
    ...
]

# 2. Check CSRF cookie settings
CSRF_COOKIE_SECURE = True  # Only if HTTPS
CSRF_COOKIE_HTTPONLY = False  # JavaScript needs access

# 3. Verify CSRF token in JavaScript
console.log('CSRF Token:', getCookie('csrftoken'));
```

### Issue 4: Slow Performance

**Symptoms**: Grid takes >5 seconds to load

**Solutions**:
```python
# 1. Add database indexes
class TahapPelaksanaan(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['project', 'is_auto_generated']),
            models.Index(fields=['project', 'generation_mode']),
        ]

# 2. Optimize queries with select_related/prefetch_related
tahapan = TahapPelaksanaan.objects.filter(
    project=project
).prefetch_related('pekerjaan_items').order_by('urutan')

# 3. Add caching
from django.core.cache import cache

def get_tahapan_summary(project):
    cache_key = f'tahapan_summary_{project.id}'
    cached = cache.get(cache_key)
    if cached:
        return cached

    result = _compute_summary(project)
    cache.set(cache_key, result, 300)  # Cache 5 minutes
    return result

# 4. Database query profiling
from django.db import connection
print(connection.queries)
```

### Issue 5: Assignment Conversion Inaccuracies

**Symptoms**: Total proporsi changes after mode switch

**Solutions**:
```python
# 1. Run validation command
python manage.py shell
>>> from detail_project.models import Pekerjaan, PekerjaanTahapan
>>> for p in Pekerjaan.objects.filter(project_id=1):
...     total = PekerjaanTahapan.objects.filter(pekerjaan=p).aggregate(Sum('proporsi_volume'))['proporsi_volume__sum'] or 0
...     if abs(total - 100) > 0.5:
...         print(f"Pekerjaan {p.id}: Total = {total}%")

# 2. Re-run regeneration with conversion
# Through UI or API call with convert_assignments=true

# 3. Manual fix if needed
python manage.py fix_tahapan_assignments --project-id=1
```

---

## Security Considerations

### 1. Authentication & Authorization

```python
# All views require login
@login_required
def api_list_create_tahapan(request, project_id):
    # Verify ownership
    project = _owner_or_404(project_id, request.user)
    ...
```

### 2. Input Validation

```python
# Validate proporsi range
if not (0 <= proporsi <= 100):
    return JsonResponse({'ok': False, 'error': 'Invalid proporsi'}, status=400)
```

### 3. SQL Injection Protection

Django ORM protects against SQL injection. **Never** use raw SQL with user input:

```python
# ❌ DANGEROUS
cursor.execute(f"SELECT * FROM tahapan WHERE nama = '{user_input}'")

# ✅ SAFE
TahapPelaksanaan.objects.filter(nama=user_input)
```

### 4. XSS Protection

Template rendering auto-escapes HTML. For JavaScript values:

```javascript
// ✅ SAFE - Django template escapes JSON
const projectId = {{ project.id|safe }};  // Numbers are safe
const projectName = "{{ project.name|escapejs }}";  // Strings escaped
```

---

## Conclusion

Following this deployment guide ensures:

- ✅ Safe database migrations
- ✅ Proper static file serving
- ✅ Production-ready configuration
- ✅ Comprehensive post-deployment testing
- ✅ Rollback capability if issues occur
- ✅ Ongoing monitoring and maintenance

For additional support, contact the development team or refer to:
- [User Guide](JADWAL_PEKERJAAN_USER_GUIDE.md)
- [API Documentation](JADWAL_PEKERJAAN_API.md)

---

**Document Version**: 1.0
**Last Updated**: 26 Oktober 2025
**Maintained By**: Development Team
