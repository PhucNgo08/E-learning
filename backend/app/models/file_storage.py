from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum
from app.database.connection import Base

from datetime import datetime
from sqlalchemy.orm import relationship  
class FileStorage(Base):
    __tablename__ = 'file_storage'

    id = Column(String(36), primary_key=True)
    file_name = Column(String(255), nullable=False)
    original_name = Column(String(255))
    file_path = Column(String(500), nullable=False)
    file_url = Column(String(500), nullable=False)
    
    file_size = Column(Integer, nullable=False, default=0)
    file_type = Column(String(100))
    file_extension = Column(String(20))
    dimensions = Column(String(50))
    duration_seconds = Column(Integer)

    storage_provider = Column(Enum('local', 's3', 'cdn', 'google_drive', name='storage_provider_enum'), default='local')
    bucket_name = Column(String(100))
    storage_class = Column(String(50), default='standard')

    is_optimized = Column(Integer, default=0)
    optimized_size = Column(Integer, default=0)
    optimization_algorithm = Column(String(50))

    is_public = Column(Integer, default=0)
    access_token = Column(String(100))
    expires_at = Column(DateTime)

    download_count = Column(Integer, default=0)
    last_accessed = Column(DateTime)

    uploaded_by = Column(String(36), ForeignKey("users.id"))
    related_entity_type = Column(String(50))
    related_entity_id = Column(String(36))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    uploaded_by_user = relationship("User", backref="file_storage")
