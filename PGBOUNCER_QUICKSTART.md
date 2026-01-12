# 🚀 PgBouncer Quick Start Guide

**Goal**: Setup PgBouncer connection pooling to handle 100+ concurrent users

**Time Required**: 10-15 minutes

---

## 📋 STEP-BY-STEP INSTRUCTIONS

### Step 1: Update .env File

1. Open `.env` file in your project root (or create it from `.env.pgbouncer`)
2. Add/update these lines:

```bash
# Your PostgreSQL password
POSTGRES_PASSWORD=your_actual_password_here

# Enable PgBouncer (port 6432)
PGBOUNCER_PORT=6432
```

**Important**: Replace `your_actual_password_here` with your real PostgreSQL password!

---

### Step 2: Start PgBouncer Container

**On Windows (PowerShell/CMD):**
```bash
.\setup_pgbouncer.bat
```

**On Linux/WSL/Mac:**
```bash
chmod +x setup_pgbouncer.sh
./setup_pgbouncer.sh
```

**Or manually with Docker Compose:**
```bash
docker-compose -f docker-compose-pgbouncer.yml up -d
```

**Expected output:**
```
[1/5] Docker detected successfully
[2/5] Environment file (.env) found
[3/5] PostgreSQL password configured
[4/5] Stopping existing PgBouncer container (if any)...
[5/5] Starting PgBouncer container...
✅ PgBouncer Started Successfully!
```

---

### Step 3: Verify PgBouncer is Running

**Check Docker container:**
```bash
docker ps
```

Expected output:
```
CONTAINER ID   IMAGE                       STATUS    PORTS
abc123def456   pgbouncer/pgbouncer:latest  Up        0.0.0.0:6432->6432/tcp
```

**Check PgBouncer logs:**
```bash
docker logs ahsp_pgbouncer
```

Expected: No error messages, should show "listening on 0.0.0.0:6432"

---

### Step 4: Run Verification Script

```bash
python verify_pgbouncer.py
```

**Expected output:**
```
============================================================
  PgBouncer Verification Script
============================================================

1. Checking Environment Variables
----------------------------------
POSTGRES_HOST: localhost
POSTGRES_USER: postgres
POSTGRES_PASSWORD: ***
PGBOUNCER_PORT: 6432

✅ Environment variables configured correctly

2. Checking Django Database Settings
------------------------------------
Port: 6432
CONN_MAX_AGE: 0
DISABLE_SERVER_SIDE_CURSORS: True

✅ Django configured to use PgBouncer (port 6432)
✅ PgBouncer-specific settings correct

3. Testing Django Database Connection
--------------------------------------
PostgreSQL version: PostgreSQL 15.x ...
Connected to: localhost:6432

✅ Django can connect to database successfully

4. Testing PgBouncer Statistics
--------------------------------
PgBouncer Pool Status:
Database        User            Active     Idle
------------------------------------------------------------
postgres        postgres        1          24

✅ PgBouncer is running and accessible

5. Testing Django Migrations
-----------------------------
✅ Migrations are accessible

Verification Summary
--------------------
✅ PASS - Environment Variables
✅ PASS - Django Settings
✅ PASS - Django Connection
✅ PASS - PgBouncer Stats
✅ PASS - Django Migrations

🎉 All checks passed! PgBouncer is configured correctly.
```

---

### Step 5: Restart Django Server

**Stop Django if running** (Ctrl+C)

**Start Django:**
```bash
python manage.py runserver
```

Django should now connect via PgBouncer (port 6432) instead of directly to PostgreSQL (port 5432).

---

### Step 6: Test Basic Functionality

1. Open browser: http://localhost:8000
2. Login to dashboard
3. Navigate to a few pages
4. Check for any errors

**Everything should work exactly the same - but now with connection pooling!**

---

## ✅ VERIFICATION CHECKLIST

Before running load test, verify:

- [ ] `.env` file has `POSTGRES_PASSWORD` set (not default)
- [ ] `.env` file has `PGBOUNCER_PORT=6432`
- [ ] `docker ps` shows pgbouncer container running
- [ ] `python verify_pgbouncer.py` shows all checks passed
- [ ] Django server starts without errors
- [ ] Can login to Django admin
- [ ] Dashboard loads successfully

---

## 🧪 READY FOR LOAD TEST

Once all checks pass, you can run the load test:

**50-user baseline test:**
```bash
locust -f load_testing/locustfile.py \
    --headless \
    -u 50 \
    -r 2 \
    -t 300s \
    --host=http://localhost:8000 \
    --csv=hasil_test_v11_50u_pgbouncer \
    --html=hasil_test_v11_50u_pgbouncer.html
```

**Expected improvement:**
- Success rate: >99% (vs 98.58% without PgBouncer)
- No connection exhaustion errors
- Consistent performance

**100-user test (after 50u passes):**
```bash
locust -f load_testing/locustfile.py \
    --headless \
    -u 100 \
    -r 2 \
    -t 300s \
    --host=http://localhost:8000 \
    --csv=hasil_test_v11_100u_pgbouncer \
    --html=hasil_test_v11_100u_pgbouncer.html
```

**Expected improvement:**
- Success rate: >97% (vs 91.72% without PgBouncer)
- Connection errors eliminated
- Median response: <600ms (vs 1,200ms without PgBouncer)
- Auth failures still high (need Priority 2: Redis - next step)

---

## 🔧 TROUBLESHOOTING

### Issue: "Docker not found"

**Error:**
```
Docker is not installed or not in PATH
```

**Solution:**
1. Install Docker Desktop for Windows: https://www.docker.com/products/docker-desktop
2. Restart terminal after installation
3. Run `docker --version` to verify

---

### Issue: "Port 6432 already in use"

**Error:**
```
Error starting userland proxy: listen tcp4 0.0.0.0:6432: bind: address already in use
```

**Solution:**
```bash
# Find process using port 6432
netstat -ano | findstr :6432

# Kill the process
taskkill /PID <process_id> /F

# Or use different port in docker-compose-pgbouncer.yml:
ports:
  - "6433:6432"  # Map to 6433 instead

# Then update .env:
PGBOUNCER_PORT=6433
```

---

### Issue: "Authentication failed"

**Error:**
```
psycopg.OperationalError: connection failed: password authentication failed for user "postgres"
```

**Solution:**
1. Verify password in `.env` is correct
2. Test direct PostgreSQL connection:
   ```bash
   psql -h localhost -p 5432 -U postgres -d postgres
   # Enter password when prompted
   ```
3. If direct connection works, check PgBouncer container env vars:
   ```bash
   docker inspect ahsp_pgbouncer | grep -A 20 Env
   ```

---

### Issue: Django connects to 5432 instead of 6432

**Symptom:** `verify_pgbouncer.py` shows "not connected via PgBouncer"

**Solution:**
1. Check `.env` has `PGBOUNCER_PORT=6432`
2. Restart Django server (Ctrl+C, then `python manage.py runserver`)
3. Verify environment variable is loaded:
   ```bash
   python -c "import os; print(os.getenv('PGBOUNCER_PORT'))"
   ```

---

### Issue: "prepared statement already exists"

**Error:**
```
django.db.utils.ProgrammingError: prepared statement "S_1" already exists
```

**Solution:**
This should be fixed by `DISABLE_SERVER_SIDE_CURSORS = True` in Django settings.

If still occurs:
1. Check `config/settings/base.py` line 155 has `DISABLE_SERVER_SIDE_CURSORS`
2. Restart Django server
3. Clear any persistent connections:
   ```bash
   docker-compose -f docker-compose-pgbouncer.yml restart
   ```

---

## 📊 MONITORING PGBOUNCER

### View PgBouncer stats in real-time:

```bash
# Connect to PgBouncer admin console
docker exec -it ahsp_pgbouncer psql -h localhost -p 6432 -U postgres -d pgbouncer

# Inside psql, run:
SHOW POOLS;
SHOW STATS;
SHOW CLIENTS;
SHOW SERVERS;
```

### Useful commands:

```sql
-- Show connection pools
SHOW POOLS;

-- Show per-database statistics
SHOW STATS;

-- Show active client connections
SHOW CLIENTS;

-- Show server connections to PostgreSQL
SHOW SERVERS;

-- Show configuration
SHOW CONFIG;

-- Reload configuration (after editing pgbouncer.ini)
RELOAD;

-- Pause all database operations
PAUSE;

-- Resume operations
RESUME;
```

---

## 🛑 STOPPING PGBOUNCER

**To stop PgBouncer:**
```bash
docker-compose -f docker-compose-pgbouncer.yml down
```

**To stop and remove volumes:**
```bash
docker-compose -f docker-compose-pgbouncer.yml down -v
```

**To switch back to direct PostgreSQL:**

1. Remove or comment out `PGBOUNCER_PORT=6432` in `.env`
2. Restart Django server

Django will automatically fall back to direct PostgreSQL connection (port 5432).

---

## 📝 NEXT STEPS AFTER PGBOUNCER

Once PgBouncer is working and 100-user test passes:

1. **Priority 2: Redis Session Store** (fix 70% auth failures)
2. **Priority 3: Query Result Caching** (fix dashboard 6.9% failures)
3. **Priority 4: Database Indexes** (improve response times)
4. **Retest 100 users** with all improvements
5. **Stretch goal: 150-user test**

---

**Created**: 2026-01-10
**For**: Django AHSP Project - 100 User Scale Test
**Expected Impact**: Eliminate connection pool exhaustion, support 500+ concurrent users
