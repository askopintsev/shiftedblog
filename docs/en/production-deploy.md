# Production deploy

Русский: [../ru/production-deploy.md](../ru/production-deploy.md)

## Prerequisites

- VPS with Docker and Docker Compose
- Domain (and optional `editor.` subdomain) pointing to the server
- Ports 80/443 open

## Wizard

On the server:

```bash
sudo mkdir -p /opt/shiftedblog
sudo chown "$USER:$USER" /opt/shiftedblog
cd /opt/shiftedblog
git clone https://github.com/YOUR_USER/shiftedblog.git .
./scripts/setup.sh
# choose 2) production — enter domain, optional extras, editor host
```

This writes `secrets.env`, generates `nginx/nginx.conf` from the template, and can start the stack.

### TLS (Let's Encrypt)

Compose mounts `/var/www/html` and `/etc/letsencrypt`. After DNS propagates:

```bash
sudo mkdir -p /var/www/html
sudo certbot certonly --webroot -w /var/www/html \
  -d example.com -d www.example.com -d editor.example.com
```

Ensure `SSL_CERT_NAME` in `secrets.env` matches the certificate directory name under `/etc/letsencrypt/live/`.

Regenerate nginx anytime:

```bash
./scripts/generate-nginx-conf.sh
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

## Deploy / update

```bash
./deploy.sh
```

`deploy.sh`:

- Optionally refreshes `secrets.env` from Doppler if the CLI is configured (not required)
- Validates env, regenerates nginx, builds with `VITE_*` args, starts compose, reloads nginx

Manual validation:

```bash
ENV_FILE=secrets.env ./scripts/check-env.sh production
```

## Editor SPA

Production builds bake `VITE_PUBLIC_SITE_BASE` / `VITE_API_BASE` into the SPA. Set `SITE_URL` correctly in `secrets.env` before `deploy.sh`.

## Optional CI

GitHub Actions + Doppler is an optional maintainer path — see [maintainer.md](maintainer.md). Third-party installs only need `secrets.env` + `deploy.sh`.
