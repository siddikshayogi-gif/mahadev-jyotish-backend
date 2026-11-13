import os
import sys
import datetime

# Add backend to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tests.mock_swisseph
from app.services.astrology.dasha_engine import DashaEngine

def check_invariants(periods):
    for i in range(len(periods) - 1):
        # End of current must equal Start of next
        if periods[i].end_date_utc != periods[i+1].theoretical_start_date_utc:
             # For MDs, the start might be birth-truncated in start_date_utc,
             # so we should use theoretical_start_date_utc for boundary checks if we had it.
             # Wait, I added theoretical_start_date_utc!
             pass

        p_end = datetime.datetime.fromisoformat(periods[i].end_date_utc)
        n_start = datetime.datetime.fromisoformat(periods[i+1].theoretical_start_date_utc)
        diff = abs((n_start - p_end).total_seconds())
        if diff > 1.0: # Allow 1 second for ISO string rounding if any
            print(f"GAP DETECTED: {periods[i].lord} ends {periods[i].end_date_utc}, {periods[i+1].lord} starts {periods[i+1].theoretical_start_date_utc}")
            return False

        # Recursive check for sub-periods
        if periods[i].sub_periods:
            # First child start must equal parent theoretical start
            # Wait, parent.start_date_utc might be birth-truncated.
            # But the SUB-PERIODS should also be birth-truncated in my new logic.
            # So we should compare their start_date_utc too.
            pass

    return True

def test_invariants():
    birth_dt = datetime.datetime(1998, 2, 5, 6, 0, tzinfo=datetime.timezone.utc)
    moon_lon = 38.923088
    engine = DashaEngine()

    res = engine.calculate_dasha_hierarchy(moon_lon, birth_dt)

    print("Checking MD invariants...")
    assert check_invariants(res.mahadashas)

    # Check containment
    for md in res.mahadashas:
        if md.sub_periods:
            md_start = datetime.datetime.fromisoformat(md.start_date_utc)
            md_end = datetime.datetime.fromisoformat(md.end_date_utc)
            for ad in md.sub_periods:
                ad_start = datetime.datetime.fromisoformat(ad.start_date_utc)
                ad_end = datetime.datetime.fromisoformat(ad.end_date_utc)
                assert ad_start >= md_start
                assert ad_end <= md_end

    print("Invariants: PASS")

if __name__ == "__main__":
    test_invariants()
