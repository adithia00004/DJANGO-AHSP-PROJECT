# Redis Setup for Windows

## 🪟 Redis di Windows - 3 Opsi

### **Option 1: Memurai (RECOMMENDED untuk Windows)** ✅

Memurai adalah Redis-compatible server untuk Windows.

**Download & Install:**
```bash
# Download dari: https://www.memurai.com/get-memurai
# Atau gunakan chocolatey:
choco install memurai-developer

# Start Memurai
net start memurai

# Test connection
redis-cli ping  # Should return: PONG
```

**Pro:**
- ✅ Native Windows support
- ✅ Compatible dengan Django cache
- ✅ Easy installation
- ✅ Free developer edition

---

### **Option 2: WSL2 + Redis (Best for Development)** ✅

Gunakan Windows Subsystem for Linux.

**Install WSL2:**
```powershell
# Run in PowerShell as Administrator
wsl --install

# Restart computer
```

**Install Redis in WSL2:**
```bash
# Open WSL terminal
wsl

# Install Redis
sudo apt update
sudo apt install redis-server

# Start Redis
sudo service redis-server start

# Test connection
redis-cli ping  # Should return: PONG
```

**Configure Django to use WSL2 Redis:**
```python
# config/settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',  # Will work from Windows
    }
}
```

**Pro:**
- ✅ True Linux environment
- ✅ Best for development
- ✅ No compatibility issues

---

### **Option 3: Redis for Windows (Unofficial Port)** ⚠️

Microsoft's unofficial port (archived, not maintained).

**Download & Install:**
```bash
# Download from GitHub releases:
# https://github.com/microsoftarchive/redis/releases

# Download: Redis-x64-3.0.504.msi
# Install with installer

# Start Redis
redis-server

# Test connection
redis-cli ping  # Should return: PONG
```

**Pro:**
- ✅ Simple installation
- ✅ Works for development

**Con:**
- ⚠️ Outdated version (3.0.504)
- ⚠️ Not maintained
- ⚠️ Missing newer features

---

## 🎯 **QUICK RECOMMENDATION FOR YOU:**

**For immediate testing:** Use **Memurai Developer Edition**

```bash
# 1. Download Memurai Developer from:
#    https://www.memurai.com/get-memurai

# 2. Install (double-click installer)

# 3. Start Memurai service
net start memurai

# 4. Verify connection
redis-cli ping
```

Then update your `.env` file:
```bash
# Cache configuration
CACHE_BACKEND=django_redis.cache.RedisCache
CACHE_LOCATION=redis://127.0.0.1:6379/1
CACHE_TIMEOUT=300
```

---

## 🧪 After Redis is Running:

```bash
# Test Redis connection in Python
python manage.py shell
```

```python
from django.core.cache import cache

# Test cache
cache.set('test_key', 'test_value', 60)
result = cache.get('test_key')
print(f"Cache test: {result}")  # Should print: test_value

# Clear cache
cache.clear()
```

---

## 🔧 Alternative: Use Django's LocMemCache (TEMPORARY ONLY!)

If you can't install Redis right now, you can temporarily use Django's local memory cache for testing:

```python
# config/settings.py - TEMPORARY ONLY!
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}
```

**⚠️ WARNING:** This only works with single process!
- ❌ Won't work with multiple Gunicorn workers
- ❌ Rate limiting won't work properly in production
- ✅ OK for development/testing only

---

## 📝 Summary

| Option | Ease | Production Ready | Recommended |
|--------|------|-----------------|-------------|
| Memurai | ⭐⭐⭐⭐⭐ | ✅ Yes | ✅ **Best for Windows** |
| WSL2 + Redis | ⭐⭐⭐⭐ | ✅ Yes | ✅ Best for dev |
| Redis Windows Port | ⭐⭐⭐⭐ | ⚠️ Outdated | ⚠️ OK for testing |
| LocMemCache | ⭐⭐⭐⭐⭐ | ❌ No | ❌ Temporary only |

**My Recommendation:** Install **Memurai** or **WSL2 + Redis** for proper testing.
