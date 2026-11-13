"""Phase 04 Automated Tests — KP (Krishnamurti Paddhati) Engine.

Verifies:
1. Exact Vimshottari proportional Sub Lord and Sub-Sub-Lord (SSL) calculation rules.
2. Placidus house planet assignments and cusp lordships.
3. 4-level House and Planet Significators matrix.
4. Ruling Planets (RP) derivation including Lagna, Moon, Day lord, and node proxies.
5. Deterministic Event House rule evidence generation.
6. REST API endpoint `POST /api/v1/calculations/kp`.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.astrology.calculation_service import CalculationService
from app.services.astrology.kp_engine import KPEngine, get_kp_sub_and_ssl

client = TestClient(app)

def test_exact_sub_and_ssl_lords():
    """Verify sub lord and SSL calculations for known longitude positions."""
    # Ashwini 0°00'00" (0.0°): Nakshatra = Ketu.
    # First sub lord in Ketu nakshatra is Ketu. First SSL under Ketu sub lord is Ketu.
    sub_lord, ssl_lord = get_kp_sub_and_ssl(0.0)
    assert sub_lord == "Ketu"
    assert ssl_lord == "Ketu"

    # Ashwini slightly offset (0.5°):
    # Ketu nakshatra arc = 13°20' (800 minutes). Ketu sub arc = 800 * (7/120) = 46.6667 minutes = 0.7777°
    # So 0.5° is still in Ketu sub.
    sub_lord_05, ssl_lord_05 = get_kp_sub_and_ssl(0.5)
    assert sub_lord_05 == "Ketu"

    # Longitude past Ketu sub lord (e.g. 1.0°): Next sub lord in Ketu nakshatra is Venus
    sub_lord_10, ssl_lord_10 = get_kp_sub_and_ssl(1.0)
    assert sub_lord_10 == "Venus"

def test_kp_engine_jaipur_calculation():
    """Verify KP Engine produces valid 12 cusps, planets, significators, ruling planets for Jaipur reference profile."""
    calc_service = CalculationService()
    canonical = calc_service.calculate_natal(
        profile_id="test_jaipur_kp",
        name="Jaipur KP Test",
        birth_date="1998-02-05",
        birth_time="11:30:00",
        place_label="Jaipur, Rajasthan, India",
        latitude=26.9124,
        longitude=75.7873,
        timezone_id="Asia/Kolkata"
    )

    kp_engine = KPEngine()
    res = kp_engine.calculate_kp(canonical)

    # 12 Placidus Cusps
    assert len(res.cusps) == 12
    for cusp in res.cusps:
        assert 1 <= cusp.house_number <= 12
        assert cusp.sign_lord in ["Mars", "Venus", "Mercury", "Moon", "Sun", "Jupiter", "Saturn"]
        assert cusp.star_lord in ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
        assert cusp.sub_lord in ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
        assert cusp.sub_sub_lord in ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]

    # 9 Planets
    assert len(res.planets) >= 9
    body_names = [p.body for p in res.planets]
    assert "Sun" in body_names
    assert "Moon" in body_names
    assert "Rahu" in body_names
    assert "Ketu" in body_names

    for p in res.planets:
        assert 1 <= p.house_occupying <= 12

    # House Significators (1..12)
    assert len(res.house_significators) == 12
    for hs in res.house_significators:
        assert hs.significators.level4_house_lord != ""
        assert len(hs.significators.combined_significators) > 0

    # Planet Significators
    assert len(res.planet_significators) >= 9

    # Ruling Planets
    assert res.ruling_planets.lagna_sign_lord != ""
    assert res.ruling_planets.lagna_star_lord != ""
    assert res.ruling_planets.moon_sign_lord != ""
    assert res.ruling_planets.moon_star_lord != ""
    assert res.ruling_planets.day_lord != ""

    # Event Evidences
    assert len(res.event_evidences) == 6
    event_names = [e.event_name for e in res.event_evidences]
    assert "Marriage & Relationships" in event_names
    assert "Career & Promotion" in event_names

def test_api_endpoint_kp_calculation():
    """Verify REST API endpoint POST /api/v1/calculations/kp."""
    payload = {
        "profile_id": "test_kp_api",
        "name": "API KP Test",
        "date_of_birth": "1998-02-05",
        "time_of_birth": "11:30:00",
        "place_of_birth": "Jaipur, Rajasthan, India",
        "latitude": 26.9124,
        "longitude": 75.7873,
        "timezone_id": "Asia/Kolkata"
    }
    response = client.post("/api/v1/calculations/kp", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "cusps" in data
    assert len(data["cusps"]) == 12
    assert "planets" in data
    assert "house_significators" in data
    assert "ruling_planets" in data
    assert "event_evidences" in data
    assert data["calculation_version"] == "4.0.0"
