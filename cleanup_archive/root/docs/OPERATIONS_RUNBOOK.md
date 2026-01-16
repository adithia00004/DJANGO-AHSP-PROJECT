# Operations Runbook - Django AHSP Project
## Version 2.0 - Production Ready

**Last Updated**: 2026-01-15
**Status**: ✅ Production Ready

---

## 🚀 Quick Start (Docker Deployment)

### Prerequisites
- Docker Desktop installed and running
- Git repository cloned
- Minimum 4GB RAM available

### Start All Services
```bash
# Start core services (web, database, cache)
docker-compose up -d

# Verify all containers are healthy
docker ps

# Expected output: 6 containers running
# - ahsp_web (Django)
# - ahsp_postgres (PostgreSQL)
# - ahsp_pgbouncer (Connection Pooling)
# - ahsp_redis (Cache & Sessions)
# - ahsp_celery (Background Tasks)
# - ahsp_flower (Task Monitoring)
```

### Stop All Services
```bash
docker-compose down
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f postgres
```

---

## 🗄️ Database Migration from Docker to Production

> **IMPORTANT**: Sistem ini dirancang untuk dapat di-deploy langsung dari Docker environment beserta database yang sudah ada. Data superuser, admin, dan referensi tidak perlu dibuat ulang di production.

### Export Database dari Docker Development

```bash
# 1. Export database lengkap (dengan data superuser, admin, referensi)
docker exec ahsp_postgres pg_dump -U ahspuser -d ahsp_db -F c -f /tmp/ahsp_production_backup.dump

# 2. Copy file dari container ke host
docker cp ahsp_postgres:/tmp/ahsp_production_backup.dump ./backups/ahsp_production_backup.dump
```

### Import ke Production Server

```bash
# 1. Copy file ke production server
scp ./backups/ahsp_production_backup.dump user@production-server:/tmp/

# 2. Di production server, restore database
pg_restore -U ahspuser -d ahsp_db -c /tmp/ahsp_production_backup.dump

# 3. Verify data integrity
psql -U ahspuser -d ahsp_db -c "SELECT COUNT(*) FROM auth_user;"
psql -U ahspuser -d ahsp_db -c "SELECT COUNT(*) FROM referensi_ahspreferensi;"
```

### Data yang Akan Ter-include
| Data Type | Table | Description |
|-----------|-------|-------------|
| Superuser | `auth_user` | Admin accounts dengan password terenkripsi |
| User Profiles | `accounts_userprofile` | Profile data pengguna |
| Referensi AHSP | `referensi_ahspreferensi` | Master data analisa harga |
| Referensi Koefisien | `referensi_ahspkoefisienreferensi` | Master data koefisien |
| User Projects | `dashboard_project` | Project data pengguna |

### Keamanan Data
- ⚠️ Password sudah ter-hash dengan PBKDF2/Argon2
- ⚠️ Token CSRF akan di-regenerate secara otomatis
- ⚠️ Session data akan di-reset (user harus login ulang)

---

## 📊 Database Backup & Restore

### Daily Backup (Automated via Cron)
```bash
# Create backup script
cat > /opt/scripts/backup_ahsp.sh << 'EOF'
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/backups/ahsp
docker exec ahsp_postgres pg_dump -U ahspuser -d ahsp_db -F c -f /tmp/backup_$TIMESTAMP.dump
docker cp ahsp_postgres:/tmp/backup_$TIMESTAMP.dump $BACKUP_DIR/
# Keep only last 7 days
find $BACKUP_DIR -name "*.dump" -mtime +7 -delete
EOF

chmod +x /opt/scripts/backup_ahsp.sh

# Add to crontab (daily at 2 AM)
echo "0 2 * * * /opt/scripts/backup_ahsp.sh" | crontab -
```

### Manual Backup
```bash
docker exec ahsp_postgres pg_dump -U ahspuser -d ahsp_db -F c -f /tmp/manual_backup.dump
docker cp ahsp_postgres:/tmp/manual_backup.dump ./backups/
```

### Restore from Backup
```bash
# Stop web service first
docker-compose stop web celery

# Restore database
docker cp ./backups/backup_20260115.dump ahsp_postgres:/tmp/
docker exec ahsp_postgres pg_restore -U ahspuser -d ahsp_db -c /tmp/backup_20260115.dump

# Apply any pending migrations
docker-compose exec web python manage.py migrate

# Restart services
docker-compose up -d
```

---

## 📍 Log Monitoring

### Log Locations
| Log Type | Location | Description |
|----------|----------|-------------|
| Django App | `logs/django.log` | Application logs |
| Gunicorn | `logs/gunicorn.log` | WSGI server logs |
| Celery | Docker logs | Background task logs |
| PostgreSQL | Docker logs | Database logs |
| Nginx | `/var/log/nginx/` | Reverse proxy logs |

### Monitor Real-time Logs
```bash
# Django application logs
tail -f logs/django.log

# All Docker services
docker-compose logs -f --tail=100

# Specific error monitoring
docker-compose logs -f 2>&1 | grep -i error
```

### Log Rotation (logrotate config)
```
/path/to/project/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
}
```

---

## 🏥 Health Check Endpoints

### Available Health Checks
| Endpoint | Method | Expected Response |
|----------|--------|-------------------|
| `/health/` | GET | `{"status": "ok"}` |
| `/api/monitoring/performance-metrics/` | GET | Performance metrics JSON |
| `/api/monitoring/deprecation-metrics/` | GET | Deprecation warnings |

### Automated Health Check Script
```bash
#!/bin/bash
HEALTH_URL="http://localhost:8000/health/"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ "$RESPONSE" != "200" ]; then
    echo "Health check failed! HTTP $RESPONSE"
    # Send alert (slack, email, etc.)
    exit 1
fi

echo "Health check passed"
```

---

## ⚙️ Celery Worker Management

### Start Celery Workers
```bash
# Start with docker-compose profile
docker-compose --profile celery up -d

# Or manually
docker-compose exec -d web celery -A config worker -l info
```

### Monitor Workers
```bash
# Check worker status
docker-compose exec web celery -A config inspect active

# View Flower dashboard
# Open http://localhost:5555 in browser
```

### Restart Workers
```bash
docker-compose restart celery celery_beat
```

---

## 🔴 Redis Cache Management

### Check Redis Connection
```bash
docker exec ahsp_redis redis-cli ping
# Expected: PONG
```

### View Cache Stats
```bash
docker exec ahsp_redis redis-cli info stats
```

### Clear Cache (Careful!)
```bash
# Clear specific key pattern
docker exec ahsp_redis redis-cli KEYS "v2_*" | xargs docker exec ahsp_redis redis-cli DEL

# Clear ALL cache (use only in emergency)
docker exec ahsp_redis redis-cli FLUSHALL
```

### Session Management
```bash
# View active sessions count
docker exec ahsp_redis redis-cli DBSIZE

# Clear sessions (will log out all users)
docker exec ahsp_redis redis-cli KEYS "session:*" | xargs docker exec ahsp_redis redis-cli DEL
```

---

## 🔒 Environment Variables

### Required Variables (Production)
```bash
# .env.production
DEBUG=False
SECRET_KEY=<generate-secure-key>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
PGBOUNCER_HOST=pgbouncer
PGBOUNCER_PORT=6432
DATABASE_URL=postgres://ahspuser:password@pgbouncer:6432/ahsp_db

# Cache
REDIS_URL=redis://redis:6379/0
CACHE_BACKEND=redis

# Email (optional)
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
```

### Generate Secret Key
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 🆘 Emergency Procedures

### High CPU Usage
1. Check running queries: `docker exec ahsp_postgres pg_stat_activity`
2. Kill long-running queries if needed
3. Check Celery task queue
4. Restart workers if needed

### Database Connection Issues
1. Check PgBouncer status: `docker exec ahsp_pgbouncer pgbouncer show stats`
2. Check connection pool: `docker exec ahsp_pgbouncer pgbouncer show pools`
3. Restart PgBouncer if needed: `docker-compose restart pgbouncer`

### Out of Memory
1. Check container stats: `docker stats`
2. Restart affected containers
3. Consider increasing memory limits in docker-compose.yml

---

## 📞 Contact & Support

- **Technical Lead**: [Your Name]
- **DevOps**: [DevOps Contact]
- **On-Call Schedule**: [Link to schedule]
