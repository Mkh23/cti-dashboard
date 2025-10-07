"""Test scans management endpoints."""
import pytest
from datetime import datetime
from app.models import User, Role, UserRole, Device, Scan, ScanStatus, Asset, Farm


@pytest.fixture
def admin_user(test_db):
    """Create an admin user for testing."""
    db = test_db()
    
    from app.security import hash_password
    user = User(email="admin@scan.com", hashed_password=hash_password("password123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    
    admin_role = db.query(Role).filter_by(name="admin").first()
    db.add(UserRole(user_id=user.id, role_id=admin_role.id))
    db.commit()
    
    db.close()
    return user


@pytest.fixture
def technician_user(test_db):
    """Create a technician user for testing."""
    db = test_db()
    
    from app.security import hash_password
    user = User(email="tech@scan.com", hashed_password=hash_password("password123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    
    tech_role = db.query(Role).filter_by(name="technician").first()
    db.add(UserRole(user_id=user.id, role_id=tech_role.id))
    db.commit()
    
    db.close()
    return user


@pytest.fixture
def admin_token(client, admin_user):
    """Get JWT token for admin user."""
    response = client.post("/auth/login", data={
        "username": "admin@scan.com",
        "password": "password123"
    })
    return response.json()["access_token"]


@pytest.fixture
def tech_token(client, technician_user):
    """Get JWT token for technician user."""
    response = client.post("/auth/login", data={
        "username": "tech@scan.com",
        "password": "password123"
    })
    return response.json()["access_token"]


@pytest.fixture
def test_device(test_db):
    """Create a test device."""
    import uuid
    db = test_db()
    # Use unique device code to avoid conflicts between tests
    device_code = f"SCAN-DEV-{str(uuid.uuid4())[:8]}"
    device = Device(device_code=device_code, label="Scan Test Device")
    db.add(device)
    db.commit()
    db.refresh(device)
    device_id = device.id
    db.close()
    
    # Return the ID since the object is detached
    return device_id


@pytest.fixture
def test_scan(test_db, test_device):
    """Create a test scan."""
    db = test_db()
    scan = Scan(
        capture_id="cap_test_001",
        ingest_key="test-bucket/raw/SCAN-DEV-001/2025/01/01/cap_test_001/",
        device_id=test_device,
        status=ScanStatus.uploaded
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    scan_id = scan.id
    db.close()
    
    return scan_id


# ============ Scans Listing Tests ============

def test_list_scans_as_admin(client, admin_token, test_scan):
    """Admin can list all scans."""
    response = client.get(
        "/scans",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "scans" in data
    assert "total" in data
    assert "page" in data
    assert len(data["scans"]) >= 1


def test_list_scans_as_technician(client, tech_token, test_scan):
    """Technician can list scans."""
    response = client.get(
        "/scans",
        headers={"Authorization": f"Bearer {tech_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "scans" in data


def test_list_scans_unauthorized(client, test_scan):
    """Cannot list scans without authentication."""
    response = client.get("/scans")
    assert response.status_code == 401


def test_list_scans_with_status_filter(client, admin_token, test_scan):
    """Can filter scans by status."""
    response = client.get(
        "/scans?status=uploaded",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    # All returned scans should have uploaded status
    for scan in data["scans"]:
        assert scan["status"] == "uploaded"


def test_list_scans_with_pagination(client, admin_token, test_scan):
    """Can paginate scan results."""
    response = client.get(
        "/scans?page=1&per_page=5",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["per_page"] == 5


# ============ Scan Detail Tests ============

def test_get_scan_detail_as_admin(client, admin_token, test_scan):
    """Admin can view scan details."""
    response = client.get(
        f"/scans/{test_scan}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert str(data["id"]) == str(test_scan)
    assert "capture_id" in data
    assert "status" in data


def test_get_scan_detail_as_technician(client, tech_token, test_scan):
    """Technician can view scan details."""
    response = client.get(
        f"/scans/{test_scan}",
        headers={"Authorization": f"Bearer {tech_token}"}
    )
    assert response.status_code == 200


def test_get_scan_detail_not_found(client, admin_token):
    """Returns 404 for non-existent scan."""
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    response = client.get(
        f"/scans/{fake_uuid}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404


def test_get_scan_detail_unauthorized(client, test_scan):
    """Cannot view scan without authentication."""
    response = client.get(f"/scans/{test_scan}")
    assert response.status_code == 401


# ============ Scan Statistics Tests ============

def test_get_scan_stats_as_admin(client, admin_token, test_scan):
    """Admin can view scan statistics."""
    response = client.get(
        "/scans/stats",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "by_status" in data
    assert isinstance(data["by_status"], dict)


def test_get_scan_stats_as_technician(client, tech_token, test_scan):
    """Technician can view scan statistics."""
    response = client.get(
        "/scans/stats",
        headers={"Authorization": f"Bearer {tech_token}"}
    )
    assert response.status_code == 200


def test_get_scan_stats_unauthorized(client):
    """Cannot view stats without authentication."""
    response = client.get("/scans/stats")
    assert response.status_code == 401


# ============ Scan with Assets Tests ============

def test_scan_with_image_asset(test_db, test_device):
    """Scan can be linked to image asset."""
    db = test_db()
    
    # Create asset
    asset = Asset(
        bucket="test-bucket",
        object_key="raw/SCAN-DEV-001/image.jpg",
        sha256="abc123",
        size_bytes=1024,
        mime_type="image/jpeg"
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    
    # Create scan with asset
    scan = Scan(
        capture_id="cap_with_asset",
        ingest_key="test-bucket/raw/SCAN-DEV-001/2025/01/01/cap_with_asset/",
        device_id=test_device,
        image_asset_id=asset.id,
        status=ScanStatus.uploaded
    )
    db.add(scan)
    db.commit()
    
    # Verify link
    assert scan.image_asset_id == asset.id
    db.close()


def test_scan_with_mask_asset(test_db, test_device):
    """Scan can be linked to mask asset."""
    db = test_db()
    
    # Create assets
    image_asset = Asset(
        bucket="test-bucket",
        object_key="raw/SCAN-DEV-001/image.jpg",
        sha256="img123",
        size_bytes=1024,
        mime_type="image/jpeg"
    )
    mask_asset = Asset(
        bucket="test-bucket",
        object_key="raw/SCAN-DEV-001/mask.png",
        sha256="mask123",
        size_bytes=512,
        mime_type="image/png"
    )
    db.add_all([image_asset, mask_asset])
    db.commit()
    
    # Create scan with both assets
    scan = Scan(
        capture_id="cap_with_mask",
        ingest_key="test-bucket/raw/SCAN-DEV-001/2025/01/01/cap_with_mask/",
        device_id=test_device,
        image_asset_id=image_asset.id,
        mask_asset_id=mask_asset.id,
        status=ScanStatus.uploaded
    )
    db.add(scan)
    db.commit()
    
    # Verify links
    assert scan.image_asset_id == image_asset.id
    assert scan.mask_asset_id == mask_asset.id
    db.close()


# ============ Scan Status Tests ============

def test_scan_status_transitions(test_db, test_device):
    """Scan can transition through different statuses."""
    db = test_db()
    
    # Create scan in uploaded status
    scan = Scan(
        capture_id="cap_status_test",
        ingest_key="test-bucket/raw/SCAN-DEV-001/2025/01/01/cap_status_test/",
        device_id=test_device,
        status=ScanStatus.uploaded
    )
    db.add(scan)
    db.commit()
    assert scan.status == ScanStatus.uploaded
    
    # Update to ingested
    scan.status = ScanStatus.ingested
    db.commit()
    assert scan.status == ScanStatus.ingested
    
    # Update to graded
    scan.status = ScanStatus.graded
    db.commit()
    assert scan.status == ScanStatus.graded
    
    # Update to error
    scan.status = ScanStatus.error
    db.commit()
    assert scan.status == ScanStatus.error
    
    db.close()


def test_scan_with_farm(test_db, test_device):
    """Scan can be linked to a farm."""
    db = test_db()
    
    # Create farm
    farm = Farm(name="Test Scan Farm")
    db.add(farm)
    db.commit()
    db.refresh(farm)
    
    # Create scan with farm
    scan = Scan(
        capture_id="cap_with_farm",
        ingest_key="test-bucket/raw/SCAN-DEV-001/2025/01/01/cap_with_farm/",
        device_id=test_device,
        farm_id=farm.id,
        status=ScanStatus.uploaded
    )
    db.add(scan)
    db.commit()
    
    # Verify link
    assert scan.farm_id == farm.id
    db.close()


# ============ Enhanced Scan Detail Tests ============

def test_get_scan_detail_with_presigned_urls(client, admin_token, test_scan, test_db):
    """Scan detail includes presigned URLs for assets."""
    from unittest.mock import patch
    
    # Create assets for the scan
    db = test_db()
    scan = db.get(Scan, test_scan)
    
    # Create image asset
    image_asset = Asset(
        bucket="test-bucket",
        object_key="raw/SCAN-DEV-001/image.jpg",
        sha256="img123",
        size_bytes=1024,
        mime_type="image/jpeg"
    )
    db.add(image_asset)
    db.commit()
    db.refresh(image_asset)
    
    # Link asset to scan
    scan.image_asset_id = image_asset.id
    db.commit()
    db.close()
    
    # Mock presigned URL generation
    with patch('app.routers.scans.generate_presigned_url') as mock_url:
        mock_url.return_value = "https://example.com/signed-image.jpg"
        
        response = client.get(
            f"/scans/{test_scan}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "image_url" in data
        # URL generation should be attempted
        mock_url.assert_called()


def test_scan_detail_includes_device_info(client, admin_token, test_scan):
    """Scan detail includes related device information."""
    response = client.get(
        f"/scans/{test_scan}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "device_code" in data
    assert data["device_code"] is not None  # Device code exists
    assert data["device_label"] == "Scan Test Device"


def test_scan_detail_includes_farm_info(test_db, client, admin_token, test_device):
    """Scan detail includes farm information when available."""
    db = test_db()
    
    # Create farm
    farm = Farm(name="Detail Test Farm")
    db.add(farm)
    db.commit()
    db.refresh(farm)
    
    # Create scan with farm
    scan = Scan(
        capture_id="cap_detail_farm",
        ingest_key="test-bucket/raw/SCAN-DEV-001/2025/01/01/cap_detail_farm/",
        device_id=test_device,
        farm_id=farm.id,
        status=ScanStatus.uploaded
    )
    db.add(scan)
    db.commit()
    scan_id = scan.id
    db.close()
    
    response = client.get(
        f"/scans/{scan_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "farm_name" in data
    assert data["farm_name"] == "Detail Test Farm"
