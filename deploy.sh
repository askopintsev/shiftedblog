#!/bin/bash

# Deployment script for shiftedblog
set -e

echo "Starting deployment..."

# Pull latest changes
git pull origin master

# Ensure writable bind-mount dirs exist before containers start
mkdir -p logs backups static media static_blog
chown -R 1000:1000 logs backups static media 2>/dev/null || chmod -R a+rwX logs backups static media

# Stop existing containers
docker compose -f docker-compose.prod.yml down

# Free disk before build (small VPS fills up with old images/build cache)
docker builder prune -af || true
docker image prune -af || true

# Build new images (layer cache keeps disk use lower than --no-cache)
docker compose -f docker-compose.prod.yml build

# Start containers (entrypoint runs collectstatic, migrate, gunicorn)
docker compose -f docker-compose.prod.yml up -d

# Clean up dangling resources
docker system prune -f

echo "Deployment completed successfully!" 