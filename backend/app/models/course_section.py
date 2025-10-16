from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base
from sqlalchemy import DECIMAL , Enum
from datetime import datetime

class CourseSection(Base):
    __tablename__ = 'course_sections'

    id = Column(String(36), primary_key=True)
    course_id = Column(String(36), ForeignKey("courses.id"))
    section_code = Column(String(10), nullable=False)
    section_name = Column(String(100))
    
    max_students = Column(Integer, default=50)
    current_students = Column(Integer, default=0)
    schedule_info = Column(String(500))
    location = Column(String(100))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    course = relationship("Course", backref="sections")
