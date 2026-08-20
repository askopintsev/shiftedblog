# Конфигурация

English: [Configuration](../en/configuration.md)

## Ваша цель: понять, где что менять

ShiftedBlog хранит настройки в **двух слоях**:

1. **Файл окружения** (`.env` локально, `secrets.env` на сервере) — секреты, домен, безопасность, сборка редактора.
2. **Site settings** в панели администратора — бренд, соцсети, несекретные email-поля, переключатели функций.

После первой настройки большинство повседневных изменений — в **Site settings** или в **редакторе → Настройки → Сайт**. Файл env трогайте при смене домена, деплое или секретов.

> Полный список переменных — в [`env.example`](../../env.example). Создание файла: `./scripts/setup.sh` (**`1) local`** или **`2) online`**).

---

## Файлы окружения

| Режим | Файл | Compose |
|-------|------|---------|
| Локально | `.env` | `docker-compose.yml` |
| Онлайн (на сервере) | `secrets.env` | `docker-compose.prod.yml` |

Проверка перед деплоем:

```bash
./scripts/check-env.sh local          # локально
ENV_FILE=secrets.env ./scripts/check-env.sh online   # на сервере
```

`deploy.sh` на production сам вызывает `check-env.sh online`.

**Docker Compose:** в паролях экранируйте `$` как `$$`, иначе Compose обрежет значение (например `$E` в пароле SMTP).

---

## Что остаётся в env (и почему)

| Группа | Переменные | Зачем в файле |
|--------|------------|---------------|
| Криpto | `SECRET_KEY`, `CREDENTIALS_ENCRYPTION_KEY` | Секреты Django и шифрование credentials |
| База / Redis | `DB_*`, `POSTGRES_*`, `REDIS_URL` | Инфраструктура Docker |
| Публичный URL | `SITE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | Безопасность и canonical URL |
| SSL / cookies | `SESSION_COOKIE_*`, `CSRF_COOKIE_*`, `SECURE_*` | HTTPS и сессии |
| Админка | `ADMIN_URL` | Нестандартный путь `/mellon/` → свой slug |
| Почта (секрет) | `EMAIL_HOST_PASSWORD` | Пароль SMTP |
| Редактор / SPA | `EDITOR_URL`, `CORS_ALLOWED_ORIGINS`, `VITE_*`, cookie domain | Поддомен редактора и сборка UI |
| Nginx / домен | `DOMAIN`, `EDITOR_DOMAIN`, `SSL_CERT_NAME`, `SERVER_IP` | `./scripts/generate-nginx-conf.sh` |
| Ops | `BACKUP_DIR`, `YADISK_TOKEN`, прокси | Бэкапы и интеграции |

`SITE_URL` **обязателен** в production: Django проверяет его при старте, `./deploy.sh` подставляет его в сборку интерфейса редактора (`VITE_PUBLIC_SITE_BASE`).

---

## Домен и nginx

| Переменная | Назначение |
|------------|------------|
| `DOMAIN` | Основной домен без `www` |
| `EDITOR_DOMAIN` | Поддомен редактора (например `editor.example.com`) |
| `SITE_URL` | Канонический публичный URL (`https://example.com`) |
| `SSL_CERT_NAME` | Имя каталога в `/etc/letsencrypt/live/` |
| `SERVER_IP` | Публичный IP (nginx `server_name`, `ALLOWED_HOSTS`) |
| `EXTRA_DOMAINS` | **Тот же** сайт на доп. хостах (дубли) |
| `REDIRECT_FROM_DOMAINS` | Legacy apex/www → **301** на `SITE_URL` |
| `REDIRECT_FROM_EDITOR_DOMAINS` | Legacy editor host → **301** на `EDITOR_DOMAIN` |

**Не кладите** legacy-имена для 301 в `EXTRA_DOMAINS` — только в `REDIRECT_FROM_*`.

Смена домена **без** ротации `SECRET_KEY`, `ADMIN_URL` и паролей БД:

```bash
./scripts/apply-domain.sh --domain new.example.com \
  --site-url https://new.example.com \
  --editor-domain editor.new.example.com \
  --redirect-from old.example.com,www.old.example.com \
  --redirect-from-editor editor.old.example.com \
  --server-ip IP_ВАШЕГО_VPS
```

Затем TLS (если нужно) и **`./deploy.sh`** — пересборка редактора с новым `SITE_URL`.

Полный перенос VPS или домена: [host-migration.md](host-migration.md).

---

## Site settings (админка)

После `migrate`: **Admin → Core → Site settings** (или **редактор → Настройки → Сайт**):

- Бренд: название, tagline, footer
- Соцсети и контактный email
- Несекретные поля SMTP (хост, порт, from, admin)
- Переключатели: rich Telegram, проверка текста

Подробнее: [site-settings.md](site-settings.md).

Пароль SMTP — только **`EMAIL_HOST_PASSWORD`** в env.

---

## Bootstrap и runtime

Значения email / Twitter из env — **запасной вариант**, пока не заданы в Site settings. Переключатели можно включить через env для bootstrap; для повседневной работы удобнее админка.

При смене только Site settings **перезапуск не нужен** — изменения сразу на сайте. При смене `SITE_URL` или доменных ключей — **`./deploy.sh`** (online) или пересборка локального стека.

---

## См. также

- [Быстрый старт](getting-started.md)
- [Локальный запуск](local-deploy.md)
- [Онлайн запуск (на сервере)](production-deploy.md)
- [Перенос хоста и домена](host-migration.md)
- [Site settings](site-settings.md)
- [Security runbook](../security-runbook.md)
