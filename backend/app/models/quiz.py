from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, DECIMAL
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime

class Quiz(Base):
    __tablename__ = 'quizzes'

    id = Column(String(36), primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(String(500))

    quiz_type = Column(Enum('practice', 'graded', 'survey', name='quiz_type_enum'), default='practice')
    difficulty_level = Column(Enum('easy', 'medium', 'hard', name='difficulty_enum'), default='medium')
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

    lesson = relationship("Lesson", backref="quizzes")
    course = relationship("Course", backref="quizzes")
