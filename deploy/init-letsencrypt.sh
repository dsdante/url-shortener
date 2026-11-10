#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then set -a; . ./.env; set +a; fi
: "${DOMAIN:?set DOMAIN in .env}"
: "${LETSENCRYPT_EMAIL:?set LETSENCRYPT_EMAIL in .env}"

CERT_DIR="/etc/letsencrypt/live/$DOMAIN"
STAGING_ARG=""
[ "${CERTBOT_STAGING:-0}" != "0" ] && STAGING_ARG="--staging"

wait_for_healthy() {
    local name="$1" cid="$2" max="${3:-60}"
    echo -n "  waiting for $name "
    for _ in $(seq 1 "$max"); do
        local s
        s=$(docker inspect "$cid" --format '{{.State.Health.Status}}' 2>/dev/null || echo none)
        if [ "$s" = healthy ]; then echo "healthy"; return 0; fi
        if [ "$s" = unhealthy ]; then echo "UNHEALTHY"; return 1; fi
        echo -n "."
        sleep 1
    done
    echo " TIMEOUT"; return 1
}

echo "### 1/5 Starting app and waiting for health"
docker compose up -d app
wait_for_healthy app url-shortener-app 90 \
  || { echo "ERROR: app did not become healthy. See: docker compose logs app" >&2; exit 1; }

echo "### 2/5 Ensuring a placeholder certificate exists (non-destructive)"
docker compose run --rm --entrypoint sh certbot -c "
  if [ ! -f '$CERT_DIR/fullchain.pem' ] || [ ! -f '$CERT_DIR/privkey.pem' ]; then
    mkdir -p '$CERT_DIR' &&
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
      -keyout '$CERT_DIR/privkey.pem' \
      -out    '$CERT_DIR/fullchain.pem' \
      -subj '/CN=$DOMAIN' &&
    cp '$CERT_DIR/fullchain.pem' '$CERT_DIR/chain.pem'
  fi"

echo "### 3/5 Starting nginx and waiting for health"
docker compose up -d nginx
wait_for_healthy nginx url-shortener-nginx 60 \
  || { echo "ERROR: nginx did not become healthy. See: docker compose logs nginx" >&2; exit 1; }

echo "### 4/5 Verifying port 80 serves the ACME challenge locally"
status=$(curl -s -o /dev/null -w '%{http_code}' \
         "http://127.0.0.1/.well-known/acme-challenge/" || true)
if [ "$status" != "404" ]; then
    echo "ERROR: port 80 not serving ACME challenge path (HTTP $status)." >&2
    echo "Check: sudo ss -ltnp 'sport = :80' | host firewall | cloud security group" >&2
    exit 1
fi

echo "### 5/5 Requesting certificate (replaces the placeholder in place)"
docker compose run --rm --entrypoint sh certbot -c "
  certbot certonly --webroot -w /var/www/certbot $STAGING_ARG \
    --email '$LETSENCRYPT_EMAIL' -d '$DOMAIN' \
    --rsa-key-size 4096 --agree-tos --no-eff-email --force-renewal"

echo "Reloading nginx to pick up the real certificate"
docker compose exec nginx nginx -s reload

echo "Done. Certificate for $DOMAIN is live."