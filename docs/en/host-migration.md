# Host and domain migration

Русский: [../ru/host-migration.md](../ru/host-migration.md)

Move ShiftedBlog to a new VPS and/or hostname without baking a provider into the app. Third-party installs use the same scripts: `backup_db` / `restore_db`, `apply-domain.sh`, and `REDIRECT_FROM_*` in nginx.

Do **not** rotate `SECRET_KEY` or `CREDENTIALS_ENCRYPTION_KEY` when restoring an existing site. Postgres dumps must match the server major (**17** in `docker-compose.prod.yml`).

## Choose a scenario

1. **A — Same hostname, new VPS** — only the IP changes.
2. **B — New hostname + soft sunset** — new `SITE_URL`, old names HTTPS 301 on the **new** VPS until the old domain expires. The old VPS is powered off after cutover.

Worked example (Scenario B): live `SITE_URL` is **apex** `https://shiftedstuff.ru` (`PREPEND_WWW=false`; `www` also answers). Target: `https://shiftedstuff.space`, editor `https://editor.shiftedstuff.space`. Also serving today: `shiftedstuff.online` / `www` / `editor`. Old VPS (Beget, `90.156.169.116`) is shut down after the flip. Domain `shiftedstuff.ru` is paid until **21.01.2027** and is **not** renewed. Keep Beget SMTP (`noreply@shiftedstuff.ru`) until mail moves.

| Date | Action |
|------|--------|
| Cutover | Both zones point at the new VPS; 301s live; old VPS off after 24–48h |
| **01.12.2026** | Do not renew `.ru` |
| **~07.01.2027** | Remove `REDIRECT_FROM_*`, reissue cert for `.space` only, delete `.ru` DNS |
| **21.01.2027** | `.ru` expires; old URLs stop resolving |

`EXTRA_DOMAINS` serves the **same** site on extra hosts (duplicate content). Use `REDIRECT_FROM_DOMAINS` / `REDIRECT_FROM_EDITOR_DOMAINS` for legacy 301s.

## Operator increments (this move)

Do one increment, paste results back, then take the next. Do not point public DNS at the new VPS until the cutover increment.

1. **Inventory + off-box backup + lower `.ru` TTL** (source / Beget) — done (2026-08-13)
2. Jino zone for `.space` (A records can wait) — done (2026-08-13)
3. FirstVDS: SSH keys, OS, firewall, Docker — done (2026-08-14). ufw 22/80/443; host nginx/ISPmanager/named disabled.
4. Install + restore on FirstVDS (no public DNS yet) — you are here
5. Hosts-file rehearsal
6. Cutover (DNS + certs + 301s + CI)
7. Power off Beget after 24–48h
8. Sunset calendar (do not renew `.ru`)

---

## Inventory (source host)

Copy this off the old VPS (never commit secrets). On the **current** (Beget) server:

```bash
# confirm path (often /opt/shiftedblog)
pwd
hostname -I
docker --version
docker compose version
ls /etc/letsencrypt/live/ 2>/dev/null || true
crontab -l
# names only — do not paste secret values into chat or git
grep -E '^(DOMAIN|SITE_URL|EDITOR_|SSL_CERT_NAME|EXTRA_DOMAINS|EMAIL_HOST)=' secrets.env
```

- [ ] Public IPv4 / IPv6
- [ ] App path (docs assume `/opt/shiftedblog`)
- [ ] Docker / Compose versions
- [ ] DNS: A/AAAA/CNAME/MX/TXT for apex, `www`, `editor`
- [ ] Mail (host, from-address). Beget example: `smtp.beget.com` — see [security-runbook.md](../security-runbook.md)
- [ ] Cron (`scripts/backup/run-backup.sh`, optional `security_auth_report`)
- [ ] `SSL_CERT_NAME` and `/etc/letsencrypt/live/`
- [ ] CI: `VPS_HOST`, deploy SSH user (names only)
- [ ] Webmaster / Dzen / profile URLs

Backup and store **off both** machines:

```bash
cd /opt/shiftedblog
docker compose -f docker-compose.prod.yml exec -T web python manage.py backup_db
```

Copy `backups/*.sql.gz`, `backups/media_*.tar.gz`, and `secrets.env` somewhere private. Lower the old zone TTL to 300s if the panel allows.

### Increment 2 — Jino zone (this move)

In the Jino panel for `shiftedstuff.space`:

- [x] Domain is delegated to Jino NS (`ns1`–`ns4.jino.ru`)
- [x] A today: `@` and `*.shiftedstuff.space` → `81.177.141.15` (Jino parking — **not** Beget). Change to FirstVDS IP at cutover. Wildcard covers `www` and `editor`.
- [ ] Optional TXT later (SPF) — not required until mail moves

Do not change Beget `.ru` / `.online` records yet.

### This move (Beget, 2026-08-13)

| Item | Value |
|------|--------|
| Path | `/opt/shiftedblog` |
| IPv4 | `90.156.169.116` (docker bridges `172.17.0.1` `172.18.0.1` — ignore) |
| Docker | 28.3.1 / Compose v2.38.1 |
| Cert dir | `/etc/letsencrypt/live/shiftedstuff.ru` |
| `SITE_URL` | `https://shiftedstuff.ru` (not www) |
| Editor | `https://editor.shiftedstuff.ru` |
| Extra hosts | `shiftedstuff.online`, `www`, `editor` (same site today) |
| Mail | `smtp.beget.com:465` SSL, `noreply@shiftedstuff.ru` |
| Secrets | Doppler `shifted_blog` / `prd` (no `DOMAIN` / `SSL_CERT_NAME` keys; nginx is generated/committed) |
| Dzen | `DZEN_VERIFICATION_FILE` set |
| Cron | `0 3 * * *` `scripts/backup/run-backup.sh`; Sun `15 3` delete backups `+30` days; Mon `0 9` `security_auth_report --hours 168 --email` |

`secrets.env` on the new VPS must keep the same `SECRET_KEY` and `CREDENTIALS_ENCRYPTION_KEY`. DB name/user today: `blog_db` / `blogger`.

---

## Provision (target host)

1. Create the new zone (example: Jino for `shiftedstuff.space`) with apex, `www`, `editor`. **Do not** point A/AAAA at the Beget IP. Leave A empty or a dummy until FirstVDS exists.
2. New VPS (example: FirstVDS `94.250.250.65`): **SSH key access before anything else**, then Ubuntu packages, `ufw` 22/80/443, Docker Compose. Do **not** clone the app yet (next increment).

This move: FirstVDS `94.250.250.65`, Ubuntu 24.04.4 LTS, hostname `milleniumfalcon`. Operator pubkey is in `/root/.ssh/authorized_keys` (2026-08-14). Next: sudo user `deploy`, then packages.

**Operator key (laptop), not the GitHub Actions deploy key** (`scripts/ssh/generate-vps-deploy-key.sh` is for CI later):

```bash
# on your laptop — reuse ~/.ssh/id_ed25519 if you already have one
test -f ~/.ssh/id_ed25519.pub || ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -C "shiftedblog-operator"
cat ~/.ssh/id_ed25519.pub
```

FirstVDS panel → server → SSH keys (or file `/root/.ssh/authorized_keys` via VNC): paste that **one line**. Then from the laptop:

```bash
ssh -o PreferredAuthentications=publickey root@94.250.250.65
```

If you see `Permission denied (publickey,password)`: the daemon is up, but **this laptop key is not in `/root/.ssh/authorized_keys` yet**. Adding the key only in chat or only generating it locally does nothing. FirstVDS with “password not set” still needs the `.pub` line installed via **panel SSH keys** (then reboot/reapply if the panel says so) or **VNC/KVM console**.

On the laptop, confirm which key `ssh` sends:

```bash
ssh -v -o PreferredAuthentications=publickey root@94.250.250.65 2>&1 | grep -E 'Offering public key|Authentications that can continue|identity file'
cat ~/.ssh/id_ed25519.pub
```

Via FirstVDS **VNC** (as root):

```bash
mkdir -p /root/.ssh
chmod 700 /root/.ssh
# paste the exact one-line .pub (ssh-ed25519 AAAA... comment)
nano /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
restorecon -Rv /root/.ssh 2>/dev/null || true
```

Retry `ssh`. Do not create `deploy` or disable passwords until that works. Never paste the **private** key into the panel.

On the VPS, create a sudo user and lock password SSH. Keep this root session open until a **second** terminal logs in as the new user.

```bash
# on the VPS as root — pick a username you will use daily
adduser --disabled-password --gecos "" deploy
usermod -aG sudo deploy
passwd deploy
# set a sudo password (SSH stays key-only; this is not the FirstVDS panel password)
mkdir -p /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
# paste the SAME operator .pub line
nano /home/deploy/.ssh/authorized_keys
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh

cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak
# Debian/Ubuntu drop-in (survives package upgrades)
mkdir -p /etc/ssh/sshd_config.d
cat >/etc/ssh/sshd_config.d/99-shiftedblog-hardening.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
EOF
sshd -t && systemctl reload ssh
```

In a **new** laptop terminal, confirm before closing root:

```bash
ssh -o PreferredAuthentications=publickey deploy@94.250.250.65
sudo -n true || sudo true
```

Optional later: `PermitRootLogin no` after you are sure `deploy` + sudo works. CI deploy key is a **second** pubkey on this user (`scripts/ssh/install-vps-authorized-key.sh`) — not now.

Then packages (as `deploy` with sudo):

```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y ca-certificates curl ufw fail2ban
```

Install Docker from Docker’s Ubuntu repo (creates the `docker` group — `usermod -aG docker` **after** that). Then firewall. FirstVDS images often ship **ISPmanager + mail/FTP/DNS** `ufw` allows. This project only needs 22/80/443. Check who owns 80/443 before Compose:

```bash
sudo ss -tlnp | grep -E ':80|:443|:22'
sudo ufw status numbered
```

If `ispmanager`, `exim`, `named`, or a panel nginx is on 80/443, stop/disable that stack so Docker nginx can bind:

```bash
sudo systemctl stop nginx apache2 ihttpd 2>/dev/null || true
sudo systemctl disable nginx apache2 ihttpd 2>/dev/null || true
sudo systemctl stop named bind9 2>/dev/null || true
sudo systemctl disable named bind9 2>/dev/null || true
sudo ss -tlnp | grep -E ':80|:443|:1500'
```

Port 80/443 must be free (sshd on 22 is expected). Then reset ufw to a tight policy...

```bash
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status
```

This move (2026-08-14): Docker 29.7.2 / Compose v5.4.0; ufw tightened to 22/80/443. Host **nginx** was on `:80`, ISPmanager `ihttpd` on `:1500`, `named` on `:53`. Stop/disable those before Compose.
3. Install the app as in [production-deploy.md](production-deploy.md). If migration scripts are not on `origin/master` yet, **rsync the laptop checkout** instead of `git clone` (exclude `.venv`, `node_modules`, `.env`, `secrets.env`). Do **not** run `setup.sh` for a restore: it would rotate `ADMIN_URL`. Copy the old `secrets.env` and run `apply-domain.sh`.

```bash
sudo mkdir -p /opt/shiftedblog
sudo chown "$USER:$USER" /opt/shiftedblog
cd /opt/shiftedblog
git clone https://github.com/YOUR_USER/shiftedblog.git .
./scripts/setup.sh
# production: new apex domain, canonical URL, optional REDIRECT_FROM_*
```

4. Copy crypto keys from the **old** `secrets.env` into the new file (`SECRET_KEY`, `CREDENTIALS_ENCRYPTION_KEY`). A new `DB_PASS` on the new box is fine.
5. Do **not** point public DNS at the new IP yet.

```bash
sudo mkdir -p /opt/shiftedblog/backups
sudo chown deploy:deploy /opt/shiftedblog/backups
```

Then from the laptop:

```bash
scp /path/to/*_pg_dump_*.sql.gz deploy@94.250.250.65:/opt/shiftedblog/backups/
scp /path/to/media_*.tar.gz deploy@94.250.250.65:/opt/shiftedblog/backups/
scp /path/to/beget-secrets.env deploy@94.250.250.65:/opt/shiftedblog/secrets.env
```

Restore (dump major must be 17):

```bash
cd /opt/shiftedblog
ls -lh backups/
./scripts/backup/restore.sh --dry-run
./scripts/backup/restore.sh --force
```

Or:

```bash
docker compose -f docker-compose.prod.yml exec -T web \
  python manage.py restore_db --force
```

`restore_db` refuses a non-empty public schema without `--force`, then sets `django.contrib.sites` `Site` (`SITE_ID=1`) from `SITE_URL`.

If you already ran setup with the old hostname, switch without rotating keys:

```bash
./scripts/apply-domain.sh \
  --domain shiftedstuff.space \
  --site-url https://shiftedstuff.space \
  --editor-domain editor.shiftedstuff.space \
  --redirect-from shiftedstuff.ru,www.shiftedstuff.ru \
  --redirect-from-editor editor.shiftedstuff.ru
./deploy.sh
```

---

## TLS

HSTS on the old site means browsers will only speak HTTPS to the old hostname. A redirect needs a **valid certificate** for those names on the new VPS.

Prefer **one** Let’s Encrypt cert (`SSL_CERT_NAME`) with all SANs:

- New: `shiftedstuff.space`, `www.shiftedstuff.space`, `editor.shiftedstuff.space`
- Legacy (Scenario B): `shiftedstuff.ru`, `www.shiftedstuff.ru`, `editor.shiftedstuff.ru`

Options:

1. HTTP-01 after `.space` DNS points at the new VPS. Install certbot on the host; **first** cert while Docker nginx is not up yet — use `--standalone` (port 80 must be free):

```bash
sudo apt-get update
sudo apt-get install -y certbot
If `certbot --standalone` says port 80 is in use but Compose has no `nginx` container, check **host** nginx (FirstVDS/ISPmanager image):

```bash
sudo ss -tlnp | grep ':80 '
docker compose -f docker-compose.prod.yml ps
sudo systemctl stop nginx apache2 ihttpd
sudo ss -tlnp | grep ':80 '   # must be empty before standalone
sudo certbot certonly --standalone -d example.com -d www.example.com -d editor.example.com
```
ls /etc/letsencrypt/live/shiftedstuff.space/
```

Later renewals can use `--webroot -w /var/www/html` once Compose nginx is running.

2. Copy `/etc/letsencrypt` from the old host for **old** names only; still issue a cert for the **new** names (or expand).
3. DNS-01 if the new zone is already in your registrar.

```bash
sudo mkdir -p /var/www/html
sudo certbot certonly --webroot -w /var/www/html \
  -d shiftedstuff.space -d www.shiftedstuff.space -d editor.shiftedstuff.space \
  -d shiftedstuff.ru -d www.shiftedstuff.ru -d editor.shiftedstuff.ru
```

---

## Dress rehearsal

On the new VPS, add `/etc/hosts` entries for the **new** names → new IP:

- [ ] Homepage, a post, and a media image
- [ ] Sitemap / canonical host matches `SITE_URL`
- [ ] Editor login (cookies are `.newdomain`; expect a re-login after a hostname change)
- [ ] `ENV_FILE=secrets.env ./scripts/check-env.sh production`
- [ ] `./scripts/backup/run-backup.sh` (or `restore.sh --dry-run`)

Legacy 301s need the old names in DNS or hosts **and** a cert covering them.

Rollback until cutover: leave public A records on the old IP.

---

## Cutover

1. Freeze writes on the old VPS (`docker compose -f docker-compose.prod.yml stop web` or equivalent).
2. Final `backup_db`; copy; `restore_db --force` on the new VPS; spot-check row/media counts.
3. Point **new** zone A/AAAA (apex, `www`, `editor`) at the new IP.
4. Point **old** zone A/AAAA (apex, `www`, `editor`) at the **same** new IP (redirects live on the new nginx, not on the old VPS).
5. Issue/expand certs; `./scripts/generate-nginx-conf.sh` and `./deploy.sh`.
6. Verify:

```bash
curl -sI https://www.shiftedstuff.ru/ | head
# 301 Location: https://shiftedstuff.space/
curl -sI https://www.shiftedstuff.ru/some/path?x=1 | head
# 301 Location: https://shiftedstuff.space/some/path?x=1
curl -sI https://editor.shiftedstuff.ru/login | head
# 301 Location: https://editor.shiftedstuff.space/login
curl -sI https://shiftedstuff.space/ | head
# 200
```

7. Update GitHub `VPS_HOST` (and SSH key if the deploy user is new). Update Doppler `SITE_URL`, hosts, `REDIRECT_FROM_*` if you use it. See [maintainer.md](maintainer.md).
8. Add the new host in Yandex/Google Search Console; use change-of-address if offered.
9. Update public profile links (Telegram, Habr, GitHub).
10. After 24–48h of clean checks: **power off the old VPS**. Keep a provider snapshot a few days if available.

Mail can stay on the old mailbox/SMTP until you create addresses on the new domain. Then update Site settings + `EMAIL_HOST_PASSWORD`.

---

## Soft sunset (Scenario B)

The old **domain** stays as DNS + certs on the new VPS only. The old **VPS** is already gone.

- Keep `REDIRECT_FROM_*` until you drop the old zone.
- **01.12.2026** (this move): do not renew `shiftedstuff.ru`.
- **~07.01.2027**: remove redirect env keys, `./scripts/apply-domain.sh` without `--redirect-from`, reissue cert for `.space` only, delete `.ru` records.
- **21.01.2027**: domain lapses.

---

## Cron on the new VPS

```bash
# daily backup (adjust path/user)
0 3 * * * cd /opt/shiftedblog && ./scripts/backup/run-backup.sh
```

Optional weekly report: [security-runbook.md](../security-runbook.md).

---

## Related

- [production-deploy.md](production-deploy.md)
- [configuration.md](configuration.md)
- [maintainer.md](maintainer.md)
