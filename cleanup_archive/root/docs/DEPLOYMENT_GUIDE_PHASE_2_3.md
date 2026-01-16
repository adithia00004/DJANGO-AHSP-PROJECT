# Deployment Guide: Phase 2 & 3

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Pre-Deployment Checklist](#pre-deployment-checklist)
4. [Deployment Steps](#deployment-steps)
5. [Post-Deployment Verification](#post-deployment-verification)
6. [Rollback Procedures](#rollback-procedures)
7. [Production Configuration](#production-configuration)
8. [Monitoring Setup](#monitoring-setup)
9. [Troubleshooting](#troubleshooting)

---

## Overview

This guide covers deploying Phase 2 (Audit & Logging) and Phase 3 (Database Search Optimization) to production environments.

### What's Being Deployed

**Phase 2: Audit & Logging (85% Complete)**
- SecurityAuditLog model with 5 severity levels
- 4 dashboard templates (1,320 lines)
- 3 management commands (721 lines)
- Audit event tracking system
- Security monitoring dashboard

**Phase 3: Database Search Optimization (100% Complete)**
- PostgreSQL full-text search (10-100x faster)
- GIN indexes with tsvector
- 9 repository search methods
- 34+ comprehensive tests

### Deployment Timeline

| Phase | Estimated Downtime | Migration Time | Total Time |
|-------|-------------------|----------------|------------|
| Phase 2 | None | 2-5 minutes | 15-30 minutes |
| Phase 3 | Optional (5 min) | 5-15 minutes | 30-45 minutes |
| **Combined** | **5 minutes** | **7-20 minutes** | **45-75 minutes** |

*Migration time depends on database size. Estimates for 10,000-100,000 records.*

---

## Prerequisites

### System Requirements

- **PostgreSQL**: Version 12+ (13+ recommended)
- **Python**: 3.9+ (3.11+ recommended)
- **Django**: 4.2+ (from project requirements)
- **Disk Space**: Additional 10-15% of current database size
- **RAM**: Sufficient for index building (2GB+ recommended)

### Required PostgreSQL Extensions

```bash
# Check if extensions are available
psql -U postgres -d your_database -c "SELECT * FROM pg_available_extensions WHERE name = 'pg_trgm';"

# If not available, install PostgreSQL contrib package
# Ubuntu/Debian
sudo apt-get install postgresql-contrib

# CentOS/RHEL
sudo yum install postgresql-contrib

# macOS (Homebrew)
brew install postgresql
```

### Python Dependencies

All dependencies should already be in `requirements.txt`:
```
Django>=4.2
psycopg2-binary>=2.9
django-environ
```

### Access Requirements

- Database superuser access (for creating extensions)
- Django admin access
- Server SSH access
- Backup system access

---

## Pre-Deployment Checklist

### 1. Backup Everything

```bash
# Database backup
pg_dump -U postgres -d your_database -F c -f backup_$(date +%Y%m%d_%H%M%S).dump

# Code backup (if not using git)
tar -czf codebase_backup_$(date +%Y%m%d_%H%M%S).tar.gz /path/to/project

# Media files backup
tar -czf media_backup_$(date +%Y%m%d_%H%M%S).tar.gz /path/to/media

# Verify backups
ls -lh *.dump *.tar.gz
```

### 2. Check Database Size

```sql
-- Current database size
SELECT
    pg_size_pretty(pg_database_size(current_database())) AS db_size;

-- Current table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
```

### 3. Check Current Migration Status

```bash
# Check which migrations are applied
python manage.py showmigrations referensi

# Expected output should show migrations up to 0017 or earlier
# [ ] referensi.0018_add_fulltext_search (not yet applied)
```

### 4. Review Current Configuration

```bash
# Check environment variables
cat .env | grep -E "FTS_|AUDIT_|SECURITY_"

# Check Django settings
python manage.py shell -c "from django.conf import settings; print(f'DEBUG={settings.DEBUG}')"
```

### 5. Disk Space Check

```bash
# Check available disk space (need at least 10-15% of DB size free)
df -h /var/lib/postgresql

# Check inode availability
df -i /var/lib/postgresql
```

### 6. Schedule Maintenance Window

**Recommended Window:**
- **Duration**: 1-2 hours
- **Time**: Off-peak hours (e.g., 2-4 AM)
- **Day**: Weekday with low traffic

**Optional Downtime:**
- Phase 2: No downtime required
- Phase 3: 5-10 minutes for large datasets (optional)

---

## Deployment Steps

### Step 1: Prepare Code Deployment

```bash
# 1. Pull latest code (on production server)
cd /path/to/project
git fetch origin
git checkout main  # or your production branch
git pull origin main

# 2. Verify code integrity
git log -1 --oneline
git status

# 3. Activate virtual environment
source venv/bin/activate  # or your venv path

# 4. Install/update dependencies
pip install -r requirements.txt --upgrade

# 5. Collect static files (if needed)
python manage.py collectstatic --noinput
```

### Step 2: Enable PostgreSQL Extensions

```bash
# Connect to database as superuser
psql -U postgres -d your_database

# Enable pg_trgm extension (required for Phase 3)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

# Verify extension
\dx pg_trgm

# Expected output:
#   Name   | Version | Schema |             Description
# ---------+---------+--------+-------------------------------------
#  pg_trgm | 1.5     | public | text similarity measurement and ...

# Exit psql
\q
```

### Step 3: Test Migrations in Staging

**CRITICAL: Always test in staging first!**

```bash
# On staging server
python manage.py migrate referensi 0018_add_fulltext_search --plan

# Review the plan output carefully
# Should show:
# 1. Adding search_vector columns
# 2. Creating GIN indexes
# 3. Creating trigram indexes

# Run migration
python manage.py migrate referensi 0018_add_fulltext_search

# Verify success
python manage.py showmigrations referensi | grep 0018
# Should show: [X] 0018_add_fulltext_search
```

### Step 4: Production Migration - Phase 2 & 3

```bash
# On production server

# A. Review migration plan
python manage.py migrate referensi 0018_add_fulltext_search --plan

# B. Start migration (this will take 5-20 minutes depending on data size)
echo "Starting migration at $(date)"
python manage.py migrate referensi 0018_add_fulltext_search
echo "Migration completed at $(date)"

# C. The migration includes:
#    - Phase 2: SecurityAuditLog model (already should exist from earlier)
#    - Phase 3: Full-text search columns and indexes
```

### Step 5: Verify Database Changes

```sql
-- Connect to database
psql -U postgres -d your_database

-- 1. Verify search_vector columns exist
\d referensi_ahspreferensi
-- Should show: search_vector | tsvector | ... GENERATED ALWAYS AS ...

\d referensi_rincianreferensi
-- Should show: search_vector | tsvector | ... GENERATED ALWAYS AS ...

-- 2. Verify indexes were created
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('referensi_ahspreferensi', 'referensi_rincianreferensi')
    AND indexname LIKE '%search%'
ORDER BY tablename, indexname;

-- Expected output (5 indexes):
-- ix_ahsp_search_vector
-- ix_ahsp_kode_trigram
-- ix_ahsp_nama_trigram
-- ix_rincian_search_vector
-- ix_rincian_uraian_trigram

-- 3. Check index sizes
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE indexname LIKE '%search%'
ORDER BY pg_relation_size(indexrelid) DESC;

-- 4. Verify search_vector is populated
SELECT
    kode_ahsp,
    nama_ahsp,
    search_vector IS NOT NULL AS has_search_vector
FROM referensi_ahspreferensi
LIMIT 5;
-- All rows should have has_search_vector = true

\q
```

### Step 6: Update Environment Configuration

```bash
# Edit .env file
nano .env  # or vim/editor of choice

# Add Phase 3 Full-Text Search settings (if not present)
cat >> .env << 'EOF'

# ============================================
# Phase 3: Full-Text Search Configuration
# ============================================
FTS_LANGUAGE=simple
FTS_MAX_RESULTS=1000
FTS_MIN_QUERY_LENGTH=2
FTS_FUZZY_THRESHOLD=0.3
FTS_AUTOCOMPLETE_LIMIT=20
FTS_ENABLE_SUGGESTIONS=True
FTS_CACHE_RESULTS=True
FTS_CACHE_TTL=300

EOF

# Verify settings were added
tail -15 .env
```

### Step 7: Restart Application

```bash
# For systemd service
sudo systemctl restart your-django-app

# For gunicorn
sudo systemctl restart gunicorn

# For supervisor
sudo supervisorctl restart your-django-app

# Verify service is running
sudo systemctl status your-django-app
# or
sudo supervisorctl status your-django-app
```

### Step 8: Clear Cache (if using)

```bash
# Django cache
python manage.py shell -c "from django.core.cache import cache; cache.clear(); print('Cache cleared')"

# Redis cache (if applicable)
redis-cli FLUSHALL

# Memcached (if applicable)
echo "flush_all" | nc localhost 11211
```

---

## Post-Deployment Verification

### 1. Run Test Suite

```bash
# Run full-text search tests
python manage.py test referensi.tests.test_fulltext_search -v 2

# Expected: 34+ tests pass, 0 failures

# If any tests fail, check:
# - PostgreSQL extensions enabled
# - Indexes created successfully
# - search_vector columns populated
```

### 2. Manual Smoke Tests

```bash
# Open Django shell
python manage.py shell

# Test Phase 3: Full-text search
from referensi.services.ahsp_repository import AHSPRepository
repo = AHSPRepository()

# Test basic search
results = repo.search_ahsp("pekerjaan", limit=5)
print(f"Found {results.count()} results")
for job in results:
    print(f"  {job.kode_ahsp}: {job.nama_ahsp}")

# Test fuzzy search
fuzzy_results = repo.fuzzy_search_ahsp("pkerjaan", threshold=0.3, limit=5)
print(f"Fuzzy search found {fuzzy_results.count()} results")

# Test auto-complete
suggestions = repo.get_search_suggestions("peker", limit=10)
print(f"Auto-complete suggestions: {suggestions}")

# Exit shell
exit()
```

### 3. Check Audit Dashboard (Phase 2)

```bash
# 1. Access audit dashboard in browser
# URL: http://your-domain/referensi/audit/dashboard/

# 2. Verify elements load:
#    - Summary cards (Total Events, Critical Events, etc.)
#    - Event timeline chart
#    - Severity distribution pie chart
#    - Top users bar chart
#    - Recent events table

# 3. Check audit logs list
# URL: http://your-domain/referensi/audit/logs/

# 4. Test filtering and search
```

### 4. Performance Benchmarks

```bash
# Run performance tests
python manage.py test referensi.tests.test_fulltext_search.TestPerformanceBenchmarks -v 2

# Manual performance check
python manage.py shell

import time
from referensi.services.ahsp_repository import AHSPRepository

repo = AHSPRepository()

# Benchmark simple search
start = time.time()
results = list(repo.search_ahsp("pekerjaan", limit=100))
duration = time.time() - start
print(f"Simple search (100 results): {duration*1000:.2f}ms")
# Expected: <50ms

# Benchmark fuzzy search
start = time.time()
results = list(repo.fuzzy_search_ahsp("pekerjaan", limit=50))
duration = time.time() - start
print(f"Fuzzy search (50 results): {duration*1000:.2f}ms")
# Expected: <100ms

exit()
```

### 5. Check Database Statistics

```sql
-- Connect to database
psql -U postgres -d your_database

-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE indexname LIKE '%search%'
ORDER BY idx_scan DESC;

-- After running some searches, idx_scan should be > 0

-- Check table bloat
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size
FROM pg_tables
WHERE tablename IN ('referensi_ahspreferensi', 'referensi_rincianreferensi')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

\q
```

### 6. Monitor Application Logs

```bash
# Check Django logs
tail -f /path/to/logs/django.log

# Check Gunicorn logs
tail -f /var/log/gunicorn/error.log

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-13-main.log

# Look for:
# - No errors related to search_vector
# - No missing index warnings
# - Successful query executions
```

### 7. Check Management Commands (Phase 2)

```bash
# Test cleanup command (dry run)
python manage.py cleanup_audit_logs --dry-run --days 90

# Expected output showing what would be deleted

# Test audit summary generation
python manage.py generate_audit_summary --period daily

# Expected output showing summary stats

# Test alert command (dry run if possible)
# Check that email settings are configured first
```

---

## Rollback Procedures

### Quick Rollback (Code Only)

If issues are detected but migration succeeded:

```bash
# 1. Stop application
sudo systemctl stop your-django-app

# 2. Rollback code
git log --oneline -5
git checkout <previous-commit-hash>

# 3. Restart application
sudo systemctl start your-django-app
```

### Full Rollback (Code + Database)

If migration caused issues:

```bash
# 1. Stop application
sudo systemctl stop your-django-app

# 2. Rollback migration
python manage.py migrate referensi 0017_previous_migration

# The reverse migration will:
# - Drop search_vector columns
# - Drop all created indexes
# - Remove pg_trgm extension (if safe)

# 3. Rollback code
git checkout <previous-commit-hash>

# 4. Restart application
sudo systemctl start your-django-app

# 5. Verify rollback
python manage.py showmigrations referensi
# Should NOT show [X] next to 0018_add_fulltext_search
```

### Emergency Restore from Backup

If rollback fails:

```bash
# 1. Stop application
sudo systemctl stop your-django-app

# 2. Restore database from backup
pg_restore -U postgres -d your_database -c backup_20250104_020000.dump

# 3. Restore code
cd /path/to/project
git reset --hard <backup-commit>

# 4. Restart application
sudo systemctl start your-django-app
```

---

## Production Configuration

### Django Settings Optimization

```python
# config/settings/production.py

# Phase 2: Audit & Logging
AUDIT_LOG_RETENTION_DAYS = 90
AUDIT_CRITICAL_RETENTION_DAYS = 180
AUDIT_ENABLE_EMAIL_ALERTS = True
AUDIT_ALERT_THRESHOLD = 5
AUDIT_ALERT_RECIPIENTS = ['admin@example.com', 'security@example.com']

# Phase 3: Full-Text Search
FTS_LANGUAGE = 'simple'  # Use 'indonesian' if available
FTS_MAX_RESULTS = 1000
FTS_MIN_QUERY_LENGTH = 2
FTS_FUZZY_THRESHOLD = 0.3
FTS_AUTOCOMPLETE_LIMIT = 20
FTS_ENABLE_SUGGESTIONS = True
FTS_CACHE_RESULTS = True
FTS_CACHE_TTL = 300  # 5 minutes

# Database connection pooling (recommended)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,  # Connection pooling
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}
```

### PostgreSQL Tuning

```sql
-- postgresql.conf optimizations for full-text search

-- Increase work_mem for index building
work_mem = 64MB  # Default is 4MB

-- Optimize for GIN indexes
gin_pending_list_limit = 4MB  # Default is 4MB, increase if needed

-- Maintenance work memory (for VACUUM, REINDEX)
maintenance_work_mem = 256MB  # Default is 64MB

-- Shared buffers (25% of RAM recommended)
shared_buffers = 2GB  # Adjust based on available RAM

-- Effective cache size (50-75% of RAM)
effective_cache_size = 6GB  # Adjust based on available RAM

-- After changes, restart PostgreSQL
sudo systemctl restart postgresql
```

### Nginx Configuration (if applicable)

```nginx
# Increase timeout for search operations
location /referensi/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Increase timeouts for search operations
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}
```

### Cron Jobs for Maintenance

```bash
# Add to crontab
crontab -e

# Cleanup old audit logs daily at 3 AM
0 3 * * * /path/to/venv/bin/python /path/to/project/manage.py cleanup_audit_logs --days 90 --force >> /var/log/cleanup_audit.log 2>&1

# Generate audit summary daily at 1 AM
0 1 * * * /path/to/venv/bin/python /path/to/project/manage.py generate_audit_summary --period daily >> /var/log/audit_summary.log 2>&1

# Send audit alerts every hour
0 * * * * /path/to/venv/bin/python /path/to/project/manage.py send_audit_alerts >> /var/log/audit_alerts.log 2>&1

# Rebuild search indexes monthly (first day of month at 2 AM)
0 2 1 * * /path/to/venv/bin/python /path/to/project/manage.py dbshell -c "REINDEX INDEX CONCURRENTLY ix_ahsp_search_vector; REINDEX INDEX CONCURRENTLY ix_rincian_search_vector; ANALYZE;" >> /var/log/reindex.log 2>&1
```

---

## Monitoring Setup

### 1. Database Monitoring Queries

Create monitoring views for easy checking:

```sql
-- Create monitoring views
CREATE OR REPLACE VIEW v_search_index_health AS
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    idx_scan AS scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched,
    CASE
        WHEN idx_scan = 0 THEN 'UNUSED'
        WHEN idx_scan < 10 THEN 'LOW_USAGE'
        WHEN idx_scan < 100 THEN 'MEDIUM_USAGE'
        ELSE 'HIGH_USAGE'
    END AS usage_status
FROM pg_stat_user_indexes
WHERE indexname LIKE '%search%';

-- Query the view
SELECT * FROM v_search_index_health ORDER BY scans DESC;
```

### 2. Application Performance Monitoring

```python
# Add to middleware or logging configuration
import logging
import time

logger = logging.getLogger('performance')

class SearchPerformanceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if '/search/' in request.path:
            start_time = time.time()
            response = self.get_response(request)
            duration = time.time() - start_time

            if duration > 0.5:  # Log slow searches (>500ms)
                logger.warning(
                    f"Slow search detected: {request.path} "
                    f"took {duration*1000:.2f}ms"
                )

            return response
        return self.get_response(request)
```

### 3. Alert Triggers

```sql
-- Create function to alert on slow queries
CREATE OR REPLACE FUNCTION log_slow_search_queries()
RETURNS trigger AS $$
BEGIN
    IF NEW.duration > 1000 THEN  -- 1 second
        INSERT INTO slow_query_log (query, duration, timestamp)
        VALUES (NEW.query, NEW.duration, NOW());
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### 4. Monitoring Dashboard URLs

After deployment, verify these URLs are accessible:

- **Audit Dashboard**: `/referensi/audit/dashboard/`
- **Audit Logs List**: `/referensi/audit/logs/`
- **Audit Statistics**: `/referensi/audit/statistics/`
- **Search Interface**: (Your custom search page)

---

## Troubleshooting

### Issue 1: Migration Timeout

**Symptom:**
```
django.db.utils.OperationalError: canceling statement due to statement timeout
```

**Solution:**
```bash
# Increase database timeout
export DATABASE_TIMEOUT=1800  # 30 minutes

# Or edit postgresql.conf
statement_timeout = 1800000  # 30 minutes in milliseconds

# Restart PostgreSQL
sudo systemctl restart postgresql

# Retry migration
python manage.py migrate referensi 0018_add_fulltext_search
```

### Issue 2: Insufficient Disk Space

**Symptom:**
```
ERROR: could not extend file: No space left on device
```

**Solution:**
```bash
# Check disk usage
df -h /var/lib/postgresql

# Clean up old data
# 1. Vacuum old tables
psql -U postgres -d your_database -c "VACUUM FULL;"

# 2. Remove old logs
sudo find /var/log -name "*.log" -mtime +30 -delete

# 3. If still insufficient, consider:
#    - Mounting additional storage
#    - Moving database to larger volume
#    - Archiving old audit logs
```

### Issue 3: High Memory Usage During Migration

**Symptom:**
Server becomes unresponsive during index creation.

**Solution:**
```sql
-- Run index creation one at a time manually
-- Instead of full migration, create indexes sequentially

-- 1. Create indexes without CONCURRENT (faster but locks table)
CREATE INDEX ix_ahsp_search_vector
ON referensi_ahspreferensi USING GIN(search_vector);

-- Or use CONCURRENTLY (slower but no locks)
CREATE INDEX CONCURRENTLY ix_ahsp_search_vector
ON referensi_ahspreferensi USING GIN(search_vector);

-- Monitor memory usage
SELECT * FROM pg_stat_activity WHERE state = 'active';
```

### Issue 4: Search Returns No Results

**Symptom:**
All searches return empty querysets.

**Diagnosis & Solution:**
```bash
# 1. Check if search_vector is populated
python manage.py shell

from referensi.models import AHSPReferensi
job = AHSPReferensi.objects.first()
print(f"search_vector: {job.search_vector}")

# If None, regenerate:
exit()

# 2. Rollback and reapply migration
python manage.py migrate referensi 0017_previous_migration
python manage.py migrate referensi 0018_add_fulltext_search

# 3. Force update
python manage.py shell

from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("ANALYZE referensi_ahspreferensi;")
    cursor.execute("ANALYZE referensi_rincianreferensi;")
```

### Issue 5: Slow Performance After Deployment

**Symptom:**
Searches are slower than expected (>100ms).

**Solution:**
```sql
-- 1. Check if indexes are being used
EXPLAIN ANALYZE
SELECT * FROM referensi_ahspreferensi
WHERE search_vector @@ websearch_to_tsquery('simple', 'pekerjaan')
LIMIT 50;

-- Look for "Index Scan using ix_ahsp_search_vector"
-- If showing "Seq Scan", indexes aren't being used

-- 2. Update table statistics
ANALYZE referensi_ahspreferensi;
ANALYZE referensi_rincianreferensi;

-- 3. Rebuild indexes
REINDEX INDEX CONCURRENTLY ix_ahsp_search_vector;
REINDEX INDEX CONCURRENTLY ix_rincian_search_vector;

-- 4. Check PostgreSQL configuration
SHOW work_mem;
SHOW shared_buffers;
SHOW effective_cache_size;

-- Adjust if values are too low (see Production Configuration section)
```

---

## Security Considerations

### 1. Database Permissions

```sql
-- Ensure application user has minimal permissions
GRANT SELECT, INSERT, UPDATE, DELETE
ON referensi_ahspreferensi, referensi_rincianreferensi, referensi_securityauditlog
TO your_app_user;

-- Do NOT grant:
-- - SUPERUSER
-- - CREATE EXTENSION
-- - DROP TABLE
```

### 2. Audit Log Protection

```python
# Ensure audit logs are tamper-proof
# In models.py, SecurityAuditLog should have:

class SecurityAuditLog(models.Model):
    # ... fields ...

    class Meta:
        # Prevent accidental bulk deletion
        permissions = [
            ('delete_audit_log', 'Can delete audit log entries'),
        ]

    def delete(self, *args, **kwargs):
        # Override to require special permission or prevent deletion
        if not self.can_be_deleted():
            raise PermissionDenied("Audit logs cannot be deleted manually")
        super().delete(*args, **kwargs)
```

### 3. Search Query Sanitization

Already handled by Django ORM, but verify:

```python
# Repository methods use parameterized queries
# Never construct raw SQL with user input:

# BAD (SQL injection risk):
# raw_query = f"SELECT * FROM table WHERE name = '{user_input}'"

# GOOD (uses Django ORM):
# results = repo.search_ahsp(user_input)  # Safe
```

---

## Performance Monitoring Checklist

After deployment, monitor these metrics weekly:

- [ ] Average search query time (<50ms target)
- [ ] Index usage statistics (should be increasing)
- [ ] Database size growth rate (<2% per month expected)
- [ ] Audit log count and retention compliance
- [ ] Error rate in application logs (should be near 0%)
- [ ] PostgreSQL slow query log (>1s queries)
- [ ] Server resource usage (CPU, RAM, disk I/O)

---

## Next Steps

After successful deployment:

1. **Week 1**: Monitor intensively, watch for errors
2. **Week 2-4**: Optimize based on usage patterns
3. **Month 2**: Review and tune PostgreSQL configuration
4. **Month 3**: Consider implementing remaining Phase 2 tests (15%)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-04
**Deployment Target**: Production
**Estimated Total Time**: 45-75 minutes
**Risk Level**: Low (with proper backup and staging testing)
