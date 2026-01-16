# Deployment Guide - detail_project with P0/P1 Improvements

## ⚠️ CRITICAL PREREQUISITES

### 1. Cache Backend Configuration (MANDATORY for Rate Limiting)

**Problem:** Rate limiting menggunakan Django cache. Default cache (`locmem`) tidak akan bekerja di production dengan multiple workers.

#### Option A: Redis (Recommended)

**Install Dependencies:**
```bash
pip install redis django-redis
```

**settings.py Configuration:**
```python
# settings.py

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
        },
        'KEY_PREFIX': 'ahsp',
        'TIMEOUT': 300,  # Default timeout 5 minutes
    }
}

# Optional: Session backend juga bisa pakai Redis
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

**Docker Compose (if using Docker):**
```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped

  web:
    build: .
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/1

volumes:
  redis_data:
```

**Environment Variables:**
```bash
# .env
REDIS_URL=redis://127.0.0.1:6379/1
REDIS_PASSWORD=your_secure_password  # In production
```

**Verify Redis Connection:**
```python
# Python shell
from django.core.cache import cache
cache.set('test', 'Hello Redis', 60)
print(cache.get('test'))  # Should print: Hello Redis
```

#### Option B: Memcached

**Install Dependencies:**
```bash
pip install python-memcached
```

**settings.py Configuration:**
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': '127.0.0.1:11211',
        'KEY_PREFIX': 'ahsp',
        'TIMEOUT': 300,
    }
}
```

---

## 📋 Pre-Deployment Checklist

### Environment Setup
- [ ] Redis/Memcached installed and running
- [ ] Cache configuration in settings.py
- [ ] Environment variables configured (.env file)
- [ ] Database migrations applied
- [ ] Static files collected (`python manage.py collectstatic`)
- [ ] Frontend assets built (`npm install && npm run build` untuk menghasilkan bundel Vite + manifest)

### Security
- [ ] SECRET_KEY in environment variable (not in code)
- [ ] DEBUG = False in production
- [ ] ALLOWED_HOSTS configured
- [ ] CORS settings if applicable
- [ ] CSRF protection enabled
- [ ] Secure headers configured (see below)

### Dependencies
- [ ] All pip packages installed (`pip install -r requirements.txt`)
- [ ] Redis/Memcached client libraries installed
- [ ] Node modules for frontend (if any)

### Testing
- [ ] All tests passing (`python manage.py test`)
- [ ] Rate limiting tested with multiple workers
- [ ] Cache connectivity verified
- [ ] API endpoints returning correct format
- [ ] Frontend loading states working

---

## 🔧 Production Settings

### Required Settings (settings.py or settings_production.py)

```python
import os
from pathlib import Path

# Security
DEBUG = False
SECRET_KEY = os.environ.get('SECRET_KEY')
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Database (example for PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,  # Connection pooling
    }
}

# Cache (Redis)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PASSWORD': os.environ.get('REDIS_PASSWORD', None),
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
            },
        },
        'KEY_PREFIX': 'ahsp',
    }
}

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Security Headers
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Logging
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
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'detail_project': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

---

## 🚀 Deployment Steps

### Step 1: Prepare Environment

```bash
# Create logs directory
mkdir -p logs

# Set environment variables
export SECRET_KEY='your-secret-key-here'
export DEBUG='False'
export ALLOWED_HOSTS='yourdomain.com,www.yourdomain.com'
export REDIS_URL='redis://127.0.0.1:6379/1'
export DB_NAME='ahsp_production'
export DB_USER='ahsp_user'
export DB_PASSWORD='secure_password'
```

### Step 2: Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install Redis client
pip install redis django-redis

# Verify installation
python -c "import redis; print('Redis client installed')"
```

### Step 3: Database Setup

```bash
# Run migrations
python manage.py migrate

# Create superuser (if needed)
python manage.py createsuperuser

# Verify database
python manage.py check
```

### Step 4: Frontend Build & Static Files

```bash
# Build Vite assets (generates detail_project/static/detail_project/dist + manifest)
npm install
npm run build

# Collect static files (serves both Django assets & Vite bundle)
python manage.py collectstatic --no-input

# Verify static files
ls -la staticfiles/
```

### Step 5: Test Cache Connection

```bash
# Test cache
python manage.py shell
>>> from django.core.cache import cache
>>> cache.set('deployment_test', 'OK', 60)
>>> print(cache.get('deployment_test'))
OK
>>> exit()
```

### Step 6: Start Application

#### Option A: Gunicorn (Recommended)

```bash
# Install Gunicorn
pip install gunicorn

# Start with multiple workers
gunicorn config.wsgi:application \
    --workers 4 \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --log-level info
```

#### Option B: uWSGI

```bash
# Install uWSGI
pip install uwsgi

# Start uWSGI
uwsgi --http :8000 \
      --module config.wsgi \
      --processes 4 \
      --threads 2 \
      --master
```

### Step 7: Verify Deployment

```bash
# Health check
curl http://localhost:8000/admin/

# Test API endpoint
curl -X GET http://localhost:8000/api/project/1/list-pekerjaan/tree/ \
     -H "Authorization: Bearer YOUR_TOKEN"

# Check rate limiting (should get 429 after limit)
for i in {1..15}; do
    curl -X POST http://localhost:8000/api/project/1/save/ \
         -H "Content-Type: application/json" \
         -d '{"test": true}'
    echo "Request $i"
done
```

---

## 🔍 Troubleshooting

### Issue: Rate Limiting Not Working

**Symptoms:**
- Users can make more requests than the limit
- Rate limit counter resets randomly

**Diagnosis:**
```python
# Check cache backend
python manage.py shell
>>> from django.core.cache import cache
>>> cache._cache  # Should NOT be LocMemCache
>>> cache.set('test', 1, 60)
>>> cache.get('test')  # Should return 1
```

**Solution:**
- Verify Redis is running: `redis-cli ping` (should return PONG)
- Check Redis connection in settings
- Restart application servers
- Clear cache: `cache.clear()`

### Issue: API Responses Inconsistent

**Symptoms:**
- Some endpoints return old format
- Error messages not standardized

**Solution:**
- Check which endpoints are using `APIResponse` helpers
- Gradually migrate old endpoints (see migration plan)
- Test with API client (Postman/curl)

### Issue: Loading States Not Showing

**Symptoms:**
- No loading overlay appears
- Console errors about LoadingManager

**Diagnosis:**
- Check browser console for errors
- Verify loading.css is loaded: `View Source → search for loading.css`
- Check if LoadingManager is imported correctly

**Solution:**
- Ensure `base_detail.html` includes loading.css
- Run `collectstatic` again
- Clear browser cache
- Check JS module imports

---

## 📊 Monitoring & Health Checks

### Health Check Endpoint

Create a health check view:

```python
# detail_project/views.py
from django.http import JsonResponse
from django.core.cache import cache
from django.db import connection

def health_check(request):
    """Health check endpoint for monitoring"""
    health = {
        'status': 'ok',
        'checks': {}
    }

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health['checks']['database'] = 'ok'
    except Exception as e:
        health['status'] = 'error'
        health['checks']['database'] = f'error: {str(e)}'

    # Cache check
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health['checks']['cache'] = 'ok'
        else:
            health['status'] = 'error'
            health['checks']['cache'] = 'error: cache not working'
    except Exception as e:
        health['status'] = 'error'
        health['checks']['cache'] = f'error: {str(e)}'

    status_code = 200 if health['status'] == 'ok' else 503
    return JsonResponse(health, status=status_code)
```

### Monitoring Metrics

**Key metrics to monitor:**
- Request rate per endpoint
- Rate limit hits
- Cache hit/miss ratio
- API response times (p50, p95, p99)
- Error rates (4xx, 5xx)
- Database connection pool usage

**Recommended Tools:**
- Prometheus + Grafana
- Sentry for error tracking
- New Relic or DataDog for APM
- Redis monitoring (`redis-cli --stat`)

---

## 🔄 Rollback Procedure

If deployment fails:

```bash
# 1. Stop application
pkill -f gunicorn

# 2. Revert code to previous version
git checkout previous-tag

# 3. Rollback database migrations (if needed)
python manage.py migrate detail_project <previous_migration>

# 4. Clear cache
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()

# 5. Restart application
gunicorn config.wsgi:application --workers 4 --bind 0.0.0.0:8000
```

---

## 📝 Post-Deployment Checklist

- [ ] All services running (app, redis, nginx)
- [ ] Health check endpoint returning 200
- [ ] Rate limiting working (test with curl loop)
- [ ] Loading states working on frontend
- [ ] Error messages displaying correctly
- [ ] Logs being written to files
- [ ] Monitoring dashboards showing metrics
- [ ] SSL/HTTPS working
- [ ] Database backups scheduled

---

## 🆘 Support & Escalation

### Common Issues & Solutions

| Issue | Quick Fix | Documentation |
|-------|-----------|---------------|
| Rate limit not working | Check Redis connection | See "Troubleshooting" |
| Slow API responses | Check DB indexes | See performance guide |
| Memory leaks | Check cache size | Monitor Redis memory |
| 500 errors | Check logs | `tail -f logs/django.log` |

### Emergency Contacts

- **Ops Team:** ops@example.com
- **Dev Team:** dev@example.com
- **On-Call:** Use PagerDuty/Slack

---

**Last Updated:** 2025-11-07
**Version:** 1.0 (P0/P1 Improvements)
