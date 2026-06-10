#!/usr/bin/env bash
set -euo pipefail

# Bind mounts from the host are often root-owned; ensure appuser can write logs/backups.
mkdir -p /app/logs
chown -R appuser:appuser /app/logs /backups

runuser -u appuser -- bash -c '
set -euo pipefail
python manage.py collectstatic --noinput
python manage.py migrate --noinput
exec python -m gunicorn --bind 0.0.0.0:8000 --workers 3 shiftedblog.wsgi:application \
  --access-logfile - --error-logfile - --log-level info
'
