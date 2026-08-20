#!/usr/bin/env bash
# One-time VPS prep so GitHub Actions deploys do not fight for ports 80/443.
# Run on the server as root (or with sudo): ./scripts/vps-prepare-for-ci.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== ShiftedBlog VPS prepare for CI deploy ==="

if command -v systemctl >/dev/null 2>&1; then
  if systemctl is-enabled nginx >/dev/null 2>&1; then
    echo "Disabling host nginx (Docker serves HTTP/HTTPS)..."
    systemctl stop nginx
    systemctl disable nginx
  fi
  if systemctl is-enabled apache2 >/dev/null 2>&1; then
    echo "Disabling host apache2..."
    systemctl stop apache2
    systemctl disable apache2
  fi
fi

if [[ -f .env ]]; then
  echo "Removing legacy .env (use secrets.env only)..."
  rm -f .env
fi

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git config --global --add safe.directory "$ROOT" 2>/dev/null || true
fi

if [[ -x "${ROOT}/scripts/free-web-ports.sh" ]]; then
  COMPOSE_FILE=docker-compose.prod.yml WAIT_SECONDS=45 \
    "${ROOT}/scripts/free-web-ports.sh" "$ROOT" || true
fi

echo ""
echo "Check ports (should be free or only during active deploy):"
ss -tlnp | grep -E ':80|:443' || echo "ports 80 and 443 are free"
echo ""
echo "Done. Keep only /opt/shiftedblog docker compose on 80/443."
