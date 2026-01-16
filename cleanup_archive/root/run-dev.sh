#!/usr/bin/env bash
set -euo pipefail

# Default values
PORT="8000"
RUN_MIGRATE=0

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper for printing
info() { echo -e "${CYAN}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -p|--port) PORT="$2"; shift ;;
        -m|--migrate) RUN_MIGRATE=1 ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

get_lan_ip() {
    local ip=""
    
    # 1. Windows Git Bash / MSYS
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        # Try finding IPv4 Address line from ipconfig
        # Filter out "Media disconnected" and look for valid IP
        # Note: This takes the first found IPv4. 
        ip=$(ipconfig | grep "IPv4 Address" | head -n 1 | awk -F': ' '{print $2}' | tr -d '\r')
    fi

    # 2. Linux / WSL
    if [[ -z "$ip" ]] && command -v hostname &> /dev/null; then
        ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    fi
    
    # 3. macOS
    if [[ -z "$ip" ]] && [[ "$OSTYPE" == "darwin"* ]]; then
        ip=$(ipconfig getifaddr en0 2>/dev/null)
    fi

    # Validation
    if [[ "$ip" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
        echo "$ip"
    else
        echo "127.0.0.1"
    fi
}

info "Detecting LAN IP..."
LAN_IP=$(get_lan_ip)
success "Using IP: $LAN_IP"

# Set Evironment Variables
export DJANGO_DEBUG="True"
export DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,$LAN_IP,*"

info "Environment Configured:"
echo "  DJANGO_DEBUG=$DJANGO_DEBUG"
echo "  DJANGO_ALLOWED_HOSTS=$DJANGO_ALLOWED_HOSTS"

# FORCE localhost for database/redis when running locally
export POSTGRES_HOST="localhost"
export REDIS_HOST="localhost"
export REDIS_URL="redis://:redis_password@localhost:6379/1"
export CELERY_BROKER_URL="redis://:redis_password@localhost:6379/0"
export CELERY_RESULT_BACKEND="redis://:redis_password@localhost:6379/0"

info "Forcing Local Connection: POSTGRES_HOST=localhost"

# Activates venv if exists in common locations (optional convenience)
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    if [[ -f "env/Scripts/activate" ]]; then
        source env/Scripts/activate
    elif [[ -f ".venv/Scripts/activate" ]]; then
        source .venv/Scripts/activate
    elif [[ -f "env/bin/activate" ]]; then
        source env/bin/activate
    fi
fi

if [[ "$RUN_MIGRATE" == "1" ]]; then
    info "Running migrations..."
    python manage.py migrate
fi

info "Starting Django Server on $LAN_IP:$PORT"
success "Access URL: http://$LAN_IP:$PORT"

# Run Server
python manage.py runserver 0.0.0.0:$PORT
