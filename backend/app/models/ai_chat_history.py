from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
import uuid

def uuid_str():
    return str(uuid.uuid4())

class AIChatHistory(Base):
    __tablename__ = "ai_chat_history"

    id = Column(String(36), primary_key=True, default=uuid_str)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # ✅ Enum khớp với DB (chỉ chấp nhận 'user' hoặc 'assistant')
    role = Column(Enum('user', 'assistant', name='ai_role_enum'), default='user', nullable=False)

    message = Column(Text, nullable=False)
    response = Column(Text)
    model_name = Column(String(100))
    token_usage = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="ai_chat_history")

    def __repr__(self):
        return f"<AIChatHistory(user_id={self.user_id}, role={self.role}, model={self.model_name})>"
