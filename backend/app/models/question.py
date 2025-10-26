from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, DECIMAL
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime

class Question(Base):
    __tablename__ = "questions"

    id = Column(String(36), primary_key=True)
    quiz_id = Column(String(36), ForeignKey("quizzes.id"))

    question_type = Column(
        Enum("multiple_choice", "true_false", "essay", name="question_type_enum"),
        default="multiple_choice",
    )
    question_text = Column(String(500), nullable=False)
    explanation = Column(String(500))
    points = Column(DECIMAL(5, 2), default=1.00)
    difficulty_level = Column(Enum("easy", "medium", "hard", name="difficulty_enum"), default="medium")
    question_order = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ✅ Quan hệ với Quiz
    quiz = relationship("Quiz", back_populates="questions")

    # ✅ Quan hệ với QuestionOption (SỬA: dùng back_populates thay backref)
    options = relationship("QuestionOption", back_populates="question", cascade="all, delete-orphan")

    # ✅ Quan hệ với AttemptAnswer
    attempt_answers = relationship("AttemptAnswer", back_populates="question", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Question(text='{self.question_text[:30]}...', quiz_id='{self.quiz_id}')>"
