"""Test ChatService imports and _log_prediction."""
import asyncio
import uuid
from datetime import datetime, timezone
from app.services.ai.chat_service import ChatService
from app.schemas.ai_chat import AskPredictionRequest
from app.services.astrology.prediction_protocol_service import NatalPromiseResult, NatalPromiseState, EventState, PredictionProtocolResult
from app.services.astrology.question_intent_engine import EventType

async def test_log_prediction():
    service = ChatService()

    # Mock data for _log_prediction
    req = AskPredictionRequest(
        question="Test question?",
        date_of_birth="1995-05-15",
        time_of_birth="10:30:00",
        place_of_birth="Delhi, India",
        latitude=28.6139,
        longitude=77.2090,
        timezone_id="Asia/Kolkata"
    )

    protocol = PredictionProtocolResult(
        event_type=EventType.MARRIAGE,
        natal_promise=NatalPromiseResult(
            state=NatalPromiseState.MODERATE_SUPPORT,
            score=50.0,
            reasons=["Strong 7th lord"]
        ),
        event_state=EventState.ACTIVE,
        confidence="MEDIUM",
        timing_windows=[],
        calculated_facts={},
        evidence_consensus={},
        contradictions=[],
        allowed_specificity="YEAR_WINDOW",
        forbidden_claims=[]
    )

    print("Testing _log_prediction...")
    try:
        # This will call hashlib and json.dumps
        service._log_prediction(req, protocol, "Test answer")
        print("Log prediction successful! Imports are correct.")
    except Exception as e:
        print(f"FAILED: {e}")
        raise e

if __name__ == "__main__":
    asyncio.run(test_log_prediction())
