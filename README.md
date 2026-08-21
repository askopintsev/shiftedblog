# ShiftedBlog

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/askopintsev/shiftedblog/actions/workflows/deploy.yml/badge.svg)](https://github.com/askopintsev/shiftedblog/actions/workflows/deploy.yml)
[![Coverage](https://img.shields.io/badge/coverage-%E2%89%A568%25-brightgreen)](https://github.com/askopintsev/shiftedblog/actions/workflows/deploy.yml)

**Multichannel blog management** — one editor, one dispatch flow, several channels.

[English](#english) · [Русский](#русский) · [Docs](docs/en/getting-started.md) · [Документация](docs/ru/getting-started.md)

## English

Write once, publish to your site and other channels from a single workspace.

- **United editor** — draft and prepare posts in one place
- **Dispatch** — send a release to selected channels (site, Telegram, …)
- **Self-hosted** — your data, domain, and credentials stay with you

```bash
git clone https://github.com/askopintsev/shiftedblog.git
cd shiftedblog && ./scripts/setup.sh   # one-time setup
./scripts/start-local.sh             # daily → editor http://localhost:5173/login
```

Prerequisites: [Docker](https://docs.docker.com/get-docker/) · [Git](https://git-scm.com/downloads)

More: [getting started](docs/en/getting-started.md) · [online deploy](docs/en/production-deploy.md) · [private editor](docs/en/private-editor-deploy.md) · [host/domain move](docs/en/host-migration.md)

## Русский

Пишете один раз — публикуете на сайт и в другие каналы из одного рабочего места.

- **Единый редактор** — черновики и подготовка в одном месте
- **Отправка в каналы** — публикация в выбранные каналы (сайт, Telegram и др.)
- **На вашем оборудовании** — данные и доступы остаются у вас

Скачайте проект, один раз настройте, затем каждый день запускайте:

```bash
git clone https://github.com/askopintsev/shiftedblog.git
cd shiftedblog && ./scripts/setup.sh   # однократная настройка
./scripts/start-local.sh             # каждый день → http://localhost:5173/login
```

Или дважды щёлкните `Start ShiftedBlog.command` / `start-shiftedblog.desktop`.

Сначала установите: [Docker](https://docs.docker.com/get-docker/) · [Git](https://git-scm.com/downloads)

Подробнее: [быстрый старт](docs/ru/getting-started.md) · [онлайн запуск](docs/ru/production-deploy.md) · [приватный редактор](docs/ru/private-editor-deploy.md) · [перенос](docs/ru/host-migration.md)

## License

[MIT](LICENSE) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md)
