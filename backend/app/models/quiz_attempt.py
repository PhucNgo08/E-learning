from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, DECIMAL, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)   # Người làm bài
    quiz_id = Column(String(36), ForeignKey("quizzes.id"), nullable=False)
    graded_by = Column(String(36), ForeignKey("users.id"), nullable=True)  # Người chấm bài (nếu có)

    attempt_number = Column(Integer, default=1)
    score = Column(DECIMAL(5, 2))
    total_questions = Column(Integer)
    correct_answers = Column(Integer)
    time_spent_seconds = Column(Integer)

    status = Column(
        Enum("in_progress", "submitted", "graded", name="quiz_attempt_status_enum"),
        default="in_progress",
    )
    started_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    graded_at = Column(DateTime, nullable=True)
    teacher_feedback = Column(String(500))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # =====================================================
    # 🔹 QUAN HỆ ORM
    # =====================================================

    # 👉 1 Quiz có nhiều Attempt
    quiz = relationship("Quiz", back_populates="attempts")

    # 👉 Người làm bài
    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="quiz_attempts",
        overlaps="graded_quiz_attempts",
    )

    # 👉 Người chấm bài (giáo viên)
    graded_by_user = relationship(
        "User",
        foreign_keys=[graded_by],
        back_populates="graded_quiz_attempts",
        overlaps="quiz_attempts",
    )

    # 👉 Attempt có nhiều câu trả lời
    answers = relationship(
        "AttemptAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<QuizAttempt(user_id={self.user_id}, quiz_id={self.quiz_id}, score={self.score})>"
