"""Smart Muhurat Finder Engine.

Calculates optimal auspicious time windows for events over 7 to 30 days ahead based on:
1. Chandra Bala (Moon transit house from Natal Moon & Lagna).
2. Tara Bala (9-Tara cycle from Natal Moon Nakshatra).
3. Rahu Kaal & Gulika Kaal per weekday.
4. KP Moon Sub-Lord alignment.
Produces 0-100 Muhurat Score and selects top 6 Muhurat slots.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.services.astrology.astrology_constants import (
    RASHI_NAMES,
    NAKSHATRA_NAMES,
    get_rashi_info,
    get_nakshatra_info
)
from app.services.astrology.gochar_engine import GocharEngine
from app.services.astrology.kp_engine import get_kp_sub_and_ssl
from app.schemas.canonical_astrology import CanonicalAstrologyResult

TARA_NAMES = [
    "Janma (Danger)", "Sampat (Wealth)", "Vipat (Hurdles)", "Kshema (Security)",
    "Pratyak (Opposition)", "Sadhana (Success)", "Naidhana (Loss)", "Mitra (Good)", "Param Mitra (Excellent)"
]

TARA_SCORES = [ -15, 20, -20, 15, -15, 20, -25, 15, 20 ]

# Rahu Kaal 1/8th slot index (1 to 8) for Mon..Sun
RAHU_KAAL_SLOT = {
    0: 2, # Mon (07:30-09:00)
    1: 7, # Tue (15:00-16:30)
    2: 5, # Wed (12:00-13:30)
    3: 6, # Thu (13:30-15:00)
    4: 4, # Fri (10:30-12:00)
    5: 3, # Sat (09:00-10:30)
    6: 8, # Sun (16:30-18:00)
}

GULIKA_KAAL_SLOT = {
    0: 6, # Mon
    1: 5, # Tue
    2: 4, # Wed
    3: 3, # Thu
    4: 2, # Fri
    5: 1, # Sat
    6: 7  # Sun
}

class MuhuratSlot(BaseModel):
    date_display: str
    start_time_utc: str
    end_time_utc: str
    category: str
    score: float
    chandra_bala_house: int
    tara_bala_name: str
    is_rahu_kaal: bool
    is_gulika_kaal: bool
    kp_moon_sub_lord: str
    recommendation_hindi: str
    recommendation_english: str

class MuhuratFinderResult(BaseModel):
    category: str
    days_scanned: int
    total_slots_evaluated: int
    top_muhurats: List[MuhuratSlot]

class SmartMuhuratEngine:
    def __init__(self):
        self.gochar_engine = GocharEngine()

    def find_muhurats(
        self,
        canonical_natal: CanonicalAstrologyResult,
        category: str = "GENERAL",
        days_ahead: int = 30,
        start_date: Optional[datetime] = None
    ) -> MuhuratFinderResult:
        if start_date is None:
            start_date = datetime.now(timezone.utc)
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)

        # Natal Moon info
        moon_p = next(p for p in canonical_natal.planets if p.body == "Moon")
        natal_moon_rashi = moon_p.rashi
        natal_moon_nak = moon_p.nakshatra

        slots_evaluated = 0
        all_slots: List[MuhuratSlot] = []

        # Scan each day, evaluating 4 daytime slots per day
        for day_offset in range(days_ahead):
            curr_day = start_date + timedelta(days=day_offset)
            weekday = curr_day.weekday() # 0..6

            # 4 daytime slots: 08:00, 11:00, 14:00, 16:30 UTC/local
            slot_hours = [8, 11, 14, 16]
            for h in slot_hours:
                slots_evaluated += 1
                slot_start = curr_day.replace(hour=h, minute=0, second=0, microsecond=0)
                slot_end = slot_start + timedelta(hours=2)

                # Determine 1/8th daylight slot (1 to 8)
                # Daylight assumed 06:00 to 18:00 (12h = 720m, 1.5h per slot)
                slot_idx = min(8, max(1, int((h - 6) // 1.5) + 1))

                is_rahu = (slot_idx == RAHU_KAAL_SLOT[weekday])
                is_gulika = (slot_idx == GULIKA_KAAL_SLOT[weekday])

                # Evaluate Gochar transits for this slot
                gochar = self.gochar_engine.calculate_gochar_snapshot(canonical_natal, slot_start)
                t_moon = next(t for t in gochar.transits if t.body == "Moon")

                # 1. Chandra Bala
                c_house = t_moon.house_from_moon
                c_score = 0
                if c_house in [1, 3, 6, 7, 10, 11]: c_score = 25
                elif c_house in [2, 5, 9]: c_score = 10
                else: c_score = -20

                # 2. Tara Bala
                tara_idx = (t_moon.nakshatra - natal_moon_nak) % 9
                tara_name = TARA_NAMES[tara_idx]
                t_score = TARA_SCORES[tara_idx]

                # 3. Rahu/Gulika Penalty
                r_penalty = -30 if is_rahu else 0
                g_penalty = -20 if is_gulika else 0

                # 4. KP Moon Sub Lord
                _, sub_lord = get_kp_sub_and_ssl(t_moon.sidereal_longitude)
                kp_bonus = 15 if sub_lord in ["Jupiter", "Venus", "Mercury", "Moon"] else 5

                # Total Score calculation
                base_score = 50.0 + c_score + t_score + r_penalty + g_penalty + kp_bonus
                final_score = max(5.0, min(98.0, round(base_score, 1)))

                date_disp = slot_start.strftime("%Y-%m-%d")

                if final_score >= 60.0 and not is_rahu:
                    rec_hi = f"{date_disp} ({slot_start.strftime('%H:%M')} UTC) - चंद्र बल ({c_house} भाव), तारा: {tara_name}। शुभ मुहूर्त स्कोर: {final_score}।"
                    rec_en = f"{date_disp} ({slot_start.strftime('%H:%M')} UTC) - Chandra Bala (H-{c_house}), Tara: {tara_name}. Score: {final_score}."

                    all_slots.append(MuhuratSlot(
                        date_display=date_disp,
                        start_time_utc=slot_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        end_time_utc=slot_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        category=category,
                        score=final_score,
                        chandra_bala_house=c_house,
                        tara_bala_name=tara_name,
                        is_rahu_kaal=is_rahu,
                        is_gulika_kaal=is_gulika,
                        kp_moon_sub_lord=sub_lord,
                        recommendation_hindi=rec_hi,
                        recommendation_english=rec_en
                    ))

        # Sort slots by score descending and take top 6
        all_slots.sort(key=lambda x: x.score, reverse=True)
        top_6 = all_slots[:6]

        return MuhuratFinderResult(
            category=category,
            days_scanned=days_ahead,
            total_slots_evaluated=slots_evaluated,
            top_muhurats=top_6
        )
