#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 yourdomain.com youremail@example.com"
  exit 1
fi

DOMAIN="$1"
EMAIL="$2"

echo "Updating nginx config with domain $DOMAIN"
sed -i "s/server_name example.com/www.${DOMAIN} ${DOMAIN}/g" nginx/nginx.conf || true
sed -i "s/server_name example.com ${DOMAIN}/server_name ${DOMAIN} www.${DOMAIN}/g" nginx/nginx.conf || true

echo "Starting nginx to serve ACME challenge"
docker compose up -d nginx

echo "Requesting certificates for $DOMAIN"
docker compose run --rm certbot certonly --webroot --webroot-path /var/www/certbot -d "$DOMAIN" -m "$EMAIL" --agree-tos --no-eff-email --force-renewal

echo "Reloading nginx"
docker compose exec nginx nginx -s reload || true

echo "Certificates obtained and nginx reloaded."
