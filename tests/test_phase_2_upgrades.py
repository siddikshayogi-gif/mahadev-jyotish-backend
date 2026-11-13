"""Phase 2 User Retention Features Engine Tests."""
import asyncio
import datetime
from app.services.astrology.smart_muhurat_engine import SmartMuhuratEngine
from app.services.astrology.stress_alert_engine import MentalPeaceStressEngine
from app.services.astrology.numerology_synergy_engine import (
    NumerologySynergyEngine,
    calculate_moolank,
    calculate_bhagyank,
    calculate_namank
)
from app.api.v1.endpoints.calculations import calculate_natal, NatalCalculationRequest

async def test_smart_muhurat_engine():
    engine = SmartMuhuratEngine()
    req = NatalCalculationRequest(
        date_of_birth="1998-02-05",
        time_of_birth="11:30:00",
        place_of_birth="Jaipur, India",
        latitude=26.9124,
        longitude=75.7873,
        timezone_id="Asia/Kolkata"
    )
    canonical = await calculate_natal(req)
    res = engine.find_muhurats(canonical, category="MARRIAGE", days_ahead=15)

    assert res.category == "MARRIAGE"
    assert res.days_scanned == 15
    assert len(res.top_muhurats) > 0
    assert len(res.top_muhurats) <= 6
    assert res.top_muhurats[0].score >= res.top_muhurats[-1].score
    assert not res.top_muhurats[0].is_rahu_kaal
    print("Smart Muhurat Engine Test PASSED")

async def test_mental_peace_stress_engine():
    engine = MentalPeaceStressEngine()
    req = NatalCalculationRequest(
        date_of_birth="1998-02-05",
        time_of_birth="11:30:00",
        place_of_birth="Jaipur, India",
        latitude=26.9124,
        longitude=75.7873,
        timezone_id="Asia/Kolkata"
    )
    canonical = await calculate_natal(req)
    res = engine.evaluate_mental_peace(canonical)

    assert res.status in ["PEACEFUL", "MODERATE_PACING", "STRESS_ALERT"]
    assert 0 <= res.mental_peace_score <= 100
    assert len(res.mantra_hindi) > 0
    assert len(res.remedy_hindi) > 0
    print("Mental Peace & Stress Alert Engine Test PASSED")

def test_numerology_calculations():
    # DOB: 1998-02-05 -> Day=5 -> Moolank=5
    assert calculate_moolank("1998-02-05") == 5
    # DOB: 1998-02-05 -> 1+9+9+8+0+2+0+5 = 34 -> 3+4 = 7 -> Bhagyank=7
    assert calculate_bhagyank("1998-02-05") == 7
    # Name: "MAHADEV" -> Chaldean M(4)+A(1)+H(5)+A(1)+D(4)+E(5)+V(6) = 26 -> 2+6 = 8
    assert calculate_namank("MAHADEV", "CHALDEAN") == 8
    print("Numerology Calculations Test PASSED")

async def test_numerology_synergy_engine():
    engine = NumerologySynergyEngine()
    req = NatalCalculationRequest(
        name="Jaipur User",
        date_of_birth="1998-02-05",
        time_of_birth="11:30:00",
        place_of_birth="Jaipur, India",
        latitude=26.9124,
        longitude=75.7873,
        timezone_id="Asia/Kolkata"
    )
    canonical = await calculate_natal(req)
    res = engine.evaluate_synergy(canonical)

    assert res.moolank == 5
    assert res.moolank_ruler == "Mercury"
    assert res.bhagyank == 7
    assert res.bhagyank_ruler == "Ketu"
    assert 0 <= res.daily_energy_score <= 100
    print("Numerology & KP Synergy Engine Test PASSED")

async def main():
    await test_smart_muhurat_engine()
    await test_mental_peace_stress_engine()
    test_numerology_calculations()
    await test_numerology_synergy_engine()
    print("ALL PHASE 2 TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())
