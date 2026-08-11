#!/usr/bin/env bash
# Export VITE_* build args for prod docker compose.
# Sources secrets.env, or .env, or ENV_FILE if set.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-}"
if [[ -z "$ENV_FILE" ]]; then
  if [[ -f secrets.env ]]; then
    ENV_FILE="secrets.env"
  elif [[ -f .env ]]; then
    ENV_FILE=".env"
  else
    echo "No secrets.env or .env found. Create one with ./scripts/setup.sh" >&2
    exit 1
  fi
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "${ENV_FILE} not found." >&2
  exit 1
fi

set -a
set +u
# shellcheck disable=SC1090
source "$ENV_FILE"
set -u
set +a

site_url="${SITE_URL%/}"
if [[ -z "${site_url}" ]]; then
  echo "SITE_URL must be set in ${ENV_FILE} for editor-ui production build." >&2
  exit 1
fi

export VITE_PUBLIC_SITE_BASE="${VITE_PUBLIC_SITE_BASE:-${site_url}}"
export VITE_API_BASE="$(./scripts/sanitize-vite-api-base.sh)"

echo "VITE_PUBLIC_SITE_BASE=${VITE_PUBLIC_SITE_BASE}"
echo "VITE_API_BASE=${VITE_API_BASE}"
