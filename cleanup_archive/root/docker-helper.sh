#!/bin/bash

# AHSP Docker Helper Script - For Linux/macOS
# Usage: ./docker-helper.sh [command]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check if .env file exists
check_env() {
    if [ ! -f .env ]; then
        print_error ".env file not found!"
        print_info "Creating .env from .env.example..."
        cp .env.example .env
        print_success ".env created. Please edit it with your values."
        exit 1
    fi
}

# Commands
build() {
    print_info "Building Docker images..."
    docker-compose build
    print_success "Build completed"
}

up() {
    check_env
    print_info "Starting services..."
    docker-compose up -d
    print_success "Services started"
    print_info "Waiting for services to be healthy..."
    sleep 5
    docker-compose ps
}

down() {
    print_info "Stopping services..."
    docker-compose down
    print_success "Services stopped"
}

restart() {
    print_info "Restarting services..."
    docker-compose restart
    print_success "Services restarted"
}

logs() {
    SERVICE=${2:-web}
    docker-compose logs -f $SERVICE
}

migrate() {
    print_info "Running database migrations..."
    docker-compose exec web python manage.py migrate
    print_success "Migrations completed"
}

createsuperuser() {
    print_info "Creating superuser..."
    docker-compose exec web python manage.py createsuperuser
    print_success "Superuser created"
}

collectstatic() {
    print_info "Collecting static files..."
    docker-compose exec web python manage.py collectstatic --noinput --clear
    print_success "Static files collected"
}

shell() {
    print_info "Opening Django shell..."
    docker-compose exec web python manage.py shell
}

bash_shell() {
    print_info "Opening bash shell in web container..."
    docker-compose exec web bash
}

clean() {
    print_info "Cleaning up Docker resources..."
    docker-compose down -v
    print_success "Cleanup completed"
}

backup_db() {
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    BACKUP_FILE="backup-${TIMESTAMP}.sql.gz"
    print_info "Backing up database to $BACKUP_FILE..."
    docker-compose exec db pg_dump -U postgres ahsp_sni_db | gzip > $BACKUP_FILE
    print_success "Database backed up to $BACKUP_FILE"
}

restore_db() {
    BACKUP_FILE=${2:-""}
    if [ -z "$BACKUP_FILE" ]; then
        print_error "Please specify backup file: ./docker-helper.sh restore-db backup.sql.gz"
        exit 1
    fi
    print_info "Restoring database from $BACKUP_FILE..."
    gunzip -c $BACKUP_FILE | docker-compose exec -T db psql -U postgres ahsp_sni_db
    print_success "Database restored"
}

psql_cli() {
    print_info "Connecting to PostgreSQL..."
    docker-compose exec db psql -U postgres -d ahsp_sni_db
}

redis_cli() {
    print_info "Connecting to Redis..."
    docker-compose exec redis redis-cli -a $(grep REDIS_PASSWORD .env | cut -d= -f2)
}

test() {
    print_info "Running tests..."
    docker-compose exec web pytest
}

coverage() {
    print_info "Running tests with coverage..."
    docker-compose exec web pytest --cov=. --cov-report=html
    print_success "Coverage report generated in htmlcov/"
}

status() {
    print_info "Checking service status..."
    docker-compose ps
    echo ""
    print_info "Service health:"
    docker-compose exec -T web curl -s http://localhost:8000/health/ || print_error "Web service unhealthy"
    docker-compose exec -T redis redis-cli ping > /dev/null && print_success "Redis is healthy" || print_error "Redis unhealthy"
}

setup() {
    print_info "Running initial setup..."
    check_env
    build
    up
    migrate
    collectstatic
    print_success "Setup completed! Access app at http://localhost:8000"
}

help() {
    cat << EOF
AHSP Docker Helper Script

Usage: ./docker-helper.sh [command] [options]

Commands:
    setup               Initial setup (build, start, migrate, collectstatic)
    build               Build Docker images
    up                  Start all services
    down                Stop all services
    restart             Restart all services
    logs [service]      View service logs (default: web)
    migrate             Run database migrations
    createsuperuser     Create Django superuser
    collectstatic       Collect static files
    shell               Open Django shell
    bash                Open bash shell in web container
    clean               Stop services and remove volumes
    
    backup-db           Backup PostgreSQL database
    restore-db [file]   Restore database from backup
    psql                Connect to PostgreSQL CLI
    redis               Connect to Redis CLI
    
    test                Run all tests
    coverage            Run tests with coverage report
    status              Check service status
    
    help                Show this help message

Examples:
    ./docker-helper.sh setup
    ./docker-helper.sh logs web
    ./docker-helper.sh backup-db
    ./docker-helper.sh restore-db backup-20240113.sql.gz

EOF
}

# Main
case "$1" in
    build)
        build
        ;;
    up)
        up
        ;;
    down)
        down
        ;;
    restart)
        restart
        ;;
    logs)
        logs "$@"
        ;;
    migrate)
        migrate
        ;;
    createsuperuser)
        createsuperuser
        ;;
    collectstatic)
        collectstatic
        ;;
    shell)
        shell
        ;;
    bash)
        bash_shell
        ;;
    clean)
        clean
        ;;
    backup-db)
        backup_db
        ;;
    restore-db)
        restore_db "$@"
        ;;
    psql)
        psql_cli
        ;;
    redis)
        redis_cli
        ;;
    test)
        test
        ;;
    coverage)
        coverage
        ;;
    status)
        status
        ;;
    setup)
        setup
        ;;
    help|--help|-h|"")
        help
        ;;
    *)
        print_error "Unknown command: $1"
        help
        exit 1
        ;;
esac
