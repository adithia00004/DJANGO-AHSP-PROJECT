# Redis Setup for Windows

## 🪟 Redis di Windows - 3 Opsi

### **Option 1: Memurai (RECOMMENDED untuk Windows)** ✅

Memurai adalah Redis-compatible server untuk Windows.

**💰 COST:**
- **Developer Edition:** ✅ **FREE** (for development)
- **Production on Windows Server:** Commercial license required (paid)
- **RECOMMENDED for Production:** Use Linux server with Redis (100% FREE)

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
- ✅ FREE for development

**Con:**
- ⚠️ Production on Windows Server may require paid license
- ⚠️ Check license terms for commercial use

---

### **Option 2: WSL2 + Redis (Best for Development)** ✅

Gunakan Windows Subsystem for Linux.

**💰 COST:** ✅ **100% FREE** (development & testing)

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

---

## 🚀 **PRODUCTION DEPLOYMENT (100% FREE)** ✅

### **For Production Server - Use Linux!**

**💰 COST:** ✅ **100% FREE forever**

All production deployments should use Linux server with Redis (no licensing issues).

### **Ubuntu/Debian Server Setup:**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Redis (100% FREE)
sudo apt install -y redis-server

# Configure Redis
sudo nano /etc/redis/redis.conf

# Key settings to check:
# bind 127.0.0.1  # Only allow local connections (secure)
# maxmemory 256mb  # Set memory limit
# maxmemory-policy allkeys-lru  # Eviction policy

# Start Redis
sudo systemctl start redis-server

# Enable Redis on boot
sudo systemctl enable redis-server

# Check status
sudo systemctl status redis-server

# Test connection
redis-cli ping  # Should return: PONG
```

### **CentOS/RHEL Server Setup:**

```bash
# Install EPEL repository
sudo yum install -y epel-release

# Install Redis (100% FREE)
sudo yum install -y redis

# Start Redis
sudo systemctl start redis

# Enable on boot
sudo systemctl enable redis

# Test connection
redis-cli ping
```

### **Docker Setup (100% FREE on Linux):**

```bash
# Install Docker (FREE on Linux)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Run Redis container (100% FREE)
docker run -d \
  --name redis-ahsp \
  --restart unless-stopped \
  -p 6379:6379 \
  -v redis-data:/data \
  redis:7-alpine redis-server --appendonly yes

# Test connection
docker exec -it redis-ahsp redis-cli ping
```

### **Security Configuration:**

```bash
# Set Redis password
sudo nano /etc/redis/redis.conf

# Add/uncomment:
requirepass your_strong_password_here

# Restart Redis
sudo systemctl restart redis-server

# Update Django settings.py:
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://:your_strong_password_here@127.0.0.1:6379/1',
    }
}
```

---

## 📝 Summary

| Option | Ease | Production Ready | Cost | Recommended |
|--------|------|-----------------|------|-------------|
| **Linux Server + Redis** | ⭐⭐⭐⭐⭐ | ✅ Yes | ✅ **FREE** | ✅ **BEST for Production** |
| WSL2 + Redis | ⭐⭐⭐⭐ | ✅ Dev/Test | ✅ FREE | ✅ Best for development |
| Memurai Developer | ⭐⭐⭐⭐⭐ | ⚠️ Dev only | ✅ FREE (dev) | ✅ Windows development |
| Redis Windows Port | ⭐⭐⭐⭐ | ⚠️ Outdated | ✅ FREE | ⚠️ OK for testing |
| LocMemCache | ⭐⭐⭐⭐⭐ | ❌ No | ✅ FREE | ❌ Temporary only |

---

## 🎯 **FINAL RECOMMENDATIONS:**

### **For Development (Windows):**
- Use **Memurai Developer** (FREE) or **WSL2 + Redis** (FREE)
- Both 100% FREE for development ✅

### **For Production Server:**
- Use **Linux server with Redis** (100% FREE) ✅
- Ubuntu/Debian recommended
- No licensing issues
- No costs
- Battle-tested

### **Cost Breakdown:**
- **Development:** $0 (use Memurai or WSL2)
- **Production:** $0 (use Linux + Redis)
- **Server Hosting:** $5-10/month (VPS only cost)

**Total Software Cost:** ✅ **$0/month**
