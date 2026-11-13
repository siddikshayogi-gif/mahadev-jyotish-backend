"""Mahadev Prediction Protocol Service.

Implements the 32-rule Mahadev Prediction Protocol for deterministic,
evidence-based astrological interpretations.
"""

import hashlib
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from pydantic import BaseModel, Field
from app.schemas.ai_chat import EvidenceBundle, AskPredictionRequest, AstrologyMethod, TemporalContext, TemporalIntent
from app.schemas.canonical_astrology import CanonicalAstrologyResult
from app.services.astrology.question_intent_engine import QuestionIntentEngine, EventType
from app.services.astrology.event_signatures import EVENT_SIGNATURES, EventSignature
from app.services.astrology.prediction_rule_engine import PredictionRuleEngine
from app.services.astrology.event_state_crosscheck_engine import EventStateCrossCheckEngine
from app.services.astrology.marriage_engine_v2 import MarriageEventEngineV2
from app.services.astrology.dasha_engine import DashaEngine
from app.services.astrology.kp_engine import KPEngine
from app.services.astrology.vedic_engine import VedicEngine
from app.services.astrology.gochar_engine import GocharEngine
from app.services.astrology.yoga_engine import YogaEngine
from app.services.astrology.shadbala_engine import ShadbalaEngine
from app.services.astrology.ashtakavarga_engine import AshtakavargaEngine
from app.services.astrology.chhaya_graha_engine import ChhayaGrahaEvidenceEngine
from app.services.astrology.classical_rule_engine import ClassicalRuleEngine
from app.services.astrology.kp_horary_engine import KPHoraryEngine

class NatalPromiseState(str, Enum):
    STRONG_SUPPORT = "STRONG_SUPPORT"
    MODERATE_SUPPORT = "MODERATE_SUPPORT"
    WEAK_SUPPORT = "WEAK_SUPPORT"
    NEUTRAL = "NEUTRAL"
    CONTRADICTED = "CONTRADICTED"

class EventState(str, Enum):
    DENIED = "DENIED"
    WEAK_PROMISE = "WEAK_PROMISE"
    DORMANT = "DORMANT"
    DEVELOPING = "DEVELOPING"
    ACTIVE = "ACTIVE"
    PEAK = "PEAK"
    FADING = "FADING"
    COMPLTED_POSSIBLE = "COMPLETED_POSSIBLE"

class NatalPromiseResult(BaseModel):
    state: NatalPromiseState
    score: float
    reasons: List[str]

class PredictionProtocolResult(BaseModel):
    event_type: EventType
    natal_promise: NatalPromiseResult
    event_state: EventState
    confidence: str
    timing_windows: List[Dict[str, Any]]
    calculated_facts: Dict[str, Any]
    evidence_consensus: Dict[str, Any]
    contradictions: List[str]
    allowed_specificity: str
    forbidden_claims: List[str]

class PredictionProtocolService:
    def __init__(self):
        self.intent_engine = QuestionIntentEngine()
        self.vedic_engine = VedicEngine()
        self.kp_engine = KPEngine()
        self.dasha_engine = DashaEngine()
        self.gochar_engine = GocharEngine()
        self.yoga_engine = YogaEngine()
        self.shadbala_engine = ShadbalaEngine()
        self.ashtakavarga_engine = AshtakavargaEngine()
        self.state_engine = EventStateCrossCheckEngine()
        self.marriage_v2 = MarriageEventEngineV2()
        self.chhaya_engine = ChhayaGrahaEvidenceEngine()
        self.rule_engine = ClassicalRuleEngine()
        self.horary_engine = KPHoraryEngine()

    async def execute_protocol(
        self,
        req: AskPredictionRequest,
        canonical_natal: CanonicalAstrologyResult,
        temporal_context: Optional[TemporalContext] = None
    ) -> PredictionProtocolResult:
        # Rule 1: Question Classification
        event_type = self.intent_engine.classify(req.question)
        signature = EVENT_SIGNATURES.get(event_type.value, EVENT_SIGNATURES["GENERAL_MAJOR_EVENT"])

        import re
        horary_num = None
        match = re.search(r'\b(horary|prashna|number|no\.?|संख्या)?\s*([1-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9])\b', req.question, re.I)
        if match:
            try:
                num_val = int(match.group(2))
                if 1 <= num_val <= 249:
                    horary_num = num_val
            except Exception:
                pass

        horary_res = None
        if horary_num:
            horary_res = self.horary_engine.evaluate_horary(
                horary_number=horary_num,
                canonical_natal=canonical_natal,
                category=event_type.value
            )

        # Rule 2: Event Matrix is already in signature

        # Parallel Data Loading (Rule 4, 6, 7, 12, 13)
        vedic_chart = self.vedic_engine.calculate_vedic_chart(canonical_natal)
        kp_chart = self.kp_engine.calculate_kp(canonical_natal)

        # Rule 7: Varga Routing
        varga_status = "AVAILABLE"
        for req_v in signature.required_vargas:
            if req_v not in vedic_chart.vargas:
                varga_status = "MISSING"
                break

        target_dt = datetime.now(timezone.utc)
        if req.target_date_utc:
            target_dt = datetime.fromisoformat(req.target_date_utc.replace("Z", "+00:00"))

        dasha_res = self.dasha_engine.calculate_dasha_hierarchy(
            moon_longitude=next(p for p in canonical_natal.planets if p.body=="Moon").sidereal_longitude,
            birth_datetime_utc=datetime.fromisoformat(canonical_natal.birth.utc_instant.replace("Z", "+00:00")),
            target_datetime_utc=target_dt
        )

        gochar_res = self.gochar_engine.calculate_gochar_snapshot(canonical_natal, target_dt)
        yoga_res = self.yoga_engine.evaluate_yogas(vedic_chart)

        # Rule 3: D1 Natal Promise
        natal_promise = self._evaluate_natal_promise(vedic_chart, signature)

        # Rule 9: KP Independent Confirmation
        kp_evidence = self._evaluate_kp_confirmation(kp_chart, signature)

        # Rule 14: Classical Rules
        matched_rules = self.rule_engine.evaluate_rules(event_type.value, vedic_chart)

        # Rule 16: Evidence Consensus
        consensus = self._calculate_consensus(
            natal_promise, vedic_chart, kp_evidence, dasha_res, gochar_res, signature
        )

        # Rule 18: Event State
        # For Marriage, use the dedicated V2 engine (Rule 26)
        if event_type in [EventType.MARRIAGE, EventType.FIRST_MARRIAGE, EventType.SECOND_MARRIAGE]:
            marriage_res = await self.marriage_v2.analyze_first_marriage(canonical_natal)
            state_val = EventState.ACTIVE # Default or map from marriage_res
            if marriage_res["verdict"] == "PAST_EVENT_STRONG":
                state_val = EventState.COMPLTED_POSSIBLE
            timing_windows = marriage_res["all_plausible_future"][:3]
        else:
            state_result = await self.state_engine.infer(canonical_natal, vedic_chart, kp_chart, event_type.value)
            state_val = self._map_state(state_result.verdict)
            timing_windows = []
            if state_result.strongest_future_window:
                timing_windows.append(state_result.strongest_future_window.to_dict())

        # Rule 21: Confidence System
        confidence = self._calculate_confidence(consensus["weighted_score"], natal_promise.state)
        if varga_status == "MISSING":
            if confidence == "STRONG": confidence = "MEDIUM-STRONG"
            elif confidence == "MEDIUM-STRONG": confidence = "MEDIUM"
            elif confidence == "MEDIUM": confidence = "LOW-MEDIUM"
            else: confidence = "LOW"

        # Rule 20: Specificity Limiter
        specificity = "YEAR_WINDOW"
        if consensus["weighted_score"] > 80:
            specificity = "MONTH_WINDOW"

        facts = self._extract_facts(vedic_chart, kp_chart, dasha_res)
        if horary_res:
            facts["kp_horary"] = horary_res.model_dump()

        return PredictionProtocolResult(
            event_type=event_type,
            natal_promise=natal_promise,
            event_state=state_val,
            confidence=confidence,
            timing_windows=timing_windows,
            calculated_facts=facts,
            evidence_consensus=consensus,
            contradictions=[],
            allowed_specificity=specificity,
            forbidden_claims=["exact_date_certainty", "guaranteed_outcome"]
        )

    def _evaluate_natal_promise(self, vedic: Any, signature: EventSignature) -> NatalPromiseResult:
        score = 0.0
        reasons = []

        # Rule 4: House Lord Analysis
        lords = [h for h in vedic.house_lordships if h.house_number in signature.primary_houses]
        for l in lords:
            if str(l.lord_dignity).split(".")[-1] in {"EXALTED", "MOOLATRIKONA", "OWN_SIGN"}:
                score += 20
                reasons.append(f"Lord of House {l.house_number} is strong ({l.lord_dignity}).")
            elif str(l.lord_dignity).split(".")[-1] in {"DEBILITATED", "ENEMY"}:
                score -= 15
                reasons.append(f"Lord of House {l.house_number} is weak ({l.lord_dignity}).")

        # Rule 5: Karaka
        for p in vedic.planets:
            if p.body in signature.natural_significators:
                if str(p.dignity).split(".")[-1] not in {"DEBILITATED", "ENEMY"}:
                    score += 10
                    reasons.append(f"Karaka {p.body} is well-placed.")

        state = NatalPromiseState.NEUTRAL
        if score >= 40: state = NatalPromiseState.STRONG_SUPPORT
        elif score >= 15: state = NatalPromiseState.MODERATE_SUPPORT
        elif score < -10: state = NatalPromiseState.CONTRADICTED

        return NatalPromiseResult(state=state, score=score, reasons=reasons)

    def _evaluate_kp_confirmation(self, kp: Any, signature: EventSignature) -> Dict[str, Any]:
        event_houses = set(signature.kp_event_houses or signature.primary_houses)
        matches = 0
        for ps in kp.planet_significators:
            if set(ps.all_signified_houses).intersection(event_houses):
                matches += 1

        support = "NEUTRAL"
        if matches >= 4: support = "KP_STRONG_SUPPORT"
        elif matches >= 2: support = "KP_SUPPORT"

        return {"support": support, "matches": matches}

    def _calculate_consensus(self, natal: NatalPromiseResult, vedic: Any, kp: Dict, dasha: Any, gochar: Any, signature: EventSignature) -> Dict[str, Any]:
        weight = 0.0
        if natal.state == NatalPromiseState.STRONG_SUPPORT: weight += 35
        elif natal.state == NatalPromiseState.MODERATE_SUPPORT: weight += 20

        if kp["support"] == "KP_STRONG_SUPPORT": weight += 25
        elif kp["support"] == "KP_SUPPORT": weight += 15

        # Dasha (Rule 8)
        active = [d.lord for d in dasha.active_chain[:3]]
        if any(p in active for p in signature.natural_significators): weight += 20

        return {"weighted_score": weight, "summary": f"Consensus score: {weight}"}

    def _calculate_confidence(self, score: float, natal_state: NatalPromiseState) -> str:
        if natal_state == NatalPromiseState.CONTRADICTED: return "LOW"
        if score > 80: return "STRONG"
        if score > 60: return "MEDIUM-STRONG"
        if score > 40: return "MEDIUM"
        return "LOW-MEDIUM"

    def _map_state(self, verdict: str) -> EventState:
        mapping = {
            "PAST_EVENT_STRONG": EventState.COMPLTED_POSSIBLE,
            "FUTURE_EVENT_STRONG": EventState.ACTIVE,
            "AMBIGUOUS": EventState.DORMANT
        }
        return mapping.get(verdict, EventState.DORMANT)

    def _extract_facts(self, vedic: Any, kp: Any, dasha: Any) -> Dict[str, Any]:
        return {
            "lagna": vedic.d1_lagna.rashi_name,
            "active_dasha": [d.lord for d in dasha.active_chain[:3]],
            "shadbala": {x.planet: x.strength_label for x in vedic.shadbala.planets} if vedic.shadbala else {}
        }
