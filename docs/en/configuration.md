# Configuration

Русский: [../ru/configuration.md](../ru/configuration.md)

ShiftedBlog splits configuration into two layers.

## Environment / secrets file

Use `.env` for local Docker and `secrets.env` for production (`docker-compose.prod.yml`).

See [`env.example`](../../env.example) for the full list.

| Keep in env | Why |
|-------------|-----|
| `SECRET_KEY`, `CREDENTIALS_ENCRYPTION_KEY` | Crypto secrets |
| Database / Redis URLs and passwords | Infrastructure |
| `ALLOWED_HOSTS`, `SITE_URL`, CSRF/SSL cookie flags | Deploy-time security |
| `ADMIN_URL` | Obscure admin path |
| `EMAIL_HOST_PASSWORD` | SMTP secret |
| `VITE_*`, `EDITOR_URL`, cookie domains | Build / SPA deploy |
| Proxies, backup tokens | Ops secrets |

`SITE_URL` stays in env (Django boot checks + editor-ui production build).

Changing host or domain later: `./scripts/apply-domain.sh` and [host-migration.md](host-migration.md). Do not put legacy 301 hosts in `EXTRA_DOMAINS`.

## Site settings (admin)

After migrate, open **Admin → Core → Site settings**:

- Brand: site name, tagline, footer text
- Social URLs and contact email
- Non-secret email fields (host, from, admin address)
- Feature toggles (Telegram rich messages, text-quality checker)

Details: [site-settings.md](site-settings.md).

## Bootstrap vs runtime

Env values for email from-address / admin email / Twitter handle act as **fallbacks** until you set them in Site settings. Feature toggles can also be forced on via env for emergency/bootstrap; prefer admin for day-to-day changes.
