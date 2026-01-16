# PostgreSQL Quick Fix Guide

**CRITICAL**: Fix database connection pool before 100-user test!

---

## Problem

**Auth Login Failures**: 20/50 requests failing (40% failure rate!)
**Root Cause**: PostgreSQL `max_connections` too low for 50+ concurrent users

---

## Step 1: Check Current Configuration

Run the diagnostic script:

```bash
python check_postgres_config.py
```

**Expected Output**:
```
[HIGH] max_connections = 100 is TOO LOW for 50+ users
```

The script will show:
- Current `max_connections` value
- Connection usage percentage
- **Location of postgresql.conf file**
- Exact changes needed

---

## Step 2: Fix PostgreSQL Configuration

### Option A: Automated (Recommended for Windows)

The script will show you the **exact file location**. Example:
```
C:\Program Files\PostgreSQL\15\data\postgresql.conf
```

### Edit postgresql.conf:

1. **Open file as Administrator** (Right-click Notepad → Run as Administrator)
2. **Find or add these lines**:

```ini
# Connection Settings
max_connections = 200                # Increased from 100

# Memory Settings (adjust based on available RAM)
shared_buffers = 256MB               # 25% of RAM
work_mem = 16MB                      # For complex queries
effective_cache_size = 1GB           # 50-75% of RAM
```

3. **Save the file**

---

## Step 3: Restart PostgreSQL

### Windows:

**Method 1**: PowerShell (as Administrator):
```powershell
net stop postgresql-x64-15
net start postgresql-x64-15
```

**Method 2**: Services GUI:
```
1. Press Win+R
2. Type: services.msc
3. Find: postgresql-x64-15
4. Right-click → Restart
```

### Linux/Mac:
```bash
sudo systemctl restart postgresql
# or
sudo service postgresql restart
```

---

## Step 4: Verify Changes

Run the check script again:

```bash
python check_postgres_config.py
```

**Expected Output**:
```
[OK] max_connections = 200 is sufficient
[OK] Connection usage at 5.0%
```

---

## Step 5: Re-Test

After PostgreSQL restart, re-run 50-user test:

```bash
run_test_scale_50u_final.bat
# or
locust -f load_testing/locustfile.py --headless -u 50 -r 2 -t 300s --host=http://localhost:8000 --csv=hasil_test_v10_scalling50_final --html=hasil_test_v10_scalling50_final.html
```

**Expected Improvements**:
- Auth login failures: 20 → 0-2
- Success rate: 98.25% → 99.5%+
- Total 500 errors: 59 → <10

---

## Common Issues

### Issue 1: "Permission Denied"
**Solution**: Run Notepad as Administrator before editing postgresql.conf

### Issue 2: "Service Not Found"
**Solution**: Check PostgreSQL version number in Services (might be postgresql-x64-14, etc.)

### Issue 3: "Cannot find postgresql.conf"
**Solution**: Use script's output or check common locations:
- Windows: `C:\Program Files\PostgreSQL\[version]\data\postgresql.conf`
- Linux: `/etc/postgresql/[version]/main/postgresql.conf`

### Issue 4: PostgreSQL Won't Start After Changes
**Solution**: Check for syntax errors in postgresql.conf
- Make sure `max_connections = 200` (no quotes!)
- Check logs at: `C:\Program Files\PostgreSQL\15\data\log\` (Windows)

---

## What These Settings Do

**max_connections = 200**
- Allows 200 simultaneous database connections
- Prevents "connection pool exhausted" errors
- Needed for 50+ concurrent users

**shared_buffers = 256MB**
- Database cache in RAM
- Faster query performance
- Recommended: 25% of total RAM

**work_mem = 16MB**
- Memory for sorting/joining operations
- Higher value = faster complex queries
- Adjust based on query complexity

**effective_cache_size = 1GB**
- Hint to query planner about available OS cache
- Does NOT allocate memory
- Recommended: 50-75% of total RAM

---

## Validation Checklist

After applying fixes:

- [ ] `check_postgres_config.py` shows no errors
- [ ] PostgreSQL service is running
- [ ] Django server can connect to database
- [ ] 50-user test shows <10 failures
- [ ] Success rate >99%
- [ ] Auth login success rate >90%

---

**Time Required**: 10-15 minutes
**Impact**: Auth failures 20 → 0, Success rate +1-2%
**Priority**: CRITICAL - Required before 100-user test

