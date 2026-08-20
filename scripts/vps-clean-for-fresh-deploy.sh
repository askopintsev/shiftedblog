#!/usr/bin/env bash
# Optional: stop and remove a previous ShiftedBlog production install on this VPS.
# Use before a fresh ./scripts/setup.sh (online) when an old deploy is present.
# Skip entirely on a clean server — go straight to clone + setup.
#
# Usage:
#   cd /opt/shiftedblog && ./scripts/vps-clean-for-fresh-deploy.sh
#   # or from any directory:
#   APP_DIR=/opt/shiftedblog ./scripts/vps-clean-for-fresh-deploy.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/shiftedblog}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

echo "ShiftedBlog — optional clean of previous production install"
echo "==========================================================="
echo "App directory: $APP_DIR"
echo "(Skip this script on a fresh VPS with no prior install.)"
echo ""

if [[ -d "$APP_DIR" && -f "$APP_DIR/$COMPOSE_FILE" ]]; then
  echo "Stopping Docker stack..."
  (cd "$APP_DIR" && docker compose -f "$COMPOSE_FILE" down -v --remove-orphans) || true
else
  echo "No existing compose project in $APP_DIR (skipping compose down)."
fi

echo "Stopping host web servers that may hold ports 80/443..."
systemctl stop nginx apache2 2>/dev/null || true

echo "Removing app directory..."
rm -rf "$APP_DIR"

echo "Pruning unused Docker resources (optional cleanup)..."
docker system prune -af --volumes 2>/dev/null || true

echo ""
echo "Checking ports 80 and 443..."
if ss -tlnp 2>/dev/null | grep -qE ':80 |:443 '; then
  echo "WARNING: something still listens on 80 or 443:" >&2
  ss -tlnp | grep -E ':80 |:443 ' || true
  echo "Stop that service before deploy (panel nginx, apache, another compose project)." >&2
else
  echo "Ports 80 and 443 are free."
fi

echo ""
echo "Done. Next: clone the repo into $APP_DIR and run ./scripts/setup.sh (online)."
