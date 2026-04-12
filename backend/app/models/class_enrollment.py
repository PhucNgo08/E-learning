from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.connection import Base


def uuid_str() -> str:
    return str(uuid.uuid4())


class ClassEnrollment(Base):
    __tablename__ = "class_enrollments"
    __table_args__ = (
        UniqueConstraint("class_id", "student_id", name="uq_class_enrollments"),
    )

    id = Column(String(36), primary_key=True, default=uuid_str)
    class_id = Column(
        String(36),
        ForeignKey("classes.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    enrollment_status = Column(String(30), nullable=False, default="applied")
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    joined_at = Column(DateTime, nullable=True)
    left_at = Column(DateTime, nullable=True)
    note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    clazz = relationship("Class", back_populates="class_enrollments")
    student = relationship(
        "User",
        foreign_keys=[student_id],
        back_populates="class_enrollments",
    )
    approved_user = relationship(
        "User",
        foreign_keys=[approved_by],
        back_populates="approved_class_enrollments",
    )

    def __repr__(self) -> str:
        return (
            f"<ClassEnrollment class_id={self.class_id} "
            f"student_id={self.student_id} status={self.enrollment_status}>"
        )