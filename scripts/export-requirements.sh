#!/usr/bin/env bash
# Regenerate requirements.txt from uv.lock for Docker (pip install -r).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
uv export --no-dev -o requirements.txt
echo "Wrote requirements.txt from uv.lock"
