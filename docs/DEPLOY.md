# Deployment — production CentOS 7 VM

Target: `36.255.69.114`, Docker 20.10.21, SELinux disabled, no firewalld, **no git installed**.

⚠️ **This VM already runs a production GRP system: nginx on port 80, Tomcat on port 8080, and a
system PostgreSQL 11 on port 5432.** None of these belong to this project and none of them may be
stopped, reconfigured, or otherwise touched. This stack only ever uses port **443**, plus a
temporary port **8090** during the verification step below. All of this project's containers bind
to their own internal Docker network — none of them collide with the existing services by name or
port, but double-check `docker ps` on the host before your first deploy regardless.

There is no domain name for this app and none can be obtained. Everything below is built around
the IP address `36.255.69.114` and a Let's Encrypt **IP address certificate** (see
`web/Caddyfile.https` for why that requires the `shortlived` ACME profile and TLS-ALPN-01).

---

## Because there's no git on the VM: deploying by tar + scp

From your dev machine, at the repo root:

```bash
tar --exclude='.git' \
    --exclude='node_modules' \
    --exclude='frontend/dist' \
    --exclude='**/__pycache__' \
    --exclude='.env' --exclude='.env.prod' \
    --exclude='backend/secrets' \
    --exclude='backups' \
    -czf spectrum-bid-tracker.tar.gz .

scp spectrum-bid-tracker.tar.gz <user>@36.255.69.114:/opt/
```

On the VM:

```bash
sudo mkdir -p /opt/spectrum-bid-tracker
sudo tar xzf /opt/spectrum-bid-tracker.tar.gz -C /opt/spectrum-bid-tracker
cd /opt/spectrum-bid-tracker
```

The `service-account.json` and `.env.prod` are excluded from the tarball on purpose — they never
leave your machine over a channel that isn't `scp` directly to their final home. Copy those two
files up separately:

```bash
scp backend/secrets/service-account.json <user>@36.255.69.114:/opt/spectrum-bid-tracker/backend/secrets/
scp .env.prod <user>@36.255.69.114:/opt/spectrum-bid-tracker/.env.prod
```

**Updates** work the same way: re-run the tar/scp/extract sequence (it overwrites in place — the
extract does not touch `.env.prod` or `backend/secrets/`, since those were excluded from the
tarball). There's no `git diff` available on the VM to see what changed — review the diff on your
dev machine before packaging.

---

## First-time deploy

1. Ship the code (above), and put `.env.prod` and `backend/secrets/service-account.json` in place.
2. Fill in every placeholder in `.env.prod` — see `.env.prod.example` for what each one is.
   Start with `TLS_ENABLED=0` / `WEB_PUBLISHED_PORT=8090` (Mode 1 below). Every secret here must be
   **different** from the ones in any developer's local `.env` (§2 of `CLAUDE.md`).
3. Build the images:
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod build
   ```
4. Bring up just the database first and run migrations:
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod up -d db redis
   docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm backend python manage.py migrate
   docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm backend python manage.py createsuperuser
   ```
5. Bring up everything else:
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
   docker compose -f docker-compose.prod.yml --env-file .env.prod ps
   ```
   Wait for all services to report `healthy`.
6. Verify Mode 1 (HTTP), then switch to Mode 2 (TLS) — see below. **Do this as two separate
   steps.** Bringing up TLS and the rest of the stack at the same time means that if something
   breaks, you don't know whether it's the app or the certificate — two failure modes at once is
   not debuggable.

---

## Mode 1: HTTP verification (port 8090)

With `.env.prod` set to `TLS_ENABLED=0` and `WEB_PUBLISHED_PORT=8090`:

```bash
curl -i http://36.255.69.114:8090/api/v1/schema/
```

Open `http://36.255.69.114:8090` in a browser and confirm the dashboard loads, you can log in, and
the register/PDF export work. This mode never talks to Let's Encrypt and never touches port 443 —
it exists purely to prove gunicorn, Celery, Postgres, Redis and the reverse proxy are wired
together correctly before adding TLS to the mix.

**Do not leave the app reachable on 8090 in the long term** — it's plaintext HTTP with no session
cookie protection (`SESSION_COOKIE_SECURE`/CSRF-secure/HSTS are all off in this mode, deliberately
— see `backend/config/settings/production.py`). Move to Mode 2 as soon as Mode 1 is confirmed
working.

## Mode 2: switching to TLS (port 443)

1. In `.env.prod`, flip:
   ```ini
   TLS_ENABLED=1
   WEB_PUBLISHED_PORT=443
   ```
   and swap `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` / `FRONTEND_BASE_URL` to their
   `https://36.255.69.114` variants (commented-out in `.env.prod.example` — uncomment those,
   comment out the `:8090` ones).
2. Recreate the `web` and `backend` services (the only ones whose behavior depends on this flag):
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate web backend
   ```
3. Watch the certificate get issued:
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f web
   ```
   Look for `certificate obtained successfully` for `36.255.69.114`. First issuance can take up to
   a minute.
4. Verify:
   ```bash
   curl -i https://36.255.69.114/api/v1/schema/
   openssl s_client -connect 36.255.69.114:443 -servername 36.255.69.114 </dev/null 2>/dev/null | openssl x509 -noout -issuer -enddate
   ```
   The issuer should be Let's Encrypt (`E-number` intermediate), and `notAfter` should be about
   160 hours out (the `shortlived` profile's lifetime — this is expected and not a
   misconfiguration; Caddy renews automatically well before that).
5. Confirm port 8090 is no longer needed and stop exposing it (it stops being published the
   moment `WEB_PUBLISHED_PORT=443` takes effect in step 2 — Compose only ever publishes one host
   port for `web`, per its `ports:` entry in `docker-compose.prod.yml`).

If issuance fails, check that port 443 wasn't already reachable through some other route (nginx or
Tomcat proxying to it, a leftover firewall rule) — TLS-ALPN-01 needs port 443 to actually reach the
`web` container. `firewalld` isn't installed on this VM, so a stuck rule is unlikely to be the
cause, but it's worth ruling out `iptables -L` manually before re-running.

---

## Updates

1. Package and ship the new code (tar/scp, above).
2. Rebuild and recreate only what changed:
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod build
   docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm backend python manage.py migrate
   docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
   ```
   `up -d` only recreates containers whose image or config actually changed — it won't touch
   Caddy's certificate (stored in the `caddy_data` named volume, untouched by a rebuild) or the
   database.
3. Check `docker compose -f docker-compose.prod.yml --env-file .env.prod ps` for `healthy` on everything, and skim
   `docker compose -f docker-compose.prod.yml --env-file .env.prod logs --tail 100 backend worker beat`.

## Email delivery (Gmail SMTP)

`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD` authenticate as one real Gmail account (a 16-character App
Password, §18). Gmail requires the `From:` address to match that account's own address — if
`DEFAULT_FROM_EMAIL` (§18) is on a different domain, Gmail either **rewrites** the visible sender to
the authenticated account or **rejects the send outright**, silently breaking every outbound email
until noticed. A system check (`apps.notifications.checks`) warns loudly on every `manage.py check`/
`runserver`/`migrate` if the two domains don't match — don't ignore that warning.

**To send legitimately as `noreply@spectrum-bd.com` while authenticating as a different Gmail
account** (or vice versa), register the desired `DEFAULT_FROM_EMAIL` address as a verified **"Send
mail as" alias** on the authenticating Gmail account first:

1. Sign in to the Gmail account named by `EMAIL_HOST_USER`.
2. **Settings → See all settings → Accounts and Import → Send mail as → Add another email address.**
3. Enter the alias address (matching `DEFAULT_FROM_EMAIL`'s domain) and follow Gmail's verification
   email — it's sent to that address, so you need inbox access there too.
4. Once verified, Gmail accepts that address in `From:` for mail sent through this account without
   rewriting or rejecting it, and the two settings values are allowed to differ safely.

If you don't control that other domain's inbox (so you can't complete verification), the only safe
fix is to set `DEFAULT_FROM_EMAIL` to an address on `EMAIL_HOST_USER`'s own domain instead.

## Rollback

Docker Compose doesn't version images by itself here, so rollback means re-deploying the previous
tarball:

1. Keep the last known-good tarball around on your dev machine before shipping a new one
   (`spectrum-bid-tracker-YYYYMMDD.tar.gz`).
2. Re-run the deploy sequence (tar/scp/extract) with that older tarball.
3. `docker compose -f docker-compose.prod.yml --env-file .env.prod build && docker compose -f docker-compose.prod.yml --env-file .env.prod up -d`.
4. If the update included a migration you need to reverse: `python manage.py migrate <app>
   <previous_migration_name>` — check `python manage.py showmigrations <app>` first. If it's not
   safely reversible, restore the database backup from just before the update instead (see below).

## Database restore

See `backup.sh`'s header comment for the exact restore command. In short:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod stop backend worker beat
gunzip -c backups/spectrum_bids_YYYYmmdd_HHMMSS.sql.gz | \
  docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
docker compose -f docker-compose.prod.yml --env-file .env.prod start backend worker beat
```

Stop the app services first — otherwise gunicorn/Celery are writing to the database while you're
replaying a dump into it.

### Nightly backups

`backup.sh` runs `pg_dump` inside the `db` container, gzips it into `backups/`, and prunes
anything older than 14 days. Add it to root's crontab on the VM:

```bash
sudo crontab -e
# nightly at 02:00 Asia/Dhaka
0 2 * * * cd /opt/spectrum-bid-tracker && ./backup.sh >> /var/log/spectrum-backup.log 2>&1
```

CentOS 7 ships `crond` enabled by default — confirm with `systemctl status crond` before relying
on this.

---

## Reading logs

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f backend    # gunicorn access/error log
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f worker      # Celery task execution
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f beat        # sync/deadline schedule ticks
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f web         # Caddy — requests, TLS/ACME events
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f certwatch   # daily certificate-expiry check
```

All services log to stdout/stderr with Docker's `json-file` driver, capped at 10MB × 3 files per
service (`docker-compose.prod.yml`'s `x-logging` anchor) — logs rotate on their own, nothing to
clean up manually.

## Verifying certificate renewal

Caddy renews the IP certificate on its own well before its ~160-hour lifetime is up, and logs it
in `docker compose logs web`. As a second, independent check, the `certwatch` service connects to
the live certificate once a day and logs a `WARNING` if fewer than 48 hours remain, or an `ERROR`
if it's already expired or unreadable:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod logs certwatch | tail -20
```

A silent renewal failure means users hit a browser certificate warning with no other symptom —
that's exactly what `certwatch` exists to catch first. If you see a `WARNING` or `ERROR` there,
check `docker compose logs web` for the underlying ACME error before it reaches 0 hours.

This check is intentionally a standalone container, not something bolted onto the Google Sheet
sync pipeline (`apps/sync`) — it's operational monitoring for the deployment, unrelated to the
sync algorithm described in `CLAUDE.md` §9, and keeps working even if the Django app itself is
unhealthy.
