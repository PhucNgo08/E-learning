from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
import uuid


def uuid_str():
    return str(uuid.uuid4())


class AssignmentFile(Base):
    __tablename__ = "assignment_files"

    id = Column(String(36), primary_key=True, default=uuid_str)
    submission_id = Column(String(36), ForeignKey("assignment_submissions.id"), nullable=False)
    file_name = Column(String(255))
    file_url = Column(String(500))
    file_size = Column(Integer)
    file_type = Column(String(50))
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # 🔗 Quan hệ
    submission = relationship("AssignmentSubmission", back_populates="files")

    def __repr__(self):
        return f"<AssignmentFile(file_name='{self.file_name}', submission_id='{self.submission_id}')>"
