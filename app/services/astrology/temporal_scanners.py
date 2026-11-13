"""Temporal Scanners for Historical and Future Astrology Analysis.

Provides scanners that analyze a date range to identify and rank astrological windows
based on Dasha, Gochar, and Natal event signatures.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

from app.schemas.ai_chat import TemporalContext, EventWindow, TemporalIntent
from app.schemas.canonical_astrology import CanonicalAstrologyResult
from app.services.astrology.dasha_engine import DashaEngine
from app.services.astrology.gochar_engine import GocharEngine
from app.services.astrology.vedic_engine import VedicEngine
from app.services.astrology.kp_engine import KPEngine
from app.services.astrology.event_signatures import EVENT_SIGNATURES, EventSignature

class TemporalScanner:
    """Core engine for scanning past and future astrological windows."""

    def __init__(
        self,
        dasha_engine: Optional[DashaEngine] = None,
        gochar_engine: Optional[GocharEngine] = None,
        vedic_engine: Optional[VedicEngine] = None,
        kp_engine: Optional[KPEngine] = None
    ):
        self.dasha_engine = dasha_engine or DashaEngine()
        self.gochar_engine = gochar_engine or GocharEngine()
        self.vedic_engine = vedic_engine or VedicEngine()
        self.kp_engine = kp_engine or KPEngine()

    async def scan_range(
        self,
        canonical_natal: CanonicalAstrologyResult,
        context: TemporalContext,
        topic: str,
        limit: int = 4,
        allowed_levels: Optional[set] = None
    ) -> List[EventWindow]:
        """Scans a date range for a specific topic signature and returns ranked windows."""

        signature = EVENT_SIGNATURES.get(topic, EVENT_SIGNATURES["GENERAL_MAJOR_EVENT"])

        # Ensure UTC awareness
        if not context.start_date or not context.end_date:
            return []

        start_dt = datetime.fromisoformat(context.start_date.replace("Z", "+00:00"))
        if start_dt.tzinfo is None: start_dt = start_dt.replace(tzinfo=timezone.utc)

        end_dt = datetime.fromisoformat(context.end_date.replace("Z", "+00:00"))
        if end_dt.tzinfo is None: end_dt = end_dt.replace(tzinfo=timezone.utc)

        # 1. Get overlapping Mahadashas and Antardashas
        moon_lon = next(p for p in canonical_natal.planets if p.body == "Moon").sidereal_longitude
        birth_utc = datetime.fromisoformat(canonical_natal.birth.utc_instant.replace("Z", "+00:00"))
        if birth_utc.tzinfo is None: birth_utc = birth_utc.replace(tzinfo=timezone.utc)

        # Use canonical engine for overlapping periods
        overlapping_periods = self.dasha_engine.get_periods_in_range(
            moon_longitude=moon_lon,
            birth_datetime_utc=birth_utc,
            start_dt=start_dt,
            end_dt=end_dt,
            max_level=3
        )

        # 2. Pre-calculate Static Components (Natal Promise, D9, AV, Shadbala)
        vedic_chart = self.vedic_engine.calculate_vedic_chart(canonical_natal)
        kp_res = self.kp_engine.calculate_kp(canonical_natal)

        static_score = 30.0 # Base

        # Natal Promise
        lords = [h for h in vedic_chart.house_lordships if h.house_number in signature.primary_houses]
        good_lords = sum(1 for h in lords if str(h.lord_dignity).split(".")[-1] not in {"DEBILITATED", "ENEMY"})
        static_score += min(15.0, good_lords * 5.0)

        # Natural Significators
        for p in vedic_chart.planets:
            if p.body in signature.natural_significators:
                if str(p.dignity).split(".")[-1] not in {"DEBILITATED", "ENEMY"}:
                    static_score += 3.0

        # D9 Varga support (Static natal promise layer)
        d9 = vedic_chart.vargas.get("D9")
        if d9 and topic in {"MARRIAGE", "FIRST_MARRIAGE", "RELATIONSHIP"}:
            d9_sig_in_houses = sum(1 for p in signature.natural_significators if d9.planet_houses.get(p) in signature.primary_houses + signature.supporting_houses)
            static_score += min(10.0, d9_sig_in_houses * 5.0)

        # Ashtakavarga support (Static)
        av = vedic_chart.ashtakavarga
        if av:
            av_houses = signature.ashtakavarga_houses or signature.primary_houses
            vals = [av.sarvashtakavarga_by_house.get(str(h), 0) for h in av_houses]
            if vals:
                avg_av = sum(vals) / len(vals)
                if avg_av >= 28: static_score += 8.0
                elif avg_av >= 25: static_score += 4.0
                elif avg_av < 22: static_score -= 5.0

        # Shadbala support (Static)
        sb = vedic_chart.shadbala
        if sb:
            wanted = set(signature.shadbala_planets or signature.natural_significators)
            vals = [x.normalized_score for x in sb.planets if x.planet in wanted]
            if vals:
                avg_sb = sum(vals) / len(vals)
                if avg_sb >= 60: static_score += 7.0
                elif avg_sb >= 45: static_score += 3.0
                elif avg_sb < 30: static_score -= 4.0

        # Evaluate and Rank Windows
        windows: List[EventWindow] = []
        planet_sig_map = {ps.planet: ps.all_signified_houses for ps in kp_res.planet_significators}

        for lord, p_start, p_end, level, parents in overlapping_periods:
            if allowed_levels is not None and level not in allowed_levels:
                continue

            # Start with static score
            score = static_score

            # Dasha & KP activation (Dynamic for the period)
            hierarchy = parents + [lord]
            weights = {1: 0.45, 2: 0.75, 3: 1.0}

            kp_score_inc = 0.0
            for idx, l_name in enumerate(hierarchy, start=1):
                signifies = planet_sig_map.get(l_name, [])
                weight = weights.get(idx, 1.0)

                # Primary linkage
                kp_score_inc += len([h for h in signifies if h in signature.primary_houses]) * 12.0 * weight
                # Supporting linkage
                kp_score_inc += len([h for h in signifies if h in signature.supporting_houses]) * 4.0 * weight
                # Negative linkage
                kp_score_inc -= len([h for h in signifies if h in signature.unfavorable_houses]) * 10.0 * weight

            score += kp_score_inc
            score = max(10.0, min(95.0, score))

            if (level == 3 and score >= 45.0) or (level == 2 and score >= 55.0):
                window_start = max(start_dt, p_start)
                window_end = min(end_dt, p_end)

                # 3. Historical Gochar trigger (Dynamic for historical window)
                transit_indicators = []
                if (window_end - window_start).days < 400 and len(windows) < 15:
                    try:
                        # Use midpoint of window for historical transit evaluation
                        eval_dt = window_start + (window_end - window_start) / 2
                        gochar_res = self.gochar_engine.calculate_gochar_snapshot(canonical_natal, eval_dt)

                        t_score = 0.0
                        for tp in gochar_res.transits:
                            if tp.body in ["Jupiter", "Saturn", "Rahu", "Ketu"] or tp.body in signature.natural_significators:
                                if tp.house_from_d1_lagna in signature.primary_houses:
                                    t_score += 6.0
                                    transit_indicators.append(f"{tp.body} in H-{tp.house_from_d1_lagna}")
                                elif tp.house_from_moon in signature.primary_houses:
                                    t_score += 4.0
                                    transit_indicators.append(f"{tp.body} in Moon-H-{tp.house_from_moon}")
                        score += min(15.0, t_score)
                    except Exception:
                        pass

                score = min(100.0, score)
                strength = "LOW"
                if score >= 80: strength = "VERY_HIGH"
                elif score >= 65: strength = "HIGH"
                elif score >= 50: strength = "MODERATE"

                windows.append(EventWindow(
                    event_type=topic,
                    start_date=window_start.strftime("%Y-%m-%d"),
                    end_date=window_end.strftime("%Y-%m-%d"),
                    evidence_score=score,
                    evidence_strength=strength,
                    summary=f"Significant {lord} influence active in this period for {topic}.",
                    dasha_lord=lord,
                    transit_indicators=transit_indicators
                ))

        # 4. Deduplicate and Pick Top
        windows.sort(key=lambda x: x.evidence_score, reverse=True)
        final_windows = []
        for w in windows:
            if not any(self._is_overlapping(w, fw) for fw in final_windows):
                final_windows.append(w)
            if len(final_windows) >= max(1, limit): break
        return final_windows

    async def time_travel_scan(
        self,
        canonical_natal: CanonicalAstrologyResult,
        target_datetime_utc: datetime,
        topic: str = "GENERAL"
    ) -> Dict[str, Any]:
        """Scans arbitrary past/future date for 5-level Dasha + Transit snapshot & event activation score."""
        signature = EVENT_SIGNATURES.get(topic, EVENT_SIGNATURES["GENERAL_MAJOR_EVENT"])

        # 1. Active Dasha Hierarchy at target_datetime_utc
        moon_lon = next(p for p in canonical_natal.planets if p.body == "Moon").sidereal_longitude
        birth_utc = datetime.fromisoformat(canonical_natal.birth.utc_instant.replace("Z", "+00:00"))
        if birth_utc.tzinfo is None: birth_utc = birth_utc.replace(tzinfo=timezone.utc)
        if target_datetime_utc.tzinfo is None: target_datetime_utc = target_datetime_utc.replace(tzinfo=timezone.utc)

        dasha_hierarchy = self.dasha_engine.calculate_dasha_hierarchy(
            moon_longitude=moon_lon,
            birth_datetime_utc=birth_utc,
            target_datetime_utc=target_datetime_utc,
            max_depth=5
        )

        active_chain = [d.lord for d in dasha_hierarchy.active_chain]

        # 2. Gochar Transits at target_datetime_utc
        gochar_res = self.gochar_engine.calculate_gochar_snapshot(canonical_natal, target_datetime_utc)
        transits_str = [f"{t.body} in {t.rashi_name} (H-{t.house_from_d1_lagna})" for t in gochar_res.transits[:6]]

        # 3. Calculate activation score for the topic
        kp_res = self.kp_engine.calculate_kp(canonical_natal)
        planet_sig_map = {ps.planet: ps.all_signified_houses for ps in kp_res.planet_significators}

        score = 40.0
        weights = [1.0, 0.8, 0.6, 0.4, 0.2]
        for idx, lord_name in enumerate(active_chain[:5]):
            signifies = planet_sig_map.get(lord_name, [])
            w = weights[idx]
            score += len([h for h in signifies if h in signature.primary_houses]) * 10.0 * w
            score += len([h for h in signifies if h in signature.supporting_houses]) * 3.0 * w
            score -= len([h for h in signifies if h in signature.unfavorable_houses]) * 7.0 * w

        for tp in gochar_res.transits:
            if tp.body in ["Jupiter", "Saturn", "Rahu", "Ketu"] or tp.body in signature.natural_significators:
                if tp.house_from_d1_lagna in signature.primary_houses:
                    score += 5.0

        score = max(5.0, min(95.0, round(score, 1)))

        strength = "LOW"
        if score >= 80: strength = "VERY_HIGH"
        elif score >= 65: strength = "HIGH"
        elif score >= 50: strength = "MODERATE"

        date_str = target_datetime_utc.strftime("%d-%m-%Y")

        return {
            "target_date_utc": target_datetime_utc.isoformat(),
            "target_date_display": date_str,
            "topic": topic,
            "active_dasha_chain": active_chain,
            "key_transits": transits_str,
            "timing_score": score,
            "evidence_strength": strength,
            "summary_hindi": f"{date_str} को {topic} विषय के लिए ग्रह स्थिति {strength} ({score} अंक) दर्शाती है। सक्रिय दशा: {' -> '.join(active_chain[:3])}।",
            "summary_english": f"On {date_str}, planetary alignment shows {strength} ({score} score) for {topic}. Active Dasha: {' -> '.join(active_chain[:3])}."
        }


    async def scan_major_events(
        self,
        canonical_natal: CanonicalAstrologyResult,
        context: TemporalContext
    ) -> List[EventWindow]:
        """Scans multiple domains to find the most significant life event windows."""
        domains = ["CAREER", "MARRIAGE", "RELATIONSHIP", "TRAVEL", "WEALTH", "HEALTH"]
        all_windows = []
        for domain in domains:
            domain_windows = await self.scan_range(canonical_natal, context, domain)
            all_windows.extend(domain_windows)

        all_windows.sort(key=lambda x: x.evidence_score, reverse=True)
        unique_windows = []
        for w in all_windows:
            if not any(self._is_overlapping(w, uw) for uw in unique_windows):
                unique_windows.append(w)
            if len(unique_windows) >= 5: break
        return unique_windows

    def _is_overlapping(self, w1: EventWindow, w2: EventWindow) -> bool:
        s1 = datetime.strptime(w1.start_date, "%Y-%m-%d")
        e1 = datetime.strptime(w1.end_date, "%Y-%m-%d")
        s2 = datetime.strptime(w2.start_date, "%Y-%m-%d")
        e2 = datetime.strptime(w2.end_date, "%Y-%m-%d")
        return s1 <= e2 and s2 <= e1
