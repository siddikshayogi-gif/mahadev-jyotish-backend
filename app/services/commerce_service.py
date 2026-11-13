import uuid
import datetime
from typing import List, Optional, Dict
from app.schemas.commerce import (
    WalletResponse,
    WalletTransaction,
    TransactionType,
    TransactionStatus,
    ReferralInfo
)

# In-memory mock store
_wallets: Dict[str, int] = {} # user_id -> balance
_transactions: Dict[str, List[WalletTransaction]] = {}
_referrals: Dict[str, ReferralInfo] = {}

class CommerceService:
    def __init__(self):
        pass

    async def get_wallet(self, user_id: str) -> WalletResponse:
        balance = _wallets.get(user_id, 100) # Start with 100 bonus credits for new users
        if user_id not in _wallets:
            _wallets[user_id] = balance

        return WalletResponse(
            user_id=user_id,
            balance=balance,
            last_updated=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )

    async def get_transactions(self, user_id: str) -> List[WalletTransaction]:
        return _transactions.get(user_id, [])

    async def credit_test(self, user_id: str, amount: int) -> WalletResponse:
        current = await self.get_wallet(user_id)
        new_balance = current.balance + amount
        _wallets[user_id] = new_balance

        tx = WalletTransaction(
            id=f"tx_{uuid.uuid4().hex[:12]}",
            amount=amount,
            type=TransactionType.CREDIT,
            reason="Test Credit",
            status=TransactionStatus.SUCCESS,
            created_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )

        if user_id not in _transactions:
            _transactions[user_id] = []
        _transactions[user_id].insert(0, tx)

        return await self.get_wallet(user_id)

    async def debit(self, user_id: str, amount: int, reason: str, service: str) -> bool:
        current = await self.get_wallet(user_id)
        if current.balance < amount:
            return False

        new_balance = current.balance - amount
        _wallets[user_id] = new_balance

        tx = WalletTransaction(
            id=f"tx_{uuid.uuid4().hex[:12]}",
            amount=-amount,
            type=TransactionType.DEBIT,
            reason=reason,
            service=service,
            status=TransactionStatus.SUCCESS,
            created_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )

        if user_id not in _transactions:
            _transactions[user_id] = []
        _transactions[user_id].insert(0, tx)
        return True

    async def get_referral_info(self, user_id: str) -> ReferralInfo:
        if user_id not in _referrals:
            code = f"MAHADEV-{user_id[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
            _referrals[user_id] = ReferralInfo(
                my_referral_code=code,
                total_referrals=0,
                total_rewards_earned=0
            )
        return _referrals[user_id]

    async def apply_referral(self, user_id: str, code: str) -> ReferralInfo:
        info = await self.get_referral_info(user_id)
        if info.applied_referral_code:
            return info # Already applied

        # In local test, we just accept any valid looking code
        if not code.startswith("MAHADEV"):
            return info

        new_info = info.model_copy(update={"applied_referral_code": code})
        _referrals[user_id] = new_info

        # Reward user
        await self.credit_test(user_id, 100)

        return new_info
