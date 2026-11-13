from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum


class PalmReadingMode(str, Enum):
    QUICK = "QUICK"
    DEEP = "DEEP"


class PalmReadingStatus(str, Enum):
    PENDING = "PENDING"
    UPLOADING = "UPLOADING"
    VALIDATING = "VALIDATING"
    NEED_SUPPLEMENTAL = "NEED_SUPPLEMENTAL"
    EXTRACTING = "EXTRACTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class HandSide(str, Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class ImageType(str, Enum):
    RIGHT_FULL = "RIGHT_FULL"
    LEFT_FULL = "LEFT_FULL"
    RIGHT_CENTER_CLOSEUP = "RIGHT_CENTER_CLOSEUP"
    LEFT_CENTER_CLOSEUP = "LEFT_CENTER_CLOSEUP"
    RIGHT_THUMB_MOUNT = "RIGHT_THUMB_MOUNT"
    LEFT_THUMB_MOUNT = "LEFT_THUMB_MOUNT"
    OTHER = "OTHER"


class RegionQuality(BaseModel):
    score: float  # 0.0 to 1.0
    status: str   # VALID / LOW_CONFIDENCE / NOT_VISIBLE


class HandQualityScores(BaseModel):
    overall: float
    life_line: RegionQuality
    head_line: RegionQuality
    heart_line: RegionQuality
    fate_line: RegionQuality
    mounts: RegionQuality
    thumb: RegionQuality
    fingers: RegionQuality


class SupplementalPhotoRequest(BaseModel):
    image_type: ImageType
    reason: str
    region: str


class PalmLineObservation(BaseModel):
    name: str
    visibility: float
    characteristics: List[str]
    geometry: Optional[List[Dict[str, float]]] = None
    description: Optional[str] = None


class PalmMountObservation(BaseModel):
    name: str
    prominence: float
    description: Optional[str] = None


class HandObservations(BaseModel):
    hand_side: HandSide
    major_lines: List[PalmLineObservation]
    mounts: List[PalmMountObservation]
    hand_shape: Optional[str] = None
    finger_proportions: Optional[str] = None
    confidence: float
    quality_scores: HandQualityScores


class ComparativeObservations(BaseModel):
    line_prominence_diff: Dict[str, float]
    shape_diff: str
    dominant_hand_analysis: str


class PalmSpatialModel(BaseModel):
    """Normalized landmark-based model for visualization."""
    palm_outline: List[Dict[str, float]]
    finger_landmarks: Dict[str, List[Dict[str, float]]]
    line_paths: Dict[str, List[Dict[str, float]]]
    metadata: Dict[str, str]


class PalmReadingSessionRequest(BaseModel):
    profile_id: Optional[str] = None
    mode: PalmReadingMode = PalmReadingMode.QUICK
    dominant_hand: Optional[HandSide] = None


class PalmImageUploadRequest(BaseModel):
    session_id: str
    image_type: ImageType
    image_base64: str


class PalmChatMessage(BaseModel):
    role: str
    content: str
    timestamp: str


class PalmReadingResponse(BaseModel):
    id: str
    profile_id: Optional[str] = None
    profile_name: Optional[str] = None
    status: PalmReadingStatus
    uploaded_images: List[ImageType] = Field(default_factory=list)
    right_hand: Optional[HandObservations] = None
    left_hand: Optional[HandObservations] = None
    comparative: Optional[ComparativeObservations] = None
    spatial_model: Optional[PalmSpatialModel] = None
    supplemental_requests: List[SupplementalPhotoRequest] = Field(default_factory=list)
    interpretation: Optional[str] = None

    # Kept for API compatibility. Public responses intentionally do not expose
    # private knowledge-source details.
    sources: Optional[List[Dict[str, str]]] = None

    history: List[PalmChatMessage] = Field(default_factory=list)
    created_at: str


class PalmChatQuestionRequest(BaseModel):
    question: str
    mode: PalmReadingMode = PalmReadingMode.QUICK
    language: str = "hi"


class PalmChatResponseType(str, Enum):
    ANSWER = "ANSWER"
    NEED_MORE_EVIDENCE = "NEED_MORE_EVIDENCE"
    ERROR = "ERROR"


class PalmChatResponse(BaseModel):
    type: PalmChatResponseType
    answer: Optional[str] = None
    supplemental_request: Optional[SupplementalPhotoRequest] = None

    # Kept for Android DTO compatibility; intentionally omitted from user-facing
    # responses so internal source books/methods are not disclosed.
    sources: Optional[List[Dict[str, str]]] = None

    session_id: str
    history: List[PalmChatMessage] = Field(default_factory=list)
