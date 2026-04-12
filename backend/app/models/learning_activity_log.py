import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.connection import Base


class LearningActivityLog(Base):
    __tablename__ = "learning_activity_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(String(36), ForeignKey("courses.id", ondelete="SET NULL"), nullable=True)
    module_id = Column(String(36), ForeignKey("modules.id", ondelete="SET NULL"), nullable=True)
    lesson_id = Column(String(36), ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True)

    activity_type = Column(String(50), nullable=False)

    progress_before = Column(Integer, nullable=False, default=0)
    progress_after = Column(Integer, nullable=False, default=0)
    position_seconds = Column(Integer, nullable=False, default=0)
    duration_seconds = Column(Integer, nullable=False, default=0)

    device_type = Column(String(30), nullable=True)
    ip_address = Column(String(45), nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())

    user = relationship("User", back_populates="learning_activity_logs")
    course = relationship("Course", back_populates="learning_activity_logs")
    module = relationship("Module", back_populates="learning_activity_logs")
    lesson = relationship("Lesson", back_populates="learning_activity_logs")