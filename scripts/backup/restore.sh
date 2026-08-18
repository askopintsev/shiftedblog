#!/usr/bin/env bash
# Restore backup_db output into docker-compose.prod.yml (Postgres 17).
# Usage:
#   ./scripts/backup/restore.sh --dry-run
#   ./scripts/backup/restore.sh --force --dump /path/to.sql.gz --media /path/to/media.tar.gz
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ ! -f docker-compose.prod.yml ]]; then
  echo "Run from a production checkout (docker-compose.prod.yml missing)." >&2
  exit 1
fi

exec docker compose -f docker-compose.prod.yml exec -T web \
  python manage.py restore_db "$@"
