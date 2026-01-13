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

# Start services
docker-compose up -d

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

```bash
# View status
docker-compose ps

# View logs
docker-compose logs -f web

# Enter Django shell
docker-compose exec web python manage.py shell

# Run tests
docker-compose exec web pytest

# Stop services
docker-compose down

# Restart services
docker-compose restart
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

```bash
# Database
docker-compose exec db psql -U postgres -d ahsp_sni_db -c "SELECT version();"

# Redis
docker-compose exec redis redis-cli -a password_dari_.env ping

# Django
docker-compose exec web python manage.py migrate --check

# Browser: http://localhost:8000 ← Should load
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

# 2. Load helper module
. .\docker-helper.ps1

# 3. Initialize project (first time only)
Initialize-Project

# 4. Access application
# Browser: http://localhost:8000
# Admin: http://localhost:8000/admin (credentials: admin/admin)

# 5. View logs anytime
View-Logs web

# 6. Stop services
Stop-Services
```

### Linux/macOS Users

```bash
# 1. Clone project
git clone <repository-url>
cd django-ahsp-project

# 2. Make helper script executable
chmod +x docker-helper.sh

# 3. Initialize project (first time only)
./docker-helper.sh setup

# 4. Access application
# Browser: http://localhost:8000

# 5. Other commands
./docker-helper.sh logs web
./docker-helper.sh migrate
./docker-helper.sh down
```

### Manual Setup (Any OS)

```bash
# 1. Copy env file
cp .env.example .env
# Edit .env dengan text editor

# 2. Build images
docker-compose build

# 3. Start services
docker-compose up -d

# 4. Verify services running
docker-compose ps

# 5. Run migrations
docker-compose exec web python manage.py migrate

# 6. Create superuser
docker-compose exec web python manage.py createsuperuser

# 7. Collect static
docker-compose exec web python manage.py collectstatic --noinput
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
```

### PostgreSQL Database
```bash
# Port: 5432 (internal), jangan expose ke internet
docker-compose exec db psql -U postgres -d ahsp_sni_db
```

### Redis Cache
```bash
# Port: 6379 (internal)
docker-compose exec redis redis-cli ping
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

# Backup database
docker-compose exec db pg_dump -U postgres ahsp_sni_db | gzip > backup.sql.gz

# Restore database
gunzip -c backup.sql.gz | docker-compose exec -T db psql -U postgres ahsp_sni_db

# View connections
docker-compose exec db psql -U postgres -d ahsp_sni_db \
  -c "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;"
```

### Django Management
```bash
# Create migrations
docker-compose exec web python manage.py makemigrations

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Django shell
docker-compose exec web python manage.py shell

# Run tests
docker-compose exec web pytest

# Run with coverage
docker-compose exec web pytest --cov=.
```

### Container Management
```bash
# View all containers
docker-compose ps

# View logs
docker-compose logs web
docker-compose logs -f web         # Follow logs
docker-compose logs --tail 50 web  # Last 50 lines

# Execute command in container
docker-compose exec web bash

# Restart service
docker-compose restart web

# Stop services
docker-compose stop

# Start services
docker-compose start

# Remove everything
docker-compose down -v  # -v = remove volumes
```

---

## 🐛 Troubleshooting

### Issue: "Cannot connect to Docker daemon"
**Solution**: 
- Windows/Mac: Start Docker Desktop
- Linux: `sudo systemctl start docker`

### Issue: "Port 8000 already in use"
**Solution**: 
```bash
# Change port in .env
WEB_PORT=8001

# Or find and stop other service
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows
```

### Issue: "Database connection refused"
**Solution**:
```bash
# Check if db is running
docker-compose ps db

# Check db logs
docker-compose logs db

# Restart db
docker-compose restart db
```

### Issue: "Redis connection refused"
**Solution**:
```bash
# Check Redis
docker-compose exec redis redis-cli ping

# Verify password in .env
docker-compose exec redis redis-cli -a your-password PING

# Restart Redis
docker-compose restart redis
```

### Issue: "Static files not loading"
**Solution**:
```bash
docker-compose exec web python manage.py collectstatic --noinput --clear
docker-compose restart web
```

### Issue: "Out of memory"
**Solution**:
- Increase Docker memory limit (Settings)
- Reduce Gunicorn workers (change --workers 4 ke 2)
- Clear unused Docker resources: `docker system prune -a`

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
