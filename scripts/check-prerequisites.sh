#!/usr/bin/env bash
# Check tools required for local ShiftedBlog (git, docker, compose, curl).
#
# Usage:
#   ./scripts/check-prerequisites.sh local
#   ./scripts/check-prerequisites.sh local --quiet
set -euo pipefail

MODE="local"
QUIET=false
for arg in "$@"; do
  case "$arg" in
    --quiet) QUIET=true ;;
    local) MODE="local" ;;
    *)
      echo "Usage: $0 local [--quiet]" >&2
      exit 2
      ;;
  esac
done

GIT_URL="https://git-scm.com/downloads"
DOCKER_URL="https://docs.docker.com/get-docker/"

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
missing=()

log() {
  if [[ "$QUIET" == false ]]; then
    echo "$@"
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

docker_daemon_ok() {
  docker info >/dev/null 2>&1
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

if [[ "$errors" -gt 0 ]]; then
  if [[ "$QUIET" == false ]]; then
    echo "Missing prerequisites for local ShiftedBlog:" >&2
    for item in "${missing[@]}"; do
      echo "  - $item" >&2
    done
    echo "" >&2
    echo "Download and install:" >&2
    echo "  Git:    $GIT_URL" >&2
    echo "  Docker: $DOCKER_URL" >&2
    echo "" >&2
    echo "On Ubuntu/macOS you can try: ./scripts/install-prerequisites.sh" >&2
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

log "Prerequisites OK (git, docker, docker compose, curl)."
