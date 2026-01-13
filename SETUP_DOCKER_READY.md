# ✅ Docker Setup Sudah Siap - Setup Docker Lengkap

**Status:** ✅ **READY FOR PRODUCTION**  
**Last Updated:** 2025-01-13  
**Tested On:** Windows 11 + Docker Desktop 29.1.3

---

## 📋 Apa yang Sudah Diperbaiki

### 1. ✅ Dockerfile - Sudah Benar
- **Status:** Menggunakan `requirements.txt` (format pip yang benar)
- **Lokasi:** Line 12: `COPY requirements.txt .`
- **Tidak ada lagi:** recruitment.docker.txt yang punya decoration header

### 2. ✅ requirements.txt - Kompatibel Cross-Platform
**Perubahan yang dibuat:**
```diff
- pywin32==311
+ pywin32==311; sys_platform == 'win32'
```

**Alasan:** 
- `pywin32==311` hanya bisa diinstall di Windows
- Dengan marker `sys_platform == 'win32'`, pip akan skip install di Linux container
- Tetap tersedia untuk Windows development local

### 3. ✅ .env - Siap untuk Docker Compose
**Perubahan yang dibuat:**
```diff
- POSTGRES_HOST=localhost
+ POSTGRES_HOST=db

- REDIS_URL=redis://127.0.0.1:6379/1
+ REDIS_URL=redis://redis:6379/1
```

**Alasan:**
- Docker Compose menggunakan service names untuk network communication
- Container tidak bisa akses `localhost` - harus gunakan service name
- `db` adalah nama service di docker-compose.yml untuk PostgreSQL
- `redis` adalah nama service di docker-compose.yml untuk Redis

---

## 🚀 Cara Menggunakan Sekarang

### Step 1: Pull dari GitHub (Di PC Baru)
```bash
git clone https://github.com/adithia00004/DJANGO-AHSP-PROJECT.git
cd DJANGO-AHSP-PROJECT
```

### Step 2: Verifikasi File-file Penting Ada
```bash
ls -la Dockerfile requirements.txt .env
```

**Harus output:**
```
-rw-r--r--  Dockerfile
-rw-r--r--  requirements.txt
-rw-r--r--  .env
```

### Step 3: Start Docker Desktop (Penting!)
- **Windows:** Klik "Docker Desktop" dari Start Menu atau taskbar
- Tunggu sampai status icon Docker berubah jadi "Docker is running"
- Test dengan: `docker --version`

### Step 4: Build Docker Image
```bash
cd d:\path\to\DJANGO-AHSP-PROJECT
docker-compose build --no-cache
```

**Expected Output (akhir):**
```
 => exporting to image                                             
 => => writing image sha256:abc123...
 => => naming to django-ahsp-project:latest
Successfully built
```

**Durasi:** ~5-10 menit (tergantung internet speed)

### Step 5: Start Services
```bash
docker-compose up -d
```

**Verifikasi dengan:**
```bash
docker-compose ps
```

**Expected Output:**
```
NAME                COMMAND                  SERVICE     STATUS      PORTS
django-ahsp-db     docker-entrypoint.sh…    db          Up 2s       5432/tcp
django-ahsp-redis  redis-server …           redis       Up 2s       6379/tcp
django-ahsp-web    gunicorn …               web         Up 1s       0.0.0.0:8000→8000/tcp
```

### Step 6: Run Migrations (First Time Only)
```bash
docker-compose exec web python manage.py migrate
```

### Step 7: Akses Aplikasi
- **URL:** http://localhost:8000
- Seharusnya bisa load tanpa error

---

## ✅ Checklist Verifikasi

**Sebelum build:**
- [ ] Git clone selesai
- [ ] File `.env` ada dan sudah ada `POSTGRES_HOST=db`
- [ ] File `requirements.txt` ada
- [ ] File `Dockerfile` ada
- [ ] Docker Desktop running

**Setelah build:**
- [ ] Build berhasil (exit code 0)
- [ ] Image terbuat: `docker images | grep django-ahsp`
- [ ] Docker-compose.yml valid: `docker-compose config` (tanpa error)

**Setelah docker-compose up:**
- [ ] Semua 3 services running: `docker-compose ps` (STATUS = "Up")
- [ ] Web service bisa akses: `curl http://localhost:8000`
- [ ] DB terhubung: `docker-compose exec web python manage.py dbshell`
- [ ] Redis terhubung: `docker-compose exec web python manage.py shell` → `from django.core.cache import cache` → `cache.set('test', 'works')`

**Database (opsional):**
- [ ] List databases: `docker-compose exec db psql -U postgres -l`
- [ ] Check tables: `docker-compose exec db psql -U postgres -d ahsp_sni_db -c "\dt"`

---

## 🔧 Troubleshooting

### ❌ Error: "pywin32 no matching distribution"
**Status:** ✅ **SUDAH DIPERBAIKI**
- Sebelumnya: pywin32==311 akan error di Linux Docker
- Sekarang: Marker `sys_platform == 'win32'` membuat pip skip di Linux
- **Action:** Tidak perlu, sudah fixed di requirements.txt

### ❌ Error: "Cannot connect to postgres/redis at localhost"
**Penyebab:** File `.env` masih punya `localhost` atau `127.0.0.1`

**Fix:**
```bash
# Check current values
grep POSTGRES_HOST .env
grep REDIS_URL .env

# Should show:
# POSTGRES_HOST=db
# REDIS_URL=redis://redis:6379/1
```

### ❌ Error: "docker-compose: command not found"
**Fix:** 
```bash
# Windows - gunakan docker desktop atau
docker compose build  # Newer syntax

# Not:
docker-compose build  # Old syntax (bisa di-alias)
```

### ❌ Error: "Docker is not running"
**Fix:**
- Klik Docker Desktop icon di taskbar
- Tunggu sampai icon berubah green
- Cek: `docker ps`

---

## 📦 Data Transfer Antar PC (Optional)

### Dari PC Lama ke PC Baru

**Step 1: Di PC Lama - Backup Database**
```bash
docker-compose exec -T db pg_dump -U postgres -d ahsp_sni_db > backup.sql
```

**Step 2: Transfer file backup.sql ke PC Baru**

**Step 3: Di PC Baru - Restore Database**
```bash
# Pastikan db service sudah running
docker-compose up -d db

# Restore
docker-compose exec -T db psql -U postgres -d ahsp_sni_db < backup.sql
```

---

## 📝 Files yang Dimodifikasi

| File | Change | Reason |
|------|--------|--------|
| `requirements.txt` | Add marker `; sys_platform == 'win32'` ke `pywin32==311` | Skip di Linux Docker |
| `.env` | Change `POSTGRES_HOST=localhost` → `POSTGRES_HOST=db` | Docker service name |
| `.env` | Change `REDIS_URL=redis://127.0.0.1:6379/1` → `redis://redis:6379/1` | Docker service name |

**Commit:** `0025afa0` - "fix: Make Docker build compatible - conditional pywin32 and Docker-ready .env"

---

## 🎯 Next Steps

1. ✅ Pull dari GitHub di PC target
2. ✅ Start Docker Desktop
3. ✅ Run `docker-compose build --no-cache`
4. ✅ Run `docker-compose up -d`
5. ✅ Akses http://localhost:8000

**Semua harus berjalan lancar tanpa modifikasi tambahan!**

---

## 📞 Questions?

Jika masih ada error:
1. Share output dari: `docker-compose build 2>&1 | head -100`
2. Atau: `docker-compose ps`
3. Atau: `cat .env | grep POSTGRES_HOST`

---

**Terakhir diupdate:** 13 Januari 2025  
**Status:** ✅ PRODUCTION READY
