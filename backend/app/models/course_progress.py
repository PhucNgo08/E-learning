import uuid

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, DECIMAL, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.connection import Base


class CourseProgress(Base):
    __tablename__ = "course_progress"

    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_course_progress"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)

    progress_percent = Column(DECIMAL(5, 2), nullable=False, default=0)
    completed_lessons = Column(Integer, nullable=False, default=0)
    total_lessons = Column(Integer, nullable=False, default=0)
    status = Column(String(30), nullable=False, default="not_started")

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="course_progresses")
    course = relationship("Course", back_populates="course_progresses")