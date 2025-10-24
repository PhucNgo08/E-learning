from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime

class CourseSection(Base):
    __tablename__ = "course_sections"

    id = Column(String(36), primary_key=True)
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)
    section_code = Column(String(10), nullable=False)
    section_name = Column(String(100))
    teacher_id = Column(String(36), ForeignKey("users.id"))  # ✅ Thêm cột bị thiếu

    max_students = Column(Integer, default=50)
    current_students = Column(Integer, default=0)
    schedule_info = Column(Text)
    location = Column(String(100))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 🔗 Quan hệ ORM
    course = relationship("Course", backref="sections")
    teacher = relationship("User", backref="teaching_sections")
