from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
import uuid

def uuid_str():
    return str(uuid.uuid4())

class Discussion(Base):
    __tablename__ = "discussions"

    id = Column(String(36), primary_key=True, default=uuid_str)
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    parent_id = Column(String(36), ForeignKey("discussions.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Quan hệ
    user = relationship("User", back_populates="discussions")
    course = relationship("Course", back_populates="discussions")

    replies = relationship(
        "Discussion",
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    parent = relationship(
        "Discussion",
        back_populates="replies",
        remote_side=[id]
    )
