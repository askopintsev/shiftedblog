#!/usr/bin/env bash
# Generate a random ADMIN_URL slug for production.
set -euo pipefail

SLUG="$(openssl rand -hex 8)"

echo "Suggested ADMIN_URL for your secrets file (secrets.env / secret manager):"
echo "  ADMIN_URL=${SLUG}"
echo ""
echo "After updating secrets:"
echo "  1. Redeploy the application"
echo "  2. Update your admin bookmark to https://<domain>/${SLUG}/"
echo "  3. nginx login rate limits apply to any /{slug}/login path automatically"
