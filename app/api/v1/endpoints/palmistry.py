from fastapi import APIRouter, Depends, HTTPException
from app.schemas.palmistry import (
    PalmReadingSessionRequest,
    PalmImageUploadRequest,
    PalmReadingResponse,
    PalmChatQuestionRequest,
    PalmChatResponse
)
from app.services.palmistry_service import PalmistryService
from app.core.security import get_current_user_id

router = APIRouter()
_palm_service = PalmistryService()

@router.post("/session", response_model=PalmReadingResponse)
async def create_palm_session(
    req: PalmReadingSessionRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """Creates a new dual-hand palm reading session."""
    return await _palm_service.create_session(
        profile_id=req.profile_id,
        mode=req.mode,
        dominant_hand=req.dominant_hand
    )

@router.post("/upload", response_model=PalmReadingResponse)
async def upload_palm_image(
    req: PalmImageUploadRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """Uploads an image (Right Full, Left Full, or Supplemental) to an active session."""
    try:
        return await _palm_service.upload_image(
            session_id=req.session_id,
            image_type=req.image_type,
            image_base64=req.image_base64
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/session/{session_id}", response_model=PalmReadingResponse)
async def get_palm_session(
    session_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Retrieves current status and results of a palm reading session."""
    from app.services.palmistry_service import _palm_sessions
    if session_id not in _palm_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    return _palm_service._map_to_response(_palm_sessions[session_id])

@router.post("/session/{session_id}/ask", response_model=PalmChatResponse)
async def ask_palm_ai(
    session_id: str,
    req: PalmChatQuestionRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """Answers a question about the user's palms in the current session."""
    return await _palm_service.ask_question(session_id, req)
