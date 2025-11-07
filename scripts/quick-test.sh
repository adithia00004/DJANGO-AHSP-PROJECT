#!/bin/bash
# Quick Test Script - AHSP Detail Project
# Tests basic functionality and verifies Phase 4-6 implementations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Header
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  AHSP Detail Project - Quick Test Suite                   ║${NC}"
echo -e "${BLUE}║  Testing Phases 4-6 Implementation                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        return 1
    fi
}

# Function to print step
print_step() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}▶ STEP $1: $2${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Track test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# ============================================================================
# STEP 1: Check Prerequisites
# ============================================================================
print_step 1 "Checking Prerequisites"

echo -n "Checking Python version... "
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}$PYTHON_VERSION${NC}"
TOTAL_TESTS=$((TOTAL_TESTS + 1))
PASSED_TESTS=$((PASSED_TESTS + 1))

echo -n "Checking if virtual environment is activated... "
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo -e "${GREEN}Yes ($(basename $VIRTUAL_ENV))${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${YELLOW}No (not activated, but might be okay)${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
fi

echo -n "Checking Redis connection... "
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}Connected ✅${NC}"
    REDIS_OK=1
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}Not connected ❌${NC}"
    echo -e "${YELLOW}⚠️  WARNING: Redis is required for rate limiting!${NC}"
    echo -e "${YELLOW}   Install with: docker run -d -p 6379:6379 --name redis-ahsp redis:7-alpine${NC}"
    echo -e "${YELLOW}   Or run: ./scripts/setup-redis.sh docker${NC}"
    REDIS_OK=0
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

echo -n "Checking Django installation... "
if python -c "import django" 2>/dev/null; then
    DJANGO_VERSION=$(python -c "import django; print(django.get_version())")
    echo -e "${GREEN}$DJANGO_VERSION${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}Not installed ❌${NC}"
    echo "Run: pip install -r requirements.txt"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    FAILED_TESTS=$((FAILED_TESTS + 1))
    exit 1
fi

# ============================================================================
# STEP 2: Check Database
# ============================================================================
print_step 2 "Checking Database"

echo -n "Checking database migrations... "
if python manage.py showmigrations --plan | grep -q "\[X\]"; then
    echo -e "${GREEN}Migrations applied${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${YELLOW}No migrations applied${NC}"
    echo "Run: python manage.py migrate"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
fi

# ============================================================================
# STEP 3: Test Health Check Endpoints
# ============================================================================
print_step 3 "Testing Health Check Endpoints"

echo "Starting Django development server in background..."
python manage.py runserver 8001 > /dev/null 2>&1 &
SERVER_PID=$!
echo -e "${GREEN}Server started (PID: $SERVER_PID)${NC}"

# Wait for server to start
echo -n "Waiting for server to be ready..."
sleep 3
echo -e " ${GREEN}Ready${NC}"

# Test full health check
echo -n "Testing /health/ endpoint... "
HEALTH_RESPONSE=$(curl -s http://127.0.0.1:8001/health/)
if echo "$HEALTH_RESPONSE" | grep -q '"status"'; then
    echo -e "${GREEN}Success ✅${NC}"
    echo "  Response: $(echo $HEALTH_RESPONSE | jq -c '.status,.checks.database.status,.checks.cache.status' 2>/dev/null || echo $HEALTH_RESPONSE)"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}Failed ❌${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test simple health check
echo -n "Testing /health/simple/ endpoint... "
SIMPLE_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/health/simple/)
if [ "$SIMPLE_RESPONSE" = "200" ]; then
    echo -e "${GREEN}Success (HTTP $SIMPLE_RESPONSE) ✅${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}Failed (HTTP $SIMPLE_RESPONSE) ❌${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test readiness check
echo -n "Testing /health/ready/ endpoint... "
READY_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/health/ready/)
if [ "$READY_RESPONSE" = "200" ]; then
    echo -e "${GREEN}Success (HTTP $READY_RESPONSE) ✅${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}Failed (HTTP $READY_RESPONSE) ❌${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test liveness check
echo -n "Testing /health/live/ endpoint... "
LIVE_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/health/live/)
if [ "$LIVE_RESPONSE" = "200" ]; then
    echo -e "${GREEN}Success (HTTP $LIVE_RESPONSE) ✅${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}Failed (HTTP $LIVE_RESPONSE) ❌${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Stop server
echo "Stopping development server..."
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true
echo -e "${GREEN}Server stopped${NC}"

# ============================================================================
# STEP 4: Run Phase 4 Tests
# ============================================================================
print_step 4 "Running Phase 4 Infrastructure Tests"

if [ -f "detail_project/tests/test_phase4_infrastructure.py" ]; then
    echo "Running Phase 4 test suite..."

    # Check if pytest is installed
    if ! command -v pytest &> /dev/null; then
        echo -e "${YELLOW}pytest not installed. Installing...${NC}"
        pip install pytest pytest-django pytest-cov -q
    fi

    # Run tests
    if pytest detail_project/tests/test_phase4_infrastructure.py -v --tb=short 2>&1 | tee /tmp/phase4_tests.log; then
        PHASE4_PASSED=$(grep -c "PASSED" /tmp/phase4_tests.log || echo 0)
        PHASE4_FAILED=$(grep -c "FAILED" /tmp/phase4_tests.log || echo 0)

        echo ""
        echo -e "${GREEN}Phase 4 Tests: $PHASE4_PASSED passed, $PHASE4_FAILED failed${NC}"

        TOTAL_TESTS=$((TOTAL_TESTS + PHASE4_PASSED + PHASE4_FAILED))
        PASSED_TESTS=$((PASSED_TESTS + PHASE4_PASSED))
        FAILED_TESTS=$((FAILED_TESTS + PHASE4_FAILED))
    else
        echo -e "${RED}Phase 4 tests failed to run${NC}"
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    echo -e "${YELLOW}Phase 4 test file not found (skipping)${NC}"
fi

# ============================================================================
# STEP 5: Test Monitoring Middleware
# ============================================================================
print_step 5 "Testing Monitoring Infrastructure"

echo -n "Checking monitoring middleware file... "
if [ -f "detail_project/monitoring_middleware.py" ]; then
    echo -e "${GREEN}Found ✅${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}Not found ❌${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

echo -n "Checking Sentry config file... "
if [ -f "config/sentry_config.py" ]; then
    echo -e "${GREEN}Found ✅${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}Not found ❌${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

echo -n "Checking logging config file... "
if [ -f "config/logging_config.py" ]; then
    echo -e "${GREEN}Found ✅${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}Not found ❌${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

echo -n "Checking Grafana dashboard template... "
if [ -f "monitoring/grafana-dashboard-example.json" ]; then
    echo -e "${GREEN}Found ✅${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}Not found ❌${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

echo -n "Checking alert rules... "
if [ -f "monitoring/alert-rules.yml" ]; then
    echo -e "${GREEN}Found ✅${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}Not found ❌${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# ============================================================================
# FINAL SUMMARY
# ============================================================================
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                     TEST SUMMARY                           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "Total Tests:  ${BLUE}$TOTAL_TESTS${NC}"
echo -e "Passed:       ${GREEN}$PASSED_TESTS ✅${NC}"
echo -e "Failed:       ${RED}$FAILED_TESTS ❌${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  🎉 ALL TESTS PASSED! System is ready!                    ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "  1. Run full test suite: pytest detail_project/tests/ -v"
    echo "  2. Run load tests: locust -f detail_project/tests/locustfile.py"
    echo "  3. Check TESTING_PLAN.md for comprehensive testing"
    echo "  4. Deploy to staging: ./scripts/deploy-staging.sh"
    echo ""
    exit 0
else
    echo ""
    echo -e "${YELLOW}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  ⚠️  SOME TESTS FAILED - Review errors above              ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Troubleshooting:${NC}"
    echo "  1. Check Redis is running: redis-cli ping"
    echo "  2. Install dependencies: pip install -r requirements.txt"
    echo "  3. Run migrations: python manage.py migrate"
    echo "  4. See TESTING_PLAN.md for detailed troubleshooting"
    echo ""

    if [ $REDIS_OK -eq 0 ]; then
        echo -e "${RED}⚠️  CRITICAL: Redis is not running!${NC}"
        echo "   This is required for rate limiting and caching."
        echo "   Start Redis with: docker run -d -p 6379:6379 --name redis-ahsp redis:7-alpine"
        echo ""
    fi

    exit 1
fi
