#!/usr/bin/env bash
# Restores a dump produced by backup_db.sh. DESTRUCTIVE: overwrites every
# table currently in the database with the dump's contents.
#
#   ./deploy/restore_db.sh ./backups/multivendor_prod_20260901_030000.sql.gz
set -euo pipefail

cd "$(dirname "$0")/.."

DUMP_FILE="${1:-}"
if [ -z "$DUMP_FILE" ] || [ ! -f "$DUMP_FILE" ]; then
  echo "usage: $0 <path-to-dump.sql.gz>" >&2
  exit 1
fi

if [ ! -f .env ]; then
  echo "restore_db.sh: no .env in $(pwd)" >&2
  exit 1
fi

DB_NAME=$(grep -E '^DB_NAME=' .env | tail -n1 | cut -d= -f2-)
DB_ROOT_PASSWORD=$(grep -E '^DB_ROOT_PASSWORD=' .env | tail -n1 | cut -d= -f2-)

if [ -z "${DB_NAME:-}" ] || [ -z "${DB_ROOT_PASSWORD:-}" ]; then
  echo "restore_db.sh: DB_NAME and/or DB_ROOT_PASSWORD missing from .env" >&2
  exit 1
fi

read -r -p "This will OVERWRITE every table in '$DB_NAME' with $DUMP_FILE. Type the database name to confirm: " CONFIRM
if [ "$CONFIRM" != "$DB_NAME" ]; then
  echo "restore_db.sh: confirmation did not match '$DB_NAME' -- aborted" >&2
  exit 1
fi

gunzip -c "$DUMP_FILE" | docker compose -f docker-compose.prod.yml exec -T mysql \
  mysql -u root -p"$DB_ROOT_PASSWORD" "$DB_NAME"

echo "restore_db.sh: restored $DUMP_FILE into $DB_NAME"
