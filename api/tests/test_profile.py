"""Test profile management endpoints."""
import pytest
from app.models import User, UserRole, Role


def test_get_profile_with_all_fields(client, test_db):
    """Test getting profile with all fields populated."""
    # Register a user
    response = client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "StrongPass!123"}
    )
    assert response.status_code == 200
    
    # Login
    login_response = client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "StrongPass!123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Update profile with all fields
    update_response = client.put(
        "/me",
        json={
            "full_name": "John Doe",
            "phone_number": "+1-555-1234",
            "address": "123 Main St, City, State 12345"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert update_response.status_code == 200
    
    # Get profile
    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@example.com"
    assert data["full_name"] == "John Doe"
    assert data["phone_number"] == "+1-555-1234"
    assert data["address"] == "123 Main St, City, State 12345"
    assert "admin" in data["roles"]


def test_update_profile_partial(client, test_db):
    """Test updating only some profile fields."""
    # Register and login
    client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "StrongPass!123"}
    )
    login_response = client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "StrongPass!123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = login_response.json()["access_token"]
    
    # Update only full_name
    response = client.put(
        "/me",
        json={"full_name": "Jane Smith"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Jane Smith"
    assert data["phone_number"] is None
    assert data["address"] is None
    
    # Update only phone_number
    response = client.put(
        "/me",
        json={"phone_number": "+1-555-9999"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Jane Smith"  # Should be preserved
    assert data["phone_number"] == "+1-555-9999"
    assert data["address"] is None


def test_update_profile_unauthorized(client, test_db):
    """Test updating profile without authentication."""
    response = client.put(
        "/me",
        json={"full_name": "John Doe"}
    )
    assert response.status_code == 401


def test_change_password_success(client, test_db):
    """Test successfully changing password."""
    # Register and login
    client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "OldPass!123"}
    )
    login_response = client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "OldPass!123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = login_response.json()["access_token"]
    
    # Change password
    response = client.post(
        "/me/password",
        json={
            "current_password": "OldPass!123",
            "new_password": "NewPass!456"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Password changed successfully"
    
    # Verify old password no longer works
    login_response = client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "OldPass!123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert login_response.status_code == 401
    
    # Verify new password works
    login_response = client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "NewPass!456"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert login_response.status_code == 200


def test_change_password_wrong_current(client, test_db):
    """Test changing password with wrong current password."""
    # Register and login
    client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "CorrectPass!123"}
    )
    login_response = client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "CorrectPass!123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = login_response.json()["access_token"]
    
    # Try to change password with wrong current password
    response = client.post(
        "/me/password",
        json={
            "current_password": "WrongPass!123",
            "new_password": "NewPass!456"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "incorrect" in response.json()["detail"].lower()


def test_change_password_unauthorized(client, test_db):
    """Test changing password without authentication."""
    response = client.post(
        "/me/password",
        json={
            "current_password": "OldPass!123",
            "new_password": "NewPass!456"
        }
    )
    assert response.status_code == 401


def test_update_profile_all_roles(client, test_db):
    """Test that all roles (admin, technician, farmer) can update their profiles."""
    users = [
        ("admin@example.com", "AdminPass!123"),
        ("tech@example.com", "TechPass!123"),
        ("farmer@example.com", "FarmerPass!123"),
    ]
    
    # Register users
    for email, password in users:
        client.post("/auth/register", json={"email": email, "password": password})
    
    # Test each user can update their profile
    for idx, (email, password) in enumerate(users):
        # Login
        login_response = client.post(
            "/auth/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token = login_response.json()["access_token"]
        
        # Update profile
        response = client.put(
            "/me",
            json={
                "full_name": f"User {idx}",
                "phone_number": f"+1-555-{idx:04d}",
                "address": f"{idx} Test St"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == f"User {idx}"
        assert data["phone_number"] == f"+1-555-{idx:04d}"
        assert data["address"] == f"{idx} Test St"


def test_profile_persistence(client, test_db):
    """Test that profile updates persist across sessions."""
    # Register and login
    client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "Pass!123"}
    )
    login_response = client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "Pass!123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = login_response.json()["access_token"]
    
    # Update profile
    client.put(
        "/me",
        json={
            "full_name": "Persistent User",
            "phone_number": "+1-555-7777",
            "address": "777 Permanent Ave"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Login again (new session)
    login_response = client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "Pass!123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    new_token = login_response.json()["access_token"]
    
    # Verify profile data persisted
    response = client.get("/me", headers={"Authorization": f"Bearer {new_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Persistent User"
    assert data["phone_number"] == "+1-555-7777"
    assert data["address"] == "777 Permanent Ave"


def test_update_profile_empty_strings(client, test_db):
    """Test updating profile with empty strings."""
    # Register and login
    client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "Pass!123"}
    )
    login_response = client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "Pass!123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = login_response.json()["access_token"]
    
    # Set initial values
    client.put(
        "/me",
        json={
            "full_name": "John Doe",
            "phone_number": "+1-555-1234",
            "address": "123 Main St"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Update with empty strings (should clear fields)
    response = client.put(
        "/me",
        json={
            "full_name": "",
            "phone_number": "",
            "address": ""
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == ""
    assert data["phone_number"] == ""
    assert data["address"] == ""


def test_profile_includes_roles(client, test_db):
    """Test that profile response includes user roles."""
    # Register first user (becomes admin)
    client.post(
        "/auth/register",
        json={"email": "admin@example.com", "password": "Pass!123"}
    )
    
    # Register second user (becomes technician)
    client.post(
        "/auth/register",
        json={"email": "tech@example.com", "password": "Pass!123"}
    )
    
    # Check admin profile
    login_response = client.post(
        "/auth/login",
        data={"username": "admin@example.com", "password": "Pass!123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = login_response.json()["access_token"]
    
    response = client.put(
        "/me",
        json={"full_name": "Admin User"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "admin" in response.json()["roles"]
    
    # Check technician profile
    login_response = client.post(
        "/auth/login",
        data={"username": "tech@example.com", "password": "Pass!123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = login_response.json()["access_token"]
    
    response = client.put(
        "/me",
        json={"full_name": "Tech User"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "technician" in response.json()["roles"]
