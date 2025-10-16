from sqlalchemy import Column, String, Integer, DateTime, Enum
from app.database.connection import Base

from datetime import datetime

class ApiEndpoint(Base):
    __tablename__ = 'api_endpoints'

    id = Column(String(36), primary_key=True)
    endpoint_path = Column(String(500), nullable=False)
    method = Column(Enum('GET', 'POST', 'PUT', 'DELETE', 'PATCH', name='method_enum'), default='GET')
    description = Column(String(500))

    requests_per_minute = Column(Integer, default=60)
    requests_per_hour = Column(Integer, default=1000)
    requests_per_day = Column(Integer, default=10000)

    burst_limit = Column(Integer, default=10)
    burst_window_seconds = Column(Integer, default=60)

    requires_auth = Column(Integer, default=1)
    allowed_roles = Column(String(500))

    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
