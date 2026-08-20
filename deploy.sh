#!/usr/bin/env bash
# Production deploy for ShiftedBlog (Doppler optional).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "Starting deployment..."

# Optional: refresh secrets.env from Doppler when available
if [[ "${SKIP_DOPPLER:-0}" != "1" ]] && command -v doppler >/dev/null 2>&1; then
  if [[ -n "${DOPPLER_TOKEN:-}" ]] || doppler configure get token >/dev/null 2>&1; then
    echo "Downloading secrets via Doppler..."
    doppler secrets download --no-file --format=env > secrets.env
  fi
fi

if [[ ! -f secrets.env ]]; then
  echo "secrets.env not found. Run ./scripts/setup.sh (online or private) or provide secrets.env." >&2
  exit 1
fi

# Pull latest changes when this is a git checkout
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git pull origin master || git pull || true
fi

mkdir -p logs backups static media static_blog
chown -R 1000:1000 logs backups static media 2>/dev/null || chmod -R a+rwX logs backups static media

# Regenerate nginx from template when DOMAIN/SITE_URL present
if grep -qE '^(DOMAIN|SITE_URL)=' secrets.env; then
  ./scripts/generate-nginx-conf.sh || true
fi

if grep -qE '^PUBLIC_SITE_ENABLED=false' secrets.env 2>/dev/null; then
  ./scripts/check-env.sh private
else
  ./scripts/check-env.sh online
fi

# shellcheck disable=SC1091
source ./scripts/load-editor-ui-build-env.sh

docker compose -f docker-compose.prod.yml down

docker builder prune -af || true
docker image prune -af || true

docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Sync editor dist volume / reload nginx when containers are up
docker compose -f docker-compose.prod.yml exec -T web \
  bash -c 'if [[ -d /editor-ui/dist && -d /editor-ui/dist-export ]]; then cp -a /editor-ui/dist/. /editor-ui/dist-export/; fi' \
  || true
docker compose -f docker-compose.prod.yml exec -T nginx nginx -s reload || true

docker system prune -f || true

echo "Deployment completed successfully!"
