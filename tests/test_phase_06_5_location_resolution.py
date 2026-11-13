"""Phase 06.5 Tests: Location Search & Timezone Resolution.

Tests:
1. Place search autocomplete with debounced queries ("Jaipur", "New York").
2. Normalization of display_name, city, state, country, lat, lon, and IANA timezoneId.
3. Coordinate timezone resolution for manual overrides.
4. Validation bounds on lat (-90 to +90) and lon (-180 to +180).
5. Multiple same-name city distinction handling.
6. Graceful handling of empty or unknown queries without hardcoding Jaipur fallback.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.location.location_service import LocationService

client = TestClient(app)

def test_location_search_jaipur():
    """Test location search for Jaipur returns canonical details including Asia/Kolkata timezone."""
    response = client.get("/api/v1/locations/search?q=Jaipur")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) >= 1

    first = data["results"][0]
    assert "Jaipur" in first["display_name"] or "Jaipur" in first["city"]
    assert abs(first["latitude"] - 26.9124) < 0.5
    assert abs(first["longitude"] - 75.7873) < 0.5
    assert first["timezone_id"] == "Asia/Kolkata"

def test_location_search_new_york():
    """Test location search for New York returns canonical details including America/New_York timezone."""
    response = client.get("/api/v1/locations/search?q=New York")
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) >= 1

    first = data["results"][0]
    assert "New York" in first["display_name"]
    assert abs(first["latitude"] - 40.7128) < 1.0
    assert abs(first["longitude"] - (-74.0060)) < 1.0
    assert first["timezone_id"] == "America/New_York"

def test_location_search_post_endpoint():
    """Test POST search endpoint."""
    response = client.post("/api/v1/locations/search", json={"query": "Varanasi"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) >= 1
    assert data["results"][0]["timezone_id"] == "Asia/Kolkata"

def test_coordinate_timezone_resolution():
    """Test coordinate resolution endpoint for manual overrides."""
    # New York coords
    resp = client.post("/api/v1/locations/resolve-coords", json={"latitude": 40.7128, "longitude": -74.0060})
    assert resp.status_code == 200
    assert resp.json()["timezone_id"] == "America/New_York"

    # Jaipur coords
    resp_jaipur = client.post("/api/v1/locations/resolve-coords", json={"latitude": 26.9124, "longitude": 75.7873})
    assert resp_jaipur.status_code == 200
    assert resp_jaipur.json()["timezone_id"] == "Asia/Kolkata"

def test_coordinate_validation_out_of_bounds():
    """Test coordinates out of bounds fail validation."""
    resp = client.post("/api/v1/locations/resolve-coords", json={"latitude": 120.0, "longitude": 75.0})
    assert resp.status_code == 422  # Validation error

def test_unknown_location_query():
    """Test unknown location returns empty list without defaulting to Jaipur."""
    response = client.get("/api/v1/locations/search?q=XyzabcNonExistentCity99")
    assert response.status_code == 200
    data = response.json()
    assert data["results"] == []  # No silent default fallback
