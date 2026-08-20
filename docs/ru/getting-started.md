# Быстрый старт

ShiftedBlog — **программа для управления блогом** на вашем компьютере или на сервере в интернете. Главное после настройки — **интерфейс редактора**.

English: [Getting started](../en/getting-started.md)

## Ваша цель

**На компьютере:** **http://localhost:5173/login** → вход → **http://localhost:5173/posts**

**На сервере:** **https://editor.example.com/login** → вход → **https://editor.example.com/posts**

Это рабочее место: посты, серии, отправка в каналы. Публичный блог и панель Django — вторичны.

> **Локальная установка — не сайт в интернете.** Это панель в браузере на **вашем** компьютере. Снаружи её никто не видит. Мультиканальная отправка (сайт, Telegram и др.) работает и локально после настройки каналов в панели администратора.

---

## Выберите сценарий

| Сценарий | Когда | Инструкция |
|----------|-------|------------|
| **На своём компьютере** | Попробовать, писать посты, настроить каналы | [local-deploy.md](local-deploy.md) |
| **Онлайн запуск (на сервере)** | Публичный сайт на VPS с HTTPS | [production-deploy.md](production-deploy.md) |
| **Приватный редактор (VPS)** | HTTPS-редактор + Telegram, без публичного блога | [private-editor-deploy.md](private-editor-deploy.md) (`3) private` или `4) private-ip` без домена) |
| **Перенос хоста или домена** | Уже был production, меняете VPS или домен | [host-migration.md](host-migration.md) |

**Порядок онлайн запуска (кратко):** DNS → скачать проект → порты → `./scripts/setup.sh` (**`2) online`**, «Start Docker now?» → **`n`**) → TLS → `./deploy.sh` → логин. Подробно — в [production-deploy.md](production-deploy.md).

---

## Локальный быстрый старт

### Что установить

| Программа | Зачем | Скачать |
|-----------|-------|---------|
| Docker + Compose | Сервер и редактор в контейнерах | https://docs.docker.com/get-docker/ |
| curl | Скрипт запуска | обычно уже есть |
| Git | Клонировать репозиторий (или ZIP) | https://git-scm.com/downloads |

Проверка:

```bash
docker compose version
curl --version
```

**Node.js для обычной работы не нужен** — редактор в Docker.

### Однократная настройка

```bash
git clone https://github.com/askopintsev/shiftedblog.git
cd shiftedblog
./scripts/check-prerequisites.sh local
./scripts/setup.sh          # выберите 1) local
docker compose exec web python manage.py createsuperuser   # если мастер не создал
```

Если Git нет — архив ZIP, см. [local-deploy.md](local-deploy.md) (шаг 1).

### Каждый день

```bash
./scripts/start-local.sh
```

Откроется **http://localhost:5173/login** в браузере.

Ярлыки: `Start ShiftedBlog.command` (macOS), `start-shiftedblog.desktop` (Linux), `start-shiftedblog.bat` (Windows).

### Куда заходить (локально)

| Адрес | Для чего |
|-------|----------|
| http://localhost:5173/login | **Интерфейс редактора — начните здесь** |
| http://localhost:8888/ | Как выглядит блог для читателя |
| http://localhost:8888/lenta/ | Лента — все опубликованные (вход Django на 8888) |
| http://localhost:8888/mellon/ | Панель администратора (настройки, каналы) |

Полная инструкция: [local-deploy.md](local-deploy.md)

---

## После первого входа

1. Создавайте и редактируйте посты (**Новый пост**)
2. По желанию: панель администратора → **Core → Site settings**
3. По желанию: **Core → Credentials** — Telegram и другие каналы

---

## Дальше

- [Локальный запуск (полная инструкция)](local-deploy.md)
- [Онлайн запуск (на сервере)](production-deploy.md)
- [Приватный редактор (VPS, без публичного блога)](private-editor-deploy.md)
- [Перенос хоста и домена](host-migration.md)
- [Настройки](configuration.md)
- [Site settings](site-settings.md)
- [Security runbook](../security-runbook.md)
- [Заметки для мейнтейнера (CI / Doppler)](maintainer.md)
