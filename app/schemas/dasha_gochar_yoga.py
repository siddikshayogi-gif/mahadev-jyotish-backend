"""Dasha, Gochar, Yoga and Timing Window Schemas.

Pydantic models for 5-level Vimshottari Dasha, target-date Gochar (transits),
classical Yogas, and structured topic timing evidence.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class DashaPeriod(BaseModel):
    level: int  # 1..5
    level_name: str  # "Mahadasha", "Antardasha", "Pratyantardasha", "Sukshma", "Pran"
    lord: str
    start_date_utc: str
    end_date_utc: str
    theoretical_start_date_utc: Optional[str] = None # Added for audit
    sub_periods: Optional[List['DashaPeriod']] = None
    status: Optional[str] = None  # "PAST", "CURRENT", "FUTURE"
    parent_lords: List[str] = Field(default_factory=list)

DashaPeriod.model_rebuild()

class DashaHierarchyResult(BaseModel):
    calculation_id: str
    profile_id: str
    moon_longitude: float
    birth_date_utc: str
    target_date_utc: str
    active_chain: List[DashaPeriod]
    mahadashas: List[DashaPeriod]

class TransitPlanetFact(BaseModel):
    body: str
    sidereal_longitude: float
    rashi: int
    rashi_name: str
    degree_in_rashi: float
    speed: float
    retrograde: bool
    nakshatra: int
    nakshatra_name: str
    star_lord: str
    house_from_d1_lagna: int
    house_from_moon: int

class GocharResult(BaseModel):
    calculation_id: str
    profile_id: str
    natal_input_hash: str
    target_datetime_utc: str
    transits: List[TransitPlanetFact]
    key_aspects_and_conjunctions: List[str]

class YogaFact(BaseModel):
    id: str
    name: str
    name_hindi: str
    category: str  # "RAJA_YOGA", "DHANA_YOGA", "MAHAPURUSHA", "SPECIAL", "VIPREET"
    description: str
    planets_involved: List[str]
    houses_involved: List[int]
    is_active: bool
    strength_score: float
    source_reference: str

class YogaResult(BaseModel):
    calculation_id: str
    profile_id: str
    total_yogas_found: int
    yogas: List[YogaFact]

class TopicTimingRequest(BaseModel):
    profile_id: Optional[str] = None
    topic: str = "CAREER"
    target_date_utc: Optional[str] = None
    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    time_of_birth: Optional[str] = None
    place_of_birth: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone_id: Optional[str] = None

class TimingWindowEvidenceResult(BaseModel):
    calculation_id: str
    profile_id: str
    topic: str
    target_date_utc: str
    active_dasha_chain: List[str]
    dasha_favourability: str  # "FAVORABLE", "NEUTRAL", "UNFAVORABLE"
    dasha_evidence: str
    transit_favourability: str
    transit_evidence: List[str]
    yoga_evidence: List[str]
    kp_evidence: List[str]
    overall_timing_score: float
    verdict: str
    favorable_window: str
    evidence_strength: str = "MODERATE" # LOW, MODERATE, HIGH, VERY_HIGH
