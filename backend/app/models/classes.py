from datetime import datetime
import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.connection import Base


class Class(Base):
    __tablename__ = "classes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    class_code = Column(String(20), unique=True, nullable=False)
    class_name = Column(String(100), nullable=False)
    class_type = Column(String(30), nullable=False, default="official")

    academic_year_id = Column(String(36), ForeignKey("academic_years.id"))
    major_id = Column(String(36), ForeignKey("majors.id"))
    homeroom_teacher_id = Column(String(36), ForeignKey("users.id"))

    grade_level = Column(Integer)
    max_students = Column(Integer, nullable=False, default=50)
    current_students = Column(Integer, nullable=False, default=0)
    status = Column(String(30), nullable=False, default="planning")

    start_date = Column(Date)
    end_date = Column(Date)
    enrollment_start = Column(Date)
    enrollment_end = Column(Date)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    academic_year = relationship("AcademicYear", back_populates="classes")
    major = relationship("Major", back_populates="classes")

    homeroom_teacher = relationship(
        "User",
        back_populates="homeroom_classes",
        foreign_keys=[homeroom_teacher_id],
    )

    class_enrollments = relationship(
        "ClassEnrollment",
        back_populates="clazz",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Class(code='{self.class_code}', name='{self.class_name}', status='{self.status}')>"