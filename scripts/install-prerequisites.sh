#!/usr/bin/env bash
# Optional interactive install of local prerequisites (Linux apt/dnf, macOS Homebrew).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

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

detect_linux_pkg() {
  if command -v apt-get >/dev/null 2>&1; then
    echo "apt"
  elif command -v dnf >/dev/null 2>&1; then
    echo "dnf"
  else
    echo "unknown"
  fi
}

need_git=false
need_curl=false
need_docker=false

command -v git >/dev/null 2>&1 || need_git=true
command -v curl >/dev/null 2>&1 || need_curl=true
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  need_docker=true
fi

if [[ "$need_git" == false && "$need_curl" == false && "$need_docker" == false ]]; then
  echo "All supported prerequisites are already installed."
  ./scripts/check-prerequisites.sh local
  exit 0
fi

echo "This script can install missing tools on Ubuntu/Debian, Fedora/RHEL, or macOS (Homebrew)."
echo "Windows: install Docker Desktop manually — $DOCKER_URL"
echo ""
read -r -p "Install missing prerequisites now? [y/N]: " confirm
confirm="${confirm:-N}"
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
  echo "Skipped. Install manually:"
  echo "  Git:    $GIT_URL"
  echo "  Docker: $DOCKER_URL"
  exit 0
fi

OS="$(detect_os)"
installed_docker=false

case "$OS" in
  linux)
    PKG="$(detect_linux_pkg)"
    case "$PKG" in
      apt)
        sudo apt-get update
        pkgs=()
        [[ "$need_git" == true ]] && pkgs+=(git)
        [[ "$need_curl" == true ]] && pkgs+=(curl)
        [[ "$need_docker" == true ]] && pkgs+=(docker.io docker-compose-plugin)
        if [[ "${#pkgs[@]}" -gt 0 ]]; then
          sudo apt-get install -y "${pkgs[@]}"
        fi
        installed_docker=$need_docker
        ;;
      dnf)
        pkgs=()
        [[ "$need_git" == true ]] && pkgs+=(git)
        [[ "$need_curl" == true ]] && pkgs+=(curl)
        [[ "$need_docker" == true ]] && pkgs+=(docker docker-compose-plugin)
        if [[ "${#pkgs[@]}" -gt 0 ]]; then
          sudo dnf install -y "${pkgs[@]}"
        fi
        installed_docker=$need_docker
        ;;
      *)
        echo "Unsupported Linux package manager. Install manually:" >&2
        echo "  Git:    $GIT_URL" >&2
        echo "  Docker: $DOCKER_URL" >&2
        exit 1
        ;;
    esac
    if [[ "$installed_docker" == true ]]; then
      if ! groups "$USER" | grep -q '\bdocker\b'; then
        sudo usermod -aG docker "$USER"
        echo ""
        echo "Added $USER to the docker group."
        echo "Log out and back in (or reboot), then start Docker:"
        echo "  sudo systemctl enable --now docker"
        echo "Then run ./scripts/setup.sh again."
      else
        sudo systemctl enable --now docker 2>/dev/null || true
        echo "Start Docker if needed: sudo systemctl start docker"
      fi
    fi
    ;;
  macos)
    if ! command -v brew >/dev/null 2>&1; then
      echo "Homebrew not found. Install from https://brew.sh then re-run this script." >&2
      exit 1
    fi
    [[ "$need_git" == true ]] && brew install git
    [[ "$need_curl" == true ]] && brew install curl
    if [[ "$need_docker" == true ]]; then
      brew install --cask docker
      echo ""
      echo "Open Docker Desktop from Applications and wait until it is running."
      echo "Then run ./scripts/setup.sh again."
    fi
    ;;
  windows)
    echo "Automatic install is not supported on Windows." >&2
    echo "Install Docker Desktop: $DOCKER_URL" >&2
    echo "Use Git Bash for ./scripts/setup.sh and start-shiftedblog.bat" >&2
    exit 1
    ;;
  *)
    echo "Unsupported OS. Install manually:" >&2
    echo "  Git:    $GIT_URL" >&2
    echo "  Docker: $DOCKER_URL" >&2
    exit 1
    ;;
esac

echo ""
./scripts/check-prerequisites.sh local || {
  echo "Some prerequisites are still missing or Docker is not running yet." >&2
  exit 1
}
