"""Test auth endpoints."""
from app.models import Role, RegistrationStatus, User, UserRole

from .utils import registration_payload


def _register(client, email, **kwargs):
    """Helper to register a user."""
    return client.post("/auth/register", json=registration_payload(email, **kwargs))


def _login(client, email, password):
    return client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


def test_register_first_user_becomes_admin(client, test_db):
    response = _register(client, "admin@example.com", requested_role="technician")
    assert response.status_code == 200
    data = response.json()
    assert data["registration_status"] == RegistrationStatus.approved.value

    db = test_db()
    user = db.query(User).filter_by(email="admin@example.com").first()
    assert user.registration_status == RegistrationStatus.approved
    role = (
        db.query(Role)
        .join(UserRole, Role.id == UserRole.role_id)
        .filter(UserRole.user_id == user.id)
        .one()
    )
    assert role.name == "admin"
    db.close()


def test_second_user_pending_until_approved(client, test_db):
    _register(client, "admin@example.com")
    response = _register(client, "tech@example.com", requested_role="technician")
    assert response.json()["registration_status"] == RegistrationStatus.pending.value

    db = test_db()
    user = db.query(User).filter_by(email="tech@example.com").first()
    assert user.registration_status == RegistrationStatus.pending
    assert db.query(UserRole).filter_by(user_id=user.id).count() == 0
    db.close()


def test_register_duplicate_email(client):
    _register(client, "admin@example.com")
    dup = _register(client, "admin@example.com")
    assert dup.status_code == 400
    assert "Email already registered" in dup.json()["detail"]


def test_register_without_roles_seeded(client_without_roles):
    response = client_without_roles.post(
        "/auth/register", json=registration_payload("admin@example.com")
    )
    assert response.status_code == 500
    assert "Database not properly initialized" in response.json()["detail"]


def test_login_success(client):
    _register(client, "admin@example.com")
    response = _login(client, "admin@example.com", "StrongPass!123")
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_invalid_credentials(client):
    _register(client, "admin@example.com")
    resp = _login(client, "admin@example.com", "WrongPass!123")
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    resp = _login(client, "ghost@example.com", "SomePass!123")
    assert resp.status_code == 401


def test_pending_user_must_wait_for_admin_approval(client):
    _register(client, "admin@example.com")
    admin_token = _login(client, "admin@example.com", "StrongPass!123").json()[
        "access_token"
    ]

    pending = _register(client, "farmer@example.com", requested_role="farmer").json()
    denied = _login(client, "farmer@example.com", "StrongPass!123")
    assert denied.status_code == 403

    approve = client.post(
        f"/admin/users/{pending['id']}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"roles": ["farmer"]},
    )
    assert approve.status_code == 200

    allowed = _login(client, "farmer@example.com", "StrongPass!123")
    assert allowed.status_code == 200


def test_me_endpoint(client):
    _register(client, "admin@example.com")
    token = _login(client, "admin@example.com", "StrongPass!123").json()["access_token"]
    me = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    data = me.json()
    assert data["registration_status"] == RegistrationStatus.approved.value
    assert "admin" in data["roles"]


def test_me_endpoint_unauthorized(client):
    resp = client.get("/me")
    assert resp.status_code == 401


def test_me_endpoint_invalid_token(client):
    resp = client.get("/me", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401


def test_register_validates_email_format(client):
    payload = registration_payload("user@example.com")
    payload["email"] = "not-an-email"
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 422


def test_password_is_hashed(client, test_db):
    password = "StrongPass!123"
    _register(client, "admin@example.com", password=password)

    db = test_db()
    user = db.query(User).filter_by(email="admin@example.com").first()
    assert user.hashed_password != password
    assert user.hashed_password.startswith("$2b$")
    db.close()
