from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class TransactionType(str, Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"
    REFUND = "REFUND"
    PROMO = "PROMO"
    REFERRAL = "REFERRAL"
    CASHBACK = "CASHBACK"

class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REVERSED = "REVERSED"

class WalletTransaction(BaseModel):
    id: str
    amount: int
    type: TransactionType
    reason: str
    service: Optional[str] = None
    status: TransactionStatus
    created_at: str
    idempotency_key: Optional[str] = None

class WalletResponse(BaseModel):
    user_id: str
    balance: int
    last_updated: str

class ReferralInfo(BaseModel):
    my_referral_code: str
    applied_referral_code: Optional[str] = None
    total_referrals: int = 0
    total_rewards_earned: int = 0
