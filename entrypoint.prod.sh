#!/usr/bin/env bash
set -euo pipefail

APP_USER=appuser
LOG_MOUNT=/app/logs
FALLBACK_LOG_DIR=/tmp/shiftedblog_logs

# Bind-mounted dirs the appuser must write (collectstatic, uploads, logs, backups).
WRITABLE_MOUNTS=(
  "${LOG_MOUNT}"
  /app/static
  /app/media
  /backups
  "${FALLBACK_LOG_DIR}"
)

fix_mount_permissions() {
  local mount="$1"
  mkdir -p "${mount}"
  chown -R "${APP_USER}:${APP_USER}" "${mount}" 2>/dev/null || true
  chmod -R u+rwX "${mount}" 2>/dev/null || chmod -R a+rwX "${mount}" 2>/dev/null || true
}

for mount in "${WRITABLE_MOUNTS[@]}"; do
  fix_mount_permissions "${mount}"
done

for logfile in security.log authentication.log; do
  path="${LOG_MOUNT}/${logfile}"
  if [[ -e "${path}" ]] && ! runuser -u "${APP_USER}" -- test -w "${path}"; then
    rm -f "${path}"
  fi
  touch "${path}" 2>/dev/null || true
  chown "${APP_USER}:${APP_USER}" "${path}" 2>/dev/null || true
  chmod 664 "${path}" 2>/dev/null || true
done

log_dir_env=""
if ! runuser -u "${APP_USER}" -- test -w "${LOG_MOUNT}"; then
  echo "WARNING: ${LOG_MOUNT} is not writable by ${APP_USER}; using ${FALLBACK_LOG_DIR}" >&2
  fix_mount_permissions "${FALLBACK_LOG_DIR}"
  log_dir_env="export SHIFTED_BLOG_LOG_DIR=${FALLBACK_LOG_DIR};"
fi

runuser -u "${APP_USER}" -- bash -c "
set -euo pipefail
${log_dir_env}
python manage.py collectstatic --noinput
python manage.py migrate --noinput
exec python -m gunicorn --bind 0.0.0.0:8000 --workers \${GUNICORN_WORKERS:-2} shiftedblog.wsgi:application \
  --timeout \${GUNICORN_TIMEOUT:-120} --graceful-timeout 30 \
  --max-requests \${GUNICORN_MAX_REQUESTS:-500} --max-requests-jitter 50 \
  --access-logfile - --error-logfile - --log-level info
"
