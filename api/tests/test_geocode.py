from unittest.mock import MagicMock, patch
import os


def test_geocode_missing_api_key(client):
    with patch.dict(os.environ, {}, clear=True):
        response = client.post("/geocode", json={"city": "Calgary"})
    assert response.status_code == 500


def test_geocode_requires_input(client):
    with patch.dict(os.environ, {"OPENCAGE_API_KEY": "test-key"}):
        response = client.post("/geocode", json={})
    assert response.status_code == 400


def test_geocode_success(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {"geometry": {"lat": 51.05, "lng": -114.07}, "formatted": "Calgary, AB"}
        ]
    }
    with patch.dict(os.environ, {"OPENCAGE_API_KEY": "test-key"}):
        with patch("app.routers.geocode.requests.get", return_value=mock_response):
            response = client.post("/geocode", json={"city": "Calgary"})

    assert response.status_code == 200
    data = response.json()
    assert data["lat"] == 51.05
    assert data["lng"] == -114.07


def test_geofence_search_missing_dataset(client, tmp_path):
    with patch.dict(os.environ, {"GEOFENCE_DATA_ROOT": str(tmp_path)}):
        response = client.post(
            "/geofence/search",
            json={"lat": 51.05, "lng": -114.07, "province": "ZZ", "radius_km": 5},
        )
    assert response.status_code == 404
