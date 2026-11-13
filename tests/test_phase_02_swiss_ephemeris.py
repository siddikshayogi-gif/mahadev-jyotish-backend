import pytest
import swisseph as swe
from fastapi.testclient import TestClient

from app.main import app
from app.services.astrology.swiss_provider import SwissEphemerisProvider
from app.services.astrology.calculation_service import CalculationService

@pytest.fixture
def client():
    return TestClient(app)

def test_strict_pyswisseph_runtime_calls():
    """Verify that pyswisseph is loaded and executes real C-library calls."""
    # 1. Version
    version_str = str(swe.version)
    assert version_str.startswith("2.")

    # 2. set_sid_mode Lahiri
    swe.set_sid_mode(swe.SIDM_LAHIRI)

    # 3. get_ayanamsa_ut
    jd_test = 2450849.75  # 1998-02-05 06:00:00 UTC
    ayanamsa = swe.get_ayanamsa_ut(jd_test)
    assert 23.0 < ayanamsa < 25.0

    # 4. calc_ut Sun
    res_trop, _ = swe.calc_ut(jd_test, swe.SUN, swe.FLG_SPEED)
    res_sid, _ = swe.calc_ut(jd_test, swe.SUN, swe.FLG_SIDEREAL | swe.FLG_SPEED)
    assert 0.0 <= res_trop[0] < 360.0
    assert 0.0 <= res_sid[0] < 360.0
    # Sidereal = Tropical - Ayanamsha (with nutation/aberration refinement)
    expected_sid = (res_trop[0] - ayanamsa) % 360.0
    assert abs(res_sid[0] - expected_sid) < 1e-2

    # 5. houses_ex Placidus
    cusps, ascmc = swe.houses_ex(jd_test, 26.9124, 75.7873, b'P', swe.FLG_SIDEREAL)
    assert len(cusps) >= 12
    assert len(ascmc) >= 2

def test_reference_profile_jaipur():
    """Reference Profile 1: Jaipur, Rajasthan (1998-02-05 11:30:00, Asia/Kolkata)."""
    service = CalculationService()
    result = service.calculate_natal(
        profile_id="prof_jaipur_ref",
        name="Reference Jaipur",
        birth_date="1998-02-05",
        birth_time="11:30:00",
        place_label="Jaipur, Rajasthan, India",
        latitude=26.9124,
        longitude=75.7873,
        timezone_id="Asia/Kolkata"
    )

    # UTC Conversion verification: 11:30 IST (+5:30) = 06:00 UTC
    assert result.birth.utc_instant.startswith("1998-02-05T06:00:00")
    assert abs(result.birth.julian_day_ut - 2450849.75) < 1e-4

    # Provider metadata
    assert result.provider.sidereal_mode == "LAHIRI"
    assert result.provider.ayanamsha_value > 23.8

    # Check planets count (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu = 9)
    assert len(result.planets) == 9

    planet_dict = {p.body: p for p in result.planets}
    assert "Sun" in planet_dict
    assert "Moon" in planet_dict
    assert "Rahu" in planet_dict
    assert "Ketu" in planet_dict

    # Invariant: Ketu is EXACTLY 180 degrees opposite Rahu
    rahu_lon = planet_dict["Rahu"].sidereal_longitude
    ketu_lon = planet_dict["Ketu"].sidereal_longitude
    diff = abs((ketu_lon - rahu_lon) % 360.0 - 180.0)
    assert diff < 1e-5

    # Ascendant & MC
    assert 0.0 <= result.angles.ascendant.sidereal_longitude < 360.0
    assert 0.0 <= result.angles.mc.sidereal_longitude < 360.0

    # 12 Placidus Cusps
    assert len(result.kp.cusps) == 12

def test_reference_profile_new_york():
    """Reference Profile 2: New York City (1990-07-04 16:30:00, America/New_York)."""
    service = CalculationService()
    result = service.calculate_natal(
        profile_id="prof_nyc_ref",
        name="Reference New York",
        birth_date="1990-07-04",
        birth_time="16:30:00",
        place_label="New York City, NY, USA",
        latitude=40.7128,
        longitude=-74.0060,
        timezone_id="America/New_York"
    )

    # UTC Conversion verification: 16:30 EDT (-4:00) = 20:30 UTC
    assert result.birth.utc_instant.startswith("1990-07-04T20:30:00")

    # Invariant check: Ketu opposite Rahu
    planet_dict = {p.body: p for p in result.planets}
    rahu_lon = planet_dict["Rahu"].sidereal_longitude
    ketu_lon = planet_dict["Ketu"].sidereal_longitude
    assert abs((ketu_lon - rahu_lon) % 360.0 - 180.0) < 1e-5

    # Check sign lords and sub lords populated
    for p in result.planets:
        assert p.sign_lord != ""
        assert p.star_lord != ""
        assert p.sub_lord != ""

def test_api_endpoint_natal_calculation(client):
    payload = {
        "profile_id": "prof_api_test",
        "name": "API Test User",
        "date_of_birth": "1998-02-05",
        "time_of_birth": "11:30:00",
        "place_of_birth": "Jaipur, Rajasthan, India",
        "latitude": 26.9124,
        "longitude": 75.7873,
        "timezone_id": "Asia/Kolkata"
    }
    response = client.post("/api/v1/calculations/natal", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "identity" in data
    assert "birth" in data
    assert "provider" in data
    assert "planets" in data
    assert "kp" in data
    assert data["provider"]["sidereal_mode"] == "LAHIRI"
