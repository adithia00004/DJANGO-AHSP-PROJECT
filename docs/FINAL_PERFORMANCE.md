# Final Performance Plan

## Test Matrix

| Scenario | Target | Tooling | Status |
|----------|--------|---------|--------|
| Import 10k AHSP | ≤ 12 minutes | `python manage.py import_ahsp` with staging dataset | Pending |
| Concurrent users (50) | p95 < 800ms | k6 / Locust script | Pending |
| Search flood | 200 requests/min | `pytest -k perf` or k6 scenario | Pending |

## Commands

Current status:
- `DJANGO_ENV=production pytest --no-cov` ❌ (multiple redirects/host failures under production settings)
- `DJANGO_ENV=production python manage.py collectstatic --noinput` ☐

```bash
# Production-mode test run
DJANGO_ENV=production pytest --no-cov

# Collectstatic dry-run
DJANGO_ENV=production python manage.py collectstatic --noinput
```

## Metrics Baseline (to fill post-run)

| Metric | Value | Notes |
|--------|-------|-------|
| Import 10k AHSP | _TBD_ | Pending load test |
| Search p95 | _TBD_ | Pending load test |
| Slow requests (>0.8s) | _TBD_ | Awaiting production logs |

Document results here after executing the benchmarks.
