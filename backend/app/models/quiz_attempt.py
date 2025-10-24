# app/models/quiz_attempt.py
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, DECIMAL, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base

class QuizAttempt(Base):
    __tablename__ = 'quiz_attempts'

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"))      # Người làm bài
    quiz_id = Column(String(36), ForeignKey("quizzes.id"))
    graded_by = Column(String(36), ForeignKey("users.id"))    # Người chấm bài

    attempt_number = Column(Integer, default=1)
    score = Column(DECIMAL(5, 2))
    total_questions = Column(Integer)
    correct_answers = Column(Integer)
    time_spent_seconds = Column(Integer)

    status = Column(Enum('in_progress', 'submitted', 'graded', name='quiz_attempt_status_enum'), default='in_progress')
    started_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    graded_at = Column(DateTime, nullable=True)
    teacher_feedback = Column(String(500))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # === Quan hệ ORM ===
    quiz = relationship("Quiz", backref="quiz_attempts")

    # 🔹 Người làm bài
    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="quiz_attempts",
        overlaps="graded_quiz_attempts"
    )

    # 🔹 Người chấm bài (giáo viên)
    graded_by_user = relationship(
        "User",
        foreign_keys=[graded_by],
        back_populates="graded_quiz_attempts",
        overlaps="quiz_attempts"
    )

    def __repr__(self):
        return f"<QuizAttempt(user_id={self.user_id}, quiz_id={self.quiz_id}, score={self.score})>"
