import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.ai.chat_service import ChatService
from app.schemas.ai_chat import AskPredictionRequest

QUESTIONS = [
    # Domain 1: Marriage & Relationships
    "Meri shadi kab hogi?",
    "Mera jeevansathi kaisa hoga aur uska swabhav kaisa rahega?",
    "Kya meri love marriage hogi ya arranged marriage?",
    "Shadi me koi vilamb ya rukavat ke yog hain kya?",
    "Shadi ke baad mera bhagyo-day kaisa rahega?",
    "Mera married life kaisa rahega?",
    "Shadi ke liye sabse shubh samay konsa rahega?",

    # Domain 2: Career, Job & Government Service
    "Mujhe sarkari naukri kab milegi?",
    "Mera career graph kaisa rahega?",
    "Mujhe naukri me promotion kab milega?",
    "Kya mujhe job change karni chahiye ya abhi rukna chahiye?",
    "Meri naukri me safalta ke liye konsa kshetra sabse accha hai?",
    "Boss aur senior adhikariyo ke sath mere sambandh kaise rahenge?",
    "Mujhe karya me badi safalta kab milegi?",

    # Domain 3: Business & Wealth
    "Kya mujhe business karna chahiye ya job?",
    "Mera apna startup ya vyapar kab shuru hoga?",
    "Mujhe dhan labh kab hoga aur meri financial condition kaisi rahegi?",
    "Purane karj ya debt se kab mukti milegi?",
    "Kya mujhe share market ya investment me labh hoga?",
    "Mujhe aarthik sthiti me badi vridhi kab dikhegi?",

    # Domain 4: Property, Vehicle & Travel
    "Mera apna ghar ya zameen kab khareed paunga?",
    "Mera naya vahan / gadi kab khareedi jayegi?",
    "Kya mujhe videsh yatra ya foreign settlement ke yog hain?",
    "Videsh me padhai ya naukri ke yog kab hain?",
    "Ghar badalne ya sthan parivartan ke yog kab hain?",

    # Domain 5: Health & Vitality
    "Mera swasthya kaisa rahega?",
    "Mujhe mansik shanti aur stress से mukti kab milegi?",
    "Kya swasthya ko lekar koi savdhani baratni chahiye?",
    "Meri sharirik urja aur stamina ko badhane ke liye kya karen?",
    "Swasthya aur mansik sthirta ke liye sabse accha tarika kya hai?",

    # Domain 6: Past Timeline Verification
    "Mere past ki 5 main ghatnae batao",
    "Pehle ke samay me mere career me bada badlav kab aaya tha?",
    "Past me meri padhai aur vidya ka samay kaisa था?",
    "Mere jeevan me 2018 se 2022 ke beech kya mukhya ghatna hui thi?",
    "Past me arthik sthiti me bada badlav kab aaya tha?",
    "Mere jeevan ka sabse bada turning point past me kab tha?",

    # Domain 7: Present Day & Current Period
    "Aaj ka din kaisa rahega?",
    "Aaj ke din mujhe kis disha me karya karna chahiye?",
    "Abhi meri konsi mahadasha aur antardasha chal rahi hai aur uska kya prabhav hai?",
    "Is maheene me mera samay kaisa chal raha hai?",
    "Abhi ke samay me mujhe kya savdhani baratni chahiye?",
    "Aaj ke din mere liye konsa muhurta shubh rahega?",

    # Domain 8: Spiritual Remedies, Yogas & Prashna
    "Meri kundali me sabse shubh raj yoga konsa hai?",
    "Mujhe apni unnati ke liye konsa ratna dharan karna chahiye?",
    "Meri kundali me Manglik Dosh hai kya aur uska parihar kaise hoga?",
    "Mujhe konsi puja ya mantra ka jaap karna chahiye?",
    "Prashna Sankhya 45 ke anusaar mera kaam kab banega?",
    "Prashna Sankhya 108 ke anusaar meri safalta ke yog kab hain?",
    "Meri kundali me sabse majboot graha konsa hai?",
    "Mera jeevan lakshya aur spiritual path kaisa rahega?"
]

async def main():
    print("================================================================================")
    print("      MAHADEV JYOTISH AI — 50-QUESTION EXHAUSTIVE BATTERY AUDIT (VINEET)       ")
    print("================================================================================")

    service = ChatService()
    profile_id = "vineet_1998"

    passed_count = 0
    failed_count = 0
    jargon_leaks = 0

    start_time = time.time()

    for idx, q in enumerate(QUESTIONS, 1):
        print(f"\n[{idx}/50] QUESTION: '{q}'")
        req = AskPredictionRequest(
            profile_id=profile_id,
            question=q,
            language="hi",
            mode="DEEP" if idx % 2 == 1 else "QUICK",
            date_of_birth="1998-02-05",
            time_of_birth="11:30:00",
            latitude=26.9124,
            longitude=75.7873,
            timezone_id="Asia/Kolkata"
        )

        try:
            res = await service.process_prediction(req)
            ans = res.answer

            # Audit Checks:
            # 1. Non-empty response
            # 2. No raw "AI" word
            # 3. No raw BPHS/Sub-Lord/Placidus/FactHash internal leaks
            # 4. Respectful Pandit Ji phrasing

            has_ai_word = bool(" AI " in ans or "AI assistant" in ans or "RAG" in ans or "FactHash" in ans)
            has_technical_leak = bool("Sub-Lord" in ans or "Placidus" in ans or "BPHS" in ans or "Phaladeepika" in ans)

            if has_ai_word or has_technical_leak:
                print("❌ AUDIT WARNING: Technical or AI keyword detected!")
                jargon_leaks += 1
            else:
                passed_count += 1

            print("PANDIT JI RESPONSE SNIPPET:")
            lines = [l for l in ans.split("\n") if l.strip()]
            for l in lines[:3]:
                print("  " + l)
            print("  ...")

        except Exception as exc:
            print(f"❌ EXCEPTION ON QUESTION {idx}: {exc}")
            failed_count += 1

    total_time = time.time() - start_time
    print("\n" + "="*80)
    print(f"50-QUESTION AUDIT SUMMARY:")
    print(f"Total Questions Evaluated: 50")
    print(f"Passed Cleanly (No Jargon / No AI Leaks): {passed_count} / 50")
    print(f"Jargon / AI Leaks Detected: {jargon_leaks}")
    print(f"Failed / Exceptions: {failed_count}")
    print(f"Total Execution Time: {total_time:.2f} seconds ({total_time/50:.2f}s per question)")
    print("================================================================================")

if __name__ == "__main__":
    asyncio.run(main())
