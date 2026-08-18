# Security operations runbook

Lightweight monitoring for the single-VPS shiftedblog deployment (logs + email, no Sentry/Datadog).

Self-host guides: [en/getting-started.md](en/getting-started.md) · [ru/getting-started.md](ru/getting-started.md). Maintainer CI notes: [en/maintainer.md](en/maintainer.md).

## Monthly checklist

1. Review `logs/security.log` and `logs/authentication.log` on the server (`./logs` volume in production).
2. Open Django admin → Axes access attempts / failure logs (stock axes admin).
3. Run `python manage.py security_auth_report --hours 168` (last 7 days).
4. Confirm `ADMIN_URL` in `secrets.env` (or your secret manager) is non-default and not shared publicly.
5. Review GitHub deploy keys, `VPS_SSH_KEY`, and secret-manager access.
6. Check Dependabot PRs and CI `pip-audit` results.

## Weekly automated report (optional cron on VPS)

```bash
cd /opt/shiftedblog
docker compose -f docker-compose.prod.yml exec web \
  python manage.py security_auth_report --hours 168 --email
```

Exit code `1` means threshold alerts were detected (see command output).

## Account lockout

- **Automatic:** django-axes cooloff (`AXES_COOLOFF_TIME`, default 1 hour).
- **Admin UI:** Users → select user → action **Unlock account (clear axes lockout)**.
- **CLI:** `python manage.py axes_reset_user user@example.com`

Lockout notifications are emailed to `ADMIN_EMAIL` when SMTP is configured.

### SMTP (any provider)

Non-secret fields (`email_host`, port, user, TLS flags, from/admin) can live in **Admin → Site settings**. The password stays `EMAIL_HOST_PASSWORD` in `secrets.env`.

| Setting | Typical values |
|---------|----------------|
| `EMAIL_HOST` | Provider SMTP hostname (see your mail/hosting panel) |
| `EMAIL_PORT` | `465` (SSL) or `587` (STARTTLS) |
| `EMAIL_USE_SSL` | `True` on 465; `False` on 587 |
| `EMAIL_USE_TLS` | `False` on 465; `True` on 587 |
| `EMAIL_HOST_USER` | Full mailbox address |
| `DEFAULT_FROM_EMAIL` | Usually the same mailbox |
| `ADMIN_EMAIL` | Where alerts are received (any address) |

`Connection unexpectedly closed` often means wrong port/TLS mode (587+TLS vs 465+SSL).

**Docker Compose `.env`:** escape `$` in passwords as `$$` or Compose strips `$E` etc. and breaks SMTP auth.

After a host/domain move, mail can stay on the **old** mailbox/SMTP until you create addresses on the new domain. See [en/host-migration.md](en/host-migration.md).

**Example (one hoster’s documented pair):** `smtp.beget.com:465` with SSL — see the provider’s mail KB for current values.

## Rate limiting layers

| Layer | Config | Logs |
|-------|--------|------|
| nginx | 5 req/min on login paths | 429 responses |
| django-ratelimit | 10 req/min on 2FA views | `django_ratelimit` in `security.log` |
| django-axes | 5 failures → lockout | `axes` in `authentication.log` |

## Secrets rotation

1. Rotate `SECRET_KEY` / `CREDENTIALS_ENCRYPTION_KEY` in Doppler.
2. Set `SECRET_KEY_ROTATED_AT` / `CREDENTIALS_ENCRYPTION_KEY_ROTATED_AT` to today's date (YYYY-MM-DD).
3. Redeploy. Admin shows a warning banner until dates are set or credentials are refreshed.
4. Re-encrypt stored credentials if `CREDENTIALS_ENCRYPTION_KEY` changed (manual process).

Generate a new admin path:

```bash
./scripts/security/generate-admin-url.sh
```

## ADMIN_URL change procedure

1. Set new `ADMIN_URL` in Doppler `prd`.
2. Deploy (`git push` to `master` or `./deploy.sh` on VPS).
3. Update bookmarks; robots.txt disallows the new path automatically.

## Failed-login spike thresholds

Default `security_auth_report` thresholds:

- One IP: ≥20 failures in the lookback window
- One username from >3 IPs in the window

Adjust with `--ip-threshold` and `--username-ip-threshold`.

## Editor subdomain (`editor.*`)

1. Set `EDITOR_URL`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` (include editor origin), and cookie domain vars in Doppler (see `env.example`).
2. Ensure TLS cert covers your editor hostname (e.g. `editor.example.com`) as a SAN.
3. After deploy, verify login at `EDITOR_URL/login` and API session from browser devtools (`/api/editor/v1/auth/me/`).
4. Keep Django admin as fallback; link **Open new editor** appears on Posts changelist when `EDITOR_URL` is set.
