# Login Failure Diagnosis (Evidence-Based)

Date: 2026-01-11
Scope: Investigate primary cause of login failures under load.

## Evidence Sources
- `logs/runserver_8000.err.log`
- `logs/django_errors.log`
- `logs/auth_debug.log`
- `docker-compose-pgbouncer.yml`
- `config/settings/base.py`
- `load_testing/locustfile.py`

## Confirmed Findings (Strong Evidence)

### 1) Primary Failure Mode: Database connection wait timeout via PgBouncer
Evidence:
- Login failures (HTTP 500) recorded at 12:59:17:
  - `logs/runserver_8000.err.log:3532`
  - `logs/runserver_8000.err.log:3534`
  - `logs/django_errors.log:27`
- Immediately after the login 500s, the server logs show `query_wait_timeout` during DB connection setup:
  - `logs/runserver_8000.err.log:3540`
  - `logs/runserver_8000.err.log:3559`
  - `logs/runserver_8000.err.log:3564`

Interpretation:
- `query_wait_timeout` is raised while trying to establish a DB connection, which indicates PgBouncer queue wait timeout (pool is exhausted or backend slots unavailable).
- The error occurs at the same timestamp as `/accounts/login/` 500s, so login failures are caused by DB connection wait timeout under load.

### 2) Pool sizing likely insufficient for 100-user concurrency
Evidence:
- PgBouncer pool config uses env defaults:
  - `docker-compose-pgbouncer.yml:17`
  - `docker-compose-pgbouncer.yml:18`
  - `docker-compose-pgbouncer.yml:19`
  - `docker-compose-pgbouncer.yml:20`
- `.env` currently sets:
  - `PGBOUNCER_DEFAULT_POOL_SIZE=50`
  - `PGBOUNCER_RESERVE_POOL_SIZE=10`

Interpretation:
- Effective pool is ~60 server connections (default + reserve).
- Auth probes at 50 concurrent users already trigger `query_wait_timeout` (PgBouncer logs), so pool pressure is still a bottleneck.

### 3) Connection churn with PgBouncer transaction pooling
Evidence:
- PgBouncer active, `CONN_MAX_AGE` forced to 0:
  - `config/settings/base.py:129`
  - `config/settings/base.py:152`
  - `config/settings/base.py:154`

Interpretation:
- Each request uses a short-lived connection (expected for transaction pooling).
- Under high concurrency, this increases connection churn and makes pool pressure more visible.

## Measurement Gaps / Under-Reporting

### Locust login failure detection was undercounting (fixed)
Evidence:
- Login flow now marks failures when login page is returned:
  - `load_testing/locustfile.py:170`
  - `load_testing/locustfile.py:198`
  - `load_testing/locustfile.py:215`

Interpretation:
- CSV failure counts now include "login page returned" cases.
- New tests after this change show accurate failure rates.

## What Is Not Confirmed (No direct evidence yet)
- Password hashing CPU bottleneck: no CPU or profiler evidence in logs.
- CSRF failure: would return 403, but observed failures are 500 with DB wait timeout.
- Application-level auth logic bug: no stack trace pointing to auth code; failures occur before a usable DB connection is established.

## Conclusion (Most Likely Root Cause)
Primary cause of login failures under load is PgBouncer connection queue wait timeout (`query_wait_timeout`) leading to failed DB connections, which manifests as HTTP 500 on `/accounts/login/`.

Supporting evidence:
- Correlation between `/accounts/login/` 500 and `query_wait_timeout` stack traces.
- Pool size (25 + 5 reserve) is much smaller than concurrency (50-100 users).

## Recommended Next Steps (Diagnostics)
1) Adjust PgBouncer pool size to match expected concurrent load, then rerun auth probe.
2) Update Locust login flow to mark failures when login page is returned (HTTP 200) so metrics are accurate.
3) Capture DB-side metrics (PgBouncer logs / Postgres connection stats) during load to confirm queue wait reduction.


## Update: Auth Rate Limiting Confirmed (2026-01-11)

Auth-only A/B tests show login failures caused by Allauth rate limits:
- Single-user auth-only: 39/39 login failures, error "Terlalu banyak percobaan masuk yang gagal. Coba lagi nanti."
- Multi-user auth-only (10 accounts): 32/32 login failures, same error text
- `ACCOUNT_RATE_LIMITS` (Allauth defaults):
  - `login`: `30/m/ip`
  - `login_failed`: `10/m/ip,5/300s/key`

Implication:
- Failures are IP rate-limit related, not caused by reusing a single username.

## Update: PgBouncer Logs Confirm query_wait_timeout (2026-01-11)

Evidence:
- `docker logs ahsp_pgbouncer --tail 200` shows multiple:
  - `pooler error: query_wait_timeout`
  - `closing because: query_wait_timeout (age=120s)`

Interpretation:
- PgBouncer is actively timing out client queries under concurrency.
- This aligns with Django stack traces showing `psycopg.errors.ProtocolViolation: query_wait_timeout` during `/accounts/login/`.

## Update: Rate Limit Disabled Auth-Only Tests (2026-01-11)

Environment:
- `ACCOUNT_RATE_LIMITS_DISABLED=true` (dev override)
- `LOCUST_AUTH_ONLY=true`

Results:
- Single-user auth-only:
  - CSV: `hasil_test_auth_only_50u_single_nolimit_stats.csv`
  - Aggregated: 66 requests, 0 failures
  - Login POST: 16 requests, 0 failures, avg ~11.5s, max ~13s
- Multi-user auth-only:
  - CSV: `hasil_test_auth_only_50u_multi_nolimit_stats.csv`
  - Aggregated: 50 requests, 0 failures
  - Only GET `/accounts/login/` recorded; no POST rows logged

Interpretation:
- Rate limiting is removed: login failures disappear in single-user auth-only.
- Multi-user auth-only run did not record POST attempts; this is a tracking anomaly that needs follow-up.

## Update: Auth-Only Multi-User v2 + v19 No Limit (2026-01-11)

Evidence:
- `hasil_test_auth_only_50u_multi_nolimit_v2_stats.csv`
  - Aggregated: 100 requests, 20 failures
  - Login POST: 50 requests, 20 failures (HTTP 500)
  - Avg login: ~50.6s, P95 ~121s, max ~120.6s
- `hasil_test_v19_100u_nolimit_stats.csv`
  - Aggregated: 200 requests, 80 failures
  - Login POST: 100 requests, 80 failures (HTTP 500)
  - Avg login: ~93s, P95 ~128s, max ~128.8s
- `logs/runserver_8000.err.log` continues to show `query_wait_timeout`

Interpretation:
- After rate limits are disabled, login failures are still severe under concurrency.
- Root cause shifts to PgBouncer queue timeouts (DB pool saturation).

## Update: Pool 100/20 Retest (2026-01-11)

Evidence:
- `hasil_test_auth_only_50u_multi_nolimit_v3_pool100_stats.csv`
  - Aggregated: 100 requests, 0 failures
  - Login POST: 50 requests, 0 failures (avg ~795ms, P95 ~1.1s)
- `hasil_test_v19_100u_nolimit_pool100_stats.csv`
  - Aggregated: 3,838 requests, 221 failures (~5.76%)
  - Login POST: 100 requests, 64 failures (HTTP 500), avg ~64.9s, P95 ~120s
- `logs/runserver_8000.err.log` still shows `query_wait_timeout`

Interpretation:
- PgBouncer pool increase resolves auth-only login failures.
- Under full mixed load, connection timeouts remain; pool saturation still limits throughput.

## Update: Pool 140/20 Retest (2026-01-11)

Evidence:
- `hasil_test_v19_100u_nolimit_pool140_stats.csv`
  - Aggregated: 4,252 requests, 126 failures (~2.96%)
  - Login POST: 100 requests, 72 failures (HTTP 500), avg ~72.0s, P95 ~120s
- `logs/runserver_8000.err.log` still shows `query_wait_timeout`

Interpretation:
- Increasing pool reduces overall failure rate but does not eliminate login 500s.
- DB connection timeouts persist under mixed workload.

## Update: Pool 140/20 No-Export Retest (2026-01-11)

Evidence:
- `hasil_test_v19_100u_nolimit_pool140_no_export_stats.csv`
  - Aggregated: 3,385 requests, 429 failures (~12.64%)
  - Login POST: 100 requests, 53 failures (HTTP 500), avg ~85.7s, P95 ~122s
- Failures are concentrated on core pages/APIs (dashboard, list-pekerjaan, jadwal-pekerjaan, rincian-ahsp, rekap-rab)
- `logs/runserver_8000.err.log` still shows `query_wait_timeout`

Interpretation:
- Export traffic is not the primary cause of failures.
- Core pages/APIs are holding DB connections too long, leading to queue timeouts.
