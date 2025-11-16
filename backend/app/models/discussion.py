from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
import uuid

def uuid_str():
    return str(uuid.uuid4())

class Discussion(Base):
    __tablename__ = "discussions"

    id = Column(String(36), primary_key=True, default=uuid_str)
    course_id = Column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    content = Column(Text, nullable=False)

    # ❗ PHẢI CÓ – KHỚP DATABASE & SERVICE
    parent_id = Column(String(36), ForeignKey("discussions.id", ondelete="CASCADE"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # ========== Relationships ==========
    user = relationship("User", back_populates="discussions")

    course = relationship("Course", back_populates="discussions")

    # Self-referential (reply)
    parent = relationship("Discussion", remote_side=[id], backref="children")

    def __repr__(self):
        return f"<Discussion id={self.id} parent_id={self.parent_id}>"
