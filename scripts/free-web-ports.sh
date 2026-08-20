#!/usr/bin/env bash
# Release host ports 80/443 before starting ShiftedBlog nginx in Docker.
#
# Usage (from repo root):
#   ./scripts/free-web-ports.sh
#   COMPOSE_FILE=docker-compose.prod.yml WAIT_SECONDS=45 ./scripts/free-web-ports.sh /opt/shiftedblog
set -euo pipefail

ROOT="$(cd "${1:-.}" && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
WAIT_SECONDS="${WAIT_SECONDS:-30}"

cd "$ROOT"

compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

port_in_use() {
  local port="$1"
  ss -tln 2>/dev/null | grep -qE ":${port} "
}

kill_port_listeners() {
  local port="$1"
  if ! command -v fuser >/dev/null 2>&1; then
    return 0
  fi
  local pid comm
  for pid in $(fuser -n tcp "${port}" 2>/dev/null || true); do
    [[ "$pid" =~ ^[0-9]+$ ]] || continue
    comm="$(ps -p "$pid" -o comm= 2>/dev/null || true)"
    echo "Port ${port}: stopping pid ${pid} (${comm})..."
    kill "$pid" 2>/dev/null || true
  done
}

wait_for_ports() {
  local attempt
  for ((attempt = 1; attempt <= WAIT_SECONDS; attempt++)); do
    if ! port_in_use 80 && ! port_in_use 443; then
      return 0
    fi
    if ((attempt % 5 == 0)); then
      kill_port_listeners 80
      kill_port_listeners 443
    fi
    sleep 1
  done
  return 1
}

remove_docker_publishers() {
  local port="$1"
  local cid
  while read -r cid; do
    [[ -n "$cid" ]] || continue
    echo "Removing container ${cid} still publishing port ${port}..."
    docker rm -f "$cid" || true
  done < <(docker ps -aq --filter "publish=${port}" 2>/dev/null || true)
}

echo "Releasing ports 80/443..."

if [[ -f "${COMPOSE_FILE}" ]]; then
  compose stop nginx 2>/dev/null || true
  compose rm -f nginx 2>/dev/null || true
fi

remove_docker_publishers 80
remove_docker_publishers 443

if command -v systemctl >/dev/null 2>&1; then
  systemctl stop nginx apache2 2>/dev/null || true
fi

if wait_for_ports; then
  echo "Ports 80/443 are free."
  exit 0
fi

echo "Ports 80/443 are still in use:" >&2
ss -tlnp 2>/dev/null | grep -E ':(80|443) ' || true
echo "Stop the process above, or run: docker compose -f ${COMPOSE_FILE} down" >&2
exit 1
