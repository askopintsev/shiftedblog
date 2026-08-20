# Host and domain migration

Русский: [Перенос хоста и домена](../ru/host-migration.md)

## Your goal: same blog on a new VPS and/or domain

After migration you should be able to open:

**https://editor.new.example.com/login** → sign in → **https://editor.new.example.com/posts**

When changing domain (scenario B), legacy URLs (`https://old.example.com/…`) must return **HTTPS 301** to the new `SITE_URL` from the **new** VPS until the old domain expires.

> This guide is **provider-agnostic**. Use `backup_db` / `restore_db`, `./scripts/apply-domain.sh`, and `REDIRECT_FROM_*` in nginx.

**Migration order:** inventory (1) → new domain DNS (2) → prepare VPS (3) → project + restore (4) → TLS + rehearsal (5) → cutover (6) → old domain sunset (7). Point **legacy** public DNS at the new IP only at **step 6** (except the **new** domain zone for rehearsal at step 5).

## Before you start

- A working production install on the old VPS (`secrets.env`, backups)
- Off-box copies of `backups/*.sql.gz`, `backups/media_*.tar.gz`, and `secrets.env`
- Postgres dump major version **17** (matches `docker-compose.prod.yml`)
- When restoring, do **not** rotate `SECRET_KEY`, `CREDENTIALS_ENCRYPTION_KEY`, `ADMIN_URL`, or database passwords

## Scenarios

| | **A — Same hostname, new VPS** | **B — New hostname + soft sunset** |
|---|-------------------------------|-------------------------------------|
| What changes | Server IP only | `SITE_URL`, editor hostname |
| DNS cutover | Old zone A/AAAA → new IP | Old zone → new IP; new zone from step 5 |
| Old VPS | Power off 24–48h after cutover | Same |
| Legacy 301s | Not needed | `REDIRECT_FROM_DOMAINS` / `REDIRECT_FROM_EDITOR_DOMAINS` |

Example (B): `https://old.example.com` → `https://new.example.com`, editor `https://editor.new.example.com`.

`EXTRA_DOMAINS` serves the **same** site on extra hosts (duplicate content). For **legacy** 301s use `REDIRECT_FROM_*`, **not** `EXTRA_DOMAINS`.

---

## Step 1. Inventory (source host)

On the **current** production server (never commit secrets):

```bash
cd /opt/shiftedblog
pwd
hostname -I
docker compose version
ls /etc/letsencrypt/live/ 2>/dev/null || true
crontab -l
grep -E '^(DOMAIN|SITE_URL|EDITOR_|SSL_CERT_NAME|EXTRA_DOMAINS|REDIRECT_FROM|EMAIL_HOST|SERVER_IP)=' secrets.env
```

Record off-box:

- [ ] Public IPv4 / IPv6, app path (usually `/opt/shiftedblog`)
- [ ] DNS: A/AAAA for apex, `www`, `editor`
- [ ] Mail (SMTP), cron, certificates, CI (`VPS_HOST`), search consoles

Lower the **old** zone TTL to 300s if the panel allows.

Backup:

```bash
cd /opt/shiftedblog
docker compose -f docker-compose.prod.yml exec -T web python manage.py backup_db
```

Copy `backups/*.sql.gz`, `backups/media_*.tar.gz`, and `secrets.env` to your laptop or object storage.

---

## Step 2. New domain DNS

**Scenario A** — skip if the hostname does not change.

In your **registrar / DNS panel** for the **new** domain:

| Name | Type | Value |
|------|------|-------|
| `@` | A | `NEW_VPS_IP` (at step 5) or parking IP |
| `www` | A | same |
| `editor` | A | same |

- [ ] Nameservers are correct
- [ ] Do **not** change the **old** zone until cutover (step 6)

When A records point at the new VPS:

```bash
dig +short new.example.com A
dig +short editor.new.example.com A
```

---

## Step 3. Prepare the new VPS

Replace `NEW_VPS_IP` and `deploy` with your values.

### SSH keys

Use an **operator key** on your laptop (not the GitHub Actions deploy key — that is for CI):

```bash
test -f ~/.ssh/id_ed25519.pub || ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -C "shiftedblog-operator"
cat ~/.ssh/id_ed25519.pub
```

Install the **public** line via the provider panel or console (`/root/.ssh/authorized_keys`). Then:

```bash
ssh -o PreferredAuthentications=publickey root@NEW_VPS_IP
```

If you see `Permission denied (publickey,password)`, the key is not on the server yet. Never upload the private key.

Create a sudo user (keep the root session open until a second terminal confirms login):

```bash
adduser --disabled-password --gecos "" deploy
usermod -aG sudo deploy
passwd deploy
mkdir -p /home/deploy/.ssh && chmod 700 /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/authorized_keys
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh

mkdir -p /etc/ssh/sshd_config.d
cat >/etc/ssh/sshd_config.d/99-shiftedblog-hardening.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
EOF
sshd -t && systemctl reload ssh
```

Confirm from a **new** terminal: `ssh deploy@NEW_VPS_IP` and `sudo true`.

### Ports 80 and 443

Docker nginx and Let's Encrypt need **80** and **443** free:

```bash
ss -tlnp | grep -E ':80|:443' || echo "ports 80 and 443 are free"
```

On macOS without `ss`:

```bash
lsof -nP -iTCP:80 -sTCP:LISTEN
lsof -nP -iTCP:443 -sTCP:LISTEN
```

| What you see in `ss` | Action |
|----------------------|--------|
| **nginx** / **apache2** | Host panel web server — stop it (below) |
| **docker-proxy** | Old Docker stack — `docker compose down` or `./scripts/vps-clean-for-fresh-deploy.sh` |
| Empty | Continue to Docker install |

```bash
sudo systemctl stop nginx apache2 2>/dev/null || true
sudo systemctl disable nginx apache2 2>/dev/null || true
ss -tlnp | grep -E ':80|:443' || echo "ports 80 and 443 are free"
```

### Packages, firewall, Docker

```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y ca-certificates curl ufw fail2ban certbot
sudo ufw --force reset && sudo ufw default deny incoming && sudo ufw default allow outgoing
sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw --force enable
```

Docker (Ubuntu/Debian):

```bash
curl -fsSL https://get.docker.com | sh
sudo systemctl enable --now docker
sudo usermod -aG docker deploy
```

Log in again as `deploy`, then verify:

```bash
docker compose version
certbot --version
```

---

## Step 4. Project and restore

> Do **not** run `./scripts/setup.sh` when migrating an existing site — the wizard generates a new `ADMIN_URL` and may overwrite keys.

### Get the project

```bash
sudo mkdir -p /opt/shiftedblog
sudo chown deploy:deploy /opt/shiftedblog
cd /opt/shiftedblog
git clone https://github.com/YOUR_USER/shiftedblog.git .
```

If Git is unavailable — ZIP archive, see [local-deploy.md](local-deploy.md) step 1.

```bash
cd /opt/shiftedblog
./scripts/check-prerequisites.sh online
chmod +x scripts/*.sh scripts/backup/*.sh
```

### Copy backups and secrets.env

From your laptop:

```bash
scp /path/to/*_pg_dump_*.sql.gz deploy@NEW_VPS_IP:/opt/shiftedblog/backups/
scp /path/to/media_*.tar.gz deploy@NEW_VPS_IP:/opt/shiftedblog/backups/
scp /path/to/old-secrets.env deploy@NEW_VPS_IP:/opt/shiftedblog/secrets.env
```

### Update domain keys (no secret rotation)

**Scenario A** (same domain, new IP):

```bash
cd /opt/shiftedblog
./scripts/apply-domain.sh \
  --domain example.com \
  --site-url https://example.com \
  --editor-domain editor.example.com \
  --ssl-cert-name example.com \
  --server-ip NEW_VPS_IP
```

**Scenario B** (new domain + legacy 301s):

```bash
cd /opt/shiftedblog
./scripts/apply-domain.sh \
  --domain new.example.com \
  --site-url https://new.example.com \
  --editor-domain editor.new.example.com \
  --ssl-cert-name new.example.com \
  --redirect-from old.example.com,www.old.example.com \
  --redirect-from-editor editor.old.example.com \
  --server-ip NEW_VPS_IP
```

Only list names in `--redirect-from*` that **resolve in public DNS** when you request certificates.

`apply-domain.sh` regenerates nginx; rebuild the editor UI with **`./deploy.sh`** (step 5).

### Restore data

```bash
cd /opt/shiftedblog
mkdir -p logs static media static_blog backups
docker compose -f docker-compose.prod.yml up -d db redis web
./scripts/backup/restore.sh --dry-run
./scripts/backup/restore.sh --force
```

---

## Step 5. TLS and rehearsal

All commands assume `/opt/shiftedblog`. The **new** domain DNS must point at `NEW_VPS_IP` (or use a hosts file on your laptop for rehearsal before cutover).

> In the commands below, `new.example.com` is the **new** domain (scenario B). For **scenario A**, substitute your existing domain (`example.com`, `editor.example.com`).

```bash
cd /opt/shiftedblog
dig +short new.example.com A
```

### First Let's Encrypt certificate

```bash
sudo mkdir -p /var/www/html
docker compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true
sudo systemctl stop nginx 2>/dev/null || true
sudo certbot certonly --standalone --agree-tos --register-unsafely-without-email \
  -d new.example.com -d www.new.example.com -d editor.new.example.com
```

`SSL_CERT_NAME` in `secrets.env` must match the directory under `/etc/letsencrypt/live/` (usually the primary domain).

### Launch the stack

```bash
cd /opt/shiftedblog
./deploy.sh
```

The first run may take **several minutes** (image build, including the editor UI).

Renewals later (stack already running):

```bash
sudo certbot certonly --webroot -w /var/www/html \
  -d new.example.com -d www.new.example.com -d editor.new.example.com
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

### Rehearsal before cutover (hosts file)

If the **legacy** zone still points at the old VPS, on your laptop:

```text
NEW_VPS_IP  new.example.com
NEW_VPS_IP  www.new.example.com
NEW_VPS_IP  editor.new.example.com
```

Then open **https://editor.new.example.com/login** (browser cert warnings are normal if LE covers only the new domain).

### Rehearsal checklist

- [ ] Homepage, post, media image
- [ ] Canonical / sitemap host = `SITE_URL`
- [ ] **https://editor.new.example.com/login** — sign in (cookies on new parent domain → expect re-login)
- [ ] `ENV_FILE=secrets.env ./scripts/check-env.sh online`
- [ ] `docker compose -f docker-compose.prod.yml ps` — all services up

---

## Step 6. Cutover

> **Scenario A:** point the old zone A/AAAA at `NEW_VPS_IP`, reissue the cert if needed (step 5, without `--expand` or legacy names), run `./deploy.sh`, and verify the editor. Items 4–5 below are for **scenario B** only.

1. **Freeze writes** on the old VPS: `docker compose -f docker-compose.prod.yml stop web`
2. **Final backup** on the old VPS; `./scripts/backup/restore.sh --force` on the new VPS if needed
3. **Legacy zone DNS** — A/AAAA (apex, `www`, `editor`) → **NEW_VPS_IP**
4. **Expand the certificate** — only names that already resolve to the new IP:

```bash
cd /opt/shiftedblog
docker compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true
sudo systemctl stop nginx 2>/dev/null || true
sudo certbot certonly --standalone --cert-name new.example.com --expand \
  --agree-tos --register-unsafely-without-email \
  -d new.example.com -d www.new.example.com -d editor.new.example.com \
  -d old.example.com -d www.old.example.com -d editor.old.example.com
./deploy.sh
```

5. **Verify:**

```bash
curl -sI https://www.old.example.com/ | head -3
# expect 301 → https://new.example.com/
curl -sI https://new.example.com/ | head -3
# expect 200
curl -skI https://editor.new.example.com/login | head -1
docker compose -f docker-compose.prod.yml ps
```

Open **https://editor.new.example.com/login** in a browser.

6. Update CI / secret manager — [maintainer.md](maintainer.md)
7. After **24–48h**, **power off the old VPS**

Mail can stay on the old SMTP until you create addresses on the new domain — see [security-runbook.md](../security-runbook.md).

---

## Step 7. Soft sunset (scenario B)

- Old domain = DNS + certificates on the **new** VPS only; old server is off
- Set a calendar reminder **before** old domain expiry: do not renew if redirects are enough until then
- **~2 weeks before expiry**: remove `REDIRECT_FROM_*` via `./scripts/apply-domain.sh`, reissue cert for new names only, delete old DNS records
- After expiry, legacy URLs stop resolving

---

## Cron on the new VPS

```bash
0 3 * * * cd /opt/shiftedblog && ./scripts/backup/run-backup.sh
```

Optional weekly report: [security-runbook.md](../security-runbook.md).

---

## Related

- [Online deploy (on server)](production-deploy.md) — first install from scratch
- [Local deploy](local-deploy.md) — development on your computer
- [configuration.md](configuration.md) — `REDIRECT_FROM_*`, `EXTRA_DOMAINS`
- [maintainer.md](maintainer.md) — CI and Doppler
