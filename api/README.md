# CTI Dashboard API

FastAPI backend for the CTI platform. It exposes authentication, admin management, scan browsing, and ingest webhook endpoints backed by PostgreSQL + PostGIS.

## Prerequisites

- Python 3.11+
- Postgres 15 with PostGIS (use `docker compose up -d db` from the repo root)
- `pip`, `virtualenv`, and `alembic`

## Local setup

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The service reads configuration from environment variables (see `.env.example` or create `api/.env`):

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/cti
JWT_SECRET=change_me
HMAC_SECRET=change_me
CORS_ORIGINS=http://localhost:3000
```

## API Endpoints

### Authentication

- `POST /auth/register` - Register new user
- `POST /auth/login` - Login (returns JWT token)
- `GET /me` - Get current user info with roles

### Profile Management

- `GET /me` - Get current user profile (includes email, full_name, phone_number, address, roles)
- `PUT /me` - Update user profile information
  - Body: `{"full_name": "...", "phone_number": "...", "address": "..."}`
  - All fields optional
  - Returns updated profile
- `POST /me/password` - Change user password
  - Body: `{"current_password": "...", "new_password": "..."}`
  - Validates current password before updating
  - Returns success message

### Health Checks

- `GET /healthz` - Basic health check
- `GET /readyz` - Database connectivity check

### Admin

- `GET/POST /admin/users` - User management
- `GET/POST /admin/devices` - Device registry
- `POST /admin/database/sync-scans` - Trigger AWS scan reconciliation (add-only or add+remove) using the same ingest path as the webhook

### Farms

- `GET /farms` - List farms scoped to the authenticated user (admins see all)
- `POST /farms` - Create a farm (admins, technicians, and farmers)
- `GET/PUT /farms/{farm_id}` - View/update farms the caller owns; admins can update anyone's farm
- `POST /farms/{farm_id}/members` - Add a user to the farm management group (admins any role, farmers technicians only)
- `DELETE /farms/{farm_id}/members/{user_id}` - Remove a user from the management group with the same role restrictions

### Cattle

- `GET /cattle` - List cattle groups (admins see all, others are scoped to their farms)
- `POST /cattle` - Create a cattle group with optional external ID and born date
- `GET/PUT /cattle/{cattle_id}` - View or update cattle metadata (role-aware farm enforcement)

### Animals

- `GET /animals` - List animals tied to the caller's farms (admins can see all)
- `POST /animals` - Create an animal with optional RFID/tag metadata and farm/cattle linkage
- `GET/PUT /animals/{animal_id}` - View or update an animal record with the same farm guardrails

### Scans

- `GET /scans` - List scans with pagination and role-aware scoping
- `GET /scans/{scan_id}` - Retrieve scan details with presigned asset URLs and grading history
- `GET /scans/stats` - Aggregate totals and status breakdown (role aware)
- `POST /scans/{scan_id}/grade` - Trigger a grading record (admins & technicians)
- `PATCH /scans/{scan_id}` - Update review metadata (label, clarity, usability) for a scan

### Announcements

- `GET /announcements` - Public feed of admin-approved announcements shown on the landing page
- `GET /admin/announcements` - Admin-only listing of all announcements
- `POST /admin/announcements` - Create a new announcement (rich-text HTML, optional landing-page visibility)
## Key modules

- `app/main.py` – FastAPI application, middleware, and routers
- `app/db.py` – SQLAlchemy engine + session configuration
- `app/models.py` – ORM models for auth, farms/devices, scans/assets/events, grading
- `app/routers/` – API routers
  - `auth.py` – register/login endpoints, role seeding
  - `me.py` – current user info via bearer token
  - `admin.py` – user/device management (admin-only)
  - `farms.py` – farm management with role-aware ownership controls
  - `cattle.py` – cattle manager endpoints
  - `scans.py` – scan list/detail/stats, grading actions, and presigned URLs
  - `webhooks.py` – signed ingest webhook that stores meta payloads (IMF/backfat/weight/Animal_RFID/cattle_ID) and auto-assigns farms/cattle/animals using geofences
- `app/s3_utils.py` – presigned URL helper
- `app/schemas/meta_v1.json` – ingest contract enforced on webhook payloads

## Running tests

Tests require a running PostgreSQL instance with PostGIS. By default the suite connects to `postgresql+psycopg2://postgres:postgres@localhost:5432/cti_test`. Override `TEST_DATABASE_URL` to point at a prepared test database if needed.

```bash
cd api
source .venv/bin/activate
pytest
```

`pytest.ini` adds coverage reporting (`--cov=app --cov-report=term-missing --cov-report=html`) and enforces a 70% minimum; the current suite passes at roughly 85% coverage. The suite covers:

- Authentication flows (`tests/test_auth.py`)
- Admin management (`tests/test_admin.py`)
- Scan APIs (`tests/test_scans.py`)
- Webhook security & schema validation (`tests/test_webhooks.py`)
- S3 helper utilities (`tests/test_s3_utils.py`)
- Health probes (`tests/test_health.py`)

See the repo-level [TESTING.md](../TESTING.md) for instructions on provisioning the test databases and enabling PostGIS extensions.

## Common issues

- **Connection refused / missing database** – ensure Postgres is running and the `cti`, `cti_test`, and `cti_test_no_roles` databases exist with PostGIS enabled.
- **`Database not properly initialized` during registration** – run Alembic migrations to seed default roles (`alembic upgrade head`).
- **HMAC signature failures** – verify `HMAC_SECRET` matches the value used by the uploader/Lambda.

## Development tooling

```bash
# Formatting
black app tests

# Linting
ruff check app tests

# Type checking
mypy app
```

## Structure

```
app/
├── db.py
├── main.py
├── models.py
├── routers/
│   ├── admin.py
│   ├── auth.py
│   ├── me.py
│   ├── scans.py
│   └── webhooks.py
├── s3_utils.py
├── schemas/
│   └── meta_v1.json
└── security.py
```

## Licensing

Specify the project license before shipping.
