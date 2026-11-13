from fastapi import APIRouter
from app.schemas.contracts import HealthResponse, ReadinessResponse
from app.services.astrology.swiss_provider import SwissEphemerisProvider
from app.core.config import settings

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """System liveness endpoint."""
    return HealthResponse(status="ok", version="1.2.0-prediction-protocol")

@router.get("/readiness", response_model=ReadinessResponse)
async def readiness_check():
    """System subsystem readiness split endpoint."""
    # Check Swiss Ephemeris
    swiss_status = "ready"
    try:
        provider = SwissEphemerisProvider(ephe_path=settings.swiss_ephemeris_path)
        _ = provider.version
    except:
        swiss_status = "error"

    return ReadinessResponse(
        status="ready" if swiss_status == "ready" else "partially_ready",
        database="connected", # DB ping could be added here
        swiss_ephemeris=swiss_status,
        ai_provider="ready"
    )
