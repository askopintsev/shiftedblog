# Local deploy

Русский: [../ru/local-deploy.md](../ru/local-deploy.md)

## Recommended: Docker wizard

Prerequisites: Docker Engine and Docker Compose plugin.

```bash
git clone https://github.com/askopintsev/shiftedblog.git
cd shiftedblog
./scripts/setup.sh
# choose 1) local
```

- Site: http://localhost:8888/
- Admin: http://localhost:8888/`ADMIN_URL`/ (default `mellon`)

Useful commands:

```bash
docker compose logs -f web
docker compose exec web python manage.py createsuperuser
docker compose down
```

`HOST_UID` / `HOST_GID` are set by the wizard so bind-mounted code stays writable.

## Advanced: virtualenv (no Docker app container)

You still need PostgreSQL and Redis reachable from the host.

```bash
cp env.example .env
# edit DB_HOST=localhost, REDIS_URL=redis://localhost:6379/1, DEBUG=True, …
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

For the editor SPA in development, run `editor-ui` with Vite separately (see `editor-ui/README` if present, or `npm install && npm run dev` in `editor-ui/`).

## Validate env

```bash
./scripts/check-env.sh local
```
