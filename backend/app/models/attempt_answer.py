from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, DECIMAL, Boolean
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"

    id = Column(String(36), primary_key=True)
    attempt_id = Column(String(36), ForeignKey("quiz_attempts.id"), nullable=False)
    question_id = Column(String(36), ForeignKey("questions.id"), nullable=False)
    selected_option_id = Column(String(36), ForeignKey("question_options.id"), nullable=True)
    answer_text = Column(String(500), nullable=True)
    is_correct = Column(Boolean, default=False)
    points_earned = Column(DECIMAL(5, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # =====================================================
    # 🔹 QUAN HỆ ORM (2 chiều)
    # =====================================================
    attempt = relationship("QuizAttempt", back_populates="answers")
    question = relationship("Question", back_populates="attempt_answers")
    selected_option = relationship("QuestionOption", back_populates="attempt_answers")

    def __repr__(self):
        return f"<AttemptAnswer(question_id={self.question_id}, is_correct={self.is_correct})>"
