#!/usr/bin/env bash
# Generate a read-only deploy key for git pull on the VPS (GitHub Deploy Keys).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KEY_DIR="${1:-$ROOT/scripts/ssh/keys/git-deploy}"
KEY_FILE="$KEY_DIR/id_ed25519"
REPO="${GITHUB_REPO:-askopintsev/shiftedblog}"

mkdir -p "$KEY_DIR"
chmod 700 "$KEY_DIR"

if [[ -f "$KEY_FILE" ]]; then
  echo "Key already exists: $KEY_FILE"
  echo "Remove it first or pass another directory as the first argument."
  exit 1
fi

ssh-keygen -t ed25519 -f "$KEY_FILE" -N "" -C "shiftedblog-vps-git-deploy"

echo ""
echo "=== Git deploy key created ==="
echo "1. GitHub repo -> Settings -> Deploy keys -> Add deploy key"
echo "   Title: shiftedblog-vps-git-deploy"
echo "   Key (read-only):"
cat "${KEY_FILE}.pub"
echo ""
echo "2. On the VPS, install the PRIVATE key and SSH config:"
echo "   scripts/ssh/install-server-git-access.sh"
echo "   (copy $KEY_FILE and ${KEY_FILE}.pub to the server first, e.g. scp)"
echo ""
echo "3. Use SSH remote on the server:"
echo "   git remote set-url origin git@github.com:${REPO}.git"
