#!/bin/bash
#
# Database Backup Script
#
# Creates timestamped backups of the PostgreSQL database.
# Supports full backups and automatic retention management.
#
# Usage:
#   ./scripts/backup-database.sh [production|staging|development]
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# ============================================================================
# Configuration
# ============================================================================

ENVIRONMENT=${1:-development}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE=$(date +%Y-%m-%d)

# Default backup directory
BACKUP_DIR="/var/backups/ahsp"

# Retention days (how long to keep backups)
case $ENVIRONMENT in
    production)
        RETENTION_DAYS=30
        ;;
    staging)
        RETENTION_DAYS=7
        ;;
    development)
        RETENTION_DAYS=3
        ;;
    *)
        log_error "Invalid environment: $ENVIRONMENT"
        log_error "Usage: $0 [production|staging|development]"
        exit 1
        ;;
esac

# ============================================================================
# Load Environment Variables
# ============================================================================

load_env_variables() {
    log_info "Loading environment variables..."

    ENV_FILE=".env.$ENVIRONMENT"

    if [ ! -f "$ENV_FILE" ]; then
        log_warning "Environment file not found: $ENV_FILE"
        log_info "Using default .env file"
        ENV_FILE=".env"
    fi

    if [ -f "$ENV_FILE" ]; then
        export $(grep -v '^#' $ENV_FILE | xargs)
        log_success "Environment variables loaded from $ENV_FILE"
    else
        log_error "No environment file found!"
        exit 1
    fi
}

# ============================================================================
# Create Backup Directory
# ============================================================================

create_backup_directory() {
    log_info "Creating backup directory..."

    BACKUP_SUBDIR="$BACKUP_DIR/$ENVIRONMENT/$DATE"

    mkdir -p "$BACKUP_SUBDIR"

    if [ $? -eq 0 ]; then
        log_success "Backup directory created: $BACKUP_SUBDIR"
    else
        log_error "Failed to create backup directory!"
        exit 1
    fi
}

# ============================================================================
# Create Full Backup
# ============================================================================

create_full_backup() {
    log_info "Creating full database backup..."

    BACKUP_FILE="$BACKUP_SUBDIR/full_backup_${TIMESTAMP}.dump"

    PGPASSWORD=$POSTGRES_PASSWORD pg_dump \
        -h $POSTGRES_HOST \
        -U $POSTGRES_USER \
        -d $POSTGRES_DB \
        -F c \
        -b \
        -v \
        -f "$BACKUP_FILE"

    if [ $? -eq 0 ]; then
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        log_success "Full backup created: $BACKUP_FILE ($BACKUP_SIZE)"
    else
        log_error "Full backup failed!"
        exit 1
    fi
}

# ============================================================================
# Create SQL Backup (for easy inspection)
# ============================================================================

create_sql_backup() {
    log_info "Creating SQL backup (for inspection)..."

    SQL_FILE="$BACKUP_SUBDIR/backup_${TIMESTAMP}.sql"

    PGPASSWORD=$POSTGRES_PASSWORD pg_dump \
        -h $POSTGRES_HOST \
        -U $POSTGRES_USER \
        -d $POSTGRES_DB \
        -F p \
        -f "$SQL_FILE"

    if [ $? -eq 0 ]; then
        # Compress SQL file
        gzip "$SQL_FILE"
        SQL_SIZE=$(du -h "${SQL_FILE}.gz" | cut -f1)
        log_success "SQL backup created: ${SQL_FILE}.gz ($SQL_SIZE)"
    else
        log_warning "SQL backup failed (non-critical)"
    fi
}

# ============================================================================
# Create Schema-Only Backup
# ============================================================================

create_schema_backup() {
    log_info "Creating schema-only backup..."

    SCHEMA_FILE="$BACKUP_SUBDIR/schema_${TIMESTAMP}.sql"

    PGPASSWORD=$POSTGRES_PASSWORD pg_dump \
        -h $POSTGRES_HOST \
        -U $POSTGRES_USER \
        -d $POSTGRES_DB \
        -F p \
        -s \
        -f "$SCHEMA_FILE"

    if [ $? -eq 0 ]; then
        SCHEMA_SIZE=$(du -h "$SCHEMA_FILE" | cut -f1)
        log_success "Schema backup created: $SCHEMA_FILE ($SCHEMA_SIZE)"
    else
        log_warning "Schema backup failed (non-critical)"
    fi
}

# ============================================================================
# Backup Metadata
# ============================================================================

create_metadata() {
    log_info "Creating backup metadata..."

    METADATA_FILE="$BACKUP_SUBDIR/metadata_${TIMESTAMP}.txt"

    cat > "$METADATA_FILE" <<EOF
Backup Metadata
================

Environment: $ENVIRONMENT
Timestamp: $TIMESTAMP
Date: $DATE

Database Information:
- Host: $POSTGRES_HOST
- Port: $POSTGRES_PORT
- Database: $POSTGRES_DB
- User: $POSTGRES_USER

Backup Files:
- Full backup: full_backup_${TIMESTAMP}.dump
- SQL backup: backup_${TIMESTAMP}.sql.gz
- Schema: schema_${TIMESTAMP}.sql

System Information:
- Hostname: $(hostname)
- OS: $(uname -s)
- Python: $(python --version 2>&1)
- Django: $(python -c "import django; print(django.get_version())" 2>&1 || echo "N/A")

Git Information:
- Branch: $(git rev-parse --abbrev-ref HEAD 2>&1 || echo "N/A")
- Commit: $(git rev-parse --short HEAD 2>&1 || echo "N/A")
- Message: $(git log -1 --pretty=%B 2>&1 || echo "N/A")
EOF

    log_success "Metadata created: $METADATA_FILE"
}

# ============================================================================
# Verify Backup
# ============================================================================

verify_backup() {
    log_info "Verifying backup integrity..."

    BACKUP_FILE="$BACKUP_SUBDIR/full_backup_${TIMESTAMP}.dump"

    # Check if file exists and is not empty
    if [ -s "$BACKUP_FILE" ]; then
        # Try to list contents (pg_restore --list)
        PGPASSWORD=$POSTGRES_PASSWORD pg_restore --list "$BACKUP_FILE" > /dev/null 2>&1

        if [ $? -eq 0 ]; then
            log_success "Backup verification passed"
        else
            log_error "Backup verification failed!"
            exit 1
        fi
    else
        log_error "Backup file is empty or missing!"
        exit 1
    fi
}

# ============================================================================
# Cleanup Old Backups
# ============================================================================

cleanup_old_backups() {
    log_info "Cleaning up old backups (retention: $RETENTION_DAYS days)..."

    # Find and delete backups older than retention period
    DELETED=$(find "$BACKUP_DIR/$ENVIRONMENT" -type d -mtime +$RETENTION_DAYS -exec rm -rf {} \; -print 2>/dev/null | wc -l)

    if [ "$DELETED" -gt 0 ]; then
        log_success "Deleted $DELETED old backup(s)"
    else
        log_info "No old backups to clean up"
    fi
}

# ============================================================================
# Generate Backup Report
# ============================================================================

generate_report() {
    log_info "========================================="
    log_info "Backup Summary"
    log_info "========================================="
    log_info "Environment: $ENVIRONMENT"
    log_info "Timestamp: $TIMESTAMP"
    log_info "Backup Directory: $BACKUP_SUBDIR"
    log_info "Retention: $RETENTION_DAYS days"
    echo

    log_info "Backup Files:"
    ls -lh "$BACKUP_SUBDIR"
    echo

    log_info "Total Backup Size:"
    du -sh "$BACKUP_SUBDIR"
    echo

    log_info "Disk Usage:"
    df -h "$BACKUP_DIR"
    echo

    log_success "Backup completed successfully!"
}

# ============================================================================
# Main
# ============================================================================

main() {
    log_info "========================================="
    log_info "Database Backup Script"
    log_info "========================================="
    log_info "Environment: $ENVIRONMENT"
    log_info "Timestamp: $(date)"
    echo

    load_env_variables
    echo

    create_backup_directory
    echo

    create_full_backup
    echo

    create_sql_backup
    echo

    create_schema_backup
    echo

    create_metadata
    echo

    verify_backup
    echo

    cleanup_old_backups
    echo

    generate_report
    echo

    log_info "Next Steps:"
    log_info "1. Verify backup: pg_restore --list $BACKUP_SUBDIR/full_backup_${TIMESTAMP}.dump"
    log_info "2. Test restore in a separate database"
    log_info "3. Store backup off-site (AWS S3, Google Cloud Storage, etc.)"
}

main

exit 0
