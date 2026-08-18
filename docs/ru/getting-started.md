# Быстрый старт

ShiftedBlog — self-hosted блог на Django. Рекомендуемый путь для новых пользователей: Docker и мастер настройки.

English: [../en/getting-started.md](../en/getting-started.md)

## Выберите сценарий

1. **Local** — запуск на своей машине ([local-deploy.md](local-deploy.md))
2. **Production** — деплой на VPS с HTTPS ([production-deploy.md](production-deploy.md))
3. **Перенос** — смена VPS и/или домена ([host-migration.md](host-migration.md))

```bash
./scripts/setup.sh
```

Мастер создаёт `.env` (local) или `secrets.env` (production), генерирует секреты, проверяет конфигурацию и может сразу поднять Docker.

## После первого запуска

1. Создайте суперпользователя (запрос мастера или `docker compose exec web python manage.py createsuperuser`)
2. Откройте админку → **Core → Site settings** — название сайта, соцсети, контактный email
3. Опционально: Telegram-креды в **Core → Credentials** (нужен `CREDENTIALS_ENCRYPTION_KEY`)

## Дальше

- [Конфигурация: env и Site settings](configuration.md)
- [Site settings](site-settings.md)
- [Перенос хоста и домена](host-migration.md)
- [Security runbook](../security-runbook.md)
- [Заметки для мейнтейнера / CI](../en/maintainer.md)
