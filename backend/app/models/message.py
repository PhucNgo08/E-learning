from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True)
    sender_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)

    # File đính kèm
    attachment_url = Column(String(500), nullable=True)
    attachment_name = Column(String(255), nullable=True)
    attachment_size = Column(String(50), nullable=True)

    # ✅ Quan hệ ORM TWO-WAY đúng chuẩn
    sender = relationship(
        "User",
        foreign_keys=[sender_id],
        back_populates="messages_sent"
    )

    receiver = relationship(
        "User",
        foreign_keys=[receiver_id],
        back_populates="messages_received"
    )

    def __repr__(self):
        return f"<Message from={self.sender_id} to={self.receiver_id} sent_at={self.sent_at}>"
