from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship  # Thêm import này
from app.database.connection import Base

from datetime import datetime

class ApiRequestLog(Base):
    __tablename__ = 'api_request_logs'

    id = Column(String(36), primary_key=True)
    endpoint_id = Column(String(36), ForeignKey("api_endpoints.id"))
    user_id = Column(String(36), ForeignKey("users.id"))
    ip_address = Column(String(45), nullable=False)
    user_agent = Column(String(500))

    method = Column(String(10), nullable=False)
    path = Column(String(500), nullable=False)
    query_params = Column(String(500))
    request_size = Column(Integer, default=0)

    status_code = Column(Integer)
    response_size = Column(Integer, default=0)
    response_time_ms = Column(Integer, default=0)

    was_rate_limited = Column(Integer, default=0)
    rate_limit_remaining = Column(Integer, default=0)

    requested_at = Column(DateTime, default=datetime.utcnow)

    # Các relationship đã được định nghĩa tại đây
    endpoint = relationship("ApiEndpoint", backref="request_logs")
    user = relationship("User", backref="request_logs")
