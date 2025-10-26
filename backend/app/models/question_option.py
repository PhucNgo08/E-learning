from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime


class QuestionOption(Base):
    __tablename__ = "question_options"

    id = Column(String(36), primary_key=True)
    question_id = Column(String(36), ForeignKey("questions.id"))
    option_text = Column(String(500), nullable=False)
    is_correct = Column(Integer, default=0)
    option_order = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    # ✅ Liên kết với Question (1 câu hỏi có nhiều lựa chọn)
    question = relationship("Question", back_populates="options")

    # ✅ Liên kết với AttemptAnswer (1 lựa chọn có thể xuất hiện trong nhiều bài làm)
    attempt_answers = relationship(
        "AttemptAnswer",
        back_populates="selected_option",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<QuestionOption(text='{self.option_text[:30]}...', is_correct={self.is_correct})>"
