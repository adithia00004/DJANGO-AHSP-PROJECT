# PHASE 4: Infrastructure Setup - Implementation Guide

## 📅 Start Date: November 8, 2025
## ⏱️ Duration: 3-5 days
## 🎯 Goal: Setup Redis cache backend dan deployment infrastructure

---

## 🚨 CRITICAL BLOCKER

**WITHOUT REDIS, RATE LIMITING WILL NOT WORK IN PRODUCTION!**

Default Django cache (locmem) is per-process, meaning:
- Gunicorn dengan 4 workers = 4 separate caches
- User bisa bypass rate limit dengan hit different worker
- Security vulnerability!

---

## 📋 PHASE 4 OVERVIEW

### Tasks Breakdown:

| Day | Task | Priority | Duration | Owner |
|-----|------|----------|----------|-------|
| 1 | Redis installation & configuration | 🔴 Critical | 2-4 hours | DevOps/Developer |
| 2 | Django cache configuration | 🔴 Critical | 1-2 hours | Developer |
| 2 | Environment variables setup | 🟠 High | 1-2 hours | Developer |
| 3 | Static files configuration | 🟠 High | 1-2 hours | Developer |
| 3-4 | Gunicorn/uWSGI setup | 🟠 High | 2-3 hours | DevOps |
| 4 | Health check endpoint | 🟡 Medium | 1 hour | Developer |
| 5 | Staging deployment & testing | 🔴 Critical | 3-4 hours | All |

**Total Estimated Time:** 12-18 hours (spread over 3-5 days)

---

## DAY 1: REDIS INSTALLATION & CONFIGURATION

### Option A: Docker (Recommended for Development)

#### Step 1.1: Install Docker (if not installed)

```bash
# Check if Docker is installed
docker --version

# If not installed:
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# macOS
brew install --cask docker

# Windows
# Download from https://www.docker.com/products/docker-desktop
```

#### Step 1.2: Run Redis Container

```bash
# Pull Redis image
docker pull redis:7-alpine

# Run Redis with persistence
docker run -d \
  --name ahsp-redis \
  -p 6379:6379 \
  -v redis-data:/data \
  --restart unless-stopped \
  redis:7-alpine redis-server --appendonly yes

# Verify Redis is running
docker ps | grep redis

# Test connection
docker exec -it ahsp-redis redis-cli ping
# Should return: PONG
```

#### Step 1.3: Test Redis from Python

```bash
# Install Redis client
pip install redis django-redis

# Test connection
python manage.py shell
>>> import redis
>>> r = redis.Redis(host='localhost', port=6379, db=0)
>>> r.ping()
True
>>> r.set('test', 'hello')
True
>>> r.get('test')
b'hello'
>>> exit()
```

**✅ Checkpoint:** Redis running dan responding to ping

---

### Option B: Native Installation (Production)

#### Ubuntu/Debian:

```bash
# Install Redis
sudo apt-get update
sudo apt-get install redis-server

# Enable Redis to start on boot
sudo systemctl enable redis-server

# Start Redis
sudo systemctl start redis-server

# Check status
sudo systemctl status redis-server

# Test connection
redis-cli ping
# Should return: PONG
```

#### macOS:

```bash
# Install via Homebrew
brew install redis

# Start Redis
brew services start redis

# Test connection
redis-cli ping
```

#### Windows:

```bash
# Use Docker or WSL2 (recommended)
# Or download Windows port from: https://github.com/microsoftarchive/redis/releases
```

---

### Step 1.4: Configure Redis for Production

```bash
# Edit Redis config (Ubuntu/Debian)
sudo nano /etc/redis/redis.conf

# Important settings:
```

**Production Redis Configuration:**

```conf
# /etc/redis/redis.conf

# Set password (IMPORTANT!)
requirepass your_secure_password_here

# Bind to localhost only (if Django is on same server)
bind 127.0.0.1

# Enable persistence
appendonly yes
appendfilename "appendonly.aof"

# Memory limit (adjust based on your RAM)
maxmemory 256mb
maxmemory-policy allkeys-lru

# Log level
loglevel notice
logfile /var/log/redis/redis-server.log

# Save to disk periodically
save 900 1      # Save after 900 sec if 1 key changed
save 300 10     # Save after 300 sec if 10 keys changed
save 60 10000   # Save after 60 sec if 10000 keys changed
```

**Restart Redis after config changes:**

```bash
sudo systemctl restart redis-server

# Test with password
redis-cli -a your_secure_password_here ping
```

**✅ Checkpoint:** Redis configured dengan password dan persistence

---

## DAY 2: DJANGO CONFIGURATION

### Step 2.1: Install Python Dependencies

```bash
# Install Redis client libraries
pip install redis django-redis

# Update requirements.txt
pip freeze | grep redis >> requirements.txt
pip freeze | grep django-redis >> requirements.txt

# Verify installation
python -c "import redis; import django_redis; print('Redis clients installed')"
```

---

### Step 2.2: Configure Django Cache Backend

**Create/Update: `config/settings.py` (or `settings_production.py`)**

```python
# config/settings.py

import os
from pathlib import Path

# ... existing settings ...

# ============================================================================
# CACHE CONFIGURATION (CRITICAL for Rate Limiting)
# ============================================================================

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PASSWORD': os.environ.get('REDIS_PASSWORD', None),
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,  # seconds
            'SOCKET_TIMEOUT': 5,  # seconds
        },
        'KEY_PREFIX': 'ahsp',
        'TIMEOUT': 300,  # Default 5 minutes
    }
}

# Optional: Use Redis for session backend too (better performance)
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

---

### Step 2.3: Environment Variables Setup

**Create: `.env` file (Development)**

```bash
# .env (for development)

# Django
SECRET_KEY=your-development-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (if using PostgreSQL)
DB_NAME=ahsp_dev
DB_USER=ahsp_user
DB_PASSWORD=dev_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://127.0.0.1:6379/1
REDIS_PASSWORD=

# Optional
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
```

**Create: `.env.staging` file**

```bash
# .env.staging

# Django
SECRET_KEY=your-staging-secret-key-here-change-this
DEBUG=False
ALLOWED_HOSTS=staging.yoursite.com,www.staging.yoursite.com

# Database
DB_NAME=ahsp_staging
DB_USER=ahsp_staging_user
DB_PASSWORD=secure_staging_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://127.0.0.1:6379/1
REDIS_PASSWORD=your_redis_password_here

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

**Create: `.env.production` file**

```bash
# .env.production

# Django
SECRET_KEY=your-production-secret-key-here-VERY-SECURE
DEBUG=False
ALLOWED_HOSTS=yoursite.com,www.yoursite.com

# Database
DB_NAME=ahsp_production
DB_USER=ahsp_prod_user
DB_PASSWORD=very_secure_production_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://127.0.0.1:6379/1
REDIS_PASSWORD=very_secure_redis_password

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

**Load environment variables in Django:**

```python
# config/settings.py

from pathlib import Path
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Access variables
SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'PASSWORD': os.environ.get('REDIS_PASSWORD', None),
            # ... other options
        },
    }
}
```

**Install python-dotenv:**

```bash
pip install python-dotenv
echo "python-dotenv" >> requirements.txt
```

---

### Step 2.4: Test Cache Configuration

```bash
# Test Django cache
python manage.py shell

>>> from django.core.cache import cache
>>>
>>> # Test set/get
>>> cache.set('test_key', 'Hello Redis!', 60)
True
>>>
>>> cache.get('test_key')
'Hello Redis!'
>>>
>>> # Test rate limiting cache key format
>>> cache.set('rate_limit:1:api_test_endpoint', 5, 300)
True
>>>
>>> cache.get('rate_limit:1:api_test_endpoint')
5
>>>
>>> # Check cache backend
>>> cache._cache
<django_redis.client.default.DefaultClient object at 0x...>
>>>
>>> # Success!
>>> exit()
```

**✅ Checkpoint:** Django dapat connect ke Redis dan cache bekerja

---

## DAY 3: STATIC FILES & APPLICATION SERVER

### Step 3.1: Configure Static Files

**Update: `config/settings.py`**

```python
# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# For production with whitenoise (recommended)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

**Install whitenoise:**

```bash
pip install whitenoise
echo "whitenoise" >> requirements.txt
```

**Update middleware:**

```python
# config/settings.py

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add this after SecurityMiddleware
    # ... other middleware
]
```

**Collect static files:**

```bash
# Create staticfiles directory
mkdir -p staticfiles

# Collect static files
python manage.py collectstatic --no-input

# Verify
ls -la staticfiles/
```

**✅ Checkpoint:** Static files collected successfully

---

### Step 3.2: Install & Configure Gunicorn

```bash
# Install Gunicorn
pip install gunicorn
echo "gunicorn" >> requirements.txt

# Test Gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1 --timeout 120

# Visit http://localhost:8000 to verify
```

**Create Gunicorn config file:**

```python
# gunicorn.conf.py

import multiprocessing

# Server socket
bind = '0.0.0.0:8000'
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1  # Recommended formula
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = 'logs/gunicorn-access.log'
errorlog = 'logs/gunicorn-error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = 'ahsp_django'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Maximum requests per worker (helps with memory leaks)
max_requests = 1000
max_requests_jitter = 50
```

**Create logs directory:**

```bash
mkdir -p logs
touch logs/gunicorn-access.log
touch logs/gunicorn-error.log
```

**Run with config:**

```bash
gunicorn config.wsgi:application -c gunicorn.conf.py
```

**✅ Checkpoint:** Gunicorn running dengan multiple workers

---

### Step 3.3: Test Rate Limiting with Multiple Workers

```bash
# Start Gunicorn dengan 4 workers
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120

# In another terminal, test rate limiting
for i in {1..15}; do
    echo "Request $i"
    curl -X POST http://localhost:8000/api/project/1/some-endpoint/ \
         -H "Content-Type: application/json" \
         -H "Cookie: sessionid=YOUR_SESSION_ID" \
         -d '{"test": true}'
    sleep 1
done

# Expected result:
# Requests 1-10: 200 OK (or 201/400 depending on endpoint)
# Requests 11+: 429 Too Many Requests
```

**If 429 not appearing after 10 requests:**
- ❌ Redis not configured correctly
- ❌ Cache backend still using locmem
- ❌ Check Django cache settings

**✅ Checkpoint:** Rate limiting working across multiple workers

---

## DAY 4: HEALTH CHECK & MONITORING

### Step 4.1: Create Health Check Endpoint

**Create: `detail_project/views_health.py`**

```python
# detail_project/views_health.py

from django.http import JsonResponse
from django.core.cache import cache
from django.db import connection
import redis
import os

def health_check(request):
    """
    Health check endpoint for monitoring.

    Returns 200 if all systems OK, 503 if any system down.
    """
    health = {
        'status': 'ok',
        'checks': {},
        'version': os.environ.get('APP_VERSION', 'dev'),
    }

    # Check 1: Database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        health['checks']['database'] = {
            'status': 'ok',
            'message': 'Database connection successful'
        }
    except Exception as e:
        health['status'] = 'error'
        health['checks']['database'] = {
            'status': 'error',
            'message': f'Database error: {str(e)}'
        }

    # Check 2: Cache (Redis)
    try:
        cache.set('health_check_test', 'ok', 10)
        result = cache.get('health_check_test')
        if result == 'ok':
            health['checks']['cache'] = {
                'status': 'ok',
                'message': 'Cache connection successful'
            }
        else:
            health['status'] = 'error'
            health['checks']['cache'] = {
                'status': 'error',
                'message': 'Cache not returning correct values'
            }
    except Exception as e:
        health['status'] = 'error'
        health['checks']['cache'] = {
            'status': 'error',
            'message': f'Cache error: {str(e)}'
        }

    # Check 3: Redis direct connection
    try:
        redis_url = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1')
        r = redis.from_url(redis_url)
        r.ping()
        health['checks']['redis'] = {
            'status': 'ok',
            'message': 'Redis connection successful'
        }
    except Exception as e:
        health['status'] = 'error'
        health['checks']['redis'] = {
            'status': 'error',
            'message': f'Redis error: {str(e)}'
        }

    # Return appropriate status code
    status_code = 200 if health['status'] == 'ok' else 503
    return JsonResponse(health, status=status_code)
```

**Update: `detail_project/urls.py`**

```python
# detail_project/urls.py

from django.urls import path
from .views_health import health_check

urlpatterns = [
    # Health check (no authentication required)
    path('health/', health_check, name='health_check'),

    # ... other URLs
]
```

**Test health check:**

```bash
# Test health endpoint
curl http://localhost:8000/health/

# Expected response:
{
    "status": "ok",
    "checks": {
        "database": {
            "status": "ok",
            "message": "Database connection successful"
        },
        "cache": {
            "status": "ok",
            "message": "Cache connection successful"
        },
        "redis": {
            "status": "ok",
            "message": "Redis connection successful"
        }
    },
    "version": "dev"
}
```

**✅ Checkpoint:** Health check endpoint working

---

## DAY 5: STAGING DEPLOYMENT & TESTING

### Step 5.1: Deploy to Staging

**Deployment checklist:**

```bash
# 1. Create logs directory
mkdir -p logs

# 2. Set environment
export DJANGO_SETTINGS_MODULE=config.settings
export $(cat .env.staging | xargs)

# 3. Database migrations
python manage.py migrate --no-input

# 4. Collect static files
python manage.py collectstatic --no-input

# 5. Create superuser (if needed)
python manage.py createsuperuser

# 6. Start Redis
docker start ahsp-redis

# 7. Start Gunicorn
gunicorn config.wsgi:application -c gunicorn.conf.py --daemon

# 8. Check processes
ps aux | grep gunicorn
docker ps | grep redis

# 9. Test health check
curl http://localhost:8000/health/
```

**✅ Checkpoint:** Application running on staging

---

### Step 5.2: Comprehensive Testing

**Test Suite:**

```bash
# Test 1: Health check
curl http://staging.yoursite.com/health/

# Test 2: Admin access
curl http://staging.yoursite.com/admin/

# Test 3: API endpoint
curl -X GET http://staging.yoursite.com/api/project/1/list-pekerjaan/tree/ \
     -H "Authorization: Bearer YOUR_TOKEN"

# Test 4: Rate limiting
for i in {1..15}; do
    echo "Request $i"
    curl -X POST http://staging.yoursite.com/api/test/
done

# Expected: 429 after 10 requests

# Test 5: Loading states (manual browser test)
# - Open browser
# - Trigger save operation
# - Should see loading overlay

# Test 6: Error handling (manual browser test)
# - Trigger error (e.g., invalid data)
# - Should see error overlay with retry button
```

**✅ Checkpoint:** All tests passing

---

## 📊 SUCCESS CRITERIA

Phase 4 is complete when ALL of these are true:

- ✅ Redis installed and running
- ✅ Redis configured with password (production)
- ✅ Django cache backend configured (django-redis)
- ✅ Cache connection tested and working
- ✅ Environment variables configured (.env files)
- ✅ Static files collected
- ✅ Gunicorn installed and configured
- ✅ Multiple workers (4) running
- ✅ Rate limiting works across workers (tested!)
- ✅ Health check endpoint implemented
- ✅ Health check returns 200 for all systems
- ✅ Deployed to staging
- ✅ Staging tests passing

---

## 🚨 TROUBLESHOOTING

### Problem: Redis not connecting

**Symptoms:**
```python
>>> from django.core.cache import cache
>>> cache.get('test')
# Error: Connection refused
```

**Solutions:**
```bash
# Check if Redis is running
docker ps | grep redis
# OR
sudo systemctl status redis-server

# Check Redis logs
docker logs ahsp-redis
# OR
sudo tail -f /var/log/redis/redis-server.log

# Test Redis directly
redis-cli ping
```

---

### Problem: Rate limiting not working

**Symptoms:**
- Can make more than 10 requests without getting 429

**Solutions:**
```bash
# 1. Check cache backend
python manage.py shell
>>> from django.core.cache import cache
>>> type(cache._cache)
# Should be: django_redis.client.default.DefaultClient
# NOT: django.core.cache.backends.locmem.LocMemCache

# 2. Check Redis connection
>>> cache.set('test', 1, 60)
>>> cache.get('test')
# Should return: 1

# 3. Check rate limit keys
>>> from django.core.cache import cache
>>> cache.keys('rate_limit:*')
# Should show rate limit keys if requests made

# 4. Clear cache and retry
>>> cache.clear()
```

---

### Problem: Gunicorn workers crashing

**Symptoms:**
```
[CRITICAL] WORKER TIMEOUT
```

**Solutions:**
```bash
# Increase timeout
gunicorn config.wsgi:application --timeout 300

# Check worker logs
tail -f logs/gunicorn-error.log

# Reduce workers if low memory
gunicorn config.wsgi:application --workers 2
```

---

## 📝 DELIVERABLES CHECKLIST

Phase 4 deliverables:

- [ ] Redis running (Docker or native)
- [ ] Redis configuration file (production)
- [ ] Django cache settings updated
- [ ] Environment files (.env, .env.staging, .env.production)
- [ ] requirements.txt updated (redis, django-redis, gunicorn, whitenoise)
- [ ] gunicorn.conf.py created
- [ ] Health check endpoint implemented
- [ ] Logs directory created
- [ ] Static files collected
- [ ] Staging deployment successful
- [ ] Testing completed and documented

---

## 🎯 NEXT PHASE

After Phase 4 is complete, proceed to:

**PHASE 5: Testing & QA** (Week 2)
- Integration tests
- Load testing
- Security testing
- Frontend testing
- UAT

**Status:** Ready to start Phase 4
**Target Completion:** November 12, 2025 (5 days)

---

**Last Updated:** November 7, 2025
**Version:** 1.0
