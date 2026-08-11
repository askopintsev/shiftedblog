# Локальный запуск

English: [../en/local-deploy.md](../en/local-deploy.md)

## Рекомендуется: Docker + мастер

Нужны Docker Engine и Docker Compose plugin.

```bash
git clone https://github.com/askopintsev/shiftedblog.git
cd shiftedblog
./scripts/setup.sh
# выберите 1) local
```

- Сайт: http://localhost:8888/
- Админка: http://localhost:8888/`ADMIN_URL`/ (по умолчанию `mellon`)

Полезные команды:

```bash
docker compose logs -f web
docker compose exec web python manage.py createsuperuser
docker compose down
```

Мастер выставляет `HOST_UID` / `HOST_GID`, чтобы запись в смонтированный код работала.

## Продвинутый вариант: venv

Нужны доступные с хоста PostgreSQL и Redis.

```bash
cp env.example .env
# DB_HOST=localhost, REDIS_URL=redis://localhost:6379/1, DEBUG=True, …
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Editor SPA в dev: отдельно `npm install && npm run dev` в `editor-ui/`.

## Проверка env

```bash
./scripts/check-env.sh local
```
