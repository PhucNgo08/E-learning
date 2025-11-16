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

    # FK
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(String(36), ForeignKey("classes.id", ondelete="CASCADE"), nullable=True)
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=True)

    enrollment_type = Column(
        Enum("official", "elective", "audit", "temporary", "student", "teacher",
             name="enrollment_type_enum"),
        default="official"
    )
    enrollment_status = Column(
        Enum("applied", "approved", "rejected", "active", "completed", "dropped", "transferred",
             name="enrollment_status_enum"),
        default="applied"
    )

    applied_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime)
    enrolled_at = Column(DateTime)
    completed_at = Column(DateTime)

    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)

    final_grade = Column(DECIMAL(5, 2))
    grade_letter = Column(String(5))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ========================
    # 🔗 RELATIONSHIPS FIXED
    # ========================
    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="enrollments"
    )

    approved_user = relationship(
        "User",
        foreign_keys=[approved_by],
        back_populates="approved_enrollments"
    )

    course = relationship("Course", back_populates="enrollments")

    clazz = relationship("Class", back_populates="enrollments")

    def __repr__(self):
        return f"<Enrollment(user_id={self.user_id}, course_id={self.course_id})>"
