# Monitoring & Observability

## Slow Request Logging

Slow requests are captured by `referensi.middleware.performance.PerformanceLoggingMiddleware`.  
Enable it automatically by running with `DJANGO_ENV=production` or add it manually to `MIDDLEWARE`.

Configure the threshold via the `DJANGO_PERF_THRESHOLD` environment variable (seconds, default `0.8`).

Example log entry (JSON formatted):

```json
{
  "timestamp": "2025-11-02T14:12:41",
  "level": "WARNING",
  "logger": "performance",
  "message": "slow_request",
  "path": "/referensi/admin/database/",
  "method": "GET",
  "status_code": 200,
  "duration": 1.24
}
```

## Structured Logging

Production logging outputs JSON to stdout. Forward logs to your provider (e.g., CloudWatch, ELK, Grafana Loki).

Set `DJANGO_LOG_LEVEL` (default `INFO`) to control verbosity.

## Key Dashboards

| Metric | Source | Notes |
|--------|--------|-------|
| Slow requests (> threshold) | Performance logs | Monitor volume spikes |
| Django errors | `django.request` logger | Configure alerting via Sentry or logging provider |
| Cache hit rate | Database cache table metrics | Schedule `django-admin inspectdb` or SQL checks |
| Celery/async tasks (if enabled later) | Task queue metrics | To be added in future phase |

## Manual Health Checks

1. `python manage.py check --deploy`
2. `python manage.py showmigrations --plan`
3. `python manage.py dbshell -c "SELECT count(*) FROM referensi_ahspreferensi;"` (sanity check)

Document any additional monitoring integrations here as they are adopted.
