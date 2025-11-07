#!/bin/bash
#
# Production Deployment Script
#
# This script automates the deployment process for production environment.
# It performs health checks, database migrations, static file collection,
# and graceful service restart.
#
# Usage:
#   ./scripts/deploy-production.sh
#
# Prerequisites:
#   - SSH access to production server
#   - Environment variables configured
#   - Gunicorn systemd service configured
#   - Nginx configured as reverse proxy
#   - Redis running
#   - PostgreSQL database accessible
#

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# ============================================================================
# Configuration
# ============================================================================

PROJECT_NAME="ahsp"
PROJECT_DIR="/var/www/ahsp"
VENV_DIR="$PROJECT_DIR/venv"
BACKUP_DIR="/var/backups/ahsp"
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

    # Check if running as correct user
    if [ "$EUID" -eq 0 ]; then
        log_error "Do not run this script as root! Run as the app user."
        exit 1
    fi

    # Check if project directory exists
    if [ ! -d "$PROJECT_DIR" ]; then
        log_error "Project directory not found: $PROJECT_DIR"
        exit 1
    fi

    # Check if virtual environment exists
    if [ ! -d "$VENV_DIR" ]; then
        log_error "Virtual environment not found: $VENV_DIR"
        exit 1
    fi

    # Check if Redis is running
    if ! redis-cli ping > /dev/null 2>&1; then
        log_error "Redis is not running! Start Redis first."
        exit 1
    fi

    # Check if PostgreSQL is accessible
    if ! PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1" > /dev/null 2>&1; then
        log_error "Cannot connect to PostgreSQL database!"
        exit 1
    fi

    log_success "All prerequisites passed"
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
        -f "$BACKUP_FILE"

    if [ $? -eq 0 ]; then
        log_success "Database backed up to: $BACKUP_FILE"
    else
        log_error "Database backup failed!"
        exit 1
    fi

    # Keep only last 7 days of backups
    find "$BACKUP_DIR" -name "db_backup_*.sql" -mtime +7 -delete
}

pull_latest_code() {
    log_info "Pulling latest code from git..."

    cd "$PROJECT_DIR"

    # Check current branch
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    log_info "Current branch: $CURRENT_BRANCH"

    # Stash any local changes
    git stash

    # Pull latest changes
    git pull origin "$CURRENT_BRANCH"

    if [ $? -eq 0 ]; then
        log_success "Code updated successfully"
    else
        log_error "Git pull failed!"
        exit 1
    fi

    # Show current commit
    COMMIT_HASH=$(git rev-parse --short HEAD)
    COMMIT_MSG=$(git log -1 --pretty=%B)
    log_info "Deployed commit: $COMMIT_HASH - $COMMIT_MSG"
}

install_dependencies() {
    log_info "Installing/updating Python dependencies..."

    cd "$PROJECT_DIR"

    pip install --upgrade pip
    pip install -r requirements/production.txt

    if [ $? -eq 0 ]; then
        log_success "Dependencies installed successfully"
    else
        log_error "Failed to install dependencies!"
        exit 1
    fi
}

run_migrations() {
    log_info "Running database migrations..."

    cd "$PROJECT_DIR"

    # Check for pending migrations
    PENDING=$(python manage.py showmigrations --plan | grep "\[ \]" | wc -l)

    if [ "$PENDING" -gt 0 ]; then
        log_info "Found $PENDING pending migrations"

        # Run migrations
        python manage.py migrate --noinput

        if [ $? -eq 0 ]; then
            log_success "Migrations completed successfully"
        else
            log_error "Migration failed!"
            log_warning "Rolling back deployment..."
            # Restore from backup if needed
            exit 1
        fi
    else
        log_info "No pending migrations"
    fi
}

collect_static_files() {
    log_info "Collecting static files..."

    cd "$PROJECT_DIR"

    python manage.py collectstatic --noinput --clear

    if [ $? -eq 0 ]; then
        log_success "Static files collected successfully"
    else
        log_error "Failed to collect static files!"
        exit 1
    fi
}

clear_cache() {
    log_info "Clearing Django cache..."

    cd "$PROJECT_DIR"

    # Clear Redis cache
    redis-cli FLUSHDB

    log_success "Cache cleared"
}

health_check_before() {
    log_info "Running pre-deployment health check..."

    cd "$PROJECT_DIR"

    # Check if service is running
    if systemctl is-active --quiet gunicorn-${PROJECT_NAME}; then
        log_info "Service is currently running"
    else
        log_warning "Service is not running!"
    fi

    # Try health check endpoint
    if curl -sf http://localhost:8000/health/ > /dev/null 2>&1; then
        log_success "Health check passed"
    else
        log_warning "Health check failed (service may be down)"
    fi
}

restart_services() {
    log_info "Restarting application services..."

    # Restart Gunicorn
    sudo systemctl restart gunicorn-${PROJECT_NAME}

    if [ $? -eq 0 ]; then
        log_success "Gunicorn restarted"
    else
        log_error "Failed to restart Gunicorn!"
        exit 1
    fi

    # Reload Nginx (graceful reload)
    sudo systemctl reload nginx

    if [ $? -eq 0 ]; then
        log_success "Nginx reloaded"
    else
        log_error "Failed to reload Nginx!"
        exit 1
    fi

    # Wait for services to start
    log_info "Waiting for services to start..."
    sleep 5
}

health_check_after() {
    log_info "Running post-deployment health check..."

    RETRIES=5
    WAIT_TIME=3

    for i in $(seq 1 $RETRIES); do
        if curl -sf http://localhost:8000/health/ > /dev/null 2>&1; then
            log_success "Health check passed!"
            return 0
        else
            log_warning "Health check attempt $i/$RETRIES failed, retrying in ${WAIT_TIME}s..."
            sleep $WAIT_TIME
        fi
    done

    log_error "Health check failed after $RETRIES attempts!"
    log_error "Deployment may have issues. Check logs:"
    log_error "  - Application: $LOG_DIR/gunicorn-error.log"
    log_error "  - Nginx: /var/log/nginx/error.log"
    exit 1
}

run_smoke_tests() {
    log_info "Running smoke tests..."

    cd "$PROJECT_DIR"

    # Test database connectivity
    if python manage.py check --database default > /dev/null 2>&1; then
        log_success "Database connectivity: OK"
    else
        log_error "Database connectivity: FAILED"
        return 1
    fi

    # Test cache connectivity
    if python manage.py shell -c "from django.core.cache import cache; cache.set('test', 'ok', 1); assert cache.get('test') == 'ok'" > /dev/null 2>&1; then
        log_success "Cache connectivity: OK"
    else
        log_error "Cache connectivity: FAILED"
        return 1
    fi

    # Test static files
    if [ -f "$PROJECT_DIR/staticfiles/admin/css/base.css" ]; then
        log_success "Static files: OK"
    else
        log_error "Static files: FAILED"
        return 1
    fi

    log_success "All smoke tests passed!"
}

deployment_summary() {
    log_info "========================================="
    log_info "Deployment Summary"
    log_info "========================================="
    log_info "Timestamp: $TIMESTAMP"
    log_info "Branch: $(git rev-parse --abbrev-ref HEAD)"
    log_info "Commit: $(git rev-parse --short HEAD)"
    log_info "Environment: Production"
    log_info "========================================="

    # Show recent log entries
    log_info "Recent application logs:"
    tail -n 20 "$LOG_DIR/gunicorn-error.log" 2>/dev/null || echo "No logs found"
}

# ============================================================================
# Main Deployment Flow
# ============================================================================

main() {
    log_info "========================================="
    log_info "Starting Production Deployment"
    log_info "========================================="
    log_info "Time: $(date)"
    echo

    # Step 1: Prerequisites
    check_prerequisites
    echo

    # Step 2: Activate virtual environment
    activate_virtualenv
    echo

    # Step 3: Pre-deployment health check
    health_check_before
    echo

    # Step 4: Backup database
    backup_database
    echo

    # Step 5: Pull latest code
    pull_latest_code
    echo

    # Step 6: Install dependencies
    install_dependencies
    echo

    # Step 7: Run migrations
    run_migrations
    echo

    # Step 8: Collect static files
    collect_static_files
    echo

    # Step 9: Clear cache
    clear_cache
    echo

    # Step 10: Restart services
    restart_services
    echo

    # Step 11: Post-deployment health check
    health_check_after
    echo

    # Step 12: Run smoke tests
    run_smoke_tests
    echo

    # Step 13: Summary
    deployment_summary
    echo

    log_success "========================================="
    log_success "Deployment Completed Successfully!"
    log_success "========================================="
}

# Run main function
main

exit 0
