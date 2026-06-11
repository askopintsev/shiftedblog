#!/bin/bash

# Deployment script for shiftedblog
set -e

echo "Starting deployment..."

# Pull latest changes
git pull origin master

# Ensure writable log/backups dirs exist before bind mounts
mkdir -p logs backups
chown -R 1000:1000 logs backups 2>/dev/null || chmod -R a+rwX logs backups

# Stop existing containers
docker compose -f docker-compose.prod.yml down

# Free disk before build (small VPS fills up with old images/build cache)
docker builder prune -af || true
docker image prune -af || true

# Build new images (layer cache keeps disk use lower than --no-cache)
docker compose -f docker-compose.prod.yml build

# Start containers
docker compose -f docker-compose.prod.yml up -d

# Run migrations
docker compose -f docker-compose.prod.yml exec web python manage.py migrate

# Collect static files
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Clean up dangling resources
docker system prune -f

echo "Deployment completed successfully!" 