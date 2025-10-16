from sqlalchemy import Column, String, Integer, Text, DateTime
from app.database.connection import Base
from datetime import datetime

class Report(Base):
    __tablename__ = 'reports'

    # Các trường của bảng reports
    id = Column(String(36), primary_key=True)
    report_name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Report(id={self.id}, report_name={self.report_name})>"
