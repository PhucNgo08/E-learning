# backend/app/models/student_profile.py
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.connection import Base


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    mssv = Column(String(20), unique=True, nullable=True)
    academic_year_id = Column(String(36), ForeignKey("academic_years.id"), nullable=True)
    major_id = Column(String(36), ForeignKey("majors.id"), nullable=True)
    enrollment_status = Column(String(30), nullable=False, default="pending_enrollment")
    points = Column(Integer, nullable=False, default=0)
    level_no = Column(Integer, nullable=False, default=1)
    total_learning_time = Column(Integer, nullable=False, default=0)
    total_assignments_submitted = Column(Integer, nullable=False, default=0)
    total_assignments_graded = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="student_profile")
    academic_year = relationship("AcademicYear", back_populates="student_profiles")
    major = relationship("Major", back_populates="student_profiles")

    def __repr__(self):
        return f"<StudentProfile(user_id='{self.user_id}', mssv='{self.mssv}')>"