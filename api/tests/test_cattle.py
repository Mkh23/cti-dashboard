"""Tests for cattle management endpoints."""
import pytest

from app.models import Role, User, UserRole, Farm, UserFarm, RegistrationStatus
from app.security import hash_password


def _create_user_with_role(db_session_factory, email: str, role_name: str) -> User:
    session = db_session_factory()
    try:
        user = User(
            email=email,
            hashed_password=hash_password("password123"),
            registration_status=RegistrationStatus.approved,
            is_active=True,
        )
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
    return _create_user_with_role(test_db, "admin-cattle@test.com", "admin")


@pytest.fixture
def farmer_user(test_db):
    return _create_user_with_role(test_db, "farmer-cattle@test.com", "farmer")


@pytest.fixture
def admin_token(client, admin_user):
    resp = client.post(
        "/auth/login",
        data={"username": admin_user.email, "password": "password123"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def farmer_token(client, farmer_user):
    resp = client.post(
        "/auth/login",
        data={"username": farmer_user.email, "password": "password123"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def farm(test_db, farmer_user):
    session = test_db()
    try:
        farm = Farm(name="Primary Farm")
        session.add(farm)
        session.commit()
        session.refresh(farm)
        session.add(UserFarm(user_id=farmer_user.id, farm_id=farm.id, is_owner=True))
        session.commit()
        return farm
    finally:
        session.close()


@pytest.fixture
def other_farm(test_db):
    session = test_db()
    try:
        farm = Farm(name="Other Farm")
        session.add(farm)
        session.commit()
        session.refresh(farm)
        return farm
    finally:
        session.close()


def test_admin_can_create_cattle(client, admin_token, farm):
    payload = {
        "name": "Herd Alpha",
        "external_id": "HERD-001",
        "born_date": "2020-01-01",
        "farm_id": str(farm.id),
    }
    resp = client.post(
        "/cattle",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == payload["name"]
    assert data["external_id"] == payload["external_id"]
    assert data["farm_id"] == str(farm.id)


def test_farmer_cannot_create_cattle_for_unowned_farm(client, farmer_token, other_farm):
    payload = {
        "name": "Unowned Herd",
        "farm_id": str(other_farm.id),
    }
    resp = client.post(
        "/cattle",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json=payload,
    )
    assert resp.status_code == 403


def test_farmer_lists_cattle_for_owned_farm(client, farmer_token, farm):
    create_resp = client.post(
        "/cattle",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={
            "name": "Owned Herd",
            "farm_id": str(farm.id),
            "born_date": "2022-05-05",
        },
    )
    assert create_resp.status_code == 200

    list_resp = client.get(
        "/cattle",
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert list_resp.status_code == 200
    herds = list_resp.json()
    assert any(herd["name"] == "Owned Herd" for herd in herds)
