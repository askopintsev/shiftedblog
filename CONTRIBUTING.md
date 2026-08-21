# Contributing

Thanks for your interest in ShiftedBlog.

Русская версия: [docs/ru/contributing.md](docs/ru/contributing.md)

## Your goal: changes that pass CI and improve the project

ShiftedBlog is Django + DRF + Postgres + React (editor-ui). Before opening a PR, ensure your local environment works, code style checks pass, and the PR description explains **why** the change is needed.

> Do not commit secrets: `.env`, `secrets.env`, SSH keys, tokens.

---

## Development setup

The recommended path is **Docker** (same as end users):

```bash
git clone https://github.com/askopintsev/shiftedblog.git
cd shiftedblog
./scripts/check-prerequisites.sh local
./scripts/setup.sh          # choose 1) local
./scripts/start-local.sh    # editor: http://localhost:5173/login
```

Full guide: [docs/en/local-deploy.md](docs/en/local-deploy.md) · [docs/ru/local-deploy.md](docs/ru/local-deploy.md).

**Without Docker** (PostgreSQL, Redis, Node.js on the host) — see the advanced section in local-deploy docs.

---

## Checks before a pull request

CI runs Python lint, **Django tests with a coverage gate**, and editor-ui (typecheck, build, e2e) on every PR. Reproduce locally.

### Python (matches `.github/workflows/deploy.yml`)

Requires [uv](https://docs.astral.sh/uv/) and Python **3.14** (same as CI):

```bash
uv sync --frozen --extra dev --python 3.14

PATHS="api blog core editor sender shiftedblog team manage.py templates"

uv run ruff format --check $PATHS
uv run ruff check --ignore RUF001 $PATHS
uv run pyright $PATHS
uv run bandit -c pyproject.toml -r blog core editor sender shiftedblog team -ll -x '**/migrations/*'

# Django tests + coverage (needs Postgres + Redis; matches CI `test-coverage`)
./scripts/run-coverage.sh
```

Coverage is measured with [coverage.py](https://coverage.readthedocs.io/) (`fail_under` in `pyproject.toml`). The CI gate is **68%** of application code (migrations, settings, and management commands are excluded). Industry practice is about **80%** on business logic, not 100%; raise `fail_under` as the suite grows, and do not drop below the current floor.

Auto-format: `uv run ruff format $PATHS`

### Git hooks (optional)

```bash
./scripts/install-git-hooks.sh
```

Pre-commit runs ruff, pyright, and bandit on staged Python files. The coverage gate runs in CI (and locally via `./scripts/run-coverage.sh`) because it needs Postgres and Redis.

### Python dependencies

Change **`pyproject.toml` / `uv.lock`**, do not hand-edit `requirements.txt`. Export:

```bash
./scripts/export-requirements.sh
```

### Editor UI (`editor-ui/`)

When changing the frontend:

```bash
cd editor-ui
npm install
npm run typecheck
npm run build
npx playwright install --with-deps chromium   # first time
npm run test:e2e
```

---

## Style and architecture

| Area | Rule |
|------|------|
| Python | [Ruff](https://docs.astral.io/ruff/) + [Pyright](https://microsoft.github.io/pyright/) — settings in `pyproject.toml` |
| Layers | Serializers → views → **services** for business logic; keep views thin |
| ORM | `select_related` / `prefetch_related`; avoid N+1 queries |
| Frontend | TypeScript, React; API via OpenAPI in `editor-ui` |
| Secrets | Env / secret manager only, never in the repo |

Configuration reference: [docs/en/configuration.md](docs/en/configuration.md).

---

## Pull requests

1. **Fork** and create a feature branch (from `master`)
2. Keep changes **focused**; add tests when behavior changes (Django `tests.py`, Playwright for UI)
3. Run the checks above
4. Describe the **why** in the PR (not only what changed)
5. Docs: when changing deploy/scripts, update `docs/en/` and `docs/ru/` in pairs

Upstream deploy after merge to `master`: [docs/en/maintainer.md](docs/en/maintainer.md).

---

## Security

Report vulnerabilities **privately** — see [SECURITY.md](SECURITY.md).

---

## Related

- [Getting started](docs/en/getting-started.md)
- [Local deploy](docs/en/local-deploy.md)
- [Configuration](docs/en/configuration.md)
- [Maintainer notes](docs/en/maintainer.md)
