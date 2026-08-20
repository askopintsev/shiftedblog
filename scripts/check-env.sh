#!/usr/bin/env bash
# Validate required environment variables for local or online (server) deploy.
#
# Usage:
#   ./scripts/check-env.sh local
#   ./scripts/check-env.sh online
#   ENV_FILE=secrets.env ./scripts/check-env.sh online
#   ./scripts/check-env.sh production  # alias for online
set -euo pipefail

MODE="${1:-local}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

case "$MODE" in
  local) ;;
  online|production) MODE="production" ;;
  *)
    echo "Usage: $0 local|online" >&2
    exit 2
    ;;
esac

ENV_FILE="${ENV_FILE:-}"
if [[ -z "$ENV_FILE" ]]; then
  if [[ "$MODE" == "production" ]]; then
    ENV_FILE="secrets.env"
  else
    ENV_FILE=".env"
  fi
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Env file not found: $ENV_FILE" >&2
  exit 1
fi

set -a
set +u
# shellcheck disable=SC1090
source "$ENV_FILE"
set -u
set +a

errors=0
warn() { echo "WARNING: $*" >&2; }
fail() { echo "ERROR: $*" >&2; errors=$((errors + 1)); }

require() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    fail "$name is required in $ENV_FILE"
  fi
}

require SECRET_KEY
require DB_NAME
require DB_USER
require DB_PASS
require POSTGRES_DB
require POSTGRES_USER
require POSTGRES_PASSWORD

if [[ "${DB_NAME}" != "${POSTGRES_DB}" ]]; then
  fail "DB_NAME must match POSTGRES_DB"
fi
if [[ "${DB_USER}" != "${POSTGRES_USER}" ]]; then
  fail "DB_USER must match POSTGRES_USER"
fi
if [[ "${DB_PASS}" != "${POSTGRES_PASSWORD}" ]]; then
  fail "DB_PASS must match POSTGRES_PASSWORD"
fi

debug_val="$(echo "${DEBUG:-False}" | tr '[:upper:]' '[:lower:]')"
site_url="${SITE_URL:-}"

if [[ "$MODE" == "production" ]]; then
  require SITE_URL
  require ALLOWED_HOSTS
  require CSRF_TRUSTED_ORIGINS
  if [[ "$debug_val" == "true" || "$debug_val" == "1" || "$debug_val" == "yes" ]]; then
    fail "DEBUG must be False in production"
  fi
  if [[ "$site_url" != https://* ]]; then
    fail "SITE_URL must be an https:// URL in production"
  fi
  if [[ "$site_url" == *localhost* || "$site_url" == *127.0.0.1* ]]; then
    fail "SITE_URL must not be localhost in production"
  fi
  if [[ "${SECRET_KEY}" == *"change-this"* || "${SECRET_KEY}" == *"insecure"* ]]; then
    fail "SECRET_KEY looks like a placeholder; generate a real key"
  fi
  if [[ -z "${CREDENTIALS_ENCRYPTION_KEY:-}" ]]; then
    warn "CREDENTIALS_ENCRYPTION_KEY is empty (needed for multi-channel / Telegram credentials)"
  fi
else
  if [[ -z "$site_url" ]]; then
    warn "SITE_URL is unset; Django will derive it from ALLOWED_HOSTS"
  fi
fi

MODE_LABEL="$MODE"
if [[ "$MODE" == "production" ]]; then
  MODE_LABEL="online"
fi

if [[ "$errors" -gt 0 ]]; then
  echo "check-env: $errors error(s) in $ENV_FILE ($MODE_LABEL)" >&2
  exit 1
fi

echo "check-env: $ENV_FILE OK for $MODE_LABEL"
