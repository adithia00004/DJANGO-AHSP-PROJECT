# 🧪 Comprehensive Testing Plan - AHSP Detail Project

## 📅 Created: November 7, 2025
## 🎯 Purpose: Verify all Phase 0-6 implementations

---

# 🚀 QUICK START TESTING PLAN

Follow these steps in order to verify all implementations.

---

## ✅ STEP 1: Prerequisites Check (5 minutes)

### 1.1 Check Python Dependencies

```bash
# Check Python version (should be 3.8+)
python --version

# Check if virtual environment is activated
which python

# Install/update dependencies
pip install -r requirements.txt

# Install testing dependencies
pip install pytest pytest-django pytest-cov locust
```

### 1.2 Check Redis Installation (CRITICAL!)

```bash
# Check if Redis is running
redis-cli ping
# Expected output: PONG

# If Redis not installed, install it:
# Option 1: Docker (recommended)
docker run -d -p 6379:6379 --name redis-ahsp redis:7-alpine

# Option 2: Use setup script
./scripts/setup-redis.sh docker
```

**⚠️ CRITICAL**: Redis is required for rate limiting! Without it:
- Rate limiting won't work
- Cache-based features will fail
- Tests will fail

### 1.3 Verify Database

```bash
# Run migrations
python manage.py migrate

# Create superuser if not exists
python manage.py createsuperuser --username admin --email admin@example.com
```

---

## ✅ STEP 2: Basic Functionality Test (10 minutes)

### 2.1 Run Development Server

```bash
# Start server
python manage.py runserver

# Expected output:
# Starting development server at http://127.0.0.1:8000/
# Quit the server with CONTROL-C.
```

### 2.2 Verify Basic Pages (Open in browser)

**Test these URLs:**

1. **Admin Page**: http://127.0.0.1:8000/admin/
   - ✅ Should load login page
   - ✅ Login with superuser
   - ✅ Should see admin dashboard

2. **Dashboard**: http://127.0.0.1:8000/dashboard/
   - ✅ Should redirect to login if not logged in
   - ✅ After login, should see project list

3. **Health Check**: http://127.0.0.1:8000/health/
   - ✅ Should return JSON with status "ok"
   - ✅ Database check: "ok"
   - ✅ Cache check: "ok" (if Redis running)

**Expected Response:**
```json
{
  "status": "ok",
  "checks": {
    "database": {"status": "ok"},
    "cache": {"status": "ok"}
  },
  "version": null,
  "timestamp": "2025-11-07T..."
}
```

---

## ✅ STEP 3: Health Check Endpoints (5 minutes)

Test all health check endpoints:

### 3.1 Full Health Check

```bash
curl http://127.0.0.1:8000/health/ | jq
```

**Expected:** Status 200, all checks "ok"

### 3.2 Simple Health Check

```bash
curl http://127.0.0.1:8000/health/simple/
```

**Expected:** Status 200, plain text "OK"

### 3.3 Readiness Check

```bash
curl http://127.0.0.1:8000/health/ready/ | jq
```

**Expected:** Status 200, database and cache "ok"

### 3.4 Liveness Check

```bash
curl http://127.0.0.1:8000/health/live/
```

**Expected:** Status 200, plain text "OK"

### 3.5 Test with Redis Down (Optional)

```bash
# Stop Redis
docker stop redis-ahsp  # or: sudo systemctl stop redis

# Test health check
curl http://127.0.0.1:8000/health/ | jq

# Expected: cache status should be "error", overall status "degraded"

# Start Redis again
docker start redis-ahsp  # or: sudo systemctl start redis
```

---

## ✅ STEP 4: Phase 4 Infrastructure Tests (15 minutes)

### 4.1 Run Phase 4 Test Suite

```bash
# Run all Phase 4 tests
pytest detail_project/tests/test_phase4_infrastructure.py -v

# Run with coverage
pytest detail_project/tests/test_phase4_infrastructure.py -v --cov=detail_project --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### 4.2 Expected Results

**Test Categories:**
- ✅ Health Check Tests (12 tests) - All should pass
- ✅ API Response Helpers (7 tests) - All should pass
- ✅ Rate Limiting Tests (10 tests) - All should pass
- ✅ API Endpoint Tests (4 tests) - All should pass
- ✅ Integration Tests (3 tests) - All should pass

**Total:** ~36 tests, all should PASS

### 4.3 Run Specific Test Categories

```bash
# Health checks only
pytest detail_project/tests/test_phase4_infrastructure.py::TestHealthCheckEndpoints -v

# Rate limiting only
pytest detail_project/tests/test_phase4_infrastructure.py::TestRateLimitDecorator -v

# API helpers only
pytest detail_project/tests/test_phase4_infrastructure.py::TestAPIResponse -v
```

---

## ✅ STEP 5: Phase 5 Testing Suite (20 minutes)

### 5.1 Integration Tests

```bash
# Run all integration tests
pytest detail_project/tests/test_phase5_integration.py -v

# Expected: 20+ tests, all should pass
```

**Test Categories:**
- ✅ Rate Limiting Integration (6 tests)
- ✅ Transaction Safety (2 tests)
- ✅ Cache Behavior (3 tests)
- ✅ Error Handling (4 tests)
- ✅ Complete User Flows (2 tests)
- ✅ Performance Baselines (3 tests)

### 5.2 Security Tests

```bash
# Run all security tests
pytest detail_project/tests/test_phase5_security.py -v

# Expected: 22+ tests, all should pass
```

**OWASP Coverage:**
- ✅ A01: Broken Access Control (4 tests)
- ✅ A02: Cryptographic Failures (2 tests)
- ✅ A03: Injection (3 tests)
- ✅ A04: Insecure Design (2 tests)
- ✅ A05: Security Misconfiguration (6 tests)
- ✅ A07: Authentication Failures (3 tests)
- ✅ A09: Logging & Monitoring (2 tests)

### 5.3 Run All Tests Together

```bash
# Run all tests with coverage
pytest detail_project/tests/ -v --cov=detail_project --cov-report=html --cov-report=term

# Target: 70%+ coverage
```

---

## ✅ STEP 6: Load Testing with Locust (15 minutes)

### 6.1 Quick Load Test (30 seconds)

```bash
# Start server in one terminal
python manage.py runserver

# In another terminal, run Locust
locust -f detail_project/tests/locustfile.py \
  --host=http://127.0.0.1:8000 \
  --users=10 \
  --spawn-rate=2 \
  --run-time=30s \
  --headless
```

### 6.2 Standard Load Test (5 minutes)

```bash
locust -f detail_project/tests/locustfile.py \
  --host=http://127.0.0.1:8000 \
  --users=50 \
  --spawn-rate=5 \
  --run-time=5m \
  --headless
```

### 6.3 Interactive Load Test

```bash
# Start Locust web UI
locust -f detail_project/tests/locustfile.py \
  --host=http://127.0.0.1:8000

# Open browser: http://localhost:8089
# Configure users and spawn rate
# Click "Start swarming"
```

### 6.4 Expected Metrics

**Target Performance:**
- ✅ p50 response time: < 200ms (read operations)
- ✅ p95 response time: < 500ms (read), < 1000ms (write)
- ✅ Error rate: < 1%
- ✅ Requests per second: 50+ (with 50 users)

---

## ✅ STEP 7: Rate Limiting Verification (10 minutes)

### 7.1 Test Rate Limit on Write Endpoint

Create a test script:

```bash
# Create test_rate_limit.sh
cat > test_rate_limit.sh << 'EOF'
#!/bin/bash
# Test rate limiting on API endpoint

URL="http://127.0.0.1:8000/detail_project/api/save_volume/1/"
COOKIE="sessionid=YOUR_SESSION_ID"

echo "Testing rate limiting (20 requests/min for write)..."

for i in {1..25}; do
  echo -n "Request $i: "
  RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$URL" \
    -H "Cookie: $COOKIE" \
    -H "Content-Type: application/json" \
    -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
    -d '{"volumes": []}')

  echo "HTTP $RESPONSE"

  if [ "$RESPONSE" = "429" ]; then
    echo "✅ Rate limit activated after $i requests!"
    break
  fi

  sleep 1
done
EOF

chmod +x test_rate_limit.sh
```

**Note:** You'll need to:
1. Login to get session ID
2. Get CSRF token from page
3. Update script with real values

### 7.2 Test Different Rate Limit Categories

**Categories:**
- `bulk`: 5 requests per 5 minutes (deep copy)
- `write`: 20 requests per minute (saves)
- `read`: 100 requests per minute (searches)
- `export`: 10 requests per minute (PDF/Excel)

---

## ✅ STEP 8: Monitoring & Metrics Verification (10 minutes)

### 8.1 Enable Monitoring Middleware

Add to `config/settings.py`:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # Add monitoring middleware
    'detail_project.monitoring_middleware.MonitoringMiddleware',
]
```

### 8.2 Test Metrics Collection

```bash
# Make some requests
curl http://127.0.0.1:8000/health/
curl http://127.0.0.1:8000/dashboard/

# Check metrics in Django shell
python manage.py shell
```

```python
from detail_project.monitoring_middleware import get_metrics_summary

# Get metrics summary
metrics = get_metrics_summary()
print(metrics)

# Expected output:
# {
#   'requests_total': 2,
#   'errors_4xx': 0,
#   'errors_5xx': 0,
#   'rate_limit_hits': 0,
#   'error_rate': 0.0
# }
```

### 8.3 Test Logging Configuration

```bash
# Create logs directory
mkdir -p logs

# Add logging config to settings.py
# Then make requests and check logs
tail -f logs/application.log
tail -f logs/errors.log
```

---

## ✅ STEP 9: Frontend Features Test (15 minutes)

### 9.1 Test Loading States

1. Login to application
2. Navigate to a project
3. Try these operations and verify loading indicators:
   - ✅ Save volume data → Should show loading overlay
   - ✅ Save pekerjaan → Should show "Saving..." message
   - ✅ Export to Excel → Should show progress bar
   - ✅ Deep copy project → Should show progress

### 9.2 Test Error Handling

1. Disconnect internet (or stop server)
2. Try to save data
3. Should see:
   - ✅ Error overlay with clear message
   - ✅ "Retry" and "Cancel" buttons
   - ✅ Error details

### 9.3 Test Toast Notifications

Operations should show toast messages:
- ✅ Success: Green toast "Data saved successfully"
- ✅ Error: Red toast with error message
- ✅ Warning: Yellow toast for warnings
- ✅ Info: Blue toast for information

---

## ✅ STEP 10: Production-like Test with Gunicorn (15 minutes)

### 10.1 Test with Gunicorn

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn config.wsgi:application \
  --bind 127.0.0.1:8000 \
  --workers 4 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

### 10.2 Test Rate Limiting with Multiple Workers

```bash
# With multiple workers, rate limiting must use Redis
# Test health check
curl http://127.0.0.1:8000/health/

# Make rapid requests to test rate limiting
for i in {1..25}; do curl -s http://127.0.0.1:8000/health/ -o /dev/null -w "%{http_code}\n"; done
```

---

## 📊 TESTING CHECKLIST

### Phase 4 - Infrastructure ✅
- [ ] Redis installed and running
- [ ] Health check endpoints working
- [ ] API helpers working (APIResponse)
- [ ] Rate limiting working (all categories)
- [ ] All Phase 4 tests passing (36 tests)

### Phase 5 - Testing ✅
- [ ] Integration tests passing (20+ tests)
- [ ] Security tests passing (22+ tests)
- [ ] Load test completed successfully
- [ ] Performance baselines met
- [ ] 70%+ test coverage achieved

### Phase 6 - Monitoring ✅
- [ ] Monitoring middleware enabled
- [ ] Metrics being collected
- [ ] Logs directory created
- [ ] Log files being written
- [ ] Metrics summary working

### Frontend ✅
- [ ] Loading states working
- [ ] Error overlays working
- [ ] Toast notifications working
- [ ] All operations provide feedback

### Production Readiness ✅
- [ ] Gunicorn can start application
- [ ] Multiple workers functioning
- [ ] Rate limiting works across workers
- [ ] No errors in logs
- [ ] All tests passing

---

## 🚨 TROUBLESHOOTING

### Issue: Redis Connection Failed

**Symptoms:**
- Health check shows cache "error"
- Rate limiting not working
- Tests failing with cache errors

**Solution:**
```bash
# Start Redis
docker start redis-ahsp
# OR
sudo systemctl start redis

# Verify
redis-cli ping
```

### Issue: Tests Failing

**Symptoms:**
- pytest shows failures
- Import errors

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt
pip install pytest pytest-django pytest-cov

# Run migrations
python manage.py migrate

# Clear cache
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()
```

### Issue: Rate Limiting Not Working

**Symptoms:**
- Can make unlimited requests
- No 429 errors

**Solution:**
1. Check Redis is running: `redis-cli ping`
2. Check cache config in settings.py
3. Check middleware is enabled
4. Verify decorator is applied to view

### Issue: Monitoring Not Collecting Metrics

**Symptoms:**
- `get_metrics_summary()` returns zeros
- No metrics in cache

**Solution:**
1. Check middleware is in MIDDLEWARE list
2. Check middleware is before other middleware
3. Make some requests first
4. Check Redis is running

---

## 📈 EXPECTED RESULTS SUMMARY

### Test Results
- **Phase 4 Tests**: 36/36 passing ✅
- **Phase 5 Integration**: 20/20 passing ✅
- **Phase 5 Security**: 22/22 passing ✅
- **Total Test Coverage**: 70%+ ✅

### Performance Metrics
- **Response Time p50**: < 200ms ✅
- **Response Time p95**: < 500ms (read), < 1000ms (write) ✅
- **Error Rate**: < 1% ✅
- **Requests/Second**: 50+ (with 50 concurrent users) ✅

### Monitoring Metrics
- **Metrics Collection**: Active ✅
- **Error Tracking**: Ready (Sentry pending) ✅
- **Structured Logging**: Configured ✅
- **Health Checks**: All passing ✅

---

## 🎯 NEXT STEPS AFTER TESTING

### If All Tests Pass ✅

1. **Deploy to Staging**
   ```bash
   ./scripts/deploy-staging.sh
   ```

2. **Run Tests on Staging**
   - Repeat all tests on staging environment
   - Verify with real data

3. **Setup Monitoring**
   - Create Sentry project
   - Configure environment variables
   - Import Grafana dashboards

4. **UAT (User Acceptance Testing)**
   - Invite beta testers
   - Collect feedback
   - Fix any issues

5. **Production Deployment**
   - Follow deployment guide
   - Use deployment script
   - Monitor closely

### If Tests Fail ❌

1. **Identify Root Cause**
   - Check error messages
   - Review logs
   - Use troubleshooting guide

2. **Fix Issues**
   - Make necessary code changes
   - Update tests if needed

3. **Re-run Tests**
   - Verify fixes work
   - Run full test suite

4. **Document Learnings**
   - Update troubleshooting guide
   - Add to known issues

---

## 📞 SUPPORT

For issues or questions:
1. Check this testing guide
2. Check `MONITORING_GUIDE.md`
3. Check `TEST_PHASE4_GUIDE.md`
4. Check `TEST_PHASE5_GUIDE.md`
5. Review deployment guides

---

**Last Updated:** November 7, 2025
**Version:** 1.0
**Status:** Ready for Testing

**Estimated Total Testing Time:** 2-3 hours for complete verification
