# app/models/quiz_attempt.py
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, DECIMAL, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base

class QuizAttempt(Base):
    __tablename__ = 'quiz_attempts'

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"))  # Foreign key đến bảng User
    quiz_id = Column(String(36), ForeignKey("quizzes.id"))

    attempt_number = Column(Integer, default=1)
    score = Column(DECIMAL(5, 2))
    total_questions = Column(Integer)
    correct_answers = Column(Integer)
    time_spent_seconds = Column(Integer)

    status = Column(Enum('in_progress', 'submitted', 'graded', name='quiz_attempt_status_enum'), default='in_progress')
    started_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)

    graded_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    graded_at = Column(DateTime, nullable=True)
    teacher_feedback = Column(String(500))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Quan hệ với User (người làm bài quiz)
    user = relationship("User", foreign_keys=[user_id])  # Không sử dụng backref nữa

    # Quan hệ với Quiz
    quiz = relationship("Quiz", backref="quiz_attempts")

    # Quan hệ với User (người chấm bài)
    graded_by_user = relationship("User", backref="graded_quiz_attempts", foreign_keys=[graded_by])
