from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime


class QuestionOption(Base):
    __tablename__ = "question_options"

    id = Column(String(36), primary_key=True)

    question_id = Column(
        String(36),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False
    )

    option_text = Column(Text, nullable=False)
    is_correct = Column(Integer, default=0)
    option_order = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)

    question = relationship("Question", back_populates="options")

    attempt_answers = relationship(
        "AttemptAnswer",
        back_populates="selected_option",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        preview = self.option_text[:30] if self.option_text else ""
        return f"<QuestionOption(text='{preview}...', is_correct={self.is_correct})>"