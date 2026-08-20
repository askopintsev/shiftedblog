#!/usr/bin/env bash
set -euo pipefail

cd /editor-ui

if [[ ! -x node_modules/.bin/vite ]]; then
  echo "Installing editor UI dependencies (first run may take a minute)..."
  npm ci || npm install
fi

exec npm run dev
