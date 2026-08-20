# Getting started

ShiftedBlog is a self-hosted blog **management** tool. Your main destination after setup is the **editor UI**.

Русский: [../ru/getting-started.md](../ru/getting-started.md)

## What you are setting up

```text
Editor UI (your workspace)     →  http://localhost:5173/login
Public blog (visitor view)     →  http://localhost:8888/
Django admin (settings)        →  http://localhost:8888/mellon/
```

**Goal:** run setup once, then `./scripts/start-local.sh` (or double-click the launcher) → log in.

> **Local setup is not a website.** It is the management interface in your browser on `localhost`. Multichannel dispatch (site, Telegram, …) works from local too once channels are configured.

Full guide: [local-deploy.md](local-deploy.md)

## Choose a path

1. **Local** — try on your machine ([local-deploy.md](local-deploy.md))
2. **Production** — deploy on a VPS with HTTPS ([production-deploy.md](production-deploy.md))
3. **Migrate** — move host and/or domain ([host-migration.md](host-migration.md))

## Prerequisites (local)

| Tool | Download |
|------|----------|
| Git | https://git-scm.com/downloads |
| Docker + Compose | https://docs.docker.com/get-docker/ |

## Quick start (local)

**One-time:**

```bash
git clone https://github.com/askopintsev/shiftedblog.git
cd shiftedblog
./scripts/setup.sh          # choose 1) local
docker compose exec web python manage.py createsuperuser   # if needed
```

**Every day:**

```bash
./scripts/start-local.sh
```

Opens http://localhost:5173/login in your browser.

Launchers: `Start ShiftedBlog.command` (macOS), `start-shiftedblog.desktop` (Linux), `start-shiftedblog.bat` (Windows).

## After first login

1. Create and edit posts in the editor (**New post**)
2. Optional: Django admin → **Core → Site settings**
3. Optional: **Core → Credentials** — Telegram and other channels

## Learn more

- [Local deploy (full guide)](local-deploy.md)
- [Configuration](configuration.md)
- [Site settings](site-settings.md)
- [Host/domain migration](host-migration.md)
- [Security runbook](../security-runbook.md)
- [Maintainer / CI notes](maintainer.md)
