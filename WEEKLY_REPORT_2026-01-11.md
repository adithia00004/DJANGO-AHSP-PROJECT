# Weekly Report 2026-01-11
Week: W-1

Ringkasan Minggu Ini:
- Completed: Task 1.1 database indexes applied (migration 0032), Task 1.2 dashboard pagination, Task 1.3 client metrics fix, Task 1.4 auth debug logging enabled
- In Progress: Auth failure root cause (HTTP 500 during login)
- Blocked: None

Perubahan Utama:
- Added login failure instrumentation (writes `logs/locust_login_failures.log`) and TEST_USER_POOL support for multi-user auth tests
- Files: `detail_project/views_monitoring.py`, `config/middleware/auth_debug.py`, `config/settings/development.py`, `dashboard/tests/test_views.py`, `load_testing/locustfile.py`
- Docs: `GETTING_STARTED_NOW.md`, `MASTER_EXECUTION_TRACKER.md`
- Multi-user auth-only missing POST root cause identified: TEST_USER_POOL format mismatch; validation logging added (see `MULTIUSER_TEST_DIAGNOSIS_2026-01-11.md`)

Tes dan Validasi:
- Load test v18 (100 users, 300s)
  - Command: `locust -f load_testing/locustfile.py --headless -u 100 -r 4 -t 300s --host=http://localhost:8000 --csv=hasil_test_v18_100u_pgbouncer_redis_20260111_114225 --html=hasil_test_v18_100u_pgbouncer_redis_20260111_114225.html`
  - Result (Aggregated): 7,064 requests, 45 failures (0.64%), median 25ms, p95 2.1s, p99 19s, RPS 23.6
  - Auth failures: `[AUTH] Login POST` 45/100 failures (HTTP 500)
  - Client metrics: `/api/monitoring/report-client-metric/` 0 failures
- Auth probe test (20 users, 60s, exclude export)
  - Command: `locust -f load_testing/locustfile.py --headless -u 20 -r 2 -t 60s --host=http://localhost:8000 --exclude-tags export --csv=hasil_test_auth_probe`
  - Result: 117 requests, 0 failures; auth login 20/20 success; P95 2.9s
- Auth probe test (50 users, 120s, exclude export)
  - Command: `locust -f load_testing/locustfile.py --headless -u 50 -r 4 -t 120s --host=http://localhost:8000 --exclude-tags export --csv=hasil_test_auth_probe_50u`
  - Result: 825 requests, 0 failures in CSV; auth login avg ~13.3s, max ~59s
  - Note: locust console shows repeated login failures with status 200 (not counted as failures)

- Auth probe test (50 users, 120s, after PgBouncer tuning)
  - Command: `locust -f load_testing/locustfile.py --headless -u 50 -r 4 -t 120s --host=http://localhost:8000 --exclude-tags export --csv=hasil_test_auth_probe_50u_after_pgbouncer`
  - Result: 1,100 requests, 28 failures (~2.55%); login 28/50 failures (56%)
  - Failure breakdown: 26 `login page returned`, 2 `login server error: 500`

- Auth-only A/B test (single vs multi user)
  - Single: `hasil_test_auth_only_50u_single_stats.csv` ? login 39/39 failures (100%)
  - Multi (10 users): `hasil_test_auth_only_50u_multi_stats.csv` ? login 32/32 failures (100%)
  - Error message: "Terlalu banyak percobaan masuk yang gagal. Coba lagi nanti."
  - Allauth rate limits: login `30/m/ip`, login_failed `10/m/ip`

- Auth-only tests (rate limits disabled)
  - Single: `hasil_test_auth_only_50u_single_nolimit_stats.csv` ? login 16/16 success (0 failures), avg ~11.5s
  - Multi: `hasil_test_auth_only_50u_multi_nolimit_stats.csv` ? only GET login page recorded (no POST rows)
  - Note: multi-user nolimit run shows missing POST metrics (needs follow-up)

- Auth-only multi-user retest (rate limits disabled, corrected pool format)
  - Command: `locust -f load_testing/locustfile.py --headless -u 50 -r 4 -t 180s --host=http://localhost:8000 --csv=hasil_test_auth_only_50u_multi_nolimit_v2 --loglevel DEBUG`
  - Result: 100 requests, 20 failures
  - Auth login: 50 requests, 20 failures (HTTP 500), avg ~50.6s, P95 ~121s

- Auth-only multi-user retest (pool 100/20)
  - Command: `locust -f load_testing/locustfile.py --headless -u 50 -r 4 -t 180s --host=http://localhost:8000 --csv=hasil_test_auth_only_50u_multi_nolimit_v3_pool100 --loglevel DEBUG`
  - Result: 100 requests, 0 failures
  - Auth login: 50 requests, 0 failures, avg ~795ms, P95 ~1.1s

- Full load test v19 (100 users, rate limits disabled)
  - Command: `locust -f load_testing/locustfile.py --headless -u 100 -r 4 -t 300s --host=http://localhost:8000 --csv=hasil_test_v19_100u_nolimit --html=hasil_test_v19_100u_nolimit.html`
  - Result: 200 requests, 80 failures
  - Auth login: 100 requests, 80 failures (HTTP 500), avg ~93s, P95 ~128s

- Full load test v19 (pool 100/20)
  - Command: `locust -f load_testing/locustfile.py --headless -u 100 -r 4 -t 300s --host=http://localhost:8000 --csv=hasil_test_v19_100u_nolimit_pool100 --html=hasil_test_v19_100u_nolimit_pool100.html`
  - Result: 3,838 requests, 221 failures (~5.76%)
  - Auth login: 100 requests, 64 failures (HTTP 500), avg ~64.9s, P95 ~120s

- Full load test v19 (pool 140/20)
  - Command: `locust -f load_testing/locustfile.py --headless -u 100 -r 4 -t 300s --host=http://localhost:8000 --csv=hasil_test_v19_100u_nolimit_pool140 --html=hasil_test_v19_100u_nolimit_pool140.html`
  - Result: 4,252 requests, 126 failures (~2.96%)
  - Auth login: 100 requests, 72 failures (HTTP 500), avg ~72.0s, P95 ~120s

- Full load test v19 (pool 140/20, exclude export)
  - Command: `locust -f load_testing/locustfile.py --headless -u 100 -r 4 -t 300s --host=http://localhost:8000 --exclude-tags export --csv=hasil_test_v19_100u_nolimit_pool140_no_export --html=hasil_test_v19_100u_nolimit_pool140_no_export.html`
  - Result: 3,385 requests, 429 failures (~12.64%)
  - Auth login: 100 requests, 53 failures (HTTP 500), avg ~85.7s, P95 ~122s
  - Failures dominated by dashboard + core pages/APIs (non-export)

- Full load test v20 (pool 140/20, exclude export)
  - Command: `locust -f load_testing/locustfile.py --headless -u 100 -r 4 -t 300s --host=http://localhost:8000 --exclude-tags export --csv=hasil_test_v20_100u_pool140_no_export`
  - Result: 3,919 requests, 102 failures (~2.60%)
  - Auth login: 100 requests, 67 failures (HTTP 500), avg ~63.9s, P95 ~121s
  - P95 hotspots: `/api/project/[id]/rekap-kebutuhan/validate/` (120s), `/api/project/[id]/rekap-kebutuhan/` (58s)
  - Failures remain on dashboard, list-pekerjaan tree, rincian-ahsp, audit-trail, rekap-rab

- Full load test v21 (pool 140/20, exclude export)
  - Command: `locust -f load_testing/locustfile.py --headless -u 100 -r 4 -t 300s --host=http://localhost:8000 --exclude-tags export --csv=hasil_test_v21_100u_pool140_no_export`
  - Result: 4,182 requests, 98 failures (~2.34%)
  - Auth login: 100 requests, 71 failures (HTTP 500), avg ~68.9s, P95 ~120s
  - Rekap kebutuhan validate P95 now 180ms (bottleneck resolved)
  - New P95 hotspots: `/api/project/[id]/tahapan/unassigned/` (~68s), `/api/project/[id]/pricing/` (~66s)

- Full load test v23 (pool 140/20, exclude export+admin)
  - Command: `locust -f load_testing/locustfile.py --headless -u 100 -r 4 -t 300s --host=http://localhost:8000 --exclude-tags export,admin --csv=hasil_test_v23_100u_pool140_no_export_no_admin`
  - Result: 4,305 requests, 216 failures (~5.02%)
  - Auth login: 100 requests, 73 failures (HTTP 500), avg ~76.9s, P95 ~121s
  - Export endpoints still appear in stats (rekap-kebutuhan pdf/xlsx) despite exclude-tags
  - Recommended rerun with `--tags api,page,phase1,phase2` to fully omit export tasks

- Full load test v24 (pool 140/20, tags api,page,phase1,phase2)
  - Command: `locust -f load_testing/locustfile.py --headless -u 100 -r 4 -t 300s --host=http://localhost:8000 --tags api,page,phase1,phase2 --csv=hasil_test_v24_100u_pool140_no_export_no_admin`
  - Result: 200 requests, 82 failures (41%)
  - Only auth endpoints executed (login GET/POST)
  - Root cause: Locust expects tags as space-separated args; comma-separated treated as one tag
  - Action: rerun with `--tags api page phase1 phase2`


Log Capture:
- `logs/django_errors.log` size 5,548 bytes; contains Internal Server Error lines including `/accounts/login/` at 12:59:17
- No stack trace lines present in `logs/django_errors.log` yet
- `logs/auth_debug.log` records login responses status 500 at 12:59:17
- `logs/runserver_8000.err.log` shows `psycopg.errors.ProtocolViolation: query_wait_timeout`
- `docker logs ahsp_pgbouncer` shows repeated `pooler error: query_wait_timeout`
- `logs/runserver_8000.err.log` still shows `query_wait_timeout` after pool 100/20 (v19 pool100)
- `logs/runserver_8000.err.log` still shows `query_wait_timeout` after pool 140/20 (v19 pool140)
- `logs/runserver_8000.err.log` continues showing `query_wait_timeout` during no-export run

Metrik:
- Auth Success: 55% (target >99%)
- P95: 2.1s (target <2s)
- P99: 19s (target <2s)

Risiko/Issue:
- PgBouncer pool tuning prepared in `docker-compose-pgbouncer.yml` with env defaults in `.env` (restart required)
- Root cause confirmed: PgBouncer `query_wait_timeout` during `/accounts/login/` under load (see `LOGIN_FAILURE_DIAGNOSIS_2026-01-11.md`)
- Login failures now dominated by Allauth rate limiting (per-IP) during auth-only tests
- Export endpoints masih lambat (p95 17-60s)
- Login failure detection fixed in locustfile; failures persist (login page returned, 500)

Rencana Minggu Depan:
- Tangkap exception detail login via `logs/django_errors.log` dan `logs/auth_debug.log`
- Jalankan test kecil (20 users) untuk fokus auth
- Perbaiki flow auth berdasarkan root cause (CSRF/session/DB contention)

Crosscheck (Claude):
- Verifikasi status task di `MASTER_EXECUTION_TRACKER.md`
- Cocokkan hasil v18 dengan CSV `hasil_test_v18_100u_pgbouncer_redis_20260111_114225_stats.csv`

Update - Core Endpoint Optimization (Day 2 focus):
- List Pekerjaan tree cached with signature + values() payload
- Audit Trail list uses include_diff=0, detail fetched by entry_id
- Rincian AHSP bundle totals aggregated in DB (Sum on expanded rows)
- Rekap RAB skips override query when markup_eff already present
- Rekap Kebutuhan cache signature computed only when cache entry exists
- Rekap Kebutuhan timeline cached + validation count loop optimized
- Tahapan unassigned cached + values() payload (reduces N+1)
- Pricing GET avoids get_or_create; POST wrapped in atomic only
- Tahapan summary aggregated + cached (reduces N+1 on /api/project/[id]/tahapan/)
- Load test tags: audit-trail + orphaned-items flagged as `admin` for exclusion
- V2 assignments list cached + values() payload (reduces load on /api/v2/project/[id]/assignments/)
- Files touched: `detail_project/views_api.py`, `detail_project/views_api_tahapan_v2.py`, `detail_project/services.py`, `detail_project/static/detail_project/js/audit_trail.js`, `load_testing/locustfile.py`
