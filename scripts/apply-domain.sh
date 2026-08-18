#!/usr/bin/env bash
# Update domain-related keys in an existing secrets.env without rotating
# SECRET_KEY, CREDENTIALS_ENCRYPTION_KEY, ADMIN_URL, or database passwords.
#
# Usage:
#   ./scripts/apply-domain.sh --domain example.com
#   ./scripts/apply-domain.sh --domain example.com \
#       --site-url https://www.example.com \
#       --editor-domain editor.example.com \
#       --redirect-from old.com,www.old.com \
#       --redirect-from-editor editor.old.com
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-secrets.env}"
DOMAIN_IN=""
SITE_URL_IN=""
EDITOR_IN=""
CERT_IN=""
EXTRA_IN=""
SERVER_IP_IN=""
REDIRECT_IN=""
REDIRECT_EDITOR_IN=""
REDIRECT_FROM_SET=0
REDIRECT_EDITOR_SET=0

usage() {
  sed -n '2,16p' "$0" | sed 's/^# \?//'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --domain)
      DOMAIN_IN="$2"
      shift 2
      ;;
    --site-url)
      SITE_URL_IN="$2"
      shift 2
      ;;
    --editor-domain)
      EDITOR_IN="$2"
      shift 2
      ;;
    --ssl-cert-name)
      CERT_IN="$2"
      shift 2
      ;;
    --extra-domains)
      EXTRA_IN="$2"
      shift 2
      ;;
    --server-ip)
      SERVER_IP_IN="$2"
      shift 2
      ;;
    --redirect-from)
      REDIRECT_IN="$2"
      REDIRECT_FROM_SET=1
      shift 2
      ;;
    --redirect-from-editor)
      REDIRECT_EDITOR_IN="$2"
      REDIRECT_EDITOR_SET=1
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$DOMAIN_IN" ]]; then
  echo "--domain is required." >&2
  exit 2
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Env file not found: $ENV_FILE (create it with ./scripts/setup.sh first)." >&2
  exit 1
fi

if [[ "$DOMAIN_IN" == www.* ]]; then
  DOMAIN_IN="${DOMAIN_IN#www.}"
fi

SITE_URL_IN="${SITE_URL_IN:-https://${DOMAIN_IN}}"
SITE_URL_IN="${SITE_URL_IN%/}"
EDITOR_IN="${EDITOR_IN:-editor.${DOMAIN_IN}}"
CERT_IN="${CERT_IN:-${DOMAIN_IN}}"

upsert_env() {
  local file="$1"
  local key="$2"
  local value="$3"
  python3 - "$file" "$key" "$value" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
out = []
found = False
for line in lines:
    if line.startswith(f"{key}=") or line.startswith(f"# {key}="):
        out.append(f"{key}={value}")
        found = True
    else:
        out.append(line)
if not found:
    out.append(f"{key}={value}")
path.write_text("\n".join(out) + "\n", encoding="utf-8")
PY
}

upsert_env "$ENV_FILE" "DOMAIN" "$DOMAIN_IN"
upsert_env "$ENV_FILE" "EDITOR_DOMAIN" "$EDITOR_IN"
upsert_env "$ENV_FILE" "SSL_CERT_NAME" "$CERT_IN"
upsert_env "$ENV_FILE" "SITE_URL" "$SITE_URL_IN"
upsert_env "$ENV_FILE" "ALLOWED_HOSTS" "${DOMAIN_IN},www.${DOMAIN_IN},${EDITOR_IN},localhost,127.0.0.1"
upsert_env "$ENV_FILE" "CSRF_TRUSTED_ORIGINS" "https://${DOMAIN_IN},https://www.${DOMAIN_IN},https://${EDITOR_IN}"
upsert_env "$ENV_FILE" "EDITOR_URL" "https://${EDITOR_IN}"
upsert_env "$ENV_FILE" "CORS_ALLOWED_ORIGINS" "https://${EDITOR_IN}"
upsert_env "$ENV_FILE" "SESSION_COOKIE_DOMAIN" ".${DOMAIN_IN}"
upsert_env "$ENV_FILE" "CSRF_COOKIE_DOMAIN" ".${DOMAIN_IN}"
upsert_env "$ENV_FILE" "VITE_PUBLIC_SITE_BASE" "$SITE_URL_IN"
upsert_env "$ENV_FILE" "VITE_API_BASE" "/api/editor/v1"

if [[ -n "$EXTRA_IN" ]]; then
  upsert_env "$ENV_FILE" "EXTRA_DOMAINS" "$EXTRA_IN"
fi
if [[ -n "$SERVER_IP_IN" ]]; then
  upsert_env "$ENV_FILE" "SERVER_IP" "$SERVER_IP_IN"
fi
if [[ "$REDIRECT_FROM_SET" -eq 1 ]]; then
  upsert_env "$ENV_FILE" "REDIRECT_FROM_DOMAINS" "$REDIRECT_IN"
fi
if [[ "$REDIRECT_EDITOR_SET" -eq 1 ]]; then
  upsert_env "$ENV_FILE" "REDIRECT_FROM_EDITOR_DOMAINS" "$REDIRECT_EDITOR_IN"
fi

ENV_FILE="$ENV_FILE" ./scripts/check-env.sh production
./scripts/generate-nginx-conf.sh

echo ""
echo "Updated $ENV_FILE (crypto keys and ADMIN_URL left unchanged)."
echo "Nginx regenerated. Rebuild the SPA with ./deploy.sh so VITE_* take effect."
echo "Issue or expand a Let's Encrypt cert that covers SITE_URL, editor, and REDIRECT_FROM_* names."
