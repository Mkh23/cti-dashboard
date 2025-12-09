# CTI Dashboard — Cattle Tech Imaging Platform

CTI (Cattle Tech Imaging) connects Raspberry Pi capture devices to AWS S3, ingests signed webhook events into a FastAPI backend, stores geo-aware metadata in Postgres/PostGIS, and surfaces results through a role-aware Next.js dashboard.

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
- Admin user listing now returns full names alongside emails to support dashboard editing
- Scan browsing, detail views, aggregate stats, and grading triggers (`/scans`, `/scans/{scan_id}/grade`) with presigned URLs via `app/s3_utils.py`
- HMAC-protected ingest webhook validating `meta_v1.json`, persisting scans/assets/events/logs, and storing the full `meta_json` blob for later edits
- Incoming metadata now captures grading labels, IMF, backfat thickness, animal weight, `Animal_RFID`, and `cattle_ID`, automatically creating cattle/animal records, reconciling farm ownership via geofences, and flagging unassigned scans for admin reassignment
- Cattle-to-farm updates cascade farm assignment to related animals and scans so lists stay consistent after edits
- Updated cattle edits to explicitly refresh related animals/scans with the new farm for consistent listings in drill-down views
- Cattle farm/birth-date edits now cascade to animals so cattle/animal detail pages show updated farm and birth data; animal scan links respect role-specific scan paths to avoid 404s
- Cattle updates now propagate farm + birth date to animals/scans; animal/cattle forms toggle between register/edit states based on context
- Fixed Animals form toggle (show/hide) so it initializes correctly when editing
- Added Geofence builder stub page per farm; store your province .gpkg/.geojson files outside git (e.g., `resources/geofence/`) and wire a backend endpoint to feed the map
- Scan viewer exposes ribeye area plus clarity/usability/label annotations, supports label-based filters, and includes a mask overlay toggle that highlights the segmentation in green
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
- Next.js build config now hard-wires the `@` alias so server builds resolve shared libs the same way as local dev
- Backend scan API schemas now explicitly allow `model_name` / `model_version` fields via a shared Pydantic config so dev/prod logs stay noise-free
- Shared cattle manager lets permitted roles define herds with born dates and external IDs for scan linkage
- Manage Database panel lets admins launch AWS sync jobs (add-only or add+remove) and review ingestion summaries in real time
- User administration page doubles as a pending-approval queue, so admins can review new registration requests, select roles, and approve or reject them in-app
- Scan listing supports label filters/badges, and scan detail pages now include a mask overlay toggle plus editable clarity/usability/label annotations
- Global dashboard navigation now adapts per role (admins only see admin tools; technicians/farmers only see their panels) while still offering Home/Scans shortcuts, sign-out, and branded routing, and the landing page keeps announcements and CTAs front-and-center for quick orientation
- Login view offers inline shortcuts back to the marketing home or the public registration form so users can recover from mistyped URLs quickly

## Running tests

The backend test suite now covers auth, profile, admin, farms, cattle/animals, scans, webhook flows, S3 helpers, and health probes (91 tests across `api/tests`). A PostgreSQL instance with PostGIS is required (`TEST_DATABASE_URL` defaults to `postgresql+psycopg2://postgres:postgres@localhost:5432/cti_test`).

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

✅ **Backend foundations**
- Alembic-backed schema covering auth, farms/devices, scans/assets/events, and grading scaffolding
- Auth + role enforcement with admin-only management APIs and comprehensive unit/integration tests in `tests/`
- Ingest webhook with JSON Schema validation, HMAC window enforcement, idempotency, and logging
- Scan listing/detail/statistics endpoints returning presigned URLs for assets
- Role-aware farm ownership enforced via `/farms` endpoints and `user_farms` association with dedicated tests
- Meta ingestion now persists all grading hints plus IMF/backfat/weight data, automatically linking scans to cattle/animals via `Animal_RFID`/`cattle_ID` or flagging them for admin assignment
- Test suite with **~85% coverage (91 tests)** across auth, profile, admin, farm, cattle/animal, scans, webhook, S3, and health flows

🚧 **Work in progress**
- Frontend dashboards beyond admin stubs (technician/farmer scan viewers and grading insights)
- AWS infrastructure wiring (EventBridge rule, Lambda signer, DLQ replay)
- Automated provisioning of environment secrets and TLS termination

🛣️ **Next milestones** (see ROADMAP for detail)
- Flesh out scan viewer, grading insights, and farmer reporting in the Next.js app
- Stand up worker pipeline for grading results and overlays
- Implement observability, lifecycle policies, and CI/CD deploy automation

# Run specific test files
pytest tests/test_auth.py
pytest tests/test_admin.py
pytest tests/test_webhooks.py
\`\`\`

**Test Coverage:** ~93% when Postgres is available (73 tests)
- Auth endpoints: 12 tests, 100% coverage ✅
- Admin endpoints: 16 tests, 83% coverage ✅
- Scans endpoints: 19 tests, 95% coverage ✅
- Webhooks: 6 tests, 89% coverage ✅
- S3 utilities: 6 tests, 100% coverage ✅
- Health checks: 2 tests, 100% coverage ✅

Tests use a separate PostgreSQL database (\`cti_test\`) and follow best practices with isolated fixtures.

## 🔑 Key API Endpoints

### Authentication
- `POST /auth/register` - Register user (first user becomes admin)
- `POST /auth/login` - Login (returns JWT token)
- `GET /me` - Current user profile with roles

### Profile Management
- `GET /me` - Get current user profile (email, name, phone, address, roles)
- `PUT /me` - Update user profile (name, phone, address)
- `POST /me/password` - Change password

### Admin
- `GET/POST /admin/users` - Manage users (admin only)
- `GET/POST /admin/devices` - Manage devices (admin)

### Farms
- `GET /farms` - List farms available to the current user (admins see all)
- `POST /farms` - Create a farm (admins, technicians, and farmers)
- `GET/PUT /farms/{farm_id}` - View or update farms you own; admins can update any farm
- `POST /farms/{farm_id}/members` - Add a user to the farm management group (admins any role, farmers technicians only)
- `DELETE /farms/{farm_id}/members/{user_id}` - Remove a user from the management group with the same role guardrails

### Cattle
- `GET /cattle` - List cattle groups scoped to the authenticated user's farms (admins see all)
- `POST /cattle` - Create a cattle group with optional external ID and born date
- `GET/PUT /cattle/{cattle_id}` - View or update cattle information (role-aware farm enforcement)

### Scans
- `GET /scans` - List scans with filtering and pagination (authenticated)
- `GET /scans/{scan_id}` - Get scan details with presigned URLs for assets
- `GET /scans/stats` - Get scan statistics (total, by status, recent)
- `POST /scans/{scan_id}/grade` - Trigger a grading run (admins and technicians)

### Ingest
- `POST /ingest/webhook` - Receive S3 notifications (HMAC required)

### Health
- `GET /healthz` - Health check
- `GET /readyz` - Database connectivity check

## 🎯 Project Status

✅ **Completed**
- Database schema with Alembic migrations
- User authentication and RBAC (with comprehensive tests)
- Webhook ingest with HMAC validation (with tests)
- Admin APIs for users and devices (with comprehensive tests)
- Role-aware farm APIs covering admins, technicians, and farmers (with comprehensive tests)
- PostGIS integration
- **S3 presigned URL generation for secure asset access**
- **Enhanced scans API with role-based filtering, statistics, and grading triggers**
- **Role-based scan dashboards delivering stats, signed media previews, and grading controls**
- **Webhook persistence of meta payloads with automatic farm assignment via PostGIS geofences**
- Test suite with **~93% coverage** (73 tests passing when Postgres is available)
  - Auth module: 100% coverage (12 tests)
  - Admin module: 83% coverage (16 tests)
  - Scans module: 95% coverage (19 tests)
  - Webhooks: 89% coverage (6 tests)
  - S3 utils: 100% coverage (6 tests)
  - Models & Schemas: 100% coverage
  - Security module: 100% coverage

🚧 **In Progress**
- Expanded analytics overlays (timeline, annotations) for scan viewer
- AWS integration (EventBridge, Lambda, DLQ)

📋 **Planned**
- Grading worker pipeline
- Herd-level reporting and notifications for farmers
- Monitoring and CI/CD

See [ROADMAP.md](ROADMAP.md) for details.

## 🔒 Security

- HMAC signatures for webhooks
- JWT tokens for API auth
- RBAC with three roles
- CORS protection
- Store secrets in environment variables

## 📦 Environment Variables

\`\`\`bash
# API
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/cti
JWT_SECRET=your_secret_here
HMAC_SECRET=your_secret_here
CORS_ORIGINS=http://localhost:3000
## Security posture

- JWT auth with bcrypt hashing and expiry windows
- HMAC-signed webhooks with timestamp drift enforcement
- Strict CORS configuration derived from `CORS_ORIGINS` env var
- Role checks for admin surfaces in both API and dashboard routes

## License

Specify project license before release.
