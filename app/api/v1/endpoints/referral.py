from fastapi import APIRouter, Depends, Query
from app.schemas.commerce import ReferralInfo
from app.services.commerce_service import CommerceService
from app.core.security import get_current_user_id

router = APIRouter()
_commerce_service = CommerceService()

@router.get("", response_model=ReferralInfo)
async def get_referral_info(current_user_id: str = Depends(get_current_user_id)):
    return await _commerce_service.get_referral_info(current_user_id)

@router.post("/apply", response_model=ReferralInfo)
async def apply_referral(
    code: str = Query(...),
    current_user_id: str = Depends(get_current_user_id)
):
    return await _commerce_service.apply_referral(current_user_id, code)
