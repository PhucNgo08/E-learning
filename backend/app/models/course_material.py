from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Enum, BigInteger
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime
import uuid

def uuid_str():
    return str(uuid.uuid4())


class CourseMaterial(Base):
    __tablename__ = "course_materials"

    # 🧩 Khóa chính
    id = Column(String(36), primary_key=True, default=uuid_str)

    # 🔗 Liên kết khóa học
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)

    # 📘 Thông tin file
    title = Column(String(200), nullable=False)
    description = Column(Text)
    file_name = Column(String(255))
    file_url = Column(String(500), nullable=False)
    file_size = Column(BigInteger, default=0)  # ⚡ dùng BigInteger thay Integer cho file lớn
    file_format = Column(String(20))
    material_type = Column(  # ✅ thêm loại tài liệu (slide, syllabus, assignment, ...)
        Enum("syllabus", "textbook", "slide", "assignment", "reference", "code", name="material_type_enum"),
        default="slide"
    )

    # 📊 Thống kê và trạng thái
    download_count = Column(Integer, default=0)
    version = Column(String(20), default="1.0")
    is_public = Column(Integer, default=0)

    # ⏰ Thời gian khả dụng
    available_from = Column(DateTime)
    available_to = Column(DateTime)

    # 👤 Người tạo
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)

    # 🕒 Thời gian hệ thống
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 🧭 Quan hệ ORM
    course = relationship("Course", back_populates="materials", lazy="joined")

    def __repr__(self):
        return f"<CourseMaterial(title='{self.title}', course_id='{self.course_id}', file='{self.file_name}')>"
