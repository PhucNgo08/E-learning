from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime


class QuestionBankOption(Base):
    __tablename__ = "question_bank_options"

    id = Column(String(36), primary_key=True)
    question_bank_id = Column(
        String(36),
        ForeignKey("question_bank.id", ondelete="CASCADE"),
        nullable=False
    )
    option_text = Column(Text, nullable=False)
    is_correct = Column(Integer, default=0)
    option_order = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    question_bank = relationship("QuestionBank", back_populates="options")

    def __repr__(self):
        return f"<QuestionBankOption(text='{self.option_text[:30]}...', is_correct={self.is_correct})>"