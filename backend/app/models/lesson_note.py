from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime
import uuid


def uuid_str():
    return str(uuid.uuid4())


class LessonNote(Base):
    __tablename__ = "lesson_notes"

    id = Column(String(36), primary_key=True, default=uuid_str)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    lesson_id = Column(String(36), ForeignKey("lessons.id"), nullable=False)
    content = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="lesson_notes")
    lesson = relationship("Lesson", backref="lesson_notes")

    def __repr__(self):
        return f"<LessonNote(user={self.user_id}, lesson={self.lesson_id})>"
