from sqlalchemy import Column, String, DECIMAL, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base
import enum
import uuid


# ============================================
# 🧩 ENUM
# ============================================
class WalletStatus(str, enum.Enum):
    active = "active"
    locked = "locked"


# ============================================
# 🧩 MODEL: WalletAccount
# ============================================
class WalletAccount(Base):
    __tablename__ = "wallet_accounts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    balance = Column(DECIMAL(12, 2), default=0)

    status = Column(Enum(WalletStatus), default=WalletStatus.active, nullable=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # RELATIONS
    user = relationship("User", back_populates="wallet")
    transactions = relationship(
        "WalletTransaction",
        back_populates="wallet",
        cascade="all, delete-orphan",
        order_by="WalletTransaction.created_at.desc()"
    )
