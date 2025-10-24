from sqlalchemy import (
    Column, String, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
import uuid


def uuid_str():
    return str(uuid.uuid4())


class AssignmentGroup(Base):
    __tablename__ = "assignment_groups"

    id = Column(String(36), primary_key=True, default=uuid_str)
    assignment_id = Column(String(36), ForeignKey("assignments.id"), nullable=False)
    group_name = Column(String(100))
    leader_id = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    # 🔗 Quan hệ
    leader = relationship("User", back_populates="assignment_groups_led")
    assignment = relationship("Assignment")

    def __repr__(self):
        return f"<AssignmentGroup(group_name='{self.group_name}', assignment_id='{self.assignment_id}')>"
