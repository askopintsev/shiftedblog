#!/usr/bin/env bash
# Development container entrypoint (optional; compose may override command).
set -euo pipefail

python manage.py migrate --noinput
exec python manage.py runserver 0.0.0.0:8000
