from sqlalchemy import Column, String, Integer, DateTime, DECIMAL,  Enum
from app.database.connection import Base

from datetime import datetime

class DatabaseHealthLog(Base):
    __tablename__ = 'database_health_logs'

    id = Column(String(36), primary_key=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(DECIMAL(15, 4), nullable=False)
    metric_unit = Column(String(20))

    details = Column(String(500))
    severity = Column(Enum('info', 'warning', 'critical', name='severity_enum'), default='info')

    measured_at = Column(DateTime, default=datetime.utcnow)
