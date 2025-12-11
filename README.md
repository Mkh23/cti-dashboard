# CTI Dashboard — Group Tech Imaging Platform

CTI (Group Tech Imaging) connects Raspberry Pi capture devices to AWS S3, ingests signed webhook events into a FastAPI backend, stores geo-aware metadata in Postgres/PostGIS, and surfaces results through a role-aware Next.js dashboard.

**Data flow:** Pi → S3 (raw) → EventBridge/Lambda (signed webhook) → FastAPI (ingest) → Postgres/PostGIS → Worker (grading) → Next.js dashboard.

## Documentation

- [PROJECT_DESCRIPTION.md](PROJECT_DESCRIPTION.md) – Product vision, architecture, and context
- [ROADMAP.md](ROADMAP.md) – Detailed milestones and checklist tracking
- [DATA_MODEL.md](DATA_MODEL.md) – Database schema and entity relationships
- [TESTING.md](TESTING.md) – Test plan, fixtures, and troubleshooting notes

## Repository layout

```
cti-dashboard/
├─ api/                 # FastAPI service (auth, admin, scans, ingest)
│  ├─ app/              # Application modules
│  ├─ tests/            # Pytest suite (auth/admin/scans/webhooks/S3)
│  └─ requirements.txt
├─ web/                 # Next.js 14 (App Router + Tailwind)
│  ├─ app/              # Dashboard routes (admin/technician/farmer stubs)
│  └─ lib/              # API client utilities
├─ scripts/             # Helper scripts (dev.sh to launch stack)
├─ docker-compose.yml   # Postgres 15 + PostGIS (local dev)
└─ *.md                 # Project documentation
```

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 20 LTS with `pnpm`
- Docker (recommended for Postgres/PostGIS)
- GNU Make or Bash-compatible shell (for `scripts/dev.sh`)

### Option A: One-command dev stack

```bash
./scripts/dev.sh
```

The script provisions Postgres with PostGIS, applies Alembic migrations, boots the FastAPI server, and starts the Next.js dev server on port 3000.

### Option B: Manual setup

```bash
# 1. Database
docker compose up -d db

# 2. API service
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. Web app
cd ../web
pnpm install
echo "NEXT_PUBLIC_API_BASE=http://localhost:8000" > .env.local
pnpm dev
```

Register the first user to seed an admin:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
        "email":"admin@example.com",
        "password":"StrongPass!123",
        "full_name":"Site Admin",
        "phone_number":"+1-555-1234",
        "address":"123 Ranch Road",
        "requested_role":"technician"
      }'
```

### Requesting access through the UI

The Next.js app now exposes `/register`, which collects full name, phone, address, and a requested role (farmer or technician). The first account created in a fresh database is auto-approved and assigned the admin role; all subsequent registrations remain in a **pending** state until an existing admin approves or rejects them from the dashboard. Pending users cannot log in until they are approved.

### Environment variables

`api/.env`

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/cti
JWT_SECRET=change_me
HMAC_SECRET=change_me
CORS_ORIGINS=http://localhost:3000
```

`web/.env.local`

```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

### Production helper

When you're ready to dry-run a production-style launch on something like `10.10.10.104`, run the prod orchestrator. It builds the Next.js app, applies Alembic migrations, and serves API/Web on `0.0.0.0:${API_PORT}` / `0.0.0.0:${WEB_PORT}` (override via env vars).

```bash
# Example: expose API 8000 and Web 3000 on 10.10.10.104
API_HOST=0.0.0.0 API_PORT=8000 \
WEB_HOST=0.0.0.0 WEB_PORT=3000 \
./scripts/prod.sh
```

If you need the helper to bring up the dockerized Postgres as well, export `RUN_DOCKER_DB=true`.

## API highlights

- Auth & RBAC (`/auth`, `/me`)
- Self-service registration queue: new signups land in `pending` status until an admin approves and assigns roles
- Admin management for users and devices (`/admin/*`)
- Role-aware farm APIs (`/farms`) so admins can view all farms while technicians and farmers manage only their own
- Farm membership endpoints enforce that admins can add/remove anyone while farmers can invite technicians to their management group
- Herd metadata endpoints/UI have been renamed to `/groups` (formerly cattle) while preserving the same create/view/edit flows
- Admin user listing now returns full names alongside emails to support dashboard editing
- Scan browsing, detail views, aggregate stats, and grading triggers (`/scans`, `/scans/{scan_id}/grade`) with presigned URLs via `app/s3_utils.py`
- HMAC-protected ingest webhook validating `meta_v1.json`, persisting scans/assets/events/logs, and storing the full `meta_json` blob for later edits
- Incoming metadata now captures grading labels, IMF, backfat thickness, animal weight, `Animal_RFID`, and `group_ID`, automatically creating group/animal records, reconciling farm ownership via geofences, and flagging unassigned scans for admin reassignment
- Ingest applies safe defaults for missing meta fields and ignores legacy/unknown keys (e.g., old cattle_ID) so AWS payload hiccups don't block scan storage
- Group-to-farm updates cascade farm assignment to related animals and scans so lists stay consistent after edits
- Updated group edits to explicitly refresh related animals/scans with the new farm for consistent listings in drill-down views
- Group farm/birth-date edits now cascade to animals so group/animal detail pages show updated farm and birth data; animal scan links respect role-specific scan paths to avoid 404s
- Group updates now propagate farm + birth date to animals/scans; animal/groups forms toggle between register/edit states based on context
- Fixed Animals form toggle (show/hide) so it initializes correctly when editing
- Added Geofence builder stub page per farm; store your province .gpkg/.geojson files outside git (e.g., `resources/geofence/`) and wire a backend endpoint to feed the map
- Scan viewer exposes ribeye area plus clarity/usability/label annotations, supports label-based filters, and includes a mask overlay toggle that highlights the segmentation in green
- Scan timestamps now render in each farm's local timezone (defaulting to America/Edmonton when no centroid is set) so captured-at times from `meta.json` match the ranch clock
- Admin announcements API lets privileged users publish rich-text notices (with landing-page visibility) and powers the new home-page broadcast strip
- Admin-only scan sync endpoint crawls the AWS bucket to backfill missing captures or mirror deletions using the exact same ingest pipeline as the webhook
- Legacy S3 `meta.json` blobs without the full schema now get sensible defaults (meta version, capture timestamps, capture IDs, probe/firmware info, image pointers) so sync jobs keep flowing instead of erroring out
- Health & readiness probes (`/healthz`, `/readyz`)

## Dashboard highlights

- Admin users page shows each person's name, email, and lets admins toggle roles with immediate API persistence
- Shared farm manager page for admins, technicians, and farmers with create/view/edit flows respecting ownership
- Farm detail screens surface the full management group and support role-aware add/remove flows with named confirmation
- Farm detail now includes a GPS/geofence editor (lat/lon + radius) so admins/owners can steer ingest routing by location
- Animal detail pages now show immutable animal metadata plus all related scans (with reported/latest grading, metrics, and image previews)
- Dedicated scan dashboards for admins, technicians, and farmers with status filters, stats, grading controls, and signed media previews
- Scan detail editor now enforces clarity/usability dropdowns with type-safe enums and payload normalization so updates can't submit invalid values or fail builds
- Scan detail view now surfaces the device-reported grading string from `meta.json` (e.g., "AAA") alongside latest grading runs
- Scan detail page now supports deleting scans and editing farm/group assignment, with list timestamps shown as “Added” in the user’s local time
- Scan deletion now also removes associated S3 image/mask objects to keep storage tidy
- Next.js build config now hard-wires the `@` alias so server builds resolve shared libs the same way as local dev
- Backend scan API schemas now explicitly allow `model_name` / `model_version` fields via a shared Pydantic config so dev/prod logs stay noise-free
- Shared group manager lets permitted roles define herds with born dates and external IDs for scan linkage
- Manage Database panel lets admins launch AWS sync jobs (add-only or add+remove) and review ingestion summaries in real time
- User administration page doubles as a pending-approval queue, so admins can review new registration requests, select roles, and approve or reject them in-app
- Scan listing supports label filters/badges, and scan detail pages now include a mask overlay toggle plus editable clarity/usability/label annotations
- Global dashboard navigation now adapts per role (admins only see admin tools; technicians/farmers only see their panels) while still offering Home/Scans shortcuts, sign-out, and branded routing, and the landing page keeps announcements and CTAs front-and-center for quick orientation
- Login view offers inline shortcuts back to the marketing home or the public registration form so users can recover from mistyped URLs quickly

## Running tests

The backend test suite now covers auth, profile, admin, farms, group/animals, scans, webhook flows, S3 helpers, and health probes (91 tests across `api/tests`). A PostgreSQL instance with PostGIS is required (`TEST_DATABASE_URL` defaults to `postgresql+psycopg2://postgres:postgres@localhost:5432/cti_test`).

```bash
cd api
source .venv/bin/activate
pytest --cov=app --cov-report=term-missing
```

`pytest.ini` enforces `--cov-fail-under=70`; with a running Postgres service the suite currently passes at ~85% coverage. See [TESTING.md](TESTING.md) for database bootstrap steps and troubleshooting.

### Ingest smoke tests (real assets)

- Real PNG image + mask fixtures and default metadata live in `tests/fixtures/sample_ingest_payload.json`.
- Real photo/mask + final `meta.json` are in `tests/scan20261208/` (override via `CTI_SAMPLE_DIR`) and are used by the S3 smoke and webhook scripts.
- Upload to AWS S3 with the final `meta.json` by running `pytest tests/test_ingestion_e2e.py` (requires `CTI_BUCKET` and AWS credentials).
- Post a signed webhook using the same assets via `UPLOAD_TO_S3=1 CTI_BUCKET=... python scripts/test_webhook_hmac.py` (uploads image/mask/meta and sends the HMAC webhook); omit `UPLOAD_TO_S3` to only send the webhook body.
- `tests/test_webhook_hmac.py` sends the same payload to `INGEST_WEBHOOK_URL` for quick end-to-end validation.
- `meta.json` supports optional `grading` (string). When provided, the dashboard shows “Reported: <grading>”; otherwise it shows “Awaiting grading.”

## Project status snapshot

- Backend foundations shipped: Alembic schema, auth/RBAC, role-aware farms/devices/groups/animals, scans/assets/events, grading scaffolding, and S3 helpers.
- Ingest hardened: `meta_v1.json` validation applies safe defaults, ignores legacy `cattle_ID`, and accepts AWS payloads even when optional fields are missing.
- Herd rename complete: all “cattle” references are now “group” across API, data model, docs, and dashboard UI.
- Scan flows: list view shows “Added” in the user’s local time; detail view shows captured/added times in farm time (default Alberta) or browser time with MT/CT/ET/PT labels; assignment editor updates farm/group; delete action removes events, grading, assets, and best-effort S3 cleanup without blocking errors.
- Dashboard: scan detail page now places a collapsible “Scan edit” card beneath grading history and keeps farm/group fields editable.
- Tests: backend suite runs via `pytest --cov=app --cov-report=term-missing` (see [TESTING.md](TESTING.md)); coverage sits above the 80% target when Postgres is available.

## 🔒 Security posture

- JWT auth with bcrypt hashing and expiry windows
- HMAC-signed webhooks with timestamp drift enforcement
- Strict CORS derived from `CORS_ORIGINS`
- Role checks enforced in API and dashboard routes

## 🔑 Key API Endpoints

- `POST /auth/register|login`, `GET/PUT /me`
- `GET/POST /admin/users`, `GET/POST /admin/devices`
- `GET/POST /farms`, `GET/POST /groups`, `GET/PUT /groups/{id}`
- `GET /scans`, `GET /scans/{id}`, `PATCH /scans/{id}`, `PATCH /scans/{id}/assignment`
- `DELETE /scans/{id}` (admin-only) removes related events/results and attempts S3 cleanup
- `POST /scans/{id}/grade`
- `POST /ingest/webhook` (HMAC + JSON Schema validation)
