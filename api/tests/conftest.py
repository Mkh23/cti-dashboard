"""Test configuration and fixtures."""
import os
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.db import Base, get_db
from app.main import app
from app.models import Role

# Use test PostgreSQL database
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/cti_test"
)

@pytest.fixture(scope="function")
def test_db():
    """Create a test database session."""
    engine = create_engine(TEST_DATABASE_URL)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, expire_on_commit=False, bind=engine
    )
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Seed roles (if not already present)
    session = TestingSessionLocal()
    try:
        existing_roles = session.query(Role).count()
        if existing_roles == 0:
            session.add_all([
                Role(id=1, name="admin"),
                Role(id=2, name="technician"),
                Role(id=3, name="farmer"),
            ])
            session.commit()
    finally:
        session.close()
    
    yield TestingSessionLocal
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with test database."""
    def override_get_db():
        try:
            db = test_db()
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def test_db_without_roles():
    """Create a test database session without seeded roles."""
    # Use a different database for this test to avoid conflicts
    test_url_no_roles = TEST_DATABASE_URL.replace("cti_test", "cti_test_no_roles")
    engine = create_engine(test_url_no_roles)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, expire_on_commit=False, bind=engine
    )
    
    # Create tables but DON'T seed roles
    Base.metadata.create_all(bind=engine)
    
    yield TestingSessionLocal
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

@pytest.fixture(scope="function")
def client_without_roles(test_db_without_roles):
    """Create a test client without seeded roles."""
    def override_get_db():
        try:
            db = test_db_without_roles()
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
