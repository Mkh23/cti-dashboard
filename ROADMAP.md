# CTI Platform — Master Roadmap with Checklists
**Flow:** Pi → S3 (raw) → EventBridge/Lambda (signed webhook) → FastAPI (ingest) → Postgres/PostGIS → Worker (grading) → Next.js 14 Dashboard  
**Repo:** `Mkh23/cti-dashboard` • **Region:** `ca-central-1` • **Dev bucket:** `cti-dev-406214277746`  
**Last updated:** 2025-10-02

---

## 0) High-Level Objectives
- [x] Define end-to-end data flow and security boundaries
- [x] Lock region, bucket, and S3 prefix policy for `dev`
- [x] Deliver a reliable ingest path with validation, idempotency, and replay (backend complete, AWS integration pending)
- [ ] Provide a role-based dashboard with scan viewing, grading, and reporting (backend APIs ready, frontend UI in progress)
- [ ] Enable reproducible deploys (CI/CD), observability, and lifecycle policies

## 1) Environments & Infra
### 1.1 Environments
- [x] `dev` (default) — iterative development
- [ ] `prod` — stable clients
- [ ] Document environment-specific configs in `/docs/env.md`

### 1.2 Servers & Secrets
- [x] Linux VM target for API/Web (Dockerized)
- [ ] Nginx/Traefik TLS termination
- [ ] `.env.example` for local, secrets via systemd `EnvironmentFile=` in prod
- [ ] Secrets inventory (`JWT_SECRET`, DB URL, S3, HMAC secret) and rotation policy

### 1.3 Feature Flags
- [ ] Add feature flag system (`api/app/core/feature_flags.py`)
- [ ] Configure flags in environment (DB or file-based)
- [ ] Initial flags: `enable_grading`, `enable_notifications`, `advanced_search`
- [ ] Document flag conventions in `/docs/feature_flags.md`

**Definition of Done (Env):**
- [ ] `make up` boots DB/API/Web locally
- [ ] One-liner `deploy.sh` (pull images, run Alembic, restart services)
- [ ] TLS certs installed and renewed (prod)
- [ ] Feature flags configurable without deployment

---

## 2) S3 Layout & Lifecycle
### 2.1 Prefix Policy (decided)
- [x] Raw (Pi): `raw/{device_code}/{YYYY}/{MM}/{DD}/{capture_id}/` → `image.jpg|png`, `mask.png?`, `meta.json`
- [x] Processed (server): `processed/{capture_id}/...` (thumbs, overlays, reports)
- [x] Exports/Audit: `exports/{YYYY}/{MM}/...`, `audit/{YYYY}/{MM}/...`

### 2.2 Lifecycle (initial scaffolding)
- [ ] `raw/` → Glacier @180d → Delete @3y
- [ ] `processed/` → Glacier @365d → Delete @5y
- [ ] Keep `meta.json` in Standard

**Tasks:**
- [ ] Add lifecycle rules to bucket (dev)
- [ ] Terraform (optional) or doc the manual steps
- [ ] Add "Storage Cost" note in README

**DoD (S3):**
- [ ] Verified example: `s3://cti-dev-406214277746/raw/dev-0001/2025/09/09/cap_1757423584/image.jpg`
- [ ] Lifecycle policies visible in console and tested with tags/simulator

---

## 3) Ingest & Webhook Security [PRIORITY]
### 3.1 Eventing
- [ ] EventBridge rule for `ObjectCreated:*` in `raw/`
- [ ] Lambda builds payload `{bucket, prefix, keys, device_code, meta_json}`
- [ ] Lambda adds `X-CTI-Timestamp`, `X-CTI-Signature` (HMAC), POSTs `/ingest/webhook`
- [ ] Lambda retries (x2), SQS DLQ on fail

### 3.2 HMAC Signing (decisions)
- [x] Secret stored in **AWS Secrets Manager** (dev/prod), rotate quarterly
- [ ] Lambda retrieves secret on cold start and caches
- [x] Server validates timestamp ±5 min & signature (constant-time compare)

### 3.3 Replay & Ops
- [ ] Create SQS DLQ `cti-dev-ingest-dlq`
- [ ] `POST /ops/ingest-replay?max=50` (admin only) drains DLQ
- [ ] CLI/script & Admin UI button to trigger replay

### 3.4 End-to-End Testing
- [ ] Local test harness to simulate S3 → Lambda → webhook flow
- [ ] Basic test images with meta.json templates
- [ ] S3 event notification simulator

**DoD (Ingest):**
- [ ] Uploading a file under `raw/.../cap_xxx/` leads to a `scans + assets` row within 5s
- [ ] Tampered signature is rejected (403), logged
- [ ] Failed events appear in DLQ and can be replayed successfully
- [ ] Test harness verifies complete ingest flow

---

## 4) `meta.json` Validation (Schema v1.0.0)
- [x] Adopt `meta_version: "1.0.0"` and validate via JSON Schema at webhook
- [x] Store schema at `api/app/schemas/meta_v1.json` and reference in README
- [ ] Unit tests for required/optional fields and error messages
- [x] Forward-compat plan: only additive optional fields until v2

**Required keys (recap):** `meta_version, device_code, capture_id, captured_at, image_sha256, files{image_relpath}, probe, firmware`  
**Optional:** `operator_id, farm_id, gps{lat,lon}, mask_sha256, files{mask_relpath,extra[]}, inference_summary{...}`

**DoD (Schema):**
- [ ] Valid sample passes; missing `image_relpath` fails with clear message
- [ ] Contract doc published for Pi-side devs

---

## 5) Database (Postgres 15 + PostGIS)
### 5.1 Conventions & Indices
- [x] SRID = **EPSG:4326**
- [ ] Enforce geometry types (e.g., farm geofence POLYGON)
- [ ] High-value indices:  
  - `scans(ingest_key) UNIQUE`, `(status, created_at DESC)`, `(device_id, captured_at DESC)`  
  - `farms USING GIST(geofence)`; optional `scans USING GIST(gps_location)`  
  - `assets(bucket, object_key) UNIQUE`

### 5.2 Entities (initial)
- [x] `users, roles, user_roles`  
- [x] `farms(geofence, centroid), animals, user_farms`  
- [x] `devices(device_code UNIQUE, label, farm_id, last_seen_at, last_upload_at, captures_count)`  
- [x] `assets(bucket, key, sha256, size, mime)`  
- [x] `scans(scan_id, capture_id, device_id, farm_id, operator_id, gps_location, captured_at, ingest_key, status)`  
- [x] `scan_events(scan_id, event, meta, created_at)`  
- [x] `grading_results(scan_id, model_name, model_version, inference_sha256, confidence, confidence_breakdown JSONB, features_used JSONB, created_at, created_by)`  
- [x] `ingestion_log(capture_id, http_status, bytes_in, ms, error)`  
- [x] `notifications(user_id, type, payload, is_read, created_at)`

### 5.3 Migrations (Alembic)
- [x] Replace `create_all()` with Alembic baseline
- [x] Migration order: auth → farms/devices/animals → assets/scans/events/ingestion_log → grading_results/notifications → secondary indexes → seeds (dev)

**DoD (DB):**
- [x] Alembic head matches ERD (`/docs/ERD.dbml`)
- [x] Fresh DB from migrations passes integration tests
- [x] Registration works correctly with seeded roles
- [x] User model includes `updated_at` column and works correctly
- [x] Documentation updated with troubleshooting for missing columns

---

## 6) API (FastAPI)
### 6.1 Auth & RBAC
- [x] `/auth/login, /auth/register, /me` with JWT tokens
- [x] Role-based access (admin/technician/farmer), farm scoping
- [x] First user registration automatically becomes admin
- [x] Comprehensive auth tests (14 tests, 100% auth module coverage)

### 6.2 Ingest & Scans [PRIORITY]
- [x] `POST /ingest/webhook` — HMAC + Schema; idempotent on `ingest_key`
- [x] `GET /scans?filters&pagination`
- [x] `GET /scans/{scan_id}` with signed URLs to assets (endpoint ready, signed URL generation pending)
- [ ] `POST /scans/{scan_id}/validate|link-animal|note` (tech/admin)

### 6.3 Devices & Admin [EARLY FOCUS]
- [x] `GET/POST /devices` (registry: device_code, label, farm_id, s3_prefix_hint)
- [x] `GET/POST /admin/users` & `/admin/farms`
- [x] Admin dashboard scaffolding (before detailed technician/farmer UI)
- [x] User/role management, device registration, farm geofencing
- [ ] Basic system status dashboard

### 6.4 Grading & Ops
- [ ] `POST /scans/{scan_id}/grade` → enqueue worker job
- [ ] `GET /grading/{scan_id}` list results
- [ ] `POST /ops/ingest-replay?max=50`

**DoD (API):**
- [x] OpenAPI spec available; critical routes have tests
- [x] All responses typed (Pydantic) and stable
- [x] Admin tools can create/manage all required entities
- [x] Auth tests with 70%+ overall coverage

---

## 7) Worker Jobs (Grading & Media)
### 7.1 Model Pipeline Architecture [EXPANDED]
- [ ] Define model registry structure:
  models/ 
    ├── ribeye-unetpp@1.0.0/ 
    │ ├── model.onnx 
    │ ├── config.json 
    │ ├── metadata.json (sha256, training_dataset, metrics) 
    │ └── preprocessing.py 
    └── ribeye-unetpp@1.1.0/ 
    └── ...
- [ ] Model versioning convention (SemVer)
- [ ] Artifact hashing and provenance tracking
- [ ] A/B comparison capability

### 7.2 Worker Implementation
- [ ] Choose queue (Celery/RQ/Arq)
- [ ] Implement grading pipeline (load model, run, compute confidence_breakdown & features_used, persist)
- [ ] Generate thumbnails/overlays under `processed/{capture_id}/`
- [ ] Backfill jobs (re-grade, feature extraction, exports)

### 7.3 Model Deployment & Management
- [ ] Model upload/registration process
- [ ] Version switching and default model selection
- [ ] Canary deployments (% traffic to new model)
- [ ] Model performance metrics collection

**DoD (Worker):**
- [ ] A sample scan produces a `grading_results` row with metrics
- [ ] Average grading time and error rate recorded
- [ ] Model versions can be switched without deployment
- [ ] Complete provenance from model to results

---

## 8) Dashboard (Next.js 14 + Tailwind)
### 8.1 Pages
- [x] Auth: login/register/reset; `/me` hydration; role redirect
- [x] Admin: Users, Farms (map pending), Devices (registry + telemetry)
- [ ] Technician: Scans (filters: status/farm/device/date), Scan Detail (ImageViewer, Meta, Timeline), Actions
- [ ] Farmer: Herd, Animal History (trend mini-charts), Notifications

### 8.2 Components
- [ ] DataTable (server pagination, 50/page default)
- [ ] ImageViewer (zoom/pan, mask toggle, signed URL refresh)
- [ ] Map (GeoJSON, farm polygon), StatusPill, Toasts

**DoD (Web):**
- [ ] Technician flow: find new scan → view image+mask → validate → run grading → see result
- [ ] Farmer sees graded results for permitted images

---

## 9) Observability & Ops [EXPANDED]
### 9.1 Logging
- [ ] Correlate logs by `capture_id` / `ingest_key` across Lambda → API → DB
- [ ] Structured logs (JSON) with request IDs
- [ ] Log rotation and archival

### 9.2 Metrics & Monitoring
- [ ] Prometheus metrics endpoints in API
- [ ] Grafana dashboards for key metrics
- [ ] Alerting on critical paths:
- Ingest success rate
- Queue depths
- API response times
- Error rates
- Resource utilization

### 9.3 Health & Operations
- [x] Health endpoints (`/healthz`, `/readyz`)
- [ ] Metrics: webhook latency, success/error rates, grading duration, queue depth
- [ ] Backups: nightly `pg_dump`, restore runbook

**DoD (Obs):**
- [ ] Grafana/Prometheus dashboards for ingest success rate & P95 latency
- [ ] Simulated failure shows up in alerts/logs
- [ ] SLOs defined for key metrics
- [ ] Backup/restore proven viable

---

## 10) Security Checklist
- [x] HMAC-signed webhook + timestamp window check
- [ ] Rate limits on `/ingest/webhook` & admin ops
- [x] JWT in HttpOnly cookies; SameSite=Strict; CSRF for unsafe methods
- [x] Strict CORS (dashboard origin only)
- [ ] IAM least privilege (Pi → S3 put to `raw/` only)
- [ ] S3: SSE-S3 (or KMS), TLS-only, versioning, object ownership enforced
- [ ] DB: least-privileged role, no superuser, periodic backups

---

## 11) CI/CD
- [ ] GitHub Actions: backend (ruff, mypy, tests) → build/push Docker
- [ ] Frontend: type-check & build
- [ ] Deploy: SSH → pull images → Alembic upgrade → restart via systemd
- [ ] Status badges in README; protected `main`

**DoD (CI/CD):**
- [ ] Green pipeline builds & deploys on merge to `main`
- [ ] Smoke tests pass post-deploy

---

## 12) Testing Strategy
- [x] Unit: Auth endpoints (register, login, /me), health checks
- [x] Integration: Full auth flow with test database
- [x] Test infrastructure: pytest with PostgreSQL test database
- [x] Unit: Admin endpoints (users, farms, devices management) ✅
- [x] Unit: Webhook HMAC signature validation, timestamp checks ✅
- [x] Integration: Schema validation, idempotency tests ✅
- [x] **Test coverage: 78.15%** (exceeds 70% target) ✅
- [ ] Integration: Complete webhook → DB → signed URL path
- [ ] E2E (Playwright/Cypress): admin, tech, farmer journeys
- [ ] Load: burst uploads to webhook
- [ ] Security: comprehensive signature tamper & replay tests

---

## 13) Phases & Milestones (with checklists) [REORDERED FOR PRIORITY]
### Phase A — Foundations
- [x] Repo scaffold & local stack
- [x] Alembic baseline & ERD (`/docs/ERD.dbml`)
- [x] Health (`/healthz`) & readiness (`/readyz`)
**DoD:** Fresh DB via migrations; `/healthz` green ✅

### Phase B — Admin Tools & Auth
- [x] JWT auth, HttpOnly cookies
- [x] Role guards (server & client)
- [x] Admin screens for users, farms, devices (backend + frontend complete)
- [x] Comprehensive admin API tests (16 tests, 83% coverage) ✅
**DoD:** Admin can create users, register devices, define farm boundaries ✅ Complete with tests (farm boundaries/map pending)

### Phase C — Ingest (AWS→Server) [PRIORITY]
- [x] `/ingest/webhook` (HMAC, Schema, idempotent)
- [x] Persist scans/assets/events/ingestion_log
- [x] Webhook ingestion tests (signature validation, schema validation, idempotency) ✅
- [ ] S3 policy/prefixes; EventBridge rule
- [ ] Lambda signer; retries; DLQ
**DoD:** Upload triggers scan creation in ≤5s; DLQ fills on forced errors (backend complete with tests, AWS integration pending)

### Phase D — Dashboard MVP
- [ ] Technician: Scans list + detail (ImageViewer + mask), actions
- [ ] Farmer: Herd/History/Notifications
**DoD:** Technician can validate and run grading; Farmer can view grades

### Phase E — Grading Pipeline
- [ ] Worker queue + model runner
- [ ] Persist `grading_results` + UI display
- [ ] Model versioning & management
**DoD:** Confidence & breakdown visible in UI; model versions swappable

### Phase F — Monitoring & Ops
- [ ] Prometheus/Grafana setup
- [ ] Key metric dashboards
- [ ] Alerting rules
- [ ] S3 lifecycle rules
- [ ] DLQ replay endpoint + admin button
- [ ] Backups & restore runbook
**DoD:** One replay from DLQ to success; nightly backup artifact; alerts firing correctly

### Phase G — Feature Flags & Refinement
- [ ] Feature flag system implementation
- [ ] Flag-gated advanced features
**DoD:** Features can be toggled without deployment

### Phase H — CI/CD
- [ ] Actions pipeline; deploy script; prod gating
**DoD:** Auto-deploy on `main` with green checks

---

## 14) Acceptance Criteria (MVP)
- [ ] Pi upload under `raw/.../cap_{id}/` produces a visible scan quickly
- [ ] Viewer shows image + mask; controls are smooth
- [ ] Grading produces a row with `model@version`, confidence, and breakdown
- [ ] Device telemetry updates (`last_upload_at`, `captures_count`)
- [ ] DLQ replay restores at least one failed ingest
- [ ] CI/CD builds, tests, and deploys on `main` merges
- [ ] Admin can manage full system lifecycle
- [ ] Prometheus/Grafana shows key metrics

---

## 15) Next 5 Commits (Actionable) [REORDERED]
1. [x] Add `api/app/schemas/meta_v1.json` + webhook validation + HMAC verify + unit tests (schema & validation complete, unit tests pending)
2. [x] Alembic baseline: users/roles → farms/devices/animals → scans/assets/events/ingestion_log → grading_results/notifications  
3. [x] Admin screens: Users, Farms (with PostGIS), Devices (registry) (backend APIs complete, frontend UI pending)
4. [ ] EventBridge + Lambda skeleton (Secrets Manager, signed POST, retries, DLQ)  
5. [ ] Basic monitoring setup: Prometheus endpoint, health checks, initial Grafana dashboard (health checks complete, Prometheus/Grafana pending)

---

## 16) Open Items
- [ ] Finalize `confidence_breakdown` metrics after model experiments
- [ ] Farmer PDF/CSV report templates
- [ ] Privacy/PII policy and retention tuning
- [ ] Terraform/IaC for reproducible infra (optional next step)