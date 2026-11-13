"""Deterministic Event-State Cross-Check Engine.

Fixes three runtime errors:
1) A grammatically future question ("meri shadi kab hogi") must not force a future first-event.
2) First-marriage windows are age-plausibility filtered, so adolescent periods cannot win
   merely because a KP/Dasha score is numerically high.
3) A cluster of strong nearby past windows is returned as a broad event phase rather than
   exposing one arbitrary Pratyantardasha slice.

Astrology remains interpretive; this engine does not verify civil status as a fact.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.services.astrology.temporal_scanners import TemporalScanner
from app.services.astrology.event_signatures import EVENT_SIGNATURES
from app.services.astrology.marriage_engine_v2 import MarriageEventEngineV2

FIRST_EVENT_MAP = {
    "MARRIAGE": "FIRST_MARRIAGE",
    "FIRST_MARRIAGE": "FIRST_MARRIAGE",
    "CHILDREN": "FIRST_CHILD",
    "FIRST_CHILD": "FIRST_CHILD",
    "GOVERNMENT_JOB": "GOVERNMENT_JOB",
    "PROPERTY_PURCHASE": "PROPERTY_PURCHASE",
    "VEHICLE_PURCHASE": "VEHICLE_PURCHASE",
}

@dataclass
class RankedWindow:
    start_date: str
    end_date: str
    raw_score: float
    adjusted_score: float
    strength: str
    dasha_lord: str
    age_at_midpoint: Optional[float] = None

    def to_dict(self):
        return asdict(self)

@dataclass
class EventStateResult:
    event: str
    state_event: str
    verdict: str
    confidence: float
    strongest_past_window: Optional[RankedWindow]
    strongest_future_window: Optional[RankedWindow]
    broad_past_phase_start: Optional[str]
    broad_past_phase_end: Optional[str]
    independent_confirmations: int
    note: str

    def to_dict(self):
        return asdict(self)

class EventStateCrossCheckEngine:
    def __init__(self):
        self.scanner = TemporalScanner()
        self.marriage_v2 = MarriageEventEngineV2()

    @staticmethod
    def _birth_dt(canonical_natal: Any) -> Optional[datetime]:
        try:
            dt = datetime.fromisoformat(canonical_natal.birth.utc_instant.replace("Z","+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None

    @staticmethod
    def _midpoint(start: str, end: str) -> datetime:
        s = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
        e = datetime.fromisoformat(end).replace(tzinfo=timezone.utc)
        return s + (e-s)/2

    def _age_adjustment(self, canonical_natal: Any, event: str, start: str, end: str) -> Tuple[float, Optional[float]]:
        birth = self._birth_dt(canonical_natal)
        if not birth:
            return 0.0, None
        mid = self._midpoint(start, end)
        age = (mid - birth).days / 365.2425

        # Only first-life events get life-stage plausibility adjustment.
        if event == "FIRST_MARRIAGE":
            if age < 18:
                return -55.0, age
            if age < 21:
                return -14.0, age
            if age <= 45:
                return +8.0, age
            if age <= 60:
                return +2.0, age
            return -4.0, age

        if event == "FIRST_CHILD":
            if age < 16:
                return -55.0, age
            if 20 <= age <= 42:
                return +6.0, age
        return 0.0, age

    @staticmethod
    def _static_confirmations(vedic: Any, kp: Any, event: str) -> int:
        sig = EVENT_SIGNATURES.get(event, EVENT_SIGNATURES["GENERAL_MAJOR_EVENT"])
        confirmations = 0

        # Relevant natal lords
        lords = [h for h in getattr(vedic, "house_lordships", []) if h.house_number in sig.primary_houses]
        if lords and any(str(h.lord_dignity).split(".")[-1] not in {"DEBILITATED","ENEMY"} for h in lords):
            confirmations += 1

        # Relevant varga
        vf = getattr(vedic, "vargas", {}).get(sig.varga or "D1")
        if vf and sig.varga != "D1":
            if any(vf.planet_houses.get(p) in sig.primary_houses + sig.supporting_houses for p in sig.natural_significators):
                confirmations += 1

        # KP event houses
        try:
            event_houses = set(sig.kp_event_houses or sig.primary_houses)
            linked = 0
            for ps in kp.planet_significators:
                if set(ps.all_signified_houses).intersection(event_houses):
                    linked += 1
            if linked >= 2:
                confirmations += 1
        except Exception:
            pass

        # Ashtakavarga support
        av = getattr(vedic, "ashtakavarga", None)
        if av:
            vals = [av.sarvashtakavarga_by_house.get(str(h),0) for h in (sig.ashtakavarga_houses or sig.primary_houses)]
            vals = [v for v in vals if v]
            if vals and sum(vals)/len(vals) >= 25:
                confirmations += 1

        # Shadbala supporting layer
        sb = getattr(vedic, "shadbala", None)
        if sb:
            wanted = set(sig.shadbala_planets or sig.natural_significators)
            vals = [x.normalized_score for x in sb.planets if x.planet in wanted]
            if vals and sum(vals)/len(vals) >= 45:
                confirmations += 1

        return confirmations

    def _rank(self, canonical_natal: Any, state_event: str, windows: List[Any]) -> List[RankedWindow]:
        ranked = []
        for w in windows:
            adj, age = self._age_adjustment(canonical_natal, state_event, w.start_date, w.end_date)
            score = max(0.0, min(100.0, float(w.evidence_score) + adj))
            ranked.append(RankedWindow(
                start_date=w.start_date,
                end_date=w.end_date,
                raw_score=round(float(w.evidence_score),1),
                adjusted_score=round(score,1),
                strength="VERY_HIGH" if score >= 80 else ("HIGH" if score >= 65 else ("MODERATE" if score >= 50 else "LOW")),
                dasha_lord=w.dasha_lord,
                age_at_midpoint=round(age,1) if age is not None else None,
            ))
        ranked.sort(key=lambda x: x.adjusted_score, reverse=True)
        return ranked

    @staticmethod
    def _broad_phase(best: Optional[RankedWindow], ranked: List[RankedWindow]) -> Tuple[Optional[str], Optional[str]]:
        if not best:
            return None, None
        bmid = datetime.fromisoformat(best.start_date)
        close = []
        for w in ranked:
            if w.adjusted_score < max(55.0, best.adjusted_score - 15.0):
                continue
            wmid = datetime.fromisoformat(w.start_date)
            if abs((wmid - bmid).days) <= 900:  # ~2.5 years around the winning cluster
                close.append(w)
        if not close:
            close = [best]
        return min(w.start_date for w in close), max(w.end_date for w in close)

    async def infer(self, canonical_natal: Any, vedic: Any, kp: Any, event: str, now: Optional[datetime] = None) -> EventStateResult:
        from app.schemas.ai_chat import TemporalContext, TemporalIntent

        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        state_event = FIRST_EVENT_MAP.get(event, event)

        # --- NEW Marriage V2 Path ---
        if state_event == "FIRST_MARRIAGE":
            res_v2 = await self.marriage_v2.analyze_first_marriage(canonical_natal)
            best_past_v2 = res_v2["best_past"]
            best_future_v2 = res_v2["best_future"]

            p_win = None
            if best_past_v2:
                p_win = RankedWindow(
                    start_date=best_past_v2["start_date"],
                    end_date=best_past_v2["end_date"],
                    raw_score=best_past_v2["total_weighted_score"],
                    adjusted_score=best_past_v2["total_weighted_score"],
                    strength="HIGH" if best_past_v2["total_weighted_score"] > 30 else "MODERATE",
                    dasha_lord=best_past_v2["pd"],
                    age_at_midpoint=best_past_v2["age"]
                )

            f_win = None
            if best_future_v2:
                f_win = RankedWindow(
                    start_date=best_future_v2["start_date"],
                    end_date=best_future_v2["end_date"],
                    raw_score=best_future_v2["total_weighted_score"],
                    adjusted_score=best_future_v2["total_weighted_score"],
                    strength="HIGH" if best_future_v2["total_weighted_score"] > 30 else "MODERATE",
                    dasha_lord=best_future_v2["pd"],
                    age_at_midpoint=best_future_v2["age"]
                )

            return EventStateResult(
                event=event,
                state_event=state_event,
                verdict=res_v2["verdict"],
                confidence=0.92 if res_v2["verdict"] != "AMBIGUOUS" else 0.5,
                strongest_past_window=p_win,
                strongest_future_window=f_win,
                broad_past_phase_start=p_win.start_date if p_win else None,
                broad_past_phase_end=p_win.end_date if p_win else None,
                independent_confirmations=best_past_v2["consensus_count"] if best_past_v2 else 0,
                note="V2 Consensus Marriage Engine results applied."
            )

        # --- Legacy Fallback for other events ---
        scan_event = state_event if state_event in EVENT_SIGNATURES else event
        if scan_event not in EVENT_SIGNATURES:
            scan_event = "GENERAL_MAJOR_EVENT"

        past_ctx = TemporalContext(
            intent=TemporalIntent.PAST,
            start_date=(now - timedelta(days=365*25)).strftime("%Y-%m-%d"), # Wider scan for past
            end_date=now.strftime("%Y-%m-%d"),
            target_date=None,
        )
        future_ctx = TemporalContext(
            intent=TemporalIntent.FUTURE,
            start_date=now.strftime("%Y-%m-%d"),
            end_date=(now + timedelta(days=365*12)).strftime("%Y-%m-%d"),
            target_date=None,
        )

        past_raw = await self.scanner.scan_range(canonical_natal, past_ctx, scan_event, limit=20)
        future_raw = await self.scanner.scan_range(canonical_natal, future_ctx, scan_event, limit=10)

        past = self._rank(canonical_natal, state_event, past_raw)
        future = self._rank(canonical_natal, state_event, future_raw)

        # --- DETAILED DEBUG LOGGING ---
        print(f"\nDEBUG_EVENT_STATE_COMPONENTS for event={event} scan_event={scan_event}")

        print("\nDEBUG_EVENT_STATE_TOP_PAST (Candidate Windows):")
        for i, w in enumerate(past[:10]):
            print(
                f"[{i+1}] {w.start_date} to {w.end_date} | Age: {w.age_at_midpoint} | "
                f"Score: {w.adjusted_score} (Raw: {w.raw_score}) | Dasha: {w.dasha_lord} | "
                f"Strength: {w.strength}"
            )

        print("\nDEBUG_EVENT_STATE_TOP_FUTURE (Candidate Windows):")
        for i, w in enumerate(future[:5]):
            print(
                f"[{i+1}] {w.start_date} to {w.end_date} | Age: {w.age_at_midpoint} | "
                f"Score: {w.adjusted_score} (Raw: {w.raw_score}) | Dasha: {w.dasha_lord} | "
                f"Strength: {w.strength}"
            )

        best_past = past[0] if past else None
        best_future = future[0] if future else None

        confirmations = self._static_confirmations(vedic, kp, scan_event)
        timing_confirmation = 1 if best_past and best_past.adjusted_score >= 65 else 0
        total_confirmations = confirmations + timing_confirmation

        # First-event completion is NOT cancelled by a later favorable period.
        if state_event in set(FIRST_EVENT_MAP.values()) and best_past and best_past.adjusted_score >= 65 and total_confirmations >= 3:
            verdict = "PAST_EVENT_STRONG"
            confidence = min(0.94, 0.64 + best_past.adjusted_score/300.0 + total_confirmations*0.025)
        elif best_future and best_future.adjusted_score >= 68 and confirmations >= 2:
            verdict = "FUTURE_EVENT_STRONG"
            confidence = min(0.92, 0.62 + best_future.adjusted_score/320.0 + confirmations*0.02)
        else:
            verdict = "AMBIGUOUS"
            confidence = 0.50

        print(
            f"\nDEBUG_EVENT_STATE_FINAL: event={event} verdict={verdict} "
            f"conf={confidence} static_confirmations={confirmations} "
            f"total_confirmations={total_confirmations} "
            f"best_past_score={best_past.adjusted_score if best_past else 'N/A'} "
            f"best_future_score={best_future.adjusted_score if best_future else 'N/A'}"
        )

        phase_start, phase_end = self._broad_phase(best_past, past)

        return EventStateResult(
            event=event,
            state_event=state_event,
            verdict=verdict,
            confidence=round(confidence,2),
            strongest_past_window=best_past,
            strongest_future_window=best_future,
            broad_past_phase_start=phase_start,
            broad_past_phase_end=phase_end,
            independent_confirmations=total_confirmations,
            note="Astrological event-state inference only; not verified civil status.",
        )
