# Docker Setup Guide - AHSP Project

## Overview
Panduan lengkap untuk menjalankan Django AHSP Project menggunakan Docker agar dapat dijalankan di PC lain dengan konfigurasi yang konsisten.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Environment Variables](#environment-variables)
4. [Docker Compose Services](#docker-compose-services)
5. [Commands Reference](#commands-reference)
6. [Deployment](#deployment)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Pastikan sudah terinstall:
- Docker (v20.10+) - [Download](https://www.docker.com/products/docker-desktop)
- Docker Compose (v1.29+) - Biasanya sudah included di Docker Desktop
- Git
- 4GB RAM minimum (8GB recommended)
- 10GB disk space

### Verify Installation
```bash
docker --version
docker-compose --version
```

---

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/django-ahsp-project.git
cd django-ahsp-project
```

### 2. Setup Environment File
```bash
# Copy template env file
cp .env.example .env

# Edit .env dengan text editor (VS Code, Notepad++, dll)
# Sesuaikan nilai-nilai sesuai kebutuhan
```

### 3. Build & Start Services
```bash
# Build Docker images
docker-compose build

# Start all services
docker-compose up -d

# Atau kombinasi build + up
docker-compose up -d --build
```

### 4. Initialize Database
```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser (optional)
docker-compose exec web python manage.py createsuperuser
```

### 5. Access Application
- **Web Application**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **Flower (Celery Monitor)**: http://localhost:5555 (jika Celery dijalankan)

---

## Environment Variables

### Development (.env)
```dotenv
# Django Configuration
DJANGO_ENV=development
DJANGO_SECRET_KEY=your-insecure-dev-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,web,192.168.x.x

# Database (PostgreSQL)
POSTGRES_DB=ahsp_sni_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres_password_dev
DB_PORT=5432

# Redis Cache
REDIS_PASSWORD=redis_password_dev
REDIS_PORT=6379
REDIS_DB=0

# Application
APP_VERSION=1.0.0-dev
LOG_LEVEL=DEBUG
WEB_PORT=8000
```

### Production (.env.production)
```dotenv
# Django Configuration - CHANGE THESE VALUES!
DJANGO_ENV=production
DJANGO_SECRET_KEY=generate-with-python-get_random_secret_key()
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database (PostgreSQL)
POSTGRES_DB=ahsp_prod_db
POSTGRES_USER=ahsp_user
POSTGRES_PASSWORD=strong-password-here
DB_PORT=5432

# Redis Cache
REDIS_PASSWORD=strong-redis-password
REDIS_PORT=6379
REDIS_DB=0

# Application
APP_VERSION=1.0.0
LOG_LEVEL=INFO
WEB_PORT=80
PGBOUNCER_PORT=6432
```

---

## Docker Compose Services

### 1. **db** - PostgreSQL Database
- **Image**: postgres:15-alpine
- **Port**: 5432
- **Volume**: postgres_data (persistent storage)
- **Health Check**: Enabled

```bash
# Access database
docker-compose exec db psql -U postgres -d ahsp_sni_db

# Backup database
docker-compose exec db pg_dump -U postgres ahsp_sni_db > backup.sql

# Restore database
docker-compose exec -T db psql -U postgres ahsp_sni_db < backup.sql
```

### 2. **redis** - Cache & Message Broker
- **Image**: redis:7-alpine
- **Port**: 6379
- **Volume**: redis_data (persistent storage)
- **Health Check**: Enabled

```bash
# Test Redis connection
docker-compose exec redis redis-cli ping
docker-compose exec redis redis-cli -a your-password PING
```

### 3. **web** - Django Application (Gunicorn)
- **Port**: 8000
- **Volumes**: Code, staticfiles, media, logs
- **Worker Threads**: 4
- **Health Check**: http://localhost:8000/health/

```bash
# View logs
docker-compose logs -f web

# Rebuild after dependency changes
docker-compose build web
docker-compose up -d web
```

### 4. **pgbouncer** - Database Connection Pool (Optional)
- **Profile**: pgbouncer
- **Port**: 6432
- **Mode**: transaction

```bash
# Enable PgBouncer
docker-compose --profile pgbouncer up -d pgbouncer

# Test PgBouncer
docker-compose exec pgbouncer psql -h localhost -p 6432 -U postgres -d ahsp_sni_db
```

### 5. **celery** - Async Task Worker (Optional)
- **Profile**: celery

```bash
# Enable Celery
docker-compose --profile celery up -d celery

# View Celery logs
docker-compose logs -f celery
```

### 6. **celery-beat** - Scheduled Tasks (Optional)
- **Profile**: celery
- Depends on: celery

### 7. **flower** - Celery Monitor (Optional)
- **Profile**: celery
- **Port**: 5555
- **Access**: http://localhost:5555

---

## Commands Reference

### Container Management
```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# View running containers
docker-compose ps

# View logs
docker-compose logs -f [service_name]

# Rebuild specific service
docker-compose build [service_name]
```

### Django Management
```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create migrations
docker-compose exec web python manage.py makemigrations

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Shell
docker-compose exec web python manage.py shell

# Run tests
docker-compose exec web pytest
```

### Database Operations
```bash
# Connect to database
docker-compose exec db psql -U postgres -d ahsp_sni_db

# Backup database
docker-compose exec db pg_dump -U postgres ahsp_sni_db > backup_$(date +%Y%m%d).sql

# Restore database
docker-compose exec -T db psql -U postgres ahsp_sni_db < backup.sql

# Check connections
docker-compose exec db psql -U postgres -d ahsp_sni_db -c "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;"
```

### Celery Operations (if enabled)
```bash
# View active tasks
docker-compose exec flower curl http://localhost:5555/api/tasks

# Purge queue
docker-compose exec celery celery -A config purge

# Monitor in real-time
docker-compose logs -f celery
```

### Development Workflow
```bash
# Development with hot reload
docker-compose exec web python manage.py runserver 0.0.0.0:8000

# Run specific app tests
docker-compose exec web pytest detail_project/tests/

# Generate coverage report
docker-compose exec web pytest --cov=. detail_project/tests/
```

---

## Deployment

### Production Checklist
- [ ] Change `DJANGO_SECRET_KEY` ke nilai random
- [ ] Set `DJANGO_DEBUG=False`
- [ ] Update `DJANGO_ALLOWED_HOSTS` dengan domain asli
- [ ] Setup strong passwords untuk PostgreSQL dan Redis
- [ ] Configure HTTPS/SSL
- [ ] Setup backup strategy untuk database
- [ ] Configure proper logging
- [ ] Setup monitoring dan alerting

### Pre-deployment Testing
```bash
# Build production image
docker build -t ahsp:latest .

# Run production tests
docker-compose -f docker-compose.yml up --abort-on-container-exit

# Check for security issues
docker-compose exec web pip-audit
```

### Docker Registry (Optional - Push to Docker Hub)
```bash
# Tag image
docker tag ahsp:latest yourusername/ahsp:latest

# Login to Docker Hub
docker login

# Push image
docker push yourusername/ahsp:latest

# Pull on another machine
docker pull yourusername/ahsp:latest
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Error
```
Error: could not translate host name "db" to address
```
**Solution:**
```bash
# Ensure db service is running
docker-compose ps

# Restart db service
docker-compose restart db

# Check database logs
docker-compose logs db
```

#### 2. Port Already in Use
```
Error: bind: address already in use :::8000
```
**Solution:**
```bash
# Change port in .env
# Or stop other containers using the port
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows
```

#### 3. Out of Memory
```
Cannot allocate memory
```
**Solution:**
- Increase Docker Desktop memory allocation
- Reduce number of Gunicorn workers
- Clear Docker unused resources:
```bash
docker system prune -a
docker volume prune
```

#### 4. Permission Denied
```
Error: permission denied while trying to connect to Docker daemon
```
**Solution (Linux):**
```bash
sudo usermod -aG docker $USER
# Logout and login again
```

#### 5. Redis Connection Refused
```
Error: Connection refused - can't connect to Redis
```
**Solution:**
```bash
# Check Redis is running
docker-compose ps redis

# Verify Redis password
docker-compose exec redis redis-cli -a your-password ping

# Restart Redis
docker-compose restart redis
```

#### 6. Static Files Not Loading
```bash
# Rebuild and collect static files
docker-compose build web
docker-compose exec web python manage.py collectstatic --noinput --clear
docker-compose restart web
```

### Debug Mode
```bash
# Enable debug logs
docker-compose logs -f web

# Execute shell in container
docker-compose exec web bash

# Run Django shell
docker-compose exec web python manage.py shell

# Check environment variables
docker-compose exec web env | grep DJANGO
```

### Performance Tuning
```bash
# Increase Gunicorn workers (in docker-compose.yml)
# Change: --workers 4 ke --workers 8

# Increase database connections (pgbouncer)
# Edit: pgbouncer/pgbouncer.ini
# default_pool_size = 25

# Monitor resources
docker-compose stats
```

---

## Advanced Configuration

### Using Docker Compose Overrides
Buat file `docker-compose.override.yml` untuk development overrides:
```yaml
version: '3.9'
services:
  web:
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - ./:/app
```

### Custom Django Settings
```bash
# Use different settings module
docker-compose exec web python manage.py shell \
  --settings=config.settings.production
```

### Network Inspection
```bash
# List networks
docker network ls

# Inspect ahsp_network
docker network inspect ahsp_network

# Connect container to existing network
docker run --network ahsp_network [image]
```

---

## Security Best Practices

1. **Secret Management**
   - Use `.env` files (include in .gitignore)
   - Consider using Docker Secrets untuk production
   - Rotate secrets regularly

2. **Image Security**
   - Use specific image versions (tidak `latest`)
   - Scan images: `docker scan ahsp:latest`
   - Keep base images updated

3. **Container Security**
   - Run as non-root user (appuser dalam Dockerfile)
   - Use read-only filesystems where possible
   - Limit container resources

4. **Network Security**
   - Use internal networks
   - Expose hanya necessary ports
   - Setup firewall rules

---

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Deployment Guide](https://docs.djangoproject.com/en/5.0/howto/deployment/)
- [PostgreSQL Docker](https://hub.docker.com/_/postgres)
- [Redis Docker](https://hub.docker.com/_/redis)

---

## FAQ

**Q: Bagaimana cara update dependencies?**
A: Edit requirements.txt, rebuild image:
```bash
docker-compose build --no-cache web
docker-compose up -d web
```

**Q: Bagaimana cara backup database production?**
A: 
```bash
docker-compose exec db pg_dump -U postgres ahsp_sni_db | gzip > backup-$(date +%Y%m%d-%H%M%S).sql.gz
```

**Q: Apakah bisa pakai localhost dari machine lain?**
A: Gunakan IP address machine:
```
http://192.168.x.x:8000
```
Dan update DJANGO_ALLOWED_HOSTS di .env

**Q: Bagaimana cara setup SSL/HTTPS?**
A: Gunakan reverse proxy (nginx) di depan Django dengan SSL certificate

---

## Support & Contribution

Untuk issues atau questions, buat issue di repository atau hubungi team developer.

---

**Last Updated**: 2026-01-13
**Version**: 1.0
