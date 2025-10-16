from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from app.database.connection import Base

from datetime import datetime

class AttemptAnswer(Base):
    __tablename__ = 'attempt_answers'

    id = Column(String(36), primary_key=True)
    attempt_id = Column(String(36), ForeignKey("quiz_attempts.id"))
    question_id = Column(String(36), ForeignKey("questions.id"))
    selected_option_id = Column(String(36), ForeignKey("question_options.id"))
    answer_text = Column(String(500))
    is_correct = Column(Integer)
    points_earned = Column(DECIMAL(5, 2), default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    attempt = relationship("QuizAttempt", backref="attempt_answers")
    question = relationship("Question", backref="attempt_answers")
    selected_option = relationship("QuestionOption", backref="attempt_answers")
