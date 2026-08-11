# Contributing

Thanks for your interest in ShiftedBlog.

Русская версия: [docs/ru/contributing.md](docs/ru/contributing.md)

## Development setup

The recommended path is Docker:

```bash
./scripts/setup.sh
# choose "local"
```

Or see [docs/en/local-deploy.md](docs/en/local-deploy.md).

## Code style

- Python: [Ruff](https://docs.astral.io/ruff/) and [Pyright](https://microsoft.github.io/pyright/) (see `pyproject.toml`)
- Prefer small services for business logic; keep views thin
- Optimize querysets (`select_related` / `prefetch_related`) to avoid N+1 queries
- Do not commit secrets (`.env`, `secrets.env`, private keys)

Install git hooks (optional):

```bash
./scripts/install-git-hooks.sh
```

## Pull requests

1. Fork and create a feature branch
2. Keep changes focused; include tests when behavior changes
3. Ensure `ruff` / `pyright` and relevant tests pass
4. Describe the *why* in the PR description

## Security

Report vulnerabilities privately — see [SECURITY.md](SECURITY.md).
