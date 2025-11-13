"""
==========================================================
📁 MODEL: FileStorage
Quản lý thông tin file tải lên hệ thống (theo bảng file_storage)
==========================================================
"""

from sqlalchemy import (
    Column, String, Integer, BigInteger, DateTime, ForeignKey, Enum
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
import uuid


def uuid_str():
    """Tạo UUID ngẫu nhiên dạng chuỗi"""
    return str(uuid.uuid4())


class FileStorage(Base):
    __tablename__ = 'file_storage'

    id = Column(String(36), primary_key=True, default=uuid_str)
    file_name = Column(String(255), nullable=False)
    original_name = Column(String(255))
    file_path = Column(String(500), nullable=False)
    file_url = Column(String(500), nullable=False)

    file_size = Column(BigInteger, nullable=False, default=0)
    file_type = Column(String(100))
    file_extension = Column(String(20))
    dimensions = Column(String(50))
    duration_seconds = Column(Integer)

    storage_provider = Column(
        Enum('local', 's3', 'cdn', 'google_drive', name='storage_provider_enum'),
        default='local'
    )
    bucket_name = Column(String(100))
    storage_class = Column(String(50), default='standard')

    is_optimized = Column(Integer, default=0)
    optimized_size = Column(BigInteger, default=0)
    optimization_algorithm = Column(String(50))

    is_public = Column(Integer, default=0)
    access_token = Column(String(100))
    expires_at = Column(DateTime)

    download_count = Column(Integer, default=0)
    last_accessed = Column(DateTime)

    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    related_entity_type = Column(String(50))
    related_entity_id = Column(String(36))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 🔗 Quan hệ
    uploaded_by_user = relationship("User", backref="uploaded_files")
    cdn_cache = relationship("CDNCache", back_populates="file", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<FileStorage(id={self.id}, name='{self.file_name}', size={self.file_size})>"
