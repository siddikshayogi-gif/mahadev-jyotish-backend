"""Numerology & KP Synergy Engine.

Computes Chaldean & Pythagorean Moolank, Bhagyank, and Namank from DOB and Name.
Evaluates planetary friendship between Numerology Rulers and Active Dasha Lords.
Computes 0-100 Daily Energy Score.
"""

import re
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

from app.schemas.canonical_astrology import CanonicalAstrologyResult
from app.services.astrology.dasha_engine import DashaEngine
from app.services.astrology.vedic_engine import NATURAL_FRIENDS, NATURAL_ENEMIES

# Chaldean Letter Mapping (1 to 8)
CHALDEAN_MAP = {
    'A': 1, 'I': 1, 'J': 1, 'Q': 1, 'Y': 1,
    'B': 2, 'K': 2, 'R': 2,
    'C': 3, 'G': 3, 'L': 3, 'S': 3,
    'D': 4, 'M': 4, 'T': 4,
    'E': 5, 'H': 5, 'N': 5, 'X': 5,
    'U': 6, 'V': 6, 'W': 6,
    'O': 7, 'Z': 7,
    'F': 8, 'P': 8
}

# Pythagorean Letter Mapping (1 to 9)
PYTHAGOREAN_MAP = {
    'A': 1, 'J': 1, 'S': 1,
    'B': 2, 'K': 2, 'T': 2,
    'C': 3, 'L': 3, 'U': 3,
    'D': 4, 'M': 4, 'V': 4,
    'E': 5, 'N': 5, 'W': 5,
    'F': 6, 'O': 6, 'X': 6,
    'G': 7, 'P': 7, 'Y': 7,
    'H': 8, 'Q': 8, 'Z': 8,
    'I': 9, 'R': 9
}

NUMEROLOGY_PLANET_RULERS = {
    1: "Sun",
    2: "Moon",
    3: "Jupiter",
    4: "Rahu",
    5: "Mercury",
    6: "Venus",
    7: "Ketu",
    8: "Saturn",
    9: "Mars"
}

def single_digit_reduce(num: int) -> int:
    """Reduces an integer to single digit 1..9."""
    while num > 9:
        num = sum(int(d) for d in str(num))
    return num

def calculate_moolank(date_of_birth_str: str) -> int:
    """Moolank (Birth Number): Single digit reduction of day of birth."""
    try:
        # Expected "YYYY-MM-DD"
        day = int(date_of_birth_str.split("-")[2])
        return single_digit_reduce(day)
    except Exception:
        return 1

def calculate_bhagyank(date_of_birth_str: str) -> int:
    """Bhagyank (Destiny Number): Single digit reduction of entire DOB (YYYYMMDD)."""
    try:
        digits_sum = sum(int(d) for d in date_of_birth_str if d.isdigit())
        return single_digit_reduce(digits_sum)
    except Exception:
        return 1

def calculate_namank(name_str: str, system: str = "CHALDEAN") -> int:
    """Namank (Name Number): Single digit reduction using Chaldean or Pythagorean system."""
    clean_name = re.sub(r'[^A-Z]', '', name_str.upper())
    if not clean_name:
        return 1
    mapping = CHALDEAN_MAP if system == "CHALDEAN" else PYTHAGOREAN_MAP
    total = sum(mapping.get(char, 0) for char in clean_name)
    return single_digit_reduce(total)

class NumerologySynergyResult(BaseModel):
    name: str
    date_of_birth: str
    moolank: int
    moolank_ruler: str
    bhagyank: int
    bhagyank_ruler: str
    namank_chaldean: int
    namank_pythagorean: int
    active_dasha_lord: str
    moolank_dasha_friendship: str  # "FRIEND", "NEUTRAL", "ENEMY"
    bhagyank_dasha_friendship: str
    daily_energy_score: float  # 0 to 100
    summary_hindi: str
    summary_english: str

class NumerologySynergyEngine:
    def __init__(self):
        self.dasha_engine = DashaEngine()

    def evaluate_synergy(
        self,
        canonical_natal: CanonicalAstrologyResult,
        target_datetime_utc: Optional[datetime] = None,
        name: Optional[str] = None
    ) -> NumerologySynergyResult:
        if target_datetime_utc is None:
            target_datetime_utc = datetime.now(timezone.utc)
        if target_datetime_utc.tzinfo is None:
            target_datetime_utc = target_datetime_utc.replace(tzinfo=timezone.utc)

        dob_str = canonical_natal.birth.local_date
        name_str = name or "User"

        moolank = calculate_moolank(dob_str)
        bhagyank = calculate_bhagyank(dob_str)
        namank_c = calculate_namank(name_str, "CHALDEAN")
        namank_p = calculate_namank(name_str, "PYTHAGOREAN")

        m_ruler = NUMEROLOGY_PLANET_RULERS[moolank]
        b_ruler = NUMEROLOGY_PLANET_RULERS[bhagyank]

        # Active Dasha Lord
        moon_p = next(p for p in canonical_natal.planets if p.body == "Moon")
        birth_utc = datetime.fromisoformat(canonical_natal.birth.utc_instant.replace("Z", "+00:00"))
        if birth_utc.tzinfo is None: birth_utc = birth_utc.replace(tzinfo=timezone.utc)

        dasha = self.dasha_engine.calculate_dasha_hierarchy(
            moon_longitude=moon_p.sidereal_longitude,
            birth_datetime_utc=birth_utc,
            target_datetime_utc=target_datetime_utc,
            max_depth=3
        )
        dasha_lord = dasha.active_chain[0].lord if dasha.active_chain else "Sun"

        # Evaluate Friendship with Moolank & Bhagyank Rulers
        def get_friendship(ruler: str, planet: str) -> str:
            if ruler == planet:
                return "FRIEND"
            if planet in NATURAL_FRIENDS.get(ruler, []):
                return "FRIEND"
            if planet in NATURAL_ENEMIES.get(ruler, []):
                return "ENEMY"
            return "NEUTRAL"

        m_friendship = get_friendship(m_ruler, dasha_lord)
        b_friendship = get_friendship(b_ruler, dasha_lord)

        # Base Energy Score (0-100)
        score = 50.0

        # Moolank Bonus/Penalty
        if m_friendship == "FRIEND": score += 25.0
        elif m_friendship == "NEUTRAL": score += 12.0
        else: score -= 15.0

        # Bhagyank Bonus/Penalty
        if b_friendship == "FRIEND": score += 15.0
        elif b_friendship == "NEUTRAL": score += 8.0
        else: score -= 10.0

        score = max(10.0, min(98.0, round(score, 1)))

        sum_hi = f"मूलांक {moolank} ({m_ruler}) व भाग्यांक {bhagyank} ({b_ruler}) की सक्रिय दशा स्वामी {dasha_lord} के साथ ऊर्जा अनुकूलता: {score}%।"
        sum_en = f"Moolank {moolank} ({m_ruler}) & Bhagyank {bhagyank} ({b_ruler}) energy synergy with Dasha lord {dasha_lord}: {score}%."

        return NumerologySynergyResult(
            name=name_str,
            date_of_birth=dob_str,
            moolank=moolank,
            moolank_ruler=m_ruler,
            bhagyank=bhagyank,
            bhagyank_ruler=b_ruler,
            namank_chaldean=namank_c,
            namank_pythagorean=namank_p,
            active_dasha_lord=dasha_lord,
            moolank_dasha_friendship=m_friendship,
            bhagyank_dasha_friendship=b_friendship,
            daily_energy_score=score,
            summary_hindi=sum_hi,
            summary_english=sum_en
        )
