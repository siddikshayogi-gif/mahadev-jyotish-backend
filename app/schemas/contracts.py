from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"

class ReadinessResponse(BaseModel):
    status: str = "ready"
    database: str = "connected"
    swiss_ephemeris: str = "available"
    ai_provider: str = "configured"

class SessionRequest(BaseModel):
    device_id: Optional[str] = None
    email: Optional[str] = None

class SessionResponse(BaseModel):
    session_token: str
    user_id: str
    created_at: str

class ProfileCreate(BaseModel):
    name: str
    date_of_birth: str  # YYYY-MM-DD
    time_of_birth: str  # HH:MM:SS
    place_of_birth: str
    latitude: float
    longitude: float
    timezone_id: str
    gender: Optional[str] = None
    is_primary: bool = False

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    time_of_birth: Optional[str] = None
    place_of_birth: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone_id: Optional[str] = None
    gender: Optional[str] = None
    is_primary: Optional[bool] = None

class ProfileResponse(BaseModel):
    id: str
    user_id: str
    name: str
    date_of_birth: str
    time_of_birth: str
    place_of_birth: str
    latitude: float
    longitude: float
    timezone_id: str
    gender: Optional[str] = None
    is_primary: bool = False
    created_at: str
