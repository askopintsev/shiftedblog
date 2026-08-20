#!/usr/bin/env bash
# Self-signed TLS for private deploy without a real domain (fake hostname + public IP).
#
# Reads DOMAIN, EDITOR_DOMAIN, SSL_CERT_NAME, SERVER_IP from secrets.env (or ENV_FILE).
#
# Usage:
#   ./scripts/generate-self-signed-cert.sh
#   ENV_FILE=secrets.env ./scripts/generate-self-signed-cert.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-secrets.env}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Env file not found: $ENV_FILE" >&2
  exit 1
fi

set -a
set +u
# shellcheck disable=SC1090
source "$ENV_FILE"
set -u
set +a

DOMAIN="${DOMAIN:-shiftedblog.local}"
EDITOR_DOMAIN="${EDITOR_DOMAIN:-editor.${DOMAIN}}"
SSL_CERT_NAME="${SSL_CERT_NAME:-${DOMAIN}}"
SERVER_IP="${SERVER_IP:-}"
CERT_DIR="/etc/letsencrypt/live/${SSL_CERT_NAME}"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root (writes under ${CERT_DIR})." >&2
  echo "  sudo $0" >&2
  exit 1
fi

mkdir -p "$CERT_DIR"
SAN="DNS:${EDITOR_DOMAIN},DNS:${DOMAIN}"
if [[ -n "$SERVER_IP" ]]; then
  SAN="${SAN},IP:${SERVER_IP}"
fi

echo "Writing self-signed certificate to ${CERT_DIR}"
echo "  SAN: ${SAN}"

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "${CERT_DIR}/privkey.pem" \
  -out "${CERT_DIR}/fullchain.pem" \
  -subj "/CN=${EDITOR_DOMAIN}" \
  -addext "subjectAltName=${SAN}"

chmod 600 "${CERT_DIR}/privkey.pem"
echo "Done. Regenerate nginx if needed: ENV_FILE=${ENV_FILE} ./scripts/generate-nginx-conf.sh"
