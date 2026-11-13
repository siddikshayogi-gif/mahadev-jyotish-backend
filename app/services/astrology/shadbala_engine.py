"""Phase-1 deterministic Shadbala support engine.

IMPORTANT:
Classical Shadbala is a large astronomical system with many sub-components.
This module deliberately does NOT pretend to be the final BPHS/Sripati implementation.

It produces a deterministic six-component normalized SUPPORT score from data already
available in the Mahadev Jyotish engine. The result is explicitly marked
PHASE1_NORMALIZED_SUPPORT and must not be displayed as classical Rupas.

A later dedicated Shadbala phase can replace this implementation without changing
the public schema or EvidenceRetriever integration.
"""

from typing import Dict, List
from app.schemas.vedic_astrology import (
    Dignity,
    ShadbalaComponentFact,
    ShadbalaPlanetFact,
    ShadbalaResult,
    VedicPlanetFact,
)

CLASSICAL_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

NAISARGIKA = {
    "Sun": 60.00,
    "Moon": 51.43,
    "Venus": 42.85,
    "Jupiter": 34.28,
    "Mercury": 25.71,
    "Mars": 17.14,
    "Saturn": 8.57,
}

DIGNITY_STHANA = {
    Dignity.EXALTED: 60.0,
    Dignity.MOOLATRIKONA: 54.0,
    Dignity.OWN_SIGN: 48.0,
    Dignity.FRIENDLY: 39.0,
    Dignity.NEUTRAL: 30.0,
    Dignity.ENEMY: 21.0,
    Dignity.DEBILITATED: 6.0,
}

# Planet -> house of maximum directional strength.
DIG_STRONG_HOUSE = {
    "Sun": 10,
    "Mars": 10,
    "Moon": 4,
    "Venus": 4,
    "Mercury": 1,
    "Jupiter": 1,
    "Saturn": 7,
}


def _circular_house_distance(a: int, b: int) -> int:
    d = abs(a - b) % 12
    return min(d, 12 - d)


def _dig_bala(planet: str, house: int) -> float:
    strong = DIG_STRONG_HOUSE[planet]
    weak = ((strong + 5) % 12) + 1
    distance_from_weak = _circular_house_distance(house, weak)
    # 0 at weak direction, 60 at opposite/strong direction.
    return max(0.0, min(60.0, distance_from_weak * 10.0))


def _cheshta_bala(p: VedicPlanetFact) -> float:
    # Deterministic support proxy from actual Swiss-Ephemeris speed/retrograde flag.
    if p.retrograde:
        return 60.0
    speed = abs(float(p.speed))
    # Smoothly map speed to 0..45; this is NOT classical Cheshta sub-formula.
    return max(0.0, min(45.0, speed * 12.0))


def _kala_bala(p: VedicPlanetFact) -> float:
    # Phase-1 stable support signal only. Full Kala Bala requires temporal
    # sub-components (Nathonnatha, Paksha, Tribhaga, Vara/Hora, Ayana, etc.).
    # Keep neutral instead of fabricating missing astronomical quantities.
    return 30.0


def _drik_bala(p: VedicPlanetFact, planets: List[VedicPlanetFact]) -> float:
    # Phase-1 sign-based aspect support proxy. Positive/negative impact is kept
    # intentionally modest so it cannot dominate a prediction.
    benefics = {"Jupiter", "Venus", "Mercury", "Moon"}
    malefics = {"Saturn", "Mars", "Sun"}

    score = 0.0
    for other in planets:
        if other.body == p.body or other.body in {"Rahu", "Ketu"}:
            continue
        delta = (other.rashi - p.rashi) % 12
        # Opposition and conjunction are the strongest broad sign relations.
        if delta in (0, 6):
            weight = 6.0
        elif delta in (4, 8):
            weight = 3.0
        else:
            continue

        if other.body in benefics:
            score += weight
        elif other.body in malefics:
            score -= weight

    return max(-30.0, min(30.0, score))


class ShadbalaEngine:
    """Phase-1 normalized six-component supporting-strength calculator."""

    def calculate(self, planets: List[VedicPlanetFact]) -> ShadbalaResult:
        classical = [p for p in planets if p.body in CLASSICAL_PLANETS]
        facts: List[ShadbalaPlanetFact] = []

        for p in classical:
            sthana = DIGNITY_STHANA.get(p.dignity, 30.0)
            if p.vargottama:
                sthana = min(60.0, sthana + 6.0)

            dig = _dig_bala(p.body, p.house_d1)
            kala = _kala_bala(p)
            cheshta = _cheshta_bala(p)
            naisargika = NAISARGIKA[p.body]
            drik = _drik_bala(p, classical)

            components = ShadbalaComponentFact(
                sthana_bala=round(sthana, 2),
                dig_bala=round(dig, 2),
                kala_bala=round(kala, 2),
                cheshta_bala=round(cheshta, 2),
                naisargika_bala=round(naisargika, 2),
                drik_bala=round(drik, 2),
            )

            total = sthana + dig + kala + cheshta + naisargika + drik
            # Normalize against a conservative 300-virupa support ceiling.
            normalized = max(0.0, min(100.0, (total / 300.0) * 100.0))

            if normalized >= 75:
                label = "VERY_STRONG"
            elif normalized >= 62:
                label = "STRONG"
            elif normalized >= 45:
                label = "AVERAGE"
            elif normalized >= 30:
                label = "WEAK"
            else:
                label = "VERY_WEAK"

            facts.append(
                ShadbalaPlanetFact(
                    planet=p.body,
                    components=components,
                    total_virupa=round(total, 2),
                    total_rupa=round(total / 60.0, 3),
                    normalized_score=round(normalized, 2),
                    strength_label=label,
                )
            )

        return ShadbalaResult(planets=facts)
