#!/bin/bash
#
# Staging Deployment Script
#
# This script automates the deployment process for staging environment.
# Similar to production but with more verbose logging and relaxed checks.
#
# Usage:
#   ./scripts/deploy-staging.sh
#

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# ============================================================================
# Configuration
# ============================================================================

PROJECT_NAME="ahsp-staging"
PROJECT_DIR="/var/www/ahsp-staging"
VENV_DIR="$PROJECT_DIR/venv"
BACKUP_DIR="/var/backups/ahsp-staging"
LOG_DIR="$PROJECT_DIR/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    if [ ! -d "$PROJECT_DIR" ]; then
        log_error "Project directory not found: $PROJECT_DIR"
        exit 1
    fi

    if [ ! -d "$VENV_DIR" ]; then
        log_error "Virtual environment not found: $VENV_DIR"
        exit 1
    fi

    # Redis check (optional for staging)
    if ! redis-cli ping > /dev/null 2>&1; then
        log_warning "Redis is not running (optional for staging)"
    fi

    log_success "Prerequisites check completed"
}

activate_virtualenv() {
    log_info "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
    log_success "Virtual environment activated"
}

backup_database() {
    log_info "Creating database backup..."

    mkdir -p "$BACKUP_DIR"

    BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql"

    PGPASSWORD=$POSTGRES_PASSWORD pg_dump \
        -h $POSTGRES_HOST \
        -U $POSTGRES_USER \
        -d $POSTGRES_DB \
        -F c \
        -f "$BACKUP_FILE" || log_warning "Backup failed (non-critical)"

    # Keep only last 3 days of backups (staging)
    find "$BACKUP_DIR" -name "db_backup_*.sql" -mtime +3 -delete

    log_success "Database backup completed"
}

pull_latest_code() {
    log_info "Pulling latest code from git..."

    cd "$PROJECT_DIR"

    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    log_info "Current branch: $CURRENT_BRANCH"

    git stash
    git pull origin "$CURRENT_BRANCH"

    COMMIT_HASH=$(git rev-parse --short HEAD)
    COMMIT_MSG=$(git log -1 --pretty=%B)
    log_info "Deployed commit: $COMMIT_HASH"
    log_info "Commit message: $COMMIT_MSG"

    log_success "Code updated successfully"
}

install_dependencies() {
    log_info "Installing/updating Python dependencies..."

    cd "$PROJECT_DIR"

    pip install --upgrade pip
    pip install -r requirements/staging.txt

    log_success "Dependencies installed successfully"
}

run_migrations() {
    log_info "Running database migrations..."

    cd "$PROJECT_DIR"

    PENDING=$(python manage.py showmigrations --plan | grep "\[ \]" | wc -l)

    if [ "$PENDING" -gt 0 ]; then
        log_info "Found $PENDING pending migrations"
        python manage.py migrate --noinput
        log_success "Migrations completed"
    else
        log_info "No pending migrations"
    fi
}

collect_static_files() {
    log_info "Collecting static files..."

    cd "$PROJECT_DIR"

    python manage.py collectstatic --noinput --clear

    log_success "Static files collected"
}

clear_cache() {
    log_info "Clearing Django cache..."

    redis-cli FLUSHDB || log_warning "Cache clear failed (non-critical)"

    log_success "Cache operation completed"
}

restart_services() {
    log_info "Restarting application services..."

    sudo systemctl restart gunicorn-${PROJECT_NAME} || log_error "Gunicorn restart failed"
    sudo systemctl reload nginx || log_error "Nginx reload failed"

    log_info "Waiting for services to start..."
    sleep 3

    log_success "Services restarted"
}

health_check() {
    log_info "Running health check..."

    RETRIES=3
    WAIT_TIME=2

    for i in $(seq 1 $RETRIES); do
        if curl -sf http://localhost:8001/health/ > /dev/null 2>&1; then
            log_success "Health check passed!"
            return 0
        else
            log_warning "Attempt $i/$RETRIES failed, retrying..."
            sleep $WAIT_TIME
        fi
    done

    log_warning "Health check failed (may be expected in staging)"
}

run_tests() {
    log_info "Running automated tests (staging)..."

    cd "$PROJECT_DIR"

    # Run pytest with coverage
    pytest --tb=short --maxfail=5 || log_warning "Some tests failed (non-blocking)"

    log_info "Test run completed"
}

deployment_summary() {
    log_info "========================================="
    log_info "Staging Deployment Summary"
    log_info "========================================="
    log_info "Timestamp: $TIMESTAMP"
    log_info "Branch: $(git rev-parse --abbrev-ref HEAD)"
    log_info "Commit: $(git rev-parse --short HEAD)"
    log_info "Environment: Staging"
    log_info "========================================="
}

# ============================================================================
# Main Deployment Flow
# ============================================================================

main() {
    log_info "========================================="
    log_info "Starting Staging Deployment"
    log_info "========================================="
    log_info "Time: $(date)"
    echo

    check_prerequisites
    echo

    activate_virtualenv
    echo

    backup_database
    echo

    pull_latest_code
    echo

    install_dependencies
    echo

    run_migrations
    echo

    collect_static_files
    echo

    clear_cache
    echo

    restart_services
    echo

    health_check
    echo

    # Optional: Run tests in staging
    # run_tests
    # echo

    deployment_summary
    echo

    log_success "========================================="
    log_success "Staging Deployment Completed!"
    log_success "========================================="
}

# Run main function
main

exit 0
