# Заметки для мейнтейнера

English: [Maintainer notes](../en/maintainer.md)

## Ваша цель: push в `master` → production обновляется автоматически

После успешного CI на сервере должна быть актуальная версия сайта и редактора:

**https://editor.example.com/login** → вход → **https://editor.example.com/posts**

> Этот путь для **операторов upstream** (Doppler + GitHub Actions + git checkout на VPS). Сторонним self-host достаточно [Онлайн запуск (на сервере)](production-deploy.md) с `secrets.env` и `./deploy.sh` — Doppler и Actions не нужны.

**Порядок однократной настройки:** production VPS готов (1) → git на сервере (2) → SSH-ключ CI (3) → Doppler (4) → секреты GitHub (5) → тестовый push (6).

## Что нужно заранее

- **Рабочий production** на VPS (`/opt/shiftedblog`, `secrets.env`, TLS) — см. [production-deploy.md](production-deploy.md)
- **Git checkout** на сервере (CI делает `git fetch` / `git reset --hard origin/master`; установка только из tarball для CI **не подходит**)
- **Права админа** в репозитории GitHub (секреты Actions, deploy keys)
- Проект **Doppler** с production-конфигом (или деплой только из файла `secrets.env` с `SKIP_DOPPLER=1`)

---

## Шаг 1. Подготовьте VPS для CI

Сервер как в [онлайн запуске](production-deploy.md): Docker, порты **80/443** для compose-nginx, приложение в `/opt/shiftedblog`.

Пользователь деплоя (часто `deploy`) должен:

- Владеть `/opt/shiftedblog` и запускать Docker (`docker compose`)
- Иметь **git** remote с доступом к GitHub (deploy key ниже)
- Принимать SSH от GitHub Actions (VPS deploy key ниже)

Проверка на сервере:

```bash
cd /opt/shiftedblog
docker compose version
git remote -v
test -f secrets.env && grep -E '^SITE_URL=' secrets.env
```

---

## Шаг 2. Git deploy key (VPS → GitHub)

CI подтягивает код через `git fetch origin master` на VPS. Используйте **read-only deploy key**, не личный SSH-ключ.

**На ноутбуке** (корень репозитория):

```bash
./scripts/ssh/generate-git-deploy-key.sh
# форк: GITHUB_REPO=YOUR_USER/shiftedblog ./scripts/ssh/generate-git-deploy-key.sh
```

1. GitHub → репозиторий **Settings → Deploy keys → Add deploy key** — вставьте **публичный** ключ (read-only).
2. Скопируйте **приватный** ключ на VPS (например `scp scripts/ssh/keys/git-deploy/id_ed25519 deploy@VPS:/home/deploy/.ssh/shiftedblog_git_deploy`).
3. На VPS под пользователем deploy:

```bash
chmod 600 ~/.ssh/shiftedblog_git_deploy
./scripts/ssh/install-server-git-access.sh
cd /opt/shiftedblog && git fetch origin master
```

Remote должен быть вида `git@github.com-shiftedblog:USER/shiftedblog.git`.

---

## Шаг 3. VPS deploy key (GitHub Actions → VPS)

Отдельный ключ для `appleboy/ssh-action` / `appleboy/scp-action`.

**На ноутбуке:**

```bash
./scripts/ssh/generate-vps-deploy-key.sh
```

1. На VPS: `./scripts/ssh/install-vps-authorized-key.sh /path/to/id_ed25519.pub` (или вставьте публичную строку).
2. GitHub → **Settings → Secrets and variables → Actions** — целиком **приватный** ключ в `VPS_SSH_KEY`.

Проверка с ноутбука:

```bash
ssh -i scripts/ssh/keys/vps-deploy/id_ed25519 deploy@VPS_HOST
```

---

## Шаг 4. Doppler

CI скачивает production-секреты перед деплоем:

```bash
doppler secrets download \
  --project shifted_blog \
  --config prd \
  --no-file \
  --format=env > secrets.env
```

На VPS `deploy.sh` и `scripts/ci/vps-deploy-remote.sh` тоже могут использовать Doppler, если CLI залогинен или задан `DOPPLER_TOKEN`.

| Переменная | Назначение |
|------------|------------|
| `DOPPLER_TOKEN` | Секрет GitHub Actions; CI собирает `secrets.env` |
| `SKIP_DOPPLER=1` | Только файл (CI выставляет на VPS после upload `secrets.env`) |

Локальный / ручной деплой с Doppler:

```bash
cd /opt/shiftedblog
./deploy.sh
```

Только файл (без Doppler на сервере):

```bash
SKIP_DOPPLER=1 ./deploy.sh
```

При смене домена синхронизируйте Doppler (`SITE_URL`, `ALLOWED_HOSTS`, cookie domains, `REDIRECT_FROM_*`) — или обновите `secrets.env` и `./scripts/apply-domain.sh` перед следующим деплоем. Плейбук: [host-migration.md](host-migration.md).

---

## Шаг 5. Секреты GitHub Actions

Workflow: [`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml)

| Секрет | Пример / примечание |
|--------|---------------------|
| `VPS_HOST` | Публичный IP или hostname VPS |
| `VPS_USERNAME` | SSH-пользователь (`deploy`) |
| `VPS_SSH_KEY` | Полный приватный ключ из шага 3 |
| `VPS_PORT` | Обычно `22` |
| `DOPPLER_TOKEN` | Service token для `shifted_blog` / `prd` |

Скрипты: `scripts/ssh/` (`GITHUB_REPO` можно указать на форк).

---

## Шаг 6. Что происходит при push в `master`

```text
push master  →  lint + tests/coverage + editor-ui  →  deploy job (если зелёные)
                    │
                    ├─ Doppler → secrets.env (в CI runner)
                    ├─ scp secrets.env → VPS:/opt/shiftedblog/
                    └─ SSH → scripts/ci/vps-deploy-remote.sh
                              ├─ git fetch / reset origin/master
                              ├─ проверка secrets.env (SITE_URL)
                              ├─ generate nginx.conf
                              ├─ docker compose build + up (prod)
                              └─ sync editor dist + reload nginx
```

- **Pull request** — lint, Django-тесты (порог coverage) и тесты редактора (без деплоя).
- **Deploy** — при `push` в `master` или **workflow_dispatch** (ручной запуск во вкладке Actions).

Скрипт на сервере: [`scripts/ci/vps-deploy-remote.sh`](../../scripts/ci/vps-deploy-remote.sh).

**Один раз на VPS** (чтобы деплой не падал на порту 80):

```bash
cd /opt/shiftedblog
git pull origin master   # или дождитесь следующего CI sync
./scripts/vps-prepare-for-ci.sh
```

Отключает системный nginx/apache, удаляет устаревший `.env`, освобождает порты 80/443. Только Docker Compose в `/opt/shiftedblog` должен слушать эти порты.

Первый CI-деплой на небольшом VPS может занять **15–30+ минут** (холодная сборка Docker: `npm ci`, pip, editor-ui). SSH-шаг deploy использует **command_timeout 45m**. Повторные запуски быстрее при тёплом кэше слоёв Docker; неиспользуемые образы удаляются при каждом deploy.

---

## Шаг 7. Проверка после настройки

1. Push тривиального коммита в `master` (или **Run workflow** → `workflow_dispatch`).
2. GitHub Actions → job **Deploy to VPS** → зелёный.
3. На VPS:

```bash
cd /opt/shiftedblog
git log -1 --oneline
docker compose -f docker-compose.prod.yml ps
curl -skI https://editor.example.com/login | head -1
```

4. Откройте **https://editor.example.com/login** в браузере.

---

## Ручной деплой (без ожидания CI)

На VPS:

```bash
cd /opt/shiftedblog
git pull origin master   # или fetch/reset как в CI
./deploy.sh              # или SKIP_DOPPLER=1 ./deploy.sh
```

Как в [онлайн запуске](production-deploy.md), шаг 6: `ENV_FILE=secrets.env ./scripts/check-env.sh online` (необязательно — `deploy.sh` сам проверяет).

---

## После смены VPS или домена

| Изменение | Обновить |
|-----------|----------|
| Новый IP / хост VPS | GitHub `VPS_HOST`; `VPS_SSH_KEY`, если сменился пользователь/ключ |
| Новый домен | Doppler (или `secrets.env`) — `SITE_URL`, hosts, cookies, `REDIRECT_FROM_*`; `./scripts/apply-domain.sh`; TLS; `./deploy.sh` |
| Полный перенос | [host-migration.md](host-migration.md) |

Повторите шаги 2–3, если пересоздали сервер или пользователя deploy.

---

## Если что-то пошло не так

| Симптом | Вероятная причина |
|---------|-------------------|
| Deploy job пропущен | Не `master`, или упали lint/test-coverage/editor-ui |
| `Permission denied (publickey)` | Неверный `VPS_SSH_KEY` или ключ не в `authorized_keys` |
| `git fetch` падает на VPS | Нет git deploy key или неверный remote |
| `Ports 80/443 are already in use` | Хостовый nginx/apache — остановите (см. [production-deploy.md](production-deploy.md), шаг 3) |
| Deploy падает после «Stopping existing stack» / предупреждения compose про `$E` | Устаревший `.env` в `/opt/shiftedblog` — удалите; CI использует только `secrets.env` |
| `failed to bind host port 0.0.0.0:80` / порт 80 занят при `compose up` | Старый контейнер nginx или системный веб-сервер — `./scripts/vps-prepare-for-ci.sh` на VPS; CI использует rolling deploy (nginx не снимается, если уже работает) |
| Редактор с неверным URL сайта | `SITE_URL` в secrets; нужен `./deploy.sh` для пересборки UI |
| Пустой `secrets.env` в CI | `DOPPLER_TOKEN` или имя project/config в Doppler |

Логи на VPS:

```bash
cd /opt/shiftedblog
docker compose -f docker-compose.prod.yml logs --tail=50 web nginx
```

---

## Security runbook

Эксплуатация и hardening (SMTP, axes, поддомен редактора): [../security-runbook.md](../security-runbook.md).

---

## См. также

- [Онлайн запуск (на сервере)](production-deploy.md) — первичная установка (нужна и для CI)
- [Перенос хоста и домена](host-migration.md) — смена VPS или домена
- [configuration.md](configuration.md) — справочник переменных
