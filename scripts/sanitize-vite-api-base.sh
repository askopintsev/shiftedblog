#!/usr/bin/env bash
# Normalize VITE_API_BASE for editor-ui Docker builds.
# Doppler may still have a legacy value like https://shiftedstuff.ru (missing /api/editor/v1).
set -euo pipefail

value="${VITE_API_BASE:-}"

if [[ -z "${value}" || "${value}" == "/api/editor/v1" || "${value}" == /api/editor/v1/* ]]; then
  echo "/api/editor/v1"
  exit 0
fi

if [[ "${value}" == http* && "${value}" != *"/api/editor/"* ]]; then
  echo "WARNING: invalid VITE_API_BASE=${value}; using /api/editor/v1" >&2
  echo "/api/editor/v1"
  exit 0
fi

echo "${value%/}"
