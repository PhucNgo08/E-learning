"""
==========================================================
🌍 MODEL: CDNCache
Quản lý cache CDN cho file, theo bảng `cdn_cache`
==========================================================
"""

from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, Enum
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
import uuid


def uuid_str():
    """Sinh UUID tự động"""
    return str(uuid.uuid4())


class CDNCache(Base):
    __tablename__ = "cdn_cache"

    id = Column(String(36), primary_key=True, default=uuid_str)
    file_id = Column(String(36), ForeignKey("file_storage.id", ondelete="CASCADE"), nullable=False)

    cdn_url = Column(String(500), nullable=False)
    cdn_provider = Column(String(50), default="cloudflare")

    cache_status = Column(
        Enum("miss", "hit", "refresh", name="cdn_cache_status_enum"),
        default="miss"
    )
    cache_key = Column(String(255))
    cache_control = Column(String(100), default="public, max-age=3600")

    load_time_ms = Column(Integer, default=0)
    cache_hit_count = Column(Integer, default=0)
    last_cache_hit = Column(DateTime)

    purged_at = Column(DateTime)
    purge_reason = Column(String(100))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 🔗 Quan hệ ngược lại FileStorage
    file = relationship("FileStorage", back_populates="cdn_cache")

    def __repr__(self):
        return f"<CDNCache(id={self.id}, file_id={self.file_id}, status={self.cache_status})>"
