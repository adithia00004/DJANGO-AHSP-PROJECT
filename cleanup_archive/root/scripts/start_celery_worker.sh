#!/bin/bash
# Start Celery Worker
#
# PHASE 5: Celery Async Tasks
#
# This script starts a Celery worker to process background tasks.
#
# Usage:
#   ./scripts/start_celery_worker.sh
#
# Options:
#   CONCURRENCY: Number of worker processes (default: 4)
#   LOGLEVEL: Logging level (default: info)

set -e

# Configuration
CONCURRENCY=${CELERY_WORKER_CONCURRENCY:-4}
LOGLEVEL=${CELERY_LOGLEVEL:-info}
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🚀 Starting Celery Worker${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Project Dir: ${YELLOW}${PROJECT_DIR}${NC}"
echo -e "Concurrency: ${YELLOW}${CONCURRENCY}${NC}"
echo -e "Log Level:   ${YELLOW}${LOGLEVEL}${NC}"
echo ""

cd "${PROJECT_DIR}"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# Start Celery worker
echo -e "${GREEN}Starting worker...${NC}"
echo ""

celery -A config worker \
    --loglevel="${LOGLEVEL}" \
    --concurrency="${CONCURRENCY}" \
    --max-tasks-per-child=1000 \
    --time-limit=1800 \
    --soft-time-limit=1500

# Note: Use supervisord or systemd for production deployment
