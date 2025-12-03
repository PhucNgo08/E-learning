from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, Enum,
    DECIMAL, Boolean, Text
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base


class Quiz(Base):
    __tablename__ = "quizzes"

    # ======================================
    # 🔑 Thông tin cơ bản
    # ======================================
    id = Column(String(36), primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)

    # ======================================
    # 🔧 Loại quiz & độ khó
    # ======================================
    quiz_type = Column(
        Enum("practice", "graded", "survey", name="quiz_type_enum"),
        default="practice"
    )
    difficulty_level = Column(
        Enum("easy", "medium", "hard", name="quiz_difficulty_enum"),
        default="medium"
    )

    # ======================================
    # ⚙️ Cấu hình đề thi
    # ======================================
    time_limit_minutes = Column(Integer)
    max_attempts = Column(Integer, default=1)
    passing_score = Column(DECIMAL(5, 2), default=60.00)
    total_questions = Column(Integer, nullable=False)

    # ======================================
    # 🎛 Tùy chọn hiển thị
    # ======================================
    show_correct_answers = Column(Boolean, default=True)
    randomize_questions = Column(Boolean, default=False)
    randomize_options = Column(Boolean, default=False)

    # ======================================
    # 🛡 Phê duyệt & trạng thái
    # ======================================
    status = Column(String(20), default="pending")
    is_approved = Column(Boolean, default=False)

    # ======================================
    # 🔗 Quan hệ khoá ngoại
    # ======================================

    # ❗ Thêm lesson_id (bắt buộc vì backend tạo quiz theo bài học)
    lesson_id = Column(String(36), ForeignKey("lessons.id"), nullable=True)
    lesson = relationship("Lesson", back_populates="quizzes")

    course_id = Column(String(36), ForeignKey("courses.id"))
    course = relationship("Course", back_populates="quizzes")

    # ======================================
    # 🧩 Quan hệ câu hỏi / attempt
    # ======================================
    questions = relationship(
        "Question",
        back_populates="quiz",
        cascade="all, delete-orphan"
    )

    attempts = relationship(
        "QuizAttempt",
        back_populates="quiz",
        cascade="all, delete-orphan"
    )

    # ======================================
    # ⏳ Thời gian mở / đóng bài thi
    # ======================================
    available_from = Column(DateTime)
    available_to = Column(DateTime)

    # ======================================
    # 🕒 Timestamp
    # ======================================
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


    def __repr__(self):
        return f"<Quiz title={self.title} type={self.quiz_type} approved={self.is_approved}>"
