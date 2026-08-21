#!/usr/bin/env bash
# Run Django tests with coverage.py and fail if the project is under the
# configured [tool.coverage.report] fail_under threshold.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if [[ -z "${CREDENTIALS_ENCRYPTION_KEY:-}" ]]; then
  CREDENTIALS_ENCRYPTION_KEY="$(
    uv run --extra dev --python 3.14 python -c \
      'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
  )"
  export CREDENTIALS_ENCRYPTION_KEY
fi

uv run --extra dev --python 3.14 coverage run manage.py test --verbosity="${VERBOSITY:-1}"
uv run --extra dev --python 3.14 coverage xml -o coverage.xml
uv run --extra dev --python 3.14 coverage json -o coverage.json
uv run --extra dev --python 3.14 coverage report
