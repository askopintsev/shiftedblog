# Online deploy (on server)

Русский: [Онлайн запуск (на сервере)](../ru/production-deploy.md)

## Your goal: log into the editor on your domain

After setup you should open:

**https://editor.example.com/login** → sign in → **https://editor.example.com/posts**

That is the main workspace. The public blog at `https://example.com/` and Django admin are secondary.

> This guide is **provider-agnostic** (any VPS with Docker). Use a clean server for the simplest path. If an old install is present, optional cleanup is described below.

> **No public blog?** Use [private-editor-deploy.md](private-editor-deploy.md) (`setup.sh` **`3) private`**, `PUBLIC_SITE_ENABLED=false`).

**First-run order:** DNS (step 1) → clone project (2) → ports (3) → `./scripts/setup.sh` with **`2) online`**, answer **`n`** to “Start Docker now?” (4) → TLS (5) → `./deploy.sh` (6) → login (7) → browser check (8).

## Before you start

You need:

- A **VPS** (Ubuntu/Debian recommended) with SSH access
- A **domain** you control (e.g. `example.com`)
- **DNS** pointing at the VPS **before** TLS (see step 1)

Check on the server (manual `docker` / `git` / `curl`; run `./scripts/check-prerequisites.sh online` **after** step 2 when the project is on disk):

```bash
docker compose version   # Docker + Compose plugin
git --version
curl --version
certbot --version        # for Let's Encrypt
```

Install Docker on Ubuntu if missing:

```bash
curl -fsSL https://get.docker.com | sh
sudo systemctl enable --now docker
```

Optional installer (Ubuntu/Debian or macOS — mainly for local dev): `./scripts/install-prerequisites.sh`

---

## Step 1. Point DNS to the VPS

In your domain registrar or DNS panel, create **A records** to the server public IP:

| Name | Type | Value |
|------|------|-------|
| `@` | A | `YOUR_VPS_IP` |
| `www` | A | `YOUR_VPS_IP` |
| `editor` | A | `YOUR_VPS_IP` |

Verify (from your laptop or the VPS):

```bash
dig +short example.com A
dig +short editor.example.com A
```

Both must return your VPS IP before Let's Encrypt will succeed.

> **DNS not working yet?** You can still test by IP while fixing registrar/NS settings. In **`./scripts/setup.sh`** (step 4), enter the **server public IP** — it is added to nginx and `ALLOWED_HOSTS`. Use a temporary self-signed certificate (step 5) or wait for DNS and Let's Encrypt. Open `https://YOUR_VPS_IP/`. For the editor, add to your computer's hosts file:
>
> ```text
> YOUR_VPS_IP  editor.example.com
> ```
>
> Then open `https://editor.example.com/login`.

---

## Step 2. Get the project on the server

```bash
sudo mkdir -p /opt/shiftedblog
sudo chown "$USER:$USER" /opt/shiftedblog
cd /opt/shiftedblog
git clone https://github.com/YOUR_USER/shiftedblog.git .
```

Or download a ZIP if Git is unavailable (see [local-deploy.md](local-deploy.md) step 1).

---

## Step 3. Check ports and (optional) remove a previous install

### Check that ports 80 and 443 are free

The server needs **80** and **443** (nginx and Let's Encrypt). Check manually:

```bash
ss -tlnp | grep -E ':80|:443' || echo "ports 80 and 443 are free"
```

On macOS without `ss`:

```bash
lsof -nP -iTCP:80 -sTCP:LISTEN
lsof -nP -iTCP:443 -sTCP:LISTEN
```

After cloning the project (step 2), the script also warns:

```bash
cd /opt/shiftedblog
./scripts/check-prerequisites.sh online
```

| Result | What to do |
|--------|------------|
| **Ports free** | Continue to the setup wizard (step 4) |
| **80 or 443 in use** | See **who** is listening (below) and follow the matching row |

**How to tell what owns the port.** In `ss` output, read the last column (`users:(("…"))`) — the process name:

```text
# ports free — no lines, or only «ports free»
# host nginx:
LISTEN … users:(("nginx",pid=…))
# apache:
LISTEN … users:(("apache2",pid=…))
# Docker (old ShiftedBlog or another compose stack):
LISTEN … users:(("docker-proxy",pid=…))
```

| What you see | Action |
|--------------|--------|
| **nginx** or **apache2** | Host panel web server — stop it (commands below), then check ports again |
| **docker-proxy** | Old Docker stack — optional cleanup below or `docker compose -f docker-compose.prod.yml down` |
| **Something else** | Note the PID, check with your VPS provider, or stop that process manually |

**Only if the output showed nginx/apache** — stop the host web server:

```bash
sudo systemctl stop nginx apache2 2>/dev/null || true
ss -tlnp | grep -E ':80|:443' || echo "ports 80 and 443 are free"
```

If ports are still in use, use the table above (often `docker-proxy` remains).

### Optional — remove a previous ShiftedBlog install

**Skip on a fresh VPS** with nothing in `/opt/shiftedblog`.

If an old ShiftedBlog (or other Docker stack on ports 80/443) is already on this machine:

```bash
cd /opt/shiftedblog
./scripts/vps-clean-for-fresh-deploy.sh
```

Then clone again (step 2) or continue from a clean directory.

---

## Step 4. Run the setup wizard

```bash
cd /opt/shiftedblog
./scripts/setup.sh
```

Choose **`2) online`**. Enter:

- Primary domain (e.g. `example.com`, without `www`)
- Public URL (default `https://example.com`)
- Editor subdomain (default `editor.example.com`)
- Let's Encrypt certificate name (default = primary domain)
- Server public IP (optional but useful for nginx)

The wizard creates `secrets.env`, generates `nginx/nginx.conf`, and can start Docker.

When asked **“Start Docker now?”** — you may answer **`n`** if TLS certificates are not ready yet (recommended on first run on the server).

---

## Step 5. Obtain TLS certificates

DNS must already resolve to this server (step 1) **when using Let's Encrypt**. All commands below assume the project directory:

```bash
cd /opt/shiftedblog
```

### First Let's Encrypt certificate (simplest — port 80 is free)

```bash
sudo mkdir -p /var/www/html
docker compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true
sudo certbot certonly --standalone --agree-tos --register-unsafely-without-email \
  -d example.com -d www.example.com -d editor.example.com
```

Ensure `SSL_CERT_NAME` in `secrets.env` matches the directory under `/etc/letsencrypt/live/` (usually your primary domain, e.g. `example.com`).

### Temporary self-signed certificate (DNS not ready yet)

Replace `example.com` with your domain, then run step 6 (`./deploy.sh`).

```bash
sudo mkdir -p /etc/letsencrypt/live/example.com
sudo openssl req -x509 -nodes -days 30 -newkey rsa:2048 \
  -keyout /etc/letsencrypt/live/example.com/privkey.pem \
  -out /etc/letsencrypt/live/example.com/fullchain.pem \
  -subj "/CN=example.com" \
  -addext "subjectAltName=DNS:example.com,DNS:www.example.com,DNS:editor.example.com"
```

When DNS works, obtain Let's Encrypt (command above) and run `./deploy.sh` again.

### Renewals / later reissue (project already running)

```bash
sudo certbot certonly --webroot -w /var/www/html \
  -d example.com -d www.example.com -d editor.example.com
```

**If you changed the domain name** (in `secrets.env` or via `./scripts/apply-domain.sh`) — regenerate nginx and reload it:

```bash
./scripts/generate-nginx-conf.sh
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

---

## Step 6. Launch on the server

```bash
cd /opt/shiftedblog
./deploy.sh
```

`deploy.sh` validates `secrets.env`, rebuilds images (including the editor UI), starts `docker-compose.prod.yml`, and reloads nginx. The first run may take **several minutes**.

Validate env manually (optional — `deploy.sh` already runs this):

```bash
ENV_FILE=secrets.env ./scripts/check-env.sh online
```

---

## Step 7. Create a login

If the wizard on step 4 did not create a user, run:

```bash
cd /opt/shiftedblog
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

Use your **email** as the username. Save the admin path from the wizard output (`ADMIN_URL` in `secrets.env`).

---

## Step 8. Verify

Open **https://editor.example.com/login** in a browser and sign in.

On the server (domain must resolve to this VPS; add `-k` for a self-signed cert):

```bash
curl -sI https://editor.example.com/login | head -1
docker compose -f docker-compose.prod.yml ps
```

Admin URL (non-default path): check `ADMIN_URL` in `secrets.env` → `https://example.com/ADMIN_URL/`

---

## Updates

```bash
cd /opt/shiftedblog
./deploy.sh
```

## Editor UI build

**For a normal install you do not need extra steps.** `./scripts/setup.sh` already writes `SITE_URL` to `secrets.env`, and `./deploy.sh` passes it into the editor UI build automatically.

| Situation | Action |
|-----------|--------|
| First install following this guide | Nothing — follow steps 4–6 |
| You changed the domain or edited `SITE_URL` manually | Update `secrets.env` (or run `./scripts/apply-domain.sh`), then `./deploy.sh` again |

Reference: the Docker image bakes in `VITE_PUBLIC_SITE_BASE` and `VITE_API_BASE` from `SITE_URL` in `secrets.env` at build time.

## Optional CI

GitHub Actions + Doppler — maintainer path: [maintainer.md](maintainer.md). Self-hosters only need `secrets.env` + `./deploy.sh`.

## Moving host or domain

Do not put legacy hostnames in `EXTRA_DOMAINS` (duplicate site). Use `REDIRECT_FROM_DOMAINS` / `REDIRECT_FROM_EDITOR_DOMAINS` for HTTPS 301 to `SITE_URL`. Change domain keys without rotating secrets: `./scripts/apply-domain.sh`. Full playbook: [host-migration.md](host-migration.md).
