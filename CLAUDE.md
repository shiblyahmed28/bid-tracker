# CLAUDE.md — Spectrum Bid Tracker

Read this file fully before doing anything. It is the source of truth for this project.
If a user instruction conflicts with this file, ask before proceeding.

---

## 1. What this is

An internal web dashboard for **Spectrum Engineering Consortium (Pvt.) Ltd.**, Dhaka.
It mirrors a private Google Sheet of government and enterprise tender bids into PostgreSQL and
presents it to Spectrum's management as a login-gated dashboard.

**Audience: senior management.** Not a hobby app. Density, clarity and correctness beat cleverness.

A previous developer built a version of this and abandoned it; it no longer runs.
Do not reuse or reverse-engineer it. Build fresh.

### Pipeline

```
Private Google Sheet ──(service account, read + one narrow write)──▶ Django ingestion
      ▲                                                                    │
      │ writes ONLY the uid column                                         ▼
      └──────────────────────────────────────────────  PostgreSQL ──▶ DRF API ──▶ React SPA
                                                            │                     (Flutter later)
                                                     Celery Beat (8h) + worker
                                                            │
                                                     Gmail SMTP + in-app notifications
```

---

## 2. Non-negotiables

1. **No dashboard without a valid session.** Enforced on the server. React route guards are UX, not security.
2. **Never commit secrets.** `.env` is gitignored from the first commit. No credentials in code, logs or fixtures.
3. **The sheet is not damaged.** The service account writes exactly one column (`uid`) and nothing else, ever.
4. **Nothing is silently overwritten.** A local edit disagreeing with the sheet raises a conflict.
5. **Every mutation is attributed.** Creates, edits, deletes, sign-ins and sync runs record who or what caused them. The audit log is append-only.
6. **Sheet data is dirty.** Every parser handles failure without crashing the run. Bad rows are quarantined, not fatal.
7. **Timezone is `Asia/Dhaka`.** Store UTC, render Dhaka.
8. **API versioned at `/api/v1/`** from the first endpoint.
9. **Only `@spectrum-bd.com` email addresses may exist as accounts.** Validated on the server.
10. **Every screen is responsive** down to 380px.

---

## 3. Stack

| Layer | Choice | Notes |
|---|---|---|
| Frontend | React 18 + Vite + TypeScript | Not Create-React-App |
| Routing | React Router v6 | |
| Charts | Recharts | |
| Backend | Django 5 + Django REST Framework | |
| Auth | `djangorestframework-simplejwt` | Refresh tokens tracked per session |
| DB | PostgreSQL 16 | |
| Tasks | Celery + Redis, Celery Beat | |
| Sheets | `gspread` + `google-auth` | Service account |
| Email | Django SMTP → Gmail | 2FA + 16-char App Password |
| PDF | WeasyPrint | Server-side, landscape A4 |
| UA parsing | `user-agents` (PyPI) | Device type, brand, browser, OS |
| Deploy | Docker Compose | See below — dev and prod OSes differ |

**Development is Ubuntu-only.** Do not write Windows or macOS instructions.

**Production is a CentOS 7 VM** (`36.255.69.114`), not Ubuntu: Docker 20.10.21, SELinux
disabled, no firewalld, **no git installed**. Deployment ships by `tar` + `scp`, not `git pull` —
see `docs/DEPLOY.md`. The VM already runs a production GRP system — **nginx on port 80 and
Tomcat on 8080, plus a system PostgreSQL 11 on port 5432 — none of which this project may touch.**
Only port 443 (and a temporary port 8090 for pre-TLS verification) belong to this app.

---

## 4. Repo layout

```
spectrum-bid-tracker/
├── docker-compose.yml / docker-compose.prod.yml
├── .env.example (committed) / .env (gitignored)
├── CLAUDE.md · README.md
├── spectrum-dashboard-mockup.html      # design reference
├── backend/
│   ├── Dockerfile · requirements.txt · manage.py
│   ├── config/                         # settings, urls, celery
│   ├── secrets/service-account.json    # gitignored
│   └── apps/
│       ├── accounts/    # user, roles, sessions, profile, password
│       ├── bids/        # models, API, serial logic, PDF export
│       ├── sync/        # sheets client, normalizers, conflicts
│       ├── notifications/
│       └── audit/
└── frontend/
    ├── Dockerfile · package.json
    └── src/{api,auth,components,pages,theme}
```

---

## 5. Data contract — the Google Sheet

Sheet ID `1VH8VTGMsr9oyU7514PtjF4SIm_I2jXzeL0EE1N6Gz-4`
Service account `overseer-0@deployment-heisenberg.iam.gserviceaccount.com`
Tabs: `bids` (source of truth), `summary-by-month`, `summary-by-client`, `z-data` (enum lists).

**Only read `bids`.** The summary tabs are Excel formulas — recompute those in SQL or they drift.
Use `z-data` to seed dropdown options.

### Header structure

The header block is **three rows tall** with merged group labels.
**Real column names are on row 3. Data starts on row 4.**

### Columns (0-indexed, as they appear on row 3)

| # | Name | Type | Notes |
|---|---|---|---|
| 0 | `#` | int | Sheet's own counter. Unreliable. Ignore. |
| 1 | `client` | text | Always present. 157 distinct. |
| 2 | `description` | text | Long free text. |
| 3 | `cam` | text | 40 distinct, whitespace variants |
| 4 | `sales-resource` | text | 44 distinct |
| 5 | `bid-manager` | text | 44 distinct |
| 6 | `initiation-mode` | enum | Sales Effort, Tender Mela, e-GP Notice, CPTU Notice… |
| 7 | `stage` | enum | TENDER 259, RFP 105, RFQ 54, EOI 41, Enlistment 23, eGP-RFP 19 |
| 8 | `procurement type` | enum | **Only 24 of 575 filled.** |
| 9 | `goods` | flag | see delivery-type note |
| 10 | `works` | flag | |
| 11 | `service` | flag | |
| 12 | `tender-id` | text | **NOT UNIQUE — see §6** |
| 13 | `initiation` | date | |
| 14 | `"published" -> "initiation"` | — | Stray annotation. Ignore. |
| 15 | `published` | date | 18 values are text strings |
| 16 | `pre-bid \n date` | date | Header contains a newline |
| 17 | `pre-bid time` | time | |
| 18 | `submission` | date | **Deadline.** 569/575 filled |
| 19 | `submission time` | time | |
| 20 | `security-mode` | enum | Bank Guarantee 307, Not Applicable 95, Pay Order 37 |
| 21 | `security-amount` | money | **103 non-numeric, mixed currency** |
| 22 | `credit-facility` | money | **130 non-numeric** |
| 23 | `Issuing Date` | date | 6 text values |
| 24 | `BG/ Reference Number` | text | |
| 25 | `Issuing Bank` | text | |
| 26 | `Expiry Date` | date | **79 cells contain the text `N/A`** |
| 27 | `submission` | enum | **DUPLICATE NAME.** Submitted 458 / Not Submitted 96. Address by index 27. |
| 28 | `result` | enum | Pending 237, Lost 72, Won 50, Lowest 11, Qualified 11, Cancelled 8 |
| 29 | *(unnamed)* | — | Spacer. Ignore. |
| 30 | `remarks` | text | |
| 31-33 | *(unnamed)* | — | Ignore. |
| **NEW** | `uid` | uuid | Added at far right by Shibly. See §6. |

**Address columns by index, not by header name.** Two columns are both named `submission`,
one header contains a newline, one is a stray annotation. Name lookup picks the wrong column.

---

## 6. Identity and matching — read this twice

### The problem

`tender-id` is **not unique**, despite what the sheet's authors believe. Across all 575 rows:
194 rows (34%) leave it **blank**, 86 contain the literal string **`"N/A"`**, and ~6 real IDs
appear **twice**. Only ~51% carry a usable unique tender-id. Keying on it corrupts the database.

### The solution

A `uid` column exists at the far right of the sheet. On each sync:

1. Read every row.
2. If `uid` is blank, generate a UUID4 and **write it back to that one cell**.
3. Match sheet rows to `Bid` records on `uid` only. Never on tender-id, never on row position.

This is the only write the application ever makes to the sheet. Batch with
`worksheet.batch_update` — never cell by cell, it will hit rate limits.

### Serial numbers

| Field | Purpose | Stable? |
|---|---|---|
| `id` (UUID) | Primary key, all FKs and API paths | Permanent |
| `reference` (`SPC-YYYY-NNNN`) | Human-quotable, used in emails and details | Permanent |
| `serial` | Display position in the table | **Recomputed, shifts on delete** |

- Serial is a **computed display position** derived from `arrival_seq` — never stored as truth.
- `arrival_seq` is a monotonic counter assigned in order of first appearance, whether the record
  came from the sheet or was created in the app.
- Worked example: the sheet's newest row is serial 501. A user creates a bid in the app → 502.
  The sheet's next new row syncs later → 503, even though the sheet itself calls it 502.
- On delete, serials **close up with no gaps**.
- Implement as `ROW_NUMBER() OVER (ORDER BY arrival_seq)` over non-deleted rows, computed ascending
  across the whole table — never over a paginated slice, or every page would start back at 1.

**Never put a serial in an email, notification or permalink.** Use `reference`.

### Display ordering

Every bid list — All bids, Classic view, the dashboard's bid table, and PDF/CSV export — displays
**newest first**: `ORDER BY arrival_seq DESC`. The `serial` value itself is still computed
ascending (above), so the newest bid holds the highest serial number and sits at the top of page 1.
With 577 bids and the default page size of 50, page 1 shows serials 577 down to 528; page 3 shows
477 down to 428 — never 1 up to 50, which is what a window function computed after `LIMIT`/`OFFSET`
would wrongly produce.

### App-created records

`source='app'`, **no `uid`**. Never written to the sheet, never deleted by the sync as "missing".

---

## 7. New fields — not in the sheet

Three fields exist only in the app. They are app-native, editable by editors and admins, never
synced, and never overwritten by a sheet fetch.

| Field | Type | Notes |
|---|---|---|
| `team` | FK to `Team` | Which Spectrum team owns the bid. Seed: Government, Banking & Fintech, Education & Research, Telecom, Enterprise. Admin-editable list. |
| `engaged_resources` | M2M to `Person`, through `BidEngagement` | **A list, not a count.** Everyone who worked the bid, not just the three named roles. The count is derived — never store it. Still read/written as a plain `Person` list everywhere (`.set()`, `.all()`); only the underlying table gained extra per-row columns (below). |
| `engagement_from` / `engagement_to` | date | The bid-level period those people were engaged. `engagement_days` is a computed property, not a column. Distinct from `BidEngagement`'s own per-person dates below. |

Editable in the create and edit forms as a multi-select and a date pair. Both are filterable and
selectable columns on the register, and `team` is a dashboard breakdown.

When back-filling existing rows, leave them null rather than guessing. The prototype seeds
plausible values for demo purposes only — **do not port that seeding logic into the app.**

### Engagement and cost tracking (Phase 19)

Two more app-native models, never touched by sync (§9 step 4d):

**`BidEngagement`** — the through-model for `engaged_resources` above. One row per (bid, person),
unique together:

| Field | Type | Notes |
|---|---|---|
| `engaged_from` / `engaged_to` | date, optional | This person's own engagement window — separate from the bid-level `engagement_from`/`engagement_to`. |
| `days` | int, required, default 0 | **Actual worked days, entered directly — never derived from the date span.** Someone engaged 1–15 Aug may have worked 7 days. |
| `convenience_bill` | Decimal, default 0 | Always BDT — no currency field of its own. |
| `note` | text, optional | |

**`BidCostLine`** — bid preparation costs: `bid` FK, `description`, `date`, `reference`,
`amount` (Decimal), `currency` (default BDT), `category` (optional — admin-managed choice list,
same pattern as `stage`/`security_mode`: a plain string, not an FK), `created_by`, `created_at`.
Its display position (`line_number`) is computed per bid, never stored — see §10.

**Computed on `Bid`, none stored:**

| Property | Computes |
|---|---|
| `total_engagement_days` | `Sum(BidEngagement.days)` |
| `total_convenience_bill` | `Sum(BidEngagement.convenience_bill)` — always BDT |
| `total_cost_lines` | `Sum(BidCostLine.amount)`, **BDT and USD reported separately** |
| `management_cost` | `total_cost_lines + total_convenience_bill`, per currency — only the BDT side gets `total_convenience_bill` added, since that figure is always BDT |

All four aggregate in the database (`.aggregate()`), never by looping over the related rows in
Python. Never sum BDT and USD into one figure (§8, §20).

### Engaged Resources (Phase 20)

The Master Settings screen for `Person` is labelled **"Engaged Resources"** in the UI — a label
change only, the model stays `Person` and every API path stays `/settings/people/`.

- **Management screen**: name, email, internal/external, organization, phone, active, linked user
  account, and a usage count (bids as CAM/sales resource/bid manager/engaged resource). Filter by
  type and by active. Inline create/edit/deactivate.
- **Duplicate detection and merge**: groups `Person` rows by whitespace-collapsed, case-folded
  `canonical_name` — `canonical_name` is unique at the DB level but only case-sensitively, so
  historical rows can still collide this way. Merging one person into another reassigns every
  `BidEngagement` (skipping — not overwriting — any bid the survivor is already engaged on) plus
  every `cam`/`sales_resource`/`bid_manager` reference on `Bid`. The absorbed record is
  **deactivated, never hard-deleted** (avoids a `PROTECT` failure and keeps its audit history
  intact). **Run this before turning on welcome emails**, so a duplicate doesn't miss its email.
- **Engagement history**: selecting a resource lists every bid they were engaged on — days, dates,
  convenience bill — plus totals.
- **Welcome email**, admin-triggered only, never automatic:
  - Global switch (`WelcomeEmailSettings`, above), **default off** — checked inside the send
    service itself, not just hidden in the UI, so the gate holds regardless of who calls it.
  - One send per (bid, person) — `welcome_email_sent_at` lives on `BidEngagement`, not `Person`,
    precisely so this is per-bid. A "Resend" button deliberately bypasses the one-send guard;
    there's no hard limit at the API level, only the button's label distinguishes first send from
    resend.
  - Blocked with no email on file for that person.
  - **External recipients get a reduced version** — no security amounts, no credit facility, no BG
    details. Enforced by leaving those keys out of the template context entirely for external
    people, not by a template conditional alone, so a template bug can't leak them.
  - Every send is audited (recipient, bid, triggering admin), and so is every toggle of the global
    switch.

---

## 8. Normalization rules

Every field goes through a normalizer. **A parse failure never aborts the run** — it records a
`QuarantineRow` and continues.

**Text** — strip whitespace, collapse internal runs. Treat `""`, `"-"`, `"N/A"`, `"NA"` as null.

**People** — normalize to a `Person` table with `canonical_name`. Match case-insensitively on the
whitespace-stripped name so `"Aminul Quader Khalili "` and `"Aminul Quader Khalili"` collapse to one.

**Delivery type** — three columns collapse into three booleans. Values include `goods`, `service`,
`services`, `works`, `n/a`, blank. Lowercase and singularize: `services → service`.

**Dates** — try native datetime → `%a,%B %d,%Y` → `%a, %B %d, %Y` → `%a,%b %d,%Y` → `%d/%m/%Y` → `%Y-%m-%d`.
**Reject any year outside 2000–2100.** Row 184 contains `Wed, May 07, 0206` → year 206.
On failure store null and quarantine with the raw value.

**Money — three fields per amount.** Store all three; never discard the original.

| Field | Content |
|---|---|
| `security_amount_raw` | Exact cell text, unmodified. Shown on the details page. |
| `security_amount` | Parsed `Decimal`, or null |
| `security_currency` | `BDT` or `USD` |

- Contains `USD` or `$` → `USD`; otherwise `BDT`
- Strip everything except digits and `.`
- **Bangladeshi grouping**: `9,20,000.00` is 920000. Removing commas handles this — never use locale-aware parsing.
- Unparseable → null amount, keep raw, do not quarantine (common and benign)

**Never sum across currencies.** Report BDT and USD separately.

**Enums** — uppercase and trim `stage`. Seed valid values from `z-data`, but accept unknown values
and flag for review rather than rejecting the row.

---

## 9. Sync algorithm

Every 8 hours (00:00, 08:00, 16:00 Asia/Dhaka) via Celery Beat, and on demand via
`POST /api/v1/sync/run` (admin only).

```
1  Open a SyncRun (trigger = scheduled | manual, actor).
2  Read `bids` from row 4 down.
3  Backfill blank uid cells — batched, one write call.
4  For each row:
     a  Normalize every field. Collect parse errors.
     b  Critical field missing (no client, no usable submission date) → QuarantineRow, continue.
     c  Look up Bid by uid.
        - Not found → create, source='sheet', next arrival_seq, emit "created".
        - Found → diff field by field:
            · unchanged → skip
            · changed, not locally overridden → apply, emit "updated" with old/new
            · changed AND locally overridden → do NOT apply, create SyncConflict, notify
     d  NEVER touch team, engaged_resources, engagement dates, BidEngagement (including its
        welcome_email_sent_at), BidCostLine, or the new Person fields (email, person_type,
        organization, phone, is_active, user) — all app-native (§7).
5  source='sheet' bids whose uid vanished → missing_from_sheet=True. NEVER auto-delete.
6  Close SyncRun with counts: read, created, updated, conflicted, quarantined, duration.
7  Queue notification digests.
```

### Conflict handling

A user editing a sheet-owned field adds that field to `locally_overridden` (a JSON list on the Bid).
At the next sync, if the sheet differs on an overridden field, create a `SyncConflict` with
`field`, `sheet_value`, `local_value`, `local_editor`, `local_edited_at`. **Neither wins
automatically.** UI shows "Sheet says X, you set Y" with *Keep mine* / *Take sheet's* and a bulk
resolve. Admins can set a global policy (`ask` | `sheet_wins` | `app_wins`), default `ask`.

### Deletion

- **User deletes in the app** → soft delete. Hidden everywhere, serials close up, record and audit history survive, admin can restore.
- **Row disappears from the sheet** → never auto-delete. Flag `missing_from_sheet` for admin review.

---

## 10. Domain model

```
User(AbstractUser)
  email unique, MUST match ^[^@\s]+@spectrum-bd\.com$   (validator + serializer + admin)
  full_name, phone
  role: admin | editor | viewer
  must_change_password: bool
  notifications_muted, email_digest, email_deadline, email_newbid: bool

UserSession
  user FK, refresh_jti unique, ip, user_agent
  device_type: desktop | mobile | tablet | unknown
  device_brand, os, browser          # parsed from user_agent, best-effort
  created_at, last_seen_at, revoked_at
  is_active property = revoked_at is null and not expired

Team              name, is_active
Person            canonical_name, aliases[]
                  email unique-when-set null · person_type: internal|external, default internal
                  organization · phone · is_active bool          # NEW, app-native (Phase 19)
                  user FK to User null (OneToOne)                # NEW, app-native (Phase 19)
Client            name, canonical_name

Bid
  id UUID pk · reference unique · arrival_seq bigint unique
  uid UUID null unique · source: sheet|app · sheet_row int null
  client FK · description
  cam FK · sales_resource FK · bid_manager FK
  team FK null                          # NEW, app-native
  engaged_resources M2M Person through BidEngagement   # NEW, app-native, a list
  engagement_from, engagement_to date   # NEW, app-native
  stage · initiation_mode · procurement_type
  is_goods, is_works, is_service bool
  tender_id                             # informational only, NOT a key
  initiation_date, published_date, prebid_date, submission_date
  submission_status · result
  security_mode
  security_amount_raw, security_amount, security_currency
  credit_facility_raw, credit_facility, credit_facility_currency
  bg_issue_date, bg_reference, bg_bank, bg_expiry_date
  remarks
  locally_overridden JSON · missing_from_sheet, is_deleted bool
  created_by, updated_by FK · created_at, updated_at

  @property engagement_days = (engagement_to - engagement_from).days   # computed, never stored
  @property total_engagement_days, total_convenience_bill,             # computed, never stored
            total_cost_lines, management_cost                          # (§7 Phase 19, per-currency)

BidEngagement     bid FK · person FK · unique(bid, person)             # NEW, app-native (Phase 19)
                  engaged_from, engaged_to date null · days int default 0
                  convenience_bill Decimal default 0 (BDT) · note
                  welcome_email_sent_at datetime null                  # NEW, app-native (Phase 20) —
                  # per (bid, person), not per Person: "never sends twice for the same bid"

WelcomeEmailSettings   singleton (pk=1) · enabled bool default False   # NEW (Phase 20 item 5)
                       updated_by FK · updated_at

BidCostLine       bid FK · description · date · reference              # NEW, app-native (Phase 19)
                  amount Decimal · currency default BDT · category (choice-list value)
                  created_by FK · created_at
                  # line_number is a computed display position, never stored

BidNote · SyncRun · QuarantineRow · SyncConflict
AuditEntry        actor FK null, actor_label, action, bid FK null, field,
                  old_value, new_value, ip, user_agent, created_at   # append-only
NotificationSubscription   user FK, field_name, enabled
Notification      user FK, kind, title, body, bid FK, read, created_at
```

---

## 11. Roles

| Capability | Viewer | Editor | Admin |
|---|:--:|:--:|:--:|
| Both dashboards, register, details, PDF export | ✅ | ✅ | ✅ |
| Own profile, own password, own sign-in history | ✅ | ✅ | ✅ |
| Receive and configure own notifications | ✅ | ✅ | ✅ |
| Create bid · edit bid · resolve conflicts | ❌ | ✅ | ✅ |
| Soft-delete bid | ❌ | ❌ | ✅ |
| Trigger manual sync | ❌ | ❌ | ✅ |
| **Sync history & quarantine** | ❌ | ❌ | ✅ |
| **Audit log** | ❌ | ❌ | ✅ |
| All users' sign-in history · revoke others' sessions | ❌ | ❌ | ✅ |
| User management · reset any password | ❌ | ❌ | ✅ |
| Merge engaged resources · view engagement history | ❌ | ❌ | ✅ |
| Toggle and send welcome emails (`manage_welcome_emails`) | ❌ | ❌ | ✅ |

Enforce with DRF permission classes on **every** viewset. Never rely on a hidden frontend button.
Sync history and the audit log are admin-only. This is explicit and not negotiable.

---

## 12. Dashboard behaviour

### Shared date range

One control drives everything on the dashboard. It filters on **submission date**.

- **Default: today − 7 days to today + 7 days.**
- Presets: ±7 days (14 days) · ±14 days (28 days) · ±30 days (60 days) · This year · Past 12 months ·
  All, plus free date entry. The first three are symmetric around today — each label spells out the
  total span so "±7 days" reads unambiguously as 14 days end to end, not 7.
- **Every panel responds** — KPI cards, trend chart, result mix, clients by volume, bid managers,
  team breakdown, security exposure, the bid table. Nothing is pinned to "all time".
- Each panel still carries a small scope label so the user can see what it covers.

### Adaptive bucketing

The trend chart must not render 365 daily bars. Pick the bucket from the span:

| Span | Bucket |
|---|---|
| ≤ 31 days | daily |
| ≤ 800 days | monthly |
| > 800 days | quarterly |

### Submission runway

The signature panel. For spans ≤ 31 days, a day-by-day rail with today marked and bids as
clickable stage-labelled markers — green submitted, amber open, red passed-but-not-submitted.
For longer spans it degrades to a bucketed volume strip.

⚠️ **Known gap:** the sheet contains **zero future submission dates** — every row is entered after
its deadline passed. Surface this in the runway rather than showing an empty strip.

### Panels

KPI row (submitted in range, win rate, awaiting result, security locked up) · submitted vs not
submitted · result mix donut · clients by volume · bid managers · team breakdown · bid security
expiring in 60 days · a bid table (SL, client, team, stage, bid manager, engaged resources,
published, submission, submission status, result — newest first, Details per row, server-paginated
at 25).

---

## 13. All bids — the register

A read-only mirror of the `bids` worksheet. No editing here; editing lives on the bid detail page.

- **Pagination** — 50 rows per page by default, with a numbered page index at the bottom
  (first, ellipsis, neighbours, ellipsis, last) plus a page-size selector (25/50/100/200).
  **Server-side.** Never ship 575 rows to the browser.
- **Column picker** — all 28 columns can be shown or hidden, grouped as
  Core / New fields / People / Dates / Financial / Status. Defaults to the 11 important ones:
  `SL, Client, Team, Stage, Bid manager, Engaged resources, Published, Submission, BG expiry,
  Submission status, Result`. Selection persists per user.
- **Filters** — one per column. Enum columns get a dropdown of distinct values; text, list and
  money columns get a contains-match input. Filters combine with AND. Show active filters as
  removable chips.
- **Date range** — the same control as the dashboard, on submission date.
- **Search** — one box across client, description, tender id and bid manager.
- **Details** — a button at the end of every row opening the full record.
- **Charts** — at the bottom, a breakdown of the currently filtered set by client, team, bid
  manager, submission status and result. These respect **every active filter and search term**,
  not just the date range — unlike the executive dashboard's breakdowns, which are date-range only.
  Each chart is labelled with a summary of the active filters.

### PDF export

A dialog before download, not a blind button:

1. Shows how many records will be exported and which filters are applied.
2. Lets the user pick which columns to print, defaulting to the currently visible set.
3. Generates **server-side** with WeasyPrint — landscape A4, Spectrum green header, a caption line
   listing the filters used, the generating user and the timestamp, and page numbers.
4. Exports **all filtered rows**, not just the current page.

Warn in the dialog when more than ~10 columns are selected — the page gets cramped.

---

## 14. Accounts, sessions and passwords

### Profile page
Shows the user's details and lets them edit **full name, email, phone**.
Email must match `^[^@\s]+@spectrum-bd\.com$` — validated client-side for feedback and
**server-side as the real rule**. Role and join date are read-only; only an admin changes a role.

### Password change
Current + new + confirm. Minimum 10 characters with a strength meter.
**Changing a password revokes every other session** but keeps the current one alive.

### Admin password reset
`POST /users/{id}/reset-password/` with options: force change at next sign-in, email the user,
revoke all their sessions. Writes an audit entry naming the admin. **Admins never see existing
passwords** — hashes only, no exceptions.

### Login history
Every sign-in creates a `UserSession` recording time, IP, device type, probable device brand,
OS and browser, parsed from the user-agent with the `user-agents` library.

- **Viewers and editors see only their own.** **Admins see everyone's**, filterable by user.
- Active sessions are marked; the current device is labelled.
- **Sign out all other sessions** blacklists every refresh token except the current one.
- Admins can revoke an individual session, or all of one user's sessions.
- Present device brand as a best guess — user-agent strings are not authoritative. Say so in the UI.

---

## 15. Audit

Every one of these writes an `AuditEntry`: sign-in, failed sign-in, sign-out, session revoke,
bid create, bid update (one entry per changed field with old and new value), soft delete, restore,
conflict resolution, user create/update/role change, password reset, manual sync trigger.

`actor` is the user, or null with `actor_label='System (sync)'` for automated changes.
**Append-only** — no update or delete endpoints, not even for admins.
Filterable by user, action, bid and date range, with CSV export.

The client's explicit requirement: *the admin must be able to see which user made any changes.*
The audit UI is filterable **by user**, and every bid detail page shows its own history.

---

## 16. Notifications

**Per-column subscriptions** — a toggle per bid field, including the three new ones. On an update,
a user is notified only for fields they follow. Default on: `result`, `submission_status`,
`submission_date`, `security_amount`, `bg_expiry_date`, `bid_manager`, `team`, `engaged_resources`.

**New bid** — one notification regardless of column subscriptions, titled
`{client} — {first 60 chars of description} · due {submission_date}`. Viewers get these too.

**Deadline alert** — 7 days before `submission_date`, sent immediately, own toggle.
Deduplicate so a bid never alerts twice.

**Email batching is mandatory.** In-app fires instantly. Change emails batch into **one digest per
user per sync run**. Unbatched, a sync touching 40 bids across 15 users sends 600 emails and blows
Gmail's ~500/day cap in a single run. Deadline and new-bid emails send immediately.

---

## 17. API

Base `/api/v1/`. JSON only. Pagination on every list endpoint. Filter and sort via query params.

```
POST   /auth/login/  · /auth/refresh/ · /auth/logout/ · GET /auth/me/
GET    /auth/sessions/                     own sessions
POST   /auth/sessions/revoke-others/       sign out everywhere else
POST   /auth/sessions/{id}/revoke/
PATCH  /auth/profile/                      full_name, email (domain-checked), phone
POST   /auth/change-password/

GET    /bids/          ?search=&stage=&result=&client=&team=&bid_manager=&engaged=&
                        submission_after=&submission_before=&columns=&page=&page_size=
POST   /bids/          editor+
GET    /bids/{uuid}/ · PATCH editor+ · DELETE admin (soft)
GET    /bids/{uuid}/history/
POST   /bids/{uuid}/notes/
GET    /bids/export/pdf/    same filters + columns=  → WeasyPrint, landscape A4
GET    /bids/export/csv/

GET    /dashboard/summary/      ?from=&to=    all KPIs
GET    /dashboard/trend/        ?from=&to=    adaptive buckets (§12)
GET    /dashboard/breakdown/    ?from=&to=&by=client|bid_manager|team|result
GET    /dashboard/deadlines/    ?from=&to=
GET    /dashboard/bg-exposure/  ?days=60
GET    /dashboard/classic/      ?from=&to=

POST   /sync/run/ · GET /sync/runs/ · GET /sync/quarantine/     admin
GET    /sync/conflicts/ · POST /sync/conflicts/{id}/resolve/    {"choose":"sheet"|"local"}

GET    /notifications/ · POST /notifications/{id}/read/
GET/PATCH /notifications/settings/

GET    /audit/ · GET /audit/export/          admin
GET/POST/PATCH /users/                       admin
GET    /users/{id}/sessions/                 admin
POST   /users/{id}/reset-password/           admin

GET/POST/PATCH /settings/people/     ?person_type=&is_active=     manage_choice_lists (§Phase 20)
GET    /settings/people/duplicates/                               manage_choice_lists
POST   /settings/people/{id}/merge/  {"duplicate_id": id}         manage_choice_lists
GET    /settings/people/{id}/engagements/                         manage_choice_lists
GET/PATCH /settings/welcome-email/   {"enabled": bool}            manage_welcome_emails
POST   /settings/engagements/{id}/welcome-email/                  manage_welcome_emails
```

**Default when no dates given: submission date from today−7 to today+7.**

---

## 18. Environment

```ini
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
TIME_ZONE=Asia/Dhaka
ALLOWED_EMAIL_DOMAIN=spectrum-bd.com

POSTGRES_DB=spectrum_bids
POSTGRES_USER=spectrum
POSTGRES_PASSWORD=change-me
POSTGRES_HOST=db
POSTGRES_PORT=5432
REDIS_URL=redis://redis:6379/0

GOOGLE_SHEET_ID=1VH8VTGMsr9oyU7514PtjF4SIm_I2jXzeL0EE1N6Gz-4
GOOGLE_SHEET_TAB=bids
GOOGLE_SERVICE_ACCOUNT_FILE=/run/secrets/service-account.json
SYNC_INTERVAL_HOURS=8

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=1
EMAIL_HOST_USER=                  # fill locally, never commit
EMAIL_HOST_PASSWORD=              # Gmail App Password (16 chars), needs 2FA on
DEFAULT_FROM_EMAIL=Spectrum Bid Tracker <noreply@spectrum-bd.com>

VITE_API_BASE_URL=http://localhost:8000/api/v1
```

`.env` and `backend/secrets/service-account.json` are gitignored. Never paste either into a chat,
a commit or a log line.

---

## 19. Design

Palette sampled from the Spectrum logo:

```
--deep:   #2E6130   primary, nav, headings
--mid:    #6C9C60   secondary
--lime:   #8FC157   accent, active states, positive
--ink:    #2E2E38   body text (the wordmark grey)
--bg:     #F4F6F2   page background
--surface:#FFFFFF   cards
--line:   #E2E7DE   borders
--muted:  #82887F   secondary text
--danger: #C4453A   overdue, lost
--warn:   #D89B2C   pending, expiring
--classic:#6C63FF   Classic view only — the old app's indigo
```

- **All numbers use tabular monospace figures.** Digits must align in columns.
- Two dashboards: **Dashboard** (executive, Spectrum green) and **Classic** (faithful to the old
  layout, indigo). Both are real routes, both login-gated, both driven by the shared date range.
- Tables show a subset of fields with a **Details** button on every row.
- **Responsive to 380px**: the sidebar becomes a drawer behind a hamburger, the KPI grid stacks to
  one column, tables scroll horizontally, the runway scrolls, filter panels reflow, the date-range
  chips go full width.
- Visible keyboard focus. `prefers-reduced-motion` respected. Escape closes modals and the drawer.

The reference prototype is `spectrum-dashboard-mockup.html` — it runs on the real 575 rows with
working filters, pagination, column picker and PDF export. **Match its layout and behaviour.
Do not copy its markup; it is a prototype, not production code.** Its seeding of team, engaged
resources and engagement period is demo-only and must not be ported.

---

## 20. Landmines — do not do these

- ❌ Reading the header from row 1. It is on **row 3**; data starts on row 4.
- ❌ Looking up columns by name. Two are both called `submission`.
- ❌ Using `tender-id` as a key. Blank or `"N/A"` on half the rows.
- ❌ Using sheet row number as a key.
- ❌ `float(cell)` on money. 233 cells across the two money columns are text.
- ❌ Summing BDT and USD into one figure.
- ❌ Trusting a date parser on `Wed, May 07, 0206`. Range-check every year.
- ❌ Letting one bad row abort the sync.
- ❌ Auto-deleting bids missing from the sheet.
- ❌ Overwriting a local edit without asking.
- ❌ Storing the display serial, or storing `engagement_days` — both are computed.
- ❌ Letting the sync touch team, engaged resources or engagement dates.
- ❌ Writing anything to the sheet other than the `uid` column.
- ❌ Sending one email per changed bid per user.
- ❌ Shipping all 575 rows to the browser. Paginate server-side.
- ❌ Rendering 365 daily bars. Bucket adaptively.
- ❌ Accepting a non-`@spectrum-bd.com` email anywhere.
- ❌ Showing sync history or the audit log to a non-admin.
- ❌ Exposing password hashes, or letting an admin read an existing password.
- ❌ Committing `.env`, the service-account JSON, or the Gmail App Password.
- ❌ Windows or macOS setup instructions. Development is Ubuntu only.
- ❌ Assuming the production VM is Ubuntu, has git, or is otherwise like the dev box — it's
  CentOS 7, no git, tar+scp deploys. See §3 and `docs/DEPLOY.md`.
- ❌ Touching nginx (port 80), Tomcat (8080) or the system PostgreSQL 11 (5432) on the prod VM —
  they belong to another application already running there.

---

## 21. Working agreement

- Work **one phase at a time**. Finish, verify against the acceptance criteria, stop, report.
- Commit after each phase with a clear message.
- Write the migration, run it, confirm it applies cleanly before moving on.
- When this file is ambiguous or looks wrong, **ask** — do not guess.
- Prefer boring, readable code. This project doubles as a learning artifact for its owner.
