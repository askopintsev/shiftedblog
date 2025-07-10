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

### Docker Development

1. Build and start containers:
```bash
docker-compose up --build
```

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

### Server Setup

1. Connect to your VPS:
```bash
ssh user@your-vps-ip
```

2. Create project directory:
```bash
sudo mkdir -p /opt/shiftedblog
sudo chown $USER:$USER /opt/shiftedblog
cd /opt/shiftedblog
```

3. Clone the repository:
```bash
git clone https://github.com/yourusername/shiftedblog.git .
```

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

1. Add repository secrets in GitHub:
   - `VPS_HOST`: Your VPS IP address
   - `VPS_USERNAME`: SSH username
   - `VPS_SSH_KEY`: Private SSH key
   - `VPS_PORT`: SSH port (usually 22)

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

- Two-factor authentication
- Rate limiting with django-axes
- CSRF protection
- XSS protection
- Secure headers
- Password validation
- Session security

## File Structure

```
shiftedblog/
├── blog/                    # Main Django app
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