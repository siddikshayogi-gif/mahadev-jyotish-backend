from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class AstrologyMethod(str, Enum):
    VEDIC = "VEDIC"
    KP = "KP"
    HYBRID = "HYBRID"
    PRASHNA = "PRASHNA"
    MUHURTA = "MUHURTA"
    SPECIALIZED = "SPECIALIZED"
    UNSUPPORTED = "UNSUPPORTED"

class TemporalIntent(str, Enum):
    PAST = "PAST"
    PRESENT = "PRESENT"
    FUTURE = "FUTURE"
    DATE_SPECIFIC = "DATE_SPECIFIC"
    DATE_RANGE = "DATE_RANGE"
    LIFETIME = "LIFETIME"
    MIXED = "MIXED"

class TemporalContext(BaseModel):
    intent: TemporalIntent
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    target_date: Optional[str] = None
    requested_horizon_years: int = 5

class EventWindow(BaseModel):
    event_type: str
    start_date: str
    end_date: str
    evidence_score: float
    evidence_strength: str  # LOW, MODERATE, HIGH, VERY_HIGH
    summary: str
    dasha_lord: str
    transit_indicators: List[str] = Field(default_factory=list)

class AstrologyMethodDecision(BaseModel):
    question_category: str
    primary_method: AstrologyMethod
    supporting_methods: List[AstrologyMethod] = []
    required_houses: List[int] = []
    required_calculations: List[str] = []
    required_knowledge_categories: List[str] = []
    confidence: float = 1.0
    missing_data: List[str] = []

class AskPredictionRequest(BaseModel):
    profile_id: Optional[str] = None
    question: str
    language: str = "hi"  # "hi", "en", "hinglish"
    mode: str = "QUICK"   # "QUICK" or "DEEP"
    time_intent: Optional[str] = None
    target_date_utc: Optional[str] = None
    
    # Optional birth info overrides
    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    time_of_birth: Optional[str] = None
    place_of_birth: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone_id: Optional[str] = None

class EvidenceBundle(BaseModel):
    profile_id: str
    topic: str
    fact_hash: str
    lagna_rashi: str
    moon_rashi: str
    sun_rashi: str
    temporal_context: Optional[TemporalContext] = None
    candidate_windows: List[EventWindow] = Field(default_factory=list)
    active_dasha_chain: List[Dict[str, Any]] # Full 5-level dasha chain objects
    upcoming_dasha_transitions: List[Dict[str, Any]] = Field(default_factory=list)
    key_transits: List[str]
    active_yogas: List[str]
    kp_significators: List[str]
    overall_timing_score: float
    evidence_strength: str = "MODERATE"
    timing_verdict: str
    method_decision: Optional[AstrologyMethodDecision] = None
    summary_prompt_text: str
    classical_citations: List[str] = Field(default_factory=list)
    classical_rag_context: str = ""

    # Runtime truth-guard fields. These are deterministic backend facts, not LLM claims.
    event_type: Optional[str] = None
    event_state: Dict[str, Any] = Field(default_factory=dict)
    calculated_facts: Dict[str, Any] = Field(default_factory=dict)
    query_flags: Dict[str, bool] = Field(default_factory=dict)

class StructuredAIResponse(BaseModel):
    direct_answer: str
    short_explanation: str
    timing: str
    supporting_factors: List[str] = Field(default_factory=list)
    challenging_factors: List[str] = Field(default_factory=list)
    practical_suggestion: str
    confidence: Optional[float] = 0.85
    confidence_label: Optional[str] = None
    classical_basis: List[str] = Field(default_factory=list)
    technical_astrological_reason: str
    follow_up_questions: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    fact_hash: str
    disclaimer: str = "Predictions are astrological guidance, not absolute certainty. No medical diagnosis or guaranteed financial returns."

class PredictionResponse(BaseModel):
    answer: str
    structured_response: StructuredAIResponse
    mode: str
    language: str
    provider: str
    model: str
    is_mock: bool
    fact_hash: str
    claim_validation_status: str  # "VALIDATED", "REPAIRED", "REJECTED"
