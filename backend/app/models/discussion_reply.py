from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
import uuid

def uuid_str():
    return str(uuid.uuid4())

class DiscussionReply(Base):
    __tablename__ = "discussion_replies"

    id = Column(String(36), primary_key=True, default=uuid_str)
    discussion_id = Column(String(36), ForeignKey("discussions.id"))
    user_id = Column(String(36), ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    discussion = relationship("Discussion", back_populates="replies")
    author = relationship("User")
