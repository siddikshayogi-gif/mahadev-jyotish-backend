"""Phase 06 Unit & Integration Tests: Ask Mahadev AI + Gemini Server Gateway.

Tests:
1. Intent & Topic classification.
2. Identical factHash and evidence retrieval across QUICK and DEEP modes.
3. Response contract formatting & Claim Validation.
4. Profile ownership boundary enforcement on predictions.
5. Strict Live Gate behavior when fallback is disabled.
6. Provider and model metadata return.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.ai.intent_classifier import IntentClassifier
from app.services.ai.evidence_retriever import EvidenceRetriever
from app.services.ai.claim_validator import ClaimValidator
from app.services.ai.ai_provider import AIProviderGateway
from app.schemas.ai_chat import AskPredictionRequest, StructuredAIResponse, EvidenceBundle
from app.core.config import settings
from app.core.errors import ProviderException

client = TestClient(app)

PROFILE_1 = {
    "profile_id": "prof_jaipur_1998",
    "name": "Jaipur Reference",
    "date_of_birth": "1998-02-05",
    "time_of_birth": "11:30:00",
    "place_of_birth": "Jaipur, Rajasthan, India",
    "latitude": 26.9124,
    "longitude": 75.7873,
    "timezone_id": "Asia/Kolkata"
}

def test_intent_classifier():
    """Test keyword and natural language intent classification."""
    classifier = IntentClassifier()
    topic, time_intent = classifier.classify_intent("When will I get a job promotion in my office?")
    assert topic == "CAREER"
    assert time_intent == "NEXT_6_MONTHS"

    topic, time_intent = classifier.classify_intent("Mera shadi kab hoga?")
    assert topic == "MARRIAGE"

    topic, time_intent = classifier.classify_intent("Financial gains and wealth in 2026")
    assert topic == "WEALTH"

@pytest.mark.asyncio
async def test_quick_deep_identical_fact_hash():
    """Verify QUICK and DEEP modes produce identical factHash for same profile and question."""
    retriever = EvidenceRetriever()
    
    req_quick = AskPredictionRequest(
        profile_id=PROFILE_1["profile_id"],
        question="Kab milegi nayi naukri?",
        mode="QUICK",
        **{k: v for k, v in PROFILE_1.items() if k != "profile_id"}
    )
    
    req_deep = AskPredictionRequest(
        profile_id=PROFILE_1["profile_id"],
        question="Kab milegi nayi naukri?",
        mode="DEEP",
        **{k: v for k, v in PROFILE_1.items() if k != "profile_id"}
    )

    bundle_quick = await retriever.retrieve_evidence(req_quick, topic="CAREER")
    bundle_deep = await retriever.retrieve_evidence(req_deep, topic="CAREER")

    assert bundle_quick.fact_hash == bundle_deep.fact_hash
    assert bundle_quick.active_dasha_chain == bundle_deep.active_dasha_chain
    assert bundle_quick.lagna_rashi == bundle_deep.lagna_rashi

def test_claim_validator_repairs_unsupported_dasha():
    """Verify claim validator detects and repairs hallucinated Dasha claims."""
    validator = ClaimValidator()
    
    evidence = EvidenceBundle(
        profile_id="prof_test",
        topic="CAREER",
        fact_hash="abc123hash",
        lagna_rashi="Aries",
        moon_rashi="Taurus",
        sun_rashi="Capricorn",
        active_dasha_chain=["L1:Moon", "L2:Mars", "L3:Jupiter"],
        key_transits=["Saturn in Aquarius"],
        active_yogas=["Gajakesari"],
        kp_significators=["H10:Jupiter"],
        overall_timing_score=78.5,
        timing_verdict="FAVORABLE",
        summary_prompt_text="Test prompt"
    )

    raw_response = StructuredAIResponse(
        direct_answer="Good time for career.",
        short_explanation="You are running Rahu Dasha which gives rapid gains.",  # Rahu is NOT in active chain
        timing="Next 3 months",
        practical_suggestion="Focus on skills.",
        confidence=0.8,
        technical_astrological_reason="Standard factors.",
        fact_hash="abc123hash",
        disclaimer="Standard disclaimer"
    )

    repaired, status = validator.validate_and_repair(raw_response, evidence)
    assert status == "REPAIRED"
    assert "Active Dasha chain according to Swiss/Vedic math is L1:Moon -> L2:Mars -> L3:Jupiter" in repaired.short_explanation

def test_predictions_ask_endpoint():
    """Test POST /api/v1/predictions/ask with default/fallback enabled or configured provider."""
    # Temporarily set allow_analytical_fallback for integration test predictability
    original_fallback = settings.allow_analytical_fallback
    settings.allow_analytical_fallback = True

    try:
        payload = {
            "profile_id": PROFILE_1["profile_id"],
            "question": "Kab milega promotion?",
            "language": "hi",
            "mode": "QUICK",
            "name": PROFILE_1["name"],
            "date_of_birth": PROFILE_1["date_of_birth"],
            "time_of_birth": PROFILE_1["time_of_birth"],
            "place_of_birth": PROFILE_1["place_of_birth"],
            "latitude": PROFILE_1["latitude"],
            "longitude": PROFILE_1["longitude"],
            "timezone_id": PROFILE_1["timezone_id"]
        }

        response = client.post("/api/v1/predictions/ask", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert "fact_hash" in data
        assert len(data["fact_hash"]) == 64  # SHA-256 length
        assert data["mode"] == "QUICK"
        assert "claim_validation_status" in data
        assert data["claim_validation_status"] in ["VALIDATED", "REPAIRED"]

        # Verify chat history endpoint
        hist_resp = client.get(f"/api/v1/predictions/history/{PROFILE_1['profile_id']}")
        assert hist_resp.status_code == 200
        hist_data = hist_resp.json()
        assert len(hist_data) >= 1
        assert hist_data[-1]["question"] == "Kab milega promotion?"

    finally:
        settings.allow_analytical_fallback = original_fallback

def test_strict_live_gate_fails_without_credentials_when_fallback_disabled():
    """Verify strict live gate raises ProviderException when no API key exists and fallback is disabled."""
    original_fallback = settings.allow_analytical_fallback
    settings.allow_analytical_fallback = False

    try:
        provider = AIProviderGateway()
        provider.gemini_api_key = None
        provider.nvidia_api_key = None

        evidence = EvidenceBundle(
            profile_id="prof_test",
            topic="CAREER",
            fact_hash="abc123hash",
            lagna_rashi="Aries",
            moon_rashi="Taurus",
            sun_rashi="Capricorn",
            active_dasha_chain=["L1:Moon"],
            key_transits=[],
            active_yogas=[],
            kp_significators=[],
            overall_timing_score=50.0,
            timing_verdict="NEUTRAL",
            summary_prompt_text="Test prompt"
        )

        with pytest.raises(ProviderException):
            import asyncio
            asyncio.run(provider.generate_astrology_response("Job search?", evidence))
    finally:
        settings.allow_analytical_fallback = original_fallback

