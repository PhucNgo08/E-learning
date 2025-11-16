from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
import uuid

def uuid_str():
    return str(uuid.uuid4())

class DiscussionLike(Base):
    __tablename__ = "discussion_likes"

    id = Column(String(36), primary_key=True, default=uuid_str)
    discussion_id = Column(String(36), ForeignKey("discussions.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # OPTIONAL relationships
    discussion = relationship("Discussion", backref="likes")
    user = relationship("User")
