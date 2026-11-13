"""Vedic Astrology Schema Data Models.

Canonical deterministic Vedic chart fact model for downstream Dasha, Yoga, Gochar,
Prediction, RAG, and UI rendering.
"""
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class Dignity(str, Enum):
    EXALTED = "EXALTED"
    DEBILITATED = "DEBILITATED"
    MOOLATRIKONA = "MOOLATRIKONA"
    OWN_SIGN = "OWN_SIGN"
    FRIENDLY = "FRIENDLY"
    NEUTRAL = "NEUTRAL"
    ENEMY = "ENEMY"


class VedicPlanetFact(BaseModel):
    body: str
    sidereal_longitude: float
    tropical_longitude: float
    speed: float
    retrograde: bool
    rashi: int
    rashi_name: str
    degree_in_rashi: float
    house_d1: int
    nakshatra: int
    nakshatra_name: str
    pada: int
    sign_lord: str
    star_lord: str
    sub_lord: str
    dignity: Dignity
    d9_rashi: int
    d9_rashi_name: str
    d9_house: int
    d10_rashi: int
    d10_rashi_name: str
    d10_house: int
    bhava_chalit_house: int
    chandra_kundali_house: int
    vargottama: bool


class LagnaFact(BaseModel):
    name: str
    sidereal_longitude: Optional[float] = None
    rashi: int
    rashi_name: str
    degree_in_rashi: Optional[float] = None
    sign_lord: str


class HouseLordshipFact(BaseModel):
    house_number: int
    rashi: int
    rashi_name: str
    house_lord: str
    lord_natal_house: int
    lord_rashi: int
    lord_rashi_name: str
    lord_dignity: Dignity
    occupants: List[str]


class BhavaChalitHouseFact(BaseModel):
    house_number: int
    start_longitude: float
    midpoint_longitude: float
    end_longitude: float
    occupants: List[str]


class ChandraKundaliHouseFact(BaseModel):
    house_number: int
    rashi: int
    rashi_name: str
    sign_lord: str
    occupants: List[str]


class VargaChartFact(BaseModel):
    varga_name: str
    lagna_rashi: int
    lagna_rashi_name: str
    houses: Dict[str, List[str]]
    # New generic placement maps for D2/D4/D7/D12/D20/D24 and future Vargas.
    planet_rashis: Dict[str, int] = Field(default_factory=dict)
    planet_rashi_names: Dict[str, str] = Field(default_factory=dict)
    planet_houses: Dict[str, int] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ShadbalaComponentFact(BaseModel):
    sthana_bala: float
    dig_bala: float
    kala_bala: float
    cheshta_bala: float
    naisargika_bala: float
    drik_bala: float


class ShadbalaPlanetFact(BaseModel):
    planet: str
    components: ShadbalaComponentFact
    total_virupa: float
    total_rupa: float
    normalized_score: float
    strength_label: str
    # Phase-1 intentionally exposes calculation mode so this cannot be mistaken
    # for a full BPHS/Sripati Shadbala implementation.
    calculation_mode: str = "PHASE1_NORMALIZED_SUPPORT"


class ShadbalaResult(BaseModel):
    planets: List[ShadbalaPlanetFact]
    calculation_mode: str = "PHASE1_NORMALIZED_SUPPORT"
    classical_full: bool = False
    note: str = (
        "Phase-1 deterministic six-component support score. "
        "Use as supporting evidence only; full classical Shadbala sub-components "
        "require a dedicated astronomical implementation."
    )


class AshtakavargaPlanetFact(BaseModel):
    planet: str
    bindus_by_sign: List[int]
    total_bindus: int


class AshtakavargaResult(BaseModel):
    bhinnashtakavarga: List[AshtakavargaPlanetFact]
    sarvashtakavarga_by_sign: List[int]
    sarvashtakavarga_total: int
    sarvashtakavarga_by_house: Dict[str, int]
    strongest_houses: List[int]
    weakest_houses: List[int]
    calculation_mode: str = "PARASHARI_BAV_SAV"


class VedicChartResult(BaseModel):
    calculation_id: str
    profile_id: str
    input_hash: str
    calculation_version: str = "4.0.0"

    d1_lagna: LagnaFact
    d9_lagna: LagnaFact
    d10_lagna: LagnaFact
    chandra_lagna: LagnaFact

    planets: List[VedicPlanetFact]
    house_lordships: List[HouseLordshipFact]
    vargas: Dict[str, VargaChartFact]
    bhava_chalit: List[BhavaChalitHouseFact]
    chandra_kundali: List[ChandraKundaliHouseFact]

    # Phase-1 strength layers.
    shadbala: Optional[ShadbalaResult] = None
    ashtakavarga: Optional[AshtakavargaResult] = None

    metadata: Dict[str, Any]
