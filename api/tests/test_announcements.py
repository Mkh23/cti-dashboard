"""Tests for announcement endpoints."""
import pytest

from app.models import User, Role, UserRole
from app.security import hash_password


@pytest.fixture
def admin_user(test_db):
    db = test_db()
    user = User(email="announce-admin@test.com", hashed_password=hash_password("password123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    admin_role = db.query(Role).filter_by(name="admin").first()
    db.add(UserRole(user_id=user.id, role_id=admin_role.id))
    db.commit()
    db.close()
    return user


@pytest.fixture
def admin_token(client, admin_user):
    response = client.post(
        "/auth/login",
        data={"username": admin_user.email, "password": "password123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_public_announcements_empty(client):
    response = client.get("/announcements")
    assert response.status_code == 200
    assert response.json() == []


def test_admin_can_create_and_list_announcements(client, admin_token):
    create_resp = client.post(
        "/admin/announcements",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "subject": "System notice",
            "content_html": "<p>Hello world</p>",
            "show_on_home": True,
            "pinned": True,
        },
    )
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["subject"] == "System notice"
    assert created["content_html"] == "<p>Hello world</p>"
    assert created["show_on_home"] is True
    assert created["pinned"] is True

    list_resp = client.get(
        "/admin/announcements",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    update_resp = client.put(
        f"/admin/announcements/{created['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"subject": "Updated", "show_on_home": False, "pinned": False},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["subject"] == "Updated"
    assert updated["show_on_home"] is False
    assert updated["pinned"] is False

    public_resp = client.get("/announcements")
    assert public_resp.status_code == 200
    public_items = public_resp.json()
    assert len(public_items) == 0
