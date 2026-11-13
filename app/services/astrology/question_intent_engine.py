"""Mahadev Prediction Protocol - Rule 1: Question/Event Classification."""
import re
from enum import Enum
from typing import List, Optional

class EventType(str, Enum):
    MARRIAGE = "MARRIAGE"
    FIRST_MARRIAGE = "FIRST_MARRIAGE"
    SECOND_MARRIAGE = "SECOND_MARRIAGE"
    LOVE_RELATIONSHIP = "LOVE_RELATIONSHIP"
    RELATIONSHIP_TO_MARRIAGE = "RELATIONSHIP_TO_MARRIAGE"
    RELATIONSHIP_COMPLICATION = "RELATIONSHIP_COMPLICATION"
    BREAKUP = "BREAKUP"
    CAREER = "CAREER"
    GOVERNMENT_JOB = "GOVERNMENT_JOB"
    BUSINESS = "BUSINESS"
    FINANCE_GAIN = "FINANCE_GAIN"
    CHILDREN = "CHILDREN"
    FIRST_CHILD = "FIRST_CHILD"
    SECOND_CHILD = "SECOND_CHILD"
    PROPERTY = "PROPERTY"
    PROPERTY_PURCHASE = "PROPERTY_PURCHASE"
    VEHICLE = "VEHICLE"
    VEHICLE_PURCHASE = "VEHICLE_PURCHASE"
    FOREIGN_TRAVEL = "FOREIGN_TRAVEL"
    LEGAL_DISPUTE = "LEGAL_DISPUTE"
    ACCIDENT = "ACCIDENT"
    HEALTH = "HEALTH"
    EDUCATION = "EDUCATION"
    FAME_STATUS = "FAME_STATUS"
    TRAVEL = "TRAVEL"
    FAMILY = "FAMILY"
    SPIRITUALITY = "SPIRITUALITY"
    GENERAL_MAJOR_EVENT = "GENERAL_MAJOR_EVENT"

class QuestionIntentEngine:
    """Deterministic Question/Event Classification layer."""

    CLASSIFICATION_RULES = [
        (EventType.SECOND_MARRIAGE, [r"second marriage", r"2nd marriage", r"dusri shadi", r"doosri shadi", r"दूसरी शादी", r"पुनर्विवाह"]),
        (EventType.FIRST_MARRIAGE, [r"first marriage", r"pehli shadi", r"पहली शादी"]),
        (EventType.RELATIONSHIP_TO_MARRIAGE, [r"love marriage", r"relationship.*marriage", r"relationship.*shadi"]),
        (EventType.RELATIONSHIP_COMPLICATION, [r"extra-marital", r"third person", r"shadi.*baad", r"affair"]),
        (EventType.BREAKUP, [r"breakup", r"separation", r"divorce", r"ब्रेकअप", r"विच्छेद"]),
        (EventType.MARRIAGE, [r"shadi", r"shaadi", r"marriage", r"vivah", r"शादी", r"विवाह"]),
        (EventType.SECOND_CHILD, [r"second child", r"dusri santan", r"doosri santan", r"दूसरी संतान"]),
        (EventType.FIRST_CHILD, [r"first child", r"pehli santan", r"पहली संतान"]),
        (EventType.CHILDREN, [r"child", r"children", r"santan", r"bacch", r"संतान", r"बच्च"]),
        (EventType.PROPERTY_PURCHASE, [r"ghar kab", r"house purchase", r"buy.*house", r"property.*buy", r"घर.*कब", r"मकान"]),
        (EventType.VEHICLE_PURCHASE, [r"car kab", r"gadi kab", r"vehicle purchase", r"कार.*कब", r"गाड़ी.*कब"]),
        (EventType.GOVERNMENT_JOB, [r"government job", r"govt job", r"sarkari", r"सरकारी नौकरी"]),
        (EventType.BUSINESS, [r"business", r"vyapar", r"profit", r"व्यापार", r"मुनाफा"]),
        (EventType.FINANCE_GAIN, [r"paisa", r"money", r"income", r"financial gain", r"dhan", r"wealth", r"पैसा", r"धन"]),
        (EventType.LEGAL_DISPUTE, [r"police", r"court", r"case", r"jail", r"legal", r"कानूनी", r"जेल"]),
        (EventType.ACCIDENT, [r"accident", r"injury", r"durghatna", r"दुर्घटना"]),
        (EventType.FAME_STATUS, [r"fame", r"status", r"naam", r"shohrat", r"प्रसिद्धि"]),
        (EventType.FOREIGN_TRAVEL, [r"foreign", r"abroad", r"videsh", r"विदेश"]),
        (EventType.CAREER, [r"career", r"job", r"naukri", r"करियर", r"नौकरी"]),
        (EventType.PROPERTY, [r"property", r"house", r"home", r"land", r"घर", r"जमीन"]),
        (EventType.EDUCATION, [r"education", r"study", r"exam", r"पढ़ाई", r"शिक्षा"]),
        (EventType.HEALTH, [r"health", r"disease", r"sehat", r"bimari", r"स्वास्थ्य"]),
        (EventType.TRAVEL, [r"travel", r"trip", r"yatra", r"यात्रा"]),
        (EventType.FAMILY, [r"family", r"parents", r"mother", r"father", r"परिवार"]),
        (EventType.SPIRITUALITY, [r"spiritual", r"bhakti", r"sadhana", r"भक्ति", r"साधना"]),
        (EventType.LOVE_RELATIONSHIP, [r"relationship", r"love", r"girlfriend", r"boyfriend", r"pyar", r"प्यार"]),
    ]

    def classify(self, question: str, fallback_topics: Optional[List[str]] = None) -> EventType:
        """Categorizes natural language question into a deterministic EventType enum."""
        q = (question or "").lower()
        for event_type, patterns in self.CLASSIFICATION_RULES:
            if any(re.search(p, q, re.I) for p in patterns):
                return event_type

        # Fallback to provided topics if classification fails
        if fallback_topics:
            topic = fallback_topics[0].upper()
            try:
                return EventType(topic)
            except ValueError:
                pass

        return EventType.GENERAL_MAJOR_EVENT
