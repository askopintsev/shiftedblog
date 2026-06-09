#!/usr/bin/env bash
# Run ON THE VPS as the user that owns /opt/shiftedblog.
# Installs a GitHub deploy key for passwordless git pull (no HTTPS tokens).
set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-$USER}"
SSH_DIR="${HOME}/.ssh"
KEY_NAME="shiftedblog_git_deploy"
KEY_PATH="${SSH_DIR}/${KEY_NAME}"
REPO="${GITHUB_REPO:-askopintsev/shiftedblog}"
APP_DIR="${APP_DIR:-/opt/shiftedblog}"

if [[ ! -f "${KEY_PATH}" ]]; then
  echo "Missing private key: ${KEY_PATH}"
  echo "Copy the git deploy private key from generate-git-deploy-key.sh to that path."
  echo "  chmod 600 ${KEY_PATH}"
  exit 1
fi

mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"
chmod 600 "$KEY_PATH"
if [[ -f "${KEY_PATH}.pub" ]]; then
  chmod 644 "${KEY_PATH}.pub"
fi

CONFIG_BLOCK="
Host github.com-shiftedblog
    HostName github.com
    User git
    IdentityFile ${KEY_PATH}
    IdentitiesOnly yes
"

if ! grep -q "Host github.com-shiftedblog" "${SSH_DIR}/config" 2>/dev/null; then
  printf "%s\n" "$CONFIG_BLOCK" >> "${SSH_DIR}/config"
  chmod 600 "${SSH_DIR}/config"
  echo "Appended github.com-shiftedblog to ~/.ssh/config"
else
  echo "~/.ssh/config already has github.com-shiftedblog"
fi

ssh -o StrictHostKeyChecking=accept-new -T git@github.com-shiftedblog || true

if [[ -d "${APP_DIR}/.git" ]]; then
  cd "$APP_DIR"
  git remote set-url origin "git@github.com-shiftedblog:${REPO}.git"
  echo "Git remote updated in ${APP_DIR}"
  git remote -v
else
  echo "Clone with:"
  echo "  git clone git@github.com-shiftedblog:${REPO}.git ${APP_DIR}"
fi

echo "Git deploy key access is ready."
