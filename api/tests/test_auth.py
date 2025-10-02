"""Test auth endpoints."""
import pytest
from app.models import User, UserRole, Role

def test_register_first_user_becomes_admin(client, test_db):
    """Test that the first registered user becomes an admin."""
    response = client.post(
        "/auth/register",
        json={"email": "admin@example.com", "password": "StrongPass!123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@example.com"
    assert "id" in data
    
    # Check that user has admin role
    db = test_db()
    user = db.query(User).filter_by(email="admin@example.com").first()
    assert user is not None
    
    user_roles = db.query(UserRole).filter_by(user_id=user.id).all()
    assert len(user_roles) == 1
    
    role = db.query(Role).filter_by(id=user_roles[0].role_id).first()
    assert role.name == "admin"
    db.close()

def test_register_second_user_becomes_technician(client, test_db):
    """Test that subsequent users become technicians."""
    # Register first user (admin)
    response1 = client.post(
        "/auth/register",
        json={"email": "admin@example.com", "password": "StrongPass!123"}
    )
    assert response1.status_code == 200
    
    # Register second user (should be technician)
    response2 = client.post(
        "/auth/register",
        json={"email": "tech@example.com", "password": "StrongPass!123"}
    )
    assert response2.status_code == 200
    data = response2.json()
    assert data["email"] == "tech@example.com"
    
    # Check that second user has technician role
    db = test_db()
    user = db.query(User).filter_by(email="tech@example.com").first()
    assert user is not None
    
    user_roles = db.query(UserRole).filter_by(user_id=user.id).all()
    assert len(user_roles) == 1
    
    role = db.query(Role).filter_by(id=user_roles[0].role_id).first()
    assert role.name == "technician"
    db.close()

def test_register_duplicate_email(client):
    """Test that duplicate email registration fails."""
    # Register first user
    response1 = client.post(
        "/auth/register",
        json={"email": "admin@example.com", "password": "StrongPass!123"}
    )
    assert response1.status_code == 200
    
    # Try to register with same email
    response2 = client.post(
        "/auth/register",
        json={"email": "admin@example.com", "password": "DifferentPass!456"}
    )
    assert response2.status_code == 400
    assert "Email already registered" in response2.json()["detail"]

def test_register_without_roles_seeded(client_without_roles):
    """Test that registration fails gracefully when roles aren't seeded."""
    response = client_without_roles.post(
        "/auth/register",
        json={"email": "admin@example.com", "password": "StrongPass!123"}
    )
    assert response.status_code == 500
    assert "Database not properly initialized" in response.json()["detail"]
    assert "alembic upgrade head" in response.json()["detail"]

def test_login_success(client):
    """Test successful login."""
    # Register user first
    client.post(
        "/auth/register",
        json={"email": "admin@example.com", "password": "StrongPass!123"}
    )
    
    # Login
    response = client.post(
        "/auth/login",
        data={"username": "admin@example.com", "password": "StrongPass!123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client):
    """Test login with invalid credentials."""
    # Register user first
    client.post(
        "/auth/register",
        json={"email": "admin@example.com", "password": "StrongPass!123"}
    )
    
    # Try login with wrong password
    response = client.post(
        "/auth/login",
        data={"username": "admin@example.com", "password": "WrongPass!123"}
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]

def test_login_nonexistent_user(client):
    """Test login with nonexistent user."""
    response = client.post(
        "/auth/login",
        data={"username": "nonexistent@example.com", "password": "SomePass!123"}
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]

def test_me_endpoint(client):
    """Test /me endpoint returns user info with roles."""
    # Register and login
    client.post(
        "/auth/register",
        json={"email": "admin@example.com", "password": "StrongPass!123"}
    )
    
    login_response = client.post(
        "/auth/login",
        data={"username": "admin@example.com", "password": "StrongPass!123"}
    )
    token = login_response.json()["access_token"]
    
    # Get user info
    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@example.com"
    assert "id" in data
    assert "roles" in data
    assert "admin" in data["roles"]

def test_me_endpoint_unauthorized(client):
    """Test /me endpoint without token."""
    response = client.get("/me")
    assert response.status_code == 401
    assert "Missing token" in response.json()["detail"]

def test_me_endpoint_invalid_token(client):
    """Test /me endpoint with invalid token."""
    response = client.get(
        "/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
    assert "Invalid token" in response.json()["detail"]

def test_register_validates_email_format(client):
    """Test that registration validates email format."""
    response = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "StrongPass!123"}
    )
    assert response.status_code == 422  # Validation error

def test_password_is_hashed(client, test_db):
    """Test that passwords are hashed and not stored in plain text."""
    password = "StrongPass!123"
    client.post(
        "/auth/register",
        json={"email": "admin@example.com", "password": password}
    )
    
    # Check database
    db = test_db()
    user = db.query(User).filter_by(email="admin@example.com").first()
    assert user is not None
    assert user.hashed_password != password
    assert user.hashed_password.startswith("$2b$")  # bcrypt hash format
    db.close()

def test_user_has_timestamps(client, test_db):
    """Test that users have created_at and updated_at timestamps."""
    client.post(
        "/auth/register",
        json={"email": "admin@example.com", "password": "StrongPass!123"}
    )
    
    # Check database
    db = test_db()
    user = db.query(User).filter_by(email="admin@example.com").first()
    assert user is not None
    assert user.created_at is not None
    assert user.updated_at is not None
    assert user.created_at == user.updated_at  # Should be same on creation
    db.close()
