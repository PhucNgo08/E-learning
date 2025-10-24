from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from app.database.connection import Base
from datetime import datetime

class Discussion(Base):
    __tablename__ = "discussions"

    id = Column(String(36), primary_key=True)
    course_id = Column(String(36), ForeignKey("courses.id"))
    user_id = Column(String(36), ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
