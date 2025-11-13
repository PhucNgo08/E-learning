from sqlalchemy import Column, String, DateTime, ForeignKey
from datetime import datetime
from app.database.connection import Base

class DiscussionLike(Base):
    __tablename__ = "discussion_likes"

    id = Column(String(36), primary_key=True, index=True)
    discussion_id = Column(String(36), ForeignKey("discussions.id", ondelete="CASCADE"))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    created_at = Column(DateTime, default=datetime.utcnow)
