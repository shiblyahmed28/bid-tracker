# Multi-stage: the production image ships the built static bundle only,
# never node_modules or the Vite dev server.
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
# Relative path: the reverse proxy (this same Caddy) serves the API
# same-origin under /api/v1, whether the site is currently reachable over
# plain HTTP (:8090, pre-TLS verification) or HTTPS (:443) — so the built
# bundle works unmodified in both docs/DEPLOY.md rollout steps.
ENV VITE_API_BASE_URL=/api/v1
RUN npm run build

FROM caddy:2-alpine

COPY --from=frontend-build /app/dist /srv/www
COPY web/Caddyfile.http /etc/caddy/Caddyfile.http
COPY web/Caddyfile.https /etc/caddy/Caddyfile.https
COPY web/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN chmod +x /usr/local/bin/docker-entrypoint.sh \
    && addgroup -g 1000 caddy_run \
    && adduser -D -u 1000 -G caddy_run caddy_run \
    && mkdir -p /data /config \
    && chown -R caddy_run:caddy_run /data /config /srv/www /etc/caddy

USER caddy_run

EXPOSE 8080

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
