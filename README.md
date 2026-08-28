# Spectrum Bid Tracker

Internal bid-tracking dashboard for Spectrum Engineering Consortium (Pvt.) Ltd. It mirrors a
private Google Sheet of tender bids into PostgreSQL and presents it as a login-gated dashboard —
executive view, a faithful "Classic" view, the full bid register, notifications, and admin screens
for sync history, the audit log and user management.

See `CLAUDE.md` for the full spec — data contract, domain model, sync algorithm and design rules.
`claude-code-prompts.md` has the phase-by-phase build plan this app was built against.

**Ubuntu only.** These instructions assume Ubuntu with Docker Engine and Docker Compose installed.

---

## Quick start

```bash
git clone <repo-url> spectrum-bid-tracker
cd spectrum-bid-tracker
cp .env.example .env
# edit .env — at minimum you need real values for GOOGLE_SHEET_ID and
# GOOGLE_SERVICE_ACCOUNT_FILE if you want the sync to work against a real
# sheet. Everything else has a working default for local dev.
docker compose up --build
```

Then, in a second terminal, run migrations and create your first account:

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

`createsuperuser` only asks for an email and password — the custom user model requires the email
to end in `@spectrum-bd.com` (or whatever `ALLOWED_EMAIL_DOMAIN` is set to) and automatically makes
the account an admin. Sign in at http://localhost:5173 with that email and password.

**Faster local-dev shortcut** — three ready-made accounts with known passwords, instead of creating
your own:

```bash
docker compose exec backend python manage.py seed_users
```

Creates `admin@spectrum-bd.com` / `AdminPass123!` (admin), `editor@spectrum-bd.com` /
`EditorPass123!` (editor) and `viewer@spectrum-bd.com` / `ViewerPass123!` (viewer). Fine for local
development; change or remove these before anything resembling production use.

### Services

| Service  | URL / port                   | Notes |
|----------|-------------------------------|-------|
| frontend | http://localhost:5173         | Vite dev server, hot reload |
| backend  | http://localhost:8000         | Django dev server |
| admin    | http://localhost:8000/admin/  | Django admin |
| worker   | —                              | Celery worker — runs the sync task and sends emails |
| beat     | —                              | Celery Beat — the 8-hourly sync and the 08:00 deadline-alert schedule |
| db       | localhost:5432                 | PostgreSQL 16 |
| redis    | localhost:6379                 | Redis 7 — Celery broker/result backend |

Stop everything with `docker compose down`. Data persists in the named `postgres_data` volume —
`docker compose down -v` also wipes the database.

---

## Seeing real data without the Google Sheet

If you don't have (or don't want to use) real Google Sheets credentials yet, generate a synthetic
demo dataset instead — it never touches the sheet:

```bash
docker compose exec backend python manage.py seed_demo_data
```

Creates ~40 realistic app-native bids (mixed stages, results, teams, some with future submission
dates so the dashboard's submission runway has something to show — the real sheet never has any).
Re-running it replaces the previous batch rather than piling up duplicates. Pass `--count 100` for
a bigger dataset.

---

## Syncing against the real Google Sheet

Three ways to trigger a sync:

1. **Automatic** — the `beat` service runs it every 8 hours (00:00, 08:00, 16:00 Asia/Dhaka).
2. **From the UI** — the "Fetch data" button in the top bar (admin only), or the Sync history page
   (`/admin/sync`), which also shows fetch history and quarantined rows.
3. **From the CLI**:
   ```bash
   docker compose exec backend python manage.py sync_sheet
   docker compose exec backend python manage.py sync_sheet --dry-run   # writes nothing
   ```

The sync needs `GOOGLE_SHEET_ID` and a real `GOOGLE_SERVICE_ACCOUNT_FILE` (a service-account JSON
key, shared with edit access on the `bids` tab — it only ever writes the `uid` column, batched, per
CLAUDE.md §6). Mount the key at `backend/secrets/service-account.json` — that path is gitignored.

---

## Email

Change-notification digests, new-bid alerts and 7-day deadline alerts all go through email. Until
you configure real credentials, `EMAIL_HOST_USER` is blank and the backend automatically falls back
to Django's **console** email backend — every email that would have been sent is printed to the
`backend`/`worker` container logs instead:

```bash
docker compose logs -f worker
```

To send real email, fill in `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` in `.env` (a Gmail address
with 2FA on and a 16-character App Password — not your normal password) and restart the containers.
No code change is needed; `EMAIL_BACKEND` switches to real SMTP automatically once those two values
are non-empty.

---

## Secrets

- `.env` — real environment values. Gitignored. Copy from `.env.example` and fill in.
- `backend/secrets/service-account.json` — Google service account key for Sheets access. Gitignored.
- Gmail App Password goes in `.env` as `EMAIL_HOST_PASSWORD`. Never commit either file, and never
  paste their contents into chat, a commit or a log line.

---

## Running tests

```bash
docker compose exec backend pytest
```

Frontend type-check and build:

```bash
docker compose exec frontend npx tsc -b
docker compose exec frontend npm run build
```

---

## Troubleshooting

- **A container writes files owned by `root` into your working copy** (e.g. after running a
  one-off `manage.py` command as a different user) — run it as your own user instead:
  `docker compose exec -u $(id -u):$(id -g) backend <command>`.
- **You added a new Celery task and it never runs** — the `worker` and `beat` containers only load
  task code at startup: `docker compose restart worker beat`.
- **Migrations fail with "relation already exists" or similar on a fresh clone** — make sure `db`
  is healthy before migrating (`docker compose ps` should show it as `healthy`); Compose's
  `depends_on: condition: service_healthy` already waits for this for the `backend`/`worker`/`beat`
  services, but a manually-run `manage.py` command from a second terminal doesn't get that wait.
- **`createsuperuser` rejects your email** — accounts are restricted to `@spectrum-bd.com` (or
  whatever `ALLOWED_EMAIL_DOMAIN` is set to in `.env`) by design (CLAUDE.md §2 non-negotiable #9).
- **The sync fails with a Google auth error** — check `GOOGLE_SERVICE_ACCOUNT_FILE` actually points
  to a mounted, readable JSON key, and that the service account's email has been shared on the
  sheet with edit access to the `bids` tab.
- **No emails arrive even though `EMAIL_HOST_USER` is set** — Gmail requires 2-Step Verification
  turned on before it will issue an App Password; a normal account password will be rejected by
  SMTP even with correct settings otherwise.
- **The frontend can't reach the API** — check `VITE_API_BASE_URL` in `.env` matches where the
  `backend` container is actually reachable from your browser (default `http://localhost:8000/api/v1`
  works for a local Docker Compose setup; it will need to change for anything else).

---

## Development notes

- Backend and frontend source are bind-mounted into their containers — edits on the host are
  picked up by each dev server's autoreload, no rebuild needed for ordinary code changes.
- Production deployment (a real VM, alongside other existing services) is a later phase — see
  `claude-code-prompts.md` Phase 14. Nothing in this repo currently assumes a production
  environment beyond what's described above.
