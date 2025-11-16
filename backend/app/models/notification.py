"""
==========================================================
📦 MODEL: Notification (Chuẩn ORM - Không conflict backref)
==========================================================
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database.connection import Base


def uuid_str():
    return str(uuid.uuid4())


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=uuid_str)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    notification_type = Column(
        Enum(
            "system", "course", "assignment", "quiz", "message", "other",
            name="notification_type_enum"
        ),
        default="system"
    )

    link_url = Column(String(500), nullable=True)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # ---------------------------------------------------
    # 🔥 FIX QUAN TRỌNG: KHÔNG DÙNG backref !!!
    # ---------------------------------------------------
    user = relationship(
        "User",
        back_populates="notifications",
        foreign_keys=[user_id]
    )

    def __repr__(self):
        return f"<Notification(title={self.title}, user_id={self.user_id}, is_read={self.is_read})>"
