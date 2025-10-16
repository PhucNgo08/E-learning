from sqlalchemy import Column, String, Text, DateTime
from datetime import datetime
from app.database.connection import Base

class SystemSetting(Base):
    __tablename__ = "system_settings"

    setting_key = Column(String(100), primary_key=True)
    setting_value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)
