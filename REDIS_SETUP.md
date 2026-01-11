# Redis Session Store Setup Guide

**Date**: 2026-01-10
**Purpose**: Fix authentication failures (50% login failure rate) by implementing Redis session store
**Priority**: CRITICAL - Part of load testing optimization

---

## 🎯 PROBLEM IDENTIFIED

From load test v15 results:
- **Login failures**: 25/50 (50% failure rate)
- **Root cause**: Django database-backed sessions don't scale under concurrent load
- **Symptom**: Some logins taking 154-156 seconds, causing timeouts

**Original Baseline (v10)**: ~99% auth success
**With PgBouncer (v15)**: 50% auth failure
**Issue**: Session writes blocking on database

---

## ✅ SOLUTION: Redis Session Store

Redis provides:
- ✅ **In-memory speed** - microsecond latency
- ✅ **Concurrent-safe** - optimized for multiple writers
- ✅ **TTL support** - automatic session expiration
- ✅ **Persistence** - optional data durability
- ✅ **Scalable** - handles 10,000+ concurrent sessions

---

## 📋 INSTALLATION STEPS

### Step 1: Start Redis Container

```bash
# Start Redis server
docker-compose -f docker-compose-redis.yml up -d

# Verify Redis is running
docker ps | grep redis

# Test Redis connection
docker exec -it ahsp_redis redis-cli ping
# Expected output: PONG
```

### Step 2: Install Python Redis Client

```bash
# Activate virtual environment
# (Windows)
env\Scripts\activate

# (Linux/Mac)
# source env/bin/activate

# Install django-redis
pip install django-redis==5.4.0

# Verify installation
pip show django-redis
```

### Step 3: Update Django Settings

Already configured in `config/settings/base.py`:
- `SESSION_ENGINE = "django.contrib.sessions.backends.cache"`
- `CACHES` configured with Redis backend
- `SESSION_CACHE_ALIAS = "default"`

### Step 4: Add Redis Environment Variable

Add to `.env`:
```env
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Step 5: Test Redis Session

```bash
python manage.py shell
```

```python
from django.core.cache import cache
from django.contrib.sessions.backends.cache import SessionStore

# Test cache connection
cache.set('test_key', 'Hello Redis!', 30)
print(cache.get('test_key'))  # Should print: Hello Redis!

# Test session creation
session = SessionStore()
session['user_id'] = 123
session.save()
print(f"Session key: {session.session_key}")

# Verify in Redis
exit()
```

```bash
docker exec -it ahsp_redis redis-cli keys "*"
# Should show session keys
```

---

## 🔧 REDIS CONFIGURATION EXPLAINED

### docker-compose-redis.yml Settings:

```yaml
maxmemory 256mb              # Limit Redis memory usage
maxmemory-policy allkeys-lru # Evict least recently used keys when full
save 60 1000                 # Snapshot every 60s if 1000+ keys changed
appendonly yes               # Enable AOF for durability
appendfsync everysec         # Sync to disk every second
```

**Why these settings?**
- **256MB**: Enough for ~100,000 sessions @ 2.5KB each
- **allkeys-lru**: Automatically remove old sessions if memory full
- **AOF**: Protects against data loss on restart
- **everysec**: Balance between durability and performance

### Django Settings (base.py):

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PARSER_CLASS": "redis.connection.HiredisParser",
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
        },
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
```

**Key settings:**
- **Database 1**: Separate from default cache (db 0)
- **max_connections: 50**: Match concurrent user load
- **Timeouts: 5s**: Fail fast if Redis unavailable
- **HiredisParser**: Faster C-based parser

---

## ✅ VERIFICATION CHECKLIST

After setup, verify:

### 1. Redis Container Running
```bash
docker ps | grep redis
# Expected: ahsp_redis container STATUS: Up
```

### 2. Redis Responding
```bash
docker exec -it ahsp_redis redis-cli ping
# Expected: PONG
```

### 3. Django Can Connect
```bash
python manage.py shell
```
```python
from django.core.cache import cache
print(cache.get('test') or 'Redis connected!')
```

### 4. Sessions Stored in Redis
```bash
# Login to Django app via browser
# Then check Redis:
docker exec -it ahsp_redis redis-cli keys "django.contrib.sessions*"
# Should show session keys
```

### 5. Monitor Redis Stats
```bash
docker exec -it ahsp_redis redis-cli INFO stats
```

Look for:
- `total_connections_received`: Should increase
- `instantaneous_ops_per_sec`: Should be > 0 during load
- `used_memory_human`: Should be < 256MB

---

## 🧪 TESTING PLAN

### Before Load Test:
```bash
# Clear old sessions from database
python manage.py clearsessions

# Flush Redis (start fresh)
docker exec -it ahsp_redis redis-cli FLUSHALL

# Restart Django
python manage.py runserver
```

### Run Load Test v16:
```bash
locust -f load_testing/locustfile.py \
    --headless \
    -u 50 \
    -r 2 \
    -t 300s \
    --host=http://localhost:8000 \
    --csv=hasil_test_v16_50u_redis_sessions \
    --html=hasil_test_v16_50u_redis_sessions.html
```

### Expected Results:
- **Login success rate**: >95% (up from 50%)
- **Login response time**: <1s (down from 154s)
- **Total success rate**: >99% (up from 97%)
- **No session-related 500 errors**

---

## 🔍 TROUBLESHOOTING

### Error: "Connection refused" to Redis

**Check 1**: Is Redis container running?
```bash
docker ps | grep redis
```

**Fix**: Start Redis container
```bash
docker-compose -f docker-compose-redis.yml up -d
```

**Check 2**: Is port 6379 accessible?
```bash
netstat -an | findstr 6379
```

**Fix**: Ensure no other service using port 6379

---

### Error: "No module named 'django_redis'"

**Cause**: django-redis not installed

**Fix**:
```bash
pip install django-redis==5.4.0
```

---

### Error: Sessions still slow

**Check 1**: Verify Django using Redis
```python
from django.conf import settings
print(settings.SESSION_ENGINE)
# Should be: django.contrib.sessions.backends.cache
```

**Check 2**: Check Redis connection pool
```bash
docker exec -it ahsp_redis redis-cli INFO clients
```
Look for `connected_clients`

**Fix**: Increase max_connections if needed:
```python
"CONNECTION_POOL_KWARGS": {"max_connections": 100}
```

---

## 📊 MONITORING REDIS DURING LOAD TEST

### Real-time monitoring:
```bash
docker exec -it ahsp_redis redis-cli --stat
```

Shows:
- Commands/sec
- Hits/Misses
- Memory usage
- Connected clients

### Check session count:
```bash
docker exec -it ahsp_redis redis-cli DBSIZE
```

### Watch session activity:
```bash
docker exec -it ahsp_redis redis-cli MONITOR
```
(Press Ctrl+C to stop)

---

## 🎯 SUCCESS CRITERIA

Redis Session Store is working if:
- ✅ Login success rate >95%
- ✅ Login response time <1s
- ✅ No session timeouts during load test
- ✅ Redis memory usage stable (<256MB)
- ✅ Overall test success rate >99%

---

## 📈 EXPECTED IMPROVEMENT

| Metric | v15 (DB Sessions) | v16 (Redis) | Improvement |
|--------|-------------------|-------------|-------------|
| **Login Success** | 50% | >95% | +45% |
| **Login Response** | 100ms-156s | <1s | 156x faster |
| **Total Success** | 97.17% | >99% | +2% |
| **Auth Failures** | 25/50 | <3/50 | 83% reduction |

---

## 🚀 NEXT STEPS AFTER REDIS

Once Redis session store is working (v16 test passes):

**Priority 3**: Test @ 100 concurrent users
- Verify PgBouncer + Redis handle 100 users
- Target: >95% success rate
- This was the original failing test

**Priority 4**: Optimize heavy export operations
- Fix 120s timeout issues
- Implement Celery for background tasks
- Stream large responses

---

**Created**: 2026-01-10
**Status**: READY TO IMPLEMENT
**Expected completion**: 30 minutes
**Impact**: Fix 50% authentication failures
