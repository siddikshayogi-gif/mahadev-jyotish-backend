import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.ai.chat_service import ChatService
from app.schemas.ai_chat import AskPredictionRequest

async def main():
    service = ChatService()

    test_questions = [
        "Mere past ki ghatnae batao",
        "Meri shadi kab hogi aur jeevansathi ka swabhav kaisa rahega?",
        "Kya mujhe sarkari naukri milegi ya business karna chahiye?",
        "Mera apna ghar aur vahan kab khareed paunga?",
        "Aaj ka din kaisa rahega aur mujhe kya savdhani baratni chahiye?"
    ]

    for q in test_questions:
        print(f"\n================================================================================")
        print(f"QUERY: '{q}'")
        print(f"================================================================================")
        req = AskPredictionRequest(
            profile_id="vineet_1998",
            question=q,
            language="hi",
            mode="DEEP",
            date_of_birth="1998-02-05",
            time_of_birth="11:30:00",
            latitude=26.9124,
            longitude=75.7873,
            timezone_id="Asia/Kolkata"
        )
        res = await service.process_prediction(req)
        print(res.answer)

if __name__ == "__main__":
    asyncio.run(main())
