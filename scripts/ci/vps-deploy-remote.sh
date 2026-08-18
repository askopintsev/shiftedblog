#!/usr/bin/env bash
# Remote production deploy (invoked from GitHub Actions over SSH).
set -euo pipefail

ROOT="${DEPLOY_ROOT:-/opt/shiftedblog}"
cd "$ROOT"

echo "Project directory: $(pwd)"

export PATH="${HOME}/.local/bin:/usr/local/bin:${PATH}"

ensure_doppler() {
  if command -v doppler >/dev/null 2>&1; then
    return 0
  fi
  echo "Installing Doppler CLI to ~/.local/bin..."
  mkdir -p "${HOME}/.local/bin"
  tmp="$(mktemp -d)"
  curl -fsSL -o "${tmp}/doppler.tgz" \
    "https://github.com/DopplerHQ/cli/releases/download/3.75.1/doppler_3.75.1_linux_amd64.tar.gz"
  tar -xzf "${tmp}/doppler.tgz" -C "${tmp}"
  install -m 0755 "${tmp}/doppler" "${HOME}/.local/bin/doppler"
  rm -rf "${tmp}"
}

sync_git() {
  echo "Syncing git checkout to origin/master..."
  git fetch origin master
  git reset --hard origin/master
}

download_secrets() {
  local tmp_secrets
  tmp_secrets="$(mktemp "${ROOT}/secrets.env.XXXXXX")"

  if [[ -n "${DOPPLER_TOKEN:-}" ]]; then
    ensure_doppler
    printf '%s' "${DOPPLER_TOKEN}" | doppler configure set token --scope "$ROOT" >/dev/null
    doppler secrets download --no-file --format=env >"${tmp_secrets}"
  elif [[ -s "${ROOT}/secrets.env" ]]; then
    echo "Using existing secrets.env on server."
    cp "${ROOT}/secrets.env" "${tmp_secrets}"
  else
    echo "secrets.env is missing and DOPPLER_TOKEN was not provided." >&2
    exit 1
  fi

  if [[ ! -s "${tmp_secrets}" ]]; then
    rm -f "${tmp_secrets}"
    echo "Refusing to replace secrets.env with an empty file." >&2
    exit 1
  fi

  if ! grep -qE '^SITE_URL=' "${tmp_secrets}"; then
    rm -f "${tmp_secrets}"
    echo "secrets.env must contain SITE_URL." >&2
    exit 1
  fi

  chmod 600 "${tmp_secrets}"
  mv "${tmp_secrets}" "${ROOT}/secrets.env"
  rm -f "${ROOT}/.env"
}

prepare_dirs() {
  mkdir -p logs backups static media static_blog
}

validate_and_build_env() {
  set -a
  # shellcheck disable=SC1091
  source secrets.env
  set +a
  site_url="${SITE_URL%/}"
  if [[ -z "${site_url}" ]]; then
    echo "SITE_URL must be set in secrets.env for editor-ui production build." >&2
    exit 1
  fi
  export VITE_PUBLIC_SITE_BASE="${VITE_PUBLIC_SITE_BASE:-${site_url}}"
  export VITE_API_BASE="$("${ROOT}/scripts/sanitize-vite-api-base.sh")"
  echo "Editor UI build: VITE_API_BASE=${VITE_API_BASE}"
}

deploy_containers() {
  docker compose -f docker-compose.prod.yml down || echo "No containers to stop"

  docker builder prune -af || true
  docker image prune -af || true
  df -h / /var/lib/docker 2>/dev/null || df -h /

  docker compose -f docker-compose.prod.yml build web
  docker compose -f docker-compose.prod.yml up -d
  docker compose -f docker-compose.prod.yml exec -T web \
    cp -a /editor-ui/dist/. /editor-ui/dist-export/
  docker compose -f docker-compose.prod.yml restart nginx
}

sync_git
download_secrets

echo "Checking secrets.env file:"
ls -la secrets.env
echo "File size: $(wc -c <secrets.env)"
echo "First few lines of secrets.env (without values):"
head -5 secrets.env | sed 's/=.*/=***/'

prepare_dirs
validate_and_build_env
deploy_containers

echo "Running containers:"
docker ps
echo "Container logs:"
docker compose -f docker-compose.prod.yml logs --tail=20
