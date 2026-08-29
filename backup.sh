#!/bin/bash
# Nightly PostgreSQL backup for the production deployment. Intended to run
# from cron on the CentOS 7 VM, from the repo root (where
# docker-compose.prod.yml lives) — see docs/DEPLOY.md for the crontab entry.
#
# Usage: ./backup.sh
#
# Restore (stop the app first so nothing writes during the restore):
#   docker compose -f docker-compose.prod.yml --env-file .env.prod stop backend worker beat
#   gunzip -c backups/spectrum_bids_YYYYmmdd_HHMMSS.sql.gz | \
#     docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T db \
#       sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
#   docker compose -f docker-compose.prod.yml --env-file .env.prod start backend worker beat
#
# This restore replays SQL over the existing (empty or otherwise) database;
# it does not drop/recreate it. For a from-scratch restore, drop and
# recreate the database first, or `createdb` it, before piping the dump in.

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

BACKUP_DIR="backups"
RETENTION_DAYS=14
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="${BACKUP_DIR}/spectrum_bids_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T db \
    sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
    | gzip > "${OUT_FILE}"

echo "$(date -u +%FT%TZ) backup.sh: wrote ${OUT_FILE} ($(du -h "${OUT_FILE}" | cut -f1))"

find "${BACKUP_DIR}" -name 'spectrum_bids_*.sql.gz' -mtime "+${RETENTION_DAYS}" -print -delete
