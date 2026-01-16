## Phase 5: Testing & QA - Comprehensive Guide

Complete testing strategy for Phase 5 including integration tests, load tests, security tests, and user acceptance testing.

---

## 📋 Overview

**Goal:** Ensure production readiness through comprehensive testing

**Duration:** 5-7 days

**Coverage Targets:**
- Integration tests: 70%+ coverage
- Load testing: Support 50+ concurrent users
- Security: OWASP Top 10 compliant
- Performance: p95 < 500ms (read), p95 < 1000ms (write)
- Error rate: < 1%

---

## 1. Integration Testing

### Test Files Created

**`test_phase5_integration.py` (650+ lines)**

### What's Tested

#### 1.1 Rate Limiting Integration
```python
# Test rate limiting with real API endpoints
def test_rate_limit_on_api_save_endpoint(client_logged, project):
    """Test rate limiting blocks excessive save requests."""
    # Make requests up to limit
    # Verify 429 response after limit exceeded
```

**Coverage:**
- Rate limiting enforcement on actual endpoints
- Different limits per user
- Rate limit reset after window
- Retry-after headers

#### 1.2 Transaction Safety
```python
# Test rollback on errors
def test_transaction_rollback_on_error(client_logged, project):
    """Test failed operations rollback properly."""
    # Send invalid data
    # Verify no partial data in database
```

**Coverage:**
- Transaction rollback on validation errors
- select_for_update() prevents race conditions
- Concurrent update serialization

#### 1.3 Cache Behavior
```python
# Test cache operations
def test_cache_stores_rate_limit_data(client_logged, project):
    """Test rate limit data is stored in cache."""
    # Make requests
    # Verify cache keys exist
```

**Coverage:**
- Cache availability
- Rate limit data persistence
- Complex object storage

#### 1.4 Error Handling
```python
# Test error responses
def test_validation_error_returns_proper_response(client_logged, project):
    """Test validation errors return standardized response."""
    # Send invalid payload
    # Verify proper error format
```

**Coverage:**
- Validation errors
- 404 handling
- Authentication rejection
- CSRF protection

#### 1.5 Complete User Flows
```python
# End-to-end testing
def test_complete_pekerjaan_creation_flow(client_logged, project):
    """Test complete flow: create → save → retrieve."""
    # Create via API
    # Save changes
    # Retrieve and verify
```

**Coverage:**
- Full CRUD operations
- Multi-step workflows
- Data consistency

#### 1.6 Performance Baseline
```python
# Baseline performance
def test_list_pekerjaan_tree_response_time(client_logged, project):
    """Test response time is acceptable."""
    # Measure response time
    # Assert < 2 seconds
```

**Coverage:**
- Response time baselines
- Query optimization verification
- Performance regression detection

### Running Integration Tests

```bash
# All integration tests
pytest detail_project/tests/test_phase5_integration.py -v

# With coverage
pytest detail_project/tests/test_phase5_integration.py --cov=detail_project --cov-report=html

# Specific test class
pytest detail_project/tests/test_phase5_integration.py::TestRateLimitingIntegration -v

# Performance tests only
pytest detail_project/tests/test_phase5_integration.py -k "performance" -v

# With timing
pytest detail_project/tests/test_phase5_integration.py --durations=10
```

### Success Criteria

- ✅ All integration tests pass
- ✅ 70%+ code coverage
- ✅ No race conditions detected
- ✅ Transaction rollback works correctly
- ✅ Rate limiting enforced properly
- ✅ Error handling comprehensive

---

## 2. Load Testing

### Test Files Created

**`locustfile.py` (480+ lines)**

### User Types Simulated

#### 2.1 AHSPUser (Regular User)
- View project list
- View list pekerjaan
- Get pekerjaan tree (API)
- Save volume data
- View rekap
- Check health

**Weight:** 10 (most common user type)

#### 2.2 AdminUser (Heavy Operations)
- View dashboard
- Bulk export
- Deep copy projects
- System monitoring

**Weight:** 2 (fewer admin users)

#### 2.3 ReadOnlyUser (Viewer)
- Browse projects frequently
- View details
- Get tree data
- No write operations

**Weight:** 5 (many viewers)

### Running Load Tests

#### Quick Test (Development)
```bash
# 10 users for 30 seconds
locust -f detail_project/tests/locustfile.py \
  --host=http://localhost:8000 \
  --users=10 \
  --spawn-rate=2 \
  --run-time=30s \
  --headless
```

#### Staging Test (Standard)
```bash
# 50 users for 5 minutes
locust -f detail_project/tests/locustfile.py \
  --host=https://staging.example.com \
  --users=50 \
  --spawn-rate=5 \
  --run-time=5m \
  --headless \
  --csv=load_test_results
```

#### Production Stress Test
```bash
# 100 users ramping up over 10 minutes
locust -f detail_project/tests/locustfile.py \
  --host=https://production.example.com \
  --users=100 \
  --spawn-rate=10 \
  --run-time=10m \
  --headless \
  --csv=stress_test_results
```

#### Web UI Mode (Interactive)
```bash
# Start Locust web UI
locust -f detail_project/tests/locustfile.py \
  --host=http://localhost:8000

# Open browser: http://localhost:8089
# Configure users and spawn rate in UI
```

### Target Metrics

| Metric | Target | Critical |
|--------|--------|----------|
| p50 response time | < 200ms | < 500ms |
| p95 response time (read) | < 500ms | < 1000ms |
| p95 response time (write) | < 1000ms | < 2000ms |
| p99 response time | < 2000ms | < 5000ms |
| Error rate | < 0.5% | < 1% |
| Concurrent users | 50+ | 100+ |
| Requests per second | 100+ | 200+ |
| CPU usage | < 70% | < 90% |
| Memory usage | < 2GB | < 4GB |

### Analyzing Results

#### CSV Output
```bash
# Locust generates 3 CSV files:
# - results_stats.csv (request statistics)
# - results_stats_history.csv (timeline)
# - results_failures.csv (failure details)

# View summary
cat results_stats.csv | column -t -s,

# View failures
cat results_failures.csv
```

#### Key Metrics to Check

**Response Times:**
```python
# In results_stats.csv
# Look for "Average", "Median", "95%", "99%"
# Should meet target metrics
```

**Error Rate:**
```python
# Check "Failure Rate" column
# Should be < 1%
# Investigate any errors in results_failures.csv
```

**Rate Limiting:**
```python
# 429 responses are EXPECTED
# Should appear in failures but are "successful" behavior
# Indicates rate limiting is working
```

### Common Issues

**High Response Times:**
- Database queries not optimized
- No connection pooling
- Cache misses
- N+1 query problems

**High Error Rate:**
- Server crashes
- Database connection exhausted
- Memory issues
- Configuration errors

**Rate Limiting Too Strict:**
- Adjust RATE_LIMIT_CATEGORIES
- Increase limits for testing
- Verify cache is working

---

## 3. Security Testing

### Test Files Created

**`test_phase5_security.py` (480+ lines)**

### OWASP Top 10 Coverage

#### 3.1 A01:2021 – Broken Access Control
```python
# Test authentication and authorization
def test_anonymous_user_cannot_access_api(project):
    """Test unauthenticated users are rejected."""
    # Try to access protected endpoint
    # Verify 401/403 response
```

**Tests:**
- Anonymous users rejected
- Users cannot access others' projects
- Health checks are public
- Role-based access control

#### 3.2 A02:2021 – Cryptographic Failures
```python
# Test password security
def test_passwords_are_hashed():
    """Test passwords not stored in plaintext."""
    # Create user
    # Verify password is hashed
```

**Tests:**
- Passwords hashed with strong algorithm
- Session cookies have security flags
- HTTPS enforced in production
- Sensitive data encrypted

#### 3.3 A03:2021 – Injection
```python
# Test SQL injection prevention
def test_sql_injection_via_search(client_logged, project):
    """Test SQL injection attempts blocked."""
    # Send malicious SQL payloads
    # Verify no data leakage
```

**Tests:**
- SQL injection prevented (ORM protection)
- XSS attempts escaped
- Command injection blocked
- Template injection prevented

#### 3.4 A04:2021 – Insecure Design
```python
# Test secure design
def test_rate_limiting_prevents_abuse(client_logged, project):
    """Test rate limiting stops excessive requests."""
    # Make many requests
    # Verify rate limiting kicks in
```

**Tests:**
- Rate limiting enforced
- No sensitive data in errors
- Proper error handling
- Secure defaults

#### 3.5 A05:2021 – Security Misconfiguration
```python
# Test configuration
def test_debug_mode_disabled_in_production():
    """Test DEBUG is False in production."""
    # Check settings.DEBUG
    # Verify secure configuration
```

**Tests:**
- DEBUG=False in production
- SECRET_KEY is strong
- ALLOWED_HOSTS configured
- Security middleware enabled
- CSRF protection active

#### 3.7 A07:2021 – Identification and Authentication Failures
```python
# Test authentication
def test_login_required_on_sensitive_endpoints(project):
    """Test endpoints require authentication."""
    # Try to access without login
    # Verify rejection
```

**Tests:**
- Login required
- Password validation
- Session expiration
- Account lockout (if implemented)

#### 3.9 A09:2021 – Security Logging and Monitoring Failures
```python
# Test logging
def test_health_check_provides_monitoring_data(client):
    """Test health check provides monitoring data."""
    # Call health check
    # Verify comprehensive status
```

**Tests:**
- Failed logins logged
- Security events tracked
- Health check monitoring
- Audit trail

### Running Security Tests

```bash
# All security tests
pytest detail_project/tests/test_phase5_security.py -v

# Specific OWASP category
pytest detail_project/tests/test_phase5_security.py::TestAccessControl -v

# Generate security report
pytest detail_project/tests/test_phase5_security.py \
  --html=security_report.html \
  --self-contained-html

# With markers
pytest -m security -v
```

### Security Checklist

#### Before Production:
- [ ] All security tests pass
- [ ] OWASP Top 10 addressed
- [ ] HTTPS enforced
- [ ] Security headers configured
- [ ] Rate limiting tested
- [ ] Authentication/authorization verified
- [ ] Input validation comprehensive
- [ ] Error messages don't leak data
- [ ] Logging configured
- [ ] Security middleware enabled

#### Production Monitoring:
- [ ] Monitor failed login attempts
- [ ] Track rate limit violations
- [ ] Alert on security events
- [ ] Regular security audits
- [ ] Penetration testing scheduled

---

## 4. Frontend Testing

### Manual Testing Checklist

#### 4.1 Loading States
- [ ] Global loading overlay appears
- [ ] Progress bars work for long operations
- [ ] Inline button loading states
- [ ] Loading can be canceled
- [ ] Multiple concurrent loading states handled
- [ ] Loading disappears on completion
- [ ] Loading disappears on error

#### 4.2 Error Handling
- [ ] Error overlays display properly
- [ ] Error messages are user-friendly (Indonesian)
- [ ] Retry action works
- [ ] Error details available
- [ ] Errors don't crash UI
- [ ] Network errors handled
- [ ] 429 rate limit shown clearly

#### 4.3 Toast Notifications
- [ ] Success toasts appear
- [ ] Error toasts appear
- [ ] Warning toasts appear
- [ ] Info toasts appear
- [ ] Toasts auto-dismiss (except errors)
- [ ] Multiple toasts stack properly
- [ ] Toast close button works

#### 4.4 Accessibility
- [ ] Keyboard navigation works
- [ ] Tab order logical
- [ ] Focus indicators visible
- [ ] ARIA labels present
- [ ] Screen reader compatible
- [ ] Color contrast sufficient
- [ ] Text scalable

#### 4.5 Cross-Browser Testing
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Mobile Chrome
- [ ] Mobile Safari

#### 4.6 Mobile Responsiveness
- [ ] Layout adapts to mobile
- [ ] Buttons touchable (44x44px min)
- [ ] Forms usable on mobile
- [ ] Loading states visible
- [ ] Toasts positioned correctly
- [ ] No horizontal scroll

### Automated Frontend Testing (Future)

```javascript
// Example with Playwright
test('loading state appears on save', async ({ page }) => {
  await page.click('#save-button');
  await expect(page.locator('.dp-loading-overlay')).toBeVisible();
});

test('error overlay shows on failure', async ({ page }) => {
  // Simulate network error
  await page.route('**/api/save/**', route => route.abort());

  await page.click('#save-button');
  await expect(page.locator('.dp-error-overlay')).toBeVisible();
});
```

---

## 5. User Acceptance Testing (UAT)

### UAT Plan

#### 5.1 Recruit Beta Testers (3-5 users)
- Project managers
- Site engineers
- Estimators
- Admins
- Viewers

#### 5.2 UAT Scenarios

**Scenario 1: Create New Project**
1. Login to system
2. Navigate to dashboard
3. Click "Create Project"
4. Fill in project details
5. Save project
6. Verify project appears in list

**Expected:** Success with loading indicator

**Scenario 2: Add Pekerjaan Items**
1. Open existing project
2. Navigate to List Pekerjaan
3. Add new items
4. Save changes
5. Verify items saved

**Expected:** Loading state, success toast

**Scenario 3: Update Volumes**
1. Open project
2. Navigate to Volume page
3. Edit quantities
4. Save multiple items
5. Verify calculations update

**Expected:** Batch save works, loading shown

**Scenario 4: Generate Reports**
1. Open project
2. Navigate to Rekap
3. Click export PDF/Excel
4. Wait for download
5. Verify report content

**Expected:** Progress bar, successful download

**Scenario 5: Handle Errors Gracefully**
1. Disconnect internet
2. Try to save changes
3. See error message
4. Reconnect internet
5. Click retry
6. Verify save succeeds

**Expected:** Clear error, retry works

#### 5.3 Feedback Collection

**Feedback Form:**
```markdown
# UAT Feedback Form

## Tester Information
- Name:
- Role:
- Date:

## Scenarios Tested
- [ ] Scenario 1: Create Project
- [ ] Scenario 2: Add Pekerjaan
- [ ] Scenario 3: Update Volumes
- [ ] Scenario 4: Generate Reports
- [ ] Scenario 5: Error Handling

## Ratings (1-5)
- Ease of use: ___
- Loading indicators: ___
- Error messages: ___
- Overall experience: ___

## Issues Found
1.
2.
3.

## Suggestions
1.
2.
3.

## Would you recommend this system?
[ ] Yes [ ] No [ ] Maybe

## Additional Comments:
```

#### 5.4 Issue Tracking

**Priority Levels:**
- **P0 (Critical)**: System crashes, data loss, security issues
- **P1 (High)**: Major functionality broken, poor UX
- **P2 (Medium)**: Minor bugs, cosmetic issues
- **P3 (Low)**: Nice-to-have improvements

**Fix P0 immediately, P1 before launch, P2/P3 can be deferred**

---

## 6. Test Execution Schedule

### Week Schedule

**Day 1-2: Integration Testing**
- Run all integration tests
- Fix failures
- Achieve 70%+ coverage
- Document issues

**Day 2-3: Load Testing**
- Setup load testing environment
- Run quick tests (10 users)
- Run standard tests (50 users)
- Run stress tests (100 users)
- Analyze results
- Optimize bottlenecks

**Day 3-4: Security Testing**
- Run all security tests
- Manual penetration testing
- Review security configuration
- Fix vulnerabilities
- Re-test

**Day 4-5: Frontend Testing**
- Manual testing checklist
- Cross-browser testing
- Mobile testing
- Accessibility testing
- Fix UI issues

**Day 5-7: User Acceptance Testing**
- Recruit testers
- Provide UAT scenarios
- Collect feedback
- Fix critical issues
- Re-test with users
- Get sign-off

---

## 7. Success Criteria

### Phase 5 Complete When:

- ✅ Integration tests: 70%+ coverage, all pass
- ✅ Load tests: Support 50+ users, p95 < 1000ms
- ✅ Security tests: OWASP Top 10 compliant
- ✅ Frontend tests: All browsers/devices work
- ✅ UAT: 3+ testers, 80%+ satisfaction
- ✅ Critical issues (P0/P1): All fixed
- ✅ Documentation: Complete and accurate
- ✅ Performance: Meets or exceeds targets
- ✅ Error rate: < 1%
- ✅ Sign-off: Stakeholders approve

---

## 8. Tools & Dependencies

### Install Testing Tools

```bash
# Integration & security tests
pip install pytest pytest-django pytest-cov

# Load testing
pip install locust

# Code quality
pip install black flake8 pylint

# Coverage reporting
pip install coverage pytest-html
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Phase 5 Tests

on: [push, pull_request]

jobs:
  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run integration tests
        run: pytest detail_project/tests/test_phase5_integration.py -v

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run security tests
        run: pytest detail_project/tests/test_phase5_security.py -v

  load:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run load tests
        run: |
          locust -f detail_project/tests/locustfile.py \
            --host=http://localhost:8000 \
            --users=10 --spawn-rate=2 --run-time=30s \
            --headless --csv=results
```

---

## 9. Reporting

### Generate Test Reports

```bash
# HTML coverage report
pytest detail_project/tests/test_phase5*.py \
  --cov=detail_project \
  --cov-report=html \
  --html=test_report.html \
  --self-contained-html

# XML for CI/CD
pytest --cov=detail_project --cov-report=xml --junitxml=junit.xml

# Terminal report
pytest --cov=detail_project --cov-report=term-missing
```

### Test Summary Template

```markdown
# Phase 5 Testing Summary

## Date: [Date]
## Tester: [Name]

### Integration Tests
- Total: XX tests
- Passed: XX (XX%)
- Failed: XX
- Coverage: XX%

### Load Tests
- Users: XX concurrent
- Duration: XX minutes
- p95 Response Time: XXXms
- Error Rate: X.X%
- Status: PASS/FAIL

### Security Tests
- Total: XX tests
- Passed: XX
- Vulnerabilities: X
- Status: PASS/FAIL

### UAT
- Testers: X
- Scenarios: X/X passed
- Satisfaction: XX%
- Critical Issues: X

### Overall Status
[ ] READY FOR PRODUCTION
[ ] NEEDS WORK
[ ] BLOCKED

### Next Steps
1.
2.
3.
```

---

## 10. Troubleshooting

### Common Issues

**Integration Tests Fail:**
- Check database is running
- Check Redis is running
- Clear cache before tests
- Check test fixtures

**Load Tests Show High Response Times:**
- Check database connection pool
- Enable query optimization
- Check Redis cache hit rate
- Review Gunicorn worker count

**Security Tests Fail:**
- Review Django settings
- Check middleware configuration
- Verify HTTPS in production
- Review authentication setup

**UAT Issues:**
- Provide clear instructions
- Be available for questions
- Document all feedback
- Prioritize fixes

---

## 11. Next Phase

After Phase 5 completion:

**Phase 6: Monitoring & Observability**
- Setup Sentry for error tracking
- Configure Prometheus/Grafana
- Implement custom metrics
- Setup alerts
- Create dashboards

---

**Last Updated:** 2025-11-07
**Phase Status:** In Progress
**Target Completion:** 7 days from start
