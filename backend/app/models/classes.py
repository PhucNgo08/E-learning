from sqlalchemy import (
    Column, String, Integer, Date, DateTime, ForeignKey, Enum
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
import uuid   # 🚀 KHÔNG CẦN uuid_gen.py NỮA


class Class(Base):
    __tablename__ = "classes"
    __table_args__ = {"extend_existing": True}

    id = Column(
        String(36),
        primary_key=True,
        index=True,
        default=lambda: str(uuid.uuid4())   # 🚀 UUID trực tiếp
    )

    class_code = Column(String(20), unique=True, index=True, nullable=False)
    class_name = Column(String(100), nullable=False)

    class_type = Column(
        Enum("official", "club", "course", "temporary",
             name="class_type_enum"),
        default="official"
    )

    academic_year_id = Column(String(36), ForeignKey("academic_years.id"))
    major_id = Column(String(36), ForeignKey("majors.id"))
    homeroom_teacher_id = Column(String(36), ForeignKey("users.id"))

    grade_level = Column(Integer)

    max_students = Column(Integer, default=50)
    current_students = Column(Integer, default=0)

    status = Column(
        Enum("planning", "open_for_enrollment", "active",
             "completed", "cancelled", name="class_status_enum"),
        default="planning"
    )

    start_date = Column(Date)
    end_date = Column(Date)
    enrollment_start = Column(Date)
    enrollment_end = Column(Date)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    academic_year = relationship("AcademicYear", back_populates="classes")
    major = relationship("Major", back_populates="classes")
    homeroom_teacher = relationship(
        "User",
        back_populates="homeroom_classes",
        foreign_keys=[homeroom_teacher_id]
    )

    enrollments = relationship(
        "Enrollment",
        back_populates="clazz",
        cascade="all, delete-orphan"
    )

    class_schedules = relationship(
        "ClassSchedule",
        back_populates="clazz",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Class(code={self.class_code}, name={self.class_name}, status={self.status})>"
