import os
import sys
import asyncio
import datetime
import json

# Add backend to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mocking for local test environment
import tests.mock_swisseph
os.environ["ALLOW_ANALYTICAL_FALLBACK"] = "True"

from app.services.ai.chat_service import ChatService
from app.schemas.ai_chat import AskPredictionRequest

async def test_acceptance():
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

    # TEST: Fast Present Career
    print("\n--- TEST: Present Career (Vineet) ---")
    req = AskPredictionRequest(
        question="Abhi career kaisa hai?",
        **vineet,
        mode="QUICK"
    )
    res = await service.process_prediction(req)

    print(f"Answer: {res.answer[:200]}...")
    assert "/100" not in res.answer
    assert "मुख्य ज्योतिषीय आधार" not in res.answer

    # TEST 2: Relationship Disruption (Vineet)
    print("\n--- TEST 2: Relationship Disruption (Vineet) ---")
    req = AskPredictionRequest(
        question="मेरे past में relationship disruption के सबसे मजबूत periods कौन-से थे?",
        **vineet,
        mode="QUICK"
    )
    res = await service.process_prediction(req)
    print(f"Answer: {res.answer[:200]}...")
    tech = res.structured_response.technical_astrological_reason
    assert "Identified Windows" in tech
    print("Historical Scan Verification: PASS")

    # TEST 3: Government Job History (Vikash)
    print("\n--- TEST 3: Government Job History (Vikash) ---")
    vikash = {
        "profile_id": "vikash",
        "name": "Vikash",
        "date_of_birth": "1996-05-19",
        "time_of_birth": "05:15:00",
        "place_of_birth": "Sikar",
        "latitude": 27.6094,
        "longitude": 75.1397,
        "timezone_id": "Asia/Kolkata"
    }
    req = AskPredictionRequest(
        question="2019 से 2026 के बीच सरकारी नौकरी के संकेत कब मजबूत थे?",
        **vikash,
        mode="QUICK"
    )
    res = await service.process_prediction(req)
    print(f"Answer: {res.answer[:200]}...")
    assert "Identified Windows" in res.structured_response.technical_astrological_reason
    print("Gov Job Scan Verification: PASS")

    # TEST 4: Date Specific (Vineet)
    print("\n--- TEST 4: Date Specific (Vineet) ---")
    req = AskPredictionRequest(
        question="15 March 2025 को मेरा समय कैसा था?",
        **vineet,
        mode="QUICK"
    )
    res = await service.process_prediction(req)
    print(f"Answer: {res.answer[:200]}...")
    tech = res.structured_response.technical_astrological_reason
    assert "2025-03-15" in tech or "2025-03-14" in tech # Date might shift slightly depending on timezone
    print("Date Specific Verification: PASS")

    # TEST 5: Relationship Reasoning (Vikash)
    print("\n--- TEST 5: Relationship Reasoning (Vikash) ---")
    req = AskPredictionRequest(
        question="Serious relationship के बाद उसी व्यक्ति से शादी होने की संभावना ज्यादा है या अलग होने की?",
        **vikash,
        mode="DEEP"
    )
    res = await service.process_prediction(req)
    print(f"Answer: {res.answer[:500]}")
    tech = res.structured_response.technical_astrological_reason
    assert "Venus" in tech or "Venus" in res.answer
if __name__ == "__main__":
    asyncio.run(test_acceptance())
    print("\nPHASE C RUNTIME ACCEPTANCE: PASS (Logic level)")
