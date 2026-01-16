# Troubleshooting Guide - Django AHSP Project

**Last Updated**: 2026-01-15
**Version**: 2.0

---

## 🔴 Common Errors & Solutions

### 1. Login HTTP 500 Error

**Symptoms**:
- Login attempts fail with HTTP 500
- Occurs during high concurrent load (>100 users)

**Root Cause**:
- Django auth thread contention
- Password hashing (PBKDF2/Argon2) CPU intensive
- Session write race conditions

**Solution**:
This is a **known limitation** during mass concurrent login. In production:
- Users login at different times (distributed load)
- Already logged-in users are unaffected
- No action required unless >5% login failures

**Workaround for Testing**:
```python
# settings.py - Reduce hashing iterations (DEV ONLY)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',  # Fast but insecure
]
```

---

### 2. Database Connection Exhausted

**Symptoms**:
```
OperationalError: FATAL: too many connections for role "ahspuser"
```

**Root Cause**:
- Django bypassing PgBouncer
- Pool size exceeded

**Solution**:
```bash
# 1. Verify PgBouncer is being used
docker exec ahsp_web env | grep PGBOUNCER

# 2. Check environment variables in docker-compose.yml
PGBOUNCER_HOST=pgbouncer
PGBOUNCER_PORT=6432

# 3. Restart services
docker-compose restart web pgbouncer
```

---

### 3. Redis Connection Error

**Symptoms**:
```
redis.exceptions.ConnectionError: Error 111 connecting to redis:6379
```

**Root Cause**:
- Redis container not running
- Wrong Redis URL configuration

**Solution**:
```bash
# 1. Check Redis status
docker exec ahsp_redis redis-cli ping
# Expected: PONG

# 2. If not running, start it
docker-compose up -d redis

# 3. Verify configuration
echo $REDIS_URL
# Expected: redis://redis:6379/0
```

---

### 4. CSRF Token Mismatch (403 Forbidden)

**Symptoms**:
- POST requests return 403 Forbidden
- Error: "CSRF token missing or incorrect"

**Root Cause**:
- CSRF token not refreshed after login redirect (302)
- Token expired

**Solution (for Locust/Testing)**:
```python
# Refresh CSRF after login redirect
if response.status_code in [200, 302]:
    new_csrf = self.client.cookies.get("csrftoken")
    if new_csrf:
        self.client.headers["X-CSRFToken"] = new_csrf
```

**Solution (for Frontend)**:
```javascript
// Ensure CSRF token is included in headers
fetch(url, {
    method: 'POST',
    headers: {
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
    }
});
```

---

### 5. Celery Tasks Not Running

**Symptoms**:
- Async exports timeout
- Tasks stuck in queue

**Root Cause**:
- Celery worker not started
- Broker connection failed

**Solution**:
```bash
# 1. Check worker status
docker-compose exec web celery -A config inspect active

# 2. If no workers, start them
docker-compose --profile celery up -d

# 3. Check Flower dashboard
# Open http://localhost:5555

# 4. Check broker connection
docker exec ahsp_redis redis-cli LLEN celery
```

---

### 6. Static Files Not Loading (404)

**Symptoms**:
- CSS/JS files return 404
- Broken layout in production

**Root Cause**:
- Static files not collected
- Wrong STATIC_URL configuration

**Solution**:
```bash
# 1. Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# 2. Verify whitenoise is configured
grep STATICFILES_STORAGE config/settings/base.py

# 3. Check static files directory
ls -la staticfiles/
```

---

### 7. Migration Errors

**Symptoms**:
```
django.db.utils.ProgrammingError: relation "x" does not exist
```

**Root Cause**:
- Pending migrations not applied
- Migration history mismatch

**Solution**:
```bash
# 1. Check migration status
docker-compose exec web python manage.py showmigrations

# 2. Apply pending migrations
docker-compose exec web python manage.py migrate

# 3. If history mismatch, fake specific migration
docker-compose exec web python manage.py migrate app_name 0001 --fake
```

---

### 8. Export Timeout

**Symptoms**:
- PDF/Word/Excel export times out
- Large dataset export fails

**Root Cause**:
- Dataset too large for sync export
- Server timeout too short

**Solution**:
```bash
# 1. Use async export for large datasets
# API will return task_id, poll for result

# 2. Increase Gunicorn timeout (if needed)
# gunicorn.conf.py
timeout = 120  # seconds

# 3. Consider pagination for very large exports
```

---

### 9. Invalid JSON Response

**Symptoms**:
- API returns HTML instead of JSON
- JSON parse error in frontend

**Root Cause**:
- User not authenticated (redirect to login)
- AJAX request missing Accept header

**Solution (Frontend)**:
```javascript
fetch(url, {
    headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    },
    credentials: 'include'  // Include cookies
});
```

**Solution (Backend)**:
```python
# Check if authenticated before processing
if not request.user.is_authenticated:
    return JsonResponse({'error': 'Unauthorized'}, status=401)
```

---

### 10. Docker Build Failures

**Symptoms**:
```
ERROR: Service 'web' failed to build
```

**Common Causes & Fixes**:

**a) Package installation failed**:
```bash
# Clear pip cache and rebuild
docker-compose build --no-cache web
```

**b) Port already in use**:
```bash
# Find and kill process using port
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```

**c) Volume permission issues**:
```bash
# Reset volumes
docker-compose down -v
docker-compose up -d
```

---

## 🔍 Diagnostic Commands

### Check System Health
```bash
# All services status
docker-compose ps

# Container resource usage
docker stats

# Application logs
docker-compose logs -f web --tail=100

# Database connections
docker exec ahsp_pgbouncer pgbouncer show pools
```

### Check Database
```bash
# Active queries
docker exec ahsp_postgres psql -U ahspuser -d ahsp_db -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# Table sizes
docker exec ahsp_postgres psql -U ahspuser -d ahsp_db -c "SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;"
```

### Check Cache
```bash
# Redis memory usage
docker exec ahsp_redis redis-cli INFO memory

# Cache keys count
docker exec ahsp_redis redis-cli DBSIZE

# Check specific cache key
docker exec ahsp_redis redis-cli GET "v2_chart_data:160"
```

---

## 🆘 Emergency Contacts

- **On-Call Developer**: [Your contact]
- **Database Admin**: [DBA contact]
- **DevOps Team**: [DevOps contact]

---

## 📚 Related Documentation

- [Operations Runbook](./OPERATIONS_RUNBOOK.md)
- [Optimization Summary](./OPTIMIZATION_SUMMARY_8WEEKS.md)
- [Deployment Checklist](./DEPLOYMENT_CHECKLIST.md)
- [Docker Quick Start](./DOCKER_QUICK_START.md)
