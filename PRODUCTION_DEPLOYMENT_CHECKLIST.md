# Production Deployment Checklist
**Django AHSP Project - Jadwal Pekerjaan Optimization**

**Version**: 2.0 (Post-Optimization)
**Date**: 2025-01-15
**Target Deployment**: TBD

---

## 📋 PRE-DEPLOYMENT CHECKLIST

### **1. Code Quality & Testing** ✓

- [ ] **All tests passing**
  ```bash
  python manage.py test detail_project
  # Expected: 519+ assertions passing
  ```

- [ ] **Frontend tests passing**
  ```bash
  npm run test:frontend
  # Expected: All unit tests passing
  ```

- [ ] **Code quality checks**
  ```bash
  # Run linting
  npm run lint
  # Expected: No errors
  ```

- [ ] **Performance benchmarks met**
  - Grid load time: < 1.5s ✓
  - Chart update throttling: Working ✓
  - API response caching: 60s TTL ✓
  - Database queries: Indexed ✓

### **2. Database Migration**

- [ ] **Create fresh migration if needed**
  ```bash
  python manage.py makemigrations
  python manage.py migrate --check
  ```

- [ ] **Test migrations in staging**
  ```bash
  # Staging environment
  python manage.py migrate --plan
  python manage.py migrate
  ```

- [ ] **Backup production database**
  ```bash
  # Create backup before migration
  pg_dump -U postgres django_ahsp > backup_pre_migration_$(date +%Y%m%d).sql
  ```

- [ ] **Verify indexes exist**
  ```sql
  -- Check PekerjaanProgressWeekly indexes
  SELECT indexname FROM pg_indexes
  WHERE tablename = 'detail_project_pekerjaanprogressweekly';

  -- Expected indexes:
  -- - pekerjaan + week_number
  -- - project + week_number
  -- - week_start_date + week_end_date
  ```

### **3. Static Files & Assets**

- [ ] **Build frontend assets**
  ```bash
  npm run build
  # Expected: Vite build completes with chunked output
  ```

- [ ] **Collect static files**
  ```bash
  python manage.py collectstatic --noinput
  ```

- [ ] **Verify Vite manifest exists**
  ```bash
  ls detail_project/static/detail_project/dist/.vite/manifest.json
  # Expected: File exists
  ```

- [ ] **Test static file serving**
  ```bash
  # Check STATIC_ROOT is configured
  python manage.py diffsettings | grep STATIC
  ```

### **4. Environment Configuration**

- [ ] **Production settings verified**
  ```python
  # settings.py or settings_production.py

  DEBUG = False  # ✓ Must be False
  ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com']  # ✓ Set properly

  SECRET_KEY = env('SECRET_KEY')  # ✓ From environment variable

  # Database (production)
  DATABASES = {
      'default': {
          'ENGINE': 'django.db.backends.postgresql',
          'NAME': env('DB_NAME'),
          'USER': env('DB_USER'),
          'PASSWORD': env('DB_PASSWORD'),
          'HOST': env('DB_HOST'),
          'PORT': env('DB_PORT', default='5432'),
      }
  }

  # Security
  SECURE_SSL_REDIRECT = True
  SESSION_COOKIE_SECURE = True
  CSRF_COOKIE_SECURE = True
  SECURE_BROWSER_XSS_FILTER = True
  SECURE_CONTENT_TYPE_NOSNIFF = True
  X_FRAME_OPTIONS = 'DENY'

  # Static/Media
  STATIC_ROOT = '/var/www/django_ahsp/static/'
  MEDIA_ROOT = '/var/www/django_ahsp/media/'
  ```

- [ ] **Environment variables set**
  ```bash
  # .env.production (DO NOT commit to git)
  DEBUG=False
  SECRET_KEY=<strong-secret-key>
  DB_NAME=django_ahsp_prod
  DB_USER=<db-user>
  DB_PASSWORD=<db-password>
  DB_HOST=localhost
  DB_PORT=5432
  ALLOWED_HOSTS=your-domain.com,www.your-domain.com
  ```

- [ ] **Logging configured**
  ```python
  # settings_production.py
  LOGGING = {
      'version': 1,
      'disable_existing_loggers': False,
      'formatters': {
          'verbose': {
              'format': '{levelname} {asctime} {module} {message}',
              'style': '{',
          },
      },
      'handlers': {
          'file': {
              'level': 'WARNING',
              'class': 'logging.handlers.RotatingFileHandler',
              'filename': '/var/log/django_ahsp/django.log',
              'maxBytes': 1024 * 1024 * 10,  # 10 MB
              'backupCount': 5,
              'formatter': 'verbose',
          },
          'performance_file': {
              'level': 'INFO',
              'class': 'logging.handlers.RotatingFileHandler',
              'filename': '/var/log/django_ahsp/performance.log',
              'maxBytes': 1024 * 1024 * 10,
              'backupCount': 3,
              'formatter': 'verbose',
          },
      },
      'loggers': {
          'django': {
              'handlers': ['file'],
              'level': 'WARNING',
              'propagate': True,
          },
          'performance': {
              'handlers': ['performance_file'],
              'level': 'INFO',
              'propagate': False,
          },
          'api.deprecation': {
              'handlers': ['file'],
              'level': 'WARNING',
              'propagate': False,
          },
      },
  }
  ```

### **5. Security Hardening**

- [ ] **Update SECRET_KEY for production**
  ```python
  # Generate new secret key
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```

- [ ] **Review ALLOWED_HOSTS**
  ```python
  ALLOWED_HOSTS = [
      'your-domain.com',
      'www.your-domain.com',
      # Add all production domains
  ]
  ```

- [ ] **Enable HTTPS redirects**
  ```python
  SECURE_SSL_REDIRECT = True
  SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
  ```

- [ ] **Configure CORS (if using API)**
  ```python
  CORS_ALLOWED_ORIGINS = [
      'https://your-domain.com',
      'https://www.your-domain.com',
  ]
  ```

- [ ] **Rate limiting configured** (if using django-ratelimit)
  ```python
  # Example for API endpoints
  RATELIMIT_ENABLE = True
  RATELIMIT_USE_CACHE = 'default'
  ```

### **6. Caching Configuration**

- [ ] **Cache backend configured**
  ```python
  # settings_production.py
  CACHES = {
      'default': {
          'BACKEND': 'django.core.cache.backends.redis.RedisCache',
          'LOCATION': 'redis://127.0.0.1:6379/1',
          'OPTIONS': {
              'CLIENT_CLASS': 'django_redis.client.DefaultClient',
          },
          'KEY_PREFIX': 'django_ahsp',
          'TIMEOUT': 300,  # 5 minutes default
      }
  }
  ```

- [ ] **Session backend (optional)**
  ```python
  SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
  SESSION_CACHE_ALIAS = 'default'
  ```

---

## 🚀 DEPLOYMENT STEPS

### **Step 1: Server Preparation**

```bash
# 1. Update system packages
sudo apt update && sudo apt upgrade -y

# 2. Install dependencies
sudo apt install -y python3-pip python3-venv postgresql nginx supervisor redis-server

# 3. Create application directory
sudo mkdir -p /var/www/django_ahsp
sudo chown $USER:$USER /var/www/django_ahsp

# 4. Create log directory
sudo mkdir -p /var/log/django_ahsp
sudo chown $USER:$USER /var/log/django_ahsp
```

### **Step 2: Deploy Application**

```bash
# 1. Clone/copy application code
cd /var/www/django_ahsp
git clone <repository-url> .
# OR: rsync -avz --exclude='*.pyc' local/ remote:/var/www/django_ahsp/

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Install Node.js dependencies and build
npm install
npm run build

# 5. Copy environment file
cp .env.production .env

# 6. Collect static files
python manage.py collectstatic --noinput

# 7. Run migrations
python manage.py migrate
```

### **Step 3: Configure Gunicorn**

```bash
# Create gunicorn configuration
cat > /var/www/django_ahsp/gunicorn_config.py <<EOF
bind = '127.0.0.1:8000'
workers = 4  # (2 x num_cores) + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
accesslog = '/var/log/django_ahsp/gunicorn_access.log'
errorlog = '/var/log/django_ahsp/gunicorn_error.log'
loglevel = 'info'
EOF

# Test gunicorn
gunicorn --config gunicorn_config.py project.wsgi:application
```

### **Step 4: Configure Supervisor**

```bash
# Create supervisor configuration
sudo cat > /etc/supervisor/conf.d/django_ahsp.conf <<EOF
[program:django_ahsp]
command=/var/www/django_ahsp/venv/bin/gunicorn --config /var/www/django_ahsp/gunicorn_config.py project.wsgi:application
directory=/var/www/django_ahsp
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/django_ahsp/supervisor.log
environment=PATH="/var/www/django_ahsp/venv/bin"
EOF

# Reload supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start django_ahsp
sudo supervisorctl status django_ahsp
```

### **Step 5: Configure Nginx**

```bash
# Create nginx configuration
sudo cat > /etc/nginx/sites-available/django_ahsp <<EOF
upstream django_ahsp {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Redirect to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    client_max_body_size 10M;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Static files
    location /static/ {
        alias /var/www/django_ahsp/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /var/www/django_ahsp/media/;
        expires 7d;
    }

    # Proxy to Django
    location / {
        proxy_pass http://django_ahsp;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/django_ahsp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### **Step 6: Configure SSL (Let's Encrypt)**

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

---

## ✅ POST-DEPLOYMENT VERIFICATION

### **1. Health Checks**

- [ ] **Application accessible**
  ```bash
  curl https://your-domain.com/
  # Expected: 200 OK
  ```

- [ ] **Admin panel working**
  ```bash
  curl https://your-domain.com/admin/
  # Expected: 200 OK (login page)
  ```

- [ ] **Static files loading**
  ```bash
  curl -I https://your-domain.com/static/detail_project/dist/assets/index.js
  # Expected: 200 OK with Cache-Control headers
  ```

- [ ] **API endpoints responding**
  ```bash
  curl -X GET https://your-domain.com/api/v2/project/1/assignments/
  # Expected: 200 OK or 401 (if authentication required)
  ```

### **2. Performance Verification**

- [ ] **Page load times acceptable**
  - Homepage: < 2s
  - Jadwal Pekerjaan grid: < 1.5s
  - Chart rendering: < 500ms

- [ ] **Database query performance**
  ```bash
  # Check slow query log
  tail -f /var/log/django_ahsp/performance.log
  # Expected: No queries > 500ms
  ```

- [ ] **Memory usage stable**
  ```bash
  # Monitor Gunicorn workers
  ps aux | grep gunicorn
  # Expected: Memory usage < 200MB per worker
  ```

- [ ] **Response times**
  ```bash
  # Check performance dashboard
  curl https://your-domain.com/monitoring/performance-dashboard/
  ```

### **3. Monitoring Setup**

- [ ] **Deprecation dashboard accessible**
  ```
  https://your-domain.com/monitoring/deprecation-dashboard/
  # Expected: Shows v1 API usage metrics
  ```

- [ ] **Performance dashboard accessible**
  ```
  https://your-domain.com/monitoring/performance-dashboard/
  # Expected: Shows backend metrics
  ```

- [ ] **Error logging working**
  ```bash
  tail -f /var/log/django_ahsp/django.log
  # Trigger an error and verify it's logged
  ```

- [ ] **Supervisor status**
  ```bash
  sudo supervisorctl status django_ahsp
  # Expected: RUNNING
  ```

### **4. Feature Verification**

- [ ] **Grid (TanStack Table) working**
  - Load grid page
  - Edit cells (planned/actual mode)
  - Save changes
  - Verify StateManager working

- [ ] **Charts rendering**
  - Gantt chart loads
  - S-Curve chart loads
  - Chart updates on data change
  - Throttling working (no lag)

- [ ] **API v2 endpoints working**
  - Weekly assignment creation
  - Timeline regeneration
  - Week boundary configuration

- [ ] **Undo/Redo working** (if implemented)
  - Edit cell
  - Press Ctrl+Z (undo)
  - Press Ctrl+Y (redo)

---

## 🔥 ROLLBACK PROCEDURE

**If deployment fails, follow these steps:**

### **1. Quick Rollback (Nginx)**

```bash
# Switch back to previous deployment
sudo ln -sfn /var/www/django_ahsp_old /var/www/django_ahsp
sudo supervisorctl restart django_ahsp
sudo systemctl reload nginx
```

### **2. Database Rollback**

```bash
# Restore database backup
psql -U postgres django_ahsp < backup_pre_migration_20250115.sql

# Or use Django migrations
python manage.py migrate detail_project <previous_migration_number>
```

### **3. Code Rollback**

```bash
# Git rollback
cd /var/www/django_ahsp
git reset --hard <previous-commit-hash>

# Rebuild assets
npm run build
python manage.py collectstatic --noinput

# Restart services
sudo supervisorctl restart django_ahsp
```

### **4. Emergency Rollback to LEGACY Template**

If modern grid fails completely:

```bash
# 1. Restore LEGACY template
cp archive/templates/2025-12-16/kelola_tahapan_grid_LEGACY.html \
   detail_project/templates/detail_project/

# 2. Update view (detail_project/views.py line 208)
# Change: kelola_tahapan_grid_modern.html
# To: kelola_tahapan_grid_LEGACY.html

# 3. Restart Django
sudo supervisorctl restart django_ahsp
```

---

## 📊 MONITORING & MAINTENANCE

### **Daily Checks**

- [ ] Check error logs
  ```bash
  tail -n 100 /var/log/django_ahsp/django.log | grep ERROR
  ```

- [ ] Monitor deprecation metrics
  ```
  https://your-domain.com/monitoring/deprecation-dashboard/
  ```

- [ ] Check disk usage
  ```bash
  df -h
  # Expected: < 80% usage
  ```

### **Weekly Checks**

- [ ] Review performance metrics
  ```
  https://your-domain.com/monitoring/performance-dashboard/
  ```

- [ ] Check database size
  ```sql
  SELECT pg_size_pretty(pg_database_size('django_ahsp'));
  ```

- [ ] Review slow queries
  ```bash
  grep "exceeded.*threshold" /var/log/django_ahsp/performance.log
  ```

### **Monthly Maintenance**

- [ ] Rotate logs
  ```bash
  sudo logrotate /etc/logrotate.d/django_ahsp
  ```

- [ ] Update dependencies
  ```bash
  pip list --outdated
  npm outdated
  ```

- [ ] Database optimization
  ```sql
  VACUUM ANALYZE detail_project_pekerjaanprogressweekly;
  ```

- [ ] Review deprecation usage (until 2025-02-14)
  - Check which clients still use v1 APIs
  - Contact users to migrate to v2

---

## 🎯 SUCCESS CRITERIA

**Deployment is successful when:**

- ✅ All health checks passing
- ✅ Page load times < 2s
- ✅ No errors in logs (first hour)
- ✅ Grid editing works (planned + actual modes)
- ✅ Charts render correctly
- ✅ Deprecation monitoring active
- ✅ Performance metrics collecting
- ✅ SSL certificate valid
- ✅ Backups configured

---

## 📞 SUPPORT & ESCALATION

**If issues occur:**

1. **Check logs first**
   - `/var/log/django_ahsp/django.log`
   - `/var/log/django_ahsp/gunicorn_error.log`
   - `/var/log/nginx/error.log`

2. **Restart services**
   ```bash
   sudo supervisorctl restart django_ahsp
   sudo systemctl restart nginx
   ```

3. **If data corruption suspected**
   - Immediately restore from backup
   - Contact database administrator

4. **Emergency rollback**
   - Follow rollback procedure above
   - Document the issue

---

**Last Updated**: 2025-01-15
**Version**: 2.0
**Prepared by**: Development Team

**Status**: ✅ READY FOR PRODUCTION DEPLOYMENT
