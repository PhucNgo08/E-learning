from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, Enum,
    DECIMAL, Boolean
)
from sqlalchemy.orm import relationship
from app.database.connection import Base
    # ❗ Nếu bạn chưa import Boolean → thêm ở đây
from datetime import datetime


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(String(36), primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(String(500))

    # ==========================
    # Loại quiz + độ khó
    # ==========================
    quiz_type = Column(Enum("practice", "graded", "survey", name="quiz_type_enum"), default="practice")
    difficulty_level = Column(Enum("easy", "medium", "hard", name="difficulty_enum"), default="medium")

    # ==========================
    # Cấu hình kỳ thi
    # ==========================
    time_limit_minutes = Column(Integer)                      # ⏱ Thời gian làm bài
    max_attempts = Column(Integer, default=1)                 # 🔁 Số lần làm bài
    passing_score = Column(DECIMAL(5, 2), default=60.00)      # 📊 Điểm qua môn
    total_questions = Column(Integer, nullable=False)

    # ==========================
    # Các tuỳ chọn hiển thị (BỊ THIẾU)
    # ==========================
    show_correct_answers = Column(Boolean, default=True)      # 👀 Xem đáp án sau khi nộp
    randomize_questions = Column(Boolean, default=False)      # 🔀 Xáo trộn câu hỏi
    randomize_options = Column(Boolean, default=False)        # 🔀 Xáo trộn lựa chọn

    # ==========================
    # Liên kết
    # ==========================
    lesson_id = Column(String(36), ForeignKey("lessons.id"))
    course_id = Column(String(36), ForeignKey("courses.id"))

    # ==========================
    # Thời gian mở/đóng bài thi
    # ==========================
    available_from = Column(DateTime)
    available_to = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # =====================================================
    # ORM RELATIONSHIPS
    # =====================================================
    lesson = relationship("Lesson", backref="quizzes")
    course = relationship("Course", backref="quizzes")

    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Quiz(title='{self.title}', type='{self.quiz_type}', difficulty='{self.difficulty_level}')>"
