"""Marriage Event Engine V2.

Dedicated deterministic engine for First Marriage analysis.
Separates Natal Promise, Event Occurrence, and Timing using a consensus-based
multi-system evaluation (D1, D9, KP, Dasha, Gochar, AV, SB).
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

from app.services.astrology.event_signatures import EVENT_SIGNATURES
from app.services.astrology.dasha_engine import DashaEngine
from app.services.astrology.gochar_engine import GocharEngine
from app.services.astrology.kp_engine import KPEngine
from app.services.astrology.vedic_engine import VedicEngine
from app.schemas.canonical_astrology import CanonicalAstrologyResult

@dataclass
class MarriageCandidate:
    start_date: str
    end_date: str
    age: float
    md: str
    ad: str
    pd: str

    # System Scores (0-10)
    d1_score: float = 0.0
    d9_score: float = 0.0
    kp_score: float = 0.0
    dasha_activation: float = 0.0
    historical_transit: float = 0.0
    av_support: float = 0.0
    sb_support: float = 0.0
    rahu_ketu_trigger: bool = False

    consensus_count: int = 0
    total_weighted_score: float = 0.0
    is_plausible: bool = False

    def to_dict(self): return asdict(self)

class MarriageEventEngineV2:
    def __init__(self):
        self.dasha_engine = DashaEngine()
        self.gochar_engine = GocharEngine()
        self.kp_engine = KPEngine()
        self.vedic_engine = VedicEngine()

    def _evaluate_static_natal(self, vedic: Any, signature: Any) -> Dict[str, float]:
        # D1 Analysis
        lords = [h for h in vedic.house_lordships if h.house_number in [7, 2, 11]]
        d1_promise = sum(2.0 for h in lords if str(h.lord_dignity).split(".")[-1] not in {"DEBILITATED", "ENEMY"})

        # D9 Analysis
        d9 = vedic.vargas.get("D9")
        d9_promise = 0.0
        if d9:
            d9_promise += sum(2.5 for p in ["Venus", "Jupiter"] if d9.planet_houses.get(p) in [7, 1, 5, 9, 11])

        # AV / SB
        av_score = 0.0
        if vedic.ashtakavarga:
            vals = [vedic.ashtakavarga.sarvashtakavarga_by_house.get(str(h), 0) for h in [7, 2, 11]]
            avg_av = sum(vals)/len(vals) if vals else 0
            av_score = min(10.0, max(0.0, (avg_av - 20) * 0.8))

        sb_score = 0.0
        if vedic.shadbala:
            vals = [x.normalized_score for x in vedic.shadbala.planets if x.planet in ["Venus", "Jupiter"]]
            avg_sb = sum(vals)/len(vals) if vals else 0
            sb_score = min(10.0, avg_sb / 10.0)

        return {"d1": d1_promise, "d9": d9_promise, "av": av_score, "sb": sb_score}

    async def analyze_first_marriage(self, canonical_natal: CanonicalAstrologyResult) -> Dict[str, Any]:
        signature = EVENT_SIGNATURES["FIRST_MARRIAGE"]
        vedic = self.vedic_engine.calculate_vedic_chart(canonical_natal)
        kp_res = self.kp_engine.calculate_kp(canonical_natal)

        static = self._evaluate_static_natal(vedic, signature)

        # Birth and Scan range
        birth_dt = datetime.fromisoformat(canonical_natal.birth.utc_instant.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)

        # Scan from age 18 to current age + 10 years
        scan_start = birth_dt + timedelta(days=365.25 * 18)
        scan_end = now + timedelta(days=365.25 * 10)

        moon_lon = next(p for p in canonical_natal.planets if p.body == "Moon").sidereal_longitude
        periods = self.dasha_engine.get_periods_in_range(moon_lon, birth_dt, scan_start, scan_end, max_level=3)

        candidates: List[MarriageCandidate] = []
        planet_sig_map = {ps.planet: set(ps.all_signified_houses) for ps in kp_res.planet_significators}

        # Filter for PD level candidates
        pd_periods = [p for p in periods if p[3] == 3]

        for lord, p_start, p_end, level, parents in pd_periods:
            md, ad = parents[0], parents[1]
            midpoint = p_start + (p_end - p_start) / 2
            age = (midpoint - birth_dt).days / 365.25

            # KP Score (0-10)
            kp_houses = {7, 2, 11}
            kp_points = 0
            for l in [md, ad, lord]:
                sig = planet_sig_map.get(l, set())
                kp_points += len(sig.intersection(kp_houses))
            kp_score = min(10.0, kp_points * 1.5)

            # Dasha Activation
            dasha_score = 0.0
            if md in ["Venus", "Jupiter"] or any(h in planet_sig_map.get(md,set()) for h in [7]): dasha_score += 3
            if ad in ["Venus", "Jupiter"] or any(h in planet_sig_map.get(ad,set()) for h in [7]): dasha_score += 4
            if lord in ["Venus", "Jupiter"] or any(h in planet_sig_map.get(lord,set()) for h in [7]): dasha_score += 3

            # Historical Transit
            t_score = 0.0
            rk_trigger = False
            try:
                gochar = self.gochar_engine.calculate_gochar_snapshot(canonical_natal, midpoint)
                for t in gochar.transits:
                    if t.body in ["Jupiter", "Venus"]:
                        if t.house_from_d1_lagna in [7, 1, 5, 9, 11]: t_score += 3.0
                    if t.body in ["Rahu", "Ketu"]:
                        if t.house_from_d1_lagna in [7, 1, 2]: rk_trigger = True
            except: pass

            cand = MarriageCandidate(
                start_date=p_start.strftime("%Y-%m-%d"),
                end_date=p_end.strftime("%Y-%m-%d"),
                age=round(age, 1),
                md=md, ad=ad, pd=lord,
                d1_score=static["d1"],
                d9_score=static["d9"],
                kp_score=kp_score,
                dasha_activation=dasha_score,
                historical_transit=min(10.0, t_score),
                av_support=static["av"],
                sb_support=static["sb"],
                rahu_ketu_trigger=rk_trigger
            )

            # Consensus Logic
            c = 0
            if cand.d1_score >= 4: c += 1
            if cand.d9_score >= 2.5: c += 1
            if cand.kp_score >= 5: c += 1
            if cand.dasha_activation >= 6: c += 1
            if cand.historical_transit >= 3: c += 1
            if cand.rahu_ketu_trigger: c += 1

            cand.consensus_count = c
            cand.total_weighted_score = (
                cand.d1_score * 1.0 + cand.d9_score * 1.2 +
                cand.kp_score * 1.5 + cand.dasha_activation * 1.3 +
                cand.historical_transit * 1.0 + (5.0 if cand.rahu_ketu_trigger else 0.0)
            )

            if cand.consensus_count >= 3 and cand.total_weighted_score > 25:
                cand.is_plausible = True

            candidates.append(cand)

        # Print Table for debugging
        past_candidates = [c for c in candidates if datetime.fromisoformat(c.start_date).replace(tzinfo=timezone.utc) < now and c.is_plausible]
        past_candidates.sort(key=lambda x: x.total_weighted_score, reverse=True)

        print("\n" + "="*120)
        print(f"{'Period':<22} | {'Age':<4} | {'D1':<3} | {'D9':<3} | {'KP':<3} | {'MD':<3} | {'AD':<3} | {'PD':<3} | {'Transit':<7} | {'AV':<3} | {'SB':<3} | {'RK':<2} | {'Consensus'}")
        print("-" * 120)
        for c in past_candidates[:10]:
            rk = "Y" if c.rahu_ketu_trigger else "N"
            print(f"{c.start_date[:10]+'/'+c.end_date[:10]:<22} | {c.age:<4} | {c.d1_score:<3.1f} | {c.d9_score:<3.1f} | {c.kp_score:<3.1f} | {c.md[:3]:<3} | {c.ad[:3]:<3} | {c.pd[:3]:<3} | {c.historical_transit:<7.1f} | {c.av_support:<3.1f} | {c.sb_support:<3.1f} | {rk:<2} | {c.consensus_count}")
        print("="*120 + "\n")

        # Verdict
        best_past = past_candidates[0] if past_candidates else None
        future_candidates = [c for c in candidates if datetime.fromisoformat(c.start_date).replace(tzinfo=timezone.utc) >= now and c.is_plausible]
        future_candidates.sort(key=lambda x: x.total_weighted_score, reverse=True)
        best_future = future_candidates[0] if future_candidates else None

        verdict = "AMBIGUOUS"
        if best_past and best_past.total_weighted_score >= 35:
            verdict = "PAST_EVENT_STRONG"
        elif best_future and best_future.total_weighted_score >= 35:
            verdict = "FUTURE_EVENT_STRONG"

        return {
            "verdict": verdict,
            "best_past": best_past.to_dict() if best_past else None,
            "best_future": best_future.to_dict() if best_future else None,
            "all_plausible_past": [c.to_dict() for c in past_candidates],
            "all_plausible_future": [c.to_dict() for c in future_candidates]
        }
