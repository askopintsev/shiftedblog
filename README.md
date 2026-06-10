# ShiftedBlog

A Django-based blog application with advanced security features, two-factor authentication, and modern UI.

## Features

- Custom user model with email authentication
- Two-factor authentication (2FA)
- CKEditor 5 for rich text editing
- PostgreSQL database
- Docker containerization
- CI/CD with GitHub Actions
- Security features (CSRF, XSS protection, rate limiting)
- Responsive design with Bootstrap
- Multi-channel publishing to **Site** and **Telegram** (admin: *Multi-channel publish*), encrypted credentials, `PostLink` audit URLs

## Quick Start

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/shiftedblog.git
cd shiftedblog
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp env.example .env
# Edit .env with your local settings
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Create superuser:
```bash
python manage.py createsuperuser
```

7. Run development server:
```bash
python manage.py runserver
```

**Publishing to Site + Telegram (optional):** set `CREDENTIALS_ENCRYPTION_KEY` (Fernet; see `env.example`). In admin, open **Editor → Posts** and use **Multi-channel publish**, or add Telegram secrets under **Core → Credentials** (JSON: `bot_token`, `channel_name` for a public channel username, optionally `chat_id` for numeric targets). Bootstrap env vars `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHANNEL_NAME` (or `TELEGRAM_CHAT_ID`) are optional if credentials are stored in the database. **Post status “Published”** cannot be chosen on the post edit form; it is set only when Multi-channel publish succeeds.

**Telegram “bot is not a member of the channel”:** the bot must be added in Telegram under **channel → Administrators**, with permission to **post messages** (same for supergroups). The channel usually needs to be **public** if you use `channel_name` / `@username`; **private** channels typically need the numeric **`chat_id`**.

### Linting (Ruff)

The project uses [Ruff](https://docs.astral.sh/ruff/) for formatting and linting. Install dev dependencies and run:

```bash
pip install -e ".[dev]"
ruff format blog core editor sender shiftedblog team manage.py templates
ruff check blog core editor sender shiftedblog team manage.py templates --fix
```

Or in Docker (run as host user so ruff can write to mounted files; `HOME` and `RUFF_CACHE_DIR` set so pip and ruff can write): `docker compose run --no-deps --user "$(id -u):$(id -g)" -e HOME=/tmp/ruff-home -e RUFF_CACHE_DIR=/tmp/ruff-home/.ruff_cache web sh -c 'pip install ruff && python -m ruff format . && python -m ruff check . --fix'`

### Type checking (Pyright)

The project uses [Pyright](https://microsoft.github.io/pyright/) for static type checking. Run with the project venv active so Django and other deps resolve:

```bash
pip install -e ".[dev]"
pyright blog core editor sender shiftedblog team manage.py
```

Or with uv: `uv sync && uv run pyright blog core editor sender shiftedblog team manage.py`. Config lives in `pyproject.toml` under `[tool.pyright]` (Python 3.13, `basic` mode, migrations excluded).

### Docker Development

1. Build and start containers:
```bash
docker-compose up --build
```

For local development, add `HOST_UID` and `HOST_GID` to `.env` with the output of `id -u` and `id -g` so the `web` container can write to bind-mounted app directories (for example `makemigrations`). If omitted, compose defaults to `1000:1000`. Compose also sets `SHIFTED_BLOG_LOG_DIR=/tmp/shiftedblog_logs` so auth/security log files are writable inside the container.

2. Run migrations:
```bash
docker-compose exec web python manage.py migrate
```

3. Create superuser:
```bash
docker-compose exec web python manage.py createsuperuser
```

## Production Deployment

### Prerequisites

- VPS with Docker and Docker Compose installed
- Domain name pointing to your VPS
- SSL certificate (Let's Encrypt recommended)

### SSH key access (no passwords)

Use two separate keys: one for GitHub Actions to SSH into the VPS, and one for the VPS to `git pull` from GitHub.

**1. CI deploy key (GitHub Actions → VPS)**

On your machine:

```bash
./scripts/ssh/generate-vps-deploy-key.sh
```

- Copy the **public** key to the server (`scripts/ssh/install-vps-authorized-key.sh` on the VPS, or append to `~/.ssh/authorized_keys`).
- Add the **private** key to GitHub repo secret `VPS_SSH_KEY`.
- Set secrets `VPS_HOST`, `VPS_USERNAME`, `VPS_PORT` (usually `22`).

**2. Git deploy key (VPS → GitHub, read-only)**

On your machine:

```bash
./scripts/ssh/generate-git-deploy-key.sh
```

- GitHub repo → **Settings → Deploy keys** → add the **public** key (read-only).
- Copy private + public key to the VPS as `~/.ssh/shiftedblog_git_deploy` (+ `.pub`), then on the server:

```bash
chmod 600 ~/.ssh/shiftedblog_git_deploy
./scripts/ssh/install-server-git-access.sh
```

**3. Optional: disable password SSH** after keys work — see `scripts/ssh/sshd-disable-password-auth.snippet`.

**4. Set a random admin URL** in Doppler (`ADMIN_URL`) — see `scripts/security/generate-admin-url.sh`.

Generated keys are stored in `scripts/ssh/keys/` (gitignored). Never commit private keys.

### Server Setup

1. Connect to your VPS (your own SSH key or password for initial setup):

```bash
ssh user@your-vps-ip
```

2. Create project directory:

```bash
sudo mkdir -p /opt/shiftedblog
sudo chown $USER:$USER /opt/shiftedblog
cd /opt/shiftedblog
```

3. Clone the repository (after [git deploy key](#ssh-key-access-no-passwords) is installed):

```bash
git clone git@github.com-shiftedblog:askopintsev/shiftedblog.git .
```

Or clone via HTTPS for first-time setup only, then switch with `install-server-git-access.sh`.

4. Set up environment variables:
```bash
cp env.example .env
nano .env  # Edit with your production settings
```

5. Create SSL directory:
```bash
mkdir -p nginx/ssl
```

6. Deploy:
```bash
chmod +x deploy.sh
./deploy.sh
```

### GitHub Actions Setup

1. Add repository secrets in GitHub (see [SSH key access](#ssh-key-access-no-passwords)):
   - `VPS_HOST`: Your VPS IP address
   - `VPS_USERNAME`: SSH username
   - `VPS_SSH_KEY`: Private SSH key from `generate-vps-deploy-key.sh`
   - `VPS_PORT`: SSH port (usually 22)
   - `DOPPLER_TOKEN`: Doppler service token for production secrets

2. Push to main branch to trigger deployment:
```bash
git push origin master
```

## Environment Variables

### Required Variables

- `SECRET_KEY`: Django secret key
- `DEBUG`: Set to False in production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DB_NAME`: PostgreSQL database name
- `DB_USER`: PostgreSQL username
- `DB_PASS`: PostgreSQL password
- `EMAIL_HOST`: SMTP server
- `EMAIL_HOST_USER`: Email username
- `EMAIL_HOST_PASSWORD`: Email password

### Optional Variables

- `ADMIN_NAME`: Admin contact name
- `ADMIN_EMAIL`: Admin contact email
- `SECURE_SSL_REDIRECT`: Enable HTTPS redirect
- `SECURE_HSTS_SECONDS`: HSTS duration

## Security Features

- Two-factor authentication (django-two-factor-auth)
- Brute-force lockout (django-axes) with admin unlock and lockout emails
- Rate limiting (nginx + django-ratelimit)
- Session rotation on login and configurable session idle timeout
- CSRF / XSS protection and secure headers (HSTS, CSP)
- Secrets rotation reminders in admin
- CI static analysis (`bandit`) and dependency audit (`pip-audit`)

Operations guide: [docs/security-runbook.md](docs/security-runbook.md)

Production admin path: set a random `ADMIN_URL` in Doppler (`./scripts/security/generate-admin-url.sh`).

## File Structure

```
shiftedblog/
├── blog/                    # Public-facing blog URLs (list, detail, feed, search)
├── editor/                  # Content models & admin (posts, categories, series)
├── shiftedblog/            # Django project settings
├── templates/              # HTML templates
├── static/                 # Static files
├── nginx/                  # Nginx configuration
├── docker-compose.yml      # Development Docker setup
├── docker-compose.prod.yml # Production Docker setup
├── Dockerfile              # Docker image definition
├── requirements.txt        # Python dependencies
├── deploy.sh              # Deployment script
└── .github/workflows/     # GitHub Actions
```

## Maintenance

### Backup Database
```bash
docker-compose -f docker-compose.prod.yml exec db pg_dump -U $DB_USER $DB_NAME > backup.sql
```

### Update Application
```bash
git pull origin main
./deploy.sh
```

### View Logs
```bash
docker-compose -f docker-compose.prod.yml logs -f web
```

## License

This project is licensed under the MIT License.