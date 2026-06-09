#!/usr/bin/env bash
# safe_backup_db.sh

# Cegah dijalankan via "source"
if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo "Jangan pakai source. Jalankan: bash scripts/safe_backup_db.sh"
  return 1 2>/dev/null || exit 1
fi

set -u

fail() {
  echo "[ERROR] $1"
  echo "Backup gagal. Terminal tetap aman."
  exit 1
}

# Parse .env dengan python-dotenv (aman untuk karakter khusus)
load_dotenv_exports() {
  python -c "
import os, shlex
from dotenv import dotenv_values

keys = [
    'POSTGRES_HOST',
    'POSTGRES_PORT',
    'POSTGRES_DB',
    'POSTGRES_USER',
    'POSTGRES_PASSWORD',
    'PGBOUNCER_PORT',
]
merged = {}
for f in ('.env', '.env.local'):
    if os.path.exists(f):
        vals = dotenv_values(f)
        for k, v in vals.items():
            if v is not None:
                merged[k] = v

for k in keys:
    v = merged.get(k)
    if v is not None:
        print(f'export {k}={shlex.quote(str(v))}')
"
}

eval "$(load_dotenv_exports)"

# Ambil default dari POSTGRES_* bila DB_* tidak diisi
DB_HOST="${DB_HOST:-${POSTGRES_HOST:-localhost}}"
DB_PORT="${DB_PORT:-${POSTGRES_PORT:-${PGBOUNCER_PORT:-5432}}}"
DB_NAME="${DB_NAME:-${POSTGRES_DB:-}}"
DB_USER="${DB_USER:-${POSTGRES_USER:-}}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
PGPASSWORD="${PGPASSWORD:-${POSTGRES_PASSWORD:-}}"

: "${DB_HOST:?DB_HOST/POSTGRES_HOST wajib diisi}"
: "${DB_PORT:?DB_PORT/POSTGRES_PORT wajib diisi}"
: "${DB_NAME:?DB_NAME/POSTGRES_DB wajib diisi}"
: "${DB_USER:?DB_USER/POSTGRES_USER wajib diisi}"

command -v pg_dump >/dev/null 2>&1 || fail "pg_dump tidak ditemukan di PATH."
command -v pg_restore >/dev/null 2>&1 || fail "pg_restore tidak ditemukan di PATH."

mkdir -p "$BACKUP_DIR" || fail "Gagal membuat folder backup: $BACKUP_DIR"

if [[ -z "${PGPASSWORD:-}" ]]; then
  read -rsp "PostgreSQL password untuk ${DB_USER}: " PGPASSWORD
  echo
fi
export PGPASSWORD

TS="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="${BACKUP_DIR}/${DB_NAME}_pre_opaque_${TS}.dump"
META_FILE="${OUT_FILE}.meta.txt"
SHA_FILE="${OUT_FILE}.sha256"

echo "[1/4] Dump database -> $OUT_FILE"
pg_dump -w -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -Fc -f "$OUT_FILE" \
  || fail "pg_dump gagal."

echo "[2/4] Verifikasi backup (pg_restore -l)"
pg_restore -l "$OUT_FILE" > /dev/null || fail "Backup tidak valid (pg_restore -l gagal)."

echo "[3/4] Buat checksum"
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$OUT_FILE" > "$SHA_FILE" || fail "Gagal membuat sha256."
elif command -v openssl >/dev/null 2>&1; then
  openssl dgst -sha256 "$OUT_FILE" | awk '{print $2 "  '"$OUT_FILE"'"}' > "$SHA_FILE" \
    || fail "Gagal membuat checksum via openssl."
else
  echo "[WARN] sha256sum/openssl tidak ada. Lewati checksum."
  SHA_FILE="(checksum skipped)"
fi

echo "[4/4] Simpan metadata"
{
  echo "timestamp=$TS"
  echo "host=$DB_HOST"
  echo "port=$DB_PORT"
  echo "db_name=$DB_NAME"
  echo "db_user=$DB_USER"
  echo "backup_file=$OUT_FILE"
  echo "sha256_file=$SHA_FILE"
  echo "size_bytes=$(wc -c < "$OUT_FILE")"
} > "$META_FILE" || fail "Gagal menulis metadata."

echo "Backup sukses:"
ls -lh "$OUT_FILE" "$META_FILE" 2>/dev/null
[[ -f "$SHA_FILE" ]] && ls -lh "$SHA_FILE"

echo "Selesai."
