"""Regression Test for Mahadev Prediction Protocol."""
import asyncio
from datetime import datetime, timezone
from app.services.astrology.prediction_protocol_service import PredictionProtocolService
from app.schemas.ai_chat import AskPredictionRequest
from app.api.v1.endpoints.calculations import calculate_natal, NatalCalculationRequest

async def test_protocol():
    service = PredictionProtocolService()
    req = AskPredictionRequest(
        question="Meri shadi kab hogi?",
        date_of_birth="1995-05-15",
        time_of_birth="10:30:00",
        place_of_birth="Delhi, India",
        latitude=28.6139,
        longitude=77.2090,
        timezone_id="Asia/Kolkata"
    )

    natal_req = NatalCalculationRequest(
        date_of_birth=req.date_of_birth,
        time_of_birth=req.time_of_birth,
        place_of_birth=req.place_of_birth,
        latitude=req.latitude,
        longitude=req.longitude,
        timezone_id=req.timezone_id
    )

    canonical_natal = await calculate_natal(natal_req)
    result = await service.execute_protocol(req, canonical_natal)

    print("\nMAHADEV PREDICTION PROTOCOL TEST RESULT:")
    print(f"Event Type: {result.event_type}")
    print(f"Natal Promise: {result.natal_promise.state}")
    print(f"Event State: {result.event_state}")
    print(f"Confidence: {result.confidence}")
    print(f"Timing Windows Count: {len(result.timing_windows)}")

    assert result.event_type == "FIRST_MARRIAGE" or result.event_type == "MARRIAGE"
    print("TEST PASS")

if __name__ == "__main__":
    asyncio.run(test_protocol())
