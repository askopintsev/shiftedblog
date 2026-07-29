#!/usr/bin/env bash
# Fail if requirements.txt body does not match uv export (skip uv header comment).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

uv export --no-dev -o requirements.txt.check
tail -n +3 requirements.txt > requirements.body
tail -n +3 requirements.txt.check > requirements.check.body
if ! diff -q requirements.body requirements.check.body >/dev/null 2>&1; then
  diff -u requirements.body requirements.check.body || true
  rm -f requirements.txt.check requirements.body requirements.check.body
  exit 1
fi
rm -f requirements.txt.check requirements.body requirements.check.body
