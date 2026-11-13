"""Topic Timing Window & Evidence Engine.

Synthesizes Dasha, Gochar, Vedic Yogas, and KP House Significators into structured,
deterministic timing evidence for specific query topics (Career, Wealth, Marriage, Health, Travel).
"""

from datetime import datetime, timezone
from typing import List, Dict, Optional
import uuid

from app.schemas.vedic_astrology import VedicChartResult
from app.schemas.kp_astrology import KPChartResult
from app.schemas.dasha_gochar_yoga import (
    DashaHierarchyResult,
    GocharResult,
    YogaResult,
    TimingWindowEvidenceResult
)

from app.services.astrology.event_signatures import EVENT_SIGNATURES
from app.services.astrology.prediction_rule_engine import PredictionRuleEngine

_rule_engine = PredictionRuleEngine()

class TimingEngine:
    """Deterministic Topic & Time-Intent Routing Engine."""

    def evaluate_timing_evidence(
        self,
        topic: str,
        target_datetime_utc: datetime,
        vedic_chart: VedicChartResult,
        kp_chart: KPChartResult,
        dasha_result: DashaHierarchyResult,
        gochar_result: GocharResult,
        yoga_result: YogaResult,
        profile_id: str
    ) -> TimingWindowEvidenceResult:
        """Evaluates combined evidence across Dasha, Gochar, Yogas, and KP significators for a topic."""
        topic_upper = topic.upper()
        signature = EVENT_SIGNATURES.get(topic_upper, EVENT_SIGNATURES["GENERAL_MAJOR_EVENT"])

        primary_houses = signature.primary_houses
        unfavorable_houses = signature.unfavorable_houses
        natural_significators = signature.natural_significators

        # 1. Evaluate Dasha Activation
        md_lord = dasha_result.active_chain[0].lord if len(dasha_result.active_chain) > 0 else ""
        ad_lord = dasha_result.active_chain[1].lord if len(dasha_result.active_chain) > 1 else ""
        pd_lord = dasha_result.active_chain[2].lord if len(dasha_result.active_chain) > 2 else ""

        dasha_score = 50.0
        dasha_reasons: List[str] = []

        planet_sig_map = {}
        # Map planet significators
        for ps in kp_chart.planet_significators:
            planet_sig_map[ps.planet] = ps.all_signified_houses

        md_signifies = planet_sig_map.get(md_lord, [])
        ad_signifies = planet_sig_map.get(ad_lord, [])

        md_matches = [h for h in md_signifies if h in primary_houses]
        ad_matches = [h for h in ad_signifies if h in primary_houses]

        md_unfav = [h for h in md_signifies if h in unfavorable_houses]
        ad_unfav = [h for h in ad_signifies if h in unfavorable_houses]

        if md_matches:
            dasha_score += 20.0
            dasha_reasons.append(f"Mahadasha lord {md_lord} signifies primary house(s) {md_matches} via KP.")
        if md_unfav:
            dasha_score -= 10.0
            dasha_reasons.append(f"Mahadasha lord {md_lord} signifies unfavorable house(s) {md_unfav}.")

        if ad_matches:
            dasha_score += 20.0
            dasha_reasons.append(f"Antardasha lord {ad_lord} signifies primary house(s) {ad_matches} via KP.")
        if ad_unfav:
            dasha_score -= 10.0
            dasha_reasons.append(f"Antardasha lord {ad_lord} signifies unfavorable house(s) {ad_unfav}.")

        dasha_favourability = "FAVORABLE" if dasha_score >= 70.0 else ("UNFAVORABLE" if dasha_score < 40.0 else "NEUTRAL")
        dasha_evidence_str = f"Active Dasha Chain: MD-{md_lord} | AD-{ad_lord} | PD-{pd_lord}. " + (" ".join(dasha_reasons) if dasha_reasons else "Dasha lords offer moderate support.")

        # 2. Evaluate Gochar Transits
        transit_score = 50.0
        transit_evidences: List[str] = []

        for t_planet in gochar_result.transits:
            if t_planet.body in natural_significators:
                if t_planet.house_from_d1_lagna in primary_houses:
                    transit_score += 15.0
                    transit_evidences.append(f"{t_planet.body} transiting primary house {t_planet.house_from_d1_lagna} from D1 Lagna.")
                elif t_planet.house_from_moon in primary_houses:
                    transit_score += 10.0
                    transit_evidences.append(f"{t_planet.body} transiting primary house {t_planet.house_from_moon} from Chandra Lagna.")

                if t_planet.house_from_d1_lagna in unfavorable_houses:
                    transit_score -= 10.0
                    transit_evidences.append(f"{t_planet.body} transiting unfavorable house {t_planet.house_from_d1_lagna}.")

        transit_favourability = "FAVORABLE" if transit_score >= 65.0 else "NEUTRAL"

        # 3. Evaluate Yogas
        yoga_evidences: List[str] = []
        yoga_score_add = 0.0
        for y in yoga_result.yogas:
            if y.is_active:
                # Only count yogas relevant to the topic? For now just add general yogas
                yoga_evidences.append(f"{y.name} ({y.name_hindi}): {y.description} [{y.source_reference}]")
                yoga_score_add += 5.0

        # 4. Evaluate KP Significator Alignment
        kp_evidences: List[str] = []
        for h_num in primary_houses:
            for h_sig in kp_chart.house_significators:
                if h_sig.house_number == h_num:
                    comb = h_sig.significators.combined_significators
                    if comb:
                        kp_evidences.append(f"House {h_num} KP Significators: {', '.join(comb)}")

        # 5. Phase-2 deterministic astrologer-style consensus (NO random jitter)
        decision = _rule_engine.evaluate(
            topic_upper, vedic_chart, kp_chart, dasha_result, gochar_result, yoga_result
        )
        overall_score = decision.confidence
        if decision.verdict == "STRONGLY_SUPPORTED":
            evidence_strength = "VERY_HIGH"
        elif decision.verdict == "SUPPORTED":
            evidence_strength = "HIGH"
        elif decision.verdict == "WEAK_OR_DELAYED":
            evidence_strength = "LOW"
        else:
            evidence_strength = "MODERATE"

        label = topic_upper.replace("_", " ").title()
        if evidence_strength == "VERY_HIGH":
            verdict = f"Strong positive indications for {label}."
            favorable_window = f"The current window under {md_lord}-{ad_lord} is strongly supportive."
        elif evidence_strength == "HIGH":
            verdict = f"Favorable indications for {label}."
            favorable_window = f"Active window under {md_lord}-{ad_lord} offers meaningful support."
        elif evidence_strength == "LOW":
            verdict = f"Current indications for {label} are weak or delayed."
            favorable_window = "A later supporting period may be preferable."
        else:
            verdict = f"Mixed indications for {label}; timing needs corroboration."
            favorable_window = "Some support exists, but the current window is not fully confirmed."

        calc_id = f"timing_{uuid.uuid4().hex[:12]}"

        return TimingWindowEvidenceResult(
            calculation_id=calc_id,
            profile_id=profile_id,
            topic=topic_upper,
            target_date_utc=target_datetime_utc.isoformat(),
            active_dasha_chain=[p.lord for p in dasha_result.active_chain],
            dasha_favourability=dasha_favourability,
            dasha_evidence=dasha_evidence_str,
            transit_favourability=transit_favourability,
            transit_evidence=transit_evidences,
            yoga_evidence=yoga_evidences,
            kp_evidence=kp_evidences,
            overall_timing_score=round(overall_score, 1),
            verdict=verdict,
            favorable_window=favorable_window,
            evidence_strength=evidence_strength
        )
