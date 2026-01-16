#!/usr/bin/env bash
set -euo pipefail
PORT="${PORT:-8000}"

get_lan_ip() {
  if ip=$(hostname -I 2>/dev/null | awk '{print $1}'); then
    if [[ $ip =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then echo "$ip"; return; fi
  fi
  if ip=$(ip -4 route get 1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' | head -n1); then
    if [[ $ip =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then echo "$ip"; return; fi
  fi
  if ip=$(ipconfig getifaddr en0 2>/dev/null); then echo "$ip"; return; fi
  if ip=$(ipconfig getifaddr en1 2>/dev/null); then echo "$ip"; return; fi
  echo "127.0.0.1"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LAN_IP=$(get_lan_ip)
export DJANGO_DEBUG="${DJANGO_DEBUG:-True}"
export DJANGO_ALLOWED_HOSTS="${DJANGO_ALLOWED_HOSTS:-localhost,127.0.0.1,$LAN_IP}"

echo "Using LAN IP: $LAN_IP"
echo "DJANGO_ALLOWED_HOSTS=$DJANGO_ALLOWED_HOSTS"

echo "Starting waitress on 0.0.0.0:$PORT ..."
waitress-serve --listen=0.0.0.0:$PORT config.wsgi:application
