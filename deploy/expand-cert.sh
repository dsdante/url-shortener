#!/usr/bin/env bash
# Adds $UI_DOMAIN to the existing $DOMAIN certificate via `certbot --expand`.
# Idempotent: safe to re-run.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then set -a; . ./.env; set +a; fi
: "${DOMAIN:?set DOMAIN in .env}"
: "${UI_DOMAIN:?set UI_DOMAIN in .env}"
: "${LETSENCRYPT_EMAIL:?set LETSENCRYPT_EMAIL in .env}"

echo "### Ensuring nginx is up so ACME challenges can be served"
docker compose up -d app ui-build
docker compose up -d nginx
until [ "$(docker inspect url-shortener-nginx --format '{{.State.Health.Status}}')" = healthy ]; do
    sleep 1
done

echo "### Expanding certificate to cover $DOMAIN and $UI_DOMAIN"
docker compose run --rm --no-deps -T --entrypoint certbot certbot certonly \
    --webroot -w /var/www/certbot \
    --cert-name "$DOMAIN" \
    --expand --force-renewal \
    -d "$DOMAIN" -d "$UI_DOMAIN" \
    --email "$LETSENCRYPT_EMAIL" \
    --agree-tos --no-eff-email

echo "### Normalising permissions via the deploy hook"
docker compose run --rm --no-deps --entrypoint sh certbot \
    /etc/letsencrypt/renewal-hooks/deploy/01-nginx-unprivileged.sh

echo "### Reloading nginx"
docker compose exec nginx nginx -t && docker compose exec nginx nginx -s reload

echo "Done. Certificate now covers $DOMAIN and $UI_DOMAIN."