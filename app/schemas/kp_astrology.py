"""KP Astrology Schema Models.

Pydantic models for deterministic KP (Krishnamurti Paddhati) facts:
Placidus Cusps, Sign/Star/Sub/SSL lords, 4-Level House/Planet Significators,
Ruling Planets, and Event House Evidence.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class KPCuspFact(BaseModel):
    house_number: int  # 1..12
    sidereal_longitude: float
    rashi: int
    rashi_name: str
    degree_in_rashi: float
    sign_lord: str
    star_lord: str
    sub_lord: str
    sub_sub_lord: str
    occupants: List[str]

class KPPlanetFact(BaseModel):
    body: str
    sidereal_longitude: float
    rashi: int
    rashi_name: str
    degree_in_rashi: float
    house_occupying: int  # 1..12
    houses_owning: List[int]
    sign_lord: str
    star_lord: str
    sub_lord: str
    sub_sub_lord: str

class KPSignificators(BaseModel):
    level1_planets_in_star_of_occupants: List[str]
    level2_occupants: List[str]
    level3_planets_in_star_of_lord: List[str]
    level4_house_lord: str
    combined_significators: List[str]

class HouseSignificatorsFact(BaseModel):
    house_number: int  # 1..12
    significators: KPSignificators

class PlanetSignificatorFact(BaseModel):
    planet: str
    level1_houses: List[int]
    level2_houses: List[int]
    level3_houses: List[int]
    level4_houses: List[int]
    all_signified_houses: List[int]

class NodeProxyFact(BaseModel):
    node: str
    proxies: List[str]

class KPRulingPlanetsFact(BaseModel):
    lagna_sign_lord: str
    lagna_star_lord: str
    lagna_sub_lord: str
    moon_sign_lord: str
    moon_star_lord: str
    moon_sub_lord: str
    day_lord: str
    nodes_as_proxies: List[NodeProxyFact]
    ruling_planets_list: List[str]

class KPEventRuleEvidence(BaseModel):
    event_name: str
    primary_houses: List[int]
    supporting_houses: List[int]
    obstruction_houses: List[int]
    favorable_planets: List[str]
    unfavorable_planets: List[str]
    rule_evidence: str

class KPChartResult(BaseModel):
    calculation_id: str
    profile_id: str
    input_hash: str
    calculation_version: str = "4.0.0"

    cusps: List[KPCuspFact]
    planets: List[KPPlanetFact]
    house_significators: List[HouseSignificatorsFact]
    planet_significators: List[PlanetSignificatorFact]
    ruling_planets: KPRulingPlanetsFact
    event_evidences: List[KPEventRuleEvidence]
    metadata: Dict[str, Any]
