# PgBouncer Setup Guide for Windows

**Date**: 2026-01-10
**Purpose**: Setup connection pooling to handle 100+ concurrent users

---

## 📋 OVERVIEW

**Problem**: PostgreSQL max_connections=200 exhausted at 100 users
**Solution**: PgBouncer pools 1000 client connections → 25 PostgreSQL connections
**Expected Impact**: Eliminate connection exhaustion, support 500+ concurrent users

---

## 🔧 INSTALLATION STEPS FOR WINDOWS

### Option 1: Using Pre-built Windows Binary (RECOMMENDED)

1. **Download PgBouncer for Windows**
   ```
   Visit: https://www.pgbouncer.org/downloads.html
   Or: https://github.com/pgbouncer/pgbouncer/releases
   ```

2. **Extract to Program Files**
   ```
   Extract to: C:\Program Files\PgBouncer\
   ```

### Option 2: Using WSL (Windows Subsystem for Linux)

If you have WSL installed:

```bash
# In WSL terminal
sudo apt-get update
sudo apt-get install pgbouncer -y
```

### Option 3: Using Docker (EASIEST for Windows)

```bash
# Pull PgBouncer Docker image
docker pull pgbouncer/pgbouncer

# We'll configure this below
```

---

## 📝 CONFIGURATION FILES

### 1. pgbouncer.ini

Create this file at `C:\Program Files\PgBouncer\pgbouncer.ini` (or `/etc/pgbouncer/pgbouncer.ini` in WSL):

```ini
[databases]
; Database connection string
; Format: dbname = host=... port=... dbname=... user=...
ahsp_db = host=127.0.0.1 port=5432 dbname=postgres user=postgres

[pgbouncer]
; Connection pooling mode
; - session: one server connection per client connection (default)
; - transaction: server connection returned after each transaction (RECOMMENDED)
; - statement: server connection returned after each statement (least safe)
pool_mode = transaction

; Listen on localhost only (change to 0.0.0.0 for external access)
listen_addr = 127.0.0.1
listen_port = 6432

; Authentication
auth_type = md5
auth_file = C:\Program Files\PgBouncer\userlist.txt

; Connection limits
max_client_conn = 1000          ; Max client connections PgBouncer accepts
default_pool_size = 25          ; Max server connections per database
reserve_pool_size = 5           ; Emergency reserve connections
reserve_pool_timeout = 5        ; Seconds to wait for reserve pool

; Connection timeouts (in seconds)
server_connect_timeout = 15     ; Max time to connect to PostgreSQL
server_idle_timeout = 600       ; Close idle server connections after 10 min
server_lifetime = 3600          ; Close server connection after 1 hour (prevents memory leaks)

; Client timeouts
client_idle_timeout = 600       ; Disconnect idle clients after 10 min

; Logging
logfile = C:\Program Files\PgBouncer\pgbouncer.log
pidfile = C:\Program Files\PgBouncer\pgbouncer.pid

; Log level: DEBUG, INFO, WARNING, ERROR
log_connections = 1
log_disconnections = 1
log_pooler_errors = 1

; Performance
max_prepared_statements = 100
```

**For WSL/Linux**, use these paths instead:
```ini
auth_file = /etc/pgbouncer/userlist.txt
logfile = /var/log/pgbouncer/pgbouncer.log
pidfile = /var/run/pgbouncer/pgbouncer.pid
```

### 2. userlist.txt

Create this file at `C:\Program Files\PgBouncer\userlist.txt`:

```txt
"postgres" "md5<your_postgres_password_hash>"
```

**How to get the password hash**:

Run this in PostgreSQL (psql):
```sql
SELECT rolname, rolpassword FROM pg_authid WHERE rolname = 'postgres';
```

Or use plain password (less secure but easier for local dev):
```txt
"postgres" "your_plain_password"
```

Then update `pgbouncer.ini`:
```ini
auth_type = plain
```

---

## 🐳 DOCKER SETUP (EASIEST FOR WINDOWS)

### docker-compose.yml

Create this file in your project root:

```yaml
version: '3.8'

services:
  pgbouncer:
    image: pgbouncer/pgbouncer
    container_name: ahsp_pgbouncer
    environment:
      # Database connection
      DATABASES_HOST: host.docker.internal  # Windows Docker special hostname
      DATABASES_PORT: 5432
      DATABASES_USER: postgres
      DATABASES_PASSWORD: your_postgres_password
      DATABASES_DBNAME: postgres

      # PgBouncer settings
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 1000
      DEFAULT_POOL_SIZE: 25
      RESERVE_POOL_SIZE: 5
      SERVER_IDLE_TIMEOUT: 600

      # Auth
      AUTH_TYPE: md5

    ports:
      - "6432:6432"
    restart: unless-stopped
    networks:
      - ahsp_network

networks:
  ahsp_network:
    driver: bridge
```

**Start PgBouncer**:
```bash
docker-compose up -d pgbouncer
```

**Check logs**:
```bash
docker logs ahsp_pgbouncer
```

---

## 🔧 DJANGO CONFIGURATION

Update your Django settings to use PgBouncer:

### config/settings/base.py

**BEFORE** (Direct PostgreSQL):
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'postgres'),
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
        # ...
    }
}
```

**AFTER** (Via PgBouncer):
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'postgres'),
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': os.getenv('PGBOUNCER_PORT', '6432'),  # Changed from 5432 to 6432!
        'CONN_MAX_AGE': 0,  # IMPORTANT: Set to 0 for transaction pooling
        'CONN_HEALTH_CHECKS': False,  # IMPORTANT: Disable for PgBouncer
        'OPTIONS': {
            'connect_timeout': int(os.getenv("POSTGRES_CONNECT_TIMEOUT", "10")),
            'options': '-c statement_timeout=60000 -c idle_in_transaction_session_timeout=120000',
        },
        'DISABLE_SERVER_SIDE_CURSORS': True,  # IMPORTANT for transaction pooling
    }
}
```

**Key Changes**:
1. ✅ `PORT`: 5432 → 6432 (PgBouncer port)
2. ✅ `CONN_MAX_AGE`: 0 (don't hold connections, let PgBouncer pool)
3. ✅ `CONN_HEALTH_CHECKS`: False (PgBouncer handles this)
4. ✅ `DISABLE_SERVER_SIDE_CURSORS`: True (required for transaction pooling)

---

## 🧪 VERIFICATION STEPS

### 1. Test PgBouncer Connection

**Using psql**:
```bash
# Connect via PgBouncer (port 6432)
psql -h localhost -p 6432 -U postgres -d postgres

# Inside psql, run:
SHOW pool_mode;
SHOW max_client_conn;
```

Expected output:
```
 pool_mode
-----------
 transaction

 max_client_conn
-----------------
 1000
```

### 2. Test Django Connection

**Using Django shell**:
```bash
python manage.py shell
```

```python
from django.db import connection

# Test connection
cursor = connection.cursor()
cursor.execute("SELECT version();")
print(cursor.fetchone())

# Check connection settings
print(f"Host: {connection.settings_dict['HOST']}")
print(f"Port: {connection.settings_dict['PORT']}")
```

Expected: Port should be 6432

### 3. Monitor PgBouncer Stats

**Connect to PgBouncer admin console**:
```bash
psql -h localhost -p 6432 -U postgres -d pgbouncer
```

**Show pool statistics**:
```sql
SHOW POOLS;
SHOW STATS;
SHOW SERVERS;
SHOW CLIENTS;
```

**SHOW POOLS** output example:
```
 database  | user     | cl_active | cl_waiting | sv_active | sv_idle | sv_used | maxwait
-----------+----------+-----------+------------+-----------+---------+---------+---------
 ahsp_db   | postgres |        15 |          0 |         5 |      20 |       0 |       0
```

- `cl_active`: Active client connections
- `sv_active`: Active server connections to PostgreSQL
- `sv_idle`: Idle server connections (ready to use)

---

## 📊 EXPECTED IMPROVEMENTS

### Before PgBouncer (Direct PostgreSQL @ 100 users):

| Metric | Value |
|--------|-------|
| Max Connections Used | ~200 (EXHAUSTED) |
| Connection Errors | High (373 failures) |
| Success Rate | 91.72% |
| Median Response | 1,200ms |

### After PgBouncer (@ 100 users):

| Metric | Target |
|--------|--------|
| Max Client Connections | 1000 (ample headroom) |
| Server Connections Used | ~25-30 (pooled efficiently) |
| Connection Errors | ~0 |
| Success Rate | >97% |
| Median Response | <400ms |

---

## 🚨 TROUBLESHOOTING

### Issue 1: PgBouncer won't start

**Error**: `cannot bind to 127.0.0.1:6432`

**Solution**: Port already in use
```bash
# Windows
netstat -ano | findstr :6432

# Kill process using port
taskkill /PID <process_id> /F
```

### Issue 2: Auth failed

**Error**: `authentication failed for user "postgres"`

**Solution**: Check userlist.txt password hash or use `auth_type = plain` for testing

### Issue 3: Django can't connect

**Error**: `could not connect to server: Connection refused`

**Solution**:
1. Check PgBouncer is running: `docker ps` or check service
2. Verify port 6432 is correct in Django settings
3. Test connection manually with psql

### Issue 4: "prepared statement already exists"

**Error**: `prepared statement "S_1" already exists`

**Solution**: This is why we set `DISABLE_SERVER_SIDE_CURSORS = True` in Django settings

### Issue 5: Connection pool exhausted

**Error**: `sorry, too many clients already`

**Solution**: Increase `max_client_conn` or `default_pool_size` in pgbouncer.ini

---

## 🎯 VALIDATION CHECKLIST

Before running load test, verify:

- [ ] PgBouncer service is running
- [ ] Can connect via psql on port 6432
- [ ] Django connects via port 6432 (not 5432)
- [ ] `CONN_MAX_AGE = 0` in Django settings
- [ ] `DISABLE_SERVER_SIDE_CURSORS = True` in Django settings
- [ ] `SHOW POOLS` shows active connections
- [ ] Django migrations work via PgBouncer
- [ ] Django admin loads successfully

---

## 📋 NEXT STEPS AFTER PGBOUNCER SETUP

1. ✅ Run 50-user baseline test to verify no regression
2. ✅ Run 100-user test to validate improvements
3. ✅ Monitor `SHOW POOLS` during test
4. ✅ Verify success rate >97%
5. ✅ Move to Priority 2: Redis Session Store

---

**Created**: 2026-01-10
**Purpose**: Eliminate PostgreSQL connection pool exhaustion
**Expected Success Rate**: 91.72% → >97%
