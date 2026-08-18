# Maintainer notes

Optional path for the upstream project operators (Doppler + GitHub Actions + existing VPS). Third-party self-hosters should follow [production-deploy.md](production-deploy.md) with a plain `secrets.env`.

## Doppler

CI downloads production secrets:

```bash
doppler secrets download --no-file --format=env > secrets.env
```

`deploy.sh` will use Doppler when the CLI is logged in / `DOPPLER_TOKEN` is set. Set `SKIP_DOPPLER=1` to force file-only deploys.

## GitHub Actions

Workflow: `.github/workflows/deploy.yml`

Required repository secrets: `VPS_HOST`, `VPS_USERNAME`, `VPS_SSH_KEY`, `VPS_PORT`, `DOPPLER_TOKEN`.

SSH helper scripts live under `scripts/ssh/` (`GITHUB_REPO` can point at a fork).

After a VPS move, update `VPS_HOST` (and `VPS_SSH_KEY` if the deploy user is new) before the next push to `master`. After a hostname change, refresh Doppler `SITE_URL`, `ALLOWED_HOSTS`, cookie domains, and `REDIRECT_FROM_*`. Playbook: [host-migration.md](host-migration.md).

## Security runbook

Operational hardening (SMTP providers, axes, editor subdomain): [../security-runbook.md](../security-runbook.md).
