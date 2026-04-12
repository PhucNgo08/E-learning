from sqlalchemy import Column, String, Integer, DateTime, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime
import uuid


def uuid_str():
    """Sinh ID UUID cho các bảng."""
    return str(uuid.uuid4())


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(String(36), primary_key=True, default=uuid_str)
    module_id = Column(String(36), ForeignKey("modules.id"), nullable=False)
    lesson_number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)

    content_type = Column(
        Enum("video", "document", "quiz", "assignment", "mixed", name="content_type_enum"),
        default="video",
    )
    description = Column(Text)

    video_url = Column(String(500))
    document_url = Column(String(500))
    thumbnail_url = Column(String(500))

    duration_minutes = Column(Integer, default=0)
    is_preview = Column(Integer, default=0)
    is_published = Column(Integer, default=0)

    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # === Quan hệ ORM ===
    module = relationship("Module", back_populates="lessons")
    quizzes = relationship("Quiz", back_populates="lesson")
    lesson_notes = relationship(
        "LessonNote",
        back_populates="lesson",
        cascade="all, delete-orphan",
    )
    lesson_progresses = relationship("LessonProgress", back_populates="lesson", cascade="all, delete-orphan")
    learning_activity_logs = relationship("LearningActivityLog", back_populates="lesson")
    def __repr__(self):
        return f"<Lesson(id={self.id}, title={self.title}, start={self.start_time}, end={self.end_time})>"