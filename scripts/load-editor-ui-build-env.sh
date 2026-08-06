#!/usr/bin/env bash
# Export VITE_* build args for prod docker compose (source secrets.env first).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if [[ ! -f secrets.env ]]; then
  echo "secrets.env not found; run doppler secrets download first." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source secrets.env
set +a

site_url="${SITE_URL%/}"
if [[ -z "${site_url}" ]]; then
  echo "SITE_URL must be set in secrets.env for editor-ui production build." >&2
  exit 1
fi

export VITE_PUBLIC_SITE_BASE="${VITE_PUBLIC_SITE_BASE:-${site_url}}"
export VITE_API_BASE="${VITE_API_BASE:-/api/editor/v1}"

echo "VITE_PUBLIC_SITE_BASE=${VITE_PUBLIC_SITE_BASE}"
echo "VITE_API_BASE=${VITE_API_BASE}"
