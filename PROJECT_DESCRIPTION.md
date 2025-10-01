# CTI Platform — Project Description
**Name:** CTI (Cattle Tech Imaging) — Ultrasound Capture, Grading & Insights  
**Repo:** `Mkh23/cti-dashboard` • **Region:** `ca-central-1` • **Dev bucket:** `cti-dev-406214277746`  
**Last updated:** 2025-10-01

---

## 1) Elevator Pitch (1 minute)
CTI is a lean, production-minded platform for capturing bovine ultrasound images on Raspberry Pi devices, moving them safely to AWS S3, validating & ingesting metadata on a FastAPI server, persisting to Postgres/PostGIS, running ML-based grading, and presenting actionable results through a role-based Next.js dashboard. The system emphasizes reliability (signed webhooks, DLQ/replay), auditability (versioned models, feature logs), and a clear path to scale (queue-based workers, cloud storage lifecycle).

---

## 2) Problem Statement
Beef quality and herd productivity depend on timely, objective, and repeatable assessment (e.g., ribeye area, IMF proxies, backfat). Traditional workflows are manual, device-specific, and siloed. CTI provides a unified pipeline from field capture to graded insight, minimizing human error, standardizing data formats, and enabling continuous improvement of models.

---

## 3) Users & Value
- **Admin** — Onboard farms and devices, enforce access controls, monitor system health, and reprocess failures.
- **Technician** — Upload/verify scans, visualize images & masks, run grading, annotate notes, and track batches.
- **Farmer** — View permitted results (per herd/animal), follow trends, and export reports for decisions.

**Key values:** faster feedback loops, consistent grading, secure sharing, and a foundation for longitudinal analytics.

---

## 4) Scope (v1)
- **Capture:** Raspberry Pi or similar devices upload images (and optional masks + `meta.json`) to S3 under `raw/{device_code}/...`.
- **Ingest:** EventBridge/Lambda post a signed webhook to the server, which validates schema + signature and persists `scans`/`assets`.
- **Storage:** Postgres 15 + PostGIS (SRID 4326) for geo-aware farms and telemetry; S3 lifecycle rules to manage cost.
- **Grading:** Worker executes ML models, stores `grading_results` (model name/version/hash, confidence, breakdown, features).
- **Dashboard:** Next.js 14 with role-based access, viewer (image+mask), lists/filters, device registry, and basic admin ops (DLQ replay).
- **Security:** HMAC-signed webhooks, JWT in HttpOnly cookies, strict CORS, IAM least-privilege, bucket encryption/versioning.
- **Reliability:** retries, SQS DLQ, replay endpoint; health/readiness probes; structured logs and basic metrics.

---

## 5) Non-Goals (v1)
- Replacing Pi-side capture UI/firmware (only minimal guidelines for `meta.json`).  
- On-device model training (server-side/worker inference only).  
- Full self-serve multi-tenant billing or marketplace features.  
- Advanced analytics & forecasting (beyond storing features and grading results).

---

## 6) Architecture (current)
Pi → **S3 (raw)** → **EventBridge** → **Lambda (HMAC signer)** → **FastAPI (/ingest/webhook)** → **Postgres/PostGIS**  
                                                                      ↓  
                                                        **Worker (grading, overlays → S3 processed)**  
                                                                      ↓  
                                                     **Next.js Dashboard (Admin/Tech/Farmer)**

**Data contracts:**  
- `meta.json` (v1.0.0) schema for ingest.  
- HMAC headers: `X-CTI-Timestamp`, `X-CTI-Signature` (sha256).  
- `grading_results` captures model metadata and confidence breakdowns.

---

## 7) Success Criteria & KPIs
- **Ingest reliability:** ≥ 99% successful ingest on first try; DLQ replayable to 100% recovery.  
- **Latency:** ≤ 5s from S3 upload to visible scan in dashboard (dev).  
- **Auditability:** 100% of results have `model@version` and `inference_sha256`.  
- **Security:** All webhook requests signed; no unsigned requests accepted.  
- **Usability:** Technician can view image+mask, validate, and run grading in ≤ 3 clicks.  
- **Ops:** CI/CD green deploy on `main` with smoke tests passing.

---

## 8) Data & Privacy
- **Data location:** AWS `ca-central-1`.  
- **Encryption & access:** S3 SSE-S3/KMS; IAM least privilege; signed URLs for assets.  
- **Retention:** initial lifecycle (raw→Glacier@180d→Delete@3y; processed→Glacier@365d→Delete@5y; `meta.json` hot).  
- **PII:** minimize personal identifiers; limit to farm/animal identifiers necessary for operations.  
- **Audit logs:** ingestion logs and scan events retained for diagnosis and compliance.

---

## 9) Assumptions & Constraints
- Intermittent connectivity from field devices (uploads may be delayed/batched).  
- Variability in image quality; models will evolve (hence strong versioning/logging).  
- Server hosted on a Linux VM with Docker; internet egress IP may not be static (IP allowlist optional later).  
- Project prioritizes reliability and observability before advanced analytics.

---

## 10) Risks & Mitigations
- **Unreliable uploads** → Defer to S3 reliability; ingest is event-driven; DLQ + replay.  
- **Schema drift** → Versioned `meta.json`, additive changes only until v2.  
- **Model regressions** → Persist features & confidence breakdown; allow side-by-side results.  
- **Cost growth (S3/compute)** → Lifecycle policies; on-demand workers; monitor queue depth.  
- **Security gaps** → HMAC + timestamp, JWT HttpOnly, CORS, rate limits, IAM least privilege.

---

## 11) Milestones (aligned with Roadmap)
1. **Foundations** — DB migrations, health probes, minimal admin.  
2. **Ingest** — signed webhook + schema validation + idempotency, scans/assets persisted.  
3. **AWS Wiring** — EventBridge/Lambda/Secrets, retries, DLQ.  
4. **Dashboard MVP** — Scans list/detail, viewer, devices, basic admin.  
5. **Grading** — Worker pipeline, `grading_results` UI, overlays.  
6. **Ops & Lifecycle** — DLQ replay, backups, lifecycle rules.  
7. **CI/CD** — Actions pipeline, deploy script, protected `main`.

---

## 12) Glossary
- **Capture** — A single scan session with image (and optional mask, meta).  
- **Ingest Key** — Unique S3 path or composite key ensuring idempotency.  
- **Grading** — Model inference + feature computation producing confidence & metrics.  
- **DLQ** — Dead Letter Queue (SQS) where failed events can be inspected and replayed.  
- **SRID 4326** — WGS84 lat/lon reference for PostGIS geometries.

---

## 13) FAQ (short)
**Q:** Why HMAC if S3 already authenticates uploads?  
**A:** The server webhook is independently exposed; HMAC proves the call originated from our AWS path and payload wasn’t tampered.

**Q:** What happens when grading fails?  
**A:** The job errors are logged; operators can retry; ingest remains complete; a new `grading_results` record is added on success.

**Q:** Can multiple models grade the same scan?  
**A:** Yes; `grading_results` stores many rows per scan, each with `model_name@version` and metrics.

**Q:** Do farmers need AWS access?  
**A:** No; dashboard provides signed URLs and restricted views according to role and farm permissions.
