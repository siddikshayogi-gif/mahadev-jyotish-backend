"""Response Formatter Service.

Renders StructuredAIResponse into customer-friendly markdown formatting according to
AI_RESPONSE_CONTRACT.md.
"""

from app.schemas.ai_chat import StructuredAIResponse

class ResponseFormatter:
    """Formats only customer-safe astrologer output."""

    def format_customer_response(self, res: StructuredAIResponse, mode: str = "QUICK", language: str = "hi") -> str:
        parts = []
        if res.direct_answer:
            parts.append(res.direct_answer.strip())
        if res.short_explanation:
            parts.append(res.short_explanation.strip())
        if res.timing:
            parts.append(("समय का संकेत: " if language == "hi" else "Timing: ") + res.timing.strip())
        if res.practical_suggestion:
            parts.append(("सुझाव: " if language == "hi" else "Guidance: ") + res.practical_suggestion.strip())
        if res.follow_up_questions:
            qs = [q for q in res.follow_up_questions[:3] if q]
            if qs:
                header = "आप आगे यह भी पूछ सकते हैं:" if language == "hi" else "You can also ask:"
                parts.append(header + "\n" + "\n".join("• " + q for q in qs))
        if res.disclaimer:
            parts.append(res.disclaimer.strip())
        return "\n\n".join(parts)
