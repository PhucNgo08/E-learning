from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from app.database.connection import Base
from datetime import datetime

class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True)
    sender_id = Column(String(36), ForeignKey("users.id"))
    receiver_id = Column(String(36), ForeignKey("users.id"))
    content = Column(Text)
    sent_at = Column(DateTime, default=datetime.utcnow)
