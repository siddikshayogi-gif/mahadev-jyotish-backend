from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from app.schemas.rag import (
    RAGQueryRequest,
    RAGQueryResult,
    CorpusStatusResult,
    CorpusType
)
from app.services.ai.classical_rag import ClassicalRAGService

router = APIRouter()
_rag_service = ClassicalRAGService()

@router.get("/status", response_model=CorpusStatusResult)
async def get_rag_status():
    """Returns corpus status for Vedic, KP, and Palmistry classical source books."""
    return _rag_service.get_corpus_status()

@router.post("/search", response_model=RAGQueryResult)
async def search_classical_rag(req: RAGQueryRequest):
    """Performs corpus-isolated vector/hybrid search over classical source texts."""
    return _rag_service.search_rag(
        query=req.query,
        corpus=req.corpus,
        top_k=req.top_k,
        max_total_chars=req.max_total_chars
    )
