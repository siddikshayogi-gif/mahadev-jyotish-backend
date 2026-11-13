"""Phase 3 Relationship Matching, Event Journal & Final Verification Tests."""
import asyncio
from app.services.astrology.ashtakoot_compatibility_engine import AshtakootCompatibilityEngine
from app.services.astrology.event_journal_engine import EventJournalEngine, EventJournalEntry
from app.api.v1.endpoints.calculations import calculate_natal, NatalCalculationRequest

async def test_ashtakoot_compatibility_engine():
    engine = AshtakootCompatibilityEngine()
    groom_req = NatalCalculationRequest(
        name="Jaipur Groom",
        date_of_birth="1995-05-15",
        time_of_birth="10:30:00",
        place_of_birth="Jaipur, India",
        latitude=26.9124,
        longitude=75.7873,
        timezone_id="Asia/Kolkata"
    )
    bride_req = NatalCalculationRequest(
        name="Jaipur Bride",
        date_of_birth="1998-02-05",
        time_of_birth="11:30:00",
        place_of_birth="Jaipur, India",
        latitude=26.9124,
        longitude=75.7873,
        timezone_id="Asia/Kolkata"
    )
    groom_canonical = await calculate_natal(groom_req)
    bride_canonical = await calculate_natal(bride_req)

    res = engine.evaluate_matching(
        groom_canonical=groom_canonical,
        bride_canonical=bride_canonical,
        groom_name="Jaipur Groom",
        bride_name="Jaipur Bride"
    )

    assert res.groom_name == "Jaipur Groom"
    assert res.bride_name == "Jaipur Bride"
    assert 0 <= res.total_score <= 36
    assert 0 <= res.score_percentage <= 100
    assert len(res.gun_details) == 8
    assert res.compatibility_verdict in ["EXCELLENT", "GOOD", "AVERAGE", "POOR"]
    print("36-Gun Ashtakoot Compatibility Engine Test PASSED")

def test_event_journal_engine():
    engine = EventJournalEngine()

    # 1. Add Entry
    entry = EventJournalEntry(
        entry_id="ej_test_101",
        profile_id="prof_jaipur_1",
        question="Meri naukri kab lagegi?",
        predicted_event_type="CAREER",
        predicted_verdict="ACTIVE",
        predicted_window_start="2026-01-01",
        predicted_window_end="2026-06-30"
    )
    engine.add_entry(entry)

    # 2. Record Feedback (Confirmed Yes)
    recorded = engine.record_feedback(
        entry_id="ej_test_101",
        actual_outcome="CONFIRMED_YES",
        actual_event_date="2026-03-15",
        feedback_notes="Got job offer on 15 March 2026."
    )
    assert recorded is not None
    assert recorded.actual_outcome == "CONFIRMED_YES"

    # 3. Calculate Accuracy Stats
    stats = engine.calculate_accuracy_stats(profile_id="prof_jaipur_1")
    assert stats.total_predictions_tracked == 1
    assert stats.confirmed_correct == 1
    assert stats.accuracy_percentage == 100.0
    print("Event Journal Ledger Test PASSED")

async def main():
    await test_ashtakoot_compatibility_engine()
    test_event_journal_engine()
    print("ALL PHASE 3 TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())
