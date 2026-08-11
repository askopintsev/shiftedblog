# Getting started

ShiftedBlog is a self-hosted Django blog. The recommended path for new users is Docker + the setup wizard.

Русский: [../ru/getting-started.md](../ru/getting-started.md)

## Choose a path

1. **Local** — try the app on your machine ([local-deploy.md](local-deploy.md))
2. **Production** — deploy on a VPS with HTTPS ([production-deploy.md](production-deploy.md))

```bash
./scripts/setup.sh
```

The wizard creates `.env` (local) or `secrets.env` (production), generates secrets, validates configuration, and can start Docker for you.

## After first boot

1. Create a superuser (wizard prompt, or `docker compose exec web python manage.py createsuperuser`)
2. Open Django admin → **Core → Site settings** — set site name, social links, contact email
3. Optional: configure Telegram credentials under **Core → Credentials** (needs `CREDENTIALS_ENCRYPTION_KEY`)

## Learn more

- [Configuration: env vs Site settings](configuration.md)
- [Site settings](site-settings.md)
- [Security runbook](../security-runbook.md) (operations)
- [Maintainer / CI notes](maintainer.md)
