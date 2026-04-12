from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database.connection import Base


class DiscussionLike(Base):
    __tablename__ = "discussion_likes"

    discussion_id = Column(
        String(36),
        ForeignKey("discussions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    discussion = relationship(
        "Discussion",
        back_populates="discussion_likes",
    )
    user = relationship(
        "User",
        back_populates="discussion_likes",
    )

    def __repr__(self) -> str:
        return f"<DiscussionLike(discussion_id='{self.discussion_id}', user_id='{self.user_id}')>"