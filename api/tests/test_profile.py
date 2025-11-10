"""Test profile management endpoints."""

from .utils import registration_payload


def _register(client, email, **kwargs):
    payload = registration_payload(email, **kwargs)
    return client.post("/auth/register", json=payload)


def _login(client, email, password):
    return client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


def _approve(client, token, user_id, roles):
    return client.post(
        f"/admin/users/{user_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={"roles": roles},
    )


def test_get_profile_with_all_fields(client):
    _register(
        client,
        "user@example.com",
        full_name="Initial",
        phone_number="+1-555-0000",
        address="Old Ranch",
    )
    token = _login(client, "user@example.com", "StrongPass!123").json()["access_token"]

    update = client.put(
        "/me",
        json={
            "full_name": "John Doe",
            "phone_number": "+1-555-1234",
            "address": "123 Main St, City, State 12345",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update.status_code == 200

    profile = client.get("/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert profile["full_name"] == "John Doe"
    assert profile["phone_number"] == "+1-555-1234"
    assert profile["address"] == "123 Main St, City, State 12345"


def test_update_profile_partial(client):
    _register(
        client,
        "user@example.com",
        full_name="Original Name",
        phone_number="+1-555-0000",
        address="Orig Address",
    )
    token = _login(client, "user@example.com", "StrongPass!123").json()["access_token"]

    first = client.put(
        "/me",
        json={"full_name": "Jane Smith"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert first["full_name"] == "Jane Smith"
    assert first["phone_number"] == "+1-555-0000"
    assert first["address"] == "Orig Address"

    second = client.put(
        "/me",
        json={"phone_number": "+1-555-9999"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert second["full_name"] == "Jane Smith"
    assert second["phone_number"] == "+1-555-9999"
    assert second["address"] == "Orig Address"


def test_update_profile_unauthorized(client):
    resp = client.put("/me", json={"full_name": "Nope"})
    assert resp.status_code == 401


def test_change_password_success(client):
    _register(client, "user@example.com", password="OldPass!123")
    token = _login(client, "user@example.com", "OldPass!123").json()["access_token"]

    resp = client.post(
        "/me/password",
        json={"current_password": "OldPass!123", "new_password": "NewPass!456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    assert _login(client, "user@example.com", "OldPass!123").status_code == 401
    assert _login(client, "user@example.com", "NewPass!456").status_code == 200


def test_change_password_wrong_current(client):
    _register(client, "user@example.com")
    token = _login(client, "user@example.com", "StrongPass!123").json()["access_token"]

    resp = client.post(
        "/me/password",
        json={"current_password": "WrongPass!123", "new_password": "NewPass!456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_change_password_unauthorized(client):
    resp = client.post(
        "/me/password",
        json={"current_password": "OldPass!123", "new_password": "NewPass!456"},
    )
    assert resp.status_code == 401


def test_update_profile_all_roles(client):
    admin_resp = _register(client, "admin@example.com")
    admin_token = _login(client, "admin@example.com", "StrongPass!123").json()[
        "access_token"
    ]

    others = [
        ("tech@example.com", "TechPass!123", ["technician"]),
        ("farmer@example.com", "FarmerPass!123", ["farmer"]),
    ]

    user_ids = {"admin@example.com": admin_resp.json()["id"]}
    for email, password, roles in others:
        pending = _register(client, email, password=password).json()
        user_ids[email] = pending["id"]
        assert (
            _approve(client, admin_token, pending["id"], roles).status_code == 200
        )

    for email, password, _roles in [("admin@example.com", "StrongPass!123", ["admin"])] + others:
        token = _login(client, email, password).json()["access_token"]
        updated = client.put(
            "/me",
            json={
                "full_name": f"{email}-name",
                "phone_number": "+1-555-1111",
                "address": "Test Ranch",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert updated.status_code == 200
        assert updated.json()["full_name"] == f"{email}-name"


def test_profile_persistence(client):
    _register(client, "user@example.com")
    token = _login(client, "user@example.com", "StrongPass!123").json()["access_token"]

    client.put(
        "/me",
        json={
            "full_name": "Persistent User",
            "phone_number": "+1-555-7777",
            "address": "777 Permanent Ave",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    new_token = _login(client, "user@example.com", "StrongPass!123").json()[
        "access_token"
    ]
    profile = client.get("/me", headers={"Authorization": f"Bearer {new_token}"}).json()
    assert profile["full_name"] == "Persistent User"


def test_update_profile_empty_strings(client):
    _register(client, "user@example.com")
    token = _login(client, "user@example.com", "StrongPass!123").json()["access_token"]

    client.put(
        "/me",
        json={
            "full_name": "Filled",
            "phone_number": "+1-555-2222",
            "address": "Filled St",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    cleared = client.put(
        "/me",
        json={"full_name": "", "phone_number": "", "address": ""},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert cleared["full_name"] == ""
    assert cleared["phone_number"] == ""
    assert cleared["address"] == ""


def test_profile_includes_roles(client):
    admin_resp = _register(client, "admin@example.com")
    admin_token = _login(client, "admin@example.com", "StrongPass!123").json()[
        "access_token"
    ]

    tech_resp = _register(client, "tech@example.com").json()
    _approve(client, admin_token, tech_resp["id"], ["technician"])

    admin_profile = client.put(
        "/me",
        json={"full_name": "Admin User"},
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()
    assert "admin" in admin_profile["roles"]

    tech_token = _login(client, "tech@example.com", "StrongPass!123").json()[
        "access_token"
    ]
    tech_profile = client.put(
        "/me",
        json={"full_name": "Tech User"},
        headers={"Authorization": f"Bearer {tech_token}"},
    ).json()
    assert "technician" in tech_profile["roles"]
