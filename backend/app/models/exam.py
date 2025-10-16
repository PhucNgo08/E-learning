# app/models/exam.py

from sqlalchemy import Column, String, Integer, DateTime
from app.database.connection import Base
from datetime import datetime
from app.database import get_db


class Exam(Base):
    __tablename__ = "exams"
    
    id = Column(String(36), primary_key=True)
    exam_name = Column(String(100), nullable=False)
    course_id = Column(String(36), nullable=False)
    exam_date = Column(DateTime, nullable=False)
    duration = Column(Integer, nullable=False)

    def __repr__(self):
        return f"<Exam(id={self.id}, exam_name={self.exam_name}, course_id={self.course_id})>"
