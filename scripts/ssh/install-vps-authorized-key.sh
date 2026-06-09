#!/usr/bin/env bash
# Run ON THE VPS to allow GitHub Actions SSH (public key from generate-vps-deploy-key.sh).
set -euo pipefail

SSH_DIR="${HOME}/.ssh"
AUTH_KEYS="${SSH_DIR}/authorized_keys"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /path/to/id_ed25519.pub"
  echo "   or: $0 \"ssh-ed25519 AAAA... comment\""
  exit 1
fi

mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"
touch "$AUTH_KEYS"
chmod 600 "$AUTH_KEYS"

if [[ -f "$1" ]]; then
  PUBKEY="$(cat "$1")"
else
  PUBKEY="$1"
fi

FINGERPRINT="$(ssh-keygen -lf <(echo "$PUBKEY") 2>/dev/null | awk '{print $2}')"
if grep -qF "$PUBKEY" "$AUTH_KEYS" 2>/dev/null; then
  echo "Key already in authorized_keys (${FINGERPRINT})"
  exit 0
fi

echo "$PUBKEY" >> "$AUTH_KEYS"
echo "Added deploy key to ${AUTH_KEYS} (${FINGERPRINT})"
