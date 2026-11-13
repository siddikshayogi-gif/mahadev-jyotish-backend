import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data

def test_readiness_check(client):
    response = client.get("/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "database" in data
    assert "swiss_ephemeris" in data
    assert "ai_provider" in data

def test_auth_session_creation(client):
    response = client.post("/api/v1/auth/session", json={"device_id": "test_device"})
    assert response.status_code == 200
    data = response.json()
    assert "session_token" in data
    assert "user_id" in data

def test_profile_creation_and_ownership(client):
    # 1. Create a profile with User A token
    headers_user_a = {"Authorization": "Bearer token_user_a_12345"}
    profile_payload = {
        "name": "Mahadev Test User",
        "date_of_birth": "1995-05-15",
        "time_of_birth": "08:30:00",
        "place_of_birth": "Jaipur, Rajasthan",
        "latitude": 26.9124,
        "longitude": 75.7873,
        "timezone_id": "Asia/Kolkata",
        "is_primary": True
    }
    
    res = client.post("/api/v1/profiles", json=profile_payload, headers=headers_user_a)
    assert res.status_code == 201
    created_profile = res.json()
    profile_id = created_profile["id"]
    assert created_profile["name"] == "Mahadev Test User"
    assert created_profile["user_id"].startswith("usr_token_user_a")

    # 2. User A can retrieve their profile
    res_get_a = client.get(f"/api/v1/profiles/{profile_id}", headers=headers_user_a)
    assert res_get_a.status_code == 200
    assert res_get_a.json()["id"] == profile_id

    # 3. User B attempting to access User A's profile is rejected with 403 Forbidden
    headers_user_b = {"Authorization": "Bearer token_user_b_67890"}
    res_get_b = client.get(f"/api/v1/profiles/{profile_id}", headers=headers_user_b)
    assert res_get_b.status_code == 403
    err = res_get_b.json()
    assert err["error"]["code"] == "FORBIDDEN"

def test_structured_error_format_on_404(client):
    res = client.get("/api/v1/profiles/prof_non_existent", headers={"Authorization": "Bearer token_dev"})
    assert res.status_code == 404
    body = res.json()
    assert "error" in body
    assert body["error"]["code"] == "NOT_FOUND"
    assert "message" in body["error"]
