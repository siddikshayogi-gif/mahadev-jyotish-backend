from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    auth,
    profiles,
    locations,
    calculations,
    predictions,
    wallet,
    rag,
    palmistry,
    reports,
    referral
)

api_router = APIRouter()

# Register endpoint groups
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["Profiles"])
api_router.include_router(locations.router, prefix="/locations", tags=["Locations"])
api_router.include_router(calculations.router, prefix="/calculations", tags=["Calculations"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["Predictions"])
api_router.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])
api_router.include_router(rag.router, prefix="/rag", tags=["RAG"])
api_router.include_router(palmistry.router, prefix="/palm", tags=["Palmistry"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(referral.router, prefix="/referral", tags=["Referral"])
