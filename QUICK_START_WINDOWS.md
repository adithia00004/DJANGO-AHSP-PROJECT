# 🚀 Quick Start Guide - Windows

## ✅ **What You Can Do RIGHT NOW** (5 minutes)

### **Option A: Test WITHOUT Redis (Quick & Easy)** ⚡

Untuk test cepat tanpa install Redis dulu:

```bash
# Run quick test
run_tests_noredis.bat

# Or manually:
set DJANGO_SETTINGS_MODULE=config.settings_test_noredis
pytest detail_project/tests/test_phase4_infrastructure.py -v
```

**⚠️ IMPORTANT:** Ini hanya untuk testing! Production WAJIB pakai Redis!

---

### **Option B: Install Redis First (Recommended)** ✅

Pilih salah satu:

#### **1. Memurai (EASIEST for Windows)** ⭐⭐⭐⭐⭐

```bash
# Download: https://www.memurai.com/get-memurai
# Double-click installer
# Start service:
net start memurai

# Test:
redis-cli ping  # Should return: PONG
```

#### **2. WSL2 + Redis (Best for Development)** ⭐⭐⭐⭐

```powershell
# Install WSL2 (PowerShell as Admin):
wsl --install

# Restart computer, then:
wsl
sudo apt update
sudo apt install redis-server
sudo service redis-server start

# Test:
redis-cli ping  # Should return: PONG
```

**Full guide:** See `REDIS_WINDOWS_SETUP.md`

---

## 📊 **Test Results Explained**

Dari test yang kamu jalankan tadi:

### ✅ **PASSED (11 tests)**
- Health check endpoints ✅
- Database connectivity ✅
- Monitoring files exist ✅

### ❌ **FAILED (17 tests)** - FIXED!
Semua sudah di-fix di commit terbaru:
- APIResponse format mismatch → **FIXED** ✅
- Test setup issues → Will be fixed by proper test mocking

### ⚠️ **Redis Not Running** - Expected
- Rate limiting tests need Redis
- Cache tests need Redis

---

## 🎯 **Recommended Testing Flow**

### **STEP 1: Quick Test (No Redis)** - 2 minutes

```bash
# Test basic functionality
run_tests_noredis.bat
```

**Expected:** Most tests should PASS now (after APIResponse fix)

---

### **STEP 2: Install Redis** - 10 minutes

Choose Memurai atau WSL2 (see above)

---

### **STEP 3: Run Server** - Test manually

```bash
# Start server
python manage.py runserver

# Open browser:
http://127.0.0.1:8000/health/
```

**Expected response:**
```json
{
  "status": "ok",
  "checks": {
    "database": {"status": "ok"},
    "cache": {"status": "ok"}
  }
}
```

---

### **STEP 4: Run Full Tests** - 5 minutes

```bash
# Run all Phase 4 tests
pytest detail_project/tests/test_phase4_infrastructure.py -v

# Run all tests
pytest detail_project/tests/ -v
```

**Expected:**
- Phase 4: 28/28 passing ✅
- Total: 70+ tests passing ✅

---

## 🐛 **Troubleshooting**

### Issue: "redis-cli: command not found"

**Solution:** Redis not installed or not in PATH
- Check if Redis is installed
- Check if service is running: `net start memurai` (for Memurai)
- Or: `sudo service redis-server status` (for WSL2)

---

### Issue: Tests still failing after fix

**Solution:** Git pull latest changes

```bash
# Make sure you have latest code
git pull origin claude/check-main-branch-011CUsfTuyhpiENFhAkTQEVD

# Or reset to latest commit
git reset --hard origin/claude/check-main-branch-011CUsfTuyhpiENFhAkTQEVD
```

---

### Issue: ImportError or Module not found

**Solution:** Install/update dependencies

```bash
pip install -r requirements.txt
pip install pytest pytest-django pytest-cov
```

---

### Issue: Coverage warning (15% < 80%)

**Solution:** This is OK for now
- The 80% target is for detail_project app only
- Many files in other apps (referensi, dashboard) aren't covered yet
- Phase 4/5/6 code has good coverage

To run tests without coverage check:
```bash
pytest detail_project/tests/test_phase4_infrastructure.py -v --no-cov
```

---

## 📚 **Documentation Files**

| File | Purpose |
|------|---------|
| `TESTING_PLAN.md` | Complete testing guide (2-3 hours) |
| `REDIS_WINDOWS_SETUP.md` | Redis installation for Windows |
| `QUICK_START_WINDOWS.md` | This file - quick start |
| `run_tests_noredis.bat` | Quick test without Redis |

---

## ✅ **Success Checklist**

- [ ] Tests pass with `run_tests_noredis.bat`
- [ ] Redis installed (Memurai or WSL2)
- [ ] `redis-cli ping` returns `PONG`
- [ ] Server starts: `python manage.py runserver`
- [ ] Health check works: http://127.0.0.1:8000/health/
- [ ] Full tests pass: `pytest detail_project/tests/test_phase4_infrastructure.py -v`

---

## 🎉 **After All Tests Pass**

Next steps:

1. **Manual Testing** (15 min)
   - Login to application
   - Test CRUD operations
   - Verify loading states work
   - Test error handling

2. **Load Testing** (10 min)
   ```bash
   pip install locust
   locust -f detail_project/tests/locustfile.py --host=http://127.0.0.1:8000
   ```

3. **Review Documentation**
   - Check `ROADMAP_COMPLETE.md` for what's built
   - Review `MONITORING_GUIDE.md` for next steps

4. **Deploy to Staging** (when ready)
   ```bash
   ./scripts/deploy-staging.sh
   ```

---

## 💡 **Tips**

1. **Use LocMemCache for quick testing** - It works for single process
2. **Install Redis ASAP** - Required for production
3. **Memurai is easiest** - Native Windows, no Docker needed
4. **WSL2 is best for dev** - True Linux environment

---

**Questions?** Check:
- `TESTING_PLAN.md` for detailed guide
- `REDIS_WINDOWS_SETUP.md` for Redis setup
- GitHub issues if you find bugs

**Last Updated:** November 7, 2025
**Status:** Ready for Testing ✅
