from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database.connection import Base

from datetime import datetime

class LessonProgress(Base):
    __tablename__ = 'lesson_progress'

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    lesson_id = Column(String(36), ForeignKey("lessons.id"))

    progress_status = Column(Enum('not_started', 'in_progress', 'completed', name='lesson_progress_status_enum'), default='not_started')
    completion_percentage = Column(Integer, default=0)
    time_spent_seconds = Column(Integer, default=0)
    last_position_seconds = Column(Integer, default=0)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="lesson_progress")
    lesson = relationship("Lesson", backref="lesson_progress")
