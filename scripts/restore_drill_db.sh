#!/usr/bin/env bash
# restore_drill_db.sh — L6 restore drill for the Docker SSOT.
#
# Verifies a backup is actually restorable by loading it into a TEMPORARY scratch
# database inside the ahsp_postgres container, checking row counts, then dropping
# the scratch DB. The live database (ahsp_sni_db) is never touched.
#
# Usage:
#   bash scripts/restore_drill_db.sh ./backups/<file>.dump
#
# Requires: a running ahsp_postgres container and a custom-format dump
# (pg_dump -Fc), e.g. produced by scripts/safe_backup_db.sh.

set -u

PG_CONTAINER="${PG_CONTAINER:-ahsp_postgres}"
PG_USER="${PG_USER:-postgres}"
SCRATCH_DB="restore_drill_$(date +%Y%m%d_%H%M%S)"

fail() { echo "[ERROR] $1"; echo "Restore drill GAGAL."; cleanup; exit 1; }

cleanup() {
  # Best-effort drop of the scratch DB and the in-container copy of the dump.
  docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d postgres \
    -c "DROP DATABASE IF EXISTS \"$SCRATCH_DB\";" >/dev/null 2>&1 || true
  docker exec "$PG_CONTAINER" sh -c "rm -f /tmp/_drill.dump" >/dev/null 2>&1 || true
}

BACKUP_FILE="${1:-}"
[ -n "$BACKUP_FILE" ] || fail "Pakai: bash scripts/restore_drill_db.sh <file.dump>"
[ -f "$BACKUP_FILE" ] || fail "File backup tidak ditemukan: $BACKUP_FILE"
docker ps --format '{{.Names}}' | grep -qx "$PG_CONTAINER" \
  || fail "Container $PG_CONTAINER tidak berjalan."

echo "[1/5] Salin dump ke container $PG_CONTAINER"
docker cp "$BACKUP_FILE" "$PG_CONTAINER:/tmp/_drill.dump" || fail "docker cp gagal."

echo "[2/5] Validasi dump (pg_restore -l)"
docker exec "$PG_CONTAINER" pg_restore -l /tmp/_drill.dump >/dev/null \
  || fail "Dump tidak valid (pg_restore -l gagal)."

echo "[3/5] Buat scratch DB: $SCRATCH_DB"
docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d postgres \
  -c "CREATE DATABASE \"$SCRATCH_DB\";" >/dev/null || fail "CREATE DATABASE gagal."

echo "[4/5] Restore ke scratch DB"
# --no-owner/--no-acl: scratch tak butuh role asli. Abaikan error non-fatal,
# tetapi tangkap kegagalan total via verifikasi di langkah 5.
docker exec "$PG_CONTAINER" pg_restore --no-owner --no-acl -U "$PG_USER" \
  -d "$SCRATCH_DB" /tmp/_drill.dump >/tmp/_drill_restore.log 2>&1 || true

echo "[5/5] Verifikasi jumlah baris (sanity)"
COUNTS="$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$SCRATCH_DB" -At -F'|' -c "
SELECT
  (SELECT count(*) FROM dashboard_project),
  (SELECT count(*) FROM accounts_customuser),
  (SELECT count(*) FROM referensi_ahspreferensi),
  (SELECT count(*) FROM subscriptions_subscriptionplan);
" 2>/dev/null)" || fail "Query verifikasi gagal (restore kemungkinan tidak lengkap)."

PROJECTS="${COUNTS%%|*}"
echo "    projects|users|ahsp|plans = $COUNTS"
case "$PROJECTS" in
  ''|*[!0-9]*) fail "Jumlah project tidak terbaca; restore tidak sehat." ;;
esac
[ "$PROJECTS" -gt 0 ] || fail "Restore menghasilkan 0 project — backup mungkin kosong/rusak."

cleanup
echo "[OK] Restore drill LULUS. Backup '$BACKUP_FILE' dapat di-restore (projects=$PROJECTS)."
echo "     Scratch DB sudah dihapus; database live tidak tersentuh."
