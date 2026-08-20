# Локальный запуск

English: [../en/local-deploy.md](../en/local-deploy.md)

## Ваша цель: войти в интерфейс редактора

ShiftedBlog — **программа для управления блогом**. После настройки вы должны попасть сюда:

**http://localhost:5173/login** → вход → **http://localhost:5173/posts**

Это ваше рабочее место: посты, серии, отправка в каналы.

> **Установка на компьютер — это не готовый сайт в интернете.** Запускается панель управления в браузере на **вашем** компьютере. Снаружи её никто не видит. При этом работает полный редактор, в том числе **отправка в несколько каналов** (сайт, Telegram и др.) — после настройки доступов в панели администратора.

## Что нужно установить

Перед настройкой на компьютере должны быть **Docker** (с плагином Compose), **curl** и способ **скачать файлы проекта** (Git или архив с GitHub). Проверьте:

```bash
docker compose version   # Docker + плагин Compose
curl --version           # нужен скрипту запуска
git --version            # только если клонируете репозиторий
```

**Node.js для обычной работы не нужен** — интерфейс редактора запускается в Docker; [Node.js LTS](https://nodejs.org/) понадобится только если вы разрабатываете frontend отдельно.

### Шаг 1. Скачайте файлы проекта

**Если Git уже установлен** — клонируйте репозиторий и перейдите в папку:

```bash
git clone https://github.com/askopintsev/shiftedblog.git
cd shiftedblog
```

**Если Git нет** — скачайте архив и распакуйте (Linux/macOS):

```bash
curl -L -o shiftedblog.zip https://github.com/askopintsev/shiftedblog/archive/refs/heads/master.zip
unzip shiftedblog.zip
cd shiftedblog-master
```

На Windows можно скачать [архив (ZIP)](https://github.com/askopintsev/shiftedblog/archive/refs/heads/master.zip) в браузере, распаковать и открыть терминал в папке `shiftedblog-master`. Либо установите [Git](https://git-scm.com/downloads) и выполните команды клонирования выше.

### Шаг 2. Проверьте, всё ли готово

В папке проекта выполните:

```bash
./scripts/check-prerequisites.sh local
```

Дальше — в зависимости от результата:

| Результат | Что делать |
|-----------|------------|
| **«Prerequisites OK»** | Переходите к [однократной настройке](#однократная-настройка): `./scripts/setup.sh` |
| **Чего-то не хватает** | Шаг 3 — установите недостающие программы |
| **Docker установлен, но не запущен** | Запустите Docker и снова проверьте (см. ниже) |
| **Порты 8888 или 5173 заняты** | Освободите порты (см. ниже) и снова `./scripts/check-prerequisites.sh local` |

Проверка портов вручную (локально нужны **8888** — backend, **5173** — интерфейс редактора):

```bash
ss -tlnp | grep -E ':8888|:5173' || echo "порты 8888 и 5173 свободны"
```

На macOS, если `ss` нет:

```bash
lsof -nP -iTCP:8888 -sTCP:LISTEN
lsof -nP -iTCP:5173 -sTCP:LISTEN
```

Если порт **5173** занят — часто это старый `npm run dev` на хосте. Остановите его или `./scripts/stop-local.sh`, если ShiftedBlog уже запускался.

Если Docker не запущен:

```bash
# Linux
sudo systemctl start docker
./scripts/check-prerequisites.sh local
```

На macOS и Windows откройте **Docker Desktop**, дождитесь запуска, затем снова:

```bash
./scripts/check-prerequisites.sh local
```

### Шаг 3. Установите недостающие программы

**Ubuntu, Debian или macOS (Homebrew)** — скрипт установит недостающее по запросу:

```bash
./scripts/install-prerequisites.sh
```

Подтвердите установку (`y`). На Linux после установки Docker может понадобиться **выйти из сеанса и войти снова** (или перезагрузка), затем снова:

```bash
./scripts/check-prerequisites.sh local
```

**Windows или другой дистрибутив Linux** — установите вручную, затем повторите проверку:

```bash
./scripts/check-prerequisites.sh local
```

Ссылки для ручной установки:

- [Git](https://git-scm.com/downloads) — если ещё не скачивали проект через `git clone`
- [Docker Desktop](https://docs.docker.com/get-docker/)

На Windows для скриптов используйте **Git Bash** и ярлык `start-shiftedblog.bat`.

## Однократная настройка

```bash
git clone https://github.com/askopintsev/shiftedblog.git
cd shiftedblog
./scripts/setup.sh
```

Выберите **`1) local`**. Мастер создаст настройки и может сразу собрать Docker. **Первый запуск может занять несколько минут.**

Создайте логин, если мастер не предложил:

```bash
docker compose exec web python manage.py createsuperuser
```

Введите **email** и **пароль** для входа в редактор.

## Каждый день: один запуск

После настройки запустите всё и откройте страницу входа:

```bash
./scripts/start-local.sh
```

Или дважды щёлкните по файлу в папке проекта:

| Файл | Платформа |
|------|-----------|
| `Start ShiftedBlog.command` | macOS |
| `start-shiftedblog.desktop` | Linux (создаётся при setup; можно скопировать на рабочий стол) |
| `start-shiftedblog.bat` | Windows (нужен Git Bash; Docker Desktop должен быть запущен) |

Скрипт поднимает Docker (сервер + интерфейс редактора), ждёт готовности и открывает **http://localhost:5173/login** в браузере.

Остановить:

```bash
./scripts/stop-local.sh
```

## Куда заходить

| Адрес | Для чего |
|-------|----------|
| http://localhost:5173/login | **Интерфейс редактора — начните здесь** |
| http://localhost:8888/ | Как выглядит блог для читателя (на вашем компьютере) |
| http://localhost:8888/mellon/ | Панель администратора (настройки, доступы к каналам) |

## Полезные команды

```bash
docker compose logs -f web
docker compose logs -f editor-ui
docker compose exec web python manage.py createsuperuser
./scripts/stop-local.sh
```

## Если что-то пошло не так

**Ошибка пароля базы данных после повторной настройки**

```bash
docker compose down -v
./scripts/setup.sh   # снова local
```

**Скрипт запуска ждёт слишком долго**

Проверьте `docker compose ps` — у базы **healthy**, web и editor-ui **running**. Логи: `docker compose logs web editor-ui`.

**Не получается войти**

- Запустите `./scripts/start-local.sh` снова и дождитесь «Editor UI is ready»
- Email и пароль те же, что при `createsuperuser`

**Ярлык на Linux**

Если нет `start-shiftedblog.desktop`:

```bash
sed "s|@PROJECT_ROOT@|$(pwd)|g" start-shiftedblog.desktop.in > start-shiftedblog.desktop
```

## Для опытных: без Docker

Нужны PostgreSQL, Redis и Node.js на компьютере — см. [английскую версию](local-deploy.md).

## Проверка настроек

```bash
./scripts/check-env.sh local
```
