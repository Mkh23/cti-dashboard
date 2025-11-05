# Testing Documentation

## Overview

The FastAPI backend ships with a comprehensive pytest suite that exercises authentication, admin management, scan endpoints, webhook ingest, S3 helpers, and health checks. Coverage enforcement is configured at 70% (`pytest --cov-fail-under=70`), and with a running Postgres/PostGIS instance the suite typically reports coverage in the low 90s.

## Prerequisites

1. **PostgreSQL 15 + PostGIS running locally** (recommended via Docker Compose):
   ```bash
   docker compose up -d db
   ```

2. **Create and prepare test databases** (`cti_test`, `cti_test_no_roles`), both with PostGIS enabled:
   ```bash
   # (Ignore errors if the databases already exist)
   docker compose exec db psql -U postgres -c "CREATE DATABASE cti_test;" || true
   docker compose exec db psql -U postgres -c "CREATE DATABASE cti_test_no_roles;" || true
   docker compose exec db psql -U postgres -d cti_test -c "CREATE EXTENSION IF NOT EXISTS postgis;"
   docker compose exec db psql -U postgres -d cti_test_no_roles -c "CREATE EXTENSION IF NOT EXISTS postgis;"
   ```

3. **Set `TEST_DATABASE_URL` if you use a custom connection string.** Defaults to `postgresql+psycopg2://postgres:postgres@localhost:5432/cti_test`.

## Running the suite

```bash
cd api
source .venv/bin/activate
pytest --cov=app --cov-report=term-missing
```

To inspect the HTML coverage report:

```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html  # or xdg-open on Linux
```

Run specific files or tests:

```bash
pytest tests/test_auth.py
pytest tests/test_admin.py::test_list_users_as_admin
```

## Test coverage map

- `tests/test_auth.py` – registration, login, /me, role seeding
- `tests/test_admin.py` – admin-only CRUD for users, farms, devices
- `tests/test_scans.py` – pagination, filtering, detail, stats, presigned URLs
- `tests/test_webhooks.py` – HMAC validation, schema enforcement, idempotency
- `tests/test_s3_utils.py` – presigned URL helper edge cases
- `tests/test_health.py` – healthz/readyz endpoints
- Fixtures in `tests/conftest.py` spin up fresh databases per test and seed default roles when required.

## Troubleshooting

- **`psycopg2.OperationalError: connection refused`** – ensure Postgres is running and accessible on the expected host/port.
- **`Database not properly initialized. Please run migrations`** – execute `alembic upgrade head` against the primary database before running tests.
- **`meta.json` schema failures** – confirm ingest payloads align with `app/schemas/meta_v1.json`.
- **Coverage below threshold** – expand test scenarios for uncovered branches (see coverage report) or verify PostGIS is enabled so geometry columns can be created.

## CI recommendations

A minimal GitHub Actions step for running the suite:

```yaml
- name: Run API tests
  run: |
    docker compose up -d db
    sleep 10
    docker compose exec db psql -U postgres -c "CREATE DATABASE cti_test;" || true
    docker compose exec db psql -U postgres -d cti_test -c "CREATE EXTENSION IF NOT EXISTS postgis;"
    docker compose exec db psql -U postgres -c "CREATE DATABASE cti_test_no_roles;" || true
    docker compose exec db psql -U postgres -d cti_test_no_roles -c "CREATE EXTENSION IF NOT EXISTS postgis;"
    cd api
    pip install -r requirements.txt
    pytest --cov=app --cov-report=term-missing
```

## Future additions

- PostGIS-specific geometry assertions
- Browser-based E2E flows (Playwright/Cypress)
- Load and soak testing for `/ingest/webhook`
- Security regression suite (signature tampering, replay attempts)
