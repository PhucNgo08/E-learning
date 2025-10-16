from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base

from datetime import datetime

class QuestionOption(Base):
    __tablename__ = 'question_options'

    id = Column(String(36), primary_key=True)
    question_id = Column(String(36), ForeignKey("questions.id"))
    option_text = Column(String(500), nullable=False)
    is_correct = Column(Integer, default=0)
    option_order = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)

    question = relationship("Question", backref="options")
