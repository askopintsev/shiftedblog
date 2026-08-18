# Host and domain migration

Русский: [../ru/host-migration.md](../ru/host-migration.md)

Move ShiftedBlog to a new VPS and/or public hostname. The app stays provider-agnostic: use `backup_db` / `restore_db`, `apply-domain.sh`, and `REDIRECT_FROM_*` in nginx.

Do **not** rotate `SECRET_KEY` or `CREDENTIALS_ENCRYPTION_KEY` when restoring an existing site. Postgres dumps must match the server major version (**17** in `docker-compose.prod.yml`).

## Scenarios

1. **A — Same hostname, new VPS** — only the IP changes.
2. **B — New hostname + soft sunset** — new `SITE_URL`; legacy names return HTTPS 301 on the **new** VPS until the old domain expires. The old VPS is powered off after cutover.

Example (B): `https://old.example.com` → `https://new.example.com`, editor `https://editor.new.example.com`. Legacy DNS for `old.example.com` / `www` / `editor` points at the new VPS until you drop the old zone.

`EXTRA_DOMAINS` serves the **same** site on extra hosts (duplicate content). Use `REDIRECT_FROM_DOMAINS` / `REDIRECT_FROM_EDITOR_DOMAINS` for legacy 301s.

## Operator increments

Work in order. Do not point public DNS at the new VPS until the cutover step (except the **new** domain zone for rehearsal).

1. Inventory + off-box backup + lower TTL on the **old** zone
2. DNS zone for the **new** domain (A records can wait for the new IP)
3. New VPS: SSH keys, OS, firewall, Docker
4. Install app + restore (no public cutover yet)
5. Rehearsal on the new hostname (DNS or `/etc/hosts`)
6. Cutover (legacy DNS + cert expand + 301s + CI)
7. Power off old VPS after 24–48h
8. Sunset calendar for the old domain (do not renew; remove redirects before expiry)

---

## 1. Inventory (source host)

On the **current** production server (never commit secrets):

```bash
pwd
hostname -I
docker --version
docker compose version
ls /etc/letsencrypt/live/ 2>/dev/null || true
crontab -l
grep -E '^(DOMAIN|SITE_URL|EDITOR_|SSL_CERT_NAME|EXTRA_DOMAINS|REDIRECT_FROM|EMAIL_HOST)=' secrets.env
```

Record off-box:

- [ ] Public IPv4 / IPv6
- [ ] App path (often `/opt/shiftedblog`)
- [ ] Docker / Compose versions
- [ ] DNS: A/AAAA/CNAME/MX/TXT for apex, `www`, `editor`
- [ ] Mail (SMTP host, from-address) — see [security-runbook.md](../security-runbook.md)
- [ ] Cron (`scripts/backup/run-backup.sh`, optional `security_auth_report`)
- [ ] `SSL_CERT_NAME` and `/etc/letsencrypt/live/`
- [ ] CI: `VPS_HOST`, deploy SSH user (names only)
- [ ] Search consoles / verification files / profile URLs

Backup:

```bash
cd /opt/shiftedblog
docker compose -f docker-compose.prod.yml exec -T web python manage.py backup_db
```

Copy `backups/*.sql.gz`, `backups/media_*.tar.gz`, and `secrets.env` somewhere private. Lower the old zone TTL to 300s if the panel allows.

---

## 2. New domain DNS

In your **registrar / DNS panel** for the new domain:

- [ ] Nameservers are correct
- [ ] Records for apex `@`, `www`, `editor` (or a wildcard `*`) — A/AAAA may point at a parking IP until the new VPS exists
- [ ] Do **not** change the **old** zone until cutover

At cutover, point the new zone at the **new VPS IP**. Wildcard `*` covers `www` and `editor` if you use it.

---

## 3. New VPS bootstrap

Replace `NEW_VPS_IP` and `deploy` with your values.

### SSH keys first

Many images ship with root key-only login and no password. Use an **operator key** on your laptop (not the GitHub Actions deploy key — that is for CI later).

```bash
# laptop
test -f ~/.ssh/id_ed25519.pub || ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -C "shiftedblog-operator"
cat ~/.ssh/id_ed25519.pub
```

Install the **public** line via the provider panel (SSH keys) or console (`/root/.ssh/authorized_keys`). Then:

```bash
ssh -o PreferredAuthentications=publickey root@NEW_VPS_IP
```

If you see `Permission denied (publickey,password)`, the key is not on the server yet — use the provider console to append the `.pub` line. Never upload the private key.

Create a sudo user (keep the root session open until a second terminal confirms login):

```bash
adduser --disabled-password --gecos "" deploy
usermod -aG sudo deploy
passwd deploy   # for sudo only; SSH stays key-only
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

### Packages, firewall, Docker

Some VPS images include a **host** web panel (nginx/apache on :80). Docker nginx needs ports 80/443 free.

```bash
sudo ss -tlnp | grep -E ':80|:443|:22'
sudo systemctl stop nginx apache2 2>/dev/null || true
sudo systemctl disable nginx apache2 2>/dev/null || true
# stop any panel services binding :80 if present

sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y ca-certificates curl ufw fail2ban certbot
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

Install [Docker Engine + Compose plugin](https://docs.docker.com/engine/install/ubuntu/) for your OS, then:

```bash
sudo usermod -aG docker deploy
# log out and back in
docker --version
docker compose version
```

---

## 4. Install + restore

Do **not** run `setup.sh` on a restored site — it can rotate `ADMIN_URL`. Copy the old `secrets.env` and use `apply-domain.sh`.

```bash
sudo mkdir -p /opt/shiftedblog/backups
sudo chown deploy:deploy /opt/shiftedblog
```

Deploy the code (`git clone` or rsync from your machine). Copy from your laptop:

```bash
scp /path/to/*_pg_dump_*.sql.gz deploy@NEW_VPS_IP:/opt/shiftedblog/backups/
scp /path/to/media_*.tar.gz deploy@NEW_VPS_IP:/opt/shiftedblog/backups/
scp /path/to/old-secrets.env deploy@NEW_VPS_IP:/opt/shiftedblog/secrets.env
```

On the VPS:

```bash
cd /opt/shiftedblog
chmod +x scripts/apply-domain.sh scripts/backup/restore.sh scripts/generate-nginx-conf.sh

./scripts/apply-domain.sh \
  --domain new.example.com \
  --site-url https://new.example.com \
  --editor-domain editor.new.example.com \
  --ssl-cert-name new.example.com \
  --redirect-from old.example.com,www.old.example.com \
  --redirect-from-editor editor.old.example.com \
  --server-ip NEW_VPS_IP

mkdir -p logs static media static_blog
docker compose -f docker-compose.prod.yml up -d db redis web
./scripts/backup/restore.sh --dry-run
./scripts/backup/restore.sh --force
```

Only list names in `--redirect-from*` that **resolve in public DNS** when you request certificates. Skip dead zones (NXDOMAIN).

---

## 5. TLS and rehearsal

### First certificate (new hostname only)

Point **new** domain A records at `NEW_VPS_IP`. Port 80 must be free (stop host nginx and `docker compose stop nginx` if needed):

```bash
dig +short new.example.com A
sudo systemctl stop nginx 2>/dev/null || true
docker compose -f docker-compose.prod.yml stop nginx
sudo ss -tlnp | grep ':80 '   # empty

sudo certbot certonly --standalone \
  -d new.example.com -d www.new.example.com -d editor.new.example.com

docker compose -f docker-compose.prod.yml up -d nginx
./deploy.sh
```

Renewals later can use `--webroot -w /var/www/html` once Compose nginx serves ACME challenges.

### Rehearsal checklist

- [ ] Homepage, post, media image
- [ ] Canonical / sitemap host = `SITE_URL`
- [ ] Editor login (cookies on new parent domain — expect re-login)
- [ ] `ENV_FILE=secrets.env ./scripts/check-env.sh production`

---

## 6. Cutover

1. Freeze writes on the old VPS (`docker compose -f docker-compose.prod.yml stop web`).
2. Final `backup_db`; `restore_db --force` on the new VPS if needed.
3. Point **old** zone A/AAAA (apex, `www`, `editor`) at **NEW_VPS_IP** (same as new domain).
4. Expand the certificate — **only names that resolve**:

```bash
docker compose -f docker-compose.prod.yml stop nginx
sudo systemctl stop nginx 2>/dev/null || true
sudo certbot certonly --standalone --cert-name new.example.com --expand \
  -d new.example.com -d www.new.example.com -d editor.new.example.com \
  -d old.example.com -d www.old.example.com -d editor.old.example.com
docker compose -f docker-compose.prod.yml up -d nginx
./deploy.sh
```

5. Verify:

```bash
curl -sI https://www.old.example.com/ | head -3
# 301 → https://new.example.com/
curl -sI https://new.example.com/ | head -3
# 200
```

6. Update CI `VPS_HOST`, secret manager `SITE_URL` / hosts / redirects — [maintainer.md](maintainer.md).
7. Search consoles: add new property; change-of-address if offered.
8. After 24–48h: **power off the old VPS**.

Mail can stay on the old SMTP mailbox until you create addresses on the new domain.

---

## 7. Soft sunset (scenario B)

- Old domain = DNS + certs on the **new** VPS only; old VPS is off.
- Set a calendar reminder **before** old domain expiry: do not renew if redirects are enough until then.
- **~2 weeks before expiry**: remove `REDIRECT_FROM_*`, reissue cert for new names only, delete old DNS records.
- After expiry, legacy URLs stop resolving.

---

## Cron on the new VPS

```bash
0 3 * * * cd /opt/shiftedblog && ./scripts/backup/run-backup.sh
```

Optional weekly report: [security-runbook.md](../security-runbook.md).

---

## Related

- [production-deploy.md](production-deploy.md)
- [configuration.md](configuration.md)
- [maintainer.md](maintainer.md)
