# ⚡ DOCKER QUICK START - PC ALIN (2 MENIT SUMMARY)

**Setup time**: ~30 menit first time, ~5 menit selanjutnya

---

## 🎯 LANGKAH SUPER SINGKAT

### 1️⃣ Install Docker (10 menit)
```
Windows/macOS: Download Docker Desktop → Install → Restart
Linux: curl -fsSL https://get.docker.com | sudo sh
```

### 2️⃣ Clone Repo (1 menit)
```bash
git clone https://github.com/[ORG]/DJANGO-AHSP-PROJECT.git
cd DJANGO-AHSP-PROJECT
```

### 3️⃣ Setup .env (1 menit)
```bash
cp .env.example .env
# Sudah cukup! Default values untuk development sudah oke
```

### 4️⃣ BUILD & RUN (15 menit)
```bash
# Build image
docker-compose build

# Expected output (first time: ~15 menit):
# [1/2] Building base...
# [2/2] Building runtime...
# Successfully built [hash]
# Successfully tagged django_ahsp_project:latest

# Start services
docker-compose up -d

# Expected output:
# Creating ahsp_postgres ... done
# Creating ahsp_redis ... done
# Creating ahsp_web ... done

# Wait ~30 seconds...
```

### 5️⃣ ACCESS APPLICATION ✅
```
http://localhost:8000           ← Main app
http://localhost:8000/admin     ← Admin (user: admin, pw: admin123)
```

---

## 📊 WHAT'S INCLUDED

```
✅ PostgreSQL 15          → localhost:5432
✅ Redis 7                → localhost:6379
✅ Django + Gunicorn      → localhost:8000
✅ Vite + TanStack        → Auto-bundled
✅ Node.js + npm          → Auto-installed
✅ 119 Python packages    → Auto-installed
✅ 15+ npm packages       → Auto-installed
✅ PgBouncer (optional)   → docker-compose --profile pgbouncer up
✅ Celery (optional)      → docker-compose --profile celery up
✅ Flower monitor         → localhost:5555 (with Celery)
```

---

## 🔧 COMMON COMMANDS

### View Status
```bash
docker-compose ps

# Expected output:
# NAME            IMAGE               STATUS           PORTS
# ahsp_postgres   postgres:15-alpine  Up (healthy)     5432/tcp
# ahsp_redis      redis:7-alpine      Up (healthy)     6379/tcp
# ahsp_web        django_ahsp...      Up (healthy)     0.0.0.0:8000->8000/tcp
```

### View Logs
```bash
docker-compose logs -f web

# Expected output:
# [2026-01-13 12:00:00 +0000] [1] [INFO] Starting gunicorn 21.0.0
# [2026-01-13 12:00:00 +0000] [1] [INFO] Listening at: http://0.0.0.0:8000
# [2026-01-13 12:00:00 +0000] [1] [INFO] Using worker: sync
# [2026-01-13 12:00:01 +0000] [10] [INFO] Booting worker with pid: 10
# (Ctrl+C to stop)
```

### Enter Django Shell
```bash
docker-compose exec web python manage.py shell

# Expected output:
# Python 3.11.x (main, ...)
# Type "help", "copyright", "credits" or "license" for more information.
# (InteractiveConsole)
# >>>
# (Type exit() to quit)
```

### Run Tests
```bash
docker-compose exec web pytest

# Expected output:
# ======================== test session starts =========================
# collected X items
# tests/test_models.py ..................                        [100%]
# ======================== X passed in 1.23s ==========================
```

### Stop Services
```bash
docker-compose down

# Expected output:
# Stopping ahsp_web ... done
# Stopping ahsp_redis ... done
# Stopping ahsp_postgres ... done
# Removing ahsp_web ... done
# Removing ahsp_redis ... done
# Removing ahsp_postgres ... done
# Removing network ahsp_network
```

### Restart Services
```bash
docker-compose restart

# Expected output:
# Restarting ahsp_postgres ... done
# Restarting ahsp_redis ... done
# Restarting ahsp_web ... done
```

---

## 🚨 IF SOMETHING GOES WRONG

```bash
# Check logs
docker-compose logs -f web

# Rebuild
docker-compose build --no-cache
docker-compose down
docker-compose up -d

# Full reset (WARNING: DELETES DATA)
docker-compose down -v
docker system prune -a
docker-compose build --no-cache
docker-compose up -d
```

---

## ✅ VERIFY ALL WORKING

### Test Database
```bash
docker-compose exec db psql -U postgres -d ahsp_sni_db -c "SELECT version();"

# Expected output:
#  version
# ─────────────────────────────────────────────────────────────────────
#  PostgreSQL 15.x on x86_64-pc-linux-gnu, compiled by gcc (GCC) 12.2.0
# (1 row)
```

### Test Redis
```bash
docker-compose exec redis redis-cli -a password_dari_.env ping

# Expected output:
# PONG
```

### Test Django Migrations
```bash
docker-compose exec web python manage.py migrate --check

# Expected output:
# Migrations OK
# (or if need migration: [M] django.contrib.auth.0001_initial)
```

### Test Web Browser
```bash
# Browser: http://localhost:8000

# Expected:
# ✅ Django application page loads
# ✅ CSS/static files loaded properly
# ✅ No 502/503 errors
# ✅ Admin link visible
```

---

## 📋 Checklist untuk PC Alin (atau PC lain)

Sebelum menjalankan project di PC baru, pastikan:

### Prerequisites
- [ ] Install Docker Desktop (Windows/Mac) atau Docker Engine (Linux)
- [ ] Install Docker Compose (sudah included di Docker Desktop)
- [ ] Install Git
- [ ] Minimal 8GB RAM, 10GB disk space
- [ ] Internet connection untuk pull Docker images

### Setup Steps
1. [ ] Clone repository: `git clone <repo-url>`
2. [ ] Copy `.env.example` ke `.env`: `cp .env.example .env`
3. [ ] Edit `.env` sesuai kebutuhan lokal
4. [ ] Run: `docker-compose up -d --build`
5. [ ] Check: `docker-compose ps` (semua harus "Up")
6. [ ] Access: http://localhost:8000

---

## 🚀 Getting Started

### Windows Users (Recommended: PowerShell)

```powershell
# 1. Clone project
git clone <repository-url>
cd django-ahsp-project

# Expected output:
# Cloning into 'django-ahsp-project'...
# Receiving objects: 100% (XXX/XXX), XX.XX MiB | X.XX MiB/s
# Resolving deltas: 100% (XXX/XXX), done.

# 2. Load helper module
. .\docker-helper.ps1

# Expected output:
# (No output if successful)

# 3. Initialize project (first time only)
Initialize-Project

# Expected output:
# [INFO] Creating .env file...
# [INFO] Building Docker images...
# Successfully tagged django_ahsp_project:latest
# [INFO] Starting services...
# Creating ahsp_postgres ... done
# Creating ahsp_redis ... done
# Creating ahsp_web ... done
# [INFO] Project initialized successfully!

# 4. Access application
# Browser: http://localhost:8000 → Application loads ✅
# Admin: http://localhost:8000/admin (credentials: admin/admin)

# 5. View logs anytime
View-Logs web

# Expected output:
# [2026-01-13 12:00:00 +0000] [1] [INFO] Starting gunicorn 21.0.0
# [2026-01-13 12:00:00 +0000] [1] [INFO] Listening at: http://0.0.0.0:8000

# 6. Stop services
Stop-Services

# Expected output:
# Stopping ahsp_web ... done
# Stopping ahsp_redis ... done
# Stopping ahsp_postgres ... done
```

### Linux/macOS Users

```bash
# 1. Clone project
git clone <repository-url>
cd django-ahsp-project

# Expected output:
# Cloning into 'django-ahsp-project'...
# Receiving objects: 100% (XXX/XXX), XX.XX MiB | X.XX MiB/s

# 2. Make helper script executable
chmod +x docker-helper.sh

# Expected output:
# (No output if successful)

# 3. Initialize project (first time only)
./docker-helper.sh setup

# Expected output:
# ✅ Creating .env file...
# ✅ Building Docker images...
# Successfully tagged django_ahsp_project:latest
# ✅ Starting services...
# Creating ahsp_postgres ... done
# Creating ahsp_redis ... done
# Creating ahsp_web ... done
# ✅ Running migrations...
# Operations to perform:
#   Apply all migrations: admin, auth, contenttypes, ...
# Running migrations:
#   Applying contenttypes.0001_initial... OK
# ✅ Project ready! Access: http://localhost:8000

# 4. Access application
# Browser: http://localhost:8000 → Application loads ✅

# 5. Other commands
./docker-helper.sh logs web
# Expected: Shows Gunicorn logs

./docker-helper.sh migrate
# Expected: Running migrations... Operations to perform...

./docker-helper.sh down
# Expected: Stopping services... done
```

### Manual Setup (Any OS)

```bash
# 1. Copy env file
cp .env.example .env
# Expected output: (no output if successful)

# Edit .env dengan text editor
# nano .env  (or use your preferred editor)

# 2. Build images
docker-compose build

# Expected output:
# Building web
# [1/2] FROM python:3.11-slim as builder
# [2/2] FROM python:3.11-slim
# Successfully built abc123def456
# Successfully tagged django_ahsp_project:latest

# 3. Start services
docker-compose up -d

# Expected output:
# Creating ahsp_postgres ... done
# Creating ahsp_redis ... done
# Creating ahsp_web ... done

# 4. Verify services running
docker-compose ps

# Expected output:
# NAME            IMAGE               STATUS           PORTS
# ahsp_postgres   postgres:15-alpine  Up (healthy)     5432/tcp
# ahsp_redis      redis:7-alpine      Up (healthy)     6379/tcp
# ahsp_web        django_ahsp:latest  Up (healthy)     0.0.0.0:8000->8000/tcp

# 5. Run migrations
docker-compose exec web python manage.py migrate

# Expected output:
# Operations to perform:
#   Apply all migrations: admin, auth, contenttypes, sessions, ...
# Running migrations:
#   Applying contenttypes.0001_initial... OK
#   Applying auth.0001_initial... OK
# (multiple migrations)
# 18 migrations applied successfully

# 6. Create superuser
docker-compose exec web python manage.py createsuperuser

# Expected output:
# Username: admin
# Email address: admin@example.com
# Password:
# Password (again):
# Superuser created successfully.

# 7. Collect static
docker-compose exec web python manage.py collectstatic --noinput

# Expected output:
# 127 static files copied to '/app/staticfiles', 128 post-processed.
```

---

## 📁 Struktur Docker

```
docker-compose.yml         # Orchestration semua services
Dockerfile                 # Build image untuk Django app
.dockerignore             # Files yang tidak included di image
docker-entrypoint.sh      # Script initialization sebelum app start
docker-helper.sh/.ps1     # Helper commands (Linux/Windows)
.env.example              # Environment template
.env.production           # Production settings
.env.staging              # Staging settings
DOCKER_SETUP_GUIDE.md     # Documentation lengkap
```

---

## 🔧 Available Services

### Web Application (Django + Gunicorn)
```bash
# Port: 8000
# Access: http://localhost:8000
docker-compose logs -f web

# Expected output:
# [2026-01-13 12:00:00 +0000] [1] [INFO] Starting gunicorn 21.0.0
# [2026-01-13 12:00:01 +0000] [1] [INFO] Listening at: http://0.0.0.0:8000 (1)
# [2026-01-13 12:00:01 +0000] [1] [INFO] Using worker: sync
# [2026-01-13 12:00:02 +0000] [10] [INFO] Booting worker with pid: 10
```

### PostgreSQL Database
```bash
# Port: 5432 (internal), jangan expose ke internet
docker-compose exec db psql -U postgres -d ahsp_sni_db

# Expected output:
# psql (15.2)
# Type "help" for help.
# ahsp_sni_db=#
# (Type \q to quit)
```

### Redis Cache
```bash
# Port: 6379 (internal)
docker-compose exec redis redis-cli ping

# Expected output:
# PONG
```

### Optional: PgBouncer (Connection Pooling)
```bash
# Enable dengan profile
docker-compose --profile pgbouncer up -d pgbouncer
docker-compose exec pgbouncer psql -h localhost -p 6432 -U postgres
```

### Optional: Celery + Flower
```bash
# Enable async tasks
docker-compose --profile celery up -d celery celery-beat flower
# Access Flower: http://localhost:5555
```

---

## 🔐 Environment Variables

### Development (.env)
Sudah ada di `.env.example` - copy dan pakai

### Production (.env.production)
**PENTING**: Ubah semua placeholder values sebelum deploy!

```env
DJANGO_SECRET_KEY=GENERATE-NEW-KEY-HERE
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com
POSTGRES_PASSWORD=STRONG-PASSWORD
REDIS_PASSWORD=STRONG-PASSWORD
```

Cara generate Django secret key:
```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 📊 Common Tasks

### Database Management
```bash
# Connect to database
docker-compose exec db psql -U postgres -d ahsp_sni_db

# Expected output:
# psql (15.2)
# Type "help" for help.
# ahsp_sni_db=#

# Backup database
docker-compose exec db pg_dump -U postgres ahsp_sni_db | gzip > backup.sql.gz

# Expected output:
# (no output, creates backup.sql.gz file)
# You should see: -rw-r--r-- ... backup.sql.gz (with your date)

# Restore database
gunzip -c backup.sql.gz | docker-compose exec -T db psql -U postgres ahsp_sni_db

# Expected output:
# SET
# SET
# SET
# (multiple restore messages)
# COMMIT

# View connections
docker-compose exec db psql -U postgres -d ahsp_sni_db \
  -c "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;"

# Expected output:
#   datname   | count
# ────────────┼───────
#  ahsp_sni_db|     5
#  postgres   |     1
# (2 rows)
```

### Django Management
```bash
# Create migrations
docker-compose exec web python manage.py makemigrations

# Expected output:
# Migrations for 'app_name':
#   0002_model_field.py
#     - Add field 'field_name' to 'model_name'
# (or "No changes detected in models" if no changes)

# Run migrations
docker-compose exec web python manage.py migrate

# Expected output:
# Operations to perform:
#   Apply all migrations: admin, auth, ...
# Running migrations:
#   Applying app.0001_initial... OK

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Expected output:
# Username: admin
# Email: admin@test.com
# Password:
# Superuser created successfully.

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Expected output:
# 127 static files copied to '/app/staticfiles'.

# Django shell
docker-compose exec web python manage.py shell

# Expected output:
# Python 3.11.x (main, ...)
# Type "help", "copyright", "credits" or "license" for more information.
# (InteractiveConsole)
# >>>

# Run tests
docker-compose exec web pytest

# Expected output:
# ======================== test session starts =========================
# collected 15 items
# tests/test_models.py ....................                     [100%]
# ======================== 15 passed in 2.45s ==========================

# Run with coverage
docker-compose exec web pytest --cov=.

# Expected output:
# ======================== test session starts =========================
# collected 15 items
# tests/test_models.py ....................                     [100%]
# ---------- coverage: platform linux, python 3.11.x ----------
# Name                    Stmts   Miss  Cover
# ─────────────────────────────────────────
# app/models.py               15      2    87%
# TOTAL                      150     15    90%
# ======================== 15 passed in 2.45s ==========================
```

### Container Management
```bash
# View all containers
docker-compose ps

# Expected output:
# NAME            IMAGE               STATUS           PORTS
# ahsp_postgres   postgres:15-alpine  Up (healthy)     5432/tcp
# ahsp_redis      redis:7-alpine      Up (healthy)     6379/tcp
# ahsp_web        django_ahsp:latest  Up (healthy)     0.0.0.0:8000->8000/tcp

# View logs
docker-compose logs web

# Expected output:
# [2026-01-13 12:00:00 +0000] [1] [INFO] Starting gunicorn...
# [2026-01-13 12:00:01 +0000] [1] [INFO] Listening at...

# Follow logs (live)
docker-compose logs -f web

# Expected output: (same as above, updates in real-time)
# (Press Ctrl+C to stop following)

# Last 50 lines
docker-compose logs --tail 50 web

# Expected output: (last 50 lines of logs)

# Execute command in container
docker-compose exec web bash

# Expected output:
# root@container_id:/app#
# (Type 'exit' to quit)

# Restart service
docker-compose restart web

# Expected output:
# Restarting ahsp_web ... done

# Stop services
docker-compose stop

# Expected output:
# Stopping ahsp_web ... done
# Stopping ahsp_redis ... done
# Stopping ahsp_postgres ... done

# Start services
docker-compose start

# Expected output:
# Starting ahsp_postgres ... done
# Starting ahsp_redis ... done
# Starting ahsp_web ... done

# Remove everything (WARNING: DELETES DATA)
docker-compose down -v  # -v = remove volumes

# Expected output:
# Stopping ahsp_web ... done
# Stopping ahsp_redis ... done
# Stopping ahsp_postgres ... done
# Removing ahsp_web ... done
# Removing ahsp_redis ... done
# Removing ahsp_postgres ... done
# Removing network ahsp_network
# Removing volume ahsp_postgres_data
# Removing volume ahsp_redis_data
```

---

## 🐛 Troubleshooting

### Issue: "Cannot connect to Docker daemon"
**Solution**: 
- Windows/Mac: Start Docker Desktop
- Linux: `sudo systemctl start docker`

**Verify**:
```bash
docker ps
# Expected output: (list of containers or empty list)
# NOT: "Cannot connect to Docker daemon"
```

### Issue: "Port 8000 already in use"
**Solution**: 
```bash
# Change port in .env
WEB_PORT=8001

# Or find and stop other service
lsof -i :8000  # macOS/Linux
# Expected: Shows what's using port 8000

netstat -ano | findstr :8000  # Windows
# Expected: Shows process ID using port 8000

# Kill the process or restart Docker
```

### Issue: "Database connection refused"
**Solution**:
```bash
# Check if db is running
docker-compose ps db

# Expected output:
# NAME          IMAGE               STATUS           PORTS
# ahsp_postgres postgres:15-alpine  Up (healthy)     5432/tcp

# Check db logs
docker-compose logs db

# Expected output:
# [INFO] PostgreSQL Database directory appears to contain a database
# [INFO] Starting PostgreSQL
# [INFO] PostgreSQL started

# Restart db
docker-compose restart db

# Expected output:
# Restarting ahsp_postgres ... done
```

### Issue: "Redis connection refused"
**Solution**:
```bash
# Check Redis
docker-compose exec redis redis-cli ping

# Expected output:
# PONG

# Verify password in .env
docker-compose exec redis redis-cli -a your-password PING

# Expected output:
# PONG

# Restart Redis
docker-compose restart redis

# Expected output:
# Restarting ahsp_redis ... done
```

### Issue: "Static files not loading"
**Solution**:
```bash
docker-compose exec web python manage.py collectstatic --noinput --clear

# Expected output:
# 127 static files copied to '/app/staticfiles', 128 post-processed.

docker-compose restart web

# Expected output:
# Restarting ahsp_web ... done

# Verify in browser:
# http://localhost:8000 (should now have styled CSS) ✅
```

### Issue: "Out of memory"
**Solution**:
- Increase Docker memory limit (Settings)
- Reduce Gunicorn workers (change --workers 4 ke 2)
- Clear unused Docker resources:
```bash
docker system prune -a

# Expected output:
# WARNING! This will remove:
#  - all stopped containers
#  - all networks not used by at least one container
#  - all unused images
# Total reclaimed space: XXX.XX GB
```

---

## 🔍 Health Checks

Verifikasi semua services berjalan baik:

```bash
# Check all containers
docker-compose ps

# Web service health
curl http://localhost:8000/health/

# Database connection
docker-compose exec db psql -U postgres -d ahsp_sni_db -c "SELECT 1"

# Redis connection
docker-compose exec redis redis-cli ping

# View resource usage
docker-compose stats
```

---

## 🌐 Network Connectivity

### Akses dari PC/Device Lain di LAN

1. Find IP address PC Alin:
```bash
# Windows
ipconfig

# Linux/Mac
ifconfig
# Look for en0 atau eth0 dengan format 192.168.x.x
```

2. Update `.env`:
```env
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.100
```

3. Restart container:
```bash
docker-compose restart web
```

4. Access dari device lain:
```
http://192.168.1.100:8000
```

---

## 📦 Deployment to Production

### Pre-Deployment Checklist
- [ ] Change `DJANGO_SECRET_KEY`
- [ ] Set `DJANGO_DEBUG=False`
- [ ] Update `DJANGO_ALLOWED_HOSTS`
- [ ] Generate strong passwords for DB & Redis
- [ ] Setup backup strategy
- [ ] Configure logging (Sentry, DataDog)
- [ ] Setup SSL/HTTPS (nginx + Let's Encrypt)

### Using .env.production
```bash
# Copy to production machine
scp .env.production user@server:/app/.env

# Start with production settings
docker-compose up -d
```

### Docker Hub (Push your image)
```bash
# Build
docker build -t yourusername/ahsp:latest .

# Login
docker login

# Push
docker push yourusername/ahsp:latest

# On another machine
docker pull yourusername/ahsp:latest
docker-compose up -d
```

---

## 🎓 Tips & Best Practices

1. **Always use version control**
   - Commit `.env.example` (tidak `.env`)
   - Commit Dockerfile, docker-compose.yml
   - Use `.dockerignore` dengan baik

2. **Development Workflow**
   - Jangan edit di container, edit di host
   - Volumes sudah di-mount untuk live reload
   - Use `docker-compose logs -f` untuk debug

3. **Performance**
   - Use `.dockerignore` untuk faster builds
   - Multi-stage Dockerfile untuk smaller images
   - Cache layers dengan good layer ordering

4. **Security**
   - Jangan commit `.env` files
   - Use strong passwords
   - Regular update base images
   - Scan images: `docker scan yourusername/ahsp`

5. **Monitoring**
   - Setup health checks
   - Monitor logs regularly
   - Use `docker-compose stats` untuk resource usage

---

## 📚 Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Deployment Guide](https://docs.djangoproject.com/en/5.0/howto/deployment/)
- [PostgreSQL Docker Guide](https://hub.docker.com/_/postgres)
- [Redis Docker Guide](https://hub.docker.com/_/redis)
- [DOCKER_SETUP_GUIDE.md](./DOCKER_SETUP_GUIDE.md) - Comprehensive technical guide

---

## 🆘 Getting Help

Jika ada masalah:

1. Check logs first:
   ```bash
   docker-compose logs web
   docker-compose logs db
   ```

2. Verify services running:
   ```bash
   docker-compose ps
   ```

3. Test connectivity:
   ```bash
   curl http://localhost:8000/
   docker-compose exec db psql -U postgres -c "SELECT 1"
   ```

4. Check disk space:
   ```bash
   docker system df
   ```

5. Restart everything:
   ```bash
   docker-compose down -v
   docker-compose up -d --build
   ```

---

## 📝 Version History

- **v1.0** (2026-01-13): Initial Docker setup with PostgreSQL, Redis, Celery support

---

**Good luck! 🚀**

Jika ada pertanyaan atau issues, hubungi tim development.
