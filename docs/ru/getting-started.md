# Быстрый старт

ShiftedBlog — **управление блогом** на вашем компьютере или сервере. Главное после настройки — **интерфейс редактора**.

English: [../en/getting-started.md](../en/getting-started.md)

## Что вы получите

```text
Интерфейс редактора (рабочее место)  →  http://localhost:5173/login
Страница блога (для читателя)         →  http://localhost:8888/
Панель администратора                 →  http://localhost:8888/mellon/
```

**Цель:** один раз настроить → каждый день `./scripts/start-local.sh` (или ярлык) → войти.

> **Установка на компьютер — не сайт в интернете.** Это панель управления в браузере. Мультиканальная отправка работает и локально после настройки каналов.

Подробнее: [local-deploy.md](local-deploy.md)

## Выберите сценарий

1. **На своём компьютере** — [local-deploy.md](local-deploy.md)
2. **На сервере в интернете** — [production-deploy.md](production-deploy.md)
3. **Перенос** — [host-migration.md](host-migration.md)

## Что установить (локально)

| Программа | Скачать |
|-----------|---------|
| Git | https://git-scm.com/downloads |
| Docker | https://docs.docker.com/get-docker/ |

## Быстрый старт

**Один раз:**

```bash
git clone https://github.com/askopintsev/shiftedblog.git
cd shiftedblog
./scripts/setup.sh          # выберите 1) local
docker compose exec web python manage.py createsuperuser   # при необходимости
```

**Каждый день:**

```bash
./scripts/start-local.sh
```

Откроется http://localhost:5173/login в браузере.

Ярлыки: `Start ShiftedBlog.command` (macOS), `start-shiftedblog.desktop` (Linux), `start-shiftedblog.bat` (Windows).

## После первого входа

1. Создавайте посты (**Новый пост**)
2. По желанию: панель администратора → **Core → Site settings**
3. По желанию: **Core → Credentials** — Telegram и другие каналы

## Дальше

- [Локальный запуск (полная инструкция)](local-deploy.md)
- [Настройки](configuration.md)
- [Site settings](site-settings.md)
- [Перенос](host-migration.md)
- [Security runbook](../security-runbook.md)
