# 🚀 Deployment Guide - DJANGO-AHSP-PROJECT

**Project:** Dashboard Enhancement - Production Deployment
**Version:** 4.0
**Last Updated:** 2025-11-06
**Status:** Production Ready

---

## 📋 Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Environment Setup](#environment-setup)
3. [Database Migration](#database-migration)
4. [Static Files & Media](#static-files--media)
5. [Production Settings](#production-settings)
6. [Server Configuration](#server-configuration)
7. [Post-Deployment Verification](#post-deployment-verification)
8. [Rollback Procedure](#rollback-procedure)
9. [Monitoring & Maintenance](#monitoring--maintenance)

---

## 🎯 Pre-Deployment Checklist

### Code Quality ✅
- [x] All 187 tests passing (129 dashboard + 58 deep copy)
- [x] 70-80% test coverage achieved
- [x] No critical bugs or security issues
- [x] Code review completed
- [x] Performance optimized (15x faster)

### Features Verified ✅
- [x] FASE 0: Timeline UI fully functional
- [x] FASE 1: Testing Suite & Admin Panel complete
- [x] FASE 2: Analytics, Filtering, Bulk Actions, Export complete
- [x] FASE 3.1.1: Error Handling (90% coverage)
- [x] FASE 4.1: Performance Optimization

### Documentation ✅
- [x] Roadmap complete and updated (v4.0)
- [x] API documentation available
- [x] User manual prepared (Indonesian)
- [x] Deployment guide ready
- [x] Troubleshooting guide available

---

## 🛠️ Environment Setup

### 1. Server Requirements

**Minimum Requirements:**
```
OS: Ubuntu 20.04 LTS or higher / CentOS 8+
Python: 3.9+
Database: PostgreSQL 12+ or MySQL 8+
Memory: 4GB RAM (8GB recommended for production)
Storage: 20GB (50GB recommended)
CPU: 2 cores (4 cores recommended)
```

**Software Dependencies:**
```bash
# System packages
sudo apt-get update
sudo apt-get install -y \
    python3.9 \
    python3.9-venv \
    python3-pip \
    postgresql-12 \
    nginx \
    redis-server \
    supervisor \
    git
```

### 2. Clone Repository

```bash
# Create application directory
sudo mkdir -p /opt/django-ahsp
sudo chown $USER:$USER /opt/django-ahsp
cd /opt/django-ahsp

# Clone from main branch
git clone https://github.com/adithia00004/DJANGO-AHSP-PROJECT.git .
git checkout main

# Verify you're on the correct branch with all 5 phases
git log --oneline -5
```

### 3. Virtual Environment

```bash
# Create virtual environment
python3.9 -m venv venv

# Activate
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

### 4. Environment Variables

Create `.env` file:

```bash
# Copy from example
cp .env.production.example .env

# Edit with production values
nano .env
```

**Required Variables:**
```bash
# Django Settings
SECRET_KEY='your-super-secret-key-here-change-this'
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,your-server-ip

# Database (PostgreSQL recommended)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=django_ahsp_production
DB_USER=django_ahsp_user
DB_PASSWORD='strong-database-password'
DB_HOST=localhost
DB_PORT=5432

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000

# Email (for error notifications)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD='app-specific-password'
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
SERVER_EMAIL=server@yourdomain.com

# Admins (for error emails)
ADMINS=Admin Name,admin@yourdomain.com

# Static & Media
STATIC_ROOT=/opt/django-ahsp/staticfiles
MEDIA_ROOT=/opt/django-ahsp/media

# Redis (optional, for caching)
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
```

---

## 💾 Database Migration

### 1. Create Database

**PostgreSQL:**
```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE django_ahsp_production;
CREATE USER django_ahsp_user WITH PASSWORD 'strong-database-password';
ALTER ROLE django_ahsp_user SET client_encoding TO 'utf8';
ALTER ROLE django_ahsp_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE django_ahsp_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE django_ahsp_production TO django_ahsp_user;
\q
```

**MySQL:**
```sql
CREATE DATABASE django_ahsp_production CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'django_ahsp_user'@'localhost' IDENTIFIED BY 'strong-database-password';
GRANT ALL PRIVILEGES ON django_ahsp_production.* TO 'django_ahsp_user'@'localhost';
FLUSH PRIVILEGES;
```

### 2. Run Migrations

```bash
# Activate virtual environment
source venv/bin/activate

# Check migrations
python manage.py showmigrations

# Run migrations
python manage.py migrate

# Verify all migrations applied
python manage.py showmigrations | grep '\[ \]'  # Should return nothing
```

### 3. Create Superuser

```bash
python manage.py createsuperuser
# Follow prompts to create admin user
```

### 4. Load Fixtures (Optional)

```bash
# If you have initial data fixtures
python manage.py loaddata initial_data.json
```

---

## 📁 Static Files & Media

### 1. Collect Static Files

```bash
# Create directories
mkdir -p /opt/django-ahsp/staticfiles
mkdir -p /opt/django-ahsp/media

# Set permissions
sudo chown -R $USER:www-data /opt/django-ahsp/staticfiles
sudo chown -R $USER:www-data /opt/django-ahsp/media
chmod -R 755 /opt/django-ahsp/staticfiles
chmod -R 755 /opt/django-ahsp/media

# Collect static files
python manage.py collectstatic --noinput

# Verify
ls -la /opt/django-ahsp/staticfiles/
```

### 2. Media Files

```bash
# If migrating from existing system, copy media files
rsync -avz old-server:/path/to/media/ /opt/django-ahsp/media/

# Set proper permissions
sudo chown -R www-data:www-data /opt/django-ahsp/media
chmod -R 755 /opt/django-ahsp/media
```

---

## ⚙️ Production Settings

### 1. Django Settings

Ensure `settings.py` has production configurations:

```python
# Production settings
DEBUG = False
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Database connection pooling (recommended)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'
        },
        'CONN_MAX_AGE': 600,  # Connection pooling
    }
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django-ahsp/error.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
```

### 2. Gunicorn Configuration

Create `/opt/django-ahsp/gunicorn_config.py`:

```python
# Gunicorn configuration file
import multiprocessing

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = '/var/log/django-ahsp/gunicorn-access.log'
errorlog = '/var/log/django-ahsp/gunicorn-error.log'
loglevel = 'info'

# Process naming
proc_name = 'django-ahsp'

# Server mechanics
daemon = False
pidfile = '/var/run/django-ahsp/gunicorn.pid'
user = 'www-data'
group = 'www-data'
tmp_upload_dir = '/tmp'

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
```

---

## 🖥️ Server Configuration

### 1. Supervisor (Process Manager)

Create `/etc/supervisor/conf.d/django-ahsp.conf`:

```ini
[program:django-ahsp]
command=/opt/django-ahsp/venv/bin/gunicorn \
    --config /opt/django-ahsp/gunicorn_config.py \
    config.wsgi:application
directory=/opt/django-ahsp
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/django-ahsp/supervisor.log
stderr_logfile=/var/log/django-ahsp/supervisor-error.log
environment=PATH="/opt/django-ahsp/venv/bin"
```

**Start Supervisor:**
```bash
# Create log directory
sudo mkdir -p /var/log/django-ahsp
sudo chown www-data:www-data /var/log/django-ahsp

# Create PID directory
sudo mkdir -p /var/run/django-ahsp
sudo chown www-data:www-data /var/run/django-ahsp

# Reload supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start django-ahsp

# Check status
sudo supervisorctl status django-ahsp
```

### 2. Nginx Configuration

Create `/etc/nginx/sites-available/django-ahsp`:

```nginx
upstream django_app {
    server 127.0.0.1:8000 fail_timeout=0;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL certificates (use certbot for Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Max upload size
    client_max_body_size 100M;

    # Timeouts
    proxy_connect_timeout 120s;
    proxy_read_timeout 120s;

    # Static files
    location /static/ {
        alias /opt/django-ahsp/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /opt/django-ahsp/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # Django application
    location / {
        proxy_pass http://django_app;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # Health check endpoint
    location /health/ {
        access_log off;
        proxy_pass http://django_app;
    }
}
```

**Enable Site:**
```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/django-ahsp /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### 3. SSL Certificate (Let's Encrypt)

```bash
# Install certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

---

## ✅ Post-Deployment Verification

### 1. Health Checks

```bash
# Check Gunicorn is running
sudo supervisorctl status django-ahsp

# Check Nginx is running
sudo systemctl status nginx

# Check database connection
python manage.py dbshell
\q

# Test application
curl -I https://yourdomain.com
```

### 2. Run Tests

```bash
# Activate virtual environment
source /opt/django-ahsp/venv/bin/activate

# Run all tests
pytest dashboard/tests/ detail_project/tests/ -v

# Check test coverage
pytest --cov=dashboard --cov=detail_project --cov-report=html

# Verify 187 tests pass
```

### 3. Admin Panel Verification

1. Visit `https://yourdomain.com/admin/`
2. Login with superuser credentials
3. Verify all models are accessible
4. Check Project admin has all features:
   - List display with 7 columns
   - 6 filters working
   - Search functional
   - Bulk actions available

### 4. Dashboard Verification

1. Visit `https://yourdomain.com/dashboard/`
2. Verify analytics section (4 summary cards)
3. Check Chart.js charts render
4. Test filtering (all 8 filters)
5. Test bulk operations
6. Test export (Excel, CSV, PDF)
7. Create test project
8. Test deep copy functionality

### 5. Performance Verification

```bash
# Install Apache Bench for load testing
sudo apt-get install -y apache2-utils

# Test homepage (100 requests, 10 concurrent)
ab -n 100 -c 10 https://yourdomain.com/

# Test dashboard (authenticated)
ab -n 100 -c 10 -C "sessionid=YOUR_SESSION_COOKIE" https://yourdomain.com/dashboard/

# Expected results:
# - Requests per second: > 50
# - Time per request: < 200ms (mean)
# - No failed requests
```

---

## 🔄 Rollback Procedure

### Quick Rollback

```bash
# Stop application
sudo supervisorctl stop django-ahsp

# Switch to previous commit
cd /opt/django-ahsp
git log --oneline -5  # Find previous stable commit
git checkout <previous-commit-hash>

# Rollback database (if needed)
python manage.py migrate dashboard 0008  # Example: rollback to migration 0008

# Restart application
sudo supervisorctl start django-ahsp
```

### Full Rollback

```bash
# 1. Stop services
sudo supervisorctl stop django-ahsp

# 2. Restore database backup
sudo -u postgres psql django_ahsp_production < /backups/db_backup_YYYYMMDD.sql

# 3. Restore code
cd /opt/django-ahsp
git checkout main
git reset --hard <stable-commit>

# 4. Restore static files
rsync -avz /backups/staticfiles_YYYYMMDD/ /opt/django-ahsp/staticfiles/

# 5. Restart services
sudo supervisorctl start django-ahsp
sudo systemctl reload nginx
```

---

## 📊 Monitoring & Maintenance

### 1. Log Monitoring

```bash
# Application logs
tail -f /var/log/django-ahsp/error.log
tail -f /var/log/django-ahsp/gunicorn-error.log

# Nginx logs
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log

# Supervisor logs
tail -f /var/log/django-ahsp/supervisor.log
```

### 2. Database Backups

**Daily Backup Script** (`/opt/django-ahsp/scripts/backup.sh`):

```bash
#!/bin/bash
BACKUP_DIR="/backups/django-ahsp"
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
sudo -u postgres pg_dump django_ahsp_production | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Media files backup
tar -czf $BACKUP_DIR/media_$DATE.tar.gz /opt/django-ahsp/media/

# Keep only last 7 days
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

**Schedule with Cron:**
```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /opt/django-ahsp/scripts/backup.sh >> /var/log/django-ahsp/backup.log 2>&1
```

### 3. Performance Monitoring

**Install monitoring tools:**
```bash
# Install Django Debug Toolbar (dev only)
pip install django-debug-toolbar

# Install Sentry for error tracking (production)
pip install sentry-sdk

# Configure in settings.py
import sentry_sdk
sentry_sdk.init(
    dsn="your-sentry-dsn",
    traces_sample_rate=0.1,
)
```

### 4. Regular Maintenance

**Weekly:**
- Review error logs
- Check disk space (`df -h`)
- Review slow queries
- Update security patches

**Monthly:**
- Analyze performance metrics
- Review and optimize slow endpoints
- Update dependencies (`pip list --outdated`)
- Verify backups are restorable

**Quarterly:**
- Security audit
- Load testing
- Database optimization (`VACUUM ANALYZE` for PostgreSQL)
- Review and update documentation

---

## 📞 Support & Troubleshooting

**Common Issues:**
- See [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md)

**Performance Issues:**
- See [PERFORMANCE_TUNING_GUIDE.md](./PERFORMANCE_TUNING_GUIDE.md)

**Contact:**
- GitHub Issues: https://github.com/adithia00004/DJANGO-AHSP-PROJECT/issues
- Email: support@yourdomain.com

---

**Deployment Checklist Complete! ✅**

Your Django-AHSP application is now production-ready with:
- ✅ 5 phases implemented and tested
- ✅ 187 tests passing
- ✅ 93/100 production readiness score
- ✅ Complete monitoring and backup strategy
- ✅ Security hardened configuration
