import enum
import uuid

from sqlalchemy import Column, DateTime, DECIMAL, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.connection import Base


class WalletTransactionType(str, enum.Enum):
    deposit = "deposit"
    payment = "payment"
    withdraw = "withdraw"
    refund = "refund"
    adjust = "adjust"


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    wallet_id = Column(
        String(36),
        ForeignKey("wallet_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    order_id = Column(
        String(36),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
    )

    amount = Column(DECIMAL(12, 2), nullable=False)
    type = Column(String(20), nullable=False)
    description = Column(String(255), nullable=True)
    balance_before = Column(DECIMAL(12, 2), nullable=True)
    balance_after = Column(DECIMAL(12, 2), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    wallet = relationship("WalletAccount", back_populates="transactions")
    order = relationship("Order", back_populates="wallet_transactions")
    topup_request = relationship(
        "WalletTopupRequest",
        back_populates="wallet_transaction",
        foreign_keys="WalletTopupRequest.wallet_transaction_id",
        uselist=False,
    )

    def __repr__(self):
        return (
            f"<WalletTransaction wallet_id={self.wallet_id} "
            f"order_id={self.order_id} type={self.type} amount={self.amount}>"
        )