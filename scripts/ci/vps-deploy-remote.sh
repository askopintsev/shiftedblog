#!/usr/bin/env bash
# Remote production deploy (invoked from GitHub Actions over SSH).
set -euo pipefail

ROOT="${DEPLOY_ROOT:-/opt/shiftedblog}"
cd "$ROOT"

export PATH="${HOME}/.local/bin:/usr/local/bin:${PATH}"

# Build args use exported VITE_*; services load secrets.env via compose env_file.
# Do not pass --env-file here — compose also auto-loads .env and interpolates $VAR.
COMPOSE=(docker compose -f docker-compose.prod.yml)

remove_legacy_env_file() {
  if [[ -f "${ROOT}/.env" ]]; then
    echo "Removing legacy .env (compose interpolates \$ in passwords; use secrets.env only)."
    rm -f "${ROOT}/.env"
  fi
}

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

  if [[ "${SKIP_DOPPLER:-0}" == "1" ]] && [[ -s "${ROOT}/secrets.env" ]]; then
    echo "Using secrets.env uploaded by CI."
    if ! grep -qE '^SITE_URL=' "${ROOT}/secrets.env"; then
      echo "Uploaded secrets.env must contain SITE_URL." >&2
      exit 1
    fi
    remove_legacy_env_file
    return 0
  fi

  if [[ -n "${DOPPLER_TOKEN:-}" ]]; then
    ensure_doppler
    printf '%s' "${DOPPLER_TOKEN}" | doppler configure set token --scope "$ROOT" >/dev/null
    doppler secrets download \
      --project "${DOPPLER_PROJECT:-shifted_blog}" \
      --config "${DOPPLER_CONFIG:-prd}" \
      --no-file \
      --format=env >"${tmp_secrets}"
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
  remove_legacy_env_file
}

prepare_dirs() {
  mkdir -p logs backups static media static_blog
}

render_nginx_conf() {
  if grep -qE '^SITE_URL=' secrets.env; then
    echo "Rendering nginx/nginx.conf from template..."
    ENV_FILE=secrets.env ./scripts/generate-nginx-conf.sh
  fi
}

validate_and_build_env() {
  site_url="$(
    grep -m1 '^SITE_URL=' secrets.env \
      | cut -d= -f2- \
      | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" \
      | tr -d '\r'
  )"
  site_url="${site_url%/}"
  if [[ -z "${site_url}" ]]; then
    echo "SITE_URL must be set in secrets.env for editor-ui production build." >&2
    exit 1
  fi
  export VITE_PUBLIC_SITE_BASE="${VITE_PUBLIC_SITE_BASE:-${site_url}}"
  export VITE_API_BASE="$("${ROOT}/scripts/sanitize-vite-api-base.sh")"
  echo "Editor UI build: VITE_API_BASE=${VITE_API_BASE}"
}

check_env_mode() {
  if grep -qE '^PUBLIC_SITE_ENABLED=false' secrets.env 2>/dev/null; then
    ./scripts/check-env.sh private
  else
    ./scripts/check-env.sh online
  fi
}

report_port_conflict() {
  echo "Ports 80/443 are in use and blocked docker compose up:" >&2
  ss -tlnp 2>/dev/null | grep -E ':(80|443) ' || true
  echo "If host nginx holds these ports: sudo systemctl stop nginx && sudo systemctl disable nginx" >&2
}

deploy_containers() {
  remove_legacy_env_file

  # Keep builder cache between deploys; full prune makes every build cold and slow.
  docker image prune -af || true
  df -h / /var/lib/docker 2>/dev/null || df -h /

  echo "Building web image (existing stack may stay up during build)..."
  "${COMPOSE[@]}" build web

  echo "Recreating stack..."
  if ! "${COMPOSE[@]}" up -d --remove-orphans --force-recreate; then
    report_port_conflict
    exit 1
  fi

  "${COMPOSE[@]}" exec -T web \
    cp -a /editor-ui/dist/. /editor-ui/dist-export/
  "${COMPOSE[@]}" restart nginx
}

run_deploy_phase() {
  echo "Project directory: $(pwd)"
  echo "Deploy script revision: $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"

  echo "Checking secrets.env file:"
  ls -la secrets.env
  echo "File size: $(wc -c <secrets.env)"
  echo "First few lines of secrets.env (without values):"
  head -5 secrets.env | sed 's/=.*/=***/'

  prepare_dirs
  render_nginx_conf
  check_env_mode
  validate_and_build_env
  deploy_containers

  echo "Running containers:"
  docker ps
  echo "Container logs:"
  "${COMPOSE[@]}" logs --tail=20
}

if [[ "${VPS_DEPLOY_PHASE:-}" != "deploy" ]]; then
  sync_git
  download_secrets
  # Bash parses the whole script before sync_git runs; re-exec so deploy uses
  # the synced tree (including deploy_containers ordering and messages).
  export VPS_DEPLOY_PHASE=deploy
  export SKIP_DOPPLER="${SKIP_DOPPLER:-0}"
  export DEPLOY_ROOT="$ROOT"
  exec env VPS_DEPLOY_PHASE=deploy SKIP_DOPPLER="$SKIP_DOPPLER" DEPLOY_ROOT="$ROOT" bash "$0"
fi

run_deploy_phase
