#!/usr/bin/env bash
# Generate a random ADMIN_URL slug for production (Doppler prd).
set -euo pipefail

SLUG="$(openssl rand -hex 8)"

echo "Suggested ADMIN_URL for Doppler (prd config):"
echo "  ADMIN_URL=${SLUG}"
echo ""
echo "After updating Doppler:"
echo "  1. Redeploy the application"
echo "  2. Update your admin bookmark to https://<domain>/${SLUG}/"
echo "  3. nginx login rate limits apply to any /{slug}/login path automatically"
