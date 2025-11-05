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