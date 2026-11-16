#!/usr/bin/env bash
# Export the precomputed database (run on the machine that did the ingestion).
# Produces backups/accessastana-YYYYMMDD.dump (custom format, compressed).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
out="backups/accessastana-$(date +%Y%m%d).dump"
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-accessastana}" -d "${POSTGRES_DB:-accessastana}" \
  --format=custom --no-owner --schema=public > "$out"
# --schema=public: only our tables. The PostGIS extension itself (and the
# tiger/topology schemas of the postgis image) already exist on the server.
echo "wrote $out ($(du -h "$out" | cut -f1))"
