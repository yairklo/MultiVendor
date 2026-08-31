#!/usr/bin/env bash
# Dumps the production MySQL database and prunes old dumps. Meant to run on
# the VPS itself (not in a container) via cron, alongside docker-compose.prod.yml:
#
#   0 3 * * * cd /path/to/MultiVendor && ./deploy/backup_db.sh >> /var/log/multivendor-backup.log 2>&1
#
# Restores are done with restore_db.sh in this same directory.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "backup_db.sh: no .env in $(pwd) -- copy .env.example and fill it in first" >&2
  exit 1
fi

# Only need DB_NAME/DB_ROOT_PASSWORD from .env, not every var in it (some
# may contain characters `source` would choke on) -- extract just those two.
DB_NAME=$(grep -E '^DB_NAME=' .env | tail -n1 | cut -d= -f2-)
DB_ROOT_PASSWORD=$(grep -E '^DB_ROOT_PASSWORD=' .env | tail -n1 | cut -d= -f2-)

if [ -z "${DB_NAME:-}" ] || [ -z "${DB_ROOT_PASSWORD:-}" ]; then
  echo "backup_db.sh: DB_NAME and/or DB_ROOT_PASSWORD missing from .env" >&2
  exit 1
fi

RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"

# --single-transaction: a consistent snapshot without locking tables for the
# duration of the dump (InnoDB, which this project's tables all use).
docker compose -f docker-compose.prod.yml exec -T mysql \
  mysqldump -u root -p"$DB_ROOT_PASSWORD" --single-transaction --routines --triggers "$DB_NAME" \
  | gzip > "$OUT_FILE"

echo "backup_db.sh: wrote $OUT_FILE ($(du -h "$OUT_FILE" | cut -f1))"

# Prune anything older than RETENTION_DAYS -- this script's own dumps only,
# identified by the $DB_NAME prefix, so it never touches unrelated files a
# human might also keep in ./backups.
find "$BACKUP_DIR" -maxdepth 1 -name "${DB_NAME}_*.sql.gz" -mtime "+${RETENTION_DAYS}" -print -delete
