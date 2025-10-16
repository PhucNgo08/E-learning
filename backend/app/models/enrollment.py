from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, DECIMAL
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime
import uuid

def uuid_str():
    return str(uuid.uuid4())

class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(String(36), primary_key=True, default=uuid_str)
    user_id = Column(String(36), ForeignKey("users.id"))
    course_id = Column(String(36), ForeignKey("courses.id"))  # ✅ thêm dòng này
    class_id = Column(String(36), ForeignKey("classes.id"), nullable=True)

    enrollment_type = Column(
        Enum("official", "elective", "audit", "temporary", "student", "teacher", name="enrollment_type_enum"),
        default="official"
    )
    enrollment_status = Column(
        Enum("applied", "approved", "rejected", "active", "completed", "dropped", "transferred", name="enrollment_status_enum"),
        default="applied"
    )

    applied_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    enrolled_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    approved_by = Column(String(36), nullable=True)

    final_grade = Column(DECIMAL(5, 2))
    grade_letter = Column(String(5), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ✅ Quan hệ ORM
    user = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
    clazz = relationship("Class", back_populates="enrollments")

    def __repr__(self):
        return f"<Enrollment(user_id={self.user_id}, course_id={self.course_id})>"
