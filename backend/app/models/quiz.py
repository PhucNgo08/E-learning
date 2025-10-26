from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, DECIMAL
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(String(36), primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(String(500))

    quiz_type = Column(Enum("practice", "graded", "survey", name="quiz_type_enum"), default="practice")
    difficulty_level = Column(Enum("easy", "medium", "hard", name="difficulty_enum"), default="medium")

    time_limit_minutes = Column(Integer)
    max_attempts = Column(Integer, default=1)
    passing_score = Column(DECIMAL(5, 2), default=60.00)
    total_questions = Column(Integer, nullable=False)

    lesson_id = Column(String(36), ForeignKey("lessons.id"))
    course_id = Column(String(36), ForeignKey("courses.id"))

    available_from = Column(DateTime)
    available_to = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # =====================================================
    # 🔹 QUAN HỆ ORM
    # =====================================================
    lesson = relationship("Lesson", backref="quizzes")
    course = relationship("Course", backref="quizzes")

    # ✅ CHỈNH SỬA CHÍNH: dùng back_populates thay vì backref
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")

    # ✅ Liên kết với QuizAttempt
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Quiz(title='{self.title}', type='{self.quiz_type}', difficulty='{self.difficulty_level}')>"
