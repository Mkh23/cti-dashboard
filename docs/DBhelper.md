# Open psql
```
cd 'root/cti-dashboard'
docker compose exec -it db psql -U postgres -d cti
```

## see all users and roles:
This is the easiest, human-readable version:
```
SELECT 
    u.email,
    r.name AS role
FROM user_roles ur
JOIN users u ON ur.user_id = u.id
JOIN roles r ON ur.role_id = r.id
ORDER BY r.name, u.email;
```

# Drop and recreate the dev DB
From repo root; this wipes the current cti database
The database should be up!
```
./scripts/dev.sh 
docker compose exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS cti;"
docker compose exec -T db psql -U postgres -c "CREATE DATABASE cti;"
docker compose exec -T db psql -U postgres -d cti -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

# manually set admin pass:
cd api
. .venv/bin/activate
python - <<'PY'
from passlib.context import CryptContext
pwd = CryptContext(schemes=['bcrypt'], deprecated='auto')
print(pwd.hash('StrongPass!123'))
PY
-- set a new password for the admin user
UPDATE users SET password_hash = '$2b$12$KhSFkdSqhauDI2xWVnDcAOMJ5IlAypmmTluJHLSLqtQ7XPcOMYBIa' WHERE email = 'admin@example.com';


python - <<'PY'
from passlib.context import CryptContext
pwd = CryptContext(schemes=['bcrypt'], deprecated='auto')
print(pwd.hash('Mati@2322'))
PY

UPDATE users SET password_hash = '$2b$12$Ao2jK/IJAAJsBJG58DsZ4uQUnAP2U6OVt.W/UTzM88rB45VQzW8Z6' WHERE email = 'khalgh.m@gmail.com';


UPDATE users
SET hashed_password = '$2b$12$Ao2jK/IJAAJsBJG58DsZ4uQUnAP2U6OVt.W/UTzM88rB45VQzW8Z6'
WHERE email = 'khalgh.m@gmail.com';


# manually create admin through API

curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
        "email": "admin@example.com",
        "password": "StrongPass!123",
        "full_name": "Site Admin",
        "phone_number": "+1-555-1234",
        "address": "123 Ranch Road, Calgary, AB",
        "requested_role": "technician"
      }'



A) Fix the data now (psql)

Inside psql (cti=#):

1) See what’s there

SELECT id, name FROM roles ORDER BY id;
SELECT u.email, r.name
FROM user_roles ur
JOIN users u ON ur.user_id = u.id
JOIN roles r ON ur.role_id = r.id
ORDER BY u.email, r.name;


2) Upsert the three roles (idempotent)

-- create missing roles without touching existing ones
INSERT INTO roles (name) VALUES
  ('admin'),
  ('technician'),
  ('farmer')
ON CONFLICT (name) DO NOTHING;

-- check
SELECT id, name FROM roles ORDER BY id;


3) Give accounts the right roles

make your admin email an admin (replace the email):

INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u JOIN roles r ON r.name='admin'
WHERE u.email='admin@example.com'
  AND NOT EXISTS (
    SELECT 1 FROM user_roles ur
    WHERE ur.user_id=u.id AND ur.role_id=r.id
  );


keep your test users as technician/farmer:

INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u JOIN roles r ON r.name='technician'
WHERE u.email='tec@example.com'
  AND NOT EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id=u.id AND ur.role_id=r.id);

INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u JOIN roles r ON r.name='farmer'
WHERE u.email='farmer@example.com'
  AND NOT EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id=u.id AND ur.role_id=r.id);


4) Verify

SELECT u.email, string_agg(r.name, ', ' ORDER BY r.name) AS roles
FROM user_roles ur
JOIN users u ON ur.user_id=u.id
JOIN roles r ON ur.role_id=r.id
GROUP BY u.email
ORDER BY u.email;