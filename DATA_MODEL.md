# CTI Platform — Data Model & Contracts
**Scope:** Relational schema (Postgres 15 + PostGIS), relationships, and data contracts linking S3 objects, ingest events, scans, grading results, and dashboard entities.  
**Region:** `ca-central-1` • **Bucket (dev):** `cti-dev-406214277746` • **SRID:** 4326 (WGS84)  
**Last updated:** 2025-10-01

---

## 1) Purpose
This document defines how CTI data is structured, how tables relate, and what example payloads/rows look like so Pi → S3 → Lambda → Server → DB stay perfectly in sync. It includes:
- ERD (DBML) for dbdiagram.io
- Canonical SQL DDL (Postgres + PostGIS)
- Example `meta.json`, webhook payload, and table rows
- Idempotency & constraints
- Naming and indexing conventions

---

## 2) High-Level Data Flow
1. **Pi** uploads to `s3://cti-dev-406214277746/raw/{device_code}/{YYYY}/{MM}/{DD}/{capture_id}/[image.jpg|png, mask.png?, meta.json]`  
2. **EventBridge/Lambda** reads object create event, loads `meta.json`, signs and POSTs `/ingest/webhook`.  
3. **Server** validates HMAC + schema, **upserts** `devices`, creates `scans`, `assets`, `scan_events`, `ingestion_log`.  
4. **Worker** runs grading → writes `grading_results` (+ overlays to `processed/{capture_id}/...`).  
5. **Dashboard** reads via RBAC, generates reports/exports.

**Idempotency key:** `ingest_key = s3://{bucket}/raw/{device_code}/{YYYY}/{MM}/{DD}/{capture_id}/` (directory-level key).

---

## 3) ERD (DBML for dbdiagram.io)
Paste this into https://dbdiagram.io/

```dbml
Project CTI {
  database_type: "PostgreSQL"
  note: "CTI data model v1.0.0"
}

Table users {
  id uuid [pk, default: gen_random_uuid()]
  email text [unique, not null]
  full_name text
  password_hash text
  created_at timestamptz [default: now()]
  updated_at timestamptz [default: now()]
}

Table roles {
  id serial [pk]
  name text [unique, not null] // admin, technician, farmer
}

Table user_roles {
  user_id uuid [not null, ref: > users.id]
  role_id int  [not null, ref: > roles.id]
  primary key (user_id, role_id)
}

Table farms {
  id uuid [pk, default: gen_random_uuid()]
  name text [not null]
  geofence geometry(Polygon, 4326) // optional
  centroid geometry(Point, 4326)   // optional
  created_at timestamptz [default: now()]
  updated_at timestamptz [default: now()]
}

Table animals {
  id uuid [pk, default: gen_random_uuid()]
  farm_id uuid [ref: > farms.id]
  tag_id text [not null]
  breed text
  sex text
  birth_date date
  created_at timestamptz [default: now()]
  unique ("farm_id", "tag_id")
}

Table devices {
  id uuid [pk, default: gen_random_uuid()]
  device_code text [unique, not null]
  label text
  farm_id uuid [ref: > farms.id] // optional default owner
  s3_prefix_hint text
  last_seen_at timestamptz
  last_upload_at timestamptz
  captures_count int [default: 0]
  created_at timestamptz [default: now()]
  updated_at timestamptz [default: now()]
}

Table assets {
  id uuid [pk, default: gen_random_uuid()]
  bucket text [not null]
  object_key text [not null]
  sha256 char(64) [not null]
  size_bytes bigint
  mime_type text
  created_at timestamptz [default: now()]
  unique ("bucket", "object_key")
}

Enum scan_status {
  uploaded
  ingested
  graded
  error
}

Table scans {
  id uuid [pk, default: gen_random_uuid()]
  scan_id text [not null] // externally visible id (optional)
  capture_id text [not null]
  ingest_key text [not null] // s3 raw dir path — idempotency key
  device_id uuid [not null, ref: > devices.id]
  farm_id uuid [ref: > farms.id]
  animal_id uuid [ref: > animals.id] // optional link later
  operator_id uuid [ref: > users.id]
  gps geometry(Point, 4326)
  captured_at timestamptz
  status scan_status [default: 'uploaded']
  image_asset_id uuid [ref: > assets.id]
  mask_asset_id uuid [ref: > assets.id] // optional
  created_at timestamptz [default: now()]
  unique ("ingest_key")
  index ("device_id", "captured_at")
  index ("farm_id", "captured_at")
  note: "scan_id is optional public reference; capture_id matches meta.json"
}

Table scan_events {
  id bigserial [pk]
  scan_id uuid [not null, ref: > scans.id]
  event text [not null] // uploaded, ingested, graded, replayed, etc.
  meta jsonb
  created_at timestamptz [default: now()]
  index ("scan_id", "created_at")
}

Table ingestion_log {
  id bigserial [pk]
  capture_id text [not null]
  ingest_key text [not null]
  http_status int
  bytes_in int
  ms int
  error text
  created_at timestamptz [default: now()]
  index ("capture_id")
  index ("ingest_key", "created_at")
}

Table grading_results {
  id uuid [pk, default: gen_random_uuid()]
  scan_id uuid [not null, ref: > scans.id]
  model_name text [not null]
  model_version text [not null]
  inference_sha256 char(64) // of the model bundle or code
  confidence numeric(5,4) // 0..1
  confidence_breakdown jsonb
  features_used jsonb
  created_by uuid [ref: > users.id]
  created_at timestamptz [default: now()]
  index ("scan_id", "created_at")
  index ("model_name", "model_version")
}

Table notifications {
  id bigserial [pk]
  user_id uuid [not null, ref: > users.id]
  type text [not null]
  payload jsonb
  is_read boolean [default: false]
  created_at timestamptz [default: now()]
  index ("user_id", "created_at")
}
```

---

## 4) Canonical DDL (Postgres + PostGIS)
> Run via Alembic; shown here for documentation clarity. Trim as needed.

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS postgis;

-- Roles
CREATE TABLE roles(
  id serial PRIMARY KEY,
  name text UNIQUE NOT NULL
);
INSERT INTO roles(name) VALUES ('admin'), ('technician'), ('farmer')
ON CONFLICT DO NOTHING;

-- Users & user_roles
CREATE TABLE users(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text UNIQUE NOT NULL,
  full_name text,
  password_hash text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE TABLE user_roles(
  user_id uuid NOT NULL REFERENCES users(id),
  role_id int  NOT NULL REFERENCES roles(id),
  PRIMARY KEY (user_id, role_id)
);

-- Farms & animals (4326)
CREATE TABLE farms(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  geofence geometry(Polygon, 4326),
  centroid geometry(Point, 4326),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_farms_geofence_gist ON farms USING gist(geofence);

CREATE TABLE animals(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  farm_id uuid REFERENCES farms(id),
  tag_id text NOT NULL,
  breed text,
  sex text,
  birth_date date,
  created_at timestamptz DEFAULT now(),
  UNIQUE(farm_id, tag_id)
);

-- Devices
CREATE TABLE devices(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  device_code text UNIQUE NOT NULL,
  label text,
  farm_id uuid REFERENCES farms(id),
  s3_prefix_hint text,
  last_seen_at timestamptz,
  last_upload_at timestamptz,
  captures_count int DEFAULT 0,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Assets
CREATE TABLE assets(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  bucket text NOT NULL,
  object_key text NOT NULL,
  sha256 char(64) NOT NULL,
  size_bytes bigint,
  mime_type text,
  created_at timestamptz DEFAULT now(),
  UNIQUE(bucket, object_key)
);

-- Scans
DO $$ BEGIN
  CREATE TYPE scan_status AS ENUM ('uploaded','ingested','graded','error');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE scans(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scan_id text,
  capture_id text NOT NULL,
  ingest_key text NOT NULL,
  device_id uuid NOT NULL REFERENCES devices(id),
  farm_id uuid REFERENCES farms(id),
  animal_id uuid REFERENCES animals(id),
  operator_id uuid REFERENCES users(id),
  gps geometry(Point, 4326),
  captured_at timestamptz,
  status scan_status DEFAULT 'uploaded',
  image_asset_id uuid REFERENCES assets(id),
  mask_asset_id uuid REFERENCES assets(id),
  created_at timestamptz DEFAULT now(),
  UNIQUE(ingest_key)
);
CREATE INDEX idx_scans_device_captured ON scans(device_id, captured_at DESC);
CREATE INDEX idx_scans_farm_captured   ON scans(farm_id, captured_at DESC);

-- Events & ingest logs
CREATE TABLE scan_events(
  id bigserial PRIMARY KEY,
  scan_id uuid NOT NULL REFERENCES scans(id),
  event text NOT NULL,
  meta jsonb,
  created_at timestamptz DEFAULT now()
);
CREATE INDEX idx_scan_events_scan_time ON scan_events(scan_id, created_at);

CREATE TABLE ingestion_log(
  id bigserial PRIMARY KEY,
  capture_id text NOT NULL,
  ingest_key text NOT NULL,
  http_status int,
  bytes_in int,
  ms int,
  error text,
  created_at timestamptz DEFAULT now()
);
CREATE INDEX idx_ingest_log_capture ON ingestion_log(capture_id);
CREATE INDEX idx_ingest_log_key_time ON ingestion_log(ingest_key, created_at);

-- Grading
CREATE TABLE grading_results(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scan_id uuid NOT NULL REFERENCES scans(id),
  model_name text NOT NULL,
  model_version text NOT NULL,
  inference_sha256 char(64),
  confidence numeric(5,4),
  confidence_breakdown jsonb,
  features_used jsonb,
  created_by uuid REFERENCES users(id),
  created_at timestamptz DEFAULT now()
);
CREATE INDEX idx_grading_scan_time ON grading_results(scan_id, created_at);
CREATE INDEX idx_grading_model_ver ON grading_results(model_name, model_version);

-- Notifications
CREATE TABLE notifications(
  id bigserial PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES users(id),
  type text NOT NULL,
  payload jsonb,
  is_read boolean DEFAULT false,
  created_at timestamptz DEFAULT now()
);
CREATE INDEX idx_notifications_user ON notifications(user_id, created_at);
```

---

## 5) Contracts & Examples

### 5.1 S3 Layout & Keys
```
s3://cti-dev-406214277746/raw/dev-0001/2025/09/09/cap_1757423584/
  ├── image.jpg
  ├── mask.png           (optional)
  └── meta.json          (required)
```
**`ingest_key` =** `s3://cti-dev-406214277746/raw/dev-0001/2025/09/09/cap_1757423584/`

### 5.2 `meta.json` (v1.0.0 example)
```json
{
  "meta_version": "1.0.0",
  "device_code": "dev-0001",
  "capture_id": "cap_1757423584",
  "captured_at": "2025-09-09T14:18:32Z",
  "operator_id": "tech-abc",
  "farm_id": null,
  "gps": { "lat": 43.6532, "lon": -79.3832 },
  "probe": { "model": "Convex-3.5MHz", "frequency_mhz": 3.5 },
  "firmware": { "pi_os": "Bookworm-2025-07-01", "app_version": "0.3.2" },
  "image_sha256": "2f1a...<64 hex>",
  "mask_sha256": null,
  "files": { "image_relpath": "image.jpg", "mask_relpath": null, "extra": [] },
  "inference_summary": { "ribeye_bbox": [120, 88, 420, 300], "mask_iou_hint": 0.76 }
}
```

### 5.3 Webhook (Lambda → Server) example
Headers:
```
X-CTI-Timestamp: 1760029112
X-CTI-Signature: sha256=ab12cd34...ef
```
Body:
```json
{
  "bucket": "cti-dev-406214277746",
  "ingest_key": "raw/dev-0001/2025/09/09/cap_1757423584/",
  "device_code": "dev-0001",
  "objects": ["image.jpg", "meta.json"],
  "meta_json": { "...": "as above" }
}
```

### 5.4 Server mapping → rows (illustrative)
```sql
-- Upsert device
INSERT INTO devices(device_code, label, s3_prefix_hint, last_upload_at, captures_count)
VALUES ('dev-0001','North Barn Pi','raw/dev-0001/', now(), 1)
ON CONFLICT (device_code) DO UPDATE
SET last_upload_at = excluded.last_upload_at,
    captures_count = devices.captures_count + 1;

-- Create assets
INSERT INTO assets(bucket, object_key, sha256, size_bytes, mime_type)
VALUES 
 ('cti-dev-406214277746','raw/dev-0001/2025/09/09/cap_1757423584/image.jpg','2f1a...','123456','image/jpeg')
RETURNING id;

-- Create scan
INSERT INTO scans(capture_id, ingest_key, device_id, gps, captured_at, status, image_asset_id)
VALUES (
  'cap_1757423584',
  's3://cti-dev-406214277746/raw/dev-0001/2025/09/09/cap_1757423584/',
  (SELECT id FROM devices WHERE device_code='dev-0001'),
  ST_SetSRID(ST_MakePoint(-79.3832, 43.6532), 4326),
  '2025-09-09T14:18:32Z',
  'ingested',
  (SELECT id FROM assets WHERE object_key LIKE '%cap_1757423584/image.jpg' LIMIT 1)
);

-- Log event
INSERT INTO scan_events(scan_id, event, meta)
SELECT s.id, 'ingested', '{"source":"lambda"}'::jsonb
FROM scans s WHERE s.capture_id='cap_1757423584';
```

### 5.5 Grading result (example)
```sql
INSERT INTO grading_results(
  scan_id, model_name, model_version, inference_sha256, confidence, confidence_breakdown, features_used, created_by
) VALUES (
  (SELECT id FROM scans WHERE capture_id='cap_1757423584'),
  'ribeye-unetpp', '1.2.0', 'd9c4...<64 hex>', 0.8732,
  '{"mask_iou":0.84,"edge_quality":0.78,"snr":18.3}'::jsonb,
  '{"roi_area_px":46210,"mean_intensity":128.4,"texture_glcm_contrast":0.322}'::jsonb,
  (SELECT id FROM users WHERE email='tech@example.com')
);
```

---

## 6) Conventions & Constraints
- **SRID:** 4326 for all geometry; store GPS as `Point(lon, lat)`.
- **Timestamps:** UTC ISO 8601; DB `timestamptz`.
- **Idempotency:** `scans.ingest_key` UNIQUE; retry-safe webhook.
- **Hashes:** sha256 hex(64) for assets & model bundle (`inference_sha256`).
- **Status transitions:** `uploaded → ingested → graded`; errors recorded in `scan_events` and `ingestion_log`.
- **FK behavior:** default `ON DELETE RESTRICT` (avoid accidental data loss).

---

## 7) Sample Queries
```sql
-- Recent scans for a device (with image URLs later signed in API)
SELECT s.id, s.capture_id, s.captured_at, a.bucket, a.object_key
FROM scans s
JOIN assets a ON a.id = s.image_asset_id
WHERE s.device_id = (SELECT id FROM devices WHERE device_code='dev-0001')
ORDER BY s.captured_at DESC LIMIT 50;

-- Latest grading per scan
SELECT DISTINCT ON (g.scan_id)
  g.scan_id, g.model_name, g.model_version, g.confidence, g.created_at
FROM grading_results g
ORDER BY g.scan_id, g.created_at DESC;

-- Scans within a farm polygon
SELECT s.*
FROM scans s
JOIN farms f ON f.id = s.farm_id
WHERE ST_Contains(f.geofence, s.gps);
```

---

## 8) Validation Checklist (Data Sync)
- [ ] `meta.json` validates against v1.0.0 schema
- [ ] Path structure matches `ingest_key` (directory per capture)
- [ ] Device exists or is upserted by webhook handler
- [ ] `assets` rows exist for each object; hashes populated
- [ ] `scans` row created exactly once per `ingest_key`
- [ ] `scan_events` contains `uploaded/ingested/graded` transitions
- [ ] `grading_results` has `model@version` and `inference_sha256`
- [ ] Signed URLs resolve for image/mask assets via API
- [ ] All timestamps are UTC

---

## 9) Versioning & Evolution
- **Schema tags:** bump `meta_version` for breaking changes; additive fields do not require a bump.  
- **DB migrations:** Alembic; never edit tables in place without a migration.  
- **Model lineage:** record `model_name`, `model_version`, and `inference_sha256` for full reproducibility.

---

## 10) Appendix — Enumerations
- `roles.name` ∈ {`admin`, `technician`, `farmer`}  
- `scan_status` ∈ {`uploaded`, `ingested`, `graded`, `error`}
