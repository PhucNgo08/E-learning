from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base


class AcademicYear(Base):
    __tablename__ = "academic_years"

    id = Column(String(36), primary_key=True)
    year_code = Column(String(4), unique=True, nullable=False)
    year_name = Column(String(50), nullable=False)
    start_year = Column(Integer, nullable=False)
    end_year = Column(Integer, nullable=False)
    is_active = Column(Integer, default=1)  # ✅ TINYINT trong MySQL
    created_at = Column(DateTime, default=datetime.utcnow)

    # === Quan hệ ORM ===
    users = relationship("User", back_populates="academic_year", cascade="all, delete-orphan")
    classes = relationship("Class", back_populates="academic_year", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="academic_year", cascade="all, delete-orphan")


    def __repr__(self):
        return f"<AcademicYear(year_code={self.year_code}, year_name={self.year_name}, is_active={self.is_active})>"
