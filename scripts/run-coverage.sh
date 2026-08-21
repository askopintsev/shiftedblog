#!/usr/bin/env bash
# Run Django tests with coverage.py and fail if the project is under the
# configured [tool.coverage.report] fail_under threshold.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

uv run --extra dev --python 3.14 coverage run manage.py test --verbosity="${VERBOSITY:-1}"
uv run --extra dev --python 3.14 coverage xml -o coverage.xml
uv run --extra dev --python 3.14 coverage json -o coverage.json
uv run --extra dev --python 3.14 coverage report
