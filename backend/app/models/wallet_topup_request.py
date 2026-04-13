import uuid

from sqlalchemy import Column, DateTime, DECIMAL, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.connection import Base


class WalletTopupRequest(Base):
    __tablename__ = "wallet_topup_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_code = Column(String(40), unique=True, nullable=False, index=True)

    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    wallet_id = Column(
        String(36),
        ForeignKey("wallet_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    wallet_transaction_id = Column(
        String(36),
        ForeignKey("wallet_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )

    amount = Column(DECIMAL(12, 2), nullable=False)
    payment_channel = Column(String(30), nullable=False, default="bank_qr")

    bank_code = Column(String(30), nullable=True)
    bank_account_no = Column(String(50), nullable=True)
    bank_account_name = Column(String(120), nullable=True)
    transfer_note = Column(String(120), nullable=False)
    note = Column(Text, nullable=True)
    receipt_image_url = Column(String(500), nullable=True)

    status = Column(String(20), nullable=False, default="pending")
    reviewed_by = Column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_note = Column(Text, nullable=True)

    requested_at = Column(DateTime, server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    wallet = relationship("WalletAccount")
    wallet_transaction = relationship("WalletTransaction")

    def __repr__(self):
        return (
            f"<WalletTopupRequest code={self.request_code} user_id={self.user_id} "
            f"amount={self.amount} status={self.status}>"
        )
