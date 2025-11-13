#!/bin/bash
# Quick test runner for weekly canonical storage validation tests

echo "========================================="
echo "Weekly Canonical Storage - Test Runner"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest is not installed${NC}"
    echo "Install it with: pip install pytest pytest-django"
    exit 1
fi

# Run tests based on argument
case "$1" in
    "validation")
        echo -e "${YELLOW}Running Backend Validation Tests...${NC}"
        pytest detail_project/tests/test_weekly_canonical_validation.py::TestProgressValidation -v
        ;;
    "daily")
        echo -e "${YELLOW}Running Daily Mode Input Tests...${NC}"
        pytest detail_project/tests/test_weekly_canonical_validation.py::TestDailyModeInput -v
        ;;
    "monthly")
        echo -e "${YELLOW}Running Monthly Mode Input Tests...${NC}"
        pytest detail_project/tests/test_weekly_canonical_validation.py::TestMonthlyModeInput -v
        ;;
    "api")
        echo -e "${YELLOW}Running API V2 Endpoint Tests...${NC}"
        pytest detail_project/tests/test_weekly_canonical_validation.py::TestAPIV2Endpoints -v
        ;;
    "integration")
        echo -e "${YELLOW}Running Integration Tests...${NC}"
        pytest detail_project/tests/test_weekly_canonical_validation.py::TestIntegrationE2E -v
        ;;
    "coverage")
        echo -e "${YELLOW}Running All Tests with Coverage...${NC}"
        pytest detail_project/tests/test_weekly_canonical_validation.py \
            --cov=detail_project.views_api_tahapan_v2 \
            --cov=detail_project.progress_utils \
            --cov-report=html \
            --cov-report=term-missing \
            -v
        echo ""
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    "quick")
        echo -e "${YELLOW}Running Quick Smoke Tests...${NC}"
        pytest detail_project/tests/test_weekly_canonical_validation.py \
            -k "test_valid_progress_100_percent or test_invalid_progress_over_100_percent or test_weekly_input_mode_switch_lossless" \
            -v
        ;;
    "workflow3")
        echo -e "${YELLOW}Running Workflow 3 Pages Integration Suite...${NC}"
        PYTEST_ADDOPTS="--no-cov" pytest detail_project/tests/test_template_ahsp_bundle.py -v && \
        PYTEST_ADDOPTS="--no-cov" pytest detail_project/tests/test_page_interactions_comprehensive.py -v
        ;;
    *)
        echo -e "${YELLOW}Running All Validation Tests...${NC}"
        pytest detail_project/tests/test_weekly_canonical_validation.py -v
        ;;
esac

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
