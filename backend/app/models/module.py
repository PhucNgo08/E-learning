from sqlalchemy import (
    Column, String, Integer, DateTime, Text, ForeignKey, DECIMAL, Boolean
)
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime
import uuid


def uuid_str():
    """Sinh ID UUID cho các bảng."""
    return str(uuid.uuid4())


class Module(Base):
    __tablename__ = "modules"

    id = Column(String(36), primary_key=True, default=uuid_str)
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)
    module_number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    learning_objectives = Column(Text)
    estimated_duration = Column(Integer)
    is_published = Column(Integer, default=0)  # ✅ TINYINT trong MySQL

    # 📘 Bổ sung các trường liên quan đến Assignment
    has_assignment = Column(Boolean, default=False)  # 1 = có bài tập
    assignment_count = Column(Integer, default=0)    # số lượng bài tập trong module
    assignment_weight = Column(DECIMAL(5, 2), default=0)  # trọng số điểm (%)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # === Quan hệ ORM ===
    course = relationship("Course", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="module", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Module(title='{self.title}', has_assignment={self.has_assignment})>"
