from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database.connection import Base


def uuid_str():
    return str(uuid.uuid4())


class AIChatHistory(Base):
    __tablename__ = "ai_chat_history"

    id = Column(String(36), primary_key=True, default=uuid_str)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    role = Column(String(20), default="user")
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    model_name = Column(String(100), nullable=True)
    token_usage = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    # 🔥 FIX LỖI BACKREF
    user = relationship(
        "User",
        back_populates="ai_chat_history",
        foreign_keys=[user_id]
    )

    def __repr__(self):
        return f"<AIChatHistory user_id={self.user_id} role={self.role}>"
