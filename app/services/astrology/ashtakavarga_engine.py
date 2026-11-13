"""Parashari Ashtakavarga Engine.

Computes the seven planetary Bhinnashtakavargas (BAV) and Sarvashtakavarga (SAV).
Rahu/Ketu are intentionally excluded from the classical seven-planet SAV total.
"""

from typing import Dict, List
from app.schemas.vedic_astrology import (
    AshtakavargaPlanetFact,
    AshtakavargaResult,
    VedicPlanetFact,
)

ASHTAKAVARGA_PLANETS = [
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"
]

# Format:
# BINDU_TABLES[target_planet][reference_point] =
# houses counted from reference point which contribute one bindu.
BINDU_TABLES = {
    "Sun": {
        "Sun": [1, 2, 4, 7, 8, 9, 10, 11],
        "Moon": [3, 6, 10, 11],
        "Mars": [1, 2, 4, 7, 8, 9, 10, 11],
        "Mercury": [3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [5, 6, 9, 11],
        "Venus": [6, 7, 12],
        "Saturn": [1, 2, 4, 7, 8, 9, 10, 11],
        "Lagna": [3, 4, 6, 10, 11, 12],
    },
    "Moon": {
        "Sun": [3, 6, 7, 8, 10, 11],
        "Moon": [1, 3, 6, 7, 10, 11],
        "Mars": [2, 3, 5, 6, 9, 10, 11],
        "Mercury": [1, 3, 4, 5, 7, 8, 10, 11],
        "Jupiter": [1, 4, 7, 8, 10, 11, 12],
        "Venus": [3, 4, 5, 7, 9, 10, 11],
        "Saturn": [3, 5, 6, 11],
        "Lagna": [3, 6, 10, 11],
    },
    "Mars": {
        "Sun": [3, 5, 6, 10, 11],
        "Moon": [3, 6, 11],
        "Mars": [1, 2, 4, 7, 8, 10, 11],
        "Mercury": [3, 5, 6, 11],
        "Jupiter": [6, 10, 11, 12],
        "Venus": [6, 8, 11, 12],
        "Saturn": [1, 4, 7, 8, 9, 10, 11],
        "Lagna": [1, 3, 6, 10, 11],
    },
    "Mercury": {
        "Sun": [5, 6, 9, 11, 12],
        "Moon": [2, 4, 6, 8, 10, 11],
        "Mars": [1, 2, 4, 7, 8, 9, 10, 11],
        "Mercury": [1, 3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [6, 8, 11, 12],
        "Venus": [1, 2, 3, 4, 5, 8, 9, 11],
        "Saturn": [1, 2, 4, 7, 8, 9, 10, 11],
        "Lagna": [1, 2, 4, 6, 8, 10, 11],
    },
    "Jupiter": {
        "Sun": [1, 2, 3, 4, 7, 8, 9, 10, 11],
        "Moon": [2, 5, 7, 9, 11],
        "Mars": [1, 2, 4, 7, 8, 10, 11],
        "Mercury": [1, 2, 4, 5, 6, 9, 10, 11],
        "Jupiter": [1, 2, 3, 4, 7, 8, 10, 11],
        "Venus": [2, 5, 6, 9, 10, 11],
        "Saturn": [3, 5, 6, 12],
        "Lagna": [1, 2, 4, 5, 6, 7, 9, 10, 11],
    },
    "Venus": {
        "Sun": [8, 11, 12],
        "Moon": [1, 2, 3, 4, 5, 8, 9, 11, 12],
        "Mars": [3, 4, 6, 8, 9, 11, 12],
        "Mercury": [3, 5, 6, 9, 11],
        "Jupiter": [5, 8, 9, 10, 11],
        "Venus": [1, 2, 3, 4, 5, 8, 9, 10, 11],
        "Saturn": [3, 4, 5, 8, 9, 10, 11],
        "Lagna": [1, 2, 3, 4, 5, 8, 9],
    },
    "Saturn": {
        "Sun": [1, 2, 4, 7, 8, 10, 11],
        "Moon": [3, 6, 11],
        "Mars": [3, 5, 6, 10, 11, 12],
        "Mercury": [6, 8, 9, 10, 11, 12],
        "Jupiter": [5, 6, 11, 12],
        "Venus": [6, 11, 12],
        "Saturn": [3, 5, 6, 11],
        "Lagna": [1, 3, 4, 6, 10, 11],
    },
}


def _distance_house(reference_rashi: int, target_rashi: int) -> int:
    """1-indexed house distance from reference sign to target sign."""
    return ((target_rashi - reference_rashi) % 12) + 1


class AshtakavargaEngine:
    """Deterministic BAV/SAV calculator."""

    def calculate(
        self,
        planets: List[VedicPlanetFact],
        lagna_rashi: int,
    ) -> AshtakavargaResult:
        rashi_by_planet: Dict[str, int] = {
            p.body: p.rashi
            for p in planets
            if p.body in ASHTAKAVARGA_PLANETS
        }

        missing = [p for p in ASHTAKAVARGA_PLANETS if p not in rashi_by_planet]
        if missing:
            raise ValueError(f"Ashtakavarga missing classical planets: {missing}")

        references = dict(rashi_by_planet)
        references["Lagna"] = lagna_rashi

        bav_results: List[AshtakavargaPlanetFact] = []
        sav = [0] * 12

        for target in ASHTAKAVARGA_PLANETS:
            sign_scores = [0] * 12
            target_table = BINDU_TABLES[target]

            for sign in range(12):
                score = 0
                for reference_name, reference_rashi in references.items():
                    house_from_reference = _distance_house(reference_rashi, sign)
                    if house_from_reference in target_table[reference_name]:
                        score += 1
                sign_scores[sign] = score
                sav[sign] += score

            bav_results.append(
                AshtakavargaPlanetFact(
                    planet=target,
                    bindus_by_sign=sign_scores,
                    total_bindus=sum(sign_scores),
                )
            )

        # Convert sign-wise SAV to D1 house-wise SAV.
        sav_by_house = {
            str(h): sav[(lagna_rashi + h - 1) % 12]
            for h in range(1, 13)
        }

        ranked = sorted(
            range(1, 13),
            key=lambda h: sav_by_house[str(h)],
            reverse=True,
        )
        strongest = ranked[:3]
        weakest = list(reversed(ranked[-3:]))

        return AshtakavargaResult(
            bhinnashtakavarga=bav_results,
            sarvashtakavarga_by_sign=sav,
            sarvashtakavarga_total=sum(sav),
            sarvashtakavarga_by_house=sav_by_house,
            strongest_houses=strongest,
            weakest_houses=weakest,
        )
