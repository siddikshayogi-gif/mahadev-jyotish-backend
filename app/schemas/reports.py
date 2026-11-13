from pydantic import BaseModel
from typing import Optional
from enum import Enum

class ReportType(str, Enum):
    BASIC_KUNDALI = "BASIC_KUNDALI"
    FULL_JYOTISH = "FULL_JYOTISH"
    PALM_READING = "PALM_READING"

class ReportStatus(str, Enum):
    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"

class ReportRequest(BaseModel):
    profile_id: str
    type: ReportType
    language: str = "hi"

class ReportResponse(BaseModel):
    id: str
    status: ReportStatus
    file_url: Optional[str] = None
    created_at: str
