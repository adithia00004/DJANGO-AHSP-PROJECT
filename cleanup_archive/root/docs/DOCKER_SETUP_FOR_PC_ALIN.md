# 🚀 DOCKER SETUP GUIDE - UNTUK PC ALIN

**Date**: January 13, 2026  
**Status**: ✅ Ready untuk PC Alin  
**Waktu Setup**: ~30 menit (first time with Docker install), ~5 menit (subsequent runs)

---

## 📋 PERSIAPAN AWAL

### Requirement Check (5 menit)

Sebelum mulai, PC Alin perlu pastikan:

**Windows:**
- [ ] Windows 10/11 (Build 19041+)
- [ ] Min 8GB RAM (recommended 16GB)
- [ ] Min 20GB disk space
- [ ] Administrator access

**macOS:**
- [ ] macOS 11+
- [ ] Min 8GB RAM
- [ ] Min 20GB disk space

**Linux:**
- [ ] Ubuntu 20.04+ / Debian 11+
- [ ] Min 4GB RAM (recommended 8GB)
- [ ] Min 20GB disk space

---

## 🐳 STEP 1: INSTALL DOCKER

### ✅ Option A: Windows (Recommended)

**Install Docker Desktop:**

1. Download: https://www.docker.com/products/docker-desktop
2. Run installer (waktu: ~10 menit)
3. Enable "Use WSL 2 based engine" during setup
4. Restart komputer
5. Verify:
   ```powershell
   docker --version
   docker-compose --version
   ```

**Alternative: Using Chocolatey**
```powershell
# Jalankan PowerShell as Administrator
choco install docker-desktop -y
# Restart required
```

### ✅ Option B: macOS

```bash
# Using Homebrew (recommended)
brew install --cask docker

# Or download from: https://www.docker.com/products/docker-desktop
```

Verify:
```bash
docker --version
docker-compose --version
```

### ✅ Option C: Linux (Ubuntu/Debian)

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify
docker --version
docker-compose --version
```

---

## 📥 STEP 2: PULL PROJECT DARI GIT

### Clone Repository

```bash
# Pilih direktori untuk project
cd C:\Users\[YourUsername]\Projects    # Windows
# atau
cd ~/Projects                           # macOS/Linux

# Clone repo
git clone https://github.com/[YOUR_ORG]/[YOUR_REPO].git
cd DJANGO_AHSP_PROJECT

# Verifikasi branch
git branch -a
git log --oneline -5
```

**Output yang diharapkan:**
```
* main (HEAD -> main)
  feature-branch-1
  feature-branch-2
  ...
```

---

## ⚙️ STEP 3: SETUP ENVIRONMENT VARIABLES

### 3.1 Copy .env Template

```bash
# Navigate to project folder
cd DJANGO_AHSP_PROJECT

# Copy template ke .env (development)
cp .env.example .env

# Verify file ada
ls -la .env
```

**Windows (PowerShell)**:
```powershell
Copy-Item ".env.example" ".env"
Get-Item ".env"
```

### 3.2 Review & Update .env (Optional untuk development)

Untuk development, default values di `.env.example` sudah cukup. Tapi jika perlu customize:

```bash
# Edit file
nano .env          # macOS/Linux
# atau
notepad .env       # Windows
```

**Key variables untuk development** (sudah ter-set di .env.example):
```env
DJANGO_SECRET_KEY=your-insecure-dev-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
POSTGRES_DB=ahsp_sni_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
REDIS_PASSWORD=redis_password
```

### 3.3 Verifikasi .env ada di .gitignore

```bash
# Check .env di .gitignore
cat .gitignore | grep "\.env"
```

**Output yang diharapkan:**
```
.env
.env.local
.env.docker
.env.production
.env.staging
```

✅ Jika ada, berarti `.env` tidak akan ter-commit (aman!)

---

## 🚀 STEP 4: BUILD & RUN DOCKER

### 4.1 Build Docker Image

```bash
# Navigate to project folder
cd DJANGO_AHSP_PROJECT

# Build image (pertama kali: ~10-15 menit tergantung internet)
docker-compose build

# Atau jika mau rebuild dari scratch
docker-compose build --no-cache
```

**What happens during build:**
```
✅ Download base images (Python, PostgreSQL, Redis, Node.js)
✅ Install 119 Python packages
✅ Install Node.js + npm
✅ Install 15+ npm packages (@tanstack, Vite, Vitest, etc)
✅ Build frontend (npm run build)
✅ Collect static files
✅ Create Docker image (~2GB)
```

**Output yang diharapkan:**
```
Successfully built [image-hash]
Successfully tagged django_ahsp_project:latest
```

### 4.2 Jalankan Services (Minimal - PostgreSQL + Redis + Django)

```bash
# Start services
docker-compose up -d

# Tunggu ~30 detik untuk services siap
sleep 30
```

**Verify services running:**
```bash
# Check all containers
docker-compose ps

# Output yang diharapkan:
# NAME              COMMAND                  STATUS
# ahsp_db           postgres                 Up (healthy)
# ahsp_redis        redis-server             Up (healthy)
# ahsp_web          gunicorn                 Up (healthy)
```

### 4.3 Jalankan Services (Lengkap - dengan Optional Services)

Jika ingin include PgBouncer, Celery, Flower:

```bash
# Start semua services including optional
docker-compose --profile pgbouncer --profile celery up -d

# Check all containers
docker-compose ps

# Output yang diharapkan:
# NAME              COMMAND                  STATUS
# ahsp_db           postgres                 Up (healthy)
# ahsp_redis        redis-server             Up (healthy)
# ahsp_pgbouncer    pgbouncer                Up (healthy)
# ahsp_web          gunicorn                 Up (healthy)
# ahsp_celery       celery worker            Up
# ahsp_celery_beat  celery beat              Up
# ahsp_flower       flower                   Up (healthy)
```

---

## ✅ STEP 5: VERIFY SETUP

### 5.1 Check Services Health

```bash
# Lihat status semua services
docker-compose ps

# Lihat logs (real-time)
docker-compose logs -f web

# Untuk stop logs: Ctrl+C
```

### 5.2 Test Database Connection

```bash
# Connect to PostgreSQL
docker-compose exec db psql -U postgres -d ahsp_sni_db -c "SELECT version();"

# Output yang diharapkan:
# PostgreSQL 15.x on...
```

### 5.3 Test Redis Connection

```bash
# Connect to Redis
docker-compose exec redis redis-cli -a password_dari_.env ping

# Output yang diharapkan:
# PONG
```

### 5.4 Test Django Application

```bash
# Check Django migrations
docker-compose exec web python manage.py migrate --check

# Create superuser (optional)
docker-compose exec web python manage.py createsuperuser

# Atau otomatis create dev user:
docker-compose exec web python manage.py shell
# >>> dari python shell:
# from django.contrib.auth import get_user_model
# User = get_user_model()
# User.objects.create_superuser('admin', 'admin@test.com', 'admin123')
```

### 5.5 Access Application

Buka browser:

| Service | URL | Status |
|---------|-----|--------|
| **Django Web** | http://localhost:8000 | ✅ Main app |
| **Admin** | http://localhost:8000/admin | ✅ Login: admin/admin123 |
| **Flower** | http://localhost:5555 | ✅ Celery monitor (jika --profile celery) |

---

## 🛠️ STEP 6: HELPER SCRIPTS (OPTIONAL)

### Untuk Windows Users

File: `docker-helper.ps1`

```powershell
# Show menu
.\docker-helper.ps1

# Atau direct commands:
.\docker-helper.ps1 -Command up       # Start services
.\docker-helper.ps1 -Command down     # Stop services
.\docker-helper.ps1 -Command logs     # View logs
.\docker-helper.ps1 -Command shell    # Django shell
```

### Untuk macOS/Linux Users

File: `docker-helper.sh`

```bash
# Make executable
chmod +x docker-helper.sh

# Show menu
./docker-helper.sh

# Atau direct commands:
./docker-helper.sh up       # Start services
./docker-helper.sh down     # Stop services
./docker-helper.sh logs     # View logs
./docker-helper.sh shell    # Django shell
```

---

## 📝 COMMON COMMANDS

### Start Services
```bash
# Minimal setup
docker-compose up -d

# Atau dengan optional services
docker-compose --profile pgbouncer --profile celery up -d
```

### Stop Services
```bash
docker-compose down
```

### View Logs
```bash
# Lihat logs dari web service
docker-compose logs -f web

# Lihat logs dari specific service
docker-compose logs -f db
docker-compose logs -f redis
docker-compose logs -f celery

# Untuk stop logs: Ctrl+C
```

### Execute Commands in Container
```bash
# Django shell
docker-compose exec web python manage.py shell

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Run tests
docker-compose exec web pytest

# Database backup
docker-compose exec db pg_dump -U postgres ahsp_sni_db > backup.sql
```

### Troubleshooting

```bash
# Rebuild image (if code changed)
docker-compose build --no-cache

# Remove all containers & volumes (WARNING: DELETES DATA!)
docker-compose down -v

# Check disk space used by Docker
docker system df

# Clean up unused images/containers
docker system prune -a

# View network config
docker network ls
docker network inspect ahsp_network
```

---

## ⚠️ IMPORTANT NOTES

### .env File - JANGAN COMMIT!

✅ **Correct:**
```bash
# .env is in .gitignore
git status
# .env not listed
```

❌ **Wrong:**
```bash
# .env accidentally committed
git status
# .env listed as modified
```

### Database Persistence

Data PostgreSQL & Redis tersimpan di Docker volumes:
```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect ahsp_postgres_data
docker volume inspect ahsp_redis_data
```

Data akan PERSIST saat:
- ✅ Stop & start containers (`docker-compose down` → `docker-compose up`)

Data akan HILANG saat:
- ❌ Delete volumes (`docker-compose down -v`)
- ❌ Full system prune (`docker system prune -a`)

### Port Conflicts

Jika ada error "port already in use":

```bash
# Check what's using port 8000
lsof -i :8000          # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 [PID]          # macOS/Linux
taskkill /PID [PID] /F # Windows

# Atau gunakan port berbeda di docker-compose.yml
# Ubah: "8000:8000" → "9000:8000"
```

### Memory Issues

Jika Docker kehabisan memory:

```bash
# Limit memory per service (edit docker-compose.yml)
services:
  web:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G

# Restart
docker-compose restart
```

---

## 📊 EXPECTED STARTUP SEQUENCE

```
0s   → docker-compose up -d
     → Starting services...
     
5s   → PostgreSQL started
     → ✅ Database ready
     
10s  → Redis started
     → ✅ Cache ready
     
15s  → Django migrations running
     → ✅ Schema created
     
20s  → Static files collecting
     → ✅ Static assets ready
     
25s  → Gunicorn starting
     → ✅ Web server ready
     
30s+ → All services healthy
     → ✅ Application accessible at http://localhost:8000
```

---

## 🎯 VERIFICATION CHECKLIST

Setelah setup selesai, verify:

- [ ] `docker-compose ps` → semua containers UP (healthy)
- [ ] `docker-compose logs web` → no ERROR messages
- [ ] `http://localhost:8000` → page loads
- [ ] `http://localhost:8000/admin` → admin interface
- [ ] Database query works: `docker-compose exec db psql ...`
- [ ] Redis ping works: `docker-compose exec redis redis-cli ping`
- [ ] Django shell works: `docker-compose exec web python manage.py shell`
- [ ] Static files served: CSS/JS loading in browser
- [ ] Migrations applied: `docker-compose exec web python manage.py migrate --check`

---

## 🚨 TROUBLESHOOTING

### Problem: "docker: command not found"

```bash
# Solution: Install Docker Desktop atau jalankan installer ulang
# Verify:
docker --version
docker-compose --version
```

### Problem: "Cannot connect to Docker daemon"

```bash
# Windows: Start Docker Desktop
# macOS: Open Docker from Applications
# Linux: Start Docker service
sudo systemctl start docker
```

### Problem: "Port 5432 already in use"

```bash
# Option 1: Stop other PostgreSQL service
# Option 2: Change port in docker-compose.yml
# ports:
#   - "5433:5432"  # Changed from 5432
```

### Problem: "Failed to build Docker image"

```bash
# Solution: Clean rebuild
docker-compose down -v
docker system prune -a
docker-compose build --no-cache
```

### Problem: "Migrations not running"

```bash
# Check logs
docker-compose logs db
docker-compose logs web

# Manual run migrations
docker-compose exec web python manage.py migrate

# Check status
docker-compose exec web python manage.py migrate --check
```

### Problem: "Static files not loading"

```bash
# Collect static files
docker-compose exec web python manage.py collectstatic --noinput --clear

# Check volume
docker volume inspect ahsp_static_volume

# Rebuild
docker-compose build --no-cache
docker-compose down
docker-compose up -d
```

---

## 📚 NEXT STEPS AFTER SETUP

### 1. Verify All Components Work

```bash
# Test frontend (Vite + TanStack)
curl http://localhost:8000/

# Test API endpoints
curl http://localhost:8000/api/

# Test admin
curl http://localhost:8000/admin/

# Test database connectivity
docker-compose exec web python manage.py dbshell
```

### 2. Run Tests (Optional)

```bash
# Backend tests
docker-compose exec web pytest

# Frontend tests
docker-compose exec web npm run test:frontend

# Coverage
docker-compose exec web pytest --cov
```

### 3. Monitor Services

```bash
# Real-time logs
docker-compose logs -f

# Monitor resource usage
docker stats

# View specific service logs
docker-compose logs -f web   # Django
docker-compose logs -f db    # PostgreSQL
docker-compose logs -f redis # Redis
```

### 4. Scale Services (Optional)

```bash
# Run multiple Celery workers
docker-compose up -d --scale celery=3

# Check scaled services
docker-compose ps
```

---

## 📞 JIKA ADA MASALAH

1. **Check logs first:**
   ```bash
   docker-compose logs -f web
   docker-compose logs -f db
   docker-compose logs -f redis
   ```

2. **Verify Docker installation:**
   ```bash
   docker --version
   docker-compose --version
   docker images
   docker ps
   ```

3. **Check system resources:**
   ```bash
   docker system df
   docker stats
   ```

4. **Restart everything:**
   ```bash
   docker-compose restart
   # atau
   docker-compose down
   docker-compose up -d
   ```

5. **Full reset (if all else fails):**
   ```bash
   # WARNING: This will delete all data!
   docker-compose down -v
   docker system prune -a
   docker-compose build --no-cache
   docker-compose up -d
   ```

---

## ✅ YOU'RE ALL SET!

PC Alin sekarang bisa:
- ✅ Menjalankan project di Docker (Windows/macOS/Linux)
- ✅ Mengakses Django di http://localhost:8000
- ✅ Mengakses Admin di http://localhost:8000/admin
- ✅ Menggunakan PostgreSQL, Redis, Celery
- ✅ Menjalankan frontend dengan Vite + TanStack
- ✅ Semua dependency sudah installed automatically

**Waktu setup total: ~30 menit (first time), ~5 menit (selanjutnya)**

---

**Status**: ✅ Ready for Production  
**Created**: January 13, 2026  
**Last Updated**: January 13, 2026
