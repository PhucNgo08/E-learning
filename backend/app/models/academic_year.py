import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.connection import Base


class AcademicYear(Base):
    __tablename__ = "academic_years"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    year_code = Column(String(10), unique=True, nullable=False)
    year_name = Column(String(100), nullable=False)
    start_year = Column(Integer, nullable=False)
    end_year = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    student_profiles = relationship("StudentProfile", back_populates="academic_year")
    classes = relationship("Class", back_populates="academic_year")
    courses = relationship("Course", back_populates="academic_year")

    def __repr__(self):
        return (
            f"<AcademicYear(year_code='{self.year_code}', "
            f"year_name='{self.year_name}', is_active={self.is_active})>"
        )