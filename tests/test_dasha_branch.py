import os
import sys
import datetime
import json

# Add backend to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tests.mock_swisseph
from app.services.astrology.dasha_engine import DashaEngine

def test_branch():
    birth_dt = datetime.datetime(1998, 2, 5, 6, 0, tzinfo=datetime.timezone.utc)
    moon_lon = 38.923088

    target_dt = datetime.datetime(2026, 8, 15, 6, 30, tzinfo=datetime.timezone.utc)

    engine = DashaEngine()
    res = engine.calculate_dasha_hierarchy(
        moon_longitude=moon_lon,
        birth_datetime_utc=birth_dt,
        target_datetime_utc=target_dt,
        max_depth=5
    )

    print(f"Target Date: {target_dt.isoformat()}")
    print("\n--- Active Chain ---")
    for d in res.active_chain:
        print(f"{d.level_name:15}: {d.lord:8} | {d.start_date_utc[:19]} to {d.end_date_utc[:19]}")

    # Now explore Rahu -> Ketu -> Rahu -> Venus
    print("\n--- Explorer Simulation ---")
    # 1. Rahu MD
    rahu_md = next(m for m in res.mahadashas if m.lord == "Rahu")
    print(f"Rahu MD: {rahu_md.start_date_utc[:10]} to {rahu_md.end_date_utc[:10]}")

    # 2. Sub-periods of Rahu (ADs)
    ads = engine.get_sub_periods("Rahu", rahu_md.start_date_utc, rahu_md.end_date_utc, 1, target_dt.isoformat())
    ketu_ad = next(a for a in ads if a.lord == "Ketu")
    print(f"  Ketu AD: {ketu_ad.start_date_utc[:10]} to {ketu_ad.end_date_utc[:10]}")

    # 3. Sub-periods of Ketu (PDs)
    pds = engine.get_sub_periods("Ketu", ketu_ad.start_date_utc, ketu_ad.end_date_utc, 2, target_dt.isoformat())
    rahu_pd = next(p for p in pds if p.lord == "Rahu")
    print(f"    Rahu PD: {rahu_pd.start_date_utc[:10]} to {rahu_pd.end_date_utc[:10]}")

    # 4. Sub-periods of Rahu PD (SDs)
    sds = engine.get_sub_periods("Rahu", rahu_pd.start_date_utc, rahu_pd.end_date_utc, 3, target_dt.isoformat())
    venus_sd = next(s for s in sds if s.lord == "Venus")
    print(f"      Venus SD: {venus_sd.start_date_utc[:10]} to {venus_sd.end_date_utc[:10]}")

    # 5. Sub-periods of Venus SD (Pranas)
    pranas = engine.get_sub_periods("Venus", venus_sd.start_date_utc, venus_sd.end_date_utc, 4, target_dt.isoformat())
    for p in pranas:
        curr_mark = "*" if p.status == "CURRENT" else " "
        print(f"        {curr_mark} {p.lord:8}: {p.start_date_utc[:19]} to {p.end_date_utc[:19]}")

if __name__ == "__main__":
    test_branch()
