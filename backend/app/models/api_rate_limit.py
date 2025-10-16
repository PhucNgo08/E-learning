from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database.connection import Base

from datetime import datetime

class ApiRateLimit(Base):
    __tablename__ = 'api_rate_limits'

    id = Column(String(36), primary_key=True)
    identifier = Column(String(255), nullable=False)
    endpoint_id = Column(String(36), ForeignKey("api_endpoints.id"))
    window_start = Column(DateTime, nullable=False)
    request_count = Column(Integer, default=0)

    window_type = Column(Enum('minute', 'hour', 'day', name='window_type_enum'), default='minute')

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    endpoint = relationship("ApiEndpoint", backref="rate_limits")
