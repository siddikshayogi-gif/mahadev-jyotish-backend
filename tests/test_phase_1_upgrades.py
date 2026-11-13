"""Phase 1 Core Astrology & KP Horary Upgrade Tests."""
import asyncio
import datetime
from app.services.astrology.kp_horary_engine import KPHoraryEngine, build_249_sub_lord_table
from app.services.astrology.vedic_engine import VedicEngine
from app.services.astrology.temporal_scanners import TemporalScanner
from app.services.astrology.prediction_protocol_service import PredictionProtocolService
from app.schemas.ai_chat import AskPredictionRequest
from app.api.v1.endpoints.calculations import calculate_natal, NatalCalculationRequest

def test_kp_249_table():
    table = build_249_sub_lord_table()
    assert len(table) == 249, f"Expected 249 divisions, got {len(table)}"
    assert table[0].number == 1
    assert table[0].star_lord == "Ketu"
    assert table[0].sub_lord == "Ketu"
    assert table[-1].number == 249
    assert table[-1].rashi_name == "Pisces"
    print("KP 249 Sub-Lord Table Test PASSED")

async def test_kp_horary_engine():
    engine = KPHoraryEngine()
    req = NatalCalculationRequest(
        date_of_birth="1998-02-05",
        time_of_birth="11:30:00",
        place_of_birth="Jaipur, India",
        latitude=26.9124,
        longitude=75.7873,
        timezone_id="Asia/Kolkata"
    )
    canonical = await calculate_natal(req)

    # Test Horary #7 (Marriage)
    res_7 = engine.evaluate_horary(7, canonical, category="MARRIAGE")
    assert res_7.horary_number == 7
    assert res_7.verdict in ["YES", "NO", "MIXED_DELAY"]
    assert 0 <= res_7.confidence_score <= 100

    # Test Horary #125 (Career)
    res_125 = engine.evaluate_horary(125, canonical, category="CAREER")
    assert res_125.horary_number == 125
    assert res_125.horary_lagna_star_lord != ""
    print("KP Horary Engine Test PASSED")

async def test_d30_d60_vargas():
    vedic_engine = VedicEngine()
    req = NatalCalculationRequest(
        date_of_birth="1998-02-05",
        time_of_birth="11:30:00",
        place_of_birth="Jaipur, India",
        latitude=26.9124,
        longitude=75.7873,
        timezone_id="Asia/Kolkata"
    )
    canonical = await calculate_natal(req)
    vedic = vedic_engine.calculate_vedic_chart(canonical)

    assert "D30" in vedic.vargas
    assert "D60" in vedic.vargas

    d60 = vedic.vargas["D60"]
    assert "d60_deities" in d60.metadata
    deities = d60.metadata["d60_deities"]
    assert "Moon" in deities
    assert "Ascendant" in deities
    print("D30 & D60 Divisional Charts Test PASSED")

async def test_time_travel_scanner():
    scanner = TemporalScanner()
    req = NatalCalculationRequest(
        date_of_birth="1998-02-05",
        time_of_birth="11:30:00",
        place_of_birth="Jaipur, India",
        latitude=26.9124,
        longitude=75.7873,
        timezone_id="Asia/Kolkata"
    )
    canonical = await calculate_natal(req)

    past_dt = datetime.datetime(2015, 8, 15, tzinfo=datetime.timezone.utc)
    res = await scanner.time_travel_scan(canonical, past_dt, topic="CAREER")

    assert res["topic"] == "CAREER"
    assert len(res["active_dasha_chain"]) == 5
    assert len(res["key_transits"]) > 0
    assert 0 <= res["timing_score"] <= 100
    print("Time Travel Scanner Test PASSED")

async def main():
    test_kp_249_table()
    await test_kp_horary_engine()
    await test_d30_d60_vargas()
    await test_time_travel_scanner()
    print("ALL PHASE 1 TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())
