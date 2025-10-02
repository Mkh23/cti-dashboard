# CTI Dashboard — Cattle Tech Imaging Platform

A production-ready platform for capturing bovine ultrasound images, validating and ingesting them via AWS S3, and presenting actionable insights through a role-based dashboard.

**Flow:** Pi → S3 (raw) → EventBridge/Lambda (signed webhook) → FastAPI (ingest) → Postgres/PostGIS → Worker (grading) → Next.js 14 Dashboard

## 📚 Documentation

- [PROJECT_DESCRIPTION.md](PROJECT_DESCRIPTION.md) - Project overview, architecture, and goals
- [ROADMAP.md](ROADMAP.md) - Detailed roadmap with checklists
- [DATA_MODEL.md](DATA_MODEL.md) - Database schema, contracts, and examples

## Repo Structure
cti-dashboard/
├─ api/ # FastAPI app + Alembic
│ ├─ app/ # application code
│ ├─ alembic/ # migrations
│ ├─ requirements.txt
│ └─ .env # DATABASE_URL, JWT_SECRET, etc.
├─ web/ # Next.js 14 (TypeScript + Tailwind)
│ └─ .env.local # NEXT_PUBLIC_API_BASE=http://localhost:8000
├─ scripts/
│ └─ dev.sh # one-command dev launcher (migrations included)
├─ docker-compose.yml # Postgres+PostGIS
├─ DATA_MODEL.md
├─ PROJECT_DESCRIPTION.md
├─ ROADMAP.md
└─ README.md

## Prereqs
- Docker & Docker Compose
- Python 3.11+
- Node 20 LTS + `pnpm`
- WSL2 (if on Windows)

## Quick Start (Dev)

### 1) One command
```bash
./scripts/dev.sh
```
** This will: **
Start Postgres container, wait until ready
Ensure DB exists and PostGIS is enabled
Activate API venv (create if missing) and install deps (if needed)
Export api/.env and run alembic upgrade head
Launch Uvicorn (API) and Next.js dev server (Web)

### 2) URLs

API docs: http://localhost:8000/docs

Web app: http://localhost:3000

### 3) Create first admin
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"StrongPass!123"}'
```
The first user becomes admin automatically.

## Environment Variables
api/.env
```
# If absent, dev.sh injects a sensible default for dev
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/cti
JWT_SECRET=change_me
HMAC_SECRET=change_me
CORS_ORIGINS=http://localhost:3000
```

web/.env.local
```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

## Key Endpoints
POST /auth/register — Register user (first user = admin)
POST /auth/login — JWT auth
GET /me — Current user
GET/POST /admin/farms
GET/POST /admin/devices
POST /ingest/webhook — S3 notifications (HMAC-signed)
GET /healthz — Health check

## 🛠 Stack

- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind CSS
- **Backend**: FastAPI + SQLAlchemy + Alembic + PostGIS
- **Database**: PostgreSQL 15 + PostGIS
- **Auth**: JWT with RBAC (admin/technician/farmer)
- **AWS**: S3, EventBridge, Lambda, Secrets Manager

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ 
- Node.js 20 LTS + pnpm
- Git

### 1. Start Database

\`\`\`bash
docker compose up -d db
\`\`\`

### 2. Set Up API

\`\`\`bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run migrations to create all tables
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
\`\`\`

API available at http://localhost:8000/docs

**⚠️ Important:** Always run `alembic upgrade head` before starting the API server to ensure the database schema is up to date.

### 3. Create Admin User

\`\`\`bash
curl -X POST http://localhost:8000/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{"email": "admin@example.com", "password": "StrongPass!123"}'
\`\`\`

First user automatically becomes admin.

### 4. Set Up Dashboard (Optional)

\`\`\`bash
cd web
pnpm install
echo "NEXT_PUBLIC_API_BASE=http://localhost:8000" > .env.local
pnpm dev
\`\`\`

Dashboard at http://localhost:3000

## 🧪 Running Tests

\`\`\`bash
cd api
source .venv/bin/activate
pytest
\`\`\`

Tests use a separate PostgreSQL database (\`cti_test\`) and achieve 70%+ coverage.

## 🔑 Key API Endpoints

- \`POST /auth/register\` - Register user (first user becomes admin)
- \`POST /auth/login\` - Login (returns JWT token)
- \`GET /me\` - Current user profile with roles
- \`GET/POST /admin/farms\` - Manage farms (admin)
- \`GET/POST /admin/devices\` - Manage devices (admin)
- \`POST /ingest/webhook\` - Receive S3 notifications (HMAC required)
- \`GET /healthz\` - Health check
- \`GET /readyz\` - Database connectivity check

## 🎯 Project Status

✅ **Completed**
- Database schema with Alembic migrations
- User authentication and RBAC (with comprehensive tests)
- Webhook ingest with HMAC validation
- Admin APIs for users, farms, devices
- PostGIS integration
- Test suite with 70%+ coverage

🚧 **In Progress**
- Dashboard UI components
- Scans management API

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

# Web
NEXT_PUBLIC_API_BASE=http://localhost:8000
\`\`\`

## 📄 License

[Specify your license]
