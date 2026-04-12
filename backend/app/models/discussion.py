from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.database.connection import Base


def uuid_str() -> str:
    return str(uuid.uuid4())


class Discussion(Base):
    __tablename__ = "discussions"

    id = Column(String(36), primary_key=True, default=uuid_str)
    course_id = Column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    parent_id = Column(String(36), ForeignKey("discussions.id", ondelete="CASCADE"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="discussions")
    course = relationship("Course", back_populates="discussions")

    parent = relationship(
        "Discussion",
        remote_side=[id],
        back_populates="children",
    )
    children = relationship(
        "Discussion",
        back_populates="parent",
        cascade="all, delete-orphan",
    )

    discussion_likes = relationship(
        "DiscussionLike",
        back_populates="discussion",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Discussion(id='{self.id}', user_id='{self.user_id}')>"