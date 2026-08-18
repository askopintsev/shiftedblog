# Перенос хоста и домена

English: [../en/host-migration.md](../en/host-migration.md)

Перенос ShiftedBlog на новый VPS и/или hostname без привязки приложения к провайдеру. Те же скрипты для сторонней установки: `backup_db` / `restore_db`, `apply-domain.sh`, `REDIRECT_FROM_*` в nginx.

При восстановлении существующего сайта **не** меняйте `SECRET_KEY` и `CREDENTIALS_ENCRYPTION_KEY`. Дамп Postgres должен быть той же мажорной версии (**17** в `docker-compose.prod.yml`).

## Сценарии

1. **A — тот же hostname, новый VPS** — меняется только IP.
2. **B — новый hostname + мягкое затухание** — новый `SITE_URL`, старые имена отдают HTTPS 301 на **новом** VPS, пока жив старый домен. Старый VPS выключается после переключения.

Пример (сценарий B): живой `SITE_URL` — **apex** `https://shiftedstuff.ru` (`PREPEND_WWW=false`; `www` тоже отвечает). Цель: `https://shiftedstuff.space`, редактор `https://editor.shiftedstuff.space`. Сейчас также отдаются `shiftedstuff.online` / `www` / `editor`. Старый VPS (Beget, `90.156.169.116`) выключается после cutover. Домен `shiftedstuff.ru` оплачен до **21.01.2027** и **не** продлевается. SMTP Beget (`noreply@shiftedstuff.ru`) оставляем до переноса почты.

| Дата | Действие |
|------|----------|
| Cutover | Обе зоны на новый VPS; 301 включены; старый VPS выкл. через 24–48 ч |
| **01.12.2026** | Не продлевать `.ru` |
| **~07.01.2027** | Убрать `REDIRECT_FROM_*`, перевыпустить сертификат только для `.space`, удалить DNS `.ru` |
| **21.01.2027** | Срок `.ru` истекает; старые URL перестают резолвиться |

`EXTRA_DOMAINS` отдаёт **тот же** сайт на доп. именах (дубли). Для 301 со старых имён используйте `REDIRECT_FROM_DOMAINS` / `REDIRECT_FROM_EDITOR_DOMAINS`.

## Инкременты оператора (этот перенос)

Один инкремент — результат в чат — следующий шаг. Публичный DNS на новый VPS не переключать до cutover.

1. **Инвентаризация + бэкап вне сервера + снизить TTL `.ru`** (Beget) — сделано (2026-08-13)
2. Зона Jino для `.space` (A-записи можно позже) — сделано (2026-08-13)
3. FirstVDS: SSH-ключи, ОС, файрвол, Docker — сделано (2026-08-14). ufw 22/80/443; хостовый nginx/ISPmanager/named выключены.
4. Установка + restore на FirstVDS (без публичного DNS) — вы здесь
5. Репетиция через `/etc/hosts`
6. Cutover (DNS + сертификаты + 301 + CI)
7. Выключить Beget через 24–48 ч
8. Календарь затухания (не продлевать `.ru`)

---

## Инвентаризация (исходный хост)

Скопируйте это **вне** старого VPS (секреты не коммитить). На **текущем** (Beget) сервере:

```bash
# путь часто /opt/shiftedblog
pwd
hostname -I
docker --version
docker compose version
ls /etc/letsencrypt/live/ 2>/dev/null || true
crontab -l
# только имена — не вставляйте значения секретов в чат и git
grep -E '^(DOMAIN|SITE_URL|EDITOR_|SSL_CERT_NAME|EXTRA_DOMAINS|EMAIL_HOST)=' secrets.env
```

- [ ] Публичный IPv4 / IPv6
- [ ] Путь приложения (в доках `/opt/shiftedblog`)
- [ ] Версии Docker / Compose
- [ ] DNS: A/AAAA/CNAME/MX/TXT для apex, `www`, `editor`
- [ ] Почта (хост, from). Пример Beget: `smtp.beget.com` — [security-runbook.md](../security-runbook.md)
- [ ] Cron (`scripts/backup/run-backup.sh`, опционально `security_auth_report`)
- [ ] `SSL_CERT_NAME` и `/etc/letsencrypt/live/`
- [ ] CI: `VPS_HOST`, пользователь деплоя (только имена)
- [ ] Вебмастер / Дзен / ссылки в профилях

Бэкап и копия **вне обоих** серверов:

```bash
cd /opt/shiftedblog
docker compose -f docker-compose.prod.yml exec -T web python manage.py backup_db
```

Скопируйте `backups/*.sql.gz`, `backups/media_*.tar.gz` и `secrets.env` в приватное место. Снизьте TTL старой зоны до 300 с, если панель позволяет.

### Инкремент 2 — зона Jino (этот перенос)

В панели Jino для `shiftedstuff.space`:

- [x] NS Jino (`ns1`–`ns4.jino.ru`)
- [x] A сейчас: `@` и `*.shiftedstuff.space` → `81.177.141.15` (парковка Jino, **не** Beget). На cutover сменить на IP FirstVDS. Wildcard закрывает `www` и `editor`.
- [ ] TXT/SPF — позже, когда переедете почта

Зоны Beget `.ru` / `.online` пока не трогать.

### Этот перенос (Beget, 2026-08-13)

| Что | Значение |
|-----|----------|
| Путь | `/opt/shiftedblog` |
| IPv4 | `90.156.169.116` |
| Docker | 28.3.1 / Compose v2.38.1 |
| Сертификат | `/etc/letsencrypt/live/shiftedstuff.ru` |
| `SITE_URL` | `https://shiftedstuff.ru` (не www) |
| Editor | `https://editor.shiftedstuff.ru` |
| Доп. хосты | `shiftedstuff.online`, `www`, `editor` |
| Почта | `smtp.beget.com:465` SSL, `noreply@shiftedstuff.ru` |
| Секреты | Doppler `shifted_blog` / `prd` |
| Cron | ежедневно 03:00 бэкап; вс 03:15 чистка `+30` дн.; пн 09:00 `security_auth_report` |

---

## Подготовка (целевой хост)

1. Новая зона (пример: Jino для `shiftedstuff.space`) — apex, `www`, `editor`. **Не** направляйте A/AAAA на IP Beget. A пустые, пока нет FirstVDS.
2. Новый VPS (пример: FirstVDS `94.250.250.65`): **сначала вход по ключу**, затем пакеты, `ufw` 22/80/443, Docker. Приложение **пока не** клонировать.

Этот перенос: FirstVDS `94.250.250.65`, Ubuntu 24.04.4 LTS, hostname `milleniumfalcon`. Ключ оператора в `/root/.ssh/authorized_keys` (2026-08-14). Дальше: пользователь `deploy`, затем пакеты.

**Ключ оператора (ноутбук), не ключ GitHub Actions** (`scripts/ssh/generate-vps-deploy-key.sh` — для CI позже):

```bash
# на ноутбуке — можно свой существующий ~/.ssh/id_ed25519
test -f ~/.ssh/id_ed25519.pub || ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -C "shiftedblog-operator"
cat ~/.ssh/id_ed25519.pub
```

Панель FirstVDS → сервер → SSH-ключи (или `/root/.ssh/authorized_keys` через VNC): одна строка `.pub`. Затем:

```bash
ssh -o PreferredAuthentications=publickey root@94.250.250.65
```

Если `Permission denied (publickey,password)`: SSH жив, но **этого ключа ещё нет** в `/root/.ssh/authorized_keys`. Ключ только на ноутбуке не считается. FirstVDS без пароля: вставить `.pub` в **панели (SSH-ключи)** (перезагрузка/применение, если просит) или через **VNC**.

На ноутбуке — какой ключ уходит:

```bash
ssh -v -o PreferredAuthentications=publickey root@94.250.250.65 2>&1 | grep -E 'Offering public key|Authentications that can continue|identity file'
cat ~/.ssh/id_ed25519.pub
```

В **VNC** FirstVDS от root:

```bash
mkdir -p /root/.ssh
chmod 700 /root/.ssh
nano /root/.ssh/authorized_keys   # одна строка .pub
chmod 600 /root/.ssh/authorized_keys
```

Повторить `ssh`. Пользователя `deploy` и отключение паролей — только после успешного входа. Приватный ключ в панель не вставлять.

На VPS — sudo-пользователь и запрет пароля. Сессию root **не закрывать**, пока второй терминал не войдёт как новый пользователь.

```bash
adduser --disabled-password --gecos "" deploy
usermod -aG sudo deploy
passwd deploy
# пароль только для sudo; SSH по-прежнему по ключу
mkdir -p /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
nano /home/deploy/.ssh/authorized_keys   # та же строка .pub
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh

cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak
mkdir -p /etc/ssh/sshd_config.d
cat >/etc/ssh/sshd_config.d/99-shiftedblog-hardening.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
EOF
sshd -t && systemctl reload ssh
```

Новый терминал на ноутбуке:

```bash
ssh -o PreferredAuthentications=publickey deploy@94.250.250.65
sudo -n true || sudo true
```

Позже можно `PermitRootLogin no`. Ключ CI — второй pubkey у `deploy` (`scripts/ssh/install-vps-authorized-key.sh`), не сейчас.

Дальше пакеты (от `deploy` + sudo) — Docker из репозитория Docker, затем `usermod -aG docker`. Образы FirstVDS часто открывают ISPmanager/почту/FTP/DNS в `ufw` и держат **хостовый nginx на :80**. Для этого проекта нужны только 22/80/443, порт 80 должен быть свободен для Docker:

```bash
sudo systemctl stop nginx apache2 ihttpd 2>/dev/null || true
sudo systemctl disable nginx apache2 ihttpd 2>/dev/null || true
sudo ss -tlnp | grep -E ':80|:443|:1500'
```

```bash
sudo ss -tlnp | grep -E ':80|:443|:22'
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status
```
3. Установка как в [production-deploy.md](production-deploy.md):

```bash
sudo mkdir -p /opt/shiftedblog
sudo chown "$USER:$USER" /opt/shiftedblog
cd /opt/shiftedblog
git clone https://github.com/YOUR_USER/shiftedblog.git .
./scripts/setup.sh
# production: новый apex, канонический URL, при необходимости REDIRECT_FROM_*
```

4. Перенесите из **старого** `secrets.env` ключи `SECRET_KEY` и `CREDENTIALS_ENCRYPTION_KEY`. Новый `DB_PASS` на новом сервере допустим.
5. Пока **не** направляйте публичный DNS на новый IP.

Восстановление (мажор дампа — 17):

```bash
sudo mkdir -p /opt/shiftedblog/backups
sudo chown deploy:deploy /opt/shiftedblog/backups
```

С ноутбука:

```bash
scp /path/to/*_pg_dump_*.sql.gz deploy@94.250.250.65:/opt/shiftedblog/backups/
scp /path/to/media_*.tar.gz deploy@94.250.250.65:/opt/shiftedblog/backups/
scp /path/to/beget-secrets.env deploy@94.250.250.65:/opt/shiftedblog/secrets.env
```

Восстановление (мажор дампа — 17):

```bash
cd /opt/shiftedblog
ls -lh backups/
./scripts/backup/restore.sh --dry-run
./scripts/backup/restore.sh --force
```

Или:

```bash
docker compose -f docker-compose.prod.yml exec -T web \
  python manage.py restore_db --force
```

`restore_db` без `--force` откажется писать в непустую схему `public`, затем выставит `django.contrib.sites` `Site` (`SITE_ID=1`) из `SITE_URL`.

Если setup уже прогнан со старым именем — смена домена без ротации ключей:

```bash
./scripts/apply-domain.sh \
  --domain shiftedstuff.space \
  --site-url https://shiftedstuff.space \
  --editor-domain editor.shiftedstuff.space \
  --redirect-from shiftedstuff.ru,www.shiftedstuff.ru \
  --redirect-from-editor editor.shiftedstuff.ru
./deploy.sh
```

---

## TLS

HSTS на старом сайте заставляет браузеры ходить на старый hostname только по HTTPS. Для редиректа на новом VPS нужен **валидный сертификат** на эти имена.

Предпочтительно **один** сертификат Let's Encrypt (`SSL_CERT_NAME`) со всеми SAN:

- Новые: `shiftedstuff.space`, `www.shiftedstuff.space`, `editor.shiftedstuff.space`
- Старые (сценарий B): `shiftedstuff.ru`, `www.shiftedstuff.ru`, `editor.shiftedstuff.ru`

Варианты:

1. HTTP-01 после того, как `.space` смотрит на новый VPS. Установить certbot; **первый** сертификат, пока Docker nginx ещё не поднят — `--standalone` (порт 80 свободен):

```bash
sudo apt-get update
sudo apt-get install -y certbot
dig +short shiftedstuff.space A
sudo systemctl stop nginx apache2 ihttpd
sudo ss -tlnp | grep ':80 '
sudo certbot certonly --standalone \
  -d shiftedstuff.space -d www.shiftedstuff.space -d editor.shiftedstuff.space
ls /etc/letsencrypt/live/shiftedstuff.space/
```

2. Скопировать `/etc/letsencrypt` со старого хоста только для **старых** имён; для **новых** всё равно выпустить (или расширить) сертификат.
3. DNS-01, если зона уже у регистратора.

На cutover — расширить сертификат или второй выпуск с `.ru` / `.online` (см. cutover в EN-доке).

---

## Репетиция

На новом VPS в `/etc/hosts` пропишите **новые** имена → новый IP:

- [ ] Главная, пост, картинка из media
- [ ] Sitemap / canonical = `SITE_URL`
- [ ] Логин в editor (cookies `.новыйдомен`; после смены hostname — повторный вход)
- [ ] `ENV_FILE=secrets.env ./scripts/check-env.sh production`
- [ ] `./scripts/backup/run-backup.sh` (или `restore.sh --dry-run`)

Проверка 301 со старых имён — только если они в DNS/hosts **и** есть сертификат.

Откат до cutover: публичные A-записи остаются на старом IP.

---

## Cutover

1. Заморозить запись на старом VPS (`docker compose -f docker-compose.prod.yml stop web`).
2. Финальный `backup_db`; копирование; `restore_db --force` на новом; сверка чисел.
3. A/AAAA новой зоны (apex, `www`, `editor`) → новый IP.
4. A/AAAA старой зоны (apex, `www`, `editor`) → **тот же** новый IP (редиректы на новом nginx, не на старом VPS).
5. Сертификаты; `./scripts/generate-nginx-conf.sh` и `./deploy.sh`.
6. Проверка:

```bash
curl -sI https://www.shiftedstuff.ru/ | head
# 301 Location: https://shiftedstuff.space/
curl -sI https://www.shiftedstuff.ru/some/path?x=1 | head
# 301 Location: https://shiftedstuff.space/some/path?x=1
curl -sI https://editor.shiftedstuff.ru/login | head
# 301 Location: https://editor.shiftedstuff.space/login
curl -sI https://shiftedstuff.space/ | head
# 200
```

7. Обновить GitHub `VPS_HOST` (и SSH-ключ, если новый пользователь). Doppler: `SITE_URL`, хосты, `REDIRECT_FROM_*`. См. [../en/maintainer.md](../en/maintainer.md).
8. Добавить новый хост в Яндекс/Google Search Console; смена адреса, если есть.
9. Обновить ссылки в профилях (Telegram, Хабр, GitHub).
10. Через 24–48 ч без ошибок: **выключить старый VPS**. Снимок у провайдера на несколько дней — по возможности.

Почту можно оставить на старом ящике/SMTP, пока не заведёте ящики на новом домене. Затем Site settings + `EMAIL_HOST_PASSWORD`.

---

## Мягкое затухание (сценарий B)

Старый **домен** — только DNS и сертификаты на новом VPS. Старый **VPS** уже выключен.

- Держите `REDIRECT_FROM_*`, пока жива старая зона.
- **01.12.2026** (этот перенос): не продлевать `shiftedstuff.ru`.
- **~07.01.2027**: убрать redirect-переменные, `./scripts/apply-domain.sh` без `--redirect-from`, сертификат только для `.space`, удалить записи `.ru`.
- **21.01.2027**: домен истекает.

---

## Cron на новом VPS

```bash
0 3 * * * cd /opt/shiftedblog && ./scripts/backup/run-backup.sh
```

Недельный отчёт: [../security-runbook.md](../security-runbook.md).

---

## См. также

- [production-deploy.md](production-deploy.md)
- [configuration.md](configuration.md)
- [../en/maintainer.md](../en/maintainer.md)
