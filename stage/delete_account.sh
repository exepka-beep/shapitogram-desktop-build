#!/bin/bash
# Soft-delete (tombstone) a messenger account via the engine-admin API.
# Usage: delete_account.sh <user_id> <reason>
set -uo pipefail

UID_TARGET="${1:?user id required}"
REASON="${2:-coder account removed by owner}"
PG=shapitogram-main-postgres-1
API="http://127.0.0.1:2599"
TOKEN=$(grep -E '^TELESRV_ADMIN_API_TOKEN=' /root/gramsrv/deploy/docker/.env | cut -d= -f2-)
STAMP=$(date +%Y%m%d-%H%M%S)
SNAP=/root/backups/account-$UID_TARGET-$STAMP.csv

psql() { docker exec "$PG" psql -U telesrv -d telesrv_main -tAc "$1"; }

echo "=== BEFORE"
docker exec "$PG" psql -U telesrv -d telesrv_main -c \
  "SELECT id, username, first_name, deleted_at, deletion_source FROM users WHERE id=$UID_TARGET;"

mkdir -p /root/backups
docker exec "$PG" psql -U telesrv -d telesrv_main -c \
  "COPY (SELECT * FROM users WHERE id=$UID_TARGET) TO STDOUT WITH CSV HEADER" > "$SNAP" 2>/dev/null
echo "   snapshot -> $SNAP ($(wc -l < "$SNAP") lines, $(wc -c < "$SNAP") bytes)"

call() {
  curl -s -m 30 -X POST "$API/v1/accounts/delete" \
    -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
    -d "$1"
}

echo "=== DRY RUN"
call "{\"command_id\":\"dry-del-$UID_TARGET-$STAMP\",\"reason\":\"$REASON\",\"dry_run\":true,\"user_id\":$UID_TARGET}"
echo

echo "=== DELETE"
call "{\"command_id\":\"del-$UID_TARGET-$STAMP\",\"reason\":\"$REASON\",\"dry_run\":false,\"user_id\":$UID_TARGET}"
echo

echo "=== AFTER"
docker exec "$PG" psql -U telesrv -d telesrv_main -c \
  "SELECT id, username, first_name, phone, deleted_at, deletion_source, deletion_reason FROM users WHERE id=$UID_TARGET;"

echo "=== audit"
docker exec "$PG" psql -U telesrv -d telesrv_main -c \
  "SELECT command_id, action, status, to_timestamp(created_at) AS ts FROM admin_commands ORDER BY created_at DESC LIMIT 3;" 2>/dev/null \
  || echo "   (admin_commands shape differs, skipped)"
