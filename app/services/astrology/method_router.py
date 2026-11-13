"""Astrology Method Router Service.

Determines the most appropriate astrological methodology (VEDIC, KP, HYBRID, etc.)
based on the user's question intent and required calculation precision.
"""

from typing import List, Tuple
from app.schemas.ai_chat import AstrologyMethod, AstrologyMethodDecision

class AstrologyMethodRouter:
    """Intelligently routes questions to specific astrological methodologies."""

    def route_question(self, question: str, topic: str) -> AstrologyMethodDecision:
        q_lower = question.lower()

        # Default decision
        primary_method = AstrologyMethod.VEDIC
        supporting_methods = []
        required_houses = []
        required_calculations = ["natal", "dasha", "gochar"]

        # 1. Career/Job/Business - Often benefits from KP precision
        if topic == "CAREER":
            if any(kw in q_lower for kw in ["kab", "when", "date", "time", "promotion"]):
                primary_method = AstrologyMethod.HYBRID
                supporting_methods = [AstrologyMethod.KP]
                required_houses = [2, 6, 10, 11]
                required_calculations.append("kp")
            else:
                primary_method = AstrologyMethod.VEDIC
                required_houses = [10, 1]

        # 2. Marriage/Relationship
        elif topic == "MARRIAGE":
            if any(kw in q_lower for kw in ["kab", "when", "wedding date"]):
                primary_method = AstrologyMethod.HYBRID
                supporting_methods = [AstrologyMethod.KP]
                required_houses = [2, 7, 11]
                required_calculations.append("kp")
            else:
                primary_method = AstrologyMethod.VEDIC
                required_houses = [7, 5]

        # 3. Wealth/Finance
        elif topic == "WEALTH":
            primary_method = AstrologyMethod.VEDIC
            required_houses = [2, 11, 9, 5]
            if "investment" in q_lower or "shares" in q_lower:
                supporting_methods = [AstrologyMethod.KP]
                required_calculations.append("kp")

        # 4. Health
        elif topic == "HEALTH":
            primary_method = AstrologyMethod.VEDIC
            required_houses = [6, 8, 12, 1]

        # 5. Education
        elif topic == "EDUCATION":
            primary_method = AstrologyMethod.VEDIC
            required_houses = [4, 5, 2, 9]

        # 6. Travel
        elif topic == "TRAVEL":
            primary_method = AstrologyMethod.VEDIC
            required_houses = [9, 12, 3, 7]

        # 7. Specialized catch-all for "When" questions
        if any(kw in q_lower for kw in ["kab", "exactly when", "timing", "muhurta"]):
            if "muhurta" in q_lower:
                primary_method = AstrologyMethod.MUHURTA
            elif primary_method == AstrologyMethod.VEDIC:
                primary_method = AstrologyMethod.HYBRID
                supporting_methods.append(AstrologyMethod.KP)
                if "kp" not in required_calculations:
                    required_calculations.append("kp")

        return AstrologyMethodDecision(
            question_category=topic,
            primary_method=primary_method,
            supporting_methods=list(set(supporting_methods)),
            required_houses=list(set(required_houses)),
            required_calculations=list(set(required_calculations)),
            confidence=0.9
        )
