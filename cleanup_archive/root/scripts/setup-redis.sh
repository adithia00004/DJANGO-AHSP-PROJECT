#!/bin/bash
#
# Redis Setup Script
#
# This script installs and configures Redis for the AHSP project.
# Works on Ubuntu/Debian systems. For other systems, adjust package manager.
#
# Usage:
#   ./scripts/setup-redis.sh [docker|native]
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================================================
# Docker Installation
# ============================================================================

setup_redis_docker() {
    log_info "Setting up Redis with Docker..."

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Install Docker first:"
        log_error "  curl -fsSL https://get.docker.com -o get-docker.sh"
        log_error "  sudo sh get-docker.sh"
        exit 1
    fi

    # Check if Redis container already exists
    if docker ps -a | grep -q ahsp-redis; then
        log_info "Redis container already exists. Restarting..."
        docker restart ahsp-redis
    else
        log_info "Creating new Redis container..."
        docker run -d \
            --name ahsp-redis \
            -p 6379:6379 \
            --restart unless-stopped \
            redis:7-alpine redis-server --appendonly yes
    fi

    # Wait for Redis to start
    sleep 3

    # Test connection
    if docker exec ahsp-redis redis-cli ping | grep -q PONG; then
        log_success "Redis is running!"
        log_info "Connection: redis://127.0.0.1:6379/1"
    else
        log_error "Redis failed to start!"
        exit 1
    fi

    log_success "Redis setup completed (Docker)"
}

# ============================================================================
# Native Installation
# ============================================================================

setup_redis_native() {
    log_info "Setting up Redis natively..."

    # Detect OS
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    else
        log_error "Cannot detect OS. Install Redis manually."
        exit 1
    fi

    case $OS in
        ubuntu|debian)
            log_info "Installing Redis on Ubuntu/Debian..."
            sudo apt-get update
            sudo apt-get install -y redis-server

            # Configure Redis
            sudo sed -i 's/^bind 127.0.0.1/bind 0.0.0.0/' /etc/redis/redis.conf
            sudo sed -i 's/^# requirepass foobared/requirepass CHANGE-ME-redis-password/' /etc/redis/redis.conf

            # Enable and start Redis
            sudo systemctl enable redis-server
            sudo systemctl restart redis-server
            ;;

        centos|rhel|fedora)
            log_info "Installing Redis on CentOS/RHEL/Fedora..."
            sudo yum install -y redis
            sudo systemctl enable redis
            sudo systemctl start redis
            ;;

        *)
            log_error "Unsupported OS: $OS"
            log_error "Install Redis manually: https://redis.io/download"
            exit 1
            ;;
    esac

    # Test connection
    sleep 2
    if redis-cli ping | grep -q PONG; then
        log_success "Redis is running!"
        log_info "Connection: redis://127.0.0.1:6379/1"
    else
        log_error "Redis failed to start!"
        exit 1
    fi

    log_success "Redis setup completed (Native)"
    log_info "IMPORTANT: Set a strong password in /etc/redis/redis.conf"
    log_info "Search for 'requirepass' and set a secure password"
}

# ============================================================================
# Install Python Client
# ============================================================================

install_python_client() {
    log_info "Installing Python Redis client..."

    if [ -d "venv" ]; then
        log_info "Activating virtual environment..."
        source venv/bin/activate
    fi

    pip install redis django-redis hiredis

    log_success "Python Redis client installed"
}

# ============================================================================
# Verify Configuration
# ============================================================================

verify_configuration() {
    log_info "Verifying Redis configuration..."

    # Test basic operations
    redis-cli SET test_key "test_value" > /dev/null
    VALUE=$(redis-cli GET test_key)

    if [ "$VALUE" == "test_value" ]; then
        log_success "Redis read/write test passed"
        redis-cli DEL test_key > /dev/null
    else
        log_error "Redis read/write test failed!"
        exit 1
    fi

    # Show Redis info
    log_info "Redis version:"
    redis-cli --version

    log_info "Redis server info:"
    redis-cli INFO server | grep -E "redis_version|os|tcp_port"
}

# ============================================================================
# Create Django Cache Configuration
# ============================================================================

create_django_config() {
    log_info "Django cache configuration example:"
    cat <<EOF

Add to settings.py:

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PASSWORD': os.environ.get('REDIS_PASSWORD', None),
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
        },
        'KEY_PREFIX': 'ahsp',
        'TIMEOUT': 300,
    }
}

Add to .env:

REDIS_URL=redis://127.0.0.1:6379/1
REDIS_PASSWORD=your-secure-password

EOF
}

# ============================================================================
# Main
# ============================================================================

main() {
    log_info "========================================="
    log_info "Redis Setup for AHSP Project"
    log_info "========================================="
    echo

    METHOD=${1:-docker}

    case $METHOD in
        docker)
            setup_redis_docker
            ;;
        native)
            setup_redis_native
            ;;
        *)
            log_error "Invalid method: $METHOD"
            log_error "Usage: $0 [docker|native]"
            exit 1
            ;;
    esac

    echo
    install_python_client
    echo
    verify_configuration
    echo
    create_django_config
    echo

    log_success "========================================="
    log_success "Redis Setup Completed!"
    log_success "========================================="
    log_info "Next steps:"
    log_info "1. Update your .env file with Redis configuration"
    log_info "2. Test Django cache: python manage.py shell"
    log_info "   >>> from django.core.cache import cache"
    log_info "   >>> cache.set('test', 'OK', 60)"
    log_info "   >>> cache.get('test')"
}

main "$@"
