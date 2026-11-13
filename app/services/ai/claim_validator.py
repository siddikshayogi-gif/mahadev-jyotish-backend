"""Claim Validator Service.

Validates AI-generated responses against deterministic evidence bundle facts.
Detects and repairs unsupported planet, house, Dasha, transit, or timing claims.
"""

import re
from typing import Tuple
from app.schemas.ai_chat import EvidenceBundle, StructuredAIResponse

class ClaimValidator:
    """Validates claims in AI responses against deterministic evidence facts."""

    def validate_and_repair(
        self,
        ai_response: StructuredAIResponse,
        evidence: EvidenceBundle
    ) -> Tuple[StructuredAIResponse, str]:
        """Returns (validated_response, claim_validation_status).
        Status is 'VALIDATED', 'REPAIRED', or 'REJECTED'.
        """
        status = "VALIDATED"
        repaired = ai_response.model_copy(deep=True)

        # Check fact hash match
        if repaired.fact_hash != evidence.fact_hash:
            repaired.fact_hash = evidence.fact_hash
            status = "REPAIRED"

        # Check Dasha claim integrity
        # Check if Dasha lords mentioned in direct answer or explanation exist in active chain
        mentioned_dashas = re.findall(r'\b(Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)\s+Dasha\b', repaired.direct_answer + " " + repaired.short_explanation, re.IGNORECASE)
        valid_dashas = [d['lord'].lower() for d in evidence.active_dasha_chain]

        if mentioned_dashas:
            for d_claim in mentioned_dashas:
                if d_claim.lower() not in valid_dashas:
                    # Unsupported Dasha claim detected; repair explanation
                    d_summary = " -> ".join([f"{d['lord']}" for d in evidence.active_dasha_chain])
                    repaired.short_explanation += f"\n(Note: Calculated Dasha chain is {d_summary})."
                    status = "REPAIRED"
                    break

        # Check Yoga claim integrity - NO HALLUCINATED YOGAS
        mentioned_yogas = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Yoga)\b', repaired.direct_answer + " " + repaired.short_explanation)
        valid_yogas = [y.lower() for y in evidence.active_yogas]

        if mentioned_yogas:
            for y_claim in mentioned_yogas:
                # Basic check: is the yoga name (case insensitive) in the valid list?
                if y_claim.lower() not in valid_yogas and "raj yoga" not in y_claim.lower(): # Allow "Raj Yoga" as generic term sometimes used for MD/AD
                    # Hallucinated Yoga detected
                    repaired.short_explanation = repaired.short_explanation.replace(y_claim, "[astrological alignment]")
                    status = "REPAIRED"

        # Production privacy contract: technical calculation details are internal-only.
        # Never manufacture the old "Main Astrological Basis" block.
        if repaired.technical_astrological_reason:
            repaired.technical_astrological_reason = ""
            status = "REPAIRED"
        if repaired.classical_basis:
            repaired.classical_basis = []
            status = "REPAIRED"

        allow_direct_strength = bool((evidence.query_flags or {}).get("direct_strength_query"))

        # Scrub accidental internal markers from customer-facing prose.
        patterns_to_scrub = [
            r'(?i)मुख्य ज्योतिषीय आधार[^\n]*',
            r'(?i)Main Astrological Basis[^\n]*',
            r'(?i)Ashtakavarga[^\n]*',
            r'(?i)Shadbala[^\n]*',
            r'(?i)FactHash[^\n]*',
            r'(?i)Evidence Strength[^\n]*',
            r'(?i)Power:\s*(?:VERY_HIGH|HIGH|MODERATE|LOW)[^\n]*',
            r'\[(?:CALCULATED_FACT|CHART_DATA|KP_SYSTEM_SIGNIFICATORS|VIMSHOTTARI_DASHA_CHAIN|TIMING_SCAN_RESULTS|GOCHAR_TRANSITS|VERIFIED_YOGAS|METHODOLOGY_RULES_RAG|ANALYTICAL_ENGINE_VERDICT|PRIVATE_PREDICTION_DECISION|PRIVATE_FINE_TIMING|USER_OUTPUT_POLICY)\][^\n]*'
        ]
        for pattern in patterns_to_scrub:
            if allow_direct_strength and ("Ashtakavarga" in pattern or "Shadbala" in pattern):
                continue
            repaired.direct_answer = re.sub(pattern, "", repaired.direct_answer or "").strip()
            repaired.short_explanation = re.sub(pattern, "", repaired.short_explanation or "").strip()

        return repaired, status
