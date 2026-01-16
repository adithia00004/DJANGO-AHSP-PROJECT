#!/bin/bash
# Start Flower (Celery Monitoring Tool)
#
# PHASE 5: Celery Async Tasks
#
# This script starts Flower web interface for monitoring Celery tasks.
#
# Usage:
#   ./scripts/start_flower.sh
#
# Access:
#   http://localhost:5555
#
# Options:
#   FLOWER_PORT: Port to run Flower (default: 5555)
#   FLOWER_BASIC_AUTH: Basic auth (user:password)

set -e

# Configuration
FLOWER_PORT=${FLOWER_PORT:-5555}
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🌺 Starting Flower (Celery Monitor)${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Project Dir: ${YELLOW}${PROJECT_DIR}${NC}"
echo -e "Port:        ${YELLOW}${FLOWER_PORT}${NC}"
echo -e "Access URL:  ${BLUE}http://localhost:${FLOWER_PORT}${NC}"
echo ""

cd "${PROJECT_DIR}"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# Start Flower
echo -e "${GREEN}Starting Flower...${NC}"
echo ""

if [ -n "${FLOWER_BASIC_AUTH}" ]; then
    echo -e "${YELLOW}Basic auth enabled${NC}"
    celery -A config flower \
        --port="${FLOWER_PORT}" \
        --basic_auth="${FLOWER_BASIC_AUTH}"
else
    echo -e "${YELLOW}No authentication (dev mode)${NC}"
    celery -A config flower \
        --port="${FLOWER_PORT}"
fi

# Note: For production, use:
#   --basic_auth=user:password
#   --url_prefix=/flower  (if behind reverse proxy)
#   --persistent=True  (persistent storage)
