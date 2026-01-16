# WEEK 1 Implementation Guide - Full Optimization (Option A)
## Quick Wins + Tier 1 Stabilization

**Timeline**: Week 1 of 8 (Days 1-5)
**Goal**: Fix critical blockers, establish reliable baseline
**Exit Criteria**: ✅ >99% auth ✅ <2s P99 ✅ Zero 100s outliers

---

## 📅 DAY 1: QUICK WINS (7 Hours Total)

### Morning Session (9:00 AM - 1:00 PM) - 4 Hours

#### Task 1.1: Database Indexes (2 hours)
**Priority**: CRITICAL ⚠️
**Impact**: 20-30% faster queries immediately
**File**: Create new migration file

**Step-by-Step**:

```bash
# Step 1: Create migration file
cd "d:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT"
python manage.py makemigrations --empty --name add_performance_indexes apps.project
```

**Migration Code**:
```python
# File: apps/project/migrations/XXXX_add_performance_indexes.py

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('project', 'XXXX_previous_migration'),  # Update with actual previous migration
    ]

    operations = [
        # Project indexes
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_project_created_at
                ON project_project(created_at DESC);

                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_project_owner
                ON project_project(owner_id);

                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_project_status
                ON project_project(status);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_project_created_at;
                DROP INDEX IF EXISTS idx_project_owner;
                DROP INDEX IF EXISTS idx_project_status;
            """
        ),

        # Pekerjaan indexes
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pekerjaan_project
                ON project_pekerjaan(project_id);

                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pekerjaan_parent
                ON project_pekerjaan(parent_id);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_pekerjaan_project;
                DROP INDEX IF EXISTS idx_pekerjaan_parent;
            """
        ),

        # Harga Item indexes
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_harga_item_pekerjaan
                ON project_hargaitem(pekerjaan_id);

                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_harga_item_referensi
                ON project_hargaitem(item_referensi_id);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_harga_item_pekerjaan;
                DROP INDEX IF EXISTS idx_harga_item_referensi;
            """
        ),

        # Audit Trail indexes (for 100s outlier fix)
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_trail_project_time
                ON audit_trail(project_id, timestamp DESC);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_audit_trail_project_time;
            """
        ),
    ]
```

**Execute Migration**:
```bash
# Step 2: Run migration (CONCURRENTLY = no table lock)
python manage.py migrate

# Step 3: Verify indexes created
python manage.py dbshell
\di+ idx_*  # List indexes

# Expected output: Should show all 7 new indexes
```

**Validation**:
```sql
-- Step 4: Test query performance
EXPLAIN ANALYZE
SELECT * FROM project_project
WHERE owner_id = 1
ORDER BY created_at DESC
LIMIT 20;

-- Before: Sequential scan (slow)
-- After: Index scan on idx_project_created_at (fast)
```

**Checklist**:
- [ ] Migration file created
- [ ] Migration executed successfully
- [ ] 7 indexes verified in database
- [ ] Query performance improved (run EXPLAIN ANALYZE)
- [ ] No errors in Django logs

**Estimated Time**: 2 hours (including testing)

---

#### Task 1.2: Dashboard Pagination (2 hours)
**Priority**: CRITICAL ⚠️
**Impact**: Eliminates 116s outliers on highest-traffic page
**File**: `dashboard/views.py` or main dashboard view

**Step-by-Step**:

```python
# Step 1: Find dashboard view
# File: dashboard/views.py (or similar)

# BEFORE (Current problematic code):
from django.shortcuts import render
from apps.project.models import Project

def dashboard(request):
    # Loading ALL projects - causes 116s outliers
    projects = Project.objects.filter(owner=request.user)\
        .order_by('-created_at')

    context = {
        'projects': projects,  # Could be thousands!
        'total_count': projects.count()
    }
    return render(request, 'dashboard/dashboard.html', context)


# AFTER (Optimized with pagination):
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from apps.project.models import Project

def dashboard(request):
    # Optimize query with select_related
    projects_queryset = Project.objects.filter(owner=request.user)\
        .select_related('owner')\
        .order_by('-created_at')

    # Add pagination - 20 projects per page
    paginator = Paginator(projects_queryset, 20)
    page_number = request.GET.get('page', 1)

    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)

    context = {
        'page_obj': page_obj,  # Only 20 projects loaded
        'total_count': paginator.count,
        'num_pages': paginator.num_pages
    }
    return render(request, 'dashboard/dashboard.html', context)
```

**Update Template**:
```html
<!-- File: dashboard/templates/dashboard/dashboard.html -->

<!-- BEFORE: -->
{% for project in projects %}
    <!-- Project card -->
{% endfor %}

<!-- AFTER: -->
{% for project in page_obj %}
    <!-- Project card -->
{% endfor %}

<!-- Add pagination controls -->
<div class="pagination">
    <span class="step-links">
        {% if page_obj.has_previous %}
            <a href="?page=1">&laquo; first</a>
            <a href="?page={{ page_obj.previous_page_number }}">previous</a>
        {% endif %}

        <span class="current">
            Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}
        </span>

        {% if page_obj.has_next %}
            <a href="?page={{ page_obj.next_page_number }}">next</a>
            <a href="?page={{ page_obj.paginator.num_pages }}">last &raquo;</a>
        {% endif %}
    </span>
</div>

<!-- Show total count -->
<p class="text-muted">Showing {{ page_obj.start_index }}-{{ page_obj.end_index }} of {{ page_obj.paginator.count }} projects</p>
```

**Validation**:
```python
# Step 2: Test in Django shell
python manage.py shell

from django.contrib.auth import get_user_model
from apps.project.models import Project
from django.core.paginator import Paginator

User = get_user_model()
user = User.objects.first()

# Test pagination
projects = Project.objects.filter(owner=user).order_by('-created_at')
paginator = Paginator(projects, 20)

print(f"Total projects: {paginator.count}")
print(f"Total pages: {paginator.num_pages}")

page_1 = paginator.get_page(1)
print(f"Page 1 has {len(page_1)} projects")

# Expected: Should only query 20 projects, not all
```

**Checklist**:
- [ ] View function updated with pagination
- [ ] Template updated with pagination controls
- [ ] Tested in browser (should load fast)
- [ ] No 116s outliers in next load test
- [ ] Page navigation works correctly

**Estimated Time**: 2 hours (including template updates)

---

### Afternoon Session (2:00 PM - 5:00 PM) - 3 Hours

#### Task 1.3: Fix Client Metrics CSRF (1 hour)
**Priority**: HIGH
**Impact**: 100% failure → 0% failure
**File**: `apps/monitoring/views.py`

**Step-by-Step**:

```python
# File: apps/monitoring/views.py

# BEFORE (Current failing code):
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['POST'])
def report_client_metric(request):
    # This requires CSRF token, which Locust doesn't send
    # Result: 403 Forbidden
    metric_data = request.data
    # ... save metric
    return Response({'status': 'ok'})


# AFTER (Fixed with CSRF exempt):
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import logging

logger = logging.getLogger(__name__)

@csrf_exempt  # Client metrics are anonymous, no CSRF needed
@api_view(['POST'])
@permission_classes([AllowAny])  # Allow unauthenticated metrics
def report_client_metric(request):
    """
    Receive client-side performance metrics

    This endpoint accepts anonymous metrics from client browsers.
    CSRF is exempt because:
    1. No sensitive data is modified
    2. Metrics are write-only (no data returned)
    3. Used by load testing tools
    """
    try:
        metric_data = request.data

        # Validate basic structure
        if not metric_data or 'metric_type' not in metric_data:
            return Response(
                {'error': 'Missing metric_type'},
                status=400
            )

        # Save metric to database or cache
        # ... existing save logic ...

        logger.info(f"Client metric received: {metric_data.get('metric_type')}")

        return Response({'status': 'ok'}, status=200)

    except Exception as e:
        logger.error(f"Error saving client metric: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=500
        )
```

**Alternative: Use Token-Based Auth** (if you prefer not to exempt CSRF):
```python
# Option B: Use custom header instead of CSRF exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(['POST'])
@permission_classes([AllowAny])
def report_client_metric(request):
    # Accept metrics with custom header instead of CSRF
    api_key = request.META.get('HTTP_X_METRICS_KEY')

    # Simple validation (or use proper API key auth)
    if api_key != 'metrics-collector-key':
        return Response({'error': 'Invalid API key'}, status=403)

    # ... rest of the code
```

**Update Locustfile** (if using Option B):
```python
# File: load_testing/locustfile.py

class ProjectUserBehavior(TaskSet):

    @task(1)
    def report_metric(self):
        """Report client-side metric"""
        self.client.post(
            "/api/monitoring/report-client-metric/",
            json={
                "metric_type": "page_load",
                "value": 123,
                "url": "/dashboard/"
            },
            headers={
                'X-Metrics-Key': 'metrics-collector-key'  # Custom header
            },
            name="/api/monitoring/report-client-metric/"
        )
```

**Validation**:
```bash
# Step 1: Test with curl
curl -X POST http://localhost:8000/api/monitoring/report-client-metric/ \
  -H "Content-Type: application/json" \
  -d '{"metric_type": "test", "value": 100}'

# Expected: {"status": "ok"} with 200 status

# Step 2: Run quick Locust test
locust -f load_testing/locustfile.py --headless -u 10 -r 1 -t 30s \
  --host=http://localhost:8000 \
  --only-summary

# Expected: 0% failures for report-client-metric endpoint
```

**Checklist**:
- [ ] View decorated with @csrf_exempt or custom auth
- [ ] permission_classes set to [AllowAny]
- [ ] Tested with curl (200 OK response)
- [ ] Tested with Locust (0% failures)
- [ ] Logging added for debugging

**Estimated Time**: 1 hour

---

#### Task 1.4: Start Authentication Debug (2 hours)
**Priority**: CRITICAL ⚠️
**Impact**: Unblocks all dependent work
**Goal**: Identify root cause of 46% auth failures

**Debugging Steps**:

```python
# Step 1: Add detailed logging to authentication
# File: config/settings/base.py or development.py

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'debug_auth.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.contrib.auth': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'allauth': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.contrib.sessions': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

```python
# Step 2: Add middleware to log authentication attempts
# File: apps/monitoring/middleware.py (create if not exists)

import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class AuthDebugMiddleware(MiddlewareMixin):
    """Middleware to debug authentication issues"""

    def process_request(self, request):
        if request.path.endswith('/login/'):
            logger.debug(f"Login attempt from {request.META.get('REMOTE_ADDR')}")
            logger.debug(f"Session key: {request.session.session_key}")
            logger.debug(f"CSRF token: {request.META.get('CSRF_COOKIE')}")

    def process_response(self, request, response):
        if request.path.endswith('/login/'):
            logger.debug(f"Login response status: {response.status_code}")
            if response.status_code == 500:
                logger.error(f"Login failed with 500 error")
                logger.error(f"User authenticated: {request.user.is_authenticated}")

        return response
```

```python
# Step 3: Add to MIDDLEWARE
# File: config/settings/development.py

MIDDLEWARE = [
    # ... existing middleware ...
    'apps.monitoring.middleware.AuthDebugMiddleware',  # Add at the end
]
```

**Check Redis Connection Pool**:
```python
# Step 4: Verify Redis session backend configuration
# File: config/settings/base.py

# Current configuration
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # CRITICAL: Increase connection pool for concurrent users
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 100,  # Increase from default 50
                "retry_on_timeout": True,
            },
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
        },
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
```

**Run Diagnostic Test**:
```bash
# Step 5: Test authentication in isolation
python manage.py shell

from django.contrib.auth import authenticate, login
from django.contrib.auth import get_user_model
from django.test import RequestFactory

User = get_user_model()
factory = RequestFactory()

# Create test user if not exists
user, created = User.objects.get_or_create(
    username='testuser',
    defaults={'email': 'test@example.com'}
)
if created:
    user.set_password('testpass123')
    user.save()

# Test authentication
request = factory.post('/login/')
request.session = {}

# Authenticate
auth_user = authenticate(request, username='testuser', password='testpass123')
print(f"Authentication result: {auth_user}")
print(f"User authenticated: {auth_user is not None}")

# If auth fails, check:
# 1. Password hashing
# 2. Session backend
# 3. Database connection
```

**Monitor During Load Test**:
```bash
# Step 6: Run small load test and watch logs
# Terminal 1: Watch authentication logs
tail -f debug_auth.log | grep -i "login\|auth\|session"

# Terminal 2: Run Locust test
locust -f load_testing/locustfile.py --headless -u 10 -r 1 -t 60s \
  --host=http://localhost:8000

# Look for patterns:
# - Session key errors
# - CSRF token mismatches
# - Redis connection timeouts
# - Database query errors
```

**Checklist**:
- [ ] Logging configured for auth components
- [ ] AuthDebugMiddleware added
- [ ] Redis connection pool increased
- [ ] Diagnostic test run successfully
- [ ] Load test logs analyzed
- [ ] Root cause hypothesis documented

**Estimated Time**: 2 hours (debugging session)

---

### End of Day 1 Checklist

**Completed Tasks**:
- [x] Quick Win 1: Database indexes (2 hours)
- [x] Quick Win 2: Dashboard pagination (2 hours)
- [x] Quick Win 3: Client metrics CSRF fix (1 hour)
- [x] Authentication debugging started (2 hours)

**Expected Results**:
- ✅ 20-30% faster query performance
- ✅ Dashboard loads without 116s spikes
- ✅ Client metrics: 100% → 0% failure rate
- ✅ Authentication root cause identified (or narrowed down)

**Tomorrow's Focus**: Complete authentication fix

---

## 📅 DAY 2: FIX AUTHENTICATION (8 Hours)

### Based on Day 1 Findings

#### Scenario A: CSRF Token Issue

```python
# File: load_testing/locustfile.py

class ProjectUser(HttpUser):

    def on_start(self):
        """Get CSRF token before login"""
        # Step 1: Get login page to obtain CSRF token
        response = self.client.get("/accounts/login/")

        # Step 2: Extract CSRF token from cookies
        csrf_token = response.cookies.get('csrftoken')

        # Store for later use
        self.csrf_token = csrf_token

        # Step 3: Login with CSRF token
        login_response = self.client.post(
            "/accounts/login/",
            data={
                "login": "testuser",
                "password": "testpass123",
                "csrfmiddlewaretoken": csrf_token
            },
            headers={
                "Referer": self.client.base_url + "/accounts/login/"
            },
            catch_response=True
        )

        if login_response.status_code == 200:
            login_response.success()
        else:
            login_response.failure(f"Login failed: {login_response.status_code}")
```

#### Scenario B: Redis Session Timeout

```python
# File: config/settings/base.py

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 200,  # Increase even more
                "retry_on_timeout": True,
                "socket_keepalive": True,
                "socket_keepalive_options": {
                    1: 1,  # TCP_KEEPIDLE
                    2: 1,  # TCP_KEEPINTVL
                    3: 3,  # TCP_KEEPCNT
                },
            },
            "SOCKET_CONNECT_TIMEOUT": 10,  # Increase timeout
            "SOCKET_TIMEOUT": 10,
            "RETRY_ON_ERROR": [ConnectionError, TimeoutError],
        },
    }
}
```

#### Scenario C: Database Connection Pool

```python
# File: config/settings/base.py

# If using PgBouncer, ensure enough connections
DATABASES = {
    "default": {
        # ... existing config ...
        "CONN_MAX_AGE": 0 if using_pgbouncer else 600,

        # If NOT using PgBouncer, increase connection pool
        "CONN_HEALTH_CHECKS": not using_pgbouncer,

        # Add connection pool settings (if using django-db-connection-pool)
        "POOL_OPTIONS": {
            "POOL_SIZE": 20,
            "MAX_OVERFLOW": 10,
        }
    }
}
```

**Full Day 2 schedule** will be detailed based on Day 1 findings.

---

## 📅 DAY 3-5: ELIMINATE 100s OUTLIERS

Will be detailed in separate daily guides as we progress.

**Focus Areas**:
- Day 3: Rekap RAB optimization (N+1 queries)
- Day 4: Audit Trail pagination
- Day 5: Full Tier 1 validation with load tests

---

## 📊 WEEK 1 SUCCESS METRICS

**Daily Tracking**:
| Metric | Baseline | Day 1 Target | Day 2 Target | Day 5 Target |
|--------|----------|--------------|--------------|--------------|
| Auth Success | 54% | 54% | **>95%** | **>99%** |
| Dashboard P99 | 95,000ms | **<2,000ms** | <2,000ms | <1,000ms |
| Client Metrics | 100% fail | **0% fail** | 0% fail | 0% fail |
| Rekap RAB P99 | 117,000ms | 117,000ms | 117,000ms | **<2,000ms** |

---

## 🚀 GETTING STARTED NOW

**Next 30 Minutes**:
1. [ ] Review this implementation guide
2. [ ] Backup database (safety first!)
3. [ ] Create git branch: `feature/week1-optimization`
4. [ ] Start Task 1.1: Database indexes

**Backup Command**:
```bash
# Backup PostgreSQL database
pg_dump -U postgres ahsp_sni_db > backup_week1_start.sql

# Or using Django dumpdata
python manage.py dumpdata > backup_week1_start.json
```

**Git Workflow**:
```bash
git checkout -b feature/week1-optimization
git add .
git commit -m "Week 1 Day 1: Starting Quick Wins - Database indexes, Dashboard pagination, Client metrics fix"
```

---

**Ready to start?** Begin with Task 1.1 (Database Indexes) now! 🚀

All implementation details, code snippets, and validation steps are ready above.
