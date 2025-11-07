"""Tests for animals management endpoints."""
import pytest

from app.models import Role, User, UserRole, Farm, UserFarm, Cattle
from app.security import hash_password


def _create_user_with_role(db_session_factory, email: str, role_name: str) -> User:
    session = db_session_factory()
    try:
        user = User(email=email, hashed_password=hash_password("password123"))
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
    return _create_user_with_role(test_db, "admin-animals@test.com", "admin")


@pytest.fixture
def farmer_user(test_db):
    return _create_user_with_role(test_db, "farmer-animals@test.com", "farmer")


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
        farm = Farm(name="Animals Farm")
        session.add(farm)
        session.commit()
        session.refresh(farm)
        session.add(UserFarm(user_id=farmer_user.id, farm_id=farm.id, is_owner=True))
        session.commit()
        return farm
    finally:
        session.close()


@pytest.fixture
def cattle(test_db, farm):
    session = test_db()
    try:
        herd = Cattle(name="Animals Herd", farm_id=farm.id)
        session.add(herd)
        session.commit()
        session.refresh(herd)
        return herd
    finally:
        session.close()


def test_farmer_can_create_animal(client, farmer_token, farm, cattle):
    payload = {
        "tag_id": "TAG-001",
        "rfid": "RFID-001",
        "farm_id": str(farm.id),
        "cattle_id": str(cattle.id),
    }
    resp = client.post(
        "/animals",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json=payload,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["rfid"] == "RFID-001"
    assert data["cattle_id"] == str(cattle.id)


def test_farmer_cannot_access_other_farm_animal(client, farmer_token, test_db):
    session = test_db()
    try:
        other_farm = Farm(name="Other Farm")
        session.add(other_farm)
        session.commit()
        session.refresh(other_farm)
        herd = Cattle(name="Other Herd", farm_id=other_farm.id)
        session.add(herd)
        session.commit()
        session.refresh(herd)
        session.execute(
            Cattle.__table__.update().where(Cattle.id == herd.id).values(name="Other Herd")
        )
    finally:
        session.close()

    resp = client.post(
        "/animals",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json={"tag_id": "TAG-FAIL", "farm_id": str(other_farm.id)},
    )
    assert resp.status_code == 403


def test_admin_can_update_animal(client, admin_token, farm, cattle):
    create_resp = client.post(
        "/animals",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"tag_id": "TAG-777", "farm_id": str(farm.id), "rfid": "RFID-777"},
    )
    assert create_resp.status_code == 200
    animal_id = create_resp.json()["id"]

    update_resp = client.put(
        f"/animals/{animal_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"cattle_id": str(cattle.id)},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["cattle_id"] == str(cattle.id)


def test_admin_can_delete_animal(client, admin_token, farm):
    resp = client.post(
        "/animals",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"tag_id": "DELETE-ME", "farm_id": str(farm.id)},
    )
    assert resp.status_code == 200
    animal_id = resp.json()["id"]

    delete_resp = client.delete(
        f"/animals/{animal_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_resp.status_code == 204
