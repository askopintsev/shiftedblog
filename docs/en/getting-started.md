# Getting started

ShiftedBlog is a self-hosted **blog management** tool for your computer or a server on the internet. Your main destination after setup is the **editor UI**.

Русский: [Быстрый старт](../ru/getting-started.md)

## Your goal

**On your computer:** **http://localhost:5173/login** → sign in → **http://localhost:5173/posts**

**On a server:** **https://editor.example.com/login** → sign in → **https://editor.example.com/posts**

That is the workspace: posts, series, multichannel dispatch. The public blog and Django admin are secondary.

> **Local setup is not a public website.** It is the management UI in your browser on **localhost**. Nobody outside your machine can reach it. Multichannel dispatch (site, Telegram, …) works locally too once channels are configured in Django admin.

---

## Choose a path

| Path | When | Guide |
|------|------|-------|
| **Local** | Try it out, write posts, configure channels | [local-deploy.md](local-deploy.md) |
| **Online deploy (on server)** | Public site on a VPS with HTTPS | [production-deploy.md](production-deploy.md) |
| **Host/domain migration** | Existing production, new VPS or domain | [host-migration.md](host-migration.md) |

**Online first-run (short):** DNS → clone project → ports → `./scripts/setup.sh` (**`2) online`**, answer **`n`** to “Start Docker now?”) → TLS → `./deploy.sh` → login. Details: [production-deploy.md](production-deploy.md).

---

## Local quick start

### Prerequisites

| Tool | Why | Download |
|------|-----|----------|
| Docker + Compose | Backend and editor in containers | https://docs.docker.com/get-docker/ |
| curl | Used by start scripts | usually preinstalled |
| Git | Clone the repo (or use ZIP) | https://git-scm.com/downloads |

Check:

```bash
docker compose version
curl --version
```

**Node.js is not required** for normal use — the editor runs in Docker.

### One-time setup

```bash
git clone https://github.com/askopintsev/shiftedblog.git
cd shiftedblog
./scripts/check-prerequisites.sh local
./scripts/setup.sh          # choose 1) local
docker compose exec web python manage.py createsuperuser   # if the wizard did not
```

No Git? Use a ZIP archive — see [local-deploy.md](local-deploy.md) step 1.

### Every day

```bash
./scripts/start-local.sh
```

Opens **http://localhost:5173/login** in your browser.

Launchers: `Start ShiftedBlog.command` (macOS), `start-shiftedblog.desktop` (Linux), `start-shiftedblog.bat` (Windows).

### Where to go (local)

| URL | Purpose |
|-----|---------|
| http://localhost:5173/login | **Editor UI — start here** |
| http://localhost:8888/ | Public blog preview |
| http://localhost:8888/mellon/ | Django admin (settings, channels) |

Full guide: [local-deploy.md](local-deploy.md)

---

## After first login

1. Create and edit posts in the editor (**New post**)
2. Optional: Django admin → **Core → Site settings**
3. Optional: **Core → Credentials** — Telegram and other channels

---

## Learn more

- [Local deploy (full guide)](local-deploy.md)
- [Online deploy (on server)](production-deploy.md)
- [Host and domain migration](host-migration.md)
- [Configuration](configuration.md)
- [Site settings](site-settings.md)
- [Security runbook](../security-runbook.md)
- [Maintainer / CI notes](maintainer.md)
