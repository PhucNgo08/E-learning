from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
import uuid


def uuid_str():
    return str(uuid.uuid4())


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(String(36), primary_key=True, default=uuid_str)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)
    due_date = Column(DateTime, nullable=True)
    max_score = Column(Integer, default=100)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 🔗 Quan hệ với Course
    course = relationship("Course", back_populates="assignments")

    def __repr__(self):
        return f"<Assignment(title='{self.title}', course_id='{self.course_id}')>"
