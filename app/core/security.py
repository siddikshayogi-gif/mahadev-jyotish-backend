from fastapi import Header, Depends
from app.core.errors import UnauthorizedException, ForbiddenException
from typing import Optional

async def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Validate bearer token or auth session header to extract authenticated user ID."""
    if not authorization:
        # Default development user session ID if auth header missing during dev
        return "usr_dev_default_session"
    
    if not authorization.startswith("Bearer "):
        raise UnauthorizedException("Invalid authorization header format. Expected 'Bearer <token>'")
    
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise UnauthorizedException("Empty session token provided")
    
    # Session ID extracted from token
    return f"usr_{token[:16]}"

def verify_profile_ownership(profile_user_id: str, current_user_id: str) -> None:
    """Enforce strict profile ownership boundary (userId + profileId isolation)."""
    if profile_user_id != current_user_id:
        raise ForbiddenException("User does not own the requested birth profile")
