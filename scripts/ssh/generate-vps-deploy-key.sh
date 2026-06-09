#!/usr/bin/env bash
# Generate an SSH key pair for GitHub Actions -> VPS deploy (appleboy/ssh-action).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KEY_DIR="${1:-$ROOT/scripts/ssh/keys/vps-deploy}"
KEY_FILE="$KEY_DIR/id_ed25519"

mkdir -p "$KEY_DIR"
chmod 700 "$KEY_DIR"

if [[ -f "$KEY_FILE" ]]; then
  echo "Key already exists: $KEY_FILE"
  echo "Remove it first or pass another directory as the first argument."
  exit 1
fi

ssh-keygen -t ed25519 -f "$KEY_FILE" -N "" -C "shiftedblog-github-actions-vps"

echo ""
echo "=== VPS deploy key created ==="
echo "Public key (add to SERVER ~/.ssh/authorized_keys for the deploy user):"
cat "${KEY_FILE}.pub"
echo ""
echo "Private key (paste entire file into GitHub repo secret VPS_SSH_KEY):"
echo "  Settings -> Secrets and variables -> Actions -> VPS_SSH_KEY"
echo "  File: $KEY_FILE"
echo ""
echo "Also set secrets: VPS_HOST, VPS_USERNAME, VPS_PORT (usually 22)."
