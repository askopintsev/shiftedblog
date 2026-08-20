# Private editor deploy (VPS, no public blog)

Русский: [Приватный редактор на VPS](../ru/private-editor-deploy.md)

## Your goal

**https://editor.example.com/login** → sign in → write posts → multisend to **Telegram** (and other channels). There is **no anonymous public blog** on the internet.

Staff can still open the **Лента** feed at **https://editor.example.com/lenta/** (Django session login, same staff user).

> Same production stack as [online deploy](production-deploy.md) (`docker-compose.prod.yml`, `./deploy.sh`), but `PUBLIC_SITE_ENABLED=false` and nginx serves **only the editor host** (+ proxied staff paths).

**First-run order (with domain):** DNS → clone project → `./scripts/setup.sh` **`3) private`** → TLS → `./deploy.sh` → login.

**First-run order (no domain):** clone project → `./scripts/setup.sh` **`4) private-ip`** → self-signed TLS → `./deploy.sh` → hosts file on your PC → login.

---

## When to choose this path

| Scenario | Guide |
|----------|-------|
| Public blog + editor on a VPS | [production-deploy.md](production-deploy.md) |
| Editor + Telegram only, **with your domain** | **This guide** — setup **`3) private`** |
| Editor + Telegram, **no domain** (VPS + public IP) | **This guide** — [no domain](#no-domain-4-private-ip) (`4) private-ip`) |
| Try on your laptop | [local-deploy.md](local-deploy.md) |

> **Out of scope:** VPS without a public IP (VPN-only, NAT-only). Use a tunnel or VPN yourself — not documented here.

---

## Before you start

- A **VPS** with SSH, Docker, and a **public IP**
- For **`3) private`**: a **domain** (DNS A record for `editor`)
- For **`4) private-ip`**: no domain — fake hostname + `/etc/hosts` on your computer
- `./scripts/check-prerequisites.sh private` after the project is on disk

---

## No domain (`4) private-ip`)

Use when you have a **VPS with a public IP** but **no registrar domain**. No DNS; add one line to `/etc/hosts` on your computer; self-signed TLS on the server.

**Goal after setup:** **https://editor.shiftedblog.local/login** (fake name, resolved via hosts).

### Step 1. Get the project on the server

Same as [production-deploy.md](production-deploy.md) step 2 — clone into `/opt/shiftedblog` (or your path). Then:

```bash
cd /opt/shiftedblog
./scripts/check-prerequisites.sh private
```

### Step 2. Setup

```bash
cd /opt/shiftedblog
./scripts/setup.sh
```

1. Choose **`4) private-ip`**
2. Enter the server **public IP** (auto-detected when possible)
3. Answer **`n`** to “Start Docker now?” — TLS first (step 3)

Defaults in `secrets.env`:

| Variable | Value |
|----------|-------|
| `FAKE_HOSTNAME` | `true` |
| `DOMAIN` | `shiftedblog.local` |
| `EDITOR_DOMAIN` | `editor.shiftedblog.local` |
| `SITE_URL` / `EDITOR_URL` | `https://editor.shiftedblog.local` |
| `PUBLIC_SITE_ENABLED` | `false` |
| `SSL_CERT_NAME` | `shiftedblog.local` |
| `SERVER_IP` | your public IP |

### Step 3. TLS (self-signed)

```bash
cd /opt/shiftedblog
docker compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true
sudo ./scripts/generate-self-signed-cert.sh
```

Cert includes fake hostname and server IP (SAN). Path: `/etc/letsencrypt/live/shiftedblog.local/`.

### Step 4. Deploy

```bash
./deploy.sh
```

### Step 5. Hosts file on your computer

On **each PC** you use for the editor, add (replace with your IP):

```text
YOUR_VPS_IP  editor.shiftedblog.local
```

| OS | File |
|----|------|
| Linux / macOS | `/etc/hosts` |
| Windows | `C:\Windows\System32\drivers\etc\hosts` |

Without this line the browser cannot resolve `editor.shiftedblog.local`.

### Step 6. Login

1. Open **https://editor.shiftedblog.local/login**
2. Accept the self-signed certificate warning once
3. Sign in as staff → **/posts**
4. Staff feed: **https://editor.shiftedblog.local/lenta/** (Django login if prompted)

### Later: real domain

When you buy a domain, switch to **With your domain** below (`3) private` or `./scripts/apply-domain.sh --domain example.com --private`), obtain Let's Encrypt, `./deploy.sh`, remove the hosts line.

---

## With your domain (`3) private`)

**Goal after setup:** **https://editor.example.com/login**

### Step 1. DNS

Create one **A record**:

| Name | Type | Value |
|------|------|-------|
| `editor` | A | `YOUR_VPS_IP` |

Optional: add the server IP in setup for testing before DNS propagates (self-signed TLS).

### Step 2. Get the project on the server

Same as [production-deploy.md](production-deploy.md) step 2 — clone into `/opt/shiftedblog` (or your path).

```bash
cd /opt/shiftedblog
./scripts/check-prerequisites.sh private
```

### Step 3. Setup

```bash
cd /opt/shiftedblog
./scripts/setup.sh
```

Choose **`3) private`** (not `4) private-ip` — see [no domain](#no-domain-4-private-ip)). You will be asked for:

- **Parent domain** (e.g. `example.com`) — used for session cookies (`.example.com`)
- **Editor hostname** (default `editor.example.com`)
- Optional server IP, legacy editor redirects, cert name

The script writes `secrets.env` with:

- `PUBLIC_SITE_ENABLED=false`
- `SITE_URL=https://editor.example.com` (same as `EDITOR_URL`)
- Editor-only nginx config

Answer **`n`** to “Start Docker now?” until TLS exists.

### Step 4. TLS

Stop nginx if it is running, then issue a cert for the editor host (often the same cert directory as the parent domain, e.g. `SSL_CERT_NAME=example.com` when the cert includes `editor.example.com`):

```bash
docker compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true
sudo certbot certonly --standalone --agree-tos --register-unsafely-without-email \
  -d editor.example.com
```

Set `SSL_CERT_NAME` in `secrets.env` to the **directory name** under `/etc/letsencrypt/live/` (not always the editor hostname).

Self-signed fallback (DNS not ready): same approach as [production-deploy.md](production-deploy.md) step 5.

### Step 5. Deploy

```bash
./deploy.sh
```

`deploy.sh` detects `PUBLIC_SITE_ENABLED=false` and runs `check-env.sh private`.

### Step 6. Login

| URL | Purpose |
|-----|---------|
| https://editor.example.com/login | **Editor UI — start here** |
| https://editor.example.com/posts | Post list |
| https://editor.example.com/lenta/ | Staff feed (all published posts; Django login) |
| https://editor.example.com/{ADMIN_URL}/ | Django admin (path from `secrets.env`) |

---

## Changing domain later

```bash
./scripts/apply-domain.sh --domain example.com --private \
  --editor-domain editor.example.com
```

Does not rotate `SECRET_KEY`, `ADMIN_URL`, or database passwords. Re-run `./deploy.sh` after.

---

## Related docs

- [Getting started](getting-started.md)
- [Online deploy (public site)](production-deploy.md)
- [Configuration](configuration.md) — `PUBLIC_SITE_ENABLED`
- [Host migration](host-migration.md)
