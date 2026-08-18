#!/usr/bin/env bash
# Render nginx/nginx.conf from nginx/nginx.conf.template.
#
# Usage:
#   ./scripts/generate-nginx-conf.sh
#   DOMAIN=example.com EDITOR_DOMAIN=editor.example.com ./scripts/generate-nginx-conf.sh
#
# Reads DOMAIN / SITE_URL / EXTRA_DOMAINS / EDITOR_DOMAIN / SSL_CERT_NAME /
# SERVER_IP / REDIRECT_FROM_DOMAINS / REDIRECT_FROM_EDITOR_DOMAINS
# from the environment, or from secrets.env / .env if present.
#
# EXTRA_DOMAINS serves the same site (duplicate hosts). Use REDIRECT_FROM_*
# for legacy names that must 301 to SITE_URL / EDITOR_DOMAIN.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

load_env_file() {
  local file="$1"
  if [[ -f "$file" ]]; then
    set -a
    set +u
    # shellcheck disable=SC1090
    source "$file"
    set -u
    set +a
  fi
}

CLI_DOMAIN="${DOMAIN:-}"
CLI_EDITOR_DOMAIN="${EDITOR_DOMAIN:-}"
CLI_SSL_CERT_NAME="${SSL_CERT_NAME:-}"
CLI_EXTRA_DOMAINS="${EXTRA_DOMAINS:-}"
CLI_SERVER_IP="${SERVER_IP:-}"
CLI_SITE_URL="${SITE_URL:-}"
CLI_REDIRECT_FROM="${REDIRECT_FROM_DOMAINS:-}"
CLI_REDIRECT_FROM_EDITOR="${REDIRECT_FROM_EDITOR_DOMAINS:-}"

if [[ -n "${ENV_FILE:-}" && -f "$ENV_FILE" ]]; then
  load_env_file "$ENV_FILE"
elif [[ -f secrets.env ]]; then
  load_env_file secrets.env
elif [[ -f .env ]]; then
  load_env_file .env
fi

export DOMAIN="${CLI_DOMAIN:-${DOMAIN:-}}"
export EDITOR_DOMAIN="${CLI_EDITOR_DOMAIN:-${EDITOR_DOMAIN:-}}"
export SSL_CERT_NAME="${CLI_SSL_CERT_NAME:-${SSL_CERT_NAME:-}}"
export EXTRA_DOMAINS="${CLI_EXTRA_DOMAINS:-${EXTRA_DOMAINS:-}}"
export SERVER_IP="${CLI_SERVER_IP:-${SERVER_IP:-}}"
export SITE_URL="${CLI_SITE_URL:-${SITE_URL:-}}"
export REDIRECT_FROM_DOMAINS="${CLI_REDIRECT_FROM:-${REDIRECT_FROM_DOMAINS:-}}"
export REDIRECT_FROM_EDITOR_DOMAINS="${CLI_REDIRECT_FROM_EDITOR:-${REDIRECT_FROM_EDITOR_DOMAINS:-}}"

TEMPLATE="${ROOT}/nginx/nginx.conf.template"
OUTPUT="${ROOT}/nginx/nginx.conf"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "Missing template: $TEMPLATE" >&2
  exit 1
fi

python3 "${ROOT}/scripts/render_nginx_conf.py" "$TEMPLATE" "$OUTPUT"
