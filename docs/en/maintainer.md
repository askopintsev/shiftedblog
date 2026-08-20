# Maintainer notes

Русский: [Maintainer notes (RU)](../ru/maintainer.md)

## Your goal: push to `master` → production updates automatically

After a successful CI run, the live site and editor should reflect the latest commit:

**https://editor.example.com/login** → sign in → **https://editor.example.com/posts**

> This path is for **upstream operators** (Doppler + GitHub Actions + a git checkout on the VPS). Third-party self-hosters should use [Online deploy (on server)](production-deploy.md) with a plain `secrets.env` and `./deploy.sh` — no Doppler or Actions required.

**One-time setup order:** production VPS ready (1) → git access on server (2) → CI deploy SSH key (3) → Doppler (4) → GitHub secrets (5) → test push (6).

## Before you start

- A **working production install** on the VPS (`/opt/shiftedblog`, `secrets.env`, TLS) — see [production-deploy.md](production-deploy.md)
- **Git checkout** on the server (CI runs `git fetch` / `git reset --hard origin/master`; tarball-only installs are not enough for CI)
- **Admin** access to the GitHub repo (Actions secrets, deploy keys)
- **Doppler** project with production config (or plan to deploy with file-only `secrets.env` and `SKIP_DOPPLER=1`)

---

## Step 1. Prepare the VPS for CI

The server layout should match the [online deploy](production-deploy.md) guide: Docker, ports **80/443** free for compose nginx, app at `/opt/shiftedblog`.

Deploy user (often `deploy`) must:

- Own `/opt/shiftedblog` and run Docker (`docker compose`)
- Have a **git** remote that can pull from GitHub (deploy key below)
- Accept SSH from GitHub Actions (VPS deploy key below)

Check on the server:

```bash
cd /opt/shiftedblog
docker compose version
git remote -v
test -f secrets.env && grep -E '^SITE_URL=' secrets.env
```

---

## Step 2. Git deploy key (VPS → GitHub)

CI syncs code with `git fetch origin master` on the VPS. Use a **read-only deploy key**, not your personal SSH key.

**On your laptop** (repo root):

```bash
./scripts/ssh/generate-git-deploy-key.sh
# fork: GITHUB_REPO=YOUR_USER/shiftedblog ./scripts/ssh/generate-git-deploy-key.sh
```

1. GitHub → repo **Settings → Deploy keys → Add deploy key** — paste the **public** key (read-only).
2. Copy the **private** key to the VPS (e.g. `scp scripts/ssh/keys/git-deploy/id_ed25519 deploy@VPS:/home/deploy/.ssh/shiftedblog_git_deploy`).
3. On the VPS, as the deploy user:

```bash
chmod 600 ~/.ssh/shiftedblog_git_deploy
./scripts/ssh/install-server-git-access.sh
cd /opt/shiftedblog && git fetch origin master
```

Remote should look like `git@github.com-shiftedblog:USER/shiftedblog.git`.

---

## Step 3. VPS deploy key (GitHub Actions → VPS)

Separate key for `appleboy/ssh-action` / `appleboy/scp-action`.

**On your laptop:**

```bash
./scripts/ssh/generate-vps-deploy-key.sh
```

1. On the VPS: `./scripts/ssh/install-vps-authorized-key.sh /path/to/id_ed25519.pub` (or paste the public line).
2. GitHub → repo **Settings → Secrets and variables → Actions** — store the **entire private key** as `VPS_SSH_KEY`.

Test from laptop:

```bash
ssh -i scripts/ssh/keys/vps-deploy/id_ed25519 deploy@VPS_HOST
```

---

## Step 4. Doppler

CI downloads production secrets before deploy:

```bash
doppler secrets download \
  --project shifted_blog \
  --config prd \
  --no-file \
  --format=env > secrets.env
```

On the VPS, `deploy.sh` and `scripts/ci/vps-deploy-remote.sh` can also use Doppler when the CLI is logged in or `DOPPLER_TOKEN` is set.

| Variable | Purpose |
|----------|---------|
| `DOPPLER_TOKEN` | GitHub Actions secret; CI uses it to build `secrets.env` |
| `SKIP_DOPPLER=1` | Force file-only deploy (CI sets this on the VPS after uploading `secrets.env`) |

Local / manual deploy with Doppler:

```bash
cd /opt/shiftedblog
./deploy.sh
```

File-only (no Doppler on server):

```bash
SKIP_DOPPLER=1 ./deploy.sh
```

Keep Doppler in sync with domain changes (`SITE_URL`, `ALLOWED_HOSTS`, cookie domains, `REDIRECT_FROM_*`) — or update `secrets.env` and run `./scripts/apply-domain.sh` before the next deploy. Playbook: [host-migration.md](host-migration.md).

---

## Step 5. GitHub Actions secrets

Workflow: [`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml)

| Secret | Example / notes |
|--------|-----------------|
| `VPS_HOST` | Public IP or hostname of the VPS |
| `VPS_USERNAME` | SSH user (`deploy`) |
| `VPS_SSH_KEY` | Full private key from step 3 |
| `VPS_PORT` | Usually `22` |
| `DOPPLER_TOKEN` | Service token for `shifted_blog` / `prd` |

Helper scripts: `scripts/ssh/` (`GITHUB_REPO` can point at a fork).

---

## Step 6. What happens on push to `master`

```text
push master  →  lint + editor-ui tests  →  deploy job (if green)
                    │
                    ├─ Doppler → secrets.env (in CI runner)
                    ├─ scp secrets.env → VPS:/opt/shiftedblog/
                    └─ SSH → scripts/ci/vps-deploy-remote.sh
                              ├─ git fetch / reset origin/master
                              ├─ validate secrets.env (SITE_URL)
                              ├─ generate nginx.conf
                              ├─ docker compose build + up (prod)
                              └─ sync editor dist + reload nginx
```

- **Pull requests** run lint and editor tests only (no deploy).
- **Deploy** runs on `push` to `master` or **workflow_dispatch** (manual run in Actions tab).

Remote script: [`scripts/ci/vps-deploy-remote.sh`](../../scripts/ci/vps-deploy-remote.sh).

First CI deploy may take **several minutes** (image build). Later runs are similar — the script prunes builders/images each time.

---

## Step 7. Verify after setup

1. Push a trivial commit to `master` (or **Run workflow** → `workflow_dispatch`).
2. GitHub Actions → **Deploy to VPS** job → green.
3. On the VPS:

```bash
cd /opt/shiftedblog
git log -1 --oneline
docker compose -f docker-compose.prod.yml ps
curl -skI https://editor.example.com/login | head -1
```

4. Open **https://editor.example.com/login** in a browser.

---

## Manual deploy (without waiting for CI)

On the VPS:

```bash
cd /opt/shiftedblog
git pull origin master   # or fetch/reset like CI
./deploy.sh              # or SKIP_DOPPLER=1 ./deploy.sh
```

Same checks as [online deploy](production-deploy.md) step 6: `ENV_FILE=secrets.env ./scripts/check-env.sh online` (optional — `deploy.sh` runs it).

---

## After a VPS or domain change

| Change | Update |
|--------|--------|
| New VPS IP / host | GitHub `VPS_HOST`; `VPS_SSH_KEY` if deploy user/key changed |
| New domain | Doppler (or `secrets.env`) — `SITE_URL`, hosts, cookies, `REDIRECT_FROM_*`; `./scripts/apply-domain.sh`; TLS; `./deploy.sh` |
| Full migration | [host-migration.md](host-migration.md) |

Re-run steps 2–3 if the deploy user or server was recreated.

---

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| Deploy job skipped | Not `master`, or lint/editor-ui failed |
| `Permission denied (publickey)` | `VPS_SSH_KEY` mismatch or key not in `authorized_keys` |
| `git fetch` fails on VPS | Git deploy key missing or wrong remote |
| `Ports 80/443 are already in use` | Host nginx/apache — stop it (see [production-deploy.md](production-deploy.md) step 3) |
| Editor shows wrong site URL | `SITE_URL` in secrets; run `./deploy.sh` to rebuild editor UI |
| Empty `secrets.env` in CI | `DOPPLER_TOKEN` or Doppler project/config name |

Logs on the VPS:

```bash
cd /opt/shiftedblog
docker compose -f docker-compose.prod.yml logs --tail=50 web nginx
```

---

## Security runbook

Operational hardening (SMTP, axes lockout, editor subdomain): [../security-runbook.md](../security-runbook.md).

---

## Related

- [Online deploy (on server)](production-deploy.md) — first install (self-host and prerequisite for CI)
- [Host and domain migration](host-migration.md) — move VPS or change domain
- [Configuration](configuration.md) — env reference
