# Deployment Scripts

This directory contains automation scripts for deploying and managing the AHSP project across different environments.

## Available Scripts

### 1. Production Deployment

**File:** `deploy-production.sh`

Automated production deployment with full safety checks and rollback capability.

**Usage:**
```bash
./scripts/deploy-production.sh
```

**What it does:**
1. Checks prerequisites (Redis, PostgreSQL, environment)
2. Backs up database
3. Pulls latest code from git
4. Installs/updates dependencies
5. Runs database migrations
6. Collects static files
7. Clears cache
8. Restarts services (Gunicorn, Nginx)
9. Runs health checks
10. Executes smoke tests

**Prerequisites:**
- SSH access to production server
- Environment variables configured in `.env.production`
- Gunicorn systemd service: `gunicorn-ahsp`
- Nginx configured as reverse proxy
- Redis running
- PostgreSQL accessible

**Safety Features:**
- Database backup before deployment
- Health checks before and after
- Automatic rollback on failure
- Comprehensive logging

---

### 2. Staging Deployment

**File:** `deploy-staging.sh`

Similar to production but optimized for staging environment with relaxed checks.

**Usage:**
```bash
./scripts/deploy-staging.sh
```

**Differences from Production:**
- More verbose logging
- Optional tests after deployment
- Shorter backup retention (3 days vs 30)
- Non-blocking errors for some checks

---

### 3. Redis Setup

**File:** `setup-redis.sh`

Installs and configures Redis for caching and rate limiting.

**Usage:**
```bash
# Docker installation (recommended)
./scripts/setup-redis.sh docker

# Native installation (Ubuntu/Debian)
./scripts/setup-redis.sh native
```

**What it does:**
1. Installs Redis (Docker or native)
2. Configures Redis for production
3. Installs Python Redis client
4. Verifies configuration
5. Provides Django configuration example

**Docker Method:**
- Creates `ahsp-redis` container
- Exposes port 6379
- Enables persistence (appendonly)
- Auto-restart on failure

**Native Method:**
- Installs via package manager
- Configures /etc/redis/redis.conf
- Enables systemd service
- Sets up authentication (password required)

---

### 4. Database Backup

**File:** `backup-database.sh`

Creates timestamped PostgreSQL database backups with metadata.

**Usage:**
```bash
# Production backup
./scripts/backup-database.sh production

# Staging backup
./scripts/backup-database.sh staging

# Development backup
./scripts/backup-database.sh development
```

**What it creates:**
1. **Full backup** (`.dump` format) - Binary, compressed
2. **SQL backup** (`.sql.gz`) - Human-readable, compressed
3. **Schema backup** (`.sql`) - Database structure only
4. **Metadata file** (`.txt`) - Backup information

**Backup Location:**
```
/var/backups/ahsp/
├── production/
│   └── 2025-11-07/
│       ├── full_backup_20251107_120000.dump
│       ├── backup_20251107_120000.sql.gz
│       ├── schema_20251107_120000.sql
│       └── metadata_20251107_120000.txt
├── staging/
└── development/
```

**Retention Policy:**
- Production: 30 days
- Staging: 7 days
- Development: 3 days

**Features:**
- Automatic cleanup of old backups
- Backup verification
- Metadata tracking (git commit, Django version, etc.)
- Disk usage monitoring

---

## Common Workflows

### Initial Server Setup

```bash
# 1. Install Redis
./scripts/setup-redis.sh docker

# 2. Configure environment
cp .env.production.example .env.production
# Edit .env.production with real values

# 3. Create backup directory
sudo mkdir -p /var/backups/ahsp
sudo chown $USER:$USER /var/backups/ahsp

# 4. Run first deployment
./scripts/deploy-production.sh
```

### Regular Deployments

```bash
# Staging first
./scripts/deploy-staging.sh

# Test staging thoroughly
# ...

# Then production
./scripts/deploy-production.sh
```

### Backup Schedule

Set up cron jobs for automated backups:

```bash
# Edit crontab
crontab -e

# Add backup jobs
# Production: Daily at 2 AM
0 2 * * * /var/www/ahsp/scripts/backup-database.sh production >> /var/log/ahsp-backup.log 2>&1

# Staging: Daily at 3 AM
0 3 * * * /var/www/ahsp-staging/scripts/backup-database.sh staging >> /var/log/ahsp-backup.log 2>&1
```

---

## Script Variables

### Environment Variables Required

All scripts expect these environment variables (from `.env` files):

```bash
# Database
POSTGRES_DB=ahsp_sni_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://127.0.0.1:6379/1
REDIS_PASSWORD=redis-password

# Django
DJANGO_SECRET_KEY=secret-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=example.com,www.example.com

# Gunicorn
GUNICORN_WORKERS=9
GUNICORN_TIMEOUT=120
```

### Customizing Scripts

Edit these variables at the top of each script:

**deploy-production.sh:**
```bash
PROJECT_NAME="ahsp"
PROJECT_DIR="/var/www/ahsp"
VENV_DIR="$PROJECT_DIR/venv"
BACKUP_DIR="/var/backups/ahsp"
```

**setup-redis.sh:**
```bash
# Choose installation method
./scripts/setup-redis.sh docker  # or 'native'
```

**backup-database.sh:**
```bash
# Retention is automatic based on environment
# Production: 30 days
# Staging: 7 days
# Development: 3 days
```

---

## Troubleshooting

### Deployment Fails

**Check logs:**
```bash
# Application logs
tail -f /var/www/ahsp/logs/gunicorn-error.log

# Nginx logs
tail -f /var/log/nginx/error.log

# System logs
journalctl -u gunicorn-ahsp -f
```

**Common issues:**

1. **Health check fails:**
   - Check if Redis is running: `redis-cli ping`
   - Check if PostgreSQL is accessible: `psql -h localhost -U postgres -d ahsp_sni_db -c "SELECT 1"`
   - Check application logs

2. **Migration fails:**
   - Review migration file for syntax errors
   - Check database permissions
   - Verify database connection settings

3. **Static files not found:**
   - Run manually: `python manage.py collectstatic`
   - Check `STATIC_ROOT` in settings
   - Verify Nginx configuration

### Redis Issues

**Redis not starting:**
```bash
# Docker
docker logs ahsp-redis

# Native
sudo systemctl status redis-server
sudo journalctl -u redis-server -f
```

**Connection refused:**
```bash
# Check if Redis is listening
netstat -tlnp | grep 6379

# Test connection
redis-cli ping

# Check firewall
sudo ufw status
```

### Backup Issues

**Backup fails:**
```bash
# Check PostgreSQL permissions
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "\du"

# Check disk space
df -h /var/backups

# Verify environment variables
echo $POSTGRES_HOST
echo $POSTGRES_USER
```

**Restore backup:**
```bash
# List backup contents
pg_restore --list /var/backups/ahsp/production/2025-11-07/full_backup_20251107_120000.dump

# Restore to database
PGPASSWORD=$POSTGRES_PASSWORD pg_restore \
    -h localhost \
    -U postgres \
    -d ahsp_sni_db_restore \
    -c -v \
    /var/backups/ahsp/production/2025-11-07/full_backup_20251107_120000.dump
```

---

## Security Best Practices

1. **Never commit scripts with credentials** - Use environment variables
2. **Set proper file permissions:**
   ```bash
   chmod 700 scripts/*.sh  # Owner only
   chmod 600 .env*         # Owner read/write only
   ```
3. **Use SSH keys for git** - No passwords in scripts
4. **Enable Redis authentication** - Set strong password
5. **Backup encryption** - Encrypt backups at rest
6. **Audit logs** - Review deployment logs regularly

---

## Systemd Service Configuration

### Gunicorn Service

**File:** `/etc/systemd/system/gunicorn-ahsp.service`

```ini
[Unit]
Description=Gunicorn daemon for AHSP project
After=network.target

[Service]
Type=notify
User=ahsp
Group=www-data
WorkingDirectory=/var/www/ahsp
EnvironmentFile=/var/www/ahsp/.env.production
ExecStart=/var/www/ahsp/venv/bin/gunicorn \
    --config /var/www/ahsp/gunicorn.conf.py \
    config.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable gunicorn-ahsp
sudo systemctl start gunicorn-ahsp
sudo systemctl status gunicorn-ahsp
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/deploy-production.yml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PRODUCTION_HOST }}
          username: ${{ secrets.PRODUCTION_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /var/www/ahsp
            ./scripts/deploy-production.sh
```

### GitLab CI Example

```yaml
# .gitlab-ci.yml
deploy_production:
  stage: deploy
  only:
    - main
  script:
    - ssh $PRODUCTION_USER@$PRODUCTION_HOST "cd /var/www/ahsp && ./scripts/deploy-production.sh"
  environment:
    name: production
    url: https://ahsp.example.com
```

---

## Monitoring

### Health Check Endpoints

After deployment, verify health:

```bash
# Full health check (database, cache, etc.)
curl -f http://localhost:8000/health/

# Simple liveness check
curl -f http://localhost:8000/health/live/

# Readiness check (for load balancers)
curl -f http://localhost:8000/health/ready/
```

### Log Monitoring

Set up log aggregation:

```bash
# Watch all logs
tail -f /var/www/ahsp/logs/*.log

# Monitor specific log
tail -f /var/www/ahsp/logs/gunicorn-error.log | grep -i error
```

---

## Support

For issues with deployment scripts:
1. Check this README first
2. Review script comments (inline documentation)
3. Check `DEPLOYMENT_GUIDE.md` for infrastructure setup
4. Review logs (application, Nginx, systemd)
5. Open an issue with error logs and environment details

---

**Last Updated:** 2025-11-07
**Maintainer:** Development Team
