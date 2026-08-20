# Приватный редактор на VPS (без публичного блога)

English: [Private editor deploy](../en/private-editor-deploy.md)

## Ваша цель

**https://editor.example.com/login** → вход → посты → мультисенд в **Telegram** (и другие каналы). **Анонимного публичного блога** в интернете нет.

Для авторов доступна **Лента** — **https://editor.example.com/lenta/** (вход через Django-сессию, тот же staff-пользователь).

> Тот же прод-стек, что и при [онлайн запуске](production-deploy.md) (`docker-compose.prod.yml`, `./deploy.sh`), но `PUBLIC_SITE_ENABLED=false` и nginx обслуживает **только хост редактора** (+ прокси staff-путей).

**Порядок первого запуска (с доменом):** DNS → клон проекта → `./scripts/setup.sh` **`3) private`** → TLS → `./deploy.sh` → вход.

**Порядок первого запуска (без домена):** клон проекта → `./scripts/setup.sh` **`4) private-ip`** → self-signed TLS → `./deploy.sh` → строка в `/etc/hosts` на ПК → вход.

---

## Когда выбрать этот сценарий

| Сценарий | Гайд |
|----------|------|
| Публичный блог + редактор на VPS | [production-deploy.md](production-deploy.md) |
| Редактор + Telegram, **с вашим доменом** | **Этот гайд** — setup **`3) private`** |
| Редактор + Telegram, **без домена** (VPS + публичный IP) | **Этот гайд** — [без домена](#без-домена-4-private-ip) (`4) private-ip`) |
| Попробовать на ноутбуке | [local-deploy.md](local-deploy.md) |

> **Вне scope:** VPS без публичного IP (только VPN/NAT). Туннель или VPN — на вашей стороне, в документации проекта не описано.

---

## Перед стартом

- **VPS** с SSH, Docker и **публичным IP**
- Для **`3) private`**: **домен** (A-запись `editor`)
- Для **`4) private-ip`**: домен не нужен — fake hostname + `/etc/hosts` на вашем ПК
- `./scripts/check-prerequisites.sh private` после клонирования проекта

---

## Без домена (`4) private-ip`)

Подходит, если есть **VPS с публичным IP**, но **нет домена у регистратора**. DNS не нужен; на вашем компьютере добавляется одна строка в `/etc/hosts`, на сервере — self-signed TLS.

**Цель после настройки:** **https://editor.shiftedblog.local/login** (имя вымышленное, резолвится через hosts).

### Шаг 1. Проект на сервере

Как в [production-deploy.md](production-deploy.md), шаг 2 — клон в `/opt/shiftedblog` (или свой путь). Проверка:

```bash
cd /opt/shiftedblog
./scripts/check-prerequisites.sh private
```

### Шаг 2. Setup

```bash
cd /opt/shiftedblog
./scripts/setup.sh
```

1. Выберите **`4) private-ip`**
2. Укажите **публичный IP** сервера (скрипт иногда определяет его сам)
3. На «Start Docker now?» ответьте **`n`** — сначала нужен TLS (шаг 3)

В `secrets.env` по умолчанию:

| Переменная | Значение |
|------------|----------|
| `FAKE_HOSTNAME` | `true` |
| `DOMAIN` | `shiftedblog.local` |
| `EDITOR_DOMAIN` | `editor.shiftedblog.local` |
| `SITE_URL` / `EDITOR_URL` | `https://editor.shiftedblog.local` |
| `PUBLIC_SITE_ENABLED` | `false` |
| `SSL_CERT_NAME` | `shiftedblog.local` |
| `SERVER_IP` | ваш публичный IP |

### Шаг 3. TLS (self-signed)

```bash
cd /opt/shiftedblog
docker compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true
sudo ./scripts/generate-self-signed-cert.sh
```

Сертификат включает fake hostname и IP сервера (SAN). Каталог: `/etc/letsencrypt/live/shiftedblog.local/`.

### Шаг 4. Deploy

```bash
./deploy.sh
```

### Шаг 5. Hosts на вашем компьютере

На **каждом ПК**, с которого открываете редактор, добавьте строку (подставьте свой IP):

```text
IP_ВАШЕГО_VPS  editor.shiftedblog.local
```

| ОС | Файл |
|----|------|
| Linux / macOS | `/etc/hosts` |
| Windows | `C:\Windows\System32\drivers\etc\hosts` |

Без этой строки браузер не найдёт `editor.shiftedblog.local`.

### Шаг 6. Вход

1. Откройте **https://editor.shiftedblog.local/login**
2. Примите предупреждение о self-signed сертификате (один раз)
3. Войдите staff-пользователем → **/posts**
4. Лента: **https://editor.shiftedblog.local/lenta/** (при необходимости вход Django)

### Позже — реальный домен

Купили домен → перейдите на сценарий **«С вашим доменом»** ниже (`3) private` или `./scripts/apply-domain.sh --domain example.com --private`), Let's Encrypt, `./deploy.sh`, удалите строку из hosts.

---

## С вашим доменом (`3) private`)

**Цель после настройки:** **https://editor.example.com/login**

### Шаг 1. DNS

Одна **A-запись**:

| Имя | Тип | Значение |
|-----|-----|----------|
| `editor` | A | `IP_ВАШЕГО_VPS` |

Опционально: IP сервера в setup — для теста до пропагации DNS (self-signed TLS).

### Шаг 2. Проект на сервере

Как в [production-deploy.md](production-deploy.md), шаг 2 — клон в `/opt/shiftedblog` (или свой путь).

```bash
cd /opt/shiftedblog
./scripts/check-prerequisites.sh private
```

### Шаг 3. Setup

```bash
cd /opt/shiftedblog
./scripts/setup.sh
```

Выберите **`3) private`** (не `4) private-ip` — см. [без домена](#без-домена-4-private-ip)). Скрипт спросит:

- **Родительский домен** (например `example.com`) — для cookie сессии (`.example.com`)
- **Хост редактора** (по умолчанию `editor.example.com`)
- Опционально IP, legacy-редиректы editor, имя сертификата

Будет создан `secrets.env` с:

- `PUBLIC_SITE_ENABLED=false`
- `SITE_URL=https://editor.example.com` (= `EDITOR_URL`)
- nginx только для editor

На «Start Docker now?» ответьте **`n`**, пока нет TLS.

### Шаг 4. TLS

Выпустите или расширьте сертификат Let's Encrypt на editor (часто тот же каталог, что у родительского домена, например `SSL_CERT_NAME=example.com`, если в SAN есть `editor.example.com`).

```bash
sudo certbot certonly --standalone --agree-tos --register-unsafely-without-email \
  -d editor.example.com
```

`SSL_CERT_NAME` в `secrets.env` — **имя каталога** в `/etc/letsencrypt/live/` (не всегда совпадает с хостом editor).

Self-signed, если DNS ещё нет — см. [production-deploy.md](production-deploy.md), шаг 5.

### Шаг 5. Deploy

```bash
./deploy.sh
```

`deploy.sh` при `PUBLIC_SITE_ENABLED=false` вызывает `check-env.sh private`.

### Шаг 6. Вход

| URL | Назначение |
|-----|------------|
| https://editor.example.com/login | **Редактор — начните здесь** |
| https://editor.example.com/posts | Список постов |
| https://editor.example.com/lenta/ | Лента (все опубликованные; вход Django) |
| https://editor.example.com/{ADMIN_URL}/ | Django admin (путь из `secrets.env`) |

---

## Смена домена

```bash
./scripts/apply-domain.sh --domain example.com --private \
  --editor-domain editor.example.com
```

Ключи и `ADMIN_URL` не меняются. После — `./deploy.sh`.

---

## См. также

- [Быстрый старт](getting-started.md)
- [Онлайн запуск (публичный сайт)](production-deploy.md)
- [Конфигурация](configuration.md) — `PUBLIC_SITE_ENABLED`
- [Перенос хоста](host-migration.md)
