from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database.connection import Base


def uuid_str():
    return str(uuid.uuid4())


class CourseMaterial(Base):
    __tablename__ = "course_materials"

    id = Column(String(36), primary_key=True, default=uuid_str)

    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)

    title = Column(String(200), nullable=False)
    description = Column(Text)

    file_name = Column(String(255))
    file_url = Column(String(500), nullable=True)
    file_size = Column(BigInteger, default=0)
    file_format = Column(String(20))
    mime_type = Column(String(100))

    # Sửa ở đây
    material_type = Column(String(30), nullable=False, default="slide")

    download_count = Column(Integer, default=0)
    last_download_at = Column(DateTime, nullable=True)

    version = Column(String(20), default="1.0")
    is_public = Column(Integer, default=0)

    available_from = Column(DateTime)
    available_to = Column(DateTime)

    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    course = relationship("Course", back_populates="materials", lazy="joined")

    versions = relationship(
        "CourseMaterialVersion",
        back_populates="material",
        cascade="all, delete-orphan",
        order_by="desc(CourseMaterialVersion.created_at)"
    )

    def __repr__(self):
        return f"<CourseMaterial(title='{self.title}', version='{self.version}')>"