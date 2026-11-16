#!/usr/bin/env bash
# Restore a dump produced by export_db.sh into the production stack.
# Usage (on the server): ./scripts/restore_db.sh backups/accessastana-YYYYMMDD.dump
# The dump must be inside ./backups (mounted into the db container as /backups).
set -euo pipefail
cd "$(dirname "$0")/.."
dump="${1:?usage: restore_db.sh backups/<file.dump>}"
name="$(basename "$dump")"
compose="docker compose -f ${COMPOSE_FILE_PATH:-docker-compose.prod.yml} --env-file .env"
set -a; . ./.env; set +a
$compose up -d db
$compose exec -T db sh -c 'until pg_isready -q; do sleep 1; done'
# --clean --if-exists replaces existing tables, so the restore can be repeated.
# The "SCHEMA public" entry is removed from the table of contents: the PostGIS
# extension depends on that schema, so it must not be dropped.
$compose exec -T db sh -c "
  pg_restore -l /backups/$name | grep -v 'SCHEMA - public' > /tmp/restore.toc &&
  pg_restore -U \"\$POSTGRES_USER\" -d \"\${POSTGRES_DB:-accessastana}\" --clean --if-exists --no-owner \
             -L /tmp/restore.toc /backups/$name"
$compose restart api
echo "restored $name"
