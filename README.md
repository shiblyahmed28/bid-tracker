# Spectrum Bid Tracker

Internal bid-tracking dashboard for Spectrum Engineering Consortium (Pvt.) Ltd.
See `CLAUDE.md` for the full spec — data contract, domain model, sync algorithm and design rules.

**Ubuntu only.** These instructions assume Ubuntu with Docker Engine, Docker Compose and Node 20
installed (see `claude-code-prompts.md` Part 0 for first-time machine setup).

## Running the app

```bash
cp .env.example .env      # already done for local dev; edit values as needed
docker compose up --build
```

Services:

| Service  | URL / port              | Notes |
|----------|--------------------------|-------|
| frontend | http://localhost:5173    | Vite dev server, hot reload |
| backend  | http://localhost:8000    | Django dev server |
| admin    | http://localhost:8000/admin | Django admin |
| db       | localhost:5432           | PostgreSQL 16 |
| redis    | localhost:6379           | Redis 7 |
| worker   | —                        | Celery worker, logs to stdout |

Stop with `docker compose down`. Data persists in the named `postgres_data` volume.

## Secrets

- `.env` — real environment values. Gitignored. Copy from `.env.example` and fill in.
- `backend/secrets/service-account.json` — Google service account key for Sheets access. Gitignored.
- Gmail App Password goes in `.env` as `EMAIL_HOST_PASSWORD`. Never commit either file.

## Project state

This is a phased build — see `claude-code-prompts.md` for the phase list. Phase 1 (this phase) is
scaffolding only: no models, no auth, no sync logic yet. Do not run `manage.py migrate` until
Phase 2 sets `AUTH_USER_MODEL` — migrating now would lock in Django's default `auth.User` and
make the custom user model migration painful later.

## Development notes

- Backend and frontend source are bind-mounted into their containers for hot reload.
- Celery worker is wired to Redis with a `debug_task` for a smoke test:
  `docker compose exec backend python manage.py shell -c "from config.celery import debug_task; debug_task.delay()"`
  then check `docker compose logs worker` for "celery alive".
