#!/usr/bin/env bash
# Stop local Docker stack (keeps database volumes).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

docker compose down
echo "ShiftedBlog stopped."
