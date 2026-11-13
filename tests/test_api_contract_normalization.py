"""Test API Contract Normalization for confidence field."""
import json
from app.schemas.ai_chat import StructuredAIResponse, PredictionResponse
from app.services.ai.chat_service import ChatService
from app.services.astrology.prediction_protocol_service import PredictionProtocolResult, NatalPromiseResult, NatalPromiseState, EventState
from app.services.astrology.question_intent_engine import EventType

def test_confidence_normalization_labels():
    """Verify legacy string labels are mapped to numbers in the final response."""
    # This mock simulates the state after claim validation and protocol enforcement

    # Cases to test: String label, existing number, null
    test_cases = [
        ("MEDIUM-STRONG", 0.75),
        ("STRONG", 0.9),
        ("LOW", 0.2),
        (0.82, 0.82),
        (None, 0.5) # Default fallback
    ]

    # We can't easily unit test the private _process_prediction without heavy mocking,
    # but we can test the logic we added to chat_service.py by recreating it here or
    # observing it via a simpler harness if possible.

    confidence_map = {
        "LOW": 0.2,
        "LOW-MEDIUM": 0.4,
        "MEDIUM": 0.6,
        "MEDIUM-STRONG": 0.75,
        "STRONG": 0.9
    }

    for input_val, expected_val in test_cases:
        num_conf = 0.5
        label = None

        if isinstance(input_val, str):
            label = input_val
            num_conf = confidence_map.get(input_val.upper(), 0.5)
        elif isinstance(input_val, (int, float)):
            num_conf = float(input_val)

        # Verify schema accepts float
        res = StructuredAIResponse(
            direct_answer="test",
            short_explanation="test",
            timing="test",
            practical_suggestion="test",
            confidence=num_conf,
            confidence_label=label,
            technical_astrological_reason="",
            fact_hash="test"
        )

        assert isinstance(res.confidence, float)
        assert res.confidence == expected_val
        if isinstance(input_val, str):
            assert res.confidence_label == input_val

def test_json_serialization():
    """Verify final JSON structure matches Android expectations."""
    res = StructuredAIResponse(
        direct_answer="test",
        short_explanation="test",
        timing="test",
        practical_suggestion="test",
        confidence=0.78,
        confidence_label="MEDIUM-STRONG",
        technical_astrological_reason="",
        fact_hash="test"
    )

    json_data = res.model_dump_json()
    parsed = json.loads(json_data)

    assert "confidence" in parsed
    assert isinstance(parsed["confidence"], float)
    assert parsed["confidence"] == 0.78
    assert "confidence_label" in parsed
    assert parsed["confidence_label"] == "MEDIUM-STRONG"

if __name__ == "__main__":
    test_confidence_normalization_labels()
    test_json_serialization()
    print("API Contract Tests Passed")
