import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.ai.chat_service import ChatService
from app.schemas.ai_chat import AskPredictionRequest

async def main():
    service = ChatService()

    print("--- TEST 1: PAST 5 EVENTS QUERY ---")
    req1 = AskPredictionRequest(
        profile_id="prof_jaipur_1998",
        question="Mere past ki 5 ghatnae batao",
        language="hi",
        mode="DEEP",
        date_of_birth="1998-02-05",
        time_of_birth="11:30:00",
        latitude=26.9124,
        longitude=75.7873,
        timezone_id="Asia/Kolkata"
    )
    res1 = await service.process_prediction(req1)
    print("ANSWER 1:\n", res1.answer)
    print("\n" + "="*80 + "\n")

    print("--- TEST 2: TODAY'S DAY FORECAST QUERY ---")
    req2 = AskPredictionRequest(
        profile_id="prof_jaipur_1998",
        question="Aaj ka din kaisa rahega?",
        language="hi",
        mode="QUICK",
        date_of_birth="1998-02-05",
        time_of_birth="11:30:00",
        latitude=26.9124,
        longitude=75.7873,
        timezone_id="Asia/Kolkata"
    )
    res2 = await service.process_prediction(req2)
    print("ANSWER 2:\n", res2.answer)
    print("\n" + "="*80 + "\n")

    print("--- TEST 3: SPECIFIC MARRIAGE QUERY ---")
    req3 = AskPredictionRequest(
        profile_id="prof_jaipur_1998",
        question="Meri shadi kab hogi?",
        language="hi",
        mode="DEEP",
        date_of_birth="1998-02-05",
        time_of_birth="11:30:00",
        latitude=26.9124,
        longitude=75.7873,
        timezone_id="Asia/Kolkata"
    )
    res3 = await service.process_prediction(req3)
    print("ANSWER 3:\n", res3.answer)


if __name__ == "__main__":
    asyncio.run(main())
