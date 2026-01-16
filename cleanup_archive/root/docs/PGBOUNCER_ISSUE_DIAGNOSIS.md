# PgBouncer 50-User Test - Issue Diagnosis & Fix

**Date**: 2026-01-10
**Test**: hasil_test_v11_50u_pgbouncer
**Status**: ❌ **FAILED** - Network configuration issue

---

## 📊 TEST RESULTS SUMMARY

| Metric | Result | Expected | Status |
|--------|--------|----------|--------|
| **Total Requests** | 158 | ~3,600 | ❌ 96% MISSING |
| **Success Rate** | **5.7%** (9/158) | >99% | ❌❌❌ CATASTROPHIC |
| **Failures** | **149/158** | <36 | ❌ 415% WORSE |
| **Response Time** | **122 seconds** | <5s | ❌ 24,400% SLOWER |
| **Auth Failures** | **50/50 (100%)** | <5 | ❌ COMPLETE FAILURE |

---

## 🔥 ROOT CAUSE IDENTIFIED

### Issue: **PostgreSQL pg_hba.conf Network Access Restriction**

PgBouncer container **CANNOT connect to PostgreSQL** because:

1. **PgBouncer runs inside Docker** with IP `192.168.1.87` (Windows host IP)
2. **PostgreSQL pg_hba.conf** only allows connections from `127.0.0.1` and `::1` (localhost)
3. **Network access from `192.168.1.87` is REJECTED**

**Evidence from logs:**
```
psql: error: no pg_hba.conf entry for host "192.168.1.87", user "postgres",
database "ahsp_sni_db", no encryption
```

### Timeline of Investigation:

1. ✅ **PgBouncer container started successfully**
2. ❌ **All queries timeout at 120 seconds** (`query_wait_timeout`)
3. ✅ **PgBouncer logs show**: Cannot connect to PostgreSQL backend
4. ✅ **PostgreSQL is running** on port 5432
5. ❌ **Connection refused**: `pg_hba.conf` blocks IP `192.168.1.87`

---

## 🛠️ SOLUTION - TWO OPTIONS

### **Option 1: RECOMMENDED - Update pg_hba.conf (Proper Solution)**

Update PostgreSQL configuration to allow network connections.

#### Step 1: Locate pg_hba.conf

**Windows PostgreSQL location:**
```
C:\Program Files\PostgreSQL\16\data\pg_hba.conf
```

Or find it:
```bash
psql -U postgres -c "SHOW hba_file;"
```

#### Step 2: Edit pg_hba.conf

Add this line **BEFORE** the `127.0.0.1/32` line:

```conf
# Allow connections from local network (for PgBouncer container)
host    all             all             192.168.1.0/24      md5
```

**Before**:
```conf
# IPv4 local connections:
host    all             all             127.0.0.1/32            scram-sha-256
```

**After**:
```conf
# Allow connections from local network (for PgBouncer container)
host    all             all             192.168.1.0/24      md5

# IPv4 local connections:
host    all             all             127.0.0.1/32            scram-sha-256
```

#### Step 3: Reload PostgreSQL

**Windows (PowerShell as Administrator):**
```powershell
Restart-Service postgresql-x64-16
```

Or using `pg_ctl`:
```bash
pg_ctl reload -D "C:\Program Files\PostgreSQL\16\data"
```

#### Step 4: Test Connection

```bash
# Test from command line
psql -h 192.168.1.87 -p 5432 -U postgres -d ahsp_sni_db

# Test via PgBouncer
psql -h localhost -p 6432 -U postgres -d ahsp_sni_db
```

#### Step 5: Re-run Load Test

```bash
locust -f load_testing/locustfile.py \
    --headless \
    -u 50 \
    -r 2 \
    -t 300s \
    --host=http://localhost:8000 \
    --csv=hasil_test_v12_50u_pgbouncer_fixed \
    --html=hasil_test_v12_50u_pgbouncer_fixed.html
```

---

### **Option 2: TEMPORARY - Disable PgBouncer, Test Direct Connection**

If you want to test WITHOUT PgBouncer first to ensure no other issues:

#### Step 1: Remove PGBOUNCER_PORT from .env

```bash
# Comment out or remove this line in .env:
# PGBOUNCER_PORT=6432
```

#### Step 2: Restart Django

Django will auto-detect and use direct PostgreSQL connection (port 5432).

#### Step 3: Run Baseline Test

```bash
locust -f load_testing/locustfile.py \
    --headless \
    -u 50 \
    -r 2 \
    -t 300s \
    --host=http://localhost:8000 \
    --csv=hasil_test_v12_50u_direct_postgres \
    --html=hasil_test_v12_50u_direct_postgres.html
```

**Expected**: Should match previous v10_scalling50_post_import_fix results (98.58% success).

#### Step 4: After Confirming Baseline, Implement Option 1

Then come back and fix pg_hba.conf for PgBouncer.

---

## 📋 DETAILED FIX GUIDE - pg_hba.conf

### Understanding pg_hba.conf Format

```conf
# TYPE  DATABASE        USER            ADDRESS                 METHOD
host    all             all             192.168.1.0/24          md5
```

- **TYPE**: `host` (TCP/IP connections)
- **DATABASE**: `all` (all databases) or specific database name
- **USER**: `all` (all users) or specific username
- **ADDRESS**: `192.168.1.0/24` (allow whole subnet) or specific IP
- **METHOD**: `md5` (password authentication) or `scram-sha-256`

### Security Consideration

**Option A - Allow whole subnet** (easier but less secure):
```conf
host    all             all             192.168.1.0/24          md5
```

**Option B - Allow only specific IP** (more secure):
```conf
host    all             all             192.168.1.87/32         md5
```

**Option C - Allow Docker bridge network** (most specific):
```conf
host    all             all             172.18.0.0/16           md5
```

**Recommendation**: Use Option A for local development, Option C for production.

---

## 🔍 VERIFICATION CHECKLIST

After implementing pg_hba.conf fix:

### 1. Test Direct PostgreSQL Connection from Host IP

```bash
psql -h 192.168.1.87 -p 5432 -U postgres -d ahsp_sni_db -c "SELECT 1;"
```

**Expected**: Connection successful, returns `1`.

### 2. Test PgBouncer Connection

```bash
psql -h localhost -p 6432 -U postgres -d ahsp_sni_db -c "SELECT 1;"
```

**Expected**: Connection successful via PgBouncer.

### 3. Check PgBouncer Logs

```bash
docker logs ahsp_pgbouncer --tail 20
```

**Expected**: NO `query_wait_timeout` errors, should see successful connections.

### 4. Run Verification Script

```bash
export PGBOUNCER_PORT=6432
python verify_pgbouncer.py
```

**Expected**: All 5 checks PASS.

### 5. Test Django Connection

```bash
python manage.py shell
```

```python
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT 1")
print(f"Connected via port: {connection.settings_dict['PORT']}")
```

**Expected**: Output shows `6432`.

### 6. Run Load Test

```bash
locust -f load_testing/locustfile.py --headless -u 50 -r 2 -t 300s \
    --host=http://localhost:8000 \
    --csv=hasil_test_v12_50u_pgbouncer_fixed \
    --html=hasil_test_v12_50u_pgbouncer_fixed.html
```

**Expected**:
- Total requests: ~3,600
- Success rate: >99%
- No 120-second timeouts
- Normal response times (<5s)

---

## 🚨 COMMON ERRORS & FIXES

### Error: "no pg_hba.conf entry for host"

**Cause**: PostgreSQL rejecting connection from IP address

**Fix**: Add IP/subnet to pg_hba.conf as shown in Solution Option 1

---

### Error: "Connection refused" on port 6432

**Cause**: PgBouncer container not running or not exposing port

**Fix**:
```bash
docker ps  # Check if ahsp_pgbouncer is running
docker-compose -f docker-compose-pgbouncer.yml up -d
```

---

### Error: "query_wait_timeout" in PgBouncer logs

**Cause**: PgBouncer cannot connect to PostgreSQL backend

**Fix**: Check pg_hba.conf and PostgreSQL logs

---

### Error: "password authentication failed"

**Cause**: Wrong password in .env or password method mismatch

**Fix**:
1. Check POSTGRES_PASSWORD in .env matches actual password
2. Ensure pg_hba.conf uses `md5` not `scram-sha-256` for network connections

---

## 📊 EXPECTED RESULTS AFTER FIX

### @ 50 Users (After pg_hba.conf Fix)

| Metric | Current (Broken) | Expected (Fixed) |
|--------|------------------|------------------|
| **Total Requests** | 158 | ~3,600 |
| **Success Rate** | 5.7% | >99% |
| **Failures** | 149 | <36 |
| **Response Time (Median)** | 122,000ms | ~180ms |
| **Auth Failures** | 50/50 | ~0-5 |
| **Throughput** | 0.5 req/s | ~12 req/s |

### Comparison to Baseline (v10_scalling50_post_import_fix)

Should match or slightly improve over:
- Success rate: 98.58%
- Total requests: 3,603
- Median response: 180ms
- Throughput: 12.03 req/s

---

## 🎯 NEXT STEPS

### Immediate (Required):

1. ✅ **Update pg_hba.conf** - Add `192.168.1.0/24` subnet
2. ✅ **Reload PostgreSQL** - Apply configuration
3. ✅ **Test connections** - Verify psql can connect
4. ✅ **Run verification** - `python verify_pgbouncer.py`
5. ✅ **Re-run 50-user test** - Verify baseline restored

### After 50-User Test Passes:

6. ✅ **Run 100-user test** - Test PgBouncer improvements
7. ✅ **Compare results** - vs v10_scalling100 (91.72% success)
8. ✅ **Proceed to Priority 2** - Redis Session Store (if 100-user passes)

---

## 📝 LESSONS LEARNED

### Docker Networking on Windows:

1. **`host.docker.internal` doesn't always work** on Windows Docker Desktop
2. **`network_mode: host` is not fully supported** on Windows
3. **Bridge network requires actual host IP** for container-to-host communication
4. **PostgreSQL pg_hba.conf must allow network connections** from Docker bridge IP

### Recommended Docker Setup for Windows:

```yaml
services:
  pgbouncer:
    environment:
      DATABASES_HOST: 192.168.1.87  # Actual Windows host IP
    ports:
      - "6432:6432"
    networks:
      - ahsp_network
```

And update pg_hba.conf:
```conf
host    all             all             192.168.1.0/24      md5
```

---

## 🔧 ALTERNATIVE: Run PgBouncer on Windows (Not Docker)

If Docker networking continues to be problematic, consider installing PgBouncer directly on Windows:

**Download**: https://www.pgbouncer.org/downloads.html

This would eliminate all networking issues since both PostgreSQL and PgBouncer would be on localhost.

However, **this is more complex** and Docker is still recommended once pg_hba.conf is properly configured.

---

**Created**: 2026-01-10 22:40 WIB
**Issue**: PostgreSQL pg_hba.conf network access restriction
**Solution**: Update pg_hba.conf to allow connections from `192.168.1.0/24`
**Next Test**: hasil_test_v12_50u_pgbouncer_fixed (after fix)
