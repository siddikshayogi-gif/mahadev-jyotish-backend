"""Phase 4 Past-Event Cross-Check / Life-State Inference Engine.

Purpose:
- Do NOT assume every "when will X happen?" question is future-only.
- Rank past versus future event activation using deterministic astrology evidence.
- Produce an INTERNAL life-state verdict only; it is not a factual civil-status database.

The engine is intentionally conservative: it reports PAST_EVENT_STRONG only when
past evidence meaningfully exceeds future evidence and has enough corroboration.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app.services.astrology.event_signatures import EVENT_SIGNATURES
from app.services.astrology.temporal_scanners import TemporalScanner
from app.services.astrology.fine_timing_engine import FineTimingEngine

PAST_CAPABLE_EVENTS = {
    "MARRIAGE",
    "FIRST_MARRIAGE",
    "SECOND_MARRIAGE",
    "RELATIONSHIP_TO_MARRIAGE",
    "CHILDREN",
    "FIRST_CHILD",
    "SECOND_CHILD",
    "CAREER",
    "GOVERNMENT_JOB",
    "BUSINESS",
    "FOREIGN_TRAVEL",
    "PROPERTY",
    "RELATIONSHIP",
    "BREAKUP",
}

@dataclass
class EventWindowScore:
    start_date: str
    end_date: str
    score: float
    phase: str  # PAST or FUTURE
    strength: str
    source: str = "temporal_scan"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class LifeStateInference:
    event: str
    verdict: str
    confidence: float
    strongest_past_window: Optional[EventWindowScore]
    strongest_future_window: Optional[EventWindowScore]
    past_score: float
    future_score: float
    margin: float
    internal_note: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

class LifeStateInferenceEngine:
    def __init__(self):
        self.temporal_scanner = TemporalScanner()
        self.fine_timing = FineTimingEngine()

    @staticmethod
    def _strength(score: float) -> str:
        if score >= 82: return "VERY_HIGH"
        if score >= 68: return "HIGH"
        if score >= 54: return "MODERATE"
        return "LOW"

    @staticmethod
    def _as_utc(dt: datetime) -> datetime:
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    async def infer(
        self,
        canonical_natal,
        vedic_chart,
        event: str,
        now: Optional[datetime] = None,
        years_back: int = 15,
        years_forward: int = 5,
    ) -> LifeStateInference:
        now = self._as_utc(now or datetime.now(timezone.utc))
        event_key = event if event in EVENT_SIGNATURES else "GENERAL_MAJOR_EVENT"

        # Only selected event types are eligible for life-state inference.
        # Unknown/generic topics should not become factual claims.
        if event not in PAST_CAPABLE_EVENTS and event_key == "GENERAL_MAJOR_EVENT":
            return LifeStateInference(
                event=event,
                verdict="AMBIGUOUS",
                confidence=0.30,
                strongest_past_window=None,
                strongest_future_window=None,
                past_score=0.0,
                future_score=0.0,
                margin=0.0,
                internal_note="Event not eligible for deterministic past/future state inference.",
            )

        from app.schemas.ai_chat import TemporalContext, TemporalIntent

        past_start = (now - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")
        past_end = now.strftime("%Y-%m-%d")
        future_start = now.strftime("%Y-%m-%d")
        future_end = (now + timedelta(days=365 * years_forward)).strftime("%Y-%m-%d")

        past_ctx = TemporalContext(
            intent=TemporalIntent.PAST,
            start_date=past_start,
            end_date=past_end,
            target_date=None,
        )
        future_ctx = TemporalContext(
            intent=TemporalIntent.FUTURE,
            start_date=future_start,
            end_date=future_end,
            target_date=None,
        )

        past_windows = await self.temporal_scanner.scan_range(canonical_natal, past_ctx, event_key)
        future_windows = await self.temporal_scanner.scan_range(canonical_natal, future_ctx, event_key)

        # Temporal scanner scores are already event-specific. Use best non-overlapping window.
        best_past = max(past_windows, key=lambda w: w.evidence_score, default=None)
        best_future = max(future_windows, key=lambda w: w.evidence_score, default=None)

        past_score = float(best_past.evidence_score) if best_past else 0.0
        future_score = float(best_future.evidence_score) if best_future else 0.0

        # Optional Phase-3 fine timing corroboration lifts only already-strong windows.
        try:
            if best_past and past_score >= 50:
                p_start = datetime.fromisoformat(best_past.start_date).replace(tzinfo=timezone.utc)
                p_end = datetime.fromisoformat(best_past.end_date).replace(tzinfo=timezone.utc)
                ranked = await self.fine_timing.rank_windows(
                    canonical_natal, vedic_chart, event_key, p_start, p_end, limit=1
                )
                if ranked:
                    past_score = min(95.0, past_score + max(0.0, ranked[0].score - 50.0) * 0.15)
            if best_future and future_score >= 50:
                f_start = datetime.fromisoformat(best_future.start_date).replace(tzinfo=timezone.utc)
                f_end = datetime.fromisoformat(best_future.end_date).replace(tzinfo=timezone.utc)
                ranked = await self.fine_timing.rank_windows(
                    canonical_natal, vedic_chart, event_key, f_start, f_end, limit=1
                )
                if ranked:
                    future_score = min(95.0, future_score + max(0.0, ranked[0].score - 50.0) * 0.15)
        except Exception:
            pass

        margin = past_score - future_score

        # Conservative decision thresholds:
        # - never infer "already happened" from a narrow lead
        # - future also needs a real lead
        if past_score >= 68 and margin >= 12:
            verdict = "PAST_EVENT_STRONG"
            confidence = min(0.92, 0.60 + (past_score - 60.0) / 100.0 + margin / 200.0)
        elif future_score >= 68 and margin <= -12:
            verdict = "FUTURE_EVENT_STRONG"
            confidence = min(0.92, 0.60 + (future_score - 60.0) / 100.0 + (-margin) / 200.0)
        else:
            verdict = "AMBIGUOUS"
            confidence = 0.45 if max(past_score, future_score) < 60 else 0.58

        past_obj = None
        if best_past:
            past_obj = EventWindowScore(
                start_date=best_past.start_date,
                end_date=best_past.end_date,
                score=round(past_score, 1),
                phase="PAST",
                strength=self._strength(past_score),
            )
        future_obj = None
        if best_future:
            future_obj = EventWindowScore(
                start_date=best_future.start_date,
                end_date=best_future.end_date,
                score=round(future_score, 1),
                phase="FUTURE",
                strength=self._strength(future_score),
            )

        return LifeStateInference(
            event=event,
            verdict=verdict,
            confidence=round(confidence, 2),
            strongest_past_window=past_obj,
            strongest_future_window=future_obj,
            past_score=round(past_score, 1),
            future_score=round(future_score, 1),
            margin=round(margin, 1),
            internal_note=(
                "This is astrological event-state inference, not verified civil-status data. "
                "Customer wording must reflect confidence."
            ),
        )
