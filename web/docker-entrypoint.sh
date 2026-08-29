#!/bin/sh
# Picks the HTTP-only or TLS Caddyfile based on TLS_ENABLED, so the same
# image serves both rollout steps in docs/DEPLOY.md without a rebuild.
set -e

if [ "${TLS_ENABLED}" = "1" ]; then
    echo "docker-entrypoint: TLS_ENABLED=1 — running Caddyfile.https (Let's Encrypt IP cert for ${SITE_ADDRESS})"
    exec caddy run --config /etc/caddy/Caddyfile.https --adapter caddyfile
else
    echo "docker-entrypoint: TLS_ENABLED not set to 1 — running Caddyfile.http (plain HTTP verification mode)"
    exec caddy run --config /etc/caddy/Caddyfile.http --adapter caddyfile
fi
