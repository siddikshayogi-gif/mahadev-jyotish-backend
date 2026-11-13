import os
import sys
import asyncio
import json

# Add backend to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mocking
import tests.mock_swisseph
os.environ["ALLOW_ANALYTICAL_FALLBACK"] = "True"

from app.services.ai.chat_service import ChatService
from app.schemas.ai_chat import AskPredictionRequest

async def test_historical():
    service = ChatService()

    vineet = {
        "profile_id": "vineet",
        "name": "Vineet Yogi",
        "date_of_birth": "1998-02-05",
        "time_of_birth": "11:30:00",
        "place_of_birth": "Jaipur",
        "latitude": 26.9124,
        "longitude": 75.7873,
        "timezone_id": "Asia/Kolkata"
    }

    print("\n--- TEST: Historical Relationship Disruption Scan ---")
    req = AskPredictionRequest(
        question="मेरे past में relationship disruption के सबसे मजबूत periods कौन-से थे?",
        **vineet,
        mode="QUICK"
    )
    res = await service.process_prediction(req)

    print(f"Answer: {res.answer[:500]}")
    tech = res.structured_response.technical_astrological_reason
    print(f"Technical: {tech[:500]}")

    # Assertions
    assert "Identified Historical/Future Event Windows" in tech
    assert "BREAKUP" in tech or "RELATIONSHIP" in tech or "relationship" in res.answer.lower()
    assert "/100" not in res.answer
    assert "/100" not in tech

if __name__ == "__main__":
    asyncio.run(test_historical())
