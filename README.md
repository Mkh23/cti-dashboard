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
  -d '{"email":"admin@example.com","password":"StrongPass!123"}'
```

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

## API highlights

- Auth & RBAC (`/auth`, `/me`)
- Admin management for users, farms, and devices (`/admin/*`)
- Scan browsing, detail views, and stats (`/scans`) with presigned URLs via `app/s3_utils.py`
- HMAC-protected ingest webhook validating `meta_v1.json` and persisting scans/assets/events/logs
- Health & readiness probes (`/healthz`, `/readyz`)

## Running tests

The backend test suite exercises auth, admin, scans, webhook flows, and S3 helpers (61 tests across `tests/`). A PostgreSQL instance with PostGIS is required (`TEST_DATABASE_URL` defaults to `postgresql+psycopg2://postgres:postgres@localhost:5432/cti_test`).

```bash
cd api
source .venv/bin/activate
pytest --cov=app --cov-report=term-missing
```

`pytest.ini` enforces `--cov-fail-under=70`; with a running Postgres service the suite passes and typically reports coverage in the low 90s. See [TESTING.md](TESTING.md) for database bootstrap steps and troubleshooting.

## Project status snapshot

✅ **Backend foundations**
- Alembic-backed schema covering auth, farms/devices, scans/assets/events, and grading scaffolding
- Auth + role enforcement with admin-only management APIs and comprehensive unit/integration tests in `tests/`
- Ingest webhook with JSON Schema validation, HMAC window enforcement, idempotency, and logging
- Scan listing/detail/statistics endpoints returning presigned URLs for assets

🚧 **Work in progress**
- Frontend dashboards beyond admin stubs (technician/farmer flows and scan viewers)
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

**Test Coverage:** 92.93% (61 tests passing)
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
- `GET/POST /admin/farms` - Manage farms (admin)
- `GET/POST /admin/devices` - Manage devices (admin)

### Scans
- `GET /scans` - List scans with filtering and pagination (authenticated)
- `GET /scans/{scan_id}` - Get scan details with presigned URLs for assets
- `GET /scans/stats` - Get scan statistics (total, by status, recent)

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
- Admin APIs for users, farms, devices (with comprehensive tests)
- PostGIS integration
- **S3 presigned URL generation for secure asset access**
- **Enhanced scans API with role-based filtering and statistics**
- Test suite with **92.93% coverage** (61 tests passing)
  - Auth module: 100% coverage (12 tests)
  - Admin module: 83% coverage (16 tests)
  - Scans module: 95% coverage (19 tests)
  - Webhooks: 89% coverage (6 tests)
  - S3 utils: 100% coverage (6 tests)
  - Models & Schemas: 100% coverage
  - Security module: 100% coverage

🚧 **In Progress**
- Dashboard UI components
- Scans management API
- AWS integration (EventBridge, Lambda, DLQ)

📋 **Planned**
- Grading worker pipeline
- Farmer and Technician dashboards
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
