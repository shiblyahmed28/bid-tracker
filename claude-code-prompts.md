# Claude Code — Build Instructions
### Spectrum Bid Tracker · Track 1 (vibe coding)

Work top to bottom. **One phase per session.** Paste the prompt, let it finish, check the
acceptance criteria yourself, commit, then move on. Never paste two phases at once — that is how
these builds go sideways.

---

# Part 0 — Ubuntu setup

Same steps on the office laptop and the home desktop. Run once per machine.

### 0.1 System packages

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git build-essential ca-certificates gnupg python3 python3-pip python3-venv
```

### 0.2 Docker Engine + Compose

```bash
for p in docker.io docker-doc docker-compose podman-docker containerd runc; do sudo apt remove -y $p; done

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
| sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```

Verify: `docker run --rm hello-world` and `docker compose version`.

### 0.3 Node.js 20

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install 20 && nvm use 20 && nvm alias default 20
node -v && npm -v
```

### 0.4 Claude Code

```bash
npm install -g @anthropic-ai/claude-code
claude --version
```

### 0.5 Project folder

```bash
mkdir -p ~/projects/spectrum-bid-tracker && cd ~/projects/spectrum-bid-tracker
git init
```

Copy in:
- `CLAUDE.md` → repo root
- `spectrum-dashboard-mockup.html` → repo root (design reference)
- this file → `docs/claude-code-prompts.md`
- `new_logo-1.png` → `frontend/public/logo.png` (create the folder later if it doesn't exist yet)

### 0.6 Service account key

Google Cloud Console → IAM & Admin → Service Accounts →
`overseer-0@deployment-heisenberg.iam.gserviceaccount.com` → Keys → Add key → JSON.

```bash
mkdir -p backend/secrets
mv ~/Downloads/deployment-heisenberg-*.json backend/secrets/service-account.json
chmod 600 backend/secrets/service-account.json
```

### 0.7 Add the `uid` column to the sheet

In the `bids` tab, add a header **`uid`** in **row 3**, in the first empty column right of
`remarks`. Leave the cells below blank — the app fills them on the first sync. Touch nothing else.

### 0.8 Gmail App Password

Google Account → Security → **2-Step Verification** on → **App passwords** → generate one for
"Mail". You get 16 characters. It goes in `.env`. Your normal Gmail password will not work.

### 0.9 Start

```bash
cd ~/projects/spectrum-bid-tracker && claude
```

---

# Part 1 — Build phases

---

## Phase 1 — Scaffold and infrastructure

> Read CLAUDE.md in full before writing any code.
>
> Set up the project skeleton and Docker infrastructure only. No business logic yet.
>
> 1. Create the repo layout in CLAUDE.md §4.
> 2. `backend/` — Django 5 project `config`, with empty apps `accounts`, `bids`, `sync`, `notifications`, `audit`. Settings read everything from environment variables via `django-environ`. `TIME_ZONE='Asia/Dhaka'`, `USE_TZ=True`.
> 3. `frontend/` — React 18 + TypeScript via Vite, boilerplate stripped to one page reading "Spectrum Bid Tracker".
> 4. `docker-compose.yml` with five services: `db` (postgres:16), `redis` (redis:7-alpine), `backend` (Django dev server, 8000), `worker` (Celery), `frontend` (Vite, 5173). Named volume for Postgres. Bind-mount source for hot reload.
> 5. `.env.example` with every variable from CLAUDE.md §18, placeholders only. Create my real `.env` as a copy with a generated `DJANGO_SECRET_KEY`.
> 6. `.gitignore` covering `.env`, `backend/secrets/`, `__pycache__`, `node_modules`, `*.pyc`, `.venv`, `dist`.
> 7. Wire Celery to Redis. Add a `debug_task` logging "celery alive".
> 8. `README.md` with Ubuntu-only run instructions.
>
> Run `docker compose up --build`, confirm all five containers are healthy, show me the output. Fix anything failing before reporting done.

**Acceptance:** Five services up. `localhost:8000/admin` loads. `localhost:5173` shows the placeholder. Worker logs show Celery connected. `git status` shows `.env` and `backend/secrets/` untracked.

---

## Phase 2 — Users, roles, authentication

> Read CLAUDE.md §11 (roles), §14 (accounts) and §15 (audit) first.
>
> 1. Custom `User` in `accounts` extending `AbstractUser`: email as login field, `full_name`, `phone`, `role` (admin/editor/viewer, default viewer), `must_change_password`, and the four notification booleans from §16. Set `AUTH_USER_MODEL` before the first migration.
> 2. **Email domain rule** — a `RegexValidator` for `^[^@\s]+@spectrum-bd\.com$` on the model, enforced again in every serializer and in Django admin. Reject non-company addresses everywhere, with a clear error message.
> 3. JWT via `djangorestframework-simplejwt`. Access 60 min, refresh 7 days, blacklist enabled. Endpoints per §17.
> 4. DRF permission classes `IsAdmin`, `IsEditorOrAbove`, `IsAuthenticatedViewer`. Set `DEFAULT_PERMISSION_CLASSES` so **every endpoint requires authentication by default**; public access must be explicit opt-in.
> 5. `AuditEntry` model per §10. Append-only: no update/delete API, and override `save()` to raise on modifying an existing row.
> 6. Log successful sign-in, failed sign-in and sign-out with IP and user agent.
> 7. Admin-only user CRUD at `/api/v1/users/`. Admins set roles; nobody changes their own role.
> 8. Management command `seed_users` creating one admin, one editor and one viewer with known passwords.
>
> Write pytest tests proving: a viewer gets 403 on an editor endpoint, an editor gets 403 on an admin endpoint, unauthenticated requests get 401, a non-`@spectrum-bd.com` email is rejected at every entry point, and sign-in writes an audit entry. Run them and show the output.

**Acceptance:** All tests pass. `curl` without a token returns 401 everywhere. Creating a `gmail.com` user fails in both the API and Django admin.

---

## Phase 3 — Sessions and login history

> Read CLAUDE.md §14.
>
> 1. `UserSession` model per §10, one row per issued refresh token, keyed on the JWT `jti`.
> 2. On sign-in, create a session recording IP, raw user agent, and — parsed with the `user-agents` library — device type, probable device brand, OS and browser. Update `last_seen_at` on every refresh.
> 3. On sign-out or token blacklist, set `revoked_at`.
> 4. `GET /auth/sessions/` returns the caller's sessions, newest first, flagging which is the current device.
> 5. `POST /auth/sessions/revoke-others/` blacklists every refresh token except the current one.
> 6. `POST /auth/sessions/{id}/revoke/` — own sessions, or any session if admin.
> 7. `GET /users/{id}/sessions/` — admin only.
> 8. Every revoke writes an audit entry.
>
> Test: signing in from two different user agents creates two sessions with different device types; revoke-others leaves exactly one active; a viewer requesting another user's sessions gets 403.

**Acceptance:** Login history shows correct device type and browser for a desktop and a mobile user agent. Revoke-others works. Role separation holds.

---

## Phase 4 — Domain model

> Read CLAUDE.md §6 (identity), §7 (new fields) and §10 (model) first.
>
> Implement `Person`, `Client`, `Team`, `Bid`, `BidNote` in `bids`, and `SyncRun`, `QuarantineRow`, `SyncConflict` in `sync`.
>
> Critical details:
> - `Bid.id` is a UUID pk. `reference` is `SPC-YYYY-NNNN`, unique, generated on create.
> - `arrival_seq` is a monotonic `BigIntegerField`, unique, assigned from a DB sequence — collision-safe under concurrent sync and manual creation.
> - **The display serial is never stored.** Add a queryset method `.with_serial()` annotating `ROW_NUMBER() OVER (ORDER BY arrival_seq)` across non-deleted rows only, so deletes close gaps. Test it: create 5 bids, delete the third, confirm serials come back 1,2,3,4 with no gap.
> - Money is three fields per amount per §8.
> - **New fields (§7):** `team` FK, `engaged_resources` M2M to Person, `engagement_from`/`engagement_to`. `engagement_days` is a `@property`, **not a column**. Seed the five teams.
> - `locally_overridden` is a JSONField list of field names.
> - `is_deleted` soft delete, default manager excludes deleted, `all_objects` includes them.
>
> Add `Bid.apply_change(field, value, actor)` writing the value, appending the field to `locally_overridden` when the actor is human, and creating an `AuditEntry` with old and new values. All manual edits go through it.
>
> Write and run migrations. Test: reference generation, serial computation after deletes, soft delete, `apply_change` producing an audit entry, and `engagement_days` computing correctly from the date pair.

**Acceptance:** Migrations apply cleanly. Serial test passes. Django admin lists bids with team and engaged resources. `engagement_days` is not a database column.

---

## Phase 5 — Google Sheets ingestion

> Highest-risk phase. Read CLAUDE.md §5, §6, §7, §8, §9 completely, and re-read §20.
>
> Build the pipeline in `sync`:
>
> 1. `sheets_client.py` — authenticate with the service account, open the sheet, read the `bids` tab. **Header on row 3, data from row 4.** Address columns by index per §5, never by name — two are both called `submission`.
> 2. `normalizers.py` — one pure, testable function per field type: `norm_text`, `norm_person`, `norm_date`, `norm_money`, `norm_enum`, `norm_delivery_type`. Follow §8 exactly. Money returns `(raw, Decimal|None, currency)` handling `USD 250000` and `9,20,000.00`. Dates try the listed formats and **reject any year outside 2000–2100**.
> 3. `uid_backfill.py` — find blank `uid` cells, generate UUID4s, write back in **one batched `batch_update`**. The only write the app ever makes.
> 4. `sync.py` — the algorithm in §9, step for step. Match on `uid` only. Respect `locally_overridden` by raising `SyncConflict` instead of overwriting. **Never touch team, engaged_resources or the engagement dates.** Flag `missing_from_sheet` without deleting.
> 5. A row that fails to parse creates a `QuarantineRow` and the run continues. One bad row must never abort the sync.
> 6. `python manage.py sync_sheet [--dry-run]`. Dry run reports what would change and writes nothing, including no uid backfill.
> 7. Celery task scheduled by Beat every 8 hours at 00:00, 08:00, 16:00 Asia/Dhaka.
>
> Unit-test every normalizer with the real dirty values from CLAUDE.md: `"Wed, May 07, 0206"`, `"USD 250000"`, `"9,20,000.00"`, `"N/A"`, `"services"`, `"Aminul Quader Khalili "`.
>
> Then run `python manage.py sync_sheet --dry-run` against the real sheet and show me the report before anything is written.

**Acceptance:** Dry run reads all 575 rows, reports ~575 creates, a small quarantine count, zero crashes. All normalizer tests pass. After a real run: 575 bids, every sheet row has a `uid`, sane `SyncRun` counts, and every bid's `team` and `engaged_resources` are still empty.

---

## Phase 6 — REST API

> Read CLAUDE.md §12, §13, §17. Build every endpoint listed there.
>
> - **Bid list** with search (client, description, tender id, bid manager), filters for every column including `team` and `engaged`, ordering, and **server-side pagination** with a configurable page size (25/50/100/200, default 50). Default date window when none given: submission date today−7 to today+7. Never return all 575 rows.
> - **Bid detail** returning every field including the `_raw` money strings, computed serial, `reference`, `engagement_days`, conflict state and source.
> - `/bids/{id}/history/` — that bid's audit entries, newest first.
> - **Create and update**, editor and above, routed through `Bid.apply_change`. Only title (client + description) and submission date required.
> - **Soft delete**, admin only.
> - **Dashboard endpoints** — `summary`, `trend`, `breakdown`, `deadlines`, `bg-exposure`, `classic`. All take `from` and `to` and **every one respects them**. `trend` implements the adaptive bucketing table in §12 and returns the bucket mode it chose. `breakdown` supports `by=client|bid_manager|team|result`. Compute in the database with `annotate`/`aggregate` — **do not loop in Python**. BDT and USD stay separate.
> - **Sync** endpoints, admin only. Conflict list and resolve.
> - **Audit** list with filters by actor, action, bid and date range, plus CSV export. Admin only.
>
> Add `drf-spectacular`, Swagger at `/api/v1/schema/swagger-ui/`.
>
> Write API tests covering the full role matrix in §11 — for each endpoint, assert the right status for viewer, editor and admin. Explicitly assert that a viewer and an editor both get 403 on `/sync/runs/` and `/audit/`. Run them and show the output.

**Acceptance:** Swagger lists everything. Role matrix passes. `/dashboard/summary/?from=2021-01-01&to=2026-12-31` returns 575 total, 458 submitted, 96 not submitted, 61 won, 73 lost, 237 pending. `trend` returns quarterly buckets for a 5-year span and daily for a 15-day span.

---

## Phase 7 — Frontend shell, auth and responsiveness

> Read CLAUDE.md §19 and open `spectrum-dashboard-mockup.html` — match its layout, palette and behaviour. Do not copy its markup.
>
> 1. Design tokens as CSS variables from §19. Tabular monospace figures for **all** numbers — add a `.num` utility and use it wherever digits appear.
> 2. Axios client with an auth interceptor: attach the access token, refresh on 401, redirect to login when refresh fails.
> 3. Auth context with user and role. `<ProtectedRoute>` and `<RoleRoute requires="admin">` wrappers.
> 4. Login page matching the mockup, using `frontend/public/logo.png`. Client-side check that the email ends in `@spectrum-bd.com`, with the server as the real gate.
> 5. App shell: dark green sidebar, nav grouped Dashboards / Bids / Account / Administration. **The Administration group — Sync history, Audit log, Users — renders only for admins.** User block at the bottom with sign out. Top bar with title, last-sync indicator, admin-only Fetch data button, notification bell with unread count.
> 6. **Responsive, and test it.** Below 940px the sidebar becomes a drawer behind a hamburger with a scrim; below 600px the KPI grid stacks to one column and the date-range chips go full width. Tables scroll horizontally at every size. Escape closes the drawer and any modal.
> 7. Routes for every page with placeholders.
>
> Confirm: logged out, every route redirects to login. A viewer never sees Administration nav items. The layout holds at 380px, 600px, 940px and 1440px — check each.

**Acceptance:** Login works against the real API. Sidebar contents change by role. No horizontal page scroll at 380px. Drawer opens and closes.

---

## Phase 8 — Dashboard

> Build the main dashboard, matching the mockup. Read §12 first.
>
> 1. **Shared date range control** — free From/To inputs plus preset chips (±7 days, 30 days, 90 days, This year, 12 months, All). **Default ±7 days from today.** Store it in one place; every panel reads from it. Show the matched record count next to the control.
> 2. **Submission runway** — the signature panel. Spans ≤31 days render a day-by-day rail with today marked and bids as clickable stage-labelled markers, green/amber/red per §12. Longer spans degrade to a bucketed volume strip. When no bids fall after today, show the explanatory note from the mockup instead of an empty strip.
> 3. **Four KPI cards** — submitted in range, win rate, awaiting result, security locked up (BDT and USD separately).
> 4. **Submitted vs not submitted**, stacked bars, adaptive buckets from `/dashboard/trend/`.
> 5. **Result mix** donut with counted legend.
> 6. **Clients by volume** and **Bid managers** — both driven by the selected range, from `/dashboard/breakdown/`.
> 7. **Teams** breakdown — the new field, bids/won/lost.
> 8. **Bid security expiring** — next 60 days with countdown badges and the total returning to the credit facility.
>
> Every panel carries a scope label. Loading skeletons per panel, not one page-level spinner. Real empty states telling the user to widen the range.
>
> Verify by hand: switch from ±7 days to This year to All and confirm **every** panel's numbers change, including clients and bid managers.

**Acceptance:** All eight panels respond to the range. Trend switches bucket mode as the span grows. Runway markers navigate to bid detail. Holds at 380px.

---

## Phase 9 — All bids register

> Read CLAUDE.md §13. This is a read-only register — no editing here.
>
> 1. **Table** driven by `/bids/`, server-paginated, 50 per page by default with a page-size selector.
> 2. **Numbered pager** at the bottom: previous, first page, ellipsis, neighbours, ellipsis, last page, next. Show "Showing 51–100 of 575".
> 3. **Column picker** — a panel listing all 28 columns grouped Core / New fields / People / Dates / Financial / Status, with the new fields visually marked. Defaults to the 11 in §13. Select all and Reset to default buttons. **Persist the selection per user** (backend preference or localStorage — your call, state which).
> 4. **Per-column filters** — a panel with a dropdown of distinct values for each enum column and a contains input for text, list and money columns. Combine with AND. Show active filters as removable chips above the table. A Clear button resets everything.
> 5. **Date range** — the same shared control as the dashboard.
> 6. **Search box** across client, description, tender id, bid manager.
> 7. **Details button** at the end of every row.
> 8. Horizontal scroll with the header row sticky.
>
> Verify: 575 rows paginate to 12 pages; filtering to team=Government and stage=TENDER gives 72 rows; searching "bdren" gives 15.

**Acceptance:** Pagination, column picker and filters all work against the API. Only the current page is fetched. Filter chips clear individually.

---

## Phase 10 — PDF export

> Read CLAUDE.md §13, the PDF export section.
>
> 1. `GET /bids/export/pdf/` accepting the same filters as `/bids/` plus a `columns` list. Renders **all filtered rows**, not one page.
> 2. Server-side with **WeasyPrint**. Landscape A4, 11mm margins. Spectrum green header with the logo, the title "Bid Register", a caption line stating the filters applied, the generating user and the timestamp in Asia/Dhaka, and "Page X of Y" in the footer.
> 3. Repeat the table header on every page. Never split a row across pages.
> 4. Frontend dialog before download: record count, the filters that will apply, checkboxes for which columns to print defaulting to the currently visible set, and a warning above ~10 columns.
> 5. Generation is a Celery task if the row count is over 500, with the browser polling and then downloading — otherwise synchronous.
> 6. Also add `GET /bids/export/csv/` with the same filters, streamed.
>
> Test: export with default columns and no filters produces a 575-row PDF with correct page numbering; export filtered to one client produces only that client's rows.

**Acceptance:** PDF opens, is readable, header repeats, filter caption is accurate, row count matches the on-screen count.

---

## Phase 11 — Bid details, create and edit

> 1. **Details page** — every field in a definition list, including `_raw` money strings shown exactly as typed and the parsed interpretation beside them. Show the display serial (labelled as a shifting position) and the permanent `reference`. Show `team`, the full `engaged_resources` list with a count, and the engagement period with computed days. Right column: that bid's change history as a timeline, naming who made each change and whether it was manual or a sync.
> 2. **Conflict banner** — "Sheet says X, you set Y" with *Keep mine* / *Take sheet's*, per §9. Editors and admins only.
> 3. **Create page** — only title and submission date required. Client, CAM, sales resource and bid manager are searchable selects with an add-new option. **Engaged resources is a multi-select** showing a live count. Engagement from/to as a date pair. Team as a select. The security amount field accepts free text and shows a live parse preview — typing `9,20,000.00` shows "reads as BDT 920,000". State on the form that app-created bids are never written back to the sheet.
> 4. **Edit** — same form prefilled, routed through `apply_change`.
> 5. **Delete** — admin only, confirmation naming the bid, soft delete.
>
> After saving, show a toast using the same verb as the button.

**Acceptance:** Create adds a bid with the next serial and `source='app'`, and it survives the next sync unchanged with its team and engaged resources intact. Editing a sheet-owned field marks it overridden and the next sync raises a conflict.

---

## Phase 12 — Profile, password and login history

> Read CLAUDE.md §14.
>
> 1. **Profile page** — avatar with initials, name, role badge. Editable full name, email and phone. Role and join date read-only. Email validated against `@spectrum-bd.com` inline as the user types, with the server as the real gate. Save writes an audit entry.
> 2. **Change password** — current, new, confirm. Minimum 10 characters with a live strength meter. On success, revoke every other session and tell the user that happened.
> 3. **Login history page** — sessions table with when, IP, network label, device type with icon, probable brand, browser and status. Viewers and editors see only their own; **admins see everyone's with a user filter**. Three summary cards: active sessions, sign-ins in 30 days, last sign-in.
> 4. **Sign out all other sessions** — confirmation modal, then revoke.
> 5. Admins can revoke an individual session from the table.
> 6. A note under the table stating device brand is a best-effort guess from the user agent.
> 7. **Admin password reset** from the Users page: modal with new password, confirm, and toggles for force change at next sign-in, email the user, and revoke all their sessions. Writes an audit entry naming the admin. Admins never see existing passwords.
>
> Test: a viewer requesting another user's sessions gets 403. Changing a password kills other sessions but not the current one.

**Acceptance:** Profile saves. Non-company email rejected server-side. Login history shows correct device data. Admin reset works and is audited.

---

## Phase 13 — Classic view, notifications and admin screens

> 1. **Classic view** — faithful to the original (see `VIEWS.classic` in the mockup and the screenshot it was based on). From/To with Show report, the exact column set SL / Client / Stage / Published / Submission / Expiry date / Submission status / Result / Actions, the status donut with the original legend, grouped bars by month, summary by client. Keep the indigo `#6C63FF` accent for this view only. Driven by the shared date range.
> 2. **Notifications** — per-column subscription page covering all fields including the three new ones, master delivery switches, bell dropdown with unread count, mark-all-read. **In-app instant, change emails batched into one digest per user per sync run**, deadline and new-bid emails immediate. Daily Beat task at 08:00 Asia/Dhaka for the 7-day deadline alert, deduplicated. HTML templates with plain-text fallback and an unsubscribe link. Test with the console email backend first — I will add the App Password myself.
> 3. **Sync history** — admin only. Run list with trigger, duration and counts. Quarantine table showing sheet row, raw value and reason. Manual Fetch data with live progress.
> 4. **Audit log** — admin only. Filter by user, action, bid and date range. CSV export. This is the explicit client requirement: an admin must be able to see exactly which user made any change.
> 5. **Users** — list, create, edit, change role, suspend, reset password, view their sessions.
> 6. **Polish** — loading skeletons everywhere, real empty states, error boundaries, a 404 page, per-route page titles.
> 7. **README** — Ubuntu setup, how to run, how to sync, how to create the first admin, troubleshooting.
> 8. Seed script generating a realistic demo dataset so the app can be shown without touching the live sheet.
>
> Run the full test suite and show me the results.

**Acceptance:** An admin can answer "who changed this bid's result last Tuesday" in under ten seconds. A viewer gets 403 on sync history and audit. A sync touching 40 bids sends one email per user, not forty. All tests pass. A fresh clone runs with `cp .env.example .env && docker compose up`.

---

## Phase 14 — VM deployment (later, after localhost is signed off)

> Do not start until the app runs correctly on localhost and I have confirmed it.
>
> Target `36.255.69.114`. **This VM already runs Docker, nginx, Tomcat and PostgreSQL on their default ports, and hosts a production GRP system. Nothing existing may be disturbed.**
>
> 1. Before proposing ports, run `sudo ss -tulpn | grep LISTEN` and show me what is taken. Pick a free high-port block and confirm with me before continuing.
> 2. `docker-compose.prod.yml` — our own Postgres on a non-default host port, gunicorn instead of runserver, React built to static files served by our own nginx container, `DEBUG=0`, tightened `ALLOWED_HOSTS` and CORS.
> 3. Multi-stage frontend build so the production image carries no `node_modules`.
> 4. WeasyPrint's system dependencies (`libpango`, `libcairo`, fonts) installed in the backend image — this breaks in production if missed.
> 5. Nightly `pg_dump` to a host directory, 14-day retention.
> 6. Health checks on every service, `restart: unless-stopped`.
> 7. Deploy script: pull, rebuild, migrate, collectstatic.
> 8. Log rotation so container logs cannot fill the disk.
>
> Do not touch the VM's system nginx, Tomcat or PostgreSQL. Everything runs in our own containers on our own ports.

**Acceptance:** App reachable on the agreed port. GRP still working. Sync runs on schedule. PDF export works in the container. Backups appear. Containers survive a reboot.

---

# Part 2 — Working with Claude Code

**Start every session with:** `Read CLAUDE.md, then continue with Phase N.`

| Command | What it does |
|---|---|
| `/clear` | Wipe context between phases — do this every time |
| `Esc` | Interrupt mid-response |
| `claude --continue` | Resume the last session |

**When it goes wrong:**

- *Building ahead into the next phase* → stop it, `/clear`, re-anchor on the phase prompt.
- *Reinventing something CLAUDE.md already specifies* → "Re-read CLAUDE.md §N and follow it exactly."
- *Tests pass but behaviour is wrong* → ask for the failing test first, then the fix.
- *Sync crashing on a row* → §8 is not being followed. Point at the normalizer rules.
- *Dashboard panels ignoring the date range* → §12. Every panel reads the shared range, no exceptions.

**Rules for yourself:**

1. Never end a phase without running its acceptance check personally.
2. Commit after every phase. `git log` is your evidence of the work.
3. If you don't understand what it wrote, ask it to explain before moving on. Track 2 depends on you actually reading this code.
4. Never paste a password, App Password or the service-account JSON into the chat. They live in `.env` and `backend/secrets/`, both gitignored.
