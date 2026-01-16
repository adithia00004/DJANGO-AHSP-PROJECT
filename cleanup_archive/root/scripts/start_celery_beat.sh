#!/bin/bash
# Start Celery Beat (Scheduler)
#
# PHASE 5: Celery Async Tasks
#
# This script starts Celery Beat to schedule periodic tasks.
#
# Usage:
#   ./scripts/start_celery_beat.sh
#
# Options:
#   LOGLEVEL: Logging level (default: info)

set -e

# Configuration
LOGLEVEL=${CELERY_LOGLEVEL:-info}
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}⏰ Starting Celery Beat (Scheduler)${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Project Dir: ${YELLOW}${PROJECT_DIR}${NC}"
echo -e "Log Level:   ${YELLOW}${LOGLEVEL}${NC}"
echo ""

cd "${PROJECT_DIR}"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# Remove old beat schedule file
if [ -f "celerybeat-schedule" ]; then
    echo -e "${YELLOW}Removing old schedule file...${NC}"
    rm -f celerybeat-schedule
fi

# Start Celery beat
echo -e "${GREEN}Starting beat scheduler...${NC}"
echo ""

celery -A config beat \
    --loglevel="${LOGLEVEL}" \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Note: Use supervisord or systemd for production deployment
# Note: Install django-celery-beat for database-backed scheduler:
#       pip install django-celery-beat
