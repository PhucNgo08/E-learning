from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Integer, DECIMAL, Enum
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
import uuid


def uuid_str():
    return str(uuid.uuid4())


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(String(36), primary_key=True, default=uuid_str)

    title = Column(String(255), nullable=False)
    description = Column(Text)

    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)
    module_id = Column(String(36), ForeignKey("modules.id"), nullable=True)
    teacher_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    submission_type = Column(
        Enum("individual", "group", name="submission_type_enum"),
        default="individual"
    )
    allowed_file_types = Column(String(200))
    max_files = Column(Integer, default=5)
    max_file_size_mb = Column(Integer, default=50)

    start_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    allow_late_submission = Column(Integer, default=0)
    late_penalty_percent = Column(DECIMAL(5, 2), default=0)
    total_points = Column(DECIMAL(5, 2), default=10)
    grading_criteria = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    course = relationship("Course", back_populates="assignments")
    module = relationship("Module", back_populates="assignments")
    teacher = relationship("User", back_populates="assignments_created")
    submissions = relationship(
        "AssignmentSubmission",
        back_populates="assignment",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Assignment(title='{self.title}', course_id='{self.course_id}')>"