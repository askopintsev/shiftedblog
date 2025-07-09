#!/bin/bash

# Deployment script for shiftedblog
set -e

echo "Starting deployment..."

# Pull latest changes
git pull origin master

# Stop existing containers
docker compose -f docker-compose.prod.yml down

# Build new images
docker compose -f docker-compose.prod.yml build --no-cache

# Start containers
docker compose -f docker-compose.prod.yml up -d

# Run migrations
docker compose -f docker-compose.prod.yml exec web python manage.py migrate

# Collect static files
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Clean up old images
docker system prune -f

echo "Deployment completed successfully!" 