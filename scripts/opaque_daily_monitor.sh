#!/usr/bin/env bash
# Run daily opaque health snapshot and store log artifacts.

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo "Jangan pakai source. Jalankan: bash scripts/opaque_daily_monitor.sh"
  return 1 2>/dev/null || exit 1
fi

set -euo pipefail

WINDOW_DAYS="${WINDOW_DAYS:-7}"
OUT_DIR="${OUT_DIR:-./logs/opaque_monitoring}"

mkdir -p "$OUT_DIR"

TS="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="${OUT_DIR}/opaque_status_${TS}.log"

{
  echo "timestamp=${TS}"
  echo "window_days=${WINDOW_DAYS}"
  echo
  python manage.py opaque_post_deploy_status --window-days "${WINDOW_DAYS}"
} | tee "$OUT_FILE"

echo
echo "Saved report: ${OUT_FILE}"
