# Конфигурация

English: [../en/configuration.md](../en/configuration.md)

Конфигурация разделена на два слоя.

## Окружение / файл секретов

Локально — `.env`, в production — `secrets.env` (`docker-compose.prod.yml`).

Полный список: [`env.example`](../../env.example).

| Остаётся в env | Почему |
|----------------|--------|
| `SECRET_KEY`, `CREDENTIALS_ENCRYPTION_KEY` | Криптосекреты |
| БД / Redis | Инфраструктура |
| `ALLOWED_HOSTS`, `SITE_URL`, флаги CSRF/SSL | Безопасность деплоя |
| `ADMIN_URL` | Скрытый путь админки |
| `EMAIL_HOST_PASSWORD` | Пароль SMTP |
| `VITE_*`, `EDITOR_URL`, cookie domain | Сборка SPA |
| Прокси, токены бэкапов | Ops-секреты |

`SITE_URL` остаётся в env (проверка при старте Django + сборка editor-ui).

Смена хоста или домена: `./scripts/apply-domain.sh` и [host-migration.md](host-migration.md). Не кладите legacy 301-имена в `EXTRA_DOMAINS`.

## Site settings (админка)

После migrate: **Admin → Core → Site settings** — бренд, соцсети, несекретные email-поля, feature toggles.

Подробнее: [site-settings.md](site-settings.md).

## Bootstrap и runtime

Значения email/Twitter из env — **запасной вариант**, пока не заданы в Site settings. Toggles также можно включить через env; для повседневной работы удобнее админка.
