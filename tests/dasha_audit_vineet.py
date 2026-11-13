import os
import sys

# Add backend to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Inject mock before imports
import tests.mock_swisseph

import datetime
from app.services.astrology.calculation_service import CalculationService
from app.services.astrology.dasha_engine import DashaEngine, VIMSHOTTARI_LORDS, NAKSHATRA_ARC_DEG

def run_audit():
    birth_dt = datetime.datetime(1998, 2, 5, 6, 0, tzinfo=datetime.timezone.utc)

    calc_service = CalculationService()
    res = calc_service.calculate_natal(
        profile_id="vineet",
        name="Vineet Yogi",
        birth_date="1998-02-05",
        birth_time="11:30:00",
        place_label="Jaipur",
        latitude=26.9124,
        longitude=75.7873,
        timezone_id="Asia/Kolkata"
    )
    moon_lon = next(p.sidereal_longitude for p in res.planets if p.body == "Moon")
    print(f"Moon Sidereal Longitude: {moon_lon:.6f}")

    engine = DashaEngine()
    dasha_res = engine.calculate_dasha_hierarchy(
        moon_longitude=moon_lon,
        birth_datetime_utc=birth_dt,
        target_datetime_utc=datetime.datetime(2026, 8, 15, 12, 0, tzinfo=datetime.timezone.utc)
    )

    print("\n--- Current Engine Output (Vineet) ---")
    for md in dasha_res.mahadashas:
        print(f"{md.lord:8}: {md.start_date_utc[:19]} -> {md.end_date_utc[:19]}")

if __name__ == "__main__":
    run_audit()
