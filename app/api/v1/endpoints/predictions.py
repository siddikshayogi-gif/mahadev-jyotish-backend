from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import pytz

from app.schemas.dasha_gochar_yoga import (
    TopicTimingRequest,
    TimingWindowEvidenceResult
)
from app.schemas.ai_chat import (
    AskPredictionRequest,
    PredictionResponse
)
from app.api.v1.endpoints.calculations import (
    NatalCalculationRequest,
    DashaCalculationRequest,
    GocharCalculationRequest,
    calculate_natal,
    calculate_vedic,
    calculate_kp,
    calculate_dasha,
    calculate_gochar,
    calculate_yogas
)
from app.services.astrology.timing_engine import TimingEngine
from app.services.ai.chat_service import ChatService
from app.core.security import get_current_user_id

router = APIRouter()

_timing_engine = TimingEngine()
_chat_service = ChatService()

@router.post("/ask", response_model=PredictionResponse)
async def ask_prediction(
    req: AskPredictionRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """Server-side conversational AI astrology gateway using Gemini/NVIDIA and evidence-bound facts."""
    return await _chat_service.process_prediction(req, current_user_id=current_user_id)

@router.get("/history/{profile_id}")
async def get_chat_history(
    profile_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Retrieves conversation history for a given birth profile enforcing profile ownership boundary."""
    return _chat_service.get_chat_history(profile_id=profile_id, current_user_id=current_user_id)


@router.post("/timing-windows", response_model=TimingWindowEvidenceResult)
async def get_timing_window_evidence(req: TopicTimingRequest):
    """Returns structured topic timing evidence combining Dasha, Gochar, Yogas, and KP significators."""
    natal_req = NatalCalculationRequest(
        profile_id=req.profile_id,
        name=req.name,
        date_of_birth=req.date_of_birth,
        time_of_birth=req.time_of_birth,
        place_of_birth=req.place_of_birth,
        latitude=req.latitude,
        longitude=req.longitude,
        timezone_id=req.timezone_id
    )

    vedic_res = await calculate_vedic(natal_req)
    kp_res = await calculate_kp(natal_req)

    if req.target_date_utc:
        target_dt = datetime.fromisoformat(req.target_date_utc.replace("Z", "+00:00"))
    else:
        target_dt = datetime.now(timezone.utc)

    dasha_req = DashaCalculationRequest(
        **natal_req.model_dump(),
        target_date_utc=target_dt.isoformat(),
        max_depth=5
    )
    dasha_res = await calculate_dasha(dasha_req)

    gochar_req = GocharCalculationRequest(
        **natal_req.model_dump(),
        target_datetime_utc=target_dt.isoformat()
    )
    gochar_res = await calculate_gochar(gochar_req)

    yoga_res = await calculate_yogas(natal_req)

    evidence = _timing_engine.evaluate_timing_evidence(
        topic=req.topic or "CAREER",
        target_datetime_utc=target_dt,
        vedic_chart=vedic_res,
        kp_chart=kp_res,
        dasha_result=dasha_res,
        gochar_result=gochar_res,
        yoga_result=yoga_res,
        profile_id=req.profile_id or "prof_default"
    )
    return evidence

