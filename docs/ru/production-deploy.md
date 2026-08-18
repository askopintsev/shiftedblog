# Production-деплой

English: [../en/production-deploy.md](../en/production-deploy.md)

## Требования

- VPS с Docker и Docker Compose
- Домен (и при необходимости поддомен `editor.`) на IP сервера
- Открыты порты 80/443

## Мастер

На сервере:

```bash
sudo mkdir -p /opt/shiftedblog
sudo chown "$USER:$USER" /opt/shiftedblog
cd /opt/shiftedblog
git clone https://github.com/YOUR_USER/shiftedblog.git .
./scripts/setup.sh
# выберите 2) production — укажите домен и параметры
```

Будет создан `secrets.env`, сгенерирован `nginx/nginx.conf` из шаблона, при согласии — запущен стек.

### TLS (Let's Encrypt)

Compose монтирует `/var/www/html` и `/etc/letsencrypt`. После DNS:

```bash
sudo mkdir -p /var/www/html
sudo certbot certonly --webroot -w /var/www/html \
  -d example.com -d www.example.com -d editor.example.com
```

`SSL_CERT_NAME` в `secrets.env` должен совпадать с каталогом в `/etc/letsencrypt/live/`.

Перегенерация nginx:

```bash
./scripts/generate-nginx-conf.sh
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

## Обновление

```bash
./deploy.sh
```

`deploy.sh` опционально подтягивает секреты из Doppler (не обязательно), проверяет env, пересобирает с `VITE_*`, поднимает compose и перезагружает nginx.

```bash
ENV_FILE=secrets.env ./scripts/check-env.sh production
```

## Editor SPA

В production в SPA вшиваются `VITE_PUBLIC_SITE_BASE` / `VITE_API_BASE`. Перед `deploy.sh` корректно задайте `SITE_URL` в `secrets.env`.

## Опциональный CI

GitHub Actions + Doppler — путь мейнтейнера: [../en/maintainer.md](../en/maintainer.md). Для стороннего self-host достаточно `secrets.env` и `deploy.sh`.

## Перенос хоста или домена

Не кладите старые имена в `EXTRA_DOMAINS` (это дубль сайта). Для HTTPS 301 на `SITE_URL` используйте `REDIRECT_FROM_DOMAINS` / `REDIRECT_FROM_EDITOR_DOMAINS`. Смена домена без ротации секретов: `./scripts/apply-domain.sh`. Восстановление: `./scripts/backup/restore.sh`. Плейбук: [host-migration.md](host-migration.md).
