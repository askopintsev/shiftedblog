# Security operations runbook

Lightweight monitoring for the single-VPS shiftedblog deployment (logs + email, no Sentry/Datadog).

## Monthly checklist

1. Review `logs/security.log` and `logs/authentication.log` on the server (`./logs` volume in production).
2. Open Django admin → Axes access attempts / failure logs (stock axes admin).
3. Run `python manage.py security_auth_report --hours 168` (last 7 days).
4. Confirm `ADMIN_URL` in Doppler is non-default and not shared publicly.
5. Review GitHub deploy keys, `VPS_SSH_KEY`, and Doppler access.
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
