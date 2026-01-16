#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/d/PORTOFOLIO ADIT/DJANGO AHSP PROJECT"
PROJECT_ID="${PROJECT_ID:-160}"
USERNAME="${LOGIN_USERNAME:-aditf96@gmail.com}"
PASSWORD="${LOGIN_PASSWORD:-Ph@ntomk1d}"

cd "$PROJECT_DIR"
echo "[1/7] Working dir: $PROJECT_DIR"

# Guard: ensure port 8000 is free (avoid hitting old server without SQL_TRACE).
echo "[1.5/7] Checking port 8000..."
PORT_IN_USE=0
PORT_CHECK_FILE="logs/port8000_check.txt"
rm -f "$PORT_CHECK_FILE"
if command -v netstat >/dev/null 2>&1; then
  if netstat -ano 2>/dev/null | grep -q ":8000 .*LISTENING"; then
    PORT_IN_USE=1
  fi
else
  if cmd.exe /c "netstat -ano | findstr :8000 | findstr LISTENING" > "$PORT_CHECK_FILE" 2>&1; then
    PORT_IN_USE=1
  fi
fi

if [ "$PORT_IN_USE" -eq 1 ]; then
  echo "ERROR: Port 8000 is in use. Stop existing runserver first."
  if command -v netstat >/dev/null 2>&1; then
    netstat -ano 2>/dev/null | grep ":8000 .*LISTENING" || true
  else
    cat "$PORT_CHECK_FILE" || true
  fi
  exit 1
fi
echo "[1.6/7] Port 8000 is free"

export DJANGO_ENV=development
export SQL_TRACE=1

rm -f logs/sql_trace.log logs/runserver_sql_trace.log

echo "[2/7] Starting runserver with SQL_TRACE=1"
python manage.py runserver 8000 > logs/runserver_sql_trace.log 2>&1 &
SERVER_PID=$!

cleanup() {
  kill "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT

# Wait for server to be ready (max 15s)
READY=0
echo "[3/7] Waiting for server readiness (max 15s)..."
for i in {1..15}; do
  if curl -s --max-time 1 http://127.0.0.1:8000/ >/dev/null; then
    READY=1
    break
  fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "ERROR: runserver exited early. Log:"
    tail -n 80 logs/runserver_sql_trace.log || true
    exit 1
  fi
  echo "  ...not ready yet ($i/15)"
  sleep 1
done

if [ "$READY" -ne 1 ]; then
  echo "ERROR: server not ready after 15s."
  tail -n 80 logs/runserver_sql_trace.log || true
  exit 1
fi

LOGIN_URL="http://127.0.0.1:8000/accounts/login/"

echo "[4/7] Fetching CSRF"
curl -s --max-time 5 -c cookies.txt "$LOGIN_URL" > /dev/null
CSRF=$(awk '/csrftoken/ {print $7}' cookies.txt | tail -1)
if [ -z "$CSRF" ]; then
  echo "ERROR: CSRF token not found."
  exit 1
fi

echo "[5/7] Logging in"
curl -s --max-time 5 -b cookies.txt -c cookies.txt -X POST "$LOGIN_URL" \
  -H "Referer: $LOGIN_URL" \
  -d "login=$USERNAME" \
  -d "password=$PASSWORD" \
  -d "csrfmiddlewaretoken=$CSRF" > /dev/null

echo "[6/7] Hitting endpoints"
for url in \
  "http://127.0.0.1:8000/detail_project/api/v2/project/$PROJECT_ID/chart-data/?timescale=weekly&mode=both" \
  "http://127.0.0.1:8000/detail_project/$PROJECT_ID/volume-pekerjaan/" \
  "http://127.0.0.1:8000/dashboard/"
do
  code=$(curl -s --max-time 10 -b cookies.txt -o /dev/null -w "%{http_code}" "$url")
  echo "$url -> $code"
done

echo "[7/7] Checking sql_trace.log"
for i in {1..5}; do
  [ -f logs/sql_trace.log ] && break
  sleep 1
done

echo "== sql_trace.log (path=) =="
if grep -m 5 "path=" logs/sql_trace.log; then
  true
else
  echo "No path lines in sql_trace.log."
  tail -n 80 logs/runserver_sql_trace.log || true
  exit 1
fi

echo "== parsed query counts (from DEBUG django.db.backends) =="
python - <<'PY'
from pathlib import Path
import re

log_path = Path("logs/sql_trace.log")
text = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()

info_re = re.compile(r"sql_trace path=([^ ]+)")
db_re = re.compile(r"django\.db\.backends \(([\d\.]+)\)")

pending_count = 0
pending_db_ms = 0.0
last = {}

for line in text:
    if "DEBUG django.db.backends" in line:
        m = db_re.search(line)
        if m:
            pending_count += 1
            pending_db_ms += float(m.group(1)) * 1000.0
        continue
    m = info_re.search(line)
    if m:
        path = m.group(1)
        last[path] = {"count": pending_count, "db_ms": pending_db_ms}
        pending_count = 0
        pending_db_ms = 0.0

targets = [
    "/detail_project/api/v2/project/160/chart-data/",
    "/detail_project/160/volume-pekerjaan/",
    "/dashboard/",
    "/accounts/login/",
]

for path in targets:
    entry = last.get(path)
    if not entry:
        print(f"{path} -> no entry found")
        continue
    print(f"{path} -> queries={entry['count']} db_ms={entry['db_ms']:.2f}")
PY
