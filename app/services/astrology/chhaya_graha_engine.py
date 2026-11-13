"""Rahu-Ketu / Chhaya Graha event modifier using actual project schemas.

Uses VedicPlanetFact.body/house_d1/rashi/degree_in_rashi/sign_lord,
KP PlanetSignificatorFact, active dasha chain, and GocharResult.transits.
Does NOT assign classical Shadbala to Rahu/Ketu.
"""

from typing import Any, Dict, List, Optional, Set
from app.services.astrology.event_signatures import EVENT_SIGNATURES

class ChhayaGrahaEvidenceEngine:
    def analyze(
        self,
        vedic_chart: Any,
        event: str,
        active_dasha_chain: Optional[List[Dict[str, Any]]] = None,
        kp_result: Any = None,
        gochar_result: Any = None,
    ) -> Dict[str, Any]:
        sig = EVENT_SIGNATURES.get(event, EVENT_SIGNATURES["GENERAL_MAJOR_EVENT"])
        event_houses: Set[int] = set(sig.primary_houses + sig.supporting_houses)
        obstruction_houses: Set[int] = set(sig.unfavorable_houses)

        planets = {p.body: p for p in getattr(vedic_chart, "planets", [])}
        kp_map = {
            ps.planet: set(ps.all_signified_houses)
            for ps in getattr(kp_result, "planet_significators", [])
        } if kp_result is not None else {}

        active_lords = [str(x.get("lord","")) for x in (active_dasha_chain or [])]
        result: Dict[str, Any] = {"event": event}

        for node in ("Rahu","Ketu"):
            p = planets.get(node)
            if p is None:
                result[node.lower()] = {"available": False}
                continue

            score = 0.0
            reasons = []
            house = int(p.house_d1)
            sign = int(p.rashi)
            dispositor = p.sign_lord

            if house in event_houses:
                score += 20
                reasons.append("natal event-house placement")
            if house in obstruction_houses:
                score += 10
                reasons.append("natal obstruction-house modifier")

            # Dispositor delivers node results.
            dp = planets.get(dispositor)
            if dp is not None:
                if int(dp.house_d1) in event_houses:
                    score += 14
                    reasons.append("dispositor linked to event houses")

            # Same-sign close conjunction <= 8 degrees.
            conjunct = []
            for other in getattr(vedic_chart, "planets", []):
                if other.body == node or other.rashi != p.rashi:
                    continue
                if abs(float(other.degree_in_rashi) - float(p.degree_in_rashi)) <= 8.0:
                    conjunct.append(other.body)
                    if int(other.house_d1) in event_houses:
                        score += 10
            if conjunct:
                reasons.append("close conjunction: " + ", ".join(conjunct))

            # Vimshottari node/dispositor activation.
            if node in active_lords:
                score += 22
                reasons.append("node active in dasha chain")
            if dispositor in active_lords:
                score += 10
                reasons.append("dispositor active in dasha chain")

            # KP significator linkage.
            node_houses = kp_map.get(node, set())
            if node_houses.intersection(event_houses):
                score += 18
                reasons.append("KP event-house linkage")
            if node_houses.intersection(obstruction_houses):
                score += 8
                reasons.append("KP obstruction-house linkage")

            # Current gochar modifier.
            if gochar_result is not None:
                for t in getattr(gochar_result, "transits", []):
                    if t.body != node:
                        continue
                    if int(t.house_from_d1_lagna) in event_houses or int(t.house_from_moon) in event_houses:
                        score += 10
                        reasons.append("current transit activates event houses")
                    break

            result[node.lower()] = {
                "available": True,
                "house": house,
                "rashi": p.rashi_name,
                "dispositor": dispositor,
                "score": min(100.0, round(score,1)),
                "strength": "HIGH" if score >= 55 else ("MODERATE" if score >= 30 else "LOW"),
                "reasons": reasons,
            }

        mx = max(
            float(result.get("rahu",{}).get("score",0.0)),
            float(result.get("ketu",{}).get("score",0.0))
        )
        result["combined_modifier"] = "HIGH" if mx >= 55 else ("MODERATE" if mx >= 30 else "LOW")
        result["note"] = "Rahu/Ketu are event modifiers; classical Shadbala is not assigned to nodes."
        return result
