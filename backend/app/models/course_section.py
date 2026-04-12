from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime


class CourseSection(Base):
    __tablename__ = "course_sections"

    id = Column(String(36), primary_key=True)
    course_id = Column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    section_code = Column(String(10), nullable=False)
    section_name = Column(String(100))
    teacher_id = Column(String(36), ForeignKey("users.id"))

    max_students = Column(Integer, default=50)
    current_students = Column(Integer, default=0)
    schedule_info = Column(Text)
    location = Column(String(100))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    course = relationship("Course", back_populates="sections")
    teacher = relationship("User", back_populates="teaching_sections")
    schedules = relationship(
        "ClassSchedule",
        back_populates="section",
        cascade="all, delete-orphan"
    )