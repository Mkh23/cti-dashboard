"""Tests for farm access and management endpoints."""
import pytest

from app.models import Role, User, UserRole
from app.security import hash_password


def _create_user_with_role(db_session_factory, email: str, role_name: str, password: str = "password123"):
    session = db_session_factory()
    try:
        user = User(email=email, hashed_password=hash_password(password))
        session.add(user)
        session.commit()
        session.refresh(user)

        role = session.query(Role).filter_by(name=role_name).first()
        session.add(UserRole(user_id=user.id, role_id=role.id))
        session.commit()
        session.refresh(user)
        return user
    finally:
        session.close()


@pytest.fixture
def admin_user(test_db):
    return _create_user_with_role(test_db, "admin-farms@test.com", "admin")


@pytest.fixture
def farmer_user(test_db):
    return _create_user_with_role(test_db, "farmer@test.com", "farmer")


@pytest.fixture
def technician_user(test_db):
    return _create_user_with_role(test_db, "tech-farms@test.com", "technician")


@pytest.fixture
def admin_token(client, admin_user):
    response = client.post(
        "/auth/login",
        data={"username": admin_user.email, "password": "password123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def farmer_token(client, farmer_user):
    response = client.post(
        "/auth/login",
        data={"username": farmer_user.email, "password": "password123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def technician_token(client, technician_user):
    response = client.post(
        "/auth/login",
        data={"username": technician_user.email, "password": "password123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_farmer_can_create_and_list_own_farm(client, farmer_token, farmer_user):
    """Farmers can create a farm and only see their own farms."""
    create_resp = client.post(
        "/farms",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={"name": "Green Pastures"},
    )
    assert create_resp.status_code == 200
    farm = create_resp.json()
    assert farm["name"] == "Green Pastures"
    assert farm["can_edit"] is True
    owner_ids = {owner["user_id"] for owner in farm["owners"]}
    assert str(farmer_user.id) in owner_ids

    list_resp = client.get(
        "/farms",
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert list_resp.status_code == 200
    farms = list_resp.json()
    assert len(farms) == 1
    assert farms[0]["id"] == farm["id"]


def test_farmer_cannot_assign_other_owner(client, farmer_token, farmer_user, admin_user):
    """Farmers cannot assign farms to other users when creating."""
    resp = client.post(
        "/farms",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={"name": "North Field", "owner_ids": [str(admin_user.id)]},
    )
    assert resp.status_code == 403

    # Ensure no orphaned farm was created
    list_resp = client.get(
        "/farms",
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert list_resp.status_code == 200
    assert list_resp.json() == []


def test_admin_can_assign_owner(client, admin_token, farmer_user):
    """Admins can create farms for specific owners."""
    resp = client.post(
        "/farms",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Admin Ranch", "owner_ids": [str(farmer_user.id)]},
    )
    assert resp.status_code == 200
    farm = resp.json()
    assert farm["can_edit"] is True  # admin can always edit
    owner_ids = {owner["user_id"] for owner in farm["owners"]}
    assert str(farmer_user.id) in owner_ids


def test_owner_can_update_farm_name(client, farmer_token, farmer_user):
    """Farm owners can rename their farm."""
    create_resp = client.post(
        "/farms",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={"name": "Old Name"},
    )
    farm_id = create_resp.json()["id"]

    update_resp = client.put(
        f"/farms/{farm_id}",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={"name": "New Name"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "New Name"


def test_admin_can_update_owners(client, admin_token, farmer_user, technician_user):
    """Admins can change the owners of an existing farm."""
    create_resp = client.post(
        "/farms",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Shared Farm", "owner_ids": [str(farmer_user.id)]},
    )
    farm_id = create_resp.json()["id"]

    update_resp = client.put(
        f"/farms/{farm_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"owner_ids": [str(technician_user.id)]},
    )
    assert update_resp.status_code == 200
    owners = {owner["user_id"] for owner in update_resp.json()["owners"]}
    assert str(technician_user.id) in owners
    assert str(farmer_user.id) not in owners


def test_technician_cannot_view_other_farm(
    client,
    technician_token,
    technician_user,
    admin_token,
    farmer_user,
):
    """Technicians should not see farms they do not own."""
    # Admin creates a farm for the farmer
    create_for_farmer = client.post(
        "/farms",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Farmer Farm", "owner_ids": [str(farmer_user.id)]},
    )
    assert create_for_farmer.status_code == 200
    farmer_farm_id = create_for_farmer.json()["id"]

    # Technician creates their own farm
    create_for_technician = client.post(
        "/farms",
        headers={"Authorization": f"Bearer {technician_token}"},
        json={"name": "Technician Farm"},
    )
    assert create_for_technician.status_code == 200

    list_resp = client.get(
        "/farms",
        headers={"Authorization": f"Bearer {technician_token}"},
    )
    assert list_resp.status_code == 200
    farms = list_resp.json()
    assert len(farms) == 1
    assert farms[0]["name"] == "Technician Farm"

    detail_resp = client.get(
        f"/farms/{farmer_farm_id}",
        headers={"Authorization": f"Bearer {technician_token}"},
    )
    assert detail_resp.status_code == 403

