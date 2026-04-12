from sqlalchemy import Column, String, DECIMAL, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base
import uuid


class WalletAccount(Base):
    __tablename__ = "wallet_accounts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    balance = Column(DECIMAL(12, 2), default=0, nullable=False)

    # DB đang là VARCHAR(20), không phải ENUM
    status = Column(String(20), default="active", nullable=False)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="wallet")
    transactions = relationship(
        "WalletTransaction",
        back_populates="wallet",
        cascade="all, delete-orphan",
        order_by="WalletTransaction.created_at.desc()",
    )

    def __repr__(self):
        return f"<WalletAccount user_id={self.user_id} balance={self.balance} status={self.status}>"