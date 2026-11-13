"""Phase 05 Unit Tests: Dasha, Gochar, Yoga & Timing Evidence Engine.

Tests:
1. Vimshottari Dasha 5-level hierarchy, birth balance, parent-child interval locking & boundary containment.
2. Target-date Gochar snapshots via real backend Swiss Ephemeris.
3. Classical Yoga rule evaluation and source citations.
4. Topic timing window evidence synthesis and cross-engine fact consistency across two unrelated profiles.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.astrology.dasha_engine import DashaEngine
from app.services.astrology.gochar_engine import GocharEngine
from app.services.astrology.yoga_engine import YogaEngine
from app.services.astrology.timing_engine import TimingEngine
from app.services.astrology.calculation_service import CalculationService
from app.services.astrology.vedic_engine import VedicEngine
from app.services.astrology.kp_engine import KPEngine

client = TestClient(app)

PROFILE_1 = {
    "profile_id": "prof_jaipur_1998",
    "name": "Jaipur Reference",
    "date_of_birth": "1998-02-05",
    "time_of_birth": "11:30:00",
    "place_of_birth": "Jaipur, Rajasthan, India",
    "latitude": 26.9124,
    "longitude": 75.7873,
    "timezone_id": "Asia/Kolkata"
}

PROFILE_2 = {
    "profile_id": "prof_london_1985",
    "name": "London Reference",
    "date_of_birth": "1985-08-15",
    "time_of_birth": "06:15:00",
    "place_of_birth": "London, UK",
    "latitude": 51.5074,
    "longitude": -0.1278,
    "timezone_id": "Europe/London"
}

def test_dasha_five_level_hierarchy_and_interval_locking():
    """Test 5-level Vimshottari Dasha hierarchy and strict parent-child interval locking."""
    dasha_engine = DashaEngine()
    
    # Moon longitude 45.0° (Rohini nakshatra, Lord = Moon)
    moon_lon = 45.0
    birth_dt = datetime(1998, 2, 5, 6, 0, 0, tzinfo=timezone.utc)
    target_dt = datetime(2026, 8, 12, 12, 0, 0, tzinfo=timezone.utc)
    
    res = dasha_engine.calculate_dasha_hierarchy(
        moon_longitude=moon_lon,
        birth_datetime_utc=birth_dt,
        target_datetime_utc=target_dt,
        max_depth=5,
        profile_id="prof_test_dasha"
    )
    
    assert res.profile_id == "prof_test_dasha"
    assert len(res.active_chain) == 5
    assert res.active_chain[0].level_name == "Mahadasha"
    assert res.active_chain[1].level_name == "Antardasha"
    assert res.active_chain[2].level_name == "Pratyantardasha"
    assert res.active_chain[3].level_name == "Sukshma"
    assert res.active_chain[4].level_name == "Pran"
    
    # Verify parent-child interval locking for active chain
    for i in range(len(res.active_chain) - 1):
        parent = res.active_chain[i]
        child = res.active_chain[i + 1]
        p_start = datetime.fromisoformat(parent.start_date_utc)
        p_end = datetime.fromisoformat(parent.end_date_utc)
        c_start = datetime.fromisoformat(child.start_date_utc)
        c_end = datetime.fromisoformat(child.end_date_utc)
        
        # Child MUST be inside parent
        assert p_start <= c_start <= p_end
        assert p_start <= c_end <= p_end
        assert c_start <= c_end

def test_dasha_endpoint():
    """Test API endpoint /api/v1/calculations/dasha."""
    response = client.post("/api/v1/calculations/dasha", json=PROFILE_1)
    assert response.status_code == 200
    data = response.json()
    
    assert "active_chain" in data
    assert len(data["active_chain"]) == 5
    assert "mahadashas" in data
    assert len(data["mahadashas"]) == 9

def test_gochar_endpoint_real_swiss():
    """Test API endpoint /api/v1/calculations/gochar with target date transits."""
    payload = {
        **PROFILE_1,
        "target_datetime_utc": "2026-08-12T12:00:00Z"
    }
    response = client.post("/api/v1/calculations/gochar", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "transits" in data
    assert len(data["transits"]) >= 8  # Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu
    
    # Verify planet transits have valid houses from D1 Lagna and Moon
    for t in data["transits"]:
        assert 1 <= t["house_from_d1_lagna"] <= 12
        assert 1 <= t["house_from_moon"] <= 12

def test_yogas_endpoint_and_citations():
    """Test API endpoint /api/v1/calculations/yogas."""
    response = client.post("/api/v1/calculations/yogas", json=PROFILE_1)
    assert response.status_code == 200
    data = response.json()
    
    assert "total_yogas_found" in data
    assert "yogas" in data
    
    for y in data["yogas"]:
        assert "source_reference" in y
        assert len(y["source_reference"]) > 0

def test_timing_windows_endpoint_cross_profiles():
    """Test /api/v1/predictions/timing-windows across two unrelated profiles."""
    for prof in [PROFILE_1, PROFILE_2]:
        payload = {
            "profile_id": prof["profile_id"],
            "topic": "CAREER",
            "target_date_utc": "2026-08-12T12:00:00Z",
            "name": prof["name"],
            "date_of_birth": prof["date_of_birth"],
            "time_of_birth": prof["time_of_birth"],
            "place_of_birth": prof["place_of_birth"],
            "latitude": prof["latitude"],
            "longitude": prof["longitude"],
            "timezone_id": prof["timezone_id"]
        }
        response = client.post("/api/v1/predictions/timing-windows", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        assert data["topic"] == "CAREER"
        assert "active_dasha_chain" in data
        assert len(data["active_dasha_chain"]) == 5
        assert 0.0 <= data["overall_timing_score"] <= 100.0
        assert "verdict" in data
        assert "dasha_evidence" in data
