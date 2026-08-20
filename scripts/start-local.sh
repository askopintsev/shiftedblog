#!/usr/bin/env bash
# Start local Docker stack and open the editor login page in the browser.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

EDITOR_LOGIN_URL="http://localhost:5173/login"
BACKEND_URL="http://localhost:8888/"
EDITOR_URL="http://localhost:5173/"
MAX_WAIT=120

if [[ ! -f .env ]]; then
  echo "Configuration not found (.env)." >&2
  echo "Run ./scripts/setup.sh first and choose local mode." >&2
  exit 1
fi

if [[ ! -f start-shiftedblog.desktop ]] && [[ -f start-shiftedblog.desktop.in ]]; then
  sed "s|@PROJECT_ROOT@|$ROOT|g" start-shiftedblog.desktop.in > start-shiftedblog.desktop
fi

if ! ./scripts/check-prerequisites.sh local --quiet; then
  ./scripts/check-prerequisites.sh local
  exit 1
fi

wait_for_url() {
  local url="$1"
  local label="$2"
  local elapsed=0
  while [[ "$elapsed" -lt "$MAX_WAIT" ]]; do
    if curl -sf -o /dev/null "$url" 2>/dev/null; then
      echo "$label is ready."
      return 0
    fi
    sleep 2
    elapsed=$((elapsed + 2))
    if (( elapsed % 10 == 0 )); then
      echo "Waiting for $label... (${elapsed}s)"
    fi
  done
  echo "Timed out waiting for $label ($url)." >&2
  return 1
}

open_browser() {
  local url="$1"
  case "$(uname -s)" in
    Darwin)
      open "$url" || true
      ;;
    Linux)
      if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$url" >/dev/null 2>&1 || true
      elif command -v sensible-browser >/dev/null 2>&1; then
        sensible-browser "$url" >/dev/null 2>&1 || true
      else
        echo "Open in your browser: $url"
      fi
      ;;
    MINGW*|MSYS*|CYGWIN*)
      cmd.exe /c start "" "$url" 2>/dev/null || echo "Open in your browser: $url"
      ;;
    *)
      echo "Open in your browser: $url"
      ;;
  esac
}

echo "Starting ShiftedBlog (Docker)..."
mkdir -p logs backups static media static_blog
docker compose up -d

wait_for_url "$BACKEND_URL" "Backend"
wait_for_url "$EDITOR_URL" "Editor UI"

echo ""
echo "Opening editor: $EDITOR_LOGIN_URL"
open_browser "$EDITOR_LOGIN_URL"

echo ""
echo "If login fails, create a user:"
echo "  docker compose exec web python manage.py createsuperuser"
echo ""
echo "To stop: ./scripts/stop-local.sh"
