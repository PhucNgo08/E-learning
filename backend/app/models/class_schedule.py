from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database.connection import Base

from datetime import datetime

class ClassSchedule(Base):
    __tablename__ = 'class_schedules'

    id = Column(String(36), primary_key=True)
    section_id = Column(String(36), ForeignKey("course_sections.id"))
    day_of_week = Column(Enum('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', name='day_of_week_enum'))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    room_number = Column(String(50))
    building = Column(String(100))
    schedule_type = Column(Enum('weekly', 'odd_week', 'even_week', name='schedule_type_enum'), default='weekly')

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    section = relationship("CourseSection", backref="class_schedules")
