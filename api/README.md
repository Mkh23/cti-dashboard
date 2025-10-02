# CTI Dashboard API

FastAPI backend for the CTI (Cattle Tech Imaging) platform.

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15 with PostGIS extension
- Docker & Docker Compose (recommended)

### Installation

1. **Start the database:**

```bash
# From project root
docker compose up -d db
```

2. **Set up Python environment:**

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. **Run migrations:**

```bash
alembic upgrade head
```

This will:
- Create all database tables
- Seed default roles (admin, technician, farmer)
- Enable PostGIS extension

4. **Start the API:**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at http://localhost:8000  
Swagger docs at http://localhost:8000/docs

## First User Registration

The first user to register automatically becomes an admin:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "StrongPass!123"}'
```

All subsequent users are assigned the **technician** role by default.

## Testing

### Running Tests

```bash
# Run all tests with coverage
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_auth.py

# Generate coverage report
pytest --cov-report=html
# Open htmlcov/index.html in browser
```

### Test Requirements

Tests use a separate PostgreSQL database (`cti_test`). Make sure the database server is running:

```bash
docker compose up -d db
```

Test databases are automatically created and cleaned up by the test fixtures.

### Current Coverage

- **Overall:** 70%+
- **Auth module:** 100%
- **Models:** 100%
- **Schemas:** 100%
- **Security:** 100%

## Environment Variables

Create a `.env` file or set environment variables:

```bash
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/cti
JWT_SECRET=your_secret_here_change_in_production
HMAC_SECRET=your_hmac_secret_here
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

## API Endpoints

### Authentication

- `POST /auth/register` - Register new user
- `POST /auth/login` - Login (returns JWT token)
- `GET /me` - Get current user info with roles

### Health Checks

- `GET /healthz` - Basic health check
- `GET /readyz` - Database connectivity check

### Admin

- `GET/POST /admin/users` - User management
- `GET/POST /admin/farms` - Farm management
- `GET/POST /admin/devices` - Device registry

### Scans

- `GET /scans` - List scans with filters
- `GET /scans/{scan_id}` - Get scan details

### Ingest

- `POST /ingest/webhook` - Webhook endpoint for S3 notifications (HMAC required)

## Common Issues

### "Database not properly initialized" error

This error occurs when roles aren't seeded in the database. Run migrations:

```bash
alembic upgrade head
```

### PostGIS extension not found

Install PostGIS in your PostgreSQL database:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

Or use the provided Docker Compose setup which includes PostGIS.

### Tests failing with geometry errors

Make sure you're using PostgreSQL with PostGIS, not SQLite. The test configuration uses a PostgreSQL test database.

## Development

### Code Quality

```bash
# Format code
black app tests

# Lint
ruff check app tests

# Type checking
mypy app
```

### Database Migrations

Create a new migration:

```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:

```bash
alembic upgrade head
```

Rollback:

```bash
alembic downgrade -1
```

## Architecture

- **Framework:** FastAPI
- **ORM:** SQLAlchemy 2.0 with async support
- **Database:** PostgreSQL 15 + PostGIS
- **Auth:** JWT tokens with bcrypt password hashing
- **Migrations:** Alembic
- **Testing:** pytest with test database isolation

## Project Structure

```
api/
├── app/
│   ├── routers/       # API endpoint handlers
│   │   ├── auth.py    # Authentication endpoints
│   │   ├── me.py      # User profile endpoint
│   │   ├── admin.py   # Admin management endpoints
│   │   ├── scans.py   # Scan management
│   │   └── webhooks.py # S3 webhook ingestion
│   ├── models.py      # SQLAlchemy models
│   ├── schemas.py     # Pydantic schemas
│   ├── security.py    # Password hashing, JWT
│   ├── db.py          # Database connection
│   └── main.py        # FastAPI app setup
├── tests/
│   ├── conftest.py    # Test configuration
│   ├── test_auth.py   # Auth endpoint tests
│   └── test_health.py # Health check tests
├── alembic/           # Database migrations
├── requirements.txt   # Python dependencies
└── pytest.ini         # Test configuration
```

## License

[Specify your license]
