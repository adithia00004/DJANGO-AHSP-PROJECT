# Deployment Checklist - Django AHSP Project v2.0

**Last Updated**: 2026-01-15
**Version**: 2.0-optimized

---

## 🎯 Pre-Deployment Checklist

### 1. Environment Preparation

- [ ] **Production server provisioned**
  - Minimum specs: 4 vCPU, 8GB RAM, 50GB SSD
  - Docker Engine installed
  - Docker Compose installed

- [ ] **Domain & SSL**
  - [ ] Domain DNS configured
  - [ ] SSL certificate obtained (Let's Encrypt or commercial)
  - [ ] Nginx/Traefik configured for HTTPS

- [ ] **Environment variables configured**
  ```bash
  # Verify .env.production exists
  ls -la .env.production
  
  # Required variables:
  DEBUG=False
  SECRET_KEY=<generated-secure-key>
  ALLOWED_HOSTS=yourdomain.com
  DATABASE_URL=postgres://...
  REDIS_URL=redis://...
  ```

### 2. Database Preparation

- [ ] **Export database from Docker development**
  ```bash
  docker exec ahsp_postgres pg_dump -U ahspuser -d ahsp_db -F c -f /tmp/ahsp_production.dump
  docker cp ahsp_postgres:/tmp/ahsp_production.dump ./backups/
  ```

- [ ] **Verify data integrity**
  ```bash
  # Check superuser exists
  docker exec ahsp_postgres psql -U ahspuser -d ahsp_db -c "SELECT email FROM auth_user WHERE is_superuser=true;"
  
  # Check referensi data
  docker exec ahsp_postgres psql -U ahspuser -d ahsp_db -c "SELECT COUNT(*) FROM referensi_ahspreferensi;"
  ```

- [ ] **Backup current production (if upgrading)**
  ```bash
  pg_dump -U ahspuser -d ahsp_db -F c -f backup_before_upgrade.dump
  ```

### 3. Application Preparation

- [ ] **Code is on latest version**
  ```bash
  git status
  git log -1 --oneline
  ```

- [ ] **All tests pass**
  ```bash
  pytest --tb=short -q
  ```

- [ ] **Static files collected**
  ```bash
  python manage.py collectstatic --noinput
  ```

- [ ] **Dependencies up to date**
  ```bash
  pip freeze > requirements.txt
  ```

---

## 🚀 Deployment Steps

### Step 1: Transfer Files to Production

```bash
# Option A: Git clone on production server
git clone https://github.com/your-repo/django-ahsp-project.git
cd django-ahsp-project
git checkout v2.0-optimized

# Option B: SCP transfer
scp -r ./django-ahsp-project user@production-server:/opt/apps/
```

### Step 2: Configure Environment

```bash
# Copy production environment file
cp .env.production.example .env.production

# Edit with production values
nano .env.production

# Verify configuration
cat .env.production | grep -v PASSWORD
```

### Step 3: Start Services

```bash
# Pull latest images
docker-compose -f docker-compose.yml pull

# Build application image
docker-compose build web

# Start all services
docker-compose up -d

# Wait for health checks
sleep 30
docker ps
```

### Step 4: Import Database

```bash
# Copy backup to production
scp ./backups/ahsp_production.dump user@production-server:/tmp/

# Import database
docker cp /tmp/ahsp_production.dump ahsp_postgres:/tmp/
docker exec ahsp_postgres pg_restore -U ahspuser -d ahsp_db -c /tmp/ahsp_production.dump

# Verify import
docker exec ahsp_postgres psql -U ahspuser -d ahsp_db -c "SELECT COUNT(*) FROM auth_user;"
```

### Step 5: Apply Migrations

```bash
# Check pending migrations
docker-compose exec web python manage.py showmigrations

# Apply migrations
docker-compose exec web python manage.py migrate

# Verify
docker-compose exec web python manage.py showmigrations | grep "\[X\]"
```

### Step 6: Collect Static Files

```bash
docker-compose exec web python manage.py collectstatic --noinput
```

### Step 7: Start Celery Workers (Optional)

```bash
docker-compose --profile celery up -d
```

---

## ✅ Post-Deployment Verification

### 1. Health Checks

- [ ] **Web service responding**
  ```bash
  curl -I https://yourdomain.com/health/
  # Expected: HTTP/2 200
  ```

- [ ] **Database connection working**
  ```bash
  docker-compose exec web python manage.py dbshell -c "SELECT 1;"
  ```

- [ ] **Redis connection working**
  ```bash
  docker exec ahsp_redis redis-cli ping
  # Expected: PONG
  ```

### 2. Functional Tests

- [ ] **Login works**
  - Open https://yourdomain.com/accounts/login/
  - Login with superuser credentials
  - Verify dashboard loads

- [ ] **Dashboard loads**
  - Navigate to /dashboard/
  - Verify projects list displays
  - Check no JavaScript errors in console

- [ ] **API endpoints working**
  ```bash
  # Test API endpoint
  curl -s https://yourdomain.com/detail_project/api/monitoring/performance-metrics/ | jq
  ```

- [ ] **Export functionality**
  - Navigate to any project
  - Test PDF export
  - Test Excel export

### 3. Performance Verification

- [ ] **Response times acceptable**
  - Dashboard: < 500ms
  - API endpoints: < 100ms
  - Exports: < 5s for normal size

- [ ] **No memory leaks after 1 hour**
  ```bash
  docker stats --no-stream
  ```

### 4. Security Verification

- [ ] **SSL certificate valid**
  ```bash
  openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
  ```

- [ ] **DEBUG=False confirmed**
  - Visit /nonexistent-page-12345/
  - Should show custom 404, not Django debug page

- [ ] **Admin interface secured**
  - /admin/ requires login
  - No sensitive data in error messages

---

## 🔄 Rollback Procedure

If deployment fails:

### Quick Rollback

```bash
# 1. Stop new deployment
docker-compose down

# 2. Restore previous image
docker-compose pull ahsp_web:previous-version

# 3. Restore database
docker cp backup_before_upgrade.dump ahsp_postgres:/tmp/
docker exec ahsp_postgres pg_restore -U ahspuser -d ahsp_db -c /tmp/backup_before_upgrade.dump

# 4. Restart with previous version
docker-compose up -d
```

### Git Rollback

```bash
# Revert to previous tag
git checkout v1.9-stable

# Rebuild and restart
docker-compose build web
docker-compose up -d
```

---

## 📊 Monitoring Setup

### Enable Logging

```bash
# Ensure log directory exists
mkdir -p logs

# Configure log rotation
cat > /etc/logrotate.d/ahsp << EOF
/path/to/project/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
}
EOF
```

### Setup Monitoring Dashboard

- [ ] **Flower for Celery monitoring**
  - URL: http://yourdomain.com:5555
  
- [ ] **PgBouncer stats**
  ```bash
  docker exec ahsp_pgbouncer pgbouncer show stats
  ```

- [ ] **External monitoring (optional)**
  - UptimeRobot / Pingdom
  - Monitor: https://yourdomain.com/health/

---

## 📝 Final Checklist

- [ ] All services running (`docker ps` shows 6 containers)
- [ ] No critical errors in logs (`docker-compose logs | grep ERROR`)
- [ ] Superuser can login
- [ ] Data imported correctly (spot check a few records)
- [ ] Exports working (PDF, Excel, Word)
- [ ] SSL certificate valid
- [ ] Backup job scheduled
- [ ] Monitoring configured
- [ ] Team notified of deployment

---

## 🎉 Deployment Complete!

**Version Deployed**: v2.0-optimized
**Deployment Date**: ____________
**Deployed By**: ____________

### Post-Deployment Notes
```
(Add any notes about the deployment here)
```
