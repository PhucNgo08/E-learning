from datetime import datetime
import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship

from app.database.connection import Base


def uuid_str():
    return str(uuid.uuid4())


class Order(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=uuid_str)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    total_amount = Column(DECIMAL(10, 2), nullable=False)

    # DB đang là VARCHAR(30), không phải ENUM
    status = Column(String(30), nullable=False, default="pending")

    payment_method = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    wallet_transactions = relationship("WalletTransaction", back_populates="order")

    # Legacy compatibility only
    user_courses = relationship("UserCourse", back_populates="order")

    def __repr__(self):
        return f"<Order {self.id} - {self.status}>"