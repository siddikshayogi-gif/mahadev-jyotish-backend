import asyncio
import os
from app.services.ai.ai_provider import AIProviderGateway
from app.schemas.ai_chat import EvidenceBundle, TemporalContext, TemporalIntent

async def test_provider():
    gateway = AIProviderGateway()
    print(f"Testing model: {gateway.gemini_model}")

    # Simple prompt test
    print("Step 1: Simple prompt test...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{gateway.gemini_model}:generateContent?key={gateway.gemini_api_key}"
    import httpx
    payload = {
        "contents": [{"parts": [{"text": "Reply exactly: MAHADEV GEMINI OK"}]}]
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload)
        if resp.status_code == 200:
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            print(f"Response: {text.strip()}")
            if "MAHADEV GEMINI OK" in text:
                print("SIMPLE TEST: PASS")
            else:
                print("SIMPLE TEST: FAIL (Unexpected response)")
        else:
            print(f"SIMPLE TEST: FAIL (Status {resp.status_code}: {resp.text})")

    # Evidence bundle test
    print("\nStep 2: Evidence bundle test...")
    evidence = EvidenceBundle(
        profile_id="test_prof",
        topic="CAREER",
        fact_hash="test_hash",
        lagna_rashi="Aries",
        moon_rashi="Taurus",
        sun_rashi="Leo",
        temporal_context=TemporalContext(intent=TemporalIntent.PRESENT),
        active_dasha_chain=[{"level": 1, "level_name": "Mahadasha", "lord": "Saturn", "start": "2020-01-01", "end": "2039-01-01"}],
        key_transits=[],
        active_yogas=[],
        kp_significators=[],
        overall_timing_score=75.0,
        timing_verdict="Good",
        summary_prompt_text="Test evidence summary"
    )

    try:
        res = await gateway.generate_astrology_response(
            question="How is my career?",
            evidence=evidence,
            mode="QUICK",
            language="hi"
        )
        print(f"AI Provider Response received successfully.")
        print(f"Provider: {res.get('provider')}")
        print(f"Model: {res.get('model')}")
        print(f"Direct Answer: {res.get('direct_answer')}")
        print("EVIDENCE BUNDLE TEST: PASS")
    except Exception as e:
        print(f"EVIDENCE BUNDLE TEST: FAIL ({str(e)})")

if __name__ == "__main__":
    # Ensure GEMINI_API_KEY is set in environment if not in settings
    asyncio.run(test_provider())
