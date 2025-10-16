from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship  # Thêm import này
from app.database.connection import Base

from datetime import datetime

class CdnCache(Base):
    __tablename__ = 'cdn_cache'

    id = Column(String(36), primary_key=True)
    file_id = Column(String(36), ForeignKey("file_storage.id"))
    cdn_url = Column(String(500), nullable=False)
    cdn_provider = Column(String(50), default='cloudflare')

    cache_status = Column(Enum('miss', 'hit', 'refresh', name='cache_status_enum'), default='miss')
    cache_key = Column(String(255))
    cache_control = Column(String(100), default='public, max-age=3600')

    load_time_ms = Column(Integer, default=0)
    cache_hit_count = Column(Integer, default=0)
    last_cache_hit = Column(DateTime)

    purged_at = Column(DateTime)
    purge_reason = Column(String(100))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    file = relationship("FileStorage", backref="cdn_cache")
