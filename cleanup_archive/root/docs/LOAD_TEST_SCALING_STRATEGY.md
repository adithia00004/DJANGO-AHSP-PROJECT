# 🚀 Load Testing Scaling Strategy

## Executive Summary

This document outlines a **systematic approach** to load testing the Django AHSP application from current baseline (10 users) up to production-scale (1000+ users).

**Key Principle:** Incremental testing with clear success criteria at each level.

---

## 🎯 Testing Philosophy

### Why NOT Jump to 1000 Users Immediately?

1. **Lack of Diagnostic Data:**
   - System crashes without useful information
   - Can't pinpoint which component failed first

2. **Resource Waste:**
   - May need to run test 10+ times to find sweet spot
   - Each failed test = wasted time

3. **No Baseline for Comparison:**
   - Don't know when performance started degrading
   - Can't measure incremental improvements

### The Right Approach: **Incremental Load Testing**

```
10 users ✅ → 30 users → 50 users → 100 users → 200 users → 500 users → 1000 users
   |           |           |           |            |            |            |
Baseline   Light Load  Medium Load  Heavy Load  Stress Test  Peak Load  Ultimate Test
```

**At each level:**
- Measure performance metrics
- Identify bottlenecks
- Optimize if needed
- Validate fixes before scaling further

---

## 📈 Scaling Test Plan

### Phase 1: Baseline ✅ (COMPLETED)

**Configuration:**
```bash
Users: 10
Spawn Rate: 2/sec
Duration: 60s
```

**Results:**
- ✅ 100% success rate
- ✅ Median response time: 150ms
- ✅ P95: 300ms (non-auth)
- ✅ All endpoints working

**Status:** PASS - Ready for Phase 2

---

### Phase 2: Light Load (3x Scale)

**Configuration:**
```bash
locust -f load_testing/locustfile.py --headless \
  -u 30 \
  -r 3 \
  -t 180s \
  --host=http://localhost:8000 \
  --csv=hasil_test_30users \
  --html=hasil_test_30users.html
```

**Success Criteria:**
- ✅ Success rate > 99%
- ✅ P95 response time < 500ms (non-auth endpoints)
- ✅ P99 response time < 1000ms
- ✅ No server errors (5xx)
- ✅ Database connections < 80% of pool

**What to Monitor:**
- Database query times
- Connection pool usage
- CPU utilization
- Memory usage

**Expected Bottlenecks:** None (system should handle easily)

**Action if FAIL:**
- Check database connection pool settings
- Review slow queries
- Check for N+1 query problems

---

### Phase 3: Medium Load (5x Scale)

**Configuration:**
```bash
locust -f load_testing/locustfile.py --headless \
  -u 50 \
  -r 5 \
  -t 300s \
  --host=http://localhost:8000 \
  --csv=hasil_test_50users \
  --html=hasil_test_50users.html
```

**Success Criteria:**
- ✅ Success rate > 98%
- ✅ P95 response time < 750ms
- ✅ P99 response time < 1500ms
- ✅ No timeouts
- ✅ Error rate < 2%

**What to Monitor:**
- First signs of database contention
- Session storage performance
- Static file serving
- API response time degradation

**Expected Bottlenecks:**
- Chart-data endpoint may slow down (already 750ms at 10 users)
- Database queries may start queueing

**Optimization Opportunities:**
1. Add Redis caching for chart data
2. Optimize database indexes
3. Enable query result caching
4. Consider database connection pooling tuning

---

### Phase 4: Heavy Load (10x Scale)

**Configuration:**
```bash
locust -f load_testing/locustfile.py --headless \
  -u 100 \
  -r 10 \
  -t 300s \
  --host=http://localhost:8000 \
  --csv=hasil_test_100users \
  --html=hasil_test_100users.html
```

**Success Criteria:**
- ✅ Success rate > 95%
- ✅ P95 response time < 1000ms
- ✅ P99 response time < 2000ms
- ⚠️ Some degradation acceptable
- ✅ No crashes or complete failures

**What to Monitor:**
- Database connection pool saturation
- CPU usage approaching limits
- Memory pressure
- Response time distribution shift

**Expected Bottlenecks:**
- Database becomes primary bottleneck
- Connection pool exhaustion possible
- CPU may spike on complex queries
- Session storage may struggle

**Required Optimizations:**
1. **Database:**
   - Increase connection pool size
   - Add read replicas if needed
   - Implement query caching

2. **Application:**
   - Add Redis for session storage
   - Enable Django cache framework
   - Optimize ORM queries

3. **Infrastructure:**
   - Consider horizontal scaling (multiple app servers)
   - Load balancer setup

---

### Phase 5: Stress Test (20x Scale)

**Configuration:**
```bash
locust -f load_testing/locustfile.py --headless \
  -u 200 \
  -r 20 \
  -t 300s \
  --host=http://localhost:8000 \
  --csv=hasil_test_200users \
  --html=hasil_test_200users.html
```

**Success Criteria:**
- ⚠️ Success rate > 90% (degradation expected)
- ⚠️ P95 response time < 2000ms
- ⚠️ System remains responsive (no crash)
- ✅ Graceful degradation (slow but functional)

**Goal:** Find the breaking point

**What to Monitor:**
- When does success rate drop below 90%?
- Which endpoint fails first?
- What error types occur?
- Resource exhaustion patterns

**Expected Outcome:**
- System will start showing strain
- Some requests may timeout
- Errors will increase
- Clear bottleneck identification

---

### Phase 6: Peak Load (50x Scale)

**Configuration:**
```bash
locust -f load_testing/locustfile.py --headless \
  -u 500 \
  -r 50 \
  -t 300s \
  --host=http://localhost:8000 \
  --csv=hasil_test_500users \
  --html=hasil_test_500users.html
```

**Success Criteria:**
- ⚠️ Success rate > 80% (heavy degradation)
- ⚠️ System doesn't crash completely
- ✅ Recovery after load decreases

**Prerequisites:**
- Must pass Phase 5 with > 90% success
- Must implement optimizations from Phase 4
- Infrastructure improvements in place

**Expected Requirements:**
- Multiple application servers (horizontal scaling)
- Database read replicas
- Redis cluster for caching
- Load balancer with health checks
- CDN for static assets

---

### Phase 7: Ultimate Test (100x Scale)

**Configuration:**
```bash
locust -f load_testing/locustfile.py --headless \
  -u 1000 \
  -r 100 \
  -t 300s \
  --host=http://your-loadbalancer:8000 \
  --csv=hasil_test_1000users \
  --html=hasil_test_1000users.html
```

**Success Criteria:**
- ⚠️ Success rate > 70%
- ✅ Core functionality remains available
- ✅ No data corruption
- ✅ System recovers after test

**Prerequisites:**
- Production-grade infrastructure
- Horizontal scaling implemented
- Database optimization complete
- Caching layers in place
- Monitoring and alerting active

**Required Infrastructure:**
```
Load Balancer
    ↓
[App Server 1] [App Server 2] [App Server 3] ... [App Server N]
    ↓              ↓              ↓
Database Primary + Read Replicas
    ↓
Redis Cache Cluster
```

---

## 🔧 Optimization Roadmap

### After Each Phase, Consider:

#### Database Optimizations:
```python
# settings.py
DATABASES = {
    'default': {
        'CONN_MAX_AGE': 600,  # Connection pooling
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# Add indexes to frequently queried fields
class Pekerjaan(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['project', 'ordering_index']),
            models.Index(fields=['project', 'sub_klasifikasi']),
        ]
```

#### Caching Strategy:
```python
# Cache heavy endpoints
from django.core.cache import cache

def get_chart_data(project_id):
    cache_key = f'chart_data_{project_id}'
    data = cache.get(cache_key)
    if not data:
        data = expensive_chart_calculation()
        cache.set(cache_key, data, timeout=300)  # 5 minutes
    return data
```

#### Query Optimization:
```python
# Use select_related and prefetch_related
pekerjaan_list = Pekerjaan.objects.filter(
    project=project
).select_related(
    'sub_klasifikasi',
    'sub_klasifikasi__klasifikasi'
).prefetch_related(
    'detailahspproject_set__harga_item'
)
```

---

## 📊 Data Complexity Strategy

### Current: Baseline Projects
- Project IDs: [160, 161, 163, 139, 162]
- Complexity: Unknown

### Recommendation: Test with Varied Complexity

**Small Project (Baseline):**
- 10-50 pekerjaan
- 100-500 detail AHSP
- Simple structure

**Medium Project:**
- 100-200 pekerjaan
- 1000-2000 detail AHSP
- Moderate nesting

**Large Project (Stress Test):**
- 500+ pekerjaan
- 5000+ detail AHSP
- Deep nesting (5+ levels)

**Strategy:**
```python
# Update locustfile.py
TEST_PROJECT_IDS = [
    160,  # Small project
    161,  # Medium project
    163,  # Large project
    139,  # Extra large project
    162,  # Complex structure project
]
```

**Test Progression:**
1. Phase 1-3: All projects (mixed complexity)
2. Phase 4-5: Focus on large projects
3. Phase 6-7: Worst-case scenario (largest project)

---

## 🎯 Key Metrics to Track

### Performance Metrics:

| Metric | Baseline | Light | Medium | Heavy | Stress |
|--------|----------|-------|--------|-------|--------|
| **Success Rate** | 100% | >99% | >98% | >95% | >90% |
| **P50 Response** | 150ms | <200ms | <300ms | <500ms | <1000ms |
| **P95 Response** | 300ms | <500ms | <750ms | <1000ms | <2000ms |
| **P99 Response** | 2200ms | <1000ms | <1500ms | <2000ms | <3000ms |
| **Error Rate** | 0% | <1% | <2% | <5% | <10% |

### System Metrics:

| Resource | Safe | Warning | Critical |
|----------|------|---------|----------|
| **CPU** | <60% | 60-80% | >80% |
| **Memory** | <70% | 70-85% | >85% |
| **DB Connections** | <70% | 70-90% | >90% |
| **Disk I/O** | <70% | 70-85% | >85% |

---

## 🚀 Quick Start Commands

### Create Test Script:

```bash
# Create automated test runner
cat > run_scaling_tests.bat << 'EOF'
@echo off
echo ============================================================================
echo SCALING TEST SUITE - Django AHSP Application
echo ============================================================================

echo.
echo Phase 2: Light Load (30 users)
echo ----------------------------------------
locust -f load_testing/locustfile.py --headless -u 30 -r 3 -t 180s --host=http://localhost:8000 --csv=hasil_test_30users --html=hasil_test_30users.html
if %errorlevel% neq 0 goto :error

echo.
echo Phase 3: Medium Load (50 users)
echo ----------------------------------------
locust -f load_testing/locustfile.py --headless -u 50 -r 5 -t 300s --host=http://localhost:8000 --csv=hasil_test_50users --html=hasil_test_50users.html
if %errorlevel% neq 0 goto :error

echo.
echo Phase 4: Heavy Load (100 users)
echo ----------------------------------------
locust -f load_testing/locustfile.py --headless -u 100 -r 10 -t 300s --host=http://localhost:8000 --csv=hasil_test_100users --html=hasil_test_100users.html
if %errorlevel% neq 0 goto :error

echo.
echo ============================================================================
echo ALL TESTS COMPLETED SUCCESSFULLY
echo ============================================================================
goto :end

:error
echo.
echo ============================================================================
echo TEST FAILED - Stopping test suite
echo ============================================================================

:end
EOF
```

---

## 📋 Pre-Test Checklist

Before running scaling tests:

### Application:
- [ ] Latest code deployed
- [ ] Migrations applied
- [ ] Static files collected
- [ ] Debug mode OFF (`DEBUG=False`)
- [ ] Logging configured properly

### Database:
- [ ] Indexes created
- [ ] Connection pool configured
- [ ] Vacuum/optimize run (if PostgreSQL/MySQL)
- [ ] Backup taken

### Infrastructure:
- [ ] Sufficient disk space
- [ ] Monitoring enabled (CPU, Memory, Disk)
- [ ] Database monitoring enabled
- [ ] Network bandwidth adequate

### Test Environment:
- [ ] Locust installed and updated
- [ ] Test data prepared (projects with varied complexity)
- [ ] Test users validated
- [ ] Results directory created

---

## 📈 Results Analysis Template

After each test phase:

### 1. Success Metrics:
- Success rate: ____%
- P95 response time: ____ms
- Error rate: ____%
- Status: PASS / FAIL

### 2. Bottlenecks Identified:
- Primary: ________________
- Secondary: ______________
- Tertiary: _______________

### 3. System Resources:
- Peak CPU: ____%
- Peak Memory: ____%
- Peak DB Connections: ____
- Disk I/O Wait: ____%

### 4. Action Items:
1. [ ] ___________________
2. [ ] ___________________
3. [ ] ___________________

### 5. Ready for Next Phase?
- [ ] YES - All criteria met
- [ ] NO - Optimizations needed

---

## ✅ Conclusion

**Recommended Approach:**

1. ✅ Start with 30 users (Phase 2)
2. ✅ Analyze results, optimize if needed
3. ✅ Progress to 50 users (Phase 3)
4. ✅ Continue incrementally
5. ⚠️ Don't skip phases!

**DON'T:**
- ❌ Jump directly to 1000 users
- ❌ Increase complexity and load simultaneously
- ❌ Ignore warning signs at lower loads
- ❌ Skip optimization between phases

**DO:**
- ✅ Test incrementally
- ✅ Optimize at each plateau
- ✅ Monitor system resources
- ✅ Document bottlenecks
- ✅ Validate fixes before scaling

---

**Good luck with your scaling tests!** 🚀

Remember: **Slow and steady finds the bottlenecks.**
