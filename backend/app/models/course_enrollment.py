from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, DECIMAL, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.connection import Base


def uuid_str() -> str:
    return str(uuid.uuid4())


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    __table_args__ = (
        UniqueConstraint("course_id", "user_id", name="uq_course_enrollments"),
    )

    id = Column(String(36), primary_key=True, default=uuid_str)
    course_id = Column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    enrollment_status = Column(String(30), nullable=False, default="active")
    enrollment_source = Column(String(30), nullable=False, default="manual")
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    enrolled_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    final_grade = Column(DECIMAL(5, 2), nullable=True)
    grade_letter = Column(String(5), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    course = relationship("Course", back_populates="course_enrollments")
    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="course_enrollments",
    )
    approved_user = relationship(
        "User",
        foreign_keys=[approved_by],
        back_populates="approved_course_enrollments",
    )

    def __repr__(self) -> str:
        return (
            f"<CourseEnrollment course_id={self.course_id} "
            f"user_id={self.user_id} status={self.enrollment_status}>"
        )