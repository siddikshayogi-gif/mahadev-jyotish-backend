"""Mahadev Prediction Protocol - Rule 2: Event-Specific Astrology Matrix."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from enum import Enum

class EventSignature(BaseModel):
    domain: str
    primary_houses: List[int]
    supporting_houses: List[int] = []
    unfavorable_houses: List[int] = []
    natural_significators: List[str]
    varga: str = "D1"
    required_vargas: List[str] = ["D1"]
    kp_event_houses: List[int] = []
    shadbala_planets: List[str] = []
    ashtakavarga_houses: List[int] = []
    minimum_confirmations: int = 3
    parent_domain: Optional[str] = None
    classical_tags: List[str] = []

EVENT_SIGNATURES: Dict[str, EventSignature] = {
    "MARRIAGE": EventSignature(
        domain="MARRIAGE",
        primary_houses=[7, 2, 11],
        supporting_houses=[1, 5, 9],
        unfavorable_houses=[6, 8, 12, 10],
        natural_significators=["Venus", "Jupiter"],
        varga="D9",
        required_vargas=["D1", "D9"],
        kp_event_houses=[2, 7, 11]
    ),
    "LOVE_RELATIONSHIP": EventSignature(
        domain="LOVE_RELATIONSHIP",
        primary_houses=[5, 7, 11],
        supporting_houses=[2],
        unfavorable_houses=[6, 8, 12, 1],
        natural_significators=["Venus", "Moon", "Rahu"],
        varga="D9",
        required_vargas=["D1", "D9"]
    ),
    "RELATIONSHIP_COMPLICATION": EventSignature(
        domain="RELATIONSHIP_COMPLICATION",
        primary_houses=[5, 7, 8, 12],
        supporting_houses=[1],
        unfavorable_houses=[2, 11],
        natural_significators=["Venus", "Rahu", "Mars"],
        varga="D9",
        required_vargas=["D1", "D9"]
    ),
    "BREAKUP": EventSignature(
        domain="BREAKUP",
        primary_houses=[8, 12, 6, 1],
        supporting_houses=[4, 10],
        unfavorable_houses=[2, 7, 11],
        natural_significators=["Rahu", "Saturn", "Mars"],
        varga="D9"
    ),
    "CAREER": EventSignature(
        domain="CAREER",
        primary_houses=[10, 1, 2, 6, 11],
        supporting_houses=[3, 9],
        unfavorable_houses=[8, 12],
        natural_significators=["Sun", "Saturn", "Mercury", "Jupiter"],
        varga="D10",
        required_vargas=["D1", "D10"]
    ),
    "GOVERNMENT_JOB": EventSignature(
        domain="GOVERNMENT_JOB",
        primary_houses=[6, 10, 11, 1],
        supporting_houses=[2, 9],
        unfavorable_houses=[8, 12],
        natural_significators=["Sun", "Saturn", "Jupiter"],
        varga="D10",
        required_vargas=["D1", "D10"],
        minimum_confirmations=4
    ),
    "BUSINESS": EventSignature(
        domain="BUSINESS",
        primary_houses=[7, 10, 11, 3, 2],
        supporting_houses=[1, 9],
        unfavorable_houses=[6, 8, 12],
        natural_significators=["Mercury", "Jupiter", "Mars"],
        varga="D10",
        required_vargas=["D1", "D10"]
    ),
    "FINANCE_GAIN": EventSignature(
        domain="FINANCE_GAIN",
        primary_houses=[2, 11, 5, 9, 1],
        supporting_houses=[10],
        unfavorable_houses=[6, 8, 12],
        natural_significators=["Jupiter", "Venus", "Mercury"],
        varga="D2",
        required_vargas=["D1", "D2"]
    ),
    "CHILDREN": EventSignature(
        domain="CHILDREN",
        primary_houses=[5, 2, 11],
        supporting_houses=[9],
        unfavorable_houses=[1, 4, 10],
        natural_significators=["Jupiter"],
        varga="D7",
        required_vargas=["D1", "D7"]
    ),
    "PROPERTY": EventSignature(
        domain="PROPERTY",
        primary_houses=[4, 2, 11],
        supporting_houses=[1, 9],
        unfavorable_houses=[6, 8, 12],
        natural_significators=["Mars", "Venus", "Jupiter"],
        varga="D4",
        required_vargas=["D1", "D4"]
    ),
    "VEHICLE": EventSignature(
        domain="VEHICLE",
        primary_houses=[4, 11],
        supporting_houses=[2, 1, 9],
        unfavorable_houses=[6, 8, 12],
        natural_significators=["Venus", "Moon", "Mars"],
        varga="D4",
        required_vargas=["D1", "D4"]
    ),
    "FOREIGN_TRAVEL": EventSignature(
        domain="FOREIGN_TRAVEL",
        primary_houses=[3, 9, 12, 7, 1],
        supporting_houses=[],
        unfavorable_houses=[4],
        natural_significators=["Moon", "Rahu", "Saturn"],
        varga="D1"
    ),
    "LEGAL_DISPUTE": EventSignature(
        domain="LEGAL_DISPUTE",
        primary_houses=[6, 8, 12, 7],
        supporting_houses=[10, 11],
        unfavorable_houses=[2, 4, 5],
        natural_significators=["Saturn", "Mars", "Rahu"],
        varga="D1"
    ),
    "ACCIDENT": EventSignature(
        domain="ACCIDENT",
        primary_houses=[1, 6, 8, 12],
        supporting_houses=[],
        unfavorable_houses=[5, 9, 11],
        natural_significators=["Mars", "Saturn", "Rahu"],
        varga="D1"
    ),
    "HEALTH": EventSignature(
        domain="HEALTH",
        primary_houses=[1, 6, 8, 12],
        supporting_houses=[],
        unfavorable_houses=[5, 9, 11],
        natural_significators=["Sun", "Moon", "Saturn"],
        varga="D1"
    ),
    "EDUCATION": EventSignature(
        domain="EDUCATION",
        primary_houses=[4, 5, 2, 9, 11],
        supporting_houses=[1],
        unfavorable_houses=[6, 8, 12],
        natural_significators=["Mercury", "Jupiter"],
        varga="D24",
        required_vargas=["D1", "D24"]
    ),
    "FAME_STATUS": EventSignature(
        domain="FAME_STATUS",
        primary_houses=[1, 10, 11, 5, 9],
        supporting_houses=[2, 4, 7],
        unfavorable_houses=[6, 8, 12],
        natural_significators=["Sun", "Jupiter", "Moon"],
        varga="D1"
    ),
    "GENERAL_MAJOR_EVENT": EventSignature(
        domain="GENERAL_MAJOR_EVENT",
        primary_houses=[1, 10, 7, 4],
        supporting_houses=[5, 9, 2, 11],
        unfavorable_houses=[],
        natural_significators=["Sun", "Moon", "Saturn", "Jupiter", "Rahu", "Ketu"],
        varga="D1"
    )
}

# Sub-event exact signatures
EVENT_SIGNATURES.update({
    "FIRST_MARRIAGE": EVENT_SIGNATURES["MARRIAGE"].model_copy(update={"domain": "FIRST_MARRIAGE", "parent_domain": "MARRIAGE"}),
    "SECOND_MARRIAGE": EVENT_SIGNATURES["MARRIAGE"].model_copy(update={"domain": "SECOND_MARRIAGE", "parent_domain": "MARRIAGE", "supporting_houses": [8, 9, 1], "unfavorable_houses": [6, 12, 10]}),
    "FIRST_CHILD": EVENT_SIGNATURES["CHILDREN"].model_copy(update={"domain": "FIRST_CHILD", "parent_domain": "CHILDREN"}),
    "SECOND_CHILD": EVENT_SIGNATURES["CHILDREN"].model_copy(update={"domain": "SECOND_CHILD", "parent_domain": "CHILDREN", "primary_houses": [7]}),
    "PROPERTY_PURCHASE": EVENT_SIGNATURES["PROPERTY"].model_copy(update={"domain": "PROPERTY_PURCHASE", "parent_domain": "PROPERTY"}),
    "VEHICLE_PURCHASE": EVENT_SIGNATURES["VEHICLE"].model_copy(update={"domain": "VEHICLE_PURCHASE", "parent_domain": "VEHICLE"}),
})
