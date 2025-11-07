# ⚡ Cache Quick Start Guide

**TL;DR:** Aplikasi sudah siap development **TANPA Redis/Garnet**. Nanti saat hosting, tinggal set 2 environment variables! 🚀

---

## 🎯 Status Saat Ini

```
✅ Konfigurasi Django: PRODUCTION-READY
✅ Fallback mechanism: ACTIVE (locmem cache)
✅ Rate limiting: WORKING (uses locmem)
✅ Session management: WORKING (cached_db + locmem)
✅ Dependencies: COMPLETE (django-redis ready di requirements.txt)
```

**Anda bisa langsung develop sekarang!**

---

## 🏃 Development (Sekarang)

### 1. Setup Project

```bash
# Clone & setup
git clone https://github.com/adithia00004/DJANGO-AHSP-PROJECT.git
cd DJANGO-AHSP-PROJECT

# Create virtual environment
python -m venv env
source env/bin/activate  # Linux/Mac
# atau
.\env\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Setup database
python manage.py migrate

# Run development server
python manage.py runserver
```

**✅ DONE! No Redis needed for development!**

### 2. Verify Cache Working

```bash
python manage.py shell

>>> from django.core.cache import cache
>>> cache.set('test_key', 'Hello World!', 300)
>>> print(cache.get('test_key'))
'Hello World!'
```

**Expected output:** Cache working dengan locmem backend ✅

---

## 🚀 Production (Nanti Saat Hosting)

### Step 1: Setup Redis/Garnet Server

**Option A: Docker (Tercepat)**
```bash
# Garnet (Microsoft - 100% Redis compatible)
docker run -d -p 6379:6379 --name garnet ghcr.io/microsoft/garnet

# Atau Redis
docker run -d -p 6379:6379 --name redis redis:latest

# Atau Valkey (Redis fork)
docker run -d -p 6379:6379 --name valkey valkey/valkey:latest
```

**Option B: Cloud FREE Tier**
- Oracle Cloud Always Free: 1GB RAM Redis
- Upstash Redis: 10,000 commands/day
- Redis Cloud: 30MB free
- Railway: 500 hours/month

### Step 2: Update Environment Variables

**File: `.env` (production server)**

```bash
# Enable Redis cache
CACHE_BACKEND=redis
REDIS_URL=redis://your-redis-host:6379/1

# Optional: If using Celery
CELERY_BROKER_URL=redis://your-redis-host:6379/0
CELERY_RESULT_BACKEND=redis://your-redis-host:6379/0
```

### Step 3: Restart Application

```bash
# Restart Django application
systemctl restart django-app  # atau sesuai setup Anda

# Verify Redis connection
python manage.py shell
>>> from django.core.cache import cache
>>> cache.set('production_test', 'Redis working!', 60)
>>> print(cache.get('production_test'))
'Redis working!'
```

**✅ DONE! Zero code changes needed!**

---

## 🔍 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'django_redis'"

**Solusi:**
```bash
pip install django-redis==5.4.0
```

**Atau:**
Aplikasi akan otomatis fallback ke locmem cache (development mode)

### Issue: "ConnectionRefusedError: [Errno 111] Connection refused"

**Penyebab:** Redis server tidak running atau salah host/port

**Solusi:**
```bash
# Cek Redis running
docker ps | grep redis  # Jika pakai Docker
redis-cli ping  # Should return "PONG"

# Atau fallback ke database cache
CACHE_BACKEND=db python manage.py runserver
```

### Issue: Rate limiting tidak bekerja

**Penyebab:** Cache tidak accessible

**Solusi:**
```bash
# Test cache
python manage.py shell
>>> from django.core.cache import cache
>>> cache.set('test', 'value')
>>> print(cache.get('test'))

# Jika None, cek CACHE_BACKEND di settings
```

---

## 📊 Cache Backends Comparison

| Backend | Development | Production | Persistence | Multi-Server |
|---------|-------------|------------|-------------|--------------|
| **locmem** | ✅ Perfect | ❌ No | ❌ No | ❌ No |
| **db** | ⚠️ Slow | ⚠️ OK | ✅ Yes | ✅ Yes |
| **Redis/Garnet** | ⚠️ Setup required | ✅ Perfect | ⚠️ Optional | ✅ Yes |

**Recommendation:**
- **Development:** locmem (default, no setup)
- **Production:** Redis/Garnet (best performance)
- **Fallback:** db cache (if Redis unavailable)

---

## 📚 Documentation

- **Full Roadmap:** [CACHE_STRATEGY_PRODUCTION_ROADMAP.md](./CACHE_STRATEGY_PRODUCTION_ROADMAP.md)
- **Redis Alternatives:** [VALKEY_GARNET_ALTERNATIVES.md](./VALKEY_GARNET_ALTERNATIVES.md)
- **Windows Setup:** [REDIS_WINDOWS_SETUP.md](./REDIS_WINDOWS_SETUP.md)
- **Free Options:** [REDIS_FREE_PRODUCTION_SOLUTION.md](./REDIS_FREE_PRODUCTION_SOLUTION.md)

---

## ❓ FAQ

**Q: Apakah wajib install Redis untuk development?**
A: **TIDAK.** Aplikasi otomatis fallback ke locmem cache yang cukup untuk development.

**Q: Apakah code perlu diubah saat pakai Redis production?**
A: **TIDAK.** Tinggal set `CACHE_BACKEND=redis` dan `REDIS_URL` di environment variables.

**Q: Garnet vs Redis, mana yang lebih baik?**
A: **Garnet** = FREE forever, open source Microsoft, compatible 100% dengan Redis. **Redis** = More mature, larger ecosystem. Keduanya bagus untuk production.

**Q: Bagaimana cara test dengan Redis sebelum production?**
A: Jalankan `docker run -d -p 6379:6379 redis:latest` dan set `CACHE_BACKEND=redis` di `.env` development.

**Q: Session hilang saat restart development server?**
A: Normal untuk locmem cache (in-memory). Di production dengan Redis atau `cached_db`, session persistent.

---

**✨ Bottom Line:** Develop sekarang dengan locmem, deploy production dengan Redis/Garnet nanti. Zero stress! 🎉
