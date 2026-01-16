# Deep Copy vs Rate Limiting - Conflict Analysis & Solutions

## 🚨 PROBLEM IDENTIFIED

### Current Situation:

**Deep Copy Features:**
1. `api_deep_copy_project` - Single project copy
2. `api_batch_copy_project` - **Up to 50 projects** in one request

**Rate Limiting:**
- Default: 10-20 requests per minute
- Applied to ALL endpoints via `@api_endpoint` decorator

### Conflict Scenarios:

#### Scenario 1: Batch Copy Long Operation
```python
# User copies 50 projects in one batch
POST /api/project/1/batch-copy/
{
    "base_name": "Monthly Template",
    "count": 50  # Maximum allowed
}

# Problem:
# - Single HTTP request = OK (not rate limited)
# - But operation takes 5-10 minutes
# - Request timeout (Gunicorn default: 30s)
# - User gets error, but backend still processing!
```

**Impact:** 🔴 CRITICAL
- User experience: Timeout errors
- Backend: Wasted resources (processing after client disconnect)
- Database: Potentially 50 partial projects

---

#### Scenario 2: Multiple Sequential Copies
```javascript
// User copies 15 projects sequentially
for (let i = 0; i < 15; i++) {
    await fetch('/api/project/1/deep-copy/', {
        method: 'POST',
        body: JSON.stringify({
            new_name: `Copy ${i}`
        })
    });
}

// Problem:
// - Request 1-10: OK
// - Request 11+: RATE LIMITED (429)
// - User's legitimate operation blocked!
```

**Impact:** 🟠 HIGH
- Legitimate operations blocked
- User frustration
- Feature unusable for bulk operations

---

#### Scenario 3: Concurrent Users
```
User A: Copies 5 projects (5 requests)
User B: Copies 8 projects (8 requests)
User C: Copies 10 projects (10 requests)

Total in 1 minute: 23 requests

Result:
- First 10 requests: OK
- Requests 11-23: RATE LIMITED (if using shared cache key)
```

**Impact:** 🟡 MEDIUM
- Multiple users affected by each other
- Though our rate limit is per-user, so this is OK

---

## 💡 SOLUTIONS

### Solution 1: Endpoint-Specific Rate Limits ✅ **RECOMMENDED**

**Approach:** Different rate limits for different endpoint types

**Implementation:**

```python
# detail_project/api_helpers.py - Enhanced

def api_endpoint(max_requests=100, window=60, endpoint_category=None):
    """
    Enhanced API endpoint decorator with category-based rate limiting.

    Categories:
    - 'bulk': Bulk operations (deep copy, batch operations)
    - 'read': Read-only operations (search, list)
    - 'write': Normal write operations (save, update)
    - None: Default rate limits
    """
    # Category-specific limits
    CATEGORY_LIMITS = {
        'bulk': {'max_requests': 5, 'window': 300},      # 5 req per 5 minutes
        'read': {'max_requests': 100, 'window': 60},     # 100 req per minute
        'write': {'max_requests': 20, 'window': 60},     # 20 req per minute
    }

    # Override with category limits if provided
    if endpoint_category and endpoint_category in CATEGORY_LIMITS:
        limits = CATEGORY_LIMITS[endpoint_category]
        max_requests = limits['max_requests']
        window = limits['window']

    def decorator(view_func):
        @functools.wraps(view_func)
        @login_required
        @rate_limit(max_requests=max_requests, window=window)
        def wrapped_view(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator
```

**Usage:**

```python
# views_api.py

# Bulk operations - 5 requests per 5 minutes
@api_endpoint(endpoint_category='bulk')
@require_POST
def api_deep_copy_project(request, project_id):
    """Deep copy with relaxed rate limit"""
    ...

@api_endpoint(endpoint_category='bulk')
@require_POST
def api_batch_copy_project(request, project_id):
    """Batch copy with relaxed rate limit"""
    ...

# Normal write operations - 20 requests per minute
@api_endpoint(endpoint_category='write')
@require_POST
def api_save_pekerjaan(request, project_id):
    """Normal save operation"""
    ...

# Read operations - 100 requests per minute
@api_endpoint(endpoint_category='read')
@require_GET
def api_search_ahsp(request, project_id):
    """Search operation with high limit"""
    ...
```

**Pros:**
- ✅ Granular control per endpoint type
- ✅ Protects critical operations
- ✅ Allows bulk operations
- ✅ Easy to configure per category

**Cons:**
- ⚠️ Need to categorize each endpoint
- ⚠️ May need tuning based on usage

---

### Solution 2: Background Jobs for Batch Operations ✅ **BEST LONG-TERM**

**Approach:** Move long-running operations to background jobs

**Implementation:**

```python
# Install Celery
pip install celery redis

# detail_project/tasks.py
from celery import shared_task
from .services import DeepCopyService

@shared_task(bind=True)
def batch_copy_project_task(self, source_project_id, new_owner_id, base_name, count, **kwargs):
    """
    Background task for batch copying projects.

    Updates progress periodically for frontend tracking.
    """
    from dashboard.models import Project
    from django.contrib.auth import get_user_model

    User = get_user_model()
    source_project = Project.objects.get(id=source_project_id)
    new_owner = User.objects.get(id=new_owner_id)

    service = DeepCopyService(source_project)
    projects = []
    errors = []

    for i in range(1, count + 1):
        try:
            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': i,
                    'total': count,
                    'status': f'Copying project {i} of {count}...'
                }
            )

            # Perform copy
            copy_name = f"{base_name} - Copy {i}"
            new_project = service.copy(
                new_owner=new_owner,
                new_name=copy_name,
                **kwargs
            )

            projects.append({
                'id': new_project.id,
                'nama': new_project.nama
            })

        except Exception as e:
            errors.append({
                'index': i,
                'name': f"{base_name} - Copy {i}",
                'error': str(e)
            })

    return {
        'projects': projects,
        'errors': errors,
        'summary': {
            'requested': count,
            'successful': len(projects),
            'failed': len(errors)
        }
    }


# views_api.py - New async endpoint
@api_endpoint(endpoint_category='bulk')
@require_POST
def api_batch_copy_project_async(request, project_id):
    """
    Start batch copy as background job.

    Returns immediately with task_id for progress tracking.
    """
    source_project = _owner_or_404(project_id, request.user)

    # Parse payload
    payload = json.loads(request.body)

    # Start background task
    task = batch_copy_project_task.delay(
        source_project_id=project_id,
        new_owner_id=request.user.id,
        base_name=payload['base_name'],
        count=payload['count'],
        copy_jadwal=payload.get('copy_jadwal', True)
    )

    return APIResponse.success(
        data={
            'task_id': task.id,
            'status_url': f'/api/task/{task.id}/status/'
        },
        message=f'Batch copy started. Processing {payload["count"]} projects...',
        status=202  # Accepted
    )


# Task status endpoint
@api_endpoint(endpoint_category='read')
@require_GET
def api_task_status(request, task_id):
    """
    Get status of background task.

    Returns: progress, state, result
    """
    from celery.result import AsyncResult

    task = AsyncResult(task_id)

    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if task.state == 'SUCCESS':
            response['result'] = task.info
    else:
        response = {
            'state': task.state,
            'status': str(task.info)
        }

    return APIResponse.success(data=response)
```

**Frontend Integration:**

```javascript
// Start batch copy
const response = await fetch('/api/project/1/batch-copy-async/', {
    method: 'POST',
    body: JSON.stringify({
        base_name: 'Template',
        count: 50
    })
});

const { task_id, status_url } = await response.json();

// Poll for progress
LoadingManager.showProgress('Copying projects...', 0, 50);

const interval = setInterval(async () => {
    const statusResponse = await fetch(status_url);
    const status = await statusResponse.json();

    if (status.state === 'PROGRESS') {
        LoadingManager.updateProgress(status.current, status.total);
    } else if (status.state === 'SUCCESS') {
        clearInterval(interval);
        LoadingManager.hide();
        toast.success(`Successfully copied ${status.result.summary.successful} projects`);
    } else if (status.state === 'FAILURE') {
        clearInterval(interval);
        LoadingManager.showError({
            title: 'Batch Copy Failed',
            message: status.status
        });
    }
}, 2000); // Poll every 2 seconds
```

**Pros:**
- ✅ No timeout issues
- ✅ Progress tracking
- ✅ User can navigate away
- ✅ No rate limit conflicts
- ✅ Better resource management

**Cons:**
- ⚠️ Requires Celery + Redis/RabbitMQ
- ⚠️ More complex setup
- ⚠️ Need task monitoring

---

### Solution 3: Hybrid Approach ✅ **PRACTICAL COMPROMISE**

**Approach:** Combine both solutions

**Small batches (<= 5):** Synchronous with relaxed rate limits
**Large batches (> 5):** Background jobs

```python
@api_endpoint(endpoint_category='bulk')
@require_POST
def api_batch_copy_project_smart(request, project_id):
    """
    Smart batch copy:
    - Small batches (<=5): Synchronous
    - Large batches (>5): Background job
    """
    payload = json.loads(request.body)
    count = payload['count']

    if count <= 5:
        # Synchronous - quick response
        return _batch_copy_sync(request, project_id, payload)
    else:
        # Async - background job
        return _batch_copy_async(request, project_id, payload)
```

---

### Solution 4: Whitelist Deep Copy Endpoints ⚠️ **NOT RECOMMENDED**

**Approach:** Skip rate limiting for deep copy endpoints

```python
# api_helpers.py
RATE_LIMIT_EXEMPT_ENDPOINTS = [
    'api_deep_copy_project',
    'api_batch_copy_project',
]

def rate_limit(max_requests=100, window=60):
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Skip rate limiting for exempt endpoints
            if view_func.__name__ in RATE_LIMIT_EXEMPT_ENDPOINTS:
                return view_func(request, *args, **kwargs)

            # Normal rate limiting
            ...
        return wrapped_view
    return decorator
```

**Pros:**
- ✅ Simple implementation
- ✅ No changes to endpoints

**Cons:**
- ❌ **SECURITY RISK:** No protection against abuse
- ❌ User could spam deep copy (expensive operation!)
- ❌ DoS vulnerability

---

## 📊 COMPARISON

| Solution | Complexity | Security | UX | Production Ready |
|----------|-----------|----------|-----|------------------|
| **1. Category Limits** | Low | Good | Good | ✅ Yes |
| **2. Background Jobs** | High | Excellent | Excellent | ⏳ Needs Celery |
| **3. Hybrid** | Medium | Good | Excellent | ✅ Yes |
| **4. Whitelist** | Very Low | Poor | Good | ❌ No |

---

## ✅ RECOMMENDED IMPLEMENTATION

### Phase 1 (Immediate): Category-Based Rate Limits

```python
# Apply now - quick fix
@api_endpoint(endpoint_category='bulk')  # 5 req per 5 min
def api_deep_copy_project(request, project_id):
    ...

@api_endpoint(endpoint_category='bulk')  # 5 req per 5 min
def api_batch_copy_project(request, project_id):
    ...
```

### Phase 2 (Week 2-3): Background Jobs

- Setup Celery
- Implement async batch copy
- Add progress tracking
- Migrate large batches (>5) to async

### Phase 3 (Week 4+): Optimization

- Add batch size recommendations
- Implement queue priorities
- Add admin controls for limits

---

## 🎯 IMMEDIATE ACTION ITEMS

1. **Update api_helpers.py** - Add category support
2. **Update deep copy endpoints** - Use `endpoint_category='bulk'`
3. **Test batch copy** - Verify it works with new limits
4. **Document limits** - Update API docs with rate limits per category
5. **Monitor usage** - Track deep copy frequency

---

## 📝 CONFIGURATION RECOMMENDATIONS

### Rate Limits by Category:

```python
RATE_LIMIT_CONFIG = {
    'bulk': {
        'max_requests': 5,
        'window': 300,  # 5 minutes
        'description': 'Deep copy, batch operations'
    },
    'write': {
        'max_requests': 20,
        'window': 60,  # 1 minute
        'description': 'Save, update operations'
    },
    'read': {
        'max_requests': 100,
        'window': 60,  # 1 minute
        'description': 'Search, list operations'
    },
    'export': {
        'max_requests': 10,
        'window': 60,  # 1 minute
        'description': 'PDF, Excel exports'
    }
}
```

### Endpoint Categorization:

| Endpoint | Category | Limit | Reason |
|----------|----------|-------|--------|
| `deep-copy` | bulk | 5/5min | Expensive operation |
| `batch-copy` | bulk | 5/5min | Very expensive |
| `save-*` | write | 20/min | Normal write |
| `search-*` | read | 100/min | Lightweight read |
| `export-*` | export | 10/min | CPU intensive |

---

## 🚨 WARNING SIGNS TO MONITOR

After implementing category limits, monitor for:

1. **Legitimate users hitting limits**
   - Solution: Increase category limits

2. **Batch operations timing out**
   - Solution: Implement background jobs (Phase 2)

3. **Users attempting workarounds**
   - Solution: Add batch size guidance in UI

4. **Rate limit abuse on bulk endpoints**
   - Solution: Add additional checks (IP-based, daily limits)

---

**Status:** 🟡 Issue Identified - Solution Ready
**Priority:** 🔴 HIGH - Should implement before production
**Timeline:** Can implement Phase 1 today, Phase 2 in Week 2-3
