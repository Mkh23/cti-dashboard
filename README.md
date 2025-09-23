# CTI Dashboard Starter (Pi → AWS S3 → Server)

A production‑ready starter to build your cattle ultrasound (US) grading dashboard.

## Stack
- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind CSS
- **Backend**: FastAPI (JWT auth, role-based access), SQLAlchemy
- **DB**: PostgreSQL 15 + PostGIS (Docker)
- **Local Dev**: Docker Compose (DB only), `uvicorn` for API, `next dev` for web

> AWS side (Pi → S3 → Lambda) already exists. This repo covers **everything on your Linux server**: API, DB, Dashboard UI.

---

## 0) Prereqs (Windows)
- **Recommended**: WSL2 + Ubuntu 22.04
- Docker Desktop (enable WSL integration)
- Node.js 20 LTS + pnpm (`npm i -g pnpm`)
- Python 3.11 (`py -3.11 -m venv .venv` on Windows, or `python3.11 -m venv .venv` on WSL)
- Git + GitHub account

## 1) Clone & bootstrap
```bash
# A) Create empty repo on GitHub first (e.g., cti-dashboard)

# B) Locally
git clone <your-repo-url> cti-dashboard
cd cti-dashboard

# If you downloaded this starter zip:
# unzip it so that files land in this folder, then:
git add .
git commit -m "chore: import CTI dashboard starter"
git push origin main
```

## 2) Start database (Docker)
```bash
docker compose up -d db
```

## 3) Run API (FastAPI)
```bash
cd api
cp .env.example .env  # adjust secrets if needed
python -m venv .venv && source .venv/bin/activate  # (on Windows PowerShell: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will auto-create tables on first run and seed default roles. Visit http://localhost:8000/docs

## 4) Run Web (Next.js)
```bash
cd ../web
cp .env.local.example .env.local
pnpm install
pnpm dev
```

Open http://localhost:3000. Use the **Login** page to create an admin first:
- Register at `POST /auth/register` via Swagger or call from the Login page (email+password).
- Then log in; you’ll be routed to your role dashboard.

## 5) Environments
- **Local**: as above
- **Server (Linux)**: use the same Docker db; run API with `gunicorn`/`uvicorn` behind **Traefik**/**Nginx**; build Next.js (`pnpm build`, `pnpm start`)

## 6) Next steps
- Hook S3/Lambda → server: add an AWS webhook receiver in `api/app/routers/webhooks.py`
- Replace `create_all()` with Alembic migrations
- Wire your PostGIS spatial columns for farms, geofences, parcels
- Build role-specific pages and shared components incrementally

Enjoy!
