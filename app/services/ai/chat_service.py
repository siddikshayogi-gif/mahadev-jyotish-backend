"""Chat & Prediction Service Orchestrator.

Handles chat pipeline, profile ownership verification, persistent conversation history,
and evidence-bound AI generation.
"""

import uuid
import time
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from app.schemas.ai_chat import (
    AskPredictionRequest,
    PredictionResponse,
    StructuredAIResponse,
    EvidenceBundle
)
from app.services.ai.intent_classifier import IntentClassifier
from app.services.ai.evidence_retriever import EvidenceRetriever
from app.services.ai.ai_provider import AIProviderGateway
from app.services.ai.claim_validator import ClaimValidator
from app.services.ai.response_formatter import ResponseFormatter
from app.services.ai.date_extractor import DateExtractor
from app.services.astrology.prediction_protocol_service import PredictionProtocolService
from app.services.commerce_service import CommerceService
from app.core.security import verify_profile_ownership
from app.api.v1.endpoints.profiles import _profiles_db

# Persistent chat history store
_chat_history_db: Dict[str, List[Dict[str, Any]]] = {}

class ChatService:
    """Orchestrates prediction requests according to Mahadev Prediction Protocol."""

    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.date_extractor = DateExtractor()
        self.evidence_retriever = EvidenceRetriever()
        self.protocol_service = PredictionProtocolService()
        self.ai_provider = AIProviderGateway()
        self.claim_validator = ClaimValidator()
        self.response_formatter = ResponseFormatter()
        self.commerce_service = CommerceService()

    async def process_prediction(
        self,
        req: AskPredictionRequest,
        current_user_id: str = "usr_dev_default_session"
    ) -> PredictionResponse:
        start_time = time.time()

        # 1. Profile ownership & basic setup
        profile = _profiles_db.get(req.profile_id)
        if profile:
            verify_profile_ownership(profile.user_id, current_user_id)

        # 2. Extract context & deterministic data
        topics, temporal_context = self.intent_classifier.classify_intent(
            question=req.question,
            explicit_time_intent=req.time_intent
        )

        # 3. Retrieve baseline evidence (Backward compatible with legacy engines)
        evidence = await self.evidence_retriever.retrieve_evidence(
            req=req,
            topics=topics,
            temporal_context=temporal_context
        )

        # 4. EXECUTE MAHADEV PREDICTION PROTOCOL (Rule 26)
        # Fetch canonical natal again (or ideally pass it through)
        from app.api.v1.endpoints.calculations import calculate_natal, NatalCalculationRequest
        natal_req = NatalCalculationRequest(profile_id=req.profile_id, **req.model_dump(exclude={"profile_id", "question", "language", "mode", "time_intent", "target_date_utc"}))
        canonical_natal = await calculate_natal(natal_req)

        protocol_result = await self.protocol_service.execute_protocol(
            req=req,
            canonical_natal=canonical_natal,
            temporal_context=temporal_context
        )

        # 5. Inject Protocol Result into AI Prompt as [LOCKED_STRUCTURED_PREDICTION]
        protocol_json = protocol_result.model_dump_json(indent=2)
        evidence.summary_prompt_text += f"\n\n[LOCKED_STRUCTURED_PREDICTION]\n{protocol_json}\n"

        # 6. Generate AI response via server gateway (Rule 23, 24)
        history = self.get_chat_history(req.profile_id, current_user_id)
        raw_ai_dict = await self.ai_provider.generate_astrology_response(
            question=req.question,
            evidence=evidence,
            mode=req.mode,
            language=req.language,
            history=history
        )

        structured_res = StructuredAIResponse(**raw_ai_dict)

        # 7. Final deterministic guard (Rule 23)
        validated_res, claim_status = self.claim_validator.validate_and_repair(
            ai_response=structured_res,
            evidence=evidence
        )

        # Enforce protocol confidence and timing
        # Ensure confidence is numeric (0.0 - 1.0) or null. Store text in confidence_label.
        raw_conf = protocol_result.confidence
        num_conf = 0.5 # Default

        confidence_map = {
            "LOW": 0.2,
            "LOW-MEDIUM": 0.4,
            "MEDIUM": 0.6,
            "MEDIUM-STRONG": 0.75,
            "STRONG": 0.9
        }

        if isinstance(raw_conf, str):
            validated_res.confidence_label = raw_conf
            num_conf = confidence_map.get(raw_conf.upper(), 0.5)
        elif isinstance(raw_conf, (int, float)):
            num_conf = float(raw_conf)
            # Find closest label
            if num_conf >= 0.85: validated_res.confidence_label = "STRONG"
            elif num_conf >= 0.7: validated_res.confidence_label = "MEDIUM-STRONG"
            elif num_conf >= 0.5: validated_res.confidence_label = "MEDIUM"
            else: validated_res.confidence_label = "LOW"

        validated_res.confidence = num_conf

        if protocol_result.timing_windows:
            win = protocol_result.timing_windows[0]
            if not validated_res.timing:
                validated_res.timing = f"{win['start_date']} to {win['end_date']}"

        formatted_answer = self.response_formatter.format_customer_response(
            res=validated_res,
            mode=req.mode,
            language=req.language
        )

        response_payload = PredictionResponse(
            answer=formatted_answer,
            structured_response=validated_res,
            mode=req.mode,
            language=req.language,
            provider=raw_ai_dict.get("provider", "gemini"),
            model=raw_ai_dict.get("model", "unknown"),
            is_mock=raw_ai_dict.get("is_mock", False),
            fact_hash=evidence.fact_hash,
            claim_validation_status=claim_status
        )

        # 8. Persist and Log (Rule 27)
        self._log_prediction(req, protocol_result, formatted_answer)

        # Persist chat history bound to user & profile
        chat_entry = {
            "id": f"chat_{uuid.uuid4().hex[:12]}",
            "user_id": current_user_id,
            "profile_id": req.profile_id,
            "question": req.question,
            "formatted_answer": formatted_answer,
            "topics": topics,
            "mode": req.mode,
            "fact_hash": evidence.fact_hash,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if req.profile_id not in _chat_history_db:
            _chat_history_db[req.profile_id] = []
        _chat_history_db[req.profile_id].append(chat_entry)

        return response_payload

    def _log_prediction(self, req, protocol, answer):
        """Rule 27: Forensic Debugging Log."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "question": req.question,
            "event_type": protocol.event_type,
            "verdict": protocol.event_state,
            "confidence": protocol.confidence,
            "fact_hash": hashlib.sha256(protocol.model_dump_json().encode()).hexdigest()[:8]
        }
        print(f"MAHADEV_PROTOCOL_LOG: {json.dumps(log_entry)}")

    def _apply_runtime_truth_guard(
        self,
        res: StructuredAIResponse,
        evidence: EvidenceBundle,
        language: str
    ) -> StructuredAIResponse:
        """Final deterministic guard after AI validation.

        The LLM can narrate, but it cannot override:
        - first-event past completion state
        - direct calculated Ashtakavarga/Shadbala facts
        - broad major-peak timing requested by the user
        """
        guarded = res.model_copy(deep=True)
        flags = evidence.query_flags or {}
        facts = evidence.calculated_facts or {}
        state = evidence.event_state or {}

        # A) Direct Ashtakavarga/Shadbala calculation query: answer from numbers, not prose inference.
        if flags.get("direct_strength_query"):
            av = facts.get("ashtakavarga") or {}
            sb = facts.get("shadbala") or {}
            if language == "hi":
                pieces = []
                if av.get("house_ranking"):
                    top = av["house_ranking"][:3]
                    pieces.append(
                        "अष्टकवर्ग (SAV) में सबसे मजबूत भाव: " +
                        ", ".join(f"भाव {h} = {v} बिंदु" for h, v in top)
                    )
                if sb.get("planet_ranking"):
                    top_p = sb["planet_ranking"][:3]
                    pieces.append(
                        "षड्बल support ranking में सबसे मजबूत ग्रह: " +
                        ", ".join(f"{p} = {score}" for p, score, label, rupa in top_p)
                    )
                guarded.direct_answer = "। ".join(pieces) + ("।" if pieces else "")
                guarded.short_explanation = (
                    "ये नाम और क्रम backend की इसी कुंडली के calculated values से लिए गए हैं, "
                    "generic अनुमान से नहीं। वर्तमान Shadbala layer supporting normalized calculation है।"
                )
            else:
                pieces = []
                if av.get("house_ranking"):
                    pieces.append("Strongest SAV houses: " + ", ".join(
                        f"H{h}={v}" for h,v in av["house_ranking"][:3]
                    ))
                if sb.get("planet_ranking"):
                    pieces.append("Strongest Shadbala-support planets: " + ", ".join(
                        f"{p}={score}" for p,score,label,rupa in sb["planet_ranking"][:3]
                    ))
                guarded.direct_answer = ". ".join(pieces) + "."
                guarded.short_explanation = "These rankings are taken directly from the calculated chart values."
            guarded.timing = ""
            guarded.supporting_factors = []
            guarded.challenging_factors = []
            guarded.practical_suggestion = ""
            return guarded

        # B) First marriage already shows a strong past activation.
        if state.get("state_event") == "FIRST_MARRIAGE" and state.get("verdict") == "PAST_EVENT_STRONG":
            start = state.get("broad_past_phase_start") or (state.get("strongest_past_window") or {}).get("start_date")
            end = state.get("broad_past_phase_end") or (state.get("strongest_past_window") or {}).get("end_date")
            if language == "hi":
                guarded.direct_answer = (
                    "आपकी कुंडली की blind cross-check reading में प्रथम विवाह का मुख्य सक्रिय समय पहले ही गुजर चुका दिखाई देता है। "
                    "इसलिए नई future first-marriage date देना सही नहीं होगा।"
                )
                guarded.short_explanation = (
                    "कई स्वतंत्र ज्योतिषीय संकेत past marriage phase की ओर एक साथ झुक रहे हैं। "
                    "इसे civil-status की तथ्यात्मक पुष्टि नहीं, बल्कि कुंडली से निकला strong past-event indication मानें।"
                )
                guarded.timing = f"सबसे मजबूत past विवाह phase: {start} से {end}" if start and end else ""
            else:
                guarded.direct_answer = (
                    "The chart's strongest first-marriage activation appears to have already passed, "
                    "so giving a new future first-marriage date would be misleading."
                )
                guarded.short_explanation = "Multiple independent astrological indicators converge on a past first-marriage phase."
                guarded.timing = f"Strongest past marriage phase: {start} to {end}" if start and end else ""
            return guarded

        # C) "Biggest/major" career query: don't display an arbitrary narrow PD slice.
        if flags.get("major_peak_query") and facts.get("major_peak_window"):
            w = facts["major_peak_window"]
            if evidence.event_type in {"CAREER","BUSINESS_GROWTH","GOVERNMENT_JOB","FINANCIAL_GAIN"}:
                if language == "hi":
                    guarded.timing = f"मुख्य broad success phase: {w['start_date']} से {w['end_date']}"
                else:
                    guarded.timing = f"Main broad success phase: {w['start_date']} to {w['end_date']}"
        return guarded

    def get_chat_history(
        self,
        profile_id: str,
        current_user_id: str = "usr_dev_default_session"
    ) -> List[Dict[str, Any]]:
        profile = _profiles_db.get(profile_id)
        if profile:
            verify_profile_ownership(profile.user_id, current_user_id)
        return _chat_history_db.get(profile_id, [])
