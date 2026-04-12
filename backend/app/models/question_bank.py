from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, DECIMAL, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime


class QuestionBank(Base):
    __tablename__ = "question_bank"

    id = Column(String(36), primary_key=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(
        Enum("multiple_choice", "true_false", "essay", "fill_blank", name="question_type_enum"),
        default="multiple_choice"
    )
    difficulty_level = Column(
        Enum("easy", "medium", "hard", name="difficulty_enum"),
        default="medium"
    )
    points = Column(DECIMAL(5, 2), default=1.00)

    tags = Column(Text)
    learning_objectives = Column(Text)
    estimated_time = Column(Integer)

    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    department = Column(String(100))
    is_public = Column(Integer, default=0)

    usage_count = Column(Integer, default=0)
    average_score = Column(DECIMAL(5, 2), default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by_user = relationship("User", backref="question_banks")
    options = relationship(
        "QuestionBankOption",
        back_populates="question_bank",
        cascade="all, delete-orphan"
    )