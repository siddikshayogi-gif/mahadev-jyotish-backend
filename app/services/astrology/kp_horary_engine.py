"""KP Horary (Prashna 1-249) Engine.

Executes exact 249 Sub-Lord boundary calculation, Horary Lagna calculation,
and 4-level significator evaluation for Prashna/Horary questions.
"""

import datetime
from typing import List, Dict, Tuple, Set, Any, Optional
from pydantic import BaseModel, Field

from app.services.astrology.astrology_constants import (
    RASHI_NAMES,
    RASHI_LORDS,
    NAKSHATRA_NAMES,
    VIMSHOTTARI_LORDS,
    VIMSHOTTARI_YEARS,
    NAKSHATRA_ARC,
    get_rashi_info,
    get_nakshatra_info
)
from app.services.astrology.kp_engine import get_kp_sub_and_ssl, KPEngine
from app.schemas.canonical_astrology import CanonicalAstrologyResult

class KPHoraryDivision(BaseModel):
    number: int
    rashi: int
    rashi_name: str
    star_lord: str
    sub_lord: str
    start_longitude: float
    end_longitude: float

def build_249_sub_lord_table() -> List[KPHoraryDivision]:
    """Builds exact 249 KP Sub-Lord boundary table from 0° Aries to 360° Pisces."""
    table: List[KPHoraryDivision] = []
    num = 1

    current_lon = 0.0
    for nak_idx in range(27):
        star_lord = VIMSHOTTARI_LORDS[nak_idx % 9]
        star_lord_idx = VIMSHOTTARI_LORDS.index(star_lord)

        for i in range(9):
            sub_lord = VIMSHOTTARI_LORDS[(star_lord_idx + i) % 9]
            sub_years = VIMSHOTTARI_YEARS[sub_lord]
            sub_arc_deg = (sub_years / 120.0) * NAKSHATRA_ARC

            sub_end = current_lon + sub_arc_deg

            # Check if sub_end crosses a Rashi boundary (30°, 60°, 90°, etc.)
            next_rashi_boundary = (int(current_lon // 30.0) + 1) * 30.0

            if (next_rashi_boundary - current_lon > 1e-6) and (sub_end - next_rashi_boundary > 1e-6) and next_rashi_boundary < 360.0:
                # Split boundary 1: current_lon to next_rashi_boundary
                r_idx, r_name, _, _ = get_rashi_info(current_lon + 0.00001)
                table.append(KPHoraryDivision(
                    number=num,
                    rashi=r_idx,
                    rashi_name=r_name,
                    star_lord=star_lord,
                    sub_lord=sub_lord,
                    start_longitude=round(current_lon, 6),
                    end_longitude=round(next_rashi_boundary, 6)
                ))
                num += 1
                current_lon = next_rashi_boundary

                # Split boundary 2: next_rashi_boundary to sub_end
                r_idx2, r_name2, _, _ = get_rashi_info(current_lon + 0.00001)
                table.append(KPHoraryDivision(
                    number=num,
                    rashi=r_idx2,
                    rashi_name=r_name2,
                    star_lord=star_lord,
                    sub_lord=sub_lord,
                    start_longitude=round(current_lon, 6),
                    end_longitude=round(sub_end, 6)
                ))
                num += 1
                current_lon = sub_end
            else:
                r_idx, r_name, _, _ = get_rashi_info(current_lon + 0.00001)
                table.append(KPHoraryDivision(
                    number=num,
                    rashi=r_idx,
                    rashi_name=r_name,
                    star_lord=star_lord,
                    sub_lord=sub_lord,
                    start_longitude=round(current_lon, 6),
                    end_longitude=round(sub_end, 6)
                ))
                num += 1
                current_lon = sub_end

    return table

KP_249_TABLE = build_249_sub_lord_table()

class HoraryCategoryConfig(BaseModel):
    category: str
    primary_houses: List[int]
    supporting_houses: List[int]
    obstruction_houses: List[int]

HORARY_CATEGORIES: Dict[str, HoraryCategoryConfig] = {
    "MARRIAGE": HoraryCategoryConfig(category="MARRIAGE", primary_houses=[7], supporting_houses=[2, 11], obstruction_houses=[1, 6, 10]),
    "CAREER": HoraryCategoryConfig(category="CAREER", primary_houses=[10], supporting_houses=[2, 6, 11], obstruction_houses=[1, 5, 9]),
    "MONEY": HoraryCategoryConfig(category="MONEY", primary_houses=[2, 11], supporting_houses=[6], obstruction_houses=[5, 8, 12]),
    "HEALTH": HoraryCategoryConfig(category="HEALTH", primary_houses=[1, 5, 11], supporting_houses=[], obstruction_houses=[6, 8, 12]),
    "PROPERTY": HoraryCategoryConfig(category="PROPERTY", primary_houses=[4, 11], supporting_houses=[2], obstruction_houses=[6, 8, 12]),
    "TRAVEL": HoraryCategoryConfig(category="TRAVEL", primary_houses=[3, 9, 12], supporting_houses=[7], obstruction_houses=[4]),
    "LEGAL": HoraryCategoryConfig(category="LEGAL", primary_houses=[6, 11], supporting_houses=[10], obstruction_houses=[8, 12]),
    "GENERAL": HoraryCategoryConfig(category="GENERAL", primary_houses=[1, 11], supporting_houses=[2, 10], obstruction_houses=[6, 8, 12])
}

class KPHoraryResult(BaseModel):
    horary_number: int
    horary_lagna_longitude: float
    horary_lagna_rashi: str
    horary_lagna_sign_lord: str
    horary_lagna_star_lord: str
    horary_lagna_sub_lord: str
    category: str
    verdict: str  # "YES", "NO", "MIXED_DELAY"
    confidence_score: float  # 0 to 100
    primary_houses: List[int]
    supporting_houses: List[int]
    obstruction_houses: List[int]
    favorable_planets: List[str]
    unfavorable_planets: List[str]
    ruling_planets: List[str]
    summary_hindi: str
    summary_english: str

class KPHoraryEngine:
    """KP Horary (Prashna 1-249) Evaluation Engine."""

    def __init__(self):
        self.table = KP_249_TABLE
        self.kp_engine = KPEngine()

    def get_division(self, horary_number: int) -> KPHoraryDivision:
        num = max(1, min(249, horary_number))
        return self.table[num - 1]

    def evaluate_horary(
        self,
        horary_number: int,
        canonical_natal: CanonicalAstrologyResult,
        category: str = "GENERAL"
    ) -> KPHoraryResult:
        div = self.get_division(horary_number)
        cat_cfg = HORARY_CATEGORIES.get(category.upper(), HORARY_CATEGORIES["GENERAL"])

        # Horary Lagna Longitude is the midpoint of the 249 sub division
        horary_lagna_lon = (div.start_longitude + div.end_longitude) / 2.0

        # Calculate Horary Chart using KP Engine over canonical planets
        kp_res = self.kp_engine.calculate_kp(canonical_natal)

        fav_houses = set(cat_cfg.primary_houses + cat_cfg.supporting_houses)
        obs_houses = set(cat_cfg.obstruction_houses)

        fav_planets = []
        unfav_planets = []

        for psf in kp_res.planet_significators:
            signified = set(psf.all_signified_houses)
            has_fav = len(signified.intersection(fav_houses)) > 0
            has_obs = len(signified.intersection(obs_houses)) > 0

            if has_fav and not has_obs:
                fav_planets.append(psf.planet)
            elif has_obs and not has_fav:
                unfav_planets.append(psf.planet)

        # Score computation
        score = 50.0
        score += len(fav_planets) * 12.0
        score -= len(unfav_planets) * 10.0

        # Check Lagna Sub-Lord alignment
        sub_lord = div.sub_lord
        sub_signified = set()
        for psf in kp_res.planet_significators:
            if psf.planet == sub_lord:
                sub_signified = set(psf.all_signified_houses)
                break

        if len(sub_signified.intersection(fav_houses)) > 0:
            score += 15.0
        if len(sub_signified.intersection(obs_houses)) > 0:
            score -= 15.0

        score = max(5.0, min(95.0, round(score, 1)))

        if score >= 65.0:
            verdict = "YES"
            summary_hi = f"प्रश्न संख्या {horary_number} ({div.sub_lord} उप-स्वामी) के अनुसार {cat_cfg.category} के लिए सकारात्मक संकेत हैं।"
            summary_en = f"Horary No. {horary_number} (Sub-Lord: {div.sub_lord}) indicates positive outcome for {cat_cfg.category}."
        elif score <= 40.0:
            verdict = "NO"
            summary_hi = f"प्रश्न संख्या {horary_number} के अनुसार {cat_cfg.category} के लिए अनुकूलता कम दिखाई देती है।"
            summary_en = f"Horary No. {horary_number} indicates unfavorable conditions for {cat_cfg.category}."
        else:
            verdict = "MIXED_DELAY"
            summary_hi = f"प्रश्न संख्या {horary_number} के अनुसार {cat_cfg.category} में विलंब या मिला-जुला परिणाम संभव है।"
            summary_en = f"Horary No. {horary_number} indicates mixed results with possible delay for {cat_cfg.category}."

        return KPHoraryResult(
            horary_number=horary_number,
            horary_lagna_longitude=round(horary_lagna_lon, 4),
            horary_lagna_rashi=div.rashi_name,
            horary_lagna_sign_lord=RASHI_LORDS[div.rashi],
            horary_lagna_star_lord=div.star_lord,
            horary_lagna_sub_lord=div.sub_lord,
            category=cat_cfg.category,
            verdict=verdict,
            confidence_score=score,
            primary_houses=cat_cfg.primary_houses,
            supporting_houses=cat_cfg.supporting_houses,
            obstruction_houses=cat_cfg.obstruction_houses,
            favorable_planets=fav_planets,
            unfavorable_planets=unfav_planets,
            ruling_planets=kp_res.ruling_planets.ruling_planets_list,
            summary_hindi=summary_hi,
            summary_english=summary_en
        )
