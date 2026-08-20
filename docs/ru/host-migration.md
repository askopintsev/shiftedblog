# Перенос хоста и домена

English: [../en/host-migration.md](../en/host-migration.md)

Перенос ShiftedBlog на новый VPS и/или публичный hostname. Приложение не привязано к провайдеру: `backup_db` / `restore_db`, `apply-domain.sh`, `REDIRECT_FROM_*` в nginx.

При восстановлении **не** меняйте `SECRET_KEY` и `CREDENTIALS_ENCRYPTION_KEY`. Мажорная версия дампа Postgres должна совпадать с сервером (**17** в `docker-compose.prod.yml`).

## Сценарии

1. **A — тот же hostname, новый VPS** — меняется только IP.
2. **B — новый hostname + мягкое затухание** — новый `SITE_URL`; старые имена отдают HTTPS 301 на **новом** VPS, пока жив старый домен. Старый VPS выключается после cutover.

Пример (B): `https://old.example.com` → `https://new.example.com`, редактор `https://editor.new.example.com`. DNS старого домена указывает на новый VPS до удаления зоны.

`EXTRA_DOMAINS` — тот же сайт на доп. хостах (дубли). Для 301 со старых имён — `REDIRECT_FROM_DOMAINS` / `REDIRECT_FROM_EDITOR_DOMAINS`.

## Инкременты оператора

По порядку. Публичный DNS на новый VPS — только на шаге cutover (кроме **нового** домена для репетиции).

1. Инвентаризация + бэкап вне сервера + снизить TTL старой зоны
2. DNS для **нового** домена (A можно отложить)
3. Новый VPS: SSH-ключи, ОС, файрвол, Docker
4. Установка + restore (без cutover)
5. Репетиция на новом hostname
6. Cutover (старый DNS + расширение сертификата + 301 + CI)
7. Выключить старый VPS через 24–48 ч
8. Календарь затухания старого домена

---

## 1. Инвентаризация (исходный хост)

На **текущем** production-сервере (секреты не коммитить):

```bash
pwd
hostname -I
docker --version
docker compose version
ls /etc/letsencrypt/live/ 2>/dev/null || true
crontab -l
grep -E '^(DOMAIN|SITE_URL|EDITOR_|SSL_CERT_NAME|EXTRA_DOMAINS|REDIRECT_FROM|EMAIL_HOST)=' secrets.env
```

- [ ] Публичный IPv4 / IPv6, путь приложения, Docker
- [ ] DNS, почта, cron, сертификаты, CI, вебмастер

```bash
cd /opt/shiftedblog
docker compose -f docker-compose.prod.yml exec -T web python manage.py backup_db
```

Скопируйте `backups/*.sql.gz`, `backups/media_*.tar.gz`, `secrets.env` вне обоих серверов. TTL старой зоны — 300 с, если можно.

---

## 2. DNS нового домена

В панели **регистратора / DNS** для нового домена:

- [ ] NS корректны
- [ ] Записи `@`, `www`, `editor` (или wildcard `*`) — A/AAAA могут указывать на парковку, пока нет VPS
- [ ] **Старую** зону не менять до cutover

---

## 3. Bootstrap нового VPS

Подставьте `NEW_VPS_IP` и пользователя `deploy`.

### SSH-ключи

Ключ **оператора** на ноутбуке (не ключ GitHub Actions — он для CI позже):

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

### Пакеты, ufw, Docker

Образы VPS иногда держат **хостовый** nginx на :80 — освободите порт для Docker.

```bash
sudo systemctl stop nginx apache2 2>/dev/null || true
sudo systemctl disable nginx apache2 2>/dev/null || true
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y ca-certificates curl ufw fail2ban certbot
sudo ufw --force reset && sudo ufw default deny incoming && sudo ufw default allow outgoing
sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw --force enable
```

[Docker Engine + Compose](https://docs.docker.com/engine/install/ubuntu/), затем `sudo usermod -aG docker deploy` и перелогин.

---

## 4. Установка + restore

Не запускайте `setup.sh` при restore — сменит `ADMIN_URL`. Скопируйте старый `secrets.env` и `apply-domain.sh`.

```bash
sudo mkdir -p /opt/shiftedblog/backups
sudo chown deploy:deploy /opt/shiftedblog
scp ... deploy@NEW_VPS_IP:/opt/shiftedblog/backups/
scp old-secrets.env deploy@NEW_VPS_IP:/opt/shiftedblog/secrets.env
```

На VPS:

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
docker compose -f docker-compose.prod.yml up -d db redis web
./scripts/backup/restore.sh --force
```

В `--redirect-from*` только имена, которые **резолвятся** при выпуске сертификата.

---

## 5. TLS и репетиция

Новый домен → A на `NEW_VPS_IP`. Порт 80 свободен:

```bash
sudo systemctl stop nginx 2>/dev/null || true
docker compose -f docker-compose.prod.yml stop nginx
sudo certbot certonly --standalone \
  -d new.example.com -d www.new.example.com -d editor.new.example.com
docker compose -f docker-compose.prod.yml up -d nginx
./deploy.sh
```

---

## 6. Cutover

1. Заморозить запись на старом VPS.
2. Финальный бэкап и при необходимости `restore_db --force`.
3. Старая зона A/AAAA → **NEW_VPS_IP**.
4. Расширить сертификат (только резолвящиеся имена):

```bash
sudo certbot certonly --standalone --cert-name new.example.com --expand \
  -d new.example.com -d www.new.example.com -d editor.new.example.com \
  -d old.example.com -d www.old.example.com -d editor.old.example.com
```

5. `./deploy.sh`, проверить 301 и 200.
6. CI / secret manager — [maintainer.md](../en/maintainer.md).
7. Через 24–48 ч выключить старый VPS.

---

## 7. Мягкое затухание (B)

- Старый домен — только DNS + сертификаты на новом VPS.
- Напоминание **до** истечения: не продлевать, если хватает 301.
- **~2 недели до expiry**: убрать `REDIRECT_FROM_*`, сертификат только для новых имён, удалить DNS старого домена.

---

## Cron

```bash
0 3 * * * cd /opt/shiftedblog && ./scripts/backup/run-backup.sh
```

---

## См. также

- [Онлайн запуск (на сервере)](production-deploy.md)
- [configuration.md](configuration.md)
- [maintainer.md](../en/maintainer.md)
