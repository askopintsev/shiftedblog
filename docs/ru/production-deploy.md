# Онлайн запуск (на сервере)

English: [Online deploy (on server)](../en/production-deploy.md)

## Ваша цель: войти в интерфейс редактора на своём домене

После настройки откройте:

**https://editor.example.com/login** → вход → **https://editor.example.com/posts**

Это основное рабочее место. Публичный блог на `https://example.com/` и панель Django — вторичны.

> Инструкция **не привязана к конкретному хостингу** — подойдёт любой VPS с Docker. На чистом сервере проще всего. Если уже стояла старая установка — ниже описана **необязательная** очистка.

> **Без публичного блога?** См. [private-editor-deploy.md](private-editor-deploy.md) (`setup.sh` **`3) private`**, `PUBLIC_SITE_ENABLED=false`).

**Порядок первого запуска:** DNS (шаг 1) → скачать проект (2) → порты (3) → `./scripts/setup.sh` с **`2) online`**, на «Start Docker now?» ответить **`n`** (4) → TLS (5) → `./deploy.sh` (6) → логин (7) → проверка в браузере (8).

## Что нужно заранее

- **VPS** (удобнее Ubuntu/Debian) с доступом по SSH
- **Домен** (например `example.com`)
- **DNS**, указывающий на VPS **до** получения TLS (шаг 1)

Проверка на сервере (команды `docker`, `git`, `curl`; скрипт `./scripts/check-prerequisites.sh online` — **после** шага 2, когда проект уже скачан):

```bash
docker compose version   # Docker + плагин Compose
git --version
curl --version
certbot --version        # для Let's Encrypt
```

Установка Docker на Ubuntu, если его нет:

```bash
curl -fsSL https://get.docker.com | sh
sudo systemctl enable --now docker
```

---

## Шаг 1. Направьте DNS на VPS

В панели регистратора или DNS создайте **A-записи** на публичный IP сервера:

| Имя | Тип | Значение |
|-----|-----|----------|
| `@` | A | `IP_ВАШЕГО_VPS` |
| `www` | A | `IP_ВАШЕГО_VPS` |
| `editor` | A | `IP_ВАШЕГО_VPS` |

Проверка (с компьютера или с VPS):

```bash
dig +short example.com A
dig +short editor.example.com A
```

Оба запроса должны вернуть IP сервера — иначе Let's Encrypt не выдаст сертификат.

> **DNS ещё не работает?** Проект можно проверить по IP, пока чините записи у регистратора. При **`./scripts/setup.sh`** (шаг 4) введите **публичный IP сервера** — он попадёт в nginx и `ALLOWED_HOSTS`. Получите временный самоподписанный сертификат (шаг 5) или дождитесь DNS и Let's Encrypt. Откройте `https://IP_ВАШЕГО_VPS/`. Для редактора добавьте в hosts-файл на компьютере:
>
> ```text
> IP_ВАШЕГО_VPS  editor.example.com
> ```
>
> Затем откройте `https://editor.example.com/login`.

---

## Шаг 2. Скачайте проект на сервер

```bash
sudo mkdir -p /opt/shiftedblog
sudo chown "$USER:$USER" /opt/shiftedblog
cd /opt/shiftedblog
git clone https://github.com/YOUR_USER/shiftedblog.git .
```

Если Git недоступен — см. шаг 1 в [local-deploy.md](local-deploy.md) (архив ZIP).

---

## Шаг 3. Проверьте порты и (необязательно) удалите старую установку

### Проверьте, свободны ли порты 80 и 443

На сервере нужны порты **80** и **443** (nginx и Let's Encrypt). Проверка:

```bash
ss -tlnp | grep -E ':80|:443' || echo "порты 80 и 443 свободны"
```

На macOS, если `ss` нет:

```bash
lsof -nP -iTCP:80 -sTCP:LISTEN
lsof -nP -iTCP:443 -sTCP:LISTEN
```

После клонирования проекта (шаг 2) скрипт тоже предупредит:

```bash
cd /opt/shiftedblog
./scripts/check-prerequisites.sh online
```

| Результат | Что делать |
|-----------|------------|
| **Порты свободны** | Переходите к мастеру настройки (шаг 4) |
| **80 или 443 заняты** | Смотрите, **кто** слушает порт (ниже), и действуйте по ситуации |

**Как понять, кто занял порт.** В выводе `ss` смотрите последний столбец (`users:(("…"))`) — имя процесса:

```text
# порты свободны — команда ничего не вывела, или только строка «порты свободны»
# занят системный nginx:
LISTEN … users:(("nginx",pid=…))
# занят apache:
LISTEN … users:(("apache2",pid=…))
# занят Docker (старый ShiftedBlog или другой compose):
LISTEN … users:(("docker-proxy",pid=…))
```

| Что видите в выводе | Что сделать |
|---------------------|-------------|
| **nginx** или **apache2** | Системный веб-сервер хостинга — остановите его (команды ниже), затем снова проверьте порты |
| **docker-proxy** | Старый Docker-стек — необязательная очистка ниже или `docker compose -f docker-compose.prod.yml down` |
| **Другое имя** | Запишите PID из вывода, разберитесь у провайдера VPS или остановите процесс вручную |

**Только если в выводе был nginx/apache** — остановите системный веб-сервер:

```bash
sudo systemctl stop nginx apache2 2>/dev/null || true
ss -tlnp | grep -E ':80|:443' || echo "порты 80 и 443 свободны"
```

Если после этого порты всё ещё заняты — смотрите таблицу выше (часто остаётся `docker-proxy`).

### Необязательно — удалить старую установку ShiftedBlog

**Пропустите на чистом VPS**, где нет `/opt/shiftedblog`.

Если на машине уже был ShiftedBlog или другой Docker-стек на портах 80/443:

```bash
cd /opt/shiftedblog
./scripts/vps-clean-for-fresh-deploy.sh
```

Затем снова клонируйте проект (шаг 2) или продолжите с пустой папки.

---

## Шаг 4. Мастер настройки

```bash
cd /opt/shiftedblog
./scripts/setup.sh
```

Выберите **`2) online`**. Укажите:

- Основной домен (например `example.com`, без `www`)
- Публичный URL (по умолчанию `https://example.com`)
- Поддомен редактора (по умолчанию `editor.example.com`)
- Имя сертификата Let's Encrypt (по умолчанию = основной домен)
- Публичный IP сервера (необязательно, для nginx)

Мастер создаст `secrets.env`, сгенерирует `nginx/nginx.conf`, может запустить Docker.

На вопрос **«Start Docker now?»** при **первом** запуске на сервере можно ответить **`n`**, если сертификаты ещё не получены.

---

## Шаг 5. TLS-сертификаты

DNS уже должен указывать на этот сервер (шаг 1), **если используете Let's Encrypt**. Все команды ниже — из каталога проекта:

```bash
cd /opt/shiftedblog
```

### Первый сертификат Let's Encrypt (проще всего — порт 80 свободен)

```bash
sudo mkdir -p /var/www/html
docker compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true
sudo certbot certonly --standalone --agree-tos --register-unsafely-without-email \
  -d example.com -d www.example.com -d editor.example.com
```

`SSL_CERT_NAME` в `secrets.env` должен совпадать с каталогом в `/etc/letsencrypt/live/` (обычно основной домен, например `example.com`).

### Временный самоподписанный сертификат (DNS ещё не работает)

Замените `example.com` на ваш домен. Затем выполните шаг 6 (`./deploy.sh`).

```bash
sudo mkdir -p /etc/letsencrypt/live/example.com
sudo openssl req -x509 -nodes -days 30 -newkey rsa:2048 \
  -keyout /etc/letsencrypt/live/example.com/privkey.pem \
  -out /etc/letsencrypt/live/example.com/fullchain.pem \
  -subj "/CN=example.com" \
  -addext "subjectAltName=DNS:example.com,DNS:www.example.com,DNS:editor.example.com"
```

Когда DNS заработает — получите Let's Encrypt (команда выше) и снова `./deploy.sh`.

### Продление / перевыпуск (проект уже запущен)

```bash
sudo certbot certonly --webroot -w /var/www/html \
  -d example.com -d www.example.com -d editor.example.com
```

**Если вы сменили домен** (в `secrets.env` или через `./scripts/apply-domain.sh`) — перегенерируйте nginx и перезагрузите его:

```bash
./scripts/generate-nginx-conf.sh
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

---

## Шаг 6. Запуск на сервере

```bash
cd /opt/shiftedblog
./deploy.sh
```

`deploy.sh` проверяет `secrets.env`, собирает образы (включая интерфейс редактора), поднимает `docker-compose.prod.yml`, перезагружает nginx. Первый запуск может занять **несколько минут**.

Проверка env вручную (необязательно — `deploy.sh` делает это сам):

```bash
ENV_FILE=secrets.env ./scripts/check-env.sh online
```

---

## Шаг 7. Создайте логин

Если мастер на шаге 4 не создал пользователя, выполните:

```bash
cd /opt/shiftedblog
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

В качестве логина укажите **email**. Сохраните путь админки из вывода мастера (`ADMIN_URL` в `secrets.env`).

---

## Шаг 8. Проверка

Откройте **https://editor.example.com/login** в браузере и войдите.

На сервере (домен должен резолвиться на этот VPS; для самоподписанного сертификата добавьте `-k`):

```bash
curl -skI https://editor.example.com/login | head -1
docker compose -f docker-compose.prod.yml ps
```

Путь админки: `ADMIN_URL` в `secrets.env` → `https://example.com/ADMIN_URL/`

---

## Обновления

```bash
cd /opt/shiftedblog
./deploy.sh
```

## Сборка интерфейса редактора

**При обычной установке ничего дополнительно делать не нужно.** Мастер `./scripts/setup.sh` уже записывает `SITE_URL` в `secrets.env`, а `./deploy.sh` сам подставляет его в сборку интерфейса редактора.

| Ситуация | Действие |
|----------|----------|
| Первый запуск по этой инструкции | Ничего — следуйте шагам 4–6 |
| Сменили домен или `SITE_URL` вручную | Обновите `secrets.env` (или `./scripts/apply-domain.sh`), затем снова `./deploy.sh` |

Техническая справка: в образ вшиваются `VITE_PUBLIC_SITE_BASE` и `VITE_API_BASE`; их берут из `SITE_URL` и `secrets.env` при сборке.

## Опциональный CI

GitHub Actions + Doppler — для мейнтейнера: [maintainer.md](maintainer.md). Для self-host достаточно `secrets.env` и `./deploy.sh`.

## Перенос хоста или домена

Не кладите старые имена в `EXTRA_DOMAINS`. Для HTTPS 301 используйте `REDIRECT_FROM_DOMAINS` / `REDIRECT_FROM_EDITOR_DOMAINS`. Смена домена: `./scripts/apply-domain.sh`. Плейбук: [host-migration.md](host-migration.md).
