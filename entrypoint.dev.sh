#!/usr/bin/env bash
# Development container entrypoint (optional; compose may override command).
set -euo pipefail

wait_for_db() {
  local attempts=0
  local max_attempts=30
  until python - <<'PY'
import os

import psycopg2

psycopg2.connect(
    dbname=os.environ["DB_NAME"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASS"],
    host=os.environ["DB_HOST"],
    port=os.environ.get("DB_PORT", "5432"),
).close()
PY
  do
    attempts=$((attempts + 1))
    if [[ "$attempts" -ge "$max_attempts" ]]; then
      echo "Database not ready after ${max_attempts} attempts." >&2
      exit 1
    fi
    echo "Waiting for database... (${attempts}/${max_attempts})"
    sleep 2
  done
}

wait_for_db
python manage.py migrate --noinput
exec python manage.py runserver 0.0.0.0:8000
