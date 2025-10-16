from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
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

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # === Quan hệ ORM ===
    course = relationship("Course", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Module(id={self.id}, title={self.title}, is_published={self.is_published})>"
