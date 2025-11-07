# Phase 6: Monitoring & Observability Guide

Complete guide for setting up monitoring, error tracking, and observability for the AHSP application.

---

## Overview

**Goal:** Comprehensive production monitoring and observability

**Components:**
1. Application Metrics (Prometheus/Grafana)
2. Error Tracking (Sentry)
3. Structured Logging (JSON logs)
4. Dashboards & Alerts
5. Performance Monitoring

---

## 1. Application Metrics

### 1.1 Monitoring Middleware

**File:** `detail_project/monitoring_middleware.py`

**Metrics Collected:**
- Request count per endpoint
- Response times (with percentiles)
- Error rates (4xx, 5xx)
- Rate limit hits
- Exceptions

**Setup:**

```python
# settings.py
MIDDLEWARE = [
    # ... other middleware
    'detail_project.monitoring_middleware.MonitoringMiddleware',
    'detail_project.monitoring_middleware.PerformanceMonitoringMiddleware',
    # ... other middleware
]
```

**Usage:**

```python
# Get metrics summary
from detail_project.monitoring_middleware import get_metrics_summary, get_endpoint_metrics

# Global metrics
metrics = get_metrics_summary()
# Returns: {
#     'requests_total': 1000,
#     'errors_4xx': 10,
#     'errors_5xx': 2,
#     'rate_limit_hits': 5,
#     'error_rate': 1.2
# }

# Endpoint-specific metrics
endpoint_metrics = get_endpoint_metrics('api_save_list_pekerjaan')
# Returns: {
#     'requests_GET': 100,
#     'requests_POST': 50,
#     'errors_4xx': 5,
#     'errors_5xx': 1,
#     'rate_limit_hits': 2,
#     'response_time_avg': 0.25,
#     'response_time_p95': 0.5,
#     'response_time_p99': 1.0
# }
```

### 1.2 Metrics Endpoint

Create endpoint to expose metrics:

```python
# detail_project/views_metrics.py
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from .monitoring_middleware import get_metrics_summary

@csrf_exempt
@require_GET
def metrics_endpoint(request):
    """
    Expose metrics for Prometheus/monitoring systems.
    """
    metrics = get_metrics_summary()
    return JsonResponse(metrics)
```

```python
# urls.py
path('metrics/', metrics_endpoint, name='metrics'),
```

### 1.3 Prometheus Integration (Optional)

If using Prometheus:

```bash
# Install django-prometheus
pip install django-prometheus
```

```python
# settings.py
INSTALLED_APPS = [
    'django_prometheus',
    # ... other apps
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    # ... other middleware
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]
```

```python
# urls.py
path('', include('django_prometheus.urls')),
```

---

## 2. Error Tracking with Sentry

### 2.1 Sentry Setup

**File:** `config/sentry_config.py`

**Installation:**

```bash
pip install sentry-sdk
```

**Configuration:**

```bash
# .env.production
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
APP_VERSION=1.0.0
```

```python
# settings.py
from config.sentry_config import init_sentry

# Initialize Sentry (only in production/staging)
if not DEBUG:
    init_sentry()

# Add middleware for context
MIDDLEWARE = [
    # ... other middleware
    'config.sentry_config.SentryContextMiddleware',
    # ... other middleware
]
```

### 2.2 Using Sentry in Code

**Automatic Error Capture:**
```python
# Sentry automatically captures unhandled exceptions
def my_view(request):
    result = 1 / 0  # Automatically captured by Sentry
```

**Manual Error Capture with Context:**
```python
from config.sentry_config import capture_exception_with_context, add_breadcrumb

def my_view(request):
    add_breadcrumb('User started deep copy', category='user_action')

    try:
        deep_copy_project(project_id)
    except Exception as e:
        capture_exception_with_context(
            e,
            user_id=request.user.id,
            project_id=project_id,
            operation='deep_copy'
        )
        raise
```

**Capture Messages:**
```python
from config.sentry_config import capture_message_with_level

capture_message_with_level(
    'User performed bulk operation',
    level='info',
    user_id=user.id,
    operation_count=50
)
```

### 2.3 Sentry Features

**Performance Monitoring:**
- Automatic transaction tracking
- Slow query detection
- API endpoint performance

**Release Tracking:**
- Track which version caused errors
- Deploy notifications
- Release health

**User Context:**
- See which users are affected
- User feedback collection
- Impact analysis

**Alerts:**
- Email/Slack notifications
- Custom alert rules
- Issue assignment

---

## 3. Structured Logging

### 3.1 Logging Configuration

**File:** `config/logging_config.py`

**Setup:**

```python
# settings.py
from config.logging_config import get_logging_config
import os

ENVIRONMENT = os.environ.get('DJANGO_ENV', 'development')

# Logging configuration
LOGGING = get_logging_config(ENVIRONMENT)

# Add request ID middleware
MIDDLEWARE = [
    # ... other middleware
    'config.logging_config.RequestIDMiddleware',
    # ... other middleware
]

# Create logs directory
os.makedirs('logs', exist_ok=True)
```

### 3.2 Log Files Created

| File | Purpose | Rotation |
|------|---------|----------|
| `logs/application.log` | All application logs | 10MB, 5 backups |
| `logs/errors.log` | Errors only | 10MB, 10 backups |
| `logs/performance.log` | Performance metrics | 10MB, 5 backups |
| `logs/security.log` | Security events | 10MB, 10 backups |

### 3.3 Using Structured Logging

**Standard Logging:**
```python
import logging

logger = logging.getLogger(__name__)

# Different log levels
logger.debug('Debug information')
logger.info('Informational message')
logger.warning('Warning message')
logger.error('Error occurred', exc_info=True)
logger.critical('Critical system failure')
```

**Logging with Extra Context:**
```python
logger.info('User performed action', extra={
    'user_id': user.id,
    'username': user.username,
    'action': 'deep_copy',
    'project_id': project.id
})

# In JSON logs, this becomes:
# {
#   "timestamp": "2025-11-07T12:00:00Z",
#   "level": "INFO",
#   "message": "User performed action",
#   "user_id": 123,
#   "username": "john",
#   "action": "deep_copy",
#   "project_id": 456
# }
```

**Performance Logging:**
```python
from config.logging_config import log_performance
import time

start = time.time()
result = expensive_operation()
duration = time.time() - start

log_performance('expensive_operation', duration, user_id=user.id)
```

**Security Logging:**
```python
from config.logging_config import log_security_event

# Failed login
log_security_event(
    'failed_login_attempt',
    severity='WARNING',
    username=username,
    ip_address=get_client_ip(request)
)

# Rate limit exceeded
log_security_event(
    'rate_limit_exceeded',
    severity='WARNING',
    user_id=user.id,
    endpoint=endpoint
)

# Suspicious activity
log_security_event(
    'suspicious_activity',
    severity='ERROR',
    user_id=user.id,
    details='Multiple failed attempts'
)
```

### 3.4 Log Aggregation

**ELK Stack (Elasticsearch, Logstash, Kibana):**

```yaml
# docker-compose.yml
services:
  elasticsearch:
    image: elasticsearch:8.5.0
    environment:
      - discovery.type=single-node

  logstash:
    image: logstash:8.5.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
      - ./logs:/logs

  kibana:
    image: kibana:8.5.0
    ports:
      - "5601:5601"
```

**CloudWatch (AWS):**
```bash
# Install CloudWatch agent
pip install boto3 watchtower

# settings.py
import watchtower

LOGGING['handlers']['cloudwatch'] = {
    'level': 'INFO',
    'class': 'watchtower.CloudWatchLogHandler',
    'log_group': 'ahsp-production',
    'stream_name': 'django-app',
}
```

---

## 4. Dashboards & Visualizations

### 4.1 Grafana Dashboard

**Install Grafana:**
```bash
# Docker
docker run -d -p 3000:3000 grafana/grafana

# Or use cloud: https://grafana.com
```

**Dashboard Components:**

**1. Request Rate Panel:**
```json
{
  "title": "Requests per Minute",
  "targets": [{
    "expr": "rate(http_requests_total[5m])"
  }]
}
```

**2. Response Time Panel:**
```json
{
  "title": "Response Times (p95)",
  "targets": [{
    "expr": "histogram_quantile(0.95, http_request_duration_seconds)"
  }]
}
```

**3. Error Rate Panel:**
```json
{
  "title": "Error Rate %",
  "targets": [{
    "expr": "(rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m])) * 100"
  }]
}
```

### 4.2 Dashboard Sections

**Operations Dashboard:**
- System health status
- Request rate (req/s)
- Response times (p50, p95, p99)
- Error rates (4xx, 5xx)
- Rate limit hits
- Cache hit/miss ratio
- Database connections

**Business Metrics Dashboard:**
- Active users
- Projects created
- API usage by endpoint
- Export operations
- Deep copy operations

**Error Dashboard:**
- Recent errors (from Sentry)
- Error frequency by type
- Affected users
- Error trends

### 4.3 Example Dashboard JSON

See file: `monitoring/grafana-dashboard.json` (created below)

---

## 5. Alerts & Notifications

### 5.1 Alert Rules

**Critical Alerts (PagerDuty/Phone):**
- Error rate > 5%
- Health check fails
- Database connection lost
- Redis connection lost
- API down

**Warning Alerts (Slack/Email):**
- Error rate > 1%
- Response time p95 > 2s
- Rate limit hits > 100/min
- Cache miss rate > 50%
- Disk space < 20%

**Info Alerts (Email):**
- Deployment completed
- Daily summary report
- Weekly metrics report

### 5.2 Sentry Alerts

**Setup:**
1. Go to Sentry project settings
2. Navigate to Alerts
3. Create alert rule

**Example Rules:**
```yaml
# High error rate
Condition: Event count > 10 in 1 minute
Action: Send to Slack #alerts

# New error type
Condition: First seen event
Action: Send email to team

# Regression
Condition: Event reappears after being resolved
Action: Create PagerDuty incident
```

### 5.3 Grafana Alerts

**Setup:**
```yaml
# Alerting rules
alerts:
  - name: high_error_rate
    condition: avg(error_rate) > 5
    for: 5m
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }}%"
```

### 5.4 Slack Integration

**Webhook Setup:**
```python
# settings.py
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

# In code
import requests

def send_slack_alert(message, severity='warning'):
    if not SLACK_WEBHOOK_URL:
        return

    color = {
        'info': '#36a64f',
        'warning': '#ff9800',
        'error': '#f44336'
    }[severity]

    payload = {
        'attachments': [{
            'color': color,
            'title': f'Alert: {severity.upper()}',
            'text': message,
            'ts': time.time()
        }]
    }

    requests.post(SLACK_WEBHOOK_URL, json=payload)
```

---

## 6. Monitoring Checklist

### Setup Checklist

**Application Metrics:**
- [x] Monitoring middleware installed
- [x] Metrics being collected
- [ ] Prometheus/metrics endpoint exposed
- [ ] Grafana connected
- [ ] Dashboards created

**Error Tracking:**
- [x] Sentry SDK installed
- [ ] Sentry project created
- [ ] DSN configured
- [x] Error capture working
- [ ] Alerts configured

**Logging:**
- [x] Structured logging configured
- [ ] Log files rotating
- [ ] Log aggregation setup (ELK/CloudWatch)
- [x] Security events logged
- [x] Performance events logged

**Dashboards:**
- [ ] Operations dashboard created
- [ ] Business metrics dashboard created
- [ ] Error dashboard created
- [ ] Dashboards shared with team

**Alerts:**
- [ ] Critical alerts configured
- [ ] Warning alerts configured
- [ ] Slack/Email integration setup
- [ ] On-call rotation defined
- [ ] Alert response procedures documented

### Production Readiness

- [ ] All metrics collecting
- [ ] Error tracking active
- [ ] Logs being aggregated
- [ ] Dashboards accessible
- [ ] Alerts tested
- [ ] Team trained on monitoring
- [ ] Runbooks created
- [ ] Incident response procedures defined

---

## 7. Key Metrics to Monitor

### Golden Signals (SRE)

**Latency:**
- p50, p95, p99 response times
- Target: p95 < 500ms (read), < 1000ms (write)

**Traffic:**
- Requests per second
- Active users
- API calls per endpoint

**Errors:**
- Error rate (%)
- 4xx errors (client errors)
- 5xx errors (server errors)
- Target: < 1% error rate

**Saturation:**
- CPU usage (< 70%)
- Memory usage (< 80%)
- Database connections (< 80% pool)
- Cache hit rate (> 80%)

### Application-Specific Metrics

**Rate Limiting:**
- Rate limit hits per endpoint
- Users hitting rate limits
- Category-based limit effectiveness

**Business Metrics:**
- Projects created per day
- Export operations per day
- Deep copy operations
- Active users per hour

**Performance:**
- Database query count per request
- Slow requests (> 2s)
- Cache operations
- Background job queue size

---

## 8. Troubleshooting

### High Error Rate

**Check:**
1. Sentry for error details
2. Application logs for stack traces
3. Recent deployments
4. Database connectivity
5. Redis connectivity

**Actions:**
- Rollback if needed
- Fix critical bugs
- Scale resources if needed

### Slow Response Times

**Check:**
1. Database query performance
2. Cache hit rate
3. External API calls
4. Resource usage (CPU, memory)

**Actions:**
- Optimize slow queries
- Add database indexes
- Increase cache hit rate
- Scale horizontally

### High Rate Limit Hits

**Check:**
1. Which endpoints are affected
2. Which users are hitting limits
3. Are limits too strict?
4. Is it legitimate usage?

**Actions:**
- Adjust rate limits if needed
- Contact users if abuse
- Optimize endpoints if slow

---

## 9. Next Steps

After Phase 6 setup:

1. **Monitor for 1 week** - Establish baselines
2. **Adjust alerts** - Reduce noise, catch real issues
3. **Create runbooks** - Document common issues
4. **Train team** - Ensure everyone can use monitoring
5. **Phase 7** - Migration & rollout with monitoring active

---

## 10. Resources

**Documentation:**
- [Sentry Django](https://docs.sentry.io/platforms/python/guides/django/)
- [Prometheus](https://prometheus.io/docs/)
- [Grafana](https://grafana.com/docs/)
- [Django Logging](https://docs.djangoproject.com/en/5.2/topics/logging/)

**Tools:**
- Sentry: https://sentry.io
- Grafana Cloud: https://grafana.com
- Datadog: https://www.datadoghq.com
- New Relic: https://newrelic.com

**Best Practices:**
- [Google SRE Book](https://sre.google/sre-book/table-of-contents/)
- [Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)

---

**Last Updated:** 2025-11-07
**Phase Status:** Code Complete
**Ready for:** Production deployment with monitoring
