# Перенос хоста и домена

English: [Host and domain migration](../en/host-migration.md)

## Ваша цель: тот же блог на новом VPS и/или домене

После переноса должно работать:

**https://editor.new.example.com/login** → вход → **https://editor.new.example.com/posts**

При смене домена (сценарий B) старые URL (`https://old.example.com/…`) отдают **HTTPS 301** на новый `SITE_URL` с **нового** VPS, пока жив старый домен.

> Инструкция **не привязана к конкретному хостингу**. Используйте `backup_db` / `restore_db`, `./scripts/apply-domain.sh` и `REDIRECT_FROM_*` в nginx.

**Порядок переноса:** инвентаризация (1) → DNS нового домена (2) → подготовка VPS (3) → проект + restore (4) → TLS и репетиция (5) → cutover (6) → затухание старого домена (7). Публичный DNS старой зоны на новый IP — **только на шаге 6** (кроме **нового** домена для репетиции на шаге 5).

## Что нужно заранее

- Рабочий production на старом VPS (`secrets.env`, бэкапы)
- Копии `backups/*.sql.gz`, `backups/media_*.tar.gz` и `secrets.env` **вне обоих серверов**
- Postgres в дампе — **мажорная версия 17** (как в `docker-compose.prod.yml`)
- При restore **не меняйте** `SECRET_KEY`, `CREDENTIALS_ENCRYPTION_KEY`, `ADMIN_URL` и пароли БД

## Сценарии

| | **A — тот же hostname, новый VPS** | **B — новый hostname + мягкое затухание** |
|---|-----------------------------------|-------------------------------------------|
| Меняется | Только IP сервера | `SITE_URL`, домен редактора |
| DNS cutover | A/AAAA старой зоны → новый IP | Старая зона → новый IP; новая зона — с шага 5 |
| Старый VPS | Выключить через 24–48 ч после cutover | То же |
| 301 со старых имён | Не нужны | `REDIRECT_FROM_DOMAINS` / `REDIRECT_FROM_EDITOR_DOMAINS` |

Пример (B): `https://old.example.com` → `https://new.example.com`, редактор `https://editor.new.example.com`.

`EXTRA_DOMAINS` — **тот же** сайт на дополнительных хостах (дубли контента). Для 301 со **старых** имён используйте `REDIRECT_FROM_*`, **не** `EXTRA_DOMAINS`.

---

## Шаг 1. Инвентаризация (исходный хост)

На **текущем** production-сервере (секреты не коммитить):

```bash
cd /opt/shiftedblog
pwd
hostname -I
docker compose version
ls /etc/letsencrypt/live/ 2>/dev/null || true
crontab -l
grep -E '^(DOMAIN|SITE_URL|EDITOR_|SSL_CERT_NAME|EXTRA_DOMAINS|REDIRECT_FROM|EMAIL_HOST|SERVER_IP)=' secrets.env
```

Запишите вне сервера:

- [ ] Публичный IPv4 / IPv6, путь приложения (обычно `/opt/shiftedblog`)
- [ ] DNS: A/AAAA для `@`, `www`, `editor`
- [ ] Почта (SMTP), cron, сертификаты, CI (`VPS_HOST`), вебмастер

Снизьте TTL **старой** зоны до 300 с, если панель позволяет.

Бэкап:

```bash
cd /opt/shiftedblog
docker compose -f docker-compose.prod.yml exec -T web python manage.py backup_db
```

Скопируйте `backups/*.sql.gz`, `backups/media_*.tar.gz` и `secrets.env` на ноутбук или в объектное хранилище.

---

## Шаг 2. DNS нового домена

**Сценарий A** — пропустите, если hostname не меняется.

В панели **регистратора / DNS** для **нового** домена создайте записи (A можно временно не указывать на VPS):

| Имя | Тип | Значение |
|-----|-----|----------|
| `@` | A | `IP_НОВОГО_VPS` (на шаге 5) или парковка |
| `www` | A | то же |
| `editor` | A | то же |

- [ ] NS корректны
- [ ] **Старую** зону не менять до cutover (шаг 6)

Проверка (когда A укажете на новый VPS):

```bash
dig +short new.example.com A
dig +short editor.new.example.com A
```

---

## Шаг 3. Подготовка нового VPS

Подставьте `NEW_VPS_IP` и пользователя `deploy` (или своего).

### SSH-ключи

Ключ **оператора** на ноутбуке (не ключ GitHub Actions — он для CI):

```bash
test -f ~/.ssh/id_ed25519.pub || ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -C "shiftedblog-operator"
cat ~/.ssh/id_ed25519.pub
```

Публичную строку — в панель провайдера или `/root/.ssh/authorized_keys` через консоль. Затем:

```bash
ssh -o PreferredAuthentications=publickey root@NEW_VPS_IP
```

При `Permission denied (publickey,password)` ключ ещё не на сервере. Приватный ключ в панель не загружать.

Sudo-пользователь (сессию root не закрывать, пока второй терминал не войдёт):

```bash
adduser --disabled-password --gecos "" deploy
usermod -aG sudo deploy
passwd deploy
mkdir -p /home/deploy/.ssh && chmod 700 /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/authorized_keys
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh

mkdir -p /etc/ssh/sshd_config.d
cat >/etc/ssh/sshd_config.d/99-shiftedblog-hardening.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
EOF
sshd -t && systemctl reload ssh
```

Проверьте из **нового** терминала: `ssh deploy@NEW_VPS_IP` и `sudo true`.

### Порты 80 и 443

Docker-nginx и Let's Encrypt нужны свободные **80** и **443**:

```bash
ss -tlnp | grep -E ':80|:443' || echo "порты 80 и 443 свободны"
```

| Что в выводе `ss` | Что сделать |
|-------------------|-------------|
| **nginx** / **apache2** | Системный веб-сервер хостинга — остановите (ниже) |
| **docker-proxy** | Старый Docker-стек — `docker compose down` или `./scripts/vps-clean-for-fresh-deploy.sh` |
| Пусто | Переходите к установке Docker |

```bash
sudo systemctl stop nginx apache2 2>/dev/null || true
sudo systemctl disable nginx apache2 2>/dev/null || true
ss -tlnp | grep -E ':80|:443' || echo "порты 80 и 443 свободны"
```

### Пакеты, файрвол, Docker

```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y ca-certificates curl ufw fail2ban certbot
sudo ufw --force reset && sudo ufw default deny incoming && sudo ufw default allow outgoing
sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw --force enable
```

Docker (Ubuntu/Debian):

```bash
curl -fsSL https://get.docker.com | sh
sudo systemctl enable --now docker
sudo usermod -aG docker deploy
```

Перелогиньтесь как `deploy`, проверьте:

```bash
docker compose version
certbot --version
```

---

## Шаг 4. Проект и restore

> **Не запускайте `./scripts/setup.sh`** при переносе существующего сайта — мастер сгенерирует новый `ADMIN_URL` и может перезаписать ключи.

### Скачайте проект

```bash
sudo mkdir -p /opt/shiftedblog
sudo chown deploy:deploy /opt/shiftedblog
cd /opt/shiftedblog
git clone https://github.com/YOUR_USER/shiftedblog.git .
```

Если Git недоступен — архив ZIP, см. [local-deploy.md](local-deploy.md) (шаг 1).

```bash
cd /opt/shiftedblog
./scripts/check-prerequisites.sh online
chmod +x scripts/*.sh scripts/backup/*.sh
```

### Скопируйте бэкапы и secrets.env

С ноутбука:

```bash
scp /path/to/*_pg_dump_*.sql.gz deploy@NEW_VPS_IP:/opt/shiftedblog/backups/
scp /path/to/media_*.tar.gz deploy@NEW_VPS_IP:/opt/shiftedblog/backups/
scp /path/to/old-secrets.env deploy@NEW_VPS_IP:/opt/shiftedblog/secrets.env
```

### Обновите доменные ключи (без ротации секретов)

**Сценарий A** (тот же домен, новый IP):

```bash
cd /opt/shiftedblog
./scripts/apply-domain.sh \
  --domain example.com \
  --site-url https://example.com \
  --editor-domain editor.example.com \
  --ssl-cert-name example.com \
  --server-ip NEW_VPS_IP
```

**Сценарий B** (новый домен + 301 со старых имён):

```bash
cd /opt/shiftedblog
./scripts/apply-domain.sh \
  --domain new.example.com \
  --site-url https://new.example.com \
  --editor-domain editor.new.example.com \
  --ssl-cert-name new.example.com \
  --redirect-from old.example.com,www.old.example.com \
  --redirect-from-editor editor.old.example.com \
  --server-ip NEW_VPS_IP
```

В `--redirect-from*` указывайте только имена, которые **резолвятся в DNS** на момент выпуска сертификата.

`apply-domain.sh` перегенерирует nginx; интерфейс редактора пересоберёт **`./deploy.sh`** (шаг 5).

### Восстановите данные

```bash
cd /opt/shiftedblog
mkdir -p logs static media static_blog backups
docker compose -f docker-compose.prod.yml up -d db redis web
./scripts/backup/restore.sh --dry-run
./scripts/backup/restore.sh --force
```

---

## Шаг 5. TLS и репетиция

Все команды — из `/opt/shiftedblog`. DNS **нового** домена должен указывать на `NEW_VPS_IP` (или используйте hosts-файл на ноутбуке для репетиции до cutover).

> В командах ниже `new.example.com` — **новый** домен (сценарий B). Для **сценария A** подставьте прежний домен (`example.com`, `editor.example.com`).

```bash
cd /opt/shiftedblog
dig +short new.example.com A
```

### Первый сертификат Let's Encrypt

```bash
sudo mkdir -p /var/www/html
docker compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true
sudo systemctl stop nginx 2>/dev/null || true
sudo certbot certonly --standalone --agree-tos --register-unsafely-without-email \
  -d new.example.com -d www.new.example.com -d editor.new.example.com
```

`SSL_CERT_NAME` в `secrets.env` должен совпадать с каталогом в `/etc/letsencrypt/live/` (обычно основной домен).

### Запуск проекта

```bash
cd /opt/shiftedblog
./deploy.sh
```

Первый запуск может занять **несколько минут** (сборка образов, в том числе редактора).

Продление позже (проект уже запущен):

```bash
sudo certbot certonly --webroot -w /var/www/html \
  -d new.example.com -d www.new.example.com -d editor.new.example.com
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

### Репетиция до cutover (hosts-файл)

Если **старая** зона ещё указывает на старый VPS, на ноутбуке:

```text
NEW_VPS_IP  new.example.com
NEW_VPS_IP  www.new.example.com
NEW_VPS_IP  editor.new.example.com
```

Затем откройте **https://editor.new.example.com/login** (предупреждение браузера о сертификате — нормально, если LE только для нового домена).

### Чеклист репетиции

- [ ] Главная, пост, картинка из media
- [ ] Canonical / sitemap = `SITE_URL`
- [ ] **https://editor.new.example.com/login** — вход (cookies на новом домене → повторный логин ожидаем)
- [ ] `ENV_FILE=secrets.env ./scripts/check-env.sh online`
- [ ] `docker compose -f docker-compose.prod.yml ps` — все сервисы up

---

## Шаг 6. Cutover

> **Сценарий A:** переключите A/AAAA старой зоны на `NEW_VPS_IP`, при необходимости перевыпустите сертификат (шаг 5, без `--expand` и без старых имён), выполните `./deploy.sh` и проверьте редактор. Пункты 4–5 ниже — для **сценария B**.

1. **Заморозьте запись** на старом VPS: `docker compose -f docker-compose.prod.yml stop web`
2. **Финальный бэкап** на старом VPS; при необходимости `./scripts/backup/restore.sh --force` на новом
3. **DNS старой зоны** — A/AAAA (`@`, `www`, `editor`) → **NEW_VPS_IP**
4. **Расширьте сертификат** (только имена, которые уже резолвятся на новый IP):

```bash
cd /opt/shiftedblog
docker compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true
sudo systemctl stop nginx 2>/dev/null || true
sudo certbot certonly --standalone --cert-name new.example.com --expand \
  --agree-tos --register-unsafely-without-email \
  -d new.example.com -d www.new.example.com -d editor.new.example.com \
  -d old.example.com -d www.old.example.com -d editor.old.example.com
./deploy.sh
```

5. **Проверка:**

```bash
curl -sI https://www.old.example.com/ | head -3
# ожидается 301 → https://new.example.com/
curl -sI https://new.example.com/ | head -3
# ожидается 200
curl -skI https://editor.new.example.com/login | head -1
docker compose -f docker-compose.prod.yml ps
```

Откройте **https://editor.new.example.com/login** в браузере.

6. Обновите CI / secret manager — [maintainer.md](maintainer.md)
7. Через **24–48 ч** выключите старый VPS

Почта может оставаться на старом SMTP до создания ящиков на новом домене — см. [security-runbook.md](../security-runbook.md).

---

## Шаг 7. Мягкое затухание (сценарий B)

- Старый домен = только DNS + сертификаты на **новом** VPS; старый сервер выключен
- Напоминание **до** истечения регистрации: не продлевать, если хватает 301
- **~2 недели до expiry**: уберите `REDIRECT_FROM_*` через `./scripts/apply-domain.sh`, перевыпустите сертификат только для новых имён, удалите DNS старого домена
- После expiry legacy URL перестанут резолвиться

---

## Cron на новом VPS

```bash
0 3 * * * cd /opt/shiftedblog && ./scripts/backup/run-backup.sh
```

Опционально: еженедельный отчёт — [security-runbook.md](../security-runbook.md).

---

## См. также

- [Онлайн запуск (на сервере)](production-deploy.md) — первичная установка с нуля
- [Локальный запуск](local-deploy.md) — разработка на компьютере
- [configuration.md](configuration.md) — переменные `REDIRECT_FROM_*`, `EXTRA_DOMAINS`
- [maintainer.md](maintainer.md) — CI и Doppler
