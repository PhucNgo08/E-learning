from sqlalchemy import Column, String, Integer, DateTime, Enum, Text
from app.database.connection import Base
from datetime import datetime

class BackupHistory(Base):
    __tablename__ = 'backup_history'

    id = Column(String(36), primary_key=True)
    backup_type = Column(Enum('full', 'incremental', 'differential', name='backup_type_enum'), default='full')
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, default=0)
    database_name = Column(String(100), nullable=False)

    table_count = Column(Integer, default=0)
    total_records = Column(Integer, default=0)
    backup_start = Column(DateTime, nullable=False)
    backup_end = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer)

    status = Column(Enum('in_progress', 'completed', 'failed', 'verified', name='backup_status_enum'), default='in_progress')
    checksum = Column(String(64))
    error_message = Column(Text, nullable=True)

    retention_days = Column(Integer, default=30)
    scheduled_backup_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
