from sqlalchemy import Column, String, Integer, DateTime, Enum
from app.database.connection import Base

from datetime import datetime

class BackupSchedule(Base):
    __tablename__ = 'backup_schedules'

    id = Column(String(36), primary_key=True)
    schedule_name = Column(String(100), nullable=False)
    backup_type = Column(Enum('full', 'incremental', name='backup_type_enum'), default='full')

    frequency = Column(Enum('daily', 'weekly', 'monthly', name='backup_frequency_enum'), default='daily')
    frequency_detail = Column(String(500))

    preferred_start_time = Column(String(8), default='02:00:00')
    max_duration_minutes = Column(Integer, default=240)

    retention_days = Column(Integer, default=30)
    keep_last_n = Column(Integer, default=10)

    notify_on_success = Column(Integer, default=0)
    notify_on_failure = Column(Integer, default=1)
    notification_emails = Column(String(500))

    is_active = Column(Integer, default=1)
    last_run = Column(DateTime, nullable=True)
    last_status = Column(Enum('success', 'failed', 'running', name='last_status_enum'), default='success')

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
