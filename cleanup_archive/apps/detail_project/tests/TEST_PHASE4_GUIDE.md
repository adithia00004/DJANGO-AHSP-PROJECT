# Phase 4 Infrastructure Testing Guide

This guide covers testing strategy for Phase 4 infrastructure components including health checks, rate limiting, and API helpers.

## Test Coverage Overview

### Components Tested

1. **Health Check Endpoints** (`/health/*`)
   - Full health check with database and cache validation
   - Simple liveness check
   - Readiness check for orchestration
   - Liveness check for container health

2. **API Response Helpers** (`APIResponse` class)
   - Success responses (200, 201)
   - Error responses (400, 404, 500)
   - Standardized JSON format
   - Proper HTTP status codes

3. **Rate Limiting** (`@rate_limit` decorator)
   - Per-user rate tracking
   - Category-based limits (bulk, write, read, export)
   - Cache-based state management
   - Retry-after headers

4. **API Endpoint Decorator** (`@api_endpoint`)
   - Authentication requirement
   - Rate limit integration
   - Exception handling

## Running Tests

### Full Test Suite

```bash
# Run all Phase 4 tests
pytest detail_project/tests/test_phase4_infrastructure.py -v

# Run with coverage
pytest detail_project/tests/test_phase4_infrastructure.py --cov=detail_project --cov-report=html

# Run specific test class
pytest detail_project/tests/test_phase4_infrastructure.py::TestHealthCheckEndpoints -v

# Run specific test
pytest detail_project/tests/test_phase4_infrastructure.py::TestHealthCheckEndpoints::test_health_check_success -v
```

### Quick Validation

```bash
# Syntax check only
python -m py_compile detail_project/tests/test_phase4_infrastructure.py

# Run smoke tests only
pytest detail_project/tests/test_phase4_infrastructure.py -k "smoke" -v
```

## Test Scenarios

### 1. Health Check Tests

#### Scenario: All Systems Healthy
```python
def test_health_check_success(client):
    response = client.get('/health/')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['checks']['database']['status'] == 'ok'
    assert data['checks']['cache']['status'] == 'ok'
```

**Expected:**
- HTTP 200 OK
- JSON with status='ok'
- Database check passes
- Cache check passes
- Version and timestamp included

#### Scenario: Database Failure
```python
def test_health_check_database_failure(client):
    with patch('django.db.connection.cursor') as mock_cursor:
        mock_cursor.side_effect = Exception('Database connection failed')
        response = client.get('/health/')
        assert response.status_code == 503
```

**Expected:**
- HTTP 503 Service Unavailable
- JSON with status='error'
- Database check shows error
- Error message included

#### Scenario: Cache Failure
```python
def test_health_check_cache_failure(client):
    with patch('django.core.cache.cache.set') as mock_set:
        mock_set.side_effect = Exception('Redis connection failed')
        response = client.get('/health/')
        assert response.status_code == 503
```

**Expected:**
- HTTP 503 Service Unavailable
- JSON with status='error'
- Cache check shows error

### 2. API Response Helper Tests

#### Scenario: Success Response
```python
def test_api_response_success():
    response = APIResponse.success(
        data={'id': 1, 'name': 'Test'},
        message='Operation successful'
    )
    assert response.status_code == 200
    data = json.loads(response.content)
    assert data['success'] is True
```

**Expected JSON:**
```json
{
  "success": true,
  "data": {"id": 1, "name": "Test"},
  "message": "Operation successful"
}
```

#### Scenario: Error Response
```python
def test_api_response_error():
    response = APIResponse.error(
        message='Validation failed',
        code='VALIDATION_ERROR',
        details={'field': 'name'},
        status=400
    )
    assert response.status_code == 400
```

**Expected JSON:**
```json
{
  "success": false,
  "message": "Validation failed",
  "code": "VALIDATION_ERROR",
  "details": {"field": "name"}
}
```

### 3. Rate Limiting Tests

#### Scenario: Basic Rate Limiting
```python
@rate_limit(max_requests=5, window=60)
def test_view(request):
    return JsonResponse({'status': 'ok'})

# First 5 requests succeed
for i in range(5):
    response = test_view(request)
    assert response.status_code == 200

# 6th request is rate limited
response = test_view(request)
assert response.status_code == 429
```

**Expected:**
- First 5 requests: HTTP 200 OK
- 6th request: HTTP 429 Too Many Requests
- Response includes retry_after

#### Scenario: Per-User Rate Limiting
```python
# User1 exhausts their limit
for i in range(3):
    response = test_view(client1.request())
    assert response.status_code == 200

# User1 is blocked
response = test_view(client1.request())
assert response.status_code == 429

# But user2 can still make requests
response = test_view(client2.request())
assert response.status_code == 200
```

**Expected:**
- Rate limits are tracked per user
- Different users have independent limits
- Anonymous users are also rate limited

#### Scenario: Category-Based Rate Limiting

```python
# Bulk operations: 5 requests per 5 minutes
@rate_limit(category='bulk')
def bulk_operation(request):
    return JsonResponse({'status': 'ok'})

# Write operations: 20 requests per minute
@rate_limit(category='write')
def write_operation(request):
    return JsonResponse({'status': 'ok'})

# Read operations: 100 requests per minute
@rate_limit(category='read')
def read_operation(request):
    return JsonResponse({'status': 'ok'})
```

**Expected:**
- Bulk operations have strictest limits
- Read operations have most lenient limits
- Different windows per category

### 4. API Endpoint Decorator Tests

#### Scenario: Authentication Required
```python
@api_endpoint()
def protected_view(request):
    return JsonResponse({'status': 'ok'})

# Anonymous request is rejected
response = protected_view(anonymous_request)
assert response.status_code == 401
```

**Expected:**
- HTTP 401 Unauthorized for anonymous users
- HTTP 200 OK for authenticated users

#### Scenario: Rate Limiting Integration
```python
@api_endpoint(category='bulk')
def bulk_api(request):
    return JsonResponse({'status': 'ok'})
```

**Expected:**
- Authentication check first
- Then rate limiting applied
- Category-specific limits enforced

#### Scenario: Exception Handling
```python
@api_endpoint()
def error_view(request):
    raise ValueError('Test error')

response = error_view(authenticated_request)
assert response.status_code == 500
```

**Expected:**
- Exceptions caught gracefully
- Returns standardized JSON error
- HTTP 500 for unhandled exceptions

## Integration Testing

### Complete Request Flow

```python
def test_complete_api_request_flow():
    # 1. Anonymous request → 401
    response = client.get(api_url)
    assert response.status_code == 401

    # 2. Authenticated request → 200
    client.force_login(user)
    response = client.get(api_url)
    assert response.status_code == 200

    # 3. Multiple requests → rate limited
    for i in range(max_requests + 1):
        response = client.get(api_url)

    assert response.status_code == 429

    # 4. Response format is standardized
    data = response.json()
    assert 'success' in data
    assert 'message' in data
```

## Test Data Setup

### Fixtures Used

```python
@pytest.fixture
def client():
    """Unauthenticated test client."""
    return Client()

@pytest.fixture
def user(db):
    """Test user for authentication."""
    return User.objects.create_user(
        username='testuser',
        password='testpass123'
    )

@pytest.fixture
def client_logged(client, user):
    """Authenticated test client."""
    client.force_login(user)
    return client

@pytest.fixture
def project(db, user):
    """Test project."""
    return Project.objects.create(
        nama='Test Project',
        owner=user,
        tahun_project=2025
    )
```

### Cache Setup

Tests automatically clear cache before each test:

```python
def setup_method(self):
    """Clear cache before each test."""
    cache.clear()
```

## Mocking Strategy

### Database Failure Simulation

```python
with patch('django.db.connection.cursor') as mock_cursor:
    mock_cursor.side_effect = Exception('Database connection failed')
    # Run test
```

### Cache Failure Simulation

```python
with patch('django.core.cache.cache.set') as mock_set:
    mock_set.side_effect = Exception('Redis connection failed')
    # Run test
```

### Custom Mock Objects

```python
mock_request = MagicMock()
mock_request.user = user
mock_request.method = 'GET'
mock_request.path = '/api/test/'
```

## Assertions Checklist

### Health Check Assertions

- [ ] Status code is 200 (healthy) or 503 (unhealthy)
- [ ] Response is valid JSON
- [ ] Contains 'status' field
- [ ] Contains 'checks' object
- [ ] Contains 'database' check
- [ ] Contains 'cache' check
- [ ] Contains 'version' string
- [ ] Contains 'timestamp' in ISO format

### API Response Assertions

- [ ] Status code matches expectation (200, 201, 400, 404, 500, etc.)
- [ ] Response is valid JSON
- [ ] Contains 'success' boolean
- [ ] Contains 'message' string (or null)
- [ ] Success responses include 'data'
- [ ] Error responses include 'code'
- [ ] Error responses may include 'details'

### Rate Limiting Assertions

- [ ] First N requests return 200
- [ ] N+1 request returns 429
- [ ] Response includes 'retry_after'
- [ ] Rate limits are per-user
- [ ] Anonymous users are rate limited
- [ ] Category limits are enforced
- [ ] Cache is used for tracking

## Continuous Integration

### GitHub Actions Example

```yaml
name: Phase 4 Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_DB: test_db
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements/development.txt

      - name: Run Phase 4 tests
        run: |
          pytest detail_project/tests/test_phase4_infrastructure.py -v --cov
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0
```

## Performance Testing

### Rate Limit Performance

Test rate limiting with high request volume:

```bash
# Load test with 100 concurrent users
pytest detail_project/tests/test_phase4_infrastructure.py \
  --benchmark-only \
  -k "rate_limit"
```

### Health Check Performance

Health checks should respond within 100ms:

```python
import time

def test_health_check_performance():
    start = time.time()
    response = client.get('/health/')
    duration = time.time() - start

    assert duration < 0.1  # 100ms
    assert response.status_code == 200
```

## Troubleshooting Test Failures

### Common Issues

1. **Cache Not Available**
   ```
   Error: ConnectionRefusedError: Error 111 connecting to localhost:6379
   ```
   **Solution:** Start Redis: `docker run -d -p 6379:6379 redis:7-alpine`

2. **Database Not Available**
   ```
   Error: connection to server at "localhost" failed
   ```
   **Solution:** Start PostgreSQL or use SQLite for tests

3. **Import Errors**
   ```
   ModuleNotFoundError: No module named 'detail_project.api_helpers'
   ```
   **Solution:** Ensure PYTHONPATH includes project root

4. **Rate Limit Tests Fail**
   ```
   AssertionError: expected 429, got 200
   ```
   **Solution:** Clear cache before test or check rate limit configuration

### Debug Mode

Run tests with verbose output:

```bash
pytest detail_project/tests/test_phase4_infrastructure.py \
  -vv \
  --tb=long \
  --log-cli-level=DEBUG
```

## Coverage Goals

### Phase 4 Coverage Targets

- Health checks: 100% (critical for monitoring)
- API helpers: 100% (core infrastructure)
- Rate limiting: 95% (complex logic)
- API endpoints: 85% (integration tests)

### Checking Coverage

```bash
pytest detail_project/tests/test_phase4_infrastructure.py \
  --cov=detail_project.api_helpers \
  --cov=detail_project.views_health \
  --cov-report=html \
  --cov-report=term

# View HTML report
open htmlcov/index.html
```

## Next Steps

After Phase 4 tests pass:

1. **Phase 5: Integration Tests**
   - Test actual API endpoints with rate limiting
   - Test deep copy with bulk category
   - Test export endpoints with export category

2. **Phase 6: Load Testing**
   - Simulate 50+ concurrent users
   - Test rate limiting under load
   - Verify cache performance

3. **Phase 7: Security Testing**
   - Test authentication bypass attempts
   - Test rate limit circumvention
   - Test injection attacks

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [Django Testing](https://docs.djangoproject.com/en/5.2/topics/testing/)
- [pytest-django](https://pytest-django.readthedocs.io/)
- [HTTP Status Codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)
- [Rate Limiting Best Practices](https://cloud.google.com/architecture/rate-limiting-strategies)

---

**Last Updated:** 2025-11-07
**Test Coverage:** 95%+ target for Phase 4 components
