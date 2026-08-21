# Участие в разработке

English: [CONTRIBUTING.md](../../CONTRIBUTING.md)

## Ваша цель: изменения, которые проходят CI и улучшают проект

ShiftedBlog — Django + DRF + Postgres + React (editor-ui). Перед PR убедитесь, что локальная среда работает, стиль кода соблюдён, а описание PR объясняет **зачем** нужны изменения.

> Не коммитьте секреты: `.env`, `secrets.env`, ключи SSH, токены.

---

## Локальная среда

Рекомендуемый путь — **Docker** (как у пользователей):

```bash
git clone https://github.com/askopintsev/shiftedblog.git
cd shiftedblog
./scripts/check-prerequisites.sh local
./scripts/setup.sh          # выберите 1) local
./scripts/start-local.sh    # редактор: http://localhost:5173/login
```

Полная инструкция: [local-deploy.md](local-deploy.md).

**Без Docker** (PostgreSQL, Redis, Node.js на хосте) — см. [local-deploy.md](local-deploy.md) (раздел для опытных) и [CONTRIBUTING.md](../../CONTRIBUTING.md).

---

## Проверки перед pull request

CI на каждый PR запускает lint Python, **Django-тесты с порогом coverage** и editor-ui (typecheck, build, e2e). Воспроизведите локально.

### Python (как в `.github/workflows/deploy.yml`)

Нужны [uv](https://docs.astral.sh/uv/) и Python **3.14** (как в CI):

```bash
uv sync --frozen --extra dev --python 3.14

PATHS="api blog core editor sender shiftedblog team manage.py templates"

uv run ruff format --check $PATHS
uv run ruff check --ignore RUF001 $PATHS
uv run pyright $PATHS
uv run bandit -c pyproject.toml -r blog core editor sender shiftedblog team -ll -x '**/migrations/*'

# Django-тесты + coverage (нужны Postgres и Redis; как CI `test-coverage`)
./scripts/run-coverage.sh
```

Coverage считается через [coverage.py](https://coverage.readthedocs.io/) (`fail_under` в `pyproject.toml`). Порог CI — **80%** прикладного кода (миграции, settings, management-команды и HTML Django admin не входят). Это обычный пол для бизнес-логики; не опускайте его и покрывайте publish/API/редактор/публичный сайт, а не admin без содержательных проверок.

Автоисправление форматирования: `uv run ruff format $PATHS`

### Git hooks (необязательно)

```bash
./scripts/install-git-hooks.sh
```

Pre-commit запускает ruff, pyright и bandit на staged Python-файлах. Порог coverage проверяется в CI (и локально через `./scripts/run-coverage.sh`), потому что нужны Postgres и Redis.

### Зависимости Python

Меняйте **`pyproject.toml` / `uv.lock`**, не редактируйте `requirements.txt` вручную. Экспорт:

```bash
./scripts/export-requirements.sh
```

### Editor UI (`editor-ui/`)

При изменениях frontend:

```bash
cd editor-ui
npm install
npm run typecheck
npm run build
npx playwright install --with-deps chromium   # первый раз
npm run test:e2e
```

---

## Стиль и архитектура

| Область | Правило |
|---------|---------|
| Python | [Ruff](https://docs.astral.io/ruff/) + [Pyright](https://microsoft.github.io/pyright/) — настройки в `pyproject.toml` |
| Слои | Serializers → views → **services** для бизнес-логики; views тонкие |
| ORM | `select_related` / `prefetch_related`; избегайте N+1 |
| Frontend | TypeScript, React; API через OpenAPI в `editor-ui` |
| Секреты | Только env / secret manager, не в репозитории |

Подробнее о конфигурации: [configuration.md](configuration.md).

---

## Pull request

1. **Форк** и ветка под задачу (от `master`)
2. **Точечные** изменения; при смене поведения — тесты (Django `tests.py`, Playwright для UI)
3. Прогоните проверки выше
4. В описании PR — **зачем** (не только «что изменилось»)
5. Документация: при смене деплоя/скриптов обновите `docs/en/` и `docs/ru/` парами

Деплой upstream после merge в `master`: [maintainer.md](maintainer.md).

---

## Безопасность

Уязвимости сообщайте **приватно** — см. [SECURITY.md](../../SECURITY.md).

---

## См. также

- [Быстрый старт](getting-started.md)
- [Локальный запуск](local-deploy.md)
- [Конфигурация](configuration.md)
- [Заметки для мейнтейнера](maintainer.md)
