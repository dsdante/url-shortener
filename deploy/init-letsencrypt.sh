#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then set -a; . ./.env; set +a; fi
: "${DOMAIN:?set DOMAIN in .env}"
: "${LETSENCRYPT_EMAIL:?set LETSENCRYPT_EMAIL in .env}"

CERT_PATH="/etc/letsencrypt/live/$DOMAIN"
STAGING_ARG=""
[ "${CERTBOT_STAGING:-0}" != "0" ] && STAGING_ARG="--staging"

echo "### 1/5 Creating dummy certificate"
docker compose run --rm --entrypoint sh certbot -c "
  mkdir -p '$CERT_PATH' &&
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout '$CERT_PATH/privkey.pem' \
    -out    '$CERT_PATH/fullchain.pem' \
    -subj '/CN=localhost'"

echo "### 2/5 Starting nginx"
docker compose up -d nginx

echo "### 3/5 Deleting dummy certificate"
docker compose run --rm --entrypoint sh certbot -c "
  rm -rf '/etc/letsencrypt/live/$DOMAIN' \
         '/etc/letsencrypt/archive/$DOMAIN' \
         '/etc/letsencrypt/renewal/$DOMAIN.conf'"

echo "### 4/5 Requesting Let's Encrypt certificate"
docker compose run --rm --entrypoint sh certbot -c "
  certbot certonly --webroot -w /var/www/certbot $STAGING_ARG \
    --email '$LETSENCRYPT_EMAIL' -d '$DOMAIN' \
    --rsa-key-size 4096 --agree-tos --no-eff-email --force-renewal"

echo "### 5/5 Reloading nginx"
docker compose exec nginx nginx -s reload

echo "Done. Start the full stack with: docker compose up -d"