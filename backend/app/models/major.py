import uuid

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.connection import Base


class Major(Base):
    __tablename__ = "majors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    major_code = Column(String(20), unique=True, nullable=False)
    major_name = Column(String(150), nullable=False)
    faculty_name = Column(String(150), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    student_profiles = relationship("StudentProfile", back_populates="major")
    teacher_profiles = relationship("TeacherProfile", back_populates="major")
    classes = relationship("Class", back_populates="major")
    courses = relationship("Course", back_populates="major")

    def __repr__(self):
        return (
            f"<Major(major_code='{self.major_code}', "
            f"major_name='{self.major_name}', is_active={self.is_active})>"
        )
