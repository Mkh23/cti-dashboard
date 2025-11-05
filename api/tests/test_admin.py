"""Test admin endpoints."""
import pytest
from app.models import User, Role, UserRole, Farm, Device


@pytest.fixture
def admin_user(test_db):
    """Create an admin user for testing."""
    db = test_db()
    
    # Create user
    from app.security import hash_password
    user = User(email="admin@test.com", hashed_password=hash_password("password123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Assign admin role
    admin_role = db.query(Role).filter_by(name="admin").first()
    db.add(UserRole(user_id=user.id, role_id=admin_role.id))
    db.commit()
    
    db.close()
    return user


@pytest.fixture
def technician_user(test_db):
    """Create a technician user for testing."""
    db = test_db()
    
    # Create user
    from app.security import hash_password
    user = User(email="tech@test.com", hashed_password=hash_password("password123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Assign technician role
    tech_role = db.query(Role).filter_by(name="technician").first()
    db.add(UserRole(user_id=user.id, role_id=tech_role.id))
    db.commit()
    
    # Return just the ID to avoid detached instance issues
    user_id = user.id
    db.close()
    return user_id


@pytest.fixture
def admin_token(client, admin_user):
    """Get JWT token for admin user."""
    response = client.post("/auth/login", data={
        "username": "admin@test.com",
        "password": "password123"
    })
    return response.json()["access_token"]


@pytest.fixture
def tech_token(client, technician_user):
    """Get JWT token for technician user."""
    response = client.post("/auth/login", data={
        "username": "tech@test.com",
        "password": "password123"
    })
    return response.json()["access_token"]


# ============ User Management Tests ============

def test_list_users_as_admin(client, admin_token):
    """Admin can list all users."""
    response = client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    assert len(users) >= 1  # At least the admin user
    assert "full_name" in users[0]


def test_list_users_as_technician_forbidden(client, tech_token):
    """Non-admin cannot list users."""
    response = client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {tech_token}"}
    )
    assert response.status_code == 403
    assert "Admin only" in response.json()["detail"]


def test_list_users_unauthorized(client):
    """Cannot list users without authentication."""
    response = client.get("/admin/users")
    assert response.status_code == 401


def test_update_user_roles_as_admin(client, admin_token, technician_user):
    """Admin can update user roles."""
    response = client.put(
        f"/admin/users/{technician_user}/roles",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"roles": ["technician", "farmer"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert "technician" in data["roles"]
    assert "farmer" in data["roles"]
    assert "full_name" in data


def test_update_user_roles_invalid_role(client, admin_token, technician_user):
    """Cannot assign non-existent role."""
    response = client.put(
        f"/admin/users/{technician_user}/roles",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"roles": ["invalid_role"]}
    )
    assert response.status_code == 400


def test_update_user_roles_as_technician_forbidden(client, tech_token, technician_user):
    """Non-admin cannot update user roles."""
    response = client.put(
        f"/admin/users/{technician_user}/roles",
        headers={"Authorization": f"Bearer {tech_token}"},
        json={"roles": ["admin"]}
    )
    assert response.status_code == 403


# ============ Device Management Tests ============

def test_create_device_as_admin(client, admin_token):
    """Admin can register a device."""
    response = client.post(
        "/admin/devices",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "device_code": "DEV-001",
            "label": "Test Device"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["device_code"] == "DEV-001"
    assert data["label"] == "Test Device"
    assert "id" in data


def test_list_devices_as_admin(client, admin_token):
    """Admin can list all devices."""
    # Create a device first
    client.post(
        "/admin/devices",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "device_code": "DEV-002",
            "label": "Device 2"
        }
    )
    
    response = client.get(
        "/admin/devices",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    devices = response.json()
    assert isinstance(devices, list)
    assert len(devices) >= 1


def test_create_device_duplicate_code(client, admin_token):
    """Cannot create device with duplicate device_code."""
    # Create first device
    client.post(
        "/admin/devices",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "device_code": "DEV-DUP",
            "label": "First"
        }
    )
    
    # Try to create duplicate
    response = client.post(
        "/admin/devices",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "device_code": "DEV-DUP",
            "label": "Second"
        }
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_create_device_as_technician_forbidden(client, tech_token):
    """Non-admin cannot create devices."""
    response = client.post(
        "/admin/devices",
        headers={"Authorization": f"Bearer {tech_token}"},
        json={
            "device_code": "DEV-003",
            "label": "Test Device"
        }
    )
    assert response.status_code == 403


def test_create_device_unauthorized(client):
    """Cannot create device without authentication."""
    response = client.post(
        "/admin/devices",
        json={
            "device_code": "DEV-004",
            "label": "Test Device"
        }
    )
    assert response.status_code == 401


def test_create_device_with_farm(client, admin_token, test_db):
    """Admin can create device linked to a farm."""
    # Create a farm first
    db = test_db()
    farm = Farm(name="Device Farm")
    db.add(farm)
    db.commit()
    db.refresh(farm)
    farm_id = str(farm.id)
    db.close()
    
    # Create device with farm
    response = client.post(
        "/admin/devices",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "device_code": "DEV-FARM",
            "label": "Farm Device",
            "farm_id": farm_id
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["farm_id"] == farm_id
