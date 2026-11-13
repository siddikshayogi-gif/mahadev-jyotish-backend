from fastapi import APIRouter, Depends
from app.schemas.contracts import SessionRequest, SessionResponse
from app.core.security import get_current_user_id
import uuid
import datetime

router = APIRouter()

@router.post("/session", response_model=SessionResponse)
async def create_session(request: SessionRequest):
    """Session exchange endpoint."""
    session_token = str(uuid.uuid4())
    user_id = f"usr_{session_token[:12]}"
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return SessionResponse(
        session_token=session_token,
        user_id=user_id,
        created_at=created_at
    )
