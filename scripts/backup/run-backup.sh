#!/usr/bin/env bash
# Run from cron on the VPS. Matches docker-compose.prod.yml (not legacy docker-compose).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

docker compose -f docker-compose.prod.yml exec -T web python manage.py backup_db
