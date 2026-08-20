# Configuration

Русский: [Конфигурация](../ru/configuration.md)

## Your goal: know where to change what

ShiftedBlog stores settings in **two layers**:

1. **Environment file** (`.env` locally, `secrets.env` on the server) — secrets, domain, security, editor build.
2. **Site settings** in Django admin — brand, social links, non-secret email fields, feature toggles.

After first setup, most day-to-day changes belong in **Site settings** or **Editor → Settings → Site**. Touch the env file when changing domain, deploy secrets, or infrastructure.

> Full variable list: [`env.example`](../../env.example). Create the file with `./scripts/setup.sh` (**`1) local`**, **`2) online`**, **`3) private`**, or **`4) private-ip`**).

---

## Environment files

| Mode | File | Compose |
|------|------|---------|
| Local | `.env` | `docker-compose.yml` |
| Online (server) | `secrets.env` | `docker-compose.prod.yml` |
| Private editor (server) | `secrets.env` | `docker-compose.prod.yml` |

Validate before deploy:

```bash
./scripts/check-env.sh local          # local
ENV_FILE=secrets.env ./scripts/check-env.sh online   # public site
ENV_FILE=secrets.env ./scripts/check-env.sh private  # editor-only VPS
```

Production `deploy.sh` runs `check-env.sh online` or `private` automatically based on `PUBLIC_SITE_ENABLED`.

**Docker Compose:** escape `$` in passwords as `$$`, or Compose will strip parts of the value (e.g. `$E` in an SMTP password).

---

## What stays in env (and why)

| Group | Variables | Why in the file |
|-------|-----------|-----------------|
| Crypto | `SECRET_KEY`, `CREDENTIALS_ENCRYPTION_KEY` | Django secrets and credential encryption |
| Database / Redis | `DB_*`, `POSTGRES_*`, `REDIS_URL` | Docker infrastructure |
| Public URL | `SITE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `PUBLIC_SITE_ENABLED`, `FAKE_HOSTNAME` | Security and canonical URL |
| SSL / cookies | `SESSION_COOKIE_*`, `CSRF_COOKIE_*`, `SECURE_*` | HTTPS and sessions |
| Admin | `ADMIN_URL` | Non-default path instead of `/mellon/` |
| Mail (secret) | `EMAIL_HOST_PASSWORD` | SMTP password |
| Editor / SPA | `EDITOR_URL`, `CORS_ALLOWED_ORIGINS`, `VITE_*`, cookie domains | Editor subdomain and UI build |
| Nginx / domain | `DOMAIN`, `EDITOR_DOMAIN`, `SSL_CERT_NAME`, `SERVER_IP` | `./scripts/generate-nginx-conf.sh` |
| Ops | `BACKUP_DIR`, `YADISK_TOKEN`, proxies | Backups and integrations |

`SITE_URL` is **required** in production: Django validates it at boot; `./deploy.sh` passes it into the editor UI build (`VITE_PUBLIC_SITE_BASE`).

---

## Domain and nginx

| Variable | Purpose |
|----------|---------|
| `DOMAIN` | Primary domain without `www` |
| `EDITOR_DOMAIN` | Editor subdomain (e.g. `editor.example.com`) |
| `SITE_URL` | Canonical public URL (`https://example.com`; private editor: `https://editor.example.com`) |
| `PUBLIC_SITE_ENABLED` | `false` — editor-only VPS (no main nginx vhost, site channel hidden). Default `true`. |
| `FAKE_HOSTNAME` | `true` — **`4) private-ip`** deploy: no registrar domain; uses `shiftedblog.local` fake names. Requires `SERVER_IP`. |
| `SSL_CERT_NAME` | Directory name under `/etc/letsencrypt/live/` |
| `SERVER_IP` | Public IP (nginx `server_name`, `ALLOWED_HOSTS`) |
| `EXTRA_DOMAINS` | **Same** site on extra hosts (duplicate content) |
| `REDIRECT_FROM_DOMAINS` | Legacy apex/www → **301** to `SITE_URL` |
| `REDIRECT_FROM_EDITOR_DOMAINS` | Legacy editor host → **301** to `EDITOR_DOMAIN` |

Do **not** put legacy 301 hostnames in `EXTRA_DOMAINS` — use `REDIRECT_FROM_*` only.

Change domain **without** rotating `SECRET_KEY`, `ADMIN_URL`, or DB passwords:

```bash
./scripts/apply-domain.sh --domain new.example.com \
  --site-url https://new.example.com \
  --editor-domain editor.new.example.com \
  --redirect-from old.example.com,www.old.example.com \
  --redirect-from-editor editor.old.example.com \
  --server-ip YOUR_VPS_IP
```

Then TLS if needed and **`./deploy.sh`** to rebuild the editor with the new `SITE_URL`.

Full VPS or domain move: [host-migration.md](host-migration.md).

---

## Site settings (admin)

After `migrate`, open **Admin → Core → Site settings** (or **Editor → Settings → Site**):

- Brand: site name, tagline, footer
- Social URLs and contact email
- Non-secret SMTP fields (host, port, from, admin address)
- Toggles: Telegram rich messages, text-quality checker

Details: [site-settings.md](site-settings.md).

SMTP password stays in **`EMAIL_HOST_PASSWORD`** in env only.

---

## Bootstrap vs runtime

Env values for email / Twitter act as **fallbacks** until set in Site settings. Toggles can be forced via env for bootstrap; prefer admin for day-to-day changes.

Site settings changes apply **immediately** — no restart. After changing `SITE_URL` or domain keys, run **`./deploy.sh`** (online) or rebuild the local stack.

---

## Related

- [Getting started](getting-started.md)
- [Local deploy](local-deploy.md)
- [Online deploy (on server)](production-deploy.md)
- [Host and domain migration](host-migration.md)
- [Site settings](site-settings.md)
- [Security runbook](../security-runbook.md)
