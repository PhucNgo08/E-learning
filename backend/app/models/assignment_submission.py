from sqlalchemy import (
    Column, String, Text, DateTime, DECIMAL, Enum, ForeignKey
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
import uuid


def uuid_str():
    return str(uuid.uuid4())


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"

    id = Column(String(36), primary_key=True, default=uuid_str)
    assignment_id = Column(String(36), ForeignKey("assignments.id"), nullable=False)
    student_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    group_id = Column(String(36), ForeignKey("assignment_groups.id"), nullable=True)

    submission_text = Column(Text)
    submission_time = Column(DateTime, default=datetime.utcnow)
    status = Column(
        Enum("submitted", "graded", "late", "resubmitted", name="submission_status_enum"),
        default="submitted"
    )

    grade = Column(DECIMAL(5, 2))
    feedback = Column(Text)
    graded_by = Column(String(36), ForeignKey("users.id"))
    graded_at = Column(DateTime)

    # 🔗 Quan hệ
    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("User", foreign_keys=[student_id], back_populates="assignment_submissions")
    grader = relationship("User", foreign_keys=[graded_by])
    files = relationship("AssignmentFile", back_populates="submission", cascade="all, delete")

    def __repr__(self):
        return f"<AssignmentSubmission(assignment_id='{self.assignment_id}', student_id='{self.student_id}')>"
