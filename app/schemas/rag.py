from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class CorpusType(str, Enum):
    VEDIC = "VEDIC"
    KP = "KP"
    PALMISTRY = "PALMISTRY"

class RightsStatus(str, Enum):
    OWNED = "OWNED"
    LICENSED = "LICENSED"
    PUBLIC_DOMAIN = "PUBLIC_DOMAIN"
    PERMISSION_REQUIRED = "PERMISSION_REQUIRED"
    UNKNOWN = "UNKNOWN"

class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    PARTIAL = "PARTIAL"
    VERIFIED = "VERIFIED"

class BookManifest(BaseModel):
    source_id: str
    title: str
    author: Optional[str] = "Unknown"
    edition: Optional[str] = None
    language: str = "en"
    file_name: str
    corpus: CorpusType
    rights_status: RightsStatus = RightsStatus.UNKNOWN
    allowed_for_production_rag: bool = False
    checksum: str
    page_mapping_available: bool = False
    citation_verification: VerificationStatus = VerificationStatus.UNVERIFIED
    notes: Optional[str] = None
    ingested_at: Optional[str] = None
    total_chunks: int = 0

class TextChunk(BaseModel):
    chunk_id: str
    source_id: str
    book_title: str
    corpus: CorpusType
    chapter: Optional[str] = None
    page: Optional[int] = None
    verse: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    text: str
    checksum: str
    score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RAGQueryRequest(BaseModel):
    query: str
    corpus: CorpusType = CorpusType.VEDIC
    topic: Optional[str] = None
    top_k: int = 3
    max_total_chars: int = 1500

class RAGQueryResult(BaseModel):
    query: str
    corpus: CorpusType
    retrieved_chunks: List[TextChunk] = Field(default_factory=list)
    total_chunks_found: int = 0
    citations: List[str] = Field(default_factory=list)
    formatted_prompt_context: str = ""

class CorpusStatusResult(BaseModel):
    vedic_status: str
    kp_status: str
    palmistry_status: str
    is_ready_for_production: bool
    total_books_ingested: int
    total_chunks_indexed: int
    message: str
