#!/usr/bin/env bash
# Interactive bootstrap for local or production Docker deploy.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "ShiftedBlog setup"
echo "================="
echo "1) local      — Docker Compose on this machine (port 8888)"
echo "2) online     — VPS / public site (secrets.env + nginx + HTTPS)"
read -r -p "Choose mode [1/2]: " mode_choice

case "${mode_choice}" in
  1|local|Local|LOCAL) MODE="local" ;;
  2|online|Online|ONLINE|production|Production|PRODUCTION|prod) MODE="production" ;;
  *)
    echo "Invalid choice." >&2
    exit 2
    ;;
esac

if [[ "$MODE" == "local" ]]; then
  ENV_FILE=".env"
else
  ENV_FILE="secrets.env"
fi

if [[ "$MODE" == "local" ]]; then
  if ! ./scripts/check-prerequisites.sh local; then
    read -r -p "Install missing prerequisites now? [y/N]: " install_prereqs || true
    install_prereqs="${install_prereqs:-N}"
    if [[ "$install_prereqs" =~ ^[Yy]$ ]]; then
      ./scripts/install-prerequisites.sh
    else
      exit 1
    fi
    ./scripts/check-prerequisites.sh local || exit 1
  fi
elif [[ "$MODE" == "production" ]]; then
  ./scripts/check-prerequisites.sh online || exit 1
fi

generate_secret_key() {
  python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(50))
PY
}

generate_fernet_key() {
  python3 - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
}

generate_password() {
  python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
}

generate_admin_url() {
  openssl rand -hex 8
}

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

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ ! -f env.example ]]; then
    echo "env.example not found." >&2
    exit 1
  fi
  cp env.example "$ENV_FILE"
  echo "Created $ENV_FILE from env.example"
else
  echo "Using existing $ENV_FILE"
fi

read_env_value() {
  local file="$1"
  local key="$2"
  python3 - "$file" "$key" <<'PY'
import sys
from pathlib import Path
path = Path(sys.argv[1])
key = sys.argv[2]
if not path.exists():
    raise SystemExit(0)
for line in path.read_text(encoding="utf-8").splitlines():
    if line.startswith(f"{key}="):
        print(line.split("=", 1)[1])
        break
PY
}

is_placeholder() {
  local value="$1"
  [[ -z "$value" || "$value" == *"change-this"* || "$value" == *"insecure"* || "$value" == *"your-"* || "$value" == *"your_"* ]]
}

CURRENT_SECRET="$(read_env_value "$ENV_FILE" "SECRET_KEY")"
if is_placeholder "$CURRENT_SECRET"; then
  upsert_env "$ENV_FILE" "SECRET_KEY" "$(generate_secret_key)"
fi

CURRENT_FERNET="$(read_env_value "$ENV_FILE" "CREDENTIALS_ENCRYPTION_KEY")"
if is_placeholder "$CURRENT_FERNET"; then
  FERNET_VAL="$(generate_fernet_key 2>/dev/null || true)"
  if [[ -n "${FERNET_VAL}" ]]; then
    upsert_env "$ENV_FILE" "CREDENTIALS_ENCRYPTION_KEY" "$FERNET_VAL"
  else
    echo "cryptography not installed in host Python; CREDENTIALS_ENCRYPTION_KEY left for later." >&2
  fi
fi

CURRENT_DB_PASS="$(read_env_value "$ENV_FILE" "DB_PASS")"
if is_placeholder "$CURRENT_DB_PASS"; then
  DB_PASS_VAL="$(generate_password)"
  upsert_env "$ENV_FILE" "DB_PASS" "$DB_PASS_VAL"
  upsert_env "$ENV_FILE" "POSTGRES_PASSWORD" "$DB_PASS_VAL"
fi

upsert_env "$ENV_FILE" "DB_NAME" "shiftedblog"
upsert_env "$ENV_FILE" "DB_USER" "shiftedblog"
upsert_env "$ENV_FILE" "POSTGRES_DB" "shiftedblog"
upsert_env "$ENV_FILE" "POSTGRES_USER" "shiftedblog"
upsert_env "$ENV_FILE" "DB_HOST" "db"
upsert_env "$ENV_FILE" "DB_PORT" "5432"
upsert_env "$ENV_FILE" "REDIS_URL" "redis://redis:6379/1"

if [[ "$MODE" == "local" ]]; then
  upsert_env "$ENV_FILE" "DEBUG" "True"
  upsert_env "$ENV_FILE" "ALLOWED_HOSTS" "localhost,127.0.0.1,0.0.0.0"
  upsert_env "$ENV_FILE" "SITE_URL" "http://localhost:8888"
  upsert_env "$ENV_FILE" "CSRF_TRUSTED_ORIGINS" "http://localhost:8888,http://127.0.0.1:8888"
  upsert_env "$ENV_FILE" "SESSION_COOKIE_SECURE" "False"
  upsert_env "$ENV_FILE" "CSRF_COOKIE_SECURE" "False"
  upsert_env "$ENV_FILE" "SECURE_SSL_REDIRECT" "False"
  upsert_env "$ENV_FILE" "SECURE_HSTS_SECONDS" "0"
  upsert_env "$ENV_FILE" "ADMIN_URL" "mellon"
  if command -v id >/dev/null 2>&1; then
    upsert_env "$ENV_FILE" "HOST_UID" "$(id -u)"
    upsert_env "$ENV_FILE" "HOST_GID" "$(id -g)"
  fi
else
  read -r -p "Primary domain (e.g. example.com, no www): " DOMAIN_IN
  if [[ -z "$DOMAIN_IN" ]]; then
    echo "Domain is required for production." >&2
    exit 1
  fi
  if [[ "$DOMAIN_IN" == www.* ]]; then
    DOMAIN_IN="${DOMAIN_IN#www.}"
  fi
  read -r -p "Canonical public URL [https://${DOMAIN_IN}]: " SITE_URL_IN
  SITE_URL_IN="${SITE_URL_IN:-https://${DOMAIN_IN}}"
  SITE_URL_IN="${SITE_URL_IN%/}"
  read -r -p "Extra domains comma-separated (optional; same site, not redirects): " EXTRA_IN
  read -r -p "Legacy domains to 301 to the canonical URL (optional, e.g. old.com,www.old.com): " REDIRECT_IN
  read -r -p "Editor subdomain [editor.${DOMAIN_IN}]: " EDITOR_IN
  EDITOR_IN="${EDITOR_IN:-editor.${DOMAIN_IN}}"
  read -r -p "Legacy editor hosts to 301 (optional, e.g. editor.old.com): " REDIRECT_EDITOR_IN
  read -r -p "Let's Encrypt cert name [${DOMAIN_IN}]: " CERT_IN
  CERT_IN="${CERT_IN:-${DOMAIN_IN}}"
  read -r -p "Server public IP (optional, for nginx server_name): " SERVER_IP_IN

  ADMIN_URL_VAL="$(generate_admin_url)"
  upsert_env "$ENV_FILE" "DEBUG" "False"
  upsert_env "$ENV_FILE" "DOMAIN" "$DOMAIN_IN"
  upsert_env "$ENV_FILE" "EDITOR_DOMAIN" "$EDITOR_IN"
  upsert_env "$ENV_FILE" "SSL_CERT_NAME" "$CERT_IN"
  upsert_env "$ENV_FILE" "EXTRA_DOMAINS" "$EXTRA_IN"
  upsert_env "$ENV_FILE" "REDIRECT_FROM_DOMAINS" "$REDIRECT_IN"
  upsert_env "$ENV_FILE" "REDIRECT_FROM_EDITOR_DOMAINS" "$REDIRECT_EDITOR_IN"
  upsert_env "$ENV_FILE" "SERVER_IP" "$SERVER_IP_IN"
  upsert_env "$ENV_FILE" "SITE_URL" "$SITE_URL_IN"
  upsert_env "$ENV_FILE" "ALLOWED_HOSTS" "${DOMAIN_IN},www.${DOMAIN_IN},${EDITOR_IN},localhost,127.0.0.1${SERVER_IP_IN:+,${SERVER_IP_IN}}"
  upsert_env "$ENV_FILE" "CSRF_TRUSTED_ORIGINS" "https://${DOMAIN_IN},https://www.${DOMAIN_IN},https://${EDITOR_IN}"
  upsert_env "$ENV_FILE" "EDITOR_URL" "https://${EDITOR_IN}"
  upsert_env "$ENV_FILE" "CORS_ALLOWED_ORIGINS" "https://${EDITOR_IN}"
  upsert_env "$ENV_FILE" "SESSION_COOKIE_DOMAIN" ".${DOMAIN_IN}"
  upsert_env "$ENV_FILE" "CSRF_COOKIE_DOMAIN" ".${DOMAIN_IN}"
  upsert_env "$ENV_FILE" "SESSION_COOKIE_SECURE" "True"
  upsert_env "$ENV_FILE" "CSRF_COOKIE_SECURE" "True"
  upsert_env "$ENV_FILE" "SECURE_SSL_REDIRECT" "True"
  upsert_env "$ENV_FILE" "SECURE_HSTS_SECONDS" "31536000"
  upsert_env "$ENV_FILE" "ADMIN_URL" "$ADMIN_URL_VAL"
  upsert_env "$ENV_FILE" "VITE_PUBLIC_SITE_BASE" "$SITE_URL_IN"
  upsert_env "$ENV_FILE" "VITE_API_BASE" "/api/editor/v1"
fi

./scripts/check-env.sh "$MODE"

if [[ "$MODE" == "production" ]]; then
  ./scripts/generate-nginx-conf.sh
  echo ""
  echo "Nginx config generated. Before first HTTPS deploy:"
  echo "  1. Point DNS A records for ${DOMAIN_IN} / www / ${EDITOR_IN} to this server"
  echo "  2. Obtain TLS (first run — port 80 free; stop nginx if needed), e.g.:"
  echo "       cd $(pwd)"
  echo "       docker compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true"
  echo "       sudo certbot certonly --standalone --agree-tos --register-unsafely-without-email \\"
  echo "         -d ${DOMAIN_IN} -d www.${DOMAIN_IN} -d ${EDITOR_IN}"
  echo "     Or self-signed if DNS is not ready — see docs/ru/production-deploy.md (step 5)"
  echo "  3. ./deploy.sh"
  echo "  4. Changing domain later: ./scripts/apply-domain.sh (does not rotate keys)"
  echo "  5. Host/domain move: docs/ru/host-migration.md"
fi

read -r -p "Start Docker now? [Y/n]: " start_docker || true
start_docker="${start_docker:-Y}"
if [[ "$start_docker" =~ ^[Yy]$ ]]; then
  mkdir -p logs backups static media static_blog
  if [[ "$MODE" == "local" ]]; then
    docker compose up --build -d
    echo ""
    echo "Local site: http://localhost:8888/"
    echo "Admin (default): http://localhost:8888/mellon/"
  else
    # shellcheck disable=SC1091
    source ./scripts/load-editor-ui-build-env.sh
    docker compose -f docker-compose.prod.yml up --build -d
    echo ""
    echo "Production stack started."
    echo "Admin path: /${ADMIN_URL_VAL}/"
  fi

  read -r -p "Create Django superuser now? [y/N]: " create_su || true
  if [[ "${create_su:-N}" =~ ^[Yy]$ ]]; then
    if [[ "$MODE" == "local" ]]; then
      docker compose exec web python manage.py createsuperuser
    else
      docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
    fi
  fi
fi

echo ""
echo "Next steps:"
if [[ "$MODE" == "local" ]]; then
  if [[ -f "$ROOT/start-shiftedblog.desktop.in" ]]; then
    sed "s|@PROJECT_ROOT@|$ROOT|g" "$ROOT/start-shiftedblog.desktop.in" > "$ROOT/start-shiftedblog.desktop"
  fi
  echo "  - Daily start: ./scripts/start-local.sh"
  echo "  - Or double-click: Start ShiftedBlog.command (macOS) / start-shiftedblog.desktop (Linux)"
  echo "  - Editor login: http://localhost:5173/login"
  echo "  - Full guide: docs/en/local-deploy.md (docs/ru/local-deploy.md)"
fi
echo "  - Configure brand/social/email toggles in admin → Core → Site settings"
echo "  - Docs (EN): docs/en/getting-started.md"
echo "  - Docs (RU): docs/ru/getting-started.md"
echo "Done."
