#!/usr/bin/env bash
# /opt/url-shortener/deploy/reload-nginx-on-renew.sh
set -euo pipefail

# Cron runs with PATH=/usr/bin:/bin. docker is often elsewhere
# (/usr/local/bin, /snap/bin). Pin a known-good PATH.
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

cd "$(dirname "$0")/.."          # /opt/url-shortener

# The certbot deploy hook writes this marker after a successful renewal.
docker compose exec -T certbot \
    test -f /var/www/certbot/.reload-requested 2>/dev/null || exit 0

echo "[$(date -Is)] reload marker found, validating nginx config"

# Validate *before* reloading. If nginx -t fails, keep the marker so the
# next tick retries — never silently drop the request.
if ! docker compose exec -T nginx nginx -t; then
    echo "[$(date -Is)] nginx -t failed, keeping marker for retry" >&2
    exit 1
fi

docker compose exec -T nginx nginx -s reload
docker compose exec -T certbot rm -f /var/www/certbot/.reload-requested
echo "[$(date -Is)] nginx reloaded"