from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime


class QuizTemplate(Base):
    __tablename__ = 'quiz_templates'

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))

    rules = Column(String(500), nullable=False)
    question_types = Column(String(500))
    tags_filter = Column(String(500))

    time_limit_minutes = Column(Integer)
    passing_score = Column(DECIMAL(5, 2), default=60.00)
    randomize_questions = Column(Integer, default=1)

    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    is_public = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 🔥 Chuẩn quan hệ 2 chiều User <-> QuizTemplate
    creator = relationship("User", back_populates="quiz_templates")

    # 🔥 Dùng cho template Jinja: t.created_by_user
    @property
    def created_by_user(self):
        return self.creator
