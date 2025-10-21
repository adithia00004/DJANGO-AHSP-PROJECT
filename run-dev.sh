#!/usr/bin/env bash
set -euo pipefail
PORT="${PORT:-8000}"
RUN_MIGRATE="${RUN_MIGRATE:-0}"

get_lan_ip() {
  # Linux hostname -I
  if ip=$(hostname -I 2>/dev/null | awk '{print $1}'); then
    if [[ $ip =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then echo "$ip"; return; fi
  fi
  # Linux: ip route
  if ip=$(ip -4 route get 1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' | head -n1); then
    if [[ $ip =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then echo "$ip"; return; fi
  fi
  # macOS: en0/en1
  if ip=$(ipconfig getifaddr en0 2>/dev/null); then echo "$ip"; return; fi
  if ip=$(ipconfig getifaddr en1 2>/dev/null); then echo "$ip"; return; fi
  # Fallback
  echo "127.0.0.1"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LAN_IP=$(get_lan_ip)
export DJANGO_DEBUG="${DJANGO_DEBUG:-True}"
export DJANGO_ALLOWED_HOSTS="${DJANGO_ALLOWED_HOSTS:-localhost,127.0.0.1,$LAN_IP}"

echo "Using LAN IP: $LAN_IP"
echo "DJANGO_ALLOWED_HOSTS=$DJANGO_ALLOWED_HOSTS"

if [[ "$RUN_MIGRATE" == "1" ]]; then
  echo "Running migrations..."
  python manage.py migrate
fi

echo "Starting server on 0.0.0.0:$PORT ..."
python manage.py runserver 0.0.0.0:$PORT
