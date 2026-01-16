# 👋 For PC Alin - Setup Guide

Halo Alin! Follow these steps to run AHSP Project di PC kamu.

---

## ⚡ Super Quick (5 Minutes)

### Step 1: Install Docker
- **Windows**: [Download Docker Desktop](https://www.docker.com/products/docker-desktop)
  - Jalankan installer
  - Restart komputer setelah install
  
- **macOS**: [Download Docker Desktop](https://www.docker.com/products/docker-desktop)
  - Jalankan installer
  - Restart setelah install

- **Linux**: Jalankan di terminal:
  ```bash
  sudo apt-get update
  sudo apt-get install docker.io docker-compose
  sudo usermod -aG docker $USER
  ```

### Step 2: Verify Installation
Buka terminal/PowerShell dan run:
```bash
docker --version
docker-compose --version
```
Harus keluar versi (contoh: Docker version 20.10.0)

### Step 3: Clone Project
```bash
git clone https://github.com/adithia00004/DJANGO-AHSP-PROJECT.git
cd DJANGO-AHSP-PROJECT
```

### Step 4: Run Project

**Windows (PowerShell)**
```powershell
# Open PowerShell
# Navigate ke project folder
cd path\to\DJANGO-AHSP-PROJECT

# Run helper
. .\docker-helper.ps1
Initialize-Project

# Wait 2-3 minutes untuk images build dan services start
```

**macOS/Linux**
```bash
chmod +x docker-helper.sh
./docker-helper.sh setup

# Wait 2-3 minutes
```

### Step 5: Access Application
Buka browser dan go to:
```
http://localhost:8000
```

Admin panel:
```
http://localhost:8000/admin
Username: admin
Password: admin
```

---

## ✅ Verification Checklist

Pastikan yang ini berhasil:

- [ ] Docker installed dan running
- [ ] Project cloned
- [ ] `docker-compose ps` shows all containers "Up"
- [ ] Browser bisa akses http://localhost:8000
- [ ] Admin login berhasil
- [ ] Tidak ada red error di console

---

## 🔧 Common Issues

### "Docker not found" or "docker-compose not found"
**Problem**: Docker belum installed atau PATH tidak set
**Solution**: 
1. Verify installation: `docker --version`
2. Restart terminal/PowerShell
3. Restart komputer jika perlu

### "Port 8000 already in use"
**Problem**: Port 8000 sudah dipakai aplikasi lain
**Solution**:
1. Edit `.env` file
2. Change `WEB_PORT=8000` ke `WEB_PORT=8001`
3. Restart: `docker-compose restart`
4. Access: http://localhost:8001

### "Cannot connect to Docker daemon"
**Problem**: Docker service tidak berjalan
**Solution**:
- **Windows**: Buka Docker Desktop dari Start Menu
- **macOS**: Buka Docker Desktop dari Applications
- **Linux**: `sudo systemctl start docker`

### "Services not starting / red error logs"
**Problem**: Berbagai kemungkinan
**Solution**:
```bash
# Check logs
docker-compose logs

# Restart everything
docker-compose restart

# Or start fresh
docker-compose down -v
docker-compose up -d --build
```

---

## 📚 Useful Commands

### Check status
```bash
docker-compose ps
```

### View logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs web
docker-compose logs db
docker-compose logs redis

# Follow logs (real-time)
docker-compose logs -f web
```

### Database access
```bash
# Connect to database
docker-compose exec db psql -U postgres -d ahsp_sni_db

# Create backup
docker-compose exec db pg_dump -U postgres ahsp_sni_db > backup.sql

# Restore backup
docker-compose exec -T db psql -U postgres ahsp_sni_db < backup.sql
```

### Django commands
```bash
# Create migrations
docker-compose exec web python manage.py makemigrations

# Run migrations
docker-compose exec web python manage.py migrate

# Create another superuser
docker-compose exec web python manage.py createsuperuser

# Django shell
docker-compose exec web python manage.py shell

# Run tests
docker-compose exec web pytest
```

### Container management
```bash
# Stop services
docker-compose stop

# Start services
docker-compose start

# Restart services
docker-compose restart

# Stop and remove everything (keep data)
docker-compose down

# Stop and remove everything (delete data)
docker-compose down -v

# Rebuild images
docker-compose build --no-cache
```

---

## 🎯 Development Workflow

### Making code changes
1. Edit file di project folder (menggunakan text editor biasa)
2. Code changes automatically reflected di container
3. Refresh browser untuk lihat changes
4. Check console jika ada error

### Database changes
```bash
# After menambah/mengubah models
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate

# Refresh browser
```

### Switching branches
```bash
# Stop current branch
docker-compose down -v

# Switch branch
git checkout branch-name

# Start dengan branch baru
docker-compose up -d --build
```

### Sharing database snapshot
```bash
# Create backup
docker-compose exec db pg_dump -U postgres ahsp_sni_db | gzip > snapshot.sql.gz

# Share file snapshot.sql.gz dengan team

# Restore di PC lain
gunzip -c snapshot.sql.gz | docker-compose exec -T db psql -U postgres ahsp_sni_db
```

---

## 🔐 Important Notes

### About .env file
- **Jangan commit `.env` file** - itu secret! ✗
- **Jangan beri `.env` file ke orang** - itu password! ✗
- **Always edit `.env` locally** sesuai PC kamu
- `.env.example` sudah safe untuk share

### Passwords
Default development passwords sudah safe (testing only):
- Database: `password`
- Redis: `redis_password`
- Admin: `admin`/`admin`

⚠️ **JANGAN PAKAI DI PRODUCTION!**

---

## 🚀 Next Steps

### Want to understand more?
1. Read: `DOCKER_QUICK_START.md` - More detailed guide
2. Read: `DOCKER_SETUP_GUIDE.md` - Technical deep dive

### Want to contribute?
1. Create branch: `git checkout -b feature/your-feature`
2. Make changes
3. Test: `docker-compose exec web pytest`
4. Create pull request

### Want to deploy to production?
1. Ask team lead
2. Read: `DOCKER_SETUP_GUIDE.md` section "Deployment"

---

## 💬 Need Help?

### If something doesn't work:

1. **Check logs first**
   ```bash
   docker-compose logs
   ```

2. **Try restarting**
   ```bash
   docker-compose restart
   ```

3. **Check if it's your PC**
   ```bash
   # Does docker work?
   docker ps
   
   # Does docker-compose work?
   docker-compose version
   ```

4. **Check resources**
   ```bash
   # Cukup memory?
   docker-compose stats
   ```

5. **If still stuck**
   - Check: `DOCKER_QUICK_START.md` section "Troubleshooting"
   - Check: `DOCKER_SETUP_GUIDE.md` section "Troubleshooting"
   - Ask: Team lead / Adithia

---

## 📋 Frequently Asked Questions

**Q: Bisakah saya pakai Linux Subsystem Windows (WSL)?**
A: Ya! Install Docker Desktop with WSL 2 backend

**Q: Berapa space yang dibutuhkan?**
A: ~10GB untuk images dan volumes

**Q: Bisakah saya akses database dari aplikasi lain?**
A: Ya, connect ke localhost:5432 (tapi perlu .env diedit)

**Q: Bagaimana cara update dependencies baru?**
A: Edit requirements.txt, then `docker-compose build --no-cache web`

**Q: Apakah saya perlu command line expert?**
A: Tidak! Semua command sudah simplified

**Q: Apakah bisa jalan offline?**
A: Tidak, need internet first untuk pull Docker images. After that bisa offline.

---

## 🎉 You're All Set!

Sekarang PC kamu setup dan ready untuk development! 

### What you have now:
- ✅ Django web application
- ✅ PostgreSQL database
- ✅ Redis cache
- ✅ All dependencies included
- ✅ Same environment sebagai team
- ✅ Easy to switch between projects

### Have fun coding! 🚀

---

**Last Updated**: 2026-01-13
**Version**: 1.0

Still questions? Check documentation atau hubungi Adithia!
