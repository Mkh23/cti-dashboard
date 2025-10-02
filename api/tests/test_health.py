"""Test health endpoints."""

def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"ok": True, "service": "cti-api"}

def test_readiness_endpoint(client):
    """Test readiness check endpoint."""
    response = client.get("/readyz")
    assert response.status_code == 200
    data = response.json()
    assert "ok" in data
    assert "db" in data
    assert data["db"] == "connected"
