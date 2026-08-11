#!/usr/bin/env bash
# Render nginx/nginx.conf from nginx/nginx.conf.template.
#
# Usage:
#   ./scripts/generate-nginx-conf.sh
#   DOMAIN=example.com EDITOR_DOMAIN=editor.example.com ./scripts/generate-nginx-conf.sh
#
# Reads DOMAIN / EXTRA_DOMAINS / EDITOR_DOMAIN / SSL_CERT_NAME / SERVER_IP
# from the environment, or from secrets.env / .env if present.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

load_env_file() {
  local file="$1"
  if [[ -f "$file" ]]; then
    set -a
    set +u
    # shellcheck disable=SC1090
    source "$file"
    set -u
    set +a
  fi
}

# Preserve explicitly exported vars over values from env files.
CLI_DOMAIN="${DOMAIN:-}"
CLI_EDITOR_DOMAIN="${EDITOR_DOMAIN:-}"
CLI_SSL_CERT_NAME="${SSL_CERT_NAME:-}"
CLI_EXTRA_DOMAINS="${EXTRA_DOMAINS:-}"
CLI_SERVER_IP="${SERVER_IP:-}"

if [[ -f secrets.env ]]; then
  load_env_file secrets.env
elif [[ -f .env ]]; then
  load_env_file .env
fi

DOMAIN="${CLI_DOMAIN:-${DOMAIN:-}}"
EDITOR_DOMAIN="${CLI_EDITOR_DOMAIN:-${EDITOR_DOMAIN:-}}"
SSL_CERT_NAME="${CLI_SSL_CERT_NAME:-${SSL_CERT_NAME:-}}"
EXTRA_DOMAINS="${CLI_EXTRA_DOMAINS:-${EXTRA_DOMAINS:-}}"
SERVER_IP="${CLI_SERVER_IP:-${SERVER_IP:-}}"

DOMAIN="${DOMAIN:-}"
if [[ -z "$DOMAIN" && -n "${SITE_URL:-}" ]]; then
  DOMAIN="${SITE_URL#https://}"
  DOMAIN="${DOMAIN#http://}"
  DOMAIN="${DOMAIN%%/*}"
  DOMAIN="${DOMAIN%%:*}"
fi

if [[ -z "$DOMAIN" ]]; then
  echo "DOMAIN (or SITE_URL) is required." >&2
  exit 1
fi

EDITOR_DOMAIN="${EDITOR_DOMAIN:-editor.${DOMAIN}}"
SSL_CERT_NAME="${SSL_CERT_NAME:-${DOMAIN}}"
EXTRA_DOMAINS="${EXTRA_DOMAINS:-}"
SERVER_IP="${SERVER_IP:-}"
WWW_DOMAIN="www.${DOMAIN}"

http_names=("${DOMAIN}" "${WWW_DOMAIN}" "${EDITOR_DOMAIN}")
https_names=("${DOMAIN}" "${WWW_DOMAIN}")
editor_names=("${EDITOR_DOMAIN}")

if [[ -n "$EXTRA_DOMAINS" ]]; then
  IFS=',' read -r -a extras <<< "$EXTRA_DOMAINS"
  for host in "${extras[@]}"; do
    host="$(echo "$host" | xargs)"
    [[ -z "$host" ]] && continue
    http_names+=("$host")
    if [[ "$host" == editor.* ]]; then
      editor_names+=("$host")
    else
      https_names+=("$host")
    fi
  done
fi

if [[ -n "$SERVER_IP" ]]; then
  http_names+=("$SERVER_IP")
  https_names+=("$SERVER_IP")
fi

join_names() {
  local out=""
  local n
  for n in "$@"; do
    if [[ -z "$out" ]]; then
      out="$n"
    else
      out+=$'\n'"                    $n"
    fi
  done
  printf '%s' "$out"
}

export HTTP_SERVER_NAMES
export HTTPS_SERVER_NAMES
export EDITOR_SERVER_NAMES
export SSL_CERTIFICATE
export SSL_CERTIFICATE_KEY
export CSP_CONNECT_ORIGINS

HTTP_SERVER_NAMES="$(join_names "${http_names[@]}")"
HTTPS_SERVER_NAMES="$(join_names "${https_names[@]}")"
EDITOR_SERVER_NAMES="$(join_names "${editor_names[@]}")"
SSL_CERTIFICATE="/etc/letsencrypt/live/${SSL_CERT_NAME}/fullchain.pem"
SSL_CERTIFICATE_KEY="/etc/letsencrypt/live/${SSL_CERT_NAME}/privkey.pem"

csp_origins=("https://${DOMAIN}" "https://${WWW_DOMAIN}")
if [[ -n "$EXTRA_DOMAINS" ]]; then
  IFS=',' read -r -a extras <<< "$EXTRA_DOMAINS"
  for host in "${extras[@]}"; do
    host="$(echo "$host" | xargs)"
    [[ -z "$host" || "$host" == editor.* ]] && continue
    csp_origins+=("https://${host}")
  done
fi
CSP_CONNECT_ORIGINS="$(IFS=' '; echo "${csp_origins[*]}")"

# Re-export after assignment
export HTTP_SERVER_NAMES HTTPS_SERVER_NAMES EDITOR_SERVER_NAMES
export SSL_CERTIFICATE SSL_CERTIFICATE_KEY CSP_CONNECT_ORIGINS

TEMPLATE="${ROOT}/nginx/nginx.conf.template"
OUTPUT="${ROOT}/nginx/nginx.conf"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "Missing template: $TEMPLATE" >&2
  exit 1
fi

python3 - "$TEMPLATE" "$OUTPUT" <<'PY'
import os
import sys
from pathlib import Path

template_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
text = template_path.read_text(encoding="utf-8")
replacements = {
    "__HTTP_SERVER_NAMES__": os.environ["HTTP_SERVER_NAMES"],
    "__HTTPS_SERVER_NAMES__": os.environ["HTTPS_SERVER_NAMES"],
    "__EDITOR_SERVER_NAMES__": os.environ["EDITOR_SERVER_NAMES"],
    "__SSL_CERTIFICATE__": os.environ["SSL_CERTIFICATE"],
    "__SSL_CERTIFICATE_KEY__": os.environ["SSL_CERTIFICATE_KEY"],
    "__CSP_CONNECT_ORIGINS__": os.environ["CSP_CONNECT_ORIGINS"],
}
for key, value in replacements.items():
    text = text.replace(key, value)
output_path.write_text(text, encoding="utf-8")
print(f"Wrote {output_path}")
PY
