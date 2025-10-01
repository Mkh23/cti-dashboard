# CTI Dashboard — Cattle Tech Imaging Platform

A production-ready platform for capturing bovine ultrasound images, validating and ingesting them via AWS S3, and presenting actionable insights through a role-based dashboard.

**Flow:** Pi → S3 (raw) → EventBridge/Lambda (signed webhook) → FastAPI (ingest) → Postgres/PostGIS → Worker (grading) → Next.js 14 Dashboard

## 📚 Documentation

- [PROJECT_DESCRIPTION.md](PROJECT_DESCRIPTION.md) - Project overview, architecture, and goals
- [ROADMAP.md](ROADMAP.md) - Detailed roadmap with checklists
- [DATA_MODEL.md](DATA_MODEL.md) - Database schema, contracts, and examples

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
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
\`\`\`

API available at http://localhost:8000/docs

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

## 🔑 Key API Endpoints

- \`POST /auth/register\` - Register user
- \`POST /auth/login\` - Login
- \`GET /me\` - Current user profile
- \`GET/POST /admin/farms\` - Manage farms (admin)
- \`GET/POST /admin/devices\` - Manage devices (admin)
- \`POST /ingest/webhook\` - Receive S3 notifications (HMAC required)
- \`GET /healthz\` - Health check

## 🎯 Project Status

✅ **Completed**
- Database schema with Alembic migrations
- User authentication and RBAC
- Webhook ingest with HMAC validation
- Admin APIs for users, farms, devices
- PostGIS integration

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
