#!/bin/sh
# Runs inside the certbot container after every successful issuance/renewal.
# Restores the ownership and modes nginx-unprivileged (uid/gid 101) needs.
set -eu

chown -R root:101 /etc/letsencrypt/live /etc/letsencrypt/archive
chmod 0755 /etc/letsencrypt/live /etc/letsencrypt/archive
find /etc/letsencrypt/live /etc/letsencrypt/archive -type d -exec chmod 0755 {} +
find /etc/letsencrypt/archive -name '*.pem' -exec chmod 0644 {} +
find /etc/letsencrypt/archive -name 'privkey*.pem' -exec chmod 0640 {} +

echo "certbot-deploy-hook: permissions normalised for nginx (uid 101)" >&2

# Drop a marker in the shared volume so the host-side cron knows to reload
# nginx. Using a marker rather than reloading here keeps certbot free of
# Docker-socket access.
: > /var/www/certbot/.reload-requested