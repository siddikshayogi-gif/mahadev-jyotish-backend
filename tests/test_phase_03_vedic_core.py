"""Phase 03 — Vedic Core Engine Tests.

Verifies deterministic calculation of:
- D1 Whole Sign houses
- D9 Navamsha boundaries & Lagnas
- D10 Dashamsha boundaries & Lagnas
- Vargottama detection
- Bhava Chalit Rashi invariance
- Chandra Kundali Moon-as-House-1 mapping
- House Lordship
- Planetary Dignities
- API Endpoint /api/v1/calculations/vedic
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.astrology.calculation_service import CalculationService
from app.services.astrology.vedic_engine import (
    VedicEngine,
    calculate_d9_rashi,
    calculate_d10_rashi,
    calculate_dignity
)
from app.schemas.vedic_astrology import Dignity

@pytest.fixture
def client():
    return TestClient(app)

def test_d9_navamsha_boundary_and_sign_rules():
    """Verify D9 Navamsha division logic across Movable, Fixed, Dual signs."""

    # 1. Movable Sign (Aries = 0): Navamsha 0 starts from Aries(0), Navamsha 8 is Sagittarius(8)
    # Aries 0°00' -> Navamsha 0 = Aries (0)
    assert calculate_d9_rashi(0.0) == (0, "Aries")
    # Aries 3°19' -> Navamsha 0 = Aries (0)
    assert calculate_d9_rashi(3.30) == (0, "Aries")
    # Aries 3°21' -> Navamsha 1 = Taurus (1)
    assert calculate_d9_rashi(3.35) == (1, "Taurus")
    # Aries 29°59' -> Navamsha 8 = Sagittarius (8)
    assert calculate_d9_rashi(29.99) == (8, "Sagittarius")

    # 2. Fixed Sign (Taurus = 1): Navamsha 0 starts from 9th sign = Capricorn (9)
    # Taurus 0°00' -> Navamsha 0 = Capricorn (9)
    assert calculate_d9_rashi(30.0) == (9, "Capricorn")
    # Taurus 3°21' -> Navamsha 1 = Aquarius (10)
    assert calculate_d9_rashi(33.35) == (10, "Aquarius")

    # 3. Dual Sign (Gemini = 2): Navamsha 0 starts from 5th sign = Libra (6)
    # Gemini 0°00' -> Navamsha 0 = Libra (6)
    assert calculate_d9_rashi(60.0) == (6, "Libra")
    # Gemini 3°21' -> Navamsha 1 = Scorpio (7)
    assert calculate_d9_rashi(63.35) == (7, "Scorpio")

def test_d10_dashamsha_boundary_and_sign_rules():
    """Verify D10 Dashamsha division logic across Odd and Even signs."""

    # 1. Odd Sign (Aries = 0): Dashamsha 0 starts from Aries(0)
    # Aries 0°00' -> Dashamsha 0 = Aries (0)
    assert calculate_d10_rashi(0.0) == (0, "Aries")
    # Aries 2°59' -> Dashamsha 0 = Aries (0)
    assert calculate_d10_rashi(2.9) == (0, "Aries")
    # Aries 3°01' -> Dashamsha 1 = Taurus (1)
    assert calculate_d10_rashi(3.1) == (1, "Taurus")

    # 2. Even Sign (Taurus = 1): Dashamsha 0 starts from 9th sign = Capricorn (9)
    # Taurus 0°00' -> Dashamsha 0 = Capricorn (9)
    assert calculate_d10_rashi(30.0) == (9, "Capricorn")
    # Taurus 3°01' -> Dashamsha 1 = Aquarius (10)
    assert calculate_d10_rashi(33.1) == (10, "Aquarius")

def test_dignity_engine_table():
    """Verify deterministic planetary dignity assignments."""
    # Sun in Aries 10° -> Exalted
    assert calculate_dignity("Sun", 0, 10.0) == Dignity.EXALTED
    # Sun in Libra 10° -> Debilitated
    assert calculate_dignity("Sun", 6, 10.0) == Dignity.DEBILITATED
    # Sun in Leo 10° -> Moolatrikona
    assert calculate_dignity("Sun", 4, 10.0) == Dignity.MOOLATRIKONA
    # Sun in Leo 25° -> Own Sign
    assert calculate_dignity("Sun", 4, 25.0) == Dignity.OWN_SIGN
    # Sun in Sagittarius (Jupiter lord, friend) -> Friendly
    assert calculate_dignity("Sun", 8, 15.0) == Dignity.FRIENDLY
    # Sun in Aquarius (Saturn lord, enemy) -> Enemy
    assert calculate_dignity("Sun", 10, 15.0) == Dignity.ENEMY

def test_jaipur_reference_vedic_chart():
    """Verify complete Vedic chart execution for Phase 02 Jaipur canonical result."""
    calc_service = CalculationService()
    canonical = calc_service.calculate_natal(
        profile_id="prof_jaipur_vedic",
        name="Jaipur Vedic Test",
        birth_date="1998-02-05",
        birth_time="11:30:00",
        place_label="Jaipur, Rajasthan, India",
        latitude=26.9124,
        longitude=75.7873,
        timezone_id="Asia/Kolkata"
    )

    engine = VedicEngine()
    vedic = engine.calculate_vedic_chart(canonical)

    # 1. Verify Lagnas
    # D1 Lagna: 17.52° Aries (0)
    assert vedic.d1_lagna.rashi == 0
    assert vedic.d1_lagna.rashi_name == "Aries"

    # D9 Lagna for 17.52° Aries: Aries is Movable, 17.52° / 3.3333 = Navamsha index 5 (Virgo = 5)
    # 0 (Aries) + 5 = 5 (Virgo)
    assert vedic.d9_lagna.rashi == 5
    assert vedic.d9_lagna.rashi_name == "Virgo"

    # D10 Lagna for 17.52° Aries: Aries is Odd, 17.52° / 3.0 = Dashamsha index 5 (Virgo = 5)
    # 0 (Aries) + 5 = 5 (Virgo)
    assert vedic.d10_lagna.rashi == 5
    assert vedic.d10_lagna.rashi_name == "Virgo"

    # Chandra Lagna: Moon at 38.92° (Taurus = 1)
    assert vedic.chandra_lagna.rashi == 1
    assert vedic.chandra_lagna.rashi_name == "Taurus"

    # 2. Check Whole Sign D1 Planet placements
    p_map = {p.body: p for p in vedic.planets}
    assert "Sun" in p_map
    assert p_map["Sun"].house_d1 == 10  # Sun in Capricorn (9), Aries Lagna (0) -> House 10
    assert p_map["Moon"].house_d1 == 2  # Moon in Taurus (1), Aries Lagna -> House 2

    # 3. Check Vargottama status (Sun in Capricorn(9), D9 in Taurus(1) -> False; check Revati Saturn or others)
    for p in vedic.planets:
        if p.rashi == p.d9_rashi:
            assert p.vargottama is True
        else:
            assert p.vargottama is False

    # 4. Check Bhava Chalit Rashi Invariance
    # Rashi MUST NOT change between D1 and Bhava Chalit
    for p in vedic.planets:
        assert p.rashi == canonical.planets[next(i for i, cp in enumerate(canonical.planets) if cp.body == p.body)].rashi

    # 5. Check Chandra Kundali (Moon in Taurus = House 1)
    # Planet in Taurus should be in House 1 of Chandra Kundali
    for p in vedic.planets:
        expected_ck_house = ((p.rashi - 1) % 12) + 1
        assert p.chandra_kundali_house == expected_ck_house

    # 6. Check House Lordships (12 houses)
    assert len(vedic.house_lordships) == 12
    # House 1 (Aries) -> Lord Mars
    assert vedic.house_lordships[0].house_lord == "Mars"
    assert vedic.house_lordships[0].rashi_name == "Aries"
    # House 2 (Taurus) -> Lord Venus
    assert vedic.house_lordships[1].house_lord == "Venus"

def test_api_endpoint_vedic_calculation(client):
    payload = {
        "profile_id": "prof_vedic_api",
        "name": "API Vedic User",
        "date_of_birth": "1998-02-05",
        "time_of_birth": "11:30:00",
        "place_of_birth": "Jaipur, Rajasthan, India",
        "latitude": 26.9124,
        "longitude": 75.7873,
        "timezone_id": "Asia/Kolkata"
    }
    response = client.post("/api/v1/calculations/vedic", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "d1_lagna" in data
    assert "d9_lagna" in data
    assert "d10_lagna" in data
    assert "chandra_lagna" in data
    assert "planets" in data
    assert "house_lordships" in data
    assert "vargas" in data
    assert "bhava_chalit" in data
    assert "chandra_kundali" in data
