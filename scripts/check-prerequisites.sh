#!/usr/bin/env bash
# Check tools required for ShiftedBlog deploy (local or production VPS).
#
# Usage:
#   ./scripts/check-prerequisites.sh local [--quiet]
#   ./scripts/check-prerequisites.sh online [--quiet]
#   ./scripts/check-prerequisites.sh private [--quiet]
#   ./scripts/check-prerequisites.sh private-ip [--quiet]
#   ./scripts/check-prerequisites.sh production [--quiet]  # alias for online
set -euo pipefail

MODE="local"
QUIET=false
for arg in "$@"; do
  case "$arg" in
    --quiet) QUIET=true ;;
    local) MODE="local" ;;
    online|production|private|private-ip) MODE="production" ;;
    *)
      echo "Usage: $0 local|online|private|private-ip [--quiet]" >&2
      exit 2
      ;;
  esac
done

GIT_URL="https://git-scm.com/downloads"
DOCKER_URL="https://docs.docker.com/get-docker/"
CERTBOT_URL="https://certbot.eff.org/instructions"

detect_os() {
  case "$(uname -s)" in
    Darwin) echo "macos" ;;
    Linux) echo "linux" ;;
    MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
    *) echo "unknown" ;;
  esac
}

OS="$(detect_os)"
errors=0
warnings=0
missing=()

log() {
  if [[ "$QUIET" == false ]]; then
    echo "$@"
  fi
}

warn() {
  warnings=$((warnings + 1))
  if [[ "$QUIET" == false ]]; then
    echo "WARNING: $*" >&2
  fi
}

fail() {
  missing+=("$1")
  errors=$((errors + 1))
}

has_git() {
  command -v git >/dev/null 2>&1
}

has_docker() {
  command -v docker >/dev/null 2>&1
}

has_compose() {
  docker compose version >/dev/null 2>&1
}

has_curl() {
  command -v curl >/dev/null 2>&1
}

has_certbot() {
  command -v certbot >/dev/null 2>&1
}

docker_daemon_ok() {
  docker info >/dev/null 2>&1
}

ports_in_use() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -tlnp 2>/dev/null | grep -qE ":${port} "
    return
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
    return
  fi
  return 1
}

ports_80_443_free() {
  ! ports_in_use 80 && ! ports_in_use 443
}

ports_local_free() {
  ! ports_in_use 8888 && ! ports_in_use 5173
}

list_busy_ports() {
  local ports=("$@")
  local busy=()
  for port in "${ports[@]}"; do
    if ports_in_use "$port"; then
      busy+=("$port")
    fi
  done
  if [[ "${#busy[@]}" -gt 0 ]]; then
    echo "${busy[*]}"
  fi
}

if ! has_git; then
  fail "git"
fi

if ! has_docker; then
  fail "docker"
fi

if has_docker && ! has_compose; then
  fail "docker compose"
fi

if ! has_curl; then
  fail "curl"
fi

if [[ "$MODE" == "production" ]] && ! has_certbot; then
  warn "certbot not found (required on the VPS for Let's Encrypt TLS)"
fi

if [[ "$MODE" == "production" ]] && ! ports_80_443_free; then
  busy="$(list_busy_ports 80 443)"
  warn "ports in use (${busy}) — stop host nginx/apache or an old stack before deploy"
fi

if [[ "$MODE" == "local" ]] && ! ports_local_free; then
  busy="$(list_busy_ports 8888 5173)"
  warn "ports in use (${busy}) — stop other Docker stacks or local npm/vite on 5173"
fi

if [[ "$errors" -gt 0 ]]; then
  if [[ "$QUIET" == false ]]; then
    echo "Missing prerequisites for ShiftedBlog ($MODE):" >&2
    for item in "${missing[@]}"; do
      echo "  - $item" >&2
    done
    echo "" >&2
    echo "Download and install:" >&2
    echo "  Git:    $GIT_URL" >&2
    echo "  Docker: $DOCKER_URL" >&2
    if [[ "$MODE" == "production" ]]; then
      echo "  Certbot: $CERTBOT_URL" >&2
    fi
    echo "" >&2
    echo "On Ubuntu/macOS (local) you can try: ./scripts/install-prerequisites.sh" >&2
    if [[ "$OS" == "windows" ]]; then
      echo "On Windows: install Docker Desktop manually and use Git Bash for scripts." >&2
    fi
  fi
  exit 1
fi

if ! docker_daemon_ok; then
  if [[ "$QUIET" == false ]]; then
    echo "Docker is installed but not running." >&2
    case "$OS" in
      macos|windows)
        echo "Start Docker Desktop, then try again." >&2
        ;;
      linux)
        echo "Try: sudo systemctl start docker" >&2
        echo "If you just installed Docker, log out and back in (docker group)." >&2
        ;;
      *)
        echo "Start the Docker service, then try again." >&2
        ;;
    esac
  fi
  exit 1
fi

if [[ "$MODE" == "production" ]]; then
  log "Prerequisites OK for online deploy (git, docker, docker compose, curl)."
  if [[ "$warnings" -gt 0 && "$QUIET" == false ]]; then
    echo "See warnings above before continuing." >&2
  fi
else
  log "Prerequisites OK (git, docker, docker compose, curl)."
  if [[ "$warnings" -gt 0 && "$QUIET" == false ]]; then
    echo "See warnings above before continuing." >&2
  fi
fi
