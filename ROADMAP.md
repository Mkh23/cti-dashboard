# CTI Dashboard — Step-by-Step Roadmap (Repo-Aware)

This roadmap reflects **what’s already in your GitHub repo** and what’s left to build. Boxes **[x]** = done in repo now, **[ ]** = to do, **[~]** = stub/partial.

> Source of truth I checked:
> - Repo layout shows `api/`, `web/`, `scripts/`, `.gitignore`, `docker-compose.yml`, and a detailed README with local run steps【see repo README lines showing stack and run steps】.  
> - README indicates: Dockerized Postgres, FastAPI that **auto-creates tables and seeds default roles**, Swagger at `http://localhost:8000/docs`, and a Next.js app with a Login/Register flow and `.env` examples【README shows DB start, API run, Web run, and notes that API will auto-create tables; login/register from web or Swagger】.  
>   (Specifically: stack + local dev sections + “API will auto-create tables… seed default roles… visit /docs” and “Open :3000, use Login page to create an admin” are present.) :contentReference[oaicite:0]{index=0}
>   Github repo: https://github.com/Mkh23/cti-dashboard

---

## Phase 0 — Repo & Environments
**Goal:** Monorepo skeleton, envs wired, “Hello World” for API & Web.

- [x] Monorepo structure present: `api/` (FastAPI), `web/` (Next.js), `scripts/`, `docker-compose.yml`, README. :contentReference[oaicite:1]{index=1}
- [x] Local DB via **Docker Compose** (`docker compose up -d db`). :contentReference[oaicite:2]{index=2}
- [x] API boots with `uvicorn` and **Swagger** at `http://localhost:8000/docs`. :contentReference[oaicite:3]{index=3}
- [x] Web boots with `pnpm dev` at `http://localhost:3000`. Login/Register flow scaffolded. :contentReference[oaicite:4]{index=4}
- [x] `.env.example` / `.env.local.example` provided in `api/` and `web/`. :contentReference[oaicite:5]{index=5}

**Exit criteria:** You can start DB, run API, and open Web locally (per README). ✔️

---

## Phase 1 — Database Schema & Migrations
**Goal:** Implement the **canonical Postgres + PostGIS schema** with migrations.

- [~] **Temporary `create_all()`** behavior exists (API “auto-creates tables and seeds roles”). Replace with Alembic. :contentReference[oaicite:6]{index=6}
- [ ] Translate your **ERD.dbml** schema into SQLAlchemy models exactly (types, FKs, indexes).
- [ ] Add **Alembic** migrations; remove `create_all()` in favor of `alembic upgrade head`.
- [ ] Seed script for base data (roles; demo farm/device/users).

**Exit criteria:** `alembic upgrade head` creates the full schema; seed loads without errors.

---

## Phase 2 — AuthN/Z & RBAC
**Goal:** Secure API and role-based app shell.

- [~] **Auth endpoints exist** (README references `POST /auth/register` and login via Web). :contentReference[oaicite:7]{index=7}
- [ ] Implement JWT **access/refresh** httpOnly cookies, `/auth/refresh`, `/me`.
- [ ] Add server-side guards (RBAC) and client route guards (`/dashboard/{admin|technician|farmer}`).
- [ ] Global 401 handler with silent refresh → logout fallback.

**Exit criteria:** Login redirects to the correct role dashboard; protected routes enforced.

---

## Phase 3 — Admin Surfaces (Users, Farms, Devices)
**Goal:** Minimal admin to support technician/farmer flows.

- [ ] **Users**: list/create/edit/activate + role assignment (+ audit logging).
- [ ] **Farms**: list/detail; **GeoJSON geofence** render; centroid display.
- [ ] **Devices**: list/register; associate to farm; show `last_seen_at`.
- [ ] API: `GET/POST/PUT` for users/farms/devices with RBAC checks.

**Exit criteria:** Admin can create farm (with geofence), register device, create users.

---

## Phase 4 — Ingestion Path (AWS → API)
**Goal:** Create scans from S3 “triplets” (img/msk/meta).

- [ ] `POST /ingest/webhook` with **HMAC** verification & **idempotency** on `ingest_key`.
- [ ] Persist **assets**, **scans**, **ingestion_log**, and **scan_events`.
- [ ] (Optional) Resolve `farm_id` by **GPS geofence** → status `located`.
- [ ] CLI/dev endpoint to simulate webhook payload.

**Exit criteria:** Sending a sample payload creates assets + a scan (`received`/`located`) visible in queue.

---

## Phase 5 — Technician Scans Queue & Detail
**Goal:** Core technician workflow.

- [ ] List: `GET /scans?status=...` with filters (status/farm/device/date).
- [ ] Detail: image viewer (zoom/pan) + **mask overlay toggle**, meta panel, timeline from `scan_events`.
- [ ] Actions: **Validate** (`/scans/{id}/validate`), set **quality** (`good|ok|poor`), **Link animal**, **Add note**.
- [ ] Optimistic updates with rollback and toasts.

**Exit criteria:** Tech can validate a new scan, set quality, link an animal, and see legal status transitions.

---

## Phase 6 — Asset Viewing (Signed URL Proxy)
**Goal:** Safe access to S3 images & masks.

- [ ] `GET /assets/{id}/view` → short-lived signed URL (S3).
- [ ] Frontend viewer uses that URL; toggle mask overlay (canvas or CSS blend).
- [ ] Re-fetch on URL expiry.

**Exit criteria:** Authorized users see images/masks without direct S3 exposure.

---

## Phase 7 — Farmer Surfaces (Herd, History, Notifications)
**Goal:** Farmer read flows.

- [ ] **Herd** list for farms in `user_farms`.
- [ ] **Animal history**: scans + `grading_results`, mini trend chart.
- [ ] **Notifications** center: list unread + mark read.

**Exit criteria:** Farmer can browse animals, open history, and clear notifications.

---

## Phase 8 — Grading Hook & Results
**Goal:** Store & display human/model grades.

- [ ] `POST /scans/{id}/grade` → write `grading_results` (+ confidence, model info).
- [ ] Tech UI: “Trigger Grade” (stub to model later) + show result.
- [ ] Farmer history: show grade label, confidence, timestamp, source.

**Exit criteria:** Grade appears in both technician detail and farmer history.

---

## Phase 9 — AWS Lambda Integration
**Goal:** Real cloud signal to webhook.

- [ ] Lambda on `s3:ObjectCreated:*` for capture prefix → assemble payload (bucket, prefix, `img.png|msk.png|meta.json`, pre-signed URLs, `device_code`) + HMAC → `POST /ingest/webhook`.
- [ ] Retries + idempotency; DLQ/logging.

**Exit criteria:** Pi uploads → scans appear in the technician queue automatically.

---

## Phase 10 — QA, E2E, & Polish
**Goal:** Stability and UX quality.

- [ ] **API tests**: auth, RBAC, ingest webhook, scans transitions, asset view.
- [ ] **E2E** (Playwright): admin/tech/farmer journeys.
- [ ] Loading/empty states, a11y, error boundaries, consistent toasts.

**Exit criteria:** CI green; happy-paths reliable; key UX smooth.

---

## Phase 11 — Deployment (Linux Server with Public IP)
**Goal:** Production behind HTTPS.

- [ ] Reverse proxy (nginx/traefik): TLS; route `/api` → uvicorn; `/` → Next.js (`pnpm build && pnpm start`). :contentReference[oaicite:8]{index=8}
- [ ] systemd units: `cti-api.service`, `cti-web.service` (+ optional `cti-worker.service`).
- [ ] Environment files with secrets; JWT rotation; CORS restricted to web origin.
- [ ] Backups: DB dumps; S3 retention; log rotation.

**Exit criteria:** HTTPS dashboard live; end-to-end ingest to view works.

---

## Phase 12 — Data Export & Ops
**Goal:** ML export & ops visibility.

- [ ] Technician **dataset export** (CSV/JSON manifest with asset links, statuses, quality).
- [ ] Admin reports (counts by farm/device/status).
- [ ] Observability: structured logs, request IDs, minimal dashboards.
- [ ] Documentation: update README, `/docs/ERD.dbml`, API reference, runbooks.

**Exit criteria:** Repeatable exports; basic ops visibility; docs current.

---

## Milestones & Demos
- **M1 (after Phase 5):** Technician validates an ingested scan locally.
- **M2 (after Phase 9):** Real Pi→S3→Lambda→API ingest populates queue.
- **M3 (after Phase 11):** HTTPS production with Admin/Tech/Farmer journeys live.
- **M4 (after Phase 12):** Dataset export + docs + minimal ops complete.

---

## Acceptance Criteria Summary
- **Security:** JWT httpOnly, RBAC enforced, webhook HMAC, no direct S3 exposure.
- **Data Integrity:** Idempotent ingest (`ingest_key`), `scan_events` + `audit_log`.
- **Usability:** Clear status machine, mask overlay viewer, robust error toasts.
- **Reliability:** CI green; E2E pass; logs usable; backups configured.

---

### Snapshot of Current Status (from repo)
- ✅ Monorepo + Docker DB + run scripts are in README (“Start DB,” “Run API,” “Run Web”). The README states the **API auto-creates tables and seeds roles** and shows both Swagger and Login/Register flows. These establish Phase 0 completion and partial Phase 1/2 scaffolding. :contentReference[oaicite:9]{index=9}
- ⏳ Remaining: Alembic migrations; RBAC guards; Admin/Farm/Device UIs; Ingest webhook; Technician & Farmer surfaces; Signed URL asset proxy; Lambda integration; tests; deployment hardening.

> Keep this file at repo root as `ROADMAP.md` and update checkboxes as you ship features.
