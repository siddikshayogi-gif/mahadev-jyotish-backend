"""Canonical Astrology Schema Data Models.

Matches /project_brain/docs/CANONICAL_ASTROLOGY_SCHEMA.md.
Single immutable astronomical fact contract.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class IdentitySection(BaseModel):
    calculation_id: str
    profile_id: str
    input_hash: str
    calculation_version: str = "2.0.0"

class BirthSection(BaseModel):
    local_date: str
    local_time: str
    timezone_id: str
    utc_instant: str
    latitude: float
    longitude: float
    place_label: str
    julian_day_ut: float

class ProviderSection(BaseModel):
    swiss_version: str
    ephemeris_mode: str = "SWIEPH"
    sidereal_mode: str = "LAHIRI"
    ayanamsha_name: str = "CHITRAPAKSHA_LAHIRI"
    ayanamsha_value: float
    node_mode: str = "MEAN_NODE"

class PlanetDetail(BaseModel):
    body: str
    tropical_longitude: float
    sidereal_longitude: float
    speed: float
    retrograde: bool
    rashi: int
    rashi_name: str
    degree_in_rashi: float
    nakshatra: int
    nakshatra_name: str
    pada: int
    sign_lord: str
    star_lord: str
    sub_lord: str

class AngleDetail(BaseModel):
    name: str
    sidereal_longitude: float
    rashi: int
    rashi_name: str
    degree_in_rashi: float
    nakshatra: int
    nakshatra_name: str
    pada: int
    sign_lord: str
    star_lord: str
    sub_lord: str

class AnglesSection(BaseModel):
    ascendant: AngleDetail
    mc: AngleDetail

class VedicSection(BaseModel):
    whole_sign_houses: Dict[int, int]  # House 1..12 -> Rashi 0..11

class BhavaCuspDetail(BaseModel):
    house_number: int
    sidereal_longitude: float
    rashi: int
    rashi_name: str
    degree_in_rashi: float
    sign_lord: str
    star_lord: str
    sub_lord: str

class BhavaSection(BaseModel):
    method: str = "PLACIDUS"
    cusps: List[BhavaCuspDetail]

class KPSection(BaseModel):
    cusps: List[BhavaCuspDetail]

class ProvenanceSection(BaseModel):
    calculated_at_utc: str
    engine_build: str = "pyswisseph-production-2.0"
    checksum: str

class CanonicalAstrologyResult(BaseModel):
    identity: IdentitySection
    birth: BirthSection
    provider: ProviderSection
    planets: List[PlanetDetail]
    angles: AnglesSection
    vedic: VedicSection
    bhava: BhavaSection
    kp: KPSection
    provenance: ProvenanceSection
