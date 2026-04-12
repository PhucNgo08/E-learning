# backend/app/models/teacher_profile.py
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.connection import Base


class TeacherProfile(Base):
    __tablename__ = "teacher_profiles"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    employee_code = Column(String(20), unique=True, nullable=True)
    major_id = Column(String(36), ForeignKey("majors.id"), nullable=True)
    bio = Column(Text, nullable=True)
    total_assignments_created = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="teacher_profile")
    major = relationship("Major", back_populates="teacher_profiles")

    def __repr__(self):
        return f"<TeacherProfile(user_id='{self.user_id}', employee_code='{self.employee_code}')>"