"""Intent & Topic Classifier Service.

Determines the primary life topic (CAREER, WEALTH, MARRIAGE, HEALTH, EDUCATION, TRAVEL, GENERAL)
and time intent from user natural language query.
"""

import re
from typing import Tuple, Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from app.schemas.ai_chat import TemporalIntent, TemporalContext
from app.services.ai.date_extractor import DateExtractor

TOPIC_KEYWORDS = {
    "CAREER": ["job", "career", "promotion", "office", "boss", "naukri", "interview", "profession", "work", "kaam", "post", "naukari"],
    "GOVERNMENT_JOB": ["government job", "sarkari", "civil service", "ias", "ips", "upsc", "psc", "selection", "joining", "gazetted", "सरकारी", "नौकरी"],
    "BUSINESS": ["business", "vyapar", "dhandha", "startup", "trade", "profit", "loss", "client", "partnership"],
    "WEALTH": ["money", "wealth", "finance", "paisa", "dhan", "loan", "debt", "investment", "shares", "gains", "income", "salary", "salary increase", "stree dhan"],
    "MARRIAGE": ["marriage", "wedding", "spouse", "shadi", "vivah", "matchmaking", "husband", "wife", "patni", "pati", "marriage type", "love marriage", "arranged marriage"],
    "RELATIONSHIP": ["love", "partner", "relationship", "pyaar", "ishq", "girlfriend", "boyfriend", "commitment", "serious relationship"],
    "RELATIONSHIP_TO_MARRIAGE": ["relationship to marriage", "shadi usi se hogi", "love conversion", "relationship conversion"],
    "BREAKUP": ["breakup", "divorce", "separation", "disruption", "dhokha", "split", "talaq"],
    "CHILDREN": ["child", "children", "baby", "son", "daughter", "pregnancy", "bacha", "santana", "conceive"],
    "HEALTH": ["health", "disease", "illness", "body", "operation", "sehat", "bimari", "doctor", "recovery", "mental", "hospital"],
    "ACCIDENT": ["accident", "injury", "hurt", "operation", "surgery", "chot", "durghatna"],
    "LEGAL": ["court", "case", "legal", "lawyer", "litigation", "police", "jail", "vivad", "kanoon"],
    "EDUCATION": ["study", "exam", "college", "school", "degree", "pariksha", "results", "rank", "admission", "padhai"],
    "PROPERTY": ["property", "home", "house", "land", "flat", "plot", "zameen", "makan", "ghar", "buy house"],
    "TRAVEL": ["travel", "foreign", "visa", "abroad", "trip", "yatra", "videsh", "relocation", "immigration", "passport"],
    "FAMILY": ["family", "parents", "mother", "father", "brother", "sister", "parivar", "mata", "pita"],
    "SPIRITUALITY": ["spiritual", "god", "bhakti", "meditation", "dhyan", "moksha", "guru", "mantra", "puja"],
    "TODAYS_DAILY_FORECAST": ["aaj ka din", "aaj kaisa", "aaj ka rashifal", "today forecast", "today day", "how is my day", "aaj ka samay", "आज का दिन", "आज कैसा", "aaj mera din"],
    "PAST_5_MAJOR_EVENTS": ["past 5 events", "past ghatnaye", "past ghatna", "beeti ghatnae", "pehle ki ghatna", "past history", "5 past events", "5 ghatna", "past 5", "past events"],
    "GENERAL_MAJOR_EVENTS": ["major events", "life events", "life-event", "big events", "mukhya ghatnayein", "ghatna", "important", "badi ghatna", "strengths", "कुंडली की", "विशेषताएं"],

    "DASHA": ["dasha", "period", "vimshottari", "timeline", "mahadasa"],
    "GOCHAR": ["gochar", "transit", "planet shift", "planet change"],
    "PRASHNA": ["prashna", "horary", "question now"],
    "MUHURTA": ["muhurta", "shubh samay", "good time to start"],
    "ASHTAKAVARGA": ["ashtakavarga", "ashtakvarga", "अष्टकवर्ग", "points", "bindu", "बिंदु"],
    "SHADBALA": ["shadbala", "shadbal", "षड्बल", "ग्रह बल", "planet strength"]
}

class IntentClassifier:
    """Classifies user astrology questions deterministically or via lightweight keyword rules."""

    def __init__(self):
        self.date_extractor = DateExtractor()

    def classify_intent(self, question: str, explicit_time_intent: Optional[str] = None) -> Tuple[List[str], TemporalContext]:
        q_lower = question.lower()

        # Multi-intent logic: e.g. "relationship to marriage"
        detected_topics = []
        if ("relationship" in q_lower or "love" in q_lower) and ("marriage" in q_lower or "shadi" in q_lower or "shaadi" in q_lower):
            detected_topics.append("RELATIONSHIP_TO_MARRIAGE")

        # Topic detection
        for topic, keywords in TOPIC_KEYWORDS.items():
            if topic == "RELATIONSHIP_TO_MARRIAGE" and detected_topics: continue
            for kw in keywords:
                pattern = r'\b' + re.escape(kw) + r'\b' if kw.isascii() else re.escape(kw)
                if re.search(pattern, q_lower):
                    detected_topics.append(topic)
                    break

        if not detected_topics:
            detected_topics = ["GENERAL"]

        # Deduplicate
        detected_topics = sorted(list(set(detected_topics)))

        # 1. Extract specific dates
        years = re.findall(r'\b(19\d{2}|20\d{2})\b', q_lower)
        target_date = self.date_extractor.extract_date(question)

        intent = TemporalIntent.PRESENT
        start_date = None
        end_date = None

        # Determine intent and dates
        if len(years) >= 2:
            intent = TemporalIntent.DATE_RANGE
            start_date = f"{min(years)}-01-01"
            end_date = f"{max(years)}-12-31"
        elif target_date:
            intent = TemporalIntent.DATE_SPECIFIC
        elif any(kw in q_lower for kw in ["lifetime", "whole life", "jeevan", "zindagi", "major events", "life events", "life-event", "career graph", "जीवन", "ज़िंदगी", "कितने", "kitne", "kitni"]):
            intent = TemporalIntent.LIFETIME
        elif any(kw in q_lower for kw in ["future", "upcoming", "bhavishya", "aage", "when", "kab", "hoga", "hogi", "agle", "agley", "अगले", "आगे", "कब", "होगा", "होगी", "रहेगा", "रहेंगी"]):
            intent = TemporalIntent.FUTURE
        elif any(kw in q_lower for kw in ["past", "historical", "pehle", "beeta hua", "history", "tha", "thi", "the", "पहले", "बीता", "था", "थी", "थे", "गया"]):
            intent = TemporalIntent.PAST
        elif any(kw in q_lower for kw in ["now", "today", "current", "aaj", "abhi", "present", "अभी", "आज", "अब"]):
            intent = TemporalIntent.PRESENT
        elif "hai" in q_lower or "hein" in q_lower or "है" in q_lower or "हैं" in q_lower:
            intent = TemporalIntent.PRESENT

        # Refine if explicit field provided
        if explicit_time_intent == "PAST": intent = TemporalIntent.PAST
        elif explicit_time_intent == "FUTURE": intent = TemporalIntent.FUTURE
        elif explicit_time_intent == "LIFETIME": intent = TemporalIntent.LIFETIME

        # Default horizons
        now = datetime.now(timezone.utc)
        if intent == TemporalIntent.FUTURE and not start_date:
            start_date = now.strftime("%Y-%m-%d")
            long_future_terms = [
                "sabse badi", "sabse bada", "सबसे बड़ी", "सबसे बड़ा",
                "biggest", "largest", "major turning point", "peak success",
                "badi safalta", "bada safalta", "बड़ी सफलता", "बड़ा turning"
            ]
            horizon_years = 15 if any(x in q_lower for x in long_future_terms) else 5
            end_date = (now + timedelta(days=365*horizon_years)).strftime("%Y-%m-%d")
        elif intent == TemporalIntent.PAST and not start_date:
            end_date = now.strftime("%Y-%m-%d")
            start_date = (now - timedelta(days=365*5)).strftime("%Y-%m-%d") # 5 years for past
        elif intent == TemporalIntent.LIFETIME:
            # For lifetime, reduce range for faster dev scanning
            end_date = (now + timedelta(days=365*2)).strftime("%Y-%m-%d")
            start_date = (now - timedelta(days=365*10)).strftime("%Y-%m-%d")

        context = TemporalContext(
            intent=intent,
            start_date=start_date,
            end_date=end_date,
            target_date=target_date.strftime("%Y-%m-%d") if target_date else None
        )

        return detected_topics, context
