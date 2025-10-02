# Testing Documentation

## Overview

The CTI Dashboard project includes a comprehensive test suite for the API backend with 70%+ code coverage.

## Running Tests

### Prerequisites

1. **PostgreSQL with PostGIS must be running:**
   ```bash
   docker compose up -d db
   ```

2. **Test databases must be created:**
   ```bash
   # Create test databases
   docker exec cti-dashboard-db-1 psql -U postgres -c "CREATE DATABASE cti_test;"
   docker exec cti-dashboard-db-1 psql -U postgres -c "CREATE DATABASE cti_test_no_roles;"
   
   # Enable PostGIS extension
   docker exec cti-dashboard-db-1 psql -U postgres -d cti_test -c "CREATE EXTENSION IF NOT EXISTS postgis;"
   docker exec cti-dashboard-db-1 psql -U postgres -d cti_test_no_roles -c "CREATE EXTENSION IF NOT EXISTS postgis;"
   ```

### Run All Tests

```bash
cd api
source .venv/bin/activate
pytest
```

### Run with Verbose Output

```bash
pytest -v
```

### Run Specific Test File

```bash
pytest tests/test_auth.py
pytest tests/test_health.py
```

### Run Specific Test

```bash
pytest tests/test_auth.py::test_register_first_user_becomes_admin
```

### Generate Coverage Report

```bash
# Terminal report
pytest --cov-report=term-missing

# HTML report
pytest --cov-report=html
# Open htmlcov/index.html in browser
```

## Test Suite

### Authentication Tests (`tests/test_auth.py`)

- ✅ `test_register_first_user_becomes_admin` - Verifies first user gets admin role
- ✅ `test_register_second_user_becomes_technician` - Verifies subsequent users get technician role
- ✅ `test_register_duplicate_email` - Verifies duplicate email rejection
- ✅ `test_register_without_roles_seeded` - Verifies graceful failure when roles not seeded
- ✅ `test_login_success` - Verifies successful login returns JWT token
- ✅ `test_login_invalid_credentials` - Verifies invalid password is rejected
- ✅ `test_login_nonexistent_user` - Verifies nonexistent user is rejected
- ✅ `test_me_endpoint` - Verifies /me returns user info with roles
- ✅ `test_me_endpoint_unauthorized` - Verifies /me requires authentication
- ✅ `test_me_endpoint_invalid_token` - Verifies /me rejects invalid tokens
- ✅ `test_register_validates_email_format` - Verifies email validation
- ✅ `test_password_is_hashed` - Verifies passwords are hashed, not stored in plain text

### Health Check Tests (`tests/test_health.py`)

- ✅ `test_health_endpoint` - Verifies /healthz returns ok status
- ✅ `test_readiness_endpoint` - Verifies /readyz checks database connectivity

## Coverage Report

| Module | Coverage | Notes |
|--------|----------|-------|
| `app/routers/auth.py` | 100% | Full coverage of authentication logic |
| `app/routers/me.py` | 96% | Nearly complete coverage |
| `app/models.py` | 100% | All models covered |
| `app/schemas.py` | 100% | All schemas covered |
| `app/security.py` | 100% | Password hashing and JWT covered |
| `app/main.py` | 92% | Main app setup covered |
| **Overall** | **70.92%** | Exceeds 70% target |

## Test Database Strategy

The test suite uses PostgreSQL with PostGIS, not SQLite, because the production code uses PostGIS geometry types that aren't compatible with SQLite.

- **Main test database:** `cti_test` - used for most tests
- **No-roles database:** `cti_test_no_roles` - used to test error handling when roles aren't seeded

Each test function gets a fresh database state with automatic cleanup.

## Continuous Integration

Tests should be run in CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    docker compose up -d db
    sleep 10
    docker exec cti-dashboard-db-1 psql -U postgres -c "CREATE DATABASE cti_test;"
    docker exec cti-dashboard-db-1 psql -U postgres -d cti_test -c "CREATE EXTENSION IF NOT EXISTS postgis;"
    cd api
    pip install -r requirements.txt
    pytest --cov-fail-under=70
```

## Adding New Tests

### Test File Structure

```python
# tests/test_feature.py
"""Test description."""

def test_something(client, test_db):
    """Test that something works."""
    # Arrange
    data = {"key": "value"}
    
    # Act
    response = client.post("/endpoint", json=data)
    
    # Assert
    assert response.status_code == 200
    assert response.json() == expected
```

### Using Fixtures

Available fixtures from `conftest.py`:

- `client` - TestClient with test database
- `test_db` - Test database session with roles seeded
- `client_without_roles` - TestClient without roles seeded
- `test_db_without_roles` - Test database without roles

## Troubleshooting

### Database connection errors

Ensure PostgreSQL is running:
```bash
docker compose ps db
```

### Test databases don't exist

Recreate them:
```bash
docker exec cti-dashboard-db-1 psql -U postgres -c "DROP DATABASE IF EXISTS cti_test;"
docker exec cti-dashboard-db-1 psql -U postgres -c "DROP DATABASE IF EXISTS cti_test_no_roles;"
# Then create them again (see Prerequisites section)
```

### PostGIS errors

Ensure PostGIS extension is enabled:
```bash
docker exec cti-dashboard-db-1 psql -U postgres -d cti_test -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

### "column users.updated_at does not exist" error

This error occurs when the database was created using an older method (before Alembic migrations). The solution is to either:

**Option 1:** Drop and recreate databases:
```bash
cd /home/runner/work/cti-dashboard/cti-dashboard
docker compose exec db psql -U postgres -c "DROP DATABASE IF EXISTS cti;"
docker compose exec db psql -U postgres -c "DROP DATABASE IF EXISTS cti_test;"
docker compose exec db psql -U postgres -c "DROP DATABASE IF EXISTS cti_test_no_roles;"
docker compose exec db psql -U postgres -c "CREATE DATABASE cti;"
docker compose exec db psql -U postgres -c "CREATE DATABASE cti_test;"
docker compose exec db psql -U postgres -c "CREATE DATABASE cti_test_no_roles;"
docker compose exec db psql -U postgres -d cti -c "CREATE EXTENSION IF NOT EXISTS postgis;"
docker compose exec db psql -U postgres -d cti_test -c "CREATE EXTENSION IF NOT EXISTS postgis;"
docker compose exec db psql -U postgres -d cti_test_no_roles -c "CREATE EXTENSION IF NOT EXISTS postgis;"

cd api
alembic upgrade head
```

**Option 2:** Add the missing column manually (if you have data to preserve):
```bash
docker compose exec db psql -U postgres -d cti -c "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();"
docker compose exec db psql -U postgres -d cti_test -c "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();"
```

### Coverage too low

Add more tests for uncovered modules. Focus on:
- Error handling paths
- Edge cases
- Integration tests for complex workflows

## Future Test Additions

- [ ] Admin endpoint tests
- [ ] Scan management tests
- [ ] Webhook ingestion tests
- [ ] HMAC signature validation tests
- [ ] File upload tests
- [ ] PostGIS geometry tests
- [ ] Performance tests
- [ ] Load tests
