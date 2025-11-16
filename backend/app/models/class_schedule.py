from sqlalchemy import Column, String, Time, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database.connection import Base
import uuid
from datetime import datetime

class ClassSchedule(Base):
    __tablename__ = "class_schedules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 🔥 Quan hệ đúng với Class
    class_id = Column(String(36), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)

    day_of_week = Column(Enum(
        "monday", "tuesday", "wednesday", "thursday",
        "friday", "saturday", "sunday",
        name="day_of_week_enum"
    ), nullable=False)

    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    room_number = Column(String(50))
    building = Column(String(100))

    schedule_type = Column(Enum(
        "weekly", "odd_week", "even_week",
        name="schedule_type_enum"
    ), default="weekly")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 🔄 Quan hệ ngược với Class
    clazz = relationship("Class", back_populates="class_schedules")
