from fastapi import APIRouter, Depends, Query
from typing import List
from app.schemas.commerce import WalletResponse, WalletTransaction
from app.services.commerce_service import CommerceService
from app.core.security import get_current_user_id

router = APIRouter()
_commerce_service = CommerceService()

@router.get("", response_model=WalletResponse)
async def get_wallet(current_user_id: str = Depends(get_current_user_id)):
    return await _commerce_service.get_wallet(current_user_id)

@router.get("/transactions", response_model=List[WalletTransaction])
async def get_transactions(current_user_id: str = Depends(get_current_user_id)):
    return await _commerce_service.get_transactions(current_user_id)

@router.post("/credit-test", response_model=WalletResponse)
async def credit_test(
    amount: int = Query(..., gt=0),
    current_user_id: str = Depends(get_current_user_id)
):
    return await _commerce_service.credit_test(current_user_id, amount)
