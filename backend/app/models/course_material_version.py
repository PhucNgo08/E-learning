from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database.connection import Base


def uuid_str():
    return str(uuid.uuid4())


class CourseMaterialVersion(Base):
    __tablename__ = "course_material_versions"

    id = Column(String(36), primary_key=True, default=uuid_str)
    material_id = Column(
        String(36),
        ForeignKey("course_materials.id", ondelete="CASCADE"),
        nullable=False
    )

    # -------------------------
    # Thông tin file từng phiên bản
    # -------------------------
    version = Column(String(10), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_size = Column(BigInteger, default=0)
    file_format = Column(String(20))
    mime_type = Column(String(100))

    created_at = Column(DateTime, default=datetime.utcnow)

    # Quan hệ ngược
    material = relationship("CourseMaterial", back_populates="versions")

    def __repr__(self):
        return f"<MaterialVersion {self.version} - {self.file_name}>"
